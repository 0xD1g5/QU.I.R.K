# Phase 64: Trend Analysis Foundation - Research

**Researched:** 2026-05-10
**Domain:** FastAPI timeline endpoint + Recharts LineChart multi-series + localStorage regression alerts
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Add `GET /api/trends/timeline?n=30` as a new endpoint alongside the existing `GET /api/trends`. The existing endpoint is kept unchanged.
- **D-02:** Timeline endpoint returns `TrendTimelineResponse` with a `sessions` array (newest-first, max N). Each item: `session_ts` (ISO string), `score` (int), `subscores` (all 6 keys), `finding_counts` ({high, medium, low}).
- **D-03:** Session enumeration reuses `_list_session_timestamps()` pattern with `LIMIT n` (default 30, max 200). `n` validated by Pydantic `Query(default=30, ge=2, le=200)`.
- **D-04:** Compute subscores inline per session — `build_evidence_summary(endpoints)` then `compute_readiness_score(evidence)` for each session. No caching. ~1.5s max acceptable.
- **D-05:** Finding counts per session: count `CryptoEndpoint` rows bucketed by severity using the existing `_SEVERITY_BUCKET` map. Do NOT call `compute_trend_report()`.
- **D-06:** Subscore keys in response use internal scoring.py names: `hygiene`, `modern_tls`, `identity_trust`, `agility_signals`, `data_at_rest`, `data_in_motion`.
- **D-07:** Regression detection reuses existing `GET /api/trends` response. Condition: `score_delta !== null && score_delta <= -5` OR `new_high > 0`. `RegressionAlertChip` reads existing `useTrendsData()`.
- **D-08:** Dismissal stored in `localStorage` under key `quirk.dismissed_regression.<session_ts>`. Per-session, not global. No DB table.
- **D-09:** Chip renders on `ExecutivePage`, inserted above the score gauge section. Click "×" writes to localStorage and hides chip without page reload. Contains deep-link anchor to `/trends`.
- **D-10:** Use Recharts `LineChart` (not `AreaChart`) with 7 `<Line>` series. Wrap in `<ChartContainer>`. Never conditionally mount/unmount `<Line>` components — use `strokeOpacity={0}` for toggling.
- **D-11:** `<XAxis dataKey="session_ts" />` formatted as `MM/DD HH:mm`. `<YAxis domain={[0, 100]} />`. Custom `<Tooltip>` shows full `session_ts` as `toLocaleString()` plus all 7 score values.
- **D-12:** `useTimelineData` hook: cancellation-safe (`let cancelled = false` inside `useEffect`). Located at `src/dashboard/src/hooks/useTimelineData.ts`.

### Claude's Discretion

- Line colors: `hsl(var(--quantum-safe))` for overall score; existing CSS variable palette for subscores.
- Loading state: reuse `<PageSpinner>` from `src/dashboard/src/components/PageSpinner.tsx`.
- Empty state (< 2 sessions): keep existing "Run two or more scans" message; do not show partial chart.
- The `TrendsPage` keeps the existing score-delta card and new/resolved finding tables below the chart.

### Deferred Ideas (OUT OF SCOPE)

- Per-line visibility toggle checkbox list
- Configurable regression threshold UI control
- Trend correlation with `scheduled_runs.scan_id`
- Exported trend report (CSV/PDF)
- Sub-pillar drilldown on timeline point click
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| TREND-01 | Dashboard `/trends` route renders a multi-scan timeline of overall readiness score, per-pillar subscores, and finding counts across the last N scans (default 30) | New `GET /api/trends/timeline` endpoint + `useTimelineData` hook + Recharts `LineChart` with 7 series |
| TREND-02 | Trend regressions surfaced as alert chips on dashboard home with deep-links to the regressing scan | `RegressionAlertChip` on `ExecutivePage` reading existing `useTrendsData()` data; localStorage dismissal per-session |
</phase_requirements>

---

## Summary

Phase 64 upgrades the existing pairwise trend view into a full multi-scan timeline. The backend work is a targeted extension to `quirk/dashboard/api/routes/trends.py` — a new `GET /api/trends/timeline` endpoint that loops over up to N session timestamps, computes scores and subscores inline via existing intelligence functions, and returns a flat array. The existing `GET /api/trends` endpoint is untouched; it continues to drive the regression-detection chip on the executive page.

The frontend work has two parts: (1) a new `useTimelineData` hook and Recharts `LineChart` with 7 series added to `TrendsPage`, and (2) a new `RegressionAlertChip` component inserted above the score gauge on `ExecutivePage`. The chip reads the already-fetched `useTrendsData()` result — no new API call required for TREND-02.

