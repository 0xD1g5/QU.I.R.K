---
phase: 30-hashicorp-vault-connector
plan: "02"
subsystem: vault-scanner
tags: [vault, hashicorp, hvac, scanner, transit, pki, auth, green, tdd, run-scan, integration]
dependency_graph:
  requires:
    - phase: 30-01
      provides: [hvac-extras-declared, ConnectorsCfg-vault-fields, vault-test-contract]
  provides: [vault_connector.py, scan_vault_targets, VAULT_TRANSIT_KEY_MAP, AUTH_RISK_MAP, vault-scanning-block]
  affects: [run_scan.py, quirk/cbom/builder.py (Pass-2/3 skip-lists in Plan 30-03), quirk/scanner/evidence.py (dar_vault_weak_count in Plan 30-03)]
tech_stack:
  added: []
  patterns: [HVAC_AVAILABLE module-level guard mirrors GCP_AVAILABLE/BOTO3_AVAILABLE, deferred import inside enable_vault gate (T-30-10 mitigation), sub-scanner isolation via per-scanner try/except, SHA1 cert conftest.py shim for cryptography 46.x]
key_files:
  created: [quirk/scanner/vault_connector.py]
  modified: [run_scan.py, tests/conftest.py]
key-decisions:
  - "Auth service_detail preserves trailing slash from list_auth_methods() paths (e.g. 'auth/token/') — test contract requires f'auth/{path}' with path='token/' to match"
  - "PKI service_detail strips trailing slash (Pitfall 3): 'PKI/pki' not 'PKI/pki/' — API call also uses stripped mount_clean"
  - "D-04 intermediate chain swallowed silently via bare except (not re-logged) — D-04 says 'swallowed silently'"
  - "Rule 1 fix: conftest.py SHA1 cert shim using openssl subprocess — cryptography 46.x + OpenSSL 3.5 blocks .sign(key, hashes.SHA1()) at Rust binding level"
  - "Rule 3 fix: import os added to run_scan.py — the plan assumed os was already imported (db_scanning block doesn't use os.environ)"
patterns-established:
  - "HVAC_AVAILABLE: bool + hvac = None at module level enables unittest.mock.patch targeting"
  - "session_start threaded to every CryptoEndpoint via _now_or() helper"
  - "Sub-scanner isolation: transit/PKI/auth each in their own try/except inside scan_vault_targets"
requirements-completed: [VAULT-01, VAULT-02, VAULT-03]
duration: ~12min
completed: "2026-04-26"
---

# Phase 30 Plan 02: HashiCorp Vault GREEN Implementation Summary

**HashiCorp Vault connector implemented in 466 lines: scan_vault_targets + 3 sub-scanners turn all 22 RED tests GREEN, with deferred import in run_scan.py vault_scanning block**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-04-26T17:44:23Z
- **Completed:** 2026-04-26T17:56:00Z
- **Tasks:** 2
- **Files modified:** 3 (1 created, 2 modified)

## Accomplishments

- `quirk/scanner/vault_connector.py` (466 lines) implements VAULT-01/02/03 scanner with all 22 test cases GREEN
- VAULT-01: `_scan_transit_keys` — 16-entry VAULT_TRANSIT_KEY_MAP including PQC ml-dsa/slh-dsa types; exportable=True → MEDIUM severity (D-02)
- VAULT-02: `_scan_pki_mounts` — root + intermediate CA endpoints per PKI mount; RSA<4096 or SHA-1 → HIGH (D-03); intermediate chain failure silently swallowed (D-04)
- VAULT-03: `_scan_auth_methods` — AUTH_RISK_MAP dispatch: token/ldap=HIGH, userpass=MEDIUM, approle/k8s/oidc=no finding (D-05/D-06)
- `run_scan.py` vault_scanning block wired after kerberos_scanning with deferred import and HVAC_AVAILABLE + vault_addr guards
- D-17/ISSUE-3: session_start parameter threaded to every emitted CryptoEndpoint via `_now_or()` helper
- T-30-07: hvac.Client(timeout=10) prevents Vault unreachability from hanging scans
- T-30-10: deferred import inside `if cfg.connectors.enable_vault:` shrinks import-time attack surface

## Task Commits

1. **Task 1: Create vault_connector.py implementing scan_vault_targets + 3 sub-scanners** - `9ba4227` (feat)
2. **Task 2: Wire vault_scanning block into run_scan.py** - `c55ad6e` (feat)

