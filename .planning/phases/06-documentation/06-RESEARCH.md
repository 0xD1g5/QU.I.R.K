# Phase 6: Documentation - Research

**Researched:** 2026-03-31
**Domain:** Technical documentation — Markdown guide suite for a Python CLI security tool
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Create `docs/` folder at repo root with one Markdown file per guide:
  ```
  docs/
    getting-started.md
    installation.md
    configuration.md
    connectors/
      aws.md
      azure.md
      docker.md
      git.md
    report-interpretation.md
    cbom-guide.md
    chaos-lab.md
  ```
- **D-02:** Update `README.md` as clean product intro with links into `docs/`. Current README is stale (qcscan/Quantum Crypto Scanner pre-Phase 1 content). README = product intro + Quick Start snippet + links to full docs.
- **D-03:** Plain Markdown, no build step. Works on GitHub, readable offline, air-gapped engagements. Phase 7 can layer MkDocs/Material skin on top without restructuring.
- **D-04:** Primary install path is development install:
  ```bash
  git clone ...
  cd quirk
  python -m venv .venv && source .venv/bin/activate
  pip install -e '.[dashboard]'
  playwright install chromium
  quirk --help
  ```
- **D-05:** Add callout box with future PyPI path (Phase 7 promotes it to primary).
- **D-06:** Getting Started must achieve < 10 min from clean macOS or Linux. Cover: Python 3.10+ check, venv creation, install, config.yaml minimal setup (127.0.0.1 target), first scan, `quirk serve`, open browser.
- **D-07:** Windows WSL covered in `installation.md` (separate section, not Getting Started main path).
- **D-08:** Report interpretation guide uses two-layer structure: (1) reference table, (2) "Client Conversation" sidebox per major section.
- **D-09:** Source score labels and thresholds from `quirk/intelligence/scoring.py`. Severity thresholds from `quirk/engine/` risk rules.
- **D-10:** CBOM guide: three sections — (1) what a CBOM is for compliance officers, (2) how QU.I.R.K. produces it, (3) how to cite as compliance evidence (NIST SP 800-208, CNSA 2.0 mappings).
- **D-11:** AWS guide: least-privilege IAM policy JSON (read-only ACM + KMS + CloudFront + ELBv2), config.yaml snippet, boto3 credential chain explanation.
- **D-12:** Azure guide: RBAC role definition, config.yaml snippet, env var list (AZURE_CLIENT_ID, AZURE_TENANT_ID, AZURE_CLIENT_SECRET).
- **D-13:** Docker connector guide: Docker socket access, Syft requirement, scan target config. Git connector: Gitea/GitHub access, semgrep dependency.
- **D-14:** New `docs/chaos-lab.md` covering ALL profiles (core + phaseA + cloud + identity + pki + jwt + registry + source + storage + ssh-weak + ldaps).
- **D-15:** Existing `quantum-chaos-enterprise-lab/CHAOS_LAB_BUILD_AND_OPERATIONS_text_only.md` stays as historical artifact. New `docs/chaos-lab.md` is authoritative. Update chaos lab `README.md` to link to `docs/chaos-lab.md`.
- **D-16:** `docs/chaos-lab.md` includes `expected_results_v3.md` port matrix inline.
- **D-17:** Document every top-level key in `config.yaml`. Include defaults, valid ranges, scan profile differences (quick/standard/deep), required vs optional.
- **D-18:** Include CLI flag reference from `run_scan.py` argparse: `--config`, `--profile`, `--targets`. `quirk serve` flags: `--port`, `--no-open`.

### Claude's Discretion
- Exact Markdown formatting, heading hierarchy, and code block style within each guide
- Whether connectors subdirectory uses individual files or a single `connectors.md`
- Ordering of topics within the configuration reference
- Specific IAM policy JSON (derive from what connectors actually call in `quirk/connectors/`)

### Deferred Ideas (OUT OF SCOPE)
- Full narrative onboarding guide (story-format training document for new team members) — captured for backlog.

</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DOC-01 | Getting Started guide — zero-to-first-scan in under 10 minutes | Install sequence verified from pyproject.toml entry points and config.yaml defaults |
| DOC-02 | Installation guide — macOS, Linux, Windows via WSL; system requirements | Python 3.10+ requirement confirmed in pyproject.toml `requires-python` |
| DOC-03 | Configuration reference — all config.yaml options documented | All keys extracted from config.yaml + ConnectorsCfg dataclass + run_scan.py argparse |
| DOC-04 | Connector setup guides — AWS, Azure, Docker, Git with least-privilege credential templates | Exact boto3 API calls extracted from aws_connector.py; Azure SDK calls from azure_connector.py |
| DOC-05 | Report interpretation guide — what each score/finding means, what to tell the client | Score bands, subscore weights, rating thresholds, finding titles/severities all extracted from source |
| DOC-06 | CBOM guide — what it is, how to use it for compliance evidence | CycloneDX 1.6 schema, quantum_safety_label(), NIST PQC levels confirmed from classifier.py |
| DOC-07 | Chaos lab operator guide — updated for all new profiles | All profiles and ports confirmed from docker-compose.yml and expected_results_v3.md |

</phase_requirements>

---

## Summary

Phase 6 is purely a documentation phase — no new code, no schema changes, no scanner work. The codebase is complete through Phase 5. The task is to extract the ground truth from source files and write a guide suite that enables a consultant with zero prior exposure to install, scan, and present results to a client entirely from the docs.

The documentation strategy is plain Markdown in a `docs/` folder at the repo root (D-03). This is the correct choice: no build tooling, works on GitHub, printable for air-gapped engagements, and MkDocs can wrap it in Phase 7 without restructuring. The existing `README.md` must be completely replaced — it still refers to `qcscan` and `Quantum Crypto Scanner` from pre-Phase 1.

