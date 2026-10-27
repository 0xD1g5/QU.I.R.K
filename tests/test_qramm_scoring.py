"""Tests for quirk/qramm/scoring.py — QRAMM-04.

Verifies CSNP reference calculation, weakest-link rule (D-06), profile
multiplier application, overall score formula, maturity thresholds,
and D-09 isolation (no risk_engine/scanner/db/models imports).
"""
from __future__ import annotations

import inspect
import pathlib

import pytest

from quirk.qramm import scoring
from quirk.qramm.scoring import (
    compute_dimension_score,
    compute_overall_score,
    compute_practice_score,
)


def test_practice_score_reference():
    """CSNP-verified reference: [3,2,3,4,2,2,3,2,3,1] -> 2.5."""
    scores = [3, 2, 3, 4, 2, 2, 3, 2, 3, 1]
    assert compute_practice_score(scores) == 2.5


def test_practice_score_empty():
    """Empty answer list returns 0.0 (not error)."""
    assert compute_practice_score([]) == 0.0


def test_weakest_link_rule():
    """D-06: dimension score is min() of practice scores, NOT mean."""
    # If this were a mean, result would be (2.5 + 3.4 + 1.5) / 3 == 2.466...
    assert compute_dimension_score([2.5, 3.4, 1.5]) == 1.5


def test_weakest_link_empty():
    """Empty practice scores returns 0.0."""
    assert compute_dimension_score([]) == 0.0


def test_profile_multiplier():
    """Multiplier 1.2 applied to dimension score 1.5 yields weighted 1.8."""
    result = compute_overall_score(
        {"CVI": 1.5, "SGRM": 1.5, "DPE": 1.5, "ITR": 1.5},
        multiplier=1.2,
    )
    assert result["dimensions"]["CVI"] == pytest.approx(1.8)
    assert result["dimensions"]["SGRM"] == pytest.approx(1.8)
    assert result["overall"] == pytest.approx(1.8)
    assert result["profile_multiplier"] == 1.2


def test_overall_score_csnp_example():
    """CSNP worked example: dims (2.8, 3.1, 2.5, 2.9), mult 1.0 -> 2.825 'Established'."""
    result = compute_overall_score(
        {"CVI": 2.8, "SGRM": 3.1, "DPE": 2.5, "ITR": 2.9},
        multiplier=1.0,
    )
    assert result["overall"] == pytest.approx(2.825)
    assert result["maturity"] == "Established"
    assert result["profile_multiplier"] == 1.0


def test_overall_score_default_multiplier():
    """Default multiplier is 1.0 (neutral) when not specified."""
    result = compute_overall_score({"CVI": 2.0, "SGRM": 2.0, "DPE": 2.0, "ITR": 2.0})
    assert result["profile_multiplier"] == 1.0
    assert result["overall"] == pytest.approx(2.0)


def test_maturity_label_thresholds():
    """Maturity thresholds: 1.0-1.4 Basic | 1.5-2.4 Developing | 2.5-3.4 Established | 3.5-3.9 Advanced | 4.0 Optimizing."""
    cases = [
        (1.0, "Basic"),
        (1.4, "Basic"),
        (1.5, "Developing"),
        (2.4, "Developing"),
        (2.5, "Established"),
        (3.4, "Established"),
        (3.5, "Advanced"),
        (3.9, "Advanced"),
        (4.0, "Optimizing"),
    ]
    for score, expected in cases:
        result = compute_overall_score({"CVI": score, "SGRM": score, "DPE": score, "ITR": score}, 1.0)
        assert result["maturity"] == expected, f"score={score}: expected {expected}, got {result['maturity']}"


def test_d09_isolation_no_forbidden_imports():
    """D-09: scoring.py must not import risk_engine, scanner, db, or models.

    This is a static-source check — guards against circular import chains
    that would block Phase 53's evidence bridge.
    """
    src_path = pathlib.Path(inspect.getsourcefile(scoring))
    text = src_path.read_text(encoding="utf-8")
    forbidden = ["quirk.risk_engine", "quirk.scanner", "quirk.db", "quirk.models"]
    for f in forbidden:
        assert f"from {f}" not in text, f"D-09 violation: scoring.py imports {f}"
        assert f"import {f}" not in text, f"D-09 violation: scoring.py imports {f}"


