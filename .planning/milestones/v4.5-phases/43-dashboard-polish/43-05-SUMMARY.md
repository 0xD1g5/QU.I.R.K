---
phase: 43-dashboard-polish
plan: "05"
subsystem: dashboard
tags: [a11y, pagination, bug-fix, uat-gap-closure]
requirements: [DASH-07, DASH-08]

dependency_graph:
  requires: []
  provides:
    - "Accurate a11y summary PASS/FAIL based on new-violation delta"
    - "Pagination bar hidden on single-page datasets in Findings and Identity pages"
  affects:
    - src/dashboard/tests/a11y/run-a11y.mjs
    - src/dashboard/src/pages/findings.tsx
    - src/dashboard/src/pages/identity.tsx

tech_stack:
  added: []
  patterns:
    - "JSX conditional rendering with short-circuit {expr && (<JSX>)} for absent-not-disabled UI"
    - "Let variable declaration before if/else branch for cross-branch accumulation"

key_files:
  created: []
  modified:
    - src/dashboard/tests/a11y/run-a11y.mjs
    - src/dashboard/src/pages/findings.tsx
    - src/dashboard/src/pages/identity.tsx

decisions:
  - "Initialize newViolationsCount = 0 before the UPDATE_BASELINES branch so the variable is always in scope for the summary.push — UPDATE_BASELINES mode leaves it as 0, diff mode assigns newViolations.length"
  - "Use conditional rendering {table.getPageCount() > 1 && (...)} rather than CSS visibility to truly remove pagination DOM from the tree, not just hide it"

metrics:
  duration: "8 minutes"
  completed: "2026-05-02"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 3
---

# Phase 43 Plan 05: UAT Gap Closure — A11y Summary and Phantom Pagination Summary

Fixed two UAT-identified gaps: a11y harness summary now uses new-violation delta (not raw axe count) for PASS/FAIL, and Findings/Identity pagination bars are absent (not disabled) on single-page datasets.

## What Was Built

### Task 1: Fix a11y summary to use baseline-delta count (commit 4b001a5)

The `run-a11y.mjs` harness computed `newViolations` (a filtered set of violations not in the baseline) per route but pushed `results.violations.length` (raw axe total) to the summary array. This caused routes to show `FAIL` in the summary even when all violations were in the baseline.

Fix: declare `let newViolationsCount = 0` before the `UPDATE_BASELINES` branch, assign `newViolationsCount = newViolations.length` inside the diff-mode else block after the filter, then push `newViolationsCount` in `summary.push`. The `UPDATE_BASELINES` path naturally leaves it as 0.

**Result:** Routes with baseline violations but zero new violations now correctly show `PASS` in the summary block.

### Task 2: Guard pagination bar on single-page datasets (commit d862573)

The pagination `<div>` in `findings.tsx` and `identity.tsx` rendered unconditionally. When `pageSize=25` and fewer than 25 rows exist, `table.getPageCount()` returns 1 and both buttons appear in a permanently-disabled state — visible in the DOM but functionally absent, causing UAT confusion.

Fix: wrap the entire pagination `<div>` in `{table.getPageCount() > 1 && (...)}` in both files. The element is now absent from the DOM entirely on single-page datasets.

**Result:** Pagination controls are completely absent when all findings or identity items fit on one page.

## Deviations from Plan

None — plan executed exactly as written.

## Verification Results

1. `grep -n "newViolationsCount" tests/a11y/run-a11y.mjs` — 3 lines: declaration (147), assignment (183), usage in summary.push (209)
2. `grep "results.violations.length" ... | grep "summary.push"` — no output (confirms raw count removed from summary)
3. `grep -c "getPageCount() > 1" src/pages/findings.tsx src/pages/identity.tsx` — 1 each
4. TypeScript build: `tsc --noEmit` exits 0 with no errors

## Self-Check: PASSED

- `src/dashboard/tests/a11y/run-a11y.mjs` — modified, committed 4b001a5
- `src/dashboard/src/pages/findings.tsx` — modified, committed d862573
- `src/dashboard/src/pages/identity.tsx` — modified, committed d862573
- Both commits verified in git log
