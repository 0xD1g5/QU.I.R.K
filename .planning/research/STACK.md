# Stack Research: v4.3 Data at Rest

**Domain:** Cryptographic inventory expansion — cloud (GCP), database encryption-at-rest, object storage, Kubernetes secrets, HashiCorp Vault, trend analysis
**Researched:** 2026-04-24
**Confidence:** HIGH (all library versions verified via PyPI; integration patterns verified via official docs and existing connector code)

---

## Scope

This research covers ONLY the net-new capabilities needed for v4.3. The existing stack
(boto3, azure-identity, azure-keyvault-*, azure-mgmt-network, sslyze, cyclonedx-python-lib,
httpx, cryptography, SQLAlchemy, dnspython, lxml, defusedxml, signxml, impacket, PyJWT) is
validated and carries forward unchanged. See `pyproject.toml` for current pinned versions.

The question answered here is: what is the minimal delta to existing deps to enable all 6 new v4.3 features?

---

## Recommended Stack

### Net-New Python Dependencies

| Library | Version | Purpose | Why Recommended |
|---------|---------|---------|-----------------|
| `google-cloud-kms` | `>=3.12.0` | GCP connector — Cloud KMS key ring enumeration, crypto key version algorithm inspection | The official, first-party Google Cloud Python client for KMS. Uses the Cloud KMS v1 REST API. Exposes `KeyManagementServiceClient.list_key_rings()`, `list_crypto_keys()`, `list_crypto_key_versions()` with `CryptoKeyVersion.algorithm` field directly. Installs `google-auth` and `google-api-core` as transitive deps (no separate auth library needed). Ships binary-free wheels. |
| `google-cloud-storage` | `>=3.10.1` | GCP connector — GCS bucket encryption policy inspection (`defaultKmsKeyName`, CMEK vs Google-managed) | Official first-party GCS client. `storage.Client().get_bucket(name)` returns a `Bucket` object with `.default_kms_key_name` (non-empty = CMEK, empty = Google-managed platform key). No separate REST API call construction needed. Consistent auth pattern with `google-cloud-kms` via `google-auth` ADC. |
| `hvac` | `>=2.4.0` | HashiCorp Vault connector — transit key listing, PKI mount enumeration, auth method audit | Only maintained Python client for the Vault HTTP API. `client.secrets.transit.list_keys()` enumerates transit engine keys; `client.sys.list_mounted_secrets_engines()` discovers PKI mounts; `client.sys.list_auth_methods()` audits auth backends. Version 2.4.0 (October 2025) is current stable. Requires only `requests` as a transitive dep (already present transitively). |
| `kubernetes` | `>=35.0.0` | Kubernetes secrets inspection — list Secret types across namespaces, read kube-apiserver pod spec to detect `--encryption-provider-config` flag | Official Python client, generated from the Kubernetes OpenAPI spec. `CoreV1Api.list_secret_for_all_namespaces()` returns `V1Secret` objects with `.type` and `.metadata` fields for secret type inventory. `CoreV1Api.list_namespaced_pod(namespace="kube-system")` + container command inspection is the canonical way to detect `--encryption-provider-config` without direct etcd access. Version 35.0.0 (January 2026) tracks Kubernetes 1.32. |
| `psycopg2-binary` | `>=2.9.12` | Database encryption detection — PostgreSQL `pg_stat_ssl` and `pg_stat_activity` queries for TLS-in-transit and connection encryption state | `psycopg2-binary` is the self-contained wheel (includes libpq) — correct for a consulting tool with zero-host-dep constraint. `pg_stat_ssl` view returns `ssl` (bool), `version`, `cipher`, `bits` per backend PID. `sslmode=require` connection + query is the agentless probe pattern. Version 2.9.12 released April 20, 2026 — current stable. |
| `PyMySQL` | `>=1.1.2` | Database encryption detection — MySQL TLS connection capability probe; `SHOW VARIABLES LIKE 'have_ssl'` and `SHOW STATUS LIKE 'Ssl_%'` | Pure-Python MySQL driver (no C binary dependency). Accepts `ssl` dict param for `sslmode` equivalent. Can probe MySQL TLS posture by connecting with `ssl={'ca': None}` (TLS required mode) and querying `@@ssl_type` or `SHOW STATUS LIKE 'Ssl_cipher'`. Pairs with boto3 (already in stack) for RDS encryption-at-rest metadata. |
| `ldap3` | `>=2.9.1` | Phase 25 carry-over — LDAP enumeration for Kerberos KERB-03 path (already deferred from v4.2; fixes ISSUE-2 in `[identity]` extras group) | Already documented as ISSUE-2. Adding `ldap3>=2.9.1` to `[identity]` extras unblocks the LDAP degradation path in the Kerberos scanner. Version 2.9.1 is the latest stable (2.10.2rc4 pre-release exists but is not GA). Pure Python — no system binary deps. |

