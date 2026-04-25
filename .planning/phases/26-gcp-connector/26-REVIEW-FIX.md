---
phase: 26-gcp-connector
fixed_at: 2026-04-25T00:00:00Z
review_path: .planning/phases/26-gcp-connector/26-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 26: Code Review Fix Report

**Fixed at:** 2026-04-25
**Source review:** .planning/phases/26-gcp-connector/26-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 4
- Fixed: 4
- Skipped: 0

## Fixed Issues

### WR-01: SQL injection via column-name string interpolation in db.py migration

**Files modified:** `quirk/db.py`
**Commit:** 3461568
**Applied fix:** Added `import re` and a module-level `_SAFE_COL_RE = re.compile(r"^[a-z][a-z0-9_]*$")` constant. Both `_ensure_identity_columns()` and `_ensure_gcp_columns()` now validate each column name against this pattern before interpolating it into the `ALTER TABLE` DDL. Any non-conforming name raises `ValueError` immediately, eliminating the SQL injection surface.

---

### WR-02: CBOM builder registers Cloud SQL severity strings as algorithm components

**Files modified:** `quirk/cbom/builder.py`
**Commit:** 32dcf70
**Applied fix:** Replaced the `CLOUD_SQL` branch body (which called `_register_algorithm(ep.cert_pubkey_alg, ...)` unconditionally) with a `pass` and an explanatory comment. Severity labels (`"HIGH"`, `"MEDIUM"`) stored in `cert_pubkey_alg` are no longer registered as CycloneDX algorithm components. Finding detail remains available via `cloud_scan_json`.

---

### WR-03: KMS keys with CRYPTO_KEY_VERSION_ALGORITHM_UNSPECIFIED are emitted as endpoints

**Files modified:** `quirk/scanner/gcp_connector.py`
**Commit:** 5a2e20b
**Applied fix:** Added a `continue` guard immediately after the `GCP_KMS_ALGORITHM_MAP.get()` call. When `alg_name == "UNKNOWN"`, the key is logged at verbose level (if a logger is present) and skipped — no `CryptoEndpoint` is created and no database row is inserted. This filters both `CRYPTO_KEY_VERSION_ALGORITHM_UNSPECIFIED` (explicitly mapped to `"UNKNOWN"`) and any unrecognised algorithm strings.

---

### WR-04: Mock service does not terminate all list_next() paths in test helper

**Files modified:** `tests/test_cloud_connectors.py`
**Commit:** 91f4a21
**Applied fix:** Added three `assert_called_once()` checks at the end of `test_gcp_kms_algorithm_mapping`, one for each KMS pagination level (`locations.list_next`, `keyRings.list_next`, `cryptoKeys.list_next`). These assertions confirm that each `list_next` path was invoked exactly once and returned `None` (the pre-wired termination value), catching any future regression where a new pagination path auto-creates a truthy `MagicMock` and loops.

---

_Fixed: 2026-04-25_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
