# Phase 26: GCP Connector - Context

**Gathered:** 2026-04-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Build a GCP connector module (`quirk/scanner/gcp_connector.py`) that enumerates three GCP
cryptographic surfaces for a configured project using Application Default Credentials (ADC):
- Cloud KMS key specs with quantum-safety classification (GCP-01)
- Cloud SQL instance TLS enforcement mode (GCP-02)
- GCS bucket default encryption type (GCP-03)

GCS bucket enumeration data is serialized to a new `gcs_scan_json` DB column for zero-duplicate
reuse in Phase 28 (Object Storage Audit, STOR-03).

This phase does NOT include a chaos lab profile or dashboard UI changes — output flows through
existing `CryptoEndpoint` rows and the CBOM builder unchanged.

</domain>

<decisions>
## Implementation Decisions

### Dependency Placement
- **D-01:** GCP SDK packages go in a new `[cloud]` optional extras group in `pyproject.toml`.
  Add `google-api-python-client>=2.0.0` (and `google-auth>=2.36.0` if not pulled transitively).
  boto3 and azure SDK packages **stay in main dependencies** for backward compatibility.
  The `[cloud]` group is created now so Phase 30 (HashiCorp Vault, `hvac`) can land there too.

### GCP SDK Library
- **D-02:** Use `google-api-python-client` for all three GCP services (Cloud KMS, Cloud SQL Admin,
  GCS). Single package in `[cloud]` extras, uniform call pattern:
  `service = build("cloudkms"/"sqladmin"/"storage", "v1", credentials=creds)`.
  Auth via `google.auth.default()` (ADC) — no credentials stored in the module.
  Module-level optional import with `GCP_AVAILABLE` flag, same pattern as `BOTO3_AVAILABLE`
  in `aws_connector.py`.

### GCS Data Hand-off for Phase 28
- **D-03:** Add a new `gcs_scan_json` TEXT column to `crypto_endpoints` table. Follow the
  `_IDENTITY_COLUMNS` / `_ensure_identity_columns()` pattern in `db.py` exactly:
  - Add `"gcs_scan_json"` to a `_GCP_COLUMNS` list alongside a `_ensure_gcp_columns()` function
  - Called from `init_db()` after `_ensure_identity_columns()`
  - Phase 26 writes the full GCS bucket list as a JSON array to this column once per scan
  - Phase 28 reads `gcs_scan_json` from the scan record — zero duplicate `storage.buckets.list`
    API calls (satisfies STOR-03)

### KMS Key Version Scope
- **D-04:** Enumerate primary version only — one `CryptoEndpoint` per Cloud KMS key.
  Use `key.primary` version for algorithm and protection level.
  Matches the AWS KMS connector model (one row per key, not per version).
  Destroyed/disabled versions are skipped.

### KMS Location Discovery
- **D-05:** Auto-discover all KMS locations via `projects.locations.list(name=project_resource)`.
  Filter results to locations that support Cloud KMS (check `locationId` against `cloudkms.googleapis.com`
  service, or enumerate all and gracefully handle 404 on key ring list).
  Zero user config beyond `gcp_project_id`. No `gcp_kms_locations` config field needed.

### Config Schema
- **D-06:** Add to `ConnectorsCfg` in `config.py`:
  ```python
  enable_gcp: bool = False
  gcp_project_id: Optional[str] = None
  ```
  Add matching fields to `config_template.yaml` under `connectors:` section.

### GCP KMS Key Spec Map
- **D-07:** Build `GCP_KMS_ALGORITHM_MAP` dict mapping GCP algorithm strings to
  `(algorithm, key_size)` tuples, mirroring `KMS_KEY_SPEC_MAP` in `aws_connector.py`.
  Must cover:
  - Asymmetric sign: `RSA_SIGN_PKCS1_2048_SHA256` → ("RSA", 2048), EC_SIGN_P256 → ("ECDSA", 256), etc.
  - Asymmetric decrypt: `RSA_DECRYPT_OAEP_2048_SHA256` → ("RSA", 2048)
  - Symmetric: `GOOGLE_SYMMETRIC_ENCRYPTION` → ("AES", 256)
  - MAC: `HMAC_SHA256` → ("HMAC", 256), `HMAC_SHA512` → ("HMAC", 512)
  - External/HSM variants map to the same algorithm — `service_detail` captures protection level

### Cloud SQL TLS Finding Logic
- **D-08:** `sslMode` field from Cloud SQL Admin API v1 response:
  - `"ALLOW_UNENCRYPTED_AND_ENCRYPTED"` → HIGH finding (plaintext connections allowed)
  - `"ENCRYPTED_ONLY"` → MEDIUM finding (encryption required but no client cert)
  - `"TRUSTED_CLIENT_CERTIFICATE_REQUIRED"` → no finding (mTLS enforced — safe)
  - Missing/null → HIGH finding
  Protocol field on CryptoEndpoint: `"CLOUD_SQL"`, service_detail: instance name

