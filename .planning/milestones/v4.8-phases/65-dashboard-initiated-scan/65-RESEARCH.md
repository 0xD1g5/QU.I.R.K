# Phase 65: Dashboard-Initiated Scan - Research

**Researched:** 2026-05-13
**Domain:** FastAPI job dispatch, SQLAlchemy ORM, React polling hooks, subprocess lifecycle
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** `subprocess.Popen` dispatch — identical to Phase 63 scheduler pattern. Do NOT use `BackgroundTasks` or asyncio subprocess.
- **D-02:** `scan_jobs` SQLite table — 12 columns exactly as specified in CONTEXT.md (job_id PK, pid, status, current_stage, target, profile, calibration, enable_nmap, started_at, completed_at, scan_run_id, error_message).
- **D-03:** `--job-id <uuid>` optional argparse flag in `run_scan.py`; `quirk/cli/job_progress.py` helper; 7 stage names in order: discovery, tls, ssh, api, identity, data_at_rest, reports.
- **D-04:** `/api/jobs` router at `quirk/dashboard/api/routes/jobs.py` — POST (201), GET (200), DELETE (204); registered with prefix `/api` in `app.py`.
- **D-05:** `ScanSubmitRequest` + `JobStatusResponse` Pydantic schemas in `quirk/dashboard/api/schemas.py`; `stage_index` computed on backend.
- **D-06:** Form with four controls only: targets textarea, profile radio (quick/standard/deep), calibration radio (strict/balanced/lenient), enable_nmap checkbox.
- **D-07:** `useJobStatus` hook — 3s polling, `let cancelled = false` Phase 62 pattern exactly.
- **D-08:** Post-completion: `setSelectedScanId(scan_run_id)` then `navigate("/")`.
- **D-09:** "Cancel scan" button fires DELETE immediately (no dialog); navigate to `/scan/new` on 204 with inline notice.
- **D-10:** All `/api/jobs` routes: `require_auth`. POST + DELETE: also `require_csrf`. GET: `require_auth` only.
- **D-11:** Two React routes in `App.tsx`: `/scan/new` → `<ScanNewPage />`, `/scan/job/:jobId` → `<ScanJobPage />`. "New Scan" `Button variant="default"` at top of sidebar above nav links.
- **D-12:** FastAPI lifespan `@asynccontextmanager` in `app.py`; startup sweeps `running` jobs to `failed`; `create_app(db_path)` adds `db_path` parameter.

### Claude's Discretion

- Output directory for spawned scans: `output/jobs/{job_id}/`
- Signal handling: catch `ProcessLookupError` silently on `os.kill` (race condition)
- `stage_index` computed on backend from `current_stage` string
- Loading state on `/scan/job/:jobId`: use `<PageSpinner />` until first poll
- 404 from `GET /api/jobs/{job_id}`: show error state with link back, no silent redirect

### Deferred Ideas (OUT OF SCOPE)

- Per-scanner granular toggles
- WebSocket real-time streaming
- Multi-user job ownership
- Operator notification on completion
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| UI-SCAN-01 | `/scan/new` dashboard route — configure scan, validate against Pydantic schema, submit | D-05 ScanSubmitRequest schema; D-06 form fields; `ScanNewPage` component; `fetchApi` POST pattern |
| UI-SCAN-02 | Scan submission spawns scan with job ID; live status page polls stage transitions | D-01 Popen dispatch; D-03 `--job-id` flag + `job_progress.py`; D-07 `useJobStatus` hook |
| UI-SCAN-03 | On completion: navigate to results; new scan selectable from switcher | D-08 `setSelectedScanId` + `navigate("/")`; `useScanList` auto-refreshes; scan indistinguishable from CLI scan |
</phase_requirements>

---

## Summary

Phase 65 wires together three already-proven patterns in the QUIRK codebase:
(1) the Phase 63 `subprocess.Popen` scheduler dispatch pattern, adapted for ad-hoc job submission;
(2) the Phase 62 `let cancelled = false` polling hook, adapted for continuous job-status polling;
(3) the Phase 58 `require_auth` + `require_csrf` dependency injection, applied to the new `/api/jobs` router.

The primary new work is: a `scan_jobs` SQLite table and `ScanJob` model; a `--job-id` argparse flag in `run_scan.py` plus the `job_progress.py` helper; the `/api/jobs` FastAPI router; two React pages (`ScanNewPage`, `ScanJobPage`); and a `useJobStatus` hook. A lifespan function is introduced to `app.py` for the first time — the startup block sweeps stale `running` jobs to `failed` on API restart.

