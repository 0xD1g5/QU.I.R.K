"""Phase 143 / TAIL-02: server-enforced trusted-targets scan-consent allowlist.

Single chokepoint (D-04) for both scan entry points — the CLI (``run_scan.py::main``)
and the dashboard (``quirk/dashboard/api/routes/jobs.py::create_job``). Neither entry
point re-implements matching; both call ``is_target_trusted`` / ``enforce_trusted_targets``
from this module.

Matching (D-06): exact host/IP string membership, or CIDR containment for entries that
contain a "/". No wildcard-subdomain matching. An empty ``trusted_targets`` list means
allow-all (D-03) — backward compatible with every existing scan config.
"""
from __future__ import annotations

import ipaddress
import re
import socket
import unicodedata
from dataclasses import dataclass
from typing import Final, Optional
from urllib.parse import urlparse

RC_NOT_IN_ALLOWLIST: Final[str] = "not_in_trusted_targets"
RC_UNREADABLE_TARGET: Final[str] = "unreadable_target_value"
RC_NON_ASCII_IP_LITERAL: Final[str] = "non_ascii_ip_literal"
RC_AMBIGUOUS_TARGET: Final[str] = "ambiguous_target_value"

SHAPE_URL: Final[str] = "url"
SHAPE_LDAP: Final[str] = "ldap"
SHAPE_HOST_PORT: Final[str] = "host-port"
SHAPE_NAME: Final[str] = "name"
# Host and port with no IP-literal host containing ":"; used while a connector still
# splits its target on the first ":" (plan 239-06 moves it to parse_target).
SHAPE_HOST_PORT_NO_V6: Final[str] = "host-port-no-v6"


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    reason: str
    redacted_preview: str


def is_target_trusted(host_or_ip: str, trusted_targets: list) -> ValidationResult:
    """D-03: empty trusted_targets means allow-all (backward compatible).
    D-06: exact host/IP match OR CIDR containment — no wildcard subdomains.
    """
    if not trusted_targets:
        return ValidationResult(True, "", "")

    if host_or_ip is AMBIGUOUS_TARGET:
        return ValidationResult(False, RC_AMBIGUOUS_TARGET, "")

    if not isinstance(host_or_ip, str):
        return ValidationResult(False, RC_UNREADABLE_TARGET, "<unreadable value>")

    # Phase 239 TRUST-03 D-12: refuse before the exact match so a listed non-ASCII
    # string cannot pass. Non-IP forms go through resolution below and the gate
    # checks the resolved address.
    try:
        ipaddress.ip_address(host_or_ip)
    except ValueError:
        pass
    else:
        if not host_or_ip.isascii():
            return ValidationResult(False, RC_NON_ASCII_IP_LITERAL, host_or_ip[:32])

    if host_or_ip in trusted_targets:
        return ValidationResult(True, "", "")

    try:
        candidate_ip = ipaddress.ip_address(host_or_ip)
    except ValueError:
        try:
            results = socket.getaddrinfo(host_or_ip, None, family=socket.AF_UNSPEC)
            candidate_ips = [ipaddress.ip_address(r[4][0]) for r in results if r[4]]
        except (socket.gaierror, OSError, UnicodeError, ValueError):
            return ValidationResult(False, RC_NOT_IN_ALLOWLIST, host_or_ip[:32])
    else:
        candidate_ips = [candidate_ip]

    for entry in trusted_targets:
        if "/" not in entry:
            continue
        try:
            network = ipaddress.ip_network(entry, strict=False)
        except ValueError:
            continue
        if any(ip in network for ip in candidate_ips):
            return ValidationResult(True, "", "")

    return ValidationResult(False, RC_NOT_IN_ALLOWLIST, host_or_ip[:32])


class AmbiguousTargetError(ValueError):
    """A target value does not read as exactly one host and port."""


@dataclass(frozen=True)
class ParsedTarget:
    host: str
    port: Optional[int]
    scheme: Optional[str]


class _AmbiguousTarget:
    """Marker yielded by connector_host_values for a value parse_target refuses."""

    def __repr__(self) -> str:
        return "<ambiguous target value>"


AMBIGUOUS_TARGET: Final = _AmbiguousTarget()

_SCHEME_RE = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*\Z")
_NAME_FORBIDDEN = frozenset(": / @ ? # , [ ] %".split())


