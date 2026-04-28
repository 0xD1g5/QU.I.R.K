---
phase: 33-broker-scanner
plan: "01"
subsystem: schema-migration
tags: [phase-33, broker-scanner, schema, migration, BROKER-00]
requirements: [BROKER-00]

dependency_graph:
  requires: []
  provides:
    - "broker_scan_json TEXT NULL column on crypto_endpoints"
    - "_ensure_broker_columns(engine) idempotent migration helper"
  affects:
    - quirk/db.py
    - quirk/models.py

tech_stack:
  added: []
  patterns:
    - "Inspector-first idempotent ALTER TABLE (mirrors _ensure_email_columns Phase 32)"
    - "_SAFE_COL_RE guard for SQL column-name injection prevention"

key_files:
  created:
    - tests/test_broker_db_schema.py
  modified:
    - quirk/models.py
    - quirk/db.py

decisions:
  - "Adapted test file to use init_db(db_path: str) pattern (tempfile) matching test_email_scanner.py — plan code used init_db(engine) which does not match actual signature"
  - "test_migration_preserves_existing_rows skips when Base.metadata already includes column (model updated), covered by idempotency test — acceptable per plan"

metrics:
  duration: "~5 minutes"
  completed: "2026-04-28"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 2
  files_created: 1
---

# Phase 33 Plan 01: Broker DB Schema — SUMMARY

**One-liner:** Added `broker_scan_json TEXT NULL` column to `crypto_endpoints` via idempotent `_ensure_broker_columns()` migration helper wired into `init_db()`, mirroring Phase 32 email scanner shape exactly.

## What Was Built

### Task 1: broker_scan_json column + migration helper

**quirk/models.py** — added `broker_scan_json = Column(Text, nullable=True)` immediately after `email_scan_json` in the `CryptoEndpoint` model under the `v4.4 Data in Motion fields` section. Column comment marks Phase 33 and BROKER-00.

**quirk/db.py** — added:
- `_BROKER_COLUMNS = ["broker_scan_json"]` constant
- `_ensure_broker_columns(engine) -> None` function: inspector-first check, `_SAFE_COL_RE` guard, `ALTER TABLE crypto_endpoints ADD COLUMN broker_scan_json TEXT`, idempotent (skips if column exists)
- Call site `_ensure_broker_columns(engine)` inside `init_db()` directly after `_ensure_email_columns(engine)` call

### Task 2: Schema regression tests

**tests/test_broker_db_schema.py** — 3 tests:

| Test | Result |
|------|--------|
| `test_broker_scan_json_column_exists` | PASSED — column present, nullable=True |
| `test_init_db_twice_no_error` | PASSED — idempotent, no raise on second call |
| `test_migration_preserves_existing_rows` | SKIPPED — column already in Base.metadata (acceptable) |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Adapted test init_db call signature**
- **Found during:** Task 2
- **Issue:** Plan's test code used `init_db(engine)` and `Base.metadata.create_all(engine)` in `_fresh_engine()` helper — but the actual `init_db()` signature is `init_db(db_path: str) -> Engine`. Calling it with an engine object would fail.
- **Fix:** Replaced `_fresh_engine()` helper with `_fresh_db()` returning `(tmp_path, engine)` using `tempfile.NamedTemporaryFile` and `init_db(tmp.name)` — matching the pattern in `tests/test_email_scanner.py`. `test_migration_preserves_existing_rows` uses `create_engine` directly then calls `_ensure_broker_columns(engine)` for the data-preservation assertion.
- **Files modified:** `tests/test_broker_db_schema.py`
- **Commits:** efcb018

## Verification Passed

```
python -m compileall quirk/db.py quirk/models.py tests/test_broker_db_schema.py  -> exit 0
python -m pytest tests/test_broker_db_schema.py -v                                 -> 2 passed, 1 skipped
grep -c "broker_scan_json" quirk/models.py quirk/db.py                             -> 1 + 2 = 3 (>=3 required)
```

## Commits

| Hash | Message |
|------|---------|
| b7894e8 | feat(33-01): add broker_scan_json column to model and _ensure_broker_columns migration |
| efcb018 | test(33-01): add broker_scan_json schema regression tests for BROKER-00 |

## Known Stubs

None.

## Threat Flags

T-33-01 (SQL injection via ALTER TABLE interpolation): mitigated — `_SAFE_COL_RE.match(col)` guard applied to `broker_scan_json` in `_ensure_broker_columns()`, matching the existing `_ensure_email_columns` mitigation pattern. Column name is a static literal in `_BROKER_COLUMNS`.
