---
phase: 26-gcp-connector
verified: 2026-04-25T12:30:00Z
status: passed
score: 20/20 must-haves verified
overrides_applied: 0
re_verification: false
---

# Phase 26: GCP Connector Verification Report

**Phase Goal:** Add a GCP connector that scans Cloud KMS key specs, Cloud SQL TLS enforcement, and GCS bucket encryption — populating CryptoEndpoints and CBOM output.
**Verified:** 2026-04-25T12:30:00Z
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

All must-haves drawn from three plan frontmatter sets plus roadmap success criteria for GCP-01, GCP-02, and GCP-03.

**Plan 01 Truths**

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `pip install quirk[cloud]` resolves google-api-python-client and google-auth without grpcio | VERIFIED | `pyproject.toml` lines 44-47 contain `cloud = ["google-api-python-client>=2.0.0", "google-auth>=2.36.0"]`; no grpcio or google-cloud-kms found in file |
| 2 | ConnectorsCfg has enable_gcp and gcp_project_id fields with safe defaults | VERIFIED | `quirk/config.py` lines 69-71: `enable_gcp: bool = False`, `gcp_project_id: Optional[str] = None`; programmatic assertion passed |
| 3 | config_template.yaml contains GCP connector block under connectors section | VERIFIED | Lines 72-73 contain commented `enable_gcp: false` and `gcp_project_id: "my-gcp-project"` |
| 4 | gcs_scan_json column exists in CryptoEndpoint ORM model | VERIFIED | `quirk/models.py` line 74: `gcs_scan_json = Column(Text, nullable=True)` |
| 5 | _ensure_gcp_columns() idempotently adds gcs_scan_json to existing databases | VERIFIED | `quirk/db.py` lines 60-76: `_GCP_COLUMNS = ["gcs_scan_json"]`, `_ensure_gcp_columns()` uses inspector-first ALTER TABLE pattern; `init_db()` line 97 calls it after `_ensure_identity_columns()` |
| 6 | GCP test scaffold exists with failing tests for KMS, Cloud SQL, GCS, credentials error, and unavailable SDK | VERIFIED | `tests/test_cloud_connectors.py` contains all 10 required test functions: `test_gcp_unavailable`, `test_gcp_credentials_error_graceful`, `test_gcp_kms_algorithm_mapping`, `test_gcp_cloud_sql_plaintext_allowed`, `test_gcp_cloud_sql_encrypted_only`, `test_gcp_cloud_sql_mtls_no_finding`, `test_gcp_cloud_sql_null_ssl_mode`, `test_gcp_gcs_cmek_detection`, `test_gcp_gcs_scan_json_written`, `test_gcp_ensure_columns_idempotent` |