The most technically dense work is the Report Interpretation Guide (DOC-05) and CBOM Guide (DOC-06), both of which require accurate extraction from `scoring.py`, `risk_engine.py`, and `classifier.py`. These files have been read in full for this research; the exact numbers are documented below. The Chaos Lab Operator Guide (DOC-07) requires assembling the complete port matrix from all 10 profiles across the docker-compose.yml — that data is also extracted here.

**Primary recommendation:** Write each guide against the verified source data extracted in this research. The scoring model, severity tiers, IAM permissions, and port matrices below should be used verbatim — do not derive them again from the files during planning or implementation.

---

## Standard Stack

### Core
| Component | Version/Spec | Purpose | Notes |
|-----------|-------------|---------|-------|
| Markdown | CommonMark (GitHub-flavored) | All guide content | No build step required (D-03) |
| `docs/` folder | Repo root | Guide home | Created fresh — does not exist yet |
| `README.md` | Repo root | Product intro + Quick Start + links | Full replacement required |

### Supporting
| Component | Version/Spec | Purpose | When to Use |
|-----------|-------------|---------|-------------|
| Code fences with language tags | `bash`, `yaml`, `json`, `python` | All code samples | Every command block and config snippet |
| Callout/admonition pattern | `> **Note:**` blockquote | Future PyPI path note, WSL warnings, platform caveats | Per D-05 guidance |
| Table syntax | GFM pipe tables | Score reference tables, port matrices, config key tables | Reference sections |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Plain Markdown | MkDocs/Material | MkDocs requires Python build step; deferred to Phase 7 per D-03 |
| Plain Markdown | Sphinx | Too heavy for a dev-install guide suite; RST syntax unfamiliar to consultants |
| Individual connector files under `connectors/` | Single `connectors.md` | Individual files (D-01 spec) allow direct links per cloud provider from other docs |

---

## Architecture Patterns

### Recommended Project Structure (to be created)
```
docs/
  getting-started.md       # DOC-01: zero-to-first-scan < 10 min
  installation.md          # DOC-02: macOS / Linux / Windows WSL
  configuration.md         # DOC-03: config.yaml + CLI flags reference
  connectors/
    aws.md                 # DOC-04: boto3, IAM policy, config snippet
    azure.md               # DOC-04: SDK, RBAC role, env vars
    docker.md              # DOC-04: socket access, Syft requirement
    git.md                 # DOC-04: Gitea/GitHub, semgrep dependency
  report-interpretation.md # DOC-05: score reference table + Client Conversation sideboxes
  cbom-guide.md            # DOC-06: what/how/cite
  chaos-lab.md             # DOC-07: all 10 profiles, port matrix
README.md                  # Product intro + Quick Start + links (REPLACE existing)
quantum-chaos-enterprise-lab/README.md  # Update to link to docs/chaos-lab.md
```

### Pattern 1: Two-Layer Reference + Client Conversation (DOC-05 specific)
**What:** Every major section of the report interpretation guide has a machine-readable reference table followed by a `> **Client Conversation:**` blockquote with suggested spoken language.
**When to use:** Scoring sections, severity tier explanations, CBOM summary, migration roadmap section.
**Example:**
```markdown
### Quantum-Readiness Score

| Score Range | Rating | Plain-English Meaning |
|-------------|--------|-----------------------|
| 85–100 | EXCELLENT | Cryptographic posture is strong. Minor gaps exist but pose low near-term risk. |
| 70–84  | GOOD     | Solid posture with addressable gaps. Prioritized improvements recommended. |
| 55–69  | MODERATE | Material gaps present. Remediation roadmap needed within 90 days. |
| 35–54  | FAIR     | Significant exposure. Executive attention and funded remediation required. |
| 0–34   | POOR     | Critical gaps. Urgent remediation required before quantum-timeline milestones. |

> **Client Conversation:** "Your score of X puts you in the [RATING] band. In practical terms, this means..."
```

### Pattern 2: Copy-Pasteable Credential Block (DOC-04 specific)
**What:** Connector guides lead with a complete, runnable credential block (IAM JSON, RBAC YAML, env var list) before any narrative. Operators copy-paste first, read explanation second.
**Example:**
```markdown
### Minimum IAM Policy (AWS)

```json
{
  "Version": "2012-10-17",
  "Statement": [...]
}
```

Apply this policy to the IAM user or role QU.I.R.K. will use. The permissions map to exactly the API calls the scanner makes — no wildcards, no write access.
```

### Pattern 3: Profile Command Block (DOC-07 specific)
**What:** Each chaos lab profile section opens with the exact `lab.sh` command to start it, then the port matrix, then expected findings.
**Example:**
```markdown
### Profile: jwt

```bash
PROFILE_ARGS="--profile jwt" ./lab.sh up
```

| Port  | Service      | Algorithm   | Expected Finding         |
|-------|-------------|-------------|--------------------------|
| 20001 | jwt-rs256   | RS256 (RSA) | quantum-vulnerable asymmetric |
...
```

