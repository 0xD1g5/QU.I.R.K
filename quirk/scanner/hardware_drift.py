"""Phase 155 (HWLC-04/05/06/07/09): hardware lifecycle drift detection.

Pure computation layer over lists of ``HardwareDevice`` rows (produced by
``quirk.models_util.recent_successful_hardware_rows()``, plan 155-04) — the
N-of-M confirmation gate, per-row state derivations for tier / bridge
evidence / EOL state, the CVE delta, and the candidate-event builder. Plan
155-04 adds the DB-facing half — ``reconcile_device_history()`` — which
turns candidates into deduplicated, persisted ``HardwareDriftEvent`` rows.
Everything else in this module remains a pure function.

Advisory-only: this module is never referenced by
``quirk/intelligence/scoring.py`` or ``SCORE_WEIGHTS`` (mirroring
``hw_cve.py`` lines 5-8; guarded by an extended
``tests/test_cve_score_guard.py`` test, T-155-01).
"""
from __future__ import annotations

import json
import logging
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Callable, Optional

from quirk.models import HardwareDriftEvent, VendorPqcTrendEvent
from quirk.models_util import recent_successful_hardware_rows, vendor_fleet_snapshot
from quirk.scanner import hw_cve
from quirk.scanner.hardware_eol import eol_state as _eol_state
from quirk.scanner.hardware_tier import TIER_ORDER
from quirk.util.safe_exc import safe_str

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module constants — imported by plan 155-04
# ---------------------------------------------------------------------------

# V5 input-validation allowlist for HardwareDriftEvent.event_type (T-155-03).
EVENT_TYPES: tuple[str, ...] = (
    "tier_crossing",
    "upstream_mitigated_change",
    "cve_delta",
    "eol_state_change",
)

DEFAULT_N: int = 2  # of-M confirmations required to trust a reading (D-02)
DEFAULT_M: int = 3  # window size (D-02)

# V5 input-validation allowlist for VendorPqcTrendEvent.event_type (Phase 160
# HWLC-17, mirrors T-155-03). Deliberately a separate constant from
# EVENT_TYPES because vendor_pqc_trend_events and hardware_drift_events are
# distinct tables (vendor-scoped fleet-wide vs. per-device (host, port)).
VENDOR_EVENT_TYPES: tuple[str, ...] = (
    "pqc_status_change",
)


# ---------------------------------------------------------------------------
# N-of-M confirmation gate (T-155-09, HWLC-07)
# ---------------------------------------------------------------------------


def _confirmed_value(
    rows: list, extractor: Callable[[object], Optional[str]], n: int = DEFAULT_N
) -> Optional[str]:
    """Applies ``extractor`` to every row in ``rows`` (newest-first), drops
    ``None`` results, and returns the single most common value if its count
    is ``>= n``, else ``None``.

    Fail-closed (T-155-09): no value reaching ``n`` — including the
    all-distinct case and the empty case — returns ``None``, meaning "no
    confirmed value -> no event". An extractor callable is used (rather than
    an attribute-name string) because two of the three tracked fields
    (bridge evidence state, EOL state) are DERIVED, not stored columns.
    """
    values = [extractor(row) for row in rows]
    values = [v for v in values if v is not None]
    if not values:
        return None
    counts = Counter(values)
    value, count = counts.most_common(1)[0]
    if count >= n:
        return value
    return None


# ---------------------------------------------------------------------------
# Per-row state derivations
# ---------------------------------------------------------------------------


def bridge_evidence_state(row) -> str:
    """Persisted per-row proxy for upstream-mitigation evidence.

    ``bridge_status`` is NOT a ``HardwareDevice`` column — it is a transient
    dict key computed cross-device by
    ``quirk/cbom/bridge.py::_confirm_upstream_mitigation()``; reading a
    a ``bridge_status`` attribute read directly off the row would silently
    always be ``None`` and the event would never fire. Instead this returns
    ``"evidence_present"`` when
    ``row.bridge_confirmed_at`` is not ``None`` AND
    ``json.loads(row.bridge_evidence_json)`` yields a non-empty list, else
    ``"no_evidence"``.

    Cross-device ``partial_only -> upstream_mitigated`` promotion remains
    owned by ``quirk/cbom/bridge.py`` and is deliberately NOT re-derived
    here — this is only the per-row evidence-presence proxy.

    Never raises (T-155-08): a malformed/non-JSON ``bridge_evidence_json``
    (device-controlled ARP-evidence blob) yields ``"no_evidence"``, not an
    exception.
    """
    if getattr(row, "bridge_confirmed_at", None) is None:
        return "no_evidence"
    try:
        parsed = json.loads(getattr(row, "bridge_evidence_json", None))
    except (TypeError, ValueError):
        return "no_evidence"
    if isinstance(parsed, list) and parsed:
        return "evidence_present"
    return "no_evidence"