**Plan 02 Truths**

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 7 | GCP_AVAILABLE flag is False when google-api-python-client is not installed | VERIFIED | `gcp_connector.py` lines 23-32: optional import block sets `GCP_AVAILABLE = False` on ImportError; confirmed `GCP_AVAILABLE=False` in dev environment where SDK is not installed |
| 8 | scan_gcp_targets returns empty list when GCP_AVAILABLE is False | VERIFIED | `gcp_connector.py` lines 353-356: explicit guard returns `[]` when not GCP_AVAILABLE; tested by `test_gcp_unavailable` (PASS) |
| 9 | DefaultCredentialsError produces scan_error endpoint, not a crash | VERIFIED | `gcp_connector.py` lines 366-382: broad `except Exception` at `google.auth.default()` returns single CryptoEndpoint with `scan_error=f"gcp-credentials-unavailable: {exc}"`; tested by `test_gcp_credentials_error_graceful` (PASS) |
| 10 | Cloud KMS keys are mapped via GCP_KMS_ALGORITHM_MAP to algorithm/key_size tuples on CryptoEndpoint | VERIFIED | `gcp_connector.py` lines 38-96: 47-entry `GCP_KMS_ALGORITHM_MAP` present; `_scan_kms()` uses map at line 169; `test_gcp_kms_algorithm_mapping` asserts RSA 2048 extraction (PASS) |
| 11 | Cloud KMS auto-discovers all locations via projects.locations.list | VERIFIED | `gcp_connector.py` lines 131-215: nested pagination loop: locations → keyRings → cryptoKeys; `list_next()` called at all three levels |
| 12 | Cloud SQL sslMode ALLOW_UNENCRYPTED_AND_ENCRYPTED produces HIGH finding | VERIFIED | `gcp_connector.py` lines 241-263: `SSL_FINDING_MAP` entry, endpoint created with `cert_pubkey_alg="HIGH"`; `test_gcp_cloud_sql_plaintext_allowed` (PASS) |
| 13 | Cloud SQL sslMode ENCRYPTED_ONLY produces MEDIUM finding | VERIFIED | `SSL_FINDING_MAP` entry `("MEDIUM", ...)`; `test_gcp_cloud_sql_encrypted_only` (PASS) |
| 14 | Cloud SQL sslMode TRUSTED_CLIENT_CERTIFICATE_REQUIRED produces no finding | VERIFIED | `gcp_connector.py` line 245-246: explicit `continue` on mTLS mode; `test_gcp_cloud_sql_mtls_no_finding` (PASS) |
| 15 | Cloud SQL missing/null/SSL_MODE_UNSPECIFIED sslMode produces HIGH finding | VERIFIED | `gcp_connector.py` lines 241-242: normalizes None/empty/SSL_MODE_UNSPECIFIED to ALLOW_UNENCRYPTED; `test_gcp_cloud_sql_null_ssl_mode` (PASS) |
| 16 | GCS buckets with defaultKmsKeyName produce CMEK endpoint | VERIFIED | `gcp_connector.py` lines 314-316: `alg = "CMEK" if kms_key else "Google-Managed"`; `test_gcp_gcs_cmek_detection` (PASS) |
| 17 | GCS buckets without defaultKmsKeyName produce Google-Managed endpoint | VERIFIED | Same branch — `"Google-Managed"` when no kms_key; `test_gcp_gcs_cmek_detection` (PASS) |
| 18 | gcs_scan_json is written once on sentinel endpoint with full bucket list | VERIFIED | `gcp_connector.py` lines 300-307: sentinel with `cert_pubkey_alg="GCS-SUMMARY"` carries `gcs_scan_json=json.dumps(bucket_list)`; `test_gcp_gcs_scan_json_written` (PASS) |

**Plan 03 Truths**

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 19 | run_scan.py imports scan_gcp_targets from gcp_connector | VERIFIED | `run_scan.py` line 22: `from quirk.scanner.gcp_connector import scan_gcp_targets` |
| 20 | GCP scan phase runs behind cfg.connectors.enable_gcp guard | VERIFIED | `run_scan.py` lines 463-472: phase block with `_phase_timer(run_stats, "gcp_scanning")` and `if cfg.connectors.enable_gcp:` guard |

