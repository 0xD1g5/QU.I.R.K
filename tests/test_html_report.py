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


# ============================================================
# Phase 100 / CR-01: _load_logo_b64 graceful-omit failure paths
# ============================================================

def test_logo_missing_path_returns_none():
    """_load_logo_b64 returns (None, 'png') when path does not exist."""
    from quirk.reports.html_renderer import _load_logo_b64
    b64, mime = _load_logo_b64("/nonexistent/path/logo.png")
    assert b64 is None
    assert mime == "png"


def test_logo_none_path_returns_none():
    """_load_logo_b64 returns (None, 'png') when logo_path is None."""
    from quirk.reports.html_renderer import _load_logo_b64
    b64, mime = _load_logo_b64(None)
    assert b64 is None
    assert mime == "png"


def test_logo_oversized_returns_none(tmp_path, monkeypatch, capsys):
    """_load_logo_b64 returns (None, 'png') and prints stderr advisory for oversized logo."""
    import os
    from quirk.reports import html_renderer
    # Monkeypatch the limit to 10 bytes so we don't need a truly large file
    monkeypatch.setattr(html_renderer, "_MAX_LOGO_BYTES", 10)
    # Write a file that exceeds the patched limit
    logo_file = str(tmp_path / "big_logo.png")
    with open(logo_file, "wb") as f:
        f.write(b"\x89PNG" + b"\x00" * 20)  # 24 bytes > 10 byte limit
    b64, mime = html_renderer._load_logo_b64(logo_file)
    assert b64 is None, "Expected None for oversized logo"
    assert mime == "png"
    captured = capsys.readouterr()
    assert "exceeds size limit" in captured.err, (
        f"Expected size-limit advisory in stderr; got: {captured.err!r}"
    )


def test_bridge_badge_label_maps_status_to_verbatim_labels():
    """_bridge_badge_label maps bridge_status -> UI-SPEC label, never the raw enum (BRIDGE-03)."""
    from quirk.reports.html_renderer import _bridge_badge_label

    assert _bridge_badge_label({"bridge_status": "partial_only"}) == "Partial (assumed)"
    assert _bridge_badge_label({"bridge_status": "upstream_mitigated"}) == "SNMP-confirmed"
    assert _bridge_badge_label({}) == ""
    assert _bridge_badge_label({"bridge_status": None}) == ""


def test_html_report_renders_scan_completed_timestamp(tmp_path):
    """SCORE-03 / D-16b (Phase 184.3): HTML report renders a zone-labeled scan
    instant, distinct from the report-generation instant, when provided."""
    from datetime import datetime
    from quirk.reports.html_renderer import render_html_report

    cfg = _make_minimal_cfg()
    scan_instant = datetime(2026, 9, 4, 15, 28, 56)
    out = str(tmp_path / "report-scan-completed.html")
    render_html_report(
        path=out, cfg=cfg, endpoints=[], findings=[],
        score={"total": 50, "subscores": {}, "drivers": []},
        conf={"confidence": 60, "confidence_factors": {}},
        roadmap_items=[],
        scan_completed_at=scan_instant,
    )
    content = open(out).read()
    scan_label = "2026-09-04 15:28 UTC"
    assert scan_label in content, "Expected formatted scan instant in HTML output"
    assert "Scan Completed" in content or "Scan completed" in content
    assert "Generated" in content


def test_html_report_scan_completed_timestamp_unknown_marker(tmp_path):
    """SCORE-03 / D-16b: a report with no derivable scan instant renders the
    explicit unknown marker, never the render (generated_at) time in its place."""
    from quirk.reports.html_renderer import render_html_report
    from quirk.reports.writer import SCAN_COMPLETED_AT_UNKNOWN

    cfg = _make_minimal_cfg()
    out = str(tmp_path / "report-scan-unknown.html")
    render_html_report(
        path=out, cfg=cfg, endpoints=[], findings=[],
        score={"total": 50, "subscores": {}, "drivers": []},
        conf={"confidence": 60, "confidence_factors": {}},
        roadmap_items=[],
        scan_completed_at=None,
    )
    content = open(out).read()
    assert SCAN_COMPLETED_AT_UNKNOWN in content


# Phase 184.4 D-05 / SCORE-04 / SCORE-05: severity-aware fallback band + cap-reason render.

def test_score_band_deleted_no_second_band_producer():
    """D-05: `_score_band()` must not exist on html_renderer — it was a second live band
    producer feeding the same congruence guard as `quirk/severity_bands.py`. If this
    assertion fails, someone reintroduced a severity-blind band helper here; route through
    `quirk/severity_bands.py` instead (band_for_score / cap_band_for_severity)."""
    import quirk.reports.html_renderer as html_renderer
    assert not hasattr(html_renderer, "_score_band"), (
        "_score_band() was a second live band producer feeding the same congruence guard "
        "as quirk/severity_bands.py and must not be reintroduced — route through "
        "quirk/severity_bands.py instead."
    )


def test_fallback_path_severity_aware_no_halt(tmp_path):
    """D-05: the exec_content=None (backward-compat) path must compute a severity-aware
    band BEFORE calling assert_congruent(), so a high score with an open CRITICAL finding
    no longer halts report generation on this route — the html_renderer-path twin of the
    D-13 regression. Pre-fix, this raised ReportCongruenceError."""
    from quirk.reports.html_renderer import render_html_report
    from quirk.reports.content_model import ReportCongruenceError

    cfg = _make_minimal_cfg()
    out = str(tmp_path / "report-fallback-critical.html")
    findings = [{"severity": "CRITICAL", "category": "cert_expired", "title": "TLS certificate expired"}]
    try:
        render_html_report(
            path=out, cfg=cfg, endpoints=[], findings=findings,
            score={"score": 89, "subscores": {}, "drivers": []},
            conf={"confidence": 80, "confidence_factors": {}},
            roadmap_items=[],
        )
    except ReportCongruenceError as exc:  # pragma: no cover - failure path
        pytest.fail(f"Fallback path halted on a severity-aware-capable band: {exc}")
    content = open(out).read()
    assert "FAIR" in content


def test_cap_reason_renders_when_capped_and_absent_when_not(tmp_path):
    """Presence-only assertion (this project's render tests assert field/column presence,
    not visual order — see 184.4-VALIDATION.md for the manual placement check). The
    cap-reason CSS class and reason string must appear for a capped render and must be
    absent for an uncapped one, so a renderer that always emits the block would fail."""
    from quirk.reports.html_renderer import render_html_report

    cfg = _make_minimal_cfg()

    capped_out = str(tmp_path / "report-capped.html")
    render_html_report(
        path=capped_out, cfg=cfg, endpoints=[],
        findings=[{"severity": "CRITICAL", "category": "cert_expired", "title": "TLS certificate expired"}],
        score={"score": 89, "subscores": {}, "drivers": []},
        conf={"confidence": 80, "confidence_factors": {}},
        roadmap_items=[],
    )
    capped_content = open(capped_out).read()
    assert 'class="score-cap-reason"' in capped_content
    assert "Band capped at FAIR" in capped_content

    uncapped_out = str(tmp_path / "report-uncapped.html")
    render_html_report(
        path=uncapped_out, cfg=cfg, endpoints=[], findings=[],
        score={"score": 89, "subscores": {}, "drivers": []},
        conf={"confidence": 80, "confidence_factors": {}},
        roadmap_items=[],
    )
    uncapped_content = open(uncapped_out).read()
    assert 'class="score-cap-reason"' not in uncapped_content
