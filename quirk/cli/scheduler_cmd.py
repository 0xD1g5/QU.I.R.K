"""quirk scheduler — Phase 63 SCHED-02: long-running 60s dispatch loop."""
from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from croniter import croniter
from sqlalchemy.orm import Session

from quirk.db import get_session, init_db
from quirk.models import ScheduledScan, ScheduledRun

# ---------------------------------------------------------------------------
# Datetime convention (Pitfall 1): ALL datetimes are stored and compared as
# timezone-naive UTC throughout this module.  Use _utcnow_naive() everywhere;
# NEVER mix tz-aware and tz-naive datetimes.
# ---------------------------------------------------------------------------

_stop_flag = False


def _handle_signal(signum, frame) -> None:
    global _stop_flag
    _stop_flag = True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _utcnow_naive() -> datetime:
    """Return the current UTC time as a timezone-naive datetime (Pitfall 1)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _resolve_db_path(config_arg: Optional[str]) -> str:
    """Resolve DB path in priority order: --config arg > QUIRK_DB_PATH env > ./quirk.db."""
    if config_arg is not None:
        return config_arg
    env_path = os.environ.get("QUIRK_DB_PATH")
    if env_path:
        return env_path
    return "./quirk.db"


def _compute_next_run(schedule: ScheduledScan) -> datetime:
    """Compute the next run time from last_run_at (or immediately if never run).

    Uses croniter with a timezone-naive base datetime — returns a timezone-naive datetime (D-06).

    When last_run_at is None (schedule has never run), use a base 1 minute before now
    so croniter.get_next() returns a time that is <= now, making the schedule immediately
    eligible for dispatch on the first iteration.
    """
    if schedule.last_run_at is not None:
        base = schedule.last_run_at
    else:
        # Never run — treat as due immediately by computing next run from 2 minutes ago
        # so croniter.get_next() returns a time guaranteed to be <= now.
        base = _utcnow_naive() - timedelta(minutes=2)
    return croniter(schedule.cron_expr, base).get_next(datetime)


# ---------------------------------------------------------------------------
# Startup recovery (Pitfall 4 / T-63-10)
# ---------------------------------------------------------------------------

_STALE_THRESHOLD = timedelta(hours=2)


def _recover_stale_runs(db: Session) -> int:
    """Mark stale pending/running rows as failed/INTERRUPTED on scheduler startup.

    Any scheduled_runs row with status in ('pending', 'running') whose dispatched_at
    is older than _STALE_THRESHOLD (2 hours) is assumed to belong to a prior crashed
    scheduler process and is marked failed to avoid perpetual "running" state in the
    dashboard (Pitfall 4).
    """
    cutoff = _utcnow_naive() - _STALE_THRESHOLD
    stale = (
        db.query(ScheduledRun)
        .filter(
            ScheduledRun.status.in_(("pending", "running")),
            ScheduledRun.dispatched_at < cutoff,
        )
        .all()
    )
    for run in stale:
        run.status = "failed"
        run.scan_output_path = "INTERRUPTED"
        run.completed_at = _utcnow_naive()
    db.commit()
    return len(stale)


# ---------------------------------------------------------------------------
# Dispatch one due schedule
# ---------------------------------------------------------------------------


def _dispatch_schedule(
    schedule: ScheduledScan, db: Session, config_path: str
) -> ScheduledRun:
    """Create a scheduled_runs row and invoke the scan subprocess.

    Status transitions: pending → running → completed/failed.
    Uses sys.executable + -m run_scan to avoid PATH issues (Pitfall 5 / T-63-07).
    """
    now = _utcnow_naive()
    run = ScheduledRun(
        schedule_id=schedule.id,
        dispatched_at=now,
        status="pending",
        scan_output_path=None,
        scan_id=None,
    )
    db.add(run)
    db.flush()  # obtain run.id without closing session

    output_dir = (
        Path("output/scheduled") / schedule.name / now.strftime("%Y%m%d-%H%M%S")
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    # T-63-07: list-form Popen — no shell=True, no metacharacter expansion
    # Pitfall 5: sys.executable + -m run_scan (not "quirk" which may not be on PATH)
    cmd = [
        sys.executable,
        "-m",
        "run_scan",
        "--config",
        config_path,
        "--target",
        schedule.target,
        "--profile",
        schedule.profile or "balanced",
        "--output",
        str(output_dir),
    ]

    run.status = "running"
    db.commit()

    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        _stdout, _stderr = proc.communicate()
        run.status = "completed" if proc.returncode == 0 else "failed"
    except Exception:
        run.status = "failed"

    run.completed_at = _utcnow_naive()
    run.scan_output_path = str(output_dir)
    schedule.last_run_at = now
    db.commit()
    return run


# ---------------------------------------------------------------------------
# Single iteration: find and dispatch all due schedules
# ---------------------------------------------------------------------------


def _check_and_dispatch_due(db: Session, config_path: str) -> int:
    """Query enabled schedules, compute next_run_at, dispatch any that are past due.

    Returns the count of schedules dispatched this iteration.
    """
    dispatched = 0
    now = _utcnow_naive()
    # noqa: E712 — SQLAlchemy requires == True, not `is True`
    schedules = (
        db.query(ScheduledScan).filter(ScheduledScan.enabled == True).all()  # noqa: E712
    )
    for s in schedules:
        next_run = _compute_next_run(s)
        if next_run <= now:
            _dispatch_schedule(s, db, config_path)
            dispatched += 1
    return dispatched


# ---------------------------------------------------------------------------
# Public entrypoint
# ---------------------------------------------------------------------------


def run_scheduler(argv: list[str]) -> None:
    """Main entrypoint called from run_scan.py interception block.

    argv = sys.argv[2:] — supports subcommand `run`, flags `--config <path>` and
    `--once` (single iteration then exit, used in tests and verification).

    Signal handlers (SIGINT / SIGTERM) set _stop_flag so the 1-second sub-sleep
    loop exits gracefully within 60 seconds of receiving a signal (D-05 / Pattern 7).
    """
    parser = argparse.ArgumentParser(prog="quirk scheduler")
    sub = parser.add_subparsers(dest="action", required=True)

    p_run = sub.add_parser("run", help="Start the scheduler dispatch loop")
    p_run.add_argument("--config", default=None, help="Path to quirk.db or :memory:")
    p_run.add_argument(
        "--once",
        action="store_true",
        help="Run a single iteration then exit (for tests and smoke checks).",
    )

    args = parser.parse_args(argv)
    db_path = _resolve_db_path(args.config)

    # Ensure tables exist before first session (idempotent)
    init_db(db_path)

    # Install signal handlers (Pattern 7 — must run in main thread)
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    # Startup recovery: mark stale runs from a prior crashed scheduler as failed
    with get_session(db_path) as db:
        _recover_stale_runs(db)

    if args.once:
        # Test / smoke-check mode: dispatch due schedules once and return
        with get_session(db_path) as db:
            _check_and_dispatch_due(db, db_path)
        return

    # Long-running loop (D-05): sleep in 1-second increments for SIGINT responsiveness
    global _stop_flag
    while not _stop_flag:
        with get_session(db_path) as db:
            _check_and_dispatch_due(db, db_path)
        # 60 × 1-second sleep — allows _stop_flag to be checked each second
        for _ in range(60):
            if _stop_flag:
                break
            time.sleep(1)
