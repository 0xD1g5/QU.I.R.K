"""Phase 99 Plan 03 / CTX-01 / D-03: Render-parity gate across all report surfaces.

Asserts that the ``quantum_risk`` field populates correctly in:
- CLI markdown table (build_tech_markdown) — new Quantum Risk column between Description and Recommendation
- HTML All Findings table (render_html_report) — new Quantum Risk column
- HTML Top Findings table (render_html_report) — .quantum-risk-block inside Description cell
- Fallback string rendered when quantum_risk is absent
"""
from __future__ import annotations

import os
from types import SimpleNamespace

import pytest

from quirk.reports.technical import build_tech_markdown, FALLBACK_QR
from quirk.reports.html_renderer import render_html_report


# ── Fixtures ────────────────────────────────────────────────────────────────

_QR_TEXT = "RSA key material is vulnerable to Shor's algorithm — a sufficiently powerful quantum computer can factor the modulus and recover the private key, breaking both confidentiality and non-repudiation."

_FINDING_WITH_QR = {
    "severity": "HIGH",
    "host": "10.0.0.1",
    "port": 443,
    "title": "RSA-2048 certificate — quantum-vulnerable",
    "description": "Endpoint uses RSA-2048 which is quantum-vulnerable.",
    "recommendation": "Replace with ML-KEM.",
    "quantum_risk": _QR_TEXT,
    "compliance": [],
}

_FINDING_WITHOUT_QR = {
    "severity": "MEDIUM",
    "host": "10.0.0.2",
    "port": 8443,
    "title": "Weak cipher suite",
    "description": "Server supports a weak cipher suite.",
    "recommendation": "Disable weak cipher suites.",
    "compliance": [],
}


def _cfg():
    return SimpleNamespace(
        assessment=SimpleNamespace(
            name="Parity Test Org",
            report_owner="Tester",
            data_classification="CONFIDENTIAL",
            timezone="UTC",
        ),
        output=SimpleNamespace(directory="/tmp/quirk_test_99_03"),
    )


def _render_html(tmp_path, findings):
    out = os.path.join(str(tmp_path), "report.html")
    render_html_report(
        path=out,
        cfg=_cfg(),
        endpoints=[],
        findings=findings,
        score={"total": 50, "subscores": {}, "drivers": []},
        conf={"confidence": 60, "confidence_factors": {}},
        roadmap_items=[],
    )
    return open(out, encoding="utf-8").read()


# ── Markdown surface tests ───────────────────────────────────────────────────

def test_markdown_has_quantum_risk_column():
    """build_tech_markdown header row must contain 'Quantum Risk' column."""
    cfg = SimpleNamespace(assessment=SimpleNamespace(name="Test"))
    output = build_tech_markdown(cfg, [], [_FINDING_WITH_QR])
    assert "Quantum Risk" in output, (
        "CTX-01: build_tech_markdown must include a 'Quantum Risk' column header"
    )


def test_markdown_renders_quantum_risk_text():
    """A finding with quantum_risk set must render that text in the markdown table."""
    cfg = SimpleNamespace(assessment=SimpleNamespace(name="Test"))
    output = build_tech_markdown(cfg, [], [_FINDING_WITH_QR])
    # truncated to 120 chars in the cell
    expected_fragment = _QR_TEXT[:60]
    assert expected_fragment in output, (
        f"CTX-01: quantum_risk text must appear in the markdown findings table. "
        f"Looking for: {expected_fragment!r}"
    )


def test_render_fallback_when_missing():
    """A finding without quantum_risk must render the fallback string in the markdown table."""
    cfg = SimpleNamespace(assessment=SimpleNamespace(name="Test"))
    output = build_tech_markdown(cfg, [], [_FINDING_WITHOUT_QR])
    # The fallback string (truncated to 120) must appear in the cell
    assert FALLBACK_QR[:60] in output, (
        f"CTX-01: when quantum_risk is absent the fallback '{FALLBACK_QR[:40]}...' must appear"
    )


# ── HTML surface tests ───────────────────────────────────────────────────────

def test_html_all_findings_has_quantum_risk(tmp_path):
    """HTML All Findings table must contain a Quantum Risk header and the finding's value."""
    html = _render_html(tmp_path, [_FINDING_WITH_QR])
    assert "Quantum Risk" in html, (
        "CTX-01: HTML All Findings table must have a Quantum Risk header"
    )
    # quantum_risk value (first 80 chars) must appear in the rendered HTML
    assert _QR_TEXT[:80] in html, (
        "CTX-01: HTML must render the quantum_risk field value in All Findings table"
    )


def test_html_top_findings_risk_block(tmp_path):
    """HTML Top Findings table must contain the .quantum-risk-block class."""
    html = _render_html(tmp_path, [_FINDING_WITH_QR])
    assert "quantum-risk-block" in html, (
        "CTX-01: HTML Top Findings Description cell must contain class 'quantum-risk-block'"
    )