All key patterns (session grouping, severity bucketing, cancellation-safe hooks, `ChartContainer` wrapper, Recharts static children rule) are already established in the codebase. The phase is primarily wiring work with no new dependencies.

**Primary recommendation:** Implement in three sequential tasks — (1) backend schema + endpoint, (2) `useTimelineData` hook + `TrendsPage` chart, (3) `RegressionAlertChip` + `ExecutivePage` insertion. Each task has a clear integration seam and can be independently tested.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Timeline data aggregation | API / Backend | — | Session enumeration, scoring, and bucketing are CPU-bound Python operations on DB data; never in browser |
| Regression detection | API / Backend | — | Existing `/api/trends` already computes score_delta and new_high; frontend just reads the result |
| Timeline visualization | Browser / Client | — | Recharts LineChart with static data; no SSR needed |
| Regression dismissal state | Browser / Client | — | localStorage is explicit decision (D-08); per-user, per-session, no server sync |
| Subscore computation | API / Backend | — | `compute_readiness_score()` is a pure Python function; called per session in the handler |

---

## Standard Stack

### Core (all already installed — no new deps)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | existing | Backend endpoint + Pydantic schema | Project standard [VERIFIED: app.py] |
| Pydantic v2 | existing | `TrendTimelineResponse`, `TrendSessionPoint` schemas | Project standard [VERIFIED: schemas.py] |
| SQLAlchemy | existing | Session enumeration queries | Project standard [VERIFIED: routes/trends.py] |
| recharts | ^2.15.4 | `LineChart` with 7 `<Line>` series | Already installed [VERIFIED: src/dashboard/package.json] |
| lucide-react | ^0.474.0 | `AlertTriangle` icon for RegressionAlertChip | Already installed [VERIFIED: src/dashboard/package.json] |
| react-router-dom | existing | `<Link to="/trends">` in chip | Already installed [VERIFIED: App.tsx] |

### No new npm or pip packages required for this phase.

**Installation:** None needed.

---

## Architecture Patterns

### System Architecture Diagram

```
Browser                         FastAPI Backend                        SQLite DB
  │                                    │                                    │
  │  GET /api/trends/timeline?n=30     │                                    │
  │ ─────────────────────────────────► │                                    │
  │                                    │  _list_session_timestamps(n)       │
  │                                    │ ──────────────────────────────────►│
  │                                    │ ◄────────────────── [ts1,ts2,...] ─│
  │                                    │                                    │
  │                                    │  for each ts:                      │
  │                                    │    _fetch_session_endpoints(ts)   │
  │                                    │ ──────────────────────────────────►│
  │                                    │ ◄──────── [CryptoEndpoint rows] ───│
  │                                    │    build_evidence_summary(eps)     │
  │                                    │    compute_readiness_score(ev)     │
  │                                    │    _count_by_bucket(eps)          │
  │                                    │                                    │
  │ ◄── TrendTimelineResponse ─────────│                                    │
  │   { sessions: [{session_ts,        │                                    │
  │     score, subscores,              │                                    │
  │     finding_counts}, ...] }        │                                    │
  │                                    │                                    │
  │  (separately)                      │                                    │
  │  GET /api/trends                   │                                    │
  │ ─────────────────────────────────► │  compute_trend_report(curr,prev)   │
  │ ◄── TrendReportResponse ───────────│                                    │
  │   { score_delta, new_high, ... }   │                                    │
  │                                    │                                    │
  │  useTimelineData → TrendsPage      │                                    │
  │  LineChart [7 Line series]         │                                    │
  │                                    │                                    │
  │  useTrendsData → ExecutivePage     │                                    │
  │  RegressionAlertChip               │                                    │
  │  (dismissal → localStorage)        │                                    │
```

### Recommended Project Structure

No new directories. New files only:

```
quirk/dashboard/api/
└── routes/trends.py          ← add @router.get("/trends/timeline") here

quirk/dashboard/api/
└── schemas.py                ← add TrendSessionPoint, TrendTimelineResponse

src/dashboard/src/
├── hooks/
│   └── useTimelineData.ts    ← new hook (cancellation-safe)
├── components/
│   └── RegressionAlertChip.tsx  ← new component
└── types/
    └── api.ts                ← add TrendSessionPoint, TrendTimeline interfaces
```

