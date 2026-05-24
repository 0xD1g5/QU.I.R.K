"""Phase 98 EXEC-04 — Cross-surface content parity gate (D-03a).

Belt-and-suspenders corroboration on top of the structural D-03 guarantee:
one ExecContent instance passed to both CLI and HTML renderers must produce
identical narrative_lead text and identical top_risks count + labels.

This test is NOT the primary parity mechanism (D-03's single shared instance IS),
but provides an observable, auto-running regression gate for EXEC-04.

Test node IDs from 98-VALIDATION.md:
  - test_narrative_content_parity
  - test_top_risks_parity
"""
from __future__ import annotations

import os
from types import SimpleNamespace

from quirk.reports.content_model import build_exec_content, ExecContent


# ---------------------------------------------------------------------------
# Shared fixtures — canonical score_raw shape (Pitfall 1: "score" not "total")
# ---------------------------------------------------------------------------

# FAIR band: no CRITICAL-count restriction so the congruence guard won't fire
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

# One MEDIUM-severity RSA finding — guarantees at least one top_risk entry
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
    """Minimal cfg-like namespace for renderer calls (mirrors test_html_report.py pattern)."""
    return SimpleNamespace(
        assessment=SimpleNamespace(
            name="Cross-Surface Parity Test Org",
            report_owner="Parity Tester",
            data_classification="CONFIDENTIAL",
            timezone="UTC",
        ),
        output=SimpleNamespace(directory="/tmp/quirk_test_cross_surface_parity"),
        intelligence=SimpleNamespace(
            profile="balanced",
            calibration_overrides=None,
        ),
    )


# ---------------------------------------------------------------------------
# EXEC-04 / D-03a: test_narrative_content_parity
# ---------------------------------------------------------------------------

def test_narrative_content_parity(tmp_path):
    """EXEC-04 / D-03a: single ExecContent yields identical narrative_lead in CLI and HTML.

    One ExecContent instance is built and passed to BOTH build_exec_markdown() and
    render_html_report(). The narrative_lead string must appear verbatim in both outputs.
    This is the cross-surface belt-and-suspenders corroboration of D-03 (structural
    single-source guarantee).

    Node ID: test_cross_surface_parity.py::test_narrative_content_parity
    """
    from quirk.reports.executive import build_exec_markdown
    from quirk.reports.html_renderer import render_html_report

    # Build ONE ExecContent instance (D-03 guarantee: same object → same content)
    exec_content: ExecContent = build_exec_content(
        score_raw=_SCORE_RAW,
        findings=_FINDINGS,
        roadmap_items=_ROADMAP_ITEMS_RAW,
    )
    assert exec_content.narrative_lead, (
        "exec_content.narrative_lead is empty — build_exec_content returned no narrative lead. "
        "EXEC-04: cannot assert parity on an empty string."
    )

    # CLI surface: pass exec_content to build_exec_markdown
    cfg = _make_minimal_cfg()
    cli_output: str = build_exec_markdown(
        cfg=cfg,
        endpoints=[],
        findings=_FINDINGS,
        exec_content=exec_content,
    )

    # HTML surface: render to tmp dir, read back
    html_path = os.path.join(str(tmp_path), "parity-test.html")
    render_html_report(
        path=html_path,
        cfg=cfg,
        endpoints=[],
        findings=_FINDINGS,
        score={
            "total": _SCORE_RAW["score"],
            "subscores": _SCORE_RAW["subscores"],
            "drivers": list(_SCORE_RAW["drivers"]),
        },
        conf={"confidence": 60, "confidence_factors": {}},
        roadmap_items=_ROADMAP_ITEMS_RAW,
        exec_content=exec_content,
    )
    html_output: str = open(html_path, encoding="utf-8").read()

    # EXEC-04 assertion: narrative_lead appears verbatim in CLI output
    assert exec_content.narrative_lead in cli_output, (
        f"EXEC-04 VIOLATION: exec_content.narrative_lead not found in CLI markdown output.\n"
        f"  Expected substring: {exec_content.narrative_lead!r}\n"
        f"  CLI output preview: {cli_output[:400]!r}"
    )

    # EXEC-04 assertion: narrative_lead appears verbatim in HTML output
    assert exec_content.narrative_lead in html_output, (
        f"EXEC-04 VIOLATION: exec_content.narrative_lead not found in HTML output.\n"
        f"  Expected substring: {exec_content.narrative_lead!r}\n"
        f"  HTML output preview (first 600 chars after <body): ..."
    )

    # Belt-and-suspenders: both surfaces contain the identical string — parity confirmed
    assert (exec_content.narrative_lead in cli_output) and (exec_content.narrative_lead in html_output), (
        "EXEC-04 VIOLATION: narrative_lead is present in one surface but absent in the other. "
        "D-03 shared content model must guarantee identical narrative_lead across CLI and HTML."
    )


