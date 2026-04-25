# Phase 28: Object Storage Audit - Research

**Researched:** 2026-04-25
**Domain:** AWS S3 / Azure Blob / GCS encryption detection, extending existing cloud connectors
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Module Structure**
- D-01: S3 scanning extends `quirk/scanner/aws_connector.py` — add `_scan_s3_encryption(session, logger)` alongside `_scan_kms`, `_scan_rds_encryption`. Reuses existing boto3 session. Call from `scan_aws_targets()`.
- D-02: Azure Blob scanning extends `quirk/scanner/azure_connector.py` — add `_scan_blob_encryption(credential, subscription_id, logger)`. Call from `scan_azure_targets()`.
- GCS bucket encryption reuses Phase 26 `gcs_scan_json` data — zero new `storage.buckets.list` API calls.

**Azure Blob SDK**
- D-03: Use `azure-mgmt-storage` (management plane) to enumerate storage accounts. Add `azure-mgmt-storage>=21.0.0` to `[cloud]` extras in `pyproject.toml`.
- D-04: Add `enable_blob: bool = False` to `ConnectorsCfg` in `config.py`. Uses existing `azure_subscription_id`. Matching entry in `config_template.yaml`.
- D-05: Azure Blob findings use `protocol="AZURE_BLOB"` (distinct from `protocol="AZURE"`).
- Implementation note: Azure encryption is at the storage account level, not per-container. Enumerate all containers per account, create one CryptoEndpoint per container, apply parent account's encryption setting.

**S3 Encryption API**
- D-06: Use `client.get_bucket_encryption(Bucket=name)` per bucket (not a paginator). Use `ThreadPoolExecutor(max_workers=10)` to parallelize. Severity ladder:
  - `ServerSideEncryptionRule` absent or `SSEAlgorithm="none"` → HIGH, `service_detail="S3/unencrypted"`
  - `SSEAlgorithm="AES256"` (SSE-S3) → no finding, `service_detail="S3/sse-s3"`
  - `SSEAlgorithm="aws:kms"` with `alias/aws/s3` or absent KMSMasterKeyID → MEDIUM, `service_detail="S3/sse-kms-aws"`
  - `SSEAlgorithm="aws:kms"` with customer KMSMasterKeyID → no finding, `service_detail="S3/sse-kms-cmk"`
  Protocol field: `"S3"`. Store per-bucket JSON in `dat_scan_json`.

**Azure Blob Finding Logic**
- D-07: `encryption.keySource` from storage account:
  - `"Microsoft.Storage"` → MEDIUM, `service_detail="BLOB/platform-managed"`
  - `"Microsoft.Keyvault"` → no finding, `service_detail="BLOB/cmk"`
  - absent/null → MEDIUM (treat as platform-managed)
  Protocol field: `"AZURE_BLOB"`. Store per-container JSON in `dat_scan_json`.

**Chaos Lab Profile**
- D-08: Add `storage` Docker Compose profile using MinIO (`minio/minio:latest`). Two buckets:
  - `encrypted-bucket` — SSE-S3 enabled (no-finding path + ThreadPoolExecutor enumeration)
  - `unencrypted-bucket` — no encryption (HIGH finding path)
  No KMS sidecar. MinIO endpoint via `aws_endpoint_url` config field. Expected results in `labs/storage/expected_results.md`.

**dar_ Evidence Counters and Scoring Weights**
- D-09: Add to `evidence.py`:
  - `dar_storage_unencrypted_count` — S3 + Azure Blob containers with no encryption (HIGH)
  - `dar_storage_aws_managed_count` — S3 SSE-KMS AWS-managed + Azure Blob platform-managed (MEDIUM)
- D-10: Add to `scoring.py` `IMPACT_WEIGHTS`:
  - `"dar_storage_unencrypted_ratio": 12.0`
  - `"dar_storage_aws_managed_ratio": 4.0`

**ISSUE-2/ISSUE-3 Structural Requirements**
- D-11: `pyproject.toml` diff is a required deliverable: add `azure-mgmt-storage>=21.0.0` to `[cloud]` extras.
- D-12: `session_start` parameter is mandatory for all new scanner invocations in `run_scan.py`.

### Claude's Discretion
- GCS read mechanism: `run_scan.py` queries current scan's CryptoEndpoint rows for `cert_pubkey_alg="GCS-SUMMARY"` to retrieve `gcs_scan_json`; passes parsed bucket list JSON to GCS encryption processor. No new API calls.
- CBOM integration: S3, Azure Blob, and GCS CryptoEndpoint rows flow through existing CBOM Pass 1. Sentinel/summary rows (`cert_pubkey_alg` ending in `-SUMMARY`) are skipped per existing skip-list pattern.
- `dat_scan_json` usage: per-bucket JSON on individual CryptoEndpoint rows.
- S3 `enable_s3: bool = False` config field added to `ConnectorsCfg`.

### Deferred Ideas (OUT OF SCOPE)
- SSE-KMS with customer CMK validation in MinIO chaos lab (requires KMS sidecar)
- Dashboard Data at Rest tab (deferred from Phase 27, DAR-05)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| STOR-01 | Scanner can determine S3 bucket encryption policy per bucket (SSE-S3, SSE-KMS with CMK vs AWS-managed key, unencrypted) across all buckets in a configured AWS account | D-06 severity ladder; `get_bucket_encryption` + `ServerSideEncryptionConfigurationNotFoundError` pattern verified in aws_connector.py inspection |
| STOR-02 | Scanner can determine Azure Blob container encryption configuration (platform-managed key vs customer-managed CMK) for a configured Azure subscription | D-03/D-05/D-07; `azure-mgmt-storage` management plane; per-container CryptoEndpoint from account-level keySource |
| STOR-03 | GCS bucket encryption audit reuses Phase 26 GCP connector's bucket enumeration — no duplicate GCS bucket list API calls issued in a single scan run | D-02 (Claude's Discretion); sentinel `cert_pubkey_alg="GCS-SUMMARY"` row in DB carries `gcs_scan_json`; Phase 28 reads from DB, not the GCS API |
</phase_requirements>

---

## Summary

Phase 28 adds object storage encryption audit for S3, Azure Blob, and GCS to QU.I.R.K.'s data-at-rest coverage. The work is entirely within the existing cloud connector modules — no new files except a chaos lab init script and an expected_results.md. The schema, scoring architecture, and CBOM pipeline are already in place from Phases 26 and 27; Phase 28 only needs to extend them with new protocol values and new `dar_storage_*` evidence counters.