One structural pitfall: `create_app()` currently takes **no arguments**, but D-12 requires changing its signature to `create_app(db_path)`. All existing test files that call `create_app()` without arguments (at least `conftest.py`, `test_schedules_api.py`, `test_qramm_evidence_bridge.py`) must be updated to pass a db_path or use a default. The planner must allocate a dedicated task to handle this signature migration — it will break tests if not handled atomically.

**Primary recommendation:** Build in five discrete waves — (1) backend model + migration, (2) `run_scan.py` + `job_progress.py`, (3) `/api/jobs` router + Pydantic schemas, (4) `app.py` lifespan + router registration + `create_app(db_path)` migration, (5) React pages + hook + route + sidebar CTA + shadcn Checkbox install.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Scan job creation + subprocess dispatch | API / Backend | — | Subprocess launch must be server-side; browser cannot spawn processes |
| Job status tracking (DB writes) | Subprocess (run_scan.py) | API / Backend | The spawned scan owns stage writes; API owns initial row creation |
| Job status polling (reads) | API / Backend | Browser / Client | API reads DB; React hooks poll API at 3s interval |
| Form validation (schema) | API / Backend | Browser / Client | Pydantic is authoritative; client-side is a UX convenience only |
| Post-completion navigation | Browser / Client | — | React Router + ScanContext; no server involvement |
| Cancellation (SIGTERM) | API / Backend | — | `os.kill` must run server-side where the PID is accessible |
| Stale job recovery | API / Backend | — | FastAPI lifespan startup hook; runs once on API restart |

---

## Standard Stack

All libraries are already in the project. No new pip dependencies.

### Core (Backend)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | existing | `/api/jobs` router | Already the dashboard API framework |
| SQLAlchemy | existing | `ScanJob` ORM model | Already used for all other tables |
| Pydantic v2 | existing | `ScanSubmitRequest`, `JobStatusResponse` | Already used in `schemas.py`; `@field_validator` is v2 syntax |
| `subprocess` (stdlib) | stdlib | `Popen` dispatch | Phase 63 pattern; no new dep |
| `signal` (stdlib) | stdlib | `os.kill(pid, signal.SIGTERM)` | Standard POSIX cancellation |
| `contextlib` (stdlib) | stdlib | `@asynccontextmanager` for lifespan | FastAPI lifespan requirement |
| `uuid` (stdlib) | stdlib | `str(uuid.uuid4())` for job_id | Standard unique ID generation |

### Core (Frontend)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React Router DOM | existing | `/scan/new`, `/scan/job/:jobId` routes | Already in `App.tsx` |
| shadcn/ui | existing | Button, RadioGroup, Progress, Badge, Card, Skeleton, Separator, Label | Already installed |
| lucide-react | existing | `<Scan />` icon for sidebar CTA | Already in `sidebar.tsx` |
| `fetchApi` | project util | Authenticated fetch wrapper | Used by all existing hooks |

### One New Component Install Required
| Component | Status | Install Command |
|-----------|--------|-----------------|
| `Checkbox` | NOT installed (confirmed by `ls src/dashboard/src/components/ui/`) | `cd src/dashboard && npx shadcn add checkbox` |

[VERIFIED: file system check — no `checkbox.tsx` in `src/dashboard/src/components/ui/`]

---

## Architecture Patterns

### System Architecture Diagram

```
Browser                   FastAPI (dashboard API)           SQLite DB
  │                              │                              │
  │  POST /api/jobs              │                              │
  ├─────────────────────────────>│                              │
  │  (ScanSubmitRequest)         │  INSERT scan_jobs row        │
  │                              │ (status=queued)              │
  │                              ├────────────────────────────>│
  │                              │  subprocess.Popen(          │
  │                              │    quirk ... --job-id uuid) │
  │                              │  UPDATE pid, status=running  │
  │                              ├────────────────────────────>│
  │  201 {job_id}                │                              │
  │<─────────────────────────────┤                       ┌──────┘
  │                              │                       │ run_scan.py subprocess
  │  navigate /scan/job/:jobId   │                       │   UPDATE current_stage
  │                              │              (7 times)│   at each phase boundary
  │  GET /api/jobs/{id} (poll)   │                       │   UPDATE status=completed
  ├─────────────────────────────>│                       │   SET scan_run_id
  │  (every 3s)                  │  SELECT scan_jobs     │
  │                              ├────────────────────────────>│
  │  200 {JobStatusResponse}     │                              │
  │<─────────────────────────────┤                              │
  │                              │                              │
  │  [on status=completed]       │                              │
  │  setSelectedScanId(run_id)   │                              │
  │  navigate("/")               │                              │
```

