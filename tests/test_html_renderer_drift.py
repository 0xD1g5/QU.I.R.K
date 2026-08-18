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


def _base_device(**overrides) -> dict:
    device = {
        "host": "10.0.0.5",
        "port": 22,
        "vendor": "Schneider Electric",
        "model": "M221",
        "pqc_status": "unsupported",
        "confidence": "high",
        "eol_date": None,
        "remediation_tier": "Tier 1",
    }
    device.update(overrides)
    return device


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


# ---------------------------------------------------------------------------
# Phase 157 (HWLC-18) — EOL/Tier forecast subsection
# ---------------------------------------------------------------------------
# Fixtures below are literal dicts matching Plan 02's build_eol_forecast()
# contract; these tests do not call build_eol_forecast() itself — that
# coupling belongs to tests/test_hardware_forecast.py.


def _base_forecast(**overrides) -> dict:
    forecast = {
        "narrative": (
            "2 devices (2 Tier 2) are projected to reach vendor end-of-life "
            "within 0-3 months, based on vendor-published dates verified as "
            "of 2026-01-01. 1 device (1 Tier 1) is projected to reach vendor "
            "end-of-life within 6-12 months, based on vendor-published dates "
            "verified as of 2026-01-01."
        ),
        "buckets": [
            {
                "label": "0-3 months",
                "count": 2,
                "tier_counts": {"Tier 2": 2},
                "sentence": (
                    "2 devices (2 Tier 2) are projected to reach vendor "
                    "end-of-life within 0-3 months, based on vendor-published "
                    "dates verified as of 2026-01-01."
                ),
            },
            {
                "label": "6-12 months",
                "count": 1,
                "tier_counts": {"Tier 1": 1},
                "sentence": (
                    "1 device (1 Tier 1) is projected to reach vendor "
                    "end-of-life within 6-12 months, based on vendor-published "
                    "dates verified as of 2026-01-01."
                ),
            },
        ],
        "catalog_last_verified": "2026-01-01",
        "catalog_stale": False,
        "total_devices_with_eol": 3,
    }
    forecast.update(overrides)
    return forecast


def test_forecast_subsection_present() -> None:
    from quirk.reports.html_renderer import render_eol_forecast_section

    forecast = _base_forecast()
    html = render_eol_forecast_section(forecast)

    assert "EOL/Tier Forecast" in html
    for bucket in forecast["buckets"]:
        assert bucket["sentence"] in html


def test_forecast_section_empty_when_no_buckets() -> None:
    from quirk.reports.html_renderer import render_eol_forecast_section

    assert render_eol_forecast_section({"narrative": "", "buckets": [], "catalog_last_verified": "2026-01-01", "catalog_stale": False, "total_devices_with_eol": 0}) == ""
    assert render_eol_forecast_section({}) == ""


def test_forecast_renders_with_zero_drift_events() -> None:
    from quirk.reports.html_renderer import render_drift_section, render_eol_forecast_section

    drift_html = render_drift_section([])
    forecast_html = render_eol_forecast_section(_base_forecast())

    assert drift_html == ""
    assert forecast_html != ""


def test_forecast_section_is_distinct_from_drift_list() -> None:
    from quirk.reports.html_renderer import render_eol_forecast_section

    html = render_eol_forecast_section(_base_forecast())

    assert "<table" not in html
    assert "Recent Lifecycle Changes" not in html


def test_forecast_section_escapes_untrusted_text() -> None:
    from quirk.reports.html_renderer import render_eol_forecast_section

    forecast = _base_forecast(
        buckets=[
            {
                "label": "0-3 months",
                "count": 1,
                "tier_counts": {"Tier 1": 1},
                "sentence": "1 device <script>alert(1)</script> is projected to reach EOL.",
            }
        ],
    )
    html = render_eol_forecast_section(forecast)

    assert "<script" not in html
    assert "&lt;script&gt;" in html


def test_forecast_section_surfaces_stale_catalog() -> None:
    from quirk.reports.html_renderer import render_eol_forecast_section

    stale_html = render_eol_forecast_section(_base_forecast(catalog_stale=True))
    fresh_html = render_eol_forecast_section(_base_forecast(catalog_stale=False))

    assert "2026-01-01" in stale_html
    # A staleness qualifier phrase should appear only when catalog_stale is True.
    assert stale_html != fresh_html
    stale_only_fragment = stale_html.replace(fresh_html, "")
    assert stale_only_fragment.strip() != "" or "stale" in stale_html.lower() or "not been re-verified" in stale_html.lower()


# ---------------------------------------------------------------------------
# Phase 159 HWLC-13/D-159-M/N/P: always-visible "partial re-probe" banner.
# Import the banner constant rather than retyping the literal, so a future
# copy change cannot silently pass a stale assertion.
# ---------------------------------------------------------------------------


def test_render_drift_section_checkin_shows_banner() -> None:
    from quirk.reports.html_renderer import render_drift_section, PARTIAL_SCAN_BANNER

    html = render_drift_section([_base_event(is_partial_scan=True)])

    assert PARTIAL_SCAN_BANNER in html


def test_render_drift_section_no_checkin_omits_banner() -> None:
    from quirk.reports.html_renderer import render_drift_section, PARTIAL_SCAN_BANNER

    html = render_drift_section([_base_event(is_partial_scan=False)])

    assert PARTIAL_SCAN_BANNER not in html


def test_render_hardware_section_checkin_shows_banner_before_details() -> None:
    from quirk.reports.html_renderer import render_hardware_section, PARTIAL_SCAN_BANNER

    html = render_hardware_section([_base_device(is_partial_scan=True)])

    assert PARTIAL_SCAN_BANNER in html
    # D-159-N: always visible — banner must precede <details>, never inside it.
    assert html.index(PARTIAL_SCAN_BANNER) < html.index("<details")


def test_render_hardware_section_no_checkin_omits_banner() -> None:
    from quirk.reports.html_renderer import render_hardware_section, PARTIAL_SCAN_BANNER

    html = render_hardware_section([_base_device(is_partial_scan=False)])

    assert PARTIAL_SCAN_BANNER not in html