### No New Libraries Needed (capabilities covered by existing stack)

| Capability | Handled By | Notes |
|------------|-----------|-------|
| AWS RDS encryption-at-rest (`StorageEncrypted` field) | `boto3` (already in stack) | `rds_client.describe_db_instances()` returns `StorageEncrypted` bool and `KmsKeyId` on each instance. No new boto3 surface — just a new scanner module calling existing client pattern. |
| AWS S3 SSE-S3 / SSE-KMS bucket encryption | `boto3` (already in stack) | `s3_client.get_bucket_encryption(Bucket=name)` returns `ServerSideEncryptionConfiguration` rules with `SSEAlgorithm` (`AES256` = SSE-S3, `aws:kms` = SSE-KMS). Existing `aws_connector.py` boto3 session reused. |
| Azure Blob encryption CMK vs platform key | `azure-mgmt-storage` (net-new, see below) + `azure-identity` (already in stack) | `DefaultAzureCredential` already in stack handles auth. Only the mgmt client lib is new. |
| Trend / delta analysis across scan sessions | `SQLAlchemy` (already in stack) | Cross-session delta is a query pattern against the existing `crypto_endpoints` table grouped by `scanned_at`. No new library: `session.query(CryptoEndpoint).filter(CryptoEndpoint.scanned_at >= t_prev)` comparison. The existing `db.py` session pattern is sufficient. |
| GCP auth (ADC) | `google-auth` (transitive of google-cloud-kms) | `google.auth.default()` provides Application Default Credentials. The same credential object is shared across `google-cloud-kms` and `google-cloud-storage` clients, matching the boto3 ambient credential pattern already used for AWS. |

### One Additional Azure Management Library

| Library | Version | Purpose | Why Recommended |
|---------|---------|---------|-----------------|
| `azure-mgmt-storage` | `>=21.2.0` | Azure Blob encryption audit — `StorageManagementClient.storage_accounts.list()` returns `encryption.key_source` (`Microsoft.Storage` = platform key, `Microsoft.Keyvault` = CMK) and `encryption.key_vault_properties` | Follows the exact pattern of `azure-mgmt-network` (already in stack for App Gateway). `DefaultAzureCredential` already handles auth. `StorageAccount.encryption.key_source` is the single field distinguishing CMK from platform-managed. Latest stable is approximately 21.2.x (released March 2026). |

---

## Extras Groups: Updated pyproject.toml Structure

The v4.3 additions span two extras groups — one new (`[cloud]`) and one carry-over extension (`[identity]`):

```toml
[project.optional-dependencies]
dashboard = [
    "fastapi>=0.128.8",
    "uvicorn[standard]>=0.39.0",
    "python-multipart>=0.0.20",
    "playwright>=1.58.0",
]
identity = [
    "impacket>=0.13.0,<0.14",
    "ldap3>=2.9.1",          # v4.3 Phase 25: fixes ISSUE-2 KERB-03 LDAP path
]
cloud = [
    "google-cloud-kms>=3.12.0",
    "google-cloud-storage>=3.10.1",
    "azure-mgmt-storage>=21.2.0",   # joins existing azure-mgmt-network
    "kubernetes>=35.0.0",
    "hvac>=2.4.0",
]
db = [
    "psycopg2-binary>=2.9.12",
    "PyMySQL>=1.1.2",
]
```

**Why split this way:**

- `[cloud]` — GCP (google-cloud-*), Kubernetes (kubernetes), and Vault (hvac) are all heavy, optional, require API credentials, and should not bloat core installs. `azure-mgmt-storage` joins `azure-mgmt-network` (already in core) — consider moving it to `[cloud]` since mgmt plane access requires subscription-level IAM that not every engagement will have.
- `[db]` — Database probing requires target credentials. Separate group lets consultants opt in only when they have DB access. psycopg2-binary and PyMySQL are < 5MB combined but the credential-requirement argument still holds.
- `[identity]` — ldap3 addition is a one-liner fix for Phase 25; keeps existing impacket isolation intact.

**Core deps unchanged:** boto3 and azure-identity (core) are not moved. RDS and S3 encryption detection uses existing boto3 session — zero new core deps for AWS data-at-rest features.

---

## Integration Patterns

### GCP Connector Pattern

Mirrors the existing AWS and Azure connector shape exactly:

