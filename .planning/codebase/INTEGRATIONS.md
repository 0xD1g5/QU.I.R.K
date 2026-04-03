# External Integrations

**Analysis Date:** 2026-04-02

## APIs & External Services

**JWKS / OIDC Discovery (active):**
- Any OIDC/OAuth2 identity provider exposing a JWKS endpoint
  - Probed paths: `/.well-known/jwks.json`, `/oauth/jwks`, `/.well-known/openid-configuration`
  - Client: `httpx` (sync, `verify=False`, follows redirects)
  - Auth: None — reads public key material only
  - Config: `connectors.jwt_targets` list in `config.yaml`
  - Implementation: `quirk/scanner/jwt_scanner.py`

**CycloneDX SBOM/CBOM format (active):**
- No network call — uses the `cyclonedx-python-lib` library to serialize Bom objects
- Output format: CycloneDX 1.6 JSON and XML
- Implementation: `quirk/cbom/builder.py`, `quirk/cbom/writer.py`

## Data Storage

**Databases:**
- SQLite (single file)
  - Default path: `output/quirk.db` (configurable via `config.yaml` → `output.db_path`)
  - Client: SQLAlchemy 2.0 ORM (`quirk/db.py`)
  - Table: `crypto_endpoints` (single table; see `quirk/models.py`)
  - No migrations framework — schema is created with `Base.metadata.create_all()` on each run
  - Sessions: `get_session()` context manager with `expire_on_commit=False`

**File Storage:**
- Local filesystem only
- Output directory: `output/` (configurable via `config.yaml` → `output.directory`)
- Artifacts written per-scan: `findings-*.json`, `intelligence-*.json`, `executive-summary-*.md`, `technical-findings-*.md`, `scorecard-*.md`, `roadmap-*.md`, `report-*.html`, `report-*.pdf`, `cbom-*.cdx.json`, `cbom-*.cdx.xml`, `run-stats-*.json`
- Discovery cache: `output/.cache/` (JSON files, TTL-controlled)

**Caching:**
- Custom file-based JSON cache in `output/.cache/`
- Keys hashed from config scope (targets, ports, mode) via `quirk/engine/cache.py`
- TTL: `--cache-ttl-hours` (default 24h)
- Activated by `--cache` and `--resume` flags

## Authentication & Identity

**AWS:**
- Auth: Ambient `boto3.Session` — resolves credentials in order: env vars → `~/.aws/credentials` named profile → instance role/ECS task role
- No credentials stored in code
- Implementation: `quirk/scanner/aws_connector.py`
- Config: `connectors.aws_region` (default `us-east-1`), optional `connectors.aws_profile`

**Azure:**
- Auth: `DefaultAzureCredential` from `azure-identity`
  - Resolution order: env vars (`AZURE_CLIENT_ID`, etc.) → Azure CLI login → managed identity → Visual Studio Code credential
- No credentials stored in code
- Implementation: `quirk/scanner/azure_connector.py`
- Config: `connectors.azure_subscription_id`, `connectors.azure_keyvault_urls`

**No application-level auth:**
- The dashboard (`quirk serve`) binds to `127.0.0.1` only — no authentication layer
- No JWT verification, no API keys, no session management

## Cloud Service Integrations

**AWS (active, optional):**
- Services scanned: ACM certificates, KMS keys, CloudFront distributions, ELBv2 HTTPS listeners
- SDK: `boto3` (all four services use paginator-based enumeration)
- Enabled by: `connectors.enable_aws: true` in config
- Falls back gracefully with empty result list if `boto3` not installed (import guarded)
- Implementation: `quirk/scanner/aws_connector.py`

**Azure (active, optional):**
- Services scanned: Key Vault keys (via `azure-keyvault-keys`), App Gateway TLS policies (via `azure-mgmt-network`)
- Note: `azure-keyvault-certificates` is installed and in `pyproject.toml` but `CertificateClient` is imported at module level and set to `None` on ImportError — it is never actually instantiated in the current implementation. Only `KeyClient` is used.
- SDK: `azure-identity` + `azure-keyvault-keys` + `azure-mgmt-network`
- Enabled by: `connectors.enable_azure: true` in config
- Falls back gracefully if azure SDK not installed
- Implementation: `quirk/scanner/azure_connector.py`

**GCP:** Not implemented. Planned as future phase (`999.10-gcp-connector`).

**HashiCorp Vault:** Not implemented. Planned as future phase (`999.19-hashicorp-vault-live-connector`).

**Windows AD CS:** Stub only (`quirk/connectors/windows_adcs_stub.py` — 3 lines of comments). Planned future work.

## External Tool Integrations (System Binaries)

**sslyze (optional, not installed):**
- Purpose: Deep TLS cipher suite enumeration, full protocol matrix (SSLv2 through TLS 1.3)
- Integration: Optional Python package; imported with try/except guard at module top
- Status: NOT installed in active `.venv`. `SSLYZE_AVAILABLE = False` at runtime.
- Fallback: stdlib `ssl` + `cryptography` scanner (`_scan_one_fallback` in `quirk/scanner/tls_scanner.py`)
- Would be enabled by: `pip install sslyze`

