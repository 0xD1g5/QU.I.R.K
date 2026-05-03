"""Phase 45 / Plan 03 / Task 2 — HTML report Coverage Gaps section + sev-count exclusion."""
from __future__ import annotations

import os
from types import SimpleNamespace

import pytest


def _cfg():
    return SimpleNamespace(
        assessment=SimpleNamespace(
            name="Test Org",
            report_owner="Owner",
            data_classification="CONFIDENTIAL",
            timezone="UTC",
        ),
        output=SimpleNamespace(directory="/tmp/quirk_test_45_03"),
    )


def _render(tmp_path, findings):
    from quirk.reports.html_renderer import render_html_report

    out = os.path.join(str(tmp_path), "report.html")
    render_html_report(
        path=out,
        cfg=_cfg(),
        endpoints=[],
        findings=findings,
        score={"total": 75, "subscores": {}, "drivers": []},
        conf={"confidence": 80, "confidence_factors": {}},
        roadmap_items=[],
    )
    return open(out, encoding="utf-8").read()


_GAP_REC = "Kerberos scanning skipped — install pip install quirk[identity] to enable"


def _gap_finding(host="kerberos_scanner", recommendation=_GAP_REC):
    return {
        "severity": "INFO",
        "category": "coverage_gap",
        "host": host,
        "port": 0,
        "title": "Scanner skipped — optional extra not installed",
        "recommendation": recommendation,
    }


def test_coverage_gaps_section_renders(tmp_path):
    html = _render(tmp_path, [_gap_finding()])
    assert "<h2>Coverage Gaps</h2>" in html
    assert "kerberos_scanner" in html
    # Recommendation text rendered (fragment of install hint)
    assert "pip install quirk[identity]" in html


def test_coverage_gap_excluded_from_all_findings_table(tmp_path):
    sentinel = "UNIQUE-SENTINEL-COVGAP-XYZ install hint sample"
    html = _render(tmp_path, [_gap_finding(recommendation=sentinel)])
    # Sentinel must appear exactly ONCE — only in the Coverage Gaps section,
    # not duplicated into the All Findings table.
    assert html.count(sentinel) == 1, (
        f"coverage_gap recommendation appeared {html.count(sentinel)} times "
        f"(expected exactly 1 in Coverage Gaps section only)"
    )


def test_sev_counts_exclude_coverage_gap(tmp_path):
    findings = [
        {
            "severity": "HIGH",
            "host": "x",
            "port": 1,
            "title": "Plaintext HTTP service detected",
            "recommendation": "Migrate.",
        },
        _gap_finding(host="kerb"),
        _gap_finding(host="saml"),
    ]
    html = _render(tmp_path, findings)
    # The sev_counts pills should report HIGH=1, INFO=0 (the two coverage_gap rows
    # must NOT inflate the INFO count).
    # The renderer formats counts via the template — assert via the literal value cells.
    # Look for the INFO pill and ensure its accompanying count is 0.
    # Search for "INFO" in proximity to "0" in the sev_counts area; safer: assert the
    # sev_counts pill text contains "INFO" and "0" near each other.
    # Use a robust approach: render with NO coverage_gap, render with 2 coverage_gap,
    # confirm INFO count is identical (0 in both).
    html_zero = _render(tmp_path, [findings[0]])
    # Pull the exact "INFO ... <some int>" sequence; if both reports equal, we're good.
    assert ">INFO<" in html_zero or "INFO" in html_zero
    # Most direct: extract the sev_counts dict-driven pill markup. The renderer
    # produces something like `<span class="pill ...">INFO {{ count }}</span>` —
    # rather than parsing markup, assert the pair.
    # We assert the precise template substring contains an INFO=0 occurrence.
    # For both renders, count occurrences of "INFO" — they should match.
    # Strongest check: the integer `2` should NOT appear next to INFO since INFO is 0.
    import re
    # Pull the severity pills section; renderer outputs something like:
    # <span class="...">INFO</span><span ...>0</span> or similar.
    # Find any "INFO" then nearest digit afterwards (within 50 chars).
    m = re.search(r"INFO[^0-9<]{0,80}([0-9]+)", html)
    assert m is not None, "could not locate INFO count in rendered HTML"
    info_count = int(m.group(1))
    assert info_count == 0, (
        f"INFO sev count was {info_count}; expected 0 (coverage_gap rows must be excluded)"
    )
    m2 = re.search(r"HIGH[^0-9<]{0,80}([0-9]+)", html)
    assert m2 is not None
    assert int(m2.group(1)) == 1


def test_no_coverage_gaps_section_when_empty(tmp_path):
    html = _render(tmp_path, [])
    assert "<h2>Coverage Gaps</h2>" not in html


def test_top10_executive_preview_excludes_coverage_gap(tmp_path):
    # Mix: one HIGH plaintext finding + one coverage_gap. The exec top-10 preview
    # must NOT contain the coverage_gap row.
    sentinel = "TOP10-SENTINEL-NO-COVGAP-HERE"
    findings = [
        {
            "severity": "HIGH",
            "host": "x",
            "port": 1,
            "title": "Plaintext HTTP service detected",
            "recommendation": "Migrate.",
        },
        _gap_finding(host="kerb", recommendation=sentinel),
    ]
    html = _render(tmp_path, findings)
    # The Coverage Gaps section will contain the sentinel — exactly once.
    assert html.count(sentinel) == 1
    # And the Top Findings (top-10 preview) must not contain the coverage_gap title.
    # The preview block sits under '<h2>Top Findings</h2>'. Slice to that section:
    if "<h2>Top Findings</h2>" in html:
        top_idx = html.index("<h2>Top Findings</h2>")
        # End at the next h2 boundary
        rest = html[top_idx:]
        next_h2 = rest.find("<h2>", 5)
        top_block = rest[:next_h2] if next_h2 > 0 else rest
        assert "Scanner skipped — optional extra not installed" not in top_block, (
            "coverage_gap finding leaked into Top Findings (top-10) preview"
        )