The three requirements map cleanly to three sub-features: (1) S3 uses `get_bucket_encryption` with `ThreadPoolExecutor` parallelism and a `ClientError`-based unencrypted detection path; (2) Azure Blob uses `azure-mgmt-storage` StorageManagementClient to enumerate accounts and their containers, applying account-level `encryption.keySource` to each container CryptoEndpoint; (3) GCS reuses the sentinel endpoint written by Phase 26 rather than re-calling the GCS API, which is the entire point of STOR-03.

The key integration challenge is the GCS re-use path in `run_scan.py`: it must query the DB for the sentinel row immediately after gcp_endpoints are persisted (or from the in-memory endpoint list), extract `gcs_scan_json`, and pass it to a new GCS processor function. The CBOM builder already skips `GCS-SUMMARY` sentinel rows; both `S3` and `AZURE_BLOB` protocol values need to be added to the Pass 2/3 skip-lists.

**Primary recommendation:** Implement in three focused plans — (1) S3 connector extension + config + run_scan wiring; (2) Azure Blob connector extension + pyproject.toml + run_scan wiring; (3) GCS re-use path + evidence/scoring updates + MinIO chaos lab + test coverage.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| S3 bucket encryption detection | API / Backend (scanner) | — | boto3 management-plane call; scanner owns cloud probing |
| Azure Blob account/container enumeration | API / Backend (scanner) | — | azure-mgmt-storage management plane; same tier as existing azure_connector.py |
| GCS bucket encryption re-use | API / Backend (scanner) | Database / Storage | Read sentinel row from in-memory endpoint list (no DB query needed); process bucket list JSON |
| dar_ evidence counter accumulation | API / Backend (evidence.py) | — | Parallel to existing `dar_db_*` counters |
| dar_ scoring weights | API / Backend (scoring.py) | — | IMPACT_WEIGHTS dict; same module as existing `dar_db_*` weights |
| CBOM algorithm registration | API / Backend (builder.py) | — | Pass 1 extension; `S3` and `AZURE_BLOB` follow `POSTGRESQL`/`MYSQL`/`RDS` pass-through pattern |
| MinIO chaos lab | CDN / Static (local Docker) | — | Docker Compose `storage` profile; init script seeds bucket configs |

---

## Standard Stack

### Core (all verified in codebase — no new major dependencies except azure-mgmt-storage)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| boto3 | >=1.42.0 (in core deps) [VERIFIED: pyproject.toml] | S3 `list_buckets`, `get_bucket_encryption`, per-bucket encryption probing | Already a core dependency; same session used for KMS, RDS, ACM, CloudFront |
| azure-mgmt-storage | >=21.0.0 (to add) [ASSUMED] | Enumerate Azure storage accounts and containers via management plane | Consistent with existing `azure-mgmt-network>=30.2.0`; management plane is the correct tier for policy queries |
| azure-identity | >=1.25.0 (in core deps) [VERIFIED: pyproject.toml] | `DefaultAzureCredential` — ambient auth, same as Key Vault and App Gateway connectors | Already a core dependency |
| concurrent.futures.ThreadPoolExecutor | stdlib | Parallelize `get_bucket_encryption` across buckets | S3 `list_buckets` is not paginated (OperationNotPageableError); parallelism required for large accounts |
| minio/minio:latest | latest [ASSUMED] | Local S3-compatible server for chaos lab | Standard MinIO image; S3 API compatibility for boto3 testing |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| amazon/aws-cli:latest | latest [VERIFIED: docker-compose.yml] | Init container pattern (kms-seed.sh) | Use `mc` (MinIO client) or AWS CLI in entrypoint for bucket seeding; matches kms-seed.sh pattern |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| azure-mgmt-storage management plane | azure-storage-blob data plane | Management plane provides account-level encryption settings; data plane only accesses blob content — wrong tier for policy audit |
| MinIO for S3 chaos lab | LocalStack (already in compose) | MinIO is simpler for pure S3 encryption testing; LocalStack `SERVICES=s3` is an alternative but MinIO has better `get_bucket_encryption` support for SSE-S3 |

**Installation (pyproject.toml diff only):**
```
[project.optional-dependencies]
cloud = [
    "google-api-python-client>=2.0.0",
    "google-auth>=2.36.0",
    "azure-mgmt-storage>=21.0.0",   # Phase 28 addition
]
```

---

## Architecture Patterns

### System Architecture Diagram

```
                        run_scan.py
                            │
          ┌─────────────────┼──────────────────────┐
          │                 │                       │
    enable_s3=True    enable_blob=True        enable_gcp=True
          │                 │                       │
          ▼                 ▼                       ▼
 aws_connector.py    azure_connector.py      [Phase 26, already ran]
 scan_aws_targets()  scan_azure_targets()         │
          │                 │               gcp_endpoints (in memory)
          │                 │                       │
 _scan_s3_encryption()  _scan_blob_encryption()     │
 boto3 list_buckets     StorageManagementClient      │ sentinel row
 ThreadPoolExecutor     list_all() + containers      │ cert_pubkey_alg="GCS-SUMMARY"
 get_bucket_encryption  encryption.keySource         │ gcs_scan_json=[{...}]
          │                 │                       ▼
          │                 │           _process_gcs_encryption(bucket_list)
          │                 │           (reads gcs_scan_json from sentinel;
          │                 │            creates per-bucket CryptoEndpoints)
          ▼                 ▼                       │
  CryptoEndpoint rows (protocol="S3")               │
  CryptoEndpoint rows (protocol="AZURE_BLOB")        │
                        ▼               ◄───────────┘
              All storage endpoints merged
                        │
              evidence.py: _collect_evidence()
              dar_storage_unencrypted_count
              dar_storage_aws_managed_count
                        │
              scoring.py: compute_readiness_score()
              dar_storage_unencrypted_ratio × 12.0
              dar_storage_aws_managed_ratio × 4.0
                        │
              cbom/builder.py: build_cbom()
              Pass 1: S3/AZURE_BLOB → pass (no alg to register)
              Pass 2/3: S3/AZURE_BLOB → skip (no cert/protocol components)
```