Modified files:
- `src/dashboard/src/pages/trends.tsx` — add LineChart section above existing delta cards
- `src/dashboard/src/pages/executive.tsx` — insert `<RegressionAlertChip />` above score gauge Card

### Pattern 1: New Timeline Endpoint

**What:** Add `@router.get("/trends/timeline")` to the existing router in `routes/trends.py`. Reuses the established session-grouping pattern with a parameterized LIMIT.

**When to use:** Any new time-series endpoint that iterates sessions.

```python
# Source: quirk/dashboard/api/routes/trends.py (extension pattern)
from fastapi import Query
from quirk.dashboard.api.schemas import TrendTimelineResponse, TrendSessionPoint

@router.get("/trends/timeline", response_model=TrendTimelineResponse)
def get_trends_timeline(
    n: int = Query(default=30, ge=2, le=200),
    db: Session = Depends(get_db),
) -> TrendTimelineResponse:
    sessions = _list_session_timestamps_n(db, n)
    points = []
    for ts in sessions:
        eps = _fetch_session_endpoints(db, ts)
        if not eps:
            continue
        evidence = build_evidence_summary(eps)
        score_dict = compute_readiness_score(evidence)
        sub = score_dict["subscores"]
        # count by bucket using existing _count_by_bucket
        keys = [(ep.host, ep.port, ep.protocol, ep.severity)
                for ep in eps if ep.scan_error is None]
        counts = _count_by_bucket(keys)
        points.append(TrendSessionPoint(
            session_ts=ts.isoformat(),
            score=score_dict["score"],
            subscores=sub,
            finding_counts=counts,
        ))
    return TrendTimelineResponse(sessions=points)
```

**Key detail:** Import `build_evidence_summary` and `compute_readiness_score` in routes/trends.py — they are already imported in `quirk/intelligence/trends.py` but not yet in the route file. `_fetch_session_endpoints` and `_count_by_bucket` are defined in trends.py (the intelligence module) so they need to be imported or re-referenced.

**IMPORTANT — import boundary:** `_fetch_session_endpoints` and `_count_by_bucket` are module-private (`_` prefix) in `quirk/intelligence/trends.py`. The simplest approach is to import them directly; alternatively, define a thin public helper in trends.py. Either approach is acceptable — pick the one that avoids code duplication.

### Pattern 2: `_list_session_timestamps_n` — Parameterized LIMIT

**What:** Variant of the existing `_list_session_timestamps()` that accepts `n` instead of hardcoding `LIMIT 10`.

```python
# Source: quirk/dashboard/api/routes/trends.py (extension)
def _list_session_timestamps_n(db: Session, n: int) -> List[datetime]:
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

**Note:** The existing `_list_session_timestamps()` hardcodes `LIMIT 10`. Do NOT modify it — the existing `get_trends` route calls it. Add a new `_list_session_timestamps_n(db, n)` function alongside it.

### Pattern 3: Pydantic Schemas

```python
# Source: quirk/dashboard/api/schemas.py (new additions)
class FindingCounts(BaseModel):
    high: int = 0
    medium: int = 0
    low: int = 0

class TrendSessionPoint(BaseModel):
    session_ts: str  # ISO 8601 string
    score: int
    subscores: SubScores  # reuses existing SubScores model
    finding_counts: FindingCounts

class TrendTimelineResponse(BaseModel):
    sessions: List[TrendSessionPoint] = []
```

**Note:** `SubScores` is already defined in `schemas.py` with all 6 keys. Reuse it directly — do not define a duplicate.

### Pattern 4: TypeScript Types

```typescript
// Source: src/dashboard/src/types/api.ts (additions)
export interface TrendFindingCounts {
  high: number
  medium: number
  low: number
}

export interface TrendSessionPoint {
  session_ts: string
  score: number
  subscores: SubScores  // reuse existing SubScores interface
  finding_counts: TrendFindingCounts
}

export interface TrendTimeline {
  sessions: TrendSessionPoint[]
}
```

### Pattern 5: `useTimelineData` Hook (cancellation-safe)

```typescript
// Source: src/dashboard/src/hooks/useTrendsData.ts (template)
// Location: src/dashboard/src/hooks/useTimelineData.ts
import { useState, useEffect } from "react"
import type { TrendTimeline } from "@/types/api"
import { fetchApi } from "@/lib/api"

