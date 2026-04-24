# Feature Research: Data at Rest — v4.3 Milestone

**Domain:** Cloud and infrastructure data-at-rest cryptographic inventory for post-quantum readiness
**Milestone:** v4.3 Data at Rest
**Researched:** 2026-04-24
**Confidence:** HIGH (GCP/AWS/Azure official docs verified; K8s official docs verified; Vault official docs verified; patterns confirmed against existing codebase)

---

## Context: What Already Exists (Do Not Rebuild)

QU.I.R.K. v4.2.0 ships the following that v4.3 must plug into:

- `CryptoEndpoint` SQLite model with additive `*_scan_json` blob columns per scanner
- `cloud_scan_json` column used by `aws_connector.py` and `azure_connector.py` — GCP reuses this same column, same pattern
- `KMS_KEY_SPEC_MAP` in `aws_connector.py` maps key spec strings → (algorithm, key_size) — GCP needs an equivalent `GCP_KEY_ALGORITHM_MAP`
- `build_cbom()` dispatches on `ep.protocol` — new protocol strings `GCP`, `DATABASE`, `OBJECT_STORAGE`, `K8S`, `VAULT` need dispatch entries in Pass 1 and Pass 3
- `classify_algorithm()` in `quirk/cbom/classifier.py` is the single lookup table — new algorithm names must go here
- `scanned_at` DateTime column on `CryptoEndpoint` is the only scan session marker — trend analysis needs a new `ScanSession` SQLite table or equivalent session-level metadata record
- `run_scan.py` propagates a shared `session_start` datetime to all scanners (Phase 24 fix) — trend analysis anchors on this value
- Intelligence scoring in `evidence.py` aggregates counters — new data-at-rest surface needs new evidence counters fed into scoring

---

## Feature 1: GCP Connector

### What It Does

Enumerates GCP Cloud KMS crypto key specs, Cloud SQL TLS enforcement mode, and GCS bucket
default encryption configuration. Uses `google-cloud-kms`, `google-cloud-storage`, and
`google-cloud-sqladmin` Python client libraries with ambient Application Default Credentials
(ADC). Mirrors the structural pattern of `aws_connector.py`.

### Table Stakes: GCP Connector

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Cloud KMS key enumeration — list all key rings and crypto keys per project | GCP KMS is the primary secret/key store; consultants expect this like AWS KMS | MEDIUM | `google-cloud-kms` client; `KeyManagementServiceClient.list_key_rings()` + `list_crypto_keys()` paginated; protection level (SOFTWARE/HSM/EXTERNAL) is a critical finding field |
| Map GCP key algorithm → (algorithm_name, key_size) | Without this, keys are opaque resource names | LOW | `CryptoKeyVersion.algorithm` enum: RSA_SIGN_PKCS1_2048_SHA256, EC_SIGN_P256_SHA256, GOOGLE_SYMMETRIC_ENCRYPTION, etc. Static map; 15–20 entries covers full GCP KMS algorithm set |
| Cloud KMS key rotation status — rotation period and next rotation time | Unrotated keys are a compliance finding; many enterprise policies require 90-day rotation | LOW | `CryptoKey.rotation_period` field available via API; no rotation = finding |
| Cloud SQL TLS enforcement mode — `ALLOW_UNENCRYPTED_AND_ENCRYPTED` vs `ENCRYPTED_ONLY` vs `TRUSTED_CLIENT_CERTIFICATE_REQUIRED` | Cloud SQL with TLS not enforced is a data-in-motion and posture finding | MEDIUM | `google-cloud-sqladmin` via `sqladmin_v1beta4` Discovery API; `DatabaseInstance.settings.ip_configuration.ssl_mode` field |
| GCS bucket default encryption — GOOGLE_MANAGED (GMEK) vs CUSTOMER_MANAGED (CMEK) vs CUSTOMER_SUPPLIED (CSEK) | Storage encryption posture is table-stakes for a data-at-rest audit | MEDIUM | `google-cloud-storage` client; `Bucket.default_kms_key_name` — None means GMEK; present means CMEK with the KMS key URI |
| Graceful degradation when `google-cloud-*` libraries not installed | Consistent with AWS/Azure pattern in the codebase | LOW | Try/except import at module top; log message if unavailable |
| `protocol="GCP"` on CryptoEndpoint; `cloud_scan_json` blob storage | Required for CBOM dispatch; reuse existing column | LOW | Same pattern as `aws_connector.py` and `azure_connector.py`; no new DB column needed |
| GCP ADC ambient auth — no credentials stored in code | Same requirement as AWS ambient IAM and Azure DefaultAzureCredential | LOW | `google.auth.default()` or `google.oauth2.credentials.Credentials`; no API key hardcoding |

### Differentiators: GCP Connector

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Cloud KMS protection level: SOFTWARE vs HSM | HSM-backed keys provide hardware attestation; consultants ask this for FedRAMP/PCI-DSS clients | LOW | `CryptoKeyVersion.protection_level` field; flag SOFTWARE as a finding when client has compliance requirements |
| Detect Cloud KMS keys NOT set as default for GCS buckets | Cross-surface finding: KMS key exists but GCS still uses GMEK | MEDIUM | Requires correlating KMS key list with GCS bucket CMEK assignments; useful aggregate finding |
| Cloud SQL Server CA cert algorithm | Cloud SQL issues a server cert for TLS — check its algorithm | MEDIUM | Available via `SslCert` resource on the instance; maps to existing cert_pubkey_alg field |
| BigQuery CMEK status | BigQuery datasets can use CMEK; enterprise clients often use BigQuery | MEDIUM | `google-cloud-bigquery` client; `Dataset.default_encryption_configuration`; defer to v4.4 unless straightforward |
| Cloud Spanner encryption | Spanner uses Google-managed encryption by default; CMEK available | HIGH | Low enterprise frequency; defer |

