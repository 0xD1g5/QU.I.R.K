"""Phase 98 EXEC-01/02/03, TRANS-02 — ordering and presence tests for CLI and HTML surfaces.

Verifies that:
  - CLI markdown narrative prose appears before any finding table (EXEC-01)
  - HTML narrative-block appears before the first <table> (EXEC-01)
  - HTML risks-list is present when findings exist (EXEC-02)
  - HTML roadmap items have priority-label spans (EXEC-03)
  - HTML rollup formula block is present (TRANS-02)

Test node IDs from 98-VALIDATION.md:
  - test_narrative_before_findings_cli
  - test_narrative_before_table_html
  - test_risks_list_in_html
  - test_priority_labels_in_html_roadmap
  - test_rollup_formula_in_html
"""
from __future__ import annotations

import os
from types import SimpleNamespace

import pytest

from quirk.reports.content_model import build_exec_content, ExecContent


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

def _make_minimal_cfg():
    """Return a minimal cfg-like namespace for renderer calls."""
    return SimpleNamespace(
        assessment=SimpleNamespace(
            name="Test Org",
            report_owner="Test Owner",
            data_classification="CONFIDENTIAL",
            timezone="UTC",
        ),
        output=SimpleNamespace(directory="/tmp/quirk_test_ordering"),
        intelligence=SimpleNamespace(
            profile="balanced",
            calibration_overrides=None,
        ),
    )


# Canonical score_raw (uses "score" key, not "total" — Pitfall 1 avoidance)
_SCORE_RAW_FAIR = {
    "score": 45,
    "rating": "FAIR",   # FAIR — no CRITICAL restriction, so guard won't fire
    "subscores": {
        "hygiene": 10,
        "modern_tls": 8,
        "identity_trust": 12,
        "agility_signals": 8,
        "data_at_rest": 4,
        "data_in_motion": 3,
    },
    "drivers": ["Weak TLS configuration detected", "No PQC candidates identified"],
}

_FINDINGS_WITH_RSA = [
    {
        "title": "RSA-2048 certificate",
        "severity": "HIGH",
        "category": "certificate",
        "description": "RSA-2048 certificate in use; quantum-vulnerable.",
        "host": "example.com",
        "port": 443,
    },
    {
        "title": "TLS 1.0 enabled",
        "severity": "MEDIUM",
        "category": "modern_tls",
        "description": "TLS 1.0 is deprecated and should be disabled.",
        "host": "example.com",
        "port": 443,
    },
]

_ROADMAP_ITEMS_RAW = [
    {
        "phase": "NOW",
        "title": "Rotate TLS 1.0 certificates",
        "why": "TLS 1.0 is deprecated; upgrade to TLS 1.3.",
        "owner_placeholder": "Security Team",
        "timeframe": "NOW",
        "dependencies": [],
        "_priority": 1,
    },
    {
        "phase": "NEXT",
        "title": "Evaluate PQC hybrid key exchange",
        "why": "Prepare for post-quantum migration.",
        "owner_placeholder": "Architecture Team",
        "timeframe": "NEXT",
        "dependencies": [],
        "_priority": 2,
    },
]


def _make_exec_content() -> ExecContent:
    """Build an ExecContent for FAIR band (no guard restrictions)."""
    return build_exec_content(
        score_raw=_SCORE_RAW_FAIR,
        findings=_FINDINGS_WITH_RSA,
        roadmap_items=_ROADMAP_ITEMS_RAW,
    )


def _render_html(tmp_path, exec_content: ExecContent) -> str:
    """Render HTML report and return its content string."""
    from quirk.reports.html_renderer import render_html_report

    cfg = _make_minimal_cfg()
    out = os.path.join(str(tmp_path), "report-ordering-test.html")
    os.makedirs(os.path.dirname(out), exist_ok=True)

    render_html_report(
        path=out,
        cfg=cfg,
        endpoints=[],
        findings=_FINDINGS_WITH_RSA,
        score={
            "total": _SCORE_RAW_FAIR["score"],
            "subscores": _SCORE_RAW_FAIR["subscores"],
            "drivers": [d for d in _SCORE_RAW_FAIR["drivers"]],
        },
        conf={"confidence": 65, "confidence_factors": {}},
        roadmap_items=_ROADMAP_ITEMS_RAW,
        exec_content=exec_content,
    )
    return open(out, encoding="utf-8").read()


