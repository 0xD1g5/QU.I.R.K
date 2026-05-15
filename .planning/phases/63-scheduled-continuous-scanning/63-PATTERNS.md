# Phase 63: Scheduled / Continuous Scanning — Pattern Map

**Mapped:** 2026-05-10
**Files analyzed:** 10 new/modified files
**Analogs found:** 10 / 10

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `quirk/models.py` (append) | model | CRUD | `quirk/models.py` QRAMMSession/QRAMMProfile blocks | exact |
| `quirk/db.py` (append) | config/migration | CRUD | `quirk/db.py` `_ensure_qramm_tables()` | exact |
| `quirk/cli/schedule_cmd.py` | utility/CLI | CRUD | `quirk/cli/doctor_cmd.py` + `quirk/cli/init_cmd.py` | role-match |
| `quirk/cli/scheduler_cmd.py` | utility/CLI | event-driven | `quirk/cli/doctor_cmd.py` (structure) | partial-match |
| `quirk/dashboard/api/routes/schedules.py` | controller | CRUD | `quirk/dashboard/api/routes/qramm.py` | exact |
| `quirk/dashboard/api/app.py` (modify) | config | request-response | `quirk/dashboard/api/app.py` existing `include_router` calls | exact |
| `run_scan.py` (modify) | config | request-response | `run_scan.py` lines 191-265 existing interception blocks | exact |
| `src/dashboard/src/hooks/useSchedules.ts` | hook | request-response | `src/dashboard/src/hooks/useScanData.ts` | exact |
| `src/dashboard/src/pages/schedules.tsx` | component | request-response | `src/dashboard/src/pages/findings.tsx` | role-match |
| `src/dashboard/src/components/sidebar.tsx` (modify) | component | event-driven | `src/dashboard/src/components/sidebar.tsx` NAV_ITEMS | exact |
| `src/dashboard/src/App.tsx` (modify) | config | request-response | `src/dashboard/src/App.tsx` existing Routes | exact |

---

## Pattern Assignments

### `quirk/models.py` — append ScheduledScan + ScheduledRun (model, CRUD)

**Analog:** `quirk/models.py` — QRAMMSession and QRAMMProfile classes (lines 95–156)

**Imports pattern** (lines 1–6):
```python
from __future__ import annotations

from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Float

Base = declarative_base()
```

**Core ORM model pattern** (lines 95–156 — QRAMMSession and QRAMMProfile as template):
```python
class QRAMMSession(Base):
    __tablename__ = "qramm_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    org_name = Column(String(255), nullable=True)
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    model_version = Column(String(32), nullable=True)
    profile_id = Column(Integer, nullable=True)  # FK -> qramm_profiles.id
    status = Column(String(32), nullable=True)   # "draft" | "scored" | "complete"
    score_json = Column(Text, nullable=True)
```

**Apply to new models:** Follow the exact same `Column`/`Base` style. `ScheduledScan` uses `unique=True` on `name` column (catches duplicate schedule names via `IntegrityError`). `ScheduledRun` uses `Integer` FK column referencing `scheduled_scans.id` (no DB-level constraint — SQLite pattern).

**New models to append:**
```python
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
    scan_id = Column(String(64), nullable=True)       # null until scan completes
```

---

### `quirk/db.py` — append `_ensure_scheduled_tables` + call in `init_db` (config/migration, CRUD)

**Analog:** `quirk/db.py` — `_ensure_qramm_tables()` function (lines 214–225) and `init_db()` call pattern (line 252)

**Core migration helper pattern** (lines 214–225):
```python
def _ensure_qramm_tables(engine) -> None:
    """Phase 51 QRAMM-01: create QRAMM assessment tables if absent (idempotent).

    Uses Base.metadata.create_all with checkfirst=True. These are entirely
    new tables (qramm_sessions, qramm_answers, qramm_profiles) — not new
    columns on crypto_endpoints — so we use create_all rather than the
    ALTER TABLE pattern of the other _ensure_* functions.

    QRAMMSession/QRAMMAnswer/QRAMMProfile are registered on Base.metadata
    via the import of quirk.models at the top of this file (D-05).
    """
    Base.metadata.create_all(engine, checkfirst=True)
```

