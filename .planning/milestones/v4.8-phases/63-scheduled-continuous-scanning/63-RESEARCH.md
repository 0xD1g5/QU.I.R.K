# Phase 63: Scheduled / Continuous Scanning — Research

**Researched:** 2026-05-10
**Domain:** Python scheduler loop, SQLAlchemy ORM, FastAPI CRUD routes, React hooks
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01: Cron Parsing Library**
Use `croniter>=1.4.0` (MIT, no transitive extras). Do NOT use APScheduler or a custom parser.
Add to `[dashboard]` optional extra in `pyproject.toml`.

**D-02: Dispatcher Mechanism**
`quirk scheduler run` dispatches each due schedule via `subprocess.Popen`. Do NOT import
`run_scan.main()` directly. Pass `--config`, `--target`, `--profile`, `--output` flags.

**D-03: Run History Table**
Create a separate `scheduled_runs` table with `schedule_id` (FK), `dispatched_at`,
`completed_at`, `status` (pending/running/completed/failed), `scan_output_path`, `scan_id`.

**D-04: Dashboard Mutability**
Four routes: `GET`, `POST`, `PATCH /api/schedules/{id}`, `DELETE /api/schedules/{id}`.
All mutating routes require Phase 58 bearer token + CSRF double-submit header.

**D-05: Scheduler Process Model**
Simple 60-second sleep-loop (`while True: ... time.sleep(60)`). No asyncio, no threading.
One-minute polling granularity is intentional.

**D-06: `next_run_at` Computation**
Computed on-the-fly via `croniter(cron_expr, last_run_at).get_next(datetime)`.
Store `last_run_at` on `scheduled_scans`. Do NOT store `next_run_at` as a persistent column.

**D-07: CLI Subcommand Pattern**
Intercept via `if _sys.argv[1] == "schedule":` and `if _sys.argv[1] == "scheduler":` in
`run_scan.py:main()` before argparse, exactly like `init`, `serve`, `compliance`.
New files: `quirk/cli/schedule_cmd.py` and `quirk/cli/scheduler_cmd.py`.

### Claude's Discretion

- Output directory for dispatched scans: `output/scheduled/{schedule_name}/{timestamp}/`
- Signal handling: catch `SIGINT`/`SIGTERM`, set a stop flag, wait up to 30s before exit
- `quirk schedule list` format: Rich table via Logger, same pattern as existing CLI output

### Deferred Ideas (OUT OF SCOPE)

- Notification on failure (email/webhook)
- Distributed scheduler (leadership election)
- Sub-minute scheduling
- Resumable scheduled scans (Phase 67 integration)
- Dashboard-initiated ad-hoc scheduling (Phase 65)
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SCHED-01 | `quirk schedule add --name <X> --cron <expr> --target <Y>` persists to `scheduled_scans` SQLite table with cron expr, target spec, profile, and enabled flag; visible via `quirk schedule list` | D-01 (croniter validation), D-07 (CLI interception), D-03 (DB schema), `quirk/models.py` pattern |
| SCHED-02 | `quirk scheduler run` dispatches on cron time, writes to standard output path, surfaces `pending/running/completed/failed` to dashboard | D-02 (subprocess dispatch), D-05 (sleep-loop), D-06 (next_run_at), D-03 (scheduled_runs table) |
| SCHED-03 | Dashboard `/schedules` lists all schedules with name/target/profile/cron/next-run/last-run+status and enable/disable toggles that round-trip to backend | D-04 (FastAPI CRUD routes), Phase 58 auth pattern, React hook cancellation pattern from Phase 62 |
</phase_requirements>

---

## Summary

Phase 63 adds three integrated components to QUIRK: a CLI CRUD layer for managing scan
schedules, a long-running dispatcher process that reads from SQLite and invokes `quirk` as
a subprocess at cron-scheduled times, and the first writable dashboard route that exposes
schedule management to browser operators.

All three components reuse existing patterns established in previous phases. The CLI
subcommand pattern (intercepting `_sys.argv[1]` before argparse) is used by `init`,
`serve`, `compliance`, and `qramm`. The SQLAlchemy model pattern (Base, Column types,
`_ensure_*` migration helpers in `db.py`) is used by every phase since v3. The FastAPI
route pattern with bearer auth + CSRF guard is used by `qramm.py` and `pdf.py`. The React
cancellation-safe hook pattern is established by Phase 62.

The key architectural novelty is that this phase introduces the first **mutating** dashboard
routes (`POST`, `PATCH`, `DELETE /api/schedules`). The Phase 58 auth middleware (`require_auth`
+ `require_csrf`) is already in place; the schedules router simply applies both as
`APIRouter(dependencies=[Depends(require_auth), Depends(require_csrf)])`, mirroring the
QRAMM router pattern exactly.

