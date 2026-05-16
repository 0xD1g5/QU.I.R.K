"""Jinja2-based standalone HTML report renderer for QU.I.R.K. (Phase 7, D-08 to D-12)."""
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

from quirk.util.safe_exc import safe_str
from quirk.util.sanitize import sanitize_scanner_text


def _score_band(total: int) -> str:
    if total >= 85:
        return "EXCELLENT"
    if total >= 70:
        return "GOOD"
    if total >= 55:
        return "MODERATE"
    if total >= 35:
        return "FAIR"
    return "POOR"


def _score_color(band: str) -> str:
    return {
        "EXCELLENT": "#4caf50",
        "GOOD": "#66bb6a",
        "MODERATE": "#f9a825",
        "FAIR": "#f57c00",
        "POOR": "#e53935",
    }.get(band, "#aaaaaa")


def _severity_color(severity: str) -> str:
    return {
        "CRITICAL": "#e53935",
        "HIGH": "#f57c00",
        "MEDIUM": "#f9a825",
        "LOW": "#5c9cff",
        "INFO": "#888888",
    }.get(str(severity).upper(), "#888888")


# Use FileSystemLoader so templates are found without pip reinstall (RESEARCH.md Pattern 2).
# This works for both development installs and editable installs without package data rebuild.
_TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")


def render_html_report(
    path: str,
    cfg: Any,
    endpoints: List[Any],
    findings: List[Dict[str, Any]],
    score: Dict[str, Any],
    conf: Dict[str, Any],
    roadmap_items: List[Dict[str, Any]],
) -> None:
    """Render a self-contained HTML report to *path*.

    All CSS is inlined. No CDN references. Works offline (D-08).
    """
    env = Environment(
        loader=FileSystemLoader(_TEMPLATES_DIR),
        autoescape=select_autoescape(["html", "j2"]),
    )
    env.filters["sanitize"] = sanitize_scanner_text
    template = env.get_template("report.html.j2")

    total_score = score.get("total", 0)
    band = _score_band(total_score)

    # Severity counts
    sev_counts: Dict[str, int] = {}
    for f in (findings or []):
        # Phase 45 / D-07: coverage_gap findings are advisory-only and MUST NOT
        # inflate severity counts in the executive summary.
        if f.get("category") == "coverage_gap":
            continue
        s = str(f.get("severity", "INFO")).upper()
        sev_counts[s] = sev_counts.get(s, 0) + 1

    # Roadmap sections
    # Phase 77 D-13 / cbom-intel-reports/IN-07: C-7 verification — both branches
    # (timeframe match and phase match) are reachable; closes IN-07 as
    # audit-flip-only. See tests/test_html_renderer_roadmap_section.py for the
    # mutation evidence.
    def roadmap_section(tf: str) -> List[Dict]:
        return [r for r in (roadmap_items or []) if r.get("timeframe") == tf or r.get("phase") == tf]

    html = template.render(
        org_name=getattr(getattr(cfg, "assessment", None), "name", "Unknown"),
        report_owner=getattr(getattr(cfg, "assessment", None), "report_owner", ""),
        data_classification=getattr(getattr(cfg, "assessment", None), "data_classification", "CONFIDENTIAL"),
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        total_score=total_score,
        score_band=band,
        score_color=_score_color(band),
        confidence=conf.get("confidence", 0),
        sev_counts=sev_counts,
        drivers=score.get("drivers", []),
        findings=findings or [],
        endpoints=endpoints or [],
        roadmap_now=roadmap_section("NOW"),
        roadmap_next=roadmap_section("NEXT"),
        roadmap_later=roadmap_section("LATER"),
        severity_color=_severity_color,
    )
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)


def render_pdf_report(html_path: str, pdf_path: str) -> bool:
    """Render html_path to pdf_path using Playwright headless Chromium.

    Returns True on success, False if Playwright is unavailable (graceful degradation, D-11).
    """
    try:
        from playwright.sync_api import sync_playwright
        from playwright.sync_api import Error as PlaywrightError, TimeoutError as PlaywrightTimeoutError
    except ImportError:
        return False
    browser = None
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(f"file://{os.path.abspath(html_path)}")
            page.pdf(
                path=pdf_path,
                format="A4",
                margin={"top": "15mm", "bottom": "15mm", "left": "12mm", "right": "12mm"},
                print_background=True,
            )
        return True
    except (PlaywrightError, PlaywrightTimeoutError, OSError, RuntimeError) as e:
        print(
            f"PDF generation failed: {safe_str(e)}; scan complete, HTML report at {html_path}",
            file=sys.stderr,
        )
        return False
    finally:
        if browser is not None:
            try:
                browser.close()
            except Exception:
                pass
