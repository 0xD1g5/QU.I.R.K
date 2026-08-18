"""Phase 157 (HWLC-18 / D-04 / D-05) — CLI/markdown "EOL/Tier Forecast" subsection
tests for quirk.reports.executive.build_exec_markdown.

This is a NET-NEW subsection: executive.py has no "Recent Lifecycle Changes"
section to extend (Phase 156 D-12 deliberately deferred CLI drift rendering).
The forecast block is a sibling of the "### Hardware PQC Advisory" block,
gated on exec_content.eol_forecast alone (independently suppressible from the
Hardware PQC Advisory block).

Node IDs:
  test_cli_forecast_subsection_present
  test_cli_forecast_absent_when_empty
  test_cli_forecast_is_separate_from_hardware_pqc_advisory
  test_cli_forecast_renders_without_exec_content
  test_cli_forecast_carries_advisory_qualifier
  test_cli_forecast_surfaces_stale_catalog
"""
from __future__ import annotations

from types import SimpleNamespace

from quirk.reports.content_model import ExecContent


def _make_minimal_cfg():
    return SimpleNamespace(
        assessment=SimpleNamespace(
            name="Forecast Test Org",
            report_owner="Forecast Tester",
            data_classification="CONFIDENTIAL",
            timezone="UTC",
            logo_path=None,
        ),
        output=SimpleNamespace(directory="/tmp/quirk_test_executive_forecast"),
        intelligence=SimpleNamespace(
            profile="balanced",
            calibration_overrides=None,
        ),
    )


def _two_bucket_forecast(**overrides):
    forecast = {
        "narrative": "Projected EOL/tier posture over the next 12 months.",
        "buckets": [
            {
                "label": "0-6 months",
                "count": 2,
                "tier_counts": {"Tier 1": 2},
                "sentence": "2 device(s) reach EOL or a worse CNSA 2.0 tier within 0-6 months.",
            },
            {
                "label": "7-12 months",
                "count": 1,
                "tier_counts": {"Tier 2": 1},
                "sentence": "1 device(s) reach EOL or a worse CNSA 2.0 tier within 7-12 months.",
            },
        ],
        "catalog_last_verified": "2026-05-01",
        "catalog_stale": False,
        "total_devices_with_eol": 3,
    }
    forecast.update(overrides)
    return forecast


def _base_exec_content(eol_forecast, hardware_devices=None):
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
        hardware_devices=hardware_devices or [],
        eol_forecast=eol_forecast,
    )


def test_cli_forecast_subsection_present():
    from quirk.reports.executive import build_exec_markdown

    exec_content = _base_exec_content(_two_bucket_forecast())
    output = build_exec_markdown(
        cfg=_make_minimal_cfg(), endpoints=[], findings=[], exec_content=exec_content
    )

    assert "### EOL/Tier Forecast" in output
    assert "2 device(s) reach EOL or a worse CNSA 2.0 tier within 0-6 months." in output
    assert "1 device(s) reach EOL or a worse CNSA 2.0 tier within 7-12 months." in output


def test_cli_forecast_absent_when_empty():
    from quirk.reports.executive import build_exec_markdown

    for empty_forecast in ({}, {"narrative": "", "buckets": []}):
        exec_content = _base_exec_content(empty_forecast)
        output = build_exec_markdown(
            cfg=_make_minimal_cfg(), endpoints=[], findings=[], exec_content=exec_content
        )
        assert "EOL/Tier Forecast" not in output


def test_cli_forecast_is_separate_from_hardware_pqc_advisory():
    from quirk.reports.executive import build_exec_markdown

    hardware_devices = [
        {"remediation_tier": "Tier 1"},
        {"remediation_tier": "Tier 2"},
    ]
    exec_content = _base_exec_content(_two_bucket_forecast(), hardware_devices=hardware_devices)
    output = build_exec_markdown(
        cfg=_make_minimal_cfg(), endpoints=[], findings=[], exec_content=exec_content
    )

    assert "### Hardware PQC Advisory" in output
    assert "### EOL/Tier Forecast" in output

    forecast_idx = output.index("### EOL/Tier Forecast")
    advisory_idx = output.index("### Hardware PQC Advisory")
    forecast_sentence = "2 device(s) reach EOL or a worse CNSA 2.0 tier within 0-6 months."
    sentence_idx = output.index(forecast_sentence)

    assert sentence_idx > forecast_idx
    # The forecast sentence must not appear inside the Hardware PQC Advisory
    # paragraph range (i.e., before the forecast heading).
    assert not (advisory_idx < sentence_idx < forecast_idx)