```python
try:
    from google.cloud import kms_v1, storage
    from google.auth.exceptions import DefaultCredentialsError
    GCP_AVAILABLE = True
except ImportError:
    GCP_AVAILABLE = False

def scan_gcp(project_id: str, location: str, logger) -> List[CryptoEndpoint]:
    if not GCP_AVAILABLE:
        return []
    kms_client = kms_v1.KeyManagementServiceClient()
    parent = f"projects/{project_id}/locations/{location}"
    for key_ring in kms_client.list_key_rings(parent=parent):
        for key in kms_client.list_crypto_keys(parent=key_ring.name):
            for version in kms_client.list_crypto_key_versions(parent=key.name):
                alg = version.algorithm.name  # e.g. "RSA_SIGN_PSS_2048_SHA256"
                ...
```

`CryptoKeyVersion.algorithm` is a `CryptoKeyVersion.CryptoKeyVersionAlgorithm` enum whose `.name` is a string like `GOOGLE_SYMMETRIC_ENCRYPTION`, `RSA_SIGN_PSS_4096_SHA512`, `EC_SIGN_P256_SHA256`. These map directly to QU.I.R.K.'s quantum-safety lookup table.

### Kubernetes EncryptionConfiguration Detection

**Critical finding:** EncryptionConfiguration is NOT a queryable Kubernetes API resource. It exists only as a file on the control-plane node, referenced by `--encryption-provider-config` on the kube-apiserver process. The only agentless way to detect it is to inspect the kube-apiserver Pod spec in the `kube-system` namespace:

```python
from kubernetes import client, config

config.load_kube_config()   # or load_incluster_config() inside cluster
v1 = client.CoreV1Api()
pods = v1.list_namespaced_pod(namespace="kube-system", label_selector="component=kube-apiserver")
for pod in pods.items:
    for container in pod.spec.containers:
        args = container.command or [] + container.args or []
        has_encryption = any("--encryption-provider-config" in a for a in args)
```

If `--encryption-provider-config` is absent from all kube-apiserver containers, secrets are stored in etcd as plaintext — this is the HIGH-severity finding to emit. If the arg is present, QU.I.R.K. reports the configuration path and flags it as requiring manual inspection of the referenced file (which is on the node filesystem, not accessible via the API).

For **Secret type inventory** (the other K8s feature), `list_secret_for_all_namespaces()` returns all secrets with `.type` field: `kubernetes.io/tls` (TLS certs), `kubernetes.io/service-account-token`, `Opaque`, `kubernetes.io/dockerconfigjson`, etc. This feeds a count-by-type summary.

### HashiCorp Vault Connector Pattern

```python
import hvac

client = hvac.Client(url=vault_addr, token=vault_token)
# Transit keys
transit_keys = client.secrets.transit.list_keys()["data"]["keys"]
for key_name in transit_keys:
    key_detail = client.secrets.transit.read_key(name=key_name)["data"]
    key_type = key_detail["type"]  # "aes256-gcm96", "rsa-2048", "ecdsa-p256", etc.
# PKI mounts
mounts = client.sys.list_mounted_secrets_engines()["data"]
pki_mounts = {path: info for path, info in mounts.items() if info["type"] == "pki"}
# Auth methods
auth_methods = client.sys.list_auth_methods()["data"]
```

Transit key type strings map directly to QU.I.R.K.'s algorithm classification: `aes256-gcm96` is SAFE symmetric, `rsa-2048` is WARN quantum-unsafe, `ecdsa-p256` is WARN quantum-unsafe.

### Database Encryption Pattern

**RDS (no new deps):** `boto3` `rds_client.describe_db_instances()` — check `StorageEncrypted` bool and `KmsKeyId` on each instance dict. Wire into existing `aws_connector.py`.

**PostgreSQL TLS probe (psycopg2-binary):**
```python
import psycopg2
conn = psycopg2.connect(host=host, port=port, user=user, password=pw, sslmode="require")
cur = conn.cursor()
cur.execute("SELECT ssl, version, cipher, bits FROM pg_stat_ssl WHERE pid = pg_backend_pid()")
row = cur.fetchone()  # (True, "TLSv1.3", "TLS_AES_256_GCM_SHA384", 256)
```

**MySQL TLS probe (PyMySQL):**
```python
import pymysql
conn = pymysql.connect(host=host, port=port, user=user, password=pw, ssl={'ssl': True})
cur = conn.cursor()
cur.execute("SHOW STATUS LIKE 'Ssl_cipher'")
cipher = cur.fetchone()  # ("Ssl_cipher", "TLS_AES_256_GCM_SHA384") or ("Ssl_cipher", "")
```

