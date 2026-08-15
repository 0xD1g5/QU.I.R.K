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


# ---------------------------------------------------------------------------
# Task 2 — write-time advisories on POST /api/schedules and `quirk schedule
# add` (D-26: write-time WARNS, never rejects). Both surfaces must create the
# row and return 2xx/exit 0; PATCH must remain untouched.
# ---------------------------------------------------------------------------

import inspect
import sys

_VALID_PAYLOAD_WT = {
    "name": "wt-test-schedule",
    "cron_expr": "0 0 * * 0",  # weekly, at-or-above floor
    "target": "example.com",
    "profile": "balanced",
}


def test_write_time_post_sub_floor_returns_201_with_advisory(dashboard_client):
    payload = {**_VALID_PAYLOAD_WT, "name": "wt-sub-floor", "cron_expr": "0 0 * * *"}
    response = dashboard_client.post("/api/schedules", json=payload)
    assert response.status_code == 201, response.text
    data = response.json()
    assert len(data["advisories"]) == 1
    assert "OT/ICS minimum cadence floor" in data["advisories"][0]


def test_write_time_post_at_floor_returns_201_no_advisory(dashboard_client):
    payload = {**_VALID_PAYLOAD_WT, "name": "wt-at-floor", "cron_expr": "0 0 * * 0"}
    response = dashboard_client.post("/api/schedules", json=payload)
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["advisories"] == []


def test_write_time_post_invalid_cron_still_returns_400(dashboard_client):
    payload = {**_VALID_PAYLOAD_WT, "name": "wt-bad-cron", "cron_expr": "not-a-cron"}
    response = dashboard_client.post("/api/schedules", json=payload)
    assert response.status_code == 400, response.text


def test_write_time_get_schedules_advisories_field_present(dashboard_client):
    payload = {**_VALID_PAYLOAD_WT, "name": "wt-get-list"}
    dashboard_client.post("/api/schedules", json=payload)
    response = dashboard_client.get("/api/schedules")
    assert response.status_code == 200
    data = response.json()
    assert len(data["schedules"]) >= 1
    assert data["schedules"][0]["advisories"] == []


def test_write_time_patch_unmodified_by_otics_cadence(dashboard_client):
    """PATCH still returns 200 for a toggle and its handler references no floor_advisory."""
    import quirk.dashboard.api.routes.schedules as _schedules_mod

    payload = {**_VALID_PAYLOAD_WT, "name": "wt-patch-target"}
    create = dashboard_client.post("/api/schedules", json=payload)
    schedule_id = create.json()["id"]
    response = dashboard_client.patch(f"/api/schedules/{schedule_id}", json={"enabled": False})
    assert response.status_code == 200, response.text
    assert "floor_advisory" not in inspect.getsource(_schedules_mod.update_schedule)


def test_write_time_cli_schedule_add_sub_floor_prints_advisory(tmp_path, capsys):
    from quirk.cli.schedule_cmd import run_schedule

    db_path = str(tmp_path / "cli-wt.db")
    run_schedule(
        [
            "add",
            "--name",
            "cli-wt-sub-floor",
            "--cron",
            "0 0 * * *",
            "--target",
            "example.com",
            "--config",
            db_path,
        ]
    )
    captured = capsys.readouterr()
    assert "OT/ICS minimum cadence floor" in captured.out


def test_write_time_cli_schedule_add_at_floor_no_advisory(tmp_path, capsys):
    from quirk.cli.schedule_cmd import run_schedule

    db_path = str(tmp_path / "cli-wt2.db")
    run_schedule(
        [
            "add",
            "--name",
            "cli-wt-at-floor",
            "--cron",
            "0 0 * * 0",
            "--target",
            "example.com",
            "--config",
            db_path,
        ]
    )
    captured = capsys.readouterr()
    assert "OT/ICS minimum cadence floor" not in captured.out


# ---------------------------------------------------------------------------
# Task 3 — write-path inventory guard + one-off-scan-unaffected guard.
#
# Proves the set of schedule-creation surfaces is exactly what the gate
# covers, so a future unguarded write path fails loudly (T-156-01), and that
# a one-off operator-initiated enable_modbus scan cannot reach the gate at
# all (D-15).
# ---------------------------------------------------------------------------

import pathlib
import re

from fastapi.routing import APIRoute

from quirk.dashboard.api.app import create_app

EXPECTED_SCHEDULE_WRITE_ROUTES = {("POST", "/api/schedules")}
EXPECTED_SCHEDULE_SUBCOMMANDS = {"add", "list", "enable", "disable", "remove"}
EXPECTED_OTICS_GATE_MODULES = {
    "cli/scheduler_cmd.py",
    "cli/schedule_cmd.py",
    "dashboard/api/routes/schedules.py",
}

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
_QUIRK_ROOT = _REPO_ROOT / "quirk"


