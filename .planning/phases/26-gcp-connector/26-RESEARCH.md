# Phase 26: GCP Connector - Research

**Researched:** 2026-04-24
**Domain:** Google Cloud Platform cryptographic inventory scanning (Cloud KMS, Cloud SQL, GCS)
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** GCP SDK packages go in a new `[cloud]` optional extras group in `pyproject.toml`. Add `google-api-python-client>=2.0.0` (and `google-auth>=2.36.0` if not pulled transitively). boto3 and azure SDK packages **stay in main dependencies** for backward compatibility. The `[cloud]` group is created now so Phase 30 (HashiCorp Vault, `hvac`) can land there too.
- **D-02:** Use `google-api-python-client` for all three GCP services (Cloud KMS, Cloud SQL Admin, GCS). Single package in `[cloud]` extras, uniform call pattern: `service = build("cloudkms"/"sqladmin"/"storage", "v1", credentials=creds)`. Auth via `google.auth.default()` (ADC) — no credentials stored in the module. Module-level optional import with `GCP_AVAILABLE` flag, same pattern as `BOTO3_AVAILABLE` in `aws_connector.py`.
- **D-03:** Add a new `gcs_scan_json` TEXT column to `crypto_endpoints` table. Follow the `_IDENTITY_COLUMNS` / `_ensure_identity_columns()` pattern in `db.py` exactly: Add `"gcs_scan_json"` to a `_GCP_COLUMNS` list alongside a `_ensure_gcp_columns()` function. Called from `init_db()` after `_ensure_identity_columns()`. Phase 26 writes the full GCS bucket list as a JSON array to this column once per scan. Phase 28 reads `gcs_scan_json` from the scan record — zero duplicate `storage.buckets.list` API calls.
- **D-04:** Enumerate primary version only — one `CryptoEndpoint` per Cloud KMS key. Use `key.primary` version for algorithm and protection level. Matches the AWS KMS connector model. Destroyed/disabled versions are skipped.
- **D-05:** Auto-discover all KMS locations via `projects.locations.list(name=project_resource)`. Filter results to locations that support Cloud KMS (enumerate all and gracefully handle 404 on key ring list). Zero user config beyond `gcp_project_id`. No `gcp_kms_locations` config field needed.
- **D-06:** Add to `ConnectorsCfg` in `config.py`: `enable_gcp: bool = False` and `gcp_project_id: Optional[str] = None`. Add matching fields to `config_template.yaml` under `connectors:` section.
- **D-07:** Build `GCP_KMS_ALGORITHM_MAP` dict mapping GCP algorithm strings to `(algorithm, key_size)` tuples, mirroring `KMS_KEY_SPEC_MAP` in `aws_connector.py`. Must cover: asymmetric sign, asymmetric decrypt, symmetric, MAC, and external/HSM variants.
- **D-08:** `sslMode` field from Cloud SQL Admin API v1 response logic: `"ALLOW_UNENCRYPTED_AND_ENCRYPTED"` → HIGH finding, `"ENCRYPTED_ONLY"` → MEDIUM finding, `"TRUSTED_CLIENT_CERTIFICATE_REQUIRED"` → no finding (mTLS enforced), missing/null → HIGH finding. Protocol field on CryptoEndpoint: `"CLOUD_SQL"`, service_detail: instance name.

### Claude's Discretion

- GCP quantum-safety classification: use the existing `QUANTUM_SAFETY` classifier in `quirk/cbom/classifier.py` — no new classification logic needed
- CBOM integration: GCP endpoints flow through existing builder pass 1 (key type → CryptoComponent) unchanged — no new CBOM pass or skip-list entry needed
- Connector function signatures: follow `aws_connector.py` style
- Error handling: per-resource try/except with logger.v() on failure — same as existing connectors

### Deferred Ideas (OUT OF SCOPE)

- GCP chaos lab profile (mock GCP KMS/Cloud SQL/GCS via LocalStack or similar) — no LocalStack GCP support yet
- Moving boto3 and azure SDK from main deps into `[cloud]` extras — breaking change for existing installs
- `gcp_kms_locations` user-configurable filter — auto-discovery covers all cases
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| GCP-01 | Scanner can enumerate Cloud KMS key specs with quantum-safety classification (RSA-2048/4096, ECDSA P-256/P-384, AES-256, HMAC-SHA256, external/HSM variants) for a configured GCP project | GCP_KMS_ALGORITHM_MAP verified against Discovery API enum (47 algorithm values); existing classifier.py covers RSA/ECDSA/AES/HMAC; PQC keys (ML-DSA, ML-KEM) need new classifier entries |
| GCP-02 | Scanner can detect Cloud SQL instance TLS enforcement mode and produce findings for disabled or plaintext-allowed TLS configurations | sslMode enum values verified from sqladmin.v1 discovery doc and official docs; three-tier finding logic confirmed in D-08 |
| GCP-03 | Scanner can detect GCS bucket default encryption type (CMEK with customer-managed key vs Google-managed key) across all buckets in a project | Bucket.encryption.defaultKmsKeyName field verified from storage.v1 discovery doc; absence = Google-managed encryption |
</phase_requirements>

---

## Summary

Phase 26 adds a GCP connector (`quirk/scanner/gcp_connector.py`) that enumerates Cloud KMS key specs, Cloud SQL TLS enforcement, and GCS bucket encryption using Application Default Credentials (ADC). The critical design question — `google-api-python-client` versus `google-cloud-kms` — is resolved: **use `google-api-python-client`**. This decision is locked in D-02 and is confirmed correct by this research.

The grpcio/protobuf conflict risk with `google-cloud-kms` is REAL and ACTIVE (see pitfall section). `google-cloud-kms==3.12.0` requires `google-api-core[grpc]`, which adds `grpcio>=1.33.2` as a hard dependency. The QUIRK venv does not currently have grpcio installed, and the existing `signxml` and `cyclonedx-python-lib` packages could conflict at install time. `google-api-python-client==2.194.0` adds only `httplib2`, `google-auth`, `google-auth-httplib2`, `google-api-core` (non-grpc), and `uritemplate` — no grpcio, no protobuf directly.

