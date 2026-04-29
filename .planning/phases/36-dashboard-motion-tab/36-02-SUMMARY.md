---
phase: 36-dashboard-motion-tab
plan: "02"
subsystem: dashboard-ui
tags: [dashboard, react, typescript, react-router-dom, lucide-react, scaffolding]

requires:
  - phase: 36-01
    provides: [MotionFinding Pydantic model, SubScores.data_in_motion, ScanLatestResponse.motion_findings]
provides:
  - SubScores.data_in_motion TypeScript field (non-optional number)
  - MotionFinding TypeScript interface (mirrors Pydantic shape exactly)
  - ScanLatestResponse.motion_findings TypeScript field (non-optional array)
  - 6th ScoreGauge for Data in Motion in ExecutivePage
  - Motion sidebar nav entry (Activity icon, /motion path, between Identity and Certificates)
  - /motion Route registered in App.tsx flat Routes block
  - Placeholder motion.tsx enabling clean tsc -b at wave 2 boundary
affects: [36-03, src/dashboard/src/pages/motion.tsx (Plan 36-03 replaces placeholder body)]

tech-stack:
  added: []
  patterns:
    - TypeScript interface mirrors Pydantic model field-for-field (no drift)
    - Placeholder page export enables clean tsc -b before full implementation lands
    - Flat react-router-dom v7 Routes/Route siblings (no Outlet/nested routes)

key-files:
  created:
    - src/dashboard/src/pages/motion.tsx (placeholder — replaced by Plan 36-03)
  modified:
    - src/dashboard/src/types/api.ts
    - src/dashboard/src/pages/executive.tsx
    - src/dashboard/src/components/sidebar.tsx
    - src/dashboard/src/App.tsx

key-decisions:
  - "Used placeholder motion.tsx stub (export function MotionPage() { return null }) so tsc -b is clean at wave 2 boundary; Plan 36-03 replaces the body"
  - "motion_findings and plaintext_exposed and starttls_warning are NON-optional in TS — mirrors Pydantic defaults, server always returns them"
  - "Activity icon from lucide-react used for Motion nav entry — matches existing icon convention"

patterns-established:
  - "New dashboard tab pattern: extend api.ts -> add ScoreGauge to executive -> add sidebar NAV_ITEM -> register Route -> stub page for clean build"

requirements-completed: [DASH-01, DASH-04]

duration: ~11min
completed: 2026-04-29
---

# Phase 36 Plan 02: Frontend Scaffolding — Motion Tab Wiring Summary

**React dashboard wired for Motion tab: TS api.ts extended with MotionFinding interface and data_in_motion subscore, 6th ScoreGauge added to executive summary, Motion sidebar entry with Activity icon inserted, /motion route registered in App.tsx, placeholder motion.tsx created for clean tsc -b.**

## Performance

- **Duration:** ~11 min
- **Started:** 2026-04-29T01:32:21Z
- **Completed:** 2026-04-29T01:43:11Z
- **Tasks:** 4
- **Files modified:** 5

## Accomplishments

- Extended `src/dashboard/src/types/api.ts` with `SubScores.data_in_motion`, the `MotionFinding` interface (15 fields, 2 non-optional booleans), and `ScanLatestResponse.motion_findings` — all mirroring Plan 36-01's Pydantic shapes exactly
- Added the 6th `ScoreGauge` for Data in Motion to `executive.tsx` gauge row and bumped loading skeleton from `length: 5` to `length: 6`
- Added Motion sidebar nav entry (`{ path: "/motion", label: "Motion", Icon: Activity }`) between Identity and Certificates with `Activity` imported from `lucide-react`
- Registered `/motion` route in `App.tsx` flat Routes block and imported `MotionPage` from `@/pages/motion`; created placeholder stub so `tsc -b` produces zero errors at wave 2 boundary

## Task Commits

