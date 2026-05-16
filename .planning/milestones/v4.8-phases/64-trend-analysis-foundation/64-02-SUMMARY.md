---
phase: 64
plan: "02"
subsystem: dashboard-frontend
tags: [frontend, trends, timeline, recharts, linechart, react, hooks]
dependency_graph:
  requires: [64-01]
  provides: [TrendTimeline TypeScript types, useTimelineData hook, Score & Pillar Timeline chart on /trends]
  affects: [src/dashboard/src/types/api.ts, src/dashboard/src/hooks/useTimelineData.ts, src/dashboard/src/pages/trends.tsx, quirk/dashboard/static/]
tech_stack:
  added: []
  patterns: [Phase 62 cancellation-safe fetch hook, Recharts LineChart with 7 static lines, flat data flatten+reverse for chart rendering]
key_files:
  created:
    - src/dashboard/src/hooks/useTimelineData.ts
  modified:
    - src/dashboard/src/types/api.ts
    - src/dashboard/src/pages/trends.tsx
    - quirk/dashboard/static/ (rebuilt bundle)
decisions:
  - "Flatten sessions array (s.subscores.hygiene -> s.hygiene) before passing to Recharts — dot-notation dataKey does not work"
  - "Reverse sessions before chart render — API returns newest-first; chart renders oldest-left"
  - "All 7 <Line> components statically mounted with isAnimationActive=false (Recharts static-children rule)"
  - "Custom tooltip renders full session_ts + all 7 scores + finding counts (HIGH/MED/LOW)"
  - "npm ci run to sync @radix-ui/react-switch and rebuild bundle successfully"
metrics:
  duration: "~12 minutes"
  completed: "2026-05-10"
  tasks: 2
  files: 4
---

# Phase 64 Plan 02: Timeline Frontend — Types + Hook + LineChart Summary

**One-liner:** Recharts LineChart with 7 statically-mounted lines (overall + 6 subscores) on `/trends`, fed by a Phase 62-pattern cancellation-safe `useTimelineData` hook fetching `/api/trends/timeline?n=30`, with sessions flattened and reversed oldest-first before render.

---

## What Was Built

### Task 1: TrendTimeline TypeScript interfaces and useTimelineData hook

Added three new exported interfaces to `src/dashboard/src/types/api.ts` — inserted above the QRAMM section, after the existing `TrendReport` interface. Reuses the existing `SubScores` interface (no duplication):

- `TrendFindingCounts` — `{ high: number; medium: number; low: number }`
- `TrendSessionPoint` — `{ session_ts: string; score: number; subscores: SubScores; finding_counts: TrendFindingCounts }`
- `TrendTimeline` — `{ sessions: TrendSessionPoint[] }`

Created `src/dashboard/src/hooks/useTimelineData.ts` by cloning `useTrendsData.ts` with these changes:
- Imports `TrendTimeline` instead of `TrendReport`
- Endpoint: `/api/trends/timeline?n=30`
- Error fallback: `"Failed to load timeline"`
- Exports `useTimelineData()` returning `{ data: TrendTimeline | null; loading: boolean; error: string | null }`
- Preserves exact Phase 62 cancellation pattern: `let cancelled = false` + guards on all `setState` calls + `return () => { cancelled = true }` cleanup
- Preserves 401/403/429 status-code handling with `Retry-After` header read for 429

### Task 2: Score & Pillar Timeline LineChart on TrendsPage + bundle rebuild

Modified `src/dashboard/src/pages/trends.tsx`:

**Imports added:**
- `LineChart, Line, XAxis, YAxis` from `"recharts"`
- `ChartContainer, ChartTooltip` from `"@/components/ui/chart"`
- `ChartConfig` type from `"@/components/ui/chart"`
- `useTimelineData` from `"@/hooks/useTimelineData"`

**Module-scope constant:**
```typescript
const TIMELINE_CHART_CONFIG: ChartConfig = {
  score, hygiene, modern_tls, identity_trust, agility_signals, data_at_rest, data_in_motion
}
```

**Inside TrendsPage:**
- Calls `useTimelineData()` alongside existing `useTrendsData()`
- Flattens sessions: `s.subscores.hygiene → s.hygiene` etc. (Recharts cannot traverse dot-notation)
- Reverses array: API returns newest-first; chart renders oldest-left
- `showChart = chartDataAsc.length >= 2` guard

**Chart section** inserted above the existing Score Delta card:
- Loading state: `<PageSpinner ariaLabel="Loading trend timeline" />`
- Error state: muted text with error message
- Chart state: `<ChartContainer>` wrapping `<LineChart>` with all 7 `<Line>` components ALWAYS mounted
- Empty state (< 2 sessions): "Run two or more scans to see the score & pillar timeline."
- Custom tooltip: full `session_ts` as `toLocaleString()`, all 7 score values with colored swatches, `Findings: HIGH N MED N LOW N`

**Existing delta cards and finding tables preserved unchanged below the chart.**

**npm run build** completed successfully — rebuilt `quirk/dashboard/static/` bundle. Also synced `package.json` and `package-lock.json` to include `@radix-ui/react-switch` which was missing from worktree node_modules.

---

## Verification Results

```
grep -c "<Line " src/dashboard/src/pages/trends.tsx  →  7 (one per series, all static)
tsc --noEmit -p tsconfig.json                        →  exit 0 (no TS errors)
npm run build                                        →  ✓ built in 663ms
find quirk/dashboard/static -name "*.js" -newer trends.tsx  →  index-CktffHQ9.js (bundle refreshed)
```

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Worktree node_modules missing @radix-ui/react-switch**
- **Found during:** Task 2 (npm run build)
- **Issue:** The worktree's `node_modules` was initialized from the worktree's `package-lock.json` which predated the `@radix-ui/react-switch` addition (used by `src/components/ui/switch.tsx`). Build failed with `error TS2688: Cannot find module '@radix-ui/react-switch'`.
- **Fix:** Synced `package.json` and `package-lock.json` from the main repo's dashboard directory, then ran `npm ci`. Build succeeded.
- **Files modified:** `src/dashboard/package.json`, `src/dashboard/package-lock.json`
- **Commit:** 2baf1cf (bundled with Task 2 source changes)

---

## Commits

| Task | Commit | Message |
|------|--------|---------|
| 1 | 3f3c0be | feat(64-02): add TrendTimeline types and useTimelineData hook |
| 2 | 2baf1cf | feat(64-02): add multi-scan LineChart timeline to TrendsPage (TREND-01) |

---

## Threat Surface Scan

No new network endpoints introduced. The `useTimelineData` hook fetches the existing `/api/trends/timeline` endpoint (introduced in Plan 01 and in the plan threat model as T-64-05, T-64-06, T-64-07). No new trust boundaries.

- T-64-05 (Information Disclosure): 401/403/429 handled with generic strings — no raw response bodies surfaced.
- T-64-06 (DoS via Recharts mount/unmount): All 7 `<Line>` components statically mounted with `isAnimationActive={false}`.
- T-64-07 (XSS via timestamp): `session_ts` is server-generated ISO 8601; React text-node rendering escapes by default.

## Known Stubs

None.

## Self-Check: PASSED

- src/dashboard/src/hooks/useTimelineData.ts: FOUND
- src/dashboard/src/types/api.ts (TrendTimeline): FOUND
- src/dashboard/src/pages/trends.tsx (TIMELINE_CHART_CONFIG): FOUND
- quirk/dashboard/static/assets/index-CktffHQ9.js: FOUND (rebuilt bundle)
- Commits 3f3c0be, 2baf1cf: FOUND in git log
