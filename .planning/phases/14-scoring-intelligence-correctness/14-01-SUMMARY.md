---
phase: 14-scoring-intelligence-correctness
plan: "01"
subsystem: testing
tags: [scoring, intelligence, validate, migration-advisor, dashboard, tdd, red-scaffold]

requires:
  - phase: 13-interactive-mode-overhaul
    provides: 215 passing tests, stable interactive.py baseline
provides:
  - RED test scaffold confirming SCORE-02 and SCORE-04 bugs exist
  - Regression guards for SCORE-01 (profile multipliers) and SCORE-03 (migration advisor matching)
affects:
  - 14-02 (must make all 4 new failing tests GREEN)

tech-stack:
  added: []
  patterns:
    - "RED-first TDD: test file created before fixes; SCORE-02 and SCORE-04 tests fail against current code"
    - "inspect.signature + inspect.getsource used to test API contracts without running live routes"

key-files:
  created:
    - tests/test_scoring_correctness.py
  modified: []

key-decisions:
  - "SCORE-01 and SCORE-03 tests are GREEN regression guards — profiles and migration matching already correct after Phase 08/09"
  - "SCORE-02 tests verify require_delta_if_baseline must be removed from validate_run signature and main() argparse"
  - "SCORE-04 tests use inspect.getsource on get_latest_scan to assert profile= kwarg and calibration field presence"
  - "calibration field (not assessment) is the correct read target per Research Pitfall 2"

patterns-established:
  - "Source inspection pattern: inspect.getsource(fn) used to assert code structure contracts in dashboard routes without standing up FastAPI"

requirements-completed: [SCORE-01, SCORE-02, SCORE-03, SCORE-04]

duration: 2min
completed: 2026-04-07
---

# Phase 14 Plan 01: Scoring Correctness RED Scaffold Summary

**7-test RED scaffold covering SCORE-01 through SCORE-04: profile multipliers verified, validate.py dead param caught, migration advisor regression-guarded, dashboard profile gap exposed**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-07T00:08:17Z
- **Completed:** 2026-04-07T00:09:23Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Created `tests/test_scoring_correctness.py` with 7 test methods across 4 classes
- Confirmed SCORE-02 is RED: `require_delta_if_baseline` still in `validate_run` signature and `main()` argparse (2 failing tests)
- Confirmed SCORE-04 is RED: `get_latest_scan` calls `compute_readiness_score(evidence)` without `profile=` and no `calibration` reference (2 failing tests)
- Confirmed SCORE-01 and SCORE-03 are GREEN regression guards (profile multipliers and migration advisor already correct)
- Zero regressions — 215 existing tests still pass

## Task Commits

1. **Task 1: Write RED test scaffold for SCORE-01 through SCORE-04** - `6b90692` (test)

## Files Created/Modified

- `tests/test_scoring_correctness.py` — 7-test RED scaffold for all 4 SCORE requirements

## Decisions Made

- SCORE-01 and SCORE-03 tests are permanent regression guards; they pass immediately because phases 08 and 09 already fixed those subsystems
- SCORE-02 RED assertion targets both the function signature (`inspect.signature`) and the argparse wiring (`inspect.getsource(main)`)
- SCORE-04 RED assertion uses `inspect.getsource(get_latest_scan)` to catch the missing `profile=` kwarg and missing `calibration` field reference — avoids needing a live database for the test

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## Known Stubs

None — this plan creates tests only, no UI data stubs.

## Next Phase Readiness

- Plan 02 has a precise contract: make SCORE-02 and SCORE-04 tests GREEN while keeping SCORE-01 and SCORE-03 GREEN
- Fix targets are exactly identified:
  - `quirk/validate.py:105` — remove `require_delta_if_baseline` param and `main()` argparse arg
  - `quirk/dashboard/api/routes/scan.py:330` — add `profile=` kwarg reading from `calibration.profile`

## Self-Check: PASSED

- tests/test_scoring_correctness.py: FOUND
- Commit 6b90692: FOUND

---
*Phase: 14-scoring-intelligence-correctness*
*Completed: 2026-04-07*
