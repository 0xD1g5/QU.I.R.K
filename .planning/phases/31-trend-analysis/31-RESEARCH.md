# Phase 31: Trend Analysis - Research

**Researched:** 2026-04-26
**Domain:** Python intelligence layer (pure function), FastAPI endpoint, React dashboard page
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01** Match key for finding comparison: `(host, port, protocol, severity)` — exact column values from `CryptoEndpoint`.
**D-02** `host` used as-is; document caveat about IP-addressed targets in docstring.
**D-03** Severity included in match key — severity change surfaces as "OLD resolved + NEW new."
**D-04** `scan_error` endpoints (`scan_error IS NOT NULL`) excluded from finding delta.
**D-05** Scan error count delta surfaced separately: `scan_errors_new_count` / `scan_errors_resolved_count` (integers only, no host detail).
**D-06** Single-session: HTTP 200 with `score_delta: null`, all counts `0`, `previous_session_ts: null`, empty sample arrays.
**D-07** Full API response schema (see field list in CONTEXT.md §API Response Schema).
**D-08** `compute_trend_report(current_ts, previous_ts, db)` → `TrendReport` — pure function, receives DB session, calls `list_scans()` indirection lives in the route layer not the function.
**D-09** New `/trends` page follows exact established pattern: `pages/trends.tsx` + `Route` in `App.tsx` + `NAV_ITEMS` in `sidebar.tsx` with `TrendingUp` icon.
**D-10** Trends page layout: header row, score delta card, new/resolved finding cards, scan error row, two collapsible tables (top-5 samples).
**D-11** No new Python dependencies — pure SQLAlchemy + existing `compute_readiness_score()`.
**D-12** `compute_trend_report()` is a pure function — no `datetime.now()` inside; timestamps come from caller.
**D-13** NULL collision with v4.2-era sessions is expected — filter `scanned_at IS NULL` before grouping; document as behavior, not a bug.

### Claude's Discretion

- Exact Pydantic schema class name for the API response (e.g., `TrendReportResponse`)
- Whether `compute_trend_report()` returns a dataclass or a Pydantic model
- The exact lucide-react icon for the Trends nav entry (TrendingUp recommended)
- Whether the score delta badge uses a `+` prefix for positive deltas
- Exact wording of the "Baseline scan" empty state message on the Trends page

### Deferred Ideas (OUT OF SCOPE)

- Historical time-series charts (requires `trend_snapshots` table — v4.4 candidate)
- Full new/resolved finding lists with pagination
- Per-scanner-type trend breakdown (subscore history)
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| TREND-01 | Intelligence layer computes readiness score delta between current and most recent previous scan session using existing `scanned_at` grouping from `list_scans()` | `compute_readiness_score()` and `build_evidence_summary()` in `scoring.py`/`evidence.py` accept an endpoint list and return a score dict; session grouping via `func.strftime` confirmed in `scan.py:450` |
| TREND-02 | Trend report identifies net-new findings (present in current, absent in previous) with counts by severity | Set-difference on `(host, port, protocol, severity)` keys; severity already in `CryptoEndpoint.severity` column (populated in Phase 27+) |
| TREND-03 | Trend report identifies resolved findings (present in previous, absent in current) with counts by severity | Symmetric set-difference; same key tuple; severity filtering for HIGH/MEDIUM/LOW counts |
| TREND-04 | Dashboard surfaces trend data: score delta and new/resolved counts for two most recent sessions | `GET /api/trends` → `useTrendsData` hook → `/trends` page with score delta card + finding count cards |
</phase_requirements>

---

## Summary

Phase 31 adds a pure-Python intelligence function (`compute_trend_report()`), a single new FastAPI route (`GET /api/trends`), and a new React page (`/trends`) to surface session-over-session scan deltas. All three tiers are well-bounded: the intelligence function is stateless and has no external dependencies, the route is a thin orchestration layer that calls existing helpers, and the React page follows an already-established pattern.

