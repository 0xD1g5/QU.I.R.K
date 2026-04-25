# Phase 28: Object Storage Audit - Context

**Gathered:** 2026-04-25
**Status:** Ready for planning

<domain>
## Phase Boundary

QU.I.R.K. can determine per-bucket/container encryption policy for S3, Azure Blob, and GCS —
consuming Phase 26's `gcs_scan_json` column for GCS rather than re-fetching, with parallel
S3 probing via ThreadPoolExecutor. All object storage findings are stored as
`protocol="STORAGE"` CryptoEndpoint rows and flow into the existing CBOM pipeline.

Phase 28 extends existing cloud connector modules (aws_connector.py, azure_connector.py) rather
than creating a new storage module. No dashboard UI changes — findings appear in the existing
Findings tab. The `dat_scan_json` column and `dar_` scoring infrastructure are already installed
from Phase 27.

</domain>

<decisions>
## Implementation Decisions

### Module Structure
- **D-01:** S3 scanning extends `quirk/scanner/aws_connector.py` — add `_scan_s3_encryption(session, logger)` alongside existing `_scan_kms`, `_scan_rds_encryption`. Reuses the existing boto3 session. Call from `scan_aws_targets()`.
- **D-02:** Azure Blob scanning extends `quirk/scanner/azure_connector.py` — add `_scan_blob_encryption(credential, subscription_id, logger)` alongside existing `_scan_keyvault_keys`, `_scan_app_gateways`. Call from `scan_azure_targets()`.
- GCS bucket encryption reuses Phase 26 `gcs_scan_json` data. The sentinel CryptoEndpoint written by Phase 26 carries the full bucket list as JSON in the `gcs_scan_json` column. Phase 28 reads this from the current scan's DB row and processes it — zero new `storage.buckets.list` API calls.

### Azure Blob SDK
- **D-03:** Use `azure-mgmt-storage` (management plane) to enumerate storage accounts in the configured subscription and read account-level encryption settings. Consistent with existing `azure-mgmt-network` usage. Add `azure-mgmt-storage>=21.0.0` to `[cloud]` extras in `pyproject.toml`.
- **D-04:** Add `enable_blob: bool = False` to `ConnectorsCfg` in `config.py`. No additional config fields — uses the existing `azure_subscription_id` field already in `ConnectorsCfg`. Matching entry in `config_template.yaml`.
- **D-05:** Azure Blob findings use `protocol="AZURE_BLOB"` on CryptoEndpoint rows (distinct from existing `protocol="AZURE"` used for Key Vault/App Gateway). Makes storage findings filterable in the Findings tab.
- **Implementation note:** Azure encryption is at the storage account level, not per-container. "Per-container" in STOR-02 means: enumerate all containers in each storage account, create one CryptoEndpoint per container, and apply the parent account's encryption setting (CMK vs platform-managed key) to each row.

### S3 Encryption API
- **D-06:** Use `client.get_bucket_encryption(Bucket=name)` per bucket (not a paginator — `list_buckets` is not paginated). Use `ThreadPoolExecutor(max_workers=10)` to parallelize per-bucket encryption calls. Severity ladder per ROADMAP success criteria:
  - `ServerSideEncryptionRule` absent or `SSEAlgorithm="none"` → HIGH finding, `service_detail="S3/unencrypted"`
  - `SSEAlgorithm="AES256"` (SSE-S3) → no finding, `service_detail="S3/sse-s3"`
  - `SSEAlgorithm="aws:kms"` with `KMSMasterKeyID` matching `alias/aws/s3` or absent → MEDIUM, `service_detail="S3/sse-kms-aws"`
  - `SSEAlgorithm="aws:kms"` with customer `KMSMasterKeyID` → no finding, `service_detail="S3/sse-kms-cmk"`
  Protocol field: `"S3"`. Store per-bucket JSON in `dat_scan_json`.

### Azure Blob Finding Logic
- **D-07:** `encryption.keySource` from storage account:
  - `"Microsoft.Storage"` (platform-managed) → MEDIUM finding, `service_detail="BLOB/platform-managed"`
  - `"Microsoft.Keyvault"` (CMK) → no finding, `service_detail="BLOB/cmk"`
  - absent/null → MEDIUM finding (safe default — treat as platform-managed)
  Protocol field: `"AZURE_BLOB"`. Store per-container JSON in `dat_scan_json`.

