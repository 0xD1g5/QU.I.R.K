# Phase 66: Dashboard Scan History + Clone/Compare — Pattern Map

**Mapped:** 2026-05-14
**Files analyzed:** 9 new/modified files
**Analogs found:** 9 / 9

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `quirk/dashboard/api/routes/scan.py` | route (extend) | request-response / CRUD | `quirk/dashboard/api/routes/trends.py` | exact |
| `quirk/dashboard/api/schemas.py` | model (extend) | — | `quirk/dashboard/api/schemas.py` (existing ScanSession, FindingCounts) | exact |
| `src/dashboard/src/types/api.ts` | model (extend) | — | `src/dashboard/src/types/api.ts` (existing ScanSession interface) | exact |
| `src/dashboard/src/hooks/useCompareData.ts` | hook | request-response | `src/dashboard/src/hooks/useTimelineData.ts` | exact |
| `src/dashboard/src/pages/scan-history.tsx` | component (page) | request-response | `src/dashboard/src/pages/trends.tsx` + `src/dashboard/src/pages/findings.tsx` | role-match |
| `src/dashboard/src/pages/compare.tsx` | component (page) | request-response | `src/dashboard/src/pages/trends.tsx` | role-match |
| `src/dashboard/src/pages/scan-new.tsx` | component (extend) | request-response | self (existing ScanNewPage with `useSearchParams` addition) | exact |
| `src/dashboard/src/App.tsx` | config (extend) | — | self (existing Route entries) | exact |
| `src/dashboard/src/components/sidebar.tsx` | component (extend) | — | self (existing NAV_ITEMS array) | exact |

---

## Pattern Assignments

### `quirk/dashboard/api/routes/scan.py` (route, request-response)

**Analogs:**
- `quirk/dashboard/api/routes/scan.py` lines 737–760 — `list_scans()` (extend this directly)
- `quirk/dashboard/api/routes/trends.py` lines 153–195 — `get_trends_timeline()` (PRIMARY template for per-session enrichment loop)

**Imports pattern** (`scan.py` lines 1–34):
```python
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from quirk.dashboard.api.middleware.auth import require_auth
from sqlalchemy import func
from sqlalchemy.orm import Session

from quirk.dashboard.api.deps import get_db
from quirk.dashboard.api.schemas import (
    ScanSession,
    # Phase 66 additions:
    CompareResponse, CompareScanSummary, CompareFinding, CompareEndpoint, SubscoreDelta,
    FindingCounts,
)
from quirk.models import CryptoEndpoint, ScanJob
from quirk.intelligence.evidence import build_evidence_summary
from quirk.intelligence.scoring import compute_readiness_score
from quirk.intelligence.trends import _count_by_bucket

router = APIRouter(dependencies=[Depends(require_auth)])
```

**Auth pattern** (`scan.py` line 34):
```python
# Router-level: ALL routes in this file get require_auth for free.
# Do NOT add require_auth as a per-route dependency on compare_scans().
router = APIRouter(dependencies=[Depends(require_auth)])
```

**Current `list_scans()` to extend** (`scan.py` lines 737–760):
```python
@router.get("/scans", response_model=List[ScanSession])
def list_scans(db: Session = Depends(get_db)) -> List[ScanSession]:
    ts_sec = func.strftime("%Y-%m-%d %H:%M:%S", CryptoEndpoint.scanned_at).label("ts_sec")
    rows = (
        db.query(ts_sec, func.count(CryptoEndpoint.id).label("cnt"))
        .group_by("ts_sec")
        .order_by(ts_sec.desc())
        .limit(10)       # REMOVE THIS — D-01
        .all()
    )
    return [
        ScanSession(
            scan_id=ts_str,
            scanned_at=datetime.fromisoformat(ts_str),
            total_endpoints=cnt,
        )
        for ts_str, cnt in rows
    ]
```