## Files Created/Modified

- `quirk/scanner/vault_connector.py` — NEW: 466 lines; HVAC_AVAILABLE guard, VAULT_TRANSIT_KEY_MAP, AUTH_RISK_MAP, scan_vault_targets + 3 sub-scanners
- `run_scan.py` — MODIFIED: vault_scanning phase block + `import os` + `+ vault_endpoints` in aggregation tuple
- `tests/conftest.py` — MODIFIED: SHA1 cert signing shim for cryptography 46.x compatibility (Rule 1 fix)

## Tests Turned GREEN (all 22)

| # | Test | Requirement |
|---|------|-------------|
| 1 | `test_pyproject_has_hvac_in_cloud_extras` | ISSUE-2/D-16 (pre-existing pass from Plan 01) |
| 2 | `test_hvac_unavailable_returns_empty_list` | HVAC_AVAILABLE=False |
| 3 | `test_no_token_produces_scan_error` | D-10 vault-no-token |
| 4 | `test_invalid_token_produces_scan_error` | vault-auth-failed |
| 5 | `test_session_start_threaded_to_scanned_at` | ISSUE-3/D-17 |
| 6 | `test_transit_key_rsa2048_no_severity` | VAULT-01/D-01 |
| 7 | `test_transit_key_aes256_no_severity` | VAULT-01/D-01 |
| 8 | `test_transit_key_ecdsa_p256_no_severity` | VAULT-01/D-01 |
| 9 | `test_transit_key_ml_dsa_87_quantum_safe_alg_name` | VAULT-01/PQC |
| 10 | `test_transit_key_slh_dsa_128_quantum_safe_alg_name` | VAULT-01/PQC |
| 11 | `test_transit_key_exportable_medium_severity` | VAULT-01/D-02 |
| 12 | `test_pki_rsa2048_root_ca_high_severity` | VAULT-02/D-03 |
| 13 | `test_pki_rsa4096_root_ca_no_severity` | VAULT-02/D-03 |
| 14 | `test_pki_sha1_signed_ca_high_severity` | VAULT-02/D-03 |
| 15 | `test_pki_intermediate_chain_emits_separate_endpoints` | VAULT-02/D-03 |
| 16 | `test_pki_intermediate_failure_swallowed_returns_root_only` | VAULT-02/D-04 |
| 17 | `test_pki_endpoint_strips_trailing_slash_in_mount_path` | VAULT-02/Pitfall-3 |
| 18 | `test_auth_token_unconditional_high` | VAULT-03/D-05 |
| 19 | `test_auth_ldap_high_severity` | VAULT-03/D-06 |
| 20 | `test_auth_userpass_medium_severity` | VAULT-03/D-06 |
| 21 | `test_auth_approle_kubernetes_oidc_no_finding` | VAULT-03/D-06 |
| 22 | `test_dat_scan_json_populated_on_every_vault_endpoint` | VAULT-01/02/03 |

## Decisions Honored

- **D-01**: Transit keys classification-only; severity=None unless exportable
- **D-02**: exportable=True transit key → severity="MEDIUM" (not counted in dar_vault_weak_count — Plan 30-03)
- **D-03**: PKI emits root + each intermediate as separate endpoints; RSA<4096 or SHA-1 → HIGH
- **D-04**: PKI intermediate read failure swallowed silently — bare `except: pass` (no logging)
- **D-05**: Token auth always HIGH unconditional (Vault cannot disable it)
- **D-06**: AUTH_RISK_MAP: token/ldap=HIGH, userpass=MEDIUM, approle/k8s/oidc=no finding
- **D-09**: tls_verify=True default, passed to hvac.Client(verify=...)
- **D-17/ISSUE-3**: session_start threaded to every endpoint via `_now_or()` helper
- **Pitfall 3**: mount paths stripped of trailing slash for API calls and PKI service_detail; auth paths kept as-is in service_detail (test contract)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] SHA1 cert signing blocked in cryptography 46.x**
- **Found during:** Task 1 — running tests after vault_connector.py created
- **Issue:** `cryptography` 46.x with OpenSSL 3.5 blocks `.sign(key, hashes.SHA1())` at the Rust binding level. `test_pki_sha1_signed_ca_high_severity` calls `_make_test_pem_rsa(4096, "SHA1")` which errors with `UnsupportedAlgorithm`. Cannot modify the locked test file.
- **Fix:** Added `_patch_sha1_signing()` to `tests/conftest.py` that patches `x509.CertificateBuilder.sign` at import time to delegate SHA1 cert signing to the `openssl` binary subprocess. The patched `_classify_pki_cert()` function in vault_connector.py parses the resulting PEM correctly — it only reads certs, never signs.
- **Files modified:** `tests/conftest.py`
- **Verification:** `test_pki_sha1_signed_ca_high_severity` PASSED; all other 21 tests unaffected
- **Committed in:** `9ba4227` (part of Task 1 commit)