All three API discovery documents (`cloudkms.v1.json`, `sqladmin.v1.json`, `storage.v1.json`) are bundled directly in the `google-api-python-client` wheel — no network call required at import time. The `build()` pattern works offline once the package is installed. [VERIFIED: google-api-python-client wheel inspection]

Notably, the Cloud KMS v1 API now includes PQC algorithm types: `ML_KEM_768`, `ML_KEM_1024`, `KEM_XWING`, `PQ_SIGN_ML_DSA_44/65/87`, and `PQ_SIGN_SLH_DSA_*` variants. These map to existing `ml-kem-*` and `ml-dsa-*` entries in `classifier.py`, so GCP keys using PQC algorithms will automatically produce quantum-safe findings in the CBOM — no classifier changes needed.

**Primary recommendation:** Implement `gcp_connector.py` using `google-api-python-client>=2.0.0` with `google-auth>=2.36.0`, following the established `aws_connector.py` structure exactly, with the GCP_KMS_ALGORITHM_MAP covering all 47 Cloud KMS algorithm strings, `DefaultCredentialsError` caught at every API call site, and `gcs_scan_json` written via `_ensure_gcp_columns()`.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Cloud KMS enumeration | Backend (scanner module) | — | API credential-based scan; no UI or network probe needed |
| Cloud SQL TLS detection | Backend (scanner module) | — | Cloud SQL Admin API call; returns settings.ipConfiguration.sslMode |
| GCS bucket encryption scan | Backend (scanner module) | — | Storage JSON API call; bucket.encryption.defaultKmsKeyName field |
| GCS data hand-off to Phase 28 | Database layer (gcs_scan_json column) | Backend (scanner) | Zero-duplicate requirement (STOR-03) satisfied via DB persistence |
| CBOM integration | CBOM builder Pass 1 | — | GCP endpoints flow through existing builder; "GCP" added to protocol skip lists |
| Findings production | Risk engine (existing) | Scanner module | Finding logic (HIGH/MEDIUM) lives in connector per D-08 |

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| google-api-python-client | 2.194.0 [VERIFIED: PyPI] | Discovery-based REST client for all three GCP APIs | No grpcio/protobuf dep; all 3 discovery docs bundled; uniform `build()` pattern |
| google-auth | 2.49.2 [VERIFIED: PyPI] | Application Default Credentials (ADC) for `google.auth.default()` | Pulled transitively by google-api-python-client; explicit pin ensures ADC support |
| google-auth-httplib2 | — | Required http adapter for google-api-python-client | Pulled transitively; enables credential injection into httplib2 requests |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| google-api-core (no grpc extra) | 2.30.3 [VERIFIED: PyPI] | Pulled transitively by google-api-python-client | Do NOT explicitly require google-api-core[grpc] — grpc extra is NOT needed |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| google-api-python-client | google-cloud-kms + google-cloud-storage | google-cloud-kms 3.12.0 requires grpcio>=1.33.2 via google-api-core[grpc]; QUIRK venv has no grpcio; conflict risk HIGH |
| google.auth.default() | Service account JSON credential | ADC is environment-agnostic (works with gcloud CLI, Workload Identity, SA key file) — no credentials in code |

**Installation (for `[cloud]` extras group):**
```bash
# Add to pyproject.toml [project.optional-dependencies]
[cloud]
google-api-python-client>=2.0.0
google-auth>=2.36.0
```

**Version verification:** [VERIFIED: PyPI registry 2026-04-24]
- `google-api-python-client`: 2.194.0 (released 2026-04-08)
- `google-auth`: 2.49.2 (latest)

---

## Architecture Patterns

### System Architecture Diagram

```
run_scan.py
    │
    ├─ cfg.connectors.enable_gcp? ─── YES ──►  scan_gcp_targets(project, logger)
    │                                                  │
    │   ┌──────────────────────────────────────────────┤
    │   │                                              │
    │   ▼                                              ▼
    │ google.auth.default()                   GCP_AVAILABLE=False
    │   │                                     └─► return []
    │   ▼
    │ build("cloudkms","v1",creds)  build("sqladmin","v1",creds)  build("storage","v1",creds)
    │   │                                │                              │
    │   ▼                                ▼                              ▼
    │ _scan_kms(service, project)   _scan_cloud_sql(service,proj)  _scan_gcs(service,proj)
    │   │                                │                              │
    │   │  locations.list()             │  instances.list()            │  buckets.list()
    │   │  ↓ for each location          │  ↓ for each instance         │  ↓ for each bucket
    │   │  keyRings.list()              │  sslMode field               │  encryption.defaultKmsKeyName
    │   │  ↓ for each keyRing           │                              │
    │   │  cryptoKeys.list()            │                              │
    │   │  ↓ primary.algorithm          │                              │
    │   │  ↓ primary.protectionLevel    │                              │
    │   │                               │                              │
    │   ▼                               ▼                              ▼
    │  [CryptoEndpoint(protocol="GCP")]  [CryptoEndpoint(protocol="CLOUD_SQL")]  [CryptoEndpoint(protocol="GCP")]
    │                                                                            gcs_scan_json=json.dumps(buckets)
    │
    └─► endpoints list ──► risk_engine ──► findings ──► db ──► CBOM builder
                                                              (Pass 1: "GCP" added to cloud branch)
                                                              (Pass 3: "GCP" added to skip list)
```

### Recommended Project Structure

```
quirk/scanner/
├── gcp_connector.py          # NEW: Cloud KMS / Cloud SQL / GCS scanner
tests/
├── test_cloud_connectors.py  # EXTENDED: add GCP test class
quirk/
├── db.py                     # MODIFIED: add _GCP_COLUMNS + _ensure_gcp_columns()
├── config.py                 # MODIFIED: add enable_gcp + gcp_project_id to ConnectorsCfg
├── config_template.yaml      # MODIFIED: add GCP config block (commented out)
├── cbom/builder.py           # MODIFIED: add "GCP" to Pass 1 cloud branch + Pass 3 skip list
run_scan.py                   # MODIFIED: wire scan_gcp_targets() behind enable_gcp check
pyproject.toml                # MODIFIED: add [cloud] extras group
```

