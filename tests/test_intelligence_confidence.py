import logging
import unittest

import pytest

from quirk.intelligence.confidence import compute_confidence
from quirk.intelligence.scoring import compute_readiness_score


def _evidence() -> dict:
    return {
        "totals": {"endpoints": 10, "findings": 4},
        "protocol_counts": {"TLS": 6, "HTTP": 2, "SSH": 1, "UNKNOWN": 1},
        # Phase 184.1 SCORE-01: protocol_counts is 6 TLS + 2 HTTP + 1 SSH + 1 UNKNOWN
        # over totals.endpoints == 10. Under the new rules 6 TLS + 2 HTTP (D-08 keeps
        # plaintext HTTP in the numerator) + 1 SSH = 9 assessed; the 1 UNKNOWN is
        # excluded from the numerator but stays in the denominator (D-09); no
        # ADVISORY/CLOSED rows, so the denominator remains 10.
        "assessed_crypto_count": 9,
        "assessable_endpoint_count": 10,
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
            # Phase 184.1 SCORE-01: 1 TLS + 8 HTTP (D-08) + 1 SSH = 10 assessed;
            # no UNKNOWN/ADVISORY/CLOSED rows, so denominator also remains 10.
            "assessed_crypto_count": 10,
            "assessable_endpoint_count": 10,
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

    def test_evidence_fixture_carries_assessed_counters(self) -> None:
        """Phase 184.1 SCORE-01 false-negative guard: _evidence() must carry both new
        coverage counter keys with non-zero values. Without this guard, a future edit
        could silently drop assessed_crypto_count / assessable_endpoint_count back out
        of the fixture and re-arm the exact false negative this plan exists to avoid —
        compute_confidence defaults missing keys to 0, so coverage_ratio would compute
        0/10 = 0.0 without any test noticing (relative-comparison tests would still pass).
        """
        evidence = _evidence()
        self.assertIn("assessed_crypto_count", evidence)
        self.assertIn("assessable_endpoint_count", evidence)
        self.assertGreater(evidence["assessed_crypto_count"], 0)
        self.assertGreater(evidence["assessable_endpoint_count"], 0)

    def test_coverage_ratio_uses_evidence_derived_counters(self) -> None:
        """Phase 184.1 SCORE-01: coverage_ratio == assessed_crypto_count / assessable_endpoint_count,
        not (tls_count + ssh_count) / endpoints. _evidence() carries 9 assessed / 10 assessable
        (see its docstring), which is 0.9 under the new formula versus 0.7 under the old one
        (6 TLS + 1 SSH = 7 / 10 endpoints) — a value that would only agree by coincidence.
        """
        result = compute_confidence(_evidence())
        self.assertEqual(result["factor_breakdown"]["coverage_ratio"]["value"], 0.9)

    def test_confidence_formula_version_present(self) -> None:
        """D-12/D-14: every compute_confidence result carries the dedicated formula-version
        marker (distinct from the three drifting intelligence_version values elsewhere in the
        codebase), so a client asking why the score moved gets a checkable answer."""
        result = compute_confidence(_evidence())
        self.assertEqual(result["confidence_formula_version"], "2.0.0")

    def test_confidence_formula_version_present_on_no_data(self) -> None:
        """D-15: absence of confidence_formula_version means a report predates Phase 184.1 —
        that rule is only reliable if the marker is present on EVERY return path, including
        the pre-existing endpoints == 0 NO_DATA short-circuit."""
        result = compute_confidence({"totals": {"endpoints": 0}})
        self.assertEqual(result["confidence_rating"], "NO_DATA")
        self.assertEqual(result["confidence_formula_version"], "2.0.0")

    def test_zero_assessable_endpoints_returns_no_data(self) -> None:
        """D-10: totals.endpoints > 0 but assessable_endpoint_count == 0 (e.g. a port sweep that
        found nothing open plus one ADVISORY row) must return the NO_DATA shape rather than
        awarding partial coverage points — the same phantom-points defect CR-01 guards against.
        Distinct from test_zero_endpoints, which covers totals.endpoints == 0 itself.
        """
        result = compute_confidence(
            {
                "totals": {"endpoints": 5},
                "assessed_crypto_count": 0,
                "assessable_endpoint_count": 0,
            }
        )
        self.assertEqual(result["confidence_score"], 0)
        self.assertEqual(result["confidence_rating"], "NO_DATA")
        self.assertEqual(result["confidence_formula_version"], "2.0.0")

    def test_all_plaintext_http_yields_full_coverage(self) -> None:
        """D-08: coverage answers "did we assess it", not "is it good". An evidence set whose
        assessed endpoints are entirely plaintext HTTP still yields coverage_ratio == 1.0 —
        high coverage plus a poor readiness score is the correct reading of a fully-plaintext
        estate, since plaintext is penalised separately via plaintext_http_count in
        scoring.py, and keeping the two orthogonal is what makes confidence meaningful.
        """
        evidence = {
            "totals": {"endpoints": 4},
            "protocol_counts": {"HTTP": 4},
            "assessed_crypto_count": 4,
            "assessable_endpoint_count": 4,
            "scan_error": {"count": 0, "rate": 0.0},
        }
        result = compute_confidence(evidence)
        self.assertEqual(result["factor_breakdown"]["coverage_ratio"]["value"], 1.0)

    def test_d18_exact_value_regression_matches_live_scan_mix(self) -> None:
        """Phase 184.1 SCORE-01 D-18: an exact-value lock on coverage_ratio, the first this
        codebase has ever had. Every other test in this file (and every scoring test in the
        repo) asserts relative comparisons (assertLess/assertGreater between two computed
        scores); none pins a literal, so a regression that shifts the formula by a fixed
        multiplier would sail through untested. This test closes that gap.

        Composition mirrors scan_run_id 2026-09-04T15:28:54 (re-measured live against the
        project's local scan database per 184.1-CONTEXT.md's §Specific Ideas — 20 endpoints,
        coverage 8/20 = 0.40 under the OLD tls_count-plus-ssh_count formula):
            6 TLS, 2 SSH, 2 SMTP-STARTTLS, 1 SMTPS, 1 IMAPS, 1 IMAP-STARTTLS, 1 POP3S,
            1 POP3-STARTTLS, 1 KERBEROS, 2 HTTP, 1 UNKNOWN, 1 ADVISORY   (= 20 rows)
        Plus rows the live scan did NOT have, added specifically to exercise D-05 (scan_error)
        and D-07 (CLOSED):
            2 CLOSED, 1 additional TLS row carrying a truthy scan_error   (= 3 more rows)
        Total endpoints = 23.

        Hand-derived arithmetic (this is a hand-built evidence dict — build_evidence_summary
        is NOT invoked here; Task 2's end-to-end module exercises that side):
            assessable_endpoint_count = 23 total - 1 ADVISORY (D-06) - 2 CLOSED (D-07) = 20
            assessed_crypto_count     = 20 assessable - 1 UNKNOWN (D-09) - 1 scan_error (D-05)
                                       = 18
                                       (the 2 SMTP-STARTTLS, 1 SMTPS, 1 IMAPS, 1 IMAP-STARTTLS,
                                       1 POP3S, 1 POP3-STARTTLS all stay IN the numerator per
                                       D-04 even though _PROTOCOL_KEYS can't see their protocol
                                       names, and the 2 plaintext HTTP rows stay in per D-08)
            coverage_ratio = 18 / 20 = 0.9

        This fixture is a snapshot: it will not notice a brand-new protocol appearing in
        _NON_ASSET_PROTOCOLS or _PROTOCOL_KEYS tomorrow — that is
        tests/test_evidence_protocol_disposition.py's (D-11's) job, a run-time source scan
        with no snapshot to go stale. The two are complementary by design, not redundant: this
        test locks the ARITHMETIC for a known mix; that test locks the CLASSIFICATION of every
        protocol literal in the source tree.
        """
        evidence = {
            "totals": {"endpoints": 23, "findings": 0},
            # Only TLS/SSH/UNKNOWN are read by compute_confidence's protocol_counts lookups;
            # the email/STARTTLS protocols are included here for readability only and are NOT
            # read by confidence.py — that invisibility is exactly what D-02 routes around via
            # assessed_crypto_count / assessable_endpoint_count instead of protocol_counts.
            "protocol_counts": {
                "TLS": 7,  # 6 healthy + 1 carrying scan_error
                "SSH": 2,
                "SMTP-STARTTLS": 2,
                "SMTPS": 1,
                "IMAPS": 1,
                "IMAP-STARTTLS": 1,
                "POP3S": 1,
                "POP3-STARTTLS": 1,
                "KERBEROS": 1,
                "HTTP": 2,
                "UNKNOWN": 1,
                "ADVISORY": 1,
                "CLOSED": 2,
            },
            "assessed_crypto_count": 18,
            "assessable_endpoint_count": 20,
            "scan_error": {"count": 1, "rate": 0.0435},
            "tls_enum_coverage_ratio": 1.0,
        }
        result = compute_confidence(evidence)

        # coverage_ratio = 18 / 20 = 0.9 exactly.
        self.assertEqual(result["factor_breakdown"]["coverage_ratio"]["value"], 0.9)
        # score lands in the >=85 HIGH band (computed: 31.5 coverage + 28.695 scan_error +
        # 14.3478... unknown + 20.0 tls_enum = 94.5428..., rounds to 95).
        self.assertEqual(result["confidence_score"], 95)
        self.assertEqual(result["confidence_rating"], "HIGH")
        self.assertEqual(result["confidence_formula_version"], "2.0.0")


if __name__ == "__main__":
    unittest.main()


def test_zero_tls_produces_no_enum_coverage_bonus():
    """SCORE-03 regression guard (D-08): tls_count=0 must yield 0.0 tls_enum_coverage_ratio points.

    Phase 184.1 SCORE-01 (D-19: old-arithmetic classification): this fixture predates the
    184.1-02 coverage rewrite and originally omitted assessed_crypto_count /
    assessable_endpoint_count entirely. Under the new formula that omission defaults both
    to 0, which now trips the D-10 degenerate-denominator NO_DATA branch — and NO_DATA's
    factor_breakdown also zeroes tls_enum_coverage_ratio, so the assertions below kept
    passing for the wrong reason (NO_DATA collision, not the CR-01 guard this test is
    named for). Explicit counters are added here so the test again exercises the real
    CR-01 branch: SSH is the only assessed-crypto protocol in this fixture (assessed
    count 3, carried over 1:1 from the old ssh_count arithmetic), and no ADVISORY/CLOSED
    rows are present so the denominator stays at totals.endpoints (10).
    """
    from quirk.intelligence.confidence import compute_confidence

    evidence = {
        "totals": {"endpoints": 10},
        "protocol_counts": {"TLS": 0, "SSH": 3, "UNKNOWN": 2},
        "assessed_crypto_count": 3,
        "assessable_endpoint_count": 10,
        # Deliberately omit tls_enum_coverage_ratio and tls_enum_coverage_pct
    }
    result = compute_confidence(evidence)
    assert result["confidence_rating"] != "NO_DATA", (
        "fixture must exercise the CR-01 TLS-enum guard, not the D-10 NO_DATA branch"
    )
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