**Primary recommendation:** Follow the QRAMM router as the primary template for the API
layer; follow `useScanData.ts` as the template for the React hook; follow `doctor_cmd.py`
and `qramm_cmd.py` as CLI module templates.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Schedule persistence (CRUD) | Backend / SQLite | — | Schedule metadata is server state; CLI and API both write to the same DB |
| Cron next-run computation | Backend (API response + dispatcher) | — | croniter runs Python-side; next_run_at is computed at query time, never stored |
| Scan dispatch | CLI process (scheduler_cmd) | — | subprocess.Popen keeps crash isolation; not an API concern |
| Run history recording | Backend / SQLite | — | scheduled_runs rows written by dispatcher process |
| Schedule list + status display | Frontend (React) | Backend (GET /api/schedules) | React fetches, backend queries scheduled_scans JOIN last scheduled_run |
| Enable/disable toggle | Frontend (React) | Backend (PATCH /api/schedules/{id}) | Toggle is a UI gesture; backend enforces auth + validates enabled flag |
| Auth enforcement | Backend (FastAPI middleware) | — | Phase 58 bearer + CSRF; no auth logic in frontend |

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| croniter | 6.2.2 (latest) | 5-field cron expression parsing; `get_next(datetime)`, `is_valid()` | De facto Python cron parser; MIT; no transitive deps; D-01 locked |
| SQLAlchemy | >=2.0 (already in project) | ORM for `scheduled_scans` and `scheduled_runs` tables | Project standard since v3; `declarative_base` pattern already used |
| FastAPI | >=0.128.8 (already in project) | `/api/schedules` CRUD routes | Project dashboard standard; already in `[dashboard]` extra |
| React + TypeScript | already in project | `useSchedules` hook + `schedules.tsx` page | Project frontend standard |

**Version verification (registry):**
`croniter` latest stable: 6.2.2 (published 2025). CONTEXT.md specifies `>=1.4.0`; pip will
install 6.2.2. The `>=1.4.0` floor ensures `is_valid()` classmethod is available (added in
1.x). [VERIFIED: pip3 index versions croniter]

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| signal (stdlib) | Python stdlib | SIGTERM/SIGINT handler in scheduler loop | Graceful shutdown of `quirk scheduler run` |
| subprocess (stdlib) | Python stdlib | Popen for dispatching `quirk` as child process | D-02: crash-isolated dispatch |
| time (stdlib) | Python stdlib | `time.sleep(60)` in the dispatcher loop | D-05: 60s polling granularity |
| lucide-react | already in project | Icon for "Schedules" nav item (Calendar or Clock icon) | Sidebar NAV_ITEMS entry |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| croniter | APScheduler | APScheduler is a full scheduling framework (heavier, manages its own thread pool). D-01 locks croniter. |
| subprocess.Popen | Direct function call to run_scan.main() | Direct call shares process state; a scan crash would crash the scheduler. D-02 locks subprocess. |
| sleep-loop | asyncio event loop | Adds complexity with no benefit for 60s granularity. D-05 locks sleep-loop. |
| SQLite scheduled_runs | Status columns on scheduled_scans | Destroys per-dispatch history; can't support Phase 64 trend correlation. D-03 locks separate table. |

**Installation:**
```bash
pip install "croniter>=1.4.0"
```
Add to `pyproject.toml` `[project.optional-dependencies]` under `dashboard`:
```toml
dashboard = [
    "fastapi>=0.128.8",
    "uvicorn[standard]>=0.39.0",
    "python-multipart>=0.0.20",
    "playwright>=1.58.0",
    "croniter>=1.4.0",
]
```

---

## Architecture Patterns

### System Architecture Diagram

```
                    ┌─────────────────────────────────────────┐
                    │            OPERATOR ENTRY POINTS         │
                    └──────────────┬──────────────────────────┘
                                   │
              ┌────────────────────┼────────────────────────────┐
              │                    │                            │
   quirk schedule add/list/...   quirk scheduler run     Dashboard /schedules
              │                    │                            │
              ▼                    ▼                            ▼
  ┌───────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐
  │ schedule_cmd.py   │  │  scheduler_cmd.py     │  │  React schedules.tsx │
  │ (argparse CRUD)   │  │  60s sleep-loop       │  │  useSchedules hook   │
  └────────┬──────────┘  └──────────┬───────────┘  └──────────┬───────────┘
           │                        │                          │
           │ SQLAlchemy             │ croniter.get_next()      │ fetchApi()
           │ get_session()          │ subprocess.Popen()       │ GET/PATCH/DELETE
           ▼                        ▼                          ▼
  ┌────────────────────────────────────────────────────────────────────────┐
  │                          SQLite (quirk.db)                             │
  │  ┌─────────────────────────────┐  ┌──────────────────────────────────┐ │
  │  │ scheduled_scans             │  │ scheduled_runs                   │ │
  │  │ id, name, target, profile   │  │ id, schedule_id, dispatched_at   │ │
  │  │ cron_expr, enabled          │  │ completed_at, status             │ │
  │  │ last_run_at, created_at     │  │ scan_output_path, scan_id        │ │
  │  └─────────────────────────────┘  └──────────────────────────────────┘ │
  └────────────────────────────────────────────────────────────────────────┘
           ▲
           │ get_db() Depends()
  ┌────────┴──────────────────────────────────────────────────────────────┐
  │              FastAPI /api/schedules router                            │
  │  GET list ──────────────────────────────────────────┐                │
  │  POST create   ─┬─ require_auth + require_csrf ──┐  │                │
  │  PATCH enable   ─┤                               ▼  ▼                │
  │  DELETE remove  ─┘             Pydantic schemas (inline, per D-11)   │
  └───────────────────────────────────────────────────────────────────────┘
```