### Anti-Patterns to Avoid
- **Assuming PyPI install works:** The primary path is `pip install -e '.[dashboard]'`. PyPI publish is Phase 7. Do NOT write getting-started instructions that use `pip install quirk` without the callout box.
- **Deriving score thresholds from memory:** All score bands, weights, and rating labels MUST match `scoring.py` exactly. Use the verified values in this document.
- **Omitting `playwright install chromium`:** This is a mandatory one-time step after dashboard install. Skipping it causes PDF export to fail silently.
- **Using `--no-open` in normal Getting Started flow:** The auto-open behavior is the intended UX. Document `--no-open` only in the configuration reference as a flag that exists.
- **Confusing Vault port:** Vault is on 20009 (not 20008 as mentioned in the CONTEXT.md — the docker-compose.yml shows `"20009:8200"`). Always use verified port numbers from docker-compose.yml.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Score reference table values | Re-reading scoring.py and computing by hand | Use the verified table in this RESEARCH.md | Risk of transcription error |
| IAM policy derivation | Guessing permissions | Read aws_connector.py — exact boto3 calls enumerated | Documented in this research |
| Port matrix | Re-reading docker-compose.yml | Use the verified port matrix in this RESEARCH.md | Saves implementation time, avoids typos |
| CBOM classification labels | Re-reading classifier.py | Use exact strings: "quantum-vulnerable", "quantum-safe", "unknown" | QuantumSafety enum defines these verbatim |

---

## Verified Source Data (Implementation-Ready)

This section contains ground truth extracted directly from source files. Plans and implementation MUST use these values verbatim.

### Scoring Model (from `quirk/intelligence/scoring.py`)

**Architecture:** 4 subscores, each worth 0–25 points, summed to 0–100.

| Subscore | Key Name | What It Measures |
|----------|----------|------------------|
| Hygiene | `hygiene` | Plaintext HTTP exposure, HTTP on TLS-designated ports, scan error rate |
| Modern TLS | `modern_tls` | Legacy TLS versions (1.0/1.1), unknown open services, assessment blockers |
| Identity Trust | `identity_trust` | Expired/expiring/self-signed certs; bonus for mTLS enforcement |
| Agility Signals | `agility_signals` | High-impact findings ratio, RSA-only posture penalty, ECDSA adoption bonus |

**Rating bands (from `_rating()` function):**

| Score | Rating |
|-------|--------|
| 85–100 | EXCELLENT |
| 70–84 | GOOD |
| 55–69 | MODERATE |
| 35–54 | FAIR |
| 0–34 | POOR |

**Key weight values (documentation accuracy):**
- Hygiene: plaintext HTTP ratio penalty = 18 pts max; HTTP on TLS port = 16 pts; scan error = 6 pts
- Modern TLS: legacy versions = 14 pts; unknown services = 6 pts; scan error = 5 pts
- Identity: expired certs = 14 pts; expiring = 7 pts; self-signed = 9 pts; mTLS bonus = +6 pts
- Agility: high-impact findings = 14 pts; unknown inventory = 6 pts; RSA-only penalty = 8 pts; ECDSA bonus = +4 pts

### Severity Tiers (from `quirk/engine/risk_engine.py`)

| Severity | Finding Titles | Recommendation Theme |
|----------|---------------|---------------------|
| CRITICAL | (from finding_severity_counts — contributed by scanner findings) | Immediate action |
| HIGH | "Plaintext HTTP service detected", "HTTP on TLS-designated port" | Migrate to TLS |
| MEDIUM | "TLS handshake blocked assessment", "Unknown open service" | Investigate/validate |
| LOW | "Legacy TLS versions allowed (TLS 1.0/1.1)" | Upgrade schedule |
| INFO | "SSH quantum planning advisory", "mTLS required", "Informational protocol observation" | Awareness |

### CBOM Quantum Safety Labels (from `quirk/cbom/classifier.py`)

Exact label strings returned by `quantum_safety_label(nist_level)`:
- `nist_level == 0` → `"quantum-vulnerable"` (RSA, ECDSA, all current elliptic curve, DH, SHA-256)
- `nist_level >= 1` → `"quantum-safe"` (ML-KEM, ML-DSA, SLH-DSA, AES-256-CBC nist_level=3, HMAC-SHA512 nist_level=2)
- `nist_level is None` → `"unknown"`

**Notable classifications consultants will ask about:**
- RSA (any size): `quantum-vulnerable` — Shor's algorithm breaks it
- ECDSA / EC: `quantum-vulnerable` — Shor's algorithm breaks discrete log
- AES-256-GCM: `quantum-safe` (nist_level=1) — Grover halving leaves 128-bit effective security
- AES-128: `quantum-safe` (nist_level=1) — 64-bit effective security post-Grover (marginal but classified safe)
- SHA-256: `quantum-vulnerable` (nist_level=0) — Grover halving to 128-bit effective
- SHA-384: `quantum-safe` (nist_level=2)
- ML-KEM-768, ML-KEM-1024: `quantum-safe` (NIST FIPS 203)
- alg:none JWT: `unknown` — no cryptography, critical vulnerability

### AWS Connector Permissions (from `quirk/scanner/aws_connector.py`)

The scanner makes exactly these boto3 API calls. The least-privilege IAM policy must grant:

| Service | API Calls | IAM Action |
|---------|----------|------------|
| ACM | `get_paginator("list_certificates")`, `describe_certificate(CertificateArn=...)` | `acm:ListCertificates`, `acm:DescribeCertificate` |
| KMS | `get_paginator("list_keys")`, `describe_key(KeyId=...)` | `kms:ListKeys`, `kms:DescribeKey` |
| CloudFront | `get_paginator("list_distributions")` | `cloudfront:ListDistributions` |
| ELBv2 | `get_paginator("describe_load_balancers")`, `describe_listeners(LoadBalancerArn=...)` | `elasticloadbalancing:DescribeLoadBalancers`, `elasticloadbalancing:DescribeListeners` |

**Credential chain:** `boto3.Session(region_name=region, profile_name=profile)` — resolves via standard chain: env vars → `~/.aws/credentials` → IAM instance role.

**Config.yaml knobs for AWS:**
```yaml
connectors:
  enable_aws: true
  aws_region: "us-east-1"        # required
  aws_profile: "quirk-readonly"  # optional, uses default profile if omitted
```

### Azure Connector Permissions (from `quirk/scanner/azure_connector.py`)

