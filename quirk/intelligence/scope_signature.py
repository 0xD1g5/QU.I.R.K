"""Phase 179 Plan 04: record a scan's scope signature for Phase 180's closure refusal.

This module RECORDS a scan's scope — port scope, profile, optional extras
present, credential presence, sensor set — plus per-probe-family health, as
discrete columns AND a SHA256 digest. It performs no comparison and no
refusal itself: Phase 180 owns the two-sided closure condition and reads
what this module writes. It never imports the quantum-readiness weighting
module (ADVISORY-01, guarded by ``tests/test_remediation_advisory_guard.py``).

The concrete failure this prevents: a re-engagement run with
``--profile quick`` auto-generating an attestation that claims dozens of
false closures against a client's estate. The signature exists so closure
across incomparable scans is *refused*, not silently permitted.

Probe health is POSITIVELY ASSERTED from family-specific evidence columns.
Exit status, the absence of an exception, and ``scan_error IS NULL`` are
explicitly NOT evidence that a probe ran — see TRIAGE-176-03:
``quirk/scanner/ssh_scanner.py::_run_ssh_audit`` passed host and port as two
positionals when ``ssh-audit`` accepts a single ``host:port`` target, so the
invocation exited 2 with empty stdout while the scan itself exited 0 and
``scan_error`` stayed NULL — every SSH scan silently degraded to a banner
grab for the entire life of the integration. A phase timing key may only
DOWNGRADE a family's status to ``not_run``; it may never UPGRADE one to
``healthy`` — Phase 173 found a stale ``broker_scanning`` timing key
surviving in ``run_stats["timings_sec"]`` when no broker phase ran at all,
so timing-key presence alone is never treated as positive evidence here.

Sensor-origin limitation (179-CONTEXT.md § Sensor-Origin Coverage): this
module's signature is keyed on ``scan_run_id``.
``quirk/cli/console_cmd.py::_ingest_envelope`` (~line 565) constructs
``CryptoEndpoint`` rows with ``sensor_id``/``segment`` set but NEVER sets
``scan_run_id`` — so sensor-origin findings have NO signature coverage and
are excluded from closure by explicit user decision. This module does not
synthesize a ``scan_run_id`` for envelopes: a signature that is structurally
present but semantically empty would pass a mismatch check it never actually
evaluated, which is worse than an absent one. See
``persist_scope_signature``'s docstring for the full rationale.

A MISSING signature row for a ``scan_run_id`` means NOT-COMPARABLE, never
comparable-by-default. This is why the signature is written at scan
COMPLETION rather than scan start: a scan that crashes before producing
endpoints leaves no signature row at all, which is the honest outcome —
Phase 180 must treat a missing signature as not-comparable.
"""
from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict, FrozenSet, Iterable, Optional

from quirk.db import get_session
from quirk.models import ScanScopeSignature, Sensor
from quirk.util.optional_extra import REGISTRY, is_extra_available

logger = logging.getLogger(__name__)

# Bump whenever the field set captured by build_scope_signature() changes, so
# Phase 180 can refuse to compare signatures written under different field
# sets rather than silently comparing incomplete records (T-179-15).
SCOPE_SIGNATURE_VERSION = "1.0.0"

# Exactly the fields the digest is computed over. probe_health_json is
# deliberately NOT one of them — see compute_signature_digest()'s docstring.
_DIGEST_FIELDS = (
    "signature_version",
    "port_scope",
    "profile",
    "extras_present",
    "credentials_present",
    "sensor_set",
)


def build_scope_signature(cfg: Any, session: Any = None) -> Dict[str, Any]:
    """Build the six discrete scope-signature fields from a scan's config.

    Returns a dict with keys: signature_version, port_scope, profile,
    extras_present, credentials_present, sensor_set. The three list-valued
    fields are SORTED lists of strings so the digest is stable regardless of
    dict/set iteration order.
    """
    port_scope = getattr(cfg.scan, "nmap_port_scope", None)
    if not port_scope:
        port_scope = ",".join(str(p) for p in sorted(cfg.scan.ports_tls))

    profile = str(getattr(cfg.intelligence, "profile", "") or "")

    extras_present = sorted(
        entry.extra for entry in REGISTRY if is_extra_available(entry.extra)
    )

    # T-179-05 (information disclosure, mitigated): credentials_present
    # stores credential KIND LABELS only. Each check below reads a
    # PRESENCE fact off the credential field (a dict being non-empty, or a
    # username/profile/subscription-id/project-id string being set) — never
    # the field's VALUE. No username, password, env-var name, profile name,
    # subscription id, or project id is ever assigned into this list.
    # Adding a value here would be an information-disclosure defect.
    conn = cfg.connectors
    credentials_present = []
    if getattr(cfg, "broker_credentials", None):
        credentials_present.append("broker")
    if getattr(conn, "snmp_v3_credentials", None):
        credentials_present.append("snmp_v3")
    if getattr(conn, "pg_scanner_user", None):
        credentials_present.append("postgres")
    if getattr(conn, "mysql_scanner_user", None):
        credentials_present.append("mysql")
    if getattr(conn, "aws_profile", None):
        credentials_present.append("aws")
    if getattr(conn, "azure_subscription_id", None):
        credentials_present.append("azure")
    if getattr(conn, "gcp_project_id", None):
        credentials_present.append("gcp")
    credentials_present = sorted(credentials_present)

    # A CLI scan's own endpoints carry no sensor_id (see module docstring's
    # Sensor-Origin Coverage section). This field records the enrolled
    # fleet as a scope fact of the estate, not the origin of the findings
    # in THIS scan.
    sensor_set = []
    if session is not None:
        sensor_set = sorted(row[0] for row in session.query(Sensor.sensor_id).all())

    return {
        "signature_version": SCOPE_SIGNATURE_VERSION,
        "port_scope": port_scope,
        "profile": profile,
        "extras_present": extras_present,
        "credentials_present": credentials_present,
        "sensor_set": sensor_set,
    }