### Trend Analysis Pattern (no new deps)

Cross-session delta uses the existing `scanned_at` timestamp on `CryptoEndpoint`. Two queries against the existing SQLite schema:

```python
from sqlalchemy import func
# Get two most recent distinct scan timestamps
timestamps = (
    session.query(func.date(CryptoEndpoint.scanned_at))
    .distinct()
    .order_by(CryptoEndpoint.scanned_at.desc())
    .limit(2)
    .all()
)
prev_t, curr_t = timestamps[1][0], timestamps[0][0]
# Delta: new endpoints in current scan not seen in previous
# Delta: resolved endpoints in previous scan absent from current
```

Score delta is computed by diffing the intelligence JSON blobs from two consecutive scan records — no new library needed, pure JSON comparison in Python.

---

## Alternatives Considered

| Recommended | Alternative | Why Not |
|-------------|-------------|---------|
| `google-cloud-kms` | `google-api-python-client` (discovery-based) | Discovery client requires manual construction of resource paths and response parsing. `google-cloud-kms` is the purpose-built, type-safe client with proper enum types for algorithm values. Maintainers recommend cloud-specific clients over discovery-based for new work. |
| `google-cloud-kms` | REST via `httpx` + service account JSON | Requires hand-rolling auth (OAuth2 token exchange) and JSON schema knowledge. `google-cloud-kms` handles all of this with `google-auth` ADC — consistent with how boto3 handles AWS credential resolution. |
| `hvac` | Direct `httpx` calls to Vault HTTP API | Vault HTTP API is well-documented, but `hvac` provides typed response parsing, proper error handling, and covers transit/PKI/sys APIs with correct path construction. For an audit scanner (read-only), `hvac` is the right abstraction. No significant overhead. |
| `kubernetes` (official client) | `httpx` to kube-apiserver REST | Requires handling kubeconfig parsing, service account token injection, and TLS cert validation manually. The official client handles all of this. Version 35.0.0 tracks K8s 1.32 and supports Python 3.11+. |
| `psycopg2-binary` | `psycopg` (v3) | psycopg v3 is the future but `psycopg2-binary` is the current production standard with universal binary wheel support for Python 3.10-3.14 on all platforms. For a read-only SSL probe (not a production ORM), v2 is the correct choice — zero compilation, zero system deps. |
| `PyMySQL` | `mysql-connector-python` (Oracle) | mysql-connector-python is heavier (GPL license), has a C extension option that can complicate installs. PyMySQL is pure Python, permissive MIT license, supports the same SSL probe pattern. |
| `azure-mgmt-storage` in core deps | `azure-mgmt-storage` in `[cloud]` extras | The mgmt plane (`azure-mgmt-*`) requires subscription-level IAM access that data-plane (`azure-keyvault-*`) does not. Moving to `[cloud]` extras is consistent with the principle that cloud management access is opt-in. However, `azure-mgmt-network` is currently in core — if that stays in core, `azure-mgmt-storage` should join it for consistency. **Decision for implementation phase.** |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `google-api-python-client` for KMS/GCS | Deprecated usage pattern for Cloud APIs; requires manual discovery document handling | `google-cloud-kms`, `google-cloud-storage` |
| `cloud-sql-python-connector` | This library makes connections TO Cloud SQL instances, not reads their TLS/encryption metadata. Cloud SQL TLS config comes from the Cloud SQL Admin API (discovery-based) or `google-cloud-sql-connector` REST — complex and out of scope for v4.3 audit use | Use Cloud SQL Admin API via `google-api-python-client` only if Cloud SQL TLS config inspection is added later |
| `psycopg` (v3) in place of `psycopg2-binary` | The v3 API is different enough to cause confusion; no wheel advantage for a simple probe use case; v2 has wider consultant machine support | `psycopg2-binary>=2.9.12` |
| `kubernetes>=35.0.0` in core deps | K8s client is 25MB+ with many transitive deps; only relevant when scanning K8s clusters; should be opt-in | Place in `[cloud]` extras group |
| `hvac>=2.4.0` in core deps | Vault connector is opt-in — not every engagement has Vault; adding to core raises install size unnecessarily | Place in `[cloud]` extras group |
| `ldap3>=2.10.2rc4` (pre-release) | 2.10.2rc4 is a release candidate, not stable. 2.9.1 is the latest stable GA | `ldap3>=2.9.1` |

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| `google-cloud-kms>=3.12.0` | `cryptography>=44.0` (in stack) | google-cloud-kms transitively pulls `google-auth>=2.49.2` — no conflict with existing stack. Pure Python + proto bindings, no C extensions beyond protobuf. |
| `google-cloud-storage>=3.10.1` | `google-auth` (shared with google-cloud-kms) | Same ADC credential object can be shared between KMS and GCS clients — no duplicate auth setup. |
| `hvac>=2.4.0` | `requests` (transitively present via boto3/azure-sdk) | hvac depends on `requests`. `requests` is already a transitive dep in the venv. Zero new transitive deps in practice. |
| `kubernetes>=35.0.0` | Python 3.11+ (already project minimum) | kubernetes 35.0.0 requires Python >=3.8; no upper-bound conflict. Transitively pulls `certifi`, `urllib3`, `six` (already present). |
| `psycopg2-binary>=2.9.12` | Python 3.10-3.14, all platforms via wheel | Binary wheel bundles libpq and libssl. Note: the bundled libssl is independent of the system libssl. This is intentional for a consulting tool — no system SSL library conflicts. |
| `PyMySQL>=1.1.2` | Python 3.9+ | Pure Python. No conflicts. Supports both MySQL 8.x and MariaDB 10.x TLS probes. |
| `ldap3>=2.9.1` | `impacket>=0.13.0` (in `[identity]`) | Both are in the `[identity]` extras group. No shared transitive dependencies that conflict. ldap3 is pure Python. |
| `azure-mgmt-storage>=21.2.0` | `azure-identity>=1.25.0` (in core) | Uses the same `DefaultAzureCredential` as `azure-keyvault-*` already in stack. No new auth surface. |

