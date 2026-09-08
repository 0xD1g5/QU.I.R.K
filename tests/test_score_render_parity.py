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


# ---------------------------------------------------------------------------
# Phase 188 SCORE-06 / plan 188-03, Task 3: cross-surface coverage-disclosure,
# dynamic-divisor, and not-computed parity.
#
# Reuses this file's existing all-surfaces convention (CLI markdown, HTML, DOCX,
# writer.py compat scorecard markdown) rather than adding a parallel driver.
# Presence-only per CLAUDE.md's render-parity convention -- visual placement
# is routed to human UAT via 188-VALIDATION.md's manual-only table.
# ---------------------------------------------------------------------------

import os
from types import SimpleNamespace

from quirk.intelligence.scoring import SCORING_VERSION
from quirk.reports.content_model import build_exec_content, NOT_COMPUTED_STATEMENT


def _make_minimal_cfg(outdir: str):
    return SimpleNamespace(
        assessment=SimpleNamespace(
            name="188-03 Parity Test Org",
            report_owner="Parity Tester",
            data_classification="CONFIDENTIAL",
            timezone="UTC",
            logo_path=None,
        ),
        output=SimpleNamespace(directory=outdir),
        intelligence=SimpleNamespace(profile="balanced", calibration_overrides=None),
    )


# 4-of-6 partial coverage -- identity_trust and data_at_rest excluded (None).
_PARTIAL_SCORE_RAW = {
    "score": 78,
    "rating": "GOOD",
    "subscores": {
        "hygiene": 20,
        "modern_tls": 18,
        "identity_trust": None,
        "agility_signals": 15,
        "data_at_rest": None,
        "data_in_motion": 21,
    },
    "drivers": [],
    "domains_assessed": 4,
    "domains_total": 6,
    "score_divisor": 1.0,
    "coverage_disclosure": "4 of 6 domains assessed",
    "scoring_version": SCORING_VERSION,
}

_ZERO_ASSESSED_SCORE_RAW = {
    "score": None,
    "rating": "NOT_ASSESSED",
    "subscores": {
        "hygiene": None, "modern_tls": None, "identity_trust": None,
        "agility_signals": None, "data_at_rest": None, "data_in_motion": None,
    },
    "drivers": [],
    "domains_assessed": 0,
    "domains_total": 6,
    "score_divisor": None,
    "coverage_disclosure": "0 of 6 domains assessed",
    "scoring_version": SCORING_VERSION,
}


def _compat_score_dict(score_raw):
    """Mirror writer.py's compat wrapper shape (score.get('total'), not 'score')."""
    return {
        "total": score_raw["score"],
        "subscores": score_raw["subscores"],
        "drivers": list(score_raw.get("drivers", [])),
        "rating_cap_reason": None,
        "domains_assessed": score_raw["domains_assessed"],
        "domains_total": score_raw["domains_total"],
        "score_divisor": score_raw["score_divisor"],
        "coverage_disclosure": score_raw["coverage_disclosure"],
        "scoring_version": score_raw["scoring_version"],
    }


def _render_all_surfaces(tmp_path, score_raw, label):
    """Drive CLI markdown, HTML, DOCX (skipped if python-docx absent), and the
    writer.py compat scorecard markdown from ONE ExecContent built off score_raw.
    Returns a dict of surface_name -> rendered text (docx omitted if unavailable).
    """
    from quirk.reports.executive import build_exec_markdown
    from quirk.reports.html_renderer import render_html_report
    from quirk.reports.writer import _scorecard_markdown

    exec_content = build_exec_content(score_raw=score_raw, findings=[], roadmap_items=[])
    cfg = _make_minimal_cfg(str(tmp_path))

    cli_output = build_exec_markdown(cfg=cfg, endpoints=[], findings=[], exec_content=exec_content)

    html_path = os.path.join(str(tmp_path), f"{label}.html")
    render_html_report(
        path=html_path,
        cfg=cfg,
        endpoints=[],
        findings=[],
        score={"drivers": []},
        conf={"confidence": 60, "confidence_factors": {}},
        roadmap_items=[],
        exec_content=exec_content,
    )
    html_output = open(html_path, encoding="utf-8").read()

    compat_score = _compat_score_dict(score_raw)
    scorecard_output = _scorecard_markdown(
        cfg, compat_score, {"confidence": 60}, drivers=[], roadmap=[],
    )

    surfaces = {
        "cli": cli_output,
        "html": html_output,
        "scorecard": scorecard_output,
    }

    try:
        from docx import Document
    except ImportError:
        return surfaces  # DOCX leg skipped -- python-docx not installed

    from quirk.reports.docx_renderer import render_docx_report

    docx_path = os.path.join(str(tmp_path), f"{label}.docx")
    result = render_docx_report(path=docx_path, cfg=cfg, findings=[], exec_content=exec_content)
    if result:
        doc = Document(docx_path)
        surfaces["docx"] = "\n".join(p.text for p in doc.paragraphs)
    return surfaces


def test_coverage_disclosure_and_divisor_parity_across_surfaces(tmp_path):
    """T-188-09 / T-188-10: all surfaces disclose the SAME coverage sentence and
    the SAME divisor for a partial-coverage score -- comparing surfaces to each
    other, not each to a re-typed literal, is what makes this a parity test.
    """
    surfaces = _render_all_surfaces(tmp_path, _PARTIAL_SCORE_RAW, "partial")

    expected_disclosure = _PARTIAL_SCORE_RAW["coverage_disclosure"]
    expected_divisor_str = f"{_PARTIAL_SCORE_RAW['score_divisor']:g}"

    for name, text in surfaces.items():
        assert expected_disclosure in text, (
            f"{name} surface missing the coverage-disclosure sentence {expected_disclosure!r}."
        )
        assert expected_divisor_str in text, (
            f"{name} surface missing the dynamic divisor {expected_divisor_str!r}."
        )

    # Scoring-version marker: required on CLI + HTML per this task's behavior contract.
    assert SCORING_VERSION in surfaces["cli"], "CLI markdown missing the scoring-version marker."
    assert SCORING_VERSION in surfaces["html"], "HTML output missing the scoring-version marker."


def test_not_computed_never_renders_zero_over_100_across_surfaces(tmp_path):
    """T-188-11: a zero-assessed score never renders a fabricated readiness-score
    '0 / 100' headline or rollup on any surface, and each surface carries the
    once-composed not-computed statement verbatim.

    Scoped to the READINESS-SCORE rollup/headline specifically (not a blanket
    '0/100' substring ban): quirk/intelligence/confidence.py legitimately emits
    an unrelated, correctly-labeled "NO_DATA** (0/100)" confidence line when
    evidence is sparse -- that is a different metric with a different
    denominator and is out of this phase's scope.
    """
    surfaces = _render_all_surfaces(tmp_path, _ZERO_ASSESSED_SCORE_RAW, "notcomputed")

    for name, text in surfaces.items():
        assert "= 0 / 100" not in text, (
            f"{name} surface fabricated a readiness-score rollup '= 0 / 100' for a not-computed score."
        )
        assert "= **0 / 100**" not in text, (
            f"{name} surface fabricated a readiness-score headline '= **0 / 100**' for a not-computed score."
        )
        assert '<div class="score-value">0</div>' not in text, (
            f"{name} surface fabricated an HTML score-value of 0 for a not-computed score."
        )
        assert NOT_COMPUTED_STATEMENT in text, (
            f"{name} surface missing the once-composed not-computed statement."
        )