def eol_state_for_row(row, today: Optional[date] = None) -> Optional[str]:
    """Thin wrapper around ``hardware_eol.eol_state()`` — does not
    re-implement the date math (D-17 owns it in ``hardware_eol.py``)."""
    return _eol_state(getattr(row, "eol_date", None), today=today)


# ---------------------------------------------------------------------------
# Tier direction helper (D-05) — kept separate from the stored tier value so
# it never corrupts dedup comparisons in plan 155-04.
# ---------------------------------------------------------------------------


def tier_direction(old_tier: Optional[str], new_tier: Optional[str]) -> str:
    """Describes a tier change as ``"improved"`` | ``"worsened"`` |
    ``"unchanged"`` | ``"unknown"`` using ``TIER_ORDER`` (lower int = more
    urgent, so a numerically lower new tier means the device got worse).
    Returns ``"unknown"`` when either tier is absent from ``TIER_ORDER``.
    """
    if old_tier not in TIER_ORDER or new_tier not in TIER_ORDER:
        return "unknown"
    old_rank = TIER_ORDER[old_tier]
    new_rank = TIER_ORDER[new_tier]
    if new_rank == old_rank:
        return "unchanged"
    return "worsened" if new_rank < old_rank else "improved"


# ---------------------------------------------------------------------------
# DriftCandidate + cve_delta() + compute_drift_candidates()
# ---------------------------------------------------------------------------


@dataclass
class DriftCandidate:
    """A candidate drift event produced by ``compute_drift_candidates()``.
    ``old_value``/``new_value`` must remain short scalars — never raw
    banners, never ``bridge_evidence_json`` contents, never SNMP community
    strings (T-155-03)."""

    event_type: str
    old_value: Optional[str]
    new_value: Optional[str]


def _cve_ids_for_row(row) -> set:
    """Returns the set of correlated cve_id strings for one row, applying
    the Phase 142 CVE-01/D-03 vendor gate (empty set for falsy/"Unknown"
    vendor) before calling ``hw_cve.correlate_device()``."""
    vendor = getattr(row, "vendor", None)
    if not vendor or vendor == "Unknown":
        return set()
    result = hw_cve.correlate_device(
        vendor, getattr(row, "model", None), hw_cve.firmware_for_correlation(row)
    )
    return {m["cve_id"] for m in result.matches}


def cve_delta(prior_row, current_row) -> set:
    """Returns the set of ``cve_id`` strings present for ``current_row``'s
    (vendor, model, firmware) but absent for ``prior_row``'s.

    Uses ``hw_cve.firmware_for_correlation()`` for both rows — no
    re-derived firmware expression. Applies the Phase 142 CVE-01/D-03
    vendor gate here (call-site responsibility): if either row's ``vendor``
    is falsy or equals ``"Unknown"``, returns an empty set without calling
    ``correlate_device()`` for that row (and thus never for the delta as a
    whole, since a gated row contributes an empty id set).

    Never caches (D-11) — recomputed every call; the delta intentionally
    reflects ``CVE_TABLE`` growth between scans even when
    vendor/model/firmware are unchanged (D-12).
    """
    for row in (prior_row, current_row):
        vendor = getattr(row, "vendor", None)
        if not vendor or vendor == "Unknown":
            return set()
    prior_ids = _cve_ids_for_row(prior_row)
    current_ids = _cve_ids_for_row(current_row)
    return current_ids - prior_ids