The hardest technical decision was already locked in CONTEXT.md: using `(host, port, protocol, severity)` as the match key, excluding `scan_error` rows, and expressing the NULL collision with v4.2 sessions as expected behavior. None of these require net-new library research — they are implementation choices over existing infrastructure.

The only design work left open to Claude's discretion involves cosmetic naming (`TrendReportResponse` vs `TrendReport`) and two UI copy decisions. Existing codebase patterns answer every structural question.

**Primary recommendation:** Implement in three plans — RED scaffold (stub + failing tests), GREEN intelligence + API route, React Trends page + docs/UAT. This mirrors the TDD pattern used in Phases 28–30.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Session boundary resolution | API / Backend | — | `list_scans()` already lives in `scan.py`; the route layer calls it to derive the two session timestamps before passing them to the intelligence function |
| Finding delta computation | API / Backend (intelligence layer) | — | Pure Python set arithmetic over `CryptoEndpoint` rows; no browser involvement; `quirk/intelligence/trends.py` |
| Score per session | API / Backend (intelligence layer) | — | Reuses `build_evidence_summary()` + `compute_readiness_score()`; both are server-side functions |
| Trend data exposure | API / Backend | — | New `GET /api/trends` FastAPI route in `quirk/dashboard/api/routes/` |
| Trend data display | Browser / Client | — | `pages/trends.tsx` consumes `useTrendsData` hook; renders cards + collapsible sample tables |
| Navigation entry | Browser / Client | — | `NAV_ITEMS` in `sidebar.tsx`; `Route` in `App.tsx` |

---

## Standard Stack

### Core (all already in project — no new installs required)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy | (existing) | Session grouping query, endpoint fetch | All DB access in this project uses SQLAlchemy ORM + `func.strftime` pattern established in `scan.py` |
| FastAPI / Pydantic | (existing) | API route, response schema | All routes in `quirk/dashboard/api/routes/` use FastAPI + Pydantic models in `schemas.py` |
| React + TypeScript | (existing) | Trends page component | All dashboard pages are `.tsx` files in `src/dashboard/src/pages/` |
| shadcn/ui | (existing) | Card, Badge, Table, Skeleton UI components | All installed; confirmed in `src/dashboard/src/components/ui/` |
| lucide-react | (existing) | `TrendingUp` icon for nav entry | All nav icons come from lucide-react (confirmed in `sidebar.tsx`) |

**Installation:** None required. [VERIFIED: codebase grep of `quirk/intelligence/`, `quirk/dashboard/api/`, `src/dashboard/src/components/ui/`]

### Component Availability Check

| Component | Status |
|-----------|--------|
| `Card`, `CardHeader`, `CardContent`, `CardTitle` | Installed (`card.tsx` confirmed) |
| `Badge` | Installed (`badge.tsx` confirmed) |
| `Table`, `TableBody`, `TableCell`, `TableHead`, `TableHeader`, `TableRow` | Installed (`table.tsx` confirmed) |
| `Skeleton` | Installed (`skeleton.tsx` confirmed) |
| `Collapsible` | **NOT installed** — use native `<details>`/`<summary>` |

[VERIFIED: `src/dashboard/src/components/ui/` directory listing — no `collapsible.tsx` present]

---

## Architecture Patterns

### System Architecture Diagram

