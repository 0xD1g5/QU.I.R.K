---
phase: 15-code-hygiene
plan: "01"
subsystem: testing
tags: [pytest, unittest, ast, pathlib, tdd, hygiene]

# Dependency graph
requires:
  - phase: 14-scoring-intelligence-correctness
    provides: test patterns using inspect.getsource structural assertions
provides:
  - Wave 0 TDD scaffold for HYGN-01 through HYGN-04 code hygiene requirements
  - Regression tests guarding quirk/connectors/ absence (HYGN-01)
  - Structural source assertion tests for cfg.scan mutation guard (HYGN-02)
  - RED tests asserting scorecard.py deletion required (HYGN-03)
  - RED test asserting all 14 completed phase VALIDATION.md files need nyquist_compliant: true (HYGN-04)
affects: [15-02-code-hygiene-implementation]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "pathlib.Path.rglob('*.py') + ast.parse + ast.walk for codebase-wide import auditing"
    - "inspect.getsource(module) + line-by-line structural assertion for try/finally placement verification"
    - "re.match frontmatter extraction for YAML VALIDATION.md compliance checks"

key-files:
  created:
    - tests/test_hygiene.py
  modified: []

key-decisions:
  - "HYGN-02 SSH test uses inspect.getsource structural assertion (not mock injection) to detect that mutations precede the try block — matches Phase 14 pattern for validate.py"
  - "HYGN-04 test covers all 14 completed phases (not the 11 mentioned in REQUIREMENTS.md) because phases 12-14 were added after the requirement was written"
  - "HYGN-03 import scan restricted to quirk/ production code only (not tests/) since test_reports_scorecard.py importing scorecard is expected and will be deleted in Plan 02"

patterns-established:
  - "Wave 0 TDD scaffold: write RED tests first, implement in Plan 02"
  - "No @unittest.expectedFailure decorators — actual RED state confirms problems exist"

requirements-completed:
  - HYGN-01
  - HYGN-02
  - HYGN-03
  - HYGN-04

# Metrics
duration: 2min
completed: 2026-04-08
---

# Phase 15 Plan 01: Code Hygiene TDD Scaffold Summary

**7-test Wave 0 scaffold asserting quirk/connectors/ absent (GREEN), cfg.scan SSH mutation guard structure (RED), scorecard.py absent (RED), and all 14 phase VALIDATION.md files nyquist_compliant (RED)**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-08T02:22:23Z
- **Completed:** 2026-04-08T02:24:02Z
- **Tasks:** 1 of 1
- **Files modified:** 1

## Accomplishments

- Created `tests/test_hygiene.py` with 7 test functions covering all 4 HYGN requirements
- HYGN-01 tests pass immediately (2 GREEN): regression guards that quirk/connectors/ directory is absent and no imports exist from quirk.connectors
- HYGN-02 TLS test passes (GREEN): structural assertion that base_timeout is captured before mutation and finally restores it
- HYGN-02 SSH test fails (RED): detects that cfg.scan mutations at lines 380-381 precede the try: block at line 384 — defines Plan 02 fix target
- HYGN-03 tests: scorecard.py absent assertion RED (file still present); no production scorecard imports GREEN
- HYGN-04 test fails (RED): 11 stale VALIDATION.md files + 2 missing files discovered across all 14 completed phases

## Task Commits

1. **Task 1: Create test_hygiene.py TDD scaffold with 7 RED/GREEN tests** - `9a6aa81` (test)

**Plan metadata:** (final commit follows this summary)

## Files Created/Modified

- `tests/test_hygiene.py` - Wave 0 TDD scaffold: 7 tests for HYGN-01 through HYGN-04, 4 GREEN/3 RED

## Decisions Made

- HYGN-02 SSH test uses `inspect.getsource(run_scan)` structural assertion matching the Phase 14 pattern: find the SSH section, find try_line_idx and mutation_line_idx, assert mutation_line > try_line. This is RED because lines 380-381 precede try: at line 384.
- HYGN-04 test covers all 14 completed phases rather than the 11 in REQUIREMENTS.md since phases 12-14 were added after the requirement was written. This matches the RESEARCH.md finding.
- Import scan for HYGN-03 scans only `quirk/` (production code), not `tests/` — test_reports_scorecard.py importing scorecard is expected and will be deleted alongside scorecard.py in Plan 02.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 02 (15-02) ready to execute: delete quirk/reports/scorecard.py and tests/test_reports_scorecard.py, move SSH cfg.scan mutations inside try block, update 13 VALIDATION.md files
- 3 RED tests provide clear implementation targets for Plan 02
- No blockers

## Known Stubs

None — this plan only creates test infrastructure, no production code stubs.

---
*Phase: 15-code-hygiene*
*Completed: 2026-04-08*