def _all_route_method_paths(app) -> set:
    """Recursively collect (method, path) pairs, including routes nested inside
    include_router()-mounted sub-routers.

    Phase 150 D-17: on fastapi>=0.141/starlette>=1.6, `application.routes` no
    longer flattens included sub-router routes into plain APIRoute entries at
    include time -- a flat `isinstance(r, APIRoute)` walk over `app.routes`
    misses every /api/* route. See tests/test_sensor_ingest.py::_all_route_paths
    for the same pattern (Phase 150 origin).
    """
    pairs: set = set()

    def _walk(routes, prefix: str = "") -> None:
        for route in routes:
            if type(route).__name__ == "_IncludedRouter":
                sub_prefix = getattr(route.include_context, "prefix", "") or ""
                _walk(route.original_router.routes, prefix + sub_prefix)
            elif isinstance(route, APIRoute):
                for method in (route.methods or set()):
                    pairs.add((method, prefix + route.path))

    _walk(app.routes)
    return pairs


def test_write_path_inventory_routes_exactly_schedule_creation_set():
    app = create_app()
    all_pairs = _all_route_method_paths(app)
    schedule_write_pairs = {
        (method, path)
        for (method, path) in all_pairs
        if path.startswith("/api/schedules") and method in {"POST", "PUT"}
    }
    assert schedule_write_pairs == EXPECTED_SCHEDULE_WRITE_ROUTES, (
        "A schedule-creation route was added or removed. A new schedule-creation "
        "route must call quirk.otics_cadence.floor_advisory and then be added to "
        f"EXPECTED_SCHEDULE_WRITE_ROUTES in this test file. Found: {schedule_write_pairs}"
    )


def test_write_path_inventory_cli_subcommands_exactly_expected_set():
    """Source-text inventory of add_parser("<name>" literals (module exposes no parser-building
    function separate from run_schedule's inline argparse construction)."""
    source = (_QUIRK_ROOT / "cli" / "schedule_cmd.py").read_text(encoding="utf-8")
    found = set(re.findall(r'add_parser\(\s*"([^"]+)"', source))
    assert found == EXPECTED_SCHEDULE_SUBCOMMANDS, (
        "A `quirk schedule` subcommand was added or removed. A new subcommand that "
        "can create a schedule must call quirk.otics_cadence.floor_advisory and be "
        f"added to EXPECTED_SCHEDULE_SUBCOMMANDS. Found: {found}"
    )


def test_write_path_inventory_otics_gate_modules_exactly_expected_set():
    found: set = set()
    for path in _QUIRK_ROOT.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        if path.resolve() == (_QUIRK_ROOT / "otics_cadence.py").resolve():
            continue
        text = path.read_text(encoding="utf-8")
        code_lines = [
            line for line in text.splitlines() if not line.strip().startswith("#")
        ]
        if "otics_cadence" in "\n".join(code_lines):
            found.add(str(path.relative_to(_QUIRK_ROOT)))
    assert found == EXPECTED_OTICS_GATE_MODULES, (
        "The set of modules importing quirk.otics_cadence changed. This must stay "
        "confined to the recurring/scheduled write+dispatch path. "
        f"Found: {found}"
    )


def _read_code_lines(path: pathlib.Path) -> str:
    text = path.read_text(encoding="utf-8")
    return "\n".join(
        line for line in text.splitlines() if not line.strip().startswith("#")
    )


def test_one_off_unaffected_scanner_modules_free_of_otics_cadence():
    for rel in (
        "scanner/hardware_scanner.py",
        "scanner/modbus_scanner.py",
        "scanner/bacnet_scanner.py",
    ):
        code = _read_code_lines(_QUIRK_ROOT / rel)
        assert "otics_cadence" not in code, f"{rel} references otics_cadence"
        assert "OTICS_MIN_INTERVAL_HOURS" not in code, f"{rel} references OTICS_MIN_INTERVAL_HOURS"

    run_scan_code = _read_code_lines(_REPO_ROOT / "run_scan.py")
    assert "otics_cadence" not in run_scan_code
    assert "OTICS_MIN_INTERVAL_HOURS" not in run_scan_code


def test_one_off_unaffected_profiles_module_free_of_otics_connector_keys():
    code = _read_code_lines(_QUIRK_ROOT / "engine" / "profiles.py")
    assert "enable_modbus" not in code
    assert "enable_bacnet" not in code
