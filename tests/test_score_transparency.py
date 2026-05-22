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


def _make_mock_score():
    """Construct a writer.py-style wrapped score dict (key='total', not 'score')."""
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
    assert "÷ 1.5" in output or "/ 1.5" in output, (
        "_scorecard_markdown output missing rollup math ('÷ 1.5' or '/ 1.5'). "
        "SCORE-XPARENCY-01 requires sum->÷1.5->overall rollup."
    )
    assert "Score Decomposition" in output, (
        "_scorecard_markdown output missing 'Score Decomposition' section header."
    )


def test_exec_markdown_contains_subscore_decomposition():
    """Gate: build_exec_markdown output contains N/25 labels and rollup math."""
    cfg = _make_mock_cfg()

    # build_exec_markdown calls build_evidence_summary + compute_readiness_score internally;
    # pass empty endpoints/findings so it produces a baseline score with subscores.
    output = build_exec_markdown(cfg, [], [])

    assert "/25" in output, (
        "build_exec_markdown output missing '/25' budget strings. "
        "SCORE-XPARENCY-01 requires subscore decomposition block."
    )
    assert "÷ 1.5" in output or "/ 1.5" in output, (
        "build_exec_markdown output missing rollup math ('÷ 1.5' or '/ 1.5'). "
        "SCORE-XPARENCY-01 requires sum->÷1.5->overall rollup."
    )
    assert "Score Decomposition" in output, (
        "build_exec_markdown output missing 'Score Decomposition' section header."
    )