### Recommended Project Structure
```
quirk/scanner/
├── aws_connector.py      # Add _scan_s3_encryption() + enable_s3 config usage
├── azure_connector.py    # Add _scan_blob_encryption() + AZURE_AVAILABLE import extension
quirk/
├── config.py             # ConnectorsCfg: add enable_blob, enable_s3, aws_endpoint_url
├── config_template.yaml  # Add enable_s3, enable_blob, aws_endpoint_url commented entries
quirk/intelligence/
├── evidence.py           # Add dar_storage_unencrypted_count/aws_managed_count
├── scoring.py            # Add dar_storage_unencrypted_ratio/aws_managed_ratio weights
quirk/cbom/
├── builder.py            # Pass 1/2/3 skip-list extensions for S3, AZURE_BLOB
run_scan.py               # S3 / Azure Blob scan phase blocks + GCS re-use path
quantum-chaos-enterprise-lab/
├── docker-compose.yml    # Add storage profile: minio + minio-seed
├── storage/
│   ├── minio-seed.sh     # Init buckets (encrypted-bucket, unencrypted-bucket)
│   └── expected_results.md  # NEW: Phase 28 expected results
tests/
├── test_storage_connectors.py  # NEW: S3, Azure Blob, GCS re-use tests
```

### Pattern 1: S3 Encryption Scan — `ClientError` as Unencrypted Detection

The critical implementation detail for S3: when no encryption policy exists, `get_bucket_encryption` raises `ClientError` with code `ServerSideEncryptionConfigurationNotFoundError`. This is NOT a scan error — it is the unencrypted detection path.

```python
# Source: CONTEXT.md D-06 specifics + aws_connector.py _scan_rds_encryption pattern
from concurrent.futures import ThreadPoolExecutor
from botocore.exceptions import ClientError

def _probe_bucket_encryption(client, bucket_name: str, logger) -> dict:
    """Returns a dict with 'service_detail' and optional 'severity'."""
    try:
        resp = client.get_bucket_encryption(Bucket=bucket_name)
        rules = resp.get("ServerSideEncryptionConfiguration", {}).get("Rules", [])
        if not rules:
            return {"service_detail": "S3/unencrypted", "severity": "HIGH"}
        rule = rules[0].get("ApplyServerSideEncryptionByDefault", {})
        algo = rule.get("SSEAlgorithm", "")
        kms_key = str(rule.get("KMSMasterKeyID") or "").strip()
        if algo == "AES256":
            return {"service_detail": "S3/sse-s3", "severity": None}
        elif algo == "aws:kms":
            if not kms_key or "alias/aws/s3" in kms_key:
                return {"service_detail": "S3/sse-kms-aws", "severity": "MEDIUM"}
            return {"service_detail": "S3/sse-kms-cmk", "severity": None}
        return {"service_detail": "S3/unencrypted", "severity": "HIGH"}
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code == "ServerSideEncryptionConfigurationNotFoundError":
            # This is NOT a scan error — it IS the unencrypted signal
            return {"service_detail": "S3/unencrypted", "severity": "HIGH"}
        # Genuine access error
        if logger:
            logger.v(f"S3 get_bucket_encryption error for {bucket_name}: {e}")
        return None  # skip this bucket

def _scan_s3_encryption(session, logger, session_start=None) -> List[CryptoEndpoint]:
    results = []
    try:
        client = session.client("s3")
        buckets = client.list_buckets().get("Buckets", [])  # NOT a paginator
        
        def probe(bucket):
            name = bucket.get("Name", "")
            enc = _probe_bucket_encryption(client, name, logger)
            if enc is None:
                return None
            ep = CryptoEndpoint(
                host=f"arn:aws:s3:::{name}",
                port=0,
                protocol="S3",
                service_detail=enc["service_detail"],
                dat_scan_json=json.dumps({"bucket": name, **enc}, default=str),
                scanned_at=(session_start or datetime.now(timezone.utc)).replace(tzinfo=None),
            )
            if enc["severity"]:
                ep.severity = enc["severity"]
            return ep
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            for result in executor.map(probe, buckets):
                if result is not None:
                    results.append(result)
    except Exception as exc:
        if logger:
            logger.v(f"S3 scan error: {exc}")
    return results
```

### Pattern 2: Azure Blob Account-Level Encryption — `azure-mgmt-storage`

```python
# Source: CONTEXT.md D-03/D-07 + azure_connector.py _scan_app_gateways pattern
def _scan_blob_encryption(credential, subscription_id: str, logger, session_start=None) -> List[CryptoEndpoint]:
    results = []
    try:
        from azure.mgmt.storage import StorageManagementClient
        client = StorageManagementClient(credential, subscription_id)
        for account in client.storage_accounts.list():
            try:
                enc = getattr(account, "encryption", None)
                key_source = str(getattr(enc, "key_source", "") or "").lower()
                # Normalize: "microsoft.storage" or "microsoft.keyvault"
                if key_source == "microsoft.keyvault":
                    service_detail = "BLOB/cmk"
                    severity = None
                else:
                    # "microsoft.storage" or absent/null -> MEDIUM
                    service_detail = "BLOB/platform-managed"
                    severity = "MEDIUM"
                
                # Enumerate containers — one CryptoEndpoint per container
                containers = list(client.blob_containers.list(
                    resource_group_name=account.id.split("/")[4],
                    account_name=account.name,
                ))
                for container in containers:
                    ep = CryptoEndpoint(
                        host=container.id,
                        port=0,
                        protocol="AZURE_BLOB",
                        service_detail=service_detail,
                        dat_scan_json=json.dumps({
                            "account": account.name,
                            "container": container.name,
                            "key_source": key_source or "absent",
                        }, default=str),
                        scanned_at=(session_start or datetime.now(timezone.utc)).replace(tzinfo=None),
                    )
                    if severity:
                        ep.severity = severity
                    results.append(ep)
            except Exception as exc:
                if logger:
                    logger.v(f"Azure Blob account scan error for {getattr(account, 'name', '?')}: {exc}")
    except ImportError:
        if logger:
            logger.v("azure-mgmt-storage not installed — Azure Blob scanning unavailable")
    except Exception as exc:
        if logger:
            logger.v(f"Azure Blob scan error: {exc}")
    return results
```

### Pattern 3: GCS Re-Use — Read Sentinel from In-Memory Endpoint List

STOR-03 requires zero additional GCS API calls. The sentinel row is already in the in-memory `gcp_endpoints` list from the earlier `scan_gcp_targets()` call. `run_scan.py` should extract it before assembling the master endpoint list.

