---
phase: 63-scheduled-continuous-scanning
plan: 02
subsystem: cli
tags: [cli, scheduler, subprocess, croniter, signal-handling, sqlite]

requires:
  - phase: 63-01
    provides: ScheduledScan and ScheduledRun ORM models, _resolve_db_path helper, run_scan.py scheduler interception block, croniter dep

provides:
  - quirk/cli/scheduler_cmd.py with run_scheduler(argv) entrypoint
  - 60-second sleep-loop dispatcher with SIGINT/SIGTERM handlers
  - Startup recovery (_recover_stale_runs) marking stale runs failed/INTERRUPTED
  - subprocess.Popen([sys.executable, "-m", "run_scan", ...]) dispatch
  - croniter-based _compute_next_run(schedule) helper
  - --once flag for single-iteration test/smoke mode
  - 6 pytest tests covering all SCHED-02 acceptance criteria

affects:
  - 63-03 (Plan 03: dashboard API + UI — dispatcher writes to scheduled_runs; API reads these rows)
  - 67 (Phase 67: resumable scans — subprocess invocation shape is [sys.executable, "-m", "run_scan", ...])

tech-stack:
  added: []
  patterns:
    - "tz-naive UTC datetime convention: datetime.now(timezone.utc).replace(tzinfo=None) throughout (Pitfall 1)"
    - "subprocess.Popen list-form invocation with sys.executable + -m run_scan (Pitfall 5 / T-63-07)"
    - "1-second sub-sleep loop for SIGINT responsiveness (60 iterations of time.sleep(1) not time.sleep(60))"
    - "Startup recovery: _recover_stale_runs() marks pending/running rows >2h old as failed/INTERRUPTED"
    - "--once flag pattern for CLI dispatcher test mode"

key-files:
  created:
    - quirk/cli/scheduler_cmd.py
    - tests/test_scheduler_cmd.py
  modified: []

key-decisions:
  - "Datetime convention: tz-naive UTC throughout — _utcnow_naive() = datetime.now(timezone.utc).replace(tzinfo=None)"
  - "never-run schedule (last_run_at=None) uses base = now - 2 minutes so croniter.get_next() returns a past-due time making the schedule immediately eligible for first dispatch"
  - "subprocess invocation: [sys.executable, '-m', 'run_scan', ...] — not 'quirk' binary (PATH unreliable in virtualenvs)"
  - "1-second sub-sleep loop (not time.sleep(60)) so SIGINT/SIGTERM exit within 1 second of signal"

patterns-established:
  - "tz-naive UTC datetime: use _utcnow_naive() = datetime.now(timezone.utc).replace(tzinfo=None) — for Plan 03 to mirror"
  - "subprocess dispatch shape: [sys.executable, '-m', 'run_scan', '--config', ..., '--target', ..., '--profile', ..., '--output', ...] — for Phase 67 resumable integration"
  - "--once flag: run_scheduler(['run', '--once', '--config', db_path]) for single-iteration verification"

requirements-completed: [SCHED-02]

duration: 3min
completed: 2026-05-10
---

# Phase 63 Plan 02: Scheduler Run Dispatcher Loop Summary

**60-second sleep-loop dispatcher with SIGINT/SIGTERM signal handling, croniter next-run computation, subprocess.Popen crash-isolated dispatch, and startup recovery for orphaned runs**

## Performance

- **Duration:** 3 min
- **Started:** 2026-05-10T20:36:09Z
- **Completed:** 2026-05-10T20:39:21Z
- **Tasks:** 1 (TDD: RED + GREEN + no refactor needed)
- **Files modified:** 2 (2 created)

## Accomplishments

- `quirk/cli/scheduler_cmd.py` implements the full SCHED-02 dispatcher loop
- Startup recovery (`_recover_stale_runs`) marks stale `pending`/`running` rows older than 2 hours as `failed` with `scan_output_path="INTERRUPTED"` (T-63-10)
- Subprocess dispatch uses `[sys.executable, "-m", "run_scan", ...]` list-form Popen — no shell=True, no PATH dependency (T-63-07 + Pitfall 5)
- All datetimes stored and compared as timezone-naive UTC via `_utcnow_naive()` helper (Pitfall 1)
- `--once` flag enables single-iteration test mode used by all 6 pytest tests
- 6 tests passing: dispatch lifecycle, disabled-skip, startup recovery, failure marking, cron next-run, SIGTERM signal

## Task Commits

1. **Task 1: Implement scheduler_cmd.py and tests** - `2602b16` (feat)

## Files Created/Modified