# ---------------------------------------------------------------------------
# EXEC-01: CLI narrative before finding tables
# ---------------------------------------------------------------------------

def test_narrative_before_findings_cli():
    """EXEC-01: CLI markdown narrative prose block appears before any finding table.

    ## Readiness Assessment must appear before ## Findings Overview (Executive-Relevant)
    and before any GFM table row (| header |).
    Node ID: test_exec_narrative_ordering.py::test_narrative_before_findings_cli
    """
    from quirk.reports.executive import build_exec_markdown

    exec_content = _make_exec_content()
    cfg = _make_minimal_cfg()

    output = build_exec_markdown(
        cfg=cfg,
        endpoints=[],
        findings=_FINDINGS_WITH_RSA,
        exec_content=exec_content,
    )

    assert "## Readiness Assessment" in output, (
        "CLI markdown must contain '## Readiness Assessment' narrative block. "
        "EXEC-01 requires narrative before finding tables."
    )

    narrative_pos = output.index("## Readiness Assessment")
    findings_overview_pos = output.index("## Findings Overview")

    assert narrative_pos < findings_overview_pos, (
        f"'## Readiness Assessment' (pos {narrative_pos}) must appear before "
        f"'## Findings Overview' (pos {findings_overview_pos}). "
        "EXEC-01: narrative before finding tables."
    )

    # Also verify the narrative lead content is present
    assert exec_content.narrative_lead in output, (
        "CLI markdown must contain the exec_content.narrative_lead string. "
        "EXEC-01 / D-03: same narrative lead as HTML (shared content model)."
    )


# ---------------------------------------------------------------------------
# EXEC-01: HTML narrative before table
# ---------------------------------------------------------------------------

def test_narrative_before_table_html(tmp_path):
    """EXEC-01: HTML narrative-block div appears before the first <table> element.

    The .narrative-block div must be positioned before the score decomposition
    table and all finding tables in the HTML output.
    Node ID: test_exec_narrative_ordering.py::test_narrative_before_table_html
    """
    exec_content = _make_exec_content()
    content = _render_html(tmp_path, exec_content)

    assert "narrative-block" in content, (
        "HTML report must contain 'narrative-block' class div. "
        "EXEC-01 / D-03: narrative prose block before score card."
    )
    assert "<table" in content, (
        "HTML report must contain at least one <table> element. "
        "Prerequisite for ordering test."
    )

    narrative_pos = content.index("narrative-block")
    table_pos = content.index("<table")

    assert narrative_pos < table_pos, (
        f"'narrative-block' (pos {narrative_pos}) must appear before "
        f"first '<table' (pos {table_pos}) in HTML output. "
        "EXEC-01: narrative before finding tables."
    )

    # Verify narrative lead appears in the HTML block
    assert exec_content.narrative_lead in content, (
        "HTML report must contain the narrative_lead string from exec_content. "
        "EXEC-01 / EXEC-04: consistent narrative across surfaces."
    )


# ---------------------------------------------------------------------------
# EXEC-02: Risks list in HTML
# ---------------------------------------------------------------------------

