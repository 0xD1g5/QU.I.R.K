---
phase: 26-gcp-connector
plan: 03
subsystem: pipeline-wiring
tags: [gcp, cloud-connector, run-scan, cbom-builder, pqc, wiring]

# Dependency graph
requires:
  - phase: 26-gcp-connector
    plan: 02
    provides: "quirk/scanner/gcp_connector.py with scan_gcp_targets, GCP_KMS_ALGORITHM_MAP"

provides:
  - "run_scan.py: import scan_gcp_targets and GCP scan phase with enable_gcp guard"
  - "run_scan.py: gcp_endpoints aggregated into combined endpoint list after azure_endpoints"
  - "quirk/cbom/builder.py: _normalize_cloud_key_spec handles 31 GCP algorithm strings including PQC"
  - "quirk/cbom/builder.py Pass 1: protocol GCP endpoints processed through cloud branch"
  - "quirk/cbom/builder.py Pass 1: protocol CLOUD_SQL endpoints processed through dedicated branch"
  - "quirk/cbom/builder.py Pass 2: GCP and CLOUD_SQL skipped (no X.509 certs)"
  - "quirk/cbom/builder.py Pass 3: GCP and CLOUD_SQL skipped (not TLS/SSH protocol components)"

affects:
  - 28-object-storage

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "GCP scan phase block follows AWS/Azure pattern exactly: _phase_timer + enable_gcp guard"
    - "gcp_algorithm key lookup chained into key_spec extraction alongside KeySpec/KeyAlgorithm/key_type"
    - "GCS-SUMMARY sentinel excluded from cert_pubkey_alg registration via not-in guard"
    - "CLOUD_SQL branch maps cert_pubkey_alg (severity string) directly to algo_registry"

key-files:
  created: []
  modified:
    - run_scan.py
    - quirk/cbom/builder.py

key-decisions:
  - "GCS-SUMMARY sentinel excluded from cert_pubkey_alg registration with explicit not-in guard rather than relying on _register_algorithm tolerance — more explicit and safe"
  - "gcp_endpoints placed after azure_endpoints in aggregation to keep cloud connectors grouped together"
  - "CLOUD_SQL cert_pubkey_alg holds severity level (HIGH/MEDIUM); registered directly to algo_registry since it is a finding label not a cryptographic algorithm — consistent with how CLOUD_SQL data is structured in gcp_connector.py"

# Metrics
duration: ~8min
completed: 2026-04-25
---

# Phase 26 Plan 03: GCP Connector Pipeline Wiring Summary

**GCP scan phase wired into run_scan.py behind enable_gcp guard; CBOM builder extended for GCP and CLOUD_SQL in all three passes with 31-entry GCP algorithm mapping including PQC types — end-to-end data flow for Phase 26 complete**

## Performance

- **Duration:** ~8 min
- **Completed:** 2026-04-25
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Added `from quirk.scanner.gcp_connector import scan_gcp_targets` import to run_scan.py (between azure_connector and dnssec_scanner imports — keeps cloud connectors grouped)
- Added GCP cloud connector phase block in run_scan.py: `gcp_endpoints = []` initialization, `_phase_timer(run_stats, "gcp_scanning")` context manager, `if cfg.connectors.enable_gcp:` guard, `scan_gcp_targets(project_id=cfg.connectors.gcp_project_id or "", logger=logger)` call
- Added `+ gcp_endpoints` to endpoint aggregation after `azure_endpoints` and before `dnssec_endpoints` — cloud connectors kept together
- Extended `_normalize_cloud_key_spec()` docstring and mapping dict with 31 GCP Cloud KMS algorithm strings: RSA signing variants (PKCS1/PSS/Raw), RSA decrypt (OAEP variants), EC signing (P256/P384/secp256k1/Ed25519), HMAC (SHA1/224/256/384/512), symmetric (AES-128/256 GCM/CBC/CTR, Google Symmetric), external, and PQC (ML-KEM-768/1024, KEM-XWING, ML-DSA-44/65/87, SLH-DSA, external-MU variants)
- Extended Pass 1 cloud branch: `("AWS", "AZURE", "GCP")` tuple; `gcp_algorithm` key added to key_spec extraction chain; new `CLOUD_SQL` branch that registers severity level
- Extended Pass 2 skip list: `("SSH", "CONTAINER", "SOURCE", "KERBEROS", "SAML", "DNSSEC", "GCP", "CLOUD_SQL")`
- Extended Pass 3 skip list: `("JWT", "CONTAINER", "SOURCE", "AWS", "AZURE", "GCP", "CLOUD_SQL", "DNSSEC", "SAML", "KERBEROS")`
- All 45 cloud connector + CBOM builder tests pass; full test suite at 352 passed with only 3 pre-existing failures unrelated to this plan

## Task Commits

