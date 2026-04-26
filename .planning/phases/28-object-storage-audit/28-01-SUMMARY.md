---
phase: 28
plan: 01
subsystem: object-storage-audit
tags: [scaffold, red-tests, s3, azure-blob, gcs, config, tdd]
dependency_graph:
  requires: [phase-27-database-encryption-detection]
  provides: [28-01-red-scaffold, ConnectorsCfg-object-storage-fields, azure-mgmt-storage-dep]
  affects: [quirk/config.py, pyproject.toml, tests/]
tech_stack:
  added: [azure-mgmt-storage>=21.0.0]
  patterns: [RED-then-GREEN TDD, ConnectorsCfg safe-default extension, pytest mock pattern]
key_files:
  modified:
    - pyproject.toml
    - quirk/config.py
    - quirk/config_template.yaml
  created:
    - tests/test_s3_encryption.py
    - tests/test_azure_blob.py
    - tests/test_gcs_reuse.py
    - tests/test_dar_storage_scoring.py
    - tests/test_chaos_storage.py
decisions:
  - "enable_s3, enable_blob, aws_endpoint_url added to ConnectorsCfg with safe defaults (False/None) per D-04 and T-28-02 mitigation"
  - "azure-mgmt-storage>=21.0.0 added to [cloud] extras per D-03/D-11"
  - "Test files import functions at call time (not module level) so ImportError fires per-test, enabling clear RED state reporting"
  - "test_chaos_storage.py uses pytestmark = pytest.mark.integration to gate all tests; live Docker tests additionally gated by QUIRK_RUN_DOCKER_IT env var"
metrics:
  duration: "~5 minutes"
  completed: "2026-04-25"
  tasks_completed: 3
  files_changed: 8
---

# Phase 28 Plan 01: Object Storage Audit RED Scaffold Summary

**One-liner:** RED scaffold establishing 36 failing tests for S3 severity ladder, Azure Blob keySource ladder, GCS zero-API-call invariant, dar_storage_* evidence counters, and MinIO chaos lab — with ConnectorsCfg extended for three new object storage config fields.

## What Was Built

### Task 1: pyproject.toml + ConnectorsCfg + config_template extensions

Three coordinated config edits establishing the Phase 28 foundation:

**pyproject.toml** — Added `azure-mgmt-storage>=21.0.0` to `[cloud]` extras (the only new dependency for Phase 28). Comment attributes the addition to Phase 28 and STOR-02.

**quirk/config.py** — Extended `ConnectorsCfg` dataclass with three new fields immediately after the Phase 27 DB connector block:
- `enable_s3: bool = False` — gates S3 scanning independently from `enable_aws`
- `enable_blob: bool = False` — gates Azure Blob scanning
- `aws_endpoint_url: Optional[str] = None` — MinIO/LocalStack S3 endpoint override for chaos lab

All fields default to safe values so existing `config.yaml` files load without `TypeError`. `_KNOWN_CONNECTOR_KEYS` auto-discovers them via `dataclasses.fields(ConnectorsCfg)` without any manual update needed.

**quirk/config_template.yaml** — Added three commented entries in the connectors block after the DB connector section:
```yaml
# -- Object storage connectors (optional, requires: pip install quirk[cloud]) --
# enable_s3: false
# aws_endpoint_url: null            # override for MinIO/LocalStack testing
# enable_blob: false
```

**Commit:** `f1b0bd3`

### Task 2: RED scaffold — test_s3_encryption.py + test_azure_blob.py + test_gcs_reuse.py

Three test files covering the STOR-01, STOR-02, and STOR-03 requirements:

**tests/test_s3_encryption.py** (10 tests) — Pins the complete S3 severity ladder:
- `test_s3_unavailable_returns_empty` — BOTO3_AVAILABLE=False guard
- `test_s3_no_encryption_config_error` — ServerSideEncryptionConfigurationNotFoundError → HIGH/"S3/unencrypted"
- `test_s3_sse_s3_no_finding` — AES256 → "S3/sse-s3", severity=None
- `test_s3_sse_kms_aws_managed` — aws:kms + alias/aws/s3 → MEDIUM/"S3/sse-kms-aws"
- `test_s3_sse_kms_aws_managed_absent_keyid` — aws:kms without KMSMasterKeyID → MEDIUM
- `test_s3_sse_kms_cmk_no_finding` — aws:kms + ARN key → "S3/sse-kms-cmk", severity=None
- `test_s3_parallel_scan_processes_all_buckets` — 3 buckets → 3 calls to get_bucket_encryption
- `test_s3_session_start_propagates` — session_start datetime used for scanned_at
- `test_s3_dat_scan_json_populated` — dat_scan_json contains bucket name as JSON
- `test_s3_endpoint_url_passed_to_client` — endpoint_url forwarded to session.client()