### Recommended Project Structure

New files to create:

```
quirk/
├── cli/
│   └── job_progress.py          # update_job_stage(db_path, job_id, stage) helper
├── dashboard/api/routes/
│   └── jobs.py                  # POST /api/jobs, GET /api/jobs/{id}, DELETE /api/jobs/{id}
└── models.py                    # ADD: ScanJob model (after ScheduledRun)

src/dashboard/src/
├── hooks/
│   └── useJobStatus.ts          # new — 3s polling, Phase 62 cancellation pattern
├── pages/
│   ├── scan-new.tsx             # ScanNewPage — /scan/new form
│   └── scan-job.tsx             # ScanJobPage — /scan/job/:jobId status
└── components/ui/
    └── checkbox.tsx             # installed via npx shadcn add checkbox

tests/
└── test_jobs_api.py             # Wave 0 gap: does not exist yet
```

Files to modify:

```
quirk/
├── db.py                        # ADD: _ensure_scan_jobs_table(engine) at end of init_db()
├── models.py                    # ADD: ScanJob class
└── dashboard/api/
    ├── app.py                   # ADD: lifespan, import jobs router, change create_app(db_path)
    └── schemas.py               # ADD: ScanSubmitRequest, JobStatusResponse

run_scan.py                      # ADD: --job-id argparse flag; call update_job_stage() at 7 boundaries

src/dashboard/src/
├── App.tsx                      # ADD: /scan/new, /scan/job/:jobId routes + imports
├── components/sidebar.tsx       # ADD: "New Scan" Button above nav items
└── types/api.ts                 # ADD: ScanSubmitRequest, JobStatus TypeScript interfaces

tests/
├── conftest.py                  # UPDATE: create_app() → create_app(db_path or default)
├── test_schedules_api.py        # UPDATE: same
└── test_qramm_evidence_bridge.py # UPDATE: same
```

### Pattern 1: SQLAlchemy Model — ScanJob

[VERIFIED: quirk/models.py — matches `ScheduledScan`/`ScheduledRun` pattern]

```python
# In quirk/models.py, after ScheduledRun class
class ScanJob(Base):
    """Ad-hoc dashboard-initiated scan job (Phase 65 — UI-SCAN-01)."""
    __tablename__ = "scan_jobs"

    job_id = Column(String(36), primary_key=True)   # UUID, generated by API
    pid = Column(Integer, nullable=True)             # Set after Popen succeeds
    status = Column(String(16), nullable=False)      # queued|running|completed|failed|cancelled
    current_stage = Column(String(32), nullable=True)
    target = Column(String(512), nullable=False)
    profile = Column(String(16), nullable=False)     # quick|standard|deep
    calibration = Column(String(16), nullable=False) # strict|balanced|lenient
    enable_nmap = Column(Boolean, default=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    scan_run_id = Column(String, nullable=True)      # CryptoEndpoint scan_run_id on completion
    error_message = Column(Text, nullable=True)
```

### Pattern 2: DB Registration — _ensure_scan_jobs_table

[VERIFIED: quirk/db.py — `_ensure_scheduled_tables` uses `Base.metadata.create_all(engine, checkfirst=True)`]

```python
def _ensure_scan_jobs_table(engine) -> None:
    """Phase 65 UI-SCAN-01: create scan_jobs table if absent (idempotent)."""
    Base.metadata.create_all(engine, checkfirst=True)

# In init_db(), add after _ensure_scheduled_tables(engine):
_ensure_scan_jobs_table(engine)   # Phase 65 — UI-SCAN-01
```

### Pattern 3: Pydantic Schemas

[VERIFIED: quirk/dashboard/api/schemas.py — `@field_validator` is Pydantic v2 syntax (from pydantic import field_validator already in project)]

`ScanSubmitRequest` and `JobStatusResponse` as specified verbatim in CONTEXT.md D-05. The `stage_index` to stage-name map (7 entries) lives in the backend router, not the frontend. Stage order: discovery(1), tls(2), ssh(3), api(4), identity(5), data_at_rest(6), reports(7). Stage index 0 = queued (not started), 7 = completed.

### Pattern 4: Jobs Router (POST Flow)

[VERIFIED: quirk/dashboard/api/routes/schedules.py — auth/CSRF pattern, DB session dependency]

