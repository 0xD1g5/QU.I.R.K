# Phase 111: Console Dashboard Awareness — Pattern Map

**Mapped:** 2026-05-25
**Files analyzed:** 13 new/modified files
**Analogs found:** 13 / 13

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `quirk/dashboard/api/routes/merge.py` | route | request-response | `quirk/dashboard/api/routes/scan.py` (`get_latest_scan`) | role-match |
| `quirk/dashboard/api/routes/sensor.py` | route (MODIFIED) | request-response | self — existing router in same file | exact |
| `quirk/dashboard/api/routes/scan.py` | route (MODIFIED) | request-response | self — `get_latest_scan` pattern | exact |
| `quirk/dashboard/api/schemas.py` | model (MODIFIED) | — | self — `FindingItem`, `CbomComponent` | exact |
| `quirk/dashboard/api/app.py` | config (MODIFIED) | — | self — `include_router(sensor.router, ...)` | exact |
| `src/dashboard/src/pages/sensors.tsx` | component | request-response | `src/dashboard/src/pages/data-at-rest.tsx` | exact |
| `src/dashboard/src/components/sidebar.tsx` | component (MODIFIED) | — | self — `NAV_ITEMS` array | exact |
| `src/dashboard/src/pages/executive.tsx` | component (MODIFIED) | request-response | self — gauge layout + `RegressionAlertChip` placement | exact |
| `src/dashboard/src/pages/findings.tsx` | component (MODIFIED) | request-response | self — `severityFilter`/`protocolFilter` Select pattern | exact |
| `src/dashboard/src/pages/cbom.tsx` | component (MODIFIED) | request-response | self — `qsFilter` Select pattern | exact |
| `src/dashboard/src/lib/api.ts` | utility (MODIFIED) | request-response | self — `fetchApi` | exact |
| `src/dashboard/src/types/api.ts` | model (MODIFIED) | — | self — `FindingItem`, `CbomComponent` interfaces | exact |
| `tests/test_dashboard_*.py` + `sensors-loading.test.tsx` | test | — | `tests/test_dashboard_api.py` / `findings-columns-memo.test.tsx` | role-match |

---

## Pattern Assignments

### `quirk/dashboard/api/routes/merge.py` (NEW — route, request-response)

**Analog:** `quirk/dashboard/api/routes/scan.py`

**Imports pattern** (mirror `scan.py` lines 1-48; merge.py variant):
```python
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from quirk.dashboard.api.deps import get_db
from quirk.dashboard.api.middleware.auth import require_auth
from quirk.models import MergeRun
from quirk.merge.scan import _assemble_union
from quirk.intelligence.evidence import build_evidence_summary
from quirk.intelligence.scoring import compute_readiness_score
```

**Router declaration pattern** (mirror `sensor.py` line 48):
```python
router = APIRouter(dependencies=[Depends(require_auth)])
```

**Core route pattern** — read-only GET, no db.commit(), graceful null state:
```python
@router.get("/merge/latest")
def get_merge_latest(db: Session = Depends(get_db)) -> dict:
    row = db.query(MergeRun).order_by(MergeRun.merged_at.desc()).first()
    if row is None:
        return {"merge": None}

    coverage_warning = None
    if row.coverage_warning_json:
        try:
            coverage_warning = json.loads(row.coverage_warning_json)
        except (ValueError, TypeError):
            pass  # Pitfall 4: malformed JSON must not crash the endpoint

    # Option (a): per-segment recompute on read (confirmed in RESEARCH.md)
    union = _assemble_union(db)
    per_segment: Dict[str, int] = {}
    if union:
        from collections import defaultdict
        seg_map: Dict[str, List] = defaultdict(list)
        for ep in union:
            if ep.segment is not None:
                seg_map[ep.segment].append(ep)
        for seg, eps in seg_map.items():
            evidence = build_evidence_summary(eps, findings=None)
            result = compute_readiness_score(evidence)
            per_segment[seg] = int(result["score"]) if result.get("score") is not None else 0

    return {
        "merge": {
            "scan_id": row.scan_id,
            "merged_at": row.merged_at.isoformat() if row.merged_at else None,
            "score": row.score,
            "endpoint_count": row.endpoint_count,
            "sensor_count": row.sensor_count,
            "coverage_warning": coverage_warning,
            "per_segment_scores": per_segment,
        }
    }
```

