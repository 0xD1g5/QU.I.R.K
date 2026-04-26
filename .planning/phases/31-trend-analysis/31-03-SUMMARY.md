---
phase: 31-trend-analysis
plan: "03"
subsystem: ui
tags: [react, typescript, shadcn, tailwind, trends, dashboard]

# Dependency graph
requires:
  - phase: 31-trend-analysis/31-02
    provides: GET /api/trends endpoint with TrendReportResponse Pydantic schema
provides:
  - TrendReport and SampleFinding TypeScript interfaces in src/dashboard/src/types/api.ts
  - useTrendsData React hook fetching GET /api/trends
  - TrendsPage component with loading/baseline/full-report render states
  - /trends route in App.tsx
  - Trends sidebar nav entry with TrendingUp icon
affects: [31-04-docs]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "useTrendsData: empty deps array hook pattern (no scan_id param, unlike useScanData)"
    - "ScoreDeltaBadge: conditional badge variant (green/red/muted/outline) based on numeric sign"
    - "Native details/summary collapsible for sample tables (no shadcn Collapsible dependency)"
    - "formatTs: toLocaleString() ISO to human-readable timestamp helper"

key-files:
  created:
    - src/dashboard/src/types/api.ts (appended SampleFinding + TrendReport interfaces)
    - src/dashboard/src/hooks/useTrendsData.ts
    - src/dashboard/src/pages/trends.tsx
  modified:
    - src/dashboard/src/App.tsx (added TrendsPage import + /trends Route)
    - src/dashboard/src/components/sidebar.tsx (added TrendingUp icon + NAV_ITEMS entry)

key-decisions:
  - "Empty deps array in useTrendsData — trends endpoint takes no params, unlike useScanData which depends on selectedScanId"
  - "Native details/summary for sample tables — shadcn Collapsible not installed (PATTERNS.md warning #2)"
  - "snake_case field names in TrendReport interface — mirror JSON exactly, no camelCase mapping needed"
  - "All untrusted strings rendered as React text children — React auto-escaping satisfies T-31-03-01 XSS mitigation"

patterns-established:
  - "ScoreDeltaBadge pattern: sign-based conditional badge for numeric delta values"
  - "SampleTable pattern: native details/summary collapsible wrapping shadcn Table"

requirements-completed: [TREND-04]

# Metrics
duration: 15min
completed: 2026-04-26
---

# Phase 31 Plan 03: Trends Frontend Summary

**React /trends page fully wired to GET /api/trends with score delta badge, new/resolved finding cards, and native collapsible top-5 sample tables**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-04-26T22:45:00Z
- **Completed:** 2026-04-26T23:00:00Z
- **Tasks:** 2 (Tasks 1-2 complete; Task 3 is human checkpoint)
- **Files modified:** 5

## Accomplishments

- Added `SampleFinding` and `TrendReport` TypeScript interfaces to `types/api.ts` — snake_case fields exactly mirroring the Plan 02 Pydantic schemas
- Created `useTrendsData` hook with empty deps array, cancelled-flag cleanup, and loading/error state shape consistent with `useScanData`
- Built full `TrendsPage` component handling all four render states: loading skeleton, API error, baseline empty state (no previous session), and full two-session report
- Wired route and sidebar entry; TypeScript compiles with zero errors across all five files

## Task Commits

Each task was committed atomically:

1. **Task 1: TypeScript types + useTrendsData hook** - `3abb75d` (feat)
2. **Task 2: TrendsPage component + route + sidebar entry** - `72a1faf` (feat)
3. **Task 3: Human verify Trends page rendering** - awaiting checkpoint approval

## Files Created/Modified

- `src/dashboard/src/types/api.ts` — Appended `SampleFinding` and `TrendReport` interfaces (+24 lines)
- `src/dashboard/src/hooks/useTrendsData.ts` — New hook, 50 lines
- `src/dashboard/src/pages/trends.tsx` — TrendsPage component, 148 lines
- `src/dashboard/src/App.tsx` — Added import + `/trends` Route (+2 lines)
- `src/dashboard/src/components/sidebar.tsx` — Added `TrendingUp` to lucide import + NAV_ITEMS entry (+2 lines)

## Decisions Made

- **Empty deps array in useTrendsData:** Trends endpoint takes no parameters (unlike useScanData which re-fetches on `selectedScanId` changes). Empty `[]` deps array is correct per PATTERNS.md.
- **Native details/summary for collapsible tables:** shadcn `Collapsible` is not installed in the dashboard project (confirmed in PATTERNS.md warning #2 and RESEARCH.md). Native HTML is the correct zero-dependency approach.
- **snake_case TypeScript interfaces:** Field names mirror the JSON response exactly. No camelCase adapter needed; React renders them directly as display values.
- **ScoreDeltaBadge variant logic:** `delta > 0` = green (improvement), `delta < 0` = red (regression), `delta === 0` = muted, `delta === null` = outline "First scan" per D-10 and UI-SPEC.

## Deviations from Plan

None — plan executed exactly as written. All five files match the plan's action blocks verbatim.

## Threat Surface Scan

T-31-03-01 (XSS) mitigated: all `f.host`, `f.protocol`, `f.severity` values are React text children;
React auto-escapes by default. No raw-HTML injection props are used (verified: count = 0 in trends.tsx).

No new network endpoints, auth paths, or schema changes introduced beyond the plan's declared trust boundary (same-origin fetch to `/api/trends`).

## Known Stubs

None. The `delta === null` guard in `ScoreDeltaBadge` is intentional baseline logic (first scan has no previous session), not a placeholder stub.

## Issues Encountered

- `npx tsc` installed the wrong package (npm package named `tsc` at version 2.0.4 — not TypeScript). Used `node_modules/.bin/tsc` after running `npm install` in the worktree. No impact on output.

## Next Phase Readiness

- Frontend is complete and type-safe; awaiting human verification at Task 3 checkpoint
- Plan 04 (docs update) can proceed after checkpoint approval
- No blockers identified

## Self-Check: PASSED

- [x] `src/dashboard/src/types/api.ts` — exists, exports SampleFinding + TrendReport
- [x] `src/dashboard/src/hooks/useTrendsData.ts` — exists, exports useTrendsData
- [x] `src/dashboard/src/pages/trends.tsx` — exists, exports TrendsPage
- [x] `src/dashboard/src/App.tsx` — contains `/trends` route and TrendsPage import
- [x] `src/dashboard/src/components/sidebar.tsx` — contains TrendingUp icon and `/trends` entry
- [x] TypeScript: zero errors (`node_modules/.bin/tsc --noEmit`)
- [x] Commits: 3abb75d (Task 1) and 72a1faf (Task 2) verified in git log

---
*Phase: 31-trend-analysis*
*Completed: 2026-04-26 (Tasks 1-2; Task 3 checkpoint pending)*
