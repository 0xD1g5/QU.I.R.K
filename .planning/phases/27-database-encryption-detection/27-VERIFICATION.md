---
phase: 27-database-encryption-detection
verified: 2026-04-25T00:00:00Z
status: human_needed
score: 5/5 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Run `docker compose --profile database up -d` and execute scan with pg_targets=['localhost:25432'] and mysql_targets=['localhost:23306'] in config; confirm HIGH findings appear in output"
    expected: "PostgreSQL scan produces HIGH finding with service_detail='PostgreSQL/ssl-off'; MySQL scan produces HIGH finding with service_detail='MySQL/ssl-off'; both appear in CBOM endpoint list"
    why_human: "End-to-end scan pipeline through real Docker containers cannot be exercised without starting the containers and running the actual scan binary; requires Docker and live network connections"
---

# Phase 27: Database Encryption Detection Verification Report

**Phase Goal:** QU.I.R.K. can detect encryption-at-rest posture for PostgreSQL, MySQL/MariaDB, and RDS instances — establishing the dat_scan_json column and dar_ scoring infrastructure that all subsequent data-at-rest scanner phases depend on
**Verified:** 2026-04-25
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| #  | Truth                                                                                                 | Status     | Evidence                                                                                                                                                  |
|----|-------------------------------------------------------------------------------------------------------|------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------|
| 1  | `_ensure_v43_columns()` idempotently adds dat_scan_json to crypto_endpoints (SC-1)                   | ✓ VERIFIED | `dat_scan_json` present in fresh in-memory DB; calling `_ensure_v43_columns()` twice raises no error; migration guard uses inspector-first pattern        |
| 2  | RDS scanner detects StorageEncrypted + KmsKeyId, distinguishes AWS-managed from CMK (SC-2)            | ✓ VERIFIED | `_scan_rds_encryption()` in aws_connector.py uses `db.get("StorageEncrypted")` + `db.get("KmsKeyId")`; produces RDS/none, RDS/sse-rds, RDS/sse-kms-aws, RDS/sse-kms-cmk; all 3 RDS tests pass |
| 3  | PostgreSQL scanner detects privilege level; emits scan_error when pg_read_all_stats absent (SC-3)     | ✓ VERIFIED | 3-tier probe in `scan_pg_targets()`: SHOW ssl → pg_has_role → COUNT non-SSL; `scan_error='insufficient-privilege'` emitted with INFO severity when role absent; test_pg_no_privilege_produces_scan_error passes |
| 4  | MySQL scanner reports SSL session status and emits finding with cipher when disabled/weak (SC-4)      | ✓ VERIFIED | `scan_mysql_targets()` connects with ssl_disabled=True, queries SHOW STATUS LIKE 'Ssl_cipher'; HIGH for empty cipher, MEDIUM for weak prefix, informational for strong; 4 MySQL tests pass |
| 5  | dar_ evidence counters in evidence.py flow into scoring.py as 5th subscore; [db] extras declared (SC-5) | ✓ VERIFIED | `dar_db_plaintext_count`, `dar_db_weak_ssl_count`, ratios in evidence.py return dict; `data_at_rest` key in scoring subscores dict; `dar_score` in total_score; psycopg2-binary>=2.9.0 and PyMySQL>=1.1.0 in pyproject.toml [db] extras |

**Score:** 5/5 truths verified

---

### Required Artifacts