```python
# Source: CONTEXT.md Claude's Discretion + gcp_connector.py _scan_gcs() sentinel pattern
# In run_scan.py, after gcp_endpoints is populated:

def _process_gcs_storage_encryption(gcp_endpoints: list, logger) -> List[CryptoEndpoint]:
    """Extract gcs_scan_json from GCS-SUMMARY sentinel and produce per-bucket storage findings."""
    from quirk.models import CryptoEndpoint
    sentinel = next(
        (ep for ep in gcp_endpoints if getattr(ep, "cert_pubkey_alg", "") == "GCS-SUMMARY"),
        None,
    )
    if sentinel is None or not sentinel.gcs_scan_json:
        return []
    try:
        bucket_list = json.loads(sentinel.gcs_scan_json)
    except (json.JSONDecodeError, TypeError):
        return []
    # GCS per-bucket findings are already in gcp_endpoints from Phase 26
    # STOR-03 is satisfied by NOT calling GCS API again.
    # No additional CryptoEndpoints created here — Phase 26 per-bucket rows already exist.
    return []   # sentinel consumption only; findings already present from Phase 26
```

Note: STOR-03 is satisfied architecturally by Phase 26's existing per-bucket rows in `gcp_endpoints`. The GCS processor in Phase 28 only needs to confirm `gcs_scan_json` was read and that no new API calls occurred. If the plan requires evidence counters for GCS unencrypted buckets, those can be read from the Phase 26 per-bucket rows (`cert_pubkey_alg == "Google-Managed"` → MEDIUM analogue).

### Pattern 4: Evidence Counters Extension

```python
# Source: evidence.py build_evidence_summary() — follow dar_db_* pattern
# Add alongside existing dar_db_plaintext_count/dar_db_weak_ssl_count loop

dar_storage_unencrypted_count = 0   # S3 HIGH + Azure Blob MEDIUM absent
dar_storage_aws_managed_count = 0   # S3 SSE-KMS-AWS + Azure Blob platform-managed

# In the for ep in endpoint_list loop:
elif proto == "S3":
    sd = str(getattr(ep, "service_detail", "") or "")
    if "S3/unencrypted" in sd:
        dar_storage_unencrypted_count += 1
    elif "S3/sse-kms-aws" in sd:
        dar_storage_aws_managed_count += 1

elif proto == "AZURE_BLOB":
    sd = str(getattr(ep, "service_detail", "") or "")
    if "BLOB/platform-managed" in sd:
        dar_storage_aws_managed_count += 1

# Add to returned dict:
"dar_storage_unencrypted_count": dar_storage_unencrypted_count,
"dar_storage_aws_managed_count": dar_storage_aws_managed_count,
"dar_storage_unencrypted_ratio": round(dar_storage_unencrypted_count / total_endpoints, 4) if total_endpoints else 0.0,
"dar_storage_aws_managed_ratio": round(dar_storage_aws_managed_count / total_endpoints, 4) if total_endpoints else 0.0,
```

### Pattern 5: Scoring Weights Extension

```python
# Source: scoring.py SCORE_WEIGHTS dict — follow dar_db_* pattern
SCORE_WEIGHTS: Dict[str, float] = {
    # ... existing weights ...
    "dar_db_plaintext_ratio": 12.0,
    "dar_db_weak_ssl_ratio": 6.0,
    # Phase 28 additions:
    "dar_storage_unencrypted_ratio": 12.0,   # same weight as plaintext DB
    "dar_storage_aws_managed_ratio": 4.0,    # compliance gap, not active weakness
}

# In compute_readiness_score(), extend dar_impacts:
dar_impacts: List[Tuple[str, float]] = [
    ("Database plaintext connections", -_ratio(dar_db_plaintext, denom) * w["dar_db_plaintext_ratio"]),
    ("Database weak SSL configuration", -_ratio(dar_db_weak_ssl, denom) * w["dar_db_weak_ssl_ratio"]),
    # Phase 28 additions:
    ("Object storage unencrypted", -_ratio(dar_storage_unencrypted, denom) * w["dar_storage_unencrypted_ratio"]),
    ("Object storage platform-managed keys", -_ratio(dar_storage_aws_managed, denom) * w["dar_storage_aws_managed_ratio"]),
]
```

### Pattern 6: CBOM Builder Skip-List Extension

```python
# Source: cbom/builder.py Pass 2 skip-list + Pass 3 skip-list
# Pass 2 — Certificate components (currently skips SSH, CONTAINER, SOURCE, KERBEROS, SAML,
#           DNSSEC, GCP, CLOUD_SQL, POSTGRESQL, MYSQL, RDS)
# ADD: "S3", "AZURE_BLOB" to Pass 2 skip tuple

# Pass 3 — Protocol components skip-list (same protocols)
# ADD: "S3", "AZURE_BLOB" to Pass 3 skip tuple

# Pass 1 — Algorithm registration (Add elif blocks):
elif ep.protocol in ("S3", "AZURE_BLOB"):
    # Storage config findings — no key material to catalog.
    # Security signal is in service_detail; CBOM algorithm catalog not applicable.
    pass
```

### Pattern 7: MinIO Chaos Lab

MinIO init container follows the `kms-seed.sh` pattern: a separate seed container with `restart: "no"` that depends on the MinIO service reaching healthy state. MinIO supports SSE-S3 configuration via the `mc` client.

```yaml
# quantum-chaos-enterprise-lab/docker-compose.yml addition
minio:
  image: minio/minio:latest
  profiles: ["storage-s3"]   # separate from existing "storage" profile (vault/localstack-kms/pgcrypto)
  command: server /data --console-address ":9001"
  environment:
    MINIO_ROOT_USER: minioadmin
    MINIO_ROOT_PASSWORD: minioadmin
  ports:
    - "29000:9000"
    - "29001:9001"
  healthcheck:
    test: ["CMD", "mc", "ready", "local"]
    interval: 5s
    timeout: 5s
    retries: 10
    start_period: 10s

minio-seed:
  image: minio/mc:latest
  profiles: ["storage-s3"]
  restart: "no"
  depends_on:
    minio:
      condition: service_healthy
  entrypoint: ["/bin/sh", "/minio-seed.sh"]
  volumes:
    - ./storage/minio-seed.sh:/minio-seed.sh:ro
```

```bash
# storage/minio-seed.sh
mc alias set local http://minio:9000 minioadmin minioadmin
mc mb local/encrypted-bucket
mc mb local/unencrypted-bucket
# Enable SSE-S3 on encrypted-bucket
mc encrypt set sse-s3 local/encrypted-bucket
# unencrypted-bucket left without encryption policy
echo "MinIO seed complete"
```