### Recommended Project Structure

```
quirk/
├── cli/
│   ├── schedule_cmd.py     # new: quirk schedule add/list/enable/disable/remove
│   └── scheduler_cmd.py    # new: quirk scheduler run (60s sleep-loop dispatcher)
├── models.py               # append ScheduledScan + ScheduledRun ORM models
├── db.py                   # append _ensure_scheduled_tables() call in init_db()
└── dashboard/api/
    └── routes/
        └── schedules.py    # new: GET/POST/PATCH/DELETE /api/schedules routes

src/dashboard/src/
├── hooks/
│   └── useSchedules.ts     # new: cancellation-safe schedules fetch hook
├── pages/
│   └── schedules.tsx       # new: /schedules React page
├── components/
│   └── sidebar.tsx         # modified: add Schedules nav item
└── App.tsx                 # modified: add /schedules route
```

### Pattern 1: SQLAlchemy ORM Models (ScheduledScan + ScheduledRun)

**What:** Two new ORM model classes appended to `quirk/models.py`, following the exact
`Column`/`Base` pattern of `QRAMMSession` and `QRAMMProfile`.

**When to use:** Any new table that needs to be managed by `init_db()`.

```python
# Source: verified from quirk/models.py existing pattern
class ScheduledScan(Base):
    __tablename__ = "scheduled_scans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True)
    cron_expr = Column(String(128), nullable=False)
    target = Column(String(512), nullable=False)
    profile = Column(String(64), nullable=True)       # None = "balanced"
    enabled = Column(Boolean, default=True)
    last_run_at = Column(DateTime, nullable=True)     # None = never run
    created_at = Column(DateTime, nullable=False)


class ScheduledRun(Base):
    __tablename__ = "scheduled_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    schedule_id = Column(Integer, nullable=False)     # FK -> scheduled_scans.id
    dispatched_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    status = Column(String(16), nullable=False)       # pending/running/completed/failed
    scan_output_path = Column(Text, nullable=True)
    scan_id = Column(String(64), nullable=True)       # FK to scan run, null until complete
```

[VERIFIED: quirk/models.py existing Column/Base pattern]

### Pattern 2: DB Migration Helper (_ensure_scheduled_tables)

**What:** Register new tables in `init_db()` using `Base.metadata.create_all(checkfirst=True)`.
Since `ScheduledScan` and `ScheduledRun` are fully new tables (not new columns on an existing
table), they use `create_all(checkfirst=True)` like `_ensure_qramm_tables()` — not the
`ALTER TABLE` pattern used for column additions.

**When to use:** New tables only. Column additions to existing tables use the `ALTER TABLE`
inspector pattern.

```python
# Source: verified from quirk/db.py _ensure_qramm_tables() pattern
def _ensure_scheduled_tables(engine) -> None:
    """Phase 63 SCHED-01: create scheduled_scans and scheduled_runs tables if absent.

    Uses Base.metadata.create_all with checkfirst=True. ScheduledScan and
    ScheduledRun are registered on Base.metadata via import of quirk.models.
    """
    Base.metadata.create_all(engine, checkfirst=True)
```

Call site in `init_db()`:
```python
_ensure_scheduled_tables(engine)  # Phase 63 — SCHED-01
```

[VERIFIED: quirk/db.py _ensure_qramm_tables() pattern]

### Pattern 3: CLI Subcommand Interception

**What:** Two new `if _sys.argv[1] == "..."` blocks in `run_scan.py:main()`, inserted
**before** the existing argparse block. Order within the interception chain does not matter
(they are elif-equivalent guards), but by convention insert after the last existing
interception block (`compliance`).

**When to use:** Any new CLI subcommand that would conflict with the scan argparse positional
arguments.

```python
# Source: verified from run_scan.py:main() existing pattern (lines 191-259)
# Insert before the scan argparse block:

if len(_sys.argv) > 1 and _sys.argv[1] == "schedule":
    from quirk.cli.schedule_cmd import run_schedule
    run_schedule(_sys.argv[2:])
    return

if len(_sys.argv) > 1 and _sys.argv[1] == "scheduler":
    from quirk.cli.scheduler_cmd import run_scheduler
    run_scheduler(_sys.argv[2:])
    return
```

[VERIFIED: run_scan.py lines 191-259 existing interception pattern]

### Pattern 4: FastAPI Router with Auth + CSRF (Mutating Routes)