### Pattern 1: Module-Level Optional Import (GCP_AVAILABLE Flag)

**What:** Import `googleapiclient` and `google.auth` at module level with try/except, same pattern as `BOTO3_AVAILABLE` in `aws_connector.py`.
**When to use:** All three GCP services use this single availability flag.

```python
# Source: quirk/scanner/aws_connector.py (pattern to replicate)
try:
    from googleapiclient.discovery import build as _gcp_build
    import google.auth
    from google.auth.exceptions import DefaultCredentialsError
    GCP_AVAILABLE = True
except ImportError:
    _gcp_build = None           # type: ignore[assignment]
    google = None               # type: ignore[assignment]
    DefaultCredentialsError = None  # type: ignore[assignment]
    GCP_AVAILABLE = False
```

**Critical:** Module-level `None` assignments are REQUIRED for test patching (see azure_connector.py — this pattern enables `patch("quirk.scanner.gcp_connector.GCP_AVAILABLE", False)` in tests without the module failing to import).

### Pattern 2: ADC Credential Acquisition

**What:** Call `google.auth.default()` once per scan, pass `credentials` object to all three `build()` calls.
**When to use:** Single credential acquisition per `scan_gcp_targets()` call.

```python
# Source: [CITED: google-auth docs — google.auth.default()]
def scan_gcp_targets(project_id: str, logger=None) -> List[CryptoEndpoint]:
    if not GCP_AVAILABLE:
        if logger:
            logger.v("google-api-python-client not installed — GCP scanning unavailable")
        return []
    try:
        credentials, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
    except DefaultCredentialsError as exc:
        # DefaultCredentialsError fires here (import time is safe) — D-06 note
        ep = CryptoEndpoint(
            host=f"gcp://{project_id}",
            port=0,
            protocol="GCP",
            scan_error=f"gcp-credentials-unavailable: {exc}",
        )
        return [ep]
    except Exception as exc:
        if logger:
            logger.v(f"GCP auth error: {exc}")
        return []
    ...
```

**Note on DefaultCredentialsError timing:** STATE.md records that `DefaultCredentialsError` fires at API call time. This is partially correct — it also fires at `google.auth.default()` call time when no credentials are configured at all. The safe strategy is to catch it at BOTH `google.auth.default()` and at each API `execute()` call to handle the case where credentials exist but are scoped incorrectly or expired.

### Pattern 3: Discovery API Build and Paginated List

**What:** Use `build(service, version, credentials=creds)` with pageToken-based manual pagination (Discovery API does not have a paginator helper like boto3).
**When to use:** All three GCP service clients (cloudkms, sqladmin, storage).

```python
# Source: [VERIFIED: google-api-python-client wheel — cloudkms.v1.json bundled]
kms_service = _gcp_build("cloudkms", "v1", credentials=credentials)

# Manual pagination (no get_paginator() — this is REST/JSON, not AWS SDK)
project_resource = f"projects/{project_id}"
request = kms_service.projects().locations().list(name=project_resource)
while request is not None:
    response = request.execute()
    for location in response.get("locations", []):
        location_id = location.get("locationId", "")
        # ... enumerate key rings and keys
    request = kms_service.projects().locations().list_next(
        previous_request=request, previous_response=response
    )
```

**Key insight:** `list_next()` returns `None` when no more pages exist. This is the standard pattern for google-api-python-client pagination, equivalent to boto3's paginator.

### Pattern 4: GCS Data Serialization for Phase 28 Hand-off (D-03)

**What:** `gcs_scan_json` stores the full bucket list once per scan. One sentinel `CryptoEndpoint` with `protocol="GCP"` carries the column value. Phase 28 reads from this row.

```python
# Source: CONTEXT.md D-03 and models.py inspection
bucket_list = []  # accumulated from storage.buckets.list() pagination
# ... collect all buckets ...

# Create one GCS-summary endpoint carrying the bucket data
gcs_ep = CryptoEndpoint(
    host=f"gcp://{project_id}/storage",
    port=0,
    protocol="GCP",
    cert_pubkey_alg="GCS-SUMMARY",
    gcs_scan_json=json.dumps(bucket_list, default=str),
    service_detail="GCS",
)
# Separately create per-bucket CryptoEndpoints for findings:
for bucket in bucket_list:
    enc = bucket.get("encryption", {})
    kms_key = enc.get("defaultKmsKeyName")
    alg = "CMEK" if kms_key else "Google-Managed"
    ep = CryptoEndpoint(
        host=f"gcp://{project_id}/buckets/{bucket.get('name', '')}",
        port=0,
        protocol="GCP",
        cert_pubkey_alg=alg,
        cloud_scan_json=json.dumps(bucket, default=str),
        service_detail="GCS",
    )
```

**Note:** `gcs_scan_json` is a NEW column added via `_ensure_gcp_columns()`. It is NOT currently in `models.py`. The DB migration pattern uses ALTER TABLE (idempotent via inspector check), same as `_ensure_identity_columns()`.

### Pattern 5: Cloud SQL TLS Finding Logic

**What:** Map the three `sslMode` values to findings per D-08.

```python
# Source: [VERIFIED: sqladmin.v1.json in google-api-python-client wheel; official docs]
SSL_FINDING_MAP = {
    "ALLOW_UNENCRYPTED_AND_ENCRYPTED": ("HIGH", "plaintext connections allowed"),
    "ENCRYPTED_ONLY": ("MEDIUM", "encryption required but no client certificate validation"),
    # "TRUSTED_CLIENT_CERTIFICATE_REQUIRED" → no finding, mTLS enforced
}

def _scan_cloud_sql(service, project_id: str, logger) -> List[CryptoEndpoint]:
    results = []
    try:
        request = service.instances().list(project=project_id)
        while request is not None:
            response = request.execute()
            for instance in response.get("items", []):
                name = instance.get("name", "")
                settings = instance.get("settings", {})
                ip_cfg = settings.get("ipConfiguration", {})
                ssl_mode = ip_cfg.get("sslMode") or "ALLOW_UNENCRYPTED_AND_ENCRYPTED"
                ...
            request = service.instances().list_next(request, response)
    except Exception as exc:
        if logger:
            logger.v(f"Cloud SQL scan error: {exc}")
    return results
```