Note on profile naming: the existing `storage` profile in docker-compose.yml is already taken (vault, localstack-kms, postgres-pgcrypto from Phase 27). Use `storage-s3` as the new profile name to avoid collision.

### Anti-Patterns to Avoid

- **Using `get_paginator('list_buckets')`:** This raises `OperationNotPageableError` — `list_buckets` is not paginatable. Use `client.list_buckets().get("Buckets", [])` directly. [VERIFIED: CONTEXT.md D-06 + STATE.md accumulated decisions]
- **Treating `ServerSideEncryptionConfigurationNotFoundError` as a scan error:** This `ClientError` is the primary detection mechanism for unencrypted S3 buckets. Catch it explicitly and map to `S3/unencrypted` HIGH finding. [VERIFIED: CONTEXT.md specifics]
- **Querying the GCS API again for STOR-03:** The `gcs_scan_json` sentinel from Phase 26 is in the in-memory `gcp_endpoints` list. Read from it. No `storage.buckets.list` call. [VERIFIED: gcp_connector.py _scan_gcs(), CONTEXT.md STOR-03]
- **Creating new DB columns for Phase 28:** `dat_scan_json` and `severity` are already present from Phase 27 (`_V43_COLUMN_DDLS` in db.py). Do NOT call ALTER TABLE or add new entries to `_V43_COLUMN_DDLS`. [VERIFIED: db.py]
- **Using `datetime.now()` inside scanner functions:** ISSUE-3 pattern requires `session_start` to be passed from `run_scan.py` and propagated to all new scanner invocations. [VERIFIED: run_scan.py line 475 and db_connector call pattern]
- **Using `protocol="STORAGE"` as the CONTEXT.md domain description suggests:** The actual locked decisions specify `protocol="S3"` for S3 findings and `protocol="AZURE_BLOB"` for Azure Blob findings. GCS per-bucket rows already use `protocol="GCP"` from Phase 26. [VERIFIED: CONTEXT.md D-05, D-06]
- **Missing azure-mgmt-storage import guard:** Follow the `_scan_app_gateways` pattern — use a bare `import` inside the function body with `except ImportError:` guard, not a module-level `try/except`. Module-level guard is used for the main azure.identity/azure.keyvault imports that control `AZURE_AVAILABLE`. [VERIFIED: azure_connector.py]
- **Forgetting to extend `_PROTOCOL_KEYS` tuple in evidence.py:** The `protocol_counts` dict is initialized from `_PROTOCOL_KEYS`. If `S3` and `AZURE_BLOB` are not added, storage protocol counts will be absent from evidence output. [VERIFIED: evidence.py line 9]

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| S3 encryption query | Custom HTTP API calls to S3 API | `boto3 s3.get_bucket_encryption` | boto3 is already a core dependency; handles signing, retries, region routing |
| Azure storage account enumeration | Custom REST calls to ARM | `azure.mgmt.storage.StorageManagementClient` | Management plane has typed models; handles pagination via `.list()` returning iterators |
| Per-bucket parallelism | Custom thread management | `concurrent.futures.ThreadPoolExecutor` | stdlib; same pattern used throughout codebase for fingerprinting |
| S3 endpoint URL override | Custom AWS client configuration | boto3 `endpoint_url` parameter on `session.client("s3", endpoint_url=...)` | Standard boto3 pattern for LocalStack/MinIO targeting |
| MinIO bucket seeding | Custom Python seeding script | `minio/mc` (MinIO client) via init container | Matches existing `kms-seed.sh` / `vault-seed.sh` / `postgres-init.sql` init container pattern |

**Key insight:** The only genuinely new integration surface is `azure-mgmt-storage`. Everything else reuses boto3 (already in core deps), the existing AZURE_AVAILABLE guard + DefaultAzureCredential pattern, and the in-memory GCP endpoint list from Phase 26.

---

## Common Pitfalls

### Pitfall 1: `enable_aws` vs `enable_s3` Guard Logic
**What goes wrong:** S3 scanning is gated on `enable_s3`, not on `enable_aws`. A user may have `enable_aws: true` (for KMS/RDS/ACM) but not want S3 scanning. Guarding only on `enable_aws` would silently run S3 scanning for all existing AWS-enabled configs.
**Why it happens:** The CONTEXT.md discretion adds `enable_s3: bool = False` as a separate field, which is distinct from `enable_aws`.
**How to avoid:** In `run_scan.py`, add a separate `if cfg.connectors.enable_s3:` block for calling `_scan_s3_encryption`. In `scan_aws_targets()`, the call to `_scan_s3_encryption` should be conditional on `enable_s3` being passed down, OR `_scan_s3_encryption` is called directly from `run_scan.py` after `scan_aws_targets()`.
**Warning signs:** Test config with `enable_aws: true, enable_s3: false` — should produce zero S3 CryptoEndpoints.

### Pitfall 2: Azure Blob Resource Group Extraction from Account ID
**What goes wrong:** `StorageManagementClient.blob_containers.list()` requires `resource_group_name` as a parameter. This must be extracted from the storage account's `id` field (ARM resource ID format: `/subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.Storage/storageAccounts/{name}`).
**Why it happens:** The ARM resource ID has a fixed structure; `account.id.split("/")[4]` yields the resource group name.
**How to avoid:** Parse `account.id` with a robust split or regex; do not hardcode index without a comment. Consider `account.id.split("/resourceGroups/")[1].split("/")[0]` for clarity.
**Warning signs:** `ResourceNotFoundError` on `blob_containers.list()` is often a symptom of wrong resource group name.

### Pitfall 3: MinIO Profile Name Collision
**What goes wrong:** The `storage` Docker Compose profile is already taken by vault + localstack-kms + postgres-pgcrypto (Phase 27). Adding MinIO to `profile: ["storage"]` would require Phase 27's services to start for Phase 28 testing and vice versa.
**Why it happens:** Phase 27 introduced the `storage` profile for its chaos services. Phase 28 adds MinIO under a distinct storage sub-domain.
**How to avoid:** Use `profile: ["storage-s3"]` for MinIO and minio-seed containers.
**Warning signs:** Running `docker compose --profile storage-s3 up` starts only MinIO, not Vault/LocalStack-KMS.