**What:** The schedules router follows the QRAMM router pattern exactly — `APIRouter` with
`dependencies=[Depends(require_auth), Depends(require_csrf)]`. This applies auth + CSRF to
ALL routes on the router (GET included, for the schedules router). See Note below about
GET auth.

**When to use:** Any router containing mutating routes in the QUIRK dashboard.

```python
# Source: verified from quirk/dashboard/api/routes/qramm.py
from fastapi import APIRouter, Depends
from quirk.dashboard.api.middleware.auth import require_auth
from quirk.dashboard.api.middleware.csrf import require_csrf

# Option A: auth + csrf on ALL router routes (simpler, matches QRAMM pattern)
router = APIRouter(dependencies=[Depends(require_auth), Depends(require_csrf)])

# Option B: auth on router, csrf only on mutating routes via per-route Depends
# (csrf.py's require_csrf already passes GET/HEAD/OPTIONS unconditionally,
#  so Option A is functionally identical to Option B for GET requests)
```

Note: `require_csrf` already passes `GET`/`HEAD`/`OPTIONS` unconditionally (verified in
`quirk/dashboard/api/middleware/csrf.py` line 22–27). Applying it at router level is safe
for the GET list endpoint.

[VERIFIED: quirk/dashboard/api/middleware/csrf.py, quirk/dashboard/api/routes/qramm.py]

### Pattern 5: Croniter Next-Run Computation

**What:** Use `croniter(cron_expr, base_dt).get_next(datetime)` to compute the next
scheduled run time from the last run time. Use `croniter.is_valid(cron_expr)` to validate
user-provided expressions at `schedule add` time.

**When to use:** Anywhere `next_run_at` needs to be computed or a cron expression needs
validation.

```python
# Source: Context7 /pallets-eco/croniter docs
from croniter import croniter
from datetime import datetime, timezone

# Validation at add time:
if not croniter.is_valid(cron_expr):
    raise ValueError(f"Invalid cron expression: {cron_expr!r}")

# Compute next run (use last_run_at, or datetime.now() if never run):
base = schedule.last_run_at or datetime.now(tz=timezone.utc)
next_run = croniter(schedule.cron_expr, base).get_next(datetime)

# Check if due:
if datetime.now(tz=timezone.utc) >= next_run:
    dispatch(schedule)
```

[VERIFIED: Context7 /pallets-eco/croniter, croniter 6.2.2 available via pip]

### Pattern 6: Subprocess Dispatch with Status Tracking

**What:** The dispatcher loop opens a DB session, finds due schedules, creates a
`scheduled_runs` row with `status="pending"`, calls `subprocess.Popen`, updates to
`status="running"`, then polls `proc.poll()` or calls `proc.wait()` to detect completion
and update to `status="completed"` or `status="failed"`.

**When to use:** Inside `quirk/cli/scheduler_cmd.py`'s dispatch loop.

```python
# Source: Python stdlib subprocess docs [ASSUMED for exact Popen flags]
import subprocess
import sys
from pathlib import Path

def dispatch_schedule(schedule, run_row, db):
    output_dir = Path(f"output/scheduled/{schedule.name}/{run_row.dispatched_at:%Y%m%d-%H%M%S}")
    output_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable, "-m", "run_scan",  # or: shutil.which("quirk")
        "--config", "config.yaml",
        "--target", schedule.target,
        "--profile", schedule.profile or "balanced",
        "--output", str(output_dir),
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    run_row.status = "running"
    db.commit()

    stdout, stderr = proc.communicate()
    if proc.returncode == 0:
        run_row.status = "completed"
    else:
        run_row.status = "failed"
    run_row.completed_at = datetime.now(tz=timezone.utc)
    run_row.scan_output_path = str(output_dir)
    db.commit()
```

[ASSUMED: exact Popen invocation shape; subprocess module availability verified on macOS Python 3.14]

### Pattern 7: Signal Handling in Long-Running CLI

**What:** `quirk scheduler run` must respond to SIGINT/SIGTERM for clean shutdown. Use a
module-level `threading.Event` or simple boolean flag set in the signal handler.

```python
# Source: Python stdlib signal module [VERIFIED: signal.SIGTERM + signal.SIGINT available on darwin]
import signal
import time

_stop_flag = False

def _handle_signal(signum, frame):
    global _stop_flag
    _stop_flag = True

signal.signal(signal.SIGINT, _handle_signal)
signal.signal(signal.SIGTERM, _handle_signal)

while not _stop_flag:
    check_and_dispatch_due_schedules(db)
    # Sleep in 1s increments to stay responsive to _stop_flag
    for _ in range(60):
        if _stop_flag:
            break
        time.sleep(1)
```

[VERIFIED: signal.SIGTERM and signal.SIGINT available on darwin Python 3.14]

### Pattern 8: React Cancellation-Safe Hook (useSchedules)

**What:** Mirror `useScanData.ts` exactly — `let cancelled = false`, check `!cancelled`
before every `setState` call, return `() => { cancelled = true }` from `useEffect`.