1. **Task 1: Extend TS api.ts** - `3bc2f0c` (feat)
2. **Task 2: 6th ScoreGauge in executive.tsx** - `4264cd1` (feat)
3. **Task 3: Motion sidebar nav entry** - `63de506` (feat)
4. **Task 4: /motion Route in App.tsx + placeholder** - `3375c08` (feat)

## Files Created/Modified

- `src/dashboard/src/types/api.ts` — Added `SubScores.data_in_motion: number`, `export interface MotionFinding` (15 fields), `ScanLatestResponse.motion_findings: MotionFinding[]`
- `src/dashboard/src/pages/executive.tsx` — Skeleton length 5→6; `<ScoreGauge score={score.subscores.data_in_motion} label="Data in Motion" size={120} />` added after data_at_rest gauge
- `src/dashboard/src/components/sidebar.tsx` — `Activity` added to lucide-react import; Motion NAV_ITEMS entry inserted between Identity and Certificates
- `src/dashboard/src/App.tsx` — `import { MotionPage } from "@/pages/motion"` added; `<Route path="/motion" element={<MotionPage />} />` registered between /identity and /certificates
- `src/dashboard/src/pages/motion.tsx` — Placeholder stub: `export function MotionPage() { return null }` — **replaced by Plan 36-03**

## TypeScript Build State

`tsc -b` produces **zero errors** at the end of Plan 36-02. The placeholder stub in `motion.tsx` resolves the `Cannot find module '@/pages/motion'` that would otherwise block wave 2. Plan 36-03 replaces the stub body with the full MotionPage implementation.

## No New Dependencies

No changes to `src/dashboard/package.json` — `Activity` is already part of `lucide-react` (existing dependency). All changes are pure source code edits.

## Decisions Made

- **Placeholder approach chosen** over forward-reference (tsc red): Created `motion.tsx` with `export function MotionPage() { return null }` so the build is clean at the wave 2 boundary. Plan 36-03 replaces the stub. This is the "clean build" path noted as acceptable in the plan's critical pitfalls section.
- **Non-optional TS booleans**: `plaintext_exposed: boolean` and `starttls_warning: boolean` carry no `?` — mirrors Pydantic's non-optional fields with defaults, ensuring TS consumers can read these without null checks.

## Deviations from Plan

None — plan executed exactly as written. The placeholder approach was explicitly offered in the plan's critical pitfalls section as an acceptable alternative to a forward-reference red build.

## Issues Encountered

None.

## Known Stubs

`src/dashboard/src/pages/motion.tsx` contains a placeholder `export function MotionPage() { return null }`. This is intentional per plan design — Plan 36-03 will replace the body with the full Data in Motion tab implementation. The stub is not exposed to any user-visible UI path until Plan 36-03 wires real content.

## Threat Flags

None. Pure TypeScript shape extension and React routing wiring — no new network endpoints, trust boundaries, or data access patterns introduced.

## Next Phase Readiness

- Plan 36-03 can immediately implement `MotionPage` by editing `src/dashboard/src/pages/motion.tsx` — the route, sidebar entry, and TS contract are all in place
- `MotionFinding[]` is ready for consumption via `useScanData()` hook's `data.motion_findings`
- No blockers for 36-03

---
*Phase: 36-dashboard-motion-tab*
*Completed: 2026-04-29*

## Self-Check: PASSED

- `src/dashboard/src/types/api.ts` exists, contains `MotionFinding`, `data_in_motion`, `motion_findings`
- `src/dashboard/src/pages/executive.tsx` exists, contains `subscores.data_in_motion`, `length: 6`, `label="Data in Motion"`
- `src/dashboard/src/components/sidebar.tsx` exists, contains `/motion`, `Activity`
- `src/dashboard/src/App.tsx` exists, contains `MotionPage`, `/motion`
- `src/dashboard/src/pages/motion.tsx` exists (placeholder)
- Task 1 commit: 3bc2f0c
- Task 2 commit: 4264cd1
- Task 3 commit: 63de506
- Task 4 commit: 3375c08
- `tsc -b` clean: confirmed (zero output = zero errors)