**Score:** 20/20 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `pyproject.toml` | [cloud] extras group with google-api-python-client and google-auth | VERIFIED | Lines 44-47; no grpcio |
| `quirk/config.py` | enable_gcp and gcp_project_id fields on ConnectorsCfg | VERIFIED | Lines 69-71 |
| `quirk/config_template.yaml` | GCP config block (commented out) | VERIFIED | Lines 72-73 |
| `quirk/models.py` | gcs_scan_json ORM column on CryptoEndpoint | VERIFIED | Line 74 |
| `quirk/db.py` | _GCP_COLUMNS list and _ensure_gcp_columns() migration function | VERIFIED | Lines 60-76; called from init_db() line 97 |
| `tests/test_cloud_connectors.py` | GCP test scaffold covering GCP-01, GCP-02, GCP-03 | VERIFIED | 10 test functions present; 15/15 PASS |
| `quirk/scanner/gcp_connector.py` | GCP connector module with KMS, Cloud SQL, GCS scanning (min 200 lines) | VERIFIED | 417 lines; exports GCP_AVAILABLE, GCP_KMS_ALGORITHM_MAP (47 entries), scan_gcp_targets |
| `run_scan.py` | GCP scan phase wiring with enable_gcp guard | VERIFIED | Import line 22, phase block lines 463-472, aggregation line 520 |
| `quirk/cbom/builder.py` | GCP and CLOUD_SQL protocol handling in Pass 1, Pass 2, and Pass 3 | VERIFIED | Pass 1 line 371, CLOUD_SQL branch line 388, Pass 2 skip list line 431-432, Pass 3 skip list line 511-512 |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `quirk/db.py` | `quirk/models.py` | `_ensure_gcp_columns` adds gcs_scan_json that models.py declares | WIRED | `_GCP_COLUMNS = ["gcs_scan_json"]` matches model column; both confirmed in source |
| `quirk/db.py init_db()` | `_ensure_gcp_columns()` | called after `_ensure_identity_columns()` | WIRED | `init_db()` line 97: `_ensure_gcp_columns(engine)` immediately after line 96 |
| `quirk/scanner/gcp_connector.py` | `quirk/models.py CryptoEndpoint` | import and construction | WIRED | Line 17: `from quirk.models import CryptoEndpoint`; used in `_scan_kms`, `_scan_cloud_sql`, `_scan_gcs`, `scan_gcp_targets` |
| `gcp_connector.py GCP_KMS_ALGORITHM_MAP` | `CryptoEndpoint.cert_pubkey_alg` | algorithm lookup sets cert_pubkey_alg and cert_pubkey_size | WIRED | Line 169-171: map lookup; lines 183-184: `cert_pubkey_alg=alg_name, cert_pubkey_size=key_size` |
| `gcp_connector.py _scan_gcs` | `CryptoEndpoint.gcs_scan_json` | `json.dumps(bucket_list)` on sentinel endpoint | WIRED | Lines 300-307: sentinel endpoint sets `gcs_scan_json=json.dumps(bucket_list, default=str)` |
| `run_scan.py` | `quirk/scanner/gcp_connector.py` | import scan_gcp_targets | WIRED | Line 22: `from quirk.scanner.gcp_connector import scan_gcp_targets` |
| `run_scan.py GCP scan phase` | `cfg.connectors.enable_gcp` | guard check before calling scan_gcp_targets | WIRED | Line 468: `if cfg.connectors.enable_gcp:` |
| `quirk/cbom/builder.py Pass 1` | `protocol GCP` | cloud branch tuple inclusion | WIRED | Line 371: `ep.protocol in ("AWS", "AZURE", "GCP")` |
| `quirk/cbom/builder.py _normalize_cloud_key_spec` | GCP algorithm strings | mapping dict entries for GCP | WIRED | Lines 76-104: 31 GCP entries including RSA_SIGN_PKCS1_2048_SHA256, ML_KEM_768, PQ_SIGN_ML_DSA_65 |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `gcp_connector.py _scan_gcs` | `bucket_list` | `service.buckets().list(project=project_id).execute()` | Yes — GCS API response items; `gcs_scan_json=json.dumps(bucket_list)` on sentinel | FLOWING |
| `gcp_connector.py _scan_kms` | `results` | `service.projects().locations()...cryptoKeys().list().execute()` | Yes — GCP KMS API responses; algorithm mapped from response `primary.algorithm` | FLOWING |
| `gcp_connector.py _scan_cloud_sql` | `results` | `service.instances().list(project=project_id).execute()` | Yes — sqladmin API response; sslMode extracted and mapped to finding severity | FLOWING |
| `run_scan.py gcp_endpoints` | `gcp_endpoints` | `scan_gcp_targets(project_id=...)` call | Yes — real connector result; included in `endpoints` aggregation at line 520 | FLOWING |
| `quirk/cbom/builder.py Pass 1 GCP` | `cloud_data["gcp_algorithm"]` | `json.loads(ep.cloud_scan_json)` | Yes — reads actual JSON written by `_scan_kms`; extracts `gcp_algorithm` key via `.get()` chain | FLOWING |

