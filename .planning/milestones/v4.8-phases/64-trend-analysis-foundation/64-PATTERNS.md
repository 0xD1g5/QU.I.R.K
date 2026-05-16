# Phase 64: Trend Analysis Foundation - Pattern Map

**Mapped:** 2026-05-10
**Files analyzed:** 8 new/modified files
**Analogs found:** 8 / 8

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `quirk/dashboard/api/routes/trends.py` (modify) | route | request-response | `quirk/dashboard/api/routes/trends.py` (self) | exact |
| `quirk/dashboard/api/schemas.py` (modify) | model | request-response | `quirk/dashboard/api/schemas.py` (self — `TrendReportResponse` pattern) | exact |
| `src/dashboard/src/hooks/useTimelineData.ts` | hook | request-response | `src/dashboard/src/hooks/useTrendsData.ts` | exact |
| `src/dashboard/src/components/RegressionAlertChip.tsx` | component | event-driven | `src/dashboard/src/pages/executive.tsx` (local state + conditional render pattern) | role-match |
| `src/dashboard/src/types/api.ts` (modify) | model | request-response | `src/dashboard/src/types/api.ts` (self — `TrendReport` interface block) | exact |
| `src/dashboard/src/pages/trends.tsx` (modify) | component | request-response | `src/dashboard/src/pages/executive.tsx` (Recharts usage) | role-match |
| `src/dashboard/src/pages/executive.tsx` (modify) | component | request-response | `src/dashboard/src/pages/executive.tsx` (self — insertion point) | exact |
| `tests/test_dashboard_trends.py` (modify) | test | request-response | `tests/test_dashboard_trends.py` (self — existing seeded-DB pattern) | exact |

---

## Pattern Assignments

### `quirk/dashboard/api/routes/trends.py` — add `_list_session_timestamps_n` + `GET /api/trends/timeline`

**Analog:** `quirk/dashboard/api/routes/trends.py` (self)

**Imports pattern** (lines 12–28):
```python
from __future__ import annotations

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends
from quirk.dashboard.api.middleware.auth import require_auth
from sqlalchemy import func
from sqlalchemy.orm import Session

from quirk.dashboard.api.deps import get_db
from quirk.dashboard.api.schemas import (
    SampleFinding,
    TrendReportResponse,
)
from quirk.intelligence.trends import compute_trend_report
from quirk.models import CryptoEndpoint
```

**New imports to add** (append after existing imports in the file):
```python
from fastapi import Query
from quirk.dashboard.api.schemas import TrendTimelineResponse, TrendSessionPoint
from quirk.intelligence.evidence import build_evidence_summary
from quirk.intelligence.scoring import compute_readiness_score
from quirk.intelligence.trends import (
    _fetch_session_endpoints,
    _count_by_bucket,
)
```

**Auth pattern** (line 30) — router-level, inherited automatically by all new routes:
```python
router = APIRouter(dependencies=[Depends(require_auth)])
```
No per-route auth annotation needed. Any `@router.get(...)` added to this router is automatically protected.

**Session enumeration pattern** (lines 33–50) — copy + parameterize for `_list_session_timestamps_n`:
```python
def _list_session_timestamps(db: Session) -> List[datetime]:
    ts_sec = func.strftime(
        "%Y-%m-%d %H:%M:%S", CryptoEndpoint.scanned_at
    ).label("ts_sec")
    rows = (
        db.query(ts_sec)
        .filter(CryptoEndpoint.scanned_at.isnot(None))
        .group_by("ts_sec")
        .order_by(ts_sec.desc())
        .limit(10)
        .all()
    )
    return [datetime.fromisoformat(r.ts_sec) for r in rows]
```