```python
# Auth only on GET; auth + CSRF on mutating routes
read_router = APIRouter(dependencies=[Depends(require_auth)])
write_router = APIRouter(dependencies=[Depends(require_auth), Depends(require_csrf)])

@write_router.post("/jobs", status_code=201)
def create_job(payload: ScanSubmitRequest, db: Session = Depends(get_db)):
    job_id = str(uuid.uuid4())
    output_dir = Path("output/jobs") / job_id
    output_dir.mkdir(parents=True, exist_ok=True)
    # INSERT row with status="queued"
    row = ScanJob(job_id=job_id, status="queued", ...)
    db.add(row); db.flush()
    # Resolve db_path from get_db dependency context (see Pitfall 3 below)
    db_path = _resolve_db_path()
    cmd = [sys.executable, "-m", "run_scan",
           "--target", payload.targets,
           "--profile", payload.profile,
           "--output", str(output_dir),
           "--db-path", db_path,
           "--job-id", job_id]
    if payload.enable_nmap:
        cmd += ["--discovery", "nmap"]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    row.pid = proc.pid; row.status = "running"; row.started_at = _utcnow_naive()
    db.commit()
    return {"job_id": job_id, "status": "running"}
```

### Pattern 5: useJobStatus Hook (Phase 62 Pattern)

[VERIFIED: src/dashboard/src/hooks/useSchedules.ts — `let cancelled = false` pattern]

```typescript
// src/dashboard/src/hooks/useJobStatus.ts
export function useJobStatus(jobId: string) {
  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null)
  const navigate = useNavigate()
  const { setSelectedScanId } = useSelectedScan()

  useEffect(() => {
    let cancelled = false
    const poll = async () => {
      if (cancelled) return
      try {
        const resp = await fetchApi(`/api/jobs/${jobId}`)
        if (!cancelled) {
          if (resp.status === 404) {
            setJobStatus({ status: "not_found" } as any)
            return
          }
          const data: JobStatus = await resp.json()
          setJobStatus(data)
          if (data.status === "completed" && data.scan_run_id) {
            setSelectedScanId(data.scan_run_id)
            navigate("/")
            return
          }
          if (!isTerminal(data.status)) {
            setTimeout(poll, 3000)
          }
        }
      } catch {
        if (!cancelled) setTimeout(poll, 3000) // retry on network error
      }
    }
    poll()
    return () => { cancelled = true }
  }, [jobId])

  return jobStatus
}

function isTerminal(status: string) {
  return ["completed", "failed", "cancelled"].includes(status)
}
```

### Pattern 6: FastAPI Lifespan (First Introduction in app.py)

[VERIFIED: quirk/dashboard/api/app.py — `create_app()` currently takes no arguments; no lifespan exists]

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    db_path = app.state.db_path
    _recover_stale_jobs(db_path)
    yield

def create_app(db_path: str | None = None) -> FastAPI:
    if db_path is None:
        db_path = _default_db_path()  # same logic as deps.py
    application = FastAPI(..., lifespan=lifespan)
    application.state.db_path = db_path
    # ... rest unchanged
```

Using a default `None` parameter means `create_app()` (no args) remains valid — existing test files do not break. This is the safest approach to the signature migration.

### Pattern 7: run_scan.py --job-id Wiring

[VERIFIED: run_scan.py argparse section — adds to existing argument block]

Add after existing `--profile` argument:

```python
parser.add_argument(
    "--job-id",
    default=None,
    help="Dashboard job ID for progress reporting (Phase 65). No-op if absent.",
)
parser.add_argument(
    "--db-path",
    default=None,
    help="Explicit SQLite path for job progress writes (Phase 65).",
)
```

Then at each of the 7 stage boundaries (existing `print("=== Discovery phase ===")` etc.):

```python
from quirk.cli.job_progress import update_job_stage  # at top of file
# at each phase boundary:
if args.job_id:
    update_job_stage(args.db_path or _resolve_db_path(), args.job_id, "discovery")
