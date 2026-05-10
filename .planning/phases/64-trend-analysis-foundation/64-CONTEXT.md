# Phase 64: Trend Analysis Foundation - Context

**Gathered:** 2026-05-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 64 upgrades the dashboard's trend view from a pairwise (current vs previous) delta display into a full multi-scan timeline. Three concrete deliverables:

1. **New backend timeline endpoint** — `GET /api/trends/timeline?n=30` returns up to N sessions (default 30), each with overall score, 6 subscores, and finding counts by severity tier.
2. **Recharts LineChart timeline** — replaces the existing score-delta card in `TrendsPage` with a multi-line chart showing all 7 series (overall + 6 subscores) over time; hover tooltip reveals session timestamp.
3. **Regression alert chips** — surfaced on the dashboard home when posture regresses (score drop ≥ 5 pts OR `new_high > 0`); dismissible per-session via `localStorage`; deep-link to `/trends`.

**In scope:** `GET /api/trends/timeline`, `useTimelineData` hook, `TrendsPage` chart, `RegressionAlertChip` component on executive page, `localStorage` dismissal.

**Out of scope:** Storing per-session subscores in the DB (compute inline), multi-user dismissal sync, configuring the regression threshold via UI, trend data for schedules dashboard (Phase 63), scan ID permalink URLs (no per-scan URL scheme in current router).

</domain>

<decisions>
## Implementation Decisions

### API Endpoint Design
- **D-01:** Add `GET /api/trends/timeline?n=30` as a **new** endpoint alongside the existing `GET /api/trends`. The existing endpoint is kept unchanged — it drives TREND-02 regression detection and is consumed by the existing `useTrendsData` hook. Do NOT modify or merge these two endpoints.
- **D-02:** The timeline endpoint returns a `TrendTimelineResponse` with a `sessions` array (newest-first, max N). Each item: `session_ts` (ISO string), `score` (int), `subscores` (all 6 keys from `compute_readiness_score()`), `finding_counts` ({high, medium, low}).
- **D-03:** Session enumeration reuses the existing `_list_session_timestamps()` pattern in `quirk/dashboard/api/routes/trends.py` but with `LIMIT n` (default 30, max 200). Expose `n` as a query param validated by Pydantic (`Query(default=30, ge=2, le=200)`).

### Per-Session Subscore Computation
- **D-04:** Compute subscores **inline** per session in the backend handler — call `build_evidence_summary(endpoints)` then `compute_readiness_score(evidence)` for each of the N sessions. No schema change, no caching layer. 30 sessions × ~50ms per scoring = ~1.5s max; acceptable for a consultant dashboard.
- **D-05:** Finding counts per session: count `CryptoEndpoint` rows within each session window, bucketing by severity the same way `trends.py` does (`CRITICAL/HIGH → "high"`, `MEDIUM → "medium"`, `LOW → "low"`, `INFO → excluded`). Do NOT call `compute_trend_report()` for this — just a raw count query per session.
- **D-06:** The subscore keys in the response use the **internal scoring.py key names**: `hygiene`, `modern_tls`, `identity_trust`, `agility_signals`, `data_at_rest`, `data_in_motion`. The frontend applies UI-friendly aliases via the chart config object.

### Regression Alert Chips (TREND-02)
- **D-07:** Regression detection reuses the **existing `GET /api/trends` response** — no new detection logic needed. A regression exists when `score_delta !== null && score_delta <= -5` OR `new_high > 0`. The `RegressionAlertChip` component reads the existing `useTrendsData()` hook.
- **D-08:** Dismissal is stored in **`localStorage`** under the key `quirk.dismissed_regression.<session_ts>` where `<session_ts>` is the ISO string of `current_session_ts`. Dismissal is per-session (the key encodes which scan regressed). Do NOT add a DB table — this is browser-only UI state.
- **D-09:** The chip renders on the `ExecutivePage` (`src/dashboard/src/pages/executive.tsx`), inserted above the score gauge section. Clicking "×" writes to localStorage and hides the chip without a page reload. The chip contains a deep-link anchor to `/trends`.

