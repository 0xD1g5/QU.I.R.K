import logging
import unittest

import pytest

from quirk.intelligence.confidence import compute_confidence
from quirk.intelligence.scoring import compute_readiness_score


def _evidence() -> dict:
    return {
        "totals": {"endpoints": 10, "findings": 4},
        "protocol_counts": {"TLS": 6, "HTTP": 2, "SSH": 1, "UNKNOWN": 1},
        "scan_error": {"count": 1, "rate": 0.1},
        "tls_enum_coverage_ratio": 1.0,
        "plaintext_http_count": 2,
        "http_on_tls_port_count": 1,
        "mtls_present_count": 1,
        "cert_key_type_counts": {"RSA": 6, "ECDSA": 2},
        "certificate_observations": {"certs_observed": 8, "expired_count": 0, "expiring_count": 0, "self_signed_count": 0},
        "finding_severity_counts": {"CRITICAL": 0, "HIGH": 2, "MEDIUM": 1, "LOW": 0, "INFO": 1},
    }


class ConfidenceTests(unittest.TestCase):
    def test_zero_endpoints(self) -> None:
        result = compute_confidence({"totals": {"endpoints": 0}})
        self.assertEqual(result["confidence_score"], 0)
        self.assertEqual(result["confidence_rating"], "NO_DATA")

    def test_many_scan_errors_reduces_confidence(self) -> None:
        base = _evidence()
        noisy = _evidence()
        noisy["scan_error"] = {"count": 8, "rate": 0.8}

        base_score = compute_confidence(base)["confidence_score"]
        noisy_score = compute_confidence(noisy)["confidence_score"]
        self.assertLess(noisy_score, base_score)

    def test_confidence_and_readiness_are_independent_outputs(self) -> None:
        # Use evidence with enough penalties so readiness pre-clamp sum stays under 100.
        # This is required because compute_readiness_score() clamps total to [0, 100]
        # (SCORE-01); the two inputs must differ visibly after clamping.
        heavily_penalized = {
            "totals": {"endpoints": 10, "findings": 4},
            "protocol_counts": {"TLS": 1, "HTTP": 8, "SSH": 1, "UNKNOWN": 0},
            "scan_error": {"count": 5, "rate": 0.5},
            "tls_enum_coverage_ratio": 1.0,
            "plaintext_http_count": 8,
            "http_on_tls_port_count": 7,
            "mtls_present_count": 0,
            "cert_key_type_counts": {"RSA": 10, "ECDSA": 0},
            "certificate_observations": {
                "certs_observed": 8,
                "expired_count": 6,
                "expiring_count": 0,
                "self_signed_count": 5,
            },
            "finding_severity_counts": {"CRITICAL": 0, "HIGH": 2, "MEDIUM": 1, "LOW": 0, "INFO": 1},
        }
        a = heavily_penalized
        b = {**heavily_penalized, "finding_severity_counts": {"CRITICAL": 0, "HIGH": 4, "MEDIUM": 0, "LOW": 0, "INFO": 0}}

        conf_a = compute_confidence(a)["confidence_score"]
        conf_b = compute_confidence(b)["confidence_score"]
        score_a = compute_readiness_score(a)["score"]
        score_b = compute_readiness_score(b)["score"]

        self.assertEqual(conf_a, conf_b)
        self.assertNotEqual(score_a, score_b)


if __name__ == "__main__":
    unittest.main()


def test_zero_tls_produces_no_enum_coverage_bonus():
    """SCORE-03 regression guard (D-08): tls_count=0 must yield 0.0 tls_enum_coverage_ratio points."""
    from quirk.intelligence.confidence import compute_confidence

    evidence = {
        "totals": {"endpoints": 10},
        "protocol_counts": {"TLS": 0, "SSH": 3, "UNKNOWN": 2},
        # Deliberately omit tls_enum_coverage_ratio and tls_enum_coverage_pct
    }
    result = compute_confidence(evidence)
    factor = result["factor_breakdown"]["tls_enum_coverage_ratio"]
    assert factor["value"] == 0.0, f"Expected ratio 0.0, got {factor['value']}"
    assert factor["points"] == 0.0, (
        f"Expected 0.0 points for tls_enum_coverage_ratio when no TLS, got {factor['points']}"
    )


# ---------------------------------------------------------------------------
# D-09 / WR-13 Phase 73: weight-override clamp + fail-loud + WARN unknown keys
# ---------------------------------------------------------------------------

def _baseline_evidence() -> dict:
    return _evidence()


def test_override_clamps_below_zero():
    """Below-zero override values clamp to 0.0."""
    result = compute_confidence(
        _baseline_evidence(), weights={"coverage_ratio": -0.5}
    )
    assert result["factor_breakdown"]["coverage_ratio"]["weight"] == 0.0


def test_override_clamps_above_one():
    """Above-one override values clamp to 1.0."""
    result = compute_confidence(
        _baseline_evidence(), weights={"coverage_ratio": 1.5}
    )
    assert result["factor_breakdown"]["coverage_ratio"]["weight"] == 1.0


def test_override_in_range_passes_through():
    """Override values in [0.0, 1.0] pass through unchanged (float-coerced)."""
    result = compute_confidence(
        _baseline_evidence(), weights={"coverage_ratio": 0.7}
    )
    assert result["factor_breakdown"]["coverage_ratio"]["weight"] == 0.7


def test_override_non_numeric_raises_value_error():
    """Non-numeric override value raises ValueError with diagnostic message."""
    with pytest.raises(ValueError, match=r"must be numeric in \[0\.0, 1\.0\]"):
        compute_confidence(_baseline_evidence(), weights={"coverage_ratio": "abc"})


def test_override_none_value_raises_value_error():
    """None override value raises ValueError."""
    with pytest.raises(ValueError):
        compute_confidence(_baseline_evidence(), weights={"coverage_ratio": None})


def test_override_list_value_raises_value_error():
    """List override value raises ValueError."""
    with pytest.raises(ValueError):
        compute_confidence(_baseline_evidence(), weights={"coverage_ratio": [1.0]})


def test_override_unknown_key_logs_warning_and_accepts(caplog):
    """Unknown override key logs WARNING but does not raise (forward-compat)."""
    with caplog.at_level(logging.WARNING, logger="quirk.intelligence.confidence"):
        result = compute_confidence(
            _baseline_evidence(), weights={"unknown_xyz": 0.5}
        )
    assert result["confidence_score"] >= 0
    # caplog captured at WARNING level — must contain the unknown key name.
    msgs = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    joined = " ".join(msgs)
    assert "unknown_xyz" in joined
    assert "forward-compat" in joined or "Unknown confidence override" in joined