```

### Anti-Patterns to Avoid

- **CSRF on GET routes:** `GET /api/jobs/{id}` is read-only — apply `require_auth` ONLY, not `require_csrf`. Consistent with all other GET routes in the project.
- **`os.kill` without error handling:** Always wrap in `try/except ProcessLookupError` — the process may exit between status check and kill call (race condition per CONTEXT.md Claude's Discretion).
- **Conditional chart children in ScanJobPage:** If any Recharts component is used for the progress visualization, never conditionally mount/unmount it. Use opacity instead (project-level memory from Recharts static children requirement). However, Phase 65 uses the shadcn `<Progress>` bar, not Recharts — this pitfall is not applicable here.
- **App-level module variable `app = create_app()` becoming stale:** The module-level `app` in `app.py` calls `create_app()` — it will still work with the default-parameter approach. Do not remove it; uvicorn loads it.
- **Blocking on Popen:** Do NOT call `proc.communicate()` (blocks until scan completes). Phase 63 scheduler uses `communicate()` because the scheduler loop is synchronous. The dashboard API must NOT block — call `Popen()` and return immediately.
- **`db_path` resolution in the jobs router:** The spawned subprocess needs `--db-path` to write to the same DB as the API. The API's `deps.py::_default_db_path()` logic should be reused to resolve the canonical path.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| UUID generation | Custom ID scheme | `str(uuid.uuid4())` | RFC 4122, globally unique, URL-safe |
| SIGTERM cancellation | Process group kill, custom signal | `os.kill(pid, signal.SIGTERM)` | Standard POSIX; matches process table PID |
| Auth enforcement | Custom token check | `require_auth` + `require_csrf` from Phase 58 | Already covers timing-safe comparison, auth bypass on empty token |
| Stage-to-index mapping | Frontend JS map | Backend `stage_index` field in `JobStatusResponse` | Single source of truth; eliminates frontend/backend sync bugs |
| ORM table creation | Raw SQL DDL | `Base.metadata.create_all(engine, checkfirst=True)` | Idempotent, consistent with all other tables in the project |

---

## Common Pitfalls

### Pitfall 1: `create_app()` Signature Change Breaks Tests

**What goes wrong:** Adding `db_path` as a required parameter to `create_app()` causes `TypeError` in `conftest.py`, `test_schedules_api.py`, and `test_qramm_evidence_bridge.py` which call `create_app()` with no args.

**Why it happens:** CONTEXT.md D-12 requires `create_app(db_path)` for `app.state.db_path`, but existing callers pass zero args.

**How to avoid:** Use `def create_app(db_path: str | None = None)` with `None` as default. Inside the factory, resolve `None` to `_default_db_path()`. All existing zero-arg callers remain valid.

**Warning signs:** `TypeError: create_app() missing 1 required positional argument: 'db_path'` in test output.

### Pitfall 2: Popen Blocking in FastAPI Route

**What goes wrong:** Calling `proc.communicate()` or `proc.wait()` in the `/api/jobs` POST route blocks the FastAPI worker for the entire scan duration (30-120s). All other API requests starve.

**Why it happens:** Phase 63 `_dispatch_schedule()` calls `proc.communicate()` — that is correct there because the scheduler loop is a blocking long-running process. The dashboard API POST route must return immediately.

**How to avoid:** Call `subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)` and return without waiting. The subprocess manages its own lifecycle.

**Warning signs:** `/scan/new` form submit hangs until scan completes; dashboard becomes unresponsive during scan.

### Pitfall 3: db_path Mismatch Between API and Subprocess

**What goes wrong:** The spawned `run_scan.py` subprocess writes `CryptoEndpoint` rows and `scan_jobs` updates to a different SQLite file than the dashboard API reads from.

**Why it happens:** `deps.py::_default_db_path()` uses environment variables and file-discovery heuristics. The subprocess may inherit a different working directory or env.

**How to avoid:** Resolve `db_path` once in the POST route using `_default_db_path()` (or read from `app.state.db_path` in the lifespan). Pass it explicitly as `--db-path <resolved_path>` in the `Popen` command list.

**Warning signs:** `GET /api/jobs/{id}` returns `status: "running"` forever; scan completes but `scan_run_id` is never set.

### Pitfall 4: Lifespan and `app.state` Ordering

**What goes wrong:** `_recover_stale_jobs(db_path)` called before `app.state.db_path` is set. Raises `AttributeError: 'State' object has no attribute 'db_path'`.

**Why it happens:** FastAPI's lifespan function receives the `app` instance but `app.state` attributes must be set before the `FastAPI(...)` call or in the factory body before the lifespan yields.

**How to avoid:** In `create_app(db_path)`, set `application.state.db_path = db_path` immediately after `FastAPI(lifespan=lifespan)` creation — before `include_router` calls. The lifespan context manager runs during `app.startup` and `app` by then has `state.db_path`.

**Warning signs:** `AttributeError` in lifespan at API startup.

### Pitfall 5: Route Introspection Test Catches Missing Auth

**What goes wrong:** `tests/test_api_auth.py::test_all_mutating_routes_have_auth_dependency` enumerates all `POST/PUT/DELETE/PATCH` routes and asserts `require_auth` is in their dependencies. Adding `/api/jobs` POST and DELETE without proper dependency wiring fails this existing CI gate.

**Why it happens:** The test was designed by Phase 58 to auto-catch future routes that bypass auth.

**How to avoid:** Wire `require_auth` (and `require_csrf`) using the router-level `dependencies=` parameter on the mutating router — same as `schedules.py` does.

**Warning signs:** `test_all_mutating_routes_have_auth_dependency` fails in CI listing `POST /api/jobs`.

### Pitfall 6: Datetime Timezone Naive Convention

**What goes wrong:** Mixing `datetime.utcnow()` (tz-naive) with `datetime.now(timezone.utc)` (tz-aware) produces `TypeError: can't compare offset-naive and offset-aware datetimes` in SQLAlchemy queries.