def compute_drift_candidates(
    rows: list, n: int = DEFAULT_N, today: Optional[date] = None
) -> list:
    """Returns a list of ``DriftCandidate`` for one device's ``rows``
    (newest-first list of successful ``HardwareDevice`` rows, produced by
    ``recent_successful_hardware_rows()`` in plan 155-04).

    Returns ``[]`` immediately when ``len(rows) < 2``.

    Tier, bridge-evidence, and EOL-state candidates are each N-of-M gated
    (HWLC-07): a confirmed value is computed via ``_confirmed_value()``; if
    the confirmed value doesn't match the newest row's raw reading, the
    newest reading is unconfirmed (suspected probe flakiness) and no
    candidate is emitted. Otherwise the older rows are scanned newest-first
    for the first value that differs from the confirmed value; if none
    differs, no candidate is emitted (no change).

    These are separate, independently-emitted event types — a bridge change
    is never folded into a tier event (D-06), and both a tier and an EOL
    candidate may be emitted from the same call (D-05; e.g. an EOL date
    crossing into the pre-2030 window can simultaneously flip
    ``assign_tier()``'s output to "Tier N/A", producing both an
    eol_state_change and a tier_crossing candidate).

    The CVE candidate is produced from a direct two-row diff
    (``cve_delta(rows[1], rows[0])``) — deliberately NOT N-of-M gated,
    because CVE membership is a deterministic catalog lookup rather than a
    flaky probe result (D-11/D-12), emitted only when the delta is
    non-empty.
    """
    if len(rows) < 2:
        return []

    candidates: list = []

    _fields = (
        ("tier_crossing", lambda row: getattr(row, "remediation_tier", None)),
        ("upstream_mitigated_change", bridge_evidence_state),
        ("eol_state_change", lambda row: eol_state_for_row(row, today=today)),
    )

    for event_type, extractor in _fields:
        confirmed = _confirmed_value(rows, extractor, n=n)
        if confirmed is None or confirmed != extractor(rows[0]):
            continue
        old_value = None
        for older_row in rows[1:]:
            older_value = extractor(older_row)
            if older_value != confirmed:
                old_value = older_value
                break
        else:
            continue  # no change found among older rows — nothing to emit
        candidates.append(
            DriftCandidate(event_type=event_type, old_value=old_value, new_value=confirmed)
        )

    # CVE delta: direct two-row diff, deliberately ungated (D-11/D-12).
    delta = cve_delta(rows[1], rows[0])
    if delta:
        prior_ids = _cve_ids_for_row(rows[1])
        candidates.append(
            DriftCandidate(
                event_type="cve_delta",
                old_value=str(len(prior_ids)),
                new_value=str(len(delta)),
            )
        )

    return candidates


# ---------------------------------------------------------------------------
# purge_stale_hardware_history() + persist_and_reconcile() (Phase 158
# HWLC-15, plan 158-01) — relocated from run_scan.py so the shared helper
# below can call it without importing the heavyweight root-level run_scan
# module.
# ---------------------------------------------------------------------------


