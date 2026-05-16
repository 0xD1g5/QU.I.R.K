# Phase 63: Scheduled / Continuous Scanning - Context

**Gathered:** 2026-05-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 63 transforms QUIRK from a one-shot CLI tool into a continuously-running posture monitor. Three concrete deliverables:

1. **CLI scheduling layer** — `quirk schedule add/list/enable/disable/remove` subcommands that persist schedule rows to a new `scheduled_scans` SQLite table.
2. **Long-running dispatcher** — `quirk scheduler run` that loops every 60 seconds, checks for due schedules, and dispatches them as subprocess invocations of `quirk`.
3. **Dashboard `/schedules` route** — lists all scheduled scans with status + next-run time and exposes enable/disable toggles via a PATCH endpoint (first writable dashboard route, protected by Phase 58 bearer auth).

**In scope:** `scheduled_scans` table, `scheduled_runs` table, CLI subcommands, scheduler dispatcher, `/api/schedules` FastAPI route, dashboard `/schedules` page, `croniter` pip dependency.

**Out of scope:** Resumable partial-failure scans (Phase 67 soft dep — scheduler dispatches full scans until Phase 67 lands), trend visualization (Phase 64), dashboard-initiated ad-hoc scans (Phase 65), multi-user schedule ownership, notification/alerting on scan failure, distributed scheduler mode.

</domain>

<decisions>
## Implementation Decisions

### D-01: Cron Parsing Library

Use `croniter` (pip dep, MIT license, no transitive extras). It is the de facto Python cron expression parser — parses standard 5-field cron expressions and returns next-run datetime iterators. Do NOT use `APScheduler` (full framework, heavier dependency tree) or a custom parser (error-prone, regex-based cron parsing is well-understood but subtle). Add `croniter>=1.4.0` to the `[dashboard]` optional extra in `pyproject.toml` since it's only needed when running the scheduler.

### D-02: Dispatcher Mechanism

`quirk scheduler run` dispatches each due schedule by invoking `quirk` as a **subprocess** (via `subprocess.Popen`). This keeps dispatch crash-isolated — a failed scan does not crash the scheduler — and reuses the full CLI code path unchanged (same config, same scan pipeline, same output). Do NOT attempt to import `run_scan.main()` directly; that would introduce state-sharing risks between concurrent dispatches. Pass `--config`, `--target`, `--profile`, and `--output` flags to the subprocess.

### D-03: Run History Table

Create a **separate `scheduled_runs` table** (not just status columns on `scheduled_scans`). Each row records one dispatch: `schedule_id` (FK), `dispatched_at`, `completed_at`, `status` (pending/running/completed/failed), `scan_output_path`, and `scan_id` (FK to `crypto_endpoints.scan_run_id` or equivalent — null until scan completes). This enables:
- Per-dispatch history for the dashboard listing
- Future Phase 64 trend correlation via `scan_id`
- "Last N runs" queries without destroying the current-status column

### D-04: Dashboard Mutability (Enable/Disable Toggles)

This phase adds the **first writable dashboard API route**. The architecture previously marked the dashboard as "strictly read-only"; Phase 58 bearer auth makes mutating routes safe. Implement:
- `GET /api/schedules` — list all schedules with last-run status
- `POST /api/schedules` — create a schedule (alternative to CLI for dashboard-only operators)
- `PATCH /api/schedules/{id}` — update `enabled` flag (the toggle endpoint)
- `DELETE /api/schedules/{id}` — remove a schedule

All mutating routes (`POST`, `PATCH`, `DELETE`) require the Phase 58 bearer token + CSRF double-submit cookie. Read `quirk/dashboard/api/routes/scan.py` and the Phase 58 context for the exact auth dependency pattern.

### D-05: Scheduler Process Model

`quirk scheduler run` uses a **simple 60-second sleep-loop** (not asyncio, not threading):

```python
while True:
    check_and_dispatch_due_schedules(db)
    time.sleep(60)
```

Each iteration: open a DB session, query `scheduled_scans WHERE enabled=1`, compute `next_run_at` from `croniter`, dispatch any that are past due, update `scheduled_runs` status, close session. One-minute polling granularity is appropriate for crypto posture scans (no sub-minute scheduling use case). Async/threading adds complexity with no benefit.

### D-06: `next_run_at` Computation

`next_run_at` is computed on-the-fly at dispatch-check time using `croniter(cron_expr, last_run_at).get_next(datetime)`. Store `last_run_at` on the `scheduled_scans` row (updated when dispatch starts). Recompute `next_run_at` in the API response — do NOT store it as a persistent column (it goes stale the moment `last_run_at` changes).

### D-07: CLI Subcommand Pattern

Follow the existing `run_scan.py` interception pattern — intercept `quirk schedule` before argparse:

```python
if len(_sys.argv) > 1 and _sys.argv[1] == "schedule":
    from quirk.cli.schedule_cmd import run_schedule
    run_schedule(_sys.argv[2:])
    return

if len(_sys.argv) > 1 and _sys.argv[1] == "scheduler":
    from quirk.cli.scheduler_cmd import run_scheduler
    run_scheduler(_sys.argv[2:])
    return
```

New files: `quirk/cli/schedule_cmd.py` (CRUD subcommands) and `quirk/cli/scheduler_cmd.py` (the dispatcher loop).

### Claude's Discretion

- Output directory for dispatched scans: use `output/scheduled/{schedule_name}/{timestamp}/` — keeps scheduled output separate from interactive scan output.
- Signal handling for `quirk scheduler run`: catch `SIGINT`/`SIGTERM`, set a stop flag, wait for in-flight subprocess to complete or timeout (30s) before exiting cleanly.
- `quirk schedule list` format: Rich table via `quirk/logging_util.py` Logger, same pattern as existing CLI output.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase Requirements
- `.planning/REQUIREMENTS.md` §SCHED-01, §SCHED-02, §SCHED-03 — exact acceptance criteria for this phase
- `.planning/ROADMAP.md` §Phase 63 — goal statement, success criteria, UI hint

