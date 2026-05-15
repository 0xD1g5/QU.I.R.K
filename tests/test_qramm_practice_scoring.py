"""Phase 74 QWARN-01 — practice scoring correctness tests.

Covers D-01 (out-of-range ValueError), D-02 (Practice 1.1 endpoint-count
discovery_factor), D-03 ('Indeterminate' sentinel) and D-04 (>=3.95 top-band
threshold reachable). RED-then-GREEN gating per Phase 74 plan.
"""
from __future__ import annotations

import math

import pytest

from quirk.qramm.scoring import compute_practice_score, _maturity_label


# --------------- D-01 (WR-02): compute_practice_score validation ---------------


def test_compute_practice_score_rejects_above_range() -> None:
    with pytest.raises(ValueError, match=r"5.*for 1\.1 out of range \[0, 4\]"):
        compute_practice_score([5], practice_id="1.1")


def test_compute_practice_score_rejects_negative() -> None:
    with pytest.raises(ValueError, match=r"out of range \[0, 4\]"):
        compute_practice_score([-1], practice_id="2.3")


def test_compute_practice_score_accepts_full_range_including_zero() -> None:
    # 0 is now valid per D-01 (CONTEXT widens docstring's "1-4" to {0,1,2,3,4})
    assert compute_practice_score([0, 1, 2, 3, 4]) == 2.0


def test_compute_practice_score_empty_list_returns_zero() -> None:
    assert compute_practice_score([]) == 0.0


# --------------- D-02 (WR-04): discovery_factor curve ---------------


@pytest.mark.parametrize(
    "endpoint_count, expected_factor",
    [
        (0, 0.25),       # floor via max(endpoint_count, 1)
        (1, 0.25),       # log10(1)/3 = 0 → clamped to 0.25 floor
        (10, 1.0 / 3.0), # log10(10)/3 ≈ 0.333
        (100, 2.0 / 3.0),# log10(100)/3 ≈ 0.667
        (1000, 1.0),     # log10(1000)/3 = 1.0 (ceiling)
        (10_000, 1.0),   # clamped to 1.0
    ],
)
def test_discovery_factor_curve(endpoint_count: int, expected_factor: float) -> None:
    from quirk.qramm.evidence_bridge import _discovery_factor

    assert _discovery_factor(endpoint_count) == pytest.approx(expected_factor, abs=1e-6)


def test_discovery_factor_applied_to_score_1_1() -> None:
    """Multiplying a raw score by the factor yields the expected rounded result."""
    from quirk.qramm.evidence_bridge import _discovery_factor

    raw = 4
    factor = _discovery_factor(10)
    expected = round(raw * factor, 4)
    assert expected == round(4 * math.log10(10) / 3.0, 4)
    assert expected == pytest.approx(1.3333, abs=1e-4)


# --------------- D-03 (WR-05): 'Indeterminate' sentinel ---------------


def test_maturity_label_indeterminate_on_none() -> None:
    assert _maturity_label(None) == "Indeterminate"


def test_maturity_label_returns_band_for_non_none_input() -> None:
    # 2.5 lands in 'Established' per existing bands; assertion is "NOT Indeterminate"
    label = _maturity_label(2.5)
    assert label != "Indeterminate"
    assert label == "Established"


# --------------- D-04 (WR-06): >=3.95 top-band threshold ---------------


@pytest.mark.parametrize("score", [3.95, 3.99, 4.0])
def test_maturity_label_optimizing_top_band(score: float) -> None:
    assert _maturity_label(score) == "Optimizing"


def test_maturity_label_below_top_band_is_advanced() -> None:
    # 3.94 is below the new >=3.95 threshold — stays in Advanced band.
    assert _maturity_label(3.94) != "Optimizing"
    assert _maturity_label(3.94) == "Advanced"