```
GET /api/trends
       │
       ▼
quirk/dashboard/api/routes/trends.py (or scan.py)
  ├── list_scans(db)            ← returns ordered ScanSession list
  │       (strftime grouping, newest first)
  │
  ├── sessions[0].scanned_at   ← current_ts
  ├── sessions[1].scanned_at   ← previous_ts (or null if len < 2)
  │
  └── compute_trend_report(current_ts, previous_ts, db)
              │
              ▼
      quirk/intelligence/trends.py
        ├── fetch current session endpoints  (±1s window, scanned_at IS NOT NULL)
        ├── fetch previous session endpoints (±1s window, scanned_at IS NOT NULL)
        │
        ├── build match key sets:
        │     current_keys  = {(host, port, protocol, severity) for ep
        │                       if ep.scan_error is None}
        │     previous_keys = {(host, port, protocol, severity) for ep
        │                       if ep.scan_error is None}
        │
        ├── new_keys      = current_keys  - previous_keys
        ├── resolved_keys = previous_keys - current_keys
        │
        ├── count by severity (HIGH / MEDIUM / LOW)
        ├── top-5 sample arrays
        │
        ├── scan_errors_new_count     = |scan_error EPs in current| - |in previous|
        ├── scan_errors_resolved_count = |scan_error EPs in previous| - |in current|
        │
        ├── build_evidence_summary(current_eps)  → evidence_current
        ├── compute_readiness_score(evidence_current) → current_score (int)
        ├── build_evidence_summary(previous_eps) → evidence_previous
        ├── compute_readiness_score(evidence_previous) → previous_score (int)
        │
        └── return TrendReport dataclass / Pydantic model
              │
              ▼
      JSON response → React useTrendsData hook → /trends page
```

### Recommended Project Structure

New files this phase adds:
```
quirk/intelligence/
└── trends.py                      # compute_trend_report() + TrendReport type

quirk/dashboard/api/routes/
└── trends.py                      # GET /api/trends route (new file, per discretion)
  (OR added to scan.py if preferred)

src/dashboard/src/
├── pages/trends.tsx               # Trends page component
├── hooks/useTrendsData.ts         # useTrendsData hook (mirrors useScanData.ts)
└── types/api.ts                   # Add TrendReport + SampleFinding interfaces

tests/
└── test_intelligence_trends.py    # Unit tests for compute_trend_report()
```

### Pattern 1: Session Grouping (MUST reuse verbatim)

**What:** Second-truncated `strftime` grouping to collapse microsecond-precision `scanned_at` timestamps into session boundaries.

**When to use:** Whenever fetching "all endpoints in a session" by timestamp.

```python
# Source: quirk/dashboard/api/routes/scan.py:457
ts_sec = func.strftime("%Y-%m-%d %H:%M:%S", CryptoEndpoint.scanned_at).label("ts_sec")
rows = (
    db.query(ts_sec, func.count(CryptoEndpoint.id).label("cnt"))
    .group_by("ts_sec")
    .order_by(ts_sec.desc())
    .limit(10)
    .all()
)
```

[VERIFIED: read `scan.py:449-472`]

### Pattern 2: Session Endpoint Fetch (±1 second window)

**What:** Given an ISO-format session timestamp string, fetch all endpoints in that session.

**When to use:** In `compute_trend_report()` when loading current and previous session endpoints.

```python
# Source: quirk/dashboard/api/routes/scan.py:500-507
target_ts = datetime.fromisoformat(scan_id)
endpoints = (
    db.query(CryptoEndpoint)
    .filter(
        CryptoEndpoint.scanned_at >= target_ts,
        CryptoEndpoint.scanned_at < target_ts + timedelta(seconds=1),
    )
    .all()
)
```

[VERIFIED: read `scan.py:496-507`]

### Pattern 3: NULL session filter (D-13)

**What:** Exclude endpoints with `scanned_at IS NULL` before session grouping.

**When to use:** In both the session listing and endpoint fetch queries inside `compute_trend_report()`.

```python
# Apply this filter on the strftime grouping query AND the ±1s fetch:
.filter(CryptoEndpoint.scanned_at.isnot(None))
```

[VERIFIED: D-13 in CONTEXT.md, CryptoEndpoint.scanned_at is `nullable=True` per models.py:17]

### Pattern 4: Score Derivation

**What:** Build evidence summary from an endpoint list, then compute the readiness score.

**When to use:** Once per session (current and previous) inside `compute_trend_report()`.

```python
# Source: quirk/intelligence/evidence.py + scoring.py (verified by read)
from quirk.intelligence.evidence import build_evidence_summary
from quirk.intelligence.scoring import compute_readiness_score

evidence = build_evidence_summary(endpoints)
score_dict = compute_readiness_score(evidence)
score: int = score_dict["score"]
```