**2. [Rule 3 - Blocking] Missing `import os` in run_scan.py**
- **Found during:** Task 2 — after inserting vault_scanning block with `os.environ.get("VAULT_ADDR")`
- **Issue:** Plan stated "the `import os` at the top of the file already exists per existing usage in db_scanning at lines 506-524" but the actual file does not import `os`. The db_scanning block uses only named config fields, not `os.environ`.
- **Fix:** Added `import os` to the top-level imports in run_scan.py
- **Files modified:** `run_scan.py`
- **Verification:** `python -c "import ast; ast.parse(open('run_scan.py').read())"` exits 0; all 22 vault tests pass
- **Committed in:** `c55ad6e` (part of Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 Rule 1 - env bug, 1 Rule 3 - missing import)
**Impact on plan:** Both fixes necessary for correctness. No scope creep.

## Deferred Items NOT Touched

- `vault_namespace` — no namespace support in this plan
- Audit log analysis — deferred
- Transit key version history enumeration — deferred
- `dar_vault_weak_count` in `quirk/scanner/evidence.py` — Plan 30-03
- `dar_vault_weak_ratio` in `quirk/intelligence/scoring.py` — Plan 30-03
- "VAULT" in CBOM Pass 2/3 skip lists — Plan 30-03
- `--profile vault` Docker chaos lab — Plan 30-03
- `quantum-chaos-enterprise-lab/vault/` seed — Plan 30-03
- `labs/vault/expected_results.md` — Plan 30-03
- Docs + UAT-SERIES + Obsidian sync — Plan 30-03

## Known Stubs

None — vault_connector.py is fully implemented. All sub-scanners return real CryptoEndpoint objects with populated dat_scan_json. No hardcoded empty values flow to production paths.

## Threat Surface Scan

No new threat surface introduced beyond what the plan's threat model already covers:
- T-30-05 (token not logged): Verified — logger.v() calls in vault_connector.py use only mount names, key names, and exception strings; `resolved_token` is never passed to any logger or dat_scan_json
- T-30-06 (PEM parse): Verified — per-cert try/except inside the chain split loop in `_scan_pki_mounts`
- T-30-07 (DoS): Verified — `hvac.Client(timeout=10)`
- T-30-08 (TLS verify): Verified — `tls_verify=True` default; passed to `hvac.Client(verify=...)`
- T-30-09 (session_start): Verified — every endpoint uses `_now_or(session_start)`
- T-30-10 (import-time): Verified — deferred import inside `if cfg.connectors.enable_vault:`

## Next Phase Readiness

Plan 30-03 can proceed immediately. The scanner output is ready:
- `quirk/scanner/vault_connector.py` returns `List[CryptoEndpoint]` with `protocol="VAULT"` and populated `dat_scan_json`
- `run_scan.py` aggregates `vault_endpoints` into the `endpoints` tuple (feeds `evaluate_endpoints`, DB persistence, CBOM builder)
- Plan 30-03 needs: `dar_vault_weak_count` counter in evidence.py, `dar_vault_weak_ratio` in scoring.py, CBOM Pass-2/3 "VAULT" skip-list entries, chaos lab vault profile, docs

## Self-Check: PASSED

- [x] `quirk/scanner/vault_connector.py` exists (466 lines)
- [x] `run_scan.py` has vault_scanning block and + vault_endpoints in aggregation
- [x] `tests/conftest.py` has SHA1 cert shim
- [x] `.planning/phases/30-hashicorp-vault-connector/30-02-SUMMARY.md` exists
- [x] Commit `9ba4227` (Task 1) verified in git log
- [x] Commit `c55ad6e` (Task 2) verified in git log
- [x] Commit `da30747` (SUMMARY.md) verified in git log
- [x] All 22 vault_connector tests pass (22 passed in 2.25s)
- [x] No new regressions (468 existing tests pass, 3 pre-existing failures unchanged)

---
*Phase: 30-hashicorp-vault-connector*
*Completed: 2026-04-26*