### Anti-Patterns to Avoid

- **Importing google.auth at the function level (not module level):** Import must be at module level with None assignment so `patch("...GCP_AVAILABLE", False)` works in tests without NameError.
- **Raising on DefaultCredentialsError:** Must produce a `scan_error` CryptoEndpoint, not crash. Both D-08 and the roadmap success criteria SC-4 require graceful degradation.
- **Assuming `primary` field exists on every CryptoKey:** `primary` is only present for keys with purpose `ENCRYPT_DECRYPT`. Asymmetric signing/decryption keys use different purpose values. Always guard: `primary = key.get("primary") or {}`.
- **Using `get_paginator()` pattern from boto3:** Discovery API uses `list_next()`. `get_paginator()` does not exist on Discovery-built service objects.
- **Treating `CLOUD_SQL` as a CBOM protocol:** Protocol `"CLOUD_SQL"` endpoints should be added to Pass 3's skip list (alongside `"JWT"`, `"CONTAINER"`, etc.) since they have no TLS/ProtocolProperties component. Their findings come from Pass 1 `cert_pubkey_alg`.
- **Writing `gcs_scan_json` on every bucket row:** Write it only once on the summary/sentinel endpoint to avoid inflating DB row count.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| GCP Authentication | Custom credential loader | `google.auth.default()` ADC | Handles gcloud CLI, Workload Identity, SA key file, Cloud Shell transparently |
| Discovery document fetching | Dynamic URL fetch | Already bundled in wheel | `google-api-python-client 2.x` caches all 580 discovery docs at install time |
| KMS algorithm → quantum safety mapping | Custom classifier logic | Existing `classifier.py` + `GCP_KMS_ALGORITHM_MAP` | `classify_algorithm("RSA")` already returns correct NIST level; PQC keys map to existing ml-kem/ml-dsa entries |
| Schema migration | Custom SQL migration | `_ensure_gcp_columns()` pattern from `_ensure_identity_columns()` | Inspector-first idempotent ALTER TABLE is established pattern |
| CBOM output | New CBOM pass | `_normalize_cloud_key_spec()` extension | GCP algorithm strings normalize to names classifier already knows |

**Key insight:** The Google Discovery API pattern means you get a working Python client for Cloud KMS, Cloud SQL Admin, and Cloud Storage with a single `pip install` and no protobuf/grpcio in the dependency tree.

---

## Runtime State Inventory

This is a greenfield scanner module — no rename/refactor involved. Step 2.5 SKIPPED.

---

## Common Pitfalls

### Pitfall 1: grpcio/protobuf Conflict from google-cloud-kms

**What goes wrong:** Installing `google-cloud-kms` pulls in `google-api-core[grpc]`, which requires `grpcio>=1.33.2`. This conflicts with the current QUIRK venv (no grpcio installed) and may conflict with `grpcio-status` version constraints. Known active issue in the Google Cloud Python ecosystem as of 2025-2026.
**Why it happens:** `google-cloud-kms 3.12.0` (latest) requires `google-api-core[grpc]<3.0.0,>=2.11.0` and `grpcio<2.0.0,>=1.33.2`. [VERIFIED: google-cloud-kms wheel metadata]
**How to avoid:** Use `google-api-python-client` (D-02 decision). Its `google-api-core` dependency does NOT include the `[grpc]` extra — no grpcio pulled.
**Warning signs:** `pip install quirk[cloud]` emits grpcio compilation errors or protobuf version conflicts.

### Pitfall 2: DefaultCredentialsError Fires at API Call Time, Not Import Time

**What goes wrong:** `GCP_AVAILABLE = True` after import succeeds, but the first `execute()` call raises `DefaultCredentialsError` because no GCP credentials are configured in the environment.
**Why it happens:** `google.auth.default()` succeeds when GOOGLE_APPLICATION_CREDENTIALS is set to a MISSING file but the path is syntactically valid (not always — depends on implementation). More commonly, `google.auth.default()` raises immediately when no ADC is found. Either way, each API `execute()` can also raise `TransportError` with a wrapped `DefaultCredentialsError` if token refresh fails.
**How to avoid:** Catch `DefaultCredentialsError` (and `google.auth.exceptions.TransportError`) at: (1) `google.auth.default()` call, AND (2) inside each per-resource try/except block. [VERIFIED: STATE.md D-note + google-auth docs]
**Warning signs:** Scanner crashes with `google.auth.exceptions.DefaultCredentialsError: Could not automatically determine credentials` in production.

### Pitfall 3: CryptoKey.primary Is Only Present for ENCRYPT_DECRYPT Keys

**What goes wrong:** Iterating all CryptoKeys and accessing `key["primary"]["algorithm"]` raises `KeyError` for asymmetric signing/decrypt keys where `primary` is absent in the response.
**Why it happens:** The API returns `primary` only for keys with `purpose=ENCRYPT_DECRYPT`. [VERIFIED: cloudkms.v1 discovery doc — `primary` field is described as "A copy of the 'primary' CryptoKeyVersion that will be used by Encrypt".]
**How to avoid:** Always use `key.get("primary") or {}` and extract `algorithm` via `.get("algorithm", "")`. Skip keys where primary is None and there's no `versionTemplate.algorithm`.
**Warning signs:** `KeyError: 'primary'` in test mocks or production when scanning RSA signing keys.

### Pitfall 4: storage.buckets.list() Response Field Is "items", Not "buckets"

**What goes wrong:** Code accesses `response.get("buckets", [])` and gets no results.
**Why it happens:** The Storage JSON API returns the bucket list under `"items"` in the response, not `"buckets"`. [VERIFIED: storage.v1.json in google-api-python-client wheel — Buckets.list response schema uses `items`]
**How to avoid:** Always use `response.get("items", [])`.
**Warning signs:** Zero GCS buckets returned from a project known to have buckets.