def compute_signature_digest(sig: Dict[str, Any]) -> str:
    """Deterministic SHA256 hex digest over the six scope-signature fields.

    Mirrors quirk.ticketing.base.TicketingChannel.compute_fingerprint's
    canonicalisation shape: json.dumps(payload, sort_keys=True,
    separators=(",", ":")) so key insertion order can never drift the
    digest, then hashlib.sha256(...).hexdigest().

    probe_health_json is deliberately NOT part of this payload — health
    varies scan-to-scan (a transient probe hiccup should not make an
    otherwise-identical scope incomparable) and is persisted alongside for
    Phase 180 to read and reason about separately.
    """
    payload = {field: sig.get(field) for field in _DIGEST_FIELDS}
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _has_evidence(value: Any) -> bool:
    """True iff `value` is positive evidence a probe actually produced output.

    None, "", whitespace-only, "null", "{}", and "[]" all count as NO
    evidence — an empty JSON container is a probe that produced nothing,
    not a probe that succeeded. Non-string truthy values (e.g. a populated
    dict/list already deserialized) count as evidence.
    """
    if value is None:
        return False
    if isinstance(value, str):
        stripped = value.strip()
        if stripped == "" or stripped.lower() in ("null", "{}", "[]"):
            return False
        return True
    return bool(value)


@dataclass(frozen=True)
class _FamilySpec:
    """One probe family's health-assertion recipe.

    enable_attr: the cfg.connectors.enable_* attribute name gating this
        family, or None for an always-on family (tls, ssh).
    evidence_field: the CryptoEndpoint column whose non-empty value is
        POSITIVE evidence the probe produced output.
    timing_key: the run_stats["timings_sec"] key this family's scan phase
        writes when it does real work (Phase 173 D-02 SCOPE-02 contract).
    protocols: the CryptoEndpoint.protocol values that make an endpoint a
        member of this family — determinable and enumerable for every
        family in this table (verified against the live scanner source),
        so no evidence-column-only membership fallback was needed for any
        family (Claude's Discretion per 179-CONTEXT.md, recorded here).
    disabled_extra: optional additional predicate; when it returns True the
        family is treated as not_run regardless of enable_attr. Used by the
        tls family: cfg.scan.tls_enum_mode must be "deep" for
        tls_capabilities_json to ever be populated at all — non-deep TLS is
        not_run, not a degraded probe.
    """

    enable_attr: Optional[str]
    evidence_field: str
    timing_key: str
    protocols: FrozenSet[str]
    disabled_extra: Optional[Callable[[Any], bool]] = None


