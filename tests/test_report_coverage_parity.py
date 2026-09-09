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


# ---------------------------------------------------------------------------
# Task 3 — D-14 skip notes + three/four-surface parity gate
# ---------------------------------------------------------------------------


def _make_minimal_cfg_with_intelligence(tmpdir="/tmp/quirk_test_scan_coverage_parity"):
    return SimpleNamespace(
        assessment=SimpleNamespace(
            name="Scan Coverage Parity Test Org",
            report_owner="Parity Tester",
            data_classification="CONFIDENTIAL",
            timezone="UTC",
            logo_path=None,
        ),
        output=SimpleNamespace(directory=tmpdir),
        intelligence=SimpleNamespace(profile="balanced", calibration_overrides=None),
    )


def _coverage_with_tls_skipped(**overrides) -> dict:
    base = {
        "recorded": True,
        "ran": 1,
        "skipped": 1,
        "phases": [
            {
                "phase_name": "ssh_scanning",
                "label": "SSH",
                "status": "ran",
                "reason": None,
                "detail": None,
                "duration_sec": 1.1,
            },
            {
                "phase_name": "tls_scanning",
                "label": "TLS",
                "status": "skipped",
                "reason": "disabled-by-config",
                "detail": None,
                "duration_sec": None,
            },
        ],
    }
    base.update(overrides)
    return base


class TestD14SkipNotes:
    def test_technical_markdown_shows_tls_skip_note(self):
        from quirk.reports.technical import build_tech_markdown

        md = build_tech_markdown(
            _make_minimal_cfg(),
            [],
            [],
            coverage=_coverage_with_tls_skipped(),
        )
        assert "## TLS Capabilities" in md
        assert "Not assessed — skipped: disabled-by-config" in md

    def test_html_shows_tls_skip_note(self):
        from quirk.reports.html_renderer import render_tls_capabilities_skip_note

        html = render_tls_capabilities_skip_note(_coverage_with_tls_skipped())
        assert "TLS Capabilities" in html
        assert "Not assessed — skipped: disabled-by-config" in html

    def test_docx_shows_tls_skip_note(self, tmp_path):
        from docx import Document

        from quirk.reports.docx_renderer import render_docx_report

        path = str(tmp_path / "tls_skip.docx")
        ok = render_docx_report(
            path=path,
            cfg=_make_minimal_cfg(str(tmp_path)),
            findings=[],
            exec_content=_exec_content(coverage=_coverage_with_tls_skipped()),
        )
        assert ok is True
        doc = Document(path)
        headings = [p.text for p in doc.paragraphs if p.style.name.startswith("Heading")]
        assert "TLS Capabilities" in headings
        full_text = _docx_full_text(doc)
        assert "Not assessed — skipped: disabled-by-config" in full_text

    def test_all_three_surfaces_show_tls_skip_note(self, tmp_path):
        """The single behavior the plan's acceptance criteria names explicitly:
        'Not assessed — skipped: disabled-by-config' appears in all three surfaces
        for a skipped TLS phase."""
        from docx import Document

        from quirk.reports.docx_renderer import render_docx_report
        from quirk.reports.html_renderer import render_html_report
        from quirk.reports.technical import build_tech_markdown

        coverage = _coverage_with_tls_skipped()
        expected = "Not assessed — skipped: disabled-by-config"

        md = build_tech_markdown(_make_minimal_cfg(), [], [], coverage=coverage)
        assert expected in md

        html_path = str(tmp_path / "tls_skip_all3.html")
        render_html_report(
            path=html_path,
            cfg=_make_minimal_cfg(str(tmp_path)),
            endpoints=[],
            findings=[],
            score={"score": 70, "rating": "FAIR", "subscores": {}, "drivers": []},
            conf={"confidence": 0},
            roadmap_items=[],
            exec_content=_exec_content(coverage=coverage),
        )
        with open(html_path, encoding="utf-8") as f:
            html = f.read()
        assert expected in html

        docx_path = str(tmp_path / "tls_skip_all3.docx")
        render_docx_report(
            path=docx_path,
            cfg=_make_minimal_cfg(str(tmp_path)),
            findings=[],
            exec_content=_exec_content(coverage=coverage),
        )
        doc = Document(docx_path)
        assert expected in _docx_full_text(doc)

    def test_no_skip_note_anywhere_when_not_recorded(self, tmp_path):
        """T-192-30: an unrecorded scan must not license a per-domain skip claim,
        even if a caller mistakenly passes phase data alongside recorded=False."""
        from docx import Document

        from quirk.reports.docx_renderer import render_docx_report
        from quirk.reports.html_renderer import (
            render_html_report,
            render_tls_capabilities_skip_note,
        )
        from quirk.reports.technical import build_tech_markdown

        unrecorded_but_has_phases = {
            "recorded": False,
            "ran": 0,
            "skipped": 0,
            "phases": [
                {
                    "phase_name": "tls_scanning",
                    "label": "TLS",
                    "status": "skipped",
                    "reason": "disabled-by-config",
                    "detail": None,
                    "duration_sec": None,
                }
            ],
        }

        assert render_tls_capabilities_skip_note(unrecorded_but_has_phases) == ""

        md = build_tech_markdown(
            _make_minimal_cfg(), [], [], coverage=unrecorded_but_has_phases
        )
        assert "Not assessed — skipped:" not in md
        assert "## TLS Capabilities" not in md

        html_path = str(tmp_path / "tls_not_recorded.html")
        render_html_report(
            path=html_path,
            cfg=_make_minimal_cfg(str(tmp_path)),
            endpoints=[],
            findings=[],
            score={"score": 70, "rating": "FAIR", "subscores": {}, "drivers": []},
            conf={"confidence": 0},
            roadmap_items=[],
            exec_content=_exec_content(coverage=unrecorded_but_has_phases),
        )
        with open(html_path, encoding="utf-8") as f:
            html = f.read()
        assert "Not assessed — skipped:" not in html

        docx_path = str(tmp_path / "tls_not_recorded.docx")
        render_docx_report(
            path=docx_path,
            cfg=_make_minimal_cfg(str(tmp_path)),
            findings=[],
            exec_content=_exec_content(coverage=unrecorded_but_has_phases),
        )
        doc = Document(docx_path)
        assert "Not assessed — skipped:" not in _docx_full_text(doc)


