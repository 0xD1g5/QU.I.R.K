---
phase: 63-scheduled-continuous-scanning
plan: 01
subsystem: database
tags: [sqlite, sqlalchemy, croniter, cli, scheduling]

requires:
  - phase: 51-qramm-core-infrastructure
    provides: ORM Base, get_session, init_db patterns used verbatim

provides:
  - ScheduledScan ORM model (scheduled_scans table) with unique name constraint
  - ScheduledRun ORM model (scheduled_runs table) for dispatch history
  - _ensure_scheduled_tables() migration helper registered in init_db()
  - quirk/cli/schedule_cmd.py with run_schedule(argv) entrypoint
  - Five CRUD subcommands: add, list, enable, disable, remove
  - Two new run_scan.py interception blocks: schedule and scheduler (both with return)
  - croniter>=1.4.0 added to [dashboard] optional extra in pyproject.toml
  - 7 passing pytest tests covering all SCHED-01 acceptance criteria

affects:
  - 63-02 (Plan 02: scheduler dispatcher — needs scheduler_cmd.py only; run_scan.py block already wired)
  - 63-03 (Plan 03: dashboard API + UI — needs ScheduledScan/ScheduledRun models and run_schedule entrypoint)

tech-stack:
  added: [croniter>=1.4.0]
  patterns:
    - "_ensure_*_tables(engine) migration helper pattern (same as Phase 51 QRAMM-01)"
    - "run_scan.py interception block with return (fixes missing-return bug in doctor block)"
    - "T-63-02 name allowlist regex before INSERT"
    - "T-63-03 fixed IntegrityError message (never stringify exception)"

key-files:
  created:
    - quirk/cli/schedule_cmd.py
    - tests/test_schedule_cmd.py
  modified:
    - quirk/models.py
    - quirk/db.py
    - run_scan.py
    - pyproject.toml

key-decisions:
  - "croniter>=1.4.0 added to [dashboard] optional extra only — not base deps (D-01)"
  - "ScheduledRun uses soft FK (Integer column, no DB-level constraint) matching SQLite pattern"
  - "name validated via re.match(r'^[A-Za-z0-9_\\-\\.]{1,255}$') before INSERT (T-63-02 path traversal)"
  - "scheduler interception block registered in Plan 01 to avoid second run_scan.py edit in Plan 02"
  - "IntegrityError caught with fixed message — never stringified (T-63-03 / LEAK-02 pattern)"

patterns-established:
  - "CRUD CLI pattern: run_schedule(argv: list[str]) -> None; argparse subparsers; get_session context manager"
  - "DB path resolution: --config arg > QUIRK_DB_PATH env > ./quirk.db"

requirements-completed: [SCHED-01]

duration: 4min
completed: 2026-05-10
---

# Phase 63 Plan 01: Scheduled Scans Models and CLI CRUD Summary

**SQLite-backed scheduled_scans/scheduled_runs tables with argparse CRUD subcommands (add/list/enable/disable/remove) using croniter for cron validation and path-traversal-safe name allowlist**

## Performance

- **Duration:** 4 min
- **Started:** 2026-05-10T20:28:49Z
- **Completed:** 2026-05-10T20:32:49Z
- **Tasks:** 2
- **Files modified:** 6 (4 modified, 2 created)

## Accomplishments

- Two new SQLAlchemy ORM models (`ScheduledScan` with `unique=True` name, `ScheduledRun`) appended to `quirk/models.py`
- `_ensure_scheduled_tables(engine)` migration helper added to `quirk/db.py` and called from `init_db()`
- `quirk/cli/schedule_cmd.py` with `run_schedule(argv)` implementing add/list/enable/disable/remove subcommands
- All three STRIDE mitigations applied: T-63-01 (croniter validation), T-63-02 (name allowlist regex), T-63-03 (fixed IntegrityError message)
- Two run_scan.py interception blocks wired (both with `return`) — `scheduler` block pre-wired for Plan 02
- 7 pytest tests, all passing

## ScheduledScan Column List (for Plan 02 + Plan 03 consumers)

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | Integer | PK, autoincrement | |
| name | String(255) | NOT NULL, UNIQUE | allowlist validated before INSERT |
| cron_expr | String(128) | NOT NULL | croniter.is_valid() validated |
| target | String(512) | NOT NULL | scan target (host/IP/range) |
| profile | String(64) | nullable | None = "balanced" |
| enabled | Boolean | default=True | toggled by enable/disable |
| last_run_at | DateTime | nullable | None = never run; updated by Plan 02 dispatcher |
| created_at | DateTime | NOT NULL | set at add time |