### Chart Component
- **D-10:** Use Recharts `LineChart` (not `AreaChart`) with 7 `<Line>` series — one for `score` (bold/primary) and one for each of the 6 subscores. Wrap in the existing `<ChartContainer>` from `src/dashboard/src/components/ui/chart.tsx`. Per the feedback constraint, **never conditionally mount/unmount `<Line>` components** — use `strokeOpacity={0}` / toggle via chart config if per-line visibility is needed.
- **D-11:** `<XAxis dataKey="session_ts" />` formatted as `MM/DD HH:mm` (short locale string). `<YAxis domain={[0, 100]} />`. Custom `<Tooltip>` shows full `session_ts` formatted as `toLocaleString()` plus all 7 score values.
- **D-12:** `useTimelineData` hook follows the Phase 62 cancellation-safe pattern: `let cancelled = false` + `return () => { cancelled = true }` inside `useEffect`. Located at `src/dashboard/src/hooks/useTimelineData.ts`.

### Claude's Discretion
- Line colors: use `hsl(var(--quantum-safe))` for the overall score line; use the existing CSS variable palette for subscores (muted foreground variants or explicit HSL values consistent with the existing chart colors in `executive.tsx`).
- Loading state: reuse `<PageSpinner>` from `src/dashboard/src/components/PageSpinner.tsx` (same as existing trends page).
- Empty state (< 2 sessions): keep the existing "Run two or more scans" message in `TrendsPage`; do not show a partial chart.
- The `TrendsPage` keeps the existing score-delta card and new/resolved finding tables below the chart (don't remove them — they remain useful for pairwise context).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase Requirements
- `.planning/REQUIREMENTS.md` §TREND-01, §TREND-02 — exact acceptance criteria
- `.planning/ROADMAP.md` §Phase 64 — goal statement, success criteria

### Backend: Existing Trends Layer
- `quirk/intelligence/trends.py` — `compute_trend_report()`, session grouping pattern, severity bucketing constants (`_SEVERITY_BUCKET`), `_fetch_session_endpoints()` helper
- `quirk/intelligence/scoring.py` — `compute_readiness_score()` return shape: `{score, subscores: {hygiene, modern_tls, identity_trust, agility_signals, data_at_rest, data_in_motion}}`
- `quirk/intelligence/evidence.py` — `build_evidence_summary()` (input to scoring)
- `quirk/dashboard/api/routes/trends.py` — existing `/api/trends` route; `_list_session_timestamps()` session enumeration pattern to reuse/extend
- `quirk/dashboard/api/schemas.py` — `TrendReportResponse`, `SubScores`, `SampleFinding` — new `TrendTimelineResponse` and `TrendSessionPoint` schemas go here
- `quirk/dashboard/api/deps.py` — `get_db()` FastAPI dependency
- `quirk/dashboard/api/app.py` — router mounting; new timeline route registers here

### Frontend: Hook + Chart Patterns
- `src/dashboard/src/hooks/useTrendsData.ts` — cancellation-safe fetch pattern to replicate in `useTimelineData.ts`
- `src/dashboard/src/components/ui/chart.tsx` — `ChartContainer`, `ChartTooltip`, `ChartTooltipContent` from shadcn/ui chart
- `src/dashboard/src/pages/executive.tsx` — existing BarChart (recharts) usage pattern; location for `RegressionAlertChip` insertion
- `src/dashboard/src/pages/trends.tsx` — existing `TrendsPage` to update with LineChart
- `src/dashboard/src/types/api.ts` — `TrendReport` type; add `TrendTimeline`, `TrendSessionPoint` types here

### Prior Phase Decisions
- `.planning/phases/63-scheduled-continuous-scanning/63-CONTEXT.md` §D-03 — `scheduled_runs.scan_id` FK pattern (future Phase 64 may correlate timeline points to scheduled runs; no action needed now)
- `.planning/phases/62-react-hook-cancellation-pattern/62-CONTEXT.md` — HOOK-01..04 patterns that `useTimelineData` must follow

### Feedback Constraints (MANDATORY)
- Recharts static children: never conditionally mount/unmount `<Line>`/`<Bar>`/`<Radar>` inside a chart — use `strokeOpacity`/`fillOpacity` for toggling (feedback_recharts_static_children.md)
- Dashboard build step: after `.tsx` edits, run `npm run build` in `src/dashboard/` before testing (feedback_dashboard_build_required.md)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `quirk/dashboard/api/routes/trends.py::_list_session_timestamps()` — copy + parameterize with `LIMIT n` for the timeline endpoint
- `quirk/intelligence/trends.py::_fetch_session_endpoints()` — reuse as-is to fetch each session's endpoints
- `quirk/intelligence/trends.py::_bucket_for_severity()` + `_count_by_bucket()` — reuse for per-session finding counts
- `src/dashboard/src/hooks/useTrendsData.ts` — copy as template for `useTimelineData.ts`; same cancellation pattern, different endpoint and response type
- `src/dashboard/src/components/PageSpinner.tsx` — reuse for loading state in both `TrendsPage` chart section and `RegressionAlertChip`
- `src/dashboard/src/components/ui/chart.tsx` — `ChartContainer`, `ChartTooltip` — the project's canonical Recharts wrapper; already tested in `executive.tsx`

### Established Patterns
- **Session grouping:** `func.strftime("%Y-%m-%d %H:%M:%S", CryptoEndpoint.scanned_at)` groups all endpoints in a scan run into one logical session — this is the authoritative pattern used in `trends.py` and `routes/trends.py`
- **NULL scanned_at exclusion:** Every session query filters `.filter(CryptoEndpoint.scanned_at.isnot(None))` — never omit this
- **SubScores key names:** `hygiene`, `modern_tls`, `identity_trust`, `agility_signals`, `data_at_rest`, `data_in_motion` — these are the canonical internal keys, not the roadmap's colloquial labels (TLS/SSH/API/Identity/DAR/DiM)
- **Recharts in this codebase:** `executive.tsx` uses `BarChart` via `ResponsiveContainer`; `chart.tsx` wraps Recharts with shadcn/ui theming — always use `ChartContainer` over bare `ResponsiveContainer` for consistent theming

### Integration Points
- `quirk/dashboard/api/routes/trends.py` — add `@router.get("/trends/timeline")` here (same router, same auth dependency)
- `quirk/dashboard/api/schemas.py` — add `TrendSessionPoint` + `TrendTimelineResponse` Pydantic models
- `src/dashboard/src/App.tsx` — no new route needed (`/trends` already exists); timeline data replaces the existing card
- `src/dashboard/src/pages/executive.tsx` — insert `RegressionAlertChip` above the score gauge
- `src/dashboard/src/types/api.ts` — add `TrendTimeline` and `TrendSessionPoint` TypeScript interfaces

</code_context>

<specifics>
## Specific Ideas

- TREND-01 success criterion: chart default window is **last 30 scans**, configurable via `?n=` query param (range 2–200); the UI does not yet need a control to change N — the default is sufficient
- TREND-02 success criterion: chip is **dismissible per-scan** (not global reset) — the localStorage key encodes the regressing scan's `current_session_ts`, so a new regression in the next scan shows a new chip even after the previous dismissal
- Hover tooltip must show **scan timestamp** (the session's `session_ts` as `toLocaleString()`) plus score values — "scan ID" in the ROADMAP.md means the timestamp identity, not a UUID
- The existing delta card (`TrendsPage` score comparison section) remains below the chart — it is complementary, not replaced

</specifics>

<deferred>
## Deferred Ideas

- **Per-line visibility toggle** — a checkbox list to show/hide individual subscore lines on the chart; useful but out of TREND-01 scope
- **Configurable regression threshold** — UI control to change the 5-point drop threshold; TREND-02 hardcodes 5 pts per the acceptance criterion
- **Trend correlation with scheduled runs** — linking timeline points to `scheduled_runs.scan_id` (Phase 63 introduced `scan_id` FK); Phase 63 + 64 ship independently; correlation can be a Phase 65+ enhancement
- **Exported trend report** — CSV/PDF of the timeline data; out of scope for v4.8
- **Sub-pillar drilldown** — clicking a timeline point to see which endpoints regressed within that pillar; deferred to a future dashboard phase

None — discussion stayed within phase scope (auto mode)

</deferred>

---

*Phase: 64-trend-analysis-foundation*
*Context gathered: 2026-05-10*