[VERIFIED: `compute_readiness_score()` returns `{"score": int, "rating": str, "subscores": dict, "drivers": list}` — confirmed by running the function]

### Pattern 5: FastAPI Route Registration

**What:** Register new router in the app factory.

**When to use:** When adding `trends.py` route file.

```python
# Source: pattern from quirk/dashboard/api/app.py (check _include_routers pattern)
# All existing routes registered via router.include_router(...)
```

[ASSUMED: app.py route registration exact pattern not read — check `quirk/dashboard/api/app.py` before implementing]

### Pattern 6: Pydantic Schema in schemas.py

**What:** All API response types declared in `quirk/dashboard/api/schemas.py`; TypeScript mirror in `src/dashboard/src/types/api.ts`.

**When to use:** `TrendReportResponse` Pydantic model goes in `schemas.py`. `TrendReport` + `SampleFinding` TypeScript interfaces go in `api.ts`.

```python
# Source: quirk/dashboard/api/schemas.py (verified by read)
class TrendReportResponse(BaseModel):
    current_session_ts: Optional[datetime] = None
    previous_session_ts: Optional[datetime] = None
    current_score: Optional[int] = None
    previous_score: Optional[int] = None
    score_delta: Optional[int] = None
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

class SampleFinding(BaseModel):
    host: str
    port: int
    protocol: str
    severity: str
```

Note: `score_delta` should be `Optional[int]` since `compute_readiness_score()` returns an `int` (not float). The CONTEXT.md D-07 says `float` — but the actual return type is `int` (verified by running the function). Claude's discretion: use `Optional[int]` to match reality, or cast to `float` to match the spec. Recommend `Optional[int]` since the score itself is always an integer.

[VERIFIED: ran `compute_readiness_score()` — score is `int`]

### Pattern 7: React Hook (mirrors useScanData)

```typescript
// Source: src/dashboard/src/hooks/useScanData.ts (verified by read)
// New file: src/dashboard/src/hooks/useTrendsData.ts
// Pattern: useState(null) + useEffect + fetch("/api/trends") + cancelled flag
// Returns: { data: TrendReport | null, loading: boolean, error: string | null }
```

[VERIFIED: `useScanData.ts` pattern confirmed]

### Pattern 8: Nav Registration

```typescript
// Source: src/dashboard/src/components/sidebar.tsx:18-25 (verified)
// Add to NAV_ITEMS array:
{ path: "/trends", label: "Trends", Icon: TrendingUp }
// Import TrendingUp from "lucide-react" alongside existing icons
```

[VERIFIED: `sidebar.tsx` NAV_ITEMS pattern confirmed]

### Pattern 9: Route Registration in App.tsx

```tsx
// Source: src/dashboard/src/App.tsx (verified by read)
import { TrendsPage } from "@/pages/trends"
// Inside <Routes>:
<Route path="/trends" element={<TrendsPage />} />
```

[VERIFIED: `App.tsx` Routes pattern confirmed]

### Anti-Patterns to Avoid