**CRITICAL — no write calls in GET handlers.** Do not copy `db.add()`, `db.flush()`, or `db.commit()` from `merge_scan()` (lines 196-237 of `merge/scan.py`). Those only belong in `merge_scan`, not in the read endpoint.

---

### `quirk/dashboard/api/routes/sensor.py` (MODIFIED — add GET /api/sensor/registry)

**Analog:** self — existing file; `_sensor_status` helper replicates the per-sensor subset of `quirk/merge/scan.py:_build_coverage_warning` (lines 34-84).

**Import additions** needed at top of file (alongside existing imports):
```python
from datetime import datetime, timedelta, timezone  # already present; ensure timezone imported
# Already imported: Sensor from quirk.models
```

**Per-sensor status helper** (do NOT call `_build_coverage_warning` directly — it returns one dict for a list, not per-sensor):
```python
_STALE_DAYS = 30

def _sensor_status(s: Sensor, now: datetime) -> str:
    """Compute per-sensor status badge: 'current' | 'stale' | 'unknown'."""
    if s.last_push_at is None:
        if s.enrolled_at is not None and (now - s.enrolled_at) > timedelta(days=_STALE_DAYS):
            return "unknown"  # decommissioned — enrolled long ago, never pushed
        return "unknown"  # never pushed
    silent = now - s.last_push_at
    if silent > timedelta(days=_STALE_DAYS):
        return "unknown"  # decommissioned
    cadence_minutes = s.expected_cadence_minutes or 1440
    cadence = timedelta(minutes=cadence_minutes)
    if now > s.last_push_at + 2 * cadence:
        return "stale"
    return "current"
```

**New route handler** (same router, same `Depends(require_auth)` already on router):
```python
@router.get("/sensor/registry")
def get_sensor_registry(db: Session = Depends(get_db)) -> dict:
    from quirk.dashboard.api.schemas import SensorRegistryItem, SensorRegistryResponse
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    sensors = db.query(Sensor).order_by(Sensor.enrolled_at.desc()).all()
    items = [
        SensorRegistryItem(
            sensor_id=s.sensor_id,
            segment=s.segment,
            sensor_version=s.sensor_version,
            last_push_at=s.last_push_at,
            status=_sensor_status(s, now),
        )
        for s in sensors
    ]
    return SensorRegistryResponse(sensors=items).model_dump()
```

---

### `quirk/dashboard/api/routes/scan.py` (MODIFIED — add `?segment=` param)

**Analog:** self — `get_latest_scan` at line 958.

**Existing signature** (lines 958-962):
```python
@router.get("/scan/latest", response_model=ScanLatestResponse)
def get_latest_scan(
    scan_id: Optional[str] = Query(default=None, description="ISO timestamp scan_id to load; omit for latest"),
    db: Session = Depends(get_db),
) -> ScanLatestResponse:
```

**Modified signature** — add `segment` param after `scan_id`:
```python
@router.get("/scan/latest", response_model=ScanLatestResponse)
def get_latest_scan(
    scan_id: Optional[str] = Query(default=None, description="ISO timestamp scan_id to load; omit for latest"),
    segment: Optional[str] = Query(default=None, description="Filter by segment label; omit for all"),
    db: Session = Depends(get_db),
) -> ScanLatestResponse:
```

**Filter insertion** — add AFTER the endpoints list is populated (after the `if not endpoints:` check at line 1010), BEFORE `findings = _derive_findings(endpoints)` at line 1013:
```python
# DASH-02: post-load segment filter — NULL-segment scans unaffected when param omitted
if segment is not None:
    endpoints = [ep for ep in endpoints if ep.segment == segment]
# Continue: findings = _derive_findings(endpoints) unchanged
```

**CRITICAL Pitfall 2:** the guard `if segment is not None:` MUST be present. Without it, omitting the param would filter all rows (since `None == None` is truthy). Apply identical pattern to any `/api/findings` or `/api/cbom` separate endpoints if they exist — check whether those routes use `get_latest_scan` as their data source or have separate handlers.

**`_derive_findings` and `_derive_cbom` changes** — within the `FindingItem(...)` constructor calls in `_derive_findings` (starting line 95) and `CbomComponent(...)` calls in `_derive_cbom` (starting line 692), add `sensor_id=ep.sensor_id, segment=ep.segment` keyword args once the Pydantic models have those optional fields.