**Per-session enrichment loop pattern** (`trends.py` lines 166–195 — PRIMARY template for Phase 66 extension):
```python
# From get_trends_timeline() — copy this exact structure into the list_scans() loop
for ts in sessions:
    eps = _fetch_session_endpoints(db, ts)
    if not eps:
        continue
    evidence = build_evidence_summary(eps)
    score_dict = compute_readiness_score(evidence)
    sub = score_dict["subscores"]
    keys = [
        (ep.host, ep.port, ep.protocol, ep.severity)
        for ep in eps
        if ep.scan_error is None
    ]
    counts = _count_by_bucket(keys)
    points.append(
        TrendSessionPoint(
            session_ts=ts.isoformat(),
            score=int(score_dict["score"]),
            subscores=sub,
            finding_counts=FindingCounts(
                high=counts.get("high", 0),
                medium=counts.get("medium", 0),
                low=counts.get("low", 0),
            ),
        )
    )
```

**CRITICAL PITFALL — Session precision mismatch** (RESEARCH.md Pitfall 1):
`list_scans()` groups by second-precision `ts_sec` strings. `_fetch_session_endpoints()` uses a 1ms window — it will miss endpoints with sub-second `scanned_at`. Instead, define a private 1-second window helper matching `get_latest_scan()`'s pattern, OR filter directly with:
```python
def _fetch_session_endpoints_1s(db: Session, ts: datetime) -> list[CryptoEndpoint]:
    """Fetch all CryptoEndpoint rows for a session using a 1-second window.

    Used by list_scans() and compare_scans() which group by second-precision
    timestamps. Do NOT use _fetch_session_endpoints() (uses 1ms window —
    incompatible with second-precision ts_sec strings).
    """
    return (
        db.query(CryptoEndpoint)
        .filter(
            CryptoEndpoint.scanned_at >= ts,
            CryptoEndpoint.scanned_at < ts + timedelta(seconds=1),
            CryptoEndpoint.scanned_at.isnot(None),
        )
        .all()
    )
```

**ScanJob join for clone data** (`quirk/models.py` lines 196–215, RESEARCH.md Pattern 1):
```python
# Inside the list_scans() enrichment loop, after fetching eps:
# Use startswith to handle precision mismatches (RESEARCH.md Pitfall 2)
job = db.query(ScanJob).filter(
    ScanJob.scan_run_id.startswith(ts_str[:19])
).first()
if job:
    target, profile, calibration = job.target, job.profile, job.calibration
else:
    # CLI-launched: reconstruct from distinct hosts
    hosts = {ep.host for ep in eps if ep.host}
    target = ", ".join(sorted(hosts)) if hosts else None
    profile, calibration = None, None
```

**New `compare_scans()` route** (RESEARCH.md Pattern 3 + Code Examples):
```python
@router.get("/compare", response_model=CompareResponse)
def compare_scans(
    a: str = Query(..., description="scan_id of scan A (newer)"),
    b: str = Query(..., description="scan_id of scan B (baseline)"),
    db: Session = Depends(get_db),
) -> CompareResponse:
    if a == b:
        raise HTTPException(status_code=400, detail="Cannot compare a scan to itself.")
    try:
        ts_a = datetime.fromisoformat(a)
        ts_b = datetime.fromisoformat(b)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid scan_id format.")

    eps_a = _fetch_session_endpoints_1s(db, ts_a)
    eps_b = _fetch_session_endpoints_1s(db, ts_b)
    if not eps_a:
        raise HTTPException(status_code=404, detail=f"No scan found: {a!r}")
    if not eps_b:
        raise HTTPException(status_code=404, detail=f"No scan found: {b!r}")
    # ... score computation, diff logic, return CompareResponse
```

**Error handling pattern** (`scan.py` lines 773–800 — `get_latest_scan` reference):
```python
# FastAPI raises HTTPException directly — no try/except wrapping needed for
# normal 404/400 cases. Let router-level exception handlers deal with 500s.
raise HTTPException(status_code=404, detail="No scan found: ...")
raise HTTPException(status_code=400, detail="Cannot compare a scan to itself.")
```

---

### `quirk/dashboard/api/schemas.py` (model, extend)

**Analog:** `quirk/dashboard/api/schemas.py` lines 206–210 (`ScanSession`), lines 241–261 (`FindingCounts`, `TrendSessionPoint`)

**CRITICAL:** `FindingCounts` already exists at lines 241–249. Do NOT add a second definition.

