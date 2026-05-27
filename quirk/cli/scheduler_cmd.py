"""quirk scheduler — Phase 63 SCHED-02: long-running 60s dispatch loop."""
from __future__ import annotations

import argparse
import ipaddress
import os
import re
import signal
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import yaml
from croniter import croniter
from sqlalchemy.orm import Session

from quirk.config import load_config
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
# Config materialisation for config-less schedules (STAB-03 / Phase 115)
# ---------------------------------------------------------------------------

#: Minimal YAML dict skeleton that satisfies config_from_dict / load_config.
#: All required top-level sections are present; scanner connectors and
#: concurrency are set to safe, inert defaults so run_scan can load the
#: file without error even when the schedule has no external config.
_MINIMAL_SCAN_CONFIG: dict = {
    "assessment": {
        "name": "scheduled-scan",
        "data_classification": "internal",
        "report_owner": "quirk-scheduler",
        "timezone": "UTC",
    },
    "scan": {
        "concurrency": 10,
        "ports_tls": [443, 8443],
    },
    "targets": {
        "fqdns": [],
        "cidrs": [],
        "include_ips": [],
        "exclude_ips": [],
    },
    "connectors": {},
    "output": {
        "directory": "output",
        "db_path": "quirk.db",
    },
}


def _classify_target(target: str) -> str:
    """Return the TargetsCfg key that `target` belongs to.

    Returns one of: "include_ips", "cidrs", "fqdns".
    Uses the ipaddress module for IP / CIDR detection (no regex guessing).
    """
    # Strip surrounding whitespace so " 127.0.0.1 " still parses correctly.
    t = target.strip()
    if "/" in t:
        try:
            ipaddress.ip_network(t, strict=False)
            return "cidrs"
        except ValueError:
            pass
    try:
        ipaddress.ip_address(t)
        return "include_ips"
    except ValueError:
        pass
    return "fqdns"


def _materialize_scan_config(
    schedule: ScheduledScan,
    scan_config_path: Optional[str],
    output_dir: Path,
) -> str:
    """Build (or augment) a scan config YAML that includes schedule.target.

    - If `scan_config_path` is provided, load it via yaml.safe_load and merge
      schedule.target into the appropriate targets sub-key (append, never clobber).
    - Otherwise start from the minimal inert skeleton _MINIMAL_SCAN_CONFIG.
    - Always set output.directory to str(output_dir) so artifacts land under the
      scheduled output tree (SENSOR-05 anchoring).
    - Write the merged dict to output_dir/scan-config.generated.yaml and return
      its absolute path as a str.

    Security: schedule.target goes into a YAML *value* (never a shell arg) and
    output_dir is derived from sanitized safe_name + timestamp inside the output
    tree (T-63-07 / STAB-03 threat note).
    """
    import copy

    if scan_config_path is not None:
        with open(scan_config_path, "r", encoding="utf-8") as fh:
            base: dict = yaml.safe_load(fh) or {}
    else:
        base = copy.deepcopy(_MINIMAL_SCAN_CONFIG)

    # Ensure required top-level sections exist (defensive merge for partial configs)
    for key, default in _MINIMAL_SCAN_CONFIG.items():
        if key not in base:
            base[key] = copy.deepcopy(default)

    # Inject schedule.target into the correct targets sub-key (merge, not replace)
    target = (schedule.target or "").strip()
    if target:
        targets_section = base.setdefault("targets", {})
        bucket = _classify_target(target)
        existing = targets_section.get(bucket) or []
        if not isinstance(existing, list):
            existing = [str(existing)]
        if target not in existing:
            existing = list(existing) + [target]
        targets_section[bucket] = existing

    # Anchor output.directory to the scheduled output dir (SENSOR-05 Fix 1)
    base.setdefault("output", {})["directory"] = str(output_dir)

    generated_path = output_dir / "scan-config.generated.yaml"
    with open(generated_path, "w", encoding="utf-8") as fh:
        yaml.safe_dump(base, fh, default_flow_style=False, allow_unicode=True)

    return str(generated_path)


# ---------------------------------------------------------------------------
# Dispatch one due schedule
# ---------------------------------------------------------------------------