### Anti-Features: GCP Connector

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Google Workspace (Drive, Gmail) audit | Seems like full GCP coverage | Entirely different API scope (Admin SDK); not infrastructure KMS | Explicitly out of scope; document limitation |
| Cloud HSM key material export | "Complete" key audit | HSM keys are not exportable by design; attempting this will always fail | Note in report: HSM protection level means no export possible — this is a positive security control |
| Enumerate all projects in org automatically | Auto-discovery seems useful | Requires `resourcemanager.projects.list` at org level; many clients restrict this; causes auth failures | Accept project ID list from config; user specifies which projects to scan |

---

## Feature 2: Database Encryption Detection

### What It Does

Detects encryption-at-rest status for PostgreSQL, MySQL, and AWS RDS/Aurora instances.
For cloud-managed databases (RDS), uses the cloud API. For self-hosted databases, connects
via the database protocol to read system tables or server variables. This is a detection-only
scanner — no data is read.

### Key Findings Consultants Need

Encryption-at-rest is nearly always the first checkbox in a data-at-rest audit. The actionable
finding structure is: (1) Is it encrypted at all? (2) What encryption method/key manager?
(3) Is TLS enforced for connections? RDS is the highest-value path because the API is
deterministic and agentless.

### Table Stakes: Database Encryption Detection

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| AWS RDS `StorageEncrypted` flag detection via `describe_db_instances` | Canonical data-at-rest finding for cloud databases; covered by AWS Config rule `rds-storage-encrypted` | LOW | Already have boto3 in stack via `aws_connector.py`; call `rds_client.describe_db_instances()` paginated; `StorageEncrypted=False` is a HIGH finding |
| AWS RDS `StorageEncryptionType` field — `none` vs `sse-rds` vs `sse-kms` | `StorageEncryptionType=none` is a hard finding (2025 Aurora API field); `sse-kms` confirms CMK usage | LOW | New 2025 Aurora API field; `StorageEncrypted=True` with `StorageEncryptionType=sse-rds` = AWS-owned key (weaker than CMK); CMK preferred for regulated workloads |
| AWS RDS KmsKeyId — identify which KMS key protects the database | Finding: using AWS-managed key vs customer-managed key (different compliance posture) | LOW | `KmsKeyId` field in `describe_db_instances` response; cross-reference with existing KMS key list |
| AWS RDS `MultiAZ` + snapshot encryption status | Snapshots and replicas must also be encrypted; common gap | LOW | `CopyTagsToSnapshot`, automated backup encryption inherits from instance |
| `rds_force_ssl` / `require_secure_transport` detection for connection encryption | Encryption at rest without TLS in transit is half the picture; consultants always check both | MEDIUM | Requires `describe_db_parameters` for the parameter group; `rds.force_ssl=1` for PostgreSQL, `require_secure_transport=ON` for MySQL; adds API call per instance |
| `protocol="DATABASE"` CryptoEndpoint + `cloud_scan_json` blob | CBOM integration; reuse existing field | LOW | Same pattern as cloud connectors |
| Self-hosted PostgreSQL: query `pg_settings` for `ssl` and `ssl_ca_file` | Detect TLS enforcement on self-managed Postgres | MEDIUM | Connect via `psycopg2` or `asyncpg`; `SHOW ssl;` — requires DB credentials in config; flag as requiring credentials |
| Self-hosted MySQL: `SHOW VARIABLES LIKE 'have_ssl'` and `require_secure_transport` | TLS posture for self-managed MySQL | MEDIUM | Connect via `pymysql`; `have_ssl=DISABLED` is a finding; requires DB credentials |

### Differentiators: Database Encryption Detection

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Detect tablespace-level encryption in PostgreSQL (pgcrypto, TDE via pg_tde extension) | Enterprise PostgreSQL sometimes uses application-level or extension-level encryption — distinct from OS-level | HIGH | `pg_tde` extension is new (2024); not universally deployed; query `pg_extension` table; low enterprise prevalence currently |
| AWS Aurora serverless encryption detection | Aurora serverless v2 has slightly different encryption behavior | LOW | Same API fields; `StorageEncrypted` applies; add `EngineMode=serverless` to report metadata |
| Cross-reference RDS KMS key with KMS scan findings | Show which KMS key (already in CBOM from KMS scan) protects which RDS instance | MEDIUM | Post-scan enrichment step; requires matching `KmsKeyId` ARNs |
| Azure SQL encryption detection — TDE status via Azure SQL API | Azure SQL uses TDE with either service-managed or customer-managed key | MEDIUM | `azure-mgmt-sql` client; `TransparentDataEncryption.status` field; extends existing Azure connector |

