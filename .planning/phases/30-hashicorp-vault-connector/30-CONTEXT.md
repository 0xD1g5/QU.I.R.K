# Phase 30: HashiCorp Vault Connector - Context

**Gathered:** 2026-04-26
**Status:** Ready for planning

<domain>
## Phase Boundary

QU.I.R.K. can enumerate HashiCorp Vault cryptographic posture — transit key types
with quantum-safety classification (including PQC key types ml-dsa/slh-dsa as positive
findings), PKI mount CA certificate algorithms (root AND intermediate CA per mount), and
auth method risk assessment — using the hvac Python client with configurable TLS verification.

All findings use `protocol="VAULT"` CryptoEndpoint rows stored in `dat_scan_json`. Transit
keys are classification-only (no severity unless exportable=true). PKI CA certs and
high-risk auth methods carry severity. A dedicated `--profile vault` Docker chaos lab profile
validates all finding paths.

</domain>

<decisions>
## Implementation Decisions

### Transit Key Severity Model
- **D-01:** Transit keys are **classification-only** — no severity is assigned based on algorithm
  type alone. RSA-2048, RSA-3072, AES-256, ed25519, ml-dsa-87 transit keys all appear in the
  CBOM with `cert_pubkey_alg` + `cert_pubkey_size` but no severity. This is intentional: transit
  key algorithm rotation is straightforward; the quantum-safety finding comes from the CBOM
  classification, not a severity flag.
- **D-02:** **Exportable transit keys get MEDIUM severity.** When `read_key()` returns
  `exportable=True`, the CryptoEndpoint gets `severity="MEDIUM"` with a service_detail note and
  remediation text ("Disable key export to prevent key material from leaving Vault."). MEDIUM does
  NOT increment `dar_vault_weak_count` (only HIGH does). This finding is additive — a key can be
  both classified for algorithm AND flagged for exportability.

### PKI Mount CA Certificate Enumeration
- **D-03:** Scanner enumerates **both root CA and intermediate CA** per PKI mount. Call
  `client.secrets.pki.read_ca_certificate(mount_point=...)` for the root cert AND
  `client.secrets.pki.read_ca_certificate_chain(mount_point=...)` for the intermediate chain.
  Each cert (root + each intermediate in the chain) becomes a separate CryptoEndpoint row.
  Severity ladder applies to every cert independently: RSA < 4096-bit → HIGH, SHA-1 signing
  algorithm → HIGH, RSA-4096 with SHA-256 → no finding.
- **D-04:** If `read_ca_certificate_chain` raises an exception (e.g., no intermediate configured),
  the error is silently swallowed — only the root cert endpoint is returned. Sub-scanner isolation
  applies: PKI intermediate failure does not suppress root CA result.

### Auth Method Severity
- **D-05:** Token auth is **always HIGH, unconditional.** Vault cannot disable token auth; it is
  always present. The scanner does not suppress the finding when other safe methods (AppRole,
  Kubernetes, OIDC) are also enabled. Remediation guidance: "Avoid direct use of token auth;
  prefer AppRole, Kubernetes, or OIDC auth methods."
- **D-06:** AUTH_RISK_MAP tiers (from Plan 01, confirmed unchanged):
  - `"token"` → HIGH
  - `"ldap"` → HIGH (LDAP root bind risk)
  - `"userpass"` → MEDIUM
  - `"approle"`, `"kubernetes"`, `"oidc"` → no finding (positive posture, endpoint not emitted)
  - Unknown method types → no finding (graceful unknown handling)

### Chaos Lab Profile
- **D-07:** **Dedicated `--profile vault` Docker Compose profile.** NOT extending the storage
  profile. Separate `hashicorp/vault` dev server container on port 8200. Matches the established
  pattern: one profile per scanner phase (kerberos, saml, dnssec, storage each have their own).
  The chaos lab directory is `quantum-chaos-enterprise-lab/vault/` (not `storage/vault-seed.sh`
  as previously drafted in Plan 03 — Plan 03 must be updated to use this path).
- **D-08:** Chaos lab must pre-seed the following scenarios for RED finding path coverage:
  - Transit RSA-2048 key (classification path — no severity)
  - Transit exportable RSA-2048 key (MEDIUM finding path)
  - PKI mount with RSA-2048 root CA (HIGH finding path via RSA < 4096)
  - Userpass auth method enabled (MEDIUM finding path)
  - Token auth is automatically present in Vault dev mode (HIGH finding path — always fires)

### Connection / TLS Configuration
- **D-09:** Add `vault_tls_verify: bool = True` as the **5th** new ConnectorsCfg field (after
  vault_transit_mount). Passed to `hvac.Client(verify=cfg.connectors.vault_tls_verify)`.
  Consultants connecting to HTTPS Vault with a self-signed cert set `vault_tls_verify: false`
  in config. Default is True (secure). Must be documented in config_template.yaml alongside
  the other four vault fields.
- **D-10:** This adds one field to Plan 01's ConnectorsCfg extension task. The four fields in
  the existing Plan 01 interface spec become five:
  ```python
  enable_vault: bool = False
  vault_addr: Optional[str] = None
  vault_token: Optional[str] = None
  vault_transit_mount: str = "transit"
  vault_tls_verify: bool = True   # NEW — not in existing Plan 01
  ```