**Call site pattern in `init_db()`** (lines 228–254 — specifically line 252):
```python
def init_db(db_path: str) -> Engine:
    engine = get_engine(db_path)
    with engine.connect() as conn:
        conn.commit()
    Base.metadata.create_all(engine)
    _ensure_identity_columns(engine)
    _ensure_gcp_columns(engine)
    _ensure_v43_columns(engine)
    _ensure_email_columns(engine)
    _ensure_broker_columns(engine)
    _ensure_phase41_columns(engine)
    _ensure_phase46_columns(engine)
    _ensure_qramm_tables(engine)         # Phase 51 — QRAMM-01  ← copy this pattern
    _ensure_phase54_qramm_columns(engine)
    # Phase 63 line to append:
    _ensure_scheduled_tables(engine)     # Phase 63 — SCHED-01
    return engine
```

**New function to append:**
```python
def _ensure_scheduled_tables(engine) -> None:
    """Phase 63 SCHED-01: create scheduled_scans and scheduled_runs tables if absent.

    Uses Base.metadata.create_all with checkfirst=True. ScheduledScan and
    ScheduledRun are registered on Base.metadata via import of quirk.models.
    New tables only — not new columns — so create_all is correct (not ALTER TABLE).
    """
    Base.metadata.create_all(engine, checkfirst=True)
```

**get_session pattern** (lines 257–284) — reuse unchanged for CLI CRUD commands:
```python
@contextmanager
def get_session(db_path: str) -> Iterator:
    engine = get_engine(db_path)
    Session = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        future=True,
        expire_on_commit=False,  # critical: prevents DetachedInstanceError
    )
    session = Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
```

---

### `quirk/cli/schedule_cmd.py` (utility/CLI, CRUD)

**Analog:** `quirk/cli/doctor_cmd.py` (Rich console + argparse structure) and `quirk/cli/init_cmd.py` (minimal entrypoint pattern)

**Module header pattern** (doctor_cmd.py lines 1–24):
```python
"""quirk doctor — Phase 52 DOCS-05: pre-engagement health check for operators."""
from __future__ import annotations

import sys
from typing import Tuple

from rich.console import Console
from rich.table import Table
```

**Rich table rendering pattern** (doctor_cmd.py lines 124–170):
```python
def run_doctor() -> None:
    console = Console()
    table = Table(title="QU.I.R.K. Health Check", show_header=True, header_style="bold")
    table.add_column("Check", style="bold")
    table.add_column("Status")
    # ... populate rows ...
    console.print(table)
    sys.exit(1 if failed else 0)
```

**Entrypoint function pattern** (init_cmd.py lines 7–64 — `run_init(output_path)`):
```python
def run_init(output_path: str) -> None:
    try:
        from rich.console import Console
        console = Console()
        _info = lambda msg: console.print(f"[bold #3b9dff]QU.I.R.K.[/] {msg}")
        _warn = lambda msg: console.print(f"[bold yellow]WARNING:[/] {msg}")
    except ImportError:
        _info = lambda msg: print(f"QU.I.R.K. {msg}")
        _warn = lambda msg: print(f"WARNING: {msg}")
```

**schedule_cmd.py structure to implement:**
- `run_schedule(argv: list[str]) -> None` — main entrypoint called from `run_scan.py`
- Internal argparse with subparsers: `add`, `list`, `enable`, `disable`, `remove`
- Each sub-action calls `get_session(db_path)` from `quirk.db`
- `schedule list` renders a Rich table (follow doctor_cmd table pattern)
- `schedule add` validates cron with `croniter.is_valid()` before DB write; catches `IntegrityError` for duplicate name
- DB path resolved via `_default_db_path()` logic (mirror `deps.py` priority: `QUIRK_DB_PATH` env → `./quirk.db`)

---

### `quirk/cli/scheduler_cmd.py` (utility/CLI, event-driven)