def purge_stale_hardware_history(session, hw_batch, cfg, logger=None) -> int:
    """Hard-delete ``hardware_devices`` rows older than the configured
    time-based retention window, scoped to this scan batch's own devices
    (Phase 154 HWLC-03 / D-10 / D-12).

    D-10: retention is a time-based window (``scan.hardware_history_retention_days``),
    never a row-count cap. D-12: this is an opportunistic, per-scan hard delete —
    NOT a background worker, cron job, or operator-run CLI purge command. Each
    scan purges only the (host, port) pairs present in its own ``hw_batch``; it
    is never a table-wide delete.

    Mandatory safety guard: a non-int, zero, or negative retention value would
    otherwise compute a cutoff of "now" (or later) and hard-delete the
    operator's entire hardware history. Skipping the purge entirely is the
    only safe failure mode for a destructive operation, so any coercion
    failure or a non-positive result logs a warning and returns 0 WITHOUT
    deleting anything.

    Does not commit — the caller owns the transaction (see the placement
    note at the ``run_ot_supplemental_and_persist`` / ``persist_and_reconcile``
    call sites: this must run before the hw_batch add() loop so the delete
    and the inserts share one transaction with no autoflush interaction).

    Returns the total number of deleted rows (0 if skipped or nothing to do).

    Relocated verbatim from ``run_scan.py`` in Phase 158 (D-158-B) — this
    module must not import the heavyweight root-level ``run_scan`` module,
    so ``persist_and_reconcile()`` needs this function co-located here.
    ``run_scan._purge_stale_hardware_history`` remains a module-level alias
    to this function so existing test import paths keep working.
    """
    from quirk.models import HardwareDevice

    if not hw_batch:
        return 0

    retention_raw = getattr(getattr(cfg, "scan", None), "hardware_history_retention_days", 180)
    try:
        retention_days = int(retention_raw)
    except (TypeError, ValueError):
        if logger:
            logger.warning(
                f"Hardware history retention purge skipped: invalid "
                f"hardware_history_retention_days value {safe_str(retention_raw)!r} "
                f"(must be a positive integer)"
            )
        return 0
    if retention_days <= 0:
        if logger:
            logger.warning(
                f"Hardware history retention purge skipped: non-positive "
                f"hardware_history_retention_days value {safe_str(retention_raw)!r}"
            )
        return 0

    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=retention_days)

    scope = {(d.host, d.port) for d in hw_batch}
    deleted = 0
    for host, port in scope:
        deleted += (
            session.query(HardwareDevice)
            .filter(
                HardwareDevice.host == host,
                HardwareDevice.port == port,
                HardwareDevice.scanned_at < cutoff,
            )
            .delete(synchronize_session=False)
        )
    return deleted


def persist_and_reconcile(
    session, devices, cfg, logger=None, owns_session: bool = True
) -> tuple:
    """Shared persist + purge + reconcile helper for hardware device batches
    (Phase 158 HWLC-15).

    Advisory-only: purges stale rows scoped to ``devices``' (host, port)
    pairs, adds every device, commits, then reconciles drift history exactly
    once per distinct ``(host, port)`` pair in the batch. Returns
    ``(purged_count, inserted_drift_events)``.

    ``devices == []`` or ``devices is None`` returns ``(0, [])`` without
    touching the session. ``cfg=None`` is a supported caller choice — the
    purge falls back to the 180-day default retention window.

    D-158-A: this helper always calls ``session.commit()`` internally before
    reconciling — there is deliberately no ``commit: bool`` parameter (the
    signature is locked by CONTEXT.md). ``reconcile_device_history()`` reads
    freshly-committed rows via ``recent_successful_hardware_rows()`` session
    queries, never in-memory batch objects (RESEARCH.md Pattern 3 / Phase-155
    Pitfall 2), so a plain ``flush()`` is not a substitute for the commit
    here. In Plan 03's HTTPS-injected-session case this means hardware rows
    (and whatever else is pending on that session) commit slightly ahead of
    ``_ingest_envelope()``'s own terminal ``db.flush()`` — an accepted
    commit-ordering nuance on advisory-only data (never data loss or
    corruption), since the dedup/enrollment gates both fire strictly before
    the hardware step.

    ``owns_session`` (default ``True``) mirrors the ``_own_session`` pattern
    already used by ``console_cmd.py::_ingest_envelope()``: it tells this
    helper whether ``session`` is exclusively its own (safe to
    ``session.rollback()`` on failure) or a caller-injected, shared session
    that already holds *other* pending, uncommitted work (the HTTPS
    sensor-push route's call pattern, where ``SensorPush``/``CryptoEndpoint``
    rows for the same push are already ``add()``'d/``flush()``'d on the same
    session before this helper runs). When ``owns_session=False``, a failure
    here is logged and ``(0, [])`` is returned WITHOUT calling
    ``session.rollback()`` — rolling back a shared session would silently
    discard the caller's already-pending rows too. The caller remains
    responsible for handling/rolling back its own session in that case
    (CR-01, Phase 158 review).

    Any exception raised anywhere in the body (e.g. ``session.commit()``
    failing) is caught, logged at warning level via ``safe_str()``, and
    ``(0, [])`` is returned — never re-raised (advisory-only, non-fatal).
    """
    if not devices:
        return (0, [])
    try:
        purged = purge_stale_hardware_history(session, devices, cfg, logger)
        for dev in devices:
            session.add(dev)
        session.commit()
        events: list = []
        for host, port in {(d.host, d.port) for d in devices}:
            events.extend(reconcile_device_history(session, host, port))
        return (purged, events)
    except Exception as exc:
        if owns_session:
            # Roll back so a failed insert/commit here (e.g. a malformed
            # sensor-supplied field tripping a NOT NULL constraint) never
            # leaves the session in a broken PendingRollbackError state for
            # the caller to inherit — this helper is advisory-only and must
            # never cause a sensor push or air-gap import to fail (Phase 158
            # HWLC-15).
            try:
                session.rollback()
            except Exception:
                pass
        # else: session is caller-owned/shared (e.g. the HTTPS route's
        # injected `db`, which already holds the caller's own pending
        # SensorPush/CryptoEndpoint rows for this same push) — do NOT roll
        # it back here. Leave rollback/commit decisions to the caller so a
        # hardware-only failure never silently discards unrelated pending
        # work on the shared session (CR-01).
        if logger:
            logger.warning(
                f"Hardware persist/reconcile failed (advisory-only, non-fatal): "
                f"{safe_str(exc)}"
            )
        return (0, [])


