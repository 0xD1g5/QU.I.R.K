# Phase 65: Dashboard-Initiated Scan - Pattern Map

**Mapped:** 2026-05-13
**Files analyzed:** 15 new/modified files
**Analogs found:** 14 / 15 (1 partial — lifespan has no prior analog in this project)

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `quirk/models.py` | model | CRUD | `quirk/models.py` (`ScheduledRun` class) | exact |
| `quirk/db.py` | config/migration | CRUD | `quirk/db.py` (`_ensure_scheduled_tables`) | exact |
| `quirk/cli/job_progress.py` | utility | CRUD | `quirk/cli/schedule_cmd.py` (`_resolve_db_path` + session pattern) | role-match |
| `quirk/dashboard/api/routes/jobs.py` | controller | request-response | `quirk/dashboard/api/routes/schedules.py` | exact |
| `quirk/dashboard/api/schemas.py` | model | request-response | `quirk/dashboard/api/schemas.py` (existing Pydantic models) | exact |
| `quirk/dashboard/api/app.py` | config | request-response | `quirk/dashboard/api/app.py` (existing `create_app`) | exact + new lifespan |
| `run_scan.py` | utility | batch | `run_scan.py` (existing argparse block, lines 287–345) | exact |
| `src/dashboard/src/hooks/useJobStatus.ts` | hook | request-response | `src/dashboard/src/hooks/useSchedules.ts` | exact |
| `src/dashboard/src/pages/ScanNewPage.tsx` | component | request-response | `src/dashboard/src/pages/schedules.tsx` (form + sheet pattern) | role-match |
| `src/dashboard/src/pages/ScanJobPage.tsx` | component | request-response | `src/dashboard/src/pages/schedules.tsx` (status display) | role-match |
| `src/dashboard/src/App.tsx` | config | request-response | `src/dashboard/src/App.tsx` (existing route block, lines 33–47) | exact |
| `src/dashboard/src/components/sidebar.tsx` | component | request-response | `src/dashboard/src/components/sidebar.tsx` (NAV_ITEMS + nav render) | exact |
| `src/dashboard/src/types/api.ts` | model | request-response | `src/dashboard/src/types/api.ts` (existing interface block) | exact |
| `tests/test_jobs_api.py` | test | request-response | `tests/test_schedules_api.py` | exact |
| `tests/test_job_progress.py` | test | CRUD | `tests/test_schedules_api.py` (helper pattern) | role-match |

---

## Pattern Assignments

### `quirk/models.py` — add `ScanJob` class (model, CRUD)

**Analog:** `quirk/models.py`, `ScheduledRun` class (lines 177–194)

**Import pattern** (lines 1–5):
```python
from __future__ import annotations

from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Float

Base = declarative_base()
```

**Core model pattern** (lines 177–194 — `ScheduledRun` is the closest shape: has status lifecycle, dispatched_at/completed_at, scan_id on completion):
```python
class ScheduledRun(Base):
    __tablename__ = "scheduled_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    schedule_id = Column(Integer, nullable=False)
    dispatched_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    status = Column(String(16), nullable=False)       # pending/running/completed/failed
    scan_output_path = Column(Text, nullable=True)
    scan_id = Column(String(64), nullable=True)       # null until scan completes
```

**New `ScanJob` class copies this shape but with String PK, `pid`, `current_stage`, `target`, `profile`, `calibration`, `enable_nmap`, `started_at`, `scan_run_id`, `error_message` per CONTEXT.md D-02. Add after `ScheduledRun`.**

---

### `quirk/db.py` — add `_ensure_scan_jobs_table(engine)` (config/migration, CRUD)

**Analog:** `quirk/db.py`, `_ensure_scheduled_tables` (lines 228–235) and the `init_db` call chain (lines 238–265)

**Core pattern** (lines 228–235):
```python
def _ensure_scheduled_tables(engine) -> None:
    """Phase 63 SCHED-01: create scheduled_scans and scheduled_runs tables if absent.

    Uses Base.metadata.create_all with checkfirst=True. ScheduledScan and
    ScheduledRun are registered on Base.metadata via import of quirk.models.
    New tables only — not new columns — so create_all is correct (not ALTER TABLE).
    """
    Base.metadata.create_all(engine, checkfirst=True)
```

