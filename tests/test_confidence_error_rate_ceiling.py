"""Phase 240 SCORE-11: confidence is capped below 60 when the probe error rate is above 0.5.

The 2.0.0 formula let CLOSED rows leave the coverage denominator, so a scan whose
probes mostly failed still earned full coverage points. The ceiling is additive:
rate <= 0.5 is the unchanged 2.0.0 value; rate > 0.5 is min(raw, 59).

The oracle below is a closed-form restatement of the 2.0.0 weights and never
calls compute_confidence (an independent measuring method).

Lowcov arithmetic (31 rows, rate 0.7097, 2 of 2 assessed, TLS 2):
35.0 coverage + 8.709 scan_error + 15.0 unknown + 20.0 tls_enum = 78.709,
rounds to 79, capped to 59.
"""
from __future__ import annotations

import pytest

from quirk.intelligence.confidence import compute_confidence


def _evidence(rate: float, *, coverage: float = 1.0, unknown: int = 0, tls: int = 5) -> dict:
    endpoints = 100
    assessable = 100
    return {
        "totals": {"endpoints": endpoints},
        "protocol_counts": {"TLS": tls, "UNKNOWN": unknown},
        "assessed_crypto_count": int(round(coverage * assessable)),
        "assessable_endpoint_count": assessable,
        "scan_error": {"count": int(rate * endpoints), "rate": rate},
        "tls_enum_coverage_ratio": 1.0,
    }


def _oracle(rate: float, coverage: float, unknown_ratio: float, tls_enum: float, tls: int) -> int:
    pts = 35.0 * coverage + 30.0 * (1.0 - rate) + 15.0 * (1.0 - unknown_ratio)
    if tls > 0:
        pts += 20.0 * tls_enum
    return int(round(pts))


@pytest.mark.parametrize("i", list(range(0, 101)))
def test_sweep_rates_against_oracle(i):
    from quirk.intelligence.confidence import HIGH_ERROR_RATE_CEILING, HIGH_ERROR_RATE_THRESHOLD

    rate = i / 100
    out = compute_confidence(_evidence(rate))
    raw = _oracle(rate, 1.0, 0.0, 1.0, 5)
    cap = out["factor_breakdown"]["high_error_rate_ceiling"]
    if rate > HIGH_ERROR_RATE_THRESHOLD:
        assert out["confidence_score"] < 60
        assert out["confidence_score"] == min(raw, HIGH_ERROR_RATE_CEILING)
        assert cap["applied"] is (raw > HIGH_ERROR_RATE_CEILING)
    else:
        assert out["confidence_score"] == raw
        assert cap["applied"] is False


def test_boundary_half_not_capped_and_just_above_capped():
    from quirk.intelligence.confidence import HIGH_ERROR_RATE_CEILING

    at = compute_confidence(_evidence(0.5))
    assert at["confidence_score"] == 85
    assert at["factor_breakdown"]["high_error_rate_ceiling"]["applied"] is False
    above = compute_confidence(_evidence(0.5001))
    assert above["confidence_score"] == HIGH_ERROR_RATE_CEILING == 59
    br = above["factor_breakdown"]["high_error_rate_ceiling"]
    assert br == {"applied": True, "threshold": 0.5, "ceiling": 59, "uncapped_score": 85}


def test_lowcov_shape_scores_59_with_uncapped_79():
    ev = {
        "totals": {"endpoints": 31},
        "protocol_counts": {"TLS": 2},
        "assessed_crypto_count": 2,
        "assessable_endpoint_count": 2,
        "scan_error": {"count": 22, "rate": 0.7097},
        "tls_enum_coverage_ratio": 1.0,
    }
    out = compute_confidence(ev)
    assert out["confidence_score"] == 59
    assert out["confidence_rating"] == "LOW"
    assert out["factor_breakdown"]["high_error_rate_ceiling"]["uncapped_score"] == 79


def test_low_raw_score_keeps_raw_and_is_not_applied():
    ev = _evidence(0.9, coverage=0.0, unknown=0, tls=0)
    out = compute_confidence(ev)
    raw = _oracle(0.9, 0.0, 0.0, 1.0, 0)
    assert raw <= 59
    assert out["confidence_score"] == raw
    assert out["factor_breakdown"]["high_error_rate_ceiling"]["applied"] is False


def test_no_data_paths_carry_key_and_version():
    zero = compute_confidence({"totals": {"endpoints": 0}})
    nonassess = compute_confidence({"totals": {"endpoints": 3}, "assessable_endpoint_count": 0})
    for out in (zero, nonassess):
        assert out["confidence_rating"] == "NO_DATA"
        assert out["factor_breakdown"]["high_error_rate_ceiling"]["applied"] is False
        assert out["confidence_formula_version"] == "2.1.0"


def test_formula_version_literal_on_main_path():
    assert compute_confidence(_evidence(0.1))["confidence_formula_version"] == "2.1.0"
