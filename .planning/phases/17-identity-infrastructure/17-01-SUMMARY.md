---
phase: 17-identity-infrastructure
plan: 01
subsystem: testing
tags: [pytest, unittest, tdd, red-scaffold, sqlalchemy, identity, kerberos, saml, dnssec]

# Dependency graph
requires:
  - phase: 16-v41-gap-closure
    provides: established TDD RED scaffold pattern (unittest.TestCase style)
provides:
  - RED test scaffold for INFRA-01 (schema columns), INFRA-02 (config flags), INFRA-03 (extras group)
  - 6 failing tests in tests/test_identity_infra.py asserting unmet identity infrastructure requirements
affects:
  - phase: 17-identity-infrastructure plan 02 (must turn these tests GREEN)
  - phase: 18-dnssec-scanner (depends on dnssec_scan_json column and enable_dnssec flag)
  - phase: 19-saml-scanner (depends on saml_scan_json column and enable_saml flag)
  - phase: 20-kerberos-scanner (depends on kerberos_scan_json column and enable_kerberos flag)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "unittest.TestCase RED scaffold: import-fail pattern for missing exports (_ensure_identity_columns)"
    - "SQLAlchemy in-memory engine for column existence assertions: create_engine('sqlite:///:memory:')"
    - "Inspector-first column introspection: sa_inspect(engine).get_columns(table_name)"

key-files:
  created:
    - tests/test_identity_infra.py
  modified: []

key-decisions:
  - "Table name in tests is crypto_endpoints (not scan_results) -- planning docs use ScanResult conceptually but CryptoEndpoint is the actual ORM model"
  - "test_schema_migration_idempotent uses try/except ImportError to fail with a clear message when _ensure_identity_columns is not yet exported"
  - "test_config_old_yaml_backward_compat uses AttributeError path (accessing missing attribute after successful config_from_dict call)"

patterns-established:
  - "RED scaffold pattern: write tests that fail for the right reason (missing columns vs table not found)"
  - "Import-fail test pattern: try/except ImportError -> self.fail() for missing module exports"

requirements-completed: []

# Metrics
duration: 5min
completed: 2026-04-08
---

# Phase 17 Plan 01: Identity Infrastructure RED Scaffold Summary

**6-test RED scaffold proving INFRA-01/02/03 are unmet: identity schema columns absent from CryptoEndpoint, ConnectorsCfg lacks enable_kerberos/saml/dnssec flags, pyproject.toml has no [identity] extras group**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-04-08T13:11:50Z
- **Completed:** 2026-04-08T13:14:15Z
- **Tasks:** 1 of 1
- **Files modified:** 1

## Accomplishments
- Created `tests/test_identity_infra.py` with 6 failing RED tests covering all three INFRA requirements
- Confirmed all 6 tests FAIL against unmodified codebase (correct RED state)
- Confirmed 233 pre-existing tests still pass (no regressions)
- Identified and corrected table name discrepancy: planning docs say `scan_results` but actual ORM model is `CryptoEndpoint` with `crypto_endpoints` table

## Task Commits

Each task was committed atomically:

1. **Task 1: Write RED test scaffold for INFRA-01, INFRA-02, INFRA-03** - `afe434f` (test)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `tests/test_identity_infra.py` - 6 RED tests in TestIdentityInfra class covering schema columns, config flags, extras group, and config template

## Decisions Made
- Used `crypto_endpoints` as the table name in schema inspection tests — planning docs reference `scan_results` conceptually but the actual SQLAlchemy model is `CryptoEndpoint` with `__tablename__ = "crypto_endpoints"`. The RED tests must reference the real table to fail for the right reason (columns missing, not table missing).
- `test_schema_migration_idempotent` uses `try/except ImportError` -> `self.fail()` pattern matching `test_v41_gap_closure.py` style, producing a clear diagnostic message when `_ensure_identity_columns` is not yet exported from `quirk.db`.
- `test_config_old_yaml_backward_compat` accesses `cfg.connectors.enable_kerberos` after a successful `config_from_dict()` call — this triggers `AttributeError` (not `TypeError`) in the RED state, which is the correct failure mode for a missing dataclass field with no default.

## Deviations from Plan

**1. [Rule 1 - Bug] Corrected table name from scan_results to crypto_endpoints**
- **Found during:** Task 1 (writing test assertions)
- **Issue:** Plan specifies `sa_inspect(engine).get_columns("scan_results")` but the actual SQLAlchemy `Base.metadata.tables` contains only `crypto_endpoints`. Using `scan_results` would cause the tests to fail with `sqlalchemy.exc.NoSuchTableError` rather than the intended assertion failure (column missing), making the RED state misleading.
- **Fix:** Used `crypto_endpoints` as the table name in both schema tests.
- **Files modified:** tests/test_identity_infra.py
- **Verification:** Tests fail with `AssertionError: 'kerberos_scan_json' not found in {host, port, ...}` — correct RED diagnostic.
- **Committed in:** afe434f (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug: wrong table name)
**Impact on plan:** Essential correction — tests now fail for the right reason and will provide accurate GREEN signal when Plan 02 adds the columns.

## Issues Encountered
None beyond the table name correction above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- RED scaffold complete, Plan 17-02 can now implement production code to turn all 6 tests GREEN
- Plan 17-02 must: add 3 columns to CryptoEndpoint, add `_ensure_identity_columns()` to `quirk/db.py`, add identity flags/target lists to `ConnectorsCfg`, add `[identity]` extras group to `pyproject.toml`, add identity section to `config_template.yaml`

---
*Phase: 17-identity-infrastructure*
*Completed: 2026-04-08*

## Self-Check: PASSED

- FOUND: tests/test_identity_infra.py
- FOUND: .planning/phases/17-identity-infrastructure/17-01-SUMMARY.md
- FOUND: commit afe434f (task)
- FOUND: commit ac52f31 (docs)
- 6 tests FAIL (RED state confirmed)
- 233 pre-existing tests PASS (no regressions)
