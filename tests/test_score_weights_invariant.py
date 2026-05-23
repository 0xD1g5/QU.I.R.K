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
    """
    assert abs(sum(SCORE_WEIGHTS.values()) - 303.0) < 1e-9, (
        f"SCORE_WEIGHTS sum drifted from 303.0 to {sum(SCORE_WEIGHTS.values())}. "
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
    """
    assert len(SCORE_WEIGHTS) == 41
