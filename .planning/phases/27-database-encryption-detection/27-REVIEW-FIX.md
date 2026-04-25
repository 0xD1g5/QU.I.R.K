---
phase: 27-database-encryption-detection
fixed_at: 2026-04-25T20:51:51Z
review_path: .planning/phases/27-database-encryption-detection/27-REVIEW.md
fix_scope: all
findings_in_scope: 9
fixed: 9
skipped: 0
iteration: 1
status: all_fixed
---

# Phase 27: Code Review Fix Report

**Fixed at:** 2026-04-25T20:51:51Z
**Source review:** `.planning/phases/27-database-encryption-detection/27-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 9
- Fixed: 9
- Skipped: 0

Note: WR-01 through WR-04 were applied in a prior pass and are recorded here for completeness. IN-01 through IN-05 were applied in this pass.

---

## Fixed Issues

### WR-01: Connection errors silently drop the target — no scan_error endpoint emitted

**Files modified:** `quirk/scanner/db_connector.py`
**Commit:** `d317f1a` (prior pass)
**Applied fix:** Added `results.append(CryptoEndpoint(..., scan_error=f"connection-error: {type(exc).__name__}", ...))` in both the PostgreSQL `except Exception` block and the MySQL `except Exception` block. Both now emit a scan_error endpoint consistent with other scanners.

---

### WR-02: Unencrypted RDS instances not counted in `dar_db_plaintext_count`

**Files modified:** `quirk/intelligence/evidence.py`
**Commit:** `130c436` (prior pass)
**Applied fix:** Added an `elif proto == "RDS":` branch after `elif proto == "MYSQL":`. The branch checks for `"RDS/none"` in `service_detail` and increments `dar_db_plaintext_count`. Encrypted RDS variants produce no penalty.

---

### WR-03: `_ensure_v43_columns` migrates `severity` as `TEXT`, not `VARCHAR(16)`

**Files modified:** `quirk/db.py`
**Commit:** `b9b8673` (prior pass)
**Applied fix:** Replaced `_V43_COLUMNS` list with `_V43_COLUMN_DDLS` dict mapping each column to its DDL type. Updated loop to unpack `(col, col_type)` and updated docstring to list both columns explicitly.

---

### WR-04: `_scan_rds_encryption` hardcodes `port=5432` for all RDS engine types

**Files modified:** `quirk/scanner/aws_connector.py`
**Commit:** `05729ff` (prior pass)
**Applied fix:** Added `db_port = int((db.get("Endpoint") or {}).get("Port") or 5432)` before the `CryptoEndpoint` construction and replaced hardcoded `port=5432` with `port=db_port`.

---

### IN-01: `ssl_disabled=True` means `Ssl_cipher` is always empty — "strong cipher" branch unreachable

**Files modified:** `quirk/scanner/db_connector.py`
**Commit:** `cbcddf1`
**Applied fix:** Added a 4-line `# NOTE:` comment block immediately above `cur.execute("SHOW STATUS LIKE 'Ssl_cipher'")` in `scan_mysql_targets`, explaining that `ssl_disabled=True` makes the session cipher always empty and that the meaningful signal is server acceptance of a plaintext connection.

---

### IN-02: Version not bumped to 4.3.0

**Files modified:** `pyproject.toml`, `quirk/cbom/builder.py`, `quirk/config.py`
**Commit:** `17b53b8`
**Applied fix:** Bumped `version` to `"4.3.0"` in `pyproject.toml`, `PLATFORM_VERSION` to `"4.3.0"` in `builder.py`, and `intelligence_version` default to `"4.3.0"` in `config.py`.

---

### IN-03: `ConnectorsCfg` construction raises `TypeError` on unrecognized YAML keys

**Files modified:** `quirk/config.py`
**Commit:** `4fbc8fa`
**Applied fix:** Added `import dataclasses` at the top of the file. Defined `_KNOWN_CONNECTOR_KEYS = {f.name for f in dataclasses.fields(ConnectorsCfg)}` at module level before `config_from_dict`. Replaced the `if k != "enable_windows_adcs"` filter with `if k in _KNOWN_CONNECTOR_KEYS` in the `ConnectorsCfg` construction.

---

### IN-04: Magic number `125` in score upper-bound assertion

**Files modified:** `tests/test_intelligence_scoring.py`
**Commit:** `8b5649b`
**Applied fix:** Defined `MAX_SUBSCORE = 25` and `NUM_SUBSCORES = 5` as named constants inline in the test method, and replaced `self.assertLessEqual(result["score"], 125)` with `self.assertLessEqual(result["score"], MAX_SUBSCORE * NUM_SUBSCORES)`.

---

### IN-05: Stray Kerberos sentence in Phase 27 MySQL section of expected_results_v3.md

**Files modified:** `quantum-chaos-enterprise-lab/expected_results_v3.md`
**Commit:** `916cbd7`
**Applied fix:** Replaced the copy-pasted Kerberos expected-output sentence at the end of the `mysql-ssl-off` section with the correct MySQL expected result: `**Expected:** DB scanner returns 1 HIGH finding (\`DB_MYSQL_SSL_OFF\`) for \`localhost:23306\`.`

---

_Fixed: 2026-04-25T20:51:51Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