**Analog:** `quirk/cli/doctor_cmd.py` for module structure; Python stdlib `signal` and `subprocess` for dispatch pattern.

**Module structure pattern** (doctor_cmd.py lines 1–24 — header + imports):
```python
"""quirk scheduler — Phase 63 SCHED-02: long-running 60s dispatch loop."""
from __future__ import annotations

import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
```

**Signal handling pattern** (from RESEARCH.md Pattern 7 — stdlib signal):
```python
_stop_flag = False

def _handle_signal(signum, frame):
    global _stop_flag
    _stop_flag = True

signal.signal(signal.SIGINT, _handle_signal)
signal.signal(signal.SIGTERM, _handle_signal)

while not _stop_flag:
    check_and_dispatch_due_schedules(db)
    for _ in range(60):
        if _stop_flag:
            break
        time.sleep(1)
```

**Subprocess dispatch pattern** (from RESEARCH.md Pattern 6):
```python
def dispatch_schedule(schedule, run_row, db):
    output_dir = Path(f"output/scheduled/{schedule.name}/{run_row.dispatched_at:%Y%m%d-%H%M%S}")
    output_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable, "-m", "run_scan",
        "--config", "config.yaml",
        "--target", schedule.target,
        "--profile", schedule.profile or "balanced",
        "--output", str(output_dir),
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    run_row.status = "running"
    db.commit()
    stdout, stderr = proc.communicate()
    run_row.status = "completed" if proc.returncode == 0 else "failed"
    run_row.completed_at = datetime.utcnow()
    run_row.scan_output_path = str(output_dir)
    db.commit()
```

**Startup recovery pattern** (mark stale running rows as failed on startup — no existing analog, use RESEARCH.md guidance):
```python
# At scheduler startup, mark stale runs as failed
def _recover_stale_runs(db):
    cutoff = datetime.utcnow() - timedelta(hours=2)
    stale = db.query(ScheduledRun).filter(
        ScheduledRun.status.in_(["pending", "running"]),
        ScheduledRun.dispatched_at < cutoff,
    ).all()
    for run in stale:
        run.status = "failed"
        run.scan_output_path = "INTERRUPTED"
    db.commit()
```

---

### `quirk/dashboard/api/routes/schedules.py` (controller, CRUD)

**Analog:** `quirk/dashboard/api/routes/qramm.py` — primary template (all patterns apply)

**Imports pattern** (qramm.py lines 15–47):
```python
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from quirk.dashboard.api.middleware.auth import require_auth
from quirk.dashboard.api.middleware.csrf import require_csrf
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from quirk.dashboard.api.deps import get_db
from quirk.models import ScheduledScan, ScheduledRun
```

**Auth + CSRF router pattern** (qramm.py line 46 — the single most important line):
```python
router = APIRouter(dependencies=[Depends(require_auth), Depends(require_csrf)])
logger = logging.getLogger(__name__)
```

**Pydantic models inline pattern** (qramm.py lines 52–149 — inline per D-11):
```python
# All Pydantic models defined inline in the route file (not in schemas.py)
class CreateSessionRequest(BaseModel):
    org_name: Optional[str] = Field(default=None, max_length=255)
    model_version: Optional[str] = Field(default=None, max_length=32)

class CreateSessionResponse(BaseModel):
    session_id: int
    org_name: Optional[str]
    created_at: Optional[str]
    status: str
    model_version: str
```

**GET list endpoint pattern** (qramm.py lines 444–476):
```python
@router.get("/qramm/sessions", response_model=List[SessionSummary])
def list_sessions(db: Session = Depends(get_db), limit: int = Query(default=50, ge=1, le=200)) -> List[SessionSummary]:
    rows = (
        db.query(QRAMMSession)
        .order_by(QRAMMSession.created_at.desc(), QRAMMSession.id.desc())
        .limit(limit)
        .all()
    )
    return [SessionSummary(...) for s in rows]
```

