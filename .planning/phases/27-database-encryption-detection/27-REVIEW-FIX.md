---
phase: 27-database-encryption-detection
fixed_at: 2026-04-25T00:00:00Z
review_path: .planning/phases/27-database-encryption-detection/27-REVIEW.md
iteration: 1
fix_scope: critical_warning
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 27: Code Review Fix Report

**Fixed at:** 2026-04-25
**Source review:** `.planning/phases/27-database-encryption-detection/27-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 4
- Fixed: 4
- Skipped: 0

## Fixed Issues

### WR-01: Connection errors silently drop the target — no scan_error endpoint emitted

**Files modified:** `quirk/scanner/db_connector.py`
**Commit:** d317f1a
**Applied fix:** Added `results.append(CryptoEndpoint(..., scan_error=f"connection-error: {type(exc).__name__}", ...))` in both the PostgreSQL `except Exception` block (line 152) and the MySQL `except Exception` block (line 244). Both now emit a scan_error endpoint with `protocol="POSTGRESQL"` or `protocol="MYSQL"` respectively, consistent with other scanners in the codebase.

---

### WR-02: Unencrypted RDS instances not counted in `dar_db_plaintext_count`

**Files modified:** `quirk/intelligence/evidence.py`
**Commit:** 130c436
**Applied fix:** Added an `elif proto == "RDS":` branch after the existing `elif proto == "MYSQL":` block. The branch checks for `"RDS/none"` in `service_detail` and increments `dar_db_plaintext_count`. Encrypted RDS instances (`RDS/sse-rds`, `RDS/sse-kms-*`) are explicitly left with no penalty, per reviewer guidance.

---

### WR-03: `_ensure_v43_columns` migrates `severity` as `TEXT`, not `VARCHAR(16)` — docstring also misleading

**Files modified:** `quirk/db.py`
**Commit:** b9b8673
**Applied fix:** Replaced `_V43_COLUMNS = ["dat_scan_json", "severity"]` (single type for all) with `_V43_COLUMN_DDLS = {"dat_scan_json": "TEXT", "severity": "VARCHAR(16)"}` (per-column DDL dict). Updated the loop to unpack `(col, col_type)` and interpolate both into the `ALTER TABLE` statement. Updated the docstring from "Add v4.3 data-at-rest JSON column" (singular, implied TEXT-only) to "Add v4.3 data-at-rest columns (dat_scan_json TEXT, severity VARCHAR(16)) if absent."

---

### WR-04: `_scan_rds_encryption` hardcodes `port=5432` for all RDS engine types

**Files modified:** `quirk/scanner/aws_connector.py`
**Commit:** 05729ff
**Applied fix:** Added `db_port = int((db.get("Endpoint") or {}).get("Port") or 5432)` immediately before the `CryptoEndpoint` construction and replaced the hardcoded `port=5432` with `port=db_port`. The `or 5432` fallback preserves safe behaviour when the `Endpoint` dict is absent (e.g., instances that have not yet been assigned an endpoint).

---

_Fixed: 2026-04-25_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