def _is_ip(text: str) -> bool:
    try:
        ipaddress.ip_address(text)
    except ValueError:
        return False
    return True


def _parse_port(text: str) -> int:
    if not (text.isascii() and text.isdigit()):
        raise AmbiguousTargetError("port")
    port = int(text)
    if not 1 <= port <= 65535:
        raise AmbiguousTargetError("port")
    return port


def _split_authority(text: str, default_port: Optional[int]) -> "tuple[str, Optional[int]]":
    """Host and port of an authority: ``host``, ``host:port``, ``[v6]``, ``[v6]:port`` or a bare IP."""
    if not text:
        raise AmbiguousTargetError("authority")
    if text.startswith("["):
        close = text.find("]")
        if close == -1:
            raise AmbiguousTargetError("authority")
        inner = text[1:close]
        if not _is_ip(inner):
            raise AmbiguousTargetError("authority")
        rest = text[close + 1:]
        if not rest:
            return inner, default_port
        if not rest.startswith(":"):
            raise AmbiguousTargetError("authority")
        return inner, _parse_port(rest[1:])
    colons = text.count(":")
    if colons == 0:
        return text, default_port
    if colons == 1:
        host, _, port_text = text.partition(":")
        if not host:
            raise AmbiguousTargetError("authority")
        return host, _parse_port(port_text)
    if _is_ip(text):
        return text, default_port
    raise AmbiguousTargetError("authority")


def _refuse_if(value: str, chars: str) -> None:
    if any(c in value for c in chars):
        raise AmbiguousTargetError("form")


def parse_target(value, shape: str, default_port: Optional[int] = None) -> ParsedTarget:
    """The one definition of a target value's host and port, per consumer shape.

    The trust gate and the connectors that read a host themselves both call
    this function, so they read a target's host with one shared parser. A
    value that does not read as exactly one host and port raises
    AmbiguousTargetError. No stdlib URL accessor is used: their validation
    differs between Python versions.
    """
    if not isinstance(value, str):
        raise AmbiguousTargetError("type")
    if not value.strip():
        raise AmbiguousTargetError("empty")
    for ch in value:
        if ch.isspace() or ch in "\\;" or unicodedata.category(ch) in ("Cc", "Cs"):
            raise AmbiguousTargetError("character")
    scheme: Optional[str] = None
    if shape == SHAPE_NAME:
        if not _is_ip(value) and any(c in value for c in _NAME_FORBIDDEN):
            raise AmbiguousTargetError("name")
        return ParsedTarget(value, None, None)
    if "://" not in value:
        _refuse_if(value, "/@?#,")
        authority = value
        port_default = default_port or (389 if shape == SHAPE_LDAP else None)
    elif shape in (SHAPE_HOST_PORT, SHAPE_HOST_PORT_NO_V6):
        raise AmbiguousTargetError("form")
    elif shape == SHAPE_LDAP:
        scheme, _, rest = value.partition("://")
        scheme = scheme.lower()
        if scheme not in ("ldap", "ldaps"):
            raise AmbiguousTargetError("scheme")
        authority = rest.split("/", 1)[0]
        _refuse_if(authority, "@?#,")
        port_default = default_port or (636 if scheme == "ldaps" else 389)
    else:
        scheme, _, rest = value.partition("://")
        if not _SCHEME_RE.match(scheme):
            raise AmbiguousTargetError("scheme")
        end = len(rest)
        for mark in "/?#":
            cut = rest.find(mark)
            if cut != -1:
                end = min(end, cut)
        authority = rest[:end]
        _refuse_if(authority, "@,")
        port_default = default_port
    host, port = _split_authority(authority, port_default)
    if "%" in host and not (":" in host and _is_ip(host)):
        raise AmbiguousTargetError("escape")
    if shape == SHAPE_HOST_PORT_NO_V6 and ":" in host:
        raise AmbiguousTargetError("form")
    if shape == SHAPE_URL:
        host = host.lower()
    return ParsedTarget(host, port, scheme)