**POST create pattern** (qramm.py lines 200–253):
```python
@router.post("/qramm/sessions", status_code=201, response_model=CreateSessionResponse)
def create_session(
    payload: CreateSessionRequest,
    db: Session = Depends(get_db),
) -> CreateSessionResponse:
    now = _now_iso()
    session = QRAMMSession(org_name=payload.org_name, created_at=now, ...)
    db.add(session)
    db.flush()
    db.commit()
    db.refresh(session)
    return CreateSessionResponse(session_id=session.id, ...)
```

**DELETE pattern** (qramm.py lines 416–423):
```python
@router.delete("/qramm/sessions/{session_id}", status_code=204)
def delete_session(session_id: int, db: Session = Depends(get_db)) -> None:
    session = _get_session_or_404(db, session_id)
    db.delete(session)
    db.commit()
    return None
```

**404 helper pattern** (qramm.py lines 191–195):
```python
def _get_session_or_404(db: Session, session_id: int) -> QRAMMSession:
    session = db.get(QRAMMSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session
```

**Datetime helper pattern** (qramm.py lines 183–188):
```python
def _now_iso() -> datetime:
    return datetime.now(timezone.utc)

def _iso_str(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt is not None else None
```

**Apply to schedules.py:**
- `GET /schedules` — list all ScheduledScan rows, JOIN last ScheduledRun row, compute `next_run_at` on-the-fly via `croniter`
- `POST /schedules` — validate cron expr, create ScheduledScan row, return 201; catch `IntegrityError` → 409
- `PATCH /schedules/{id}` — flip `enabled` flag; follow same `_get_or_404` + `db.commit()` pattern
- `DELETE /schedules/{id}` — delete ScheduledRun rows first (explicit cascade, no FK enforcement in SQLite), then ScheduledScan row; return 204

---

### `quirk/dashboard/api/app.py` — add schedules router (config, request-response)

**Analog:** `quirk/dashboard/api/app.py` — existing `include_router` calls (lines 22 and 62–66)

**Import line to modify** (line 22):
```python
# Before:
from quirk.dashboard.api.routes import health, pdf, qramm, scan, trends

# After:
from quirk.dashboard.api.routes import health, pdf, qramm, scan, schedules, trends
```

**Router registration to add** (after line 66, before the static file section):
```python
application.include_router(schedules.router, prefix="/api")
```

---

### `run_scan.py` — add schedule + scheduler interception blocks (config, request-response)

**Analog:** `run_scan.py` lines 191–265 — existing interception blocks for `init`, `serve`, `compliance`, `doctor`

**Exact interception pattern** (lines 261–265 — doctor block as closest shape):
```python
# --- doctor subcommand: intercept before scan argparse (Phase 52 DOCS-05 / D-10) ---
if len(_sys.argv) > 1 and _sys.argv[1] == "doctor":
    from quirk.cli.doctor_cmd import run_doctor
    run_doctor()
```

**New blocks to insert after the doctor block:**
```python
# --- schedule subcommand: intercept before scan argparse (Phase 63 SCHED-01) ---
if len(_sys.argv) > 1 and _sys.argv[1] == "schedule":
    from quirk.cli.schedule_cmd import run_schedule
    run_schedule(_sys.argv[2:])
    return

# --- scheduler subcommand: intercept before scan argparse (Phase 63 SCHED-02) ---
if len(_sys.argv) > 1 and _sys.argv[1] == "scheduler":
    from quirk.cli.scheduler_cmd import run_scheduler
    run_scheduler(_sys.argv[2:])
    return
```

**Note:** The `doctor` block is missing `return` in the existing code at line 263-264 — the `schedule`/`scheduler` blocks MUST include `return` to avoid falling through to argparse.

---

### `src/dashboard/src/hooks/useSchedules.ts` (hook, request-response)

**Analog:** `src/dashboard/src/hooks/useScanData.ts` — exact cancellation-safe pattern (lines 1–78)

