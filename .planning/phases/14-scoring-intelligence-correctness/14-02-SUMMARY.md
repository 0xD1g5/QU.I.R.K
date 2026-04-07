---
phase: 14-scoring-intelligence-correctness
plan: "02"
subsystem: scoring
tags: [scoring, intelligence, validate, dashboard, profile, calibration, tdd-green]

requires:
  - phase: 14-scoring-intelligence-correctness
    provides: RED test scaffold for SCORE-02 (validate dead param) and SCORE-04 (dashboard profile gap)

provides:
  - validate_run signature with only output_dir parameter (SCORE-02 fixed)
  - Dashboard compute_readiness_score receives calibration.profile kwarg (SCORE-04 fixed)
  - All 8 SCORE-01 through SCORE-04 tests GREEN

affects:
  - Phase 15 (code-hygiene) — validate.py and dashboard/routes/scan.py are clean baselines

tech-stack:
  added: []
  patterns:
    - "Profile read from calibration.profile in intelligence JSON (not assessment.profile)"
    - "QUIRK_OUTPUT_DIR env var pattern for output path in dashboard routes"
    - "try/except around intelligence JSON read in API route: fallback to profile=None (balanced)"

key-files:
  created: []
  modified:
    - quirk/validate.py
    - quirk/dashboard/api/routes/scan.py

key-decisions:
  - "validate_run now accepts only output_dir: Path — no dead second parameter remains"
  - "Dashboard reads calibration.profile (not assessment.profile) from latest intelligence JSON at request time"
  - "Profile read wrapped in try/except so profile=None fallback to balanced profile on any I/O error"
  - "QUIRK_OUTPUT_DIR env var used for output path in dashboard route, matching deps.py QUIRK_DB_PATH pattern"

patterns-established:
  - "Intelligence JSON read at request time in dashboard routes uses underscore-prefixed locals to avoid shadowing module imports"

requirements-completed: [SCORE-01, SCORE-02, SCORE-03, SCORE-04]

duration: 5min
completed: 2026-04-06
---

# Phase 14 Plan 02: Scoring Intelligence Correctness GREEN Fixes Summary

**SCORE-02 and SCORE-04 made GREEN: dead validate_run parameter removed and dashboard now reads calibration.profile from intelligence JSON to produce profile-aware readiness scores**

## Performance

- **Duration:** 5 min
- **Started:** 2026-04-06T00:00:00Z
- **Completed:** 2026-04-06T00:05:00Z
- **Tasks:** 3
- **Files modified:** 2

## Accomplishments

- Removed dead `require_delta_if_baseline` parameter from `validate_run` signature and `main()` argparse (SCORE-02)
- Wired `calibration.profile` from latest intelligence JSON into `compute_readiness_score(evidence, profile=stored_profile)` in `get_latest_scan` dashboard route (SCORE-04)
- All 8 SCORE tests GREEN: SCORE-01 and SCORE-03 regression guards pass, SCORE-02 and SCORE-04 now also pass
- Full suite: 223 tests passing, zero regressions

## Task Commits

1. **Task 1: Fix SCORE-02 — Remove dead require_delta_if_baseline from validate.py** - `a5e160c` (fix)
2. **Task 2: Fix SCORE-04 — Wire profile from intelligence JSON into dashboard score call** - `5a57eb1` (fix)
3. **Task 3: Verify all SCORE tests GREEN and full suite passes** - verification only, no code changes

## Files Created/Modified

- `quirk/validate.py` — Removed `require_delta_if_baseline` param from `validate_run()` and `main()` argparse
- `quirk/dashboard/api/routes/scan.py` — Added profile-aware score call reading `calibration.profile` from intelligence JSON

## Decisions Made

- validate_run parameter removal is a clean deletion: the function body never referenced the parameter, only the signature and its one internal caller (main()) used it
- Dashboard profile read uses try/except with pass fallback — `profile=None` causes `compute_readiness_score` to default to "balanced" (line 83 of scoring.py), making the fallback safe and observable
- `calibration.profile` (not `assessment.profile`) is confirmed correct per Research Pitfall 2 and the intelligence JSON structure documented in the plan context

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## Known Stubs

None — no UI data stubs introduced. Both fixes wire real data paths.

## Next Phase Readiness

- Phase 14 complete: all 4 SCORE requirements satisfied, 223 tests passing
- Phase 15 (code-hygiene) can proceed with clean validate.py and dashboard scoring baseline
- The calibration.profile read pattern in dashboard routes is now established and can be extended to other dashboard routes if needed

## Self-Check: PASSED

- quirk/validate.py: FOUND
- quirk/dashboard/api/routes/scan.py: FOUND
- Commit a5e160c: FOUND
- Commit 5a57eb1: FOUND

---
*Phase: 14-scoring-intelligence-correctness*
*Completed: 2026-04-06*