The scanner makes exactly these Azure SDK calls:

| Service | SDK Call | RBAC Permission |
|---------|----------|-----------------|
| Key Vault keys | `KeyClient.list_properties_of_keys()` | `Key Vault Reader` (or `Key Vault Crypto Service Encryption User` for read) |
| Key Vault certificates | (via CertificateClient, imported) | `Key Vault Reader` |
| App Gateway TLS policy | `NetworkManagementClient.application_gateways.list_all()` | `Reader` on subscription + `Microsoft.Network/applicationGateways/read` |

**Credential:** `DefaultAzureCredential()` — resolves via standard chain: env vars → managed identity → Azure CLI.

**Required env vars for service principal:**
- `AZURE_CLIENT_ID`
- `AZURE_TENANT_ID`
- `AZURE_CLIENT_SECRET`

**Config.yaml knobs for Azure:**
```yaml
connectors:
  enable_azure: true
  azure_subscription_id: "00000000-0000-0000-0000-000000000000"
  azure_keyvault_urls:
    - "https://myvault.vault.azure.net"
```

**Note:** `azure-mgmt-network` is imported inside `_scan_app_gateways` to keep it optional. If not installed, App Gateway scanning is skipped gracefully.

### Complete CLI Flag Reference (from `run_scan.py`)

**`quirk` (scan) flags:**

| Flag | Default | Description |
|------|---------|-------------|
| `--config PATH` | none (interactive) | Path to config.yaml; skips interactive prompts |
| `--profile` | `standard` | Scan profile: `quick`, `standard`, `deep` |
| `--score-profile` | `balanced` | Scoring calibration: `lenient`, `balanced`, `strict` |
| `--verbose` | false | Verbose output during scan |
| `--progress` | false | Show tqdm progress bars |
| `--discovery` | `builtin` | Discovery mode: `builtin` or `nmap` |
| `--nmap-path` | `nmap` | Path to nmap executable |
| `--nmap-timeout` | 1800 | Nmap discovery timeout (seconds) |
| `--nmap-extra-args` | `""` | Extra nmap arguments (quoted) |
| `--safe-mode` | false | Reduce concurrency, increase timeouts |
| `--rate-limit` | 0.0 | Targets/sec rate limiter (0 = off) |
| `--cache` | false | Enable discovery/fingerprint cache |
| `--cache-ttl-hours` | 24 | Cache TTL in hours |
| `--resume` | false | Reuse cache if valid |
| `--force-discovery` | false | Ignore discovery cache, re-run |

**`quirk serve` flags:**

| Flag | Default | Description |
|------|---------|-------------|
| `--port` | 8512 | Port to serve on |
| `--host` | `127.0.0.1` | Host to bind |
| `--no-open` | false | Do not auto-open browser |

### Complete config.yaml Key Reference (from `config.yaml` + `quirk/config.py`)

**assessment block (all required):**

| Key | Type | Example | Description |
|-----|------|---------|-------------|
| `name` | string | `"Quantum Crypto Readiness - CLIENT NAME"` | Assessment name (appears in reports) |
| `data_classification` | string | `"confidential"` | `public`, `internal`, `confidential`, `regulated` |
| `report_owner` | string | `"CLIENT NAME"` | Appears in report header |
| `timezone` | string | `"America/New_York"` | IANA timezone for report timestamps |

**scan block:**

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `timeout_seconds` | int | 5 | Global connection timeout |
| `concurrency` | int | 200 | Max parallel workers (global) |
| `ports_tls` | list[int] | `[443,8443,9443,10443,11443,12443,8444,8000,2222,5555]` | Ports to probe for TLS/HTTP/SSH |
| `include_sni` | bool | true | Send SNI in TLS handshakes |
| `tls_enum_mode` | string | `"fast"` | `off`, `fast`, `deep` |
| `fingerprint_timeout_seconds` | int | 2 | Per-target fingerprint timeout |
| `fingerprint_concurrency` | int | 200 | Fingerprint worker count |
| `tls_timeout_seconds` | int | 5 | TLS scan phase timeout |
| `tls_concurrency` | int | 150 | TLS scan worker count |
| `ssh_timeout_seconds` | int | 5 | SSH scan phase timeout |
| `ssh_concurrency` | int | 100 | SSH scan worker count |

**targets block:**

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `fqdns` | list[string] | `[]` | Fully qualified domain names to scan |
| `cidrs` | list[string] | `[127.0.0.1]` | CIDR ranges or single IPs |
| `include_ips` | list[string] | `[]` | Additional IPs to include |
| `exclude_ips` | list[string] | `[]` | IPs to exclude from results |

**connectors block:**

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `enable_aws` | bool | false | Enable AWS cloud connector |
| `enable_azure` | bool | false | Enable Azure cloud connector |
| `enable_windows_adcs` | bool | false | Enable Windows AD CS (stub, not implemented) |
| `enable_jwt` | bool | false | Enable JWT/REST scanner |
| `enable_container` | bool | false | Enable container/binary crypto scanner |
| `enable_source` | bool | false | Enable source code scanner |
| `aws_region` | string | `"us-east-1"` | AWS region for cloud connector |
| `aws_profile` | string | null | AWS named profile (null = default) |
| `azure_subscription_id` | string | null | Azure subscription UUID |
| `azure_keyvault_urls` | list[string] | `[]` | Key Vault base URLs |
| `jwt_targets` | list[string] | `[]` | URLs for JWT scanner |
| `container_targets` | list[string] | `[]` | Image refs for container scanner |
| `source_targets` | list[string] | `[]` | Repo paths/URLs for source scanner |

**output block:**

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `directory` | string | `"output"` | Output directory for reports/CBOM |
| `db_path` | string | `"output/quirk.db"` | SQLite database path |