### Anti-Features: Database Encryption Detection

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Read database schema / data samples | "Verify what's actually encrypted" | Accessing business data is out of scope; legal risk; agentless model violation | Detection is posture only; note limitation in report |
| Oracle DB encryption detection | More complete coverage | Requires Oracle JDBC driver; proprietary protocol; very different client library | Out of scope v4.3; document explicitly |
| MySQL Enterprise Audit plugin detection | Seems thorough | Requires auth + SUPER privilege; out of agentless model for self-hosted | Flag as manual verification needed for self-hosted |

---

## Feature 3: Object Storage Audit

### What It Does

Audits encryption configuration for object storage buckets across AWS S3, Azure Blob Storage,
and GCS. Detects the encryption method (platform-managed vs customer-managed key), public
access settings, and Object Lock status. This is a policy-read scanner — no object data is
accessed.

### Key Findings Consultants Need

S3/Blob/GCS buckets are the most commonly misconfigured data-at-rest surface. Since January 2023,
S3 encrypts all new objects with SSE-S3 by default, so "encryption exists" is no longer the
primary finding — the primary finding is now "what kind of encryption and who controls the key."
For regulated workloads (HIPAA, FedRAMP, PCI-DSS), SSE-KMS with a customer-managed key is
required over SSE-S3.

### Table Stakes: Object Storage Audit

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| AWS S3: enumerate all buckets in account, read `get_bucket_encryption` | Core finding: SSE-S3 vs SSE-KMS (and which KMS key) vs no encryption config | LOW | `s3.list_buckets()` + `s3.get_bucket_encryption(Bucket=name)`; `ServerSideEncryptionRule.ApplyServerSideEncryptionByDefault.SSEAlgorithm` = `aws:kms` (CMK preferred) vs `AES256` (SSE-S3, AWS-managed) |
| AWS S3: `get_public_access_block` — detect buckets with public access not blocked | Public buckets are a critical finding regardless of encryption; composite posture | LOW | `BlockPublicAcls`, `BlockPublicPolicy`, `IgnorePublicAcls`, `RestrictPublicBuckets` — all 4 must be True |
| AWS S3: detect SSE-KMS key ARN — identify CMK vs AWS-managed key (`aws/s3`) | CMK vs AWS-managed key distinction is the primary compliance finding for regulated workloads | LOW | `KMSMasterKeyID` in encryption response; `alias/aws/s3` = AWS-managed, custom ARN = CMK |
| AWS S3: Object Lock status — COMPLIANCE vs GOVERNANCE vs disabled | WORM compliance requirement in financial/healthcare; consultants check this for retention compliance | LOW | `s3.get_object_lock_configuration(Bucket=name)`; enabled/disabled + mode |
| GCS: enumerate buckets in project, read `bucket.default_kms_key_name` | GMEK vs CMEK detection; equivalent to S3 SSE-S3 vs SSE-KMS distinction | LOW | `google-cloud-storage` client; already enumerated in GCP connector; share scan results |
| GCS: uniform bucket-level access (public access prevention) | GCS public exposure equivalent of S3 public access block | LOW | `Bucket.iam_configuration.public_access_prevention` = `enforced` vs `inherited` |
| Azure Blob: list storage accounts, read encryption config — `StorageAccountProperties.encryption` | Azure Blob uses AES-256 always; the finding is whether it uses Microsoft-managed vs customer-managed key | MEDIUM | `azure-mgmt-storage` client; `Encryption.key_source` = `Microsoft.Storage` (platform) vs `Microsoft.Keyvault` (CMK); `key_vault_properties.key_name` for CMK |
| Azure Blob: `enable_https_traffic_only` flag — reject HTTP | Azure Blob equivalent of S3 secure transport; consultants always check | LOW | `StorageAccountProperties.enable_https_traffic_only` = True/False |
| `protocol="OBJECT_STORAGE"` CryptoEndpoint; `cloud_scan_json` blob | CBOM integration | LOW | Reuse existing field; `host` = bucket ARN or resource name |

### Differentiators: Object Storage Audit

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| S3 bucket policy check — detect `"Effect": "Allow", "Principal": "*"` (public policy) | Public access block can be bypassed by a bucket policy with explicit Allow; double-check | MEDIUM | `s3.get_bucket_policy(Bucket=name)`; parse JSON for `Principal: *`; common gotcha |
| S3 MFA Delete status | MFA Delete prevents accidental or malicious deletion of versioned objects; enterprise compliance | LOW | `s3.get_bucket_versioning(Bucket=name)`; `MFADelete=Enabled/Disabled` |
| GCS retention policy detection | Equivalent to S3 Object Lock for GCS | LOW | `Bucket.retention_policy`; `is_locked` boolean |
| Cross-surface finding: S3 bucket + no KMS key in KMS scan | Bucket uses CMK but KMS scan didn't find that key — key may be in different account | MEDIUM | Post-scan enrichment; requires ARN matching |

### Anti-Features: Object Storage Audit

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Object-level encryption verification (sample object reads) | "Actually verify the data is encrypted" | Reads business data; agentless model violation; legal risk | Policy-level detection is sufficient; note this in report |
| Azure Data Lake Storage Gen2 audit | Broader Azure coverage | Different API surface; ADLS Gen2 inherits storage account encryption; overlap with Blob audit | Same storage account API covers it; no separate implementation needed |
| List all bucket contents / object inventory | "Complete" audit | Volume can be millions of objects; timeout risk; data exposure | Never enumerate objects; only bucket-level policy |