**New private helper — parameterized LIMIT variant** (add after `_list_session_timestamps`):
```python
def _list_session_timestamps_n(db: Session, n: int) -> List[datetime]:
    """Return up to n most recent distinct session timestamps (newest first).

    Do NOT modify _list_session_timestamps() — it is hardcoded to LIMIT 10
    and consumed by get_trends. This variant adds a parameterized LIMIT.
    """
    ts_sec = func.strftime(
        "%Y-%m-%d %H:%M:%S", CryptoEndpoint.scanned_at
    ).label("ts_sec")
    rows = (
        db.query(ts_sec)
        .filter(CryptoEndpoint.scanned_at.isnot(None))
        .group_by("ts_sec")
        .order_by(ts_sec.desc())
        .limit(n)
        .all()
    )
    return [datetime.fromisoformat(r.ts_sec) for r in rows]
```

**Core route pattern** (model: `get_trends` at lines 53–81):
```python
@router.get("/trends", response_model=TrendReportResponse)
def get_trends(db: Session = Depends(get_db)) -> TrendReportResponse:
    sessions = _list_session_timestamps(db)
    if len(sessions) == 0:
        return TrendReportResponse()
    ...
```

New timeline route follows the same shape:
```python
@router.get("/trends/timeline", response_model=TrendTimelineResponse)
def get_trends_timeline(
    n: int = Query(default=30, ge=2, le=200),
    db: Session = Depends(get_db),
) -> TrendTimelineResponse:
    sessions = _list_session_timestamps_n(db, n)
    if not sessions:
        return TrendTimelineResponse(sessions=[])
    points = []
    for ts in sessions:
        eps = _fetch_session_endpoints(db, ts)
        if not eps:
            continue
        evidence = build_evidence_summary(eps)
        score_dict = compute_readiness_score(evidence)
        sub = score_dict["subscores"]
        keys = [
            (ep.host, ep.port, ep.protocol, ep.severity)
            for ep in eps if ep.scan_error is None
        ]
        counts = _count_by_bucket(keys)
        points.append(TrendSessionPoint(
            session_ts=ts.isoformat(),
            score=score_dict["score"],
            subscores=sub,
            finding_counts=counts,
        ))
    return TrendTimelineResponse(sessions=points)
```

**Error handling pattern:** FastAPI + Pydantic handles 422 automatically when `n < 2` (ge=2 constraint). Empty DB case returns `TrendTimelineResponse(sessions=[])` with HTTP 200 — same as `get_trends` returns `TrendReportResponse()` for the 0-session case (line 64).

---

### `quirk/dashboard/api/schemas.py` — add `FindingCounts`, `TrendSessionPoint`, `TrendTimelineResponse`

**Analog:** `quirk/dashboard/api/schemas.py` (self — `TrendReportResponse` block, lines 221–237)

**Existing `SubScores` model to reuse** (lines 20–26):
```python
class SubScores(BaseModel):
    hygiene: int
    modern_tls: int
    identity_trust: int
    agility_signals: int
    data_at_rest: int = 0
    data_in_motion: int = 0
```

**Existing `TrendReportResponse` structural pattern** (lines 221–237) — follow the same `BaseModel` + typed field style with defaults:
```python
class TrendReportResponse(BaseModel):
    current_session_ts: Optional[datetime] = None
    ...
    new_high: int = 0
    ...
    new_findings_sample: List[SampleFinding] = []
```

**New schemas to add** (append after `TrendReportResponse`):
```python
# ---- Timeline (Phase 64 TREND-01) ----

class FindingCounts(BaseModel):
    high: int = 0
    medium: int = 0
    low: int = 0


class TrendSessionPoint(BaseModel):
    session_ts: str          # ISO 8601 string
    score: int
    subscores: SubScores     # reuses existing SubScores — do NOT duplicate
    finding_counts: FindingCounts


class TrendTimelineResponse(BaseModel):
    sessions: List[TrendSessionPoint] = []
```

**Import pattern** (lines 1–11) — `List` already imported; `Optional` already imported; no new imports needed.

---

### `src/dashboard/src/hooks/useTimelineData.ts` — new cancellation-safe fetch hook