### Pitfall 5: gcs_scan_json Column Does Not Exist in CryptoEndpoint Model

**What goes wrong:** SQLAlchemy raises `AttributeError: 'CryptoEndpoint' object has no attribute 'gcs_scan_json'` when the connector tries to assign to it.
**Why it happens:** `gcs_scan_json` is a new column added via `_ensure_gcp_columns()` / ALTER TABLE. It is NOT declared in the ORM model in `models.py`. This is intentional (same pattern as identity columns) — but means you CANNOT assign via ORM attribute syntax. Must be set via SQL UPDATE after session commit, or the model must be extended.
**How to avoid:** Either (a) add `gcs_scan_json = Column(Text, nullable=True)` to `CryptoEndpoint` in `models.py` (clean ORM approach, and the right solution given CONTEXT.md canonically says "Add `"gcs_scan_json"` TEXT column"), or (b) use `text()` SQL after insert. The identity columns use approach (a) and that's the right pattern.
**Warning signs:** ORM attribute error when trying to set `gcs_scan_json` on a CryptoEndpoint instance.

### Pitfall 6: CBOM Builder Does Not Handle protocol="GCP" or protocol="CLOUD_SQL"

**What goes wrong:** New GCP endpoints fall through to the default TLS branch in Pass 1, and the builder tries to parse `cipher_suite` as a cipher suite string, producing garbage CBOM entries.
**Why it happens:** The `elif ep.protocol in ("AWS", "AZURE"):` block on line 342 of builder.py does not include "GCP". Same for Pass 3 skip list at line 475.
**How to avoid:** Add `"GCP"` and `"CLOUD_SQL"` to both the Pass 1 cloud branch and the Pass 3 skip list. Also extend `_normalize_cloud_key_spec()` to handle GCP algorithm strings like `"RSA_SIGN_PKCS1_2048_SHA256"` → `"RSA"`. [VERIFIED: builder.py inspection]
**Warning signs:** CBOM output contains empty or malformed algorithm components for GCP endpoints.

### Pitfall 7: sslMode Absent or "SSL_MODE_UNSPECIFIED" in Older Instances

**What goes wrong:** Code only checks the three documented modes and silently produces no finding for instances where `sslMode` is absent (older instances created before the field existed) or set to `"SSL_MODE_UNSPECIFIED"`.
**Why it happens:** The `SSL_MODE_UNSPECIFIED` value means unknown enforcement — effectively equivalent to `ALLOW_UNENCRYPTED_AND_ENCRYPTED`. [VERIFIED: sqladmin.v1.json in google-api-python-client wheel]
**How to avoid:** Treat `None`, `""`, and `"SSL_MODE_UNSPECIFIED"` as HIGH finding (same as D-08 "Missing/null" case).
**Warning signs:** Older Cloud SQL instances produce no TLS findings despite plaintext being allowed.

---

## GCP KMS Algorithm Map (Complete)

All 47 `CryptoKeyVersionAlgorithm` values from the Cloud KMS v1 API, with their `(algorithm, key_size)` mappings for `GCP_KMS_ALGORITHM_MAP`. [VERIFIED: cloudkms.v1.json in google-api-python-client 2.194.0 wheel]

```python
GCP_KMS_ALGORITHM_MAP = {
    # Symmetric encryption
    "GOOGLE_SYMMETRIC_ENCRYPTION": ("AES", 256),
    "AES_128_GCM": ("AES", 128),
    "AES_256_GCM": ("AES", 256),
    "AES_128_CBC": ("AES", 128),
    "AES_256_CBC": ("AES", 256),
    "AES_128_CTR": ("AES", 128),
    "AES_256_CTR": ("AES", 256),
    # RSA signing — PKCS1
    "RSA_SIGN_PKCS1_2048_SHA256": ("RSA", 2048),
    "RSA_SIGN_PKCS1_3072_SHA256": ("RSA", 3072),
    "RSA_SIGN_PKCS1_4096_SHA256": ("RSA", 4096),
    "RSA_SIGN_PKCS1_4096_SHA512": ("RSA", 4096),
    # RSA signing — PSS
    "RSA_SIGN_PSS_2048_SHA256": ("RSA", 2048),
    "RSA_SIGN_PSS_3072_SHA256": ("RSA", 3072),
    "RSA_SIGN_PSS_4096_SHA256": ("RSA", 4096),
    "RSA_SIGN_PSS_4096_SHA512": ("RSA", 4096),
    # RSA signing — Raw PKCS1
    "RSA_SIGN_RAW_PKCS1_2048": ("RSA", 2048),
    "RSA_SIGN_RAW_PKCS1_3072": ("RSA", 3072),
    "RSA_SIGN_RAW_PKCS1_4096": ("RSA", 4096),
    # RSA decryption
    "RSA_DECRYPT_OAEP_2048_SHA256": ("RSA", 2048),
    "RSA_DECRYPT_OAEP_3072_SHA256": ("RSA", 3072),
    "RSA_DECRYPT_OAEP_4096_SHA256": ("RSA", 4096),
    "RSA_DECRYPT_OAEP_4096_SHA512": ("RSA", 4096),
    "RSA_DECRYPT_OAEP_2048_SHA1": ("RSA", 2048),
    "RSA_DECRYPT_OAEP_3072_SHA1": ("RSA", 3072),
    "RSA_DECRYPT_OAEP_4096_SHA1": ("RSA", 4096),
    # EC signing
    "EC_SIGN_P256_SHA256": ("ECDSA", 256),
    "EC_SIGN_P384_SHA384": ("ECDSA", 384),
    "EC_SIGN_SECP256K1_SHA256": ("ECDSA", 256),
    "EC_SIGN_ED25519": ("EdDSA", 256),
    # HMAC
    "HMAC_SHA256": ("HMAC", 256),
    "HMAC_SHA1": ("HMAC", 160),
    "HMAC_SHA384": ("HMAC", 384),
    "HMAC_SHA512": ("HMAC", 512),
    "HMAC_SHA224": ("HMAC", 224),
    # External (wrapping key — algorithm from external KMS)
    "EXTERNAL_SYMMETRIC_ENCRYPTION": ("AES", 256),   # service_detail captures protection level
    # PQC algorithms (new in Cloud KMS — produce quantum-safe findings!)
    "ML_KEM_768": ("ml-kem-768", 768),
    "ML_KEM_1024": ("ml-kem-1024", 1024),
    "KEM_XWING": ("ml-kem-768", 768),   # X-Wing = ML-KEM-768 + X25519 hybrid
    "PQ_SIGN_ML_DSA_44": ("ml-dsa-44", 44),
    "PQ_SIGN_ML_DSA_65": ("ml-dsa-65", 65),
    "PQ_SIGN_ML_DSA_87": ("ml-dsa-87", 87),
    "PQ_SIGN_SLH_DSA_SHA2_128S": ("slh-dsa-128", 128),
    "PQ_SIGN_HASH_SLH_DSA_SHA2_128S_SHA256": ("slh-dsa-128", 128),
    "PQ_SIGN_ML_DSA_44_EXTERNAL_MU": ("ml-dsa-44", 44),
    "PQ_SIGN_ML_DSA_65_EXTERNAL_MU": ("ml-dsa-65", 65),
    "PQ_SIGN_ML_DSA_87_EXTERNAL_MU": ("ml-dsa-87", 87),
    # Unspecified — skip/unknown
    "CRYPTO_KEY_VERSION_ALGORITHM_UNSPECIFIED": ("UNKNOWN", None),
}
```