---

### `quirk/dashboard/api/schemas.py` (MODIFIED)

**Analog:** self — `FindingItem` (lines 49-66), `CbomComponent` (lines 83-89).

**`FindingItem` additions** (after existing `compliance` field, line 66):
```python
class FindingItem(BaseModel):
    # ... existing fields ...
    sensor_id: Optional[str] = None   # DASH-02: nullable, backward-compatible
    segment: Optional[str] = None     # DASH-02: nullable, backward-compatible
```

**`CbomComponent` additions** (after `source_systems`, line 89):
```python
class CbomComponent(BaseModel):
    # ... existing fields ...
    sensor_id: Optional[str] = None   # DASH-02: nullable, backward-compatible
    segment: Optional[str] = None     # DASH-02: nullable, backward-compatible
```

**New models to add** (append after existing models; `Optional` and `List` already imported at line 9):
```python
class SensorRegistryItem(BaseModel):
    sensor_id: str
    segment: str
    sensor_version: Optional[str] = None
    last_push_at: Optional[datetime] = None
    status: str  # "current" | "stale" | "unknown"

class SensorRegistryResponse(BaseModel):
    sensors: List[SensorRegistryItem]

class MergeLatestData(BaseModel):
    scan_id: Optional[str] = None
    merged_at: Optional[datetime] = None
    score: Optional[int] = None
    endpoint_count: int = 0
    sensor_count: int = 0
    coverage_warning: Optional[Dict[str, Any]] = None
    per_segment_scores: Dict[str, int] = {}

class MergeLatestResponse(BaseModel):
    merge: Optional[MergeLatestData] = None
```

**CRITICAL Pitfall 8:** When these Pydantic models change, `src/dashboard/src/types/api.ts` MUST be updated in the same plan step. The `schemas.py` docstring (line 4) states this explicitly: "TypeScript types in `src/dashboard/src/types/api.ts` must mirror these exactly."

---

### `quirk/dashboard/api/app.py` (MODIFIED — mount merge.router)

**Analog:** self — lines 25 and 116 for the existing sensor router registration.

**Import line** (line 25 — extend the existing import):
```python
# Before:
from quirk.dashboard.api.routes import health, jobs, pdf, qramm, scan, schedules, sensor, trends
# After:
from quirk.dashboard.api.routes import health, jobs, merge, pdf, qramm, scan, schedules, sensor, trends
```

**Router registration** (after `application.include_router(sensor.router, prefix="/api")` at line 116):
```python
application.include_router(merge.router, prefix="/api")
```

---

### `src/dashboard/src/pages/sensors.tsx` (NEW — component, request-response)

**Analog:** `src/dashboard/src/pages/data-at-rest.tsx`

**Imports pattern** (mirrors `data-at-rest.tsx` lines 1-11):
```tsx
import { useMemo } from "react"
import { useSensorRegistry } from "@/hooks/useSensorRegistry"
import type { SensorRegistryItem } from "@/types/api"
import { Card, CardContent } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { EmptyStateCard } from "@/components/EmptyStateCard"
import { Badge } from "@/components/ui/badge"
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"
```

**Page structure** (mirrors `data-at-rest.tsx` Card + Table layout):
```tsx
export function SensorsPage() {
  const { sensors, loading, error } = useSensorRegistry()

  if (loading) return (
    <div role="status" aria-label="Loading sensors" className="space-y-6">
      <span className="sr-only">Loading...</span>
      <Skeleton className="h-7 w-28" />
      {Array.from({ length: 5 }).map((_, r) => (
        <Skeleton key={r} className="h-10 w-full" />
      ))}
    </div>
  )
  if (error) return <p className="text-muted-foreground text-sm">{error}</p>
  if (!sensors.length) return (
    <EmptyStateCard message="No sensors enrolled. Run: quirk sensor enroll --console <url> to register a sensor." />
  )

  return (
    <div className="space-y-6">
      <h1 style={{ fontSize: 20, fontWeight: 600 }}>Sensors</h1>
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead scope="col" className="text-xs font-semibold">Sensor ID</TableHead>
                <TableHead scope="col" className="text-xs font-semibold">Segment</TableHead>
                <TableHead scope="col" className="text-xs font-semibold">Version</TableHead>
                <TableHead scope="col" className="text-xs font-semibold">Last Seen</TableHead>
                <TableHead scope="col" className="text-xs font-semibold">Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {sensors.map((s) => (
                <TableRow key={s.sensor_id} className="hover:bg-accent/5">
                  <TableCell><span className="font-mono text-xs">{s.sensor_id}</span></TableCell>
                  <TableCell className="text-sm">{s.segment}</TableCell>
                  <TableCell className="text-sm">{s.sensor_version ?? "—"}</TableCell>
                  <TableCell className="text-sm">{s.last_push_at ? relativeTime(s.last_push_at) : "Never"}</TableCell>
                  <TableCell><SensorStatusBadge status={s.status} /></TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}
```

