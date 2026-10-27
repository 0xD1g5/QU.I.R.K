"""O-6 (Phase 234): the first clean row of a not-yet-assessed domain raises
the headline. That is DELIBERATE coverage credit, pinned here.

SCORE-09 (Phase 234, scoring 4.0) is scoped by operator decision O-6 to
within-domain scan depth: adding healthy endpoints to a domain that is already
assessed must never raise the score (the 233 instrument and
``tests/test_score_properties.py::test_p2b_score_does_not_improve_by_observing_more_healthy_endpoints``).

A DIFFERENT step is kept on purpose. Phase 188's exclude-and-rescale leaves a
domain with no evidence out of the headline (subscore None, absent from the
divisor). When the first clean row of that domain is observed, the domain
enters at 25/25 and the headline rises. This is coverage credit: the engagement
now knows something about data in motion that it did not know before. It is
not dilution, because no weakness count is being divided by a larger
population.

This test PINS that behaviour so a future change to it is a decision, not an
accident. Whether a domain's first clean row should move the headline is filed
as the follow-up todo
``.planning/todos/pending/261027-score-newly-assessed-domain-step-is-coverage-credit.md``
(owner 999.139, filed by plan 234-08). The measured scores are reported in the
assertion messages only, never hard-coded.
"""
from __future__ import annotations

import copy
import re
from typing import Any, Dict

import pytest

from quirk.intelligence.scoring import _MOTION_PROTOCOL_KEYS, compute_readiness_score
from tests.test_score_properties import (
    _r2_well_run_no_pqc,
    _r3_typical_enterprise,
    _r4_neglected,
)


def _computed(result: Dict[str, Any]) -> int:
    """The pre-ceiling score: ``computed NN`` from the cap reason, else the score."""
    match = re.search(r"computed (\d+)", result.get("rating_cap_reason") or "")
    return int(match.group(1)) if match else int(result["score"])


def _without_motion(ev: Dict[str, Any]) -> Dict[str, Any]:
    base = copy.deepcopy(ev)
    for key in _MOTION_PROTOCOL_KEYS:
        if key in base["protocol_counts"]:
            base["protocol_counts"][key] = 0
    return base


@pytest.mark.parametrize(
    "rung, builder",
    [("R2", _r2_well_run_no_pqc), ("R3", _r3_typical_enterprise), ("R4", _r4_neglected)],
)
def test_newly_assessed_domain_step_is_deliberate_coverage_credit(rung, builder):
    base = _without_motion(builder())
    with_motion = copy.deepcopy(base)
    with_motion["protocol_counts"]["SMTP-STARTTLS"] = 1
    with_motion["assessable_endpoint_count"] += 1
    # No motion weakness: every motion_* counter stays absent (reads 0).
    assert not any(k.startswith("motion_") for k in with_motion)

    before = compute_readiness_score(base)
    after = compute_readiness_score(with_motion)

    assert before["subscores"]["data_in_motion"] is None, (
        f"{rung}: the base must leave data_in_motion unassessed"
    )
    assert after["subscores"]["data_in_motion"] == 25, (
        f"{rung}: one clean SMTP-STARTTLS row scored data_in_motion "
        f"{after['subscores']['data_in_motion']}, expected 25"
    )
    assert after["domains_assessed"] == before["domains_assessed"] + 1

    b, a = _computed(before), _computed(after)
    assert a > b, (
        f"{rung}: the newly assessed domain did not raise the computed score "
        f"({b} -> {a}; emitted {before['score']} -> {after['score']}). O-6 "
        "keeps this step as deliberate coverage credit; if it no longer rises, "
        "that is a model change to record against the follow-up todo."
    )