1. **Task 1: Wire GCP connector into run_scan.py** - `f3b518e` (feat)
2. **Task 2: Extend CBOM builder for GCP and CLOUD_SQL protocols** - `476471f` (feat)

## Files Created/Modified

- `run_scan.py` - Added import, GCP scan phase block (11 lines), and gcp_endpoints in aggregation (3 edits)
- `quirk/cbom/builder.py` - Extended _normalize_cloud_key_spec (31 GCP entries), Pass 1 cloud branch, Pass 2 skip list, Pass 3 skip list, new CLOUD_SQL branch (4 edits)

## Decisions Made

- GCS-SUMMARY sentinel endpoint (from `_scan_gcs`) sets `cert_pubkey_alg="GCS-SUMMARY"` and carries no real algorithm. Added explicit `not in ("GCS-SUMMARY",)` guard in Pass 1 to prevent "GCS-SUMMARY" from being registered as a cryptographic algorithm name. The original `if ep.cert_pubkey_alg:` check would have passed for "GCS-SUMMARY" since it is truthy.
- `gcp_endpoints` placed after `azure_endpoints` in the aggregation tuple to keep all three cloud connectors (AWS, Azure, GCP) grouped before the identity scanners (DNSSEC, SAML, Kerberos).

## Deviations from Plan

### Auto-added correctness guard

**1. [Rule 2 - Missing Critical Functionality] Added GCS-SUMMARY sentinel exclusion in Pass 1**
- **Found during:** Task 2
- **Issue:** The plan's Pass 1 code said "Also register cert_pubkey_alg if set (ACM certs)" with an `if ep.cert_pubkey_alg:` guard. The GCS sentinel sets `cert_pubkey_alg="GCS-SUMMARY"` which is truthy, so without the guard it would register "GCS-SUMMARY" as a cryptographic algorithm in the CBOM — which is incorrect.
- **Fix:** Added `and ep.cert_pubkey_alg not in ("GCS-SUMMARY",)` to the cert_pubkey_alg registration guard in the AWS/AZURE/GCP branch.
- **Files modified:** `quirk/cbom/builder.py`
- **Commit:** `476471f`

## Pre-existing Issues (Out of Scope)

The following test failures existed before this plan and are unrelated to the wiring changes:
- `tests/test_cli_correctness.py::test_no_quirk_scan_references` — legacy `quirk scan` syntax in docs/UAT-SERIES.md lines 1526 and 3157 (documented in Plan 02 SUMMARY)
- `tests/test_identity_surface.py::Issue3ScanWindowRegressionTest::test_issue3_scan_window_returns_all_identity_protocols` — pre-existing identity surface test failure
- `tests/test_v41_gap_closure.py::TestV41GapClosure::test_package_manifest_version_is_4_1_0` — version mismatch pre-existing since v4.2+ bump

These are logged for deferred resolution. This plan's changes did not cause or worsen any of them.

## Known Stubs

None — all wiring is complete. The GCP scan phase executes real `scan_gcp_targets()` when `enable_gcp=True` and `gcp_project_id` is set. No placeholder values or hardcoded empty returns introduced.

## Threat Flags

No new threat surface beyond the plan's threat model (T-26-08, T-26-09, T-26-10):
- T-26-08 (Tampering/cloud_scan_json parsing): Existing `try/except (json.JSONDecodeError, TypeError, ValueError)` around `json.loads` already protects the new `gcp_algorithm` key extraction
- T-26-09 (Info Disclosure/algorithm registration): GCP algorithm names are public KMS metadata; no secrets exposed
- T-26-10 (DoS/_normalize_cloud_key_spec): Mapping dict now has ~60 entries total; O(1) lookup remains

## Self-Check: PASSED

| Check | Result |
|-------|--------|
| `run_scan.py` contains `scan_gcp_targets` import | FOUND |
| `run_scan.py` contains `gcp_endpoints = []` | FOUND |
| `run_scan.py` contains `enable_gcp` guard | FOUND |
| `run_scan.py` contains `+ gcp_endpoints` in aggregation | FOUND |
| `quirk/cbom/builder.py` contains `GCP` in Pass 1 | FOUND (line 371) |
| `quirk/cbom/builder.py` contains `CLOUD_SQL` in Pass 1 | FOUND (line 388) |
| `quirk/cbom/builder.py` contains `GCP` in Pass 2 | FOUND (line 432) |
| `quirk/cbom/builder.py` contains `GCP` in Pass 3 | FOUND (line 511) |
| `quirk/cbom/builder.py` `_normalize_cloud_key_spec` handles RSA_SIGN_PKCS1_2048_SHA256 | PASSED |
| `quirk/cbom/builder.py` `_normalize_cloud_key_spec` handles ML_KEM_768 | PASSED |
| Commit `f3b518e` exists | FOUND |
| Commit `476471f` exists | FOUND |
| `pytest tests/test_cloud_connectors.py` | 15 passed |
| `pytest tests/test_cbom_builder.py` | 30 passed |