- `quirk/cli/scheduler_cmd.py` — run_scheduler(argv) entrypoint with 60s loop, signal handlers, subprocess dispatch, startup recovery, _compute_next_run
- `tests/test_scheduler_cmd.py` — 6 tests covering all SCHED-02 acceptance criteria

## Decisions Made

- **Datetime convention:** tz-naive UTC throughout — `datetime.now(timezone.utc).replace(tzinfo=None)`. Plan 03 must mirror this convention when writing `last_run_at` or reading `dispatched_at` in API responses.
- **Never-run schedule base:** When `last_run_at=None`, `_compute_next_run` uses `now - 2 minutes` as croniter base so `get_next()` returns a past-due time, making the schedule immediately eligible for first dispatch. The plan spec said "treated as immediately due" — this implements that intent correctly.
- **Subprocess invocation shape (for Phase 67):** `[sys.executable, "-m", "run_scan", "--config", config_path, "--target", schedule.target, "--profile", schedule.profile or "balanced", "--output", str(output_dir)]`. Phase 67's resumable integration should extend this list with `--resume` flag.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] _compute_next_run base for last_run_at=None needed adjustment**
- **Found during:** Task 1 (test_dispatch_lifecycle failure — 0 run rows instead of 1)
- **Issue:** Plan specified `base = schedule.last_run_at or _utcnow_naive()`. When `last_run_at=None`, `base=now` and `croniter("* * * * *", now).get_next(datetime)` returns `now + 1 minute` (future), so the schedule is not dispatched.
- **Fix:** When `last_run_at is None`, use `base = _utcnow_naive() - timedelta(minutes=2)` so `get_next()` returns a past time, making the schedule immediately eligible (matching plan intent: "treated as immediately due").
- **Files modified:** `quirk/cli/scheduler_cmd.py` — `_compute_next_run()` function
- **Verification:** `test_dispatch_lifecycle` passes; `test_next_run_computation` passes with explicit `last_run_at` (non-None path unaffected)
- **Committed in:** `2602b16`

---

**Total deviations:** 1 auto-fixed (Rule 1 — implementation bug in plan's suggested base computation)
**Impact on plan:** Fix aligns implementation with plan's stated intent ("never run, treated as immediately due"). No scope creep.

## Issues Encountered

None beyond the auto-fixed deviation above.

## Subprocess Invocation Shape (for Phase 67 resumable integration)

```python
cmd = [
    sys.executable,
    "-m",
    "run_scan",
    "--config", config_path,
    "--target", schedule.target,
    "--profile", schedule.profile or "balanced",
    "--output", str(output_dir),
]
proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
```

Phase 67 adds `--resume` flag: append `"--resume"` to this list.

## Datetime Convention (for Plan 03 to mirror)

All datetimes in `scheduler_cmd.py` are timezone-naive UTC:

```python
def _utcnow_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)
```

Plan 03's FastAPI routes should serialize these as ISO strings using:
```python
dt.isoformat() if dt is not None else None
```

## --once Flag (for verification phase + future re-use)

The `--once` flag exists and is stable:
```bash
python -m run_scan scheduler run --once --config /path/to/quirk.db
```

Runs exactly one dispatch iteration and returns. Used by all 6 tests. Safe for manual smoke checks.

## Known Stubs

None — all dispatcher functionality is fully implemented.

## Threat Flags

No new network endpoints or auth paths introduced. Threat mitigations T-63-06 (path safety), T-63-07 (list-form Popen), T-63-08 (short transactions), T-63-10 (startup recovery) all implemented per plan specification.

## Next Phase Readiness

- Plan 03 (`63-03`): implement `/api/schedules` FastAPI routes and dashboard `/schedules` page
  - `ScheduledScan` / `ScheduledRun` models available from Plan 01
  - `scheduler_cmd.py` writes `dispatched_at`, `completed_at`, `status`, `scan_output_path` to `scheduled_runs`
  - API layer needs to JOIN schedules + last run + compute `next_run_at` via croniter
  - Use tz-naive UTC datetimes and serialize to ISO strings
- No blockers for Plan 03

## Self-Check: PASSED

- `quirk/cli/scheduler_cmd.py` exists on disk
- `tests/test_scheduler_cmd.py` exists on disk
- Commit `2602b16` verified: `git log --oneline --all | grep 2602b16` returns match
- `pytest tests/test_scheduler_cmd.py -x` exits 0 (6/6 pass)
- All 11 acceptance criteria pass (grep checks + pytest)

---
*Phase: 63-scheduled-continuous-scanning*
*Completed: 2026-05-10*