**tests/test_azure_blob.py** (7 tests) — Pins the Azure Blob keySource ladder:
- `test_azure_blob_unavailable_returns_empty` — AZURE_AVAILABLE=False guard
- `test_azure_blob_platform_managed_medium` — Microsoft.Storage → MEDIUM/"BLOB/platform-managed"
- `test_azure_blob_cmk_no_finding` — Microsoft.Keyvault → "BLOB/cmk", severity=None
- `test_azure_blob_absent_key_source_medium` — encryption=None → MEDIUM (safe default)
- `test_azure_blob_per_container_endpoint` — 3 containers → 3 CryptoEndpoint rows
- `test_azure_blob_session_start_propagates` — session_start datetime used for scanned_at
- `test_azure_blob_protocol_value` — all endpoints have protocol="AZURE_BLOB"

**tests/test_gcs_reuse.py** (5 tests) — Pins the STOR-03 zero-API-call invariant:
- `test_gcs_reuse_returns_empty_when_no_sentinel` — no GCS-SUMMARY sentinel → returns []
- `test_gcs_reuse_returns_empty_when_gcp_disabled` — empty list → no raise
- `test_gcs_reuse_reads_sentinel_no_api_call` — googleapiclient.discovery.build call count == 0
- `test_gcs_reuse_handles_malformed_json` — invalid JSON → returns []
- `test_gcs_reuse_zero_storage_buckets_list_call` — google.cloud.storage.Client not called

All 22 tests fail with `ImportError` because `_scan_s3_encryption`, `_scan_blob_encryption`, and `_process_gcs_storage_encryption` don't exist yet. This is the intended RED state.

**Commit:** `9391d09`

### Task 3: RED scaffold — test_dar_storage_scoring.py + test_chaos_storage.py

Two test files covering the evidence/scoring infrastructure and MinIO chaos lab:

**tests/test_dar_storage_scoring.py** (9 tests) — Pins the D-09/D-10 counters and weights:
- `test_protocol_keys_includes_storage_protocols` — _PROTOCOL_KEYS has "S3" and "AZURE_BLOB"
- `test_dar_storage_unencrypted_count_s3` — S3/unencrypted increments unencrypted_count
- `test_dar_storage_aws_managed_count_s3` — S3/sse-kms-aws increments aws_managed_count
- `test_dar_storage_blob_platform_managed_counts` — BLOB/platform-managed increments aws_managed_count (not unencrypted)
- `test_dar_storage_no_finding_paths_no_increment` — sse-s3, sse-kms-cmk, BLOB/cmk produce zero increments
- `test_dar_storage_ratio_keys_present` — dar_storage_unencrypted_ratio and aws_managed_ratio in evidence dict
- `test_score_weights_dar_storage_values` — SCORE_WEIGHTS["dar_storage_unencrypted_ratio"] == 12.0, ["dar_storage_aws_managed_ratio"] == 4.0
- `test_dar_score_includes_storage_drivers` — scoring produces storage-related driver labels
- `test_dar_storage_unencrypted_ratio_applied` — high unencrypted ratio produces lower dar subscore

**tests/test_chaos_storage.py** (5 tests) — MinIO chaos lab contract:
- `test_minio_seed_script_exists` — minio-seed.sh present in quantum-chaos-enterprise-lab/storage/
- `test_minio_seed_creates_two_buckets` — seed script creates encrypted-bucket and unencrypted-bucket with SSE-S3
- `test_minio_compose_profile_storage_s3` — docker-compose.yml declares storage-s3 profile with minio + minio-seed
- `test_minio_unencrypted_bucket_produces_high_finding` — live Docker test (gated: QUIRK_RUN_DOCKER_IT=1)
- `test_minio_encrypted_bucket_no_finding` — live Docker test (gated: QUIRK_RUN_DOCKER_IT=1)

All 14 tests fail at this stage — scoring counters/weights absent (RED); chaos lab files not yet created (Plans 02/03).

**Commit:** `d217277`

## Deviations from Plan

None — plan executed exactly as written.

## RED State Summary

All 36 tests fail as expected. This is the success state for Plan 01:

| File | Tests | Failure Mode |
|------|-------|-------------|
| tests/test_s3_encryption.py | 10 | ImportError: cannot import `_scan_s3_encryption` |
| tests/test_azure_blob.py | 7 | ImportError: cannot import `_scan_blob_encryption` |
| tests/test_gcs_reuse.py | 5 | ImportError: cannot import `_process_gcs_storage_encryption` from run_scan |
| tests/test_dar_storage_scoring.py | 9 | AssertionError: "S3" not in _PROTOCOL_KEYS (counters/weights absent) |
| tests/test_chaos_storage.py | 5 | AssertionError: minio-seed.sh does not exist yet |

Plan 02 turns tests/test_s3_encryption.py, tests/test_azure_blob.py, tests/test_gcs_reuse.py, and tests/test_dar_storage_scoring.py GREEN by implementing the scanner functions and evidence/scoring extensions. Plan 03 (chaos lab) turns tests/test_chaos_storage.py GREEN.

## Known Stubs

None. This plan adds only configuration extensions and RED test contracts. No production code with stub patterns.

## Threat Flags

None. Changes are additive config fields and test files only. The `aws_endpoint_url` field is covered by T-28-04 in the plan's threat model (accepted — local dev only).

## Self-Check: PASSED