**Analog:** `src/dashboard/src/hooks/useTrendsData.ts` (exact copy, change endpoint + type)

**Full template** (lines 1–65 of `useTrendsData.ts`):
```typescript
import { useState, useEffect } from "react"
import type { TrendReport } from "@/types/api"
import { fetchApi } from "@/lib/api"

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
        const resp = await fetchApi("/api/trends")
        if (!resp.ok) {
          if (!cancelled) {
            if (resp.status === 401) { setError("Authentication required"); return }
            if (resp.status === 403) { setError("Request blocked"); return }
            if (resp.status === 429) {
              const retryAfter = resp.headers.get("Retry-After") ?? "60"
              setError(`Too many requests. Wait ${retryAfter} seconds and try again.`)
              return
            }
            setError(`API error: ${resp.status} ${resp.statusText}`)
          }
          return
        }
        const json: TrendReport = await resp.json()
        if (!cancelled) { setData(json) }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load trend data")
        }
      } finally {
        if (!cancelled) { setLoading(false) }
      }
    }

    fetchData()
    return () => { cancelled = true }
  }, [])

  return { data, loading, error }
}
```

**Changes to make when copying:**
- Import `TrendTimeline` instead of `TrendReport`
- Rename result interface to `UseTimelineDataResult`
- Rename function to `useTimelineData`
- Change endpoint to `/api/trends/timeline?n=30`
- Change error fallback message to `"Failed to load timeline"`
- Change type annotation `json: TrendTimeline`

---

### `src/dashboard/src/components/RegressionAlertChip.tsx` — new dismissible alert chip

**Analog:** `src/dashboard/src/pages/executive.tsx` (local state + conditional render + lucide icon pattern)

**Local state pattern from executive.tsx** (lines 29–31):
```typescript
export function ExecutivePage() {
  const { data, loading, error } = useScanData()
  const [pdfExporting, setPdfExporting] = useState(false)
```

**Lucide icon import pattern from executive.tsx** (line 9):
```typescript
import { Download, Loader2 } from "lucide-react"
```

**Conditional render pattern from executive.tsx** (lines 62–81):
```typescript
if (loading) return <PageSpinner ariaLabel="Loading executive summary" />
if (error) { return (...) }
if (!data || !data.score) { return (...) }
```

**Full component implementation** (follows CONTEXT.md D-07/D-08/D-09 and RESEARCH.md Pitfall 4 fix):
```tsx
import { useState } from "react"
import { AlertTriangle } from "lucide-react"
import { Link } from "react-router-dom"
import { useTrendsData } from "@/hooks/useTrendsData"

export function RegressionAlertChip() {
  const { data, loading } = useTrendsData()
  const [manuallyDismissed, setManuallyDismissed] = useState(false)

  if (loading || !data || manuallyDismissed) return null

  const sessionTs = data.current_session_ts ?? null
  // Compute from data (not useState initial) to avoid stale-on-mount pitfall
  const isDismissed = sessionTs
    ? !!localStorage.getItem(`quirk.dismissed_regression.${sessionTs}`)
    : false
  if (isDismissed) return null

  const isRegression =
    (data.score_delta !== null && data.score_delta <= -5) || data.new_high > 0
  if (!isRegression) return null

  function handleDismiss() {
    if (sessionTs) localStorage.setItem(`quirk.dismissed_regression.${sessionTs}`, "1")
    setManuallyDismissed(true)
  }

  const message = data.score_delta !== null && data.score_delta <= -5
    ? `Score dropped ${Math.abs(data.score_delta)} pts.`
    : `${data.new_high} new HIGH/CRITICAL finding(s) detected.`

  return (
    <div className="flex items-center gap-2 rounded-md border border-destructive bg-destructive/10 px-4 py-2 mb-8">
      <AlertTriangle className="h-4 w-4 text-destructive shrink-0" />
      <span className="text-sm flex-1">
        {message}{" "}
        <Link to="/trends" className="text-primary underline">View trends →</Link>
      </span>
      <button
        onClick={handleDismiss}
        aria-label="Dismiss regression alert"
        className="text-muted-foreground hover:text-foreground ml-2"
      >
        ×
      </button>
    </div>
  )
}
```