### Chaos Lab Profile
- **D-08:** Add a `storage` Docker Compose profile using MinIO (`minio/minio:latest`). Two buckets pre-configured on container start:
  - `encrypted-bucket` — SSE-S3 enabled (validates no-finding path and ThreadPoolExecutor enumeration)
  - `unencrypted-bucket` — no encryption policy (validates HIGH finding path)
  No KMS sidecar needed — SSE-KMS validation deferred (requires external KMS endpoint, out of scope for MinIO lab).
  MinIO endpoint configured via `aws_endpoint_url` config field (or equivalent) so scanner targets localhost instead of AWS. Expected results documented in `labs/storage/expected_results.md`.

### dar_ Evidence Counters and Scoring Weights
- **D-09:** Add to `evidence.py` alongside existing `dar_db_*` counters:
  - `dar_storage_unencrypted_count` — count of S3 buckets + Azure Blob containers with no encryption (HIGH)
  - `dar_storage_aws_managed_count` — count of S3 SSE-KMS with AWS-managed key + Azure Blob platform-managed key (MEDIUM)
  GCS CMEK findings do not add new counters — GCS bucket findings are handled by the existing GCS endpoint rows from Phase 26.
- **D-10:** Add to `scoring.py` `IMPACT_WEIGHTS` dict alongside existing `dar_db_*` weights:
  - `"dar_storage_unencrypted_ratio": 12.0` — same weight as `dar_db_plaintext_ratio` (both HIGH)
  - `"dar_storage_aws_managed_ratio": 4.0` — lower than `dar_db_weak_ssl_ratio` (6.0); AWS-managed KMS is compliance gap, not active security weakness

### ISSUE-2/ISSUE-3 Structural Requirements
- **D-11:** `pyproject.toml` diff is a required deliverable: add `azure-mgmt-storage>=21.0.0` to `[cloud]` extras. Follow the ISSUE-2 pattern — pyproject.toml diff must be explicitly shown in the plan.
- **D-12:** `session_start` parameter is mandatory for all new scanner invocations in `run_scan.py` (ISSUE-3 pattern). S3 and Azure Blob scan functions must accept and use `session_start` rather than calling `datetime.now()` internally.

### Claude's Discretion
- GCS read mechanism: `run_scan.py` queries the current scan's CryptoEndpoint rows for `cert_pubkey_alg="GCS-SUMMARY"` to retrieve `gcs_scan_json`; passes the parsed bucket list JSON to the GCS encryption processor. No new API calls.
- CBOM integration: S3, Azure Blob, and GCS (Phase 26 already handled) CryptoEndpoint rows flow through existing CBOM Pass 1 (key type → CryptoComponent). Sentinel/summary rows (cert_pubkey_alg ending in `-SUMMARY`) are skipped in Pass 1 per existing skip-list pattern.
- `dat_scan_json` usage: per-bucket JSON stored in `dat_scan_json` on individual CryptoEndpoint rows. S3 sentinel row (if needed) uses same pattern as GCS sentinel in gcs_scan_json.
- S3 `enable_s3: bool = False` config field added to `ConnectorsCfg` to allow S3 scanning independent of other AWS resources.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Reference Implementations
- `quirk/scanner/aws_connector.py` — `scan_aws_targets()` signature, `_scan_rds_encryption()` pattern, boto3 session reuse, `BOTO3_AVAILABLE` flag
- `quirk/scanner/azure_connector.py` — `scan_azure_targets()` signature, `DefaultAzureCredential` pattern, `AZURE_AVAILABLE` flag, `cloud_scan_json` usage
- `quirk/scanner/gcp_connector.py` — `gcs_scan_json` sentinel endpoint structure, `bucket.get("encryption", {})` field access, `cert_pubkey_alg="GCS-SUMMARY"` sentinel pattern

### Schema and ORM
- `quirk/db.py` — `_V43_COLUMNS`, `_ensure_v43_columns()` (dat_scan_json), `gcs_scan_json` column; do NOT add new columns for Phase 28
- `quirk/models.py` — `CryptoEndpoint` ORM model with `dat_scan_json` and `gcs_scan_json` fields

