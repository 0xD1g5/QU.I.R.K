---
phase: 41-ci-stability-scanner-robustness
plan: 05
subsystem: testing
tags: [pytest, skip-hygiene, slow-marker, ci-budget]

requires:
  - phase: 41-ci-stability-scanner-robustness
    plan: 01
    provides: skip-registry meta-gate + slow marker config
  - phase: 41-ci-stability-scanner-robustness
    plan: 04
    provides: trends.py + scan_error_category producers
provides:
  - "Stale code-reason skips deleted from tests/ (D-04 13-entry set)"
  - "Defensive pytest.skip in tests/test_version.py converted to pytest.fail"
  - "9 slow-test candidates marked @pytest.mark.slow (8 files)"
  - "Plan 01 AST meta-gate (tests/test_skip_registry.py) is GREEN"
  - "Default `pytest -m 'not slow'` runs in ~6s vs 60s budget"
affects: [41-06, 41-07]

tech-stack:
  added: []
  patterns:
    - "Stale-skip cleanup: hard-import once the dependency lands, delete defensive guards"
    - "@pytest.mark.slow placed ABOVE existing @pytest.mark.skipif for readability"

key-files:
  created: []
  modified:
    - tests/conftest.py
    - tests/test_cloud_connectors.py
    - tests/test_email_scanner.py
    - tests/test_broker_db_schema.py
    - tests/test_version.py
    - tests/test_cli_init.py
    - tests/test_cli_version.py
    - tests/test_chaos_storage.py
    - tests/test_dnssec_scanner.py
    - tests/test_saml_scanner.py
    - tests/test_kerberos_scanner.py
    - tests/test_cbom_motion_golden.py

key-decisions:
  - "tests/test_broker_db_schema.py::test_migration_preserves_existing_rows deleted entirely (always-skip dead path; idempotency covered by test_init_db_twice_no_error)"
  - "tests/test_cloud_connectors.py: dropped _HAS_GCP_MODULE soft-import guard, switched to hard import (gcp_connector.py exists)"
  - "tests/test_email_scanner.py: dropped _skip_scanner helper + 16 decorator usages, switched to hard imports (email_scanner module exists since Phase 32 Plan 03)"
  - "test_cli_version.py target function is test_version_flag (plan named test_cli_version); marked @slow as intended"

requirements-completed: [CI-01, CI-02, CI-03]

duration: ~10 min
completed: 2026-04-29
---

# Phase 41 Plan 05: Stale-Skip Deletion + Slow Marker Wiring Summary

**Deletes 13 stale code-reason skips, converts defensive skips to pytest.fail, marks 9 slow tests, and turns the Plan 01 skip-registry meta-gate green — default `pytest` now runs in ~6s with zero stale skip markers.**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-04-29
- **Completed:** 2026-04-29
- **Tasks:** 2
- **Files modified:** 12 (12 modified, 0 created)

## Accomplishments

- All 13 D-04 stale skips deleted: `tests/conftest.py:111` dashboard guard, 9× `@skipif(not _HAS_GCP_MODULE)` in `test_cloud_connectors.py`, 16× `@_skip_scanner` + helper definition in `test_email_scanner.py`, 1 dead-path skip in `test_broker_db_schema.py`.
- Defensive `pytest.skip` paths in `tests/test_version.py` converted to `pytest.fail` (CLI invokability is a hard requirement, not an acceptable skip).
- 9 slow-test candidates marked `@pytest.mark.slow` across 8 files (subprocess CLI invocations + chaos lab integrations + fixture regen).
- Plan 01's AST-walk skip registry meta-gate (`tests/test_skip_registry.py`) is now GREEN — every remaining skip site is registered in `ALLOWED_SKIPS`.
- `pytest -m 'not slow' tests/` wall-clock: 5.71s (681 passed, 10 deselected). Well under the D-16 60s budget.

## Task Commits

1. **Task 1: Delete stale code-reason skips + convert defensive skips** — `1957782` (fix)
2. **Task 2: Mark slow-test candidates + verify meta-gate green** — `34c3a97` (test)

## Files Created/Modified

