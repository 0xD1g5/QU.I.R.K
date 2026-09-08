"""Phase 88 D-07 / SCORE-XPARENCY-01: Subscore decomposition render gate.

Asserts that _scorecard_markdown and build_exec_markdown outputs contain the six
subscore labels with /25 budget strings and the sum -> divide by 1.5 -> overall rollup.

This forward-locks the transparency contract: report surfaces must match the dashboard's
existing subscore gauge display, making the headline score auditable inline.
"""
from __future__ import annotations

from unittest.mock import MagicMock

from quirk.reports.writer import _scorecard_markdown
from quirk.reports.executive import build_exec_markdown
from quirk.reports.content_model import build_exec_content
from quirk.intelligence.scoring import SCORING_VERSION


def _make_mock_score():
    """Construct a writer.py-style wrapped score dict (key='total', not 'score').

    Phase 188 SCORE-06 / 188-03: full 6-of-6 coverage so the rollup arithmetic
    renders (a not-computed / partial-coverage score suppresses the rollup line
    by design — see test_score_coverage_disclosure.py for that behavior).
    """
    return {
        "total": 67,
        "subscores": {
            "hygiene": 20,
            "modern_tls": 18,
            "identity_trust": 25,
            "agility_signals": 15,
            "data_at_rest": 22,
            "data_in_motion": 21,
        },
        "drivers": ["Plaintext HTTP exposure (-12)", "RSA-only certificate posture (-8)"],
        "domains_assessed": 6,
        "domains_total": 6,
        "score_divisor": 1.5,
        "coverage_disclosure": "6 of 6 domains assessed",
        "scoring_version": SCORING_VERSION,
    }


def _make_mock_cfg():
    """Construct a minimal cfg mock that satisfies _scorecard_markdown."""
    cfg = MagicMock()
    cfg.assessment.report_owner = "Test Owner"
    cfg.assessment.data_classification = "CONFIDENTIAL"
    cfg.assessment.name = "Test Assessment"
    cfg.intelligence.profile = "balanced"
    cfg.intelligence.calibration_overrides = None
    return cfg


def test_scorecard_markdown_contains_subscore_decomposition():
    """Gate: _scorecard_markdown output contains N/25 labels and rollup math."""
    cfg = _make_mock_cfg()
    score = _make_mock_score()
    conf = {"confidence": 82}
    drivers = score["drivers"]
    roadmap = []

    output = _scorecard_markdown(cfg, score, conf, drivers, roadmap)

    assert "/25" in output, (
        "_scorecard_markdown output missing '/25' budget strings. "
        "SCORE-XPARENCY-01 requires subscore decomposition block."
    )
    # Phase 188 SCORE-06 / 188-03: the divisor is dynamic now (never a hardcoded
    # 1.5), but for a full 6-of-6 coverage fixture it still evaluates to 1.5 —
    # this assertion locks the ARITHMETIC RESULT, not a literal source string.
    assert "÷ 1.5" in output or "/ 1.5" in output, (
        "_scorecard_markdown output missing rollup math ('÷ 1.5' or '/ 1.5') for a "
        "full-coverage fixture. SCORE-XPARENCY-01 requires sum->divisor->overall rollup."
    )
    assert "Score Decomposition" in output, (
        "_scorecard_markdown output missing 'Score Decomposition' section header."
    )
    assert "6 of 6 domains assessed" in output, (
        "_scorecard_markdown output missing the coverage-disclosure sentence (SCORE-06)."
    )


def test_exec_markdown_contains_subscore_decomposition():
    """Gate: build_exec_markdown output contains N/25 labels and rollup math.

    Phase 188 SCORE-06 / 188-03: build_exec_markdown(cfg, [], []) with no
    exec_content now takes the not-computed path (zero domains assessed from
    empty endpoints/findings) and correctly suppresses the rollup arithmetic —
    that is exactly the behavior this phase adds, not a regression. This test
    instead builds a full-coverage ExecContent directly (mirroring writer.py's
    real call shape) so the primary, exec_content-driven rendering path is
    exercised with an actually-computed score.
    """
    cfg = _make_mock_cfg()
    score_raw = {
        "score": 78,
        "rating": "GOOD",
        "subscores": {
            "hygiene": 20, "modern_tls": 18, "identity_trust": 25,
            "agility_signals": 15, "data_at_rest": 22, "data_in_motion": 21,
        },
        "drivers": [],
        "domains_assessed": 6,
        "domains_total": 6,
        "score_divisor": 1.5,
        "coverage_disclosure": "6 of 6 domains assessed",
        "scoring_version": SCORING_VERSION,
    }
    exec_content = build_exec_content(score_raw=score_raw, findings=[], roadmap_items=[])

    output = build_exec_markdown(cfg, [], [], exec_content=exec_content)

    assert "/25" in output, (
        "build_exec_markdown output missing '/25' budget strings. "
        "SCORE-XPARENCY-01 requires subscore decomposition block."
    )
    assert "÷ 1.5" in output or "/ 1.5" in output, (
        "build_exec_markdown output missing rollup math ('÷ 1.5' or '/ 1.5') for a "
        "full-coverage fixture. SCORE-XPARENCY-01 requires sum->divisor->overall rollup."
    )
    assert "Score Decomposition" in output, (
        "build_exec_markdown output missing 'Score Decomposition' section header."
    )
    assert "6 of 6 domains assessed" in output, (
        "build_exec_markdown output missing the coverage-disclosure sentence (SCORE-06)."
    )
    assert SCORING_VERSION in output, (
        "build_exec_markdown output missing the scoring-version marker (SCORE-06)."
    )