---

### `src/dashboard/src/types/api.ts` — add `TrendFindingCounts`, `TrendSessionPoint`, `TrendTimeline`

**Analog:** `src/dashboard/src/types/api.ts` (self — existing `TrendReport` block, lines 167–183)

**Existing `SubScores` interface to reuse** (lines 1–8):
```typescript
export interface SubScores {
  hygiene: number
  modern_tls: number
  identity_trust: number
  agility_signals: number
  data_at_rest: number
  data_in_motion: number
}
```

**Existing `TrendReport` pattern** (lines 167–183) — same flat field style with `| null` for optional numerics:
```typescript
export interface TrendReport {
  current_session_ts: string | null
  ...
  score_delta: number | null
  new_high: number
  ...
}
```

**New interfaces to append** (after `TrendReport`, before the `// ============== QRAMM` separator):
```typescript
// Phase 64 TREND-01: timeline types
export interface TrendFindingCounts {
  high: number
  medium: number
  low: number
}

export interface TrendSessionPoint {
  session_ts: string       // ISO 8601 string
  score: number
  subscores: SubScores     // reuses existing SubScores interface
  finding_counts: TrendFindingCounts
}

export interface TrendTimeline {
  sessions: TrendSessionPoint[]
}
```

---

### `src/dashboard/src/pages/trends.tsx` — add LineChart section above existing delta cards

**Analog:** `src/dashboard/src/pages/executive.tsx` (Recharts BarChart pattern, lines 7, 165–180)

**Recharts import pattern from executive.tsx** (line 7):
```typescript
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts"
```

New import needed in trends.tsx:
```typescript
import { LineChart, Line, XAxis, YAxis, CartesianGrid } from "recharts"
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart"
import type { ChartConfig } from "@/components/ui/chart"
import { useTimelineData } from "@/hooks/useTimelineData"
```

**ChartContainer usage pattern from executive.tsx** (lines 165–180):
```tsx
<ResponsiveContainer width="100%" height={180}>
  <BarChart data={chartData} layout="vertical" margin={{ left: 8, right: 32 }}>
    <XAxis type="number" tick={{ fontSize: 12 }} />
    <YAxis type="category" dataKey="severity" tick={{ fontSize: 12 }} width={72} />
    <Tooltip
      contentStyle={{ background: "hsl(240 6% 10%)", ... }}
    />
    <Bar dataKey="count" radius={[0, 4, 4, 0]}>
      {chartData.map(...)}
    </Bar>
  </BarChart>
</ResponsiveContainer>
```

Use `ChartContainer` (not bare `ResponsiveContainer`) for LineChart to get consistent theming:

**Chart config object** (copy from RESEARCH.md Pattern 6):
```typescript
const TIMELINE_CHART_CONFIG: ChartConfig = {
  score:          { label: "Overall",        color: "hsl(var(--quantum-safe))" },
  hygiene:        { label: "Hygiene",        color: "hsl(180 37% 47%)" },
  modern_tls:     { label: "TLS",            color: "hsl(213 94% 68%)" },
  identity_trust: { label: "Identity",       color: "hsl(38 92% 50%)" },
  agility_signals:{ label: "Agility",        color: "hsl(28 64% 52%)" },
  data_at_rest:   { label: "Data at Rest",   color: "hsl(270 50% 60%)" },
  data_in_motion: { label: "Data in Motion", color: "hsl(152 47% 45%)" },
}
```

