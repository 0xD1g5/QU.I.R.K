---
phase: 26-gcp-connector
plan: 02
subsystem: scanner
tags: [gcp, cloud-connector, kms, cloud-sql, gcs, crypto-inventory, pqc]

# Dependency graph
requires:
  - phase: 26-gcp-connector
    plan: 01
    provides: "[cloud] extras group, ConnectorsCfg GCP fields, gcs_scan_json ORM column, Wave 0 test scaffold"

provides:
  - "quirk/scanner/gcp_connector.py: complete GCP connector module"
  - "GCP_AVAILABLE flag with graceful degradation when SDK not installed"
  - "GCP_KMS_ALGORITHM_MAP: 47-entry algorithm map covering symmetric, RSA, EC, HMAC, PQC, external"
  - "_scan_kms: Cloud KMS key enumeration with auto-location discovery and list_next pagination"
  - "_scan_cloud_sql: Cloud SQL TLS enforcement detection for all sslMode values"
  - "_scan_gcs: GCS bucket encryption detection with gcs_scan_json Phase 28 hand-off"
  - "scan_gcp_targets: public entry point with ADC credential acquisition and graceful error handling"

affects:
  - 26-03-gcp-connector-wiring
  - 28-object-storage

# Tech tracking
tech-stack:
  added:
    - "google-api-python-client Discovery API pattern: build('cloudkms'/'sqladmin'/'storage', 'v1', credentials=creds)"
    - "google.auth.default() ADC acquisition with DefaultCredentialsError handling"
  patterns:
    - "list_next() pagination pattern for all three GCP Discovery API services"
    - "Sentinel endpoint pattern: one gcs_scan_json endpoint per project for Phase 28 hand-off"
    - "Two-point DefaultCredentialsError catch: at google.auth.default() and as generic Exception fallback"

key-files:
  created:
    - quirk/scanner/gcp_connector.py
  modified: []

key-decisions:
  - "Used google-api-python-client (not google-cloud-kms) per D-02 to avoid grpcio/protobuf dependency conflict"
  - "DefaultCredentialsError caught at google.auth.default() as generic Exception to handle all auth failure modes"
  - "None/empty/SSL_MODE_UNSPECIFIED sslMode mapped to ALLOW_UNENCRYPTED_AND_ENCRYPTED per Pitfall 7"
  - "response.get('items') used for GCS buckets list per Pitfall 4 (not 'buckets')"
  - "primary field guarded with key.get('primary') or {} per Pitfall 3 for asymmetric signing keys"
  - "Single sentinel endpoint carries gcs_scan_json for Phase 28 zero-duplicate hand-off per D-03"

# Metrics
duration: 15min
completed: 2026-04-25
---

# Phase 26 Plan 02: GCP Connector Implementation Summary

**GCP connector module with 47-entry algorithm map, auto-location-discovery KMS enumeration, Cloud SQL TLS enforcement detection, and GCS CMEK/Google-Managed classification with gcs_scan_json Phase 28 hand-off -- all 9 previously-skipped GCP tests now pass**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-04-25T12:00:00Z
- **Completed:** 2026-04-25T12:17:52Z
- **Tasks:** 1
- **Files created:** 1 (417 lines)

## Accomplishments

- Created `quirk/scanner/gcp_connector.py` (417 lines) as the primary deliverable for Phase 26
- Implemented `GCP_AVAILABLE` flag with module-level `None` assignments for test patching (`_gcp_build`, `google`, `DefaultCredentialsError`)
- Built `GCP_KMS_ALGORITHM_MAP` with all 47 `CryptoKeyVersionAlgorithm` entries from cloudkms.v1.json, covering: symmetric (AES-128/256 GCM/CBC/CTR, Google Symmetric), RSA signing (PKCS1/PSS/Raw), RSA decrypt (OAEP variants), EC signing (P256/P384/secp256k1/Ed25519), HMAC (SHA1/224/256/384/512), external, PQC (ML-KEM-768/1024, KEM-XWING, ML-DSA-44/65/87, SLH-DSA, external-MU variants), and UNSPECIFIED
- Implemented `_scan_kms()` with auto-discovery of all GCP locations via `projects.locations.list()` and `list_next()` pagination through locations → key rings → crypto keys; primary version guarded with `key.get("primary") or {}`; disabled/destroyed states skipped
- Implemented `_scan_cloud_sql()` with full `sslMode` mapping: ALLOW_UNENCRYPTED → HIGH, ENCRYPTED_ONLY → MEDIUM, TRUSTED_CLIENT_CERTIFICATE_REQUIRED → no finding, None/empty/SSL_MODE_UNSPECIFIED → HIGH
- Implemented `_scan_gcs()` with `response.get("items")` (not "buckets"), sentinel endpoint with `gcs_scan_json` for Phase 28, per-bucket CMEK/Google-Managed classification
- Implemented `scan_gcp_targets()` with V5 input validation (empty project_id guard), ADC credential acquisition, DefaultCredentialsError → `scan_error` endpoint, service-level build error isolation
- All 9 previously-skipped GCP tests now PASS (15/15 cloud connector tests green, 0 skips)

## Task Commits

1. **Task 1: Create gcp_connector.py with KMS, Cloud SQL, and GCS scanning** - `b4aa2fd` (feat)

## Files Created/Modified

- `quirk/scanner/gcp_connector.py` - Created (417 lines): complete GCP connector module with all three scan functions, 47-entry algorithm map, and public entry point

## Decisions Made

- Caught `DefaultCredentialsError` as generic `Exception` at `google.auth.default()` rather than as the specific exception type, because when `GCP_AVAILABLE=True` in tests but `google` is mocked, the `DefaultCredentialsError` class reference may differ. This ensures the test `test_gcp_credentials_error_graceful` (which uses `Exception` side effect) passes correctly while still producing the `scan_error` endpoint as required.
- Isolated each service build (`_gcp_build()` call) in its own try/except so a failure building one service (e.g., sqladmin) does not prevent scanning with other services (kms, storage).
- `versionTemplate.algorithm` fallback used for asymmetric keys where `primary` may not be present — covers Pitfall 3 edge case fully.

## Deviations from Plan

None — plan executed exactly as written. All pitfalls avoided, all decisions honored (D-01 through D-08).

## Pre-existing Issues Found (Out of Scope)

- `test_no_quirk_scan_references` in `tests/test_cli_correctness.py` fails on `docs/UAT-SERIES.md` lines 1526 and 3157 which contain legacy `quirk scan` CLI syntax. This failure was present before this plan ran and is unrelated to `gcp_connector.py`. Logged for Phase 26 plan 03 or next UAT-SERIES.md update.

## Known Stubs

None — `gcs_scan_json` is written on the sentinel endpoint with real bucket data. All three scan functions return live data when credentials are available. No placeholder values.

## Threat Flags

No new threat surface beyond the plan's threat model (T-26-03 through T-26-07):
- T-26-03 (Tampering/project_id): Mitigated — empty/None project_id returns `[]` with logger warning before any API call
- T-26-04 (Info Disclosure/credentials): Mitigated — exception message stored in `scan_error`, credential objects never logged
- T-26-07 (EoP/permissions): Mitigated — connector only calls read-only APIs (list operations); minimum IAM roles documented in module docstring

## Self-Check: PASSED

| Check | Result |
|-------|--------|
| `quirk/scanner/gcp_connector.py` exists | FOUND |
| `.planning/phases/26-gcp-connector/26-02-SUMMARY.md` exists | FOUND |
| Commit `b4aa2fd` exists | FOUND |
| `pytest tests/test_cloud_connectors.py` | 15 passed, 0 failed, 0 skipped |
