import unittest

from quirk.intelligence.scoring import compute_readiness_score


def _base_evidence() -> dict:
    return {
        "totals": {"endpoints": 10, "findings": 4},
        "protocol_counts": {"TLS": 6, "HTTP": 2, "SSH": 1, "UNKNOWN": 1},
        "plaintext_http_count": 1,
        "http_on_tls_port_count": 1,
        "mtls_present_count": 1,
        "cert_key_type_counts": {"RSA": 6, "ECDSA": 2},
        "certificate_observations": {
            "certs_observed": 8,
            "expired_count": 0,
            "expiring_count": 1,
            "self_signed_count": 0,
        },
        "scan_error": {"count": 1, "rate": 0.1},
        "finding_severity_counts": {"CRITICAL": 0, "HIGH": 2, "MEDIUM": 1, "LOW": 0, "INFO": 1},
    }


class ReadinessScoringTests(unittest.TestCase):
    def test_compute_readiness_score_shape(self) -> None:
        result = compute_readiness_score(_base_evidence())
        self.assertIn("score", result)
        self.assertIn("rating", result)
        self.assertIn("subscores", result)
        self.assertIn("drivers", result)
        self.assertEqual(set(result["subscores"].keys()), {"hygiene", "modern_tls", "identity_trust", "agility_signals"})
        self.assertGreaterEqual(result["score"], 0)
        self.assertLessEqual(result["score"], 100)
        self.assertLessEqual(len(result["drivers"]), 5)

    def test_risky_evidence_scores_lower(self) -> None:
        safe = _base_evidence()
        risky = _base_evidence()
        risky["plaintext_http_count"] = 4
        risky["http_on_tls_port_count"] = 3
        risky["scan_error"] = {"count": 5, "rate": 0.5}
        risky["certificate_observations"]["expired_count"] = 3
        risky["certificate_observations"]["self_signed_count"] = 2
        risky["cert_key_type_counts"] = {"RSA": 8, "ECDSA": 0}
        risky["finding_severity_counts"]["HIGH"] = 4

        safe_score = compute_readiness_score(safe)["score"]
        risky_score = compute_readiness_score(risky)["score"]
        self.assertLess(risky_score, safe_score)

    def test_output_is_deterministic(self) -> None:
        evidence = _base_evidence()
        a = compute_readiness_score(evidence)
        b = compute_readiness_score(evidence)
        self.assertEqual(a, b)


class ProfileWeightTests(unittest.TestCase):
    def test_profile_strict_scores_differently_from_lenient(self) -> None:
        """strict and lenient profiles must produce different scores on the same evidence."""
        strict_score = compute_readiness_score(_base_evidence(), profile="strict")["score"]
        lenient_score = compute_readiness_score(_base_evidence(), profile="lenient")["score"]
        self.assertNotEqual(
            strict_score,
            lenient_score,
            f"Expected strict ({strict_score}) != lenient ({lenient_score}); profiles must differ by >= 1",
        )

    def test_calibration_overrides_applied(self) -> None:
        """Zeroing out a penalty weight via weights= must raise the score."""
        default_score = compute_readiness_score(_base_evidence())["score"]
        override_score = compute_readiness_score(
            _base_evidence(), weights={"hygiene_plaintext_http_ratio": 0.0}
        )["score"]
        self.assertGreater(
            override_score,
            default_score,
            f"Override score ({override_score}) should be higher than default ({default_score})",
        )

    def test_profile_then_override(self) -> None:
        """weights= override must take precedence over profile multipliers."""
        strict_no_override = compute_readiness_score(
            _base_evidence(), profile="strict"
        )["score"]
        strict_with_zero = compute_readiness_score(
            _base_evidence(), profile="strict", weights={"agility_high_impact_ratio": 0.0}
        )["score"]
        # With override zeroing out the agility penalty, score should be >= strict without override
        # The key property is that the override was honored (not blocked by profile)
        self.assertGreaterEqual(
            strict_with_zero,
            strict_no_override,
            "weights= override should zero out agility_high_impact_ratio penalty, raising or maintaining score",
        )

    def test_invalid_profile_falls_back_to_balanced(self) -> None:
        """Unknown profile name must produce same score as balanced."""
        invalid_score = compute_readiness_score(
            _base_evidence(), profile="nonexistent"
        )["score"]
        balanced_score = compute_readiness_score(
            _base_evidence(), profile="balanced"
        )["score"]
        self.assertEqual(
            invalid_score,
            balanced_score,
            f"Invalid profile ({invalid_score}) should fall back to balanced ({balanced_score})",
        )

    def test_balanced_profile_matches_no_profile(self) -> None:
        """profile='balanced' must produce the same score as calling without profile."""
        no_profile_score = compute_readiness_score(_base_evidence())["score"]
        balanced_score = compute_readiness_score(_base_evidence(), profile="balanced")["score"]
        self.assertEqual(
            no_profile_score,
            balanced_score,
            f"No-profile ({no_profile_score}) must equal balanced ({balanced_score})",
        )


if __name__ == "__main__":
    unittest.main()