---

## Feature 4: Kubernetes Secrets Inspection

### What It Does

Detects whether Kubernetes etcd is configured with encryption at rest via `EncryptionConfiguration`,
identifies the encryption provider in use (identity/none vs aescbc vs aesgcm vs secretbox vs kms),
and enumerates Secret types to surface high-value secrets that should be encrypted
(service account tokens, TLS certs, docker registry credentials). No secret values are read.

### Key Context

By default, Kubernetes Secrets are stored in etcd as Base64-encoded plaintext — not encrypted.
This is the most commonly missed data-at-rest gap in Kubernetes security reviews. The finding
"Secrets not encrypted in etcd" is HIGH severity and found in the majority of self-managed
clusters. Managed Kubernetes (GKE, EKS, AKS) has varying defaults — GKE encrypts secrets by
default with CMEK optional; EKS provides optional envelope encryption; AKS offers optional
etcd encryption.

### Table Stakes: K8s Secrets Inspection

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Detect `EncryptionConfiguration` on kube-apiserver — provider != identity | Core finding: is etcd encryption enabled at all? | MEDIUM | Agentless path: check `kubectl get apiserver` or read kube-apiserver pod spec `--encryption-provider-config` flag; for managed clusters, use cloud API (EKS: `describe_cluster.encryptionConfig`; GKE: `cluster.databaseEncryption`; AKS: `ManagedCluster.encryptionAtRestWithCustomerKey`) |
| Identify encryption provider: `identity` (none) vs `aescbc` vs `aesgcm` vs `secretbox` vs `kms` | Provider determines the actual encryption strength | LOW | Static mapping: `identity` = CRITICAL (no encryption); `aescbc` = ADEQUATE (AES-256-CBC, quantum-adequate); `aesgcm` = ADEQUATE (AES-256-GCM, quantum-adequate + authenticated); `secretbox` = ADEQUATE (XSalsa20-Poly1305); `kms` = STRONG (delegated to external KMS) |
| AWS EKS envelope encryption: `describe_cluster` `encryptionConfig` | EKS does not enable envelope encryption by default; finding when absent | LOW | `eks_client.describe_cluster(name=cluster_name)`; `cluster.encryptionConfig` — empty list = not enabled; HIGH finding |
| GKE database encryption: `cluster.databaseEncryption.state` | GKE `DECRYPTED` state = application-layer encryption not enabled | LOW | Already enumerating GCS/KMS in GCP connector; add `container_v1.ClusterManagerClient().get_cluster()` call; `DECRYPTED` = finding |
| AKS encryption at rest: `ManagedCluster.encryption_at_rest_with_customer_key` | AKS uses platform encryption by default; CMK encryption is customer responsibility | MEDIUM | `azure-mgmt-containerservice`; check `encryptionAtRestWithCustomerKey.keyVaultProperties` presence |
| Enumerate Secret types in cluster — count by type | Show volume of sensitive secrets at risk if etcd unencrypted | MEDIUM | `kubernetes` Python client (`v1.list_secret_for_all_namespaces()`); count by `secret.type`; types: `kubernetes.io/tls`, `kubernetes.io/service-account-token`, `kubernetes.io/dockerconfigjson` — do NOT read `.data` values |
| `protocol="K8S"` CryptoEndpoint; `cloud_scan_json` blob | CBOM integration | LOW | host = cluster endpoint; service_detail = "K8S_SECRETS_ENCRYPTION" |
| Graceful fallback: kubeconfig-based auth with clear error if no kubeconfig | K8s connectivity is environment-dependent | LOW | `kubernetes` Python client reads `~/.kube/config` by default; catch `ConfigException`; log helpful message |

### Differentiators: K8s Secrets Inspection

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| RBAC audit: who can `get secrets` across namespaces | Encryption at rest is worthless if any pod can read secrets via RBAC; shows "effective protection" | HIGH | `v1.list_cluster_role_binding()` + policy analysis; significant complexity; separate feature |
| Detect Sealed Secrets (Bitnami) or External Secrets Operator | Shows whether org uses GitOps-safe secret management (preferred over native Secrets) | MEDIUM | Check for `SealedSecret` CRD or `ExternalSecret` CRD in cluster; `kubectl get crd` |
| Audit Secret TTL / rotation via annotation patterns | Long-lived secrets are a risk even when encrypted | MEDIUM | Annotation conventions vary by org; not standardized |

### Anti-Features: K8s Secrets Inspection

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Read secret values (`.data` fields) | "Verify what's actually there" | Reads credentials/tokens; hard agentless model violation; legal risk | Count secret types only; never read `.data` |
| Full etcd direct connection audit | Most thorough | Requires etcd client cert; etcd is not exposed in managed clusters; complex setup | Use kube-apiserver API; it's the correct abstraction layer |
| Kubernetes config map audit | Config maps sometimes hold sensitive data | Config maps are not encrypted even with EncryptionConfiguration unless explicitly added; out of scope | Note in report: check if sensitive data is in ConfigMaps |

---

## Feature 5: HashiCorp Vault Connector

### What It Does