**Full pattern to mirror** (useScanData.ts lines 1–78):
```typescript
import { useState, useEffect } from "react"
import { fetchApi } from "@/lib/api"

interface UseScanDataResult {
  data: ScanLatestResponse | null
  loading: boolean
  error: string | null
}

export function useScanData(): UseScanDataResult {
  const [data, setData] = useState<ScanLatestResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    // Clear stale data synchronously before initiating new fetch
    setData(null)
    setLoading(true)
    setError(null)

    async function fetchData() {
      try {
        const resp = await fetchApi("/api/scan/latest")
        if (!resp.ok) {
          if (!cancelled) setError(`API error: ${resp.status} ${resp.statusText}`)
          return
        }
        const json: ScanLatestResponse = await resp.json()
        if (!cancelled) setData(json)
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load scan data")
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    fetchData()
    return () => { cancelled = true }   // cleanup: mark stale on unmount
  }, [selectedScanId])  // ← useSchedules uses [] (no scan selection dependency)

  return { data, loading, error }
}
```

**Apply to useSchedules.ts:**
- Replace `ScanLatestResponse` with `ScheduleListResponse` (define inline or in `@/types/api`)
- Replace fetch URL with `/api/schedules`
- Change `useEffect` dependency array from `[selectedScanId]` to `[]` (schedules not scan-bound)
- Add a `patch(id, enabled)` function for the toggle action that sends `PATCH /api/schedules/{id}` and optimistically updates local state

---

### `src/dashboard/src/pages/schedules.tsx` (component, request-response)

**Analog:** `src/dashboard/src/pages/findings.tsx` — page component structure (lines 1–80)

**Imports pattern** (findings.tsx lines 1–24):
```typescript
import { useState, useMemo } from "react"
import { useScanData } from "@/hooks/useScanData"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"
```

**Page component shell pattern** (findings.tsx lines 33–51):
```typescript
export function FindingsPage() {
  const { data, loading, error } = useScanData()
  // ... local state for filters ...

  if (loading) return <FindingsSkeleton />
  if (error) return <EmptyStateCard message={error} />
  if (!data?.findings?.length) return <EmptyStateCard message="No findings yet." />

  return (
    <div>
      <Table>...</Table>
    </div>
  )
}
```

**Apply to schedules.tsx:**
- Replace `useScanData()` with `useSchedules()`
- Table columns: name, target, profile, cron_expr, next_run_at, last_run status, enabled toggle
- Toggle column uses a `Switch` or `Button` that calls `useSchedules().patch(id, !enabled)`
- Follow `findings.tsx` loading/error/empty state guard pattern before rendering the table
- Export as `SchedulesPage` (not default export — matches findings.tsx named export pattern)

---

### `src/dashboard/src/components/sidebar.tsx` — add Schedules nav item (component, event-driven)

**Analog:** `src/dashboard/src/components/sidebar.tsx` — `NAV_ITEMS` array (lines 22–33)

**NAV_ITEMS pattern** (lines 22–33):
```typescript
import {
  LayoutDashboard, AlertTriangle, Shield, Database, GitBranch,
  Fingerprint, TrendingUp, Activity, HardDrive, ClipboardList,
} from "lucide-react"

const NAV_ITEMS = [
  { path: "/", label: "Executive Summary", Icon: LayoutDashboard },
  { path: "/findings", label: "Findings", Icon: AlertTriangle },
  // ... existing items ...
  { path: "/qramm", label: "QRAMM Assessment", Icon: ClipboardList },
]
```

**New entry to add** (append to NAV_ITEMS after `/qramm`):
```typescript
import { Calendar } from "lucide-react"   // add to existing import block

// Add to NAV_ITEMS:
{ path: "/schedules", label: "Schedules", Icon: Calendar },
```

**Active-path matching note:** The `/schedules` path does not need special `startsWith` handling (unlike `/qramm` which has a sub-route `/qramm/assessment`). The existing `location.pathname === path` check is sufficient.

---

### `src/dashboard/src/App.tsx` — add /schedules route (config, request-response)

**Analog:** `src/dashboard/src/App.tsx` — existing import + `<Route>` pattern (lines 1–55)

**Import pattern** (lines 7–18):
```typescript
import { PrintPage } from "@/pages/print"
import { ExecutivePage } from "@/pages/executive"
import { FindingsPage } from "@/pages/findings"
// ... one import per page ...
```