```typescript
// Source: verified from src/dashboard/src/hooks/useScanData.ts (Phase 62 pattern)
export function useSchedules(): UseSchedulesResult {
  const [data, setData] = useState<ScheduleListResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setData(null)
    setLoading(true)
    setError(null)

    async function fetchData() {
      try {
        const resp = await fetchApi("/api/schedules")
        if (!resp.ok) {
          if (!cancelled) setError(`API error: ${resp.status}`)
          return
        }
        const json: ScheduleListResponse = await resp.json()
        if (!cancelled) setData(json)
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load")
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    fetchData()
    return () => { cancelled = true }
  }, [])  // No dependency array items — schedules fetched on mount

  return { data, loading, error }
}
```

[VERIFIED: src/dashboard/src/hooks/useScanData.ts Phase 62 pattern]

### Pattern 9: Router Registration in app.py

Add the schedules router import and `include_router` call in `quirk/dashboard/api/app.py`,
following the existing pattern:

```python
# Source: verified from quirk/dashboard/api/app.py lines 22, 62-65
from quirk.dashboard.api.routes import health, pdf, qramm, scan, schedules, trends

# In create_app():
application.include_router(schedules.router, prefix="/api")
```

[VERIFIED: quirk/dashboard/api/app.py existing router registration pattern]

### Anti-Patterns to Avoid

- **Don't import `run_scan.main()` in the dispatcher:** Importing and calling the scan
  entrypoint directly shares process memory — a segfault or unhandled exception in one scan
  crashes the entire scheduler. Use `subprocess.Popen` (D-02).
- **Don't store `next_run_at` as a DB column:** It becomes stale the instant `last_run_at`
  changes. Compute it on-the-fly in the API response (D-06).
- **Don't use APScheduler or threading.Timer:** Adds a dependency tree and introduces
  thread-safety requirements for the SQLite session. The sleep-loop is simpler and correct
  for this use case (D-05).
- **Don't add a new argparse subparser for `schedule`:** The `schedule` subcommand conflicts
  with the scan argparse positional `target`. Must use the `_sys.argv[1]` interception pattern
  (D-07).
- **Don't use `expire_on_commit=True` in the dispatcher's session:** After `db.commit()`,
  ORM instances become expired and accessing attributes raises `DetachedInstanceError`. Set
  `expire_on_commit=False` in the dispatcher's sessionmaker (matching `get_session()` in
  `quirk/db.py`).
- **Don't apply `require_csrf` as a decorator on individual routes:** It must be a
  `Depends()` at the router level, matching the existing QRAMM pattern. The CSRF middleware
  already exempts GET/HEAD/OPTIONS internally.
- **Don't conditionally mount React components inside the schedules page:** QUIRK uses
  shadcn/ui + Recharts; the "no conditional mount" rule applies to chart children. Tables and
  toggle switches are not affected by this rule.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cron expression parsing | Custom regex parser | `croniter.is_valid()` + `croniter.get_next()` | Cron has 9+ edge-case field variants (last-day-of-month, step notation, named weekdays, etc.) |
| Next-run time calculation | Manual datetime arithmetic | `croniter(expr, base).get_next(datetime)` | DST transitions, month-end rollover, and step expressions are subtle to get right |
| Bearer token comparison | `==` string comparison | `hmac.compare_digest()` | Timing attack mitigation — already done in `require_auth` |
| Subprocess result parsing | Custom stdout parser | `proc.returncode` | Exit code 0 = success; non-zero = failure — no output parsing needed |
| Schedule uniqueness check | Manual SELECT before INSERT | `unique=True` on `scheduled_scans.name` column | Let SQLite enforce the constraint; catch `IntegrityError` and return 409 |

