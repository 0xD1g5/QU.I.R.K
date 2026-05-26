# Phase 111: Console Dashboard Awareness — Research

**Researched:** 2026-05-25
**Domain:** FastAPI backend (sensor registry endpoint, merge/latest endpoint, segment filter) + React/shadcn dashboard (Sensors page, segment dropdown, per-segment gauges, coverage banner)
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Sensor Registry (DASH-01):** New top-level "Sensors" page/route. Backend: `GET /api/sensor/registry`. Status badge: green = within cadence, stale = overdue (now > last_push_at + 2×cadence), unknown = never pushed. Reuse Phase 110 `_build_coverage_warning` / overdue computation from `quirk/merge/scan.py`.
- **Segment Filter (DASH-02):** Optional `?segment=<label>` on `/api/scan/latest`, `/api/findings`, and `/api/cbom`. Nullable `sensor_id`/`segment` Pydantic fields. Frontend: shared segment dropdown on Findings and CBOM views. Default = "All segments". NULL-segment scans are unaffected.
- **Merged-View Data Source (DASH-03):** New `GET /api/merge/latest` reading the latest `merge_runs` row. Coverage warning banner when `coverage_warning_json` is non-null. Graceful no-merge state.
- **Per-Segment Gauges (DASH-03):** Reuse existing `ScoreGauge` with correct `maxValue`. Recharts children must remain statically mounted (toggle via fill/stroke opacity).
- **Build & Verify:** `.tsx` edits require `npm run build` in `src/dashboard/`. Render-parity tests assert presence/content-model, not visual; gate visual fidelity on UI-SPEC + human UAT.

### Claude's Discretion
- Exact `/api/sensor/registry` and `/api/merge/latest` response-model field names.
- The segment dropdown's empty/all representation; nav placement order of the Sensors page.

### Deferred Ideas (OUT OF SCOPE)
- Chaos-lab E2E validation of the dashboard awareness flow (Phase 112).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DASH-01 | Sensor registry on console dashboard — sensor ID, segment, version, last-seen, status badge | `GET /api/sensor/registry` reads `sensors` table; status computed via `_build_coverage_warning` logic; Sensors page mirrors `data-at-rest.tsx` structure |
| DASH-02 | Findings and CBOM views expose `sensor_id`/`segment` dimension with per-segment filter | Optional `?segment=` param on existing routes; nullable fields on `FindingItem`/`CbomComponent`; client-side filter dropdown in `FindingsPage` and `CbomPage` |
| DASH-03 | Per-segment score gauges + coverage_warning banner | `GET /api/merge/latest` re-assembles union per segment via `_assemble_union` + `compute_readiness_score`; `ScoreGauge` reused; banner in `executive.tsx` above gauges card |
</phase_requirements>

---

## Summary

Phase 111 is a pure read layer on top of the distributed infrastructure built in Phases 107–110. The backend adds three new endpoints (`GET /api/sensor/registry`, `GET /api/merge/latest`, and a `?segment=` query param on existing scan routes) and the React dashboard adds one new page (Sensors), two dropdown filters (Findings, CBOM), per-segment gauges on the Executive page, and a coverage warning banner. No schema migrations are required — all the tables and columns this phase reads already exist.

The most architecturally significant decision is how to produce per-segment scores for DASH-03. The `merge_runs` table stores only an org-wide `score` integer and no per-segment breakdown. Option (a) — recompute on read by calling `_assemble_union(db)` to get the union, grouping by segment, then calling `build_evidence_summary` + `compute_readiness_score` per segment — is **confirmed feasible and recommended**. The cost is proportional to total endpoint count in the database, which on single-tenant on-prem deployments is negligible (a few hundred to a few thousand rows at most). Option (b) — adding a `per_segment_scores_json` column to `merge_runs` and populating it in `merge_scan` — would require reopening Phase 110 and writing a schema migration; the trade-off is not justified for the expected volume.

The frontend patterns are stable and well-established. New pages follow the `data-at-rest.tsx` template exactly; new data hooks follow the `useScanData` cancellation pattern; new API calls go through the existing `fetchApi` wrapper which already injects auth and CSRF headers. No new npm packages are required — all needed shadcn primitives (`badge`, `card`, `table`, `select`, `skeleton`) are already installed.

**Primary recommendation:** Implement Option (a) per-segment recompute in `GET /api/merge/latest`. Add the three backend endpoints in `sensor.py` and a new `merge.py` route file, wire them in `app.py`, add nullable fields to schemas, add the segment filter param to existing routes, then build the frontend components following the UI-SPEC exactly.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Sensor registry data | API / Backend | — | Reads `sensors` SQLite table; status computed server-side to keep business logic out of the browser |
| Merge / per-segment scores | API / Backend | — | Requires DB access + Python scoring engine; cannot run in browser |
| Coverage warning parse | API / Backend | Frontend | Backend supplies structured JSON; frontend renders the banner text |
| Segment filter param | API / Backend | Frontend | Backend filters query results; frontend sends the param and manages dropdown state |
| Sensors page UI | Browser / Client | — | Pure display page; no server-side rendering |
| Per-segment gauges | Browser / Client | — | Purely presentational; data comes from `GET /api/merge/latest` |
| Coverage warning banner | Browser / Client | — | Renders structured data from API; no business logic |