**init_db call-chain tail** (lines 263–265 — insert after this):
```python
    _ensure_scheduled_tables(engine)     # Phase 63 — SCHED-01
    return engine
```

New call goes between `_ensure_scheduled_tables` and `return engine`:
```python
    _ensure_scheduled_tables(engine)     # Phase 63 — SCHED-01
    _ensure_scan_jobs_table(engine)      # Phase 65 — UI-SCAN-01
    return engine
```

---

### `quirk/cli/job_progress.py` — new utility (utility, CRUD)

**Analog:** `quirk/cli/schedule_cmd.py` (lines 1–34 for import + db session pattern); `quirk/cli/scheduler_cmd.py` (lines 39–51 for `_utcnow_naive` + `_resolve_db_path`)

**Import pattern** (`scheduler_cmd.py` lines 1–18):
```python
from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from quirk.db import get_session, init_db
from quirk.models import ScheduledScan, ScheduledRun
```

**`_utcnow_naive` pattern** (`scheduler_cmd.py` line 39–41):
```python
def _utcnow_naive() -> datetime:
    """Return the current UTC time as a timezone-naive datetime (Pitfall 1)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
```

**DB session open-update-close pattern** (`schedule_cmd.py` lines 51–60):
```python
    db_path = _resolve_db_path(args.config)
    init_db(db_path)

    row = ScheduledScan(...)
    with get_session(db_path) as db:
        db.add(row)
        db.flush()
```

**New `job_progress.py` is a standalone helper; the RESEARCH.md §Code Examples provides the full template — open engine directly (not `get_session`) to avoid circular deps, wrap in bare `except Exception: pass` so progress failures never crash the scan.**

---

### `quirk/dashboard/api/routes/jobs.py` — new controller (controller, request-response)

**Analog:** `quirk/dashboard/api/routes/schedules.py` (entire file, 192 lines) — exact structural match

**Import pattern** (lines 1–31):
```python
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from quirk.dashboard.api.deps import get_db
from quirk.dashboard.api.middleware.auth import require_auth
from quirk.dashboard.api.middleware.csrf import require_csrf
from quirk.models import ScheduledRun, ScheduledScan
```

**Auth/CSRF wiring pattern** (line 32 — CRITICAL: single router with both deps applied at construction):
```python
router = APIRouter(dependencies=[Depends(require_auth), Depends(require_csrf)])
```

For `jobs.py`, split into `read_router` (auth only) + `write_router` (auth + CSRF) per CONTEXT.md D-10:
```python
read_router  = APIRouter(dependencies=[Depends(require_auth)])
write_router = APIRouter(dependencies=[Depends(require_auth), Depends(require_csrf)])
```
Both must be included in `app.py` under `/api` prefix.

**`_utcnow_naive` helper** (lines 68–70 — copy verbatim):
```python
def _utcnow_naive() -> datetime:
    """Return current UTC datetime as tz-naive (Pitfall 1 — matches Plan 02 convention)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
```

**`_get_or_404` pattern** (lines 98–102):
```python
def _get_or_404(db: Session, schedule_id: int) -> ScheduledScan:
    row = db.get(ScheduledScan, schedule_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return row
```

**POST create pattern with flush-then-commit** (lines 129–161):
```python
@router.post("/schedules", status_code=201, response_model=ScheduleResponse)
def create_schedule(
    payload: ScheduleCreateRequest,
    db: Session = Depends(get_db),
) -> ScheduleResponse:
    row = ScheduledScan(
        name=payload.name,
        ...
        created_at=_utcnow_naive(),
    )
    db.add(row)
    try:
        db.flush()
        db.commit()
        db.refresh(row)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail=f"Schedule '{payload.name}' already exists")
    return _to_response(db, row)
```

**DELETE pattern returning None / 204** (lines 178–191):
```python
@router.delete("/schedules/{schedule_id}", status_code=204)
def delete_schedule(schedule_id: int, db: Session = Depends(get_db)) -> None:
    row = _get_or_404(db, schedule_id)
    db.delete(row)
    db.commit()
    return None
```

**Key difference for `jobs.py` DELETE:** wrap `os.kill` in `try/except ProcessLookupError: pass` before the DB status update (per CONTEXT.md D-09 / RESEARCH.md §DELETE Cancel Route).

---

### `quirk/dashboard/api/schemas.py` — add two Pydantic schemas (model, request-response)