@pytest.mark.parametrize("raw_score", [i * 0.5 for i in range(0, 9)])
def test_maturity_label_no_gaps_no_overlaps(raw_score):
    """SCORE-04: every score in [0.0, 4.0] at 0.5-step increments maps to
    exactly one of the five canonical QRAMM maturity labels — no gaps, no
    fall-throughs, no None returns.

    Steps: 0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0 (9 values)
    Per CONTEXT.md D-09.
    """
    from quirk.qramm.scoring import _maturity_label

    VALID_LABELS = {"Basic", "Developing", "Established", "Advanced", "Optimizing"}
    label = _maturity_label(raw_score)
    assert label is not None, f"_maturity_label({raw_score}) returned None"
    assert label in VALID_LABELS, (
        f"_maturity_label({raw_score}) returned unexpected label: {label!r}"
    )


def test_maturity_label_covers_all_five_levels():
    """Sanity check: the 9-step sweep produces all five canonical labels at
    least once, confirming full coverage of the maturity band."""
    from quirk.qramm.scoring import _maturity_label

    scores = [i * 0.5 for i in range(0, 9)]
    labels_seen = {_maturity_label(s) for s in scores}
    expected = {"Basic", "Developing", "Established", "Advanced", "Optimizing"}
    assert labels_seen == expected, (
        f"Not all labels covered. Missing: {expected - labels_seen}, "
        f"Unexpected: {labels_seen - expected}"
    )


# ---------- Phase 234 SCORE-10 (D-14 / D-25) ----------


def test_overall_mean_over_assessed_dimensions_only():
    """D-14: a Not-assessed dimension is excluded, never averaged in as 0.

    Same dimension scores as the shared contract fixture's scenario:
    (0.0 + 2.0 + 0.0) / 3 = 0.6667 (ITR excluded), not (0+2+0+0)/4 = 0.5.
    """
    result = compute_overall_score(
        {"CVI": 0.0, "SGRM": 2.0, "DPE": 0.0, "ITR": 0.0},
        multiplier=1.0,
        assessed={"CVI", "SGRM", "DPE"},
    )
    assert result["overall"] == pytest.approx(0.6667, abs=1e-4)
    assert result["maturity"] == "Basic"
    assert result["assessed_dimensions"] == ["CVI", "SGRM", "DPE"]
    assert result["dimensions_assessed"] == 3
    assert result["dimensions_total"] == 4
    # The weighted per-dimension block still reports all four dimensions.
    assert set(result["dimensions"]) == {"CVI", "SGRM", "DPE", "ITR"}


def test_overall_is_none_when_no_dimension_assessed():
    """D-14: zero assessed dimensions -> overall pending (None), not 0."""
    result = compute_overall_score(
        {"CVI": 0.0, "SGRM": 0.0, "DPE": 0.0, "ITR": 0.0},
        multiplier=1.0,
        assessed=[],
    )
    assert result["overall"] is None
    assert result["maturity"] == "Indeterminate"
    assert result["assessed_dimensions"] == []
    assert result["dimensions_assessed"] == 0
    assert result["dimensions_total"] == 4


def test_assessed_is_required_keyword():
    """D-14 / T-234-02c: ``assessed`` has no default, so omitting it can
    never silently restore the all-four-dimensions average."""
    with pytest.raises(TypeError):
        compute_overall_score({"CVI": 2.0, "SGRM": 2.0, "DPE": 2.0, "ITR": 2.0})
    with pytest.raises(TypeError):
        # Keyword-only: a third positional argument is rejected too.
        compute_overall_score(
            {"CVI": 2.0, "SGRM": 2.0, "DPE": 2.0, "ITR": 2.0},
            1.0,
            ["CVI", "SGRM", "DPE", "ITR"],
        )
    params = inspect.signature(compute_overall_score).parameters
    assert params["assessed"].kind is inspect.Parameter.KEYWORD_ONLY
    assert params["assessed"].default is inspect.Parameter.empty


def test_overall_state_is_recalculate_without_answered_counts():
    """D-25: a score_json saved before Phase 234 (no answered_by_dimension)
    still averaged Not-assessed dimensions as 0, so its overall reads
    'recalculate'; a score carrying its counts reads 'current'."""
    from quirk.qramm.assessment_state import overall_state

    legacy = {"overall": 0.5, "maturity": "Basic", "dimensions": {}}
    assert overall_state(legacy) == "recalculate"
    # A non-dict value is not a count map: still legacy.
    assert overall_state(dict(legacy, answered_by_dimension=None)) == (
        "recalculate"
    )
    current = dict(
        legacy,
        overall=0.6667,
        answered_by_dimension={"CVI": 3, "SGRM": 30, "DPE": 5, "ITR": 0},
    )
    assert overall_state(current) == "current"
    assert overall_state(None) is None
