"""Tests for quirk.discovery.coverage bounds clamping and severity normalization.

Closes audit findings:
- scanners-protocol/WR-01 — calculate_coverage clamped to [0.0, 1.0]
- scanners-protocol/WR-02 — quantum_readiness_score severity case-insensitive

See .planning/phases/71-protocol-scanner-warnings/71-CONTEXT.md decisions
D-06 (clamp) and D-07 (.upper() normalization).
"""

import pytest

from quirk.discovery.coverage import calculate_coverage, quantum_readiness_score


# ----------------------------------------------------------------------------
# calculate_coverage clamp tests (WR-01 / D-06 + D-06a percent-scale correction)
# ----------------------------------------------------------------------------


def test_calculate_coverage_clamps_above_one():
    """tls_endpoints exceeding target_count must clamp to 100.0 (percent scale)."""
    result = calculate_coverage(10, 5, 20)
    assert result <= 100.0
    assert result == 100.0


def test_calculate_coverage_clamps_below_zero():
    """Negative target_count must clamp to 0.0, not negative."""
    result = calculate_coverage(-5, 10, 5)
    assert result >= 0.0
    assert result == 0.0


def test_calculate_coverage_zero_denominator():
    """Zero target_count must not raise and must return a value in [0.0, 100.0]."""
    result = calculate_coverage(0, 0, 0)
    assert 0.0 <= result <= 100.0


def test_calculate_coverage_normal_range():
    """A valid mid-range input must return a value within [0.0, 100.0]."""
    result = calculate_coverage(10, 5, 5)
    assert 0.0 <= result <= 100.0


# ----------------------------------------------------------------------------
# quantum_readiness_score severity case-insensitive tests (WR-02 / D-07)
# ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "variant,canonical",
    [
        ("critical", "CRITICAL"),
        ("Critical", "CRITICAL"),
        ("CRITICAL", "CRITICAL"),
        ("high", "HIGH"),
        ("High", "HIGH"),
        ("HIGH", "HIGH"),
        ("medium", "MEDIUM"),
        ("Medium", "MEDIUM"),
        ("MEDIUM", "MEDIUM"),
    ],
)
def test_quantum_readiness_score_severity_case_insensitive(variant, canonical):
    """Severity strings must be compared case-insensitively (via .upper())."""
    endpoints = [object()] * 10  # avoid the discovery-deficit penalty
    score_variant = quantum_readiness_score([{"severity": variant}], endpoints)
    score_canonical = quantum_readiness_score([{"severity": canonical}], endpoints)
    assert score_variant == score_canonical


def test_quantum_readiness_score_high_penalty_applied_for_lowercase():
    """A lowercase 'high' must drop the score (proves it was not silently ignored)."""
    endpoints = [object()] * 10
    score_none = quantum_readiness_score([], endpoints)
    score_high = quantum_readiness_score([{"severity": "high"}], endpoints)
    assert score_high < score_none
