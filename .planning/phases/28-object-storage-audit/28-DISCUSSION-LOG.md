# Phase 28: Object Storage Audit - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-25
**Phase:** 28-object-storage-audit
**Areas discussed:** Module structure, Azure Blob SDK + scope, Chaos lab profile, dar_ storage scoring weights

---

## Module Structure

| Option | Description | Selected |
|--------|-------------|----------|
| Extend aws_connector.py | Add _scan_s3_encryption() alongside _scan_kms, _scan_rds_encryption; reuses boto3 session | ✓ |
| New storage_connector.py | Unified S3+Azure Blob in one file; splits boto3 logic across files | |

**User's choice:** Extend aws_connector.py for S3

| Option | Description | Selected |
|--------|-------------|----------|
| Extend azure_connector.py | Add _scan_blob_encryption() alongside existing functions; consistent pattern | ✓ |
| New storage_connector.py | Same new file as S3 option; only valid if S3 also in new file | |

**User's choice:** Extend azure_connector.py for Azure Blob

---

## Azure Blob SDK + Scope

| Option | Description | Selected |
|--------|-------------|----------|
| azure-mgmt-storage | Management plane; lists storage accounts, account-level encryption; consistent with azure-mgmt-network | ✓ |
| azure-storage-blob | Data plane; needs known storage account endpoints; more complex enumeration | |

**User's choice:** azure-mgmt-storage

| Option | Description | Selected |
|--------|-------------|----------|
| enable_blob: bool only | Single flag; uses existing subscription_id; zero new required config | ✓ |
| enable_blob + azure_storage_accounts: list | Explicit account list; more targeted but adds config burden | |

**User's choice:** enable_blob: bool only

| Option | Description | Selected |
|--------|-------------|----------|
| AZURE_BLOB protocol | Distinct from existing AZURE (Key Vault/App Gateway); filterable in Findings tab | ✓ |
| AZURE protocol | Same as existing Azure findings; harder to filter | |

**User's choice:** AZURE_BLOB

---

## Chaos Lab Profile

| Option | Description | Selected |
|--------|-------------|----------|
| Add MinIO profile | Open-source S3-compatible; supports bucket encryption API; validates HIGH finding + ThreadPoolExecutor | ✓ |
| Skip chaos lab | No profile; S3 tests use mocks only; consistent with Phase 26 (GCP had no lab) | |

**User's choice:** Add MinIO profile

| Option | Description | Selected |
|--------|-------------|----------|
| SSE-S3 + unencrypted buckets only | Two buckets; validates HIGH finding path and enumeration; no KMS sidecar needed | ✓ |
| SSE-S3 + SSE-KMS + unencrypted | Three buckets; requires KMS sidecar (Vault); significantly more lab complexity | |

**User's choice:** SSE-S3 encrypted + unencrypted buckets only

---

## dar_ Storage Scoring Weights

| Option | Description | Selected |
|--------|-------------|----------|
| dar_storage_unencrypted_ratio: 12.0 | Same as dar_db_plaintext_ratio; unencrypted S3 = same severity as DB plaintext | ✓ |
| dar_storage_unencrypted_ratio: 10.0 | Slightly lower; storage unencrypted less critical than DB plaintext | |

**User's choice:** 12.0 (same as DB plaintext)

| Option | Description | Selected |
|--------|-------------|----------|
| dar_storage_aws_managed_ratio: 4.0 | Lower than dar_db_weak_ssl_ratio (6.0); AWS-managed KMS is compliance gap, not active weakness | ✓ |
| dar_storage_aws_managed_ratio: 6.0 | Same as DB weak SSL; consistent across all MEDIUM DAR findings | |

**User's choice:** 4.0

---

## Claude's Discretion

- GCS read mechanism: run_scan.py queries CryptoEndpoint rows for cert_pubkey_alg="GCS-SUMMARY" to retrieve gcs_scan_json
- dar_ counter names: dar_storage_unencrypted_count, dar_storage_aws_managed_count
- CBOM integration: storage endpoints flow through existing Pass 1; -SUMMARY sentinel rows skipped per existing pattern
- S3 enable_s3: bool = False config field added for independent S3 control
- MinIO init pattern: mc client in entrypoint script to configure buckets

## Deferred Ideas

- SSE-KMS with CMK validation in MinIO lab — requires KMS sidecar (too complex for Phase 28)
- Dashboard Data at Rest tab — deferred from Phase 27, remains deferred to UI phase