**Existing `ScanSession` to extend** (lines 206–210):
```python
class ScanSession(BaseModel):
    scan_id: str          # ISO timestamp string
    scanned_at: datetime
    total_endpoints: int
    # Phase 66 additions — all Optional/default for backward compat with ScanSelector:
    score: int = 0
    profile: Optional[str] = None
    calibration: Optional[str] = None
    target: Optional[str] = None
    finding_counts: "FindingCounts" = Field(default_factory=FindingCounts)
```

**Existing `FindingCounts`** (lines 241–249 — reuse as-is, no changes):
```python
class FindingCounts(BaseModel):
    high: int = 0
    medium: int = 0
    low: int = 0
```

**Existing `SubScores`** (lines 20–27 — reuse in `SubscoreDelta` arithmetic):
```python
class SubScores(BaseModel):
    hygiene: int
    modern_tls: int
    identity_trust: int
    agility_signals: int
    data_at_rest: int = 0
    data_in_motion: int = 0
```

**New schemas to add** (RESEARCH.md Code Examples):
```python
class CompareScanSummary(BaseModel):
    scan_id: str
    scanned_at: datetime
    score: int

class SubscoreDelta(BaseModel):
    hygiene: int = 0
    modern_tls: int = 0
    identity_trust: int = 0
    agility_signals: int = 0
    data_at_rest: int = 0
    data_in_motion: int = 0

class CompareFinding(BaseModel):
    host: str
    protocol: Optional[str] = None
    severity: str
    description: Optional[str] = None

class CompareEndpoint(BaseModel):
    host: str
    reason: Optional[str] = None

class CompareResponse(BaseModel):
    scan_a: CompareScanSummary
    scan_b: CompareScanSummary
    score_delta: int
    subscore_deltas: SubscoreDelta
    added_findings: List[CompareFinding] = []
    removed_findings: List[CompareFinding] = []
    endpoints_only_in_a: List[str] = []
    endpoints_only_in_b: List[str] = []
    changed_endpoints: List[CompareEndpoint] = []
```

---

### `src/dashboard/src/types/api.ts` (model, extend)

**Analog:** `src/dashboard/src/types/api.ts` lines 141–145 (existing `ScanSession`), lines 1–15 (`SubScores`)

**Existing `ScanSession` to extend** (lines 141–145):
```typescript
// Current — extend in place:
export interface ScanSession {
  scan_id: string
  scanned_at: string
  total_endpoints: number
  // Phase 66 additions:
  score: number
  profile: string | null
  calibration: string | null
  target: string | null
  finding_counts: { high: number; medium: number; low: number }
}
```

**New interfaces to add** (RESEARCH.md Code Examples):
```typescript
export interface CompareScanSummary {
  scan_id: string
  scanned_at: string
  score: number
}

export interface SubscoreDelta {
  hygiene: number
  modern_tls: number
  identity_trust: number
  agility_signals: number
  data_at_rest: number
  data_in_motion: number
}

export interface CompareFinding {
  host: string
  protocol?: string
  severity: string
  description?: string
}

export interface CompareEndpoint {
  host: string
  reason?: string
}

export interface CompareResponse {
  scan_a: CompareScanSummary
  scan_b: CompareScanSummary
  score_delta: number
  subscore_deltas: SubscoreDelta
  added_findings: CompareFinding[]
  removed_findings: CompareFinding[]
  endpoints_only_in_a: string[]
  endpoints_only_in_b: string[]
  changed_endpoints: CompareEndpoint[]
}
```

---

### `src/dashboard/src/hooks/useCompareData.ts` (hook, request-response)

**Analog:** `src/dashboard/src/hooks/useTimelineData.ts` lines 1–63 (exact match — same fetch+cancel pattern with query params)