**intelligence block:**

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `intelligence_version` | string | `"3.9.0"` | Intelligence layer version tag (informational) |
| `profile` | string | `"balanced"` | Score calibration: `lenient`, `balanced`, `strict` |
| `calibration_overrides` | dict | `{}` | Advanced per-weight overrides (power user) |

### Chaos Lab Complete Port Matrix (from `docker-compose.yml` + `expected_results_v3.md`)

**Profile: core (always-on — no `--profile` flag needed)**

| Port | Service | Expected Protocol | Tag |
|------|---------|------------------|-----|
| 443 | tls-modern | TLS | MODERN_TLS |
| 8443 | tls-legacy | TLS | LEGACY_TLS |
| 9443 | tls-expired | TLS | CERT_EXPIRED_OR_EXPIRING |
| 10443 | tls-selfsigned | TLS | CERT_SELFSIGNED |
| 11443 | tls-mtls-required | TLS | MTLS_REQUIRED |
| 12443 | tls-slow-proxy | TLS | TLS_SLOW_PROXY |
| 8444 | http-on-8444 | HTTP | HTTP_ON_TLS_LIKE_PORT |
| 8000 | legacy-http | HTTP | PLAINTEXT_HTTP |
| 2222 | ssh-alt | SSH | SSH_BANNER |
| 5555 | unknown-port | UNKNOWN | UNKNOWN_OPEN_PORT |

**Start command:** `./lab.sh up`

---

**Profile: phaseA**

| Port | Service | Expected Protocol | Tag |
|------|---------|------------------|-----|
| 15001 | tls-altport | TLS | TLS_ON_ODD_PORT |
| 18000 | http-redirect | HTTP | HTTP_REDIRECT_302 |
| 5556 | unknown-port-2 | UNKNOWN | UNKNOWN_OPEN_PORT_2 |
| 15432 | postgres-plain | UNKNOWN | DB_PLAINTEXT_POSTGRES |
| 16379 | redis-plain | UNKNOWN | DB_PLAINTEXT_REDIS |
| 15672 | rabbitmq-mgmt | HTTP | RABBITMQ_MGMT_HTTP |
| 13443 | tls-missing-intermediate | TLS | CERT_CHAIN_INCOMPLETE |
| 14443 | tls-rsa1024 | TLS | CERT_RSA_1024 |
| 15443 | tls-sha1 | TLS | CERT_SHA1_SIG |
| 24443 | ingress-sni | TLS | INGRESS_SNI (multi-vhost) |

**Start command:** `PROFILE_ARGS="--profile phaseA" ./lab.sh up`

---

**Profile: cloud**

| Port | Service | Expected Protocol | Tag |
|------|---------|------------------|-----|
| 24566 | localstack-tls | TLS | CLOUD_AWS_LOCALSTACK_TLS |
| 21000 | azurite-blob-tls | TLS | CLOUD_AZURITE_BLOB_TLS |
| 21001 | azurite-queue-tls | TLS | CLOUD_AZURITE_QUEUE_TLS |
| 21002 | azurite-table-tls | TLS | CLOUD_AZURITE_TABLE_TLS |

**Start command:** `PROFILE_ARGS="--profile cloud" ./lab.sh up`

---

**Profile: identity**

| Port | Service | Expected Protocol | Tag |
|------|---------|------------------|-----|
| 15449 | keycloak-tls | TLS | IDP_TLS |
| 19000 | step-ca | TLS | PRIVATE_CA_TLS |
| 13890 | openldap | UNKNOWN | LDAP_TCP |
| 18082 | phpldapadmin | HTTP | LDAP_ADMIN_HTTP |
| 16443 | mtls-gateway | TLS | MTLS_REQUIRED |

**Start command:** `PROFILE_ARGS="--profile identity" ./lab.sh up`

---

**Profile: pki**

| Port | Service | Expected Protocol | Tag |
|------|---------|------------------|-----|
| 17443 | mtls-stepca-gateway | TLS | MTLS_STEPCA (step-ca issued client cert required) |

**Start command:** `PROFILE_ARGS="--profile pki" ./lab.sh up`
*Note: requires identity profile running first (depends on whoami and step-ca)*

---

**Profile: jwt (Phase 4 — LAB-01)**

| Port | Service | Algorithm | Expected Finding | Key Size |
|------|---------|-----------|-----------------|----------|
| 20001 | jwt-rs256 | RS256 (RSA) | quantum-vulnerable asymmetric | 2048-bit |
| 20002 | jwt-hs256 | HS256 (HMAC-SHA256) | WEAK_KEY_SIZE | 128-bit (16-byte key) |
| 20003 | jwt-rsa1024 | RS256 (RSA) | WEAK_KEY_SIZE + quantum-vulnerable | 1024-bit |
| 20004 | jwt-algnone | none | CRITICAL_NO_SIGNATURE | 0 |

**Start command:** `PROFILE_ARGS="--profile jwt" ./lab.sh up`

---

**Profile: registry (Phase 4 — LAB-02)**

| Port | Service | Content | Expected Finding |
|------|---------|---------|-----------------|
| 20005 | Docker Registry v2 | image-old-libssl (openssl 1.0.2n) | OUTDATED_CRYPTO_LIB |
| 20005 | Docker Registry v2 | image-old-pycrypto (cryptography 2.9.2, pyopenssl 19.1.0) | OUTDATED_CRYPTO_LIB |
| 20005 | Docker Registry v2 | image-mixed (both old packages) | OUTDATED_CRYPTO_LIB |

**Start command:** `PROFILE_ARGS="--profile registry" ./lab.sh up`
*Note: registry-seed container seeds images on startup. Docker socket must be available.*

---