# D-07 / D-26: every ConnectorsCfg field that can name a host is dispositioned here.
# "check"            -> every host value is checked against trusted_targets.
# "check-registry"   -> image references; only an EXPLICIT registry host is checked
#                       (first "/" component containing "." or ":" or == "localhost").
#                       A reference with no explicit registry (``nginx:1.25``) uses the
#                       default registry and is not checked.
# "check-kubeconfig" -> a kubeconfig path; every ``clusters[].cluster.server`` host
#                       in that file is checked. A file that cannot be used as a
#                       kubeconfig is checked as the path itself, so it fails closed.
# "exempt: <why>"    -> not a scan target; the reason is the record.
# Every other field is listed in CONNECTOR_NON_HOST_FIELDS with a reason. A
# run-time test walks every dataclasses.fields(ConnectorsCfg) entry and requires
# one classification each, so a new field cannot ship unclassified. The enable_* flag is deliberately NOT consulted: a stale
# untrusted host in a disabled connector is refused with the field named, which is
# safer than a list that silently starts being contacted once the connector is on.
_CLOUD_ID = (
    "exempt: cloud provider control-plane identifier reached through the provider "
    "API, not an operator-network host"
)
CONNECTOR_HOST_FIELD_DISPOSITION: Final[dict] = {
    "jwt_targets": "check",
    "saml_targets": "check",
    "kerberos_targets": "check",
    "dnssec_targets": "check",
    "smime_targets": "check",
    "adcs_targets": "check",
    "codesign_targets": "check",
    "pg_targets": "check",
    "mysql_targets": "check",
    "broker_targets": "check",
    "vault_addr": "check",
    "aws_endpoint_url": "check",
    # Each entry is a full vault URL the Key Vault client connects to.
    "azure_keyvault_urls": "check",
    "container_targets": "check-registry",
    "k8s_kubeconfig": "check-kubeconfig",
    "dnssec_resolver": (
        "exempt: resolver infrastructure the operator configures for DNSSEC "
        "queries; not a scan target"
    ),
    "source_targets": (
        "exempt: repository paths scanned from the local filesystem or a clone the "
        "operator configures, not scan targets"
    ),
    "broker_azure_namespaces": _CLOUD_ID,
    "broker_sqs_regions": _CLOUD_ID,
    "gke_clusters": _CLOUD_ID,
    "aks_clusters": _CLOUD_ID,
}


CONNECTOR_FIELD_TARGET_SHAPE: Final[dict] = {
    "jwt_targets": SHAPE_URL,
    "saml_targets": SHAPE_URL,
    "vault_addr": SHAPE_URL,
    "aws_endpoint_url": SHAPE_URL,
    "azure_keyvault_urls": SHAPE_URL,
    "adcs_targets": SHAPE_LDAP,
    "smime_targets": SHAPE_LDAP,
    "codesign_targets": SHAPE_LDAP,
    "pg_targets": SHAPE_HOST_PORT_NO_V6,
    "mysql_targets": SHAPE_HOST_PORT_NO_V6,
    "broker_targets": SHAPE_HOST_PORT,
    "kerberos_targets": SHAPE_HOST_PORT,
    "dnssec_targets": SHAPE_NAME,
}

_FLAG = "on/off switch; names no host"
_CRED = "credential or credential reference; names no host"
_CLOUD_SELECTOR = "cloud account, region or project selector used with the provider API"
_LDAP_BASE = "LDAP search base inside a directory whose host is a checked *_targets field"
_TIMEOUT = "timeout in seconds"
_K8S_SELECTOR = (
    "selects a cluster, context or namespace inside the kubeconfig, whose server "
    "hosts are checked through k8s_kubeconfig"
)
CONNECTOR_NON_HOST_FIELDS: Final[dict] = {
    "enable_aws": _FLAG, "enable_azure": _FLAG, "enable_jwt": _FLAG,
    "enable_container": _FLAG, "enable_source": _FLAG, "enable_nmap": _FLAG,
    "enable_kerberos": _FLAG, "enable_saml": _FLAG, "enable_dnssec": _FLAG,
    "enable_smime": _FLAG, "enable_adcs": _FLAG, "enable_codesign": _FLAG,
    "enable_gcp": _FLAG, "enable_db": _FLAG, "enable_s3": _FLAG,
    "enable_blob": _FLAG, "enable_k8s": _FLAG, "enable_vault": _FLAG,
    "enable_email": _FLAG, "enable_broker": _FLAG,
    "enable_authenticated_mode": _FLAG, "enable_snmp": _FLAG,
    "enable_modbus": _FLAG, "enable_bacnet": _FLAG, "enable_recurring_otics": _FLAG,
    "vault_tls_verify": "TLS verification switch for vault_addr; names no host",
    "aws_region": _CLOUD_SELECTOR, "aws_profile": _CLOUD_SELECTOR,
    "azure_subscription_id": _CLOUD_SELECTOR, "gcp_project_id": _CLOUD_SELECTOR,
    "k8s_provider": "managed-Kubernetes provider name; names no host",
    "k8s_cluster_name": _K8S_SELECTOR, "k8s_namespace": _K8S_SELECTOR,
    "k8s_context": _K8S_SELECTOR,
    "smime_search_base": _LDAP_BASE, "adcs_search_base": _LDAP_BASE,
    "codesign_search_base": _LDAP_BASE,
    "smime_timeout": _TIMEOUT, "adcs_timeout": _TIMEOUT, "codesign_timeout": _TIMEOUT,
    "adcs_user": _CRED, "adcs_password": _CRED,
    "pg_scanner_user": _CRED, "pg_scanner_password": _CRED,
    "mysql_scanner_user": _CRED, "mysql_scanner_password": _CRED,
    "vault_token": _CRED, "snmp_community": _CRED,
    "snmp_v3_credentials": (
        "per-host SNMPv3 credentials looked up for hosts discovered from the "
        "checked targets; names no additional target"
    ),
    "vault_transit_mount": "path inside the vault named by vault_addr",
    "kerberos_probe_principal": (
        "client principal name sent in the AS-REQ to a checked kerberos_targets KDC; names no host"
    ),
    "_user_set_fields": "internal record of which keys the YAML set",
}