### Evidence / Scoring
- **D-11:** `dar_vault_weak_count` increments for HIGH severity VAULT endpoints only: PKI CA
  certs with RSA < 4096 or SHA-1, and token/LDAP auth methods. MEDIUM severity (exportable
  transit keys, userpass auth) does NOT increment `dar_vault_weak_count`.
- **D-12:** `dar_vault_weak_ratio` weight: `8.0` in `SCORE_WEIGHTS` (between
  `dar_storage_unencrypted_ratio: 12.0` and `dar_storage_aws_managed_ratio: 4.0`).
- **D-13:** NUM_SUBSCORES stays 5. `dar_vault_weak_ratio` appends to existing `dar_impacts` in
  `scoring.py` — NOT a new sixth subscore. Pitfall 7 from 30-RESEARCH.md applies.

### CBOM Integration
- **D-14:** CBOM Pass 1 NOT skipped for VAULT — transit key endpoints produce
  `CryptographicAsset` algorithm components (this is the primary value of transit key scanning).
- **D-15:** CBOM Pass 2 (cert skip list) and Pass 3 (protocol skip list) include `"VAULT"` to
  avoid hollow `X.509 CertificateProperties` and `crypto/protocol/tls/` components for Vault
  endpoints.

### Structural / ISSUE-2/ISSUE-3 Requirements
- **D-16:** `hvac>=2.4.0` must be explicitly added to `[cloud]` extras in `pyproject.toml`
  (ISSUE-2 pattern). Phase comment: `# Phase 30: HashiCorp Vault connector (VAULT-01/02/03)`.
- **D-17:** `scan_vault_targets()` must accept a `session_start` parameter (ISSUE-3 pattern).
  All CryptoEndpoints stamped with `(session_start or datetime.now(timezone.utc)).replace(tzinfo=None)`.

### Claude's Discretion
- Exact `service_detail` format for transit key endpoints (e.g., `"transit/my-key-name"` or
  `"VAULT:transit/my-key-name"`) — follow the most recent connector analog.
- Exact remediation text wording for auth method and exportable key findings — follow the tone
  of existing DNSSEC and Kerberos finding descriptions.
- Vault dev server Docker image version and init command — use `hashicorp/vault:1.17` or latest
  stable; `VAULT_DEV_ROOT_TOKEN_ID=root` for reproducible test token.
- Whether the vault-seed script is a shell script (`.sh`) or a Docker entrypoint command sequence.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Reference Connector Implementations (primary patterns to mirror)
- `quirk/scanner/gcp_connector.py` — optional import guard pattern (`GCP_AVAILABLE`/module-level
  None); `_scan_kms()` → key type lookup in a dict map → CryptoEndpoint construction; this is
  the closest analog to vault_connector.py
- `quirk/scanner/aws_connector.py` — `_scan_rds_encryption()` sub-scanner pattern, boto3 session
  reuse, BOTO3_AVAILABLE flag, ThreadPoolExecutor usage
- `quirk/scanner/k8s_connector.py` — Phase 29 (most recent scanner); session_start propagation,
  RBAC-403 graceful degradation, dat_scan_json usage

### Schema and ORM
- `quirk/db.py` — `_V43_COLUMNS` / `_ensure_v43_columns()`; `dat_scan_json` TEXT column already
  exists from Phase 27; do NOT add new columns for Phase 30
- `quirk/models.py` — `CryptoEndpoint` ORM model with `dat_scan_json` field

### Config Extension
- `quirk/config.py` — `ConnectorsCfg` dataclass; add 5 vault fields (D-10): `enable_vault`,
  `vault_addr`, `vault_token`, `vault_transit_mount`, `vault_tls_verify`
- `quirk/config_template.yaml` — `connectors:` section; add 5 matching commented entries after
  Phase 29 K8s fields

### Intelligence / Scoring (Phase 27/28 baseline patterns)
- `quirk/intelligence/evidence.py` — `_PROTOCOL_KEYS` list + `dar_db_plaintext_count` /
  `dar_storage_unencrypted_count` / `dar_k8s_unencrypted_count` patterns; add `dar_vault_weak_count`
  alongside
- `quirk/intelligence/scoring.py` — `SCORE_WEIGHTS` dict, `dar_impacts` list in
  `compute_readiness_score()`; add `dar_vault_weak_ratio: 8.0` weight

### CBOM Builder
- `quirk/cbom/builder.py` — Pass 1 / Pass 2 cert skip tuple / Pass 3 protocol skip tuple
  structure; `"VAULT"` added to Pass 2 + Pass 3 only, NOT Pass 1 (D-14, D-15)

### Chaos Lab
- `quantum-chaos-enterprise-lab/docker-compose.yml` — existing `profiles:` structure; add vault
  service under `profile: [vault]` (NOT piggybacking on storage profile)
- `quantum-chaos-enterprise-lab/labs/storage/expected_results.md` — see Phase 28 format; create
  `labs/vault/expected_results.md` for Vault scenarios