**Profile: source (Phase 4 — LAB-03)**

| Port | Service | Content | Expected Finding |
|------|---------|---------|-----------------|
| 20006 | Gitea | crypto-antipatterns-python, crypto-antipatterns-go, crypto-antipatterns-java | Weak algorithm, hardcoded keys, weak random, deprecated protocol |

**Start command:** `PROFILE_ARGS="--profile source" ./lab.sh up`
*Gitea admin credentials: username `admin`, password `admin123`*

---

**Profile: storage (Phase 4 — LAB-04)**

| Port | Service | Resource | Expected Finding |
|------|---------|---------|-----------------|
| 20007 | LocalStack KMS | SYMMETRIC_DEFAULT key | AES_256 (quantum-vulnerable via Grover) |
| 20007 | LocalStack KMS | RSA_2048 key | RSA_2048 (quantum-vulnerable) |
| 20007 | LocalStack KMS | ECC_NIST_P256 key | ECC_P256 (quantum-vulnerable) |
| 20009 | HashiCorp Vault | transit/keys/rsa-2048 | RSA_2048 (quantum-vulnerable) |
| 20009 | HashiCorp Vault | transit/keys/rsa-1024 | RSA_1024 (weak + quantum-vulnerable) |
| 20009 | HashiCorp Vault | transit/keys/aes256 | AES_256 (quantum-vulnerable via Grover) |
| 20010 | postgres-pgcrypto | encrypted_demo table | pgp_sym_encrypt weak passphrase |

**Start command:** `PROFILE_ARGS="--profile storage" ./lab.sh up`
*Vault token: `root`. LocalStack credentials: `test`/`test`.*

---

**Profile: ssh-weak (Phase 4 — LAB-05)**

| Port | Service | Expected Protocol | Tag |
|------|---------|------------------|-----|
| 20022 | OpenSSH 7.6p1 (ubuntu:18.04) | SSH | SSH_WEAK_ALGORITHMS — legacy KEX/hostkey/MAC |

**Start command:** `PROFILE_ARGS="--profile ssh-weak" ./lab.sh up`

---

**Profile: ldaps (Phase 4 — LAB-06)**

| Port | Service | Expected Protocol | Tag |
|------|---------|------------------|-----|
| 636 | OpenLDAP over TLS (osixia/openldap:1.5.0) | TLS | LDAPS_TLS |

**Start command:** `PROFILE_ARGS="--profile ldaps" ./lab.sh up`

---

**Starting multiple profiles simultaneously:**
```bash
PROFILE_ARGS="--profile jwt --profile registry --profile source --profile storage --profile ssh-weak --profile ldaps" ./lab.sh up
```

---

## Common Pitfalls

### Pitfall 1: Stale README content
**What goes wrong:** Consultant clones repo, reads README expecting current content, sees "qcscan" and "Quantum Crypto Scanner" — loses confidence in the tool before even starting.
**Why it happens:** README has never been updated since pre-Phase 1.
**How to avoid:** Replace README completely in the first plan/task of this phase. Do not patch the old README.
**Warning signs:** Any reference to `qcscan`, `QuRisk`, or "Quantum Crypto Scanner" in README.md.

### Pitfall 2: Score band mismatch
**What goes wrong:** Documentation says "70-100 = EXCELLENT" but the code says 85+ = EXCELLENT. Consultant miscommunicates to client.
**Why it happens:** Score bands are easy to mis-transcribe or approximate.
**How to avoid:** Use the verified table from this RESEARCH.md. Source: `_rating()` in `quirk/intelligence/scoring.py` lines 47-56.
**Warning signs:** Any score boundary that doesn't match {85, 70, 55, 35}.

### Pitfall 3: Missing `playwright install chromium` step
**What goes wrong:** Consultant installs quirk, runs `quirk serve`, generates a report, exports PDF — fails with a cryptic Playwright error.
**Why it happens:** Playwright requires a one-time browser download step that is separate from the pip install.
**How to avoid:** Include `playwright install chromium` explicitly in getting-started AND installation guides, on its own line with an explanatory comment.
**Warning signs:** If the step is buried in a paragraph rather than its own code block.

### Pitfall 4: Vault port confusion
**What goes wrong:** Operator document says Vault is on port 20008 (as mentioned in CONTEXT.md D-14), but the actual docker-compose.yml maps `"20009:8200"`. Operator can't reach the service.
**Why it happens:** CONTEXT.md had a transcription error. docker-compose.yml is the ground truth.
**How to avoid:** Use port 20009 for Vault, 20008 does not exist in the lab. This has been verified from docker-compose.yml line 687.
**Warning signs:** Any reference to port 20008 for Vault in the chaos lab guide.

### Pitfall 5: Windows WSL buried in Getting Started
**What goes wrong:** Windows user reads Getting Started, follows macOS/Linux instructions, they fail, user gives up.
**Why it happens:** Windows path is different (WSL setup required first).
**How to avoid:** Per D-07, Windows WSL belongs only in `installation.md` (separate section). Getting Started must link to installation.md for Windows users at the very top: `> **Windows?** See [Installation - Windows WSL](installation.md#windows-wsl)`.
**Warning signs:** If WSL setup appears inline in getting-started.md rather than as a cross-reference.

### Pitfall 6: IAM permissions drift
**What goes wrong:** IAM policy JSON is written from memory and includes actions the scanner doesn't use, or is missing actions it does use.
**Why it happens:** IAM policy derivation is typically done by reading code — if the code is not re-read, the policy is a guess.
**How to avoid:** Use the verified AWS permission table in this RESEARCH.md (derived from `aws_connector.py` boto3 calls). Do NOT add wildcard permissions.
**Warning signs:** Policies with `"Action": ["acm:*"]` or similar wildcards.