**`SensorStatusBadge` helper** (badge classes from UI-SPEC color section):
```tsx
function SensorStatusBadge({ status }: { status: string }) {
  if (status === "current") {
    return <Badge className="bg-[hsl(var(--quantum-safe))] text-white text-xs" aria-label="status: Current">Current</Badge>
  }
  if (status === "stale") {
    return <Badge className="bg-[#d4893a]/10 text-[#d4893a] border border-[#d4893a]/28 text-xs" aria-label="status: Stale">Stale</Badge>
  }
  return <Badge variant="secondary" className="text-xs" aria-label="status: Unknown">Unknown</Badge>
}
```

**`TableHead scope="col"` and `hover:bg-accent/5`** are the exact `data-at-rest.tsx` table patterns — copy them verbatim.

---

### `src/dashboard/src/components/sidebar.tsx` (MODIFIED — add Radio + Sensors NAV_ITEM)

**Analog:** self — `NAV_ITEMS` array (lines 29-42) and lucide-react import (lines 4-20).

**Lucide import block** (lines 4-20) — add `Radio` to the named imports:
```tsx
import {
  LayoutDashboard,
  AlertTriangle,
  Shield,
  Database,
  GitBranch,
  Fingerprint,
  TrendingUp,
  Activity,
  HardDrive,
  ClipboardList,
  Calendar,
  Scan,
  History,
  LogOut,
  Radio,            // ADD — Sensors nav icon (Pitfall 6: must be here or runtime error)
} from "lucide-react"
```

**NAV_ITEMS insertion** (after `{ path: "/scans", label: "Scan History", Icon: History }` at line 39, before `{ path: "/schedules", ... }` at line 40):
```tsx
const NAV_ITEMS = [
  // ... existing items ...
  { path: "/scans", label: "Scan History", Icon: History },
  { path: "/sensors", label: "Sensors", Icon: Radio },    // ADD HERE
  { path: "/schedules", label: "Schedules", Icon: Calendar },
  // ...
]
```

**Nav link pattern** (lines 96-117) — the existing `map` already renders `min-h-[44px]`, `aria-label={label}`, and active state; no changes to the render function needed.

---

### `src/dashboard/src/pages/executive.tsx` (MODIFIED — per-segment gauges + coverage banner)

**Analog:** self — gauge layout lines 229-259, `RegressionAlertChip` at line 227.

**Import additions** — add `AlertTriangle` to the lucide-react import at line 9 (Pitfall 7 — currently NOT in executive.tsx):
```tsx
import { Download, Loader2, AlertTriangle } from "lucide-react"
```

**Coverage warning banner** — insert before `<RegressionAlertChip />` at line 227 (i.e., inside the `<div className="space-y-8">` block):
```tsx
{/* DASH-03: coverage warning — above RegressionAlertChip and score gauges */}
{merge?.coverage_warning && (
  <div
    className="flex items-start gap-3 rounded-md border px-4 py-3 mb-6"
    style={{ background: "var(--ds-high-dim)", borderColor: "var(--ds-high-bdr)" }}
    role="alert"
    aria-live="polite"
  >
    <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" style={{ color: "#d4893a" }} aria-hidden="true" />
    <div className="flex flex-col gap-1">
      <span className="text-sm font-semibold">Incomplete sensor coverage</span>
      <span className="text-sm text-muted-foreground">
        {merge.coverage_warning.missing_sensors.length} sensor
        {merge.coverage_warning.missing_sensors.length !== 1 ? "s" : ""} did not
        contribute to this merge. Scores may understate risk in uncovered segments.
        {merge.coverage_warning.missing_sensors.length > 0 && (
          <> Missing: <span className="font-mono text-xs">{merge.coverage_warning.missing_sensors.join(", ")}</span>.</>
        )}
      </span>
    </div>
  </div>
)}
<RegressionAlertChip />
```

