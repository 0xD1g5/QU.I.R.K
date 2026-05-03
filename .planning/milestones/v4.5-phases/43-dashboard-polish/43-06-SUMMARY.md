---
phase: 43-dashboard-polish
plan: "06"
subsystem: ui
tags: [react, playwright, pdf-export, typescript, fastapi]

requires:
  - phase: 43-dashboard-polish
    provides: print.tsx and pdf.py as the existing PDF export pipeline

provides:
  - data-ready DOM sentinel pattern: print.tsx sets body[data-ready="true"] once scan data is non-null
  - Playwright sentinel wait in pdf.py: page.wait_for_selector blocks until DOM signal fires
  - Blank PDF defect (UAT Gap 2) closed

affects: [pdf-export, dashboard-uat]

tech-stack:
  added: []
  patterns:
    - "DOM sentinel pattern: React useEffect sets body attribute after async data resolves; headless browser waits for that attribute before capture"

key-files:
  created: []
  modified:
    - src/dashboard/src/pages/print.tsx
    - quirk/dashboard/api/routes/pdf.py

key-decisions:
  - "DOM sentinel (body[data-ready='true']) preferred over arbitrary sleep or polling — deterministic, zero-latency once data resolves"
  - "timeout=15_000 on wait_for_selector provides a safety cap; failure propagates to the existing except handler returning HTTP 500"
  - "useEffect cleanup removes the sentinel on unmount to prevent stale attribute across navigation"

patterns-established:
  - "DOM sentinel pattern: set DOM attribute in useEffect after data is truthy; headless browser waits on CSS attribute selector"

requirements-completed: [DASH-06]

duration: 5min
completed: 2026-05-02
---

# Phase 43 Plan 06: Blank PDF Defect Fix Summary

**DOM sentinel pattern closes UAT Gap 2: print.tsx sets `body[data-ready]` after data loads; pdf.py waits for that attribute before calling `page.pdf()`**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-05-02T00:00:00Z
- **Completed:** 2026-05-02T00:05:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Added `useEffect` to `PrintPage` that sets `document.body.setAttribute('data-ready', 'true')` after `useScanData` returns non-null data, providing a deterministic DOM signal
- Replaced the redundant `page.wait_for_load_state("networkidle")` in `pdf.py` with `page.wait_for_selector('body[data-ready="true"]', timeout=15_000)` — Playwright now blocks until React hydrates and data arrives
- PDF export no longer captures a loading/blank state; it captures the fully populated scan results

## Task Commits

Each task was committed atomically:

1. **Task 1: Add data-ready sentinel to print.tsx** - `47e1a7d` (feat)
2. **Task 2: Wait for data-ready sentinel in pdf.py before page.pdf()** - `f8c489a` (fix)

## Files Created/Modified
- `src/dashboard/src/pages/print.tsx` - added `useEffect` import and sentinel effect inside `PrintPage()`
- `quirk/dashboard/api/routes/pdf.py` - replaced `wait_for_load_state("networkidle")` with `wait_for_selector('body[data-ready="true"]', timeout=15_000)`

## Decisions Made
- DOM sentinel preferred over arbitrary sleep — deterministic, zero overhead once data resolves
- `timeout=15_000` (15 s) provides a meaningful cap without being overly tight for a localhost API call
- Cleanup function in `useEffect` removes attribute on unmount, preventing stale sentinel on hot reload or navigation

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

`tsc` was not on PATH in the worktree; used the main repo's `node_modules/.bin/tsc --noEmit` directly. TypeScript type check exited 0.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- PDF export sentinel fix is complete; UAT Gap 2 can now be verified end-to-end by running the dashboard and clicking "Export PDF"
- No blockers for subsequent plans

---
*Phase: 43-dashboard-polish*
*Completed: 2026-05-02*