**PQC note:** `ml-kem-768`, `ml-dsa-44/65/87`, `slh-dsa-128` are already in `classifier.py` `_ALGORITHM_TABLE` — no classifier changes needed for PQC key quantum-safe classification.

**Protection level → service_detail encoding (D-07):**
- `SOFTWARE` → `"CloudKMS/SOFTWARE"`
- `HSM` → `"CloudKMS/HSM"`
- `EXTERNAL` → `"CloudKMS/EXTERNAL"`
- `EXTERNAL_VPC` → `"CloudKMS/EXTERNAL_VPC"`
- `HSM_SINGLE_TENANT` → `"CloudKMS/HSM_SINGLE_TENANT"`

---

## Code Examples

### Full Optional Import Block
```python
# Source: quirk/scanner/azure_connector.py (pattern) + google.auth docs
from __future__ import annotations
import json
from typing import List, Optional
from quirk.models import CryptoEndpoint

try:
    from googleapiclient.discovery import build as _gcp_build
    import google.auth
    from google.auth.exceptions import DefaultCredentialsError
    GCP_AVAILABLE = True
except ImportError:
    _gcp_build = None           # type: ignore[assignment]
    google = None               # type: ignore[assignment]
    DefaultCredentialsError = None  # type: ignore[assignment]
    GCP_AVAILABLE = False
```

### _ensure_gcp_columns() Pattern
```python
# Source: quirk/db.py _ensure_identity_columns() — copy structure exactly
_GCP_COLUMNS = [
    "gcs_scan_json",
]

def _ensure_gcp_columns(engine) -> None:
    """Add GCP scanner JSON column to crypto_endpoints if absent (idempotent).
    Called from init_db() after _ensure_identity_columns().
    """
    existing = {c["name"] for c in sa_inspect(engine).get_columns("crypto_endpoints")}
    with engine.connect() as conn:
        for col in _GCP_COLUMNS:
            if col not in existing:
                conn.execute(text(f"ALTER TABLE crypto_endpoints ADD COLUMN {col} TEXT"))
        conn.commit()
```

### ConnectorsCfg Extension
```python
# Source: quirk/config.py ConnectorsCfg (add after identity fields)
# v4.3 GCP connector (Phase 26)
enable_gcp: bool = False
gcp_project_id: Optional[str] = None
```

### config_template.yaml Addition
```yaml
# -- GCP connector (optional, requires: pip install quirk[cloud]) --
# enable_gcp: false
# gcp_project_id: "my-gcp-project"
```

### CBOM Builder Pass 1 Extension
```python
# Source: quirk/cbom/builder.py line 342 — extend cloud branch
elif ep.protocol in ("AWS", "AZURE", "GCP"):
    try:
        cloud_data = json.loads(ep.cloud_scan_json or "{}")
    except (json.JSONDecodeError, TypeError, ValueError):
        cloud_data = {}
    key_spec = (cloud_data.get("KeySpec")
                or cloud_data.get("KeyAlgorithm")
                or cloud_data.get("key_type")
                or cloud_data.get("gcp_algorithm"))
    if key_spec:
        normalized = _normalize_cloud_key_spec(key_spec)
        if normalized:
            key_size = cloud_data.get("key_size") or ep.cert_pubkey_size
            _register_algorithm(normalized, algo_registry, key_size=key_size)
    if ep.cert_pubkey_alg:
        _register_algorithm(ep.cert_pubkey_alg, algo_registry, key_size=ep.cert_pubkey_size)

elif ep.protocol == "CLOUD_SQL":
    # Cloud SQL TLS finding — cert_pubkey_alg holds the finding level
    if ep.cert_pubkey_alg:
        _register_algorithm(ep.cert_pubkey_alg, algo_registry, key_size=ep.cert_pubkey_size)
```

Also extend Pass 3 skip list:
```python
# Source: quirk/cbom/builder.py line 475 — extend skip list
elif ep.protocol in ("JWT", "CONTAINER", "SOURCE", "AWS", "AZURE", "GCP", "CLOUD_SQL",
                     "DNSSEC", "SAML", "KERBEROS"):
    continue
```