**Route registration pattern** (lines 32–44):
```typescript
<Routes>
  <Route path="/" element={<ExecutivePage />} />
  <Route path="/findings" element={<FindingsPage />} />
  {/* ... */}
  <Route path="/qramm" element={<OrgProfilePage />} />
  <Route path="/qramm/assessment" element={<AssessmentPage />} />
</Routes>
```

**New lines to add:**
```typescript
// Import (add to existing import block):
import { SchedulesPage } from "@/pages/schedules"

// Route (add inside <Routes>, after qramm/assessment route):
<Route path="/schedules" element={<SchedulesPage />} />
```

---

## Shared Patterns

### Authentication + CSRF (all mutating routes in schedules.py)

**Source:** `quirk/dashboard/api/routes/qramm.py` line 46
**Apply to:** `schedules.py` router declaration

```python
from quirk.dashboard.api.middleware.auth import require_auth
from quirk.dashboard.api.middleware.csrf import require_csrf

router = APIRouter(dependencies=[Depends(require_auth), Depends(require_csrf)])
```

Note: `require_csrf` already passes GET/HEAD/OPTIONS unconditionally (verified in `quirk/dashboard/api/middleware/csrf.py`), so applying at router level is safe for the GET list endpoint.

### DB Session — FastAPI Dependency

**Source:** `quirk/dashboard/api/deps.py` lines 29–49
**Apply to:** All route functions in `schedules.py`

```python
from quirk.dashboard.api.deps import get_db
from sqlalchemy.orm import Session

@router.get("/schedules")
def list_schedules(db: Session = Depends(get_db)):
    ...
```

### DB Session — CLI Context Manager

**Source:** `quirk/db.py` lines 257–284
**Apply to:** All CLI operations in `schedule_cmd.py` and `scheduler_cmd.py`

```python
from quirk.db import get_session

with get_session(db_path) as db:
    row = ScheduledScan(...)
    db.add(row)
    # commit() called automatically on context manager exit
```

### Error Handling — HTTP 404

**Source:** `quirk/dashboard/api/routes/qramm.py` lines 191–195
**Apply to:** `PATCH /api/schedules/{id}` and `DELETE /api/schedules/{id}` handlers

```python
def _get_schedule_or_404(db: Session, schedule_id: int) -> ScheduledScan:
    row = db.get(ScheduledScan, schedule_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return row
```

### Test Fixture — Dashboard Client

**Source:** `tests/conftest.py` lines 90–112
**Apply to:** `tests/test_schedules_api.py` — reuse existing `dashboard_client` fixture unchanged

```python
# In conftest.py (already exists — do not modify):
return TestClient(app, headers={"X-Quirk-Request": "1"})

# All PATCH/POST/DELETE test calls automatically get the CSRF header.
# For auth, add Authorization header per Phase 58 pattern.
```

### Cancellation-Safe React Hook

**Source:** `src/dashboard/src/hooks/useScanData.ts` lines 18–75
**Apply to:** `useSchedules.ts`

Critical invariant: Every `setState` call inside `fetchData()` is guarded by `if (!cancelled)`. The cleanup function `return () => { cancelled = true }` must be the return value of the `useEffect` callback.

---

## No Analog Found

All files have strong analogs in the codebase. No files require falling back to RESEARCH.md patterns exclusively.

The `scheduler_cmd.py` dispatcher loop (event-driven, long-running process) has no exact analog (all existing CLI modules are one-shot), but the module structure follows `doctor_cmd.py` and the dispatch/signal patterns are well-specified in RESEARCH.md Patterns 6 and 7 with stdlib references.

---

## Metadata

**Analog search scope:** `quirk/cli/`, `quirk/dashboard/api/routes/`, `quirk/models.py`, `quirk/db.py`, `quirk/dashboard/api/app.py`, `quirk/dashboard/api/deps.py`, `src/dashboard/src/hooks/`, `src/dashboard/src/pages/`, `src/dashboard/src/components/`, `run_scan.py`

**Files scanned:** 12 analog files read directly
**Pattern extraction date:** 2026-05-10