**Data flattening pattern** (CRITICAL — Recharts cannot traverse nested keys):
```typescript
const chartDataAsc = [...(timelineData?.sessions ?? [])]
  .reverse()   // API newest-first → chart oldest-left
  .map(s => ({
    session_ts:       s.session_ts,
    score:            s.score,
    hygiene:          s.subscores.hygiene,
    modern_tls:       s.subscores.modern_tls,
    identity_trust:   s.subscores.identity_trust,
    agility_signals:  s.subscores.agility_signals,
    data_at_rest:     s.subscores.data_at_rest,
    data_in_motion:   s.subscores.data_in_motion,
  }))
```

**Static children rule (MANDATORY)** — all 7 `<Line>` components must always be present; never conditionally mounted:
```tsx
<ChartContainer config={TIMELINE_CHART_CONFIG}>
  <LineChart data={chartDataAsc} margin={{ top: 4, right: 16, left: 0, bottom: 4 }}>
    <XAxis dataKey="session_ts"
      tickFormatter={(v: string) => new Date(v).toLocaleString([], {
        month: "2-digit", day: "2-digit",
        hour: "2-digit", minute: "2-digit",
      })}
    />
    <YAxis domain={[0, 100]} tickCount={6} />
    <ChartTooltip content={<ChartTooltipContent />} />
    {/* STATIC — never conditionally mount/unmount <Line> */}
    <Line dataKey="score"           stroke="hsl(var(--quantum-safe))" strokeWidth={2.5} dot={{ r: 3 }} />
    <Line dataKey="hygiene"         stroke="hsl(180 37% 47%)"         strokeWidth={1.5} dot={{ r: 2 }} strokeOpacity={0.85} />
    <Line dataKey="modern_tls"      stroke="hsl(213 94% 68%)"         strokeWidth={1.5} dot={{ r: 2 }} strokeOpacity={0.85} />
    <Line dataKey="identity_trust"  stroke="hsl(38 92% 50%)"          strokeWidth={1.5} dot={{ r: 2 }} strokeOpacity={0.85} />
    <Line dataKey="agility_signals" stroke="hsl(28 64% 52%)"          strokeWidth={1.5} dot={{ r: 2 }} strokeOpacity={0.85} />
    <Line dataKey="data_at_rest"    stroke="hsl(270 50% 60%)"         strokeWidth={1.5} dot={{ r: 2 }} strokeOpacity={0.85} />
    <Line dataKey="data_in_motion"  stroke="hsl(152 47% 45%)"         strokeWidth={1.5} dot={{ r: 2 }} strokeOpacity={0.85} />
  </LineChart>
</ChartContainer>
```

**Empty state guard** (mirror existing `!data.previous_session_ts` early return in trends.tsx, lines 96–105):
```typescript
// Existing guard (keep)
if (!data.previous_session_ts) {
  return (
    <div className="space-y-4 py-8">
      <h1 ...>Trends</h1>
      <p ...>No scan history yet. Run two or more scans to see trend lines.</p>
    </div>
  )
}
// Add timeline guard above the main return — only show chart if >= 2 sessions
const showChart = timelineData && timelineData.sessions.length >= 2
```

**Loading state** (line 82):
```tsx
if (loading) return <PageSpinner ariaLabel="Loading trends" />
```
Add a second spinner or inline skeleton for the timeline section when `timelineLoading` is true.

---

### `src/dashboard/src/pages/executive.tsx` — insert `<RegressionAlertChip />` above score gauge

**Analog:** `src/dashboard/src/pages/executive.tsx` (self — insertion point at line 128)

**Insertion point** — the `{/* Score gauges row */}` `<Card>` starts at line 128. Insert `<RegressionAlertChip />` directly above it:
```tsx
return (
  <div className="space-y-8">
    {/* Header row */}
    <div className="flex items-center justify-between">
      ...
    </div>

    {/* REGRESSION ALERT — new Phase 64 insertion */}
    <RegressionAlertChip />

    {/* Score gauges row */}
    <Card>
      <CardContent className="pt-6">
        ...
      </CardContent>
    </Card>
    ...
  </div>
)
```