**Why it happens:** SQLite stores datetimes as strings; SQLAlchemy returns them as Python `datetime` objects without tzinfo. All existing tables in the project use tz-naive UTC.

**How to avoid:** Use `datetime.now(timezone.utc).replace(tzinfo=None)` everywhere in `jobs.py` and `job_progress.py`. This is the `_utcnow_naive()` pattern established in `schedules.py` and `scheduler_cmd.py`.

**Warning signs:** `TypeError` on datetime comparison; or `completed_at` stores `+00:00` suffix that breaks downstream timestamp parsing.

### Pitfall 7: useJobStatus Cleanup on Navigate

**What goes wrong:** `navigate("/")` is called from inside the polling `useEffect`. If the component unmounts after navigate (React Router removes it from the tree), the `setTimeout` callback fires on an unmounted component and calls `setJobStatus` on unmounted state.

**Why it happens:** `setTimeout` callbacks are not automatically cancelled on unmount.

**How to avoid:** The `cancelled = true` cleanup flag already prevents this — the `return () => { cancelled = true }` cleanup runs on unmount. The CONTEXT.md D-07 pattern handles this correctly when implemented exactly. Do NOT return early from `poll` before setting `cancelled = true` in cleanup.

**Warning signs:** React warning "Can't perform a React state update on an unmounted component" in browser console after scan completion.

---

## Code Examples

### job_progress.py Helper
```python
# quirk/cli/job_progress.py
"""Lightweight helper for updating scan_jobs.current_stage from run_scan.py subprocess."""
from __future__ import annotations

from datetime import datetime, timezone


def _utcnow_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def update_job_stage(db_path: str, job_id: str, stage: str) -> None:
    """Update scan_jobs.current_stage for the given job_id. No-op if row not found."""
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
        Session = sessionmaker(bind=engine, expire_on_commit=False)
        with Session() as db:
            from quirk.models import ScanJob
            row = db.get(ScanJob, job_id)
            if row is not None:
                row.current_stage = stage
                db.commit()
    except Exception:
        pass  # progress updates are best-effort; never crash the scan
```

### DELETE Cancel Route
```python
@write_router.delete("/jobs/{job_id}", status_code=204)
def cancel_job(job_id: str, db: Session = Depends(get_db)) -> None:
    row = db.get(ScanJob, job_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if row.pid and row.status == "running":
        try:
            os.kill(row.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass  # process already exited — optimistic cancel still succeeds
    row.status = "cancelled"
    row.completed_at = _utcnow_naive()
    db.commit()
    return None
```

---

## Environment Availability

Step 2.6: Environment dependencies are stdlib (`subprocess`, `signal`, `uuid`, `os`, `contextlib`) or already-installed project dependencies. No external tools beyond what Phase 63 already requires.

| Dependency | Required By | Available | Notes |
|------------|------------|-----------|-------|
| Python 3.11+ | run_scan.py subprocess | Yes (project requirement) | — |
| SQLite | scan_jobs table | Yes (bundled with Python) | — |
| `shadcn add checkbox` CLI | Checkbox component | Yes (npx available) | Must run in `src/dashboard/` |
| `npm run build` | Frontend changes visible | Yes | Required after all .tsx edits |

---

## Validation Architecture