**Per-segment gauges** — insert after the existing subscore gauges (after line 256), still inside the `<div className="flex flex-wrap justify-around gap-8">` at line 232:
```tsx
{/* DASH-03: per-segment gauges — only when merge data present */}
{merge?.per_segment_scores && Object.entries(merge.per_segment_scores).map(([seg, segScore]) => (
  <ScoreGauge
    key={seg}
    score={segScore}
    label={seg.length > 16 ? seg.slice(0, 15) + '…' : seg}
    size={120}
    maxValue={100}
  />
))}
```

`maxValue={100}` because per-segment scores are re-computed through the full engine (0-100 scale), unlike the subscore gauges which use `maxValue={25}`.

**Recharts mounting rule:** the existing `<Bar>` and `<Cell>` in the severity chart (below line 259) are statically mounted — do not make them conditional. Per-segment gauges are SVG-based (`ScoreGauge`), not Recharts, so this rule does not apply to them directly.

**Hook addition** — `useMergeLatest` must be called at the top of `ExecutivePage`:
```tsx
import { useMergeLatest } from "@/hooks/useMergeLatest"
// Inside ExecutivePage():
const { merge } = useMergeLatest()
```

---

### `src/dashboard/src/pages/findings.tsx` (MODIFIED — add segment Select filter)

**Analog:** self — `severityFilter`/`protocolFilter` pattern (lines 36-51, 113-135).

**State addition** (after `protocolFilter` state, line 38):
```tsx
const [segmentFilter, setSegmentFilter] = useState("all")
```

**distinctSegments derivation** (after the `findings` useMemo, line 41-51):
```tsx
const distinctSegments = useMemo(() => {
  if (!data?.findings) return []
  const segs = new Set(data.findings.map(f => f.segment).filter(Boolean) as string[])
  return Array.from(segs).sort()
}, [data])
```

**Filter predicate addition** (inside the existing `findings` useMemo, after `protocolFilter` check):
```tsx
if (segmentFilter !== "all") filtered = filtered.filter(f => f.segment === segmentFilter)
```

**Segment Select** (in the filter bar, lines 113-135, after the `protocolFilter` Select):
```tsx
<Select value={segmentFilter} onValueChange={setSegmentFilter}>
  <SelectTrigger className="w-40 h-8 text-sm" aria-label="Filter by segment">
    <SelectValue placeholder="All segments" />
  </SelectTrigger>
  <SelectContent>
    <SelectItem value="all">All segments</SelectItem>
    {distinctSegments.map((seg) => (
      <SelectItem key={seg} value={seg}>{seg}</SelectItem>
    ))}
  </SelectContent>
</Select>
```

Note: existing `SelectTrigger` in findings.tsx uses `className="w-40"` without `h-8 text-sm`. The segment filter uses `className="w-40 h-8 text-sm"` per UI-SPEC to match the cbom.tsx pattern.

---

### `src/dashboard/src/pages/cbom.tsx` (MODIFIED — add segment Select filter)

**Analog:** self — `qsFilter` pattern (lines 47-84).

Same pattern as findings.tsx. The `distinctSegments` source is `data.cbom_components` instead of `data.findings`, and the field is `c.segment`.

Existing filter bar (line 73-83) uses `<SelectTrigger className="w-40 h-8 text-sm">` — the segment Select uses the same class.

---

### `src/dashboard/src/lib/api.ts` (MODIFIED — no new fetchApi changes needed)

**Analog:** self. No changes to `fetchApi` itself are required for Phase 111. New hooks call `fetchApi("/api/sensor/registry")` and `fetchApi("/api/merge/latest")` directly, following the existing pattern.

The `fetchApi` function already injects `X-Quirk-Request: 1` (CSRF) and `X-API-Key` (auth token) on every call (lines 68-80). New hooks MUST use `fetchApi`, not `fetch()` directly (HARDEN-API-01 rule, line 11).

---

### `src/dashboard/src/types/api.ts` (MODIFIED)

**Analog:** self — `FindingItem` (lines 23-34), `CbomComponent` (lines 47-53).

**`FindingItem` additions** (after `source?: string` at line 34):
```typescript
export interface FindingItem {
  // ... existing fields ...
  sensor_id?: string   // DASH-02: mirrors FindingItem.sensor_id in schemas.py
  segment?: string     // DASH-02: mirrors FindingItem.segment in schemas.py
}
```

