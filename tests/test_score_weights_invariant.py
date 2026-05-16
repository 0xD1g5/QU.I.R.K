"""D-04 / WR-06: SCORE_WEIGHTS sum invariant (Phase 73; rebalanced Phase 83)."""
from quirk.intelligence.scoring import SCORE_WEIGHTS


def test_score_weights_sum_invariant():
    """SCORE_WEIGHTS sum must be 275.0 by design (NOT normalized).

    See quirk/intelligence/scoring.py docstring above SCORE_WEIGHTS for
    rationale (Phase 73 / D-04). Any contributor changing this value must
    update this test AND document the rebalance in a phase plan.

    Phase 83 rebalance: bumped from 261.0 -> 275.0 (+14.0) to absorb Wave A
    scanner expansions:
      - Phase 79 SMIME: +3 entries at +6.0 sum
      - Phase 80 ADCS:  +4 entries at +8.0 sum
    Net delta = +7 entries / +14.0 sum (29 -> 36, 261.0 -> 275.0).
    """
    assert abs(sum(SCORE_WEIGHTS.values()) - 275.0) < 1e-9, (
        f"SCORE_WEIGHTS sum drifted from 275.0 to {sum(SCORE_WEIGHTS.values())}. "
        "Per D-04 this is intentional — update this test ONLY if rebalance is documented."
    )


def test_score_weights_count_invariant():
    """Anchors the 36-weight count alongside the sum invariant.

    Phase 83 rebalance: bumped from 29 -> 36 (+7) absorbing Phase 79 SMIME
    (+3) and Phase 80 ADCS (+4) Wave A scanner expansions.
    """
    assert len(SCORE_WEIGHTS) == 36