---

## Standard Stack

### Core (all pre-installed — no new packages)
| Library | Source | Purpose |
|---------|--------|---------|
| FastAPI + Pydantic v2 | `quirk/dashboard/api/` | Backend routes + response model validation |
| SQLAlchemy (session via `get_db`) | `quirk/dashboard/api/deps.py` | DB session injection; already wired in every route |
| `quirk.merge.scan._assemble_union` | `quirk/merge/scan.py` | Union assembly for per-segment recompute — reuse directly |
| `quirk.merge.scan._build_coverage_warning` | `quirk/merge/scan.py` | Sensor status/overdue logic — reuse for registry status |
| `quirk.intelligence.evidence.build_evidence_summary` | `quirk/intelligence/evidence.py` | Evidence dict per segment for scoring |
| `quirk.intelligence.scoring.compute_readiness_score` | `quirk/intelligence/scoring.py` | Score per segment — same call as org-wide |
| React 18 + react-router-dom | `src/dashboard/src/App.tsx` | Client-side routing; `<Route path="/sensors">` added here |
| shadcn/ui primitives | already installed | `badge`, `card`, `table`, `select`, `skeleton` — no new installs |
| lucide-react | already installed | `Radio` icon for Sensors nav item |
| `fetchApi` wrapper | `src/dashboard/src/lib/api.ts` | Auth + CSRF header injection on every API call |

### No New Packages
The UI-SPEC explicitly confirms: "No new shadcn components need to be installed. All primitives already exist." No npm installs are required for this phase. [VERIFIED: codebase inspection — UI-SPEC + package.json]

---

## Package Legitimacy Audit

Not applicable — this phase installs no new packages.

---

## Architecture Patterns

### System Architecture Diagram

```
Browser (React)
  |
  |-- GET /api/sensor/registry ---------> sensor.py router
  |                                          |-> db.query(Sensor).all()
  |                                          |-> _build_coverage_warning() per row
  |                                          |-> SensorRegistryResponse[]
  |
  |-- GET /api/merge/latest ------------> merge.py router (NEW)
  |                                          |-> db.query(MergeRun).latest row
  |                                          |-> _assemble_union(db)
  |                                          |-> group by segment
  |                                          |-> build_evidence_summary(seg_eps) per segment
  |                                          |-> compute_readiness_score(evidence) per segment
  |                                          |-> MergeLatestResponse (org score + per_segment_scores + coverage_warning)
  |
  |-- GET /api/scan/latest?segment=X ---> scan.py router (EXTENDED)
  |                                          |-> existing endpoint query
  |                                          |-> optional .filter(CryptoEndpoint.segment == segment)
  |                                          |-> existing response unchanged (nullable fields added)
  |
  |-- Sensors page (/sensors) ----------> SensorsPage.tsx
  |                                          |-> useSensorRegistry hook
  |                                          |-> Table with status badges
  |
  |-- Executive page (/) ---------------> ExecutivePage.tsx (EXTENDED)
  |                                          |-> useMergeLatest hook
  |                                          |-> CoverageWarningBanner (if coverage_warning non-null)
  |                                          |-> ScoreGauge per segment (if merge data present)
  |
  |-- FindingsPage (/findings) ---------> FindingsPage.tsx (EXTENDED)
  |                                          |-> segmentFilter state
  |                                          |-> distinctSegments from data.findings
  |                                          |-> Select dropdown + client-side filter
  |
  |-- CbomPage (/cbom) -----------------> CbomPage.tsx (EXTENDED)
                                             |-> segmentFilter state
                                             |-> distinctSegments from data.cbom_components
                                             |-> Select dropdown + client-side filter
```

### Recommended Project Structure (new files only)

```
quirk/dashboard/api/routes/
├── sensor.py         # EXTENDED — add GET /api/sensor/registry
├── merge.py          # NEW — GET /api/merge/latest

src/dashboard/src/
├── pages/
│   └── sensors.tsx                   # NEW — Sensors page
├── hooks/
│   ├── useSensorRegistry.ts          # NEW — fetches /api/sensor/registry
│   └── useMergeLatest.ts             # NEW — fetches /api/merge/latest
```

### Pattern 1: Backend Route — GET /api/sensor/registry

Add to the existing `quirk/dashboard/api/routes/sensor.py` router (which already has `router = APIRouter(dependencies=[Depends(require_auth)])`). The new endpoint reads all `Sensor` rows and computes status using the same overdue logic as `_build_coverage_warning`.

**Status computation** — replicate the overdue check from `_build_coverage_warning` inline (the full warning function is designed for list-of-sensors → one dict, not per-sensor badge; extracting the per-sensor logic is cleaner than calling the full function and parsing its output):

