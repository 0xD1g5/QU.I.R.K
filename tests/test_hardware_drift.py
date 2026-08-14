"""Phase 155 (HWLC-04/05/06/07/09) — unit tests for
``quirk.scanner.hardware_drift``: the N-of-M confirmation gate, per-row
state derivations, CVE delta, and candidate-event builder.

All tests use ``types.SimpleNamespace`` stub rows (no DB session needed) —
matches the style already used in ``tests/test_hardware_tier.py``.
"""
from __future__ import annotations

import datetime as dt
import json
from types import SimpleNamespace

from quirk.scanner.hardware_drift import (
    DEFAULT_M,
    DEFAULT_N,
    EVENT_TYPES,
    _confirmed_value,
    bridge_evidence_state,
    eol_state_for_row,
)


# ---------------------------------------------------------------------------
# Module constants
# ---------------------------------------------------------------------------


def test_event_types_and_defaults() -> None:
    assert EVENT_TYPES == (
        "tier_crossing",
        "upstream_mitigated_change",
        "cve_delta",
        "eol_state_change",
    )
    assert DEFAULT_N == 2
    assert DEFAULT_M == 3


# ---------------------------------------------------------------------------
# _confirmed_value() — N-of-M confirmation gate
# ---------------------------------------------------------------------------


def _tier_extractor(row):
    return getattr(row, "remediation_tier", None)


def test_n_of_m_single_newest_reading_is_outvoted() -> None:
    """A single anomalous newest reading is outvoted by two matching older
    readings — the stable value wins."""
    r_new = SimpleNamespace(remediation_tier="Tier 1")
    r_stable_1 = SimpleNamespace(remediation_tier="Tier 2")
    r_stable_2 = SimpleNamespace(remediation_tier="Tier 2")
    result = _confirmed_value([r_new, r_stable_1, r_stable_2], _tier_extractor, n=2)
    assert result == "Tier 2"


def test_n_of_m_two_matching_values_confirmed() -> None:
    r_a1 = SimpleNamespace(remediation_tier="Tier 1")
    r_a2 = SimpleNamespace(remediation_tier="Tier 1")
    r_b = SimpleNamespace(remediation_tier="Tier 3")
    result = _confirmed_value([r_a1, r_a2, r_b], _tier_extractor, n=2)
    assert result == "Tier 1"


def test_n_of_m_three_distinct_values_returns_none_fail_closed() -> None:
    """Fail-closed: three distinct values, none reaching n=2, returns None."""
    r_a = SimpleNamespace(remediation_tier="Tier 1")
    r_b = SimpleNamespace(remediation_tier="Tier 2")
    r_c = SimpleNamespace(remediation_tier="Tier 3")
    result = _confirmed_value([r_a, r_b, r_c], _tier_extractor, n=2)
    assert result is None


def test_n_of_m_empty_list_returns_none() -> None:
    assert _confirmed_value([], _tier_extractor) is None


def test_n_of_m_single_row_below_threshold_returns_none() -> None:
    r = SimpleNamespace(remediation_tier="Tier 1")
    assert _confirmed_value([r], _tier_extractor, n=2) is None


def test_n_of_m_skips_none_valued_rows() -> None:
    """None-valued rows are dropped before counting and never count as
    agreement."""
    r_none = SimpleNamespace(remediation_tier=None)
    r_a1 = SimpleNamespace(remediation_tier="Tier 1")
    r_a2 = SimpleNamespace(remediation_tier="Tier 1")
    result = _confirmed_value([r_none, r_a1, r_a2], _tier_extractor, n=2)
    assert result == "Tier 1"

    # All-None list also returns None, not a spurious confirmation.
    assert _confirmed_value(
        [SimpleNamespace(remediation_tier=None), SimpleNamespace(remediation_tier=None)],
        _tier_extractor,
        n=2,
    ) is None


# ---------------------------------------------------------------------------
# bridge_evidence_state() — tier_crossing_or_bridge selector
# ---------------------------------------------------------------------------


def test_tier_crossing_or_bridge_evidence_present() -> None:
    row = SimpleNamespace(
        bridge_confirmed_at=dt.datetime.now(),
        bridge_evidence_json=json.dumps([{"target_ip": "1.2.3.4", "mac": "aa:bb:cc:dd:ee:ff"}]),
    )
    assert bridge_evidence_state(row) == "evidence_present"


def test_tier_crossing_or_bridge_no_confirmed_at() -> None:
    row = SimpleNamespace(bridge_confirmed_at=None, bridge_evidence_json="[]")
    assert bridge_evidence_state(row) == "no_evidence"


def test_tier_crossing_or_bridge_empty_evidence_list() -> None:
    row = SimpleNamespace(bridge_confirmed_at=dt.datetime.now(), bridge_evidence_json="[]")
    assert bridge_evidence_state(row) == "no_evidence"


def test_tier_crossing_or_bridge_malformed_json_never_raises() -> None:
    """T-155-08: malformed/non-JSON bridge_evidence_json returns
    'no_evidence' rather than raising."""
    row = SimpleNamespace(bridge_confirmed_at=dt.datetime.now(), bridge_evidence_json="not-json")
    assert bridge_evidence_state(row) == "no_evidence"


def test_tier_crossing_or_bridge_none_evidence_json_never_raises() -> None:
    row = SimpleNamespace(bridge_confirmed_at=dt.datetime.now(), bridge_evidence_json=None)
    assert bridge_evidence_state(row) == "no_evidence"


def test_tier_crossing_or_bridge_missing_attrs_default_no_evidence() -> None:
    """Never raises on an object lacking the expected attributes."""
    assert bridge_evidence_state(SimpleNamespace()) == "no_evidence"


# ---------------------------------------------------------------------------
# eol_state_for_row() — thin wrapper over hardware_eol.eol_state()
# ---------------------------------------------------------------------------


def test_eol_state_for_row_none_when_no_eol_date() -> None:
    row = SimpleNamespace(eol_date=None)
    assert eol_state_for_row(row) is None


def test_eol_state_for_row_passed() -> None:
    today = dt.date(2026, 8, 14)
    row = SimpleNamespace(eol_date=dt.date(2020, 1, 1))
    assert eol_state_for_row(row, today=today) == "passed"


def test_eol_state_for_row_approaching() -> None:
    today = dt.date(2026, 8, 14)
    row = SimpleNamespace(eol_date=today + dt.timedelta(days=30))
    assert eol_state_for_row(row, today=today) == "approaching"


def test_eol_state_for_row_missing_attr_returns_none() -> None:
    assert eol_state_for_row(SimpleNamespace()) is None