**Key insight:** Cron expression handling looks simple (it's just a string) but contains
significant edge-case complexity (7-field extensions, named days, hash expressions, DST).
`croniter` has 100+ releases handling these cases. Do not attempt to validate or parse cron
expressions without it.

---

## Common Pitfalls

### Pitfall 1: Timezone-Naive Datetime Comparison

**What goes wrong:** `croniter(expr, base).get_next(datetime)` returns a timezone-naive
`datetime` object. Comparing it with `datetime.now(tz=timezone.utc)` (timezone-aware) raises
`TypeError: can't compare offset-naive and offset-aware datetimes`.

**Why it happens:** `croniter` returns naive datetimes by default when given a naive base
datetime.

**How to avoid:** Consistently use timezone-naive datetimes throughout the dispatcher
(store UTC without tzinfo in SQLite, use `datetime.utcnow()` for comparison). Or use
`datetime.now()` without tz in the dispatch check. Pick one convention and apply it to
all columns in `scheduled_scans` and `scheduled_runs`.

**Warning signs:** `TypeError` in the dispatcher's `check_and_dispatch_due_schedules()`.

### Pitfall 2: SQLite WAL Mode and Concurrent Writes from Dispatcher + API

**What goes wrong:** The `quirk scheduler run` process writes to `scheduled_runs` while the
FastAPI server reads `scheduled_scans` + `scheduled_runs` for the `/api/schedules` GET route.
SQLite's default journal mode can cause `database is locked` errors under concurrent write
from two processes.

**Why it happens:** SQLite has a single-writer model. Two processes holding write transactions
simultaneously will have one fail with `OperationalError: database is locked`.

**How to avoid:** Configure the dispatcher's engine with `connect_args={"timeout": 10}` to
retry on lock for up to 10 seconds before failing. The FastAPI server's `get_db()` already
uses `get_engine()` which sets `check_same_thread=False` but not a timeout. For the dispatcher,
use a short timeout to avoid infinite blocking.

**Warning signs:** `sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) database is locked`.

### Pitfall 3: Schedule Name Uniqueness Enforcement

**What goes wrong:** `quirk schedule add --name weekly-prod ...` called twice creates two
rows with the same name. Dashboard and list commands become confusing; next-run computation
is ambiguous.

**Why it happens:** SQLAlchemy's `create_all` creates the `UNIQUE` constraint on `name` only
on the first `init_db()` call. Existing DBs from before Phase 63 won't have the constraint.

**How to avoid:** Add `unique=True` to `ScheduledScan.name` Column, AND handle
`IntegrityError` in the `schedule add` CLI command with a user-friendly message. The
`_ensure_scheduled_tables()` call in `init_db()` uses `checkfirst=True` so new DBs get the
constraint; existing DBs that lack the column schema won't have the issue (the whole table
is new).

**Warning signs:** `sqlalchemy.exc.IntegrityError: UNIQUE constraint failed: scheduled_scans.name`.

### Pitfall 4: Dispatcher Leaves `status="running"` Rows After Crash

**What goes wrong:** If `quirk scheduler run` is killed (SIGKILL, OOM) while a dispatch is
in-flight, the `scheduled_runs` row remains `status="running"` indefinitely. Dashboard
shows perpetually "running" scans.

**Why it happens:** The status update to `completed`/`failed` happens after `proc.wait()`.
An abrupt kill has no chance to update the DB.

**How to avoid:** At dispatcher startup, query `scheduled_runs WHERE status IN ('pending',
'running')` older than a reasonable threshold (e.g., 2 hours) and mark them `failed` with
a note in `scan_output_path` like `"INTERRUPTED"`. This is a startup recovery check, not a
continuous cleanup.

**Warning signs:** Dashboard shows runs stuck in "running" state after a scheduler restart.

### Pitfall 5: `quirk` Binary Not on PATH in Subprocess Dispatch

**What goes wrong:** `subprocess.Popen(["quirk", ...])` fails with `FileNotFoundError` when
the dispatcher is run inside a virtualenv where the `quirk` entrypoint is not on the
system PATH.

**Why it happens:** `pyproject.toml` installs `quirk = "run_scan:main"` as a console script.
In a virtualenv, this is `venv/bin/quirk`, which may not be on `$PATH` in subprocesses.

**How to avoid:** Use `sys.executable` + `-m run_scan` (Python module invocation) or
`shutil.which("quirk")` with a fallback to `[sys.executable, "-m", "run_scan"]`. The `-m`
form works in any virtualenv where `run_scan` is a top-level module.

**Warning signs:** `FileNotFoundError: [Errno 2] No such file or directory: 'quirk'` in
dispatcher logs.

### Pitfall 6: React Toggle State Not Optimistically Updated

**What goes wrong:** Clicking enable/disable on the dashboard sends a `PATCH` request but
the toggle does not flip until the next GET poll. The UI feels sluggish.

**Why it happens:** Without optimistic updates, the UI waits for the PATCH response and then
refetches the list before re-rendering the toggle state.

**How to avoid:** After a successful `PATCH /api/schedules/{id}`, update the local `data`
state in the `useSchedules` hook before the next poll. Simple optimistic update: filter and
map the cached list to flip the `enabled` flag on the patched ID.

**Warning signs:** Toggle appears to "bounce back" or takes >500ms to visually confirm.

---

## Code Examples

### Verified: croniter basic usage

```python
# Source: Context7 /pallets-eco/croniter README
from croniter import croniter
from datetime import datetime

# Validate
croniter.is_valid('0 2 * * 1')   # True (every Monday at 02:00)
croniter.is_valid('0 wrong * *') # False

# Next run
base = datetime(2026, 5, 10, 0, 0, 0)  # last_run_at or now
next_run = croniter('0 2 * * 1', base).get_next(datetime)
# -> datetime(2026, 5, 11, 2, 0, 0)  (next Monday 02:00)
```

### Verified: Auth + CSRF router pattern (from qramm.py)

```python
# Source: verified from quirk/dashboard/api/routes/qramm.py line 37
from fastapi import APIRouter, Depends
from quirk.dashboard.api.middleware.auth import require_auth
from quirk.dashboard.api.middleware.csrf import require_csrf

router = APIRouter(dependencies=[Depends(require_auth), Depends(require_csrf)])
```