**`CbomComponent` additions** (after `source_systems: string[]` at line 53):
```typescript
export interface CbomComponent {
  // ... existing fields ...
  sensor_id?: string   // DASH-02
  segment?: string     // DASH-02
}
```

**New types to add** (append at end of file):
```typescript
export interface SensorRegistryItem {
  sensor_id: string
  segment: string
  sensor_version: string | null
  last_push_at: string | null
  status: "current" | "stale" | "unknown"
}

export interface SensorRegistryResponse {
  sensors: SensorRegistryItem[]
}

export interface MergeLatestData {
  scan_id: string | null
  merged_at: string | null
  score: number | null
  endpoint_count: number
  sensor_count: number
  coverage_warning: {
    missing_sensors: string[]
    reason: string
  } | null
  per_segment_scores: Record<string, number>
}

export interface MergeLatestResponse {
  merge: MergeLatestData | null
}
```

**CRITICAL:** These TypeScript types must be updated in the same commit/step as the Pydantic schema changes. If `FindingItem.segment` exists in Python but not in TypeScript, `finding.segment` in the frontend will be `undefined` even when the API sends it (Pitfall 8).

---

### New hooks: `useSensorRegistry.ts` and `useMergeLatest.ts`

**Analog:** `src/dashboard/src/hooks/useScanData.ts` (full file)

The cancellation pattern from `useScanData.ts` lines 18-81 is the template:
```typescript
// Core shape (copy from useScanData.ts):
useEffect(() => {
  let cancelled = false
  setData(null)    // clear stale data synchronously before fetch
  setLoading(true)
  setError(null)

  async function fetchData() {
    try {
      const resp = await fetchApi("/api/sensor/registry")  // or /api/merge/latest
      if (!resp.ok) {
        if (!cancelled) setError(`Failed to fetch sensors: ${resp.status}`)
        return
      }
      const json = await resp.json()
      if (!cancelled) setSensors(json.sensors ?? [])
    } catch (err) {
      if (!cancelled) setError(err instanceof Error ? err.message : String(err))
    } finally {
      if (!cancelled) setLoading(false)
    }
  }

  fetchData()
  return () => { cancelled = true }   // cleanup: cancel on unmount/re-render
}, [])  // no dependencies: fetch once on mount
```

Key difference from `useScanData`: no `selectedScanId` dependency — registry and merge endpoints are stateless (no scan selector).

---

### `App.tsx` (MODIFIED — add Sensors route)

**Analog:** self — `DataAtRestPage` import and route (lines 14 and 62).

**Import addition** (after `ScanHistoryPage` import, line 24):
```tsx
import { SensorsPage } from "@/pages/sensors"
```

**Route addition** (after `/scans` route, line 73):
```tsx
<Route path="/sensors" element={<SensorsPage />} />
```

---

### Tests

**Analog:** `tests/test_dashboard_api.py` (TestClient pattern) and `src/dashboard/__tests__/findings-columns-memo.test.tsx` (vitest pattern).

**Backend test shape** (copy from `test_dashboard_api.py` TestClient setup):
```python
from fastapi.testclient import TestClient
from quirk.dashboard.api.app import create_app

def test_sensor_registry_returns_list(tmp_path):
    app = create_app(db_path=str(tmp_path / "test.db"))
    client = TestClient(app)
    # seed sensor rows, then:
    resp = client.get("/api/sensor/registry", headers={"X-Quirk-Request": "1"})
    assert resp.status_code == 200
    data = resp.json()
    assert "sensors" in data
    assert isinstance(data["sensors"], list)
```

**Frontend vitest shape** (mirrors existing test structure):
```typescript
import { render, screen } from "@testing-library/react"
import { describe, it, expect, vi } from "vitest"
// mock useSensorRegistry, then:
it("shows loading skeleton", () => { ... })
it("shows empty state when no sensors", () => { ... })
it("renders sensor rows with status badges", () => { ... })
```

---

## Shared Patterns

### Auth — Router-Level Dependency
**Source:** `quirk/dashboard/api/routes/sensor.py` line 48; `quirk/dashboard/api/routes/scan.py` lines 12-14.
**Apply to:** `merge.py` (new router) and the new `/api/sensor/registry` handler in `sensor.py`.
```python
router = APIRouter(dependencies=[Depends(require_auth)])
```
Never bypass with a per-handler `dependencies=[]` override — the router-level declaration is the security contract.