export function useTimelineData(): {
  data: TrendTimeline | null
  loading: boolean
  error: string | null
} {
  const [data, setData] = useState<TrendTimeline | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    async function fetchData() {
      try {
        setLoading(true)
        setError(null)
        const resp = await fetchApi("/api/trends/timeline?n=30")
        if (!resp.ok) {
          if (!cancelled) {
            if (resp.status === 401) { setError("Authentication required"); return }
            if (resp.status === 403) { setError("Request blocked"); return }
            if (resp.status === 429) {
              const retry = resp.headers.get("Retry-After") ?? "60"
              setError(`Too many requests. Wait ${retry} seconds and try again.`)
              return
            }
            setError(`API error: ${resp.status} ${resp.statusText}`)
          }
          return
        }
        const json: TrendTimeline = await resp.json()
        if (!cancelled) setData(json)
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load timeline")
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    fetchData()
    return () => { cancelled = true }
  }, [])

  return { data, loading, error }
}
```

### Pattern 6: Recharts LineChart with 7 Static Lines

**Critical rule:** Never conditionally mount/unmount `<Line>` components. All 7 must always be present in JSX. Use `strokeOpacity` to visually suppress if needed.

```tsx
// Source: src/dashboard/src/components/ui/chart.tsx + executive.tsx (recharts usage)
const TIMELINE_CHART_CONFIG = {
  score:         { label: "Overall",       color: "hsl(var(--quantum-safe))" },
  hygiene:       { label: "Hygiene",       color: "hsl(180 37% 47%)" },
  modern_tls:    { label: "TLS",           color: "hsl(213 94% 68%)" },
  identity_trust:{ label: "Identity",      color: "hsl(38 92% 50%)" },
  agility_signals:{ label: "Agility",      color: "hsl(28 64% 52%)" },
  data_at_rest:  { label: "Data at Rest",  color: "hsl(270 50% 60%)" },
  data_in_motion:{ label: "Data in Motion", color: "hsl(152 47% 45%)" },
}

// Inside TrendsPage (chart section):
<ChartContainer config={TIMELINE_CHART_CONFIG}>
  <LineChart data={flattenedData} margin={{ top: 4, right: 16, left: 0, bottom: 4 }}>
    <XAxis dataKey="session_ts"
      tickFormatter={(v) => new Date(v).toLocaleString([], {
        month: "2-digit", day: "2-digit",
        hour: "2-digit", minute: "2-digit"
      })} />
    <YAxis domain={[0, 100]} tickCount={6} />
    <ChartTooltip content={<CustomTimelineTooltip />} />
    {/* All 7 Lines ALWAYS mounted — static children rule */}
    <Line dataKey="score"          stroke="hsl(var(--quantum-safe))"  strokeWidth={2.5} dot={{ r: 3 }} />
    <Line dataKey="hygiene"        stroke="hsl(180 37% 47%)"          strokeWidth={1.5} dot={{ r: 2 }} strokeOpacity={0.85} />
    <Line dataKey="modern_tls"     stroke="hsl(213 94% 68%)"          strokeWidth={1.5} dot={{ r: 2 }} strokeOpacity={0.85} />
    <Line dataKey="identity_trust" stroke="hsl(38 92% 50%)"           strokeWidth={1.5} dot={{ r: 2 }} strokeOpacity={0.85} />
    <Line dataKey="agility_signals" stroke="hsl(28 64% 52%)"          strokeWidth={1.5} dot={{ r: 2 }} strokeOpacity={0.85} />
    <Line dataKey="data_at_rest"   stroke="hsl(270 50% 60%)"          strokeWidth={1.5} dot={{ r: 2 }} strokeOpacity={0.85} />
    <Line dataKey="data_in_motion" stroke="hsl(152 47% 45%)"          strokeWidth={1.5} dot={{ r: 2 }} strokeOpacity={0.85} />
  </LineChart>
</ChartContainer>
```

**Data shape for Recharts:** Recharts `LineChart` expects each data row to have a flat object with one key per dataKey. Since the API returns `{ sessions: [{ session_ts, score, subscores: {...}, finding_counts }] }`, you must flatten each session before passing to `<LineChart data={...}>`:

```typescript
// Flatten sessions array for Recharts (inside TrendsPage)
const chartData = data.sessions.map(s => ({
  session_ts: s.session_ts,
  score: s.score,
  hygiene: s.subscores.hygiene,
  modern_tls: s.subscores.modern_tls,
  identity_trust: s.subscores.identity_trust,
  agility_signals: s.subscores.agility_signals,
  data_at_rest: s.subscores.data_at_rest,
  data_in_motion: s.subscores.data_in_motion,
}))
// Reverse: API returns newest-first, chart should display oldest-first (left→right)
const chartDataAsc = [...chartData].reverse()
```

**Important — sort direction:** The API returns sessions newest-first (D-02). Recharts renders data left→right, so the chart should receive sessions oldest-first. Always reverse before passing to `<LineChart>`.

### Pattern 7: `RegressionAlertChip`

```tsx
// Source: 64-UI-SPEC.md + CONTEXT.md D-07/D-08/D-09
// Location: src/dashboard/src/components/RegressionAlertChip.tsx
import { useState } from "react"
import { AlertTriangle } from "lucide-react"
import { Link } from "react-router-dom"
import { useTrendsData } from "@/hooks/useTrendsData"

