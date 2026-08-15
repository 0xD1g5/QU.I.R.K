"""Phase 156 (HWLC-10/HWLC-11 / D-11 / D-13 / T-156-04 / T-156-13) — presence tests
for the "Recent Lifecycle Changes" drift section in quirk.reports.html_renderer.

Exercises render_drift_section() with synthetic drift-event dicts (the plain-dict
shape ExecContent.hardware_drift_events carries — see content_model.py). Presence
assertions only, per this project's render-tests-assert-presence convention
(feedback_report_render_tests_presence_not_appearance).
"""
from __future__ import annotations


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


def test_render_drift_section_empty_list_returns_empty_string() -> None:
    from quirk.reports.html_renderer import render_drift_section

    assert render_drift_section([]) == ""


def test_render_drift_section_advisory_caption_present() -> None:
    from quirk.reports.html_renderer import render_drift_section, DRIFT_ADVISORY_CAPTION

    html = render_drift_section([_base_event()])

    assert DRIFT_ADVISORY_CAPTION in html
    assert "Advisory — hardware lifecycle changes do not affect the readiness score." in html


def test_render_drift_section_heading_and_labels_present() -> None:
    from quirk.reports.html_renderer import render_drift_section

    html = render_drift_section([_base_event()])

    assert "Recent Lifecycle Changes" in html
    assert "Tier crossing" in html
    assert "Worsened" in html


def test_render_drift_section_all_event_type_labels() -> None:
    from quirk.reports.html_renderer import render_drift_section

    events = [
        _base_event(event_type="tier_crossing"),
        _base_event(event_type="upstream_mitigated_change", direction="neutral"),
        _base_event(event_type="cve_delta", direction="neutral"),
        _base_event(event_type="eol_state_change", direction="neutral"),
    ]
    html = render_drift_section(events)

    assert "Tier crossing" in html
    assert "Bridge mitigation change" in html
    assert "CVE correlation change" in html
    assert "EOL/EOS state change" in html


def test_render_drift_section_neutral_direction_label_is_changed() -> None:
    from quirk.reports.html_renderer import render_drift_section

    html = render_drift_section([_base_event(direction="neutral")])

    assert "Changed" in html


def test_render_drift_section_escapes_script_payload() -> None:
    from quirk.reports.html_renderer import render_drift_section

    event = _base_event(old_value="<script>alert(1)</script>", new_value="Tier 1")
    html = render_drift_section([event])

    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_render_drift_section_caption_not_inside_details() -> None:
    from quirk.reports.html_renderer import render_drift_section

    html = render_drift_section([_base_event()])

    # The caption must be its own always-visible <p>, never collapsed inside <details>.
    assert "<details" not in html
    assert "display:none" not in html.replace(" ", "")


def test_render_drift_section_no_tier_hue_reuse() -> None:
    from quirk.reports.html_renderer import render_drift_section

    html = render_drift_section([_base_event()])

    # D-07 layer 2: must not reuse render_hardware_section's TIER_COLORS hex literals.
    assert "#dc2626" not in html
    assert "#ea580c" not in html
    assert "#3b82f6" not in html


def test_full_html_report_contains_drift_advisory_caption() -> None:
    """The full render_html_report() path surfaces the caption when
    exec_content.hardware_drift_events is populated (template slot wiring)."""
    from types import SimpleNamespace
    from quirk.reports.content_model import ExecContent
    from quirk.reports.html_renderer import render_html_report, DRIFT_ADVISORY_CAPTION

    cfg = SimpleNamespace(
        assessment=SimpleNamespace(
            name="Drift Test Org",
            report_owner="Drift Tester",
            data_classification="CONFIDENTIAL",
            timezone="UTC",
            logo_path=None,
        ),
        output=SimpleNamespace(directory="/tmp/quirk_test_html_drift"),
    )
    import os
    os.makedirs(cfg.output.directory, exist_ok=True)
    out = os.path.join(cfg.output.directory, "report-drift.html")

    exec_content = ExecContent(
        narrative_lead="Test narrative lead.",
        narrative_drivers=[],
        top_risks=[],
        roadmap_items=[],
        score_total=70,
        score_band="FAIR",
        subscores={},
        raw_sum=0,
        sev_counts={},
        hardware_drift_events=[_base_event()],
    )

    render_html_report(
        path=out, cfg=cfg, endpoints=[], findings=[],
        score={"total": 70, "subscores": {}, "drivers": []},
        conf={"confidence": 70, "confidence_factors": {}},
        roadmap_items=[],
        exec_content=exec_content,
    )
    content = open(out).read()
    assert DRIFT_ADVISORY_CAPTION in content
    assert "Recent Lifecycle Changes" in content


def test_full_html_report_omits_drift_section_when_no_events() -> None:
    """A project with zero drift events omits the section cleanly."""
    from types import SimpleNamespace
    from quirk.reports.content_model import ExecContent
    from quirk.reports.html_renderer import render_html_report, DRIFT_ADVISORY_CAPTION

    cfg = SimpleNamespace(
        assessment=SimpleNamespace(
            name="Drift Test Org",
            report_owner="Drift Tester",
            data_classification="CONFIDENTIAL",
            timezone="UTC",
            logo_path=None,
        ),
        output=SimpleNamespace(directory="/tmp/quirk_test_html_drift"),
    )
    import os
    os.makedirs(cfg.output.directory, exist_ok=True)
    out = os.path.join(cfg.output.directory, "report-nodrift.html")

    exec_content = ExecContent(
        narrative_lead="Test narrative lead.",
        narrative_drivers=[],
        top_risks=[],
        roadmap_items=[],
        score_total=70,
        score_band="FAIR",
        subscores={},
        raw_sum=0,
        sev_counts={},
        hardware_drift_events=[],
    )

    render_html_report(
        path=out, cfg=cfg, endpoints=[], findings=[],
        score={"total": 70, "subscores": {}, "drivers": []},
        conf={"confidence": 70, "confidence_factors": {}},
        roadmap_items=[],
        exec_content=exec_content,
    )
    content = open(out).read()
    assert DRIFT_ADVISORY_CAPTION not in content
    assert "Recent Lifecycle Changes" not in content
