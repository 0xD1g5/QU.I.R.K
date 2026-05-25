"""Phase 102 Plan 03 TRANS-04 — Cross-surface score parity gate.

Asserts that the CLI executive markdown score_total, score_band, and every
subscore value are numerically identical to exec_content, closing the v5.2
score-tax tech-debt item.

Test node IDs from 102-03-PLAN.md:
  - test_score_parity_across_surfaces
"""
from __future__ import annotations

from types import SimpleNamespace

from quirk.reports.content_model import build_exec_content, ExecContent


# ---------------------------------------------------------------------------
# Shared fixtures — canonical score_raw shape (reuse from test_cross_surface_parity)
# FAIR band: no CRITICAL-count restriction so the congruence guard won't fire
# ---------------------------------------------------------------------------

_SCORE_RAW = {
    "score": 42,
    "rating": "FAIR",
    "subscores": {
        "hygiene": 10,
        "modern_tls": 7,
        "identity_trust": 11,
        "agility_signals": 6,
        "data_at_rest": 5,
        "data_in_motion": 3,
    },
    "drivers": [
        "Weak TLS 1.0 configuration detected",
        "No PQC hybrid candidates identified",
    ],
}

_FINDINGS = [
    {
        "title": "RSA-2048 certificate in use",
        "severity": "HIGH",
        "category": "certificate",
        "description": "RSA-2048 certificate; quantum-vulnerable harvest-now-decrypt-later risk.",
        "check_id": "CERT-RSA-2048",
        "host": "example.com",
        "port": 443,
    },
]

_ROADMAP_ITEMS_RAW = [
    {
        "phase": "NOW",
        "title": "Rotate RSA certificates to hybrid algorithm",
        "why": "RSA-2048 is quantum-vulnerable; migrate to hybrid or PQC certificate.",
        "owner_placeholder": "PKI Team",
        "timeframe": "NOW",
        "dependencies": [],
        "_priority": 1,
    },
]


def _make_minimal_cfg():
    """Minimal cfg-like namespace for renderer calls (mirrors test_cross_surface_parity.py)."""
    return SimpleNamespace(
        assessment=SimpleNamespace(
            name="Score Parity Test Org",
            report_owner="Parity Tester",
            data_classification="CONFIDENTIAL",
            timezone="UTC",
        ),
        output=SimpleNamespace(directory="/tmp/quirk_test_score_parity"),
        intelligence=SimpleNamespace(
            profile="balanced",
            calibration_overrides=None,
        ),
    )


# ---------------------------------------------------------------------------
# TRANS-04: test_score_parity_across_surfaces
# ---------------------------------------------------------------------------

def test_score_parity_across_surfaces():
    """TRANS-04: score_total, score_band, and subscores numerically identical in CLI vs exec_content.

    Builds one ExecContent instance and asserts that build_exec_markdown's CLI output
    contains score_total, score_band, and every subscore value literally — guaranteeing
    the CLI executive report shows numerically identical scores to HTML/PDF/DOCX.

    Node ID: test_score_parity.py::test_score_parity_across_surfaces
    """
    from quirk.reports.executive import build_exec_markdown

    exec_content: ExecContent = build_exec_content(
        score_raw=_SCORE_RAW,
        findings=_FINDINGS,
        roadmap_items=_ROADMAP_ITEMS_RAW,
    )

    cfg = _make_minimal_cfg()
    cli_output: str = build_exec_markdown(
        cfg=cfg,
        endpoints=[],
        findings=_FINDINGS,
        exec_content=exec_content,
    )

    # TRANS-04 assertion 1: score_total appears in CLI markdown
    assert str(exec_content.score_total) in cli_output, (
        f"TRANS-04 VIOLATION: exec_content.score_total ({exec_content.score_total!r}) "
        f"not found in CLI markdown output.\n"
        f"CLI output preview: {cli_output[:500]!r}"
    )

    # TRANS-04 assertion 2: score_band appears in CLI markdown
    assert exec_content.score_band in cli_output, (
        f"TRANS-04 VIOLATION: exec_content.score_band ({exec_content.score_band!r}) "
        f"not found in CLI markdown output.\n"
        f"CLI output preview: {cli_output[:500]!r}"
    )

    # TRANS-04 assertion 3: every subscore value appears in CLI markdown
    for key, val in exec_content.subscores.items():
        assert str(val) in cli_output, (
            f"TRANS-04 VIOLATION: subscore[{key!r}]={val!r} not found in CLI markdown output.\n"
            f"exec_content.subscores: {exec_content.subscores}\n"
            f"CLI output preview: {cli_output[:500]!r}"
        )

    # TRANS-04 assertion 4: the score section is inside the ## Quantum Readiness Score block
    assert "## Quantum Readiness Score" in cli_output, (
        "TRANS-04 VIOLATION: '## Quantum Readiness Score' section not found in CLI markdown. "
        "build_exec_markdown must render the score section when exec_content is provided."
    )