## ScheduledRun Column List (for Plan 02 + Plan 03 consumers)

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | Integer | PK, autoincrement | |
| schedule_id | Integer | NOT NULL | soft FK -> scheduled_scans.id |
| dispatched_at | DateTime | NOT NULL | set when dispatched |
| completed_at | DateTime | nullable | set when process exits |
| status | String(16) | NOT NULL | pending/running/completed/failed |
| scan_output_path | Text | nullable | path to scan output directory |
| scan_id | String(64) | nullable | null until scan completes |

## run_schedule(argv) Entrypoint Signature (for Plan 02 import reference)

```python
# quirk/cli/schedule_cmd.py
def run_schedule(argv: list[str]) -> None:
    """Main entrypoint for `quirk schedule` subcommands.

    argv = sys.argv[2:] — does NOT include 'quirk' or 'schedule'.
    """
```

## scheduler Interception Block Status (for Plan 02)

The `scheduler` interception block is already in `run_scan.py`:

```python
# --- scheduler subcommand: intercept before scan argparse (Phase 63 SCHED-02) ---
if len(_sys.argv) > 1 and _sys.argv[1] == "scheduler":
    from quirk.cli.scheduler_cmd import run_scheduler
    run_scheduler(_sys.argv[2:])
    return
```

**Plan 02 only needs to ship `quirk/cli/scheduler_cmd.py` with `run_scheduler(argv)` — no further `run_scan.py` edits needed.**

## Task Commits

1. **Task 1: Add croniter dep, ORM models, migration helper, test stubs** - `d1a2e98` (feat)
2. **Task 2: Implement schedule_cmd.py CRUD, wire run_scan.py** - `8356724` (feat)

## Files Created/Modified

- `quirk/models.py` - Appended ScheduledScan and ScheduledRun ORM models
- `quirk/db.py` - Added _ensure_scheduled_tables() and called from init_db()
- `pyproject.toml` - Added croniter>=1.4.0 to [dashboard] optional extra
- `quirk/cli/schedule_cmd.py` - New: full CRUD CLI implementation
- `run_scan.py` - Added schedule and scheduler interception blocks
- `tests/test_schedule_cmd.py` - New: 7 tests, all passing

## Decisions Made

- croniter>=1.4.0 placed in `[dashboard]` optional extra, not base deps — scheduling is dashboard-tier feature (D-01)
- `scheduler` interception block pre-wired in Plan 01 even though `scheduler_cmd.py` ships in Plan 02; lazy import inside the `if` block means no ImportError at this stage
- Name validation via `re.match(r'^[A-Za-z0-9_\-\.]{1,255}$')` before INSERT prevents path traversal (T-63-02) since schedule name becomes a path fragment in Plan 02 dispatch output directory
- IntegrityError caught with fixed string "Schedule '{name}' already exists" — never `f"...: {exc}"` to avoid LEAK-02 pattern

## Deviations from Plan

None — plan executed exactly as written. All security mitigations (T-63-01, T-63-02, T-63-03) were part of the plan specification and implemented verbatim.

## Issues Encountered

croniter not installed for Python 3.14 (Homebrew system package) — installed with `--break-system-packages` flag. croniter 6.2.2 (satisfies >=1.4.0 requirement) is now available for tests.

## Known Stubs

None — all CLI subcommands are fully implemented. The `scheduler` interception block references `quirk.cli.scheduler_cmd` (not yet created), but the lazy import means no error until `quirk scheduler` is actually invoked. This is intentional per plan design.

## Threat Flags

No new network endpoints or auth paths introduced in this plan. CLI only; all new surface (--config flag accepting arbitrary DB path) is within the existing operator trust boundary (T-63-05 accepted).

## Next Phase Readiness

- Plan 02 (`63-02`): implement `quirk/cli/scheduler_cmd.py` with `run_scheduler(argv)` dispatch loop; `run_scan.py` interception block already in place
- Plan 03 (`63-03`): implement `/api/schedules` FastAPI routes and dashboard `/schedules` page; `ScheduledScan`/`ScheduledRun` models and `get_session` already available
- No blockers for Plan 02 or Plan 03

## Self-Check: PASSED

All files present, both commits verified, 7 tests passing.

---
*Phase: 63-scheduled-continuous-scanning*
*Completed: 2026-05-10*
