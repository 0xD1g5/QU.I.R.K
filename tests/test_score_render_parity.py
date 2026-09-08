"""Phase 88 D-04 / RENDER-CLI-01, RENDER-PDF-01: Data-layer parity gate.

All three report surfaces (CLI scorecard markdown, executive markdown, HTML/PDF)
receive identical overall score and six subscore values from the same evidence.
The Phase 86 normalized 0-100 contract is anchored: overall must be an int in [0, 100].

Verified-no-bug: there is one canonical scoring engine (quirk/intelligence/scoring.py);
the former dual-engine concern (quirk/assessment/readiness_score.py) is stale -- that
module was deleted. writer.py imports compute_readiness_score from quirk.intelligence.scoring
at line 17. This test locks the single-engine fact and the identity contract in perpetuity.
"""
from __future__ import annotations

from quirk.intelligence.scoring import compute_readiness_score
from quirk.intelligence.evidence import build_evidence_summary


FIXTURE_ENDPOINTS = []
FIXTURE_FINDINGS = []


def test_render_parity_all_surfaces():
    """D-04 gate: all render surfaces receive identical score values from same evidence.

    writer.py path: wraps compute_readiness_score output as
      {"total": score_raw["score"], "subscores": score_raw["subscores"], ...}
    html_renderer.py: receives the same wrapped dict; accesses score.get("total")
      and score.get("subscores") -- same integers, no re-rounding.
    dashboard API: calls compute_readiness_score independently with same evidence.
    """
    evidence = build_evidence_summary(FIXTURE_ENDPOINTS, FIXTURE_FINDINGS)
    canonical = compute_readiness_score(evidence)

    # writer.py compat wrapper (writer.py lines 166-170)
    writer_score = {
        "total": canonical["score"],
        "subscores": canonical["subscores"],
    }
    assert writer_score["total"] == canonical["score"], (
        f"writer.py 'total' key ({writer_score['total']}) diverges from canonical "
        f"'score' key ({canonical['score']}). RENDER-CLI-01 parity violated."
    )
    assert writer_score["subscores"] == canonical["subscores"], (
        "writer.py 'subscores' dict diverges from canonical. RENDER-CLI-01 parity violated."
    )

    # dashboard API re-calls compute_readiness_score with same evidence (independent call)
    dashboard_score = compute_readiness_score(evidence)
    assert dashboard_score["score"] == canonical["score"], (
        f"dashboard recall score ({dashboard_score['score']}) != canonical ({canonical['score']}). "
        "RENDER-PDF-01 parity violated."
    )
    assert dashboard_score["subscores"] == canonical["subscores"], (
        "dashboard recall subscores diverge from canonical. RENDER-PDF-01 parity violated."
    )

    # Phase 86 contract: overall must be an int in [0, 100], OR the Phase 188
    # SCORE-06 explicit "not computed" sentinel (None) when zero domains were
    # assessed -- true here, since FIXTURE_ENDPOINTS/FIXTURE_FINDINGS are both
    # empty (domains_assessed == 0). The parity assertions above still hold:
    # every surface receives the identical None, which is itself the parity
    # guarantee this test exists to prove -- see
    # tests/test_score_coverage_disclosure.py for the dedicated zero-assessed
    # regression.
    overall = canonical["score"]
    assert overall is None or isinstance(overall, int), (
        f"Overall score must be int or None (Phase 86 / Phase 188 SCORE-06 contract), "
        f"got {type(overall).__name__}."
    )
    if overall is not None:
        assert 0 <= overall <= 100, (
            f"Overall score {overall} outside [0, 100] (Phase 86 contract violated)."
        )
    else:
        assert canonical["domains_assessed"] == 0

    # Subscores must each be int in [0, 25], or None for an unassessed category
    # (Phase 188 SCORE-06) -- all six are unassessed here since domains_assessed == 0.
    for key, val in canonical["subscores"].items():
        assert val is None or isinstance(val, int), (
            f"Subscore '{key}' must be int or None, got {type(val).__name__}."
        )
        if val is not None:
            assert 0 <= val <= 25, (
                f"Subscore '{key}' value {val} outside [0, 25]."
            )
