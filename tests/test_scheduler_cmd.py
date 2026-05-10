"""Tests for quirk/cli/scheduler_cmd.py — Phase 63 SCHED-02.

Covers: dispatch lifecycle, disabled-skip, startup recovery, cron next-run logic,
dispatch failure, and signal-driven stop-flag (SIGTERM test skipped on Windows).

All DB operations use an in-memory SQLite DB via tmp_path fixture.
subprocess.Popen is monkeypatched to a FakePopen that returns a configurable
exit code without spawning a real process.
"""
from __future__ import annotations

import os
import signal
import sys
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from quirk.db import init_db, get_session
from quirk.models import ScheduledScan, ScheduledRun
from quirk.cli.scheduler_cmd import (
    _compute_next_run,
    _recover_stale_runs,
    _utcnow_naive,
    run_scheduler,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_db(tmp_path: Path) -> str:
    """Create an in-memory-style SQLite DB and return its path."""
    db_path = str(tmp_path / "quirk_test.db")
    init_db(db_path)
    return db_path


def _add_schedule(
    db_path: str,
    *,
    name: str = "test-scan",
    cron_expr: str = "* * * * *",
    target: str = "127.0.0.1",
    profile: str | None = None,
    enabled: bool = True,
    last_run_at: datetime | None = None,
) -> ScheduledScan:
    """Insert a ScheduledScan row and return it."""
    row = ScheduledScan(
        name=name,
        cron_expr=cron_expr,
        target=target,
        profile=profile,
        enabled=enabled,
        last_run_at=last_run_at,
        created_at=_utcnow_naive(),
    )
    with get_session(db_path) as db:
        db.add(row)
        db.flush()
        # expire_on_commit=False means we can read id after flush
        row_id = row.id
    # Re-fetch to get a detached copy with all fields set
    with get_session(db_path) as db:
        return db.query(ScheduledScan).filter_by(id=row_id).one()


def _all_runs(db_path: str) -> list[ScheduledRun]:
    with get_session(db_path) as db:
        return db.query(ScheduledRun).all()


def _get_run(db_path: str, run_id: int) -> ScheduledRun:
    with get_session(db_path) as db:
        return db.query(ScheduledRun).filter_by(id=run_id).one()


# ---------------------------------------------------------------------------
# FakePopen — monkeypatches subprocess.Popen
# ---------------------------------------------------------------------------


class FakePopen:
    """Drop-in for subprocess.Popen that returns a configurable exit code."""

    def __init__(self, returncode: int = 0):
        self._returncode = returncode
        self.stdout = None
        self.stderr = None

    def communicate(self):
        time.sleep(0.05)  # simulate tiny process delay
        return b"", b""

    @property
    def returncode(self):
        return self._returncode


# ---------------------------------------------------------------------------
# Test 1: dispatch lifecycle — enabled schedule dispatched, run row = completed
# ---------------------------------------------------------------------------


def test_dispatch_lifecycle(tmp_path, monkeypatch):
    """An enabled schedule with last_run_at=None is dispatched; run ends completed."""
    db_path = _make_db(tmp_path)
    _add_schedule(db_path, name="scan-a", cron_expr="* * * * *")

    captured_cmds: list[list[str]] = []

    def fake_popen(cmd, **kwargs):
        captured_cmds.append(cmd)
        return FakePopen(returncode=0)

    monkeypatch.setattr("quirk.cli.scheduler_cmd.subprocess.Popen", fake_popen)

    run_scheduler(["run", "--once", "--config", db_path])

    runs = _all_runs(db_path)
    assert len(runs) == 1, f"Expected 1 run row, got {len(runs)}"

    run = runs[0]
    assert run.status == "completed", f"Expected status=completed, got {run.status!r}"
    assert run.dispatched_at is not None
    assert run.completed_at is not None

    # scan_output_path should contain "output/scheduled/scan-a/"
    assert run.scan_output_path is not None
    assert "output/scheduled" in run.scan_output_path
    assert "scan-a" in run.scan_output_path

    # Verify sys.executable + -m run_scan was used (Pitfall 5)
    assert len(captured_cmds) == 1
    cmd = captured_cmds[0]
    assert cmd[0] == sys.executable
    assert cmd[1] == "-m"
    assert cmd[2] == "run_scan"


# ---------------------------------------------------------------------------
# Test 2: disabled schedule is skipped — no run row created
# ---------------------------------------------------------------------------


def test_disabled_schedule_skipped(tmp_path, monkeypatch):
    """A disabled schedule produces zero scheduled_runs rows."""
    db_path = _make_db(tmp_path)
    _add_schedule(db_path, name="skip-me", enabled=False)

    fake_calls: list = []

    def fake_popen(cmd, **kwargs):
        fake_calls.append(cmd)
        return FakePopen(returncode=0)

    monkeypatch.setattr("quirk.cli.scheduler_cmd.subprocess.Popen", fake_popen)

    run_scheduler(["run", "--once", "--config", db_path])

    runs = _all_runs(db_path)
    assert len(runs) == 0, f"Expected 0 run rows for disabled schedule, got {len(runs)}"
    assert len(fake_calls) == 0, "Popen should not have been called for a disabled schedule"


# ---------------------------------------------------------------------------
# Test 3: startup recovery — stale running row is marked failed/INTERRUPTED
# ---------------------------------------------------------------------------


def test_startup_recovery(tmp_path, monkeypatch):
    """A running row older than 2 hours is marked failed=INTERRUPTED on startup."""
    db_path = _make_db(tmp_path)
    schedule = _add_schedule(db_path, name="stale-scan")

    # Pre-seed a stale ScheduledRun (3 hours old, still "running")
    stale_dispatched_at = _utcnow_naive() - timedelta(hours=3)
    with get_session(db_path) as db:
        stale_run = ScheduledRun(
            schedule_id=schedule.id,
            dispatched_at=stale_dispatched_at,
            status="running",
            scan_output_path=None,
            scan_id=None,
        )
        db.add(stale_run)
        db.flush()
        stale_run_id = stale_run.id

    # No new scans should be dispatched (cron not yet due after seeding)
    # Monkeypatch Popen to track calls anyway
    fake_calls: list = []

    def fake_popen(cmd, **kwargs):
        fake_calls.append(cmd)
        return FakePopen(returncode=0)

    monkeypatch.setattr("quirk.cli.scheduler_cmd.subprocess.Popen", fake_popen)

    run_scheduler(["run", "--once", "--config", db_path])

    # Reload the stale run from DB
    recovered = _get_run(db_path, stale_run_id)
    assert recovered.status == "failed", (
        f"Stale run should be marked failed, got {recovered.status!r}"
    )
    assert recovered.scan_output_path == "INTERRUPTED", (
        f"Expected scan_output_path='INTERRUPTED', got {recovered.scan_output_path!r}"
    )
    assert recovered.completed_at is not None


# ---------------------------------------------------------------------------
# Test 4: subprocess failure marks run as failed
# ---------------------------------------------------------------------------


def test_dispatch_failure_marks_failed(tmp_path, monkeypatch):
    """When the dispatched process returns exit code 1, the run is marked failed."""
    db_path = _make_db(tmp_path)
    _add_schedule(db_path, name="fail-scan", cron_expr="* * * * *")

    def fake_popen(cmd, **kwargs):
        return FakePopen(returncode=1)

    monkeypatch.setattr("quirk.cli.scheduler_cmd.subprocess.Popen", fake_popen)

    run_scheduler(["run", "--once", "--config", db_path])

    runs = _all_runs(db_path)
    assert len(runs) == 1
    assert runs[0].status == "failed", (
        f"Expected status=failed for exit-code-1 subprocess, got {runs[0].status!r}"
    )


# ---------------------------------------------------------------------------
# Test 5: _compute_next_run returns correct cron next datetime
# ---------------------------------------------------------------------------


def test_next_run_computation(tmp_path):
    """_compute_next_run returns the correct next datetime for a known cron expression."""
    db_path = _make_db(tmp_path)

    # last_run_at: Sunday 2026-05-10 00:00:00 UTC (naive)
    # cron_expr: "0 2 * * 1" — every Monday at 02:00 UTC
    # Expected next: Monday 2026-05-11 02:00:00 UTC
    last_run_at = datetime(2026, 5, 10, 0, 0, 0)  # naive UTC
    expected_next = datetime(2026, 5, 11, 2, 0, 0)

    row = ScheduledScan(
        name="cron-test",
        cron_expr="0 2 * * 1",
        target="127.0.0.1",
        profile=None,
        enabled=True,
        last_run_at=last_run_at,
        created_at=_utcnow_naive(),
    )
    with get_session(db_path) as db:
        db.add(row)

    result = _compute_next_run(row)
    assert result == expected_next, (
        f"Expected next run {expected_next!r}, got {result!r}"
    )


# ---------------------------------------------------------------------------
# Test 6: SIGTERM sets _stop_flag and loop exits (Unix only)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    sys.platform.startswith("win"),
    reason="SIGTERM not supported on Windows in Python signal handlers",
)
def test_signal_sets_stop_flag(tmp_path, monkeypatch):
    """Sending SIGTERM causes run_scheduler to exit its loop within 65 seconds."""
    import quirk.cli.scheduler_cmd as sched_mod

    db_path = _make_db(tmp_path)
    # No schedules — the loop will just sleep between iterations

    def fake_popen(cmd, **kwargs):
        return FakePopen(returncode=0)

    monkeypatch.setattr("quirk.cli.scheduler_cmd.subprocess.Popen", fake_popen)

    # Reset module-level stop flag before the test
    sched_mod._stop_flag = False

    # A background thread fires SIGTERM at the main thread after 0.3s
    def _send_term():
        time.sleep(0.3)
        os.kill(os.getpid(), signal.SIGTERM)

    t = threading.Thread(target=_send_term, daemon=True)
    t.start()

    start = time.monotonic()
    # run_scheduler installs SIGTERM handler and blocks in the sleep loop
    run_scheduler(["run", "--config", db_path])
    elapsed = time.monotonic() - start

    # Should exit well within 65 seconds (signal fires at 0.3s, 1-second sub-sleep
    # means the loop checks _stop_flag within 1 second of the signal)
    assert elapsed < 65, f"Scheduler loop took too long to exit after SIGTERM: {elapsed:.1f}s"

    # Reset stop flag so other tests are not affected
    sched_mod._stop_flag = False
