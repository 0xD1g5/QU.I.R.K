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
    DriftCandidate,
    _confirmed_value,
    bridge_evidence_state,
    compute_drift_candidates,
    cve_delta,
    eol_state_for_row,
    tier_direction,
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


# ---------------------------------------------------------------------------
# tier_direction()
# ---------------------------------------------------------------------------


def test_tier_direction() -> None:
    assert tier_direction("Tier 2", "Tier 1") == "worsened"
    assert tier_direction("Tier 1", "Tier 3") == "improved"
    assert tier_direction("Tier 1", "Tier 1") == "unchanged"
    assert tier_direction("Tier 1", "bogus") == "unknown"
    assert tier_direction("bogus", "Tier 1") == "unknown"


# ---------------------------------------------------------------------------
# cve_delta()
# ---------------------------------------------------------------------------


def test_cve_delta_returns_new_ids(monkeypatch) -> None:
    from quirk.scanner import hw_cve

    def fake_correlate(vendor, model, firmware):
        if firmware == "old":
            return hw_cve.CveMatchResult(matches=[{"cve_id": "CVE-A"}], confidence="high", attempted=True)
        return hw_cve.CveMatchResult(
            matches=[{"cve_id": "CVE-A"}, {"cve_id": "CVE-B"}], confidence="high", attempted=True
        )

    monkeypatch.setattr(hw_cve, "correlate_device", fake_correlate)
    prior = SimpleNamespace(vendor="Cisco", model="IOS", modbus_firmware="old", bacnet_firmware=None)
    current = SimpleNamespace(vendor="Cisco", model="IOS", modbus_firmware="new", bacnet_firmware=None)
    assert cve_delta(prior, current) == {"CVE-B"}


def test_cve_delta_empty_when_same_set(monkeypatch) -> None:
    from quirk.scanner import hw_cve

    def fake_correlate(vendor, model, firmware):
        return hw_cve.CveMatchResult(matches=[{"cve_id": "CVE-A"}], confidence="high", attempted=True)

    monkeypatch.setattr(hw_cve, "correlate_device", fake_correlate)
    row_a = SimpleNamespace(vendor="Cisco", model="IOS", modbus_firmware="1", bacnet_firmware=None)
    row_b = SimpleNamespace(vendor="Cisco", model="IOS", modbus_firmware="1", bacnet_firmware=None)
    assert cve_delta(row_a, row_b) == set()


def test_cve_delta_empty_when_vendor_none_or_unknown() -> None:
    current = SimpleNamespace(vendor="Cisco", model="IOS", modbus_firmware=None, bacnet_firmware=None)

    prior_none = SimpleNamespace(vendor=None, model="IOS", modbus_firmware=None, bacnet_firmware=None)
    assert cve_delta(prior_none, current) == set()

    prior_unknown = SimpleNamespace(
        vendor="Unknown", model=None, modbus_firmware=None, bacnet_firmware=None
    )
    assert cve_delta(prior_unknown, current) == set()


def test_cve_delta_uses_firmware_for_correlation(monkeypatch) -> None:
    from quirk.scanner import hw_cve

    calls = []

    def fake_correlate(vendor, model, firmware):
        calls.append(firmware)
        return hw_cve.CveMatchResult(matches=[], confidence=None, attempted=True)

    monkeypatch.setattr(hw_cve, "correlate_device", fake_correlate)
    row = SimpleNamespace(vendor="Cisco", model="IOS", modbus_firmware="1.2", bacnet_firmware="9")
    cve_delta(row, row)
    assert calls == ["1.2", "1.2"]


# ---------------------------------------------------------------------------
# compute_drift_candidates()
# ---------------------------------------------------------------------------


def _make_row(
    tier="Tier 3",
    bridge_confirmed_at=None,
    bridge_evidence_json=None,
    eol_date=None,
    vendor=None,
    model=None,
    modbus_firmware=None,
    bacnet_firmware=None,
):
    return SimpleNamespace(
        remediation_tier=tier,
        bridge_confirmed_at=bridge_confirmed_at,
        bridge_evidence_json=bridge_evidence_json,
        eol_date=eol_date,
        vendor=vendor,
        model=model,
        modbus_firmware=modbus_firmware,
        bacnet_firmware=bacnet_firmware,
    )


def test_compute_drift_candidates_empty_and_single_row() -> None:
    assert compute_drift_candidates([]) == []
    assert compute_drift_candidates([_make_row()]) == []