### fetchApi Wrapper
**Source:** `src/dashboard/src/lib/api.ts` lines 54-90.
**Apply to:** `useSensorRegistry.ts`, `useMergeLatest.ts`, and any other new React data-fetching code.
```typescript
const resp = await fetchApi("/api/<path>")
```
Never call `fetch()` directly (HARDEN-API-01).

### useScanData Cancellation Pattern
**Source:** `src/dashboard/src/hooks/useScanData.ts` lines 18-81.
**Apply to:** `useSensorRegistry.ts`, `useMergeLatest.ts`.
Key elements: `let cancelled = false`, clear state synchronously before fetch, `if (!cancelled)` guard before every setState, `return () => { cancelled = true }` cleanup.

### ScoreGauge Component
**Source:** `src/dashboard/src/components/gauges/ScoreGauge.tsx` lines 1-87.
**Apply to:** per-segment gauges in `executive.tsx`.
```tsx
<ScoreGauge score={segScore} label={label} size={120} maxValue={100} />
```
Use `maxValue={100}` for per-segment gauges (full re-scored 0-100 result), NOT `maxValue={25}` (that is for individual subscores). `isOverall` remains reserved for the org-wide gauge.

### Amber Partial Badge
**Source:** `src/dashboard/src/pages/executive.tsx` lines 52-57 (`ScannerStatusCard` component).
**Apply to:** `SensorStatusBadge` `stale` state in `sensors.tsx`.
```tsx
<Badge className="bg-[#d4893a]/10 text-[#d4893a] border border-[#d4893a]/28" ...>
```

### Table Structure
**Source:** `src/dashboard/src/pages/data-at-rest.tsx` lines 64-80.
**Apply to:** `sensors.tsx` registry table.
```tsx
<TableHead scope="col" className="text-xs font-semibold">
<TableRow className="hover:bg-accent/5">
```

### pydantic Optional + nullable pattern
**Source:** `quirk/dashboard/api/schemas.py` lines 49-66 (`FindingItem`).
**Apply to:** All new nullable fields added to existing models, and all new model classes.
```python
field_name: Optional[str] = None  # always with default=None for backward compat
```

---

## Critical Traps (Planner Must Address Explicitly)

| # | Trap | Affected File | Mitigation |
|---|---|---|---|
| T1 | `Radio` icon not in lucide-react import | `sidebar.tsx` | Add `Radio` to the named import block — failure causes runtime "Radio is not defined" |
| T2 | `AlertTriangle` not in `executive.tsx` | `executive.tsx` | Add to lucide-react import; it IS in `RegressionAlertChip.tsx` but that does not help `executive.tsx` |
| T3 | `types/api.ts` not updated to mirror new Pydantic fields | `types/api.ts` | Must update `FindingItem` + `CbomComponent` + add new interfaces in same step as `schemas.py` |
| T4 | Missing `if segment is not None:` guard | `scan.py` | Without the guard, omitting `?segment=` filters ALL rows (including NULL-segment local scans) |
| T5 | Per-segment grouped by `sensor_id` instead of `segment` | `merge.py` | Group by `ep.segment`, not `ep.sensor_id` — one segment can have multiple sensors |
| T6 | `db.commit()` in read endpoint | `merge.py` | GET handlers are read-only; never copy commit/flush from `merge_scan()` |
| T7 | `_build_coverage_warning` called for per-sensor badge | `sensor.py` | Use inlined `_sensor_status()` helper — the full function returns one aggregate dict, not per-sensor values |
| T8 | `coverage_warning_json` parse without try/except | `merge.py` | Wrap in `try/except (ValueError, TypeError)` and fall back to `None` |

---

## No Analog Found

All files have analogs. No entries in this section.

---

## Metadata

**Analog search scope:** `quirk/dashboard/api/routes/`, `quirk/dashboard/api/`, `quirk/merge/`, `quirk/models.py`, `src/dashboard/src/pages/`, `src/dashboard/src/hooks/`, `src/dashboard/src/components/`, `src/dashboard/src/types/`, `src/dashboard/src/lib/`
**Files scanned:** 16 source files read directly
**Pattern extraction date:** 2026-05-25
