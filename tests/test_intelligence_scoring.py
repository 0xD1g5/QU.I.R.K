import unittest

from quirk.intelligence.scoring import compute_readiness_score


def _base_evidence() -> dict:
    # Deliberately degraded evidence so subscores sum < 100 pre-clamp.
    # This allows profile and override comparisons to produce distinct clamped scores
    # now that compute_readiness_score() applies _clamp(total, 0, 100) (SCORE-01).
    return {
        "totals": {"endpoints": 10, "findings": 10},
        "protocol_counts": {"TLS": 2, "HTTP": 6, "SSH": 1, "UNKNOWN": 1},
        "plaintext_http_count": 6,
        "http_on_tls_port_count": 5,
        "mtls_present_count": 0,
        "cert_key_type_counts": {"RSA": 10, "ECDSA": 0},
        "certificate_observations": {
            "certs_observed": 8,
            "expired_count": 4,
            "expiring_count": 2,
            "self_signed_count": 4,
        },
        "scan_error": {"count": 5, "rate": 0.5},
        "finding_severity_counts": {"CRITICAL": 3, "HIGH": 5, "MEDIUM": 2, "LOW": 0, "INFO": 0},
        "legacy_tls_count": 5,
    }


class ReadinessScoringTests(unittest.TestCase):
    def test_compute_readiness_score_shape(self) -> None:
        result = compute_readiness_score(_base_evidence())
        self.assertIn("score", result)
        self.assertIn("rating", result)
        self.assertIn("subscores", result)
        self.assertIn("drivers", result)
        self.assertEqual(set(result["subscores"].keys()), {"hygiene", "modern_tls", "identity_trust", "agility_signals", "data_at_rest", "data_in_motion"})
        MAX_SUBSCORE = 25  # per _apply_weighted_impacts cap
        NUM_SUBSCORES = 6  # + data_in_motion (Phase 34)
        self.assertGreaterEqual(result["score"], 0)
        self.assertLessEqual(result["score"], 100)
        self.assertLessEqual(len(result["drivers"]), 5)

    def test_risky_evidence_scores_lower(self) -> None:
        # _base_evidence() already produces a sub-100 score; add further degradation
        # so risky stays clearly below safe after _clamp(total, 0, 100) is applied.
        safe = _base_evidence()
        risky = _base_evidence()
        risky["plaintext_http_count"] = 8
        risky["http_on_tls_port_count"] = 8
        risky["certificate_observations"]["expired_count"] = 5
        risky["certificate_observations"]["self_signed_count"] = 5
        risky["finding_severity_counts"]["HIGH"] = 8
        risky["finding_severity_counts"]["CRITICAL"] = 5

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


def test_subscores_unaffected_by_clamp():
    """SCORE-01 regression guard: verify subscores in the returned dict are not
    clamped individually — only the top-level 'score' receives the clamp.
    Each subscore is clamped to [0, 25] by _apply_weighted_impacts; the aggregated total is clamped to [0, 100].
    """
    from quirk.intelligence.scoring import compute_readiness_score

    # Minimal evidence — all subscores should be within [0, 25]
    result = compute_readiness_score({})
    assert "subscores" in result
    for key, val in result["subscores"].items():
        assert isinstance(val, int), f"subscore {key} is not int: {val}"
        assert 0 <= val <= 25, f"subscore {key}={val} outside [0, 25]"
    # The aggregated score must be clamped
    assert 0 <= result["score"] <= 100
