"""D-04 / WR-06: SCORE_WEIGHTS sum invariant (Phase 73)."""
from quirk.intelligence.scoring import SCORE_WEIGHTS


def test_score_weights_sum_invariant():
    """SCORE_WEIGHTS sum must be 261.0 by design (NOT normalized).

    See quirk/intelligence/scoring.py docstring above SCORE_WEIGHTS for
    rationale (Phase 73 / D-04). Any contributor changing this value must
    update this test AND document the rebalance in a phase plan.
    """
    assert abs(sum(SCORE_WEIGHTS.values()) - 261.0) < 1e-9, (
        f"SCORE_WEIGHTS sum drifted from 261.0 to {sum(SCORE_WEIGHTS.values())}. "
        "Per D-04 this is intentional — update this test ONLY if rebalance is documented."
    )


def test_score_weights_count_invariant():
    """Anchors the 29-weight count alongside the sum invariant."""
    assert len(SCORE_WEIGHTS) == 29
