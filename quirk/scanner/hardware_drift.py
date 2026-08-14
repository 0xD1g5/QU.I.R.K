"""Phase 155 (HWLC-04/05/06/07/09): hardware lifecycle drift detection.

Pure computation layer over lists of ``HardwareDevice`` rows (produced by
``quirk.models_util.recent_successful_hardware_rows()``, plan 155-04) — the
N-of-M confirmation gate, per-row state derivations for tier / bridge
evidence / EOL state, the CVE delta, and the candidate-event builder. No DB
writes and no pipeline wiring here — everything in this module is a pure
function, which is what makes it exhaustively unit-testable.

Advisory-only: this module is never referenced by
``quirk/intelligence/scoring.py`` or ``SCORE_WEIGHTS`` (mirroring
``hw_cve.py`` lines 5-8; guarded by a test extending the
``tests/test_cve_score_guard.py`` pattern in plan 155-04, T-155-01).
"""
from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from datetime import date
from typing import Callable, Optional

from quirk.scanner import hw_cve
from quirk.scanner.hardware_eol import eol_state as _eol_state
from quirk.scanner.hardware_tier import TIER_ORDER

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


__all__ = [
    "EVENT_TYPES",
    "DEFAULT_N",
    "DEFAULT_M",
    "DriftCandidate",
    "bridge_evidence_state",
    "eol_state_for_row",
    "tier_direction",
    "cve_delta",
    "compute_drift_candidates",
]
