# Phase 31: Trend Analysis - Pattern Map

**Mapped:** 2026-04-26
**Files analyzed:** 8 new/modified files
**Analogs found:** 8 / 8

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `quirk/intelligence/trends.py` | service | transform | `quirk/intelligence/scoring.py` + `evidence.py` | role-match (pure function, same intelligence layer) |
| `quirk/dashboard/api/routes/trends.py` | route | request-response | `quirk/dashboard/api/routes/scan.py` | exact (FastAPI router, DB-backed, same prefix) |
| `quirk/dashboard/api/schemas.py` | model | transform | `quirk/dashboard/api/schemas.py` (existing, modified) | exact (append Pydantic models) |
| `src/dashboard/src/hooks/useTrendsData.ts` | hook | request-response | `src/dashboard/src/hooks/useScanData.ts` | exact (same fetch pattern, same return shape) |
| `src/dashboard/src/pages/trends.tsx` | component | request-response | `src/dashboard/src/pages/findings.tsx` | role-match (same page skeleton, same Table/Badge/Skeleton pattern) |
| `src/dashboard/src/App.tsx` | config | request-response | `src/dashboard/src/App.tsx` (existing, modified) | exact (add one Route import + Route element) |
| `src/dashboard/src/components/sidebar.tsx` | component | event-driven | `src/dashboard/src/components/sidebar.tsx` (existing, modified) | exact (append one NAV_ITEMS entry) |
| `tests/test_intelligence_trends.py` | test | batch | `tests/test_dar_vault_scoring.py` | role-match (unit tests for intelligence layer, same CryptoEndpoint fixture pattern) |
| `tests/test_dashboard_trends.py` | test | request-response | `tests/test_dashboard_api.py` | exact (dashboard_client fixture, same assertion style) |

---

## Pattern Assignments

### `quirk/intelligence/trends.py` (service, transform)

**Analog:** `quirk/intelligence/scoring.py` and `quirk/dashboard/api/routes/scan.py`

**Imports pattern** (derived from scoring.py lines 1-4 and scan.py imports):
```python
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from quirk.models import CryptoEndpoint
from quirk.intelligence.evidence import build_evidence_summary
from quirk.intelligence.scoring import compute_readiness_score
```

**Session grouping pattern** (scan.py lines 457-472 — MUST use verbatim):
```python
# list_scans equivalent used inside compute_trend_report to identify sessions
ts_sec = func.strftime("%Y-%m-%d %H:%M:%S", CryptoEndpoint.scanned_at).label("ts_sec")
rows = (
    db.query(ts_sec, func.count(CryptoEndpoint.id).label("cnt"))
    .filter(CryptoEndpoint.scanned_at.isnot(None))   # D-13: exclude NULL-timestamp rows
    .group_by("ts_sec")
    .order_by(ts_sec.desc())
    .limit(10)
    .all()
)
```

**Session endpoint fetch pattern (±1 second window)** (scan.py lines 497-507):
```python
# Fetch all endpoints for a given session timestamp
target_ts = datetime.fromisoformat(scan_id)   # or use datetime object directly
endpoints = (
    db.query(CryptoEndpoint)
    .filter(
        CryptoEndpoint.scanned_at >= target_ts,
        CryptoEndpoint.scanned_at < target_ts + timedelta(seconds=1),
        CryptoEndpoint.scanned_at.isnot(None),   # D-13
    )
    .all()
)
```

**Score derivation pattern** (scoring.py + evidence.py):
```python
# Call once per session — do NOT reimplement scoring logic
from quirk.intelligence.evidence import build_evidence_summary
from quirk.intelligence.scoring import compute_readiness_score

evidence = build_evidence_summary(endpoints)
score_dict = compute_readiness_score(evidence)
score: int = score_dict["score"]   # always int — see RESEARCH.md Pitfall 5
```

