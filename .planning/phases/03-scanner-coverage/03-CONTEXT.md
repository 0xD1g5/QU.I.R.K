# Phase 3: Scanner Coverage - Context

**Gathered:** 2026-03-29 (assumptions mode)
**Status:** Ready for planning

<domain>
## Phase Boundary

QU.I.R.K. discovers cryptographic material across every major attack surface — APIs/JWT, containers/binaries, source code, and cloud key management (AWS + Azure). TLS and SSH scanners are NOT in scope (Phase 1). Chaos lab targets for these scanners are NOT in scope (Phase 4). No UI changes (Phase 5).

</domain>

<decisions>
## Implementation Decisions

### CryptoEndpoint Model Extension
- **D-01:** Add one nullable JSON blob column per new scanner surface, following the `tls_capabilities_json` / `ssh_audit_json` pattern from Phase 1 (D-05). New columns: `jwt_scan_json TEXT`, `container_scan_json TEXT`, `source_scan_json TEXT`, `cloud_scan_json TEXT`. All additive — no breaking schema migrations.
- **D-02:** Use the existing `protocol` field (`String(32)`) as the scanner-type discriminator for the CBOM builder. New protocol values: `"JWT"`, `"CONTAINER"`, `"SOURCE"`, `"AWS"`, `"AZURE"`. The CBOM builder already branches on `ep.protocol == "SSH"` — extend this branching to handle all five new types.

### Scanner Integration in run_scan.py
- **D-03:** Each new scanner follows the established pattern: guarded block in `run_scan.py`, function returns `List[CryptoEndpoint]`, merged into `endpoints` before `evaluate_endpoints()` and `write_reports()`. No scanner result is processed in isolation — all flow through the CBOM pipeline.
- **D-04:** New scanner enable flags added to `ConnectorsCfg` (or a new `ScannersCfg` section): `enable_jwt`, `enable_container`, `enable_source`. Cloud connectors reuse the existing `enable_aws` / `enable_azure` booleans already in `quirk/config.py`.

### JWT/API Scanner (SCAN-03)
- **D-05:** JWT endpoints are configured explicitly in config (not discovered by CIDR sweep). Users specify a list of API base URLs. The scanner fetches `/.well-known/jwks.json` (and configurable JWKS path), parses each key entry (alg, kty, n/e for RSA key size), and optionally probes known JWT-issuing paths.
- **D-06:** Python-native: `httpx` (or `requests`) for HTTP, `PyJWT` / `python-jose` for token parsing. No subprocess — these are pip-installable. Graceful degradation if no JWT targets configured.
- **D-07:** Each JWKS key becomes one `CryptoEndpoint` row: `protocol="JWT"`, `host=<api_base_url>`, `port=443`, `cert_pubkey_alg=<alg>`, `cert_pubkey_size=<key_bits>`, `jwt_scan_json=<full key entry JSON>`.

### Container/Binary Scanner (SCAN-04)
- **D-08:** Syft subprocess only (not Trivy) for SBOM generation. Syft is SBOM-focused; Trivy adds vuln scanning outside Phase 3 scope. Command: `syft <image> -o json`, parse `artifacts` array, filter by crypto library name allowlist (openssl, libssl, libcrypto, botan, libgcrypt, nss, mbedtls, wolfssl, python-cryptography, pyOpenSSL, etc.).
- **D-09:** Each matching artifact becomes one `CryptoEndpoint` row: `protocol="CONTAINER"`, `host=<image_ref>`, `port=0`, `cipher_suite=<library_name>`, `tls_version=<library_version>`, `container_scan_json=<full artifact JSON>`.
- **D-10:** Graceful degradation: if `syft` binary is not on PATH, log a warning and skip — do not hard-fail. Match the ssh-audit not-installed behavior.

### Source Code Scanner (SCAN-05)
- **D-11:** Use `semgrep` with crypto-detection rules — NOT CBOMkit Hyperion (which is a Java SonarQube plugin requiring a running SonarQube server, incompatible with the offline/air-gapped consultant use case). Semgrep is pip-installable and runs offline.
- **D-12:** Run semgrep with `--config auto` (or a bundled ruleset targeting crypto imports) via subprocess: `semgrep --json --config p/cryptography <repo_path>`. Parse JSON output `results` array — each finding includes `path`, `start.line`, `check_id`, `extra.message`.
- **D-13:** Each semgrep finding becomes one `CryptoEndpoint` row: `protocol="SOURCE"`, `host=<repo_path>`, `port=0`, `cipher_suite=<rule_id>`, `service_detail=<file:line>`, `source_scan_json=<full finding JSON>`.
- **D-14:** Graceful degradation: if `semgrep` is not installed, log warning and skip. Source scanning is opt-in (config flag).

### Cloud Connectors (SCAN-06/07)
- **D-15:** AWS connector uses boto3 ambient credential resolution (env vars → `~/.aws/credentials` → instance profile). No credentials stored in `config.yaml`. Add `aws_region` (required when `enable_aws: true`) and optional `aws_profile` to `ConnectorsCfg`.
- **D-16:** Azure connector uses `DefaultAzureCredential` from `azure-identity`. No credentials stored in config. Add `azure_subscription_id` (required when `enable_azure: true`) to `ConnectorsCfg`.
- **D-17:** AWS surfaces: ACM certificates (`acm.list_certificates`), KMS key specs (`kms.list_keys` + `describe_key`), CloudFront TLS policies (`cloudfront.list_distributions`), ELB/ALB listeners (`elbv2.describe_listeners`). Each resource becomes one `CryptoEndpoint` row: `protocol="AWS"`, `host=<resource_arn>`, `cloud_scan_json=<resource metadata JSON>`.
- **D-18:** Azure surfaces: Key Vault certificates + keys (`azure-keyvault-certificates`, `azure-keyvault-keys`), App Gateway TLS policies (`azure-mgmt-network` `ApplicationGatewaysOperations`). Each resource: `protocol="AZURE"`, `host=<resource_id>`, `cloud_scan_json=<resource metadata JSON>`.