Connects to a HashiCorp Vault instance via its HTTP API, enumerates transit key specs
(algorithm types and rotation status), PKI mount CA certificate algorithms, and auth method
configuration. Uses the Vault token from environment or config — read-only API calls only.
Vault is the most common enterprise key management and PKI system outside of cloud KMS.

### Key Vault API Facts (Verified Against Official Docs)

Transit key types supported by Vault (from official docs, current):
`aes256-gcm96`, `chacha20-poly1305`, `ed25519`, `ecdsa-p256`, `ecdsa-p384`, `ecdsa-p521`,
`rsa-2048`, `rsa-3072`, `rsa-4096`, `ml-dsa` (experimental PQC), `slh-dsa` (experimental PQC).
All classical asymmetric types (RSA, ECDSA) are quantum-vulnerable via Shor's algorithm.

### Table Stakes: HashiCorp Vault Connector

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| List transit engine mounts — `GET /v1/sys/mounts` | Discover all mounted secret engines; transit and PKI mounts are the primary crypto surfaces | LOW | `hvac` Python client or raw `requests`; `sys/mounts` returns all engine paths + types |
| Enumerate transit keys per mount — `GET /v1/<mount>/keys` | Transit keys are Vault's encryption-as-a-service resource; key type determines quantum posture | MEDIUM | `LIST /v1/<transit_mount>/keys`; then `GET /v1/<transit_mount>/keys/<key_name>` for each key; `type` field maps to algorithm |
| Map transit key type → (algorithm, key_size) | Without this, `rsa-2048` is just a string | LOW | Static map: `rsa-2048` → (RSA, 2048), `ecdsa-p256` → (ECDSA, 256), `aes256-gcm96` → (AES, 256), `ml-dsa` → (ML-DSA, 0); 12 entries covers all types |
| Detect transit key rotation status — `min_decryption_version` vs `latest_version` | Keys not rotated in a long time are a finding; gap between min_decryption and latest = many old key versions still active | LOW | `min_decryption_version`, `latest_version`, `deletion_allowed` fields from key detail; long gap = audit finding |
| PKI mount CA cert algorithm — `GET /v1/<pki_mount>/ca/pem` | PKI mount is the internal CA; its certificate algorithm (RSA vs ECDSA) is a primary quantum finding | MEDIUM | Fetch CA PEM; parse with `cryptography` lib (already in stack); extract `cert_pubkey_alg`, `cert_pubkey_size`, `cert_not_after` |
| List auth methods — `GET /v1/sys/auth` | Auth method audit: token, approle, kubernetes, ldap, github — shows what identity methods are in use | LOW | `sys/auth` response; flag deprecated methods (`userpass` without MFA, `token` root token usage) |
| Detect root token in use (policy audit) | Root token active = CRITICAL; root should be revoked after setup | MEDIUM | Check `token_policies` on current token; query `sys/auth/token/tune`; more accurately detected via audit log analysis |
| `protocol="VAULT"` CryptoEndpoint; `cloud_scan_json` blob | CBOM integration | LOW | host = vault_addr; one CryptoEndpoint per transit key |
| Graceful degradation when Vault unreachable or token invalid | Network/auth failures must not crash scan | LOW | `hvac` connection error handling; log + skip; token stored in config |

### Differentiators: HashiCorp Vault Connector

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Transit key `exportable` flag detection | Exportable transit keys undermine the key-never-leaves-Vault security model | LOW | `exportable` boolean in key detail; flag as finding if True |
| PKI mount intermediate CA vs root CA detection | Root CA in Vault vs intermediate CA is an architectural finding | LOW | Check if CA cert is self-signed (issuer == subject); self-signed = root CA |
| PKI certificate TTL / max TTL audit | Very long-lived internal certs are a rotation hygiene finding | LOW | `GET /v1/<pki_mount>/config/ca` or role config; `max_ttl` field |
| Vault Enterprise namespace enumeration | Enterprise Vault uses namespaces; top-level scan misses them | HIGH | Requires Enterprise license; not universally applicable; defer |
| `ml-dsa` / `slh-dsa` key detection as PQC-ready | Show positive finding: org already has PQC keys in Vault | LOW | These key types are in official Vault docs as experimental; classify as QUANTUM_SAFE in CBOM |

### Anti-Features: HashiCorp Vault Connector

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Read secret values from KV mounts | "Complete" audit | Reads credentials; hard agentless model violation | KV mounts are explicitly out of scope; audit crypto surfaces only (transit, PKI, auth) |
| Vault audit log analysis | More accurate policy finding | Requires audit log backend access (file/syslog/socket); out of agentless model | Flag as "manual audit recommended" in report |
| Vault unsealing / HA status | Operational concern | Not a crypto posture finding | Out of scope |

---

## Feature 6: Trend Analysis Across Scan Sessions

### What It Does

Compares the current scan's readiness score and findings against the most recent previous scan
for the same target set. Produces a delta report: score delta (+/-), new findings introduced,
findings resolved since last scan, and hosts whose posture degraded. This is a session-to-session
diff, not time-series analytics.

### Key Context

No existing `ScanSession` table exists — `scanned_at` on `CryptoEndpoint` is the only session
marker. Trend analysis requires a new lightweight session-level metadata record in SQLite.
The `session_start` value propagated by `run_scan.py` (Phase 24 fix) is the natural session key.
The intelligence layer already computes `ScoreResult` per scan — delta is `current.score - previous.score`.