class TestFourSurfaceCoverageParity:
    """Parity gate (Task 3): ran/skipped counts and the phase-label set must be
    identical across technical markdown, executive markdown, rendered HTML, and
    DOCX paragraph/table text for one fixed coverage payload. Derived values are
    compared (never one surface's raw string against another's)."""

    def _derive_markdown_counts_and_labels(self, md: str) -> tuple[int, int, set]:
        import re

        m = re.search(r"\*\*(\d+) ran / (\d+) skipped\*\*", md)
        assert m, f"coverage summary line not found in markdown:\n{md}"
        ran, skipped = int(m.group(1)), int(m.group(2))
        # Table rows live between the "| Phase | Status | Detail |" header and the
        # next blank line.
        lines = md.splitlines()
        start = lines.index("| Phase | Status | Detail |") + 2  # skip header + separator
        labels = set()
        for line in lines[start:]:
            if not line.startswith("|"):
                break
            cells = [c.strip() for c in line.strip("|").split("|")]
            labels.add(cells[0])
        return ran, skipped, labels

    def _derive_html_counts_and_labels(self, html: str) -> tuple[int, int, set]:
        import re

        section_match = re.search(
            r'<section class="scan-coverage-section".*?</section>', html, re.DOTALL
        )
        assert section_match, f"scan-coverage-section not found in HTML:\n{html}"
        section = section_match.group(0)
        m = re.search(r"(\d+) ran / (\d+) skipped", section)
        assert m, f"coverage summary not found in HTML section:\n{section}"
        ran, skipped = int(m.group(1)), int(m.group(2))
        rows = re.findall(r"<tr><td>(.*?)</td><td>", section)
        return ran, skipped, set(rows)

    def _derive_docx_counts_and_labels(self, doc) -> tuple[int, int, set]:
        import re

        text = _docx_full_text(doc)
        m = re.search(r"(\d+) ran / (\d+) skipped", text)
        assert m, f"coverage summary not found in DOCX:\n{text}"
        ran, skipped = int(m.group(1)), int(m.group(2))
        labels = set()
        for table in doc.tables:
            header_texts = [c.text for c in table.rows[0].cells]
            if header_texts == ["Phase", "Status", "Detail"]:
                for row in table.rows[1:]:
                    labels.add(row.cells[0].text)
        return ran, skipped, labels

    def test_ran_skipped_counts_and_labels_match_across_four_surfaces(self, tmp_path):
        from docx import Document

        from quirk.reports.docx_renderer import render_docx_report
        from quirk.reports.executive import build_exec_markdown
        from quirk.reports.html_renderer import render_html_report
        from quirk.reports.technical import build_tech_markdown

        coverage = _coverage()

        tech_md = build_tech_markdown(_make_minimal_cfg(), [], [], coverage=coverage)
        tech_ran, tech_skipped, tech_labels = self._derive_markdown_counts_and_labels(tech_md)

        exec_md = build_exec_markdown(
            _make_minimal_cfg_with_intelligence(), [], [], coverage=coverage
        )
        exec_ran, exec_skipped, exec_labels = self._derive_markdown_counts_and_labels(exec_md)

        html_path = str(tmp_path / "four_surface_parity.html")
        render_html_report(
            path=html_path,
            cfg=_make_minimal_cfg(str(tmp_path)),
            endpoints=[],
            findings=[],
            score={"score": 70, "rating": "FAIR", "subscores": {}, "drivers": []},
            conf={"confidence": 0},
            roadmap_items=[],
            exec_content=_exec_content(coverage=coverage),
        )
        with open(html_path, encoding="utf-8") as f:
            html = f.read()
        html_ran, html_skipped, html_labels = self._derive_html_counts_and_labels(html)

        docx_path = str(tmp_path / "four_surface_parity.docx")
        render_docx_report(
            path=docx_path,
            cfg=_make_minimal_cfg(str(tmp_path)),
            findings=[],
            exec_content=_exec_content(coverage=coverage),
        )
        doc = Document(docx_path)
        docx_ran, docx_skipped, docx_labels = self._derive_docx_counts_and_labels(doc)

        expected_ran, expected_skipped = coverage["ran"], coverage["skipped"]
        expected_labels = {p["label"] for p in coverage["phases"]}

        assert (tech_ran, tech_skipped) == (expected_ran, expected_skipped)
        assert (exec_ran, exec_skipped) == (expected_ran, expected_skipped)
        assert (html_ran, html_skipped) == (expected_ran, expected_skipped)
        assert (docx_ran, docx_skipped) == (expected_ran, expected_skipped)

        assert tech_labels == expected_labels
        assert exec_labels == expected_labels
        assert html_labels == expected_labels
        assert docx_labels == expected_labels

    def test_absence_parity_no_data_row_anywhere(self, tmp_path):
        from docx import Document

        from quirk.reports.coverage import COVERAGE_NOT_RECORDED_NOTICE
        from quirk.reports.docx_renderer import render_docx_report
        from quirk.reports.executive import build_exec_markdown
        from quirk.reports.html_renderer import render_html_report
        from quirk.reports.technical import build_tech_markdown

        coverage = {}

        tech_md = build_tech_markdown(_make_minimal_cfg(), [], [], coverage=coverage)
        exec_md = build_exec_markdown(
            _make_minimal_cfg_with_intelligence(), [], [], coverage=coverage
        )

        html_path = str(tmp_path / "four_surface_absence.html")
        render_html_report(
            path=html_path,
            cfg=_make_minimal_cfg(str(tmp_path)),
            endpoints=[],
            findings=[],
            score={"score": 70, "rating": "FAIR", "subscores": {}, "drivers": []},
            conf={"confidence": 0},
            roadmap_items=[],
            exec_content=_exec_content(coverage=coverage),
        )
        with open(html_path, encoding="utf-8") as f:
            html = f.read()

        docx_path = str(tmp_path / "four_surface_absence.docx")
        render_docx_report(
            path=docx_path,
            cfg=_make_minimal_cfg(str(tmp_path)),
            findings=[],
            exec_content=_exec_content(coverage=coverage),
        )
        doc = Document(docx_path)
        docx_text = _docx_full_text(doc)

        for surface_name, surface_text in [
            ("technical", tech_md),
            ("executive", exec_md),
            ("html", html),
            ("docx", docx_text),
        ]:
            assert COVERAGE_NOT_RECORDED_NOTICE in surface_text, surface_name
            assert "| Phase | Status | Detail |" not in surface_text, surface_name