def _dispatch_schedule(
    schedule: ScheduledScan,
    db: Session,
    config_path: str,
    scan_config_path: Optional[str] = None,
) -> ScheduledRun:
    """Create a scheduled_runs row and invoke the scan subprocess.

    Status transitions: pending → running → completed/failed.
    Uses sys.executable + -m run_scan to avoid PATH issues (Pitfall 5 / T-63-07).

    scan_config_path: optional path to a base config.yaml for the scan subprocess.
    When provided it is used as the starting point for the generated config and
    output.directory is anchored to cfg.output.directory (SENSOR-05 Fix 1).
    When absent, a minimal inert config is generated from schedule.target so that
    config-less schedules still run (STAB-03 gap-closure, Phase 115).

    A schedule is only rejected (marked failed, no Popen) when both
    scan_config_path is None AND schedule.target is empty/falsy — there is
    genuinely nothing to scan.
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

    # STAB-03 gap-closure: fail fast only when there is genuinely nothing to scan.
    # A schedule with a non-empty target can always produce a generated config, so
    # we only bail here when both the explicit config and the target column are absent.
    if scan_config_path is None and not (schedule.target or "").strip():
        run.status = "failed"
        run.completed_at = _utcnow_naive()
        db.commit()
        import logging as _logging
        _logging.getLogger(__name__).error(
            "Schedule %r has no config file and no target — marking failed",
            schedule.name,
        )
        return run

    # WR-02: sanitize schedule.name before using it as a path component.
    # A name like '../../../etc/cron.d' would escape the output tree via Path().
    # Accept only alphanumerics, underscores, and hyphens (max 128 chars);
    # fall back to "unnamed" so mkdir never traverses outside output/scheduled/.
    _SAFE_NAME_RE = re.compile(r"^[a-zA-Z0-9_\-]{1,128}$")
    safe_name = schedule.name if _SAFE_NAME_RE.match(schedule.name) else "unnamed"

    # Determine output base: prefer cfg.output.directory from an explicit scan_config;
    # fall back to QUIRK_OUTPUT_DIR env var or "output" directory (SENSOR-05 Fix 1).
    if scan_config_path is not None:
        cfg = load_config(scan_config_path)
        output_base = Path(cfg.output.directory)
    else:
        output_base = Path(os.environ.get("QUIRK_OUTPUT_DIR", "output"))

    output_dir = output_base / "scheduled" / safe_name / now.strftime("%Y%m%d-%H%M%S")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate (or augment) a scan config that includes schedule.target.
    # The generated file is passed as --config to run_scan so target + output
    # directory are both conveyed without widening run_scan.py's arg surface
    # with --target or --output (STAB-03 invariant).
    generated_config = _materialize_scan_config(schedule, scan_config_path, output_dir)

    # T-63-07: list-form Popen — no shell=True, no metacharacter expansion
    # Pitfall 5: sys.executable + -m run_scan (not "quirk" which may not be on PATH)
    cmd = [sys.executable, "-m", "run_scan", "--config", generated_config]
    cmd += [
        "--profile",
        schedule.profile or "balanced",
    ]
    # NOTE: target + output_dir are conveyed via the generated --config.
    # Do NOT add --target or --output — run_scan.py does not accept them (STAB-03).

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

    # Phase 101 NOTIFY-01: dispatch notifications for this completed run.
    # Deferred import avoids circular-import between scheduler_cmd and dispatcher.
    # Full try/except: notification failure must NEVER propagate or corrupt the
    # scan record — the run row is already committed above (NOTIFY-07, T-101-10).
    try:
        from quirk.notify.dispatcher import dispatch_notifications
        dispatch_notifications(run=run, schedule=schedule, db=db)
    except Exception as exc:  # noqa: BLE001
        import logging as _logging
        from quirk.util.safe_exc import safe_str as _safe_str
        _logging.getLogger(__name__).warning(
            "Notification dispatch error (scan record unaffected): %s",
            _safe_str(exc),
        )

    # Phase 103 SIEM-01: after-scan SIEM export (when export_after_scan: true in [siem] config).
    # Same deferred-import + try/except isolation: SIEM failure must NEVER propagate.
    try:
        from quirk.siem.dispatcher import export_after_scan_hook
        export_after_scan_hook(run=run, schedule=schedule, db=db)
    except Exception as exc:  # noqa: BLE001
        import logging as _logging
        from quirk.util.safe_exc import safe_str as _safe_str
        _logging.getLogger(__name__).warning(
            "SIEM export error (scan record unaffected): %s",
            _safe_str(exc),
        )

    return run


# ---------------------------------------------------------------------------
# Single iteration: find and dispatch all due schedules
# ---------------------------------------------------------------------------


def _check_and_dispatch_due(
    db: Session,
    config_path: str,
    scan_config_path: Optional[str] = None,
) -> int:
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
            _dispatch_schedule(s, db, config_path, scan_config_path=scan_config_path)
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
        "--scan-config",
        default=None,
        dest="scan_config",
        help="Path to config.yaml for scan subprocess (anchors output to cfg.output.directory)",
    )
    p_run.add_argument(
        "--once",
        action="store_true",
        help="Run a single iteration then exit (for tests and smoke checks).",
    )

    args = parser.parse_args(argv)
    db_path = _resolve_db_path(args.config)
    scan_config_path = args.scan_config

    # Ensure tables exist before first session (idempotent)
    init_db(db_path)

    # Install signal handlers (Pattern 7 — must run in main thread)
    signal.signal(signal.SIGINT, _handle_signal)
    if sys.platform != "win32":
        signal.signal(signal.SIGTERM, _handle_signal)

    # Startup recovery: mark stale runs from a prior crashed scheduler as failed
    with get_session(db_path) as db:
        _recover_stale_runs(db)

    if args.once:
        # Test / smoke-check mode: dispatch due schedules once and return
        with get_session(db_path) as db:
            _check_and_dispatch_due(db, db_path, scan_config_path=scan_config_path)
        return

    # Long-running loop (D-05): sleep in 1-second increments for SIGINT responsiveness
    global _stop_flag
    while not _stop_flag:
        with get_session(db_path) as db:
            _check_and_dispatch_due(db, db_path, scan_config_path=scan_config_path)
        # 60 × 1-second sleep — allows _stop_flag to be checked each second
        for _ in range(60):
            if _stop_flag:
                break
            time.sleep(1)