### Table Stakes: Trend Analysis

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| New `ScanSession` table — id, session_start datetime, target_set hash, score, rating, endpoint_count | Without a session anchor, diff is impossible | LOW | SQLite additive table; `session_start` is the FK to `crypto_endpoints.scanned_at`; store score + rating snapshot per session |
| Score delta — current score minus previous session score | Primary trend metric; consultants use this to demonstrate improvement to clients | LOW | `current_score - previous_score`; +5 = "improved"; -3 = "regressed"; displayed on exec summary |
| New findings since last scan — findings in current session not in previous | Show what new risks appeared | MEDIUM | Compare finding fingerprints (host + protocol + finding_type) across sessions; `LEFT JOIN` on session WHERE previous has no match |
| Resolved findings since last scan — findings in previous session not in current | Show what was fixed; positive reinforcement for remediation | MEDIUM | Inverse of above; finding present in previous but absent in current |
| Degraded hosts — hosts whose individual score/risk worsened | Zoom in on which hosts drove score changes | MEDIUM | Per-host comparison across sessions; requires per-host severity roll-up |
| Report output: delta section in HTML/PDF report | Consultants present this in slide decks; it must appear in the deliverable | MEDIUM | New section in `quirk/reports/` renderer; only displayed when 2+ sessions exist for target set |
| Dashboard: trend tab or score delta badge on exec summary | Visual delta for the live dashboard session | MEDIUM | Score delta badge (+N/-N) on existing exec summary; minimal viable UI |
| CLI: `quirk compare` or `--delta` flag to trigger comparison | User-facing entry point | LOW | Compare most recent two sessions by default; `--session-id` for specific comparison |

### Differentiators: Trend Analysis

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Per-surface delta breakdown — which surface improved/worsened (TLS vs KMS vs Database) | Granular delta for consulting deliverables | MEDIUM | Requires surface-tagged findings; shows whether remediation efforts on TLS translated to score improvement |
| Multi-session trend chart in dashboard | Visual posture trajectory over N scans | HIGH | Requires chart component; N data points in `ScanSession` table; defer until 3+ scans typically exist in prod |
| Export delta report as standalone PDF | Client-ready remediation progress report | MEDIUM | Reuse existing PDF export pipeline; add delta section; triggered by `quirk report --delta` |
| Automated regression alert — score drops more than threshold | Proactive posture monitoring | HIGH | Continuous monitoring; SaaS milestone territory; not CLI-appropriate |

### Anti-Features: Trend Analysis

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Time-series analytics / aggregation over many sessions | "Historical trend" | Requires substantial data volume to be useful; complex UI; early consultants have 2-3 scans at most | Session-to-session diff is the right scope for v4.3; multi-session chart is v4.4+ |
| Compare different target sets | Cross-client benchmarking | Different target sets are not comparable; score depends on target count and surface mix | Comparison is within the same target set only; document this constraint |
| Automatic scan scheduling for trend | "Continuous monitoring" | Requires daemon/scheduler; SaaS milestone; breaks CLI delivery model | Document: run `quirk scan` periodically; delta is automatic when sessions accumulate |

---

## Feature Dependencies

```
[GCP Connector]
    └──reuses──> aws_connector.py pattern (same CryptoEndpoint + cloud_scan_json)
    └──reuses──> GCP connector output in GCS Object Storage Audit (share scan session)
    └──requires──> google-cloud-kms, google-cloud-storage, google-cloud-sqladmin (new pip deps)
    └──requires──> GCP_ALGORITHM_MAP (new static map; mirrors KMS_KEY_SPEC_MAP)

[Database Encryption Detection — AWS RDS path]
    └──reuses──> boto3 session from aws_connector.py (shared AWS session)
    └──reuses──> KmsKeyId cross-reference with existing KMS scan findings
    └──requires──> psycopg2 or pymysql for self-hosted path (optional dep; credential-gated)

[Object Storage Audit — AWS S3]
    └──reuses──> boto3 session from aws_connector.py
    └──enriches──> KMS scan (cross-reference S3 SSE-KMS key ARN with KMS key list)

[Object Storage Audit — GCS]
    └──reuses──> GCS bucket enumeration already done in GCP Connector
    └──note──> GCP Connector and Object Storage Audit must share scan data, not double-enumerate

[K8s Secrets Inspection — managed clusters]
    └──requires──> kubernetes Python client (new pip dep)
    └──reuses──> EKS cluster list via boto3 (aws_connector.py already has boto3 session)
    └──reuses──> GKE cluster via google-cloud-container (add to GCP connector extras)

[HashiCorp Vault Connector]
    └──requires──> hvac Python client (new pip dep) OR raw requests (already in stack)
    └──enriches──> PKI mount CA cert → reuse cryptography lib cert parsing (already in stack)
    └──requires──> VAULT_ADDR + VAULT_TOKEN in config (new config section)

[Trend Analysis]
    └──requires──> new ScanSession SQLite table (additive; no migration)
    └──requires──> session_start propagation from run_scan.py (already done in Phase 24)
    └──requires──> all scanners complete before session snapshot is written
    └──enhances──> existing HTML/PDF report (new delta section)
    └──enhances──> existing dashboard exec summary (score delta badge)
    └──blocks──> nothing else; purely additive read-side feature
```

### Dependency Notes