**Core return type pattern** (dataclass — Claude's discretion per CONTEXT.md):
```python
@dataclass
class SampleFindingItem:
    host: str
    port: int
    protocol: str
    severity: str

@dataclass
class TrendReport:
    current_session_ts: Optional[datetime]
    previous_session_ts: Optional[datetime]
    current_score: Optional[int]
    previous_score: Optional[int]
    score_delta: Optional[int]
    new_high: int
    new_medium: int
    new_low: int
    resolved_high: int
    resolved_medium: int
    resolved_low: int
    scan_errors_new_count: int
    scan_errors_resolved_count: int
    new_findings_sample: List[SampleFindingItem] = field(default_factory=list)
    resolved_findings_sample: List[SampleFindingItem] = field(default_factory=list)
```

**Function signature** (D-12: no datetime.now() inside):
```python
def compute_trend_report(
    current_ts: datetime,
    previous_ts: Optional[datetime],
    db: Session,
) -> TrendReport:
    """Compare two scan sessions and return a trend report.

    Accuracy note: Trend accuracy depends on consistent target configuration
    between scans — IP-addressed targets may produce phantom new/resolved
    findings if IPs change. NULL collision with v4.2-era sessions
    (scanned_at IS NULL) is expected behavior per D-13.
    """
```

**Finding delta logic pattern**:
```python
# D-04: exclude scan_error rows from finding delta
current_keys  = {(ep.host, ep.port, ep.protocol, ep.severity)
                 for ep in current_eps if ep.scan_error is None}
previous_keys = {(ep.host, ep.port, ep.protocol, ep.severity)
                 for ep in previous_eps if ep.scan_error is None}

new_keys      = current_keys  - previous_keys   # D-02/D-03 match key
resolved_keys = previous_keys - current_keys

# D-05: scan error count delta separately
scan_errors_new_count      = max(0,
    sum(1 for ep in current_eps  if ep.scan_error is not None) -
    sum(1 for ep in previous_eps if ep.scan_error is not None))
scan_errors_resolved_count = max(0,
    sum(1 for ep in previous_eps if ep.scan_error is not None) -
    sum(1 for ep in current_eps  if ep.scan_error is not None))
```

**Single-session edge case** (D-06):
```python
# When only one session exists, return null-delta response
if previous_ts is None:
    return TrendReport(
        current_session_ts=current_ts,
        previous_session_ts=None,
        current_score=current_score,
        previous_score=None,
        score_delta=None,
        new_high=0, new_medium=0, new_low=0,
        resolved_high=0, resolved_medium=0, resolved_low=0,
        scan_errors_new_count=0,
        scan_errors_resolved_count=0,
    )
```

---

### `quirk/dashboard/api/routes/trends.py` (route, request-response)

**Analog:** `quirk/dashboard/api/routes/scan.py`

**Imports pattern** (scan.py top — adapt for trends):
```python
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from quirk.dashboard.api.deps import get_db
from quirk.dashboard.api.schemas import TrendReportResponse
from quirk.intelligence.trends import compute_trend_report
```

**Router registration pattern** (app.py lines 19, 40-42):
```python
# app.py line 19 — add trends to import:
from quirk.dashboard.api.routes import health, pdf, scan, trends

# app.py lines 40-42 — add include_router call after scan:
application.include_router(health.router, prefix="/api")
application.include_router(pdf.router, prefix="/api")
application.include_router(scan.router, prefix="/api")
application.include_router(trends.router, prefix="/api")   # <-- add this line
```

**Router declaration pattern** (scan.py pattern):
```python
router = APIRouter()
```

**Route handler pattern** (scan.py lines 449-472 for list_scans, lines 485-489 for decorator):
```python
@router.get("/trends", response_model=TrendReportResponse)
def get_trends(db: Session = Depends(get_db)) -> TrendReportResponse:
    """GET /api/trends — returns trend data for the two most recent scan sessions.

    Returns HTTP 200 with score_delta=null and all counts=0 when only one
    scan session exists (D-06). No HTTP 404 raised for single-session state.
    """
    # Reuse list_scans logic inline (import and call, or inline the strftime query)
    sessions = list_scans(db)   # or inline the strftime grouping from scan.py:457-472
    if len(sessions) < 2:
        # D-06: single-session response — no exception
        current_ts = sessions[0].scanned_at if sessions else None
        return TrendReportResponse(current_session_ts=current_ts)

    report = compute_trend_report(
        current_ts=sessions[0].scanned_at,
        previous_ts=sessions[1].scanned_at,
        db=db,
    )
    return TrendReportResponse(**vars(report))
```

**Error handling pattern** (scan.py line 499 — HTTPException for invalid input only):
```python
# GET /api/trends accepts NO parameters — no user input to validate.
# The only error surface is scan.py-style HTTPException for DB failures
# (inherit FastAPI's default 500 handling — no explicit try/except needed here).
```

---

### `quirk/dashboard/api/schemas.py` (model, transform — modified file)

**Analog:** `quirk/dashboard/api/schemas.py` (existing file)

**Existing model convention** (schemas.py lines 1-13, 27-32):
```python
"""Pydantic response models for the QU.I.R.K. dashboard API.

These models define the contract between FastAPI and the React frontend.
TypeScript types in src/dashboard/src/types/api.ts must mirror these exactly.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel
```

**New models to append** (after `ScanSession` at line 134 — follow existing Pydantic field convention):
```python
# ---- Trend Analysis ----

class SampleFinding(BaseModel):
    host: str
    port: int
    protocol: str
    severity: str


class TrendReportResponse(BaseModel):
    current_session_ts: Optional[datetime] = None
    previous_session_ts: Optional[datetime] = None
    current_score: Optional[int] = None        # int matches compute_readiness_score() return
    previous_score: Optional[int] = None
    score_delta: Optional[int] = None          # null when no previous session (D-06)
    new_high: int = 0
    new_medium: int = 0
    new_low: int = 0
    resolved_high: int = 0
    resolved_medium: int = 0
    resolved_low: int = 0
    scan_errors_new_count: int = 0
    scan_errors_resolved_count: int = 0
    new_findings_sample: List[SampleFinding] = []
    resolved_findings_sample: List[SampleFinding] = []
```

---

### `src/dashboard/src/hooks/useTrendsData.ts` (hook, request-response)

**Analog:** `src/dashboard/src/hooks/useScanData.ts` (lines 1-58, full file)

**Full pattern to mirror** (useScanData.ts lines 1-58):
```typescript
import { useState, useEffect } from "react"
import type { TrendReport } from "@/types/api"

interface UseTrendsDataResult {
  data: TrendReport | null
  loading: boolean
  error: string | null
}

export function useTrendsData(): UseTrendsDataResult {
  const [data, setData] = useState<TrendReport | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    async function fetchData() {
      try {
        setLoading(true)
        setError(null)
        const resp = await fetch("/api/trends")
        if (!resp.ok) {
          setError(`API error: ${resp.status} ${resp.statusText}`)
          return
        }
        const json: TrendReport = await resp.json()
        if (!cancelled) {
          setData(json)
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load trend data")
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
  }, [])   // no dependency array items — trends endpoint has no scan_id param

  return { data, loading, error }
}
```

**Key difference from useScanData:** No `useSelectedScan()` context dependency — `GET /api/trends` always returns the two most recent sessions with no parameter. The effect dependency array is `[]` (empty).

---

### `src/dashboard/src/pages/trends.tsx` (component, request-response)

**Analog:** `src/dashboard/src/pages/findings.tsx`

**Imports pattern** (findings.tsx lines 1-22 — adapt for trends):
```typescript
import { useTrendsData } from "@/hooks/useTrendsData"
import type { TrendReport, SampleFinding } from "@/types/api"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Card, CardContent, CardHeader, CardTitle,
} from "@/components/ui/card"
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"
```

**Loading/error skeleton pattern** (findings.tsx lines 96-97):
```typescript
if (loading) return (
  <div className="space-y-2">
    {Array.from({ length: 5 }).map((_, i) => (
      <Skeleton key={i} className="h-10 w-full" />
    ))}
  </div>
)
if (error) return <p className="text-muted-foreground text-sm">{error}</p>
```

**Empty state pattern** (findings.tsx lines 100-108):
```typescript
// Baseline scan empty state (D-06: previous_session_ts is null)
if (!data?.previous_session_ts) {
  return (
    <div className="text-center py-12">
      <h2 className="text-foreground font-semibold text-xl">Baseline scan</h2>
      <p className="text-muted-foreground mt-2 text-sm">
        Run another scan to see your progress over time.
      </p>
    </div>
  )
}
```

**Page structure pattern** (findings.tsx line 111-113):
```typescript
return (
  <div className="space-y-4">
    <h1 style={{ fontSize: 20, fontWeight: 600 }}>Trends</h1>
    {/* ... cards, tables ... */}
  </div>
)
```

**SEVERITY_STYLES badge map** (findings.tsx lines 23-29 — copy verbatim for sample tables):
```typescript
const SEVERITY_STYLES: Record<string, string> = {
  CRITICAL: "bg-[hsl(0_72%_51%)] text-white",
  HIGH: "bg-[hsl(24_95%_53%)] text-white",
  MEDIUM: "bg-[hsl(38_92%_50%)] text-black",
  LOW: "bg-[hsl(213_94%_68%)] text-black",
  INFO: "bg-[hsl(240_5%_46%)] text-white",
}
```

**Table pattern** (findings.tsx lines 145-160 — simplified for 4-column sample tables):
```typescript
<div className="rounded-md border border-border">
  <Table>
    <TableHeader>
      <TableRow>
        <TableHead>Host</TableHead>
        <TableHead>Port</TableHead>
        <TableHead>Protocol</TableHead>
        <TableHead>Severity</TableHead>
      </TableRow>
    </TableHeader>
    <TableBody>
      {items.map((f, i) => (
        <TableRow key={i} className="hover:bg-accent/5">
          <TableCell className="text-sm py-2">{f.host}</TableCell>
          <TableCell className="text-sm py-2">{f.port}</TableCell>
          <TableCell className="text-sm py-2">{f.protocol}</TableCell>
          <TableCell className="text-sm py-2">
            <Badge className={`${SEVERITY_STYLES[f.severity] ?? ""} text-xs`}>
              {f.severity}
            </Badge>
          </TableCell>
        </TableRow>
      ))}
    </TableBody>
  </Table>
</div>
```

**Collapsible wrapper** (native HTML — shadcn Collapsible NOT installed per RESEARCH.md):
```typescript
{/* Do NOT use shadcn Collapsible — it is not in src/dashboard/src/components/ui/ */}
{items.length > 0 && (
  <details className="rounded-md border border-border">
    <summary className="cursor-pointer px-4 py-2 text-sm font-semibold">
      Show {items.length} samples
    </summary>
    {/* Table goes here */}
  </details>
)}
```

**Score delta badge pattern** (UI-SPEC.md approved colors):
```typescript
function ScoreDeltaBadge({ delta }: { delta: number | null }) {
  if (delta === null) return <Badge variant="outline">— First scan</Badge>
  if (delta > 0) return (
    <Badge className="bg-[hsl(var(--quantum-safe))] text-white">
      ▲ +{delta} pts
    </Badge>
  )
  if (delta < 0) return (
    <Badge className="bg-[hsl(var(--destructive))] text-white">
      ▼ {delta} pts
    </Badge>
  )
  return <Badge className="bg-[hsl(var(--muted))] text-muted-foreground">No change</Badge>
}
```

**Export convention** (findings.tsx line 31):
```typescript
export function TrendsPage() {
  // ...
}
```

---

### `src/dashboard/src/App.tsx` (config — modified file)

**Analog:** `src/dashboard/src/App.tsx` (existing file, lines 1-43)

**Import addition** (after line 12 `import { RoadmapPage }`):
```typescript
import { TrendsPage } from "@/pages/trends"
```

**Route addition** (inside `<Routes>`, after line 32 `<Route path="/roadmap">`):
```tsx
<Route path="/trends" element={<TrendsPage />} />
```

---

### `src/dashboard/src/components/sidebar.tsx` (component — modified file)

**Analog:** `src/dashboard/src/components/sidebar.tsx` (existing file, lines 1-25)

**Import addition** (line 6 — add TrendingUp alongside existing icons):
```typescript
import {
  LayoutDashboard,
  AlertTriangle,
  Shield,
  Database,
  GitBranch,
  Fingerprint,
  TrendingUp,    // <-- add this
} from "lucide-react"
```

**NAV_ITEMS addition** (after line 24 `{ path: "/roadmap", ... }`):
```typescript
const NAV_ITEMS = [
  { path: "/", label: "Executive Summary", Icon: LayoutDashboard },
  { path: "/findings", label: "Findings", Icon: AlertTriangle },
  { path: "/identity", label: "Identity", Icon: Fingerprint },
  { path: "/certificates", label: "Certificates", Icon: Shield },
  { path: "/cbom", label: "CBOM Viewer", Icon: Database },
  { path: "/roadmap", label: "Migration Roadmap", Icon: GitBranch },
  { path: "/trends", label: "Trends", Icon: TrendingUp },   // <-- add this
]
```

---

### `src/dashboard/src/types/api.ts` (model — modified file)

**Analog:** `src/dashboard/src/types/api.ts` (existing file)

**Convention** (api.ts lines 1-60 — all interfaces, camelCase mirrors snake_case Pydantic fields):
```typescript
// Append after existing interfaces — mirror schemas.py SampleFinding + TrendReportResponse exactly

export interface SampleFinding {
  host: string
  port: number
  protocol: string
  severity: string
}

export interface TrendReport {
  current_session_ts: string | null
  previous_session_ts: string | null
  current_score: number | null
  previous_score: number | null
  score_delta: number | null
  new_high: number
  new_medium: number
  new_low: number
  resolved_high: number
  resolved_medium: number
  resolved_low: number
  scan_errors_new_count: number
  scan_errors_resolved_count: number
  new_findings_sample: SampleFinding[]
  resolved_findings_sample: SampleFinding[]
}
```

---

### `tests/test_intelligence_trends.py` (test, batch)

**Analog:** `tests/test_dar_vault_scoring.py`

**Imports and fixture pattern** (test_dar_vault_scoring.py lines 1-20):
```python
"""Tests for Phase 31 compute_trend_report() — TREND-01 through TREND-03, D-03/D-04/D-05/D-13."""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from quirk.models import Base, CryptoEndpoint
from quirk.intelligence.trends import compute_trend_report


# Helper to build CryptoEndpoint objects (in-memory — no DB required for unit tests)
def _ep(host: str, port: int, protocol: str, severity: str,
        scanned_at: datetime = datetime(2026, 4, 26, 9, 0, 0),
        scan_error: str | None = None) -> CryptoEndpoint:
    return CryptoEndpoint(
        host=host, port=port, protocol=protocol, severity=severity,
        scanned_at=scanned_at, scan_error=scan_error,
    )
```

**In-memory DB fixture pattern** (conftest.py lines 83-111 — inline for intelligence tests):
```python
@pytest.fixture
def db():
    """In-memory SQLite session for trend unit tests."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
```

**Test naming pattern** (test_dar_vault_scoring.py — one assertion per test, descriptive names):
```python
def test_score_delta_computed(db):
    # TREND-01: score_delta is non-null when two sessions exist
    ...

def test_single_session_null_delta(db):
    # TREND-01: score_delta is None when only one session
    ...

def test_new_findings_counted(db):
    # TREND-02: new findings counted by severity
    ...

def test_resolved_findings_counted(db):
    # TREND-03: resolved findings counted by severity
    ...

def test_severity_change_surfaces(db):
    # D-03: severity change = old resolved + new new
    ...

def test_scan_error_excluded_from_delta(db):
    # D-04: scan_error rows not in finding delta
    ...

def test_scan_error_counts_surfaced(db):
    # D-05: error counts tracked separately
    ...

def test_null_scanned_at_excluded(db):
    # D-13: NULL scanned_at rows excluded
    ...
```

---

### `tests/test_dashboard_trends.py` (test, request-response)

**Analog:** `tests/test_dashboard_api.py`

**Imports and fixture pattern** (test_dashboard_api.py lines 1-8):
```python
"""Dashboard API integration tests — GET /api/trends.

Uses dashboard_client fixture from conftest.py (in-memory SQLite DB override).
"""
import pytest
```

**Test pattern** (test_dashboard_api.py lines 22-43):
```python
def test_trends_endpoint_schema(dashboard_client):
    """TREND-04: GET /api/trends returns HTTP 200 with correct schema."""
    resp = dashboard_client.get("/api/trends")
    assert resp.status_code == 200
    data = resp.json()
    assert "score_delta" in data
    assert "new_high" in data
    assert "new_findings_sample" in data
    assert isinstance(data["new_findings_sample"], list)


def test_trends_single_session(dashboard_client):
    """D-06: GET /api/trends returns score_delta=null when 0-1 sessions exist."""
    resp = dashboard_client.get("/api/trends")
    assert resp.status_code == 200
    data = resp.json()
    # Empty DB: previous_session_ts must be null, score_delta must be null
    assert data["previous_session_ts"] is None
    assert data["score_delta"] is None
```

---

## Shared Patterns

### SQLAlchemy DB Session Dependency
**Source:** `quirk/dashboard/api/routes/scan.py` (all route handlers)
**Apply to:** `quirk/dashboard/api/routes/trends.py`
```python
from quirk.dashboard.api.deps import get_db

@router.get("/trends", response_model=TrendReportResponse)
def get_trends(db: Session = Depends(get_db)) -> TrendReportResponse:
    ...
```

### Router Registration in app.py
**Source:** `quirk/dashboard/api/app.py` lines 19 and 40-42
**Apply to:** `quirk/dashboard/api/app.py` (modification)
```python
# Line 19 — add trends to import
from quirk.dashboard.api.routes import health, pdf, scan, trends

# Line 43 — add after scan router
application.include_router(trends.router, prefix="/api")
```

### Pydantic Optional Fields with Defaults
**Source:** `quirk/dashboard/api/schemas.py` (all models)
**Apply to:** `TrendReportResponse` in `schemas.py`
```python
# Convention: all optional fields get a sensible default (None or 0 or [])
# so the D-06 single-session response can be constructed with minimal kwargs:
return TrendReportResponse(current_session_ts=current_ts)
# ^ all other fields default to None/0/[]
```

### TypeScript Interface Convention
**Source:** `src/dashboard/src/types/api.ts` (all interfaces)
**Apply to:** `TrendReport` and `SampleFinding` in `api.ts`

- Field names use `snake_case` (match JSON from FastAPI exactly, not camelCase)
- `datetime` fields from Python become `string | null` in TypeScript (ISO string from JSON)
- `Optional[int]` becomes `number | null`
- `List[X]` becomes `X[]`

### Skeleton Loading State
**Source:** `src/dashboard/src/pages/findings.tsx` lines 96
**Apply to:** `src/dashboard/src/pages/trends.tsx`
```typescript
if (loading) return (
  <div className="space-y-2">
    {Array.from({ length: 5 }).map((_, i) => (
      <Skeleton key={i} className="h-10 w-full" />
    ))}
  </div>
)
```

### strftime Session Grouping (CRITICAL — must not deviate)
**Source:** `quirk/dashboard/api/routes/scan.py` lines 457
**Apply to:** `quirk/intelligence/trends.py` (session listing inside compute_trend_report)
```python
# This exact expression must be used — any deviation breaks session boundary
# consistency with list_scans() and the rest of the app
func.strftime("%Y-%m-%d %H:%M:%S", CryptoEndpoint.scanned_at)
```

---

## No Analog Found

All files in Phase 31 have strong analogs. No entries.

---

## Metadata

**Analog search scope:** `quirk/intelligence/`, `quirk/dashboard/api/routes/`, `quirk/dashboard/api/schemas.py`, `quirk/dashboard/api/app.py`, `src/dashboard/src/hooks/`, `src/dashboard/src/pages/`, `src/dashboard/src/App.tsx`, `src/dashboard/src/components/sidebar.tsx`, `src/dashboard/src/types/api.ts`, `tests/`
**Files scanned:** 15 source files read directly
**Pattern extraction date:** 2026-04-26

### Critical Implementation Warnings

1. **strftime grouping is mandatory** — any session listing inside `compute_trend_report()` must use `func.strftime("%Y-%m-%d %H:%M:%S", CryptoEndpoint.scanned_at)` verbatim (scan.py:457). Raw `scanned_at` grouping produces one "session" per row.

2. **Collapsible component is NOT installed** — `src/dashboard/src/components/ui/` has no `collapsible.tsx`. Use native `<details>`/`<summary>` HTML elements.

3. **router registration is manual** — `app.py` uses explicit `include_router()` calls (lines 40-42). New `trends.py` router must be added to the import on line 19 AND registered on a new line after line 42.

4. **score_delta is `int`, not `float`** — `compute_readiness_score()["score"]` returns `int`. Use `Optional[int]` in both Pydantic schema and TypeScript interface. TypeScript `number` covers both.

5. **useTrendsData has no scan_id dependency** — Unlike `useScanData`, the trends hook fetches a fixed endpoint with no parameters. The `useEffect` dependency array is `[]`, not `[selectedScanId]`.
