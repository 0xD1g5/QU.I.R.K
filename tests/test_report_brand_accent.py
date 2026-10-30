"""D-03: report cover title and header/cover borders use the brand dark accent.

The expected hex is derived from the dashboard's index.css --ds-accent (dark
block), never hard-coded, so the report and the dashboard cannot drift apart.
Links, h1 and roadmap headings intentionally keep var(--accent).
"""
from __future__ import annotations

import re
from pathlib import Path
from types import SimpleNamespace

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = REPO_ROOT / "quirk/reports/templates/report.html.j2"


def _dark_accent() -> str:
    css = (REPO_ROOT / "src/dashboard/src/index.css").read_text(encoding="utf-8")
    dark = css.split(".light {")[0]
    m = re.search(r"--ds-accent:\s*(#[0-9a-fA-F]{6})\s*;", dark)
    assert m, "no --ds-accent hex found in the dark block"
    return m.group(1).lower()


def _tpl() -> str:
    return TEMPLATE.read_text(encoding="utf-8")


def _rule(src: str, selector: str) -> str:
    m = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", src)
    assert m, f"{selector} rule not found"
    return m.group(1)


def test_brand_accent_token_matches_dashboard_dark_accent():
    m = re.search(r"--brand-accent:\s*(#[0-9a-fA-F]{6})\s*;", _tpl())
    assert m, "--brand-accent missing from template :root"
    assert m.group(1).lower() == _dark_accent()


def test_cover_and_header_rules_use_brand_accent():
    src = _tpl()
    assert "color: var(--brand-accent)" in _rule(src, ".cover-title")
    assert "border-top: 4px solid var(--brand-accent)" in _rule(src, ".cover-page")
    assert "border-bottom: 2px solid var(--brand-accent)" in _rule(src, ".report-header")


def test_accent_token_untouched_for_links():
    src = _tpl()
    assert re.search(r"--accent:\s*#3b9dff\s*;", src)
    assert "color: var(--accent)" in _rule(src, "a")
    assert "color: var(--accent)" in _rule(src, "h1")


def test_rendered_report_carries_brand_accent(tmp_path):
    from quirk.reports.html_renderer import render_html_report

    cfg = SimpleNamespace(
        assessment=SimpleNamespace(
            name="Test Org", report_owner="Owner",
            data_classification="CONFIDENTIAL", timezone="UTC",
        ),
        output=SimpleNamespace(directory=str(tmp_path)),
    )
    out = str(tmp_path / "report.html")
    render_html_report(
        path=out, cfg=cfg, endpoints=[], findings=[],
        score={"total": 75, "subscores": {}, "drivers": []},
        conf={"confidence": 80, "confidence_factors": {}},
        roadmap_items=[],
    )
    html = Path(out).read_text(encoding="utf-8")
    assert "--brand-accent:" in html
    assert "color: var(--brand-accent)" in _rule(html, ".cover-title")


def test_brand_accent_is_not_signal_green():
    m = re.search(r"--brand-accent:\s*(#[0-9a-fA-F]{6})", _tpl())
    assert m and m.group(1).lower() != "#7fe001"