**Full hook pattern** (copy structure from `useTimelineData.ts` lines 11–63, adapted for compare):
```typescript
import { useState, useEffect } from "react"
import type { CompareResponse } from "@/types/api"
import { fetchApi } from "@/lib/api"

interface UseCompareDataResult {
  data: CompareResponse | null
  loading: boolean
  error: string | null
}

export function useCompareData(
  scanA: string | null,
  scanB: string | null,
): UseCompareDataResult {
  const [data, setData] = useState<CompareResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!scanA || !scanB) return
    let cancelled = false        // HOOK-01: cancellation flag (Phase 62)
    setData(null)
    setLoading(true)
    setError(null)

    async function fetchCompare() {
      try {
        const resp = await fetchApi(
          `/api/compare?a=${encodeURIComponent(scanA)}&b=${encodeURIComponent(scanB)}`
        )
        if (!resp.ok) {
          if (!cancelled) {                            // HOOK-02: guard all branches
            if (resp.status === 401) { setError("Authentication required"); return }
            if (resp.status === 403) { setError("Request blocked"); return }
            if (resp.status === 429) {
              const retryAfter = resp.headers.get("Retry-After") ?? "60"
              setError(`Too many requests. Wait ${retryAfter} seconds and try again.`)
              return
            }
            if (resp.status === 400) {
              const body = await resp.json().catch(() => ({}))
              setError(body?.detail ?? "Bad request")
              return
            }
            setError(`API error: ${resp.status} ${resp.statusText}`)
          }
          return
        }
        const result: CompareResponse = await resp.json()
        if (!cancelled) setData(result)              // HOOK-02: guard setState
      } catch (err) {
        if (!cancelled)                              // HOOK-02: guard catch branch
          setError(err instanceof Error ? err.message : "Failed to load comparison")
      } finally {
        if (!cancelled) setLoading(false)            // HOOK-02: guard finally
      }
    }

    fetchCompare()
    return () => { cancelled = true }               // HOOK-03: cleanup sets flag
  }, [scanA, scanB])

  return { data, loading, error }
}
```

**MANDATORY Phase 62 rules (HOOK-01..04):**
- NEVER use `AbortController` — flag pattern only
- ALL `setState` calls after any `await` MUST be guarded with `if (!cancelled)`
- This includes 401, 403, 429, 400, and the general `catch` block — not just the success path

---

### `src/dashboard/src/pages/scan-history.tsx` (component/page, request-response)

**Analogs:**
- `src/dashboard/src/pages/findings.tsx` lines 1–60 — Table + Badge + filtering pattern, `useScanData` hook usage
- `src/dashboard/src/pages/trends.tsx` lines 1–50 — Card layout, PageSpinner, SEVERITY_STYLES

**Imports pattern** (copy from `findings.tsx` lines 1–25 + `trends.tsx` lines 1–17):
```typescript
import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { useScanList } from "@/hooks/useScanList"
import { PageSpinner } from "@/components/PageSpinner"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"
import type { ScanSession } from "@/types/api"
```

**Table + Badge severity pattern** (`findings.tsx` lines 25–31, 53–60):
```typescript
const SEVERITY_STYLES: Record<string, string> = {
  CRITICAL: "bg-[hsl(0_72%_51%)] text-white",
  HIGH: "bg-[hsl(24_95%_53%)] text-white",
  MEDIUM: "bg-[hsl(38_92%_50%)] text-black",
  LOW: "bg-[hsl(213_94%_68%)] text-black",
  INFO: "bg-[hsl(240_5%_46%)] text-white",
}
// In TableCell:
<Badge className={`${SEVERITY_STYLES[severity] ?? ""} font-semibold text-xs`}>
  {severity}
</Badge>
```

**Score delta color pattern** (`trends.tsx` lines 37–49 — adapt for compare score delta display):
```typescript
// From ScoreDeltaBadge in trends.tsx — adapt for compare header:
function ScoreDeltaBadge({ delta }: { delta: number | null }) {
  if (delta === null) return <Badge variant="outline">— First scan</Badge>
  if (delta > 0) return (
    <Badge className="bg-[hsl(var(--quantum-safe))] text-white">▲ +{delta} pts</Badge>
  )
  if (delta < 0) return (
    <Badge className="bg-[hsl(var(--destructive))] text-white">▼ {delta} pts</Badge>
  )
  return <Badge variant="outline" className="text-muted-foreground">No change</Badge>
}
```

**FIFO 2-selection state** (D-05 — local state, no analog exists; implement as):
```typescript
const [selected, setSelected] = useState<string[]>([])   // ordered by check time

function handleCheck(scanId: string, checked: boolean) {
  setSelected(prev => {
    if (!checked) return prev.filter(id => id !== scanId)
    const next = [...prev, scanId]
    return next.length > 2 ? next.slice(next.length - 2) : next  // drop oldest
  })
}
```

