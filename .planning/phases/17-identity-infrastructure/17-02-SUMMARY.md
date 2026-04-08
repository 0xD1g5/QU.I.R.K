---
phase: 17-identity-infrastructure
plan: 02
subsystem: infra
tags: [sqlalchemy, migration, config, dataclass, pyproject, identity, kerberos, saml, dnssec]

# Dependency graph
requires:
  - phase: 17-identity-infrastructure plan 01
    provides: 6 RED tests in tests/test_identity_infra.py asserting INFRA-01/02/03 are unmet
provides:
  - CryptoEndpoint model with kerberos_scan_json, saml_scan_json, dnssec_scan_json columns
  - _ensure_identity_columns() inspector-first idempotent migration helper in quirk/db.py
  - ConnectorsCfg with enable_kerberos/saml/dnssec flags and target lists (safe defaults)
  - config_template.yaml commented identity connectors section inside connectors block
  - pyproject.toml [identity] extras group with impacket, dnspython[dnssec], lxml, defusedxml, signxml
affects:
  - phase: 18-dnssec-scanner (depends on dnssec_scan_json column, enable_dnssec flag, dnssec_targets)
  - phase: 19-saml-scanner (depends on saml_scan_json column, enable_saml flag, saml_targets)
  - phase: 20-kerberos-scanner (depends on kerberos_scan_json column, enable_kerberos flag, kerberos_targets)

# Tech tracking
tech-stack:
  added:
    - "impacket>=0.13.0,<0.14 (optional, [identity] extras group)"
    - "dnspython[dnssec]>=2.8.0 (optional, [identity] extras group)"
    - "lxml>=6.0 (optional, [identity] extras group)"
    - "defusedxml>=0.7.1 (optional, [identity] extras group)"
    - "signxml>=4.4.0 (optional, [identity] extras group)"
  patterns:
    - "Inspector-first idempotent migration: sa_inspect(engine).get_columns(table) before ALTER TABLE"
    - "Optional pyproject extras group: pip install quirk[identity] installs scanner deps"
    - "Dataclass safe defaults: field(default_factory=list) for list fields, bool = False for flags"

key-files:
  created: []
  modified:
    - quirk/models.py
    - quirk/db.py
    - quirk/config.py
    - quirk/config_template.yaml
    - pyproject.toml

key-decisions:
  - "Table name in _ensure_identity_columns is crypto_endpoints (not scan_results) -- CryptoEndpoint is the actual ORM model; plan text said scan_results but critical_deviation note and tests confirmed crypto_endpoints"
  - "impacket placed in [identity] extras group only -- not in core dependencies to avoid pyOpenSSL transitive conflict risk"
  - "All 6 identity ConnectorsCfg fields have safe defaults so v4.1 config.yaml loads without error via config_from_dict()"

patterns-established:
  - "Migration guard pattern: inspector-first check before ALTER TABLE, no try/except OperationalError"
  - "Extras group pattern: optional scanner deps isolated in [identity] group, not in core deps"

requirements-completed:
  - INFRA-01
  - INFRA-02
  - INFRA-03

# Metrics
duration: 5min
completed: 2026-04-08
---

# Phase 17 Plan 02: Identity Infrastructure Implementation Summary

**Inspector-first SQLAlchemy migration guard adds kerberos/saml/dnssec columns to crypto_endpoints, ConnectorsCfg extended with identity flags and targets, pyproject.toml [identity] extras group declared -- all 6 RED tests now GREEN**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-04-08T13:16:38Z
- **Completed:** 2026-04-08T13:20:00Z
- **Tasks:** 2 of 2
- **Files modified:** 5

## Accomplishments
- All 6 RED tests from Plan 17-01 now pass GREEN (INFRA-01, INFRA-02, INFRA-03 complete)
- Added kerberos_scan_json, saml_scan_json, dnssec_scan_json columns to CryptoEndpoint model
- Added `_ensure_identity_columns()` inspector-first idempotent migration helper (no try/except OperationalError)
- Extended ConnectorsCfg with 6 identity fields: 3 bool flags (default False) and 3 list targets (default [])
- Added commented identity section inside config_template.yaml connectors block (no duplicate top-level key)
- Added [identity] extras group to pyproject.toml with exact package versions per D-07
- Full test suite passes: 239 tests, 0 failures, 0 regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Add CryptoEndpoint identity columns and _ensure_identity_columns migration guard** - `2d71caf` (feat)
2. **Task 2: Add ConnectorsCfg fields, config template section, and pyproject extras** - `4970deb` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `quirk/models.py` - Added kerberos_scan_json, saml_scan_json, dnssec_scan_json columns to CryptoEndpoint
- `quirk/db.py` - Added _IDENTITY_COLUMNS list, _ensure_identity_columns() function, call in init_db()
- `quirk/config.py` - Added 6 identity fields to ConnectorsCfg (enable_kerberos/saml/dnssec bool flags, kerberos/saml/dnssec_targets list fields)
- `quirk/config_template.yaml` - Added commented identity connectors section inside existing connectors block
- `pyproject.toml` - Added identity extras group with impacket, dnspython[dnssec], lxml, defusedxml, signxml

## Decisions Made
- Used `crypto_endpoints` as the table name in `_ensure_identity_columns` (not `scan_results` as plan text stated) — the actual ORM model is `CryptoEndpoint` with `__tablename__ = "crypto_endpoints"`. The critical_deviation note and RED tests both confirmed this correction is necessary.
- `impacket` kept in `[identity]` extras group only, not core dependencies — per D-08 and research decision to avoid pyOpenSSL transitive conflicts.
- Used `field(default_factory=list)` for all list target fields — per Pitfall 3 in plan, bare `= []` as class attribute default in dataclasses is a mutable default anti-pattern.

## Deviations from Plan

**1. [Rule 1 - Bug] Used crypto_endpoints instead of scan_results in _ensure_identity_columns**
- **Found during:** Task 1 (implementing migration helper)
- **Issue:** Plan specifies `sa_inspect(engine).get_columns("scan_results")` and `ALTER TABLE scan_results` in the `_ensure_identity_columns` implementation, but the actual SQLAlchemy table is `crypto_endpoints` (CryptoEndpoint model). Using `scan_results` would cause `sqlalchemy.exc.NoSuchTableError` at runtime.
- **Fix:** Used `crypto_endpoints` in both the inspector call and the ALTER TABLE statement.
- **Files modified:** quirk/db.py
- **Verification:** test_schema_migration_idempotent passes, _ensure_identity_columns() callable twice without error.
- **Committed in:** 2d71caf (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug: wrong table name in migration helper)
**Impact on plan:** Essential correction — plan was written before the table name discrepancy was discovered in Plan 17-01. Using scan_results would have caused a NoSuchTableError at runtime. The fix aligns with the critical_deviation note provided in the execution prompt.

## Issues Encountered
None beyond the table name correction documented above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- INFRA-01, INFRA-02, INFRA-03 complete — identity infrastructure scaffold ready for scanner implementation
- Phase 18 (DNSSEC scanner) can now add a scanner that populates `dnssec_scan_json`, reads `enable_dnssec`, and uses `dnssec_targets`
- Phase 19 (SAML scanner) can now add a scanner that populates `saml_scan_json`, reads `enable_saml`, and uses `saml_targets`
- Phase 20 (Kerberos scanner) can now add a scanner that populates `kerberos_scan_json`, reads `enable_kerberos`, and uses `kerberos_targets`
- Existing v4.1 databases will be migrated idempotently on first `init_db()` call with the new columns

---
*Phase: 17-identity-infrastructure*
*Completed: 2026-04-08*