- `tests/conftest.py` — `dashboard_client` fixture: `pytest.skip("quirk.dashboard not yet implemented")` → `pytest.fail("quirk.dashboard import failed unexpectedly: ...")` (dashboard exists since Phase 11)
- `tests/test_cloud_connectors.py` — Removed `try/except ImportError` soft-import of `gcp_connector` and 9× `@pytest.mark.skipif(not _HAS_GCP_MODULE, ...)` decorators; module is hard-imported now
- `tests/test_email_scanner.py` — Removed `_EMAIL_SCANNER_AVAILABLE` soft-import block, `_skip_scanner` mark helper, 16× `@_skip_scanner` decorator usages, and the obsolete Wave 0 RED-state docstring; scanner module is hard-imported now
- `tests/test_broker_db_schema.py` — Removed dead `test_migration_preserves_existing_rows` test (its only execution path was a `pytest.skip` because `broker_scan_json` is in `Base.metadata`); cleaned now-unused `text` and `_ensure_broker_columns` imports; idempotency is covered by `test_init_db_twice_no_error`
- `tests/test_version.py` — Converted 2× defensive `pytest.skip(...)` to `pytest.fail(...)` for CLI `--version` invokability; added `@pytest.mark.slow` on `test_cli_version_subprocess`
- `tests/test_cli_init.py` — Added `import pytest` + `@pytest.mark.slow` on both `test_init_creates_config` and `test_init_no_overwrite`
- `tests/test_cli_version.py` — Added `import pytest` + `@pytest.mark.slow` on `test_version_flag`
- `tests/test_chaos_storage.py` — Added `@pytest.mark.slow` above existing `@skipif(QUIRK_RUN_DOCKER_IT)` on both MinIO live tests
- `tests/test_dnssec_scanner.py` — Added `@pytest.mark.slow` above existing `@integration` + `@skipif(QUIRK_INTEGRATION_TESTS)` on `test_chaos_lab_integration`
- `tests/test_saml_scanner.py` — Same pattern for `test_chaos_lab_integration`
- `tests/test_kerberos_scanner.py` — Added `@pytest.mark.slow` above existing `@skipif(QUIRK_KERBEROS_INTEGRATION)` on `test_samba_dc_integration`
- `tests/test_cbom_motion_golden.py` — Added `@pytest.mark.slow` above existing `@skipif(REGEN_CBOM_FIXTURES != "1")` on `test_generate_fixtures`

## Decisions Made

- **Deleted dead test instead of "preserving as assertion":** `test_migration_preserves_existing_rows` in `test_broker_db_schema.py` had only one execution path — `pytest.skip` because `broker_scan_json` is now in `Base.metadata.create_all(engine)`. Reconstructing a real preservation test would require deleting the column from the model temporarily (intrusive) or building an alternate path — and `test_init_db_twice_no_error` already proves migration idempotency end-to-end. Plan explicitly authorized this option ("Choose the cleaner option") so the dead test was removed wholesale.
- **Hard-imported `gcp_connector` and `email_scanner`:** Both modules exist in the codebase (verified via `python -c "import …"`) since the Phase 32 / GCP plan landed. The defensive soft-import was a Wave 0 RED-state vestige no longer earning its keep. Hard imports also ensure that future regressions in those modules surface as collection errors instead of silent skips.
- **`@pytest.mark.slow` placed above existing `@skipif`:** Decorators apply bottom-up; the relative ordering is functionally equivalent. Putting `slow` first reads better ("this is slow AND requires env var") and matches Plan 01's pyproject `addopts = -m 'not slow'` mental model.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Plan/Code mismatch] tests/test_cli_init.py has 2 tests, plan said 3**
- **Found during:** Task 2
- **Issue:** Plan listed "tests/test_cli_init.py — all 3 tests" but the file contains exactly 2 functions: `test_init_creates_config` and `test_init_no_overwrite`.
- **Fix:** Marked both existing tests `@pytest.mark.slow`. The acceptance criterion (`grep -l "@pytest.mark.slow"` finds the file) is satisfied; "all 3" was apparently a planning miscount.
- **Files modified:** tests/test_cli_init.py
- **Committed in:** 34c3a97