| Artifact                                              | Expected                                         | Status     | Details                                                                                                                  |
|-------------------------------------------------------|--------------------------------------------------|------------|--------------------------------------------------------------------------------------------------------------------------|
| `tests/test_db_connector.py`                          | 14-test scaffold (GREEN)                         | ✓ VERIFIED | 14 tests collected, 14 pass; covers pg/mysql/rds scenarios                                                               |
| `pyproject.toml`                                      | [db] extras with psycopg2-binary and PyMySQL     | ✓ VERIFIED | Lines 49–50: `psycopg2-binary>=2.9.0`, `PyMySQL>=1.1.0`                                                                 |
| `quirk/config.py`                                     | 7 DB fields in ConnectorsCfg                     | ✓ VERIFIED | enable_db=False, pg_targets=[], pg_scanner_user=None, pg_scanner_password=None, mysql_targets=[], mysql_scanner_user=None, mysql_scanner_password=None |
| `quirk/models.py`                                     | dat_scan_json and severity columns               | ✓ VERIFIED | Both columns present on CryptoEndpoint; severity added by Plan 02 as auto-fix                                            |
| `quirk/db.py`                                         | _V43_COLUMNS, _ensure_v43_columns(), init_db call | ✓ VERIFIED | Defined at line 90; called from init_db() at line 125; "severity" also in _V43_COLUMNS                                  |
| `quirk/scanner/db_connector.py`                       | PostgreSQL and MySQL scanners                    | ✓ VERIFIED | Module-level PSYCOPG2_AVAILABLE/PYMYSQL_AVAILABLE flags; scan_pg_targets, scan_mysql_targets; pg_has_role; ssl_disabled=True |
| `quirk/scanner/aws_connector.py`                      | _scan_rds_encryption added                       | ✓ VERIFIED | Defined at line 75; called via results.extend() at line 259; uses StorageEncrypted + KmsKeyId (not StorageEncryptionType) |
| `quirk/intelligence/evidence.py`                      | 4 dar_ keys in return dict, POSTGRESQL/MYSQL branches | ✓ VERIFIED | dar_db_plaintext_count, dar_db_weak_ssl_count, dar_db_plaintext_ratio, dar_db_weak_ssl_ratio at lines 210–213            |
| `quirk/intelligence/scoring.py`                       | dar_ as 5th subscore prefix                      | ✓ VERIFIED | SCORE_WEIGHTS has dar_ entries; all 3 PROFILE_MULTIPLIERS have "dar_" key; data_at_rest in subscores dict at line 191    |
| `run_scan.py`                                         | db_scanning block after session_start            | ✓ VERIFIED | db_scanning at line 481, session_start at line 475; + db_endpoints in aggregation at line 545                            |
| `quirk/cbom/builder.py`                               | POSTGRESQL/MYSQL/RDS in Pass 1, 2, 3             | ✓ VERIFIED | Pass 1 elif at line 410; Pass 2 skip at line 437; Pass 3 skip at line 517                                                |
| `quantum-chaos-enterprise-lab/docker-compose.yml`     | database profile with postgres-ssl-off, mysql-ssl-off | ✓ VERIFIED | postgres-ssl-off (25432:5432) and mysql-ssl-off (23306:3306) at lines 824–846; profiles: ["database"]                   |
| `quantum-chaos-enterprise-lab/expected_results_v3.md` | Phase 27 section with expected findings          | ✓ VERIFIED | Phase 27 section at line 270; DB_POSTGRESQL_SSL_OFF at line 277; DB_MYSQL_SSL_OFF at line 287                            |

---

### Key Link Verification