### CBOM Builder Extension
- **D-19:** Extend `quirk/cbom/builder.py` to handle the new protocol values. JWT → `AlgorithmProperties` component (alg + key size). Container → `CryptographicLibrary` component (name + version). Source → `AlgorithmProperties` component (algorithm detected, file location in properties). Cloud → `CryptographicLibrary` or `AlgorithmProperties` depending on resource type (KMS key spec → algorithm; ACM cert → certificate component).

### Claude's Discretion
- Exact semgrep ruleset selection (`p/cryptography` vs bundled custom rules)
- Crypto library allowlist for container scanner (exact package names)
- JWT path probing beyond `/.well-known/jwks.json` (e.g., `/oauth/jwks`, `/auth/keys`)
- boto3 pagination handling strategy for large AWS accounts
- Whether to add `aws_region` as a list (multi-region scan) or single string

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing scanner patterns
- `quirk/scanner/tls_scanner.py` — Primary TLS scanner; establishes ThreadPoolExecutor + CryptoEndpoint return pattern
- `quirk/scanner/ssh_scanner.py` — ssh-audit subprocess pattern; graceful degradation when tool absent
- `run_scan.py` — Full orchestration; lines 315-356 show guarded scanner phase blocks + endpoint merge

### Data model
- `quirk/models.py` — CryptoEndpoint SQLAlchemy model; all new columns must be additive nullable Text

### CBOM pipeline (Phase 2 output — must integrate)
- `quirk/cbom/builder.py` — `build_cbom(endpoints)` entry point; extend branching for new protocol values
- `quirk/cbom/classifier.py` — Algorithm lookup table; new algorithms from JWT/cloud sources need entries

### Config
- `quirk/config.py` — `ConnectorsCfg` class; add `aws_region`, `aws_profile`, `azure_subscription_id` + new scanner enable flags

### Requirements
- `.planning/REQUIREMENTS.md` §SCAN-03…SCAN-07 — Acceptance criteria for each new scanner
- `.planning/ROADMAP.md` §Phase 3 — Success criteria (5 items, each maps to one scanner)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `run_scan.py` `_get_scan_int()` / `_phase_timer()` — Config accessor and timing helpers; use for new scanner phases
- `quirk/scanner/ssh_scanner.py` `_run_ssh_audit()` — Subprocess-with-JSON-parse pattern; clone for syft and semgrep subprocess wrappers
- `quirk/scanner/tls_scanner.py` `SSLYZE_AVAILABLE` flag + try/except ImportError — Graceful degradation pattern for optional Python deps
- `quirk/cbom/classifier.py` `_ALGORITHM_TABLE` — Algorithm → CryptoPrimitive lookup; extend with JWT alg values (RS256, HS256, ES256, etc.)
- `quirk/engine/profiles.py` — Scan profile system; new scanner enable flags should respect profile settings

### Established Patterns
- JSON blob per scanner: `tls_capabilities_json` (sslyze deep data) and `ssh_audit_json` (full ssh-audit output) are the precedent
- Protocol as discriminator: CBOM builder already branches on `ep.protocol == "SSH"` at `builder.py:274,307`
- Graceful degradation: `SSLYZE_AVAILABLE` and ssh-audit `shutil.which()` patterns are canonical
- ThreadPoolExecutor for concurrent scanning — use for JWT endpoint list and container image list

### Integration Points
- `run_scan.py` line 356: `endpoints = inventory_endpoints + tls_endpoints + ssh_endpoints` — add new scanner lists here
- `quirk/cbom/builder.py` protocol branch — extend to handle `"JWT"`, `"CONTAINER"`, `"SOURCE"`, `"AWS"`, `"AZURE"`
- `quirk/config.py` `ConnectorsCfg` — additive fields: `aws_region`, `aws_profile`, `azure_subscription_id`, `enable_jwt`, `enable_container`, `enable_source`
- `quirk/models.py` `CryptoEndpoint` — additive columns at end of model definition

</code_context>

<specifics>
## Specific Ideas

- Source scanner: `semgrep` chosen over CBOMkit Hyperion (Java SonarQube plugin — incompatible with offline CLI use case) and over regex/AST (insufficient coverage). Use `semgrep --json --config p/cryptography`.
- Container scanner: Syft only (not Trivy). Parse `artifacts` array from `syft <image> -o json`. Filter by crypto library allowlist.
- Cloud connectors: ambient credentials only — no credential storage in config. AWS needs `aws_region`; Azure needs `azure_subscription_id`.
- JWT scanner: JWKS-first approach (`/.well-known/jwks.json`). Each JWKS key entry → one CryptoEndpoint.

</specifics>

<deferred>
## Deferred Ideas

- Trivy vulnerability scanning on containers — separate concern from crypto library inventory; could be Phase 4 or backlog
- Multi-region AWS scanning (single region in Phase 3) — backlog
- Azure Front Door / CDN TLS scanning — backlog, lower priority than Key Vault + App Gateway
- SonarQube / CBOMkit Hyperion integration — requires running SonarQube server; too heavy for v1 consultant tool
- Email / S/MIME scanning — already in project Out of Scope for v1

## Reviewed Todos (not folded)

None — no pending todos matched Phase 3 scope.

</deferred>

---

*Phase: 03-scanner-coverage*
*Context gathered: 2026-03-29*