# A kubeconfig larger than this is not parsed; it is checked as the path itself.
_KUBECONFIG_MAX_BYTES: Final[int] = 1024 * 1024


def _kubeconfig_server_hosts(path) -> list:
    """Hosts of every ``clusters[].cluster.server`` in the kubeconfig at *path*.

    Anything that cannot be read as a kubeconfig with at least one cluster
    server yields ``[path]`` so the caller checks the path as a unit and
    fails closed.
    """
    import os
    import stat

    import yaml

    if not isinstance(path, str) or not path.strip():
        return []
    path = path.strip()
    try:
        st = os.stat(path)
        if not stat.S_ISREG(st.st_mode) or st.st_size > _KUBECONFIG_MAX_BYTES:
            return [path]
        with open(path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    except Exception:  # noqa: BLE001 - any unusable file fails closed
        return [path]
    hosts = []
    clusters = data.get("clusters") if isinstance(data, dict) else None
    for entry in clusters if isinstance(clusters, list) else []:
        cluster = entry.get("cluster") if isinstance(entry, dict) else None
        server = cluster.get("server") if isinstance(cluster, dict) else None
        host = _extract_host(server) if isinstance(server, str) else None
        hosts.append(host or path)
    return hosts or [path]


def _extract_host(value) -> "str | None":
    """Best-effort HOST of a target value. Never imports quirk.config.

    Handles URLs, ``[v6]``/``[v6]:port``, ``host:port``, bare hosts, dicts and
    objects with a ``host`` attribute. Anything unparseable is returned whole
    (stripped) so it is checked as a unit and fails closed.
    """
    if isinstance(value, dict):
        value = value.get("host")
    elif value is not None and not isinstance(value, str):
        value = getattr(value, "host", None)
    if not isinstance(value, str):
        return None
    candidate = value.strip()
    if not candidate:
        return None
    if "://" in candidate:
        try:
            host = urlparse(candidate).hostname
        except ValueError:
            host = None
        return host or candidate
    if candidate.startswith("["):
        rb = candidate.find("]")
        host = candidate[1:rb].strip() if rb != -1 else candidate
        return host or candidate
    if candidate.count(":") == 1:
        return candidate.split(":", 1)[0].strip() or candidate
    return candidate


def _registry_host(image_ref) -> "str | None":
    """Explicit registry host of an image reference, else None (default registry)."""
    if not isinstance(image_ref, str):
        return None
    ref = image_ref.strip()
    if "/" not in ref:
        return None
    first = ref.split("/", 1)[0]
    if "." in first or ":" in first or first == "localhost":
        return first.rsplit(":", 1)[0] if ":" in first and not first.startswith("[") else first
    return None


def _field_values(connectors, name):
    if isinstance(connectors, dict):
        raw = connectors.get(name)
    else:
        raw = getattr(connectors, name, None)
    if raw is None:
        return []
    if isinstance(raw, (list, tuple, set, frozenset)):
        return list(raw)
    return [raw]


def as_target_list(value) -> list:
    """Phase 239 TRUST-01 D-03/D-21/D-22: one shape for a target list however it is written.

    Shared by ConnectorsCfg.__post_init__, config_from_dict's and
    server_config's trusted_targets reads, and enforce_trusted_targets.
    A list is returned as the same object; a tuple/set/frozenset becomes a
    list; None and "" mean no targets; any other value is one target.
    Elements are never converted.
    """
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, (tuple, set, frozenset)):
        return list(value)
    if isinstance(value, str) and value == "":
        return []
    return [value]


