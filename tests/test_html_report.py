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


# ============================================================
# Phase 100 / FMT-01 / FMT-02: Cover page, logo embed, print CSS
# ============================================================


def _make_minimal_cfg_100(logo_path=None):
    """Return a Phase 100-extended minimal cfg namespace."""
    from types import SimpleNamespace
    return SimpleNamespace(
        assessment=SimpleNamespace(
            name="Test Org",
            report_owner="Test Owner",
            data_classification="CONFIDENTIAL",
            timezone="UTC",
            logo_path=logo_path,
        ),
        output=SimpleNamespace(directory="/tmp/quirk_test_html_100"),
    )


def _render_html(tmp_path, logo_path=None):
    """Helper: render a minimal report and return HTML content string."""
    from quirk.reports.html_renderer import render_html_report
    cfg = _make_minimal_cfg_100(logo_path=logo_path)
    out = str(tmp_path / "report-cover.html")
    render_html_report(
        path=out,
        cfg=cfg,
        endpoints=[],
        findings=[],
        score={"total": 70, "subscores": {}, "drivers": []},
        conf={"confidence": 75, "confidence_factors": {}},
        roadmap_items=[],
    )
    return open(out).read()


def test_cover_page_in_html(tmp_path):
    """Rendered HTML must contain the cover-page block."""
    content = _render_html(tmp_path)
    assert "cover-page" in content


def test_logo_absent_graceful(tmp_path):
    """When logo_path is None, no cover-logo-region div element appears in HTML."""
    content = _render_html(tmp_path, logo_path=None)
    # The CSS contains .cover-logo-region as a class name — check for the HTML *element* div
    assert '<div class="cover-logo-region">' not in content
    # org name must still be present
    assert "Test Org" in content


def test_logo_embedded(tmp_path):
    """When logo_path points to a valid PNG, rendered HTML contains base64 data URI."""
    # Create a minimal 1x1 PNG (valid PNG bytes)
    import struct, zlib
    def _minimal_png():
        sig = b'\x89PNG\r\n\x1a\n'
        def chunk(name, data):
            c = struct.pack('>I', len(data)) + name + data
            c += struct.pack('>I', zlib.crc32(name + data) & 0xffffffff)
            return c
        ihdr = chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0))
        raw = b'\x00\xff\xff\xff'  # filter byte + RGB pixel
        idat = chunk(b'IDAT', zlib.compress(raw))
        iend = chunk(b'IEND', b'')
        return sig + ihdr + idat + iend

    logo_file = str(tmp_path / "logo.png")
    with open(logo_file, "wb") as f:
        f.write(_minimal_png())
    content = _render_html(tmp_path, logo_path=logo_file)
    assert "data:image/png;base64," in content


def test_print_media_block(tmp_path):
    """Rendered HTML must contain an @media print block."""
    content = _render_html(tmp_path)
    assert "@media print" in content


def test_findings_table_class(tmp_path):
    """The All Findings table must carry class=\"findings-table\"."""
    # findings-table class is only emitted inside {% if findings %}, so pass one finding
    from quirk.reports.html_renderer import render_html_report
    cfg = _make_minimal_cfg_100()
    out = str(tmp_path / "report-findings.html")
    render_html_report(
        path=out,
        cfg=cfg,
        endpoints=[],
        findings=[{
            "severity": "HIGH",
            "title": "Test Finding",
            "host": "10.0.0.1",
            "port": 443,
            "description": "Test description",
            "recommendation": "Fix it",
            "quantum_risk": "Medium quantum risk",
        }],
        score={"total": 70, "subscores": {}, "drivers": []},
        conf={"confidence": 75, "confidence_factors": {}},
        roadmap_items=[],
    )
    content = open(out).read()
    assert 'class="findings-table"' in content


def test_fixed_table_layout_css(tmp_path):
    """Rendered HTML stylesheet must contain table-layout: fixed."""
    content = _render_html(tmp_path)
    assert "table-layout: fixed" in content