```python
# Source: quirk/merge/scan.py _build_coverage_warning — replicate overdue logic per sensor
from datetime import datetime, timedelta, timezone
_STALE_DAYS = 30

def _sensor_status(s: Sensor, now: datetime) -> str:
    if s.last_push_at is None:
        return "unknown"
    silent = now - s.last_push_at
    if silent > timedelta(days=_STALE_DAYS):
        return "unknown"  # decommissioned — treat as unknown rather than stale
    cadence = timedelta(minutes=s.expected_cadence_minutes or 1440)
    if now > s.last_push_at + 2 * cadence:
        return "stale"
    return "current"
```

Response model (add to `schemas.py`):

```python
class SensorRegistryItem(BaseModel):
    sensor_id: str
    segment: str
    sensor_version: Optional[str] = None
    last_push_at: Optional[datetime] = None
    status: str  # "current" | "stale" | "unknown"

class SensorRegistryResponse(BaseModel):
    sensors: List[SensorRegistryItem]
```

### Pattern 2: Backend Route — GET /api/merge/latest (with per-segment recompute)

New file `quirk/dashboard/api/routes/merge.py`. Key decision: **Option (a) — recompute on read**. The cost analysis:

- `_assemble_union(db)` executes two SQL queries (one subquery for latest-per-sensor, one window for NULL-sensor local rows). Cost: O(endpoints in latest push per sensor). [VERIFIED: codebase — merge/scan.py L87-138]
- `build_evidence_summary(seg_eps)` + `compute_readiness_score(evidence)` are pure-Python, no DB round-trips. Cost: O(|seg_eps|) per segment. [VERIFIED: codebase — evidence.py L61-79, scoring.py L119-148]
- For a typical on-prem deployment with 2-5 segments and a few hundred endpoints per segment, the total wall time will be under 50ms. This is entirely acceptable for a dashboard read endpoint.

Option (b) — storing `per_segment_scores_json` in `merge_runs` — would require: (i) a new `_ADDITIVE_MIGRATIONS` column entry, (ii) modifying `merge_scan()` to compute and persist per-segment scores at merge time, (iii) a migration test. The scoring result would be locked to the profile used at merge time and would not respond to profile changes. Not recommended.

```python
# New file: quirk/dashboard/api/routes/merge.py
import json
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

router = APIRouter(dependencies=[Depends(require_auth)])

@router.get("/merge/latest")
def get_merge_latest(db: Session = Depends(get_db)) -> dict:
    # Read latest MergeRun row
    row = db.query(MergeRun).order_by(MergeRun.merged_at.desc()).first()
    if row is None:
        return {"merge": None}

    # Parse coverage_warning
    coverage_warning = None
    if row.coverage_warning_json:
        try:
            coverage_warning = json.loads(row.coverage_warning_json)
        except (ValueError, TypeError):
            pass

    # Per-segment recompute (Option a)
    union = _assemble_union(db)
    per_segment: Dict[str, int] = {}
    if union:
        segments = {ep.segment for ep in union if ep.segment is not None}
        for seg in segments:
            seg_eps = [ep for ep in union if ep.segment == seg]
            evidence = build_evidence_summary(seg_eps, findings=None)
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

Register in `app.py` exactly as the other routers:
```python
from quirk.dashboard.api.routes import ..., merge
# in create_app():
application.include_router(merge.router, prefix="/api")
```

### Pattern 3: Segment Filter on Existing Routes

The `?segment=` param attaches to `get_latest_scan` (and its underlying endpoint list), and is threaded into the endpoint query. The crucial detail: the filter applies **after** the SESSION_BRACKET endpoint load, by filtering the Python list before it reaches `_derive_findings` and `_derive_cbom`. This avoids touching the window SQL query.

```python
@router.get("/scan/latest", response_model=ScanLatestResponse)
def get_latest_scan(
    scan_id: Optional[str] = Query(default=None),
    segment: Optional[str] = Query(default=None, description="Filter by segment label; omit for all"),
    db: Session = Depends(get_db),
) -> ScanLatestResponse:
    ...
    # After loading `endpoints` list:
    if segment is not None:
        endpoints = [ep for ep in endpoints if ep.segment == segment]
    # Continue into _derive_findings(endpoints), _derive_cbom(endpoints) etc. unchanged
```

NULL-segment (local) scans have `ep.segment == None`. When `segment` param is present, these are excluded — which is correct: a named-segment filter should not surface local-only rows. When `segment` is omitted, all rows (including NULL-segment) pass through unchanged. [VERIFIED: codebase — CryptoEndpoint.segment column is nullable, L99 models.py]

**No response model changes needed for `ScanLatestResponse` itself** — the segment filter changes WHAT endpoints feed the derivation functions, not the shape of the response. However, `FindingItem` and `CbomComponent` need nullable `sensor_id` and `segment` fields added for DASH-02's "expose the dimension" requirement:

```python
class FindingItem(BaseModel):
    ...
    sensor_id: Optional[str] = None   # NEW — nullable, backward-compatible
    segment: Optional[str] = None     # NEW — nullable, backward-compatible

