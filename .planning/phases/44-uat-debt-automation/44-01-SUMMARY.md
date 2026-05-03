---
phase: 44-uat-debt-automation
plan: "01"
subsystem: testing
tags: [uat, db-connector, live-infra, skip-registry, postgresql, mysql]
dependency_graph:
  requires: []
  provides: [tests/test_uat_db_integration.py, skip_registry UAT-01 entries]
  affects: [tests/skip_registry.py, test_skip_registry.py gate]
tech_stack:
  added: []
  patterns: [live_infra skip pattern (QUIRK_*_INTEGRATION env-var gate)]
key_files:
  created:
    - tests/test_uat_db_integration.py
  modified:
    - tests/skip_registry.py
decisions:
  - "Used QUIRK_DB_INTEGRATION env var (consistent with QUIRK_KERBEROS_INTEGRATION naming)"
  - "pytestmark=pytest.mark.slow keeps tests out of fast CI suite"
  - "Pre-existing registry drift (cbom_motion_golden line 189->195, cbom_classifier missing) fixed as Rule 1 bug-fix since meta-test was expected to pass"
metrics:
  duration: "2 minutes"
  completed: "2026-05-03"
  tasks: 2
  files_changed: 2
---

# Phase 44 Plan 01: DB Integration Tests (UAT-01) Summary

Live-infra integration tests for Phase 27 DB UAT: 4 tests covering PostgreSQL/ssl-off and MySQL/ssl-off HIGH findings against the `database` chaos lab profile, with ALLOWED_SKIPS registration.

## What Was Built

### Task 1: tests/test_uat_db_integration.py

Created `tests/test_uat_db_integration.py` with 4 live-infra-gated tests:

1. `test_postgres_ssl_off_produces_high_finding` — asserts `protocol=POSTGRESQL`, `severity=HIGH`, `"ssl-off" in service_detail`
2. `test_mysql_ssl_off_produces_high_finding` — asserts `protocol=MYSQL`, `severity=HIGH`, `"ssl-off" in service_detail`
3. `test_postgres_finding_includes_host_and_port` — asserts `port=25432` in results
4. `test_mysql_finding_includes_host_and_port` — asserts `port=23306` in results

All 4 tests skip cleanly when `QUIRK_DB_INTEGRATION` is unset. Marked `pytest.mark.slow` to exclude from fast CI suite.

### Task 2: tests/skip_registry.py

Added 4 new `ALLOWED_SKIPS` entries with actual `@pytest.mark.skipif` decorator line numbers:

| File | Line | Category | Reason |
|------|------|----------|--------|
| test_uat_db_integration.py | 29 | live_infra | Requires PostgreSQL chaos lab (database profile) |
| test_uat_db_integration.py | 49 | live_infra | Requires MySQL chaos lab (database profile) |
| test_uat_db_integration.py | 69 | live_infra | Requires PostgreSQL chaos lab (database profile) |
| test_uat_db_integration.py | 84 | live_infra | Requires MySQL chaos lab (database profile) |

## Operator Verification Command

```bash
cd quantum-chaos-enterprise-lab && ./lab.sh up database
QUIRK_DB_INTEGRATION=1 python -m pytest tests/test_uat_db_integration.py -v
```

Expected: All 4 tests PASS. PostgreSQL and MySQL ssl-off findings produce `severity=HIGH`
per `quantum-chaos-enterprise-lab/expected_results_v4.md` oracle.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed pre-existing skip_registry drift**
- **Found during:** Task 2 verification
- **Issue:** `test_skip_registry.py` meta-test was already failing before this plan due to:
  - `test_cbom_motion_golden.py`: skipif at line 195 but registry said 189 (delta=6, beyond ±2 tolerance)
  - `test_cbom_classifier_coverage.py:84`: `@pytest.mark.skipif` not registered at all
- **Fix:** Updated `test_cbom_motion_golden.py` entry from line 189 to 195; added `("test_cbom_classifier_coverage.py", 84, "live_infra", "REGEN_CBOM_COVERAGE guard")`
- **Files modified:** tests/skip_registry.py
- **Commit:** 9d72252

## Commits

| Task | Commit | Message |
|------|--------|---------|
| Task 1 | 877b48f | test(44-01): add live-infra integration tests for Phase 27 DB UAT |
| Task 2 | 9d72252 | fix(44-01): register new live_infra skips and fix pre-existing registry drift |

## Known Stubs

None. Both test files call real scanner functions — no hardcoded empty values or placeholder data.

## Self-Check

Files created/modified:
- tests/test_uat_db_integration.py — exists
- tests/skip_registry.py — modified with 4 new entries + 2 drift fixes

Commits verified: 877b48f, 9d72252 both in git log.
