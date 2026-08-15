"""Tests for quirk.otics_cadence — the OT/ICS recurring-probe safety floor (HWLC-12).

Phase 156 Plan 01: RED-phase coverage for min_gap_hours() cron derivation,
violates_otics_floor() fail-closed predicate, the config-dict inspection
helpers (otics_enabled_in_config / recurring_otics_opted_in), and the
strictly-allowlisted strip_otics_keys() helper. Also asserts the new
ConnectorsCfg.enable_recurring_otics opt-in field defaults to False.

See 156-RESEARCH.md Code Examples for the empirically verified min_gap_hours
behavior table and 156-CONTEXT.md D-19/D-20 for the floor value and
derivation rationale.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from quirk.config import ConnectorsCfg
from quirk.otics_cadence import (
    OTICS_MIN_INTERVAL_HOURS,
    min_gap_hours,
    violates_otics_floor,
    otics_enabled_in_config,
    recurring_otics_opted_in,
    strip_otics_keys,
)

# Fixed tz-naive UTC base datetime — the project's scheduler convention is
# tz-naive UTC throughout (schedules.py Pitfall 1 note). Using a fixed base
# (not datetime.now()) keeps the "0 0 * * 1,2" case deterministic.
_FIXED_BASE = datetime(2026, 8, 14, 0, 0, 0)


# ---------------------------------------------------------------------------
# min_gap_hours() derivation
# ---------------------------------------------------------------------------


def test_min_gap_daily_is_24h():
    assert min_gap_hours("0 0 * * *", base=_FIXED_BASE) == pytest.approx(24.0, abs=1e-3)


def test_min_gap_irregular_weekday_list_takes_minimum_not_average():
    # "0 0 * * 1,2" fires Mon+Tue each week: a 24h gap (Mon->Tue) and an 144h
    # gap (Tue->next Mon), averaging ~84h — but the load-bearing behavior is
    # that min_gap_hours reports the MINIMUM gap (24h), not the average.
    assert min_gap_hours("0 0 * * 1,2", base=_FIXED_BASE) == pytest.approx(24.0, abs=1e-3)


def test_min_gap_every_5_minutes_is_5_minutes():
    assert min_gap_hours("*/5 * * * *", base=_FIXED_BASE) == pytest.approx(0.0833, abs=1e-3)


def test_min_gap_weekly_is_168h():
    assert min_gap_hours("0 0 * * 0", base=_FIXED_BASE) == pytest.approx(168.0, abs=1e-3)


def test_min_gap_invalid_cron_returns_none():
    assert min_gap_hours("not a cron", base=_FIXED_BASE) is None


def test_min_gap_invalid_cron_raises_nothing():
    # Must never raise — exception-wrapped per T-156-02.
    try:
        min_gap_hours("not a cron", base=_FIXED_BASE)
    except Exception as exc:  # pragma: no cover - failure path
        pytest.fail(f"min_gap_hours raised unexpectedly: {exc!r}")


# ---------------------------------------------------------------------------
# violates_otics_floor() fail-closed predicate
# ---------------------------------------------------------------------------


def test_violates_floor_daily_is_true():
    # 24h < 168h floor
    assert violates_otics_floor("0 0 * * *", base=_FIXED_BASE) is True


def test_violates_floor_weekly_is_false():
    # 168h == floor, not below it — inclusive-satisfying at exactly the floor.
    assert violates_otics_floor("0 0 * * 0", base=_FIXED_BASE) is False


def test_violates_floor_invalid_cron_is_true_fail_closed():
    # An underivable cadence must be treated as violating, never as compliant.
    assert violates_otics_floor("not a cron", base=_FIXED_BASE) is True


# ---------------------------------------------------------------------------
# Floor constant
# ---------------------------------------------------------------------------


def test_otics_min_interval_hours_is_168():
    assert OTICS_MIN_INTERVAL_HOURS == 168


# ---------------------------------------------------------------------------
# otics_enabled_in_config()
# ---------------------------------------------------------------------------


def test_otics_enabled_in_config_true_when_modbus_enabled():
    assert otics_enabled_in_config({"connectors": {"enable_modbus": True}}) is True


def test_otics_enabled_in_config_false_when_connectors_empty():
    assert otics_enabled_in_config({"connectors": {}}) is False


def test_otics_enabled_in_config_false_when_base_empty():
    assert otics_enabled_in_config({}) is False


def test_otics_enabled_in_config_false_when_connectors_none():
    assert otics_enabled_in_config({"connectors": None}) is False


# ---------------------------------------------------------------------------
# recurring_otics_opted_in()
# ---------------------------------------------------------------------------


def test_recurring_otics_opted_in_true():
    assert recurring_otics_opted_in({"connectors": {"enable_recurring_otics": True}}) is True


def test_recurring_otics_opted_in_default_absent_is_false():
    assert recurring_otics_opted_in({"connectors": {}}) is False


# ---------------------------------------------------------------------------
# strip_otics_keys() — allowlist-only, never a heuristic sweep (T-156-03)
# ---------------------------------------------------------------------------


def test_strip_otics_keys_removes_only_allowlisted_keys():
    base = {
        "connectors": {
            "enable_modbus": True,
            "enable_bacnet": True,
            "enable_snmp": True,
            "snmp_community": "public",
        }
    }
    removed = strip_otics_keys(base)
    assert sorted(removed) == ["enable_bacnet", "enable_modbus"]
    assert base["connectors"]["enable_snmp"] is True
    assert base["connectors"]["snmp_community"] == "public"
    assert "enable_modbus" not in base["connectors"]
    assert "enable_bacnet" not in base["connectors"]


def test_strip_otics_keys_empty_dict_returns_empty_list():
    assert strip_otics_keys({}) == []


# ---------------------------------------------------------------------------
# ConnectorsCfg.enable_recurring_otics default-off
# ---------------------------------------------------------------------------


def test_connectors_cfg_enable_recurring_otics_defaults_false():
    assert ConnectorsCfg().enable_recurring_otics is False


# ---------------------------------------------------------------------------
# Task 1 — dispatch-time hard gate in _materialize_scan_config() (HWLC-12,
# D-16/D-21/D-26). Drives the real function against a tmp_path output dir and
# a real YAML file on disk, then reads back the generated YAML — the file is
# the actual contract run_scan.py's subprocess consumes.
# ---------------------------------------------------------------------------

import logging as _logging_mod

import yaml as _yaml

from quirk.db import init_db
from quirk.models import ScheduledScan
from quirk.cli.scheduler_cmd import _materialize_scan_config


def _write_scan_config(tmp_path, connectors: dict) -> str:
    cfg = {
        "assessment": {
            "name": "test",
            "data_classification": "internal",
            "report_owner": "quirk-test",
            "timezone": "UTC",
        },
        "scan": {"concurrency": 10, "ports_tls": [443]},
        "targets": {"fqdns": [], "cidrs": [], "include_ips": [], "exclude_ips": []},
        "connectors": connectors,
        "output": {"directory": "output", "db_path": "quirk.db"},
    }
    path = tmp_path / "base-config.yaml"
    with open(path, "w", encoding="utf-8") as fh:
        _yaml.safe_dump(cfg, fh)
    return str(path)


def _make_schedule(*, name: str = "sched-1", cron_expr: str = "0 0 * * *", target: str = "10.0.0.5") -> ScheduledScan:
    return ScheduledScan(
        id=1,
        name=name,
        cron_expr=cron_expr,
        target=target,
        profile=None,
        enabled=True,
    )


def test_dispatch_time_at_floor_with_opt_in_keeps_modbus(tmp_path):
    """168h cron + enable_recurring_otics=True: enable_modbus survives."""
    scan_config_path = _write_scan_config(
        tmp_path,
        {"enable_modbus": True, "enable_recurring_otics": True, "enable_snmp": True},
    )
    schedule = _make_schedule(cron_expr="0 0 * * 0")  # weekly = 168h
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    generated_path = _materialize_scan_config(schedule, scan_config_path, output_dir)
    with open(generated_path, encoding="utf-8") as fh:
        generated = _yaml.safe_load(fh)
    assert generated["connectors"]["enable_modbus"] is True
    assert generated["connectors"]["enable_snmp"] is True


def test_dispatch_time_sub_floor_strips_otics_keys(tmp_path, caplog):
    """24h cron: enable_modbus/enable_bacnet stripped; enable_snmp untouched."""
    scan_config_path = _write_scan_config(
        tmp_path,
        {
            "enable_modbus": True,
            "enable_bacnet": True,
            "enable_recurring_otics": True,
            "enable_snmp": True,
            "snmp_community": "public",
        },
    )
    schedule = _make_schedule(cron_expr="0 0 * * *")  # daily = 24h
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    with caplog.at_level(_logging_mod.INFO):
        generated_path = _materialize_scan_config(schedule, scan_config_path, output_dir)
    with open(generated_path, encoding="utf-8") as fh:
        generated = _yaml.safe_load(fh)
    assert "enable_modbus" not in generated["connectors"]
    assert "enable_bacnet" not in generated["connectors"]
    assert generated["connectors"]["enable_snmp"] is True
    assert generated["connectors"]["snmp_community"] == "public"
    assert any("OT/ICS probing suppressed" in rec.message for rec in caplog.records)
    assert any(schedule.name in rec.message for rec in caplog.records)


def test_dispatch_time_no_opt_in_strips_regardless_of_cadence(tmp_path):
    """enable_bacnet without enable_recurring_otics is stripped even at a compliant cadence."""
    scan_config_path = _write_scan_config(
        tmp_path,
        {"enable_bacnet": True},
    )
    schedule = _make_schedule(cron_expr="0 0 * * 0")  # weekly = 168h, would satisfy the floor
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    generated_path = _materialize_scan_config(schedule, scan_config_path, output_dir)
    with open(generated_path, encoding="utf-8") as fh:
        generated = _yaml.safe_load(fh)
    assert "enable_bacnet" not in generated["connectors"]


def test_dispatch_time_no_otics_keys_no_strip_no_log(tmp_path, caplog):
    """No connectors block / no OT/ICS keys present: nothing stripped, nothing logged."""
    scan_config_path = _write_scan_config(tmp_path, {"enable_snmp": True})
    schedule = _make_schedule(cron_expr="0 0 * * *")
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    with caplog.at_level(_logging_mod.INFO):
        generated_path = _materialize_scan_config(schedule, scan_config_path, output_dir)
    with open(generated_path, encoding="utf-8") as fh:
        generated = _yaml.safe_load(fh)
    assert generated["connectors"]["enable_snmp"] is True
    assert not any("OT/ICS probing suppressed" in rec.message for rec in caplog.records)