**Analog:** `quirk/dashboard/api/schemas.py` — existing models (lines 1–271)

**Import pattern** (lines 1–12 — extend existing imports):
```python
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel
```

For Phase 65, add `field_validator` and `Literal` to imports:
```python
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, field_validator
```

**Existing schema definition style** (lines 14–16 — simple BaseModel):
```python
class HealthResponse(BaseModel):
    status: str  # "ok"
```

**New schemas follow the exact field definition style from the existing file; add after the last schema (`TrendTimelineResponse` at line 271). Both schemas are specified verbatim in CONTEXT.md D-05 — copy them exactly.**

---

### `quirk/dashboard/api/app.py` — add lifespan + register jobs router (config, request-response)

**Analog:** `quirk/dashboard/api/app.py` (entire file, 112 lines)

**Current `create_app` signature** (line 35):
```python
def create_app() -> FastAPI:
```

**New signature (backward-compatible per RESEARCH.md Pitfall 1):**
```python
def create_app(db_path: str | None = None) -> FastAPI:
```

**Router registration pattern** (lines 62–67 — add `jobs` import + include_router call here):
```python
    application.include_router(health.router, prefix="/api")
    application.include_router(pdf.router, prefix="/api")
    application.include_router(scan.router, prefix="/api")
    application.include_router(trends.router, prefix="/api")
    application.include_router(qramm.router, prefix="/api")
    application.include_router(schedules.router, prefix="/api")
```

**Module-level `app` line** (line 111 — must remain; uvicorn loads it):
```python
app = create_app()
```

**Lifespan pattern (NEW — no prior analog in this file):** use `@asynccontextmanager` from `contextlib` per CONTEXT.md D-12. The lifespan reads `app.state.db_path` which is set inside `create_app()` before the `FastAPI(...)` instance is created. See RESEARCH.md §Pattern 6 for the exact template.

---

### `run_scan.py` — add `--job-id` + `--db-path` flags (utility, batch)

**Analog:** `run_scan.py` lines 287–345 (existing argparse block)

**Existing argument definition style** (lines 308, 301, 303):
```python
    parser.add_argument("--profile", choices=["quick", "standard", "deep"], default="standard", help="Scan profile")
    parser.add_argument("--discovery", choices=["builtin", "nmap"], default="builtin", ...)
    parser.add_argument("--nmap-path", default="nmap", help="Path to nmap executable (default: nmap)")
```

**New arguments follow the same style — add after the `--profile` argument:**
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

**`_wrapped_phase` injection point pattern** (lines 108–136): each scanner phase is already gated by `_wrapped_phase(...)`. Add `update_job_stage(...)` calls immediately before each `_wrapped_phase` call — 7 total (discovery, tls, ssh, api, identity, data_at_rest, reports). Guard with `if args.job_id:` so CLI users see no change.

---

### `src/dashboard/src/hooks/useJobStatus.ts` — new polling hook (hook, request-response)

**Analog:** `src/dashboard/src/hooks/useSchedules.ts` (entire file, 155 lines)

**Import pattern** (lines 1–2):
```python
import { useState, useEffect, useCallback } from "react"
import { fetchApi } from "@/lib/api"
```

**`let cancelled = false` Phase 62 pattern** (lines 36–78 — MANDATORY; copy exactly):
```typescript
useEffect(() => {
    let cancelled = false

    // Clear stale data synchronously before initiating new fetch (HOOK-01 pattern)
    setData(null)
    setLoading(true)
    setError(null)

    async function fetchData() {
      try {
        const resp = await fetchApi("/api/schedules")
        if (!resp.ok) {
          if (!cancelled) {
            if (resp.status === 401) {
              setError("Authentication required")
            } else if (resp.status === 403) {
              setError("Request blocked")
            } else {
              setError(`API error: ${resp.status} ${resp.statusText}`)
            }
          }
          return
        }
        const json: ScheduleListResponse = await resp.json()
        if (!cancelled) {
          setData(json)
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load schedules")
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    fetchData()
    return () => {
      cancelled = true
    }
  }, [fetchCount])
```

**Key difference for `useJobStatus`:** replace the `fetchCount` trigger with `jobId` as the `useEffect` dependency. Replace the single `fetchData()` call with the recursive `poll()` function using `setTimeout(poll, 3000)` (CONTEXT.md D-07). Add post-completion navigation when `status === "completed"` and `scan_run_id` is set. See RESEARCH.md §Pattern 5 for the full template.