### Pitfall 7: `quirk serve` default port assumption
**What goes wrong:** Documentation says "open http://localhost:8080" when the actual default is port 8512.
**Why it happens:** 8080 is a commonly assumed web server default.
**How to avoid:** Always write `http://127.0.0.1:8512` (or `http://localhost:8512`) in documentation. Verified from `run_scan.py` serve parser default.
**Warning signs:** Any URL in docs that uses port 8080, 8000, or 5000 for the dashboard.

---

## Code Examples

Verified patterns from source files:

### Minimal config.yaml for first scan
```yaml
# Source: config.yaml (repo root)
assessment:
  name: "Quantum Crypto Readiness - Acme Corp"
  data_classification: "confidential"
  report_owner: "Acme Corp"
  timezone: "America/New_York"

scan:
  timeout_seconds: 5
  concurrency: 200
  ports_tls: [443, 8443, 9443, 10443, 11443, 12443, 8444, 8000, 2222, 5555]
  include_sni: true
  tls_enum_mode: fast

targets:
  fqdns: []
  cidrs: [127.0.0.1]
  include_ips: []
  exclude_ips: []

connectors:
  enable_aws: false
  enable_azure: false
  enable_windows_adcs: false

output:
  directory: "output"
  db_path: "output/quirk.db"

intelligence:
  intelligence_version: "3.9.0"
  profile: "balanced"
  calibration_overrides: {}
```

### Getting Started install sequence
```bash
# Source: D-04 locked decision + pyproject.toml entry point
git clone https://github.com/your-org/quirk.git
cd quirk
python -m venv .venv
source .venv/bin/activate       # macOS/Linux
# On Windows WSL: same command
pip install -e '.[dashboard]'
playwright install chromium     # one-time browser download for PDF export
quirk --help
```

### Derived least-privilege IAM policy JSON
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "QuirkACMReadOnly",
      "Effect": "Allow",
      "Action": [
        "acm:ListCertificates",
        "acm:DescribeCertificate"
      ],
      "Resource": "*"
    },
    {
      "Sid": "QuirkKMSReadOnly",
      "Effect": "Allow",
      "Action": [
        "kms:ListKeys",
        "kms:DescribeKey"
      ],
      "Resource": "*"
    },
    {
      "Sid": "QuirkCloudFrontReadOnly",
      "Effect": "Allow",
      "Action": [
        "cloudfront:ListDistributions"
      ],
      "Resource": "*"
    },
    {
      "Sid": "QuirkELBv2ReadOnly",
      "Effect": "Allow",
      "Action": [
        "elasticloadbalancing:DescribeLoadBalancers",
        "elasticloadbalancing:DescribeListeners"
      ],
      "Resource": "*"
    }
  ]
}
```
*Source: Derived from `quirk/scanner/aws_connector.py` — exact boto3 API calls enumerated.*

---

## Runtime State Inventory

Step 2.5 SKIPPED — this phase is documentation-only (new Markdown files + README replacement). No renames, refactors, or string replacements of runtime identifiers. No stored data, live service config, OS registrations, secrets, or build artifacts are affected by this phase.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.10+ | Install guide testing | Assumed (dev machine) | — | Document requirement only |
| git | Getting Started clone step | Assumed | — | Document requirement only |
| Docker / Docker Compose | Chaos lab operator guide | Assumed (lab machine) | — | Document as prerequisite |
| Playwright Chromium | Install guide (PDF export step) | Installed on doc via pip | — | Note: requires `playwright install chromium` |

This is a documentation-only phase. No external services need to be running to write the docs. The chaos lab is documented as a prerequisite for operators, not for the doc writer.

**Missing dependencies with no fallback:** None — all dependencies are documented as prerequisites for the *reader*, not required to write the documentation.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (inferred from existing `tests/` directory and conftest.py) |
| Config file | none detected in repo root — pytest uses defaults |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements → Test Map

Documentation phases are fundamentally different from code phases. The deliverables are Markdown files, not Python modules. Automated unit tests cannot verify that a guide enables a consultant to complete a task in 10 minutes. The appropriate validation strategy is:

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DOC-01 | Getting Started guide exists and contains required sections (Python check, venv, install, config, scan, serve) | smoke — file content check | `python3 -c "import pathlib; t=pathlib.Path('docs/getting-started.md').read_text(); assert 'python -m venv' in t and 'playwright install' in t and 'quirk serve' in t"` | ❌ Wave 0 (file does not exist yet) |
| DOC-02 | Installation guide exists with macOS, Linux, Windows WSL sections | smoke — file content check | `python3 -c "import pathlib; t=pathlib.Path('docs/installation.md').read_text(); assert 'macOS' in t and 'Linux' in t and 'WSL' in t"` | ❌ Wave 0 |
| DOC-03 | Configuration reference covers all top-level config.yaml keys | smoke — key coverage check | `python3 -c "import pathlib; t=pathlib.Path('docs/configuration.md').read_text(); [__import__('sys').exit(1) for k in ['assessment','scan','targets','connectors','output','intelligence'] if k not in t]"` | ❌ Wave 0 |
| DOC-04 | Connector guides exist for AWS, Azure, Docker, Git | smoke — file existence | `python3 -c "import pathlib; [pathlib.Path(f'docs/connectors/{c}.md').read_text() for c in ['aws','azure','docker','git']]"` | ❌ Wave 0 |
| DOC-05 | Report interpretation guide contains score bands and severity tiers | smoke — content check | `python3 -c "import pathlib; t=pathlib.Path('docs/report-interpretation.md').read_text(); assert 'EXCELLENT' in t and 'POOR' in t and 'CRITICAL' in t"` | ❌ Wave 0 |
| DOC-06 | CBOM guide contains required sections | smoke — content check | `python3 -c "import pathlib; t=pathlib.Path('docs/cbom-guide.md').read_text(); assert 'CycloneDX' in t and 'NIST' in t and 'quantum-vulnerable' in t"` | ❌ Wave 0 |
| DOC-07 | Chaos lab guide covers all Phase 4 profiles and their ports | smoke — port and profile check | `python3 -c "import pathlib; t=pathlib.Path('docs/chaos-lab.md').read_text(); [__import__('sys').exit(1) for p in ['20001','20002','20003','20004','20005','20006','20007','20009','20022','636'] if p not in t]"` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** Single file content smoke check (see commands above per requirement)
- **Per wave merge:** All smoke checks pass
- **Phase gate:** All smoke checks green + human UAT (10-minute install walkthrough on a clean machine) before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `docs/` directory — does not exist yet, created in Wave 0
- [ ] All 9 Markdown files listed in D-01 — all new files, created during implementation
- [ ] Smoke check commands above — inline Python one-liners, no test file needed; add to verification checklist

The primary quality gate for documentation is human UAT, not automated tests. The smoke checks above verify structural completeness (sections exist, key terms present) but cannot verify accuracy or readability.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|-----------------|--------------|--------|
| README says "qcscan" | README must say "QU.I.R.K. / quirk" | Phase 1 (CORE-03) | README is now stale — must be replaced |
| No `docs/` folder | `docs/` folder with guide suite | Phase 6 (this phase) | First time documentation exists |
| `CHAOS_LAB_BUILD_AND_OPERATIONS_text_only.md` (historical) | `docs/chaos-lab.md` (authoritative) | Phase 6 | Old file stays as artifact, new file is the reference |

---

## Open Questions

1. **pyproject.toml `sslyze` and `ssh-audit` in dependencies?**
   - What we know: `requirements.txt` or extra groups may list these as system tools. Neither appears in `pyproject.toml` main deps.
   - What's unclear: Does the installation guide need to document `pip install sslyze` separately, or is it bundled?
   - Recommendation: Check `pyproject.toml` for optional extras during Wave 0. If sslyze/ssh-audit are not in any optional group, document them as system prerequisites in `installation.md`.

2. **Minimum Python version for Windows WSL**
   - What we know: `requires-python = ">=3.10"` from pyproject.toml.
   - What's unclear: Whether Python 3.10 is available by default in common WSL distributions.
   - Recommendation: Installation guide should specify `python3 --version` check and point to deadsnakes PPA for Ubuntu WSL if below 3.10.

3. **`quirk serve` UAT: does browser auto-open work in all environments?**
   - What we know: `--no-open` flag exists, defaults off (auto-open enabled).
   - What's unclear: Auto-open may not work in WSL environments.
   - Recommendation: Installation guide WSL section should note: if browser does not auto-open, manually navigate to `http://127.0.0.1:8512`.

