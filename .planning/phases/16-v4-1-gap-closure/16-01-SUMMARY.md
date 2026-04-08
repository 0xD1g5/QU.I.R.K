---
phase: 16-v4-1-gap-closure
plan: "01"
subsystem: testing
tags: [tdd, red-scaffold, pytest, importlib-metadata, pyproject, interactive-cli]

# Dependency graph
requires:
  - phase: 15-code-hygiene
    provides: clean baseline test suite at 229 passing tests
provides:
  - RED TDD scaffold proving CLI-04 (pyproject.toml manifest version stale) and SCORE-04 (interactive.py output dir default mismatch) gaps exist before Plan 02 fixes land
affects: [16-v4-1-gap-closure Plan 02 — GREEN fixes depend on these RED tests passing after changes]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Phase 16 TDD RED scaffold: source-text inspection via pathlib.Path().read_text() to assert default prompt values"
    - "CLI-04 test uses importlib.metadata.version() not quirk.__version__ — tests the installed package manifest, not the module attribute"

key-files:
  created:
    - tests/test_v41_gap_closure.py
  modified: []

key-decisions:
  - "Used importlib.metadata.version('quirk') not quirk.__version__ for CLI-04 RED test — module attribute already returns 4.1.0; only the installed egg-info is stale"
  - "Source-text inspection approach chosen for SCORE-04 over runtime mock approach — simpler, no mock complexity, directly proves the default string in the prompt call"
  - "No @unittest.expectedFailure decorator — tests are intentionally RED to prove gaps exist before Plan 02 fixes; they should fail visibly"

patterns-established:
  - "Two-plan TDD gap closure: Plan 1 writes RED tests proving gap, Plan 2 applies minimal fix and turns tests GREEN"
  - "pathlib.Path source inspection for asserting specific prompt default values in interactive.py"

requirements-completed: [CLI-04, SCORE-04]

# Metrics
duration: 1min
completed: 2026-04-08
---

# Phase 16 Plan 01: v4.1 Gap Closure RED Scaffold Summary

**4-test RED TDD scaffold proves CLI-04 (pyproject.toml manifest version = 4.0.0) and SCORE-04 (interactive.py output dir defaults to "output" not "quirk-output") gaps exist before Plan 02 fixes**

## Performance

- **Duration:** 1 min
- **Started:** 2026-04-08T03:07:17Z
- **Completed:** 2026-04-08T03:08:15Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Created `tests/test_v41_gap_closure.py` with 4 test functions covering both v4.1 gaps
- All 4 tests fail against current code (RED state), proving both gaps exist before fixes
- Existing 229-test suite remains fully green (0 regressions introduced)

## Task Commits

Each task was committed atomically:

1. **Task 1: Write RED test scaffold for CLI-04 and SCORE-04** - `a0510cf` (test)

## Files Created/Modified

- `tests/test_v41_gap_closure.py` - 4 RED tests: 2 for CLI-04 (importlib.metadata version + pyproject.toml text), 2 for SCORE-04 (interactive.py output dir and db_path prompt defaults)

## Decisions Made

- Used `importlib.metadata.version("quirk")` not `quirk.__version__` for CLI-04 test: the module attribute already returns `"4.1.0"` (not stale), but the installed egg-info still reflects `pyproject.toml` version `"4.0.0"`. Only `importlib.metadata` catches the actual gap.
- Source-text inspection with `pathlib.Path().read_text()` chosen over runtime mock approach for SCORE-04: directly asserts the string literal in the `_prompt()` call without mock complexity; more readable and already established as a pattern in this test suite.
- No `@unittest.expectedFailure` decorators: tests are meant to fail visibly to prove the gap exists before Plan 02 is applied.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- RED scaffold in place; Plan 02 can now apply the two minimal fixes:
  1. Bump `pyproject.toml` line 7 from `"4.0.0"` to `"4.1.0"` and run `pip install -e .`
  2. Change `quirk/interactive.py` lines 165-166 from `"output"` / `"output/quirk.db"` to `"quirk-output"` / `"quirk-output/quirk.db"`
- All 4 RED tests will turn GREEN after Plan 02 fixes are applied and package is reinstalled

## Self-Check: PASSED

- FOUND: tests/test_v41_gap_closure.py
- FOUND: .planning/phases/16-v4-1-gap-closure/16-01-SUMMARY.md
- FOUND: commit a0510cf

---
*Phase: 16-v4-1-gap-closure*
*Completed: 2026-04-08*