| From                                          | To                                              | Via                                        | Status     | Details                                                                                    |
|-----------------------------------------------|-------------------------------------------------|--------------------------------------------|------------|--------------------------------------------------------------------------------------------|
| `quirk/db.py init_db()`                       | `_ensure_v43_columns(engine)`                   | Direct call after _ensure_gcp_columns      | ✓ WIRED    | Line 125: `_ensure_v43_columns(engine)  # v4.3: add data-at-rest columns if missing`       |
| `scan_pg_targets()`                           | `pg_has_role(current_user, 'pg_read_all_stats', 'MEMBER')` | 3-tier probe                 | ✓ WIRED    | Line 110 in db_connector.py; NOT has_privilege (research correction applied)               |
| `scan_mysql_targets()`                        | `pymysql.connect(ssl_disabled=True)`            | SHOW STATUS LIKE 'Ssl_cipher'              | ✓ WIRED    | Line 200 in db_connector.py; ssl_disabled=True present                                     |
| `scan_aws_targets()`                          | `_scan_rds_encryption(session, logger)`         | results.extend() call                      | ✓ WIRED    | Line 259 in aws_connector.py: `results.extend(_scan_rds_encryption(session, logger))`     |
| `evidence.py build_evidence_summary`          | `dar_db_plaintext_count` / `dar_db_weak_ssl_count` | POSTGRESQL/MYSQL elif branches in loop  | ✓ WIRED    | elif proto == "POSTGRESQL" at line 145; elif proto == "MYSQL" at line 153                  |
| `scoring.py compute_readiness_score`          | `dar_score` via `_apply_weighted_impacts`       | dar_impacts list                           | ✓ WIRED    | Line 172: `dar_score, dar_drivers = _apply_weighted_impacts(dar_impacts)`                  |
| `run_scan.py session_start`                   | `db_scanning` block                             | _phase_timer + lazy import                 | ✓ WIRED    | db_scanning at line 481 > session_start at line 475; session_start passed to both scanners |
| `run_scan.py db_endpoints`                    | endpoint aggregation list                       | + db_endpoints expression                  | ✓ WIRED    | Line 545: `+ db_endpoints` between gcp_endpoints and dnssec_endpoints                      |

---

### Data-Flow Trace (Level 4)

| Artifact                    | Data Variable          | Source                                         | Produces Real Data | Status      |
|-----------------------------|------------------------|------------------------------------------------|--------------------|-------------|
| `quirk/intelligence/evidence.py` | `dar_db_plaintext_count` | POSTGRESQL/MYSQL protocol branches on endpoints list | Yes — increments on service_detail content | ✓ FLOWING |
| `quirk/intelligence/scoring.py` | `dar_score`            | `dar_db_plaintext` from evidence dict          | Yes — drives weighted impact formula       | ✓ FLOWING |
| End-to-end flow             | DB endpoints → scoring | run_scan.py → db_connector → evidence → scoring | Yes — verified via programmatic test       | ✓ FLOWING |

Verified programmatically: two POSTGRESQL/MYSQL ssl-off endpoints produce `dar_db_plaintext_count=2`, `dar_db_plaintext_ratio=1.0`, and `data_at_rest` subscore of 13 in the computed result.

---

### Behavioral Spot-Checks

| Behavior                                      | Command                                        | Result                              | Status   |
|-----------------------------------------------|------------------------------------------------|-------------------------------------|----------|
| 14 DB connector tests pass                    | `pytest tests/test_db_connector.py -q`         | 14 passed                           | ✓ PASS   |
| dar_ evidence counters present                | `pytest tests/test_intelligence_evidence.py -q`| 2 passed (incl. test_dar_db_counters)| ✓ PASS  |
| data_at_rest in scoring subscores             | `pytest tests/test_intelligence_scoring.py -q` | 8 passed                            | ✓ PASS   |
| End-to-end dar_ data flow                     | Python: endpoints → evidence → score           | dar_db_plaintext_count=2, score delivered | ✓ PASS |
| Full test suite (excl. 3 pre-existing failures)| `pytest tests/ -q --ignore=...`              | 363 passed, 1 skipped               | ✓ PASS   |
| docker-compose database profile targets       | Requires live Docker containers                | Not exercised                       | ? SKIP   |

Note: Pre-existing failures confirmed pre-dating Phase 27 via git stash:
- `test_cli_correctness.py::test_no_quirk_scan_references` — UAT-SERIES.md documentation issue
- `test_identity_surface.py::Issue3ScanWindowRegressionTest` — pre-existing regression
- `test_v41_gap_closure.py::test_package_manifest_version_is_4_1_0` — installed package version mismatch
- `test_dashboard_wiring.py::test_deps_default_db_path` — pre-existing quirk.db path mismatch (confirmed via stash)

---

### Requirements Coverage