# Populated from the two verified tables in the plan's <interfaces> section
# (CryptoEndpoint evidence columns + run_scan.py timing-key literals), plus
# the live protocol string constants confirmed in each scanner module.
#
# `database` has no dedicated *_scan_json evidence column (unlike every
# other family) — PostgreSQL/MySQL TLS handshake results are written
# directly onto the shared TLS fields (tls_version, cert_*) rather than a
# JSON blob. tls_version is used as this family's positive-evidence field;
# membership is still determined by protocol (POSTGRESQL/MYSQL), which IS
# enumerable, so no evidence-column-only fallback is needed here either.
_FAMILY_SPEC: Dict[str, _FamilySpec] = {
    "tls": _FamilySpec(
        enable_attr=None,
        evidence_field="tls_capabilities_json",
        timing_key="tls_scanning",
        protocols=frozenset({"TLS"}),
        disabled_extra=lambda cfg: getattr(cfg.scan, "tls_enum_mode", "fast") != "deep",
    ),
    "ssh": _FamilySpec(
        enable_attr=None,
        evidence_field="ssh_audit_json",
        timing_key="ssh_scanning",
        protocols=frozenset({"SSH"}),
    ),
    "jwt": _FamilySpec(
        enable_attr="enable_jwt",
        evidence_field="jwt_scan_json",
        timing_key="jwt_scanning",
        protocols=frozenset({"JWT"}),
    ),
    "container": _FamilySpec(
        enable_attr="enable_container",
        evidence_field="container_scan_json",
        timing_key="container_scanning",
        protocols=frozenset({"CONTAINER"}),
    ),
    "source": _FamilySpec(
        enable_attr="enable_source",
        evidence_field="source_scan_json",
        timing_key="source_scanning",
        protocols=frozenset({"SOURCE"}),
    ),
    "database": _FamilySpec(
        enable_attr="enable_db",
        evidence_field="tls_version",
        timing_key="db_scanning",
        protocols=frozenset({"POSTGRESQL", "MYSQL"}),
    ),
    "dnssec": _FamilySpec(
        enable_attr="enable_dnssec",
        evidence_field="dnssec_scan_json",
        timing_key="dnssec_scanning",
        protocols=frozenset({"DNSSEC"}),
    ),
    "saml": _FamilySpec(
        enable_attr="enable_saml",
        evidence_field="saml_scan_json",
        timing_key="saml_scanning",
        protocols=frozenset({"SAML"}),
    ),
    "kerberos": _FamilySpec(
        enable_attr="enable_kerberos",
        evidence_field="kerberos_scan_json",
        timing_key="kerberos_scanning",
        protocols=frozenset({"KERBEROS"}),
    ),
    "smime": _FamilySpec(
        enable_attr="enable_smime",
        evidence_field="smime_scan_json",
        timing_key="smime_scanning",
        protocols=frozenset({"SMIME"}),
    ),
    "codesign": _FamilySpec(
        enable_attr="enable_codesign",
        evidence_field="codesign_scan_json",
        timing_key="codesign_scanning",
        protocols=frozenset({"CODE_SIGNING"}),
    ),
    "email": _FamilySpec(
        enable_attr="enable_email",
        evidence_field="email_scan_json",
        timing_key="email_scanning",
        protocols=frozenset(
            {
                "SMTP-STARTTLS",
                "SMTPS",
                "IMAP-STARTTLS",
                "IMAPS",
                "POP3-STARTTLS",
                "POP3S",
            }
        ),
    ),
    "broker": _FamilySpec(
        enable_attr="enable_broker",
        evidence_field="broker_scan_json",
        timing_key="broker_scanning",
        protocols=frozenset(
            {"KAFKA-TLS", "KAFKA-PLAIN", "AMQP-PLAIN", "REDIS-TLS", "REDIS-PLAIN"}
        ),
    ),
}


def assess_probe_health(
    cfg: Any, endpoints: Iterable[Any], run_stats: Optional[Dict[str, Any]]
) -> Dict[str, Dict[str, Any]]:
    """Positively assert per-family probe health from family-specific evidence.

    Returns {family: {"status", "evidence_field", "endpoints_seen",
    "endpoints_with_evidence"}} for every family in _FAMILY_SPEC.

    Derivation order (exactly, per plan <behavior>):
      1. family disabled in cfg (or the family's disabled_extra predicate
         fires, e.g. non-deep TLS)                -> not_run
      2. family's timing key absent from
         run_stats["timings_sec"]                  -> not_run
      3. endpoints_with_evidence > 0                -> healthy
      4. endpoints_seen == 0                         -> no_targets
      5. otherwise (seen but none carry evidence)    -> unhealthy

    scan_error and exit status are NEVER consulted — see module docstring.
    A present timing key may only downgrade nothing (it is required to even
    reach step 3); its ABSENCE downgrades to not_run. It never upgrades a
    family to healthy — that requires actual evidence-column content.
    """
    endpoint_list = list(endpoints)
    timings = ((run_stats or {}).get("timings_sec") or {})

    result: Dict[str, Dict[str, Any]] = {}
    for family, spec in _FAMILY_SPEC.items():
        disabled = False
        if spec.enable_attr is not None:
            disabled = not bool(getattr(cfg.connectors, spec.enable_attr, False))
        if not disabled and spec.disabled_extra is not None and spec.disabled_extra(cfg):
            disabled = True

        if disabled or spec.timing_key not in timings:
            result[family] = {
                "status": "not_run",
                "evidence_field": spec.evidence_field,
                "endpoints_seen": 0,
                "endpoints_with_evidence": 0,
            }
            continue

        seen = [e for e in endpoint_list if getattr(e, "protocol", None) in spec.protocols]
        with_evidence = [
            e for e in seen if _has_evidence(getattr(e, spec.evidence_field, None))
        ]

        if len(with_evidence) > 0:
            status = "healthy"
        elif len(seen) == 0:
            status = "no_targets"
        else:
            status = "unhealthy"

        result[family] = {
            "status": status,
            "evidence_field": spec.evidence_field,
            "endpoints_seen": len(seen),
            "endpoints_with_evidence": len(with_evidence),
        }

    return result