def connector_host_values(connectors) -> list:
    """``(field_name, host)`` for every host named by a ``check*`` field.

    An element with no readable host (mapping without a host, int, None) is
    yielded as ``(field, None)`` so the gate refuses it while an allowlist is
    set. Empty and whitespace-only strings name nothing and are skipped.
    """
    pairs = []
    if connectors is None:
        return pairs
    for name, disposition in CONNECTOR_HOST_FIELD_DISPOSITION.items():
        if disposition not in ("check", "check-registry", "check-kubeconfig"):
            continue
        for value in _field_values(connectors, name):
            if disposition == "check-kubeconfig":
                pairs.extend((name, h) for h in _kubeconfig_server_hosts(value))
                continue
            if disposition == "check":
                if isinstance(value, dict):
                    source = value.get("host")
                elif value is not None and not isinstance(value, str):
                    source = getattr(value, "host", None)
                else:
                    source = value
                if not isinstance(source, str):
                    pairs.append((name, None))
                elif source.strip():
                    try:
                        pairs.append(
                            (name, parse_target(source, CONNECTOR_FIELD_TARGET_SHAPE[name]).host)
                        )
                    except AmbiguousTargetError:
                        pairs.append((name, AMBIGUOUS_TARGET))
                continue
            host = _registry_host(value)
            if host:
                pairs.append((name, host))
            elif not isinstance(value, str):
                pairs.append((name, None))
    return pairs


def _broker_target_hosts(cfg) -> list:
    """Thin wrapper kept for callers: hosts of connectors.broker_targets."""
    connectors = getattr(cfg, "connectors", None)
    return [h for _n, h in connector_host_values(connectors) if _n == "broker_targets" and isinstance(h, str)]


def refusal_message(result: ValidationResult, field_name: "str | None" = None) -> str:
    """The one operator-facing refusal text, used at every refusal site (D-14/D-24)."""
    where = f" (connectors.{field_name})" if field_name else ""
    if result.reason == RC_NON_ASCII_IP_LITERAL:
        return (
            f"Target {result.redacted_preview!r}{where} is an IP address literal "
            f"containing non-ASCII characters and is refused "
            f"(security.trusted_targets in config.yaml)."
        )
    if result.reason == RC_AMBIGUOUS_TARGET:
        return (
            f"A value{where} does not read as exactly one host and port and is "
            f"refused while the trusted-targets check is on "
            f"(security.trusted_targets in config.yaml)."
        )
    if result.reason == RC_UNREADABLE_TARGET:
        return (
            f"A value{where} has no readable host and is refused while the "
            f"trusted-targets check is on (security.trusted_targets in config.yaml)."
        )
    return (
        f"Target {result.redacted_preview!r}{where} is not in the trusted-targets "
        f"allowlist (security.trusted_targets in config.yaml)."
    )


def enforce_trusted_targets(cfg) -> None:
    """Single chokepoint (D-04) — raise ValueError on the first untrusted target.
    Called from BOTH run_scan.py::main and jobs.py::create_job.
    """
    trusted = as_target_list(getattr(cfg.security, "trusted_targets", None))
    if not trusted:
        return  # D-03: allow-all when empty
    plain = (
        list(cfg.targets.fqdns or [])
        + list(cfg.targets.cidrs or [])
        + list(getattr(cfg.targets, "include_ips", None) or [])
    )
    for target in plain:
        result = is_target_trusted(target, trusted)
        if not result.ok:
            raise ValueError(refusal_message(result))
    for field_name, host in connector_host_values(getattr(cfg, "connectors", None)):
        result = is_target_trusted(host, trusted)
        if not result.ok:
            raise ValueError(refusal_message(result, field_name))