### Database and ORM Patterns
- `quirk/models.py` — SQLAlchemy declarative pattern (Base, Column types, index patterns); new `ScheduledScan` and `ScheduledRun` models must follow this style
- `quirk/db.py` — `init_db()`, `get_session()` patterns; new tables must be registered here

### CLI Subcommand Patterns
- `run_scan.py` lines 191–240 — the `if _sys.argv[1] == "..."` interception pattern for `init`, `serve`, `doctor` subcommands; `schedule` and `scheduler` follow this exactly
- `quirk/cli/init_cmd.py` — minimal CLI module pattern (argparse + main function)
- `quirk/cli/doctor_cmd.py` — slightly more complex CLI module with rich output

### Dashboard API Patterns
- `quirk/dashboard/api/routes/scan.py` — primary reference for FastAPI route structure, DB session dependency, Pydantic response schemas, error handling
- `quirk/dashboard/api/routes/trends.py` — secondary reference for data-aggregation route pattern
- `quirk/dashboard/api/deps.py` — DB session dependency injection pattern
- `quirk/dashboard/api/schemas.py` — Pydantic schema location and style

### Authentication (for Mutating Routes)
- `.planning/phases/58-dashboard-api-hardening/58-CONTEXT.md` — bearer token + CSRF double-submit decisions; all `POST/PATCH/DELETE /api/schedules*` routes MUST use the same auth dependency
- `.planning/phases/58-dashboard-api-hardening/58-01-PLAN.md` — bearer auth implementation details

### Frontend Patterns
- `src/dashboard/src/hooks/` — existing cancellation-safe data-fetch hook pattern (Phase 62); new `useSchedules` hook MUST follow the `let cancelled = false` + cleanup return pattern
- `src/dashboard/src/pages/` — page component structure (e.g., `findings.tsx`, `roadmap.tsx`); new `schedules.tsx` follows this pattern
- `src/dashboard/src/App.tsx` — route registration; add `/schedules` route here

### External Library
- `croniter` PyPI package — cron expression parsing; `croniter(expr, base_dt).get_next(datetime)` for next-run computation

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `quirk/logging_util.py` Logger — Rich-based console output; use for `quirk schedule list` table rendering, same as CLI scan output
- `quirk/db.py get_session()` — context-managed SQLAlchemy session; use in both CLI CRUD commands and the dispatcher loop
- `quirk/dashboard/api/deps.py` — `get_db()` FastAPI dependency; reuse in new `/api/schedules` routes without modification
- `src/dashboard/src/hooks/useScanData.ts` — cancellation-safe fetch pattern to replicate in new `useSchedules.ts` hook

### Established Patterns
- **CLI interception:** All subcommands (`init`, `serve`, `doctor`) are intercepted before argparse via `if _sys.argv[1] == "..."` in `run_scan.py:main()` — `schedule` and `scheduler` must follow this, not be added as argparse subparsers
- **Scan output path:** Interactive scans write to `cfg.output.path` (from config YAML); dispatched scans should use a deterministic path: `output/scheduled/{name}/{YYYYMMDD-HHMMSS}/`
- **SQLAlchemy model registration:** New models are imported in `quirk/db.py` (see `Base.metadata.create_all(engine)`) — both `ScheduledScan` and `ScheduledRun` must be imported there
- **Route mounting:** New route module is imported in `quirk/dashboard/api/app.py` and included with `app.include_router()`

### Integration Points
- `run_scan.py:main()` — two new interception blocks (`schedule`, `scheduler`) before existing argparse block
- `quirk/models.py` — two new ORM models appended
- `quirk/db.py` — `init_db()` must import new models so `create_all()` creates their tables
- `quirk/dashboard/api/app.py` — include new schedules router
- `src/dashboard/src/App.tsx` — add `/schedules` route
- `src/dashboard/src/components/sidebar.tsx` — add "Schedules" nav item

</code_context>

<specifics>
## Specific Ideas

- Success criterion 1 verbatim: `quirk schedule add --name "weekly-prod" --cron "0 2 * * 1" --target prod.example.com --profile balanced` → row in `scheduled_scans` → visible via `quirk schedule list`
- Success criterion 2 verbatim: `quirk scheduler run` dispatches at cron time, writes results to standard scan output path, surfaces `pending/running/completed/failed` to dashboard `/schedules`
- Success criterion 3 verbatim: dashboard `/schedules` lists name, target, profile, cron expression, next-run time, last-run timestamp + status, with enable/disable toggles that round-trip to backend
- Phase 67 is a soft dependency (resumable scans) — scheduler dispatches full scans in Phase 63; the `scheduled_runs.status = "failed"` path is sufficient for now

</specifics>

<deferred>
## Deferred Ideas

- **Notification on failure** — email/webhook alert when a scheduled scan fails; belongs in a future notification phase
- **Distributed scheduler** — multiple QUIRK instances competing for schedule dispatch (leadership election); belongs in a future SaaS/multi-tenant phase
- **Sub-minute scheduling** — no known use case; sleep-loop granularity is 60s by design
- **Resumable scheduled scans** — Phase 67 will add `--resume` flag; Phase 63 scheduler gains `--resume` support as a Phase 67 integration task, not here
- **Dashboard-initiated ad-hoc scheduling** — Phase 65 (dashboard-initiated scan) covers one-shot dispatch; Phase 63 only covers recurrence

None — discussion stayed within phase scope (auto mode)

</deferred>

---

*Phase: 63-scheduled-continuous-scanning*
*Context gathered: 2026-05-10*