def test_risks_list_in_html(tmp_path):
    """EXEC-02: HTML report contains a .risks-list when findings produce top-risks.

    The risks-list must be present with at least one risk item when findings
    include CRITICAL/HIGH/MEDIUM severity entries matching ALGO_IMPACT_MAP.
    Node ID: test_exec_narrative_ordering.py::test_risks_list_in_html
    """
    exec_content = _make_exec_content()

    # Confirm exec_content actually has top_risks (prerequisite)
    assert exec_content.top_risks, (
        "exec_content.top_risks is empty — test fixture does not produce top-risks. "
        "Verify _FINDINGS_WITH_RSA contains CRITICAL/HIGH/MEDIUM severity RSA findings."
    )

    content = _render_html(tmp_path, exec_content)

    assert "risks-list" in content, (
        "HTML report must contain 'risks-list' class element when top_risks are present. "
        "EXEC-02: top-risks business framing in HTML."
    )
    assert "risk-label" in content, (
        "HTML report must contain 'risk-label' span inside risks-list. "
        "EXEC-02: risk label text visible in HTML."
    )
    assert "Priority Business Risks" in content, (
        "HTML report must contain 'Priority Business Risks' section heading. "
        "EXEC-02 / UI-SPEC Copywriting Contract."
    )

    # Risks list must appear after score section but before findings breakdown
    risks_pos = content.index("risks-list")
    findings_breakdown_pos = content.index("Findings Breakdown")
    assert risks_pos < findings_breakdown_pos, (
        f"'risks-list' (pos {risks_pos}) must appear before 'Findings Breakdown' "
        f"(pos {findings_breakdown_pos}). "
        "EXEC-02: risks after score decomposition, before findings."
    )


# ---------------------------------------------------------------------------
# EXEC-03: Priority labels in HTML roadmap
# ---------------------------------------------------------------------------

def test_priority_labels_in_html_roadmap(tmp_path):
    """EXEC-03: HTML roadmap items contain .priority-label spans with effort/impact.

    Each roadmap item must have a .priority-label span showing effort and impact
    bands when exec_content is provided.
    Node ID: test_exec_narrative_ordering.py::test_priority_labels_in_html_roadmap
    """
    exec_content = _make_exec_content()

    # Confirm exec_content has roadmap items (prerequisite)
    assert exec_content.roadmap_items, (
        "exec_content.roadmap_items is empty — test fixture produced no roadmap items. "
        "Verify _ROADMAP_ITEMS_RAW is non-empty."
    )

    content = _render_html(tmp_path, exec_content)

    assert "priority-label" in content, (
        "HTML roadmap items must contain 'priority-label' class spans when exec_content is provided. "
        "EXEC-03: effort/impact priority labels on roadmap items."
    )

    # Verify at least one effort/impact label pattern appears
    assert "EFFORT" in content, (
        "HTML priority-label must contain 'EFFORT' band text. "
        "EXEC-03 / UI-SPEC Copywriting Contract."
    )
    assert "IMPACT" in content, (
        "HTML priority-label must contain 'IMPACT' band text. "
        "EXEC-03 / UI-SPEC Copywriting Contract."
    )


# ---------------------------------------------------------------------------
# TRANS-02: Rollup formula in HTML
# ---------------------------------------------------------------------------

def test_rollup_formula_in_html(tmp_path):
    """TRANS-02: HTML report contains the rollup formula explanation block.

    The .rollup-formula block with 'How this score was computed' and the
    six-pillar formula prose must appear after the score decomposition table.
    Node ID: test_exec_narrative_ordering.py::test_rollup_formula_in_html
    """
    exec_content = _make_exec_content()
    content = _render_html(tmp_path, exec_content)

    assert "rollup-formula" in content, (
        "HTML report must contain 'rollup-formula' class block. "
        "TRANS-02: rollup formula explanation visible in HTML."
    )
    assert "How this score was computed" in content, (
        "HTML report must contain 'How this score was computed' heading in rollup-formula block. "
        "TRANS-02 / UI-SPEC Copywriting Contract exact string."
    )
    assert "Six pillar subscores" in content, (
        "HTML report must contain 'Six pillar subscores' formula prose. "
        "TRANS-02 / UI-SPEC Copywriting Contract exact string."
    )

    # Rollup formula must appear after Score Decomposition and before Findings Breakdown
    rollup_pos = content.index("rollup-formula")
    findings_pos = content.index("Findings Breakdown")
    assert rollup_pos < findings_pos, (
        f"'rollup-formula' (pos {rollup_pos}) must appear before 'Findings Breakdown' "
        f"(pos {findings_pos}). TRANS-02: rollup formula in score section."
    )