Note on GCS-SUMMARY sentinel: `cert_pubkey_alg="GCS-SUMMARY"` is intentionally excluded from CBOM algorithm registration via explicit guard at builder.py line 385: `ep.cert_pubkey_alg not in ("GCS-SUMMARY",)`. This is a correct design decision documented in Plan 03 SUMMARY.

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All 15 cloud connector tests pass | `pytest tests/test_cloud_connectors.py -v -q` | 15 passed, 0 failed, 0 skipped | PASS |
| All 30 CBOM builder tests pass | `pytest tests/test_cbom_builder.py -x -q` | 30 passed | PASS |
| All modified files compile clean | `python -m compileall gcp_connector.py config.py models.py db.py builder.py run_scan.py -q` | Exit 0 | PASS |
| GCP_KMS_ALGORITHM_MAP has >= 47 entries | `len(GCP_KMS_ALGORITHM_MAP) >= 47` | 47 entries exactly | PASS |
| _normalize_cloud_key_spec handles GCP algorithm strings | Programmatic assertions | RSA, ECDSA, AES-256-GCM, HMAC, ml-kem-768, ml-dsa-65 all correct | PASS |
| DB migration guard runs idempotently | `test_gcp_ensure_columns_idempotent` | PASS | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| GCP-01 | 26-01, 26-02, 26-03 | Scanner can enumerate Cloud KMS key specs with quantum-safety classification (RSA-2048/4096, ECDSA P-256/P-384, AES-256, HMAC-SHA256, external/HSM variants, PQC) for a configured GCP project | SATISFIED | `_scan_kms()` in gcp_connector.py enumerates all locations/key rings/keys; 47-entry `GCP_KMS_ALGORITHM_MAP` covers all stated types including PQC; CBOM builder processes via GCP branch; `test_gcp_kms_algorithm_mapping` verifies RSA-2048 extraction |
| GCP-02 | 26-01, 26-02, 26-03 | Scanner can detect Cloud SQL instance TLS enforcement mode and produce findings for disabled or plaintext-allowed TLS configurations | SATISFIED | `_scan_cloud_sql()` maps all sslMode values: ALLOW_UNENCRYPTED→HIGH, ENCRYPTED_ONLY→MEDIUM, TRUSTED_CLIENT_CERTIFICATE_REQUIRED→no finding, null/unspecified→HIGH; 4 test cases cover all branches; CBOM builder processes CLOUD_SQL protocol |
| GCP-03 | 26-01, 26-02, 26-03 | Scanner can detect GCS bucket default encryption type (CMEK with customer-managed key vs Google-managed key) across all buckets in a project | SATISFIED | `_scan_gcs()` checks `encryption.defaultKmsKeyName`; emits CMEK or Google-Managed per-bucket endpoints; sentinel endpoint carries `gcs_scan_json` for Phase 28 hand-off; `test_gcp_gcs_cmek_detection` and `test_gcp_gcs_scan_json_written` verify both behaviors |

All 3 phase requirements (GCP-01, GCP-02, GCP-03) are SATISFIED. No orphaned requirements found — REQUIREMENTS.md maps only GCP-01/02/03 to Phase 26 (Traceability table, line 99).

---

### Anti-Patterns Found

No blockers or warnings found.

| File | Check | Result |
|------|-------|--------|
| `quirk/scanner/gcp_connector.py` | TODO/FIXME/PLACEHOLDER | None |
| `quirk/scanner/gcp_connector.py` | `return null / return []` stub | `return []` at line 356 is a legitimate guard (GCP_AVAILABLE=False), not a stub — data path exists for the real case |
| `quirk/scanner/gcp_connector.py` | Hardcoded empty data | None — `gcs_scan_json` is written with real API data; no hardcoded empty returns in the live code path |
| `run_scan.py` | `gcp_endpoints = []` | Legitimate initialization — overwritten by scan call when `enable_gcp=True` |
| `quirk/cbom/builder.py` | GCS-SUMMARY in algorithm registration | Intentionally excluded via `not in ("GCS-SUMMARY",)` guard — correct design |

---

### Human Verification Required

None — all must-haves are programmatically verifiable and have been verified. The phase produces no UI components, no real-time behavior, and no external service integration requiring live credentials. The `GCP_AVAILABLE=False` state in the dev environment is expected (optional `[cloud]` extras not installed) and all connector logic is exercised via mocks in the test suite.

---

## Gaps Summary

No gaps. Phase 26 goal is fully achieved:

1. `quirk/scanner/gcp_connector.py` (417 lines) implements Cloud KMS enumeration with 47-entry algorithm map, Cloud SQL TLS enforcement detection for all sslMode values, and GCS bucket CMEK/Google-Managed classification with Phase 28 data hand-off via `gcs_scan_json`.
2. The connector is wired into `run_scan.py` behind the `enable_gcp` guard and aggregated into the endpoint list.
3. The CBOM builder processes GCP and CLOUD_SQL endpoints correctly in all three passes.
4. Infrastructure prerequisites (config fields, ORM column, DB migration, optional deps, test scaffold) are all in place.
5. All 15 cloud connector tests and all 30 CBOM builder tests pass. Full compilation clean.

---

_Verified: 2026-04-25T12:30:00Z_
_Verifier: Claude (gsd-verifier)_