**ssh-audit (optional):**
- Purpose: SSH algorithm audit — KEX, host key, encryption, MAC algorithm enumeration
- Integration: External binary located at runtime via `shutil.which("ssh-audit")`
- Invoked: `ssh-audit -j <host> <port>` (JSON output)
- Fallback: TCP banner grab if binary not found
- Implementation: `quirk/scanner/ssh_scanner.py`
- Install: `pip install ssh-audit` (installs as `ssh-audit` binary)

**syft (optional):**
- Purpose: Container/OCI image SBOM — enumerate crypto library packages
- Integration: External binary located via `shutil.which("syft")`
- Invoked: `syft <image_ref> -o json`
- Fallback: Returns empty list if not found
- Filters output to allowlisted crypto library names only (openssl, libssl, cryptography, pycryptodome, etc.)
- Implementation: `quirk/scanner/container_scanner.py`
- Install: `brew install syft` (macOS)

**semgrep (optional):**
- Purpose: Source code static analysis for insecure crypto usage
- Integration: External binary located via `shutil.which("semgrep")`
- Invoked: `semgrep --json --config p/cryptography <repo_path>`
- Uses Semgrep's public `p/cryptography` ruleset (requires internet access on first run)
- Fallback: Returns empty list if not found
- Implementation: `quirk/scanner/source_scanner.py`
- Install: `pip install semgrep`

**nmap (optional):**
- Purpose: Network port discovery pre-scan
- Integration: External binary; path configurable via `--nmap-path` (default `nmap` in PATH)
- Invoked: `nmap -sT -n -Pn --open -p <ports> -oX <output.xml> <targets>`
- XML output parsed by `quirk/discovery/nmap_parser.py`
- Only active with `--discovery nmap` flag
- Fallback: Built-in socket-based fingerprinting (default discovery mode)
- Implementation: `quirk/discovery/nmap_provider.py`

**Playwright / Chromium (optional):**
- Purpose: PDF report generation from HTML
- Integration: Python `playwright` package (`pip install playwright && playwright install chromium`)
- Two code paths:
  1. CLI scan: `render_pdf_report()` in `quirk/reports/html_renderer.py` — opens local HTML file
  2. Dashboard: `POST /api/export/pdf` in `quirk/dashboard/api/routes/pdf.py` — navigates to `/print` route on running server
- Fallback: HTML report still written if Playwright unavailable; PDF path set to None
- Requires: `playwright install chromium` (~150MB one-time download, not automated)

## Monitoring & Observability

**Error Tracking:** None installed or configured.

**Logs:**
- Custom `Logger` class (`quirk/logging_util.py`) — thread-safe stdout printing
- Verbose mode: `--verbose` flag enables `.v()` level messages
- No structured logging, no log files, no external log sink

## CI/CD & Deployment

**Hosting:** Local/self-hosted only. No cloud deployment target.

**CI Pipeline:** None detected. No `.github/workflows/`, no `Makefile` targets.

**Frontend Build Pipeline:**
- `npm run build` in `src/dashboard/` → output goes to `quirk/dashboard/static/`
- Vite build; TypeScript compiled before bundle
- Built assets are committed to the repo (`quirk/dashboard/static/assets/`)

## Webhooks & Callbacks

**Incoming:** None.

**Outgoing:** None. All external calls are outbound reads (TLS handshakes, AWS/Azure API calls, JWKS fetches) — no webhook delivery or event publishing.

## Environment Configuration

**Required for core scan:**
- No required environment variables for basic TLS/SSH scanning
- `config.yaml` with valid `targets` block

**Required for cloud connectors:**
- AWS: Requires ambient credentials (env vars, `~/.aws/credentials`, or instance role)
  - `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION` (if not using named profile)
- Azure: Requires `DefaultAzureCredential`-compatible auth
  - `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_TENANT_ID` (service principal)
  - Or: `az login` (Azure CLI)

**Dashboard only:**
- `QUIRK_SERVE_PORT` — read by `quirk/dashboard/api/routes/pdf.py`; defaults to `8512`

**Secrets location:**
- No secrets stored in repo
- Cloud credentials via ambient provider chains only

## Chaos Lab (quantum-chaos-enterprise-lab/)

The `quantum-chaos-enterprise-lab/` directory contains Docker Compose test infrastructure — not part of the application runtime:
- `nginx/` — various TLS misconfiguration scenarios (expired certs, SSLv3, mTLS, legacy)
- `haproxy/` — HAProxy TLS termination scenario
- `jwt/` — Four FastAPI JWT services with different vulnerabilities: `algnone`, `hs256`, `rs256`, `rsa1024`
  - Each has its own `requirements.txt` pinning `fastapi==0.111.0`, `uvicorn==0.29.0`, `PyJWT>=2.8.0`
  - These pin much older versions than the main application (fastapi 0.111 vs >=0.128.8)
- `certs/` — Test certificates including step-CA scenarios

---

*Integration audit: 2026-04-02*