def test_cli_forecast_renders_without_exec_content():
    from quirk.reports.executive import build_exec_markdown

    output = build_exec_markdown(
        cfg=_make_minimal_cfg(), endpoints=[], findings=[], exec_content=None
    )

    assert "EOL/Tier Forecast" not in output


def test_cli_forecast_carries_advisory_qualifier():
    from quirk.reports.executive import build_exec_markdown

    exec_content = _base_exec_content(_two_bucket_forecast())
    output = build_exec_markdown(
        cfg=_make_minimal_cfg(), endpoints=[], findings=[], exec_content=exec_content
    )

    forecast_idx = output.index("### EOL/Tier Forecast")
    assert "Advisory only — not included in readiness score." in output[forecast_idx:]


def test_cli_forecast_surfaces_stale_catalog():
    from quirk.reports.executive import build_exec_markdown

    stale_forecast = _two_bucket_forecast(catalog_stale=True, catalog_last_verified="2025-01-01")
    exec_content_stale = _base_exec_content(stale_forecast)
    output_stale = build_exec_markdown(
        cfg=_make_minimal_cfg(), endpoints=[], findings=[], exec_content=exec_content_stale
    )
    assert "2025-01-01" in output_stale

    fresh_forecast = _two_bucket_forecast(catalog_stale=False, catalog_last_verified="2025-01-01")
    exec_content_fresh = _base_exec_content(fresh_forecast)
    output_fresh = build_exec_markdown(
        cfg=_make_minimal_cfg(), endpoints=[], findings=[], exec_content=exec_content_fresh
    )
    assert "2025-01-01" not in output_fresh


# ---------------------------------------------------------------------------
# Phase 159 HWLC-13/D-159-M/O: always-visible "partial re-probe" banner inside
# the existing Hardware PQC Advisory block. No new CLI drift section — Phase
# 156 D-12 stands, verified by the "no Recent Lifecycle Changes heading" assert
# below so a future executor cannot satisfy the banner via the deferred section.
# ---------------------------------------------------------------------------


def test_cli_hardware_advisory_checkin_shows_banner():
    from quirk.reports.executive import build_exec_markdown

    hardware_devices = [{"remediation_tier": "Tier 1", "is_partial_scan": True}]
    exec_content = _base_exec_content({}, hardware_devices=hardware_devices)
    output = build_exec_markdown(
        cfg=_make_minimal_cfg(), endpoints=[], findings=[], exec_content=exec_content
    )

    assert "### Hardware PQC Advisory" in output
    assert "Partial re-probe — check-in scan; not a full assessment." in output
    assert "Recent Lifecycle Changes" not in output


def test_cli_hardware_advisory_no_checkin_omits_banner():
    from quirk.reports.executive import build_exec_markdown

    hardware_devices = [{"remediation_tier": "Tier 1", "is_partial_scan": False}]
    exec_content = _base_exec_content({}, hardware_devices=hardware_devices)
    output = build_exec_markdown(
        cfg=_make_minimal_cfg(), endpoints=[], findings=[], exec_content=exec_content
    )

    assert "### Hardware PQC Advisory" in output
    assert "Partial re-probe — check-in scan; not a full assessment." not in output


def test_cli_hardware_advisory_checkin_empty_devices_omits_heading_and_banner():
    from quirk.reports.executive import build_exec_markdown

    exec_content = _base_exec_content({}, hardware_devices=[])
    output = build_exec_markdown(
        cfg=_make_minimal_cfg(), endpoints=[], findings=[], exec_content=exec_content
    )

    assert "### Hardware PQC Advisory" not in output
    assert "Partial re-probe — check-in scan; not a full assessment." not in output