- **GCP shares session with Object Storage:** The GCS bucket enumeration in the GCP Connector produces the same data needed for Object Storage Audit. Implementation must pass bucket objects into both the GCP connector findings AND the object storage audit findings — do not enumerate GCS twice.
- **AWS session sharing:** RDS encryption, S3 audit, and EKS cluster checks all use boto3. They should share the same `boto3.Session` established in `aws_connector.py` rather than creating independent sessions.
- **Trend analysis is last in phase order:** It requires completed scan data; it is never a blocker for other features.
- **`hvac` vs raw requests:** `hvac` is the official HashiCorp Python client; it is pip-installable and actively maintained. Raw `requests` is an alternative but `hvac` handles token refresh and error codes correctly. Use `hvac` with optional-import graceful degradation.

---

## MVP Definition

### Launch With (v4.3)

Minimum viable set — what the milestone ships:

- [ ] GCP Connector: Cloud KMS key enumeration + algorithm map + Cloud SQL TLS mode + GCS bucket CMEK detection
- [ ] Database Encryption: AWS RDS `StorageEncrypted` + `StorageEncryptionType` + `KmsKeyId` + parameter group `rds.force_ssl` detection
- [ ] Object Storage: S3 encryption policy (SSE-S3 vs SSE-KMS vs CMK) + public access block; GCS bucket CMEK; Azure Blob key_source
- [ ] K8s Secrets: EKS `encryptionConfig` detection; GKE `databaseEncryption.state`; `kubernetes` client secret type count for self-managed clusters
- [ ] HashiCorp Vault: transit key enumeration + type map; PKI mount CA cert extraction; auth method list
- [ ] Trend Analysis: `ScanSession` table + score delta + new/resolved findings diff + HTML/PDF delta section

### Add After Validation (v4.3.x)

- [ ] Azure SQL TDE detection — trigger: consultant with Azure-heavy client
- [ ] K8s RBAC "who can read secrets" audit — trigger: client asks for deeper K8s review
- [ ] Vault transit key `exportable` flag — trigger: consultant UAT finds Vault keys marked exportable
- [ ] Multi-session trend chart in dashboard — trigger: consultants accumulate 3+ scan sessions in field use

### Future Consideration (v4.4+)

- [ ] BigQuery CMEK audit — defer until GCP connector is validated in field
- [ ] PostgreSQL TDE / pg_tde extension detection — defer until pg_tde has more adoption
- [ ] Oracle DB encryption — explicit out-of-scope for v1; requires JDBC/cx_Oracle
- [ ] Trend analysis across different target sets / benchmarking — SaaS milestone feature
- [ ] Vault Enterprise namespace enumeration — requires Enterprise license; low field frequency

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| AWS RDS encryption detection | HIGH | LOW | P1 |
| AWS S3 encryption audit | HIGH | LOW | P1 |
| GCP KMS key enumeration | HIGH | MEDIUM | P1 |
| GCS bucket CMEK detection | HIGH | LOW | P1 (shares GCP Connector work) |
| EKS/GKE etcd encryption detection | HIGH | LOW | P1 |
| Trend analysis — score delta | HIGH | MEDIUM | P1 |
| HashiCorp Vault transit key audit | HIGH | MEDIUM | P1 |
| Vault PKI CA cert extraction | HIGH | MEDIUM | P1 |
| Cloud SQL TLS enforcement mode | MEDIUM | MEDIUM | P1 |
| Azure Blob encryption key source | MEDIUM | MEDIUM | P1 |
| Trend — new/resolved findings diff | MEDIUM | MEDIUM | P2 |
| K8s secret type count (self-managed) | MEDIUM | MEDIUM | P2 |
| S3 Object Lock / MFA Delete | MEDIUM | LOW | P2 |
| Vault auth method list | MEDIUM | LOW | P2 |
| Trend dashboard delta badge | MEDIUM | LOW | P2 |
| GCP KMS protection level (HSM vs SW) | MEDIUM | LOW | P2 |
| S3 bucket policy public-Allow check | MEDIUM | MEDIUM | P2 |
| Vault transit exportable flag | LOW | LOW | P3 |
| Azure SQL TDE detection | LOW | MEDIUM | P3 |
| PostgreSQL self-hosted ssl detection | LOW | MEDIUM | P3 |
| AKS CMK encryption detection | LOW | MEDIUM | P3 |

**Priority key:**
- P1: Ships in v4.3 milestone core
- P2: Ships in v4.3 milestone if time permits; else v4.3.x
- P3: v4.3.x or v4.4

---

## Consultant-Value Framing Per Finding Type

Understanding which findings generate billable value drives phase ordering.