### Claude's Discretion
- GCP quantum-safety classification: use the existing `QUANTUM_SAFETY` classifier in
  `quirk/cbom/classifier.py` — no new classification logic needed
- CBOM integration: GCP endpoints flow through existing builder pass 1 (key type → CryptoComponent)
  unchanged — no new CBOM pass or skip-list entry needed
- Connector function signatures: follow `aws_connector.py` style
  (`def _scan_kms(service, project: str, logger) -> List[CryptoEndpoint]`)
- Error handling: per-resource try/except with logger.v() on failure — same as existing connectors

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing Connector Patterns (reference implementations)
- `quirk/scanner/aws_connector.py` — KMS_KEY_SPEC_MAP structure, BOTO3_AVAILABLE optional import, paginator pattern, CryptoEndpoint construction for cloud resources
- `quirk/scanner/azure_connector.py` — DefaultAzureCredential pattern, AZURE_AVAILABLE flag, module-level None assignments for test patching

### Schema Migration Pattern
- `quirk/db.py` — `_IDENTITY_COLUMNS`, `_ensure_identity_columns()` — mirror this exactly for `_GCP_COLUMNS` / `_ensure_gcp_columns()`

### Config Extension
- `quirk/config.py` — `ConnectorsCfg` dataclass — add `enable_gcp` and `gcp_project_id` fields
- `quirk/config_template.yaml` — add matching `enable_gcp: false` / `gcp_project_id: null` under `connectors:`

### Data Model
- `quirk/models.py` — `CryptoEndpoint` ORM model, `cloud_scan_json` TEXT column

### Dependency Structure
- `pyproject.toml` — `[project.optional-dependencies]` section; `[cloud]` group goes after `[identity]`

### Phase Requirements
- `.planning/REQUIREMENTS.md` §GCP Connector — GCP-01, GCP-02, GCP-03 acceptance criteria
- `.planning/REQUIREMENTS.md` §Object Storage — STOR-03 (zero-duplicate GCS API calls)
- `.planning/ROADMAP.md` §Phase 26 and §Phase 28 — dependency relationship and data pass-forward

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `KMS_KEY_SPEC_MAP` in `aws_connector.py`: exact dict structure to replicate as `GCP_KMS_ALGORITHM_MAP`
- `_ensure_identity_columns()` in `db.py`: copy structure for `_ensure_gcp_columns()`
- `CryptoEndpoint` fields already present: `host`, `port`, `protocol`, `cert_pubkey_alg`, `cert_pubkey_size`, `cloud_scan_json`, `service_detail` — no model changes needed beyond new `gcs_scan_json` column

### Established Patterns
- Optional SDK import: `try: import X; AVAILABLE = True except ImportError: X = None; AVAILABLE = False`
- Module-level `None` assignments required for test patching (see azure_connector.py comments)
- Per-resource try/except with `logger.v()` — not logger.warning() — for graceful degradation
- `cloud_scan_json=json.dumps(data, default=str)` on every CryptoEndpoint

### Integration Points
- `quirk/scanner/scan.py` — where `aws_connector` and `azure_connector` are currently invoked;
  GCP connector wired in the same location behind `cfg.connectors.enable_gcp` check
- `run_scan.py` — top-level orchestration; session_start pattern (Phase 24) already in place
- `quirk/cbom/builder.py` — Pass 1 processes `cloud_scan_json`; protocol="GCP" rows flow through
  without special handling (same as "AWS" and "AZURE" rows)

</code_context>

<specifics>
## Specific Ideas

- `service_detail` field on KMS endpoints should encode protection level:
  `"CloudKMS/SOFTWARE"`, `"CloudKMS/HSM"`, `"CloudKMS/EXTERNAL"` — provides richer CBOM output
  than a flat `"CloudKMS"` label
- `gcs_scan_json` stores a JSON array of bucket objects: `[{"name": "...", "encryptionConfig": {...}, ...}, ...]`
  — raw API response per bucket, not pre-processed, so Phase 28 has full flexibility

</specifics>

<deferred>
## Deferred Ideas

- GCP chaos lab profile (mock GCP KMS/Cloud SQL/GCS via LocalStack or similar) — no LocalStack
  GCP support yet; defer until community tooling matures
- Moving boto3 and azure SDK from main deps into `[cloud]` extras — breaking change for existing
  installs; revisit in a dedicated cleanup phase
- `gcp_kms_locations` user-configurable filter — auto-discovery covers all cases; add only if
  performance complaints arise from large projects with many regions

</deferred>

---

*Phase: 26-gcp-connector*
*Context gathered: 2026-04-24*
