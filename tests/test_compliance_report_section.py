"""Phase 49 COMPLY-05 smoke: rendered HTML contains a 'Compliance Summary'
section listing the three frameworks (PCI-DSS 4.0.1, HIPAA 45 CFR, FIPS 140-3)
plus a 'Findings without compliance mapping' section.

RED-state baseline: this test is expected to fail until Plan 49-04 ships the
template insertion. Wave 0 only proves the test is collectable.
"""
from __future__ import annotations

import os
import pathlib
import types

from quirk.reports.html_renderer import render_html_report

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_template_path_exists():
    """Catch accidental rename of the report.html.j2 template."""
    template = _REPO_ROOT / "quirk/reports/templates/report.html.j2"
    assert template.is_file(), (
        f"Report template missing at {template}. Update test if file was renamed."
    )


def _build_cfg() -> types.SimpleNamespace:
    return types.SimpleNamespace(
        assessment=types.SimpleNamespace(
            name="Smoke Test Org",
            report_owner="qa@example.com",
            data_classification="CONFIDENTIAL",
        )
    )


def test_html_contains_compliance_summary(tmp_path):
    findings = [
        {
            "severity": "HIGH",
            "host": "example.com",
            "port": 80,
            "title": "Plaintext HTTP service detected",
            "description": "HTTP without TLS.",
            "recommendation": "Enable TLS.",
        },
        {
            "severity": "LOW",
            "host": "example.com",
            "port": 443,
            "title": "Synthetic unmapped finding for smoke",
            "description": "Synthetic finding with no compliance mapping.",
            "recommendation": "n/a",
        },
    ]
    out_path = tmp_path / "report.html"
    render_html_report(
        path=str(out_path),
        cfg=_build_cfg(),
        endpoints=[],
        findings=findings,
        score={"total": 70, "drivers": []},
        conf={"confidence": 80},
        roadmap_items=[],
    )
    assert out_path.is_file(), "render_html_report did not produce a file."
    text = out_path.read_text(encoding="utf-8")
    for needle in (
        "Compliance Summary",
        "PCI-DSS 4.0.1",
        "HIPAA 45 CFR",
        "FIPS 140-3",
        "Findings without compliance mapping",
    ):
        assert needle in text, (
            f"Rendered HTML missing required substring '{needle}'. "
            f"Plan 49-04 must insert the Compliance Summary block into "
            f"quirk/reports/templates/report.html.j2."
        )