**Also uses (read before implementing):**
- `src/dashboard/src/hooks/useSelectedScan.ts` — for `setSelectedScanId`
- `src/dashboard/src/hooks/useScanList.ts` (lines 11–55) — for `let cancelled = false` + 401/403 error handling pattern

---

### `src/dashboard/src/pages/ScanNewPage.tsx` — new form page (component, request-response)

**Analog:** `src/dashboard/src/pages/schedules.tsx` (lines 1–30 for imports; sheet/form pattern)

**shadcn/ui import pattern** (lines 1–30):
```typescript
import { useState } from "react"
import { Trash2 } from "lucide-react"
import { useSchedules, type Schedule } from "@/hooks/useSchedules"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog"
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { Skeleton } from "@/components/ui/skeleton"
```

**For `ScanNewPage`, use:** `Button`, `Textarea` (for targets), `RadioGroup`/`RadioGroupItem`/`Label` (profile + calibration), `Checkbox` (enable_nmap — install via `npx shadcn add checkbox`), `Card`/`CardContent`/`CardHeader`.

**POST submit pattern** (from `useSchedules.ts` line 100–106 — mutating fetch with JSON body):
```typescript
      const resp = await fetchApi(`/api/schedules/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled }),
      })
```

**On 201 response:** extract `job_id` from body, call `navigate("/scan/job/" + jobId)`. On 422: display field-level error inline.

---

### `src/dashboard/src/pages/ScanJobPage.tsx` — new status page (component, request-response)

**Analog:** `src/dashboard/src/pages/schedules.tsx` (status badge + skeleton pattern); `src/dashboard/src/components/PageSpinner.tsx` (loading state)

**Status badge pattern** (`schedules.tsx` lines 62–80):
```typescript
const STATUS_STYLES: Record<string, string> = {
  pending: "bg-[var(--ds-text-faint)] text-white",
  running: "bg-[var(--ds-high)] text-white",
  completed: "bg-[var(--ds-ok)] text-white",
  failed: "bg-[var(--ds-critical)] text-white",
}

function StatusBadge({ status }: { status: Schedule["last_run_status"] }) {
  if (!status) {
    return (
      <Badge className="bg-[hsl(var(--muted))] text-muted-foreground text-xs">
        Never run
      </Badge>
    )
  }
  return (
    <Badge className={`${STATUS_STYLES[status] ?? ""} text-xs`}>
      {status}
    </Badge>
  )
}
```

**Loading state:** use `<PageSpinner />` (`src/dashboard/src/components/PageSpinner.tsx`) until first poll resolves (`jobStatus === null`).

**404 state:** show error card with link back to `/scan/new` (do not redirect silently per CONTEXT.md Claude's Discretion).

**Cancel button:** `Button variant="destructive"` fires `DELETE /api/jobs/{job_id}`. On 204: `navigate("/scan/new")`.

---

### `src/dashboard/src/App.tsx` — add two routes (config, request-response)

**Analog:** `src/dashboard/src/App.tsx` (entire file, 57 lines)

**Existing import + route block** (lines 1–47):
```typescript
import { BrowserRouter, Routes, Route } from "react-router-dom"
import { ThemeProvider } from "@/components/theme-provider"
...
import { SchedulesPage } from "@/pages/schedules"

export default function App() {
  return (
    ...
    <Routes>
      <Route path="/" element={<ExecutivePage />} />
      ...
      <Route path="/schedules" element={<SchedulesPage />} />
    </Routes>
    ...
  )
}
```

**Add two new imports and routes in the same style:**
```typescript
import { ScanNewPage } from "@/pages/scan-new"
import { ScanJobPage } from "@/pages/scan-job"

// Inside <Routes>:
<Route path="/scan/new" element={<ScanNewPage />} />
<Route path="/scan/job/:jobId" element={<ScanJobPage />} />
```

---

### `src/dashboard/src/components/sidebar.tsx` — add "New Scan" button (component, request-response)

**Analog:** `src/dashboard/src/components/sidebar.tsx` (entire file, 103 lines)

**Existing nav rendering pattern** (lines 23–92):
```typescript
const NAV_ITEMS = [
  { path: "/", label: "Executive Summary", Icon: LayoutDashboard },
  ...
  { path: "/schedules", label: "Schedules", Icon: Calendar },
]

