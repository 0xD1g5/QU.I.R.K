"""Phase 192 Plan 08 (OBS-02) — three-surface parity gate for the "Scan Coverage"

section across CLI technical markdown, executive markdown, HTML, and DOCX, plus
D-14's per-domain skip notes.

D-15 / INVERTED CONTRACT: unlike render_key_reuse_section / render_burndown_section,
which return "" (or omit their table) when their payload is entirely absent, the
Scan Coverage section ALWAYS renders — a pre-v5.21 scan with no recorded coverage
rows states that absence explicitly rather than vanishing. Every test below that
checks the "not recorded" branch asserts the heading IS present and no table is.

Follows tests/test_key_reuse_render_parity.py's fixture/assertion conventions
(minimal cfg via SimpleNamespace, ExecContent construction, paragraph/table text
helpers for DOCX) per this plan's <action> instruction to reuse existing
conventions rather than inventing new ones.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

# Auto-allowed by the skip-registry gate for a declared optional extra
# (pyproject.toml `[docx]` extra) — matching test_key_reuse_render_parity.py's
# `pytest.importorskip("docx")` convention. Gates every DOCX-leg test below.
pytest.importorskip("docx")


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


def _coverage(**overrides) -> dict:
    base = {
        "recorded": True,
        "ran": 2,
        "skipped": 1,
        "phases": [
            {
                "phase_name": "tls_scanning",
                "label": "TLS",
                "status": "ran",
                "reason": None,
                "detail": None,
                "duration_sec": 3.2,
            },
            {
                "phase_name": "ssh_scanning",
                "label": "SSH",
                "status": "ran",
                "reason": None,
                "detail": None,
                "duration_sec": 1.1,
            },
            {
                "phase_name": "jwt_scanning",
                "label": "JWT",
                "status": "skipped",
                "reason": "disabled-by-config",
                "detail": "enable_jwt=false",
                "duration_sec": None,
            },
        ],
    }
    base.update(overrides)
    return base


def _not_recorded_coverage() -> dict:
    return {}


def _make_minimal_cfg(tmpdir="/tmp/quirk_test_scan_coverage_parity"):
    return SimpleNamespace(
        assessment=SimpleNamespace(
            name="Scan Coverage Parity Test Org",
            report_owner="Parity Tester",
            data_classification="CONFIDENTIAL",
            timezone="UTC",
            logo_path=None,
        ),
        output=SimpleNamespace(directory=tmpdir),
    )


def _exec_content(coverage=None):
    from quirk.reports.content_model import ExecContent

    return ExecContent(
        narrative_lead="Test narrative lead.",
        narrative_drivers=[],
        top_risks=[],
        roadmap_items=[],
        score_total=70,
        score_band="FAIR",
        subscores={},
        raw_sum=0,
        sev_counts={},
        coverage=coverage if coverage is not None else {},
    )


def _all_paragraph_texts(doc):
    return [p.text for p in doc.paragraphs]


def _all_table_texts(doc):
    cells = []
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                cells.append(cell.text)
    return cells


def _docx_full_text(doc) -> str:
    return "\n".join(_all_paragraph_texts(doc) + _all_table_texts(doc))


# ---------------------------------------------------------------------------
# Task 1 — HTML-specific behaviors
# ---------------------------------------------------------------------------


class TestHtmlScanCoverageSection:
    def test_recorded_payload_renders_heading_summary_and_rows(self):
        from quirk.reports.html_renderer import render_scan_coverage_section

        html = render_scan_coverage_section(_coverage())
        assert "<h2" in html and "Scan Coverage" in html
        assert "2 ran / 1 skipped" in html
        assert "TLS" in html
        assert "SSH" in html
        assert "JWT" in html

    def test_empty_dict_renders_not_recorded_notice_no_table(self):
        from quirk.reports.coverage import COVERAGE_NOT_RECORDED_NOTICE
        from quirk.reports.html_renderer import render_scan_coverage_section

        html = render_scan_coverage_section({})
        assert "Scan Coverage" in html
        assert COVERAGE_NOT_RECORDED_NOTICE in html
        assert "<table" not in html

    def test_none_renders_not_recorded_notice_no_table(self):
        from quirk.reports.coverage import COVERAGE_NOT_RECORDED_NOTICE
        from quirk.reports.html_renderer import render_scan_coverage_section

        html = render_scan_coverage_section(None)
        assert "Scan Coverage" in html
        assert COVERAGE_NOT_RECORDED_NOTICE in html
        assert "<table" not in html

    def test_xss_shaped_detail_is_escaped(self):
        from quirk.reports.html_renderer import render_scan_coverage_section

        payload = _coverage()
        payload["phases"][2]["detail"] = "<script>alert(1)</script>"
        html = render_scan_coverage_section(payload)
        assert "<script>" not in html

    def test_section_precedes_readiness_assessment_in_full_report(self, tmp_path):
        from quirk.reports.html_renderer import render_html_report

        cfg = _make_minimal_cfg(str(tmp_path))
        path = str(tmp_path / "scan_coverage_report.html")
        render_html_report(
            path=path,
            cfg=cfg,
            endpoints=[],
            findings=[],
            score={"score": 70, "rating": "FAIR", "subscores": {}, "drivers": []},
            conf={"confidence": 0},
            roadmap_items=[],
            exec_content=_exec_content(coverage=_coverage()),
        )
        with open(path, encoding="utf-8") as f:
            html = f.read()
        idx_coverage = html.find("Scan Coverage")
        idx_readiness = html.find("Readiness Assessment")
        assert idx_coverage != -1
        assert idx_readiness != -1
        assert idx_coverage < idx_readiness


# ---------------------------------------------------------------------------
# Task 2 — DOCX-specific behaviors
# ---------------------------------------------------------------------------


class TestDocxScanCoverageSection:
    def test_recorded_payload_heading_and_table(self, tmp_path):
        from docx import Document

        from quirk.reports.docx_renderer import render_docx_report

        path = str(tmp_path / "scan_coverage.docx")
        cfg = _make_minimal_cfg(str(tmp_path))
        ok = render_docx_report(
            path=path,
            cfg=cfg,
            findings=[],
            exec_content=_exec_content(coverage=_coverage()),
        )
        assert ok is True
        doc = Document(path)
        headings = [p.text for p in doc.paragraphs if p.style.name.startswith("Heading")]
        assert "Scan Coverage" in headings
        full_text = _docx_full_text(doc)
        assert "TLS" in full_text
        assert "JWT" in full_text
        # A coverage table with a header row plus 3 phase rows exists.
        found_table = False
        for table in doc.tables:
            header_texts = [c.text for c in table.rows[0].cells]
            if header_texts == ["Phase", "Status", "Detail"]:
                found_table = True
                assert len(table.rows) == 1 + len(_coverage()["phases"])
        assert found_table

    def test_absent_coverage_heading_present_no_table(self, tmp_path):
        from docx import Document

        from quirk.reports.coverage import COVERAGE_NOT_RECORDED_NOTICE
        from quirk.reports.docx_renderer import render_docx_report

        path = str(tmp_path / "scan_coverage_absent.docx")
        cfg = _make_minimal_cfg(str(tmp_path))
        ok = render_docx_report(
            path=path,
            cfg=cfg,
            findings=[],
            exec_content=_exec_content(coverage={}),
        )
        assert ok is True
        doc = Document(path)
        headings = [p.text for p in doc.paragraphs if p.style.name.startswith("Heading")]
        assert "Scan Coverage" in headings
        full_text = _docx_full_text(doc)
        assert COVERAGE_NOT_RECORDED_NOTICE in full_text
        for table in doc.tables:
            header_texts = [c.text for c in table.rows[0].cells]
            assert header_texts != ["Phase", "Status", "Detail"]

    def test_heading_order_between_executive_summary_and_readiness_assessment(self, tmp_path):
        from docx import Document

        from quirk.reports.docx_renderer import render_docx_report

        path = str(tmp_path / "scan_coverage_order.docx")
        cfg = _make_minimal_cfg(str(tmp_path))
        ok = render_docx_report(
            path=path,
            cfg=cfg,
            findings=[],
            exec_content=_exec_content(coverage=_coverage()),
        )
        assert ok is True
        doc = Document(path)
        headings = [p.text for p in doc.paragraphs if p.style.name.startswith("Heading")]
        idx_exec = headings.index("Executive Summary")
        idx_coverage = headings.index("Scan Coverage")
        idx_readiness = headings.index("Readiness Assessment")
        assert idx_exec < idx_coverage < idx_readiness