- **Calling `datetime.now()` inside `compute_trend_report()`:** Violates D-12 (ISSUE-3 spirit). All timestamps come from caller.
- **Adding a new SQLite table:** Violates D-11. All session data is derived from existing `CryptoEndpoint.scanned_at` grouping.
- **Including `scan_error IS NOT NULL` rows in the finding delta:** Violates D-04. Error rows must be filtered before building match key sets.
- **Grouping by raw `scanned_at`:** Each row has microsecond-precision — grouping without `strftime` truncation produces one "session" per row. Use `func.strftime("%Y-%m-%d %H:%M:%S", ...)`.
- **Installing the shadcn Collapsible component:** It is NOT present in `src/dashboard/src/components/ui/`. Use native `<details>`/`<summary>` instead.
- **Declaring `score_delta` as `float` in Pydantic when the scorer returns `int`:** Will work (Pydantic coerces) but is misleading. Keep consistent with `score: int` in `ScoreData`.
- **Mixing scan_error filtering:** scan_error rows are excluded from finding delta (D-04) but their count IS tracked separately (D-05). These are two different queries/counts; do not conflate.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Session boundary resolution | Custom timestamp grouping | `func.strftime("%Y-%m-%d %H:%M:%S", CryptoEndpoint.scanned_at)` | Already established in `list_scans()` — any deviation breaks session boundary consistency |
| Readiness score calculation | Custom scoring logic in trends.py | `build_evidence_summary()` + `compute_readiness_score()` | Scoring logic has many weighted components; re-implementing even partially would diverge |
| UI loading state | Custom spinner | `<Skeleton>` from shadcn | Consistent with all other pages (`findings.tsx` pattern) |
| Table rendering | Custom HTML table | `Table`, `TableBody`, etc. from `@/components/ui/table` | Consistent with `findings.tsx` — UI contract requires this exact pattern |
| Collapse behavior | shadcn Collapsible | `<details>`/`<summary>` HTML | Collapsible component NOT installed; native HTML works without new registry call |

**Key insight:** The score computation is particularly complex (5 sub-scores, 20+ weighted factors, profile multipliers). There is no shortcut — call the existing functions, do not attempt a simplified version.

---

## Common Pitfalls

### Pitfall 1: Microsecond Timestamp Grouping

**What goes wrong:** Query returns one "session" per endpoint row instead of one per scan run.
**Why it happens:** Each `CryptoEndpoint` row receives its own `scanned_at` with microsecond precision when inserted. Grouping by the raw column value produces N groups for N endpoints in the same scan.
**How to avoid:** Always use `func.strftime("%Y-%m-%d %H:%M:%S", CryptoEndpoint.scanned_at)` to truncate to second precision before grouping.
**Warning signs:** `list_scans()` returns 50+ "sessions" when only 2 scans were run.

### Pitfall 2: NULL scanned_at Rows (v4.2 Session Pollution)

**What goes wrong:** v4.2-era endpoints with `scanned_at IS NULL` group into a single `None` session, making the trend report compare the current real session against a ghost "NULL session."
**Why it happens:** `scanned_at` is `nullable=True` in the model; old endpoints pre-v4.3 may not have this field set.
**How to avoid:** Filter `CryptoEndpoint.scanned_at.isnot(None)` in the session listing query and in the endpoint fetch query inside `compute_trend_report()`.
**Warning signs:** `previous_session_ts` is `None` when real previous scans exist.

### Pitfall 3: scan_error Rows in Finding Delta

**What goes wrong:** A host that was temporarily unreachable shows up as "resolved" even though the finding is still present; or vice versa for newly unreachable hosts.
**Why it happens:** `scan_error IS NOT NULL` rows have `(host, port, protocol, severity)` values that may match valid findings in the other session.
**How to avoid:** Filter `CryptoEndpoint.scan_error.is_(None)` before building the match key sets. Track error counts separately (D-05).
**Warning signs:** `resolved_high` jumps unexpectedly when targets go offline.

### Pitfall 4: Single-Session Edge Case

**What goes wrong:** Route raises an exception or returns HTTP 500 when only one scan session exists.
**Why it happens:** `list_scans()` returns a list of length 1; `sessions[1]` raises `IndexError`.
**How to avoid:** After calling `list_scans()`, check `len(sessions) < 2` before accessing `sessions[1]`. Return the D-06 null-delta response immediately.
**Warning signs:** Dashboard shows error state after first scan.

### Pitfall 5: score_delta Precision Mismatch

**What goes wrong:** `score_delta` is declared as `float` in D-07, but `compute_readiness_score()["score"]` returns `int`.
**Why it happens:** D-07 was written before the scorer's `int` return type was verified.
**How to avoid:** Use `Optional[int]` in Pydantic schema (or explicitly cast to float). Either works; be consistent within the schema.
**Warning signs:** TypeScript type errors if frontend expects `number` but gets unexpected behavior.

### Pitfall 6: Missing `scanned_at IS NULL` Filter in Evidence Build

