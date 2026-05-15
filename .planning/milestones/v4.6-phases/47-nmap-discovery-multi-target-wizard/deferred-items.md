# Phase 47 — Deferred Items

## Pre-existing Test Failures (out of scope for 47-01)

Discovered during Task 3 full regression sweep. Both failures existed before
any Phase 47 code was written (confirmed by `git stash` / `git stash pop` test).

### 1. `tests/test_cbom_schema_validation.py::test_cbom_validates_against_cyclonedx_1_6[broker]`
- **Root cause:** `cyclonedx-python-lib[json-validation]` extra not installed in dev environment.
- **Fix:** Plan 47-03 Task 1 swaps `cyclonedx-python-lib[validation]` → `[json-validation]` in pyproject.toml and installs the extra.
- **Scope:** Owned by 47-03.

### 2. `tests/test_interactive_mode.py::TestConnectorLabelsNoStub`, `TestScannerEnables`, `TestProfileSelection`, `TestDataClassificationUnified`
- **Root cause:** 4 tests in test_interactive_mode.py use a MINIMAL_INPUTS input sequence that was already misaligned with the actual interactive_config() prompt sequence before Phase 47 began. Our single-prompt change (D-01) did NOT change the failure count or which tests fail (confirmed by comparing git stash state).
- **Fix:** Phase 47 does not own these tests. They require an input-sequence update when interactive.py prompt order is formally finalized.
- **Scope:** Out of scope for Phase 47; log for future housekeeping phase.