### Verified: _ensure_qramm_tables pattern (for _ensure_scheduled_tables)

```python
# Source: verified from quirk/db.py lines 214-225
def _ensure_scheduled_tables(engine) -> None:
    """Phase 63 SCHED-01: create scheduled_scans and scheduled_runs if absent."""
    Base.metadata.create_all(engine, checkfirst=True)
```

### Verified: CSRF header requirement in TestClient

```python
# Source: verified from tests/conftest.py line 110
# All requests to mutating routes must include X-Quirk-Request: 1
return TestClient(app, headers={"X-Quirk-Request": "1"})

# For toggle endpoint test:
resp = client.patch(
    "/api/schedules/1",
    json={"enabled": False},
    headers={"X-Quirk-Request": "1"},
)
assert resp.status_code == 200
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| APScheduler (v2 era Python schedulers) | croniter + sleep-loop | Project decision D-01/D-05 | Lighter dependency; no in-process thread pool |
| Global auth skip on GET routes | Per-router auth dependency (QRAMM pattern) | Phase 58 | All routes on schedules router are auth-gated |
| Dashboard read-only API | First writable routes (POST/PATCH/DELETE) | Phase 63 | CSRF guard is now exercised on a real use case |

**Deprecated/outdated:**
- `APScheduler`: overkill for single-instance QUIRK; adds `tzlocal`, `pytz`, and thread
  management overhead; not used in this project.
- Direct argparse subparsers for `schedule`: conflicts with scan positional args; the
  `_sys.argv[1]` interception is the established QUIRK pattern.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Exact `subprocess.Popen` invocation uses `[sys.executable, "-m", "run_scan", ...]` as the command | Pattern 6 (Subprocess Dispatch) | If the `quirk` entrypoint name differs from `run_scan`, the subprocess invocation fails. Low risk — `pyproject.toml` confirms `quirk = "run_scan:main"`. |
| A2 | SQLite WAL mode is not already configured; `timeout=10` is sufficient for write contention | Pitfall 2 | If contention is higher, operator may see intermittent errors. Mitigated by short-lived write transactions in the dispatcher. |

**If this table is empty:** All other claims were verified from codebase inspection or official sources.

---

## Open Questions (RESOLVED)

1. **config.yaml path for dispatched subprocesses** — RESOLVED in Plan 02 Task 1
   - Resolution: `quirk scheduler run` accepts `--config config.yaml`; DB path derived from config or `QUIRK_DB_PATH` env var. Subprocess receives `--config config_path` argument.

2. **`quirk schedule add` — does it need a `--config` flag?** — RESOLVED in Plan 01 Task 2
   - Resolution: `--config` is optional; resolution order is `QUIRK_DB_PATH` env var → `--config` path → `./quirk.db` fallback, matching `deps.py` priority order.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11+ | All | ✓ | 3.14.4 | — |
| croniter | Cron parsing | Not installed | 6.2.2 (available) | None — must install |
| signal module | Dispatcher shutdown | ✓ | stdlib | — |
| subprocess module | Scan dispatch | ✓ | stdlib | — |
| SQLAlchemy | ORM | ✓ | in project deps | — |
| FastAPI | Dashboard routes | ✓ | in [dashboard] extra | — |
| React/TypeScript | Frontend | ✓ | in project | — |

**Missing dependencies with no fallback:**
- `croniter` — must be added to `pyproject.toml [dashboard]` extra and installed

**Missing dependencies with fallback:**
- None

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (existing, `pyproject.toml testpaths = ["tests"]`) |
| Config file | `pyproject.toml [tool.pytest.ini_options]` |
| Quick run command | `pytest tests/test_schedule_cmd.py tests/test_scheduler_cmd.py tests/test_schedules_api.py -x` |
| Full suite command | `pytest tests/ -m "not slow and not live_infra"` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SCHED-01 | `schedule add` persists row with correct fields | unit | `pytest tests/test_schedule_cmd.py::test_schedule_add_persists -x` | ❌ Wave 0 |
| SCHED-01 | `schedule list` shows persisted row | unit | `pytest tests/test_schedule_cmd.py::test_schedule_list_shows_row -x` | ❌ Wave 0 |
| SCHED-01 | Invalid cron expression rejected at add | unit | `pytest tests/test_schedule_cmd.py::test_schedule_add_invalid_cron -x` | ❌ Wave 0 |
| SCHED-01 | GET /api/schedules returns 200 with list | unit | `pytest tests/test_schedules_api.py::test_get_schedules_empty -x` | ❌ Wave 0 |
| SCHED-01 | POST /api/schedules creates row, requires auth+csrf | unit | `pytest tests/test_schedules_api.py::test_post_schedule_creates -x` | ❌ Wave 0 |
| SCHED-02 | Dispatcher marks run as running then completed | unit | `pytest tests/test_scheduler_cmd.py::test_dispatch_lifecycle -x` | ❌ Wave 0 |
| SCHED-02 | Dispatcher skips disabled schedules | unit | `pytest tests/test_scheduler_cmd.py::test_disabled_schedule_skipped -x` | ❌ Wave 0 |
| SCHED-02 | Dispatcher recovers stale running rows on startup | unit | `pytest tests/test_scheduler_cmd.py::test_startup_recovery -x` | ❌ Wave 0 |
| SCHED-03 | PATCH /api/schedules/{id} flips enabled flag | unit | `pytest tests/test_schedules_api.py::test_patch_toggle_enabled -x` | ❌ Wave 0 |
| SCHED-03 | PATCH requires X-Quirk-Request header | unit | `pytest tests/test_schedules_api.py::test_patch_requires_csrf -x` | ❌ Wave 0 |
| SCHED-03 | GET /api/schedules includes next_run_at field | unit | `pytest tests/test_schedules_api.py::test_get_includes_next_run -x` | ❌ Wave 0 |
| SCHED-03 | Dashboard route introspection gate (no unprotected mutating routes) | unit | `pytest tests/test_api_auth.py::test_no_unprotected_mutating_routes -x` | ✅ existing |

### Sampling Rate
- **Per task commit:** `pytest tests/test_schedule_cmd.py tests/test_scheduler_cmd.py tests/test_schedules_api.py -x`
- **Per wave merge:** `pytest tests/ -m "not slow and not live_infra"`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_schedule_cmd.py` — covers SCHED-01 CLI CRUD commands
- [ ] `tests/test_scheduler_cmd.py` — covers SCHED-02 dispatcher loop logic
- [ ] `tests/test_schedules_api.py` — covers SCHED-01/03 API routes