**What goes wrong:** `build_evidence_summary()` processes NULL-timestamp endpoints alongside real session endpoints, corrupting evidence counts.
**Why it happens:** The `±1s window` query naturally filters by timestamp range — but if the NULL-filter is missing from the session listing, the wrong sessions are compared.
**How to avoid:** Apply `scanned_at IS NOT NULL` in `list_scans()` equivalent query inside `compute_trend_report()`, not just in the endpoint fetch.

---

## Code Examples

### compute_trend_report() Signature and Return Type

```python
# quirk/intelligence/trends.py
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from sqlalchemy import func
from sqlalchemy.orm import Session
from quirk.models import CryptoEndpoint
from quirk.intelligence.evidence import build_evidence_summary
from quirk.intelligence.scoring import compute_readiness_score

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


def compute_trend_report(
    current_ts: datetime,
    previous_ts: Optional[datetime],
    db: Session,
) -> TrendReport:
    """Compare two scan sessions and return a trend report.

    Accuracy note: Trend accuracy depends on consistent target configuration
    between scans. IP-addressed targets may produce phantom new/resolved
    findings if IPs change between scans. NULL collision with v4.2-era sessions
    (scanned_at IS NULL) is expected behavior — the first post-v4.3 trend will
    show all DAR findings as new.
    """
    # fetch current session endpoints (scanned_at IS NOT NULL enforced by caller)
    ...
```

[VERIFIED: pattern derived from `scan.py:500-507`, `evidence.py`, `scoring.py` — all read directly]

### GET /api/trends Route Sketch

```python
# quirk/dashboard/api/routes/trends.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from quirk.dashboard.api.deps import get_db
from quirk.dashboard.api.schemas import TrendReportResponse
from quirk.intelligence.trends import compute_trend_report

router = APIRouter()

@router.get("/trends", response_model=TrendReportResponse)
def get_trends(db: Session = Depends(get_db)) -> TrendReportResponse:
    """GET /api/trends — returns trend data for the two most recent scan sessions."""
    sessions = list_scans(db)          # reuse or inline list_scans logic
    if len(sessions) < 2:
        # D-06: single-session response
        current_ts = sessions[0].scanned_at if sessions else None
        return TrendReportResponse(current_session_ts=current_ts)

    report = compute_trend_report(
        current_ts=sessions[0].scanned_at,
        previous_ts=sessions[1].scanned_at,
        db=db,
    )
    return TrendReportResponse(**vars(report))
```

### useTrendsData Hook

