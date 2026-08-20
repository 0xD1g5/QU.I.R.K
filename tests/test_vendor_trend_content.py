"""Tests for Phase 161 HWLC-19: vendor PQC trend content surfacing.

Covers:
  - build_tech_markdown()'s new keyword-only `vendor_pqc_trends` section
    (quirk/reports/technical.py)
  - writer.py's `_load_vendor_pqc_trends()` loader (Task 3)
"""
from types import SimpleNamespace

from quirk.reports.technical import build_tech_markdown, VENDOR_TREND_ADVISORY_CAPTION


def _cfg():
    return SimpleNamespace(assessment=SimpleNamespace(name="Acme Corp"))


def test_build_tech_markdown_backward_compatible_three_args():
    """build_tech_markdown(cfg, endpoints, findings) with no fourth argument
    returns the same string it did before this change (no vendor-trend
    section injected when the kwarg is simply omitted).
    """
    md = build_tech_markdown(_cfg(), [], [])
    assert "## Vendor PQC Status Trends" not in md


def test_build_tech_markdown_none_trends_no_heading():
    md = build_tech_markdown(_cfg(), [], [], vendor_pqc_trends=None)
    assert "## Vendor PQC Status Trends" not in md


def test_build_tech_markdown_empty_list_no_orphan_heading():
    md = build_tech_markdown(_cfg(), [], [], vendor_pqc_trends=[])
    assert "## Vendor PQC Status Trends" not in md


def test_build_tech_markdown_one_trend_renders_table():
    trend = {
        "vendor": "Cisco",
        "event_type": "pqc_status_change",
        "old_value": "classical_only",
        "new_value": "hybrid_available",
        "detected_at": "2026-08-01T00:00:00+00:00",
        "confirmed_at": None,
    }
    md = build_tech_markdown(_cfg(), [], [], vendor_pqc_trends=[trend])
    assert "## Vendor PQC Status Trends" in md
    assert VENDOR_TREND_ADVISORY_CAPTION in md
    assert "| Vendor | Change | Transition | Detected |" in md
    assert "Cisco" in md


def test_build_tech_markdown_pipe_in_vendor_escaped():
    trend = {
        "vendor": "Acme | Corp",
        "event_type": "pqc_status_change",
        "old_value": "classical_only",
        "new_value": "hybrid_available",
        "detected_at": "2026-08-01T00:00:00+00:00",
        "confirmed_at": None,
    }
    md = build_tech_markdown(_cfg(), [], [], vendor_pqc_trends=[trend])
    assert "Acme \\| Corp" in md
    # Table structure must survive — same number of header/divider/data rows.
    section = md.split("## Vendor PQC Status Trends", 1)[1]
    assert "|---|---|---|---|" in section


def test_build_tech_markdown_none_values_render_em_dash_not_literal_none():
    trend = {
        "vendor": "Juniper",
        "event_type": "pqc_status_change",
        "old_value": None,
        "new_value": "hybrid_available",
        "detected_at": "2026-08-01T00:00:00+00:00",
        "confirmed_at": None,
    }
    md = build_tech_markdown(_cfg(), [], [], vendor_pqc_trends=[trend])
    section = md.split("## Vendor PQC Status Trends", 1)[1]
    # No literal "None" leaking into rendered transition text.
    assert "None" not in section
    assert "—" in section  # em-dash placeholder


def test_build_tech_markdown_unknown_event_type_falls_back_to_raw():
    trend = {
        "vendor": "Fortinet",
        "event_type": "some_future_event",
        "old_value": "a",
        "new_value": "b",
        "detected_at": "2026-08-01T00:00:00+00:00",
        "confirmed_at": None,
    }
    md = build_tech_markdown(_cfg(), [], [], vendor_pqc_trends=[trend])
    assert "some_future_event" in md


# ---------------------------------------------------------------------------
# Task 3: _load_vendor_pqc_trends() loader coverage
# ---------------------------------------------------------------------------

import datetime as _dt

from quirk.db import get_session, init_db
from quirk.models import VendorPqcTrendEvent
from quirk.reports.writer import _load_vendor_pqc_trends


def _seed_db(tmp_path, rows):
    db_path = str(tmp_path / "vendor_trends.db")
    init_db(db_path)
    with get_session(db_path) as sess:
        for r in rows:
            sess.add(VendorPqcTrendEvent(**r))
        sess.commit()
    return db_path


def test_load_vendor_pqc_trends_returns_dicts_with_expected_keys(tmp_path):
    now = _dt.datetime.now(_dt.timezone.utc)
    db_path = _seed_db(tmp_path, [
        {
            "vendor": "Cisco",
            "event_type": "pqc_status_change",
            "old_value": "classical_only",
            "new_value": "hybrid_available",
            "detected_at": now,
            "confirmed_at": None,
        },
    ])
    rows = _load_vendor_pqc_trends(db_path)
    assert len(rows) == 1
    row = rows[0]
    assert set(row.keys()) == {
        "vendor", "event_type", "old_value", "new_value", "detected_at", "confirmed_at",
    }
    assert row["vendor"] == "Cisco"


def test_load_vendor_pqc_trends_newest_first(tmp_path):
    t1 = _dt.datetime(2026, 1, 1, tzinfo=_dt.timezone.utc)
    t2 = _dt.datetime(2026, 6, 1, tzinfo=_dt.timezone.utc)
    db_path = _seed_db(tmp_path, [
        {"vendor": "Old", "event_type": "pqc_status_change", "old_value": "a",
         "new_value": "b", "detected_at": t1, "confirmed_at": None},
        {"vendor": "New", "event_type": "pqc_status_change", "old_value": "a",
         "new_value": "b", "detected_at": t2, "confirmed_at": None},
    ])
    rows = _load_vendor_pqc_trends(db_path)
    assert [r["vendor"] for r in rows] == ["New", "Old"]


def test_load_vendor_pqc_trends_capped_at_50(tmp_path):
    now = _dt.datetime.now(_dt.timezone.utc)
    seed_rows = [
        {
            "vendor": f"Vendor{i}",
            "event_type": "pqc_status_change",
            "old_value": "a",
            "new_value": "b",
            "detected_at": now + _dt.timedelta(seconds=i),
            "confirmed_at": None,
        }
        for i in range(60)
    ]
    db_path = _seed_db(tmp_path, seed_rows)
    rows = _load_vendor_pqc_trends(db_path)
    assert len(rows) == 50


def test_load_vendor_pqc_trends_missing_db_returns_empty_no_raise():
    rows = _load_vendor_pqc_trends("/nonexistent/does-not-exist.db")
    assert rows == []
