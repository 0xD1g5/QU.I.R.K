---
phase: 09-scoring-consolidation
plan: 01
subsystem: testing
tags: [scoring, profiles, tdd, intelligence, pytest]

# Dependency graph
requires:
  - phase: 08-legacy-debt-cleanup
    provides: single scoring path through intelligence/scoring.py with writer.py consolidated
provides:
  - PROFILE_MULTIPLIERS constant (strict/balanced/lenient) in quirk/intelligence/scoring.py
  - profile= kwarg on compute_readiness_score() with prefix-based weight multiplication
  - Wave 0 RED stubs for executive.py migration (ExecutiveConsolidationTests, 7 expectedFailure)
affects: [09-02, 09-03, scoring, executive-report, calibration]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "profile multipliers applied before weights= override — user overrides always win (D-06)"
    - "expectedFailure as RED stubs for Wave 0 test scaffolding"

key-files:
  created: []
  modified:
    - quirk/intelligence/scoring.py
    - tests/test_intelligence_scoring.py
    - tests/test_scoring_consolidation.py

key-decisions:
  - "D-05/D-06: agility_* and identity_* prefixes multiplied per profile; hygiene_* and modern_tls_* unchanged"
  - "profile= falls back to balanced on unknown name — no error raised"
  - "weights= override applied after profile multiplication — explicit user override always wins"
  - "Wave 0 executive.py stubs use @unittest.expectedFailure until Plan 02 removes them"

patterns-established:
  - "Pattern 1: PROFILE_MULTIPLIERS prefix-loop runs before user weights= so overrides always win"
  - "Pattern 2: Wave 0 RED stubs with expectedFailure express future migration contract without breaking CI"

requirements-completed: [SC-04, SC-05]

# Metrics
duration: 2min
completed: 2026-04-03
---

# Phase 9 Plan 01: Scoring Profile Multipliers and Wave 0 Test Scaffolds Summary

**PROFILE_MULTIPLIERS constant (strict=1.4x, balanced=1.0x, lenient=0.7x) added to compute_readiness_score() with prefix-based agility/identity weight scaling, plus 7 Wave 0 expectedFailure stubs for executive.py migration**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-04-03T16:48:14Z
- **Completed:** 2026-04-03T16:50:17Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Added PROFILE_MULTIPLIERS constant and profile= kwarg to compute_readiness_score() — strict/lenient now produce measurably different scores on identical evidence
- 5 new ProfileWeightTests cover strict vs lenient differentiation, calibration override precedence, profile+override composition, invalid fallback, and balanced=no-profile equivalence
- 7 Wave 0 expectedFailure stubs in ExecutiveConsolidationTests define executive.py migration contract — suite stays green until Plan 02 removes decorators

## Task Commits

Each task was committed atomically:

1. **Task 1: Add PROFILE_MULTIPLIERS and profile param to compute_readiness_score** - `bbf81e8` (feat/test TDD)
2. **Task 2: Extend test_scoring_consolidation.py with Wave 0 stubs for executive.py migration** - `890952c` (test)

## Files Created/Modified

- `quirk/intelligence/scoring.py` - Added PROFILE_MULTIPLIERS constant and profile= kwarg with prefix-based weight multiplication
- `tests/test_intelligence_scoring.py` - Added ProfileWeightTests class with 5 tests (8 total, all green)
- `tests/test_scoring_consolidation.py` - Added _get_executive_source(), ExecutiveConsolidationTests with 7 expectedFailure stubs

## Decisions Made

- agility_* and identity_* prefixes are multiplied per profile; hygiene_* and modern_tls_* are intentionally excluded (D-05)
- profile= falls back to "balanced" silently on unknown values — avoids validation errors for callers passing unsupported profile names
- Wave 0 stubs use @unittest.expectedFailure per-method (not class-level) so individual tests can be unblocked independently in Plan 02

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 02 can begin executive.py migration immediately — Wave 0 stubs define the exact import contract
- All 7 expectedFailure decorators in ExecutiveConsolidationTests are removed in Plan 02 after migration
- SC-04 and SC-05 requirements satisfied; Plan 02 addresses SC-01/SC-02/SC-03

---
*Phase: 09-scoring-consolidation*
*Completed: 2026-04-03*