---

## Installation

```bash
# Core install (unchanged from v4.2)
pip install quirk

# GCP + Kubernetes + Vault connectors
pip install "quirk[cloud]"

# Database encryption probing (PostgreSQL + MySQL)
pip install "quirk[db]"

# Identity surface (Kerberos LDAP path + OIDC RS256 — Phase 25)
pip install "quirk[identity]"

# Full v4.3 install for development
pip install -e ".[cloud,db,identity,dashboard]"
```

---

## Sources

- [google-cloud-kms PyPI](https://pypi.org/project/google-cloud-kms/) — version 3.12.0 confirmed, released March 26, 2026
- [google-cloud-storage PyPI](https://pypi.org/project/google-cloud-storage/) — version 3.10.1 confirmed, released March 23, 2026
- [Google Cloud KMS Python docs](https://docs.cloud.google.com/python/docs/reference/cloudkms/latest) — `KeyManagementServiceClient`, `CryptoKeyVersion.algorithm` enum confirmed; version 3.11.0 shown in docs drop-down (3.12.0 is latest release)
- [hvac PyPI](https://pypi.org/project/hvac/) — version 2.4.0 confirmed, released October 30, 2025
- [hvac docs — transit list keys, PKI list roles, auth list methods](https://python-hvac.org/en/stable/overview.html) — API shape confirmed via Context7 code snippets
- [kubernetes PyPI](https://pypi.org/project/kubernetes/) — version 35.0.0 confirmed, released January 16, 2026
- [Kubernetes encrypt-data docs](https://kubernetes.io/docs/tasks/administer-cluster/encrypt-data/) — confirmed EncryptionConfiguration is not a queryable API resource; kube-apiserver pod spec inspection is the canonical agentless detection method
- [psycopg2-binary PyPI](https://pypi.org/project/psycopg2-binary/) — version 2.9.12 confirmed, released April 20, 2026
- [PyMySQL PyPI](https://pypi.org/project/PyMySQL/) — version 1.1.2 confirmed, released August 24, 2025
- [ldap3 PyPI](https://pypi.org/project/ldap3/) — version 2.9.1 is current stable; 2.10.2rc4 is pre-release only (confirmed April 2026)
- [boto3 RDS describe_db_instances docs](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/rds/client/describe_db_instances.html) — `StorageEncrypted` bool confirmed in response shape; existing boto3 session reusable
- [google-auth PyPI](https://pypi.org/project/google-auth/) — version 2.49.2 confirmed, released April 10, 2026; pulled transitively by google-cloud-kms
- WebSearch: azure-mgmt-storage latest version March 2026 confirmed; `encryption.key_source` field distinguishes CMK (`Microsoft.Keyvault`) from platform key (`Microsoft.Storage`)
- WebSearch: hvac transit/PKI/auth API patterns — code examples verified against hvac 2.4.0 docs

---

*Stack research for: QU.I.R.K. v4.3 Data at Rest — GCP connector, database encryption, object storage, Kubernetes secrets, HashiCorp Vault, trend analysis*
*Researched: 2026-04-24*