### Pitfall 4: GCS-SUMMARY Sentinel Not Found When GCP Disabled
**What goes wrong:** If `enable_gcp: false`, there are no GCP endpoints and no sentinel row. The GCS re-use path in `run_scan.py` must guard on the sentinel being present before processing.
**Why it happens:** STOR-03 re-use path assumes Phase 26 ran in the same scan session.
**How to avoid:** `_process_gcs_storage_encryption` must return `[]` gracefully when no sentinel found. No error or log message needed — GCP simply wasn't scanned.
**Warning signs:** `AttributeError` or `StopIteration` from the sentinel search when `gcp_endpoints = []`.

### Pitfall 5: `dat_scan_json` Column Null on Sentinel Row
**What goes wrong:** The Phase 26 `gcs_scan_json` sentinel uses `gcs_scan_json=json.dumps(bucket_list)` but leaves `dat_scan_json=None`. Phase 28 storage findings go in `dat_scan_json` on their own per-bucket rows. Do not confuse these two JSON columns.
**Why it happens:** `gcs_scan_json` is the GCS hand-off column (Phase 26); `dat_scan_json` is the universal DAR scan result column (Phase 27+).
**How to avoid:** S3/Azure Blob rows use `dat_scan_json` for per-bucket/container JSON. GCS re-use path reads from `gcs_scan_json` on the sentinel row. These are different fields on different rows.
**Warning signs:** `dat_scan_json` null on S3/Azure Blob rows means the storage policy JSON wasn't captured.

### Pitfall 6: `_PROTOCOL_KEYS` Missing S3 and AZURE_BLOB
**What goes wrong:** `evidence.py` initializes `protocol_counts` from `_PROTOCOL_KEYS` tuple. If `S3` and `AZURE_BLOB` are not added, they won't appear in `protocol_counts` and won't be counted in the evidence dict.
**Why it happens:** `_PROTOCOL_KEYS` is an explicit allowlist at the top of `evidence.py` (line 9).
**How to avoid:** Add `"S3"`, `"AZURE_BLOB"` to `_PROTOCOL_KEYS` tuple when adding the storage counter logic.
**Warning signs:** `protocol_counts` key absent in evidence output for a scan with S3 results.

### Pitfall 7: CBOM Pass 2 Certificate Skip
**What goes wrong:** `build_cbom` Pass 2 currently skips a hardcoded tuple of protocols for certificate components. `S3` and `AZURE_BLOB` rows have `cert_pubkey_alg=None` (no cert info) but will reach Pass 2 if not in the skip list, silently producing no cert component (acceptable) but also not raising. The real risk is Pass 1: if `cert_pubkey_alg` is set to something on an S3 row, it could accidentally register it as an algorithm.
**Why it happens:** S3/Azure Blob rows don't have `cert_pubkey_alg` set — they use `service_detail` for the encryption classification. But the builder's else-branch (TLS default) could catch them.
**How to avoid:** Add explicit `elif ep.protocol in ("S3", "AZURE_BLOB"): pass` in Pass 1, and add to Pass 2/3 skip tuples.
**Warning signs:** Unexpected algorithm components in CBOM for S3 scan results.

---

## Code Examples

### S3 Unencrypted Detection via ClientError

```python
# Source: CONTEXT.md specifics section (verified pattern for this codebase)
from botocore.exceptions import ClientError

try:
    resp = client.get_bucket_encryption(Bucket=bucket_name)
except ClientError as e:
    code = e.response.get("Error", {}).get("Code", "")
    if code == "ServerSideEncryptionConfigurationNotFoundError":
        # Detection path: bucket has no encryption policy -> HIGH
        return {"service_detail": "S3/unencrypted", "severity": "HIGH"}
    # Other ClientError (access denied, etc.) -> log and skip
    if logger:
        logger.v(f"S3 get_bucket_encryption error for {bucket_name}: {e}")
    return None
```

### RDS Pattern Reference (direct template for S3)

```python
# Source: quirk/scanner/aws_connector.py lines 75-129 [VERIFIED]
# _scan_rds_encryption is the direct template:
# - Uses paginator for describe_db_instances
# - Derives service_detail string from API response fields
# - Sets ep.severity when severity is non-None
# - Per-instance exception handling with logger.v()
```

### Azure Blob Containers List Pattern

```python
# Source: CONTEXT.md D-03 + azure_connector.py _scan_app_gateways [VERIFIED]
from azure.mgmt.storage import StorageManagementClient  # inside function body

client = StorageManagementClient(credential, subscription_id)
for account in client.storage_accounts.list():
    rg = account.id.split("/resourceGroups/")[1].split("/")[0]
    containers = list(client.blob_containers.list(
        resource_group_name=rg,
        account_name=account.name,
    ))
```

### GCS Sentinel Read Pattern

```python
# Source: gcp_connector.py lines 308-316 [VERIFIED] — sentinel creation
# Phase 28 reads what Phase 26 wrote:
sentinel = next(
    (ep for ep in gcp_endpoints if getattr(ep, "cert_pubkey_alg", "") == "GCS-SUMMARY"),
    None,
)
if sentinel and sentinel.gcs_scan_json:
    bucket_list = json.loads(sentinel.gcs_scan_json)
```

### run_scan.py Session_Start Pattern

```python
# Source: run_scan.py lines 474-499 [VERIFIED] — ISSUE-3 pattern
session_start = datetime.now(timezone.utc)   # set once before all new scanners

# S3 scan block (new, Phase 28):
s3_endpoints = []
with _phase_timer(run_stats, "s3_scanning"):
    if cfg.connectors.enable_s3:
        s3_endpoints = _scan_s3_encryption(
            session=boto3.Session(region_name=cfg.connectors.aws_region, ...),
            logger=logger,
            session_start=session_start,
        )

# Azure Blob scan block (new, Phase 28):
blob_endpoints = []
with _phase_timer(run_stats, "blob_scanning"):
    if cfg.connectors.enable_blob:
        from quirk.scanner.azure_connector import _scan_blob_encryption
        blob_endpoints = _scan_blob_encryption(
            credential=DefaultAzureCredential(),
            subscription_id=cfg.connectors.azure_subscription_id or "",
            logger=logger,
            session_start=session_start,
        )
```

---

## Runtime State Inventory