**Clone navigation** (RESEARCH.md Pattern 5):
```typescript
const navigate = useNavigate()
const handleClone = (session: ScanSession) => {
  const params = new URLSearchParams()
  if (session.target) params.set("target", session.target)
  if (session.profile) params.set("profile", session.profile)
  if (session.calibration) params.set("calibration", session.calibration)
  if (session.profile === null || session.profile === undefined) {
    params.set("reconstructed", "1")
  }
  navigate(`/scan/new?${params.toString()}`)
}
```

**Sticky compare bar z-index** (RESEARCH.md Pitfall 7):
```typescript
// sidebar is z-10; compare bar needs z-20 if fixed-positioned
// Main content offset: ml-12 lg:ml-60
<div className="fixed bottom-0 left-12 lg:left-60 right-0 z-20 bg-card border-t border-border p-4 flex items-center gap-3">
```

**Loading/error shell** (copy from `findings.tsx` — uses `useScanData` pattern):
```typescript
const { sessions, loading, error } = useScanList()
if (loading) return <PageSpinner ariaLabel="Loading scan history" />
if (error) return <p className="text-destructive text-sm">{error}</p>
```

---

### `src/dashboard/src/pages/compare.tsx` (component/page, request-response)

**Analogs:**
- `src/dashboard/src/pages/trends.tsx` — Card layout, Tabs import pattern
- `src/dashboard/src/pages/scan-job.tsx` lines 1–10 — `useParams` / `useSearchParams` + PageSpinner + Badge pattern

**Imports pattern** (from `trends.tsx` lines 1–17 + `scan-job.tsx` lines 1–10):
```typescript
import { useSearchParams } from "react-router-dom"
import { useCompareData } from "@/hooks/useCompareData"
import { PageSpinner } from "@/components/PageSpinner"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Separator } from "@/components/ui/separator"
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"
import type { CompareResponse } from "@/types/api"
```

**Route param reading pattern** (`scan-job.tsx` line 41 — adapted for query params):
```typescript
// scan-job.tsx uses useParams; compare.tsx uses useSearchParams (query params)
const [searchParams] = useSearchParams()
const scanA = searchParams.get("a")
const scanB = searchParams.get("b")
const { data, loading, error } = useCompareData(scanA, scanB)
```

**Tabs structure** (`trends.tsx` general pattern — adapt for 3 tabs):
```typescript
<Tabs defaultValue="findings">
  <TabsList>
    <TabsTrigger value="findings">Findings</TabsTrigger>
    <TabsTrigger value="subscores">Subscores</TabsTrigger>
    <TabsTrigger value="endpoints">Endpoints</TabsTrigger>
  </TabsList>
  <TabsContent value="findings">...</TabsContent>
  <TabsContent value="subscores">...</TabsContent>
  <TabsContent value="endpoints">...</TabsContent>
</Tabs>
```

**Stage/display name map pattern** (`scan-job.tsx` lines 12–20 — adapt for subscore pillar display names):
```typescript
// From scan-job.tsx STAGE_DISPLAY_NAMES record pattern:
const PILLAR_LABELS: Record<string, string> = {
  hygiene: "Hygiene",
  modern_tls: "Modern TLS",
  identity_trust: "Identity Trust",
  agility_signals: "Agility",
  data_at_rest: "Data at Rest",
  data_in_motion: "Data in Motion",
}
```