---

## Sources

### Primary (HIGH confidence)
- `quirk/intelligence/scoring.py` — full file read; all score bands, subscore weights, rating thresholds extracted verbatim
- `quirk/cbom/classifier.py` — full file read; QuantumSafety enum, quantum_safety_label(), complete _ALGORITHM_TABLE extracted
- `quirk/engine/risk_engine.py` — partial read; all finding titles and severity assignments confirmed
- `quirk/scanner/aws_connector.py` — full file read; exact boto3 API calls enumerated for IAM policy derivation
- `quirk/scanner/azure_connector.py` — full file read; exact SDK calls enumerated for RBAC derivation
- `quirk/config.py` — full file read; all ConnectorsCfg fields with defaults confirmed
- `config.yaml` — full file read; all top-level keys and example values confirmed
- `run_scan.py` — full file read; complete argparse definitions for both `quirk` and `quirk serve`
- `quantum-chaos-enterprise-lab/docker-compose.yml` — full file read; all 10 profile definitions and port mappings
- `quantum-chaos-enterprise-lab/expected_results_v3.md` — full file read; complete oracle table per profile
- `quantum-chaos-enterprise-lab/lab.sh` — full file read; `lab.sh` command syntax confirmed
- `pyproject.toml` — partial read; `requires-python`, entry point, optional groups confirmed
- `.planning/phases/06-documentation/06-CONTEXT.md` — all locked decisions (D-01 through D-18) confirmed

### Secondary (MEDIUM confidence)
- CycloneDX 1.6 schema and quantum extension — verified from cyclonedx-python-lib imports in builder.py and classifier.py (BomRef, CryptoProperties, AlgorithmProperties, CertificateProperties, ProtocolProperties)
- NIST PQC standards (FIPS 203/204/205) — confirmed from classifier.py entries for ml-kem-*, ml-dsa-*, slh-dsa-*

### Tertiary (LOW confidence)
- NIST SP 800-208 / CNSA 2.0 compliance citation language — not verified from official docs; planner should include a note for the implementer to confirm exact citation language from NIST SP 800-208 before writing the CBOM compliance section

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — plain Markdown, no tooling decisions needed, structure fully specified in CONTEXT.md
- Architecture: HIGH — folder structure locked in D-01, all source data extracted from authoritative files
- Pitfalls: HIGH — verified against actual source code, port verified against docker-compose.yml
- Score data: HIGH — extracted verbatim from scoring.py, no inference
- IAM policy: HIGH — derived directly from boto3 calls in aws_connector.py
- Port matrix: HIGH — extracted from docker-compose.yml (Vault port 20009 corrected vs CONTEXT.md)
- CBOM labels: HIGH — extracted from QuantumSafety enum and quantum_safety_label() return values

**Research date:** 2026-03-31
**Valid until:** 2026-09-30 (stable domain; no external library versions in play — only internal source code)