**Import to add:**
```typescript
import { RegressionAlertChip } from "@/components/RegressionAlertChip"
```

No other changes to `executive.tsx`.

---

### `tests/test_dashboard_trends.py` — 5 new Wave 0 test functions

**Analog:** `tests/test_dashboard_trends.py` (self — existing `test_uat_31_trends_two_sessions_flat_wire_format`, lines 98–164)

**`dashboard_client` fixture pattern** (from `conftest.py`, lines 76–112):
```python
@pytest.fixture
def dashboard_client():
    # In-memory SQLite, shared cache, Base.metadata.create_all
    # Overrides get_db dependency
    # Returns TestClient(app, headers={"X-Quirk-Request": "1"})
```
The `dashboard_client` fixture starts with an empty DB — use it directly for empty-state and validation tests. For seeded tests, use the named-cache UUID pattern from `test_uat_31_trends_two_sessions_flat_wire_format` (lines 73–95).

**Basic endpoint test pattern** (lines 12–33):
```python
def test_trends_endpoint_schema(dashboard_client):
    resp = dashboard_client.get("/api/trends")
    assert resp.status_code == 200
    data = resp.json()
    assert "current_session_ts" in data
    ...
```

**Five new tests to add** (Wave 0 — written before the route exists, RED until Plan 01 completes):

```python
# ---- Wave 0: GET /api/trends/timeline (TREND-01) ----

def test_trends_timeline_endpoint(dashboard_client):
    """TREND-01: GET /api/trends/timeline returns HTTP 200."""
    resp = dashboard_client.get("/api/trends/timeline")
    assert resp.status_code == 200
    data = resp.json()
    assert "sessions" in data
    assert isinstance(data["sessions"], list)


def test_trends_timeline_schema(dashboard_client):
    """TREND-01: timeline response has correct per-session shape."""
    # Uses named-cache UUID pattern to seed two sessions (same as UAT-31)
    # Each session item must have: session_ts, score, subscores, finding_counts
    ...  # full seeding + assertion body added in plan


def test_trends_timeline_n_param(dashboard_client):
    """TREND-01: ?n=5 returns at most 5 sessions."""
    resp = dashboard_client.get("/api/trends/timeline?n=5")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["sessions"]) <= 5


def test_trends_timeline_n_validation(dashboard_client):
    """TREND-01: ?n=1 returns 422 (ge=2 Pydantic constraint)."""
    resp = dashboard_client.get("/api/trends/timeline?n=1")
    assert resp.status_code == 422


def test_trends_timeline_empty(dashboard_client):
    """TREND-01: empty DB returns {"sessions": []} with HTTP 200."""
    resp = dashboard_client.get("/api/trends/timeline")
    assert resp.status_code == 200
    data = resp.json()
    assert data["sessions"] == []
```

**Seeded-DB helper pattern** (lines 73–95 of existing test file — replicate for `test_trends_timeline_schema`):
```python
import uuid as _uuid_trend64
from datetime import datetime as _dt_trend64
from sqlalchemy import create_engine as _create_engine_trend64
from sqlalchemy.orm import sessionmaker as _sessionmaker_trend64
from fastapi.testclient import TestClient as _TestClient_trend64

def _make_trend64_client_and_session():
    from quirk.dashboard.api.app import create_app
    from quirk.dashboard.api.deps import get_db
    from quirk.models import Base

    db_name = f"test_trend64_{_uuid_trend64.uuid4().hex}"
    engine = _create_engine_trend64(
        f"sqlite:///file:{db_name}?mode=memory&cache=shared&uri=true",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    TestingSession = _sessionmaker_trend64(bind=engine, autoflush=False, autocommit=False)

    def _override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[get_db] = _override_get_db
    return _TestClient_trend64(app, headers={"X-Quirk-Request": "1"}), TestingSession
```

---

## Shared Patterns

