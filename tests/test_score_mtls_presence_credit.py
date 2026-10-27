"""Phase 234 code review WR-03 / D-28: the mTLS bonus is a PRESENCE credit.

Scoring 4.0 (D-02) first made the +6 mTLS bonus an absolute-count curve that
saturates at N_REF = 40. That reintroduced the scan-depth reward SCORE-09
removes everywhere else: every additional healthy endpoint that enforces mTLS
raised identity_trust, up to +6. D-28 gives it the shape of the PQC credit
(D-04): the first mTLS observation earns +6 once, and further mTLS-enforcing
endpoints earn nothing.

The first observation is a deliberate, sanctioned single step (like the PQC
credit and the O-6 newly-assessed-domain step), so it is pinned here as its
own property. The depth property (no rise after the first observation) is
gated across every rung by the instrument's ``rows_mtls`` reading in
``tests/test_p2b_instrument.py::test_p2b_non_increase_all_rungs_all_readings``.
"""
from __future__ import annotations

import copy

from quirk.intelligence.scoring import SCORE_WEIGHTS, compute_readiness_score
from tests.test_score_properties import _r4_neglected

# Counts on both sides of the old curve's N_REF = 40 knee.
DEPTHS = (1, 2, 20, 39, 40, 41, 500)


def _identity(mtls: int) -> int:
    ev = copy.deepcopy(_r4_neglected())
    ev["mtls_present_count"] = mtls
    return compute_readiness_score(ev)["subscores"]["identity_trust"]


def test_first_mtls_endpoint_earns_the_presence_credit_once():
    """D-28: 0 -> 1 mTLS endpoint adds exactly the +6; more add nothing."""
    credit = SCORE_WEIGHTS["identity_mtls_ratio_bonus"]
    assert credit == 6.0
    base = _identity(0)
    # Non-vacuity: R4's identity sits far enough below 25 that a +6 is not
    # absorbed by the clamp.
    assert base + credit <= 25, f"R4 identity {base} leaves no headroom"
    with_one = _identity(1)
    assert with_one == base + int(credit), (
        f"one mTLS endpoint moved identity {base} -> {with_one}; the presence "
        f"credit is +{credit:g} once"
    )
    depth = {n: _identity(n) for n in DEPTHS}
    assert set(depth.values()) == {with_one}, (
        f"identity by mTLS endpoint count {depth}: observing more mTLS "
        "endpoints must not raise it (SCORE-09, D-28)"
    )