export function Sidebar() {
  const location = useLocation()
  return (
    <aside ...>
      {/* Logo / title */}
      <div ...>...</div>

      {/* Navigation */}
      <nav className="flex-1 flex flex-col gap-1 py-4 px-2" aria-label="Dashboard navigation">
        {NAV_ITEMS.map(({ path, label, Icon }) => { ... })}
      </nav>
      ...
    </aside>
  )
}
```

**Add "New Scan" button ABOVE the `<nav>` block (not inside NAV_ITEMS — it is an action, not a view link):**
```typescript
import { Scan } from "lucide-react"
import { Button } from "@/components/ui/button"
import { useNavigate } from "react-router-dom"

// Inside Sidebar(), before <nav>:
const navigate = useNavigate()

<div className="px-2 py-3 border-b border-border">
  <Tooltip>
    <TooltipTrigger asChild>
      <Button
        variant="default"
        className="w-full justify-start gap-3 min-h-[44px]"
        onClick={() => navigate("/scan/new")}
        aria-label="New Scan"
      >
        <Scan className="h-5 w-5 flex-shrink-0" />
        <span className="hidden lg:block">New Scan</span>
      </Button>
    </TooltipTrigger>
    <TooltipContent side="right" className="lg:hidden">New Scan</TooltipContent>
  </Tooltip>
</div>
```

---

### `src/dashboard/src/types/api.ts` — add TypeScript types (model, request-response)

**Analog:** `src/dashboard/src/types/api.ts` (entire file, 255 lines)

**Existing interface style** (lines 1–8, 141–145):
```typescript
export interface SubScores {
  hygiene: number
  modern_tls: number
  ...
}

export interface ScanSession {
  scan_id: string
  scanned_at: string
  total_endpoints: number
}
```

**Add at end of file, matching this style exactly:**
```typescript
// Phase 65 UI-SCAN-01: job submission and status types
export interface ScanSubmitRequest {
  targets: string
  profile: "quick" | "standard" | "deep"
  calibration: "strict" | "balanced" | "lenient"
  enable_nmap: boolean
}

export interface JobStatus {
  job_id: string
  status: "queued" | "running" | "completed" | "failed" | "cancelled"
  current_stage: string | null
  started_at: string | null
  completed_at: string | null
  scan_run_id: string | null
  error_message: string | null
  stage_index: number    // 0–7, backend-computed
  stage_total: number    // always 7
}
```

---

### `tests/test_jobs_api.py` — new test file (test, request-response)

**Analog:** `tests/test_schedules_api.py` (entire file — exact structural match)

**Test file setup pattern** (lines 1–49):
```python
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from quirk.dashboard.api.app import create_app
from quirk.dashboard.api.deps import get_db
from quirk.models import Base, ScheduledRun


