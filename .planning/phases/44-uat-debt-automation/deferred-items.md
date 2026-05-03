# Phase 44 Deferred Items

## Pre-existing skip_registry drift (out of scope for 44-01)

Found during 44-01 Task 2 verification. `test_skip_registry.py` meta-test was already
failing before 44-01 work due to drift in unrelated files:

1. `test_cbom_classifier_coverage.py:84` — `@pytest.mark.skipif` not registered in
   `tests/skip_registry.py` at all. Added during a CBOM phase.

2. `test_cbom_motion_golden.py:195` — registered at line 189 (±2 tolerance fails at
   delta=6). Test file grew by ~6 lines since registration.

**Action needed:** A future plan (likely 44-06 or a separate cleanup plan) should add
`("test_cbom_classifier_coverage.py", 84, "live_infra", "REGEN_CBOM_COVERAGE guard")`
and update `("test_cbom_motion_golden.py", 195, ...)` in `tests/skip_registry.py`.

These violations are pre-existing and not caused by 44-01 changes.