# ---------------------------------------------------------------------------
# reconcile_device_history() — DB-facing half (plan 155-04)
# ---------------------------------------------------------------------------


def reconcile_device_history(
    session,
    host: str,
    port: int,
    n: int = DEFAULT_N,
    m: int = DEFAULT_M,
    today: Optional[date] = None,
) -> list:
    """Reconciles one device's (host, port) N-of-M history window into
    deduplicated, persisted ``HardwareDriftEvent`` rows.

    Reads ONLY the freshly-queried, freshly-committed
    ``recent_successful_hardware_rows()`` result (RESEARCH.md Pitfall 2 —
    never in-memory ``hw_batch`` objects, whose changes may not be flushed).

    Dedup-on-write (D-09 / RESEARCH.md Pitfall 4): for each candidate, the
    most recent existing ``HardwareDriftEvent`` for the same
    (host, port, event_type) — ordered by ``detected_at`` desc, ``id`` desc,
    never mixed with ``confirmed_at`` — is looked up; if its ``new_value``
    already matches the candidate's ``new_value``, the candidate is skipped.
    Dedup is scoped per event_type (D-08): an event of one type never
    suppresses an event of a different type for the same device.

    Every candidate's ``event_type`` is validated against ``EVENT_TYPES``
    (T-155-10, V5 input validation) before insert; a candidate failing the
    allowlist is dropped and logged, never persisted.

    Advisory-only (T-155-11): the entire function body is wrapped in a
    broad ``try/except`` that logs at warning level via ``safe_str()`` and
    returns ``[]`` — a DB failure during reconciliation must never abort a
    scan, matching the existing advisory-only hw-persist idiom at
    ``run_scan.py`` (hardware fingerprint DB write).

    Does NOT add any confirmation-tracking column/flag/counter to
    ``HardwareDevice`` — the N-of-M state is recomputed from history on
    every call (D-03). Does NOT cache correlation results (D-11).
    """
    try:
        rows = recent_successful_hardware_rows(session, host, port, limit=m)
        if len(rows) < 2:
            return []

        candidates = compute_drift_candidates(rows, n=n, today=today)
        inserted: list = []
        detected_at = rows[0].scanned_at

        for candidate in candidates:
            if candidate.event_type not in EVENT_TYPES:
                logger.debug(
                    "Dropping drift candidate with out-of-allowlist event_type "
                    "%r for %s:%s", candidate.event_type, host, port,
                )
                continue

            most_recent = (
                session.query(HardwareDriftEvent)
                .filter(
                    HardwareDriftEvent.host == host,
                    HardwareDriftEvent.port == port,
                    HardwareDriftEvent.event_type == candidate.event_type,
                )
                .order_by(HardwareDriftEvent.detected_at.desc(), HardwareDriftEvent.id.desc())
                .first()
            )
            if most_recent is not None and most_recent.new_value == candidate.new_value:
                continue

            event = HardwareDriftEvent(
                host=host,
                port=port,
                event_type=candidate.event_type,
                old_value=candidate.old_value,
                new_value=candidate.new_value,
                detected_at=detected_at,
                confirmed_at=datetime.now(timezone.utc).replace(tzinfo=None),
                # Phase 159 WR-03 fix: capture is_partial_scan from the row
                # that actually produced this event (rows[0], the newest
                # successful HardwareDevice row in this reconciliation
                # window), NOT derived later via a join against the
                # device's current-state row. Same NULL-safe coercion
                # convention as build_device_lookup().
                is_partial_scan=bool(getattr(rows[0], "is_partial_scan", False)),
            )
            session.add(event)
            inserted.append(event)

        session.commit()
        return inserted
    except Exception as exc:
        logger.warning(
            "Hardware drift reconciliation failed (advisory-only, non-fatal): %s",
            safe_str(exc),
        )
        # WR-01: roll back so a failed commit here doesn't leave the shared
        # session in a broken pending-rollback state for subsequent
        # reconcile_device_history() calls in the same batch loop.
        try:
            session.rollback()
        except Exception:
            pass
        return []