def test_compute_drift_candidates_tier_crossing_confirmed() -> None:
    rows = [_make_row(tier="Tier 1"), _make_row(tier="Tier 1"), _make_row(tier="Tier 2")]
    candidates = compute_drift_candidates(rows)
    tier_candidates = [c for c in candidates if c.event_type == "tier_crossing"]
    assert len(tier_candidates) == 1
    assert tier_candidates[0].old_value == "Tier 2"
    assert tier_candidates[0].new_value == "Tier 1"


def test_compute_drift_candidates_tier_flaky_reading_suppressed() -> None:
    """HWLC-07 core suppression: one flaky newest reading among two stable
    older readings produces NO tier_crossing candidate."""
    rows = [_make_row(tier="Tier 1"), _make_row(tier="Tier 2"), _make_row(tier="Tier 2")]
    candidates = compute_drift_candidates(rows)
    assert not any(c.event_type == "tier_crossing" for c in candidates)


def test_compute_drift_candidates_bridge_evidence_change_separate_from_tier() -> None:
    rows = [
        _make_row(
            tier="Tier 3",
            bridge_confirmed_at=dt.datetime.now(),
            bridge_evidence_json=json.dumps([{"target_ip": "1.2.3.4", "mac": "aa"}]),
        ),
        _make_row(
            tier="Tier 3",
            bridge_confirmed_at=dt.datetime.now(),
            bridge_evidence_json=json.dumps([{"target_ip": "1.2.3.4", "mac": "aa"}]),
        ),
        _make_row(tier="Tier 3", bridge_confirmed_at=None, bridge_evidence_json=None),
    ]
    candidates = compute_drift_candidates(rows)
    bridge_candidates = [c for c in candidates if c.event_type == "upstream_mitigated_change"]
    assert len(bridge_candidates) == 1
    assert bridge_candidates[0].old_value == "no_evidence"
    assert bridge_candidates[0].new_value == "evidence_present"
    assert not any(c.event_type == "tier_crossing" for c in candidates)


def test_compute_drift_candidates_eol_driven_tier_crossing_pitfall_3() -> None:
    """RESEARCH.md Pitfall 3: a tier change caused solely by eol_date going
    from None to a real pre-2030 date must return BOTH an eol_state_change
    AND a tier_crossing candidate from one call — neither dropped, neither
    double-counted."""
    today = dt.date(2026, 8, 14)
    eol = dt.date(2027, 1, 1)
    rows = [
        _make_row(tier="Tier N/A", eol_date=eol),
        _make_row(tier="Tier N/A", eol_date=eol),
        _make_row(tier="Tier 3", eol_date=None),
    ]
    candidates = compute_drift_candidates(rows, today=today)
    event_types = {c.event_type for c in candidates}
    assert "eol_state_change" in event_types
    assert "tier_crossing" in event_types

    tier_c = next(c for c in candidates if c.event_type == "tier_crossing")
    assert tier_c.old_value == "Tier 3"
    assert tier_c.new_value == "Tier N/A"

    eol_c = next(c for c in candidates if c.event_type == "eol_state_change")
    assert eol_c.new_value == "approaching"


def test_compute_drift_candidates_cve_delta_ungated_two_row(monkeypatch) -> None:
    """The CVE candidate is produced WITHOUT N-of-M gating (direct two-row
    diff), unlike tier/bridge/eol which require n=2 confirmations."""
    from quirk.scanner import hw_cve

    def fake_correlate(vendor, model, firmware):
        if firmware == "old":
            return hw_cve.CveMatchResult(matches=[{"cve_id": "CVE-A"}], confidence="high", attempted=True)
        return hw_cve.CveMatchResult(
            matches=[{"cve_id": "CVE-A"}, {"cve_id": "CVE-B"}], confidence="high", attempted=True
        )

    monkeypatch.setattr(hw_cve, "correlate_device", fake_correlate)
    rows = [
        _make_row(tier="Tier 3", vendor="Cisco", model="IOS", modbus_firmware="new"),
        _make_row(tier="Tier 3", vendor="Cisco", model="IOS", modbus_firmware="old"),
    ]
    candidates = compute_drift_candidates(rows)
    cve_candidates = [c for c in candidates if c.event_type == "cve_delta"]
    assert len(cve_candidates) == 1
    assert cve_candidates[0].new_value == "1"
    assert cve_candidates[0].old_value == "1"


def test_compute_drift_candidates_all_event_types_are_valid() -> None:
    rows = [_make_row(tier="Tier 1"), _make_row(tier="Tier 1"), _make_row(tier="Tier 2")]
    candidates = compute_drift_candidates(rows)
    for c in candidates:
        assert isinstance(c, DriftCandidate)
        assert c.event_type in EVENT_TYPES