| Finding | Why Actionable | Client Impact | Remediation Clarity |
|---------|---------------|---------------|---------------------|
| RDS `StorageEncrypted=False` | Direct HIPAA/PCI-DSS gap; enable flag + snapshot re-encrypt | HIGH | HIGH — one RDS setting |
| RDS using AWS-managed key vs CMK | Compliance distinction for regulated workloads; CMK required for some certifications | HIGH | HIGH — change KMS key association |
| S3 SSE-S3 (AES256) vs SSE-KMS with CMK | CMK required for FedRAMP High, HIPAA-eligible | HIGH | HIGH — update bucket default encryption |
| S3 public access block not fully set | Data exfiltration risk regardless of encryption | CRITICAL | HIGH — 4 boolean flags |
| K8s etcd encryption not enabled (EKS/GKE) | Secrets readable by anyone with etcd access | HIGH | MEDIUM — API server flag + key provider setup |
| GCS bucket GMEK (no CMEK) | Compliance gap for GCP workloads requiring customer control | MEDIUM | MEDIUM — assign Cloud KMS key to bucket |
| Vault transit key RSA-2048 (quantum-vulnerable) | Forward-looking PQC finding; migration to ml-dsa when finalized | MEDIUM | LOW — migration path not mature |
| Vault transit key not rotated | Key hygiene finding | MEDIUM | HIGH — one Vault CLI command |
| Vault PKI CA with RSA-2048 | Internal CA quantum posture; most likely finding in enterprise | HIGH | LOW — CA replacement is multi-quarter project |
| Cloud SQL TLS not enforced | In-transit risk that compounds at-rest findings | MEDIUM | HIGH — one Cloud SQL settings change |
| GCP KMS key SOFTWARE protection level | Compliance finding for HSM requirements | MEDIUM | MEDIUM — key migration required |
| Score delta negative (posture degraded) | Client accountability metric; shows what changed between engagements | HIGH | HIGH — new findings list drives remediation |

---

## New Dependencies for v4.3

| Library | Feature | Status | Extras Group |
|---------|---------|--------|--------------|
| `google-cloud-kms` | GCP Connector (KMS) | New | `[gcp]` |
| `google-cloud-storage` | GCP Connector + Object Storage | New | `[gcp]` |
| `google-cloud-sqladmin` | GCP Connector (Cloud SQL) | New | `[gcp]` |
| `hvac` | HashiCorp Vault Connector | New | `[vault]` |
| `kubernetes` | K8s Secrets Inspection | New | `[k8s]` |
| `psycopg2-binary` | Self-hosted PostgreSQL detection | New, credential-gated | `[database]` |
| `pymysql` | Self-hosted MySQL detection | New, credential-gated | `[database]` |

All new dependencies are pip-installable. Following the existing `[identity]` extras group pattern,
v4.3 adds `[gcp]`, `[vault]`, `[k8s]`, and optionally `[database]` to `pyproject.toml`.
Core install (`pip install quirk`) gains no new required dependencies.

---

## Sources

- [Google Cloud KMS — Key purposes and algorithms](https://docs.cloud.google.com/kms/docs/algorithms)
- [Google Cloud KMS — Deep dive security](https://cloud.google.com/docs/security/key-management-deep-dive)
- [Cloud Custodian — GCP KMS cryptokey audit](https://cloudcustodian.io/docs/gcp/examples/kms-cryptokey.html)
- [GCP Cloud SQL — Configure SSL/TLS certificates](https://cloud.google.com/sql/docs/postgres/configure-ssl-instance)
- [GCP Cloud Storage — Customer-managed encryption keys](https://cloud.google.com/storage/docs/encryption/customer-managed-keys)
- [AWS RDS — Encrypting Amazon RDS resources](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Overview.Encryption.html)
- [AWS RDS StorageEncryptionType field (2025 Aurora update)](https://docs.datadoghq.com/security/default_rules/aws-rds-cluster-rds-clusters-should-have-encryption-at-rest-enabled)
- [AWS S3 — Using SSE-KMS](https://docs.aws.amazon.com/AmazonS3/latest/userguide/UsingKMSEncryption.html)
- [AWS S3 — Auditing server-side encryption methods](https://aws.amazon.com/blogs/storage/auditing-amazon-s3-server-side-encryption-methods-for-object-uploads/)
- [Kubernetes — Encrypting Confidential Data at Rest](https://kubernetes.io/docs/tasks/administer-cluster/encrypt-data/)
- [Kubernetes — Using a KMS provider for data encryption](https://kubernetes.io/docs/tasks/administer-cluster/kms-provider/)
- [HashiCorp Vault — Transit secrets engine](https://developer.hashicorp.com/vault/docs/secrets/transit)
- [HashiCorp Vault — PKI secrets engine considerations](https://developer.hashicorp.com/vault/docs/secrets/pki/considerations)
- [HashiCorp Vault — Transit API](https://developer.hashicorp.com/vault/api-docs/secret/transit)
- [SecurityScorecard — Track security progress with Company Trends Report](https://support.securityscorecard.com/hc/en-us/articles/4403014788379-Track-security-progress-with-Company-Trends-Report)
- [Post-Quantum Cryptography 2025: The Enterprise Readiness Gap](https://www.cio.inc/post-quantum-cryptography-2025-enterprise-readiness-gap-a-27367)
- [Microsoft cloud security benchmark — Data protection](https://learn.microsoft.com/en-us/security/benchmark/azure/mcsb-data-protection)
- [Percona — Testing encryption at rest in RDS](https://www.percona.com/blog/whats-best-way-to-enable-and-test-encryption-at-rest-in-rds/)
- [Kubernetes Security Checklist 2025](https://atmosly.com/blog/kubernetes-security-checklist-50-best-practices-2025-part-ii)

---

*Feature research for: QU.I.R.K. v4.3 Data at Rest milestone — GCP connector, database encryption, object storage audit, K8s secrets, HashiCorp Vault, trend analysis*
*Researched: 2026-04-24*