nyquist_validation is `true` in config.json — this section is required.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | `pyproject.toml` |
| Quick run command | `python -m pytest tests/test_jobs_api.py -x -q` |
| Full suite command | `python -m pytest tests/ -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| UI-SCAN-01 | POST /api/jobs creates scan_jobs row with correct fields | unit | `pytest tests/test_jobs_api.py::test_post_job_creates_row -x` | Wave 0 gap |
| UI-SCAN-01 | POST /api/jobs with @file target returns 422 | unit | `pytest tests/test_jobs_api.py::test_post_job_rejects_file_path -x` | Wave 0 gap |
| UI-SCAN-01 | POST /api/jobs with empty targets returns 422 | unit | `pytest tests/test_jobs_api.py::test_post_job_empty_targets -x` | Wave 0 gap |
| UI-SCAN-01 | POST /api/jobs requires auth | unit | `pytest tests/test_jobs_api.py::test_post_job_requires_auth -x` | Wave 0 gap |
| UI-SCAN-01 | POST /api/jobs requires CSRF | unit | `pytest tests/test_jobs_api.py::test_post_job_requires_csrf -x` | Wave 0 gap |
| UI-SCAN-02 | GET /api/jobs/{id} returns correct JobStatusResponse shape | unit | `pytest tests/test_jobs_api.py::test_get_job_status -x` | Wave 0 gap |
| UI-SCAN-02 | GET /api/jobs/{id} returns 404 for unknown id | unit | `pytest tests/test_jobs_api.py::test_get_job_not_found -x` | Wave 0 gap |
| UI-SCAN-02 | GET /api/jobs/{id} requires auth (no CSRF) | unit | `pytest tests/test_jobs_api.py::test_get_job_requires_auth -x` | Wave 0 gap |
| UI-SCAN-02 | stage_index computed correctly from current_stage | unit | `pytest tests/test_jobs_api.py::test_stage_index_computation -x` | Wave 0 gap |
| UI-SCAN-03 | DELETE /api/jobs/{id} sends SIGTERM and sets cancelled | unit | `pytest tests/test_jobs_api.py::test_cancel_job -x` | Wave 0 gap |
| UI-SCAN-03 | _recover_stale_jobs flips running jobs to failed | unit | `pytest tests/test_jobs_api.py::test_stale_job_recovery -x` | Wave 0 gap |
| All | Route introspection: POST/DELETE /api/jobs have require_auth | regression | `pytest tests/test_api_auth.py::test_all_mutating_routes_have_auth_dependency -x` | Existing (auto-picks up new routes) |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_jobs_api.py -x -q`
- **Per wave merge:** `python -m pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_jobs_api.py` — covers UI-SCAN-01, UI-SCAN-02, UI-SCAN-03 (all 11 test cases above)
- [ ] `tests/test_job_progress.py` — covers `update_job_stage()` no-op behavior when job not found

*(Existing test infrastructure in `conftest.py` `dashboard_client` fixture is reusable. No new fixtures needed beyond the test file.)*

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | Yes | `require_auth` (Phase 58 bearer token) — already implemented |
| V3 Session Management | No | Stateless API; no session tokens |
| V4 Access Control | Yes | All `/api/jobs` routes behind `require_auth`; CSRF on mutating routes |
| V5 Input Validation | Yes | `ScanSubmitRequest` Pydantic validation; `no_file_paths` validator rejects `@file` targets |
| V6 Cryptography | No | No new crypto operations |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Command injection via target string | Tampering | List-form `Popen` (no `shell=True`); `ScanSubmitRequest.targets` validated by Pydantic; `@file` paths rejected at schema level |
| CSRF on scan submission | Spoofing | `require_csrf` on POST /api/jobs (Phase 58 double-submit pattern) |
| Path traversal in output dir | Tampering | Output path is `output/jobs/{uuid}` — UUID is generated server-side, not user-supplied |
| PID reuse after cancel | Elevation | `ProcessLookupError` caught; status set to `cancelled` regardless — no re-kill on stale PID |
| Stale `running` jobs on restart | Information | Lifespan `_recover_stale_jobs` sweeps to `failed` on API startup |

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `create_app()` no args | `create_app(db_path=None)` | Phase 65 | `app.state.db_path` available for lifespan; backward compatible |
| No FastAPI lifespan | `@asynccontextmanager lifespan` | Phase 65 | First startup hook in the project; runs `_recover_stale_jobs` |
| Dashboard read-only | Dashboard can dispatch scans | Phase 63 (first writable route), Phase 65 (second route family) | ARCHITECTURE.md note "Dashboard API — strictly read-only" must be updated |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `run_scan.py` has exactly 7 phase-boundary `print` statements that can be used as injection points for `update_job_stage()` calls | Architecture Patterns | If boundaries are implicit or nested, stage reporting needs different injection points; verify by reading the full `main()` function |
| A2 | `scan_run_id` in `scan_jobs` is the same value as the `scanned_at` ISO timestamp used as `ScanSession.scan_id` in the existing scan list | Architecture Patterns | If the IDs differ, `setSelectedScanId(scan_run_id)` may not select the correct scan in `ScanSelector` |