class CbomComponent(BaseModel):
    ...
    sensor_id: Optional[str] = None   # NEW
    segment: Optional[str] = None     # NEW
```

The `_derive_findings` and `_derive_cbom` functions each already receive the `endpoints` list and construct their items from `ep.*` fields. They just need to copy `ep.sensor_id` and `ep.segment` into the items they construct. [VERIFIED: codebase — _derive_findings L95, _derive_cbom L692]

For distinct segments (used to populate the frontend dropdown), the frontend derives them from the data it already has — no separate `/api/segments` endpoint needed. `FindingsPage` and `CbomPage` can compute `distinctSegments` from `data.findings` or `data.cbom_components` respectively.

### Pattern 4: Adding a New React Page (Sensors)

The exact addition sequence from studying `App.tsx` and `sidebar.tsx`: [VERIFIED: codebase]

1. **Create `src/dashboard/src/pages/sensors.tsx`** — mirrors `data-at-rest.tsx` structure (imports from `@/hooks/...`, `@/components/ui/card`, `@/components/ui/table`, `@/components/ui/skeleton`, `@/components/ui/badge`).

2. **Add import + route in `App.tsx`:**
```tsx
import { SensorsPage } from "@/pages/sensors"
// Inside <Routes>:
<Route path="/sensors" element={<SensorsPage />} />
```

3. **Add to `NAV_ITEMS` in `sidebar.tsx`** after `{ path: "/scans", label: "Scan History", Icon: History }` and before `{ path: "/schedules", ... }`:
```tsx
import { Radio } from "lucide-react"   // already imported at top if added here
// In NAV_ITEMS array:
{ path: "/sensors", label: "Sensors", Icon: Radio },
```
`Radio` is not currently in the sidebar import list but IS in lucide-react (already installed). The import line must be added alongside the existing lucide imports.

### Pattern 5: Data Hook — useSensorRegistry

Follows the `useScanData` cancellation pattern exactly: [VERIFIED: codebase — useScanData.ts]

```typescript
// src/dashboard/src/hooks/useSensorRegistry.ts
import { useState, useEffect } from "react"
import { fetchApi } from "@/lib/api"

export interface SensorRegistryItem {
  sensor_id: string
  segment: string
  sensor_version: string | null
  last_push_at: string | null
  status: "current" | "stale" | "unknown"
}

interface UseSensorRegistryResult {
  sensors: SensorRegistryItem[]
  loading: boolean
  error: string | null
}

export function useSensorRegistry(): UseSensorRegistryResult {
  const [sensors, setSensors] = useState<SensorRegistryItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setSensors([])
    setLoading(true)
    setError(null)

    async function fetchData() {
      try {
        const resp = await fetchApi("/api/sensor/registry")
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
    return () => { cancelled = true }
  }, [])

  return { sensors, loading, error }
}
```

### Pattern 6: Data Hook — useMergeLatest

```typescript
// src/dashboard/src/hooks/useMergeLatest.ts
import { useState, useEffect } from "react"
import { fetchApi } from "@/lib/api"