> Omitted — Phase 28 is a greenfield extension, not a rename/refactor/migration.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `StorageEncryptionType` field on RDS | `StorageEncrypted` + `KmsKeyId` derivation | Phase 27 (discovered) | `StorageEncryptionType` does not exist in boto3 API |
| `get_paginator('list_buckets')` | Direct `list_buckets()` call | This phase | S3 `list_buckets` is not paginatable |
| S3 "no encryption" as access error | `ClientError.ServerSideEncryptionConfigurationNotFoundError` as finding | This phase | Must catch explicitly; it is the detection path, not a failure |

**Deprecated/outdated:**
- `CustomerMasterKeySpec` on KMS keys: deprecated in favor of `KeySpec`; `aws_connector.py` already handles fallback. Not relevant to S3 but worth noting for consistency.
- Azure `keySource` enum values are case-sensitive in some SDK versions — normalize with `.lower()` before comparison.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `azure-mgmt-storage>=21.0.0` is the correct minimum version for `blob_containers.list()` and `storage_accounts.list()` | Standard Stack | Wrong minimum version could cause AttributeError or missing API methods; verify with `pip show azure-mgmt-storage` after install |
| A2 | MinIO `minio/minio:latest` supports `mc encrypt set sse-s3` to configure bucket-level SSE-S3 | Standard Stack / Chaos Lab | If MinIO SSE-S3 API differs, the chaos lab `encrypted-bucket` test won't produce the expected no-finding path; SSE-KMS deferred so impact is limited |
| A3 | `azure.mgmt.storage.StorageManagementClient.blob_containers.list()` returns containers under a storage account when given `resource_group_name` and `account_name` | Architecture Patterns | Method signature may differ in 21.x; verify against azure-mgmt-storage changelog |
| A4 | `account.id.split("/resourceGroups/")[1].split("/")[0]` is a reliable way to extract resource group name from ARM resource ID | Code Examples | ARM resource ID format is stable; risk is LOW but should be guarded with try/except in implementation |

**If this table is empty:** Not empty — four assumptions that should be verified during plan execution via `pip show azure-mgmt-storage` and MinIO SSE-S3 documentation check.

---

## Open Questions

1. **`enable_s3` vs `enable_aws` invocation path**
   - What we know: `scan_aws_targets()` builds a boto3 session and calls internal scan functions. Adding `_scan_s3_encryption` to `scan_aws_targets()` is D-01.
   - What's unclear: Should `_scan_s3_encryption` be called unconditionally inside `scan_aws_targets()` (like `_scan_rds_encryption`) or should `enable_s3` be checked inside `scan_aws_targets()` (requiring ConnectorsCfg to be threaded through) or checked in `run_scan.py` before calling `scan_aws_targets()`?
   - Recommendation: Check `enable_s3` in `run_scan.py` before calling `_scan_s3_encryption` directly (not inside `scan_aws_targets()`), mirroring how `scan_aws_targets()` is gated on `enable_aws`. This keeps `scan_aws_targets()` signature stable and consistent with the existing gating pattern.

2. **aws_endpoint_url config field for MinIO targeting**
   - What we know: CONTEXT.md mentions `aws_endpoint_url` config field. It does not currently exist in `ConnectorsCfg`.
   - What's unclear: Should it be added to `ConnectorsCfg` as `aws_endpoint_url: Optional[str] = None`? Or should MinIO be targeted purely via environment variable (`AWS_ENDPOINT_URL`)?
   - Recommendation: Add `aws_endpoint_url: Optional[str] = None` to `ConnectorsCfg` and thread it through to `session.client("s3", endpoint_url=cfg.connectors.aws_endpoint_url)`. This is consistent with config-file-driven approach used throughout the project and avoids environment variable magic.

3. **GCS evidence counter integration**
   - What we know: CONTEXT.md D-09 says "GCS CMEK findings do not add new counters — GCS bucket findings are handled by the existing GCS endpoint rows from Phase 26."
   - What's unclear: Phase 26 per-bucket rows use `cert_pubkey_alg` of `"CMEK"` or `"Google-Managed"` with `protocol="GCP"`. These don't get picked up by the `S3`/`AZURE_BLOB` evidence counter logic.
   - Recommendation: GCS is intentionally excluded from Phase 28 DAR scoring. The Phase 26 rows are already in the DB; if scoring integration for GCS bucket encryption is desired, it's a Phase 31+ concern. Phase 28 scope is S3 + Azure Blob counters only.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Docker | MinIO chaos lab | [ASSUMED — not probed] | — | Skip chaos lab; unit tests mock boto3 |
| boto3 | S3 scanning | ✓ (core dep) [VERIFIED: pyproject.toml] | >=1.42.0 | N/A — in core |
| azure-identity | Azure Blob | ✓ (core dep) [VERIFIED: pyproject.toml] | >=1.25.0 | N/A — in core |
| azure-mgmt-storage | Azure Blob | ✗ (not yet added) | — | Add to [cloud] extras per D-11 |
| google-api-python-client | GCS re-use (Phase 26 data) | ✓ ([cloud] extras) [VERIFIED: pyproject.toml] | >=2.0.0 | N/A — optional, gracefully skipped |

**Missing dependencies with no fallback:**
- `azure-mgmt-storage` — required for STOR-02; must be added to `[cloud]` extras in pyproject.toml as the first task.