# ---------------------------------------------------------------------------
# EXEC-04 / D-03a: test_top_risks_parity
# ---------------------------------------------------------------------------

def test_top_risks_parity(tmp_path):
    """EXEC-04 / D-03a: CLI and HTML carry identical top_risks count and labels.

    One ExecContent instance is built (guaranteeing same top_risks list). The CLI
    markdown Priority Business Risks bullet count and the HTML .risks-list item count
    must both equal exec_content.top_risks count. Risk labels must match across surfaces.

    Node ID: test_cross_surface_parity.py::test_top_risks_parity
    """
    from quirk.reports.executive import build_exec_markdown
    from quirk.reports.html_renderer import render_html_report

    exec_content: ExecContent = build_exec_content(
        score_raw=_SCORE_RAW,
        findings=_FINDINGS,
        roadmap_items=_ROADMAP_ITEMS_RAW,
    )

    # Prerequisite: fixture findings must produce at least one top_risk
    assert exec_content.top_risks, (
        "exec_content.top_risks is empty — _FINDINGS fixture does not produce any top-risks. "
        "EXEC-04 parity test requires at least one risk entry."
    )

    expected_risk_count = len(exec_content.top_risks)
    expected_labels = [r.risk_label for r in exec_content.top_risks]

    # CLI surface
    cfg = _make_minimal_cfg()
    cli_output: str = build_exec_markdown(
        cfg=cfg,
        endpoints=[],
        findings=_FINDINGS,
        exec_content=exec_content,
    )

    # HTML surface
    html_path = os.path.join(str(tmp_path), "parity-risks-test.html")
    render_html_report(
        path=html_path,
        cfg=cfg,
        endpoints=[],
        findings=_FINDINGS,
        score={
            "total": _SCORE_RAW["score"],
            "subscores": _SCORE_RAW["subscores"],
            "drivers": list(_SCORE_RAW["drivers"]),
        },
        conf={"confidence": 60, "confidence_factors": {}},
        roadmap_items=_ROADMAP_ITEMS_RAW,
        exec_content=exec_content,
    )
    html_output: str = open(html_path, encoding="utf-8").read()

    # --- CLI count gate ---
    # Priority Business Risks bullets appear after the "## Priority Business Risks" heading.
    # Each risk produces exactly one bullet: "- **{risk_label}** — {impact_sentence}"
    assert "## Priority Business Risks" in cli_output, (
        "EXEC-04 VIOLATION: '## Priority Business Risks' section not found in CLI markdown. "
        "build_exec_markdown must render top_risks when exec_content is provided."
    )
    # Count occurrences of risk_label in CLI (one per risk bullet)
    cli_risk_label_count = sum(
        1 for label in expected_labels if label in cli_output
    )
    assert cli_risk_label_count == expected_risk_count, (
        f"EXEC-04 VIOLATION: CLI markdown risk label count ({cli_risk_label_count}) != "
        f"exec_content.top_risks count ({expected_risk_count}). "
        "D-03: CLI must render all top_risks from the shared ExecContent."
    )

    # --- HTML count gate ---
    assert "risks-list" in html_output, (
        "EXEC-04 VIOLATION: '.risks-list' not found in HTML output. "
        "render_html_report must render top_risks when exec_content is provided."
    )
    # Count occurrences of risk_label in HTML (one per <li> item)
    html_risk_label_count = sum(
        1 for label in expected_labels if label in html_output
    )
    assert html_risk_label_count == expected_risk_count, (
        f"EXEC-04 VIOLATION: HTML risk label count ({html_risk_label_count}) != "
        f"exec_content.top_risks count ({expected_risk_count}). "
        "D-03: HTML must render all top_risks from the shared ExecContent."
    )

    # --- Cross-surface label identity ---
    for label in expected_labels:
        assert label in cli_output, (
            f"EXEC-04 VIOLATION: risk_label {label!r} present in exec_content.top_risks "
            f"but not found in CLI markdown output. "
            "D-03 shared model must guarantee identical labels across surfaces."
        )
        assert label in html_output, (
            f"EXEC-04 VIOLATION: risk_label {label!r} present in exec_content.top_risks "
            f"but not found in HTML output. "
            "D-03 shared model must guarantee identical labels across surfaces."
        )