```typescript
// src/dashboard/src/hooks/useTrendsData.ts
// Pattern: mirrors useScanData.ts exactly (verified by read)
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
        if (!cancelled) setData(json)
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load trend data")
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

### Collapsible Sample Table (native HTML — no shadcn Collapsible)

```tsx
{/* Collapsible NOT installed in ui/ — use native details/summary */}
{report.new_findings_sample.length > 0 && (
  <details className="rounded-md border border-border">
    <summary className="cursor-pointer px-4 py-2 text-sm font-semibold">
      Show {report.new_findings_sample.length} samples
    </summary>
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
        {report.new_findings_sample.map((f, i) => (
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
  </details>
)}
```

### Score Delta Badge

```tsx
// Per UI-SPEC.md — color-coded by sign
function ScoreDeltaBadge({ delta }: { delta: number | null }) {
  if (delta === null) return <Badge variant="outline">— First scan</Badge>
  if (delta > 0) return (
    <Badge className="bg-[hsl(var(--quantum-safe))] text-white">
      ▲ +{delta.toFixed(1)} pts
    </Badge>
  )
  if (delta < 0) return (
    <Badge className="bg-[hsl(var(--destructive))] text-white">
      ▼ {delta.toFixed(1)} pts
    </Badge>
  )
  return <Badge className="bg-[hsl(var(--muted))] text-muted-foreground">→ No change</Badge>
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| N/A (trend analysis is new) | `compute_trend_report()` pure function with `(host, port, protocol, severity)` match key | Phase 31 | No migration needed — all prior sessions usable immediately (with NULL-filter caveat) |
| Sessions identified by max scanned_at | Sessions identified by second-truncated strftime grouping | Phase-internal (scan.py:450 pattern) | Trend must use the same grouping or session boundaries will mismatch |

**Deprecated/outdated:**
- None for this phase.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | New route should go in a new `routes/trends.py` file (not appended to `scan.py`) | Architecture Patterns | Low — either works; Claude's discretion, but verify `app.py` router registration pattern before implementing |
| A2 | `app.py` uses `include_router()` to register route modules — verify the exact registration pattern before adding new router | Pattern 5 | Low — if registration differs, new route won't be reachable; read `quirk/dashboard/api/app.py` in Plan 01 |

---

## Open Questions

1. **Route file location — `routes/trends.py` vs append to `scan.py`**
   - What we know: CONTEXT.md says "Claude's discretion — `scan.py` already has `list_scans()` which trends.py depends on, so colocating is reasonable"
   - What's unclear: Whether the `app.py` router registration is set up to auto-discover new router files or requires manual registration
   - Recommendation: Read `quirk/dashboard/api/app.py` at Plan 01 start. If manual registration, a new `routes/trends.py` file is cleaner; if any auto-discovery, colocating in `scan.py` is simpler.

2. **`score_delta` type — `int` vs `float`**
   - What we know: `compute_readiness_score()["score"]` returns `int` (verified); CONTEXT.md D-07 says `float`
   - What's unclear: Whether the UI-SPEC or frontend TypeScript type matters here
   - Recommendation: Use `Optional[int]` in Pydantic for accuracy. TypeScript `number` covers both. Document in schema docstring.

---

## Environment Availability

Step 2.6: SKIPPED — Phase 31 is a pure code/configuration change. No new external dependencies, CLI tools, databases, or services are introduced. All computation uses existing SQLite (already running), Python packages (already installed), and the existing React build chain.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (confirmed by `tests/conftest.py` and existing test files) |
| Config file | `pyproject.toml` (standard pytest config location for this project) |
| Quick run command | `python -m pytest tests/test_intelligence_trends.py -x -q` |
| Full suite command | `python -m pytest tests/ -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TREND-01 | `compute_trend_report()` returns non-null `score_delta` when two sessions exist | unit | `python -m pytest tests/test_intelligence_trends.py::test_score_delta_computed -x` | ❌ Wave 0 |
| TREND-01 | `compute_trend_report()` returns `score_delta=None` when only one session exists | unit | `python -m pytest tests/test_intelligence_trends.py::test_single_session_null_delta -x` | ❌ Wave 0 |
| TREND-02 | Net-new findings counted by severity (HIGH/MEDIUM/LOW) | unit | `python -m pytest tests/test_intelligence_trends.py::test_new_findings_counted -x` | ❌ Wave 0 |
| TREND-03 | Resolved findings counted by severity | unit | `python -m pytest tests/test_intelligence_trends.py::test_resolved_findings_counted -x` | ❌ Wave 0 |
| TREND-03 | Severity change surfaces as "old resolved + new new" (D-03) | unit | `python -m pytest tests/test_intelligence_trends.py::test_severity_change_surfaces -x` | ❌ Wave 0 |
| TREND-04 | `GET /api/trends` returns HTTP 200 with correct schema | integration | `python -m pytest tests/test_dashboard_trends.py::test_trends_endpoint_schema -x` | ❌ Wave 0 |
| TREND-04 | `GET /api/trends` returns D-06 response when only 1 session | integration | `python -m pytest tests/test_dashboard_trends.py::test_trends_single_session -x` | ❌ Wave 0 |
| D-04 | `scan_error` rows excluded from finding delta | unit | `python -m pytest tests/test_intelligence_trends.py::test_scan_error_excluded_from_delta -x` | ❌ Wave 0 |
| D-05 | Scan error counts tracked separately | unit | `python -m pytest tests/test_intelligence_trends.py::test_scan_error_counts_surfaced -x` | ❌ Wave 0 |
| D-13 | NULL scanned_at rows excluded from session grouping | unit | `python -m pytest tests/test_intelligence_trends.py::test_null_scanned_at_excluded -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `python -m pytest tests/test_intelligence_trends.py -x -q`
- **Per wave merge:** `python -m pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_intelligence_trends.py` — unit tests for `compute_trend_report()`, covers TREND-01 through TREND-03, D-03, D-04, D-05, D-13
- [ ] `tests/test_dashboard_trends.py` — integration tests for `GET /api/trends` using `dashboard_client` fixture, covers TREND-04
- [ ] `quirk/intelligence/trends.py` — stub with empty `compute_trend_report()` (RED scaffold)
- [ ] `quirk/dashboard/api/schemas.py` — add `SampleFinding` + `TrendReportResponse` Pydantic models

---

## Security Domain

> `security_enforcement` is not explicitly set to `false` in config.json — treated as enabled.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | Endpoint is read-only, no auth required in QUIRK's current architecture |
| V3 Session Management | No | Stateless API endpoint |
| V4 Access Control | No | No user roles in QUIRK v4.3 |
| V5 Input Validation | No | `GET /api/trends` accepts no parameters; no user input to validate |
| V6 Cryptography | No | No crypto operations in this phase |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SQL injection via session timestamp | Tampering | Not applicable — timestamps come from internal `list_scans()` query, not user input; no `?session_ts=` parameter accepted |
| Information disclosure via trend data | Information Disclosure | Acceptable per QUIRK's single-user local architecture |

**Security summary:** `GET /api/trends` is a zero-parameter read endpoint returning pre-computed scan comparison data. No user-supplied parameters, no writes, no authentication surface. Security posture is identical to `GET /api/scan/latest`.

---

## Sources

### Primary (HIGH confidence)
- `quirk/dashboard/api/routes/scan.py:449-472` — `list_scans()` strftime grouping pattern (read directly)
- `quirk/dashboard/api/routes/scan.py:485-530` — `get_latest_scan()` ±1s window pattern (read directly)
- `quirk/models.py` — `CryptoEndpoint` field inventory (read directly)
- `quirk/intelligence/scoring.py` — `compute_readiness_score()` signature and return shape (read + executed)
- `quirk/intelligence/evidence.py` — `build_evidence_summary()` signature and return shape (read directly)
- `quirk/dashboard/api/schemas.py` — Pydantic model conventions (read directly)
- `src/dashboard/src/hooks/useScanData.ts` — hook pattern template (read directly)
- `src/dashboard/src/App.tsx` — route registration pattern (read directly)
- `src/dashboard/src/components/sidebar.tsx` — NAV_ITEMS pattern (read directly)
- `src/dashboard/src/pages/findings.tsx` — SEVERITY_STYLES, Table pattern, Skeleton loading state (read directly)
- `src/dashboard/src/components/ui/` — component inventory (directory listing)
- `.planning/phases/31-trend-analysis/31-CONTEXT.md` — all locked decisions
- `.planning/phases/31-trend-analysis/31-UI-SPEC.md` — approved UI contract
- `tests/conftest.py` — `dashboard_client` fixture pattern (read directly)

### Secondary (MEDIUM confidence)
- None required — all decisions locked in CONTEXT.md, all patterns confirmed by direct codebase reads.

### Tertiary (LOW confidence)
- None.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries verified in-repo, no new dependencies
- Architecture: HIGH — patterns read directly from canonical source files; session grouping exact code confirmed
- Pitfalls: HIGH — derived from direct code inspection and CONTEXT.md decisions
- UI patterns: HIGH — `findings.tsx`, `sidebar.tsx`, `App.tsx`, `useScanData.ts` all read directly; Collapsible absence confirmed by directory listing

**Research date:** 2026-04-26
**Valid until:** 2026-05-26 (stable internal codebase; no external library versions at risk of staleness)
