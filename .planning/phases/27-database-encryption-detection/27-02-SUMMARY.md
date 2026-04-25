---
phase: 27-database-encryption-detection
plan: "02"
subsystem: scanner
tags: [tdd, green-implementation, db-connector, rds-encryption, postgresql, mysql]
dependency_graph:
  requires:
    - "RED scaffold from Plan 01 (tests/test_db_connector.py, CryptoEndpoint.severity column)"
  provides:
    - "quirk/scanner/db_connector.py — scan_pg_targets and scan_mysql_targets"
    - "_scan_rds_encryption() in quirk/scanner/aws_connector.py"
    - "severity column on CryptoEndpoint ORM model"
    - "All 14 DB connector tests GREEN"
  affects:
    - "quirk/scanner/aws_connector.py scan_aws_targets() call chain"
    - "quirk/models.py CryptoEndpoint schema"
    - "quirk/db.py _V43_COLUMNS migration list"
    - "tests/test_cloud_connectors.py (assert_any_call fix)"
tech_stack:
  added: []
  patterns:
    - "3-tier PostgreSQL SSL probe: SHOW ssl -> pg_has_role -> COUNT non-SSL rows"
    - "MySQL ssl_disabled=True probe with Ssl_cipher severity ladder"
    - "RDS StorageEncrypted + KmsKeyId derivation (not StorageEncryptionType)"
    - "Module-level None optional imports for test patching"
    - "session_start timestamp isolation pattern (ISSUE-3)"
key_files:
  created:
    - quirk/scanner/db_connector.py
  modified:
    - quirk/scanner/aws_connector.py
    - quirk/models.py
    - quirk/db.py
    - tests/test_cloud_connectors.py
decisions:
  - "severity column added to CryptoEndpoint model (Rule 2) — plan specified severity=str in CryptoEndpoint interface but Plan 01 did not add the column; required for GREEN state"
  - "assert_any_call fix in test_aws_acm_pagination (Rule 1) — adding _scan_rds_encryption to scan_aws_targets caused the paginator mock's last call to be describe_db_instances, breaking the ACM assert_called_with assertion; changed to assert_any_call which still validates ACM uses a paginator"
  - "_scan_rds_encryption placed before _scan_kms in aws_connector.py for logical grouping (before existing scan functions) — call added after _scan_acm in scan_aws_targets per plan spec"
metrics:
  duration: "287 seconds"
  completed: "2026-04-25"
  tasks: 2
  files: 5
---

# Phase 27 Plan 02: GREEN Implementation — DB Connector and RDS Encryption Detection

TDD GREEN wave: PostgreSQL and MySQL SSL posture scanners in db_connector.py; RDS encryption detection added to aws_connector.py; severity column added to CryptoEndpoint; all 14 RED tests from Plan 01 now GREEN.

## What Was Built

### Task 1: quirk/scanner/db_connector.py (3 files)

- **quirk/scanner/db_connector.py** (new): PostgreSQL and MySQL SSL scanners
  - `PSYCOPG2_AVAILABLE` / `PYMYSQL_AVAILABLE` module-level flags with `None` assignments for test patching
  - `scan_pg_targets(targets, user, password, logger, session_start)` — 3-tier probe: SHOW ssl -> pg_has_role(current_user, 'pg_read_all_stats', 'MEMBER') -> COUNT non-SSL rows; emits HIGH for ssl-off, INFO with scan_error='insufficient-privilege' when pg_read_all_stats absent, HIGH for plaintext connections detected
  - `scan_mysql_targets(targets, user, password, logger, session_start)` — connects with ssl_disabled=True, reads Ssl_cipher from SHOW STATUS LIKE; HIGH for empty cipher, MEDIUM for RC4/DES/NULL/EXPORT/ANON/MD5/3DES prefix, informational for strong cipher
  - Both functions use `now = (session_start or datetime.now(timezone.utc)).replace(tzinfo=None)` (ISSUE-3 pattern)
  - `MYSQL_WEAK_CIPHER_PREFIXES` frozenset with 7 weak cipher prefixes
  - `connect_timeout=5` in both psycopg2.connect and pymysql.connect (T-27-02-4 mitigated)
