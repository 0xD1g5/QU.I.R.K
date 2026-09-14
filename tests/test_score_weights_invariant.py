"""D-04 / WR-06: SCORE_WEIGHTS sum invariant (Phase 73; rebalanced Phase 83; PQC-03 Phase 90; SCORE-01 Phase 94; SCORE-01 Phase 95; SCORE-01 Phase 96)."""
from quirk.intelligence.scoring import SCORE_WEIGHTS


def test_score_weights_sum_invariant():
    """SCORE_WEIGHTS sum must be 303.0 by design (NOT normalized).

    See quirk/intelligence/scoring.py docstring above SCORE_WEIGHTS for
    rationale (Phase 73 / D-04). Any contributor changing this value must
    update this test AND document the rebalance in a phase plan.

    Phase 83 rebalance: bumped from 261.0 -> 275.0 (+14.0) to absorb Wave A
    scanner expansions:
      - Phase 79 SMIME: +3 entries at +6.0 sum
      - Phase 80 ADCS:  +4 entries at +8.0 sum
    Net delta = +7 entries / +14.0 sum (29 -> 36, 261.0 -> 275.0).

    Phase 90 PQC-03: bumped from 275.0 -> 283.0 (+8.0) for PQC-hybrid agility bonus:
      - agility_pqc_hybrid_bonus: +1 entry at +8.0
    Net delta = +1 entry / +8.0 sum (36 -> 37, 275.0 -> 283.0).

    Phase 94 SCORE-01: bumped from 283.0 -> 293.0 (+10.0) for API/bearer agility signals:
      - agility_weak_jwt_alg_ratio: +1 entry at +6.0
      - agility_openapi_plaintext_ratio: +1 entry at +4.0
    Net delta = +2 entries / +10.0 sum (37 -> 39, 283.0 -> 293.0).

    Phase 95 SCORE-01: bumped from 293.0 -> 299.0 (+6.0) for code-signing weak-algo signal:
      - agility_codesign_weak_algo_ratio: +1 entry at +6.0
    Net delta = +1 entry / +6.0 sum (39 -> 40, 293.0 -> 299.0).

    Phase 96 SCORE-01: bumped from 299.0 -> 303.0 (+4.0) for active REST fuzz agility signal:
      - agility_fuzz_crypto_posture_ratio: +1 entry at +4.0
    Net delta = +1 entry / +4.0 sum (40 -> 41, 299.0 -> 303.0).

    999.115 P8: bumped from 303.0 -> 311.0 (+8.0) for the undetermined-key-type
    assessment gap:
      - agility_unverified_key_type_penalty: +1 entry at +8.0
    Net delta = +1 entry / +8.0 sum (41 -> 42, 303.0 -> 311.0). The value is
    derived rather than chosen — it must be >= agility_rsa_only_penalty or the
    model rewards not looking; see the comment at its definition site.

    999.115 C: dropped from 311.0 -> 297.0 (-14.0) by REMOVING
    agility_high_impact_ratio. As a prevalence measure it diluted whenever its
    denominator grew, which made discovering MEDIUM and LOW findings RAISE the
    score. High-impact findings now reach the number absolutely, through
    _consequence_ceiling(), so re-denominating the ratio would have been
    fixing a term that no longer has a job. Net delta = -1 entry / -14.0 sum
    (42 -> 41, 311.0 -> 297.0).

    NOTE the coincidence, so nobody reads it as a no-op: the entry COUNT
    returned to 41, the same value it held before either change. The two
    deltas are unrelated and the SUM did not return (303.0 -> 297.0).
    """
    assert abs(sum(SCORE_WEIGHTS.values()) - 297.0) < 1e-9, (
        f"SCORE_WEIGHTS sum drifted from 297.0 to {sum(SCORE_WEIGHTS.values())}. "
        "Per D-04 this is intentional — update this test ONLY if rebalance is documented."
    )


def test_score_weights_count_invariant():
    """Anchors the 41-weight count alongside the sum invariant.

    Phase 83 rebalance: bumped from 29 -> 36 (+7) absorbing Phase 79 SMIME
    (+3) and Phase 80 ADCS (+4) Wave A scanner expansions.

    Phase 90 PQC-03: bumped from 36 -> 37 (+1) for agility_pqc_hybrid_bonus.

    Phase 94 SCORE-01: bumped from 37 -> 39 (+2) for agility_weak_jwt_alg_ratio
    and agility_openapi_plaintext_ratio.

    Phase 95 SCORE-01: bumped from 39 -> 40 (+1) for agility_codesign_weak_algo_ratio.

    Phase 96 SCORE-01: bumped from 40 -> 41 (+1) for agility_fuzz_crypto_posture_ratio.

    999.115 P8: bumped from 41 -> 42 (+1) for agility_unverified_key_type_penalty.

    999.115 C: dropped from 42 -> 41 (-1) by removing agility_high_impact_ratio.
    Back at 41 by coincidence, not by reversal — see the sum invariant's
    docstring above, where the sum shows the two changes were not a round trip.
    """
    assert len(SCORE_WEIGHTS) == 41
