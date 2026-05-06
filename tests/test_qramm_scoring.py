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