### Authentication
**Source:** `quirk/dashboard/api/routes/trends.py` line 30
**Apply to:** `GET /api/trends/timeline` (and all future routes on this router)
```python
router = APIRouter(dependencies=[Depends(require_auth)])
```
All routes registered on this router inherit auth automatically. No per-route annotation needed.

### Session Grouping (NULL exclusion)
**Source:** `quirk/dashboard/api/routes/trends.py` lines 38–50
**Apply to:** `_list_session_timestamps_n`
```python
.filter(CryptoEndpoint.scanned_at.isnot(None))
.group_by("ts_sec")
.order_by(ts_sec.desc())
```
Never omit `isnot(None)`. v4.2-era endpoints may have NULL `scanned_at` and corrupt session grouping.

### Severity Bucketing
**Source:** `quirk/intelligence/trends.py` lines 33–39, 107–118
**Apply to:** finding counts in the timeline loop
```python
_SEVERITY_BUCKET = {
    "CRITICAL": "high",
    "HIGH": "high",
    "MEDIUM": "medium",
    "LOW": "low",
    # INFO intentionally absent — excluded from counts
}
def _count_by_bucket(keys: Iterable[tuple]) -> dict:
    counts: dict = {"high": 0, "medium": 0, "low": 0}
    for _host, _port, _protocol, severity in keys:
        bucket = _bucket_for_severity(severity)
        if bucket is not None:
            counts[bucket] += 1
    return counts
```

### Cancellation-Safe Hook
**Source:** `src/dashboard/src/hooks/useTrendsData.ts` lines 16–62
**Apply to:** `useTimelineData.ts`
```typescript
useEffect(() => {
  let cancelled = false
  async function fetchData() {
    ...
    if (!cancelled) setData(json)
    ...
    if (!cancelled) setLoading(false)
  }
  fetchData()
  return () => { cancelled = true }
}, [])
```

### Recharts Static Children Rule
**Source:** Project feedback constraint (feedback_recharts_static_children.md)
**Apply to:** All `<LineChart>` / `<BarChart>` / `<RadarChart>` usages
Never use `{condition && <Line ... />}`. All child series must always be mounted. Use `strokeOpacity={0}` or `fillOpacity={0}` to suppress visually.

### PageSpinner Loading State
**Source:** `src/dashboard/src/pages/executive.tsx` line 62; `src/dashboard/src/pages/trends.tsx` line 82
**Apply to:** `TrendsPage` timeline section, `RegressionAlertChip` (returns null during loading)
```tsx
import { PageSpinner } from "@/components/PageSpinner"
if (loading) return <PageSpinner ariaLabel="Loading ..." />
```

### Pydantic `BaseModel` with defaults
**Source:** `quirk/dashboard/api/schemas.py` lines 221–237
**Apply to:** `FindingCounts`, `TrendSessionPoint`, `TrendTimelineResponse`
Use `int = 0` for count fields and `List[...] = []` for list fields so empty-DB responses serialize correctly without None values.

### Test: Named-Cache UUID Pattern
**Source:** `tests/test_dashboard_trends.py` lines 73–95
**Apply to:** `test_trends_timeline_schema` (any test needing a seeded DB)
Use `f"sqlite:///file:{db_name}?mode=memory&cache=shared&uri=true"` with a unique `uuid4().hex` prefix per test function to avoid cross-test DB pollution.

### Test: CSRF Header
**Source:** `tests/conftest.py` line 110
**Apply to:** All `TestClient` instantiations in new tests
```python
TestClient(app, headers={"X-Quirk-Request": "1"})
```

---

## No Analog Found

None — all 8 files have verified analogs in the codebase.

---

## Metadata

**Analog search scope:** `quirk/dashboard/api/`, `quirk/intelligence/`, `src/dashboard/src/hooks/`, `src/dashboard/src/pages/`, `src/dashboard/src/components/`, `src/dashboard/src/types/`, `tests/`
**Files scanned:** 10 source files read directly
**Pattern extraction date:** 2026-05-10
