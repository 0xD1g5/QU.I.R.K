"""PQC-03: agility bonus for pqc_hybrid_endpoint_count.

Tests:
  1. Uplift: a scan with pqc_hybrid_endpoint_count=1 yields a strictly higher
     agility subscore than an equivalent scan with pqc_hybrid_endpoint_count=0.
  2. Clamp: even with pqc_hybrid_endpoint_count set and no other penalties, the
     agility subscore never exceeds 25 (Phase 88 orthogonal /25 constraint).
  3. Orthogonality: the five non-agility subscores are identical between the
     count=1 and count=0 evidence inputs.
  4. Presence: the bonus applies as a binary signal (count >= 1), not zero when
     the counter is missing/None/garbage.
"""
from quirk.intelligence.scoring import compute_readiness_score


def _base_evidence(**overrides):
    """Evidence dict with a moderate agility penalty to leave room for the PQC bonus uplift.

    Includes HIGH findings at 50% of the finding population so the agility
    subscore starts below 25 without being floored at 0 — giving the +8 PQC
    bonus visible uplift headroom while remaining clamped at 25.
    """
    ev = {
        "totals": {"endpoints": 4, "findings": 4},
        "protocol_counts": {},
        "certificate_observations": {},
        "cert_key_type_counts": {},
        "scan_error": {"rate": 0.0},
        # 2 HIGH findings out of 4 total → high_impact_ratio=0.5 → -14*0.5=-7 penalty
        "finding_severity_counts": {"HIGH": 2},
    }
    ev.update(overrides)
    return ev


class TestPqcAgilityUplift:
    """Requirement: PQC-hybrid scan scores strictly higher on agility than classical-only."""

    def test_pqc_hybrid_beats_classical_agility(self):
        classical = compute_readiness_score(_base_evidence(pqc_hybrid_endpoint_count=0))
        pqc = compute_readiness_score(_base_evidence(pqc_hybrid_endpoint_count=1))
        assert pqc["subscores"]["agility_signals"] > classical["subscores"]["agility_signals"], (
            f"PQC-hybrid agility ({pqc['subscores']['agility_signals']}) must exceed "
            f"classical agility ({classical['subscores']['agility_signals']})"
        )

    def test_pqc_hybrid_multiple_endpoints_still_uplifts(self):
        """Multiple PQC endpoints: still an uplift (not a diminishing-returns regression)."""
        classical = compute_readiness_score(_base_evidence(pqc_hybrid_endpoint_count=0))
        pqc = compute_readiness_score(_base_evidence(pqc_hybrid_endpoint_count=5))
        assert pqc["subscores"]["agility_signals"] > classical["subscores"]["agility_signals"]


class TestPqcAgilityClamp:
    """Requirement: agility subscore is capped at 25 regardless of bonus."""

    def test_agility_never_exceeds_25_with_pqc(self):
        result = compute_readiness_score(_base_evidence(pqc_hybrid_endpoint_count=1))
        assert result["subscores"]["agility_signals"] <= 25, (
            f"Agility subscore {result['subscores']['agility_signals']} exceeds /25 pillar cap"
        )

    def test_agility_never_exceeds_25_with_ecdsa_and_pqc(self):
        """Both ECDSA bonus and PQC bonus active — still clamped at 25."""
        ev = _base_evidence(
            pqc_hybrid_endpoint_count=1,
            cert_key_type_counts={"ECDSA": 1},
        )
        result = compute_readiness_score(ev)
        assert result["subscores"]["agility_signals"] <= 25

    def test_agility_never_exceeds_25_strict_profile(self):
        """Strict profile multiplies agility weights up — clamp must still hold."""
        result = compute_readiness_score(
            _base_evidence(pqc_hybrid_endpoint_count=1),
            profile="strict",
        )
        assert result["subscores"]["agility_signals"] <= 25, (
            f"Strict-profile agility {result['subscores']['agility_signals']} exceeds 25"
        )


class TestPqcAgilityOrthogonality:
    """Requirement: PQC bonus must NOT alter the five non-agility subscores."""

    def _non_agility_subscores(self, result):
        s = result["subscores"]
        return {
            "hygiene": s["hygiene"],
            "modern_tls": s["modern_tls"],
            "identity_trust": s["identity_trust"],
            "data_at_rest": s["data_at_rest"],
            "data_in_motion": s["data_in_motion"],
        }

    def test_non_agility_subscores_unchanged(self):
        classical = compute_readiness_score(_base_evidence(pqc_hybrid_endpoint_count=0))
        pqc = compute_readiness_score(_base_evidence(pqc_hybrid_endpoint_count=1))
        assert self._non_agility_subscores(classical) == self._non_agility_subscores(pqc), (
            "PQC bonus leaked into non-agility subscores"
        )

    def test_non_agility_unchanged_with_penalties(self):
        """Same check when there are other findings active."""
        ev0 = _base_evidence(
            pqc_hybrid_endpoint_count=0,
            finding_severity_counts={"HIGH": 2},
            totals={"endpoints": 4, "findings": 4},
        )
        ev1 = dict(ev0)
        ev1["pqc_hybrid_endpoint_count"] = 1
        classical = compute_readiness_score(ev0)
        pqc = compute_readiness_score(ev1)
        assert self._non_agility_subscores(classical) == self._non_agility_subscores(pqc)


class TestPqcPresenceBonus:
    """Requirement: bonus is a binary presence signal; missing/bad values → no bonus."""

    def test_zero_count_no_bonus(self):
        """pqc_hybrid_endpoint_count=0 must not trigger the bonus."""
        zero = compute_readiness_score(_base_evidence(pqc_hybrid_endpoint_count=0))
        missing = compute_readiness_score(_base_evidence())
        # Both should produce the same agility score (no bonus from PQC)
        assert zero["subscores"]["agility_signals"] == missing["subscores"]["agility_signals"]

    def test_garbage_count_no_crash(self):
        """Non-integer pqc_hybrid_endpoint_count must not crash and must not add bonus."""
        baseline = compute_readiness_score(_base_evidence(pqc_hybrid_endpoint_count=0))
        for garbage in (None, "abc", [], {}, -1):
            result = compute_readiness_score(_base_evidence(pqc_hybrid_endpoint_count=garbage))
            assert result["subscores"]["agility_signals"] == baseline["subscores"]["agility_signals"], (
                f"garbage value {garbage!r} produced unexpected agility score"
            )

    def test_negative_count_no_bonus(self):
        """Negative counts must coerce to 0 (max(0, ...) guard)."""
        baseline = compute_readiness_score(_base_evidence(pqc_hybrid_endpoint_count=0))
        negative = compute_readiness_score(_base_evidence(pqc_hybrid_endpoint_count=-5))
        assert baseline["subscores"]["agility_signals"] == negative["subscores"]["agility_signals"]
