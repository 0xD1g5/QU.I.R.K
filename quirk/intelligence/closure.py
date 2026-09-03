"""Phase 180 Plan 04 (CLOSE-01): the two-sided, machine-observed closure computation.

This module is the requirement's substance. Plan 01 made scope-signature comparability
sound (adding the target-set digest that closes the estate-blind hole); this module is
what USES that soundness to decide closure. The failure being prevented is a client
attestation claiming remediation that never happened, so every design tension here
resolves toward under-claiming: refuse over proceed, ``not_observed`` over ``closed``,
machine-observed over asserted.

THE TWO-SIDED CONDITION (CLOSE-01): a fingerprint closes if and only if BOTH sides
hold — (a) it was present in a scope-comparable PRIOR scan, AND (b) the CURRENT scan
positively rechecked that fingerprint's host:port with a HEALTHY probe and did not find
it there. Absence alone is NEVER sufficient. This copies Qualys's explicit guardrail —
"does not mark a QID closed if the scanner did not recheck it" — which Tenable and Orca
concur with. A vanished host, a curtailed scan, or a shrunk target list is not evidence
of remediation.

``no_targets`` and ``not_run`` probe statuses (and ``unhealthy``) all yield
``not_observed``, never ``closed`` — the recheck never actually happened, or happened
and produced no positive signal either way.

A MISSING scope signature on either side of the comparison is NOT-COMPARABLE, never
comparable-by-default — this honours ``persist_scope_signature``'s docstring
(``quirk/intelligence/scope_signature.py``), written specifically for this module to
respect: a scan that crashed before producing a signature leaves no row at all, which is
the honest outcome, not a clean baseline to compare against.

Prior-scan selection deliberately does NOT use
``quirk/dashboard/api/routes/trends.py::_list_session_timestamps``. That helper folds
NULL-``scan_run_id`` (sensor-origin) rows into session grouping via a millisecond-
timestamp fallback key — precisely the sensor-origin population Phase 179 excluded from
scope-signature coverage (179-CONTEXT.md Sensor-Origin Coverage). Reusing it here would
silently re-admit sensor rows into a closure computation that must stay scoped to
``scan_run_id``-bearing CLI scans. Instead, the prior scan is selected purely by
``ScanScopeSignature.created_at DESC`` (T-180-22).

Probe health is READ from ``probe_health_json`` and NEVER re-derived from
``scan_error``/exit status — see TRIAGE-176-03: an SSH scan invocation bug caused every
scan to exit 0 with ``scan_error`` NULL while the probe had, in fact, silently degraded
to a banner grab. Trusting exit status here would let a probe reported healthy after
silent degradation close items that were never really rechecked (T-180-19). A malformed
or empty ``probe_health_json`` blob is treated as an empty dict, which makes every family
resolve to ``not_run`` and therefore every candidate closure resolve to ``not_observed``
— the honest failure direction (T-180-24).

D-28 — there is NO human-assert path, and its absence is enforced mechanically, not just
by convention. ``compute_closure``'s only parameters are ``db_path`` and ``scan_run_id``
— no flag, config key, environment variable, or function parameter anywhere lets a
caller supply a state (T-180-21). See ``tests/test_closure_verification.py``'s
``# CLOSE-01 (D-28)`` section for the falsifiable source-level proof, including a
negative control.

This module must NEVER reach the quantum-readiness weighting module
(ADVISORY-01, standing across Phases 177-181), nor the dashboard layer.
``tests/test_remediation_advisory_guard.py`` enforces the former with an
AST-level guard.

``resurfaced`` detection is Plan 05's responsibility, NOT this module's — Plan 05 reads
and writes ``RESURFACED_STATE``/``OPEN_LIKE_STATES`` from ``quirk/intelligence/remediation.py``
on top of what this module establishes. Pipeline wiring into ``run_scan.py`` is Plan 06's
responsibility, NOT this module's — nothing here is called from the scan pipeline yet.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from quirk.db import get_session
from quirk.intelligence.remediation import CLOSURE_EVENT_TYPES
from quirk.intelligence.scope_signature import SCOPE_SIGNATURE_VERSION, family_for_protocol
from quirk.models import (
    CryptoEndpoint,
    RemediationClosureEvent,
    RemediationItem,
    RemediationItemFingerprint,
    ScanScopeSignature,
)

logger = logging.getLogger(__name__)

CLOSURE_MODEL_VERSION = "1.0.0"

# D-25: a fixed comparability ladder — the FIRST failing check names the reason. Fixed
# order means the counter a human reads is deterministic, and the most structural
# failure is reported rather than the most superficial one.
COMPARABILITY_REASONS: Tuple[str, ...] = (
    "comparable",
    "no_prior_scan",
    "missing_signature",
    "signature_version_gap",
    "missing_target_set_digest",
    "scope_mismatch",
)

_HEALTHY_STATUS = "healthy"
_CLOSED_STATE = "closed"
_TWO_SIDED_REASON = "two_sided_verified"

_COUNTER_KEYS: Tuple[str, ...] = (
    "closed",
    "items_closed",
    "refused_no_prior",
    "refused_missing_signature",
    "refused_signature_version_gap",
    "refused_missing_target_set_digest",
    "refused_scope_mismatch",
    "refused_probe",
    "refused_absent_endpoint",
    "unchanged",
)


def _zero_counters() -> Dict[str, int]:
    return {key: 0 for key in _COUNTER_KEYS}


def select_prior_scan_run_id(session: Any, *, current_scan_run_id: str) -> Optional[str]:
    """Return the scan_run_id of the most recent OTHER scan, or None if there isn't one.

    Ordered by ``ScanScopeSignature.created_at DESC`` — deliberately NOT through
    ``trends.py::_list_session_timestamps`` (see module docstring). ``ScanScopeSignature``
    rows only ever exist for ``scan_run_id``-bearing CLI scans, which is precisely the
    population closure is scoped to.
    """
    row = (
        session.query(ScanScopeSignature)
        .filter(ScanScopeSignature.scan_run_id != current_scan_run_id)
        .order_by(ScanScopeSignature.created_at.desc())
        .first()
    )
    return row.scan_run_id if row is not None else None


def scans_are_comparable(
    session: Any, *, current_scan_run_id: str, prior_scan_run_id: Optional[str]
) -> Tuple[bool, str]:
    """Evaluate D-25's fixed comparability ladder; return (True, "comparable") or
    (False, reason) at the FIRST failing check.
    """
    if not prior_scan_run_id:
        return False, "no_prior_scan"

    current_sig = (
        session.query(ScanScopeSignature)
        .filter(ScanScopeSignature.scan_run_id == current_scan_run_id)
        .one_or_none()
    )
    prior_sig = (
        session.query(ScanScopeSignature)
        .filter(ScanScopeSignature.scan_run_id == prior_scan_run_id)
        .one_or_none()
    )
    # A MISSING signature on EITHER side is NOT-COMPARABLE, never
    # comparable-by-default (persist_scope_signature's docstring contract).
    if current_sig is None or prior_sig is None:
        return False, "missing_signature"

    if (
        current_sig.signature_version != SCOPE_SIGNATURE_VERSION
        or prior_sig.signature_version != SCOPE_SIGNATURE_VERSION
    ):
        return False, "signature_version_gap"

    if not current_sig.target_set_digest or not prior_sig.target_set_digest:
        return False, "missing_target_set_digest"

    if current_sig.digest != prior_sig.digest:
        return False, "scope_mismatch"

    return True, "comparable"


def probe_family_status(probe_health: Dict[str, Any], protocol: Optional[str]) -> str:
    """Resolve `protocol` to its probe family's status, or "not_run" (D-26).

    "not_run" is returned when the protocol is None, unclaimed by any family
    (``family_for_protocol`` returns None), or absent from the health blob. Treating an
    unclassified protocol as healthy would let a finding on it close on absence alone —
    treating it as not_run makes it resolve to not_observed, the honest under-claim.
    """
    if not protocol:
        return "not_run"
    family = family_for_protocol(protocol)
    if family is None:
        return "not_run"
    entry = probe_health.get(family)
    if not entry:
        return "not_run"
    return entry.get("status", "not_run")


def _load_probe_health(current_sig: Optional[ScanScopeSignature]) -> Dict[str, Any]:
    if current_sig is None or not current_sig.probe_health_json:
        return {}
    try:
        loaded = json.loads(current_sig.probe_health_json)
    except (TypeError, ValueError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _write_closure_event(
    session: Any,
    *,
    slug: str,
    finding_fingerprint: Optional[str],
    scan_run_id: str,
    prior_scan_run_id: Optional[str],
    event_type: str,
    from_state: Optional[str],
    to_state: Optional[str],
    reason: Optional[str],
) -> None:
    # D-22: the write-site allowlist is enforced here, not decoratively —
    # an unvalidated allowlist is decoration.
    if event_type not in CLOSURE_EVENT_TYPES:
        raise ValueError(
            f"closure.py: refusing to write RemediationClosureEvent with "
            f"event_type={event_type!r} — not a member of CLOSURE_EVENT_TYPES"
        )
    session.add(
        RemediationClosureEvent(
            slug=slug,
            finding_fingerprint=finding_fingerprint,
            scan_run_id=scan_run_id,
            prior_scan_run_id=prior_scan_run_id,
            event_type=event_type,
            from_state=from_state,
            to_state=to_state,
            reason=reason,
            observed_at=datetime.now(timezone.utc),
        )
    )


def compute_closure(db_path: str, scan_run_id: str) -> Dict[str, int]:
    """Compute two-sided closure for `scan_run_id` against its selected prior scan.

    Only parameters are db_path and scan_run_id (D-28) — no caller can supply a state.

    Returns a counters dict; every key in `_COUNTER_KEYS` is ALWAYS present (never a
    sparse dict — a missing key is indistinguishable from zero to a downstream reader).

    Advisory bookkeeping layered on already-persisted scan data — this function must
    NEVER be able to fail a scan. Any exception is caught, logged, and reported back as
    zeroed counters (mirrors persist_remediation_snapshot's exception-guard style).
    """
    counters = _zero_counters()

    if not db_path or not scan_run_id:
        logger.warning("closure: skipped — missing db_path or scan_run_id")
        return counters

    try:
        with get_session(db_path) as session:
            prior_scan_run_id = select_prior_scan_run_id(
                session, current_scan_run_id=scan_run_id
            )
            if prior_scan_run_id is None:
                counters["refused_no_prior"] = 1
                return counters

            comparable, reason = scans_are_comparable(
                session,
                current_scan_run_id=scan_run_id,
                prior_scan_run_id=prior_scan_run_id,
            )
            if not comparable:
                counters[f"refused_{reason}"] = 1
                return counters

            current_sig = (
                session.query(ScanScopeSignature)
                .filter(ScanScopeSignature.scan_run_id == scan_run_id)
                .one_or_none()
            )
            probe_health = _load_probe_health(current_sig)

            current_endpoints: Dict[Tuple[Any, Any], Optional[str]] = {
                (row.host, row.port): row.protocol
                for row in session.query(CryptoEndpoint)
                .filter(CryptoEndpoint.scan_run_id == scan_run_id)
                .all()
            }
            current_fingerprints = {
                (row.slug, row.finding_fingerprint)
                for row in session.query(RemediationItemFingerprint)
                .filter(RemediationItemFingerprint.scan_run_id == scan_run_id)
                .all()
            }

            prior_rows = (
                session.query(RemediationItemFingerprint)
                .filter(RemediationItemFingerprint.scan_run_id == prior_scan_run_id)
                .all()
            )

            touched_slugs = set()
            for row in prior_rows:
                touched_slugs.add(row.slug)

                # Idempotency: a fingerprint already closed by a prior run of this
                # exact computation stays closed and writes nothing new.
                if row.state == _CLOSED_STATE:
                    counters["unchanged"] += 1
                    continue

                # Clause (e): the fingerprint must be GONE from the current scan.
                if (row.slug, row.finding_fingerprint) in current_fingerprints:
                    counters["unchanged"] += 1
                    continue

                # Clause (c): a CryptoEndpoint must exist for the CURRENT scan at
                # this row's host:port. Absence alone is never sufficient (the
                # Qualys guardrail).
                endpoint_key = (row.host, row.port)
                if endpoint_key not in current_endpoints:
                    counters["refused_absent_endpoint"] += 1
                    continue

                # Clause (d): that endpoint's protocol family must be HEALTHY.
                protocol = current_endpoints[endpoint_key]
                status = probe_family_status(probe_health, protocol)
                if status != _HEALTHY_STATUS:
                    counters["refused_probe"] += 1
                    continue

                # All five clauses hold — close it.
                from_state = row.state
                row.state = _CLOSED_STATE
                _write_closure_event(
                    session,
                    slug=row.slug,
                    finding_fingerprint=row.finding_fingerprint,
                    scan_run_id=scan_run_id,
                    prior_scan_run_id=prior_scan_run_id,
                    event_type="closed",
                    from_state=from_state,
                    to_state=_CLOSED_STATE,
                    reason=_TWO_SIDED_REASON,
                )
                counters["closed"] += 1

            # D-27: item-level rollup. A RemediationItem becomes closed only when it
            # has at least one constituent fingerprint (at the prior scan) and EVERY
            # one of them is now closed. evidence_only items have zero constituent
            # fingerprints by construction and are correctly never touched here.
            for slug in touched_slugs:
                item = (
                    session.query(RemediationItem)
                    .filter(
                        RemediationItem.slug == slug,
                        RemediationItem.scan_run_id == prior_scan_run_id,
                    )
                    .one_or_none()
                )
                if item is None or item.state == _CLOSED_STATE:
                    continue

                constituent_states = [
                    r.state
                    for r in prior_rows
                    if r.slug == slug
                ]
                if constituent_states and all(
                    s == _CLOSED_STATE for s in constituent_states
                ):
                    item.state = _CLOSED_STATE
                    counters["items_closed"] += 1

            session.commit()
        return counters
    except Exception:  # noqa: BLE001 — must never fail a scan
        logger.exception(
            "closure: failed to compute closure for scan_run_id=%s", scan_run_id
        )
        return _zero_counters()