### Phase-Specific Research
- `.planning/phases/30-hashicorp-vault-connector/30-RESEARCH.md` — VAULT_TRANSIT_KEY_MAP rows,
  AUTH_RISK_MAP, PKI severity ladder, Open Question 1 (auto-discovery), Pitfall 2 (PEM parsing),
  Pitfall 3 (mount_point trailing slash), Pitfall 7 (NUM_SUBSCORES must stay 5)
- `.planning/phases/30-hashicorp-vault-connector/30-PATTERNS.md` — codebase patterns for
  vault_connector.py

### Phase Dependencies
- `.planning/phases/27-database-encryption-detection/27-CONTEXT.md` — D-07 (`dat_scan_json`
  column), D-08 (dar_ subscore architecture)
- `.planning/phases/28-object-storage-audit/28-CONTEXT.md` — D-09 (dar_storage_* counter
  pattern to mirror for dar_vault_*)
- `.planning/phases/29-kubernetes-secrets-inspection/29-CONTEXT.md` — most recent scanner
  module pattern (if it exists)

### Requirements
- `.planning/REQUIREMENTS.md` §HashiCorp Vault — VAULT-01, VAULT-02, VAULT-03 acceptance
  criteria

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `aws_connector.py:_scan_kms()` — key type string → (alg_name, key_size) dict lookup is exactly
  the `VAULT_TRANSIT_KEY_MAP.get(key_type, ("UNKNOWN", None))` pattern
- `gcp_connector.py` lines 22-32 — optional import guard with module-level `None` for hvac:
  `try: import hvac; HVAC_AVAILABLE = True; except ImportError: hvac = None; HVAC_AVAILABLE = False`
- `k8s_connector.py` — most recent Phase 29 scanner: RBAC-403 → scan_error, sub-scanner isolation,
  session_start propagation; read before implementing vault_connector.py
- `evidence.py:_PROTOCOL_KEYS` — list that must include `"VAULT"` for endpoint counting
- `scoring.py:IMPACT_WEIGHTS` / `dar_impacts` — pattern to append `dar_vault_weak_ratio: 8.0`

### Established Patterns
- TDD RED+GREEN: Plan 01 = RED scaffold + config, Plan 02 = GREEN scanner + run_scan.py wiring,
  Plan 03 = intelligence + CBOM + chaos lab + docs
- Optional SDK guard: `HVAC_AVAILABLE` flag + module-level `None` assignments for test patching
- Per-resource try/except with `logger.v()` (not `logger.warning()`) for graceful degradation
- Sub-scanner isolation: PKI failure must not suppress transit/auth results (per test contract)
- `dat_scan_json = json.dumps(..., default=str)` on every CryptoEndpoint (all v4.3 connectors)

### Integration Points
- `run_scan.py` — add `vault_scanning` phase block gated on `cfg.connectors.enable_vault`, after
  the k8s_scanning block; append `+ vault_endpoints` to the endpoint aggregation tuple
- `quirk/cbom/builder.py` — Pass 2 cert skip tuple + Pass 3 protocol skip tuple (add "VAULT")
- `quantum-chaos-enterprise-lab/docker-compose.yml` — new `vault` service under `profile: [vault]`

</code_context>

<specifics>
## Specific Ideas

- Vault chaos lab: `hashicorp/vault:1.17` (or latest stable) dev server, `VAULT_DEV_ROOT_TOKEN_ID=root`
  for reproducible token in tests. Seed script configures PKI mount (RSA-2048 root CA), userpass
  auth method, and an exportable RSA-2048 transit key. Token auth is automatically present in dev mode.
- `vault_tls_verify: bool = True` enables consultant workflows with self-signed HTTPS Vault by
  setting `vault_tls_verify: false` in config — avoids requiring certificate bundle configuration.
- The vault chaos lab expected results file goes in `labs/vault/expected_results.md` (parallel to
  `labs/storage/expected_results.md` from Phase 28).
- PKI intermediate CA: if `read_ca_certificate_chain` returns an empty string or raises, emit only
  the root CA endpoint without error. Do not add a `vault-no-intermediate-ca` scan_error finding —
  many Vault PKI mounts have no intermediate configured.

</specifics>

<deferred>
## Deferred Ideas

- **Vault Enterprise namespace** (`vault_namespace` config field for HCP Vault / Enterprise
  multi-tenant environments) — deferred; open-source Vault only for v4.3.
- **Transit key version history** — Vault tracks key rotation (multiple_versions). Enumerating
  historical key versions and flagging stale old versions is deferred to a future phase.
- **PKI intermediate CA chain deduplication** — comparing cert fingerprints to skip duplicates
  between root and intermediate chain — deferred; overkill for v4.3.
- **Vault audit log analysis** — reading Vault audit logs to detect suspicious auth patterns —
  requires audit log file access; deferred to v4.4+.
- **Vault namespace / Enterprise chaos lab scenario** — deferred with namespace support above.

</deferred>

---

*Phase: 30-hashicorp-vault-connector*
*Context gathered: 2026-04-26*