### Config Extension
- `quirk/config.py` — `ConnectorsCfg` dataclass; add `enable_blob: bool = False` and `enable_s3: bool = False`
- `quirk/config_template.yaml` — `connectors:` section; add matching `enable_blob: false`, `enable_s3: false`

### Scoring Architecture (Phase 27 baseline)
- `quirk/intelligence/evidence.py` — `dar_db_plaintext_count` / `dar_db_weak_ssl_count` pattern; add `dar_storage_unencrypted_count` / `dar_storage_aws_managed_count` alongside
- `quirk/intelligence/scoring.py` — `IMPACT_WEIGHTS` dict, `dar_db_plaintext_ratio: 12.0` / `dar_db_weak_ssl_ratio: 6.0`; add `dar_storage_unencrypted_ratio: 12.0` / `dar_storage_aws_managed_ratio: 4.0`

### Dependency Structure
- `pyproject.toml` — `[cloud]` extras group; add `azure-mgmt-storage>=21.0.0`

### Phase Context (dependencies)
- `.planning/phases/26-gcp-connector/26-CONTEXT.md` — D-03 (gcs_scan_json sentinel), D-02 (google-api-python-client in [cloud])
- `.planning/phases/27-database-encryption-detection/27-CONTEXT.md` — D-07 (_V43_COLUMNS/_ensure_v43_columns), D-08 (dar_ subscore architecture)

### Requirements
- `.planning/REQUIREMENTS.md` — STOR-01, STOR-02, STOR-03

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `aws_connector.py:_scan_rds_encryption()` — exact pattern for `_scan_s3_encryption()`: boto3 client, paginate/iterate, CryptoEndpoint construction with severity
- `aws_connector.py:scan_aws_targets()` — add `results.extend(_scan_s3_encryption(session, logger))` at the end
- `azure_connector.py:_scan_keyvault_keys()` — DefaultAzureCredential usage, cloud_scan_json storage pattern
- `gcp_connector.py:_scan_gcs()` — sentinel endpoint pattern with `cert_pubkey_alg="GCS-SUMMARY"`, `gcs_scan_json=json.dumps(bucket_list)`

### Established Patterns
- S3 `list_buckets` is NOT paginated — raises `OperationNotPageableError`; use direct call then ThreadPoolExecutor for per-bucket work
- `dat_scan_json` column exists from Phase 27 — no ALTER TABLE needed
- `dar_` subscore prefix with `_ratio` weights in `IMPACT_WEIGHTS` dict in scoring.py
- Optional import pattern: `BOTO3_AVAILABLE`, `AZURE_AVAILABLE`, `GCP_AVAILABLE` flags with module-level `None` assignments for test patching

### Integration Points
- `scan_aws_targets()` in aws_connector.py — add `_scan_s3_encryption` call at the end
- `scan_azure_targets()` in azure_connector.py — add `_scan_blob_encryption` call at the end
- `run_scan.py` — DB query to retrieve gcs_scan_json sentinel before calling GCS processor; session_start pass-through for all new scanner invocations
- `quirk/intelligence/evidence.py` — `_collect_evidence()` function where dar_db counters are extracted; add storage counters in same block
- `quirk/cbom/builder.py` — Pass 1 skip-list check for `-SUMMARY` cert_pubkey_alg values (already handled for GCS)

</code_context>

<specifics>
## Specific Ideas

- MinIO chaos lab: use `mc` (MinIO client) in an init container or entrypoint script to create and configure buckets on startup — same pattern as the database profile's init SQL scripts
- S3 `get_bucket_encryption` raises `ClientError` with code `ServerSideEncryptionConfigurationNotFoundError` for unencrypted buckets — must catch this as the "unencrypted" detection path (not a scan error)
- Azure Blob MEDIUM finding (`BLOB/platform-managed`) represents a compliance gap: data is encrypted but with Microsoft-managed keys, not customer-controlled. Remediation: enable Customer-Managed Keys (CMK) via Azure Key Vault.

</specifics>

<deferred>
## Deferred Ideas

- SSE-KMS with customer CMK validation in MinIO chaos lab — requires a KMS sidecar (Vault or similar); too complex for Phase 28
- Dashboard Data at Rest tab — deferred from Phase 27 (DAR-05 in memory index); remains deferred until UI work phase

</deferred>

---

*Phase: 28-object-storage-audit*
*Context gathered: 2026-04-25*