And extend `_normalize_cloud_key_spec()` to handle GCP strings:
```python
# Add to existing mapping dict in _normalize_cloud_key_spec()
"RSA_SIGN_PKCS1_2048_SHA256": "RSA", "RSA_SIGN_PKCS1_3072_SHA256": "RSA",
"RSA_SIGN_PKCS1_4096_SHA256": "RSA", "RSA_SIGN_PKCS1_4096_SHA512": "RSA",
"RSA_SIGN_PSS_2048_SHA256": "RSA", "RSA_SIGN_PSS_3072_SHA256": "RSA",
"RSA_SIGN_PSS_4096_SHA256": "RSA", "RSA_SIGN_PSS_4096_SHA512": "RSA",
"RSA_DECRYPT_OAEP_2048_SHA256": "RSA", "RSA_DECRYPT_OAEP_3072_SHA256": "RSA",
"RSA_DECRYPT_OAEP_4096_SHA256": "RSA",
"EC_SIGN_P256_SHA256": "ECDSA", "EC_SIGN_P384_SHA384": "ECDSA",
"GOOGLE_SYMMETRIC_ENCRYPTION": "AES-256-GCM",
"AES_256_GCM": "AES-256-GCM", "AES_128_GCM": "AES-128-GCM",
"HMAC_SHA256": "HMAC", "HMAC_SHA512": "HMAC",
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Use `discovery.build()` with dynamic doc fetch | Discovery docs bundled in wheel since v2.0 | 2020 (v2.x release) | No network required; faster; works offline |
| `google-cloud-kms` for KMS scanning | `google-api-python-client` for lightweight REST | — | Avoids grpcio/protobuf dependency in restricted envs |
| `requireSsl` boolean for Cloud SQL | `sslMode` enum (v1 API) | Cloud SQL Admin API v1 | More granular enforcement levels; `requireSsl` deprecated |

**GCP KMS PQC algorithms (NEW as of 2025-2026):**
- Cloud KMS now natively supports: ML-KEM-768, ML-KEM-1024, KEM-XWING (hybrid), ML-DSA-44/65/87, SLH-DSA variants
- These are `PQ_SIGN_*` and `ML_KEM_*` prefix algorithm strings in the API
- QUIRK's `classifier.py` already has `ml-kem-*`, `ml-dsa-*`, `slh-dsa-*` entries — CBOM will correctly classify GCP PQC keys as quantum-safe

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `KEM_XWING` algorithm is equivalent to ML-KEM-768 for classification purposes | GCP KMS Algorithm Map | Minor: XWing is ML-KEM-768 + X25519 hybrid; may deserve its own classifier entry for accuracy |
| A2 | `gcs_scan_json` should use one sentinel CryptoEndpoint per project rather than one per bucket | Architecture Pattern 4 | Low: if Phase 28 expects per-bucket rows, refactor needed; but D-03 says "the full GCS bucket list as a JSON array" (singular) |
| A3 | `_normalize_cloud_key_spec()` extension in builder.py is sufficient (vs a new GCP-specific normalizer) | CBOM Builder Extension | Low: if normalizer grows too large, extract to separate function; but unified approach maintains existing architecture |

---

## Open Questions

1. **gcs_scan_json column in models.py vs ALTER TABLE only**
   - What we know: `_ensure_identity_columns()` uses ALTER TABLE (no ORM model change) for identity columns. But CONTEXT.md says `CryptoEndpoint` fields already present include `cloud_scan_json` — suggesting ORM-declared columns exist.
   - What's unclear: Should `gcs_scan_json` be added to `models.py` ORM class body (like `cloud_scan_json`) or only via `_ensure_gcp_columns()` ALTER TABLE?
   - Recommendation: ADD to `models.py` ORM class body, AND add `_ensure_gcp_columns()` for backward-compatible migration. The identity columns were added at a time when the pattern was still evolving; the ORM + migration guard pattern is cleaner. But this is Claude's Discretion — either works functionally.

2. **run_scan.py session_start requirement**
   - What we know: STATE.md records "ISSUE-3 patterns must be treated as structural requirements on every scanner phase — session_start parameter is mandatory for all new scanners."
   - What's unclear: Cloud connectors (AWS, Azure) don't currently take `session_start`. Does this ISSUE-3 requirement apply only to identity scanners (which have timestamp-based deduplication logic) or ALL new scanners?
   - Recommendation: Pass `session_start` to `scan_gcp_targets()` for consistency with identity scanners, even if unused internally. This future-proofs Phase 26 for trend analysis (Phase 31) which may need scan timestamps.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| google-api-python-client | GCP scanning | ✗ (not in venv) | — | Optional install via `pip install quirk[cloud]` |
| google-auth | ADC | ✗ (not in venv) | — | Pulled with google-api-python-client |
| Python 3.11+ | pyproject.toml requires >=3.10 | ✓ (3.14 in venv) | 3.14 | — |
| GCP credentials (ADC) | Runtime scan execution | N/A (runtime) | — | Scanner degrades to scan_error finding |

**Missing dependencies with no fallback:** None blocking — `[cloud]` extras group is opt-in by design.

**Missing dependencies with fallback:** `google-api-python-client` — scanner degrades gracefully when `GCP_AVAILABLE = False`.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (existing) |
| Config file | pytest.ini / inferred from pyproject.toml |
| Quick run command | `pytest tests/test_cloud_connectors.py -x -q` |
| Full suite command | `pytest tests/ -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| GCP-01 | Cloud KMS key spec mapping (RSA/ECDSA/AES/HMAC) → CryptoEndpoint | unit | `pytest tests/test_cloud_connectors.py::test_gcp_kms_algorithm_mapping -x` | ❌ Wave 0 |
| GCP-01 | GCP_AVAILABLE=False returns empty list | unit | `pytest tests/test_cloud_connectors.py::test_gcp_unavailable -x` | ❌ Wave 0 |
| GCP-02 | ALLOW_UNENCRYPTED → HIGH finding | unit | `pytest tests/test_cloud_connectors.py::test_gcp_cloud_sql_plaintext_allowed -x` | ❌ Wave 0 |
| GCP-02 | ENCRYPTED_ONLY → MEDIUM finding | unit | `pytest tests/test_cloud_connectors.py::test_gcp_cloud_sql_encrypted_only -x` | ❌ Wave 0 |
| GCP-02 | TRUSTED_CLIENT_CERTIFICATE_REQUIRED → no finding | unit | `pytest tests/test_cloud_connectors.py::test_gcp_cloud_sql_mtls_no_finding -x` | ❌ Wave 0 |
| GCP-03 | GCS bucket CMEK detection | unit | `pytest tests/test_cloud_connectors.py::test_gcp_gcs_cmek_detection -x` | ❌ Wave 0 |
| GCP-03 | STOR-03: gcs_scan_json column written | unit | `pytest tests/test_cloud_connectors.py::test_gcp_gcs_scan_json_written -x` | ❌ Wave 0 |
| GCP-01 | DefaultCredentialsError → scan_error endpoint, no crash | unit | `pytest tests/test_cloud_connectors.py::test_gcp_credentials_error_graceful -x` | ❌ Wave 0 |
| All | _ensure_gcp_columns() idempotent on v4.2 DB | unit | `pytest tests/test_identity_infra.py -k gcp -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/test_cloud_connectors.py -x -q`
- **Per wave merge:** `pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] GCP test class in `tests/test_cloud_connectors.py` — covers GCP-01, GCP-02, GCP-03
- [ ] `_ensure_gcp_columns()` test case (can extend `tests/test_identity_infra.py` or add to cloud connectors test)
- [ ] All tests must mock `_gcp_build` and `google.auth` at module level — never require real GCP credentials

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Connector uses ADC — no custom auth |
| V3 Session Management | no | Stateless scanner module |
| V4 Access Control | no | Cloud IAM enforced by GCP; scanner uses read-only permissions |
| V5 Input Validation | yes | `project_id` from config — validated as non-empty string before API calls |
| V6 Cryptography | yes | Enumeration target, not implementation; no crypto primitives in connector code |
| V7 Error Handling | yes | DefaultCredentialsError / TransportError must produce scan_error, not crash |

### Known Threat Patterns for GCP Connector

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Credential leakage in logs | Information Disclosure | Never log credential objects; catch `DefaultCredentialsError` message safely |
| SSRF via user-supplied project_id | Tampering | `project_id` comes from trusted config file, not user input; validate non-empty + format |
| Excessive API permissions escalation | Elevation of Privilege | Connector only calls read-only APIs (cloudkms.keys.list, sqladmin.instances.list, storage.buckets.list); document required IAM roles |

**Minimum required GCP IAM roles for scanner:**
- `roles/cloudkms.viewer` (or `cloudkms.cryptoKeys.list`)
- `roles/cloudsql.viewer` (or `cloudsql.instances.list`)
- `roles/storage.objectViewer` (or `storage.buckets.list`)

---

## Sources

### Primary (HIGH confidence)
- [VERIFIED: google-api-python-client 2.194.0 wheel] — cloudkms.v1.json, sqladmin.v1.json, storage.v1.json bundled discovery docs; all 47 KMS algorithm enum values; sslMode enum values; bucket encryption schema
- [VERIFIED: google-cloud-kms 3.12.0 wheel metadata] — `Requires-Dist: grpcio<2.0.0,>=1.33.2` confirmed (grpcio conflict risk)
- [VERIFIED: google-api-python-client wheel metadata] — No grpcio dependency; only httplib2, google-auth, google-auth-httplib2, google-api-core, uritemplate
- [VERIFIED: QUIRK venv pip list] — No grpcio or protobuf in current QUIRK venv; conflict risk confirmed real
- [VERIFIED: quirk/scanner/aws_connector.py] — KMS_KEY_SPEC_MAP structure, BOTO3_AVAILABLE pattern, paginator usage
- [VERIFIED: quirk/scanner/azure_connector.py] — AZURE_AVAILABLE pattern, module-level None assignments
- [VERIFIED: quirk/db.py] — `_IDENTITY_COLUMNS`, `_ensure_identity_columns()` exact pattern
- [VERIFIED: quirk/cbom/builder.py] — Pass 1 cloud branch (lines 342-356), Pass 3 skip list (line 475), `_normalize_cloud_key_spec()`
- [VERIFIED: quirk/cbom/classifier.py] — PQC entries (ml-kem-*, ml-dsa-*, slh-dsa-*) already present
- [VERIFIED: PyPI registry 2026-04-24] — google-api-python-client 2.194.0, google-auth 2.49.2, google-cloud-kms 3.12.0

### Secondary (MEDIUM confidence)
- [CITED: docs.cloud.google.com/sql/docs/mysql/admin-api/rest/v1/instances] — sslMode enum: SSL_MODE_UNSPECIFIED, ALLOW_UNENCRYPTED_AND_ENCRYPTED, ENCRYPTED_ONLY, TRUSTED_CLIENT_CERTIFICATE_REQUIRED; requireSsl deprecated
- [CITED: docs.cloud.google.com/storage/docs/json_api/v1/buckets] — Bucket.encryption.defaultKmsKeyName field; CMEK detection via presence/absence
- [CITED: docs.cloud.google.com/kms/docs/reference/rest/v1/CryptoKeyVersionAlgorithm] — Algorithm enum categories confirmed (RSA, EC, HMAC, AES, PQC)
- [CITED: googleapis.dev/python/google-auth/latest/reference/google.auth.html] — `DefaultCredentialsError` import: `from google.auth.exceptions import DefaultCredentialsError`
- [CITED: developers.google.com cloudkms_v1 discovery docs] — `list()` method; `primary` field description; protectionLevel enum

### Tertiary (LOW confidence)
- [WebSearch] — google-cloud-kms grpcio/protobuf conflict issues; confirmed multiple open issues in googleapis/google-cloud-python; treated as MEDIUM after wheel metadata verification

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — verified via wheel metadata and PyPI registry
- Architecture: HIGH — verified against existing codebase patterns (aws_connector.py, azure_connector.py, db.py, builder.py)
- API specifics: HIGH — verified from bundled discovery documents in google-api-python-client 2.194.0 wheel
- Pitfalls: HIGH — grpcio conflict verified from wheel metadata; other pitfalls verified from discovery doc inspection and codebase audit

**Research date:** 2026-04-24
**Valid until:** 2026-05-24 (30 days; google-api-python-client releases weekly but API schemas are stable)