def _make_test_engine():
    engine = create_engine(
        "sqlite:///file::memory:?cache=shared&uri=true",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    return engine


def _app_with_db():
    """Create a fresh TestClient backed by an in-memory DB."""
    engine = _make_test_engine()
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    return app, TestClient(app, raise_server_exceptions=False)
```

**Individual test pattern** (lines 64–80):
```python
def test_get_schedules_empty(dashboard_client):
    """GET /api/schedules with no schedules returns 200 and empty list."""
    response = dashboard_client.get("/api/schedules")
    assert response.status_code == 200, response.text
    data = response.json()
    assert "schedules" in data
    assert data["schedules"] == []
```

**`dashboard_client` fixture** (`tests/conftest.py` lines 76–112): reusable as-is for `test_jobs_api.py`. The fixture calls `create_app()` with no args — this remains valid after the `db_path=None` default parameter change.

**Auth/CSRF negative test pattern** (`test_schedules_api.py` lines 26–49): use `_app_with_db()` helper to create a fresh client without the `X-Quirk-Request` header for CSRF rejection tests, and use `monkeypatch.setenv("QUIRK_API_TOKEN", ...)` for auth rejection tests.

---

### `tests/test_job_progress.py` — new test file (test, CRUD)

**Analog:** `tests/test_schedules_api.py` helper functions pattern

**DB setup pattern** (copy from `_make_test_engine` above):
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from quirk.models import Base, ScanJob
from quirk.cli.job_progress import update_job_stage

def _tmp_db(tmp_path):
    db_file = str(tmp_path / "test.db")
    engine = create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return db_file, engine
```

**Test structure:** use `pytest` `tmp_path` fixture for a real file-based SQLite DB (not in-memory — `update_job_stage` opens its own engine from a path string).

---

## Shared Patterns

### Authentication (all mutating routes)

**Source:** `quirk/dashboard/api/routes/schedules.py` lines 32–33
**Apply to:** `quirk/dashboard/api/routes/jobs.py` — all POST and DELETE handlers

```python
router = APIRouter(dependencies=[Depends(require_auth), Depends(require_csrf)])
```

For `jobs.py`, use split routers (GET read-only needs auth only):
```python
from quirk.dashboard.api.middleware.auth import require_auth
from quirk.dashboard.api.middleware.csrf import require_csrf

read_router  = APIRouter(dependencies=[Depends(require_auth)])
write_router = APIRouter(dependencies=[Depends(require_auth), Depends(require_csrf)])
```

### Datetime Naive-UTC Convention

**Source:** `quirk/dashboard/api/routes/schedules.py` lines 68–70; `quirk/cli/scheduler_cmd.py` lines 39–41
**Apply to:** `quirk/dashboard/api/routes/jobs.py`, `quirk/cli/job_progress.py`

```python
def _utcnow_naive() -> datetime:
    """Return current UTC datetime as tz-naive (Pitfall 1)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
```

NEVER use `datetime.utcnow()` (deprecated) or `datetime.now(timezone.utc)` without `.replace(tzinfo=None)`.

### DB Session (FastAPI dependency)

**Source:** `quirk/dashboard/api/deps.py` lines 29–49; `quirk/dashboard/api/routes/schedules.py` line 123
**Apply to:** all route handlers in `quirk/dashboard/api/routes/jobs.py`

```python
from quirk.dashboard.api.deps import get_db
from sqlalchemy.orm import Session

@router.get("/endpoint")
def my_handler(db: Session = Depends(get_db)):
    ...
```

### React `let cancelled = false` Hook Guard

**Source:** `src/dashboard/src/hooks/useSchedules.ts` lines 36–78; `src/dashboard/src/hooks/useScanList.ts` lines 16–52
**Apply to:** `src/dashboard/src/hooks/useJobStatus.ts`

Every `useEffect` that fetches MUST include:
```typescript
let cancelled = false
// ... all state updates guarded by: if (!cancelled) { ... }
return () => { cancelled = true }
```

### `fetchApi` Authenticated Fetch Wrapper

**Source:** `src/dashboard/src/hooks/useSchedules.ts` line 46; `src/dashboard/src/hooks/useScanList.ts` line 20
**Apply to:** `src/dashboard/src/hooks/useJobStatus.ts`, `src/dashboard/src/pages/ScanNewPage.tsx`

```typescript
import { fetchApi } from "@/lib/api"

const resp = await fetchApi("/api/jobs/some-id")
```

All API calls go through `fetchApi` — it injects auth token + CSRF header automatically.

### shadcn/ui Import Convention

**Source:** `src/dashboard/src/pages/schedules.tsx` lines 1–30
**Apply to:** `src/dashboard/src/pages/ScanNewPage.tsx`, `src/dashboard/src/pages/ScanJobPage.tsx`

Import each component from `@/components/ui/<component>`. No barrel imports. Named exports only.

### 404 HTTP Error Pattern

**Source:** `quirk/dashboard/api/routes/schedules.py` lines 98–102
**Apply to:** `quirk/dashboard/api/routes/jobs.py` GET + DELETE handlers

```python
def _get_or_404(db: Session, job_id: str) -> ScanJob:
    row = db.get(ScanJob, job_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return row
```

---

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| FastAPI lifespan in `app.py` | config | request-response | No `@asynccontextmanager` lifespan exists anywhere in the project yet; use RESEARCH.md §Pattern 6 verbatim |

---

## Metadata

**Analog search scope:** `quirk/dashboard/api/`, `quirk/cli/`, `quirk/models.py`, `quirk/db.py`, `run_scan.py`, `src/dashboard/src/hooks/`, `src/dashboard/src/pages/`, `src/dashboard/src/components/`, `src/dashboard/src/types/`, `tests/`
**Files scanned:** 16 source files read directly
**Pattern extraction date:** 2026-05-13
