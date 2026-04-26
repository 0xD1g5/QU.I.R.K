---
status: partial
phase: 28-object-storage-audit
source: [28-VERIFICATION.md]
started: 2026-04-26T00:54:10Z
updated: 2026-04-26T00:54:10Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. UAT-28-01 — MinIO chaos lab end-to-end S3 scan
expected: Boot `docker compose --profile storage-s3 up -d`, run quirk with `enable_s3: true` and `aws_endpoint_url: http://localhost:29000`. Exactly 2 `protocol=S3` rows: `arn:aws:s3:::encrypted-bucket` → `S3/sse-s3` (no severity), `arn:aws:s3:::unencrypted-bucket` → `S3/unencrypted` (severity=HIGH). No `OperationNotPageableError` in logs. `dar_storage_unencrypted_count == 1` in evidence. `drivers` list includes "Object storage unencrypted".
result: [pending]

### 2. UAT-28-02 — Azure Blob live subscription scan
expected: Run quirk with `enable_blob: true` and a real `azure_subscription_id`. One `protocol=AZURE_BLOB` CryptoEndpoint per blob container. Platform-managed accounts → `BLOB/platform-managed` (severity=MEDIUM). CMK accounts → `BLOB/cmk` (no severity). No exception traceback in logs.
result: [pending]

### 3. UAT-28-03 — GCS reuse zero-API-call confirmation
expected: Run quirk with `enable_gcp: true`. Both `gcs_scanning` and `gcs_storage_reuse` phase blocks appear in `--verbose` timing output. Total `storage.buckets.list` calls = 1 (Phase 26 only, not 2). Per-bucket GCS rows from Phase 26 still present in DB.
result: [pending]

## Summary

total: 3
passed: 0
issues: 0
pending: 3
skipped: 0
blocked: 0

## Gaps
