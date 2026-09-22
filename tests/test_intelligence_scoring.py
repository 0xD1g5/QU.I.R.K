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

    Phase 188 SCORE-06: `compute_readiness_score({})` (truly zero evidence) now
    hits the zero-assessed "not computed" branch and returns `score=None` with
    every subscore `None` (never a fabricated 0-100 to clamp) — that edge case
    is covered explicitly by tests/test_score_coverage_disclosure.py. This test
    switches to a minimal-but-nonzero evidence dict (5 endpoints, no DAR/motion/
    identity signals) so it keeps testing its original intent -- that the
    per-category clamp in `_apply_weighted_impacts` is independent of the
    top-level clamp -- against ASSESSED categories, while still allowing
    unassessed categories (data_at_rest, data_in_motion; see
    tests/test_score_coverage_disclosure.py for identity_trust's own
    independent predicate) to be None rather than int.
    """
    from quirk.intelligence.scoring import compute_readiness_score

    # Minimal-but-nonzero evidence — assessed subscores should be within [0, 25];
    # unassessed ones (no DAR/motion protocol counts here) render None.
    result = compute_readiness_score({"totals": {"endpoints": 5, "findings": 0}})
    assert "subscores" in result
    for key, val in result["subscores"].items():
        if val is None:
            continue
        assert isinstance(val, int), f"subscore {key} is not int or None: {val}"
        assert 0 <= val <= 25, f"subscore {key}={val} outside [0, 25]"
    # The aggregated score must be clamped
    assert 0 <= result["score"] <= 100


class SubscoreIsolationTests(unittest.TestCase):
    """COV-08 / UAT-8-04 / UAT-8-05 — assert the `hygiene` and `identity_trust`
    subscores directly, in isolation, never inferring them from movement in
    the overall readiness score (D-10 — that inference is the exact defect
    COV-08 exists to remove).

    D-09: each test builds its OWN minimal synthetic evidence dict via a
    private helper below, naming only the fields its target impact term
    reads. `_base_evidence()` (module-level, used by ReadinessScoringTests /
    ProfileWeightTests above) is never called here and no golden fixture is
    mutated — every evidence key this class sets is visible in the test body,
    and every key it does NOT set defaults to 0 via `evidence.get(key, 0)` in
    `compute_readiness_score`, making the held-fixed set auditable without
    opening the scorer.

    Evidence key names below are read live from `quirk/intelligence/scoring.py`
    (lines ~404-508) rather than trusted from 208-PATTERNS.md, which guessed
    several wrong (e.g. kerberos_present_count / saml_present_count /
    adcs_present_count do not exist).

    Placed after the module-level `test_subscores_unaffected_by_clamp` function
    (rather than immediately after `ProfileWeightTests`) so this class's own
    body is the tail of the file — this keeps the D-10 self-check
    (`awk '/class SubscoreIsolationTests/,0' ... | grep -c 'result\\["score"\\]'`)
    from also sweeping up unrelated, pre-existing code below it.
    """

    def _hygiene_evidence(self, plaintext_count: int) -> dict:
        # Varies ONLY plaintext_http_count. http_on_tls_port_count and
        # scan_error.rate are held fixed at 0 so the "Plaintext HTTP
        # exposure" term (hygiene_plaintext_http_ratio) is the only hygiene
        # impact ever nonzero across the two calls this test makes.
        return {
            "totals": {"endpoints": 10},
            "assessable_endpoint_count": 10,
            "plaintext_http_count": plaintext_count,
            "http_on_tls_port_count": 0,
            "scan_error": {"rate": 0.0},
        }

    def test_hygiene_isolat_subscore_to_plaintext_ratio(self) -> None:
        full_budget = compute_readiness_score(self._hygiene_evidence(0))
        self.assertIsNotNone(full_budget["subscores"]["hygiene"])
        self.assertEqual(full_budget["subscores"]["hygiene"], 25)

        at_five = compute_readiness_score(self._hygiene_evidence(5))
        hygiene_at_five = at_five["subscores"]["hygiene"]
        self.assertIsNotNone(hygiene_at_five)
        # UAT-8-04 bullet 1: "< 25 when >= 1 plaintext endpoint is present".
        self.assertLess(hygiene_at_five, 25)

        at_nine = compute_readiness_score(self._hygiene_evidence(9))
        hygiene_at_nine = at_nine["subscores"]["hygiene"]
        self.assertIsNotNone(hygiene_at_nine)
        # UAT-8-04 bullet 2: "decreases proportionally" — strict monotonic
        # decrease as plaintext_count rises with endpoint_denom held at 10.
        self.assertLess(hygiene_at_nine, hygiene_at_five)

        # D-10 guard: this method reads only result["subscores"]["hygiene"],
        # never the overall score.

    def _identity_trust_evidence(self, mtls_present_count: int) -> dict:
        # `_identity_assessed()` requires certs_observed > 0 (or a nonzero
        # _IDENTITY_PROTOCOL_KEYS count) or the identity_trust subscore comes
        # back None and this test would be comparing nothing.
        #
        # self_signed_count=1 (out of certs_observed=10) is deliberately
        # NON-zero: it gives the identity_trust subscore headroom BELOW the
        # per-category cap of 25 (_apply_weighted_impacts score_cap=25.0) so
        # the mTLS bonus term (a positive impact) has room to move the score
        # upward and produce a genuine strict inequality. Verified live: with
        # self_signed_count omitted (0), both mtls_present_count=0 and =5
        # clamp to identity_trust=25 and the assertGreater below would be
        # vacuously false — that is a fixture bug in the source plan, fixed
        # here per Rule 1 (auto-fix bug), not a deviation from D-09's intent.
        #
        # Every OTHER identity_trust penalty-term evidence key is
        # DELIBERATELY OMITTED and therefore held fixed at 0 via
        # `evidence.get(key, 0)`: expired_count, expiring_count,
        # identity_weak_etype_count (Kerberos), saml_weak_signing_count,
        # dnssec_weak_algo_count, smime_weak_signing_count,
        # smime_expired_count, smime_weak_key_count,
        # adcs_weak_template_count, adcs_misconfig_count,
        # adcs_weak_signing_count, adcs_coverage_gap_count.
        return {
            "totals": {"endpoints": 10},
            "assessable_endpoint_count": 10,
            "certificate_observations": {
                "certs_observed": 10,
                "self_signed_count": 1,
            },
            "mtls_present_count": mtls_present_count,
        }

    def test_identity_trust_subscore_mtls_isolat_bonus(self) -> None:
        without_mtls = compute_readiness_score(self._identity_trust_evidence(0))
        with_mtls = compute_readiness_score(self._identity_trust_evidence(5))

        subscore_without = without_mtls["subscores"]["identity_trust"]
        subscore_with = with_mtls["subscores"]["identity_trust"]
        # None-subscore trap: if _identity_assessed() ever returned False,
        # the subscore would be excluded (None) and assertGreater below would
        # raise TypeError rather than silently proving nothing — but guard
        # explicitly so the failure mode is legible.
        self.assertIsNotNone(subscore_without)
        self.assertIsNotNone(subscore_with)

        # UAT-8-05's own pass criterion: strictly higher with
        # mtls_present_count > 0 than at 0, all other evidence held fixed.
        self.assertGreater(subscore_with, subscore_without)

        # D-10 guard: this method reads only result["subscores"]["identity_trust"],
        # never the overall score.