| Requirement | Source Plans       | Description                                                                                                                | Status      | Evidence                                                                                        |
|-------------|--------------------|----------------------------------------------------------------------------------------------------------------------------|-------------|--------------------------------------------------------------------------------------------------|
| DB-01       | 27-01, 27-02, 27-04 | PostgreSQL SSL enforcement via pg_stat_ssl; plaintext-allowed as HIGH; graceful degradation without pg_read_all_stats     | ✓ SATISFIED | scan_pg_targets() 3-tier probe; pg_has_role check; scan_error='insufficient-privilege' emitted; 5 PostgreSQL tests pass |
| DB-02       | 27-01, 27-02, 27-04 | MySQL/MariaDB SSL session status; disabled or weak SSL as finding with negotiated cipher                                   | ✓ SATISFIED | scan_mysql_targets() with ssl_disabled=True; SHOW STATUS LIKE 'Ssl_cipher'; HIGH/MEDIUM findings; cipher in service_detail |
| DB-03       | 27-01, 27-02, 27-04 | RDS StorageEncrypted flag + encryption type; AWS-managed vs customer-managed key distinguished                             | ✓ SATISFIED | _scan_rds_encryption() in aws_connector.py; RDS/none (HIGH), RDS/sse-rds, RDS/sse-kms-aws, RDS/sse-kms-cmk; 3 RDS tests pass |

All three requirements are fully satisfied. No orphaned requirements — REQUIREMENTS.md maps only DB-01, DB-02, DB-03 to Phase 27.

Note on ROADMAP SC-2 wording: The roadmap references "StorageEncryptionType" as a conceptual label; the RESEARCH.md documents (Pitfall 3) that this is not an actual boto3 API field. The implementation correctly uses `StorageEncrypted` (bool) + `KmsKeyId` (string), deriving the equivalent classification. This is the correct behavior as documented in the plan.

---

### Anti-Patterns Found

| File                          | Line | Pattern               | Severity   | Impact                                                         |
|-------------------------------|------|-----------------------|------------|----------------------------------------------------------------|
| `quirk/scanner/db_connector.py` | 71  | `return []`           | ℹ️ Info    | Availability guard when psycopg2 not installed — not a stub    |
| `quirk/scanner/db_connector.py` | 183 | `return []`           | ℹ️ Info    | Availability guard when PyMySQL not installed — not a stub     |

Both `return []` occurrences are intentional availability guards behind `if not PSYCOPG2_AVAILABLE` / `if not PYMYSQL_AVAILABLE` checks. They are the correct behavior tested by `test_pg_unavailable_returns_empty` and `test_mysql_unavailable_returns_empty`. No genuine stubs found.

---

### Human Verification Required

#### 1. End-to-End Scan with Live Database Containers

**Test:** Start the database profile chaos lab with `docker compose --profile database up -d`, configure a QUIRK config with `enable_db: true`, `pg_targets: ["localhost:25432"]`, `mysql_targets: ["localhost:23306"]`, `pg_scanner_user: "quirk_scanner"`, `pg_scanner_password: "quirk_scanner"`, and run a full scan.

**Expected:** The scan pipeline produces:
- A POSTGRESQL endpoint with `severity=HIGH` and `service_detail='PostgreSQL/ssl-off'`
- A MYSQL endpoint with `severity=HIGH` and `service_detail='MySQL/ssl-off'`
- Both endpoints appear in the CBOM output (not as TLS entries — the Pass 1/2/3 skip protection must route them correctly)
- The readiness score includes a non-zero `data_at_rest` subscore reflecting the HIGH findings
- Run stats show a `db_scanning` phase timer entry

**Why human:** Requires Docker containers running, live psycopg2 and PyMySQL connections, and the full run_scan.py pipeline. Cannot be safely exercised programmatically without external services.

---

### Gaps Summary

No gaps blocking goal achievement. All five ROADMAP success criteria are verified against the actual codebase. All three requirement IDs (DB-01, DB-02, DB-03) are fully satisfied. The one human verification item is a UAT exercise for the chaos lab integration, which is standard for any scan phase.

---

_Verified: 2026-04-25_
_Verifier: Claude (gsd-verifier)_
