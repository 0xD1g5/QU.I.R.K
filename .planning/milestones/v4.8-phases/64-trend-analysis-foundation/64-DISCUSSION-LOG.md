# Phase 64: Trend Analysis Foundation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-10
**Phase:** 64-trend-analysis-foundation
**Mode:** --auto (all areas auto-selected, recommended options chosen)
**Areas discussed:** API Endpoint Design, Per-Session Subscore Computation, Regression Alert Chips, Chart Component

---

## API Endpoint Design

| Option | Description | Selected |
|--------|-------------|----------|
| Extend existing `/api/trends` | Add `?n=` param to return N sessions from existing endpoint; breaking change to response shape | |
| New `GET /api/trends/timeline?n=30` | Separate endpoint, existing endpoint unchanged, backward compat preserved | ✓ |

**Auto-selected:** New endpoint (recommended default)
**Notes:** Existing `/api/trends` pairwise response is consumed by the existing `useTrendsData` hook for TREND-02 regression chips — it must remain unchanged. A new endpoint avoids any breaking changes to existing consumers.

---

## Per-Session Subscore Computation

| Option | Description | Selected |
|--------|-------------|----------|
| Store subscores in DB | Add columns to `crypto_endpoints` or a new `scan_sessions` table; requires migration | |
| Compute inline per request | Call `build_evidence_summary()` + `compute_readiness_score()` for each of N sessions at request time | ✓ |
| Cache in a new `scan_scores` table | Write-through cache on each scan; avoids recompute but adds schema complexity | |

**Auto-selected:** Compute inline (recommended default)
**Notes:** 30 sessions × ~50ms scoring = ~1.5s max. Acceptable for a consultant dashboard with infrequent trend page visits. No schema change needed. Caching is a future optimization if needed.

---

## Regression Alert Dismissal Storage

| Option | Description | Selected |
|--------|-------------|----------|
| New `dismissed_alerts` DB table | Server-side dismissal, survives page reload, requires migration + API route | |
| localStorage (browser) | Client-side, keyed by session timestamp, zero schema change, per-browser | ✓ |

**Auto-selected:** localStorage (recommended default)
**Notes:** Dismissal is purely UI convenience state. Per-scan key (`quirk.dismissed_regression.<session_ts>`) ensures a new regression in the next scan surfaces a fresh chip. No server round-trip needed.

---

## Chart Component

| Option | Description | Selected |
|--------|-------------|----------|
| AreaChart | Filled areas; overlapping fills obscure lower series with 7 lines | |
| LineChart | 7 clean lines; easy to distinguish with color; standard for score timelines | ✓ |
| RadarChart | Shows current-state pillar balance, not over-time trend — wrong shape | |

**Auto-selected:** LineChart (recommended default)
**Notes:** Must use `<ChartContainer>` from `chart.tsx` (shadcn/ui wrapper). Must never conditionally mount/unmount `<Line>` components per project feedback constraint — use `strokeOpacity` for toggling if needed.

---

## Claude's Discretion

- Line colors: overall score uses `hsl(var(--quantum-safe))`; subscores use muted palette from existing chart config
- Loading state: `<PageSpinner>` (same as current TrendsPage)
- Empty state (< 2 sessions): keep existing "Run two or more scans" message, no partial chart
- TrendsPage layout: new LineChart above existing score-delta card and finding tables

## Deferred Ideas

- Per-line visibility toggle (checkbox to show/hide individual subscore lines)
- Configurable regression threshold via UI
- Timeline correlation with scheduled_runs.scan_id (Phase 63 FK introduced)
- CSV/PDF export of trend data
- Sub-pillar drilldown on timeline point click
