"""Phase 7 — BRAND-01/BRAND-03: HTML report and branding tests."""
import os
import pytest


def _make_minimal_cfg():
    """Return a minimal cfg-like namespace for renderer calls."""
    from types import SimpleNamespace
    return SimpleNamespace(
        assessment=SimpleNamespace(
            name="Test Org",
            report_owner="Test Owner",
            data_classification="CONFIDENTIAL",
            timezone="UTC",
        ),
        output=SimpleNamespace(directory="/tmp/quirk_test_html"),
    )


def test_report_contains_wordmark():
    """HTML report must contain the QU.I.R.K. wordmark string."""
    from quirk.reports.html_renderer import render_html_report  # RED: module does not exist yet
    import tempfile, os
    cfg = _make_minimal_cfg()
    os.makedirs(cfg.output.directory, exist_ok=True)
    out = os.path.join(cfg.output.directory, "report-test.html")
    render_html_report(
        path=out,
        cfg=cfg,
        endpoints=[],
        findings=[],
        score={"total": 75, "subscores": {}, "drivers": []},
        conf={"confidence": 80, "confidence_factors": {}},
        roadmap_items=[],
    )
    content = open(out).read()
    assert "QU.I.R.K." in content


def test_html_is_self_contained():
    """HTML report must not contain external CDN <link> or <script src> references."""
    from quirk.reports.html_renderer import render_html_report
    import tempfile, os
    cfg = _make_minimal_cfg()
    os.makedirs(cfg.output.directory, exist_ok=True)
    out = os.path.join(cfg.output.directory, "report-selfcontained.html")
    render_html_report(
        path=out, cfg=cfg, endpoints=[], findings=[],
        score={"total": 50, "subscores": {}, "drivers": []},
        conf={"confidence": 60, "confidence_factors": {}},
        roadmap_items=[],
    )
    content = open(out).read()
    import re
    # No external HTTP/HTTPS references in link or script elements
    external_refs = re.findall(r'<(?:link|script)[^>]+https?://', content, re.IGNORECASE)
    assert external_refs == [], f"Found external refs: {external_refs}"


def test_html_report_sections():
    """HTML report must contain executive summary section and technical appendix."""
    from quirk.reports.html_renderer import render_html_report
    import os
    cfg = _make_minimal_cfg()
    os.makedirs(cfg.output.directory, exist_ok=True)
    out = os.path.join(cfg.output.directory, "report-sections.html")
    render_html_report(
        path=out, cfg=cfg, endpoints=[], findings=[],
        score={"total": 60, "subscores": {}, "drivers": []},
        conf={"confidence": 70, "confidence_factors": {}},
        roadmap_items=[],
    )
    content = open(out).read()
    assert "Executive Summary" in content
    assert "Technical Appendix" in content


def test_pdf_graceful_degradation(tmp_path, monkeypatch):
    """write_reports() must create report.html even if playwright is unavailable."""
    import sys
    # Simulate playwright being unavailable
    monkeypatch.setitem(sys.modules, "playwright", None)
    monkeypatch.setitem(sys.modules, "playwright.sync_api", None)
    from quirk.reports import writer
    import importlib
    importlib.reload(writer)  # reload with patched modules
    # After Phase 7 implementation write_reports() will produce report-*.html
    # For now this test just asserts the module reloads without error
    assert hasattr(writer, "write_reports")
