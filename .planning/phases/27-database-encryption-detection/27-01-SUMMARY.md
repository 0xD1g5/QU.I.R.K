---
phase: 27-database-encryption-detection
plan: "01"
subsystem: infrastructure
tags: [tdd, red-scaffold, db-connector, schema-migration, config, scoring]
dependency_graph:
  requires: []
  provides:
    - "[db] extras group in pyproject.toml"
    - "ConnectorsCfg DB fields (7 fields)"
    - "dat_scan_json ORM column on CryptoEndpoint"
    - "_ensure_v43_columns() migration guard in db.py"
    - "RED test scaffold for DB-01, DB-02, DB-03 (14 tests)"
  affects:
    - "quirk/db.py init_db() call chain"
    - "tests/test_intelligence_scoring.py subscores assertion"
    - "tests/test_intelligence_evidence.py dar_ stub"
tech_stack:
  added: ["psycopg2-binary>=2.9.0 (optional, [db] extras)", "PyMySQL>=1.1.0 (optional, [db] extras)"]
  patterns: ["inspector-first migration guard", "TDD RED scaffold", "optional extras group"]
key_files:
  created:
    - tests/test_db_connector.py
  modified:
    - pyproject.toml
    - quirk/config.py
    - quirk/config_template.yaml
    - quirk/models.py
    - quirk/db.py
    - tests/test_intelligence_scoring.py
    - tests/test_intelligence_evidence.py
decisions:
  - "Schema tests (test_schema_fresh_db_has_dat_scan_json, test_v43_columns_idempotent) pass in RED scaffold — correct, these test infrastructure added in Task 1, not the scanner module"
  - "12 of 14 tests fail with ModuleNotFoundError for quirk.scanner.db_connector — RED state confirmed; Plan 02 creates the module"
  - "Pre-existing failures in test_cli_correctness.py, test_identity_surface.py, test_v41_gap_closure.py confirmed pre-existing (stash-verified, out of scope)"
  - "test_dar_db_counters uses build_evidence_summary([]) — fails with TypeError until Plan 02 adds dar_ counters to evidence.py"
metrics:
  duration: "197 seconds"
  completed: "2026-04-25"
  tasks: 2
  files: 7
---

# Phase 27 Plan 01: RED Scaffold — DB Infrastructure and Failing Tests

TDD RED wave: [db] extras group, 7 ConnectorsCfg fields, dat_scan_json ORM column, _ensure_v43_columns() migration guard, 14-test RED scaffold for PostgreSQL/MySQL/RDS detection, updated scoring/evidence stubs for dar_ subscore.

## What Was Built

### Task 1: Infrastructure (5 files)

- **pyproject.toml**: Added `[db]` extras group after `[cloud]` — `psycopg2-binary>=2.9.0` and `PyMySQL>=1.1.0`
- **quirk/config.py**: Added 7 DB fields to `ConnectorsCfg` — `enable_db`, `pg_targets`, `pg_scanner_user`, `pg_scanner_password`, `mysql_targets`, `mysql_scanner_user`, `mysql_scanner_password` — all with safe defaults, picked up automatically by `config_from_dict()` via `**kwargs`
- **quirk/config_template.yaml**: Added commented DB block after GCP block with all 7 fields documented
- **quirk/models.py**: Added `dat_scan_json = Column(Text, nullable=True)` under "v4.3 Data-at-Rest fields" section after GCP fields block
- **quirk/db.py**: Added `_V43_COLUMNS = ["dat_scan_json"]`, `_ensure_v43_columns()` mirroring `_ensure_gcp_columns()` exactly (inspector-first, `_SAFE_COL_RE` guard, idempotent), called from `init_db()` after `_ensure_gcp_columns(engine)`

### Task 2: RED Test Scaffold (3 files)

- **tests/test_db_connector.py** (new, 14 tests):
  - 2 schema/infra tests (PASS — test infrastructure from Task 1): `test_schema_fresh_db_has_dat_scan_json`, `test_v43_columns_idempotent`
  - 5 PostgreSQL tests (FAIL RED): unavailable guard, ssl=off HIGH, insufficient-privilege INFO, plaintext connections HIGH, session_start scanned_at
  - 4 MySQL tests (FAIL RED): unavailable guard, ssl-off HIGH, weak cipher MEDIUM, strong cipher no finding
  - 3 RDS tests (FAIL RED): unencrypted HIGH `RDS/none`, sse-rds service_detail, CMK service_detail
- **tests/test_intelligence_scoring.py**: Subscores assertion updated to include `"data_at_rest"` key; score cap changed from 100 to 125 (5 subscores × 25 max)
- **tests/test_intelligence_evidence.py**: `test_dar_db_counters` stub added (fails RED — `dar_` counters absent until Plan 02)

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — no UI rendering or placeholder data. The RED test scaffold is the intentional output of Plan 01.

## Threat Surface Scan

No new network endpoints, auth paths, or schema changes at trust boundaries beyond those specified in the plan threat model. `pg_scanner_password` and `mysql_scanner_password` fields declared `Optional[str] = None` — never logged (T-27-01-1 mitigated). `_ensure_v43_columns()` uses `_SAFE_COL_RE` guard for SQL injection prevention (T-27-01-2 mitigated).

## Self-Check: PASSED

| Item | Status |
|------|--------|
| tests/test_db_connector.py | FOUND |
| quirk/models.py | FOUND |
| quirk/db.py | FOUND |
| quirk/config.py | FOUND |
| pyproject.toml | FOUND |
| 27-01-SUMMARY.md | FOUND |
| commit 8797ef2 (Task 1) | FOUND |
| commit 82e436f (Task 2) | FOUND |
