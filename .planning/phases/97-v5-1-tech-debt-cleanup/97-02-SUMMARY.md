---
phase: 97-v5-1-tech-debt-cleanup
plan: "02"
subsystem: scanner
tags: [rest-fuzzer, cascade, back-off, timeout, td-02, tdd]

# Dependency graph
requires:
  - phase: 96-active-rest-fuzzing
    provides: rest_fuzzer.py with consecutive_5xx cascade tracker (WR-03 finding source)

provides:
  - Combined failure-cascade counter covering 5xx responses AND connection/request exceptions
  - Regression test proving exception-only cascade trips the pause at _CONSECUTIVE_5XX_LIMIT
  - consecutive_failures variable replacing consecutive_5xx across all 5 sites

affects:
  - rest-fuzzer cascade behavior for timeout-only or flaky hosts
  - any future phase modifying quirk/scanner/rest_fuzzer.py dispatch loop

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "D-06: increment consecutive_failures on exception instead of reset; break at _CONSECUTIVE_5XX_LIMIT"
    - "TDD RED/GREEN cycle: failing test committed before implementation fix"
    - "safe_str wraps exception text in all new log messages (T-97-04)"

key-files:
  created:
    - tests/test_rest_fuzzer_cascade.py
  modified:
    - quirk/scanner/rest_fuzzer.py

key-decisions:
  - "Renamed consecutive_5xx to consecutive_failures for semantic clarity (Claude's Discretion per CONTEXT.md)"
  - "Exception branch: increment + cascade-limit check mirrors 5xx tracker structure (lines 612-616)"
  - "Counter resets to 0 only on genuine success response — all 5 sites updated consistently"
  - "safe_str applied to exception text in new pause-warning log line (T-97-04 mitigation)"

patterns-established:
  - "Pattern: combined failure counter covers both status-level and connection-level failures"

requirements-completed: [TD-02]

# Metrics
duration: 15min
completed: 2026-05-23
---

# Phase 97 Plan 02: v5.1 Tech-Debt Cleanup — TD-02 Summary

**REST fuzzer combined failure-cascade counter: connection exceptions now increment toward _CONSECUTIVE_5XX_LIMIT so timeout-only servers cannot escape the back-off pause**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-05-23
- **Completed:** 2026-05-23
- **Tasks:** 1 (TDD — RED commit + GREEN commit)
- **Files modified:** 2

## Accomplishments

- Fixed the TD-02 / D-06 cascade bug: `consecutive_5xx = 0` on exception replaced with increment + limit check
- Renamed `consecutive_5xx` to `consecutive_failures` across all 5 sites (init, exception branch, 5xx tracker ×2, alg-confusion path) for semantic clarity
- Cascade pause now activates after `_CONSECUTIVE_5XX_LIMIT` consecutive failures regardless of whether they are 5xx responses or connection exceptions
- Counter resets to 0 only on a genuine success response (2xx/3xx/<500, no exception) — existing reset-on-success semantics preserved
- Added `tests/test_rest_fuzzer_cascade.py` with 3 regression tests (TDD cycle)
- All 44 fuzzer tests pass (gate + probes + new cascade tests)

## Task Commits

TDD execution:

1. **RED — Failing test for TD-02 exception-cascade bug** - `8900c0a` (test)
2. **GREEN — Fix: exceptions count toward cascade limit (D-06)** - `9b23f08` (feat)

## Files Created/Modified

- `quirk/scanner/rest_fuzzer.py` — renamed `consecutive_5xx` → `consecutive_failures`; exception branch increments + cascade-limit check; 5xx tracker and alg-confusion path updated; `_CONSECUTIVE_5XX_LIMIT` docstring updated
- `tests/test_rest_fuzzer_cascade.py` — 3 tests: exception-only cascade trips pause, success resets counter, 5xx-only cascade no-regression

## Decisions Made

- Renamed `consecutive_5xx` → `consecutive_failures` per Claude's Discretion in CONTEXT.md — communicates combined semantics more accurately without requiring a second constant
- Exception branch log message includes `failure N/limit` counters for operator visibility; exception text passed through `safe_str` (T-97-04)
- TDD RED/GREEN committed separately per plan's `tdd="true"` directive

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- TD-02 closed; `consecutive_failures` counter now covers all failure modes in the fuzz dispatch loop
- Phase 97 Plans 03 and 04 (TD-01 credential handling items) are unaffected by this change
- No pending todos from this plan

---

## Self-Check

- `tests/test_rest_fuzzer_cascade.py` — FOUND
- `quirk/scanner/rest_fuzzer.py` — FOUND (modified)
- RED commit `8900c0a` — FOUND
- GREEN commit `9b23f08` — FOUND

## Self-Check: PASSED

---

*Phase: 97-v5-1-tech-debt-cleanup*
*Completed: 2026-05-23*