export interface MergeLatestData {
  scan_id: string
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

interface UseMergeLatestResult {
  merge: MergeLatestData | null
  loading: boolean
  error: string | null
}

export function useMergeLatest(): UseMergeLatestResult {
  const [merge, setMerge] = useState<MergeLatestData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setMerge(null)
    setLoading(true)
    setError(null)

    async function fetchData() {
      try {
        const resp = await fetchApi("/api/merge/latest")
        if (!resp.ok) {
          if (!cancelled) setError(`Failed to fetch merge: ${resp.status}`)
          return
        }
        const json = await resp.json()
        if (!cancelled) setMerge(json.merge ?? null)
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err))
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    fetchData()
    return () => { cancelled = true }
  }, [])

  return { merge, loading, error }
}
```

### Pattern 7: ScoreGauge — Per-Segment Usage

The existing `ScoreGauge` component signature is: [VERIFIED: codebase — ScoreGauge.tsx]

```typescript
interface ScoreGaugeProps {
  score: number          // 0..maxValue
  label: string
  size?: number          // default 120
  strokeColor?: string
  isOverall?: boolean    // true = accent stroke, larger label
  maxValue?: number      // default 100
}
```

Per-segment gauges use `maxValue={100}` because `compute_readiness_score` produces a 0-100 result (via `sum of six 0-25 subscores / 1.5`). [VERIFIED: codebase — scoring.py comment L12-14]

The existing subscore gauges use `maxValue={25}` because they expose individual subscores (0-25 range). Per-segment gauges are full re-scored results, so `maxValue={100}` is correct.

**Truncation rule (from UI-SPEC):** `label.length > 16 ? label.slice(0, 15) + '…' : label`

In `executive.tsx`, per-segment gauges render inside the existing `flex flex-wrap justify-around gap-8` div alongside the org-wide gauge. No new container layout needed.

### Pattern 8: Coverage Warning Banner

The existing `RegressionAlertChip` in `executive.tsx` is rendered at L227 (`<RegressionAlertChip />`). The coverage banner renders immediately before this (`RegressionAlertChip` itself is inside the "space-y-8" outer div, above the score gauges Card). The coverage banner attaches to the same position:

```tsx
{/* Coverage warning — above RegressionAlertChip and score gauges */}
{merge?.coverage_warning && (
  <div
    className="flex items-start gap-3 rounded-md border px-4 py-3 mb-6"
    style={{
      background: "var(--ds-high-dim)",
      borderColor: "var(--ds-high-bdr)",
    }}
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
```

`AlertTriangle` is already imported in `RegressionAlertChip.tsx` but NOT currently in `executive.tsx`. It must be added to the lucide-react import in `executive.tsx`.

### Anti-Patterns to Avoid

- **Conditionally mounting Recharts children:** The existing `executive.tsx` uses Recharts for the severity bar chart (`<Bar>` inside `<BarChart>`). Do NOT add conditional mounting of Bar/Cell children. Toggle via `fillOpacity`/`strokeOpacity` if conditional display is needed. (This phase adds SVG-based ScoreGauge items, not Recharts; rule applies to any future Recharts additions in this phase.)
- **Calling `_build_coverage_warning` for per-sensor badge computation:** The function returns one dict for a list of sensors, not a per-sensor status. Use the inlined `_sensor_status` helper pattern above instead.
- **Mutating `CryptoEndpoint.scanned_at` in `_assemble_union`:** The function is explicitly documented as read-only. Never call `db.flush()` or `db.commit()` in the registry/merge endpoints.
- **Skipping `db.rollback()` on exception:** Pattern from `sensor.py` — if any exception occurs in a write path, rollback before audit. Registry and merge endpoints are read-only, so this is moot, but new routes should not accidentally open write transactions.
- **Hardcoding segment names:** Do not hardcode segment names anywhere. Derive them from the database at runtime.
- **Using raw `fetch()` instead of `fetchApi()`:** All React components must use `fetchApi` from `lib/api.ts`. [VERIFIED: codebase — HARDEN-API-01 note in api.ts]

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Per-sensor overdue computation | Custom threshold logic | `_build_coverage_warning` logic from `quirk/merge/scan.py` | Already handles: 2× cadence, stale-days exclusion, NULL last_push_at vs enrolled_at, NULL cadence fallback — all edge cases are already tested |
| Union assembly | Custom query | `_assemble_union(db)` from `quirk/merge/scan.py` | Handles SESSION_BRACKET for local rows + latest-per-sensor subquery; tested |
| Per-segment scoring | Custom scoring formula | `build_evidence_summary()` + `compute_readiness_score()` | Option A is the locked methodology; hand-rolling would diverge from the org-wide score's formula |
| CSRF + auth injection | Per-call headers | `fetchApi()` from `lib/api.ts` | Single enforcement point; bypassing it violates HARDEN-API-01 |
| Relative time formatting | Custom date math | Standard `Intl.RelativeTimeFormat` or inline calculation | Browsers handle this; avoid a date library import for one use case |

---

## Runtime State Inventory

> Not applicable — this is a greenfield read-only feature addition, not a rename/refactor/migration phase. No stored data needs updating.

---

## Common Pitfalls

### Pitfall 1: `_assemble_union` is a Read-Only DB Function — Don't Wrap in a Write Transaction
**What goes wrong:** Calling `db.commit()` or `db.flush()` after `_assemble_union` inside a GET endpoint silently starts a write transaction where none is needed.
**Why it happens:** The function calls `db.query(...)` which works in a read-only context, but careless copy-paste from `merge_scan()` (which does flush+commit) would include the write calls.
**How to avoid:** New read endpoints return data and do nothing else. No `db.add()`, `db.flush()`, or `db.commit()` calls.

### Pitfall 2: Segment Filter Breaks NULL-Segment Local Scans
**What goes wrong:** Applying `ep.segment == segment` when `segment` param is omitted filters out ALL rows (since `None == None` is truthy in Python but `ep.segment` is the column value which is SQL NULL — SQLAlchemy returns `None` for nullable columns, but the intent is to filter ONLY when param is supplied).
**Why it happens:** Forgetting the guard `if segment is not None:` before applying the filter.
**How to avoid:** The filter must be: `if segment is not None: endpoints = [ep for ep in endpoints if ep.segment == segment]`. When `segment` is None (omitted), no filtering happens — all rows including NULL-segment pass through.
**Warning signs:** Test with an existing single-host scan — if it returns 404 or empty when no segment param is given, the guard is missing.

### Pitfall 3: Per-Segment Scores Calculated on Wrong Endpoint Set
**What goes wrong:** Grouping endpoints by their `sensor_id` instead of `segment`, producing one score per sensor rather than one score per segment. A segment could have multiple sensors; a sensor always belongs to exactly one segment.
**Why it happens:** Confusing the sensor grouping (in `_assemble_union` which groups by `sensor_id`) with the segment grouping needed for per-segment scores.
**How to avoid:** Group by `ep.segment` (not `ep.sensor_id`) in the per-segment recompute loop in `GET /api/merge/latest`.

### Pitfall 4: `coverage_warning_json` Parsing Error Crashes the Endpoint
**What goes wrong:** If `coverage_warning_json` is somehow malformed JSON (shouldn't happen given Phase 110, but defensive coding is required), `json.loads()` raises `ValueError` and the endpoint 500s.
**How to avoid:** Wrap in `try/except (ValueError, TypeError)` and set `coverage_warning = None` on parse failure.

### Pitfall 5: React `distinctSegments` Out of Sync with Backend Filter
**What goes wrong:** The segment dropdown on FindingsPage is populated from `data.findings` items that already arrived without `segment` field (if `FindingItem` schema wasn't updated), leaving the dropdown empty or stale.
**How to avoid:** Ensure `FindingItem.segment` and `CbomComponent.segment` are added to the Pydantic models AND that `_derive_findings` and `_derive_cbom` copy `ep.segment` into the constructed items. The TypeScript types in `src/dashboard/src/types/api.ts` must also be updated to mirror the new optional fields.

### Pitfall 6: `Radio` Icon Not Imported in sidebar.tsx
**What goes wrong:** Adding `{ path: "/sensors", Icon: Radio }` to `NAV_ITEMS` without adding `Radio` to the lucide-react import at the top of `sidebar.tsx` causes a runtime "Radio is not defined" error.
**How to avoid:** Add `Radio` to the existing lucide-react named import block at the top of `sidebar.tsx`. [VERIFIED: codebase — sidebar.tsx L1-21 shows current imports]

### Pitfall 7: `AlertTriangle` Not Imported in executive.tsx
**What goes wrong:** The coverage warning banner uses `<AlertTriangle>` from lucide-react. This icon is imported in `RegressionAlertChip.tsx` but NOT in `executive.tsx` currently.
**How to avoid:** Add `AlertTriangle` to the lucide-react import in `executive.tsx`.

### Pitfall 8: TypeScript Types Not Updated to Match New Pydantic Fields
**What goes wrong:** Adding `sensor_id`/`segment` to Python `FindingItem`/`CbomComponent` but forgetting to add them to `src/dashboard/src/types/api.ts`. TypeScript will still compile (the extra fields are ignored), but accessing `finding.segment` in the frontend will be `undefined` even though the API sends it.
**How to avoid:** The schema docstring at the top of `schemas.py` says: "TypeScript types in `src/dashboard/src/types/api.ts` must mirror these exactly." Update both files together.

---

## Code Examples

### Backend: SensorRegistryItem response assembly
```python
# In GET /api/sensor/registry handler
now = datetime.now(timezone.utc).replace(tzinfo=None)
sensors = db.query(Sensor).order_by(Sensor.enrolled_at.desc()).all()
items = []
for s in sensors:
    items.append(SensorRegistryItem(
        sensor_id=s.sensor_id,
        segment=s.segment,
        sensor_version=s.sensor_version,
        last_push_at=s.last_push_at,
        status=_sensor_status(s, now),
    ))
return SensorRegistryResponse(sensors=items)
```

### Backend: Segment-grouped per-segment scoring
```python
# In GET /api/merge/latest — after _assemble_union(db)
from collections import defaultdict
seg_map: Dict[str, List[CryptoEndpoint]] = defaultdict(list)
for ep in union:
    if ep.segment is not None:
        seg_map[ep.segment].append(ep)

per_segment: Dict[str, int] = {}
for seg, eps in seg_map.items():
    evidence = build_evidence_summary(eps, findings=None)
    result = compute_readiness_score(evidence)
    per_segment[seg] = int(result["score"]) if result.get("score") is not None else 0
```

### Frontend: Segment filter dropdown (FindingsPage)
```tsx
// State
const [segmentFilter, setSegmentFilter] = useState("all")

// Derive distinct segments from loaded findings
const distinctSegments = useMemo(() => {
  if (!data?.findings) return []
  const segs = new Set(data.findings.map(f => f.segment).filter(Boolean) as string[])
  return Array.from(segs).sort()
}, [data])

// In the filter bar (after protocolFilter Select):
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

// In the filtered findings computation:
const findings = useMemo(() => {
  if (!data?.findings) return []
  let filtered = data.findings
  if (severityFilter !== "ALL") filtered = filtered.filter(f => f.severity === severityFilter)
  if (protocolFilter !== "ALL") filtered = filtered.filter(f => f.protocol === protocolFilter)
  if (segmentFilter !== "all") filtered = filtered.filter(f => f.segment === segmentFilter)
  return filtered
}, [data, severityFilter, protocolFilter, segmentFilter])
```

### Frontend: Per-segment gauges in executive.tsx
```tsx
// After existing subscore gauges, inside the flex-wrap div:
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

---

## State of the Art

| Area | Current State | Notes |
|------|--------------|-------|
| Per-segment score source | Not stored in `merge_runs` | Option (a): recompute on read via `_assemble_union` + `compute_readiness_score` per segment. Confirmed feasible at on-prem volume. |
| `FindingItem.segment` | Not yet in schemas | Add as `Optional[str] = None` — additive, backward-compatible |
| `CbomComponent.segment` | Not yet in schemas | Same |
| Sensor router | Only has `POST /api/sensor/push` | `GET /api/sensor/registry` is new work in this phase |
| Merge router | Does not exist | New `quirk/dashboard/api/routes/merge.py` |
| App.tsx routes | No `/sensors` route | Add Route + import |
| sidebar.tsx NAV_ITEMS | No Sensors item | Add after Scan History, before Schedules |

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Backend framework | pytest + FastAPI TestClient |
| Frontend framework | vitest 2.1.x |
| Config file | `src/dashboard/vitest.config.ts` (inferred from package.json) |
| Backend quick run | `python -m pytest tests/test_dashboard_api.py tests/test_merge_scan.py -x -q` |
| Frontend quick run | `cd src/dashboard && npm test` (runs `vitest run`) |
| Full suite | `python -m pytest tests/ -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DASH-01 | GET /api/sensor/registry returns sensor list with status badges | unit (TestClient) | `pytest tests/test_dashboard_sensor_registry.py -x` | No — Wave 0 |
| DASH-01 | `_sensor_status()` returns correct badge for current/stale/unknown | unit (pure Python) | `pytest tests/test_sensor_registry_status.py -x` | No — Wave 0 |
| DASH-02 | `?segment=X` filters findings to only that segment | unit (TestClient) | `pytest tests/test_dashboard_segment_filter.py -x` | No — Wave 0 |
| DASH-02 | NULL-segment scans unaffected when segment param omitted | unit (TestClient) | included in above | No — Wave 0 |
| DASH-03 | GET /api/merge/latest returns per_segment_scores dict | unit (TestClient) | `pytest tests/test_dashboard_merge_latest.py -x` | No — Wave 0 |
| DASH-03 | No-merge state returns `{"merge": null}` | unit (TestClient) | included in above | No — Wave 0 |
| DASH-02 | FindingItem.sensor_id / .segment fields present in response | unit (TestClient) | `pytest tests/test_dashboard_finding_segment_field.py -x` | No — Wave 0 |

**Existing tests that must stay green:**
- `tests/test_dashboard_api.py` — existing findings/cbom endpoint presence assertions must still pass (segment filter is additive; no segment param = existing behavior)
- `tests/test_merge_scan.py` — `_assemble_union` behavior must not be modified
- `src/dashboard/__tests__/findings-columns-memo.test.tsx` — adding `segmentFilter` state must not break existing column memo test

### Wave 0 Gaps
- [ ] `tests/test_dashboard_sensor_registry.py` — DASH-01 backend tests
- [ ] `tests/test_dashboard_segment_filter.py` — DASH-02 segment filter tests
- [ ] `tests/test_dashboard_merge_latest.py` — DASH-03 merge/latest endpoint tests
- [ ] `tests/test_dashboard_finding_segment_field.py` — DASH-02 schema field presence tests
- [ ] `src/dashboard/src/pages/__tests__/sensors-loading.test.tsx` — Sensors page loading/empty/populated states (vitest)

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | `Depends(require_auth)` on all new routers — same as existing routes |
| V3 Session Management | no | No new session handling |
| V4 Access Control | no | Single-tenant, no role differentiation |
| V5 Input Validation | yes | `segment` query param — plain string, used only as equality filter on `ep.segment`, no SQL injection risk (SQLAlchemy ORM binding) |
| V6 Cryptography | no | No new crypto operations |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Unauthenticated sensor registry dump | Information Disclosure | Router-level `Depends(require_auth)` on all new routes — same as existing sensor push route |
| Segment filter path traversal / injection | Tampering | String used only as SQLAlchemy ORM equality filter — parameterized automatically; no LIKE or raw SQL |
| `coverage_warning_json` parse crash (malformed stored data) | Denial of Service | `try/except (ValueError, TypeError)` wrapper; return `coverage_warning=None` on parse failure |
| `_assemble_union` triggering accidental write | Tampering | Read-only endpoint — no `db.add/flush/commit` in GET handlers |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | On-prem deployment endpoint volume (few hundred to few thousand rows) makes per-segment recompute cost negligible | Per-Segment Gauges decision | If a deployment has tens of thousands of endpoints, the recompute may be slow; Option (b) column would then be preferable |
| A2 | `Radio` icon is available in the installed version of lucide-react | Standard Stack / Sensors Nav | If icon is absent, a different lucide icon must be chosen |

---

## Open Questions

1. **Should `/api/merge/latest` trigger a new `_assemble_union` call on every page load?**
   - What we know: The Executive page calls this on mount. For a single user, one call per page visit is fine.
   - What's unclear: If the dashboard auto-refreshes (e.g., polling), repeated calls could stack up.
   - Recommendation: No polling on the merge endpoint for Phase 111. Manual refresh (page reload) is sufficient. Phase 112+ can add auto-refresh.

2. **Should the segment filter also apply to `identity_findings`, `motion_findings`, `dar_findings` in `ScanLatestResponse`?**
   - What we know: The CONTEXT.md locks the filter to findings and CBOM views. `get_latest_scan` drives all of these from the same `endpoints` list.
   - What's unclear: Whether the locked decision intends the filter to flow through to the sub-finding types or only to `findings` and `cbom_components`.
   - Recommendation: Apply the filter at the `endpoints` list level (before any `_derive_*` call). This naturally filters all derived views consistently. If the CONTEXT means only findings + CBOM should be filtered, the filter must be applied inside `_derive_findings` / `_derive_cbom` only. The consistent approach (filter the source list) is cleaner and produces no surprises.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11+ | Backend routes | assumed (project requirement) | — | — |
| `quirk.merge.scan` module | `GET /api/merge/latest` | ✓ | Phase 110 shipped | — |
| `quirk.models.MergeRun` | `GET /api/merge/latest` | ✓ | Phase 110 shipped | — |
| `quirk.models.Sensor` | `GET /api/sensor/registry` | ✓ | Phase 107 shipped | — |
| `Radio` (lucide-react) | Sensors nav icon | assumed available | check at implementation | Pick alternative icon if absent |
| `npm run build` (src/dashboard/) | All .tsx changes | ✓ | available per CLAUDE.md | — |
| vitest | Frontend tests | ✓ | ^2.1.9 per package.json | — |

---

## Sources

### Primary (HIGH confidence)
- [VERIFIED: codebase] `quirk/merge/scan.py` — `_assemble_union`, `_build_coverage_warning`, `merge_scan` signatures and behavior read directly
- [VERIFIED: codebase] `quirk/models.py` — `Sensor`, `MergeRun`, `CryptoEndpoint` column definitions
- [VERIFIED: codebase] `quirk/intelligence/scoring.py` — `compute_readiness_score` signature; scoring formula comment (0-100 = sum(6 subscores) / 1.5)
- [VERIFIED: codebase] `quirk/intelligence/evidence.py` — `build_evidence_summary` signature
- [VERIFIED: codebase] `quirk/dashboard/api/routes/scan.py` — `get_latest_scan` at ~L958, `_derive_findings` at L95, `_derive_cbom` at L692
- [VERIFIED: codebase] `quirk/dashboard/api/routes/sensor.py` — existing router structure, auth pattern
- [VERIFIED: codebase] `quirk/dashboard/api/app.py` — router registration pattern
- [VERIFIED: codebase] `quirk/dashboard/api/schemas.py` — `FindingItem`, `CbomComponent`, `ScanLatestResponse` shapes
- [VERIFIED: codebase] `src/dashboard/src/App.tsx` — route registration pattern
- [VERIFIED: codebase] `src/dashboard/src/components/sidebar.tsx` — NAV_ITEMS structure, lucide icon import pattern
- [VERIFIED: codebase] `src/dashboard/src/lib/api.ts` — `fetchApi` wrapper
- [VERIFIED: codebase] `src/dashboard/src/hooks/useScanData.ts` — hook cancellation pattern
- [VERIFIED: codebase] `src/dashboard/src/components/gauges/ScoreGauge.tsx` — full prop interface
- [VERIFIED: codebase] `src/dashboard/src/pages/executive.tsx` — RegressionAlertChip placement (L227), gauge layout (L232-256)
- [VERIFIED: codebase] `src/dashboard/src/pages/findings.tsx` — filter pattern, Select usage
- [VERIFIED: codebase] `src/dashboard/src/pages/cbom.tsx` — qsFilter pattern
- [VERIFIED: codebase] `src/dashboard/src/pages/data-at-rest.tsx` — page structure template
- [VERIFIED: codebase] `111-CONTEXT.md` — locked decisions
- [VERIFIED: codebase] `111-UI-SPEC.md` — visual/interaction contract

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all verified from codebase; no new packages
- Architecture: HIGH — all integration points read directly from source
- Per-segment recompute feasibility: HIGH — signatures and cost model verified
- Pitfalls: HIGH — derived from direct code inspection
- Option (a) vs (b) recommendation: HIGH — cost model confirmed; Option (b) requires reopening Phase 110

**Research date:** 2026-05-25
**Valid until:** 2026-06-25 (stable codebase; changes to Phase 110 merge engine would require re-verification)