**2. [Rule 1 - Plan/Code mismatch] tests/test_cli_version.py function is test_version_flag, not test_cli_version**
- **Found during:** Task 2
- **Issue:** Plan specified `test_cli_version` as the slow-marker target; actual function is `test_version_flag`.
- **Fix:** Marked `test_version_flag` `@pytest.mark.slow` (only test in the file; intent unambiguous).
- **Files modified:** tests/test_cli_version.py
- **Committed in:** 34c3a97

**3. [Rule 1 - Cleanup] Unused imports in tests/test_broker_db_schema.py after test deletion**
- **Found during:** Task 1
- **Issue:** Removing `test_migration_preserves_existing_rows` left `text` and `_ensure_broker_columns` and `pytest` unreferenced in the import block.
- **Fix:** Pruned `from sqlalchemy import text, inspect as sa_inspect` → `from sqlalchemy import inspect as sa_inspect`; pruned `from quirk.db import init_db, _ensure_broker_columns` → `from quirk.db import init_db`; dropped unused `import pytest`. Compileall + collect-only stay clean.
- **Files modified:** tests/test_broker_db_schema.py
- **Committed in:** 1957782

---

**Total deviations:** 3 auto-fixed (2 plan/code label mismatches, 1 import cleanup). No scope changes.

## Issues Encountered

None of substance. The Plan 01 meta-gate's `+/-2 line tolerance` absorbed line-number drift from the Task 1 deletions without requiring registry updates — the gate passed first try.

## Verification Evidence

- `python -m compileall tests/ -q` — exits 0
- `pytest tests/test_skip_registry.py -x` — `1 passed, 1 warning in 0.09s`
- `pytest -m 'not slow' tests/` — `681 passed, 10 deselected, 70 warnings in 5.71s` (~6s wall-clock)
- `grep -c "_skip_scanner" tests/test_email_scanner.py` — 0
- `grep -c "@pytest.mark.skipif(not _HAS_GCP_MODULE" tests/test_cloud_connectors.py` — 0
- `grep -c 'pytest.skip("quirk.dashboard not yet' tests/conftest.py` — 0
- `grep -c "pytest.skip" tests/test_version.py` — 0; `grep -c "pytest.fail" tests/test_version.py` — 2
- `grep -c 'pytest.skip("Column already present' tests/test_broker_db_schema.py` — 0
- 8 files contain `@pytest.mark.slow` (matches acceptance count exactly)

## Threat Flags

None. Test-infrastructure-only changes; no source code, network surface, auth, or trust-boundary modifications.

## Next Phase Readiness

- Plans 06 + 07 (final wave) can build on a clean, sub-10s test suite for any meta-gate or release-prep work.
- CI pipelines that previously masked failures behind these stale skips will now report real signal.
- The skip registry remains the canonical inventory; new skips MUST be added to `tests/skip_registry.py` or the meta-gate fails — guardrail is now active.

## Self-Check: PASSED

Files verified modified:
- tests/conftest.py — `pytest.fail` replaces stale skip
- tests/test_cloud_connectors.py — 0 occurrences of `_HAS_GCP_MODULE` skipif
- tests/test_email_scanner.py — 0 occurrences of `_skip_scanner`
- tests/test_broker_db_schema.py — dead test removed, imports pruned
- tests/test_version.py — 2× `pytest.fail`, 0× `pytest.skip`, has `@pytest.mark.slow`
- tests/test_cli_init.py, test_cli_version.py — `import pytest` + `@pytest.mark.slow`
- tests/test_chaos_storage.py, test_dnssec_scanner.py, test_saml_scanner.py, test_kerberos_scanner.py, test_cbom_motion_golden.py — `@pytest.mark.slow` above existing `@skipif`

Commits verified in `git log`:
- 1957782 — Task 1 (fix: delete stale code-reason skips + convert defensive skips to fail)
- 34c3a97 — Task 2 (test: mark slow-test candidates)

Meta-gate verified GREEN.

---
*Phase: 41-ci-stability-scanner-robustness*
*Plan: 05*
*Completed: 2026-04-29*