**Empty state pattern** (CONTEXT.md Claude's Discretion — no exact analog; use):
```typescript
// Consistent with EmptyStateCard used in findings.tsx
<p className="text-sm text-muted-foreground py-4 text-center">No added findings</p>
```

---

### `src/dashboard/src/pages/scan-new.tsx` (component/page, extend)

**Analog:** Self — `src/dashboard/src/pages/scan-new.tsx` lines 1–67 (extend existing component)

**Current state initialization pattern** (lines 14–17 — extend to read clone params):
```typescript
// Current:
const [targets, setTargets] = useState("")
const [profile, setProfile] = useState<ScanSubmitRequest["profile"]>("standard")
const [calibration, setCalibration] = useState<ScanSubmitRequest["calibration"]>("balanced")

// Phase 66 extension — add useSearchParams and lazy initializers:
import { useSearchParams } from "react-router-dom"

const [searchParams] = useSearchParams()
// Lazy initializer reads params once at mount — no useEffect needed (RESEARCH.md Open Q 2):
const [targets, setTargets] = useState(() => searchParams.get("target") ?? "")
const [profile, setProfile] = useState<ScanSubmitRequest["profile"]>(
  () => (searchParams.get("profile") as ScanSubmitRequest["profile"]) ?? "standard"
)
const [calibration, setCalibration] = useState<ScanSubmitRequest["calibration"]>(
  () => (searchParams.get("calibration") as ScanSubmitRequest["calibration"]) ?? "balanced"
)
const isReconstructed = searchParams.get("reconstructed") === "1"
```

**Amber notice** (D-04 — insert above the Targets field, only when `isReconstructed`):
```typescript
// Insert above the <Label htmlFor="targets"> block (line 79):
{isReconstructed && (
  <div className="rounded-md bg-amber-500/10 border border-amber-500/30 px-4 py-3 text-sm text-amber-600 dark:text-amber-400 mb-2">
    Targets reconstructed from scan results — review before submitting.
  </div>
)}
```

---

### `src/dashboard/src/App.tsx` (config, extend)

**Analog:** Self — `src/dashboard/src/App.tsx` lines 20–51 (existing Route registration)

**Route registration pattern** (lines 35–51 — add two entries):
```typescript
// Existing Phase 65 pattern to copy:
import { ScanNewPage } from "@/pages/scan-new"
import { ScanJobPage } from "@/pages/scan-job"
// ...
<Route path="/scan/new" element={<ScanNewPage />} />
<Route path="/scan/job/:jobId" element={<ScanJobPage />} />

// Phase 66 additions — same pattern:
import { ScanHistoryPage } from "@/pages/scan-history"
import { ComparePage } from "@/pages/compare"
// Inside <Routes>:
<Route path="/scans" element={<ScanHistoryPage />} />
<Route path="/compare" element={<ComparePage />} />
```

---

### `src/dashboard/src/components/sidebar.tsx` (component, extend)

**Analog:** Self — `src/dashboard/src/components/sidebar.tsx` lines 25–37 (NAV_ITEMS array)

**NAV_ITEMS pattern** (lines 25–37 — add one entry):
```typescript
// Existing pattern:
import { TrendingUp } from "lucide-react"
const NAV_ITEMS = [
  // ...
  { path: "/trends", label: "Trends", Icon: TrendingUp },
  { path: "/schedules", label: "Schedules", Icon: Calendar },
  // ...
]

// Phase 66 addition — add after Trends:
import { History } from "lucide-react"
// In NAV_ITEMS (after Trends entry):
{ path: "/scans", label: "Scan History", Icon: History },
```

**Sidebar nav link rendering pattern** (lines 80+ — reference for how each NAV_ITEMS entry renders; no changes needed to the render loop):
The `NAV_ITEMS` array drives a `map()` render loop already in place. Adding the `History` entry to the array is the only change needed.

---

## Shared Patterns

### Authentication
**Source:** `quirk/dashboard/api/routes/scan.py` line 34
**Apply to:** `compare_scans()` in `scan.py` (inherited automatically — do NOT add per-route)
```python
router = APIRouter(dependencies=[Depends(require_auth)])
# All routes in this module — including the new compare_scans() — get require_auth for free.
```

### Per-Session Score Computation
**Source:** `quirk/dashboard/api/routes/trends.py` lines 170–194
**Apply to:** `list_scans()` enrichment loop and `compare_scans()` score computation
```python
from quirk.intelligence.evidence import build_evidence_summary
from quirk.intelligence.scoring import compute_readiness_score
from quirk.intelligence.trends import _count_by_bucket, _fetch_session_endpoints

evidence = build_evidence_summary(eps)
score_dict = compute_readiness_score(evidence)
sub = score_dict["subscores"]    # SubScores model — access fields directly (.hygiene etc.)
score = int(score_dict["score"])
```

### Hook Cancellation (MANDATORY — Phase 62)
**Source:** `src/dashboard/src/hooks/useScanList.ts` lines 16–51
**Apply to:** `useCompareData.ts` (new hook) — any future hooks in this phase
```typescript
useEffect(() => {
  let cancelled = false
  async function fetchData() {
    try {
      // ...
      if (!cancelled) setData(result)
    } catch (err) {
      if (!cancelled) setError(...)
    } finally {
      if (!cancelled) setLoading(false)
    }
  }
  fetchData()
  return () => { cancelled = true }
}, [deps])
```
**Rule:** Every `setState` call after an `await` must be guarded. Applies to ALL branches (success, 401, 403, 429, 400, catch). Never use `AbortController`.

### HTTP Error Handling
**Source:** `quirk/dashboard/api/routes/scan.py` (FastAPI HTTPException pattern)
**Apply to:** `compare_scans()` route
```python
# Raise HTTPException directly — no try/except wrapper needed for expected errors
raise HTTPException(status_code=400, detail="Cannot compare a scan to itself.")
raise HTTPException(status_code=404, detail=f"No scan found: {a!r}")
raise HTTPException(status_code=400, detail="Invalid scan_id format.")
```

### Severity Badge Styling
**Source:** `src/dashboard/src/pages/findings.tsx` lines 25–31, `src/dashboard/src/pages/trends.tsx` lines 29–35
**Apply to:** `scan-history.tsx` (finding counts badges), `compare.tsx` (CompareFinding severity badges)
```typescript
const SEVERITY_STYLES: Record<string, string> = {
  CRITICAL: "bg-[hsl(0_72%_51%)] text-white",
  HIGH: "bg-[hsl(24_95%_53%)] text-white",
  MEDIUM: "bg-[hsl(38_92%_50%)] text-black",
  LOW: "bg-[hsl(213_94%_68%)] text-black",
  INFO: "bg-[hsl(240_5%_46%)] text-white",
}
```

### PageSpinner Loading State
**Source:** `src/dashboard/src/pages/scan-job.tsx` line 55
**Apply to:** `scan-history.tsx`, `compare.tsx`
```typescript
import { PageSpinner } from "@/components/PageSpinner"
if (loading) return <PageSpinner ariaLabel="Loading scan history" />
```

### Test Fixture Pattern (seeded DB)
**Source:** `tests/test_dashboard_trends.py` lines 63–95 (`_make_uat31_client_and_session()`)
**Apply to:** `tests/test_dashboard_scan_history.py` — all test cases
```python
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

def _make_client_and_session():
    from quirk.dashboard.api.app import create_app
    from quirk.dashboard.api.deps import get_db
    from quirk.models import Base

    db_name = f"test_scan_history_{uuid.uuid4().hex}"
    engine = create_engine(
        f"sqlite:///file:{db_name}?mode=memory&cache=shared&uri=true",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def _override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[get_db] = _override_get_db
    return TestClient(app), TestingSession
```

---

## No Analog Found

All files have close analogs in the codebase. No entries.

---

## Key Anti-Patterns (Enforced)

| Anti-Pattern | Source | How to Avoid |
|---|---|---|
| `LIMIT 10` remaining in `list_scans()` | RESEARCH.md D-01 | Delete `.limit(10)` from the SQLAlchemy query |
| Using `_fetch_session_endpoints()` with second-precision ts | RESEARCH.md Pitfall 1 | Use private `_fetch_session_endpoints_1s()` with 1-second window |
| Duplicate `FindingCounts` definition | RESEARCH.md Pitfall 3 | Check `schemas.py` lines 241–249 — it already exists |
| Adding `require_auth` per-route on `compare_scans()` | RESEARCH.md Pitfall 4 | Router-level declaration at line 34 covers all routes |
| `AbortController` in hooks | Phase 62 D-01 | `let cancelled = false` flag pattern only |
| `setState` without `if (!cancelled)` guard in error branches | Phase 62 bug pattern | Guard ALL branches including 400, 401, 403, 429, catch |
| Comparing findings by `CryptoEndpoint.id` | RESEARCH.md Pattern 3 | Use `(host, protocol, severity)` composite key |
| Skipping `npm run build` after `.tsx` edits | MEMORY.md feedback | Every frontend wave must end with `npm run build` in `src/dashboard/` |

---

## Metadata

**Analog search scope:** `quirk/dashboard/api/routes/`, `quirk/dashboard/api/schemas.py`, `quirk/models.py`, `quirk/intelligence/`, `src/dashboard/src/hooks/`, `src/dashboard/src/pages/`, `src/dashboard/src/components/`, `src/dashboard/src/types/`, `tests/`
**Files scanned:** 14
**Pattern extraction date:** 2026-05-14
