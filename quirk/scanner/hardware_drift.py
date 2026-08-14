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
from datetime import date
from typing import Callable, Optional

from quirk.scanner.hardware_eol import eol_state as _eol_state
from quirk.scanner.hardware_tier import TIER_ORDER  # noqa: F401 (re-exported for callers)

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


__all__ = [
    "EVENT_TYPES",
    "DEFAULT_N",
    "DEFAULT_M",
    "bridge_evidence_state",
    "eol_state_for_row",
]