- **quirk/models.py**: Added `severity = Column(String(16), nullable=True)` to CryptoEndpoint (Rule 2 fix — required for scanner output)
- **quirk/db.py**: Added `"severity"` to `_V43_COLUMNS` migration list so existing databases gain the column

### Task 2: _scan_rds_encryption() added to aws_connector.py (2 files)

- **quirk/scanner/aws_connector.py**: Added `_scan_rds_encryption(session, logger)` private function
  - Uses `client.get_paginator("describe_db_instances")` — NOT StorageEncryptionType (does not exist in boto3 API)
  - Derives service_detail from `StorageEncrypted` (bool) + `KmsKeyId` (str):
    - `StorageEncrypted=False` -> `"RDS/none"`, severity HIGH
    - `StorageEncrypted=True`, no KmsKeyId -> `"RDS/sse-rds"`
    - `StorageEncrypted=True`, KmsKeyId contains `"alias/aws/"` -> `"RDS/sse-kms-aws"`
    - `StorageEncrypted=True`, other KmsKeyId -> `"RDS/sse-kms-cmk"`
  - `results.extend(_scan_rds_encryption(session, logger))` added at end of `scan_aws_targets()`
  - `from datetime import datetime, timezone` import added
- **tests/test_cloud_connectors.py**: Changed `assert_called_with("list_certificates")` to `assert_any_call("list_certificates")` — Rule 1 fix: adding RDS caused the last `get_paginator` call to be `describe_db_instances`; test intent preserved

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical Functionality] severity column absent from CryptoEndpoint model**
- **Found during:** Task 1 — `CryptoEndpoint(severity="HIGH", ...)` raises `TypeError: 'severity' is an invalid keyword argument`
- **Issue:** Plan 02 action specifies `CryptoEndpoint(severity=str)` interface, and tests check `ep.severity`. The model had no `severity` column. Plan 01 scaffolded the tests expecting severity to work but did not add the column.
- **Fix:** Added `severity = Column(String(16), nullable=True)` to `CryptoEndpoint` in `quirk/models.py`; added `"severity"` to `_V43_COLUMNS` in `quirk/db.py` for migration of existing databases
- **Files modified:** quirk/models.py, quirk/db.py
- **Commit:** 5225ec2

**2. [Rule 1 - Bug] test_aws_acm_pagination regression from _scan_rds_encryption addition**
- **Found during:** Task 2 full suite run
- **Issue:** `test_aws_acm_pagination` used `mock_client.get_paginator.assert_called_with("list_certificates")` — checks the LAST call. After adding `_scan_rds_encryption`, the last `get_paginator` call is `"describe_db_instances"` (RDS), causing the assertion to fail.
- **Fix:** Changed to `assert_any_call("list_certificates")` — preserves the test intent (ACM must use a paginator) while accommodating additional paginator calls from RDS
- **Files modified:** tests/test_cloud_connectors.py
- **Commit:** 3b5b0d8

## TDD Gate Compliance

RED gate: Plan 01 commit 82e436f established 14 failing tests (`test(27-01)`).
GREEN gate: This plan's commits 5225ec2 and 3b5b0d8 make all 14 tests pass (`feat(27-02)`).

## Known Stubs

None — all scanner logic is fully implemented. No placeholder data flows to any UI.

## Threat Surface Scan

No new network endpoints beyond those specified in the plan threat model.

- T-27-02-1/T-27-02-2 mitigated: passwords not included in `logger.v()` error messages in db_connector.py
- T-27-02-4 mitigated: `connect_timeout=5` present in both psycopg2.connect and pymysql.connect
- T-27-02-6 mitigated: `_scan_rds_encryption` uses `db.get("StorageEncrypted")` and `db.get("KmsKeyId")` — `StorageEncryptionType` absent from implementation

## Self-Check: PASSED

| Item | Status |
|------|--------|
| quirk/scanner/db_connector.py | FOUND |
| quirk/scanner/aws_connector.py (_scan_rds_encryption) | FOUND |
| quirk/models.py (severity column) | FOUND |
| quirk/db.py (_V43_COLUMNS with severity) | FOUND |
| tests/test_cloud_connectors.py (assert_any_call fix) | FOUND |
| 27-02-SUMMARY.md | FOUND |
| commit 5225ec2 (Task 1) | FOUND |
| commit 3b5b0d8 (Task 2) | FOUND |
| All 14 tests GREEN | CONFIRMED |