def reconcile_vendor_pqc_trend(
    session, vendor: str, n: int = DEFAULT_N, m: int = DEFAULT_M
) -> list:
    """Reconciles one vendor's fleet-wide N-of-M ``pqc_status`` window into
    deduplicated, persisted ``VendorPqcTrendEvent`` rows (Phase 160 HWLC-17).

    Vendor-scoped, fleet-wide, cross-device analogue of
    ``reconcile_device_history()``. Advisory-only — must be called AFTER
    ``session.commit()`` so it reads freshly-committed rows (RESEARCH.md
    Pitfall 4); never called against an in-memory batch list.

    The "new" ``pqc_status`` is read off the persisted
    ``HardwareDevice.pqc_status`` column (catalog-assigned at fingerprint
    time by ``_apply_entry()``), NEVER re-derived from ``HARDWARE_MATRIX``
    here — this module must not import ``quirk.scanner.hardware_meta`` for
    that purpose.

    The entire body is wrapped in a broad ``try/except`` — on any exception,
    logs a warning via ``safe_str()`` (advisory-only, non-fatal), attempts
    ``session.rollback()`` inside its own suppressing try/except, and
    returns ``[]``. Never re-raises; never aborts persistence of
    device/drift rows.
    """
    try:
        rows = vendor_fleet_snapshot(session, vendor, limit=m)
        if len(rows) < 2:
            return []

        confirmed = _confirmed_value(rows, lambda row: getattr(row, "pqc_status", None), n=n)
        if confirmed is None or confirmed != rows[0].pqc_status:
            return []

        old_value = None
        for older_row in rows[1:]:
            older_value = getattr(older_row, "pqc_status", None)
            if older_value != confirmed:
                old_value = older_value
                break
        else:
            return []  # no change found among older rows — nothing to emit

        most_recent = (
            session.query(VendorPqcTrendEvent)
            .filter(
                VendorPqcTrendEvent.vendor == vendor,
                VendorPqcTrendEvent.event_type == "pqc_status_change",
            )
            .order_by(VendorPqcTrendEvent.detected_at.desc(), VendorPqcTrendEvent.id.desc())
            .first()
        )
        if most_recent is not None and most_recent.new_value == confirmed:
            return []

        if "pqc_status_change" not in VENDOR_EVENT_TYPES:
            return []

        event = VendorPqcTrendEvent(
            vendor=vendor,
            event_type="pqc_status_change",
            old_value=old_value,
            new_value=confirmed,
            detected_at=rows[0].scanned_at,
            confirmed_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        session.add(event)
        session.commit()
        return [event]
    except Exception as exc:
        logger.warning(
            "Vendor PQC trend reconciliation failed (advisory-only, non-fatal): %s",
            safe_str(exc),
        )
        try:
            session.rollback()
        except Exception:
            pass
        return []


__all__ = [
    "EVENT_TYPES",
    "VENDOR_EVENT_TYPES",
    "DEFAULT_N",
    "DEFAULT_M",
    "DriftCandidate",
    "bridge_evidence_state",
    "eol_state_for_row",
    "tier_direction",
    "cve_delta",
    "compute_drift_candidates",
    "purge_stale_hardware_history",
    "persist_and_reconcile",
    "reconcile_device_history",
    "reconcile_vendor_pqc_trend",
]
