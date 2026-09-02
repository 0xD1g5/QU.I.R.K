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