---

## Open Questions

1. **How does run_scan.py expose the scan_run_id on completion?**
   - What we know: `CryptoEndpoint` rows have `scanned_at` as the session identifier; `ScanMeta.scan_id` is an ISO timestamp string
   - What's unclear: `run_scan.py` must write `scan_run_id` back to `scan_jobs` on completion — this requires reading the `scanned_at` value that was used during the scan session, then updating the `scan_jobs` row
   - Recommendation: The planner should include a task that reads the full `main()` body of `run_scan.py` to find where `scan_run_id` (or `scanned_at`) is established, then wire the DB update at that exact point

2. **Does `run_scan.py --db-path` flag already exist?**
   - What we know: Reviewed argparse section of `run_scan.py` — no `--db-path` flag found in the first 380 lines
   - What's unclear: Whether it exists further in the file or is passed via config
   - Recommendation: Planner task must add `--db-path` as a new argparse argument; the subprocess cannot otherwise know which DB file to update for job progress

---

## Sources

### Primary (HIGH confidence)
- [VERIFIED: file read] `quirk/dashboard/api/routes/schedules.py` — auth/CSRF router pattern, `_utcnow_naive()` pattern, `IntegrityError` handling, `db.flush()` + `db.commit()` sequence
- [VERIFIED: file read] `quirk/dashboard/api/app.py` — `create_app()` current signature (no args), no lifespan exists yet, router mount pattern
- [VERIFIED: file read] `quirk/models.py` — `ScheduledScan`/`ScheduledRun` model pattern; `Base` declarative
- [VERIFIED: file read] `quirk/db.py` — `_ensure_scheduled_tables()` pattern; `init_db()` call chain
- [VERIFIED: file read] `quirk/dashboard/api/schemas.py` — Pydantic v2 syntax (`@field_validator`); schema location
- [VERIFIED: file read] `quirk/dashboard/api/deps.py` — `get_db()` FastAPI dependency; `_default_db_path()` resolution logic
- [VERIFIED: file read] `src/dashboard/src/hooks/useSchedules.ts` — `let cancelled = false` pattern; `fetchCount` refetch pattern
- [VERIFIED: file read] `src/dashboard/src/hooks/useScanList.ts` — auth error handling in hooks
- [VERIFIED: file read] `src/dashboard/src/App.tsx` — existing route registration pattern; `<ScanProvider>` wrapping
- [VERIFIED: file read] `src/dashboard/src/components/sidebar.tsx` — `NAV_ITEMS` structure; button/link rendering
- [VERIFIED: file read] `src/dashboard/src/context/ScanProvider.tsx` + `useSelectedScan.ts` — `setSelectedScanId` interface
- [VERIFIED: file read] `run_scan.py` argparse section — existing flags; no `--job-id` or `--db-path` exists
- [VERIFIED: file read] `quirk/cli/scheduler_cmd.py` — `subprocess.Popen` dispatch; `_recover_stale_runs()` pattern
- [VERIFIED: file read] `tests/conftest.py` — `create_app()` called with no args in fixture
- [VERIFIED: file read] `tests/test_schedules_api.py` — `create_app()` called with no args; route introspection gate
- [VERIFIED: file system check] `src/dashboard/src/components/ui/` — no `checkbox.tsx` exists; install required
- [VERIFIED: file read] `.planning/config.json` — `nyquist_validation: true`
- [VERIFIED: file read] `65-CONTEXT.md` — all locked decisions, schemas, form fields
- [VERIFIED: file read] `65-UI-SPEC.md` — component inventory, layout specs, copywriting contract

### Secondary (MEDIUM confidence)
- [CITED: CONTEXT.md D-12] `_recover_stale_jobs` sweeps `running` → `failed` on startup; exact cutoff (no time threshold specified, unlike scheduler's 2-hour window) — implementation choice for planner

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries verified present in codebase
- Architecture: HIGH — all patterns verified against existing analog implementations
- Pitfalls: HIGH — all derived from direct code inspection of files that will be modified
- UI: HIGH — UI-SPEC.md is approved; component inventory verified against file system

**Research date:** 2026-05-13
**Valid until:** 2026-06-13 (stable stack; 30-day window)