export function RegressionAlertChip() {
  const { data, loading } = useTrendsData()

  const sessionTs = data?.current_session_ts ?? null
  const dismissed = sessionTs
    ? !!localStorage.getItem(`quirk.dismissed_regression.${sessionTs}`)
    : false
  const [isDismissed, setIsDismissed] = useState(dismissed)

  if (loading || !data || isDismissed) return null

  const isRegression =
    (data.score_delta !== null && data.score_delta <= -5) || data.new_high > 0
  if (!isRegression) return null

  function handleDismiss() {
    if (sessionTs) localStorage.setItem(`quirk.dismissed_regression.${sessionTs}`, "1")
    setIsDismissed(true)
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

**Note on `useTrendsData` in two places:** Both `ExecutivePage` (existing) and `RegressionAlertChip` (new) call `useTrendsData()`. React's `useState`/`useEffect` will issue two separate fetches unless the hook is lifted to a shared context. For this phase, two separate fetches is acceptable — the data is small (~200 bytes) and is fetched once on page load. This avoids the complexity of a shared context provider.

### Anti-Patterns to Avoid

- **Conditionally mounting `<Line>` components:** Never use `{condition && <Line ... />}`. Recharts re-renders the entire chart on mount/unmount of child components. Use `strokeOpacity={0}` instead.
- **Modifying the existing `_list_session_timestamps()` function:** It is hardcoded to `LIMIT 10` and consumed by `get_trends`. Add a new `_list_session_timestamps_n()` alongside it — do not change the existing function signature.
- **Calling `compute_trend_report()` in the timeline loop:** The timeline only needs score + subscores + raw severity counts. `compute_trend_report()` does pairwise diff logic (new/resolved sets) which is expensive and unnecessary. Use `_score_for_session()` (already private to trends.py) pattern + `_count_by_bucket()` directly.
- **Passing `sessions` directly (nested) to Recharts:** The API returns `subscores` as a nested object. Recharts cannot traverse nested keys for `dataKey`. Always flatten to a single-level object before passing to `<LineChart data={...}>`.
- **Forgetting to reverse the sessions array:** API returns newest-first; chart should render oldest-left to newest-right. Reverse before passing to Recharts.
- **Double-rendering `useTrendsData` via context conflict:** Both `ExecutivePage` and `RegressionAlertChip` will call `useTrendsData()`. This is fine — two small fetches. Do not attempt a shared provider without explicit requirement.
- **Importing from trends.py private helpers without acknowledging the boundary:** `_fetch_session_endpoints`, `_count_by_bucket`, `_bucket_for_severity` are module-private. Either import them directly (acceptable for same-package usage) or expose thin public wrappers.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Recharts theming/CSS variables | Custom CSS injector | `ChartContainer` from `chart.tsx` | Already handles light/dark mode, `text-xs` axis styles, `aspect-video` layout [VERIFIED: chart.tsx] |
| Session enumeration | Custom datetime grouping | `func.strftime("%Y-%m-%d %H:%M:%S", ...)` group-by pattern | Already handles microsecond-precision timestamps from scan.py [VERIFIED: routes/trends.py] |
| Subscore computation | Custom score formula | `build_evidence_summary()` + `compute_readiness_score()` | Handles all 6 pillars, profile multiplier, weighting [VERIFIED: scoring.py] |
| Severity bucketing | Custom severity mapper | `_SEVERITY_BUCKET` + `_count_by_bucket()` from trends.py | INFO exclusion, CRITICAL→high mapping already correct [VERIFIED: trends.py] |
| Cancellation-safe fetch | Manual AbortController | `let cancelled = false` pattern | Established project standard, simpler than AbortController [VERIFIED: useTrendsData.ts] |
| LocalStorage dismissal state | Server-side DB flag | `localStorage.setItem/getItem` | D-08 is explicit; per-user, per-session, no server sync needed |

**Key insight:** Every hard piece of this phase has a verified template. The phase is wiring work, not invention.

---

## Common Pitfalls

### Pitfall 1: Nested Subscore Keys Break Recharts

**What goes wrong:** `<Line dataKey="subscores.hygiene" />` — Recharts does not support dot-notation traversal for `dataKey` in `LineChart`. The line renders empty.

**Why it happens:** Recharts `dataKey` resolves against each element of the `data` array using simple property access, not lodash-style path resolution.

**How to avoid:** Flatten each session object before passing to `<LineChart data={flattenedData}>`. Map `s.subscores.hygiene` → `s.hygiene` etc. [VERIFIED: confirmed by reading recharts LineChart implementation pattern in executive.tsx which uses flat data objects]

**Warning signs:** Line renders but shows no dots or a flat line at 0.

### Pitfall 2: Sessions Newest-First Renders Chart Right-to-Left

**What goes wrong:** The API returns `sessions` newest-first (D-02). If passed directly to Recharts without reversing, the chart displays time running right-to-left — confusing for consultants.

**Why it happens:** Recharts renders data in array order, left to right.

**How to avoid:** `const chartDataAsc = [...chartData].reverse()` after flattening. Do not mutate the original array.

**Warning signs:** Most recent scan appears on the left side of the chart.

### Pitfall 3: `_list_session_timestamps()` Hardcodes LIMIT 10

**What goes wrong:** Calling the existing `_list_session_timestamps(db)` for the timeline endpoint silently caps at 10 sessions even when `n=30` is requested.

**Why it happens:** The existing function was written for pairwise comparison and only needs the two most recent sessions.

**How to avoid:** Add `_list_session_timestamps_n(db, n)` as a new private function. Do not modify the original.

**Warning signs:** Timeline always shows exactly 10 or fewer points regardless of `?n=` value.

### Pitfall 4: `RegressionAlertChip` Dismissal State Stale on Mount

**What goes wrong:** `useState(dismissed)` is computed once at mount time from `localStorage`. If the `data` is not yet loaded when the component mounts (loading state), `sessionTs` is `null`, `dismissed` is `false`, and `isDismissed` is initialized to `false`. When data arrives, the component re-renders but `useState` initial value is not re-evaluated.

**Why it happens:** `useState` initial value runs only once at mount.

**How to avoid:** Compute dismissal state during render from `data` (which re-renders when loaded), not from `useState` initial value. Use `useMemo` or an inline check:

```tsx
const isDismissed = sessionTs
  ? !!localStorage.getItem(`quirk.dismissed_regression.${sessionTs}`)
  : false
const [manuallyDismissed, setManuallyDismissed] = useState(false)

if (loading || !data || isDismissed || manuallyDismissed) return null
```

**Warning signs:** Chip never shows even after a regression is detected; or chip shows briefly then disappears on hot reload.

### Pitfall 5: Auth Dependency on New Route

**What goes wrong:** New `GET /api/trends/timeline` misses the `require_auth` dependency and is accessible without a valid token.

**Why it happens:** Forgetting to include auth when the new function is added to the router.

**How to avoid:** The `router = APIRouter(dependencies=[Depends(require_auth)])` in `routes/trends.py` applies to ALL routes registered on that router. No per-route annotation needed — just add `@router.get(...)` to the same router object. [VERIFIED: routes/trends.py line 30]

**Warning signs:** `test_api_auth.py` fails with an assertion that the endpoint returns 200 without a token.

### Pitfall 6: `build_evidence_summary` / `compute_readiness_score` Import in Route File

**What goes wrong:** These functions are imported in `quirk/intelligence/trends.py` but NOT in `quirk/dashboard/api/routes/trends.py`. Calling them from the route handler without importing causes `NameError`.

**Why it happens:** The route file currently only imports `compute_trend_report` from the intelligence layer.

**How to avoid:** Add explicit imports to `routes/trends.py`:
```python
from quirk.intelligence.evidence import build_evidence_summary
from quirk.intelligence.scoring import compute_readiness_score
from quirk.intelligence.trends import (
    _fetch_session_endpoints,
    _count_by_bucket,
)
```

---

## Code Examples

### Flattening Sessions for Recharts (verified data transform pattern)

```typescript
// All 7 keys must be at the top level of each object
const chartDataAsc = [...(data?.sessions ?? [])]
  .reverse()   // API: newest-first → chart: oldest-left
  .map(s => ({
    session_ts:      s.session_ts,
    score:           s.score,
    hygiene:         s.subscores.hygiene,
    modern_tls:      s.subscores.modern_tls,
    identity_trust:  s.subscores.identity_trust,
    agility_signals: s.subscores.agility_signals,
    data_at_rest:    s.subscores.data_at_rest,
    data_in_motion:  s.subscores.data_in_motion,
  }))
```

### XAxis Tick Formatter (from UI-SPEC)

```typescript
// Source: 64-UI-SPEC.md
tickFormatter={(v: string) =>
  new Date(v).toLocaleString([], {
    month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit",
  })
}
```

### Empty State Guard (< 2 sessions)

```typescript
// Inside TrendsPage, before rendering chart section:
if (!timelineData || timelineData.sessions.length < 2) {
  // fall through to existing "Run two or more scans" message
  // do not render a partial chart
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Pairwise trend only | Multi-scan timeline (up to N=200) | Phase 64 | Consultants see posture evolution, not just last delta |
| No regression notification | Alert chip on ExecutivePage | Phase 64 | Operators alerted on regression without navigating to /trends |

**Deprecated/outdated:**
- None — no existing Phase 64 code to deprecate. The existing pairwise `/api/trends` is kept and supplemented.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `_fetch_session_endpoints` and `_count_by_bucket` can be imported directly from `quirk.intelligence.trends` by the route handler despite `_` prefix | Architecture Patterns, Pitfall 6 | Low — Python name mangling does not apply to module-level functions, only class attributes. Direct import always works. |
| A2 | Two separate `useTrendsData()` calls (one in ExecutivePage, one in RegressionAlertChip) will not cause visible performance issues | Pattern 7 | Low — the trends endpoint is fast (pairwise only, no loop) and the data is small. Two fetches fire simultaneously; both resolve quickly. |

**All other claims in this research were verified by reading the actual source files.**

---

## Open Questions

1. **`_score_for_session` accessibility**
   - What we know: `_score_for_session()` is a private helper in `quirk/intelligence/trends.py` that calls `build_evidence_summary()` + `compute_readiness_score()` and returns just the score int.
   - What's unclear: Should the route handler import and call `_score_for_session()` (simpler — one call returns the score), or import `build_evidence_summary` + `compute_readiness_score` directly (more explicit, also gets subscores)?
   - Recommendation: Call `build_evidence_summary()` + `compute_readiness_score()` directly in the route handler. `_score_for_session` only returns the overall score int and discards subscores — we need the full dict for the timeline endpoint. Do not call it.

---

## Environment Availability

Step 2.6: No new external dependencies. All tools required (Python, FastAPI, SQLAlchemy, recharts, lucide-react, react-router-dom) are already installed and verified in the project.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11+ | Backend endpoint | ✓ | 3.14.4 | — |
| recharts | LineChart | ✓ | ^2.15.4 | — |
| lucide-react | AlertTriangle icon | ✓ | ^0.474.0 | — |
| react-router-dom | `<Link to="/trends">` | ✓ | existing | — |
| pytest | Backend tests | ✓ | existing | — |
| npm run build | Frontend changes visible | ✓ | 11.12.1 | — |

**Missing dependencies:** None.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (Python backend) |
| Config file | pytest.ini or pyproject.toml (existing) |
| Quick run command | `python -m pytest tests/test_dashboard_trends.py tests/test_intelligence_trends.py -x -q` |
| Full suite command | `python -m pytest tests/ -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TREND-01 | `GET /api/trends/timeline?n=30` returns 200 with `sessions` array | integration | `python -m pytest tests/test_dashboard_trends.py::test_trends_timeline_endpoint -x` | ❌ Wave 0 |
| TREND-01 | Sessions array has correct shape (session_ts, score, subscores, finding_counts) | integration | `python -m pytest tests/test_dashboard_trends.py::test_trends_timeline_schema -x` | ❌ Wave 0 |
| TREND-01 | `?n=5` returns at most 5 sessions | integration | `python -m pytest tests/test_dashboard_trends.py::test_trends_timeline_n_param -x` | ❌ Wave 0 |
| TREND-01 | `?n=1` returns 422 (ge=2 validation) | integration | `python -m pytest tests/test_dashboard_trends.py::test_trends_timeline_n_validation -x` | ❌ Wave 0 |
| TREND-01 | Empty DB returns `{"sessions": []}` | integration | `python -m pytest tests/test_dashboard_trends.py::test_trends_timeline_empty -x` | ❌ Wave 0 |
| TREND-02 | Existing `GET /api/trends` still returns 200 (non-regression) | integration | `python -m pytest tests/test_dashboard_trends.py -x -q` | ✅ |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_dashboard_trends.py -x -q`
- **Per wave merge:** `python -m pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_dashboard_trends.py` — add 5 new test functions for the timeline endpoint (listed above)
- [ ] No new conftest needed — existing `dashboard_client` fixture and UUID-cache pattern from UAT-31 cover all needed patterns

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | `require_auth` via `router = APIRouter(dependencies=[Depends(require_auth)])` — inherited automatically by the new route |
| V3 Session Management | no | Stateless REST endpoint |
| V4 Access Control | no | Single-user dashboard; no role differentiation |
| V5 Input Validation | yes | Pydantic `Query(default=30, ge=2, le=200)` for `n` parameter |
| V6 Cryptography | no | No crypto operations in this phase |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| `n` parameter abuse (e.g., n=10000 to DoS DB) | DoS | Pydantic `le=200` hard cap; enforced at validation layer before query executes |
| localStorage XSS key injection | Tampering | Key is `quirk.dismissed_regression.<session_ts>` where session_ts is an ISO string from the API — no user-controlled input in the key |

---

## Project Constraints (from CLAUDE.md)

- Follow PEP 8 for all Python changes. [VERIFIED: CLAUDE.md]
- Keep diffs minimal — avoid unnecessary refactors.
- After changes, run `python -m compileall` and relevant tests.
- Dashboard `.tsx` edits need `npm run build` in `src/dashboard/` before they are visible; FastAPI serves pre-built statics. [VERIFIED: feedback_dashboard_build_required.md]
- Never conditionally mount/unmount `<Radar>/<Line>/<Bar>` inside a chart — use `fillOpacity`/`strokeOpacity` instead. [VERIFIED: CONTEXT.md canonical_refs]
- Mandatory phase completion steps (Obsidian note, UAT-SERIES.md update, sync, commit) required after verification passes.

---

## Sources

### Primary (HIGH confidence)
- `quirk/dashboard/api/routes/trends.py` — session enumeration pattern, auth dependency, router structure [VERIFIED: read file]
- `quirk/intelligence/trends.py` — `_fetch_session_endpoints`, `_bucket_for_severity`, `_count_by_bucket`, `_score_for_session` [VERIFIED: read file]
- `quirk/intelligence/scoring.py` — `compute_readiness_score()` return shape with `subscores` dict [VERIFIED: read file]
- `quirk/dashboard/api/schemas.py` — existing `SubScores`, `TrendReportResponse` models [VERIFIED: read file]
- `src/dashboard/src/hooks/useTrendsData.ts` — cancellation-safe hook template [VERIFIED: read file]
- `src/dashboard/src/pages/executive.tsx` — Recharts BarChart usage, insertion point for chip [VERIFIED: read file]
- `src/dashboard/src/pages/trends.tsx` — existing TrendsPage structure to extend [VERIFIED: read file]
- `src/dashboard/src/components/ui/chart.tsx` — ChartContainer, ChartTooltip, ChartTooltipContent [VERIFIED: read file]
- `src/dashboard/src/types/api.ts` — existing SubScores, TrendReport TypeScript interfaces [VERIFIED: read file]
- `src/dashboard/package.json` — recharts ^2.15.4, lucide-react ^0.474.0 [VERIFIED: read file]
- `.planning/phases/64-trend-analysis-foundation/64-CONTEXT.md` — all locked decisions [VERIFIED: read file]
- `.planning/phases/64-trend-analysis-foundation/64-UI-SPEC.md` — colors, spacing, copy, states matrix [VERIFIED: read file]
- `tests/test_dashboard_trends.py` — existing test patterns, dashboard_client fixture [VERIFIED: read file]
- `tests/conftest.py` — dashboard_client setup, UUID named-cache pattern [VERIFIED: read file]

### Secondary (MEDIUM confidence)
- Recharts LineChart flat data key requirement — confirmed by observing that executive.tsx uses flat data objects for BarChart and that the chart.tsx ChartContainer wraps ResponsiveContainer without any path-resolution middleware.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries verified in package.json and existing source files
- Architecture: HIGH — all integration points verified by reading actual source files
- Pitfalls: HIGH — derived from reading actual implementation, not from general knowledge

**Research date:** 2026-05-10
**Valid until:** 2026-06-10 (stable internal codebase; no external dependency changes anticipated)
