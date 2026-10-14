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
import socket
from dataclasses import dataclass
from typing import Final
from urllib.parse import urlparse

RC_NOT_IN_ALLOWLIST: Final[str] = "not_in_trusted_targets"


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


# D-07 / D-26: every host-shaped ConnectorsCfg field must be dispositioned here.
# "check"          -> every host value is checked against trusted_targets.
# "check-registry" -> image references; only an EXPLICIT registry host is checked
#                     (first "/" component containing "." or ":" or == "localhost").
#                     A reference with no explicit registry (``nginx:1.25``) uses the
#                     default registry and is not checked.
# "exempt: <why>"  -> not a scan target; the reason is the record.
# A run-time test walks dataclasses.fields(ConnectorsCfg) so a new field cannot
# ship undispositioned. The enable_* flag is deliberately NOT consulted: a stale
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
    "container_targets": "check-registry",
    "dnssec_resolver": (
        "exempt: resolver infrastructure the operator configures for DNSSEC "
        "queries; not a scan target"
    ),
    "source_targets": (
        "exempt: repository paths scanned from the local filesystem or a clone the "
        "operator configures, not scan targets"
    ),
    "azure_keyvault_urls": _CLOUD_ID,
    "broker_azure_namespaces": _CLOUD_ID,
    "broker_sqs_regions": _CLOUD_ID,
    "gke_clusters": _CLOUD_ID,
    "aks_clusters": _CLOUD_ID,
}


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


def connector_host_values(connectors) -> list:
    """``(field_name, host)`` for every host named by a ``check``/``check-registry`` field."""
    pairs = []
    if connectors is None:
        return pairs
    for name, disposition in CONNECTOR_HOST_FIELD_DISPOSITION.items():
        if disposition not in ("check", "check-registry"):
            continue
        for value in _field_values(connectors, name):
            host = _registry_host(value) if disposition == "check-registry" else _extract_host(value)
            if host:
                pairs.append((name, host))
    return pairs


def _broker_target_hosts(cfg) -> list:
    """Thin wrapper kept for callers: hosts of connectors.broker_targets."""
    connectors = getattr(cfg, "connectors", None)
    return [h for _n, h in connector_host_values(connectors) if _n == "broker_targets"]


def enforce_trusted_targets(cfg) -> None:
    """Single chokepoint (D-04) — raise ValueError on the first untrusted target.
    Called from BOTH run_scan.py::main and jobs.py::create_job.
    """
    trusted = list(getattr(cfg.security, "trusted_targets", None) or [])
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
            raise ValueError(
                f"Target {result.redacted_preview!r} is not in the trusted-targets "
                f"allowlist (security.trusted_targets in config.yaml)."
            )
    for field_name, host in connector_host_values(getattr(cfg, "connectors", None)):
        result = is_target_trusted(host, trusted)
        if not result.ok:
            raise ValueError(
                f"Target {result.redacted_preview!r} (connectors.{field_name}) is not in "
                f"the trusted-targets allowlist (security.trusted_targets in config.yaml)."
            )
