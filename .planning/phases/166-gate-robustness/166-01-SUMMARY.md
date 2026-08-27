---
phase: 166-gate-robustness
plan: 01
subsystem: testing
tags: [e2e, puppeteer, radix, dashboard, ci-gate]

# Dependency graph
requires: []
provides:
  - "E2E smoke test selects the `common` port scope through the real form control before submitting, dropping the top1000/nmap sweep"
  - "SCAN_TIMEOUT_MS raised from 120s to 180s as headroom"
  - "PASS-path console log of measured scan wall-clock for future drift visibility"
affects: [166-02, 166-03, 166-04]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Puppeteer driving a Radix RadioGroup: click the button[role=\"radio\"] by its id, then waitForSelector on aria-checked=\"true\" to close the React-state race before submitting a form"

key-files:
  created: []
  modified:
    - src/dashboard/tests/e2e/run-e2e.mjs

key-decisions:
  - "Selected common port scope via page.click('#scope-common') + aria-checked wait, not page.select() — the control is a Radix RadioGroup, not a Select (CONTEXT.md's original wording was corrected by research)"
  - "Budget raised to 180s is headroom only; the narrowed common scope (17-port direct TCP connect, no nmap) is the primary lever for making the gate pass on ordinary hardware"
  - "Wall-clock logging is informational only — no second hard assertion, no soft-fail warn threshold; SCAN_TIMEOUT_MS on the waitForFunction remains the single enforcement point"

patterns-established:
  - "Puppeteer + Radix RadioGroup: page.click('#id') then waitForSelector('#id[aria-checked=\"true\"]') before any dependent form submission"

requirements-completed: [GATE-01]

# Metrics
duration: 12min
completed: 2026-08-27
---

# Phase 166 Plan 01: E2E Smoke Scope Narrowing Summary

**Narrowed the E2E smoke scan's port scope from the form's `top1000` default to `common` via the real Radix RadioGroup control, raised the scan budget to 180s as headroom, and added PASS-path wall-clock logging — making `npm run e2e:smoke` satisfiable on ordinary developer hardware without weakening its coverage.**

## Performance

- **Duration:** 12 min
- **Started:** 2026-08-27T14:54:00Z
- **Completed:** 2026-08-27T15:06:52Z
- **Tasks:** 2 completed
- **Files modified:** 1

## Accomplishments
- E2E Phase 2 scan submission now clicks `#scope-common` and waits for `aria-checked="true"` before clicking Run Scan, closing the React-state race that could silently fall back to the `top1000`/nmap default.
- `SCAN_TIMEOUT_MS` raised from `120_000` to `180_000` with an inline comment explaining the headroom rationale.
- PASS path now logs `[e2e] Scan wall-clock: <N>s (budget 180s)` so future budget drift is visible in CI output without adding a second hard assertion.
- `src/dashboard/src/pages/scan-new.tsx` confirmed untouched (`git diff --name-only` across both commits shows only `run-e2e.mjs`).

## Task Commits

Each task was committed atomically:

1. **Task 1: Select the common port scope in the E2E scan submission** - `51e7ba0` (feat)
2. **Task 2: Raise the scan budget to 180s and log actual scan wall-clock** - `9d47269` (feat)

_Note: both tasks modified the same file (`run-e2e.mjs`); commits were split by isolating each task's hunk before staging, so each commit contains only that task's diff._

## Files Created/Modified
- `src/dashboard/tests/e2e/run-e2e.mjs` - Added `#scope-common` selection with `aria-checked` confirmation before form submission; raised `SCAN_TIMEOUT_MS` to 180s; added scan wall-clock logging on the PASS path.

## Deviations from Plan

None - plan executed exactly as written.

## Verification

- `node --check src/dashboard/tests/e2e/run-e2e.mjs` exits 0.
- `git diff --name-only HEAD~2 HEAD` shows only `src/dashboard/tests/e2e/run-e2e.mjs` changed — `scan-new.tsx` is untouched.
- `grep -n "page.click('#scope-common')"` returns exactly one line, preceding the `page.evaluate` block that clicks `Run Scan`.
- `grep -n 'aria-checked="true"'` returns a line referencing `#scope-common`.
- `grep -c "page.select("` and `grep -cE "fetch\(.*(/api/scan|/api/jobs)"` both return 0.
- `grep -c "120_000"` returns 0; `grep -c "SCAN_TIMEOUT_MS = 180_000"` returns 1.
- `scanStartedAt` appears at both assignment and use; no `report(` call references it or any elapsed-duration variable.
- A full local `npm run e2e:smoke` run is deferred to plan 166-04's verification task per the plan's `<verification>` section (needs the full phase merged and is environment-sensitive).

## Self-Check: PASSED

- FOUND: src/dashboard/tests/e2e/run-e2e.mjs
- FOUND: 51e7ba0 (git log --oneline --all)
- FOUND: 9d47269 (git log --oneline --all)
