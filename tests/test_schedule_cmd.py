"""Tests for quirk schedule CLI CRUD commands (Phase 63 — SCHED-01).

Task 1: model registration + table creation tests (pass immediately).
Task 2: run_schedule CLI tests (full implementations).
"""
from __future__ import annotations

import sys

import pytest
from sqlalchemy import inspect as sa_inspect

from quirk.db import get_engine, get_session, init_db
from quirk.models import ScheduledScan, ScheduledRun


# ---------------------------------------------------------------------------
# Task 1 tests — model registration and table creation (no CLI dependency)
# ---------------------------------------------------------------------------


def test_models_registered_on_metadata():
    """ScheduledScan and ScheduledRun must be registered on SQLAlchemy Base.metadata."""
    assert ScheduledScan.__tablename__ == "scheduled_scans"
    assert ScheduledRun.__tablename__ == "scheduled_runs"


def test_init_db_creates_scheduled_tables(tmp_path):
    """init_db() must create both scheduled_scans and scheduled_runs tables."""
    db_file = str(tmp_path / "quirk.db")
    engine = init_db(db_file)
    table_names = sa_inspect(engine).get_table_names()
    assert "scheduled_scans" in table_names, f"scheduled_scans missing from {table_names}"
    assert "scheduled_runs" in table_names, f"scheduled_runs missing from {table_names}"


# ---------------------------------------------------------------------------
# Task 2 tests — CLI CRUD (full implementations)
# ---------------------------------------------------------------------------


def test_schedule_add_persists(tmp_path):
    """add subcommand must write a row with all expected field values."""
    from quirk.cli.schedule_cmd import run_schedule

    db_path = str(tmp_path / "quirk.db")
    init_db(db_path)

    run_schedule([
        "add",
        "--name", "weekly-prod",
        "--cron", "0 2 * * 1",
        "--target", "prod.example.com",
        "--profile", "balanced",
        "--config", db_path,
    ])

    with get_session(db_path) as db:
        row = db.query(ScheduledScan).filter_by(name="weekly-prod").first()
        assert row is not None
        assert row.cron_expr == "0 2 * * 1"
        assert row.target == "prod.example.com"
        assert row.profile == "balanced"
        assert row.enabled is True
        assert row.created_at is not None


def test_schedule_add_invalid_cron(tmp_path):
    """add subcommand must reject invalid cron expressions with SystemExit."""
    from quirk.cli.schedule_cmd import run_schedule

    db_path = str(tmp_path / "quirk.db")
    init_db(db_path)

    with pytest.raises(SystemExit) as exc_info:
        run_schedule([
            "add",
            "--name", "bad-cron",
            "--cron", "not-a-cron",
            "--target", "example.com",
            "--config", db_path,
        ])
    assert exc_info.value.code != 0

    with get_session(db_path) as db:
        assert db.query(ScheduledScan).filter_by(name="bad-cron").first() is None


def test_schedule_list_shows_row(tmp_path, capsys):
    """list subcommand must print a table containing the schedule name."""
    from quirk.cli.schedule_cmd import run_schedule

    db_path = str(tmp_path / "quirk.db")
    init_db(db_path)

    run_schedule([
        "add",
        "--name", "weekly-prod",
        "--cron", "0 2 * * 1",
        "--target", "prod.example.com",
        "--config", db_path,
    ])

    run_schedule(["list", "--config", db_path])
    captured = capsys.readouterr()
    assert "weekly-prod" in captured.out


def test_schedule_add_duplicate_name(tmp_path, capsys):
    """Second add with same name must exit non-zero with 'already exists' message."""
    from quirk.cli.schedule_cmd import run_schedule

    db_path = str(tmp_path / "quirk.db")
    init_db(db_path)

    run_schedule([
        "add",
        "--name", "weekly-prod",
        "--cron", "0 2 * * 1",
        "--target", "prod.example.com",
        "--config", db_path,
    ])

    with pytest.raises(SystemExit) as exc_info:
        run_schedule([
            "add",
            "--name", "weekly-prod",
            "--cron", "0 3 * * 2",
            "--target", "other.example.com",
            "--config", db_path,
        ])
    assert exc_info.value.code != 0
    captured = capsys.readouterr()
    combined = captured.out + captured.err
    assert "already exists" in combined


def test_run_scan_intercepts_schedule(tmp_path, monkeypatch, capsys):
    """run_scan.main() must short-circuit on argv[1] == 'schedule' without scan argparse."""
    import run_scan

    db_path = str(tmp_path / "quirk.db")
    init_db(db_path)

    monkeypatch.setattr(sys, "argv", ["quirk", "schedule", "list", "--config", db_path])
    # Should not raise and should not fall through to scan argparse
    try:
        run_scan.main()
    except SystemExit:
        pass  # list with no rows exits 0; either way no "target required" argparse error
    captured = capsys.readouterr()
    # Must NOT have fallen through to scan argparse error about missing target
    assert "required" not in captured.err.lower() or "target" not in captured.err.lower()
