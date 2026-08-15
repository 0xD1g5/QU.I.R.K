"""Phase 156 (HWLC-10/HWLC-11 / D-11 / D-13 / T-156-04 / T-156-13) — DOCX
"Recent Lifecycle Changes" drift section tests.

Mirrors tests/test_docx_report.py's Document-open + text-readback idiom.
"""
from __future__ import annotations

from types import SimpleNamespace


def _make_minimal_cfg():
    return SimpleNamespace(
        assessment=SimpleNamespace(
            name="Drift Test Org",
            report_owner="Drift Tester",
            data_classification="CONFIDENTIAL",
            timezone="UTC",
            logo_path=None,
        ),
        output=SimpleNamespace(directory="/tmp/quirk_test_docx_drift"),
    )


def _base_exec_content(hardware_drift_events):
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
        hardware_drift_events=hardware_drift_events,
    )


def _base_event(**overrides) -> dict:
    event = {
        "host": "10.20.30.5",
        "port": 502,
        "event_type": "tier_crossing",
        "old_value": "Tier 2",
        "new_value": "Tier 1",
        "direction": "worsened",
        "detected_at": "2026-08-14",
        "vendor": "Schneider Electric",
        "model": "M221",
    }
    event.update(overrides)
    return event


def _all_paragraph_texts(doc):
    return [p.text for p in doc.paragraphs]


def test_docx_drift_section_advisory_caption_unconditional(tmp_path):
    from docx import Document
    from quirk.reports.docx_renderer import render_docx_report, _DRIFT_ADVISORY_CAPTION

    path = str(tmp_path / "drift.docx")
    exec_content = _base_exec_content([_base_event()])
    result = render_docx_report(path=path, cfg=_make_minimal_cfg(), findings=[], exec_content=exec_content)
    assert result is True

    doc = Document(path)
    texts = _all_paragraph_texts(doc)
    assert _DRIFT_ADVISORY_CAPTION in texts
    assert "Advisory — hardware lifecycle changes do not affect the readiness score." in texts


def test_docx_drift_section_heading_present(tmp_path):
    from docx import Document
    from quirk.reports.docx_renderer import render_docx_report

    path = str(tmp_path / "drift_heading.docx")
    exec_content = _base_exec_content([_base_event()])
    render_docx_report(path=path, cfg=_make_minimal_cfg(), findings=[], exec_content=exec_content)

    doc = Document(path)
    headings = [p.text for p in doc.paragraphs if p.style.name.startswith("Heading")]
    assert "Recent Lifecycle Changes" in headings


def test_docx_drift_table_has_header_plus_one_row_per_event(tmp_path):
    from docx import Document
    from quirk.reports.docx_renderer import render_docx_report

    path = str(tmp_path / "drift_table.docx")
    events = [_base_event(), _base_event(host="10.20.30.6", event_type="cve_delta", direction="neutral")]
    exec_content = _base_exec_content(events)
    render_docx_report(path=path, cfg=_make_minimal_cfg(), findings=[], exec_content=exec_content)

    doc = Document(path)
    # Find the drift table by its header row.
    drift_tables = [
        t for t in doc.tables
        if t.rows[0].cells[0].text == "Device"
    ]
    assert len(drift_tables) == 1
    tbl = drift_tables[0]
    assert len(tbl.rows) == 1 + len(events)
    header_texts = [c.text for c in tbl.rows[0].cells]
    assert header_texts == ["Device", "Change", "Transition", "Direction", "Detected"]


def test_docx_drift_table_escapes_script_as_literal_text(tmp_path):
    from docx import Document
    from quirk.reports.docx_renderer import render_docx_report

    path = str(tmp_path / "drift_script.docx")
    event = _base_event(old_value="<script>alert(1)</script>", new_value="Tier 1")
    exec_content = _base_exec_content([event])
    result = render_docx_report(path=path, cfg=_make_minimal_cfg(), findings=[], exec_content=exec_content)
    assert result is True

    doc = Document(path)
    drift_tables = [t for t in doc.tables if t.rows[0].cells[0].text == "Device"]
    assert len(drift_tables) == 1
    transition_cell_text = drift_tables[0].rows[1].cells[2].text
    assert "<script>alert(1)</script>" in transition_cell_text


def test_docx_no_drift_section_when_events_empty(tmp_path):
    from docx import Document
    from quirk.reports.docx_renderer import render_docx_report

    path = str(tmp_path / "no_drift.docx")
    exec_content = _base_exec_content([])
    render_docx_report(path=path, cfg=_make_minimal_cfg(), findings=[], exec_content=exec_content)

    doc = Document(path)
    texts = _all_paragraph_texts(doc)
    assert not any("Recent Lifecycle Changes" in t for t in texts)
    assert not any(t.rows[0].cells[0].text == "Device" for t in doc.tables)