*(Existing `tests/conftest.py::dashboard_client` fixture covers API test setup — no new conftest additions needed)*

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | Phase 58 `require_auth` bearer token — already implemented |
| V3 Session Management | no | No session cookies in QUIRK API |
| V4 Access Control | yes | All mutating routes require bearer token; CSRF header prevents CSRF attacks |
| V5 Input Validation | yes | croniter.is_valid() for cron expressions; Pydantic schemas for API request bodies |
| V6 Cryptography | no | No new crypto operations introduced |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Forged schedule POST from malicious page | Tampering | CSRF header `X-Quirk-Request: 1` (Phase 58 pattern) |
| Unauthenticated schedule deletion | Tampering | `require_auth` bearer token (Phase 58 pattern) |
| Cron expression injection (shell metacharacters) | Tampering | croniter.is_valid() rejects non-cron syntax; subprocess.Popen with list args (not shell=True) prevents shell injection |
| Path traversal in `--output` for dispatched scan | Tampering | Output path is programmatically constructed from `schedule.name` + timestamp; do not allow user-controlled path fragments in output path |
| Scheduler subprocess inheriting sensitive env vars | Information Disclosure | Popen does not strip env by default; acceptable for local single-user deployment; note in operator docs if needed |

---

## Sources

### Primary (HIGH confidence)
- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/quirk/models.py` — SQLAlchemy ORM model pattern verified
- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/quirk/db.py` — `init_db()`, `_ensure_qramm_tables()`, migration patterns verified
- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/run_scan.py` (lines 191-259) — CLI interception pattern verified
- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/quirk/dashboard/api/routes/qramm.py` — auth+csrf router pattern verified
- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/quirk/dashboard/api/middleware/auth.py` — require_auth implementation verified
- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/quirk/dashboard/api/middleware/csrf.py` — require_csrf implementation verified
- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/quirk/dashboard/api/app.py` — router registration pattern verified
- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/src/dashboard/src/hooks/useScanData.ts` — React cancellation pattern verified
- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/src/dashboard/src/App.tsx` — route registration pattern verified
- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/src/dashboard/src/components/sidebar.tsx` — NAV_ITEMS pattern verified
- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/tests/conftest.py` — dashboard_client fixture verified
- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/pyproject.toml` — optional deps structure verified
- Context7 `/pallets-eco/croniter` — `get_next(datetime)`, `is_valid()`, constructor signature
- `pip3 index versions croniter` — current version 6.2.2 [VERIFIED]
- `python3 -c "import signal; ..."` — SIGTERM/SIGINT available on darwin [VERIFIED]

### Secondary (MEDIUM confidence)
- `.planning/phases/63-scheduled-continuous-scanning/63-CONTEXT.md` — all implementation decisions (D-01 through D-07)
- `.planning/REQUIREMENTS.md` SCHED-01/02/03 — acceptance criteria

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — croniter version verified from registry; all other deps already in project
- Architecture: HIGH — all patterns verified from existing codebase; no new architectural concepts introduced
- Pitfalls: HIGH — derived from verified codebase patterns and known SQLite/subprocess/croniter behaviors

**Research date:** 2026-05-10
**Valid until:** 2026-08-10 (stable ecosystem; croniter, SQLAlchemy, FastAPI are stable)