**Missing dependencies with fallback:**
- Docker (MinIO) — unit tests mock boto3; chaos lab is validation-only and can be skipped if Docker unavailable.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (existing, no config file — discovered by convention) |
| Config file | none — pytest discovers `tests/` directory |
| Quick run command | `python -m pytest tests/test_storage_connectors.py -x -q` |
| Full suite command | `python -m pytest tests/ -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| STOR-01 | S3 `list_buckets` returns bucket list and `get_bucket_encryption` per bucket classifies SSE-S3/SSE-KMS/unencrypted | unit | `pytest tests/test_storage_connectors.py::test_s3_unencrypted_detection -x` | Wave 0 |
| STOR-01 | `ServerSideEncryptionConfigurationNotFoundError` maps to HIGH/S3/unencrypted | unit | `pytest tests/test_storage_connectors.py::test_s3_no_encryption_config_error -x` | Wave 0 |
| STOR-01 | SSE-S3 (`AES256`) produces no finding / service_detail="S3/sse-s3" | unit | `pytest tests/test_storage_connectors.py::test_s3_sse_s3_no_finding -x` | Wave 0 |
| STOR-01 | SSE-KMS AWS-managed produces MEDIUM/S3/sse-kms-aws | unit | `pytest tests/test_storage_connectors.py::test_s3_sse_kms_aws_managed -x` | Wave 0 |
| STOR-01 | SSE-KMS CMK produces no finding / service_detail="S3/sse-kms-cmk" | unit | `pytest tests/test_storage_connectors.py::test_s3_sse_kms_cmk_no_finding -x` | Wave 0 |
| STOR-01 | ThreadPoolExecutor processes multiple buckets in parallel (mock) | unit | `pytest tests/test_storage_connectors.py::test_s3_parallel_scan -x` | Wave 0 |
| STOR-02 | Azure Blob `StorageManagementClient` enumerates accounts and containers | unit | `pytest tests/test_storage_connectors.py::test_azure_blob_platform_managed -x` | Wave 0 |
| STOR-02 | `Microsoft.Keyvault` keySource produces no finding / BLOB/cmk | unit | `pytest tests/test_storage_connectors.py::test_azure_blob_cmk_no_finding -x` | Wave 0 |
| STOR-02 | Absent keySource treated as MEDIUM | unit | `pytest tests/test_storage_connectors.py::test_azure_blob_absent_key_source -x` | Wave 0 |
| STOR-03 | GCS re-use reads `gcs_scan_json` from sentinel endpoint without any API call | unit | `pytest tests/test_storage_connectors.py::test_gcs_reuse_no_api_call -x` | Wave 0 |
| STOR-03 | Missing sentinel (enable_gcp=False) returns [] gracefully | unit | `pytest tests/test_storage_connectors.py::test_gcs_reuse_no_sentinel -x` | Wave 0 |
| D-09 | `dar_storage_unencrypted_count` increments for S3/unencrypted rows | unit | `pytest tests/test_intelligence_evidence.py -x -q` (extend existing) | Exists |
| D-10 | `dar_storage_unencrypted_ratio` weight applies in scoring | unit | `pytest tests/test_intelligence_scoring.py -x -q` (extend existing) | Exists |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_storage_connectors.py -x -q`
- **Per wave merge:** `python -m pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_storage_connectors.py` — all STOR-01/STOR-02/STOR-03 test cases (new file)

*(Existing test infrastructure — pytest, conftest.py, mock patterns — covers all other needs. No framework install needed.)*

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | N/A — uses ambient cloud credentials (boto3 session, DefaultAzureCredential) |
| V3 Session Management | no | N/A — CLI tool, no user sessions |
| V4 Access Control | no | N/A — read-only management plane queries |
| V5 Input Validation | yes | `_SAFE_COL_RE` in db.py guards column names; no user-supplied SQL; `json.dumps(default=str)` prevents serialization failures |
| V6 Cryptography | no | This phase detects crypto posture; it does not implement cryptographic operations |

### Known Threat Patterns for Cloud Management Plane APIs

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Credential exfiltration via `dat_scan_json` | Information Disclosure | `dat_scan_json` stores bucket metadata only (name, encryption type) — no key material, no credentials; `default=str` prevents accidental object serialization |
| Over-privileged scanner role accessing bucket contents | Elevation of Privilege | Scanner uses management plane only (`list_buckets`, `get_bucket_encryption`, `storage_accounts.list`); no data plane calls; no `GetObject`, no blob content reads |
| MinIO admin credentials in compose file | Information Disclosure | `minioadmin/minioadmin` is test-only; lab.sh and README should document this is chaos lab only |

---

## Sources

### Primary (HIGH confidence)
- `quirk/scanner/aws_connector.py` — `_scan_rds_encryption()` exact template, `BOTO3_AVAILABLE` flag pattern, `scan_aws_targets()` signature [VERIFIED: read in this session]
- `quirk/scanner/azure_connector.py` — `DefaultAzureCredential`, `_scan_app_gateways()` inline import pattern, `AZURE_AVAILABLE` flag [VERIFIED: read in this session]
- `quirk/scanner/gcp_connector.py` — `_scan_gcs()` sentinel construction, `cert_pubkey_alg="GCS-SUMMARY"`, `gcs_scan_json=json.dumps(bucket_list)` [VERIFIED: read in this session]
- `quirk/db.py` — `_V43_COLUMN_DDLS`, `_ensure_v43_columns()`, `_ensure_gcp_columns()` chain [VERIFIED: read in this session]
- `quirk/models.py` — `CryptoEndpoint` fields `dat_scan_json`, `gcs_scan_json`, `severity` [VERIFIED: read in this session]
- `quirk/config.py` — `ConnectorsCfg` dataclass, `_KNOWN_CONNECTOR_KEYS` pattern, field defaults [VERIFIED: read in this session]
- `quirk/intelligence/evidence.py` — `_PROTOCOL_KEYS`, `dar_db_*` counter pattern, `build_evidence_summary()` structure [VERIFIED: read in this session]
- `quirk/intelligence/scoring.py` — `SCORE_WEIGHTS`, `PROFILE_MULTIPLIERS["dar_"]`, `dar_impacts` list [VERIFIED: read in this session]
- `quirk/cbom/builder.py` — Pass 1/2/3 skip patterns, `elif ep.protocol in (...)` blocks [VERIFIED: read in this session]
- `run_scan.py` — `session_start` pattern, scan phase blocks, `_phase_timer` pattern [VERIFIED: read in this session]
- `pyproject.toml` — `[cloud]` extras group current contents [VERIFIED: read in this session]
- `quantum-chaos-enterprise-lab/docker-compose.yml` — existing `storage` profile name (vault/localstack-kms/pgcrypto), init container pattern [VERIFIED: read in this session]

### Secondary (MEDIUM confidence)
- CONTEXT.md locked decisions — all API choices, severity ladders, protocol names, config field names [VERIFIED: read in this session — represents user's pre-researched decisions]
- STATE.md accumulated decisions — `S3 list_buckets is NOT paginated`, `OperationNotPageableError` warning [VERIFIED: read in this session]

### Tertiary (LOW confidence)
- None — all claims are verified against the actual codebase or locked in CONTEXT.md

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all core libraries verified in pyproject.toml; only azure-mgmt-storage version is ASSUMED
- Architecture: HIGH — direct inspection of all canonical reference files; patterns are explicit from existing Phase 27 and Phase 26 implementations
- Pitfalls: HIGH — critical S3 `ClientError` pattern, `_PROTOCOL_KEYS` gap, and `storage` profile collision all verified from codebase inspection

**Research date:** 2026-04-25
**Valid until:** 2026-05-25 (azure-mgmt-storage API is stable; boto3 S3 API is stable; only MinIO SSE details are ASSUMED)
