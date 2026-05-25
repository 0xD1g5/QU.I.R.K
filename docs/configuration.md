# Configuration Reference

QU.I.R.K. is configured through a `config.yaml` file in the working directory. Pass a custom path with `--config /path/to/config.yaml` to override the default location.

The file has six top-level blocks: `assessment`, `scan`, `targets`, `connectors`, `output`, and `intelligence`. Only the `assessment` block is required. All other blocks use sensible defaults.

---

## Assessment Block (required)

All four keys are required. They appear in every report header and deliverable.

| Key | Type | Example | Required | Description |
|-----|------|---------|----------|-------------|
| `name` | string | `"Quantum Crypto Readiness - ACME Corp"` | Yes | Assessment name — appears in all report headers |
| `data_classification` | string | `"confidential"` | Yes | One of: `public`, `internal`, `confidential`, `regulated` |
| `report_owner` | string | `"ACME Corp"` | Yes | Client name as it appears in the report |
| `timezone` | string | `"America/New_York"` | Yes | IANA timezone for report timestamps (e.g. `"Europe/London"`, `"UTC"`) |

```yaml
assessment:
  name: "Quantum Crypto Readiness - ACME Corp"
  data_classification: "confidential"
  report_owner: "ACME Corp"
  timezone: "America/New_York"
```

---

## Scan Block

Controls connection timeouts, concurrency, port selection, and TLS enumeration depth. All keys are optional — defaults are calibrated for typical enterprise networks.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `timeout_seconds` | int | `5` | Global connection timeout in seconds |
| `concurrency` | int | `200` | Maximum parallel workers (global cap) |
| `ports_tls` | list[int] | `[443,8443,9443,10443,11443,12443,8444,8000,2222,5555]` | Ports probed for TLS/HTTP/SSH |
| `include_sni` | bool | `true` | Send SNI extension in TLS handshakes |
| `tls_enum_mode` | string | `"fast"` | TLS enumeration depth: `off`, `fast`, `deep` |
| `fingerprint_timeout_seconds` | int | `2` | Per-target fingerprint timeout |
| `fingerprint_concurrency` | int | `200` | Fingerprint phase worker count |
| `tls_timeout_seconds` | int | `5` | TLS scan phase connection timeout |
| `tls_concurrency` | int | `150` | TLS scan phase worker count |
| `ssh_timeout_seconds` | int | `5` | SSH scan phase connection timeout |
| `ssh_concurrency` | int | `100` | SSH scan phase worker count |

> **Note:** For large scans (1000+ hosts), reduce `concurrency` to `50` and use `--safe-mode` to prevent connection exhaustion.

```yaml
scan:
  timeout_seconds: 5
  concurrency: 200
  ports_tls: [443, 8443, 9443, 10443, 11443, 12443, 8444, 8000, 2222, 5555]
  include_sni: true
  tls_enum_mode: fast   # off|fast|deep
  fingerprint_timeout_seconds: 2
  fingerprint_concurrency: 200
  tls_timeout_seconds: 5
  tls_concurrency: 150
  ssh_timeout_seconds: 5
  ssh_concurrency: 100
```

---

## Timeout & Retry Policy (v4.5+)

Phase 41 introduced canonical `[scan.timeouts]` and `[scan.retry]` sub-tables that supersede the
legacy flat fields. Every scanner — fingerprint, TLS, SSH, JWT, container, source, DNSSEC, SAML,
Kerberos, Vault, database, broker, email — reads its connection timeout and retry policy from
these sub-tables (canonical source: `quirk/config.py` `TimeoutsCfg` / `RetryCfg` dataclasses). The
flat fields documented above (`timeout_seconds`, `fingerprint_timeout_seconds`, `tls_timeout_seconds`,
`ssh_timeout_seconds`) remain readable for backward compatibility but emit `DeprecationWarning` on
read; new configurations should use the sub-tables.

### `[scan.timeouts]` — per-scanner connection timeouts

| Slot | Type | Default (s) | Applies to |
|------|------|-------------|------------|
| `default_seconds` | int | `5` | Fallback for any scanner without a dedicated slot |
| `fingerprint_seconds` | int | `4` | Fingerprint phase TCP/banner probe |
| `tls_seconds` | int | `6` | TLS handshake / ciphersuite enumeration |
| `ssh_seconds` | int | `6` | SSH banner + KEX exchange |
| `jwt_seconds` | int | `10` | JWT/REST endpoint probes |
| `container_seconds` | int | `120` | Container image binary scans (per image) |
| `source_seconds` | int | `300` | Source-tree crypto scan (per repo) |
| `dnssec_seconds` | int | `10` | DNSSEC record + DS chain probe |
| `saml_seconds` | int | `10` | SAML metadata fetch |
| `kerberos_seconds` | int | `10` | Kerberos KDC probe |
| `vault_seconds` | int | `10` | HashiCorp Vault / KMS API call |
| `db_connect_seconds` | int | `5` | Database driver connect (Postgres, MySQL, …) |
| `broker_seconds` | int | `10` | Message broker probe (Kafka, RabbitMQ, Redis) |
| `email_seconds` | int | `10` | SMTP/IMAP/POP3 STARTTLS probe |

### `[scan.retry]` — retry/backoff policy

| Slot | Type | Default | Description |
|------|------|---------|-------------|
| `retry_count` | int | `0` | Number of retries after the initial attempt (0 = no retry) |
| `backoff_base_seconds` | float | `1.0` | Initial backoff before the first retry |
| `backoff_max_seconds` | float | `5.0` | Backoff ceiling — exponential backoff caps here |

### Deprecation notice

The legacy flat fields below are still accepted but emit `DeprecationWarning` on read:

| Legacy field | New canonical slot |
|--------------|--------------------|
| `scan.timeout_seconds` | `scan.timeouts.default_seconds` |
| `scan.fingerprint_timeout_seconds` | `scan.timeouts.fingerprint_seconds` |
| `scan.tls_timeout_seconds` | `scan.timeouts.tls_seconds` |
| `scan.ssh_timeout_seconds` | `scan.timeouts.ssh_seconds` |

Migrate at your earliest convenience — the flat fields will be removed in a future major release.

### Overall scan upper-bound formula (D-10)

The total wall-clock upper bound for a single scan run is bounded by:

```
scan_upper_bound = (
  fingerprint_timeout * N_targets
  + tls_timeout       * N_tls_candidates
  + ssh_timeout       * N_ssh_candidates
  + max(jwt_timeout, container_timeout, source_timeout, ...) * N_connector_targets
) + 10s safety_margin
```

Where:
- `N_targets` = number of fingerprinted hosts
- `N_tls_candidates` = subset of targets with at least one TLS-eligible port open
- `N_ssh_candidates` = subset of targets with at least one SSH-eligible port open
- `N_connector_targets` = number of connector probes (JWT URLs, container images, source repos, etc.)
- The `max(...)` term reflects connector phases running in sequence — pick the longest active connector timeout
- `safety_margin` = 10s flat allowance for orchestration, report writing, and finalization

**Worked example — single-host scan, all phases enabled:**

```
fingerprint (4s) + tls (6s) + ssh (6s) + max(jwt=10s) + safety (10s)
= 4 + 6 + 6 + 10 + 10
≈ 36 seconds
```

For a 100-host scan with TLS+SSH on every host and no connectors:

```
4*100 + 6*100 + 6*100 + 10
= 400 + 600 + 600 + 10
≈ 1610 seconds (~27 min) worst case
```

Concurrency (`concurrency: 200`) reduces wall-clock substantially below the upper bound; the formula
is the consultant-quotable worst case, not the expected runtime.

### Example TOML / YAML snippet

```yaml
scan:
  concurrency: 200
  ports_tls: [443, 8443]
  timeouts:
    default_seconds: 5
    fingerprint_seconds: 4
    tls_seconds: 6
    ssh_seconds: 6
    jwt_seconds: 10
    container_seconds: 120
    source_seconds: 300
    dnssec_seconds: 10
    saml_seconds: 10
    kerberos_seconds: 10
    vault_seconds: 10
    db_connect_seconds: 5
    broker_seconds: 10
    email_seconds: 10
  retry:
    retry_count: 0
    backoff_base_seconds: 1.0
    backoff_max_seconds: 5.0
```

See [`docs/timeout-retry-audit.md`](timeout-retry-audit.md) for the per-scanner audit table mapping
each scanner to its canonical timeout slot (ROBUST-04).

---

## Targets Block

Defines what to scan. At least one of `fqdns` or `cidrs` must have entries.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `fqdns` | list[string] | `[]` | Fully qualified domain names to include in the scan |
| `cidrs` | list[string] | `[127.0.0.1]` | CIDR ranges or single IP addresses |
| `include_ips` | list[string] | `[]` | Additional IPs to append to CIDR results |
| `exclude_ips` | list[string] | `[]` | IPs to exclude from scanning |

Example showing a typical client configuration:

```yaml
targets:
  fqdns:
    - api.acme.com
    - auth.acme.com
  cidrs:
    - 10.0.0.0/24
    - 192.168.1.0/28
  exclude_ips:
    - 10.0.0.1   # router — no services
```

---

## Connectors Block

Enables optional scanner extensions for cloud infrastructure, API endpoints, containers, and source code. All connectors are disabled by default.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `enable_aws` | bool | `false` | Enable AWS cloud connector (ACM, KMS, CloudFront, ELBv2) |
| `enable_azure` | bool | `false` | Enable Azure cloud connector (Key Vault, App Gateway) |
| `enable_windows_adcs` | bool | `false` | Windows AD CS connector (stub — not implemented in v3.9) |
| `enable_jwt` | bool | `false` | Enable JWT/REST API scanner |
| `enable_container` | bool | `false` | Enable container/binary crypto scanner |
| `enable_source` | bool | `false` | Enable source code scanner |
| `enable_codesign` | bool | `false` | Enable code-signing certificate inventory (LDAP `userCertificate` + TLS EKU) |
| `codesign_targets` | list[string] | `[]` | LDAP URLs for code-signing certificate discovery (e.g. `ldap://dc.corp.com:389`) |
| `codesign_search_base` | string | `null` | LDAP search base DN for `userCertificate` discovery (e.g. `dc=corp,dc=com`) |
| `codesign_timeout` | int | `10` | Per-connection timeout (seconds) for code-signing LDAP queries |
| `aws_region` | string | `"us-east-1"` | AWS region for cloud connector |
| `aws_profile` | string | `null` | AWS named profile; `null` uses the default credential chain |
| `azure_subscription_id` | string | `null` | Azure subscription UUID |
| `azure_keyvault_urls` | list[string] | `[]` | Key Vault base URLs (e.g. `https://myvault.vault.azure.net`) |
| `jwt_targets` | list[string] | `[]` | REST endpoint URLs for JWT scanner |
| `allow_insecure_jwks` | bool | `false` | Disable TLS cert verification for JWKS fetches. Use only for internal/dev endpoints with self-signed certs. When `true`, a `HIGH` advisory finding (`ADVISORY_JWKS_VERIFY_DISABLED`) is emitted for every JWKS URL fetched. |
| `container_targets` | list[string] | `[]` | Docker image refs for container scanner |
| `source_targets` | list[string] | `[]` | Git repo paths or URLs for source scanner |
| `codesign_targets` | list[string] | `[]` | LDAP URLs for code-signing certificate discovery (e.g. `ldap://dc.corp.com:389`) |
| `codesign_search_base` | string | `null` | LDAP search base DN for `userCertificate` discovery (e.g. `dc=corp,dc=com`) |
| `codesign_timeout` | int | `10` | Per-connection timeout in seconds for code-signing LDAP queries |

> **Note:** See [Connector Guides](connectors/) for per-connector credential setup and least-privilege templates.

### Code-Signing Certificate Connector (Phase 95)

The code-signing connector discovers X.509 certificates from Active Directory LDAP servers by
reading the `userCertificate` RFC 4523 attribute. It filters for certificates carrying the
`Code Signing` Extended Key Usage (EKU OID `1.3.6.1.5.5.7.3.3`) and classifies weak-algorithm
certificates (RSA < 2048-bit, EC < 256-bit key, or SHA-1 signature) as HIGH-severity findings.

Enable the connector in the `connectors` block and activate it at scan time with the
`--inventory-code-signing` CLI flag:

```yaml
connectors:
  codesign_targets:
    - "ldap://dc01.corp.com:389"
  codesign_search_base: "dc=corp,dc=com"
  codesign_timeout: 10    # seconds; default 10
```

```bash
quirk --config config.yaml --inventory-code-signing
```

The scanner performs an anonymous LDAP bind with a paged search (page size 500). All user DNs
and certificate subject CNs that appear in log output are sanitized via `safe_str()` (control
characters and newlines are removed). No certificate content is written or transmitted
beyond the existing scan database.

**In-process TLS EKU check:** Even without `codesign_targets` configured, the `--inventory-code-signing`
flag activates an in-process check that inspects TLS certificates already collected by the TLS
scanner for the Code Signing EKU. This path requires no additional network connections and runs
against the in-memory `tls_endpoints` list.

**CBOM integration:** Code-signing certificates are emitted as CycloneDX `certificate` components
with `bom_ref = crypto/certificate/codesign/<sha256-fingerprint>`. If the same certificate was
already discovered by the TLS scanner, the TLS-derived component wins and gains a
`quirk:code-signing-eku: true` property rather than creating a duplicate component.

**Scoring impact:** The code-signing connector contributes to the **Agility Signals** subscore.
Each certificate with a weak algorithm increments the `codesign_weak_algo_count` counter; the
resulting `agility_codesign_weak_algo_ratio` reduces the subscore by up to −6.0 points
(SCORE_WEIGHTS sum: 299.0, count: 40 — Phase 95 SCORE-01).

```yaml
connectors:
  enable_aws: true
  aws_region: "us-east-1"
  aws_profile: "quirk-readonly"   # optional; omit to use default AWS credential chain

  enable_azure: true
  azure_subscription_id: "00000000-0000-0000-0000-000000000000"
  azure_keyvault_urls:
    - "https://myvault.vault.azure.net"

  enable_jwt: true
  jwt_targets:
    - "https://api.acme.com"

  enable_container: true
  container_targets:
    - "myregistry.azurecr.io/myapp:latest"

  enable_source: true
  source_targets:
    - "/path/to/repo"
    - "https://github.com/acme/backend"
```

---

## OpenAPI Spec Analysis (`[api]` extras)

Phase 94 (v5.1) introduced passive OpenAPI/Swagger spec analysis. The scanner inventories declared security schemes, plaintext `http://` server URLs, and unauthenticated path operations, with hardened defenses against `$ref` SSRF and oversized-spec DoS.

### Installing the `[api]` extras group

```bash
pip install "quirk-scanner[api]"
```

This installs `openapi-spec-validator>=0.9.0`. The `[api]` group is **not** included in `[all]` — it is opt-in to keep the base install lightweight.

> **Phase 96 update:** `schemathesis` is now included in the `[api]` extras group and powers the REST fuzzer (`--fuzz` flag). It is intentionally **excluded from `[all]`** — see [REST Fuzzing](#rest-fuzzing-active-crypto-posture-probes) below.

### CLI flag

```bash
# Local file (no network required)
quirk --config config.yaml --openapi-spec /path/to/openapi.yaml

# URL within your configured scan targets
quirk --config config.yaml --openapi-spec https://api.acme.com/openapi.json
```

The `--openapi-spec` flag accepts either a local file path or a URL. URLs must fall within the configured `targets.fqdns` scope — out-of-scope URLs are rejected before any network request is made.

### `openapi:` config block

The spec path can also be set in `config.yaml` under the `scan` block:

```yaml
scan:
  openapi_spec_path: "docs/openapi.yaml"   # local path or scope-gated URL
```

Setting `openapi_spec_path` in the config is equivalent to passing `--openapi-spec` on the CLI. A CLI flag overrides the config value.

### Security hardening

| Guard | Behavior |
|-------|----------|
| **$ref SSRF** | External or internal-network `$ref` values (e.g. `http://169.254.169.254/...`) raise `SpecParsingError` *before* the OAS validator runs. Zero outbound requests on SSRF-shaped input. |
| **10 MB size cap** | Specs larger than 10 MB are rejected before `yaml.safe_load`. Prevents billion-laughs and oversized-YAML DoS. |
| **Scope gate** | Spec URLs must start with a configured `targets.fqdns` entry. Rejected before any network request. |
| **Graceful degradation** | When `[api]` is not installed (`OPENAPI_AVAILABLE = False`), the scanner returns a single `missing_extra` advisory endpoint and continues; no exception is raised. |

### Findings produced

OpenAPI scan results appear in the standard findings table as `CryptoEndpoint(protocol="OpenAPI")` rows:

| Finding type | Severity | Description |
|-------------|----------|-------------|
| Security scheme declaration | INFO | JWT/OAuth2/API-key security scheme found in spec |
| Plaintext server | HIGH | `http://` (non-TLS) server URL declared in spec — feeds `agility_openapi_plaintext_ratio` scoring penalty |
| Unauthenticated endpoint | MEDIUM | Path operation with no security requirement declared |

---

## Authenticated Scanning (ephemeral credentials)

Phase 93 (v5.1) introduced per-scan ephemeral credential support, allowing QUIRK to attach an
HTTP-level credential to JWT/REST endpoint probes for a single scan run. Credentials are never
persisted to SQLite, the CBOM, log files, or the dashboard — they live only in-process for the
duration of the run.

### Opt-in config flag

Add `enable_authenticated_mode: true` to the `connectors` block to enable the feature:

```yaml
connectors:
  enable_jwt: true
  jwt_targets:
    - "https://api.acme.com"
  enable_authenticated_mode: true
```

Without this flag (or a CLI `--auth-*` flag), authenticated scanning is disabled and all
credential-related CLI arguments are silently ignored.

### CLI flags

| Flag | Credential scheme | Description |
|------|-------------------|-------------|
| `--auth-bearer [REF]` | Bearer token (OAuth2 / JWT) | Adds `Authorization: Bearer <token>` to probes |
| `--auth-api-key [REF]` | API-key header (`X-Api-Key`) | Adds `X-Api-Key: <key>` to probes |
| `--auth-api-key-query [REF]` | API-key query parameter | Appends `?api_key=<key>` to JWKS/probe URLs |
| `--auth-basic [REF]` | HTTP Basic (`user:password`) | Adds `Authorization: Basic <b64>` to probes |

Each flag accepts an optional `REF` argument. If `REF` is omitted the flag is treated as a bare
flag and triggers an interactive `getpass` prompt (see "Reference model" below).

### Reference-not-secret model

**Raw credential values must never appear in the CLI argument.** Passing a credential as a bare
string (e.g. `--auth-bearer eyJhbGci…`) will be rejected with a clear error.

Instead, pass a *reference* to where the credential lives:

| Input form | Example | Resolved from |
|------------|---------|---------------|
| `@file` path | `--auth-bearer @/path/to/token.txt` | File contents (first line, stripped) |
| `ENV_VAR` name | `--auth-bearer QUIRK_AUTH_TOKEN` | Environment variable at resolution time; env var is **deleted after reading** to prevent subprocess inheritance |
| Bare flag (no REF) | `--auth-bearer` | Interactive `getpass` prompt — credential is never echoed to the terminal |

**Why the reference model?** Inline secrets in `argv` are visible to `ps aux`, the shell history
(`~/.bash_history`, `~/.zsh_history`), and process-listing tools. The `@file`/`ENV_VAR`/`getpass`
forms keep the raw credential out of the process argument list entirely.

**Source precedence** (highest to lowest): interactive prompt → environment variable → `@file`/bare-flag reference.

### Ephemeral-only invariant

Credentials are held in a `bytearray` buffer (`CredentialContext`) for the scan run and
zeroed in-place via `CredentialContext.close()` on both normal exit and on any exception,
including `KeyboardInterrupt`. They are **never**:

- Written to the SQLite database (`quirk.db`)
- Included in the CBOM output (`cbom-*.json`)
- Included in log files
- Returned by the dashboard API
- Included in PDF exports

This invariant is enforced by an automated sentinel test suite (`tests/test_credential_leakage.py`,
25 tests) that injects a synthetic sentinel value across all 11 stored/rendered surfaces and asserts absence.

### Scheduler rejection (QRK-SCHED-AUTH-001)

Scheduled scans cannot use authenticated mode. Running `quirk schedule add` against a config
file that contains `enable_authenticated_mode: true` exits immediately with:

```
[QRK-SCHED-AUTH-001] Authenticated scan configs cannot be scheduled.
Fix: Remove enable_authenticated_mode from config or use a non-authenticated config for scheduled runs.
```

Exit code: `2`. This is by design — storing scheduled-scan credentials would require persisting
a secret somewhere, which violates the ephemeral-only invariant.

### Example: authenticated JWT scan

```bash
# Using a @file reference (preferred for automation)
echo "eyJhbGciOiJSUzI1NiJ9..." > /tmp/token.txt
quirk --config config.yaml --auth-bearer @/tmp/token.txt

# Using an environment variable reference
export QUIRK_AUTH_TOKEN="eyJhbGciOiJSUzI1NiJ9..."
quirk --config config.yaml --auth-bearer QUIRK_AUTH_TOKEN
unset QUIRK_AUTH_TOKEN   # QUIRK also deletes it after reading

# Interactive prompt (safest — credential never touches disk or env)
quirk --config config.yaml --auth-bearer

# API-key query parameter (appended to JWKS/probe URLs)
quirk --config config.yaml --auth-api-key-query @/tmp/apikey.txt
```

---

## REST Fuzzing (active crypto-posture probes)

Phase 96 (v5.1) introduced active REST endpoint fuzzing for crypto-posture assessment.
The fuzzer sends a bounded set of probes to discovered OpenAPI endpoints and checks for
TLS downgrade acceptance, weak cipher negotiation, missing HSTS headers, HTTP-only
credential transmission, and (behind a dedicated sub-flag) JWT RS256→HS256 algorithm
confusion. **Fuzzing is off by default and requires explicit opt-in.**

### Installing the `[api]` extras group

```bash
pip install "quirk-scanner[api]"
```

This installs `openapi-spec-validator>=0.9.0` and `schemathesis` (the request-dispatch
engine). The `[api]` group is **not** included in `[all]` — it is opt-in to keep the base
install lightweight. Running `--fuzz` without `[api]` installed prints a missing-extra
advisory and exits cleanly.

### CLI flags

| Flag | Default | Description |
|------|---------|-------------|
| `--fuzz` | `false` | Enable active REST crypto-posture fuzzing. Requires `--openapi-spec` (endpoint source) and an interactive `CONFIRM` prompt before any request is sent. |
| `--fuzz-jwt-alg-confusion` | `false` | Also run the JWT RS256→HS256 algorithm-confusion probe. Combines a Phase 93 bearer token with the target's JWKS public key to forge a symmetric token; acceptance yields a CRITICAL finding. |
| `--fuzz-budget N` | `50` | Maximum number of probe requests (hard max 500 — values above 500 are rejected before any request is sent). |

### CONFIRM gate and non-TTY hard-abort (FUZZ-01, FUZZ-03)

When `--fuzz` is set in a TTY session, the scanner prints a budget summary and requires
the user to type the **literal word `CONFIRM`** before any request is dispatched:

```
Fuzzing will send up to 50 probe requests to 3 endpoint(s).
Target: https://api.acme.com
Type CONFIRM to proceed, or press Enter to abort:
```

Any input other than `CONFIRM` (including a bare Enter) aborts cleanly with **zero
requests sent**.

> **Non-TTY hard-abort:** When stdin is not a TTY (piped input, CI/CD, scheduled jobs),
> the scanner hard-aborts **before sending any request** and prints a clear
> non-interactive-mode error. Fuzzing **never runs headlessly**. This differs from the
> nmap discovery prompt, which auto-proceeds in non-TTY mode — the fuzz gate is stricter
> by design (T-96-03).

### Six safety guardrails (FUZZ-02)

| # | Guardrail | Behavior |
|---|-----------|----------|
| 1 | GET-only by default | Only HTTP `GET` endpoints are probed; other methods require explicit future opt-in |
| 2 | Hard budget ceiling | `--fuzz-budget` default 50, hard max **500** — values above 500 are rejected before any request |
| 3 | Rate cap 5 req/s | Probe requests are rate-limited to 5 per second using the nmap TokenBucket pattern |
| 4 | CONFIRM prompt | TTY: user must type the literal word `CONFIRM`; any other input aborts with zero requests sent |
| 5 | Per-request scope enforcement | Every probe URL is validated via `validate_external_url` + `cfg.targets` before dispatch — out-of-scope URLs are rejected |
| 6 | 5xx cascade pause | After 3 consecutive HTTP 5xx responses, the fuzzer pauses and emits a warning before continuing |

### Findings produced

REST fuzzing results appear as `CryptoEndpoint(protocol="REST_FUZZ")` rows in the
standard findings table:

| Finding type | Severity | Description |
|-------------|----------|-------------|
| TLS downgrade accepted | HIGH | Server accepted a downgraded TLS version on a REST endpoint |
| Weak cipher accepted | HIGH | Server negotiated a weak cipher suite on a REST endpoint |
| HSTS header missing | HIGH | `Strict-Transport-Security` header absent on an HTTPS endpoint |
| HTTP-only credential transmission | HIGH | Endpoint accepts credentials over plain `http://` — feeds `agility_fuzz_crypto_posture_ratio` scoring penalty |
| JWT alg-confusion acceptance | CRITICAL | Server accepted an RS256→HS256 forged token (requires `--fuzz-jwt-alg-confusion`) — feeds `agility_fuzz_crypto_posture_ratio` scoring penalty |

> **CBOM note:** REST_FUZZ endpoints are excluded from the CBOM TLS and certificate
> component builders (Pass-2 and Pass-3 skip lists) to prevent phantom
> `crypto/protocol/tls/*` and `crypto/certificate/*` components for endpoints that
> were not TLS-scanned.

### Scoring impact

CRITICAL and HIGH REST fuzz findings feed the `agility_fuzz_crypto_posture_ratio` signal
in `SCORE_WEIGHTS` (weight: `4.0`, final step in the v5.1 weighted sum). The sum is
**303.0** across **41 entries** after Phase 96. INFO `probe_skipped` rows are excluded from
the finding count to prevent score drift when endpoints are unreachable.

### Example: fuzz a local OpenAPI target

```bash
# Passive OpenAPI spec analysis + active REST fuzzing
quirk --config config.yaml \
  --openapi-spec https://api.acme.com/openapi.json \
  --fuzz

# Include the JWT algorithm-confusion probe
quirk --config config.yaml \
  --openapi-spec https://api.acme.com/openapi.json \
  --fuzz --fuzz-jwt-alg-confusion

# Set a custom request budget (max 500)
quirk --config config.yaml \
  --openapi-spec https://api.acme.com/openapi.json \
  --fuzz --fuzz-budget 100
```

---

## Output Block

Controls where QU.I.R.K. writes reports, CBOM files, and its internal database.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `directory` | string | `"output"` | Directory for reports, CBOM files, and logs |
| `db_path` | string | `"output/quirk.db"` | SQLite database path for scan results |

```yaml
output:
  directory: "output"
  db_path: "output/quirk.db"
```

---

## Intelligence Block

Controls the quantum-readiness scoring calibration and version metadata.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `intelligence_version` | string | `"3.9.0"` | Intelligence layer version tag (informational) |
| `profile` | string | `"balanced"` | Score calibration profile: `lenient`, `balanced`, `strict` |
| `calibration_overrides` | dict | `{}` | Per-weight scoring overrides for advanced users |

**Score calibration profiles:**

- `lenient` — Reduces penalty weights. Use in immature environments where a score shock would be counterproductive. Suitable for a first engagement where you need to show progress rather than alarm.
- `balanced` — Default. Production-calibrated weights designed for typical enterprise networks.
- `strict` — Increases penalty weights. Use in high-compliance environments (FedRAMP, CNSA 2.0) where the client must demonstrate a tighter posture.

#### How Score Profiles Work

Score profiles adjust the weight of **crypto-agility** and **identity/certificate** scoring categories. Hygiene and TLS modernization weights are unchanged across all profiles.

| Profile | Agility Weight | Identity Weight | Use Case |
|---------|---------------|-----------------|----------|
| `strict` | 1.4x base | 1.4x base | Post-quantum readiness assessment — amplifies crypto-agility and certificate hygiene penalties |
| `balanced` | 1.0x (default) | 1.0x (default) | General-purpose assessment |
| `lenient` | 0.7x base | 0.7x base | Status-quo baseline — reduces agility and identity penalties for organizations not yet planning PQC migration |

Setting `calibration_overrides` in the intelligence section allows fine-grained per-weight adjustments that override profile defaults. For example:

```yaml
intelligence:
  profile: strict
  calibration_overrides:
    agility_rsa_only_penalty: 4.0  # Override strict's amplified RSA penalty
```

```yaml
intelligence:
  intelligence_version: "3.9.0"
  profile: "balanced"   # lenient|balanced|strict
  calibration_overrides: {}
```

---

## Scan Profiles (`--profile` flag)

The `--profile` flag applies a preset combination of timeouts and TLS enumeration depth. Profiles override the corresponding `scan` block keys at runtime — `config.yaml` is not modified.

| Profile | Timeout | TLS enum mode | Use case |
|---------|---------|---------------|----------|
| `quick` | 2s | `off` | Discovery pass — find live hosts, no deep enum |
| `standard` | 5s | `fast` | Default — balances speed and depth |
| `deep` | 10s | `deep` | Full enumeration — slow, most thorough |

```bash
# Discovery pass to find live hosts quickly
quirk --config config.yaml --profile quick

# Default balanced scan
quirk --config config.yaml --profile standard

# Thorough enumeration for final deliverable
quirk --config config.yaml --profile deep
```

---

## CLI Flag Reference

### `quirk` — Scan Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--config PATH` | (interactive) | Path to config.yaml; skips interactive prompts when provided |
| `--profile` | `standard` | Scan profile: `quick`, `standard`, `deep` |
| `--score-profile` | `balanced` | Scoring calibration: `lenient`, `balanced`, `strict` |
| `--verbose` | `false` | Verbose output during scan |
| `--progress` | `false` | Show tqdm progress bars |
| `--discovery` | `builtin` | Discovery mode: `builtin` or `nmap` |
| `--nmap-path` | `nmap` | Path to nmap executable |
| `--nmap-timeout` | `1800` | Nmap discovery timeout in seconds |
| `--nmap-extra-args` | `""` | Extra nmap arguments (pass as quoted string) |
| `--safe-mode` | `false` | Reduce concurrency and increase timeouts for fragile networks |
| `--rate-limit` | `0.0` | Targets per second rate limit (0 = disabled) |
| `--cache` | `false` | Enable discovery/fingerprint result cache |
| `--cache-ttl-hours` | `24` | Cache time-to-live in hours |
| `--resume` | `false` | Reuse cache if valid (skip re-discovery) |
| `--force-discovery` | `false` | Ignore existing discovery cache and re-run |
| `--inventory-code-signing` | `false` | Inventory code-signing certificates from LDAP `userCertificate` attributes and in-process TLS EKU check (Phase 95 CSIGN-01) |
| `--fuzz` | `false` | Enable active REST crypto-posture fuzzing (requires `--openapi-spec`; TTY `CONFIRM` prompt; hard-aborts in non-TTY) |
| `--fuzz-jwt-alg-confusion` | `false` | Also run JWT RS256→HS256 algorithm-confusion probe; acceptance = CRITICAL |
| `--fuzz-budget N` | `50` | Maximum probe requests (hard max **500**; values above 500 are rejected) |

### `quirk serve` — Dashboard Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--port` | `8512` | Port to serve the dashboard on |
| `--host` | `127.0.0.1` | Host address to bind |
| `--no-open` | `false` | Suppress auto-opening of browser on startup |

```bash
# Start dashboard on default port
quirk serve

# Start on a different port without auto-opening the browser
quirk serve --port 9000 --no-open

# Bind to all interfaces (e.g. for a remote development server)
quirk serve --host 0.0.0.0 --port 8512
```

### `quirk token` — Dashboard API Token CLI (Phase 102, AUTH-01)

The `quirk token` subcommand manages the `security.api_token` key in your QUIRK YAML config. The token is used to authenticate requests to the dashboard API and browser login form.

| Subcommand | Description |
|------------|-------------|
| `quirk token generate` | Mint a new CSPRNG token (`secrets.token_urlsafe(32)`) and write it to `security.api_token` in your config file. Prints the token to stdout so you can copy it for browser login. |
| `quirk token rotate` | Identical to `generate` — overwrites `security.api_token` with a new token, immediately invalidating the previous one. Any active dashboard session using the old token will be returned to the login form on the next API request. |
| `quirk token show` | Print the currently persisted token from the YAML config file. Reads the raw YAML value; does **not** read `QUIRK_API_TOKEN`. Exits 1 if the config file is not found. |

Pass `--config /path/to/config.yaml` to any subcommand to target a non-default config location.

```bash
# Generate a token and write it to config.yaml
quirk token generate --config config.yaml

# Rotate the token (invalidates the old one immediately)
quirk token rotate --config config.yaml

# Show the currently configured token (reads YAML, not env var)
quirk token show --config config.yaml
```

> **Precedence note:** If `QUIRK_API_TOKEN` is set in the environment, it takes precedence over the `security.api_token` YAML value at runtime. `quirk token show` always displays the YAML-persisted value; if the env var is set, a reminder is printed indicating that the env var overrides the file value for the running dashboard process.

> **Security note:** `quirk token show` echoes the raw token to the terminal, which may appear in terminal scrollback. This is a local-operator tool convenience — the token is never transmitted over the network by this command. Never embed the token value in shell scripts, version-controlled config files, or URLs.

---

## Dashboard Authentication (Phase 102, AUTH-01..03)

The QUIRK dashboard (served by `quirk serve`) optionally enforces token-based authentication on all `/api/*` routes. Authentication is **off by default** — an empty or absent `security.api_token` means the dashboard is accessible without credentials (suitable for local development only).

### Enabling authentication

Add a `security:` block to your QUIRK YAML config and populate `api_token`:

```yaml
security:
  api_token: ""   # populated by: quirk token generate --config config.yaml
```

Run `quirk token generate --config config.yaml` to write a random token into this field. Once the token is non-empty, the dashboard requires authentication on every `/api/*` request.

### Token precedence

| Source | Precedence | Notes |
|--------|-----------|-------|
| `QUIRK_API_TOKEN` env var | **Highest** | Set this in production deployments; overrides YAML at startup |
| `security.api_token` in YAML | Default | Written by `quirk token generate` / `quirk token rotate` |

### API authentication (programmatic clients)

All `/api/*` endpoints accept a token via two equivalent headers. **`X-API-Key` takes precedence** — if it is present, `Authorization: Bearer` is not consulted.

| Header | Format | Notes |
|--------|--------|-------|
| `X-API-Key` | `X-API-Key: <token>` | Preferred for API clients |
| `Authorization` | `Authorization: Bearer <token>` | Fallback; supported for compatibility |

Both paths use `hmac.compare_digest` for timing-safe comparison. An invalid or absent token on a protected route returns HTTP 401 with error code `DASHBOARD-001`.

```bash
# Using X-API-Key (preferred)
curl -H "X-API-Key: <your-token>" http://localhost:8512/api/scans

# Using bearer token (fallback)
curl -H "Authorization: Bearer <your-token>" http://localhost:8512/api/scans
```

### Browser login flow

1. Open the dashboard in a browser (`http://localhost:8512` by default).
2. If authentication is enabled, you are presented with a "Dashboard Login" card. Paste your token (from `quirk token show`) into the password field and click **Unlock Dashboard**.
3. A correct token loads the full dashboard. An incorrect token shows an inline error ("Invalid token. Check your token and try again.") and clears the input — no page redirect occurs.
4. Click **Sign out** in the sidebar to clear the session and return to the login form. The token is removed from browser storage immediately.
5. **Mid-session token rotation:** If you run `quirk token rotate` while a browser session is open, the next API request from that session returns HTTP 401 and the dashboard automatically returns you to the login form. Re-enter the new token to resume.

### Auth-disabled passthrough (development convenience)

When `security.api_token` is empty and `QUIRK_API_TOKEN` is not set, the dashboard serves all routes without authentication. This is intentional for local development and single-operator use. Do not deploy the dashboard on a network-accessible interface without setting a token.

---

## Minimal Valid Configuration

The minimum configuration to run a first scan. All other keys use their defaults.

```yaml
assessment:
  name: "Quantum Crypto Readiness - CLIENT NAME"
  data_classification: "confidential"
  report_owner: "CLIENT NAME"
  timezone: "America/New_York"

targets:
  cidrs: [127.0.0.1]
```

Save this as `config.yaml` in your working directory, then run:

```bash
quirk --config config.yaml
```

---

## Full Reference Configuration

A complete `config.yaml` showing all keys with their defaults, as a copy-pasteable template:

```yaml
assessment:
  name: "Quantum Crypto Readiness - CLIENT NAME"
  data_classification: "confidential"   # public|internal|confidential|regulated
  report_owner: "CLIENT NAME"
  timezone: "America/New_York"

scan:
  timeout_seconds: 5
  concurrency: 200
  ports_tls: [443, 8443, 9443, 10443, 11443, 12443, 8444, 8000, 2222, 5555]
  include_sni: true
  tls_enum_mode: fast                   # off|fast|deep
  fingerprint_timeout_seconds: 2
  fingerprint_concurrency: 200
  tls_timeout_seconds: 5
  tls_concurrency: 150
  ssh_timeout_seconds: 5
  ssh_concurrency: 100

targets:
  fqdns: []
  cidrs: [127.0.0.1]
  include_ips: []
  exclude_ips: []

connectors:
  enable_aws: false
  enable_azure: false
  enable_windows_adcs: false
  enable_jwt: false
  enable_container: false
  enable_source: false
  aws_region: "us-east-1"
  aws_profile: null
  azure_subscription_id: null
  azure_keyvault_urls: []
  jwt_targets: []
  container_targets: []
  source_targets: []
  codesign_targets: []
  codesign_search_base: null
  codesign_timeout: 10

output:
  directory: "output"
  db_path: "output/quirk.db"

intelligence:
  intelligence_version: "3.9.0"
  profile: "balanced"                   # lenient|balanced|strict
  calibration_overrides: {}
```

---

## Notifications (v5.3+)

Phase 101 introduces a global notification system that alerts operators after each scheduled scan when HIGH/CRITICAL findings appear or the quantum-readiness score regresses. Notifications are **off by default** — opt in by adding a `[notifications]` block to your QUIRK YAML config.

### Prerequisites

**Set `QUIRK_CONFIG_PATH`** to the path of your QUIRK YAML config file before starting the scheduler. The scheduler's `--config` argument points to the SQLite database; the notification system reads its YAML config from `QUIRK_CONFIG_PATH`.

```bash
export QUIRK_CONFIG_PATH=/etc/quirk/config.yaml
export QUIRK_DB_PATH=/var/lib/quirk/quirk.db
quirk schedule run --config "$QUIRK_DB_PATH"
```

Both env vars must be set for scheduled notifications to work (Assumption A2).

### Trigger rules (NOTIFY-02)

A notification fires when **either** of these conditions is met:

| Condition | Threshold |
|-----------|-----------|
| New HIGH or CRITICAL findings since the last scan | ≥ 1 new HIGH/CRITICAL |
| Readiness score regression | Score drops more than `trigger_score_floor` points |

Notifications are **never** sent on:
- The very first scan (no previous baseline to compare against)
- MEDIUM-only changes with score delta within the floor

### Notification config block

Add a `notifications:` block at the top level of your QUIRK YAML config:

```yaml
notifications:
  trigger_score_floor: -5       # notify when score drops more than 5 points (default -5)

  # Optional: Slack incoming-webhook delivery (NOTIFY-03)
  slack:
    slack_webhook_env: QUIRK_SLACK_WEBHOOK      # env var NAME holding the webhook URL
    dashboard_base_url: https://quirk.internal  # optional link in Slack messages

  # Optional: Email delivery via SMTP (NOTIFY-04)
  email:
    smtp_host: smtp.corp.com
    smtp_port: 587              # 587 = STARTTLS (default), 465 = SSL
    smtp_from: quirk@corp.com
    recipients:
      - security@corp.com
      - oncall@corp.com
    smtp_user: quirk-svc        # omit for unauthenticated relay
    smtp_password_env: QUIRK_SMTP_PASSWORD  # env var NAME holding the password
    use_ssl: false              # true = SMTP_SSL (port 465); false = STARTTLS (port 587)
    timeout_seconds: 10

  # Optional: Generic outbound webhook (NOTIFY-05)
  webhook:
    url_env: QUIRK_WEBHOOK_URL          # env var NAME holding the target URL
    hmac_key_env: QUIRK_WEBHOOK_HMAC_KEY  # env var NAME for HMAC-SHA256 signing key (optional)
    timeout_seconds: 10
```

### Environment variables for secrets

**Secrets must never appear in the YAML config.** The config stores only the *name* of the environment variable; the actual secret is read from the environment at delivery time and is never persisted.

| Env var name | Purpose | Example value |
|---|---|---|
| `QUIRK_SLACK_WEBHOOK` | Slack incoming-webhook URL | `https://hooks.slack.com/services/T.../B.../xxx` |
| `QUIRK_SMTP_PASSWORD` | SMTP account password | `s3cr3t` |
| `QUIRK_WEBHOOK_URL` | Target webhook endpoint | `https://siem.corp.com/api/events` |
| `QUIRK_WEBHOOK_HMAC_KEY` | HMAC-SHA256 signing key | `a-long-random-string` |
| `QUIRK_CONFIG_PATH` | Path to QUIRK YAML config | `/etc/quirk/config.yaml` |

> **Note on naming:** The config field `slack_webhook_env: QUIRK_SLACK_WEBHOOK` means "read the webhook URL from the env var named `QUIRK_SLACK_WEBHOOK`". You can use any env var name — the convention shown above is recommended.

### Security controls

| Control | Description |
|---------|-------------|
| **SSRF protection** | Every channel validates the destination URL/host via `validate_external_url()` before connecting — loopback, RFC1918, and cloud metadata IPs are blocked (ISEC-01). |
| **Secret scrubbing** | Any exception raised during delivery is passed through `safe_str()` before being written to the `integration_deliveries` audit log — Slack tokens (`xoxb-*`), SMTP passwords, and webhook URLs are redacted (ISEC-02). |
| **Failure isolation** | A delivery failure on one channel never blocks other channels or corrupts the scan record. The scheduler `_dispatch_schedule` wraps the entire notification call in `try/except` (NOTIFY-07). |
| **Optional Slack dep** | `slack_sdk` is an optional dependency. Missing `slack_sdk` logs a WARNING instead of raising `ImportError`. Install with `pip install quirk-scanner[notify]` (ISEC-04). |
| **Outbound whitelist** | Webhook payloads contain only drift-level aggregate fields (scores, counts). Host/IP/protocol topology is excluded from all outbound integration payloads (ISEC-03). |

### Installing the Slack dependency

Slack delivery requires `slack_sdk`:

```bash
pip install "quirk-scanner[notify]"
```

This extra is included in `[all]`. Email and webhook delivery use Python stdlib only — no extra installation needed.

### Audit log

Every delivery attempt — successful or failed — writes one row to the `integration_deliveries` SQLite table:

| Column | Description |
|--------|-------------|
| `scan_id` | ISO timestamp identifying the scan session |
| `destination` | `"slack"` / `"email"` / `"webhook"` |
| `status` | `"ok"` or `"failed"` |
| `attempted_at` | UTC timestamp of the delivery attempt |
| `error_summary` | `safe_str(exc)` on failure — secrets are always scrubbed |

Query the audit log from the QUIRK database:

```bash
sqlite3 "$QUIRK_DB_PATH" \
  "SELECT attempted_at, destination, status, error_summary FROM integration_deliveries ORDER BY attempted_at DESC LIMIT 20;"
```

---

## SIEM Export (syslog/CEF)

Phase 103 introduces SIEM export via syslog with Common Event Format (CEF). QUIRK formats each
finding as a CEF:0 event and delivers it to a syslog collector over UDP or TCP. Export is
**off by default** — opt in by adding a `siem:` block to your QUIRK YAML config.

> **Network placement:** syslog is plaintext (no TLS). Place your syslog collector on a trusted
> internal network segment. TLS-wrapped syslog (RFC 5425), Splunk HEC, and Elastic-native output
> are planned for a future release.

### Prerequisites

**Set `QUIRK_CONFIG_PATH`** to the path of your QUIRK YAML config file before running the
scheduler. The scheduler's `--config` argument points to the SQLite database; the SIEM system
reads its YAML config from `QUIRK_CONFIG_PATH`.

```bash
export QUIRK_CONFIG_PATH=/etc/quirk/config.yaml
export QUIRK_DB_PATH=/var/lib/quirk/quirk.db
quirk schedule run --config "$QUIRK_DB_PATH"
```

### `siem:` config block

Add a `siem:` block at the top level of your QUIRK YAML config:

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `host` | string | *(required)* | Hostname or IP of your syslog/CEF collector |
| `port` | int | `514` | UDP or TCP port of the collector |
| `protocol` | string | `"udp"` | Transport: `"udp"` or `"tcp"` |
| `export_after_scan` | bool | `false` | Automatically export findings after each scheduled scan completes |
| `timeout_seconds` | int | `5` | Socket send timeout in seconds |

```yaml
siem:
  host: siem.corp.example.com
  port: 514
  protocol: udp          # udp (default) or tcp
  export_after_scan: true
  timeout_seconds: 5
```

### CLI usage: `quirk export --siem`

Export findings from the most recent scan to your SIEM at any time:

```bash
# Export the most recent findings-*.json in the default output directory
quirk export --siem

# Specify an explicit findings file
quirk export --siem --input output/findings-2026-05-25-120000.json

# Specify the output directory to search for the latest findings file
quirk export --siem --output-dir /var/lib/quirk/output
```

**Prerequisites:**
- `QUIRK_CONFIG_PATH` must be set and point to a YAML config with a valid `siem:` block.
- `QUIRK_DB_PATH` must point to the QUIRK SQLite database (used to write the audit row).

Exit codes: `0` = all events delivered; `1` = config/flag error; `2` = no findings file found.

### CEF field mapping

Each finding produces one `CEF:0` event. QUIRK maps finding fields as follows:

| CEF field | Finding field | Notes |
|-----------|--------------|-------|
| Header severity | `severity` | `CRITICAL=10`, `HIGH=8`, `MEDIUM=5`, `LOW=3`; unknown defaults to 3 |
| `name` (header) | `title` | Pipe characters escaped as `\|`; backslash as `\\` |
| `signature` (header) | `category` → `id` → slugified title | Falls back when `category`/`id` absent |
| `dhost` | `host` | Scanned host |
| `dpt` | `port` | Scanned port |
| `cs1` | `category` | Finding category label |
| `cs2` | `description` | Truncated at 256 characters |
| `msg` | `recommendation` | Truncated at 256 characters |

**Payload safety:** The CEF payload contains only the fields listed above. Certificate PEM data,
certificate SANs, private key material, PKI topology details, and compliance control mappings are
**never** included in the CEF event. All extension field values are escaped: backslash becomes
`\\`, equals becomes `\=`, and newlines become the literal two-character sequence `\n`.

### Semantics

- **One event per finding:** Each finding in the findings JSON produces one CEF event. A scan
  with 30 findings produces 30 events.
- **After-scan export:** When `export_after_scan: true`, the SIEM export hook fires automatically
  after each scheduled scan completes. The hook is isolated — a SIEM delivery failure never
  aborts the scan, corrupts the scan record, or blocks other integrations (NOTIFY-07 / SIEM-01).
- **Audit log:** Every export attempt — successful or failed — writes one row to the
  `integration_deliveries` SQLite table with `destination="siem"`, `status="ok"/"failed"`, and
  a scrubbed `error_summary` on failure.
- **TCP framing:** Raw TCP (no octet-count prefix, no TLS). Configure your receiver for
  traditional LF-terminated or raw-bytes syslog input.

### Audit log

Query the audit log from the QUIRK database:

```bash
sqlite3 "$QUIRK_DB_PATH" \
  "SELECT attempted_at, destination, status, error_summary FROM integration_deliveries WHERE destination='siem' ORDER BY attempted_at DESC LIMIT 20;"
```

### Deferred

The following SIEM delivery paths are planned for a future release and are **not** available in
Phase 103:
- TLS-wrapped syslog (RFC 5425)
- Splunk HTTP Event Collector (HEC)
- Elastic-native output (Elasticsearch ingest API)

---

## Jira Ticketing (v5.3+)

Phase 104 introduces per-finding Jira issue creation. QUIRK opens one Jira issue per
finding discovered during a scan, tags each issue with a SHA-256 fingerprint label for
dedup, and adds a rediscovery comment on re-runs instead of creating duplicate issues.
Ticketing is **off by default** — opt in by adding a `ticketing:` block to your QUIRK
YAML config.

> **Note:** ServiceNow ticketing (TICKET-02) arrives in Phase 105, reusing the same
> abstraction. The `ticketing.jira` block documented here does not change when ServiceNow
> is added.

### Prerequisites

Install the `[tickets]` extras group before using `quirk ticket create`:

```bash
pip install "quirk-scanner[tickets]"
```

This installs `jira>=3.10.5`. The `[tickets]` group is included in `[all]`. Running
`quirk ticket create` without `[tickets]` installed prints a missing-extra advisory and
exits with code 2 — no ImportError traceback is raised.

**Set `QUIRK_CONFIG_PATH`** to your QUIRK YAML config before running the ticket command:

```bash
export QUIRK_CONFIG_PATH=/etc/quirk/config.yaml
export QUIRK_DB_PATH=/var/lib/quirk/quirk.db
quirk ticket create --input output/findings-2026-05-25-120000.json
```

### `ticketing.jira` config block

Add a `ticketing:` block at the top level of your QUIRK YAML config:

| Key | Type | Default | Required | Description |
|-----|------|---------|----------|-------------|
| `jira_url` | string | *(required)* | Yes | Base URL of your Jira instance (e.g. `https://acme.atlassian.net`) |
| `jira_user_env` | string | *(required)* | Yes | **Name** of the env var holding your Jira username or email — not the value itself |
| `jira_token_env` | string | *(required)* | Yes | **Name** of the env var holding your Jira API token or PAT — not the value itself |
| `project_key` | string | *(required)* | Yes | Jira project key (e.g. `SEC`) |
| `issue_type` | string | `"Bug"` | No | Jira issue type to create (e.g. `"Bug"`, `"Task"`, `"Security Finding"`) |
| `auth_mode` | string | `"cloud"` | No | Authentication mode: `"cloud"` or `"server"` |
| `allow_internal` | bool | `false` | No | Set `true` for self-hosted Jira on RFC1918 networks (see SSRF note below) |

```yaml
ticketing:
  jira:
    jira_url: https://acme.atlassian.net
    jira_user_env: QUIRK_JIRA_USER      # env var NAME holding your Jira email
    jira_token_env: QUIRK_JIRA_TOKEN    # env var NAME holding your Jira API token or PAT
    project_key: SEC
    issue_type: Bug                     # default
    auth_mode: cloud                    # cloud (default) or server
    allow_internal: false               # set true for self-hosted Jira on RFC1918
```

### Credential isolation model

**Credentials must never appear in the YAML config.** The config stores only the *name*
of the environment variable; QUIRK reads the actual credential from the environment at
run time. Credentials are never:

- Written to the YAML config or SQLite database
- Included in log files or exception messages (safe_str scrubs Authorization headers)
- Included in CBOM output, PDF exports, or dashboard API responses

| Field | Env var name you set | Example env var value |
|-------|---------------------|-----------------------|
| `jira_user_env: QUIRK_JIRA_USER` | `QUIRK_JIRA_USER` | `alice@acme.com` |
| `jira_token_env: QUIRK_JIRA_TOKEN` | `QUIRK_JIRA_TOKEN` | `ATATT3xFfGF0...` |

### Cloud vs. server authentication

| `auth_mode` | Jira edition | Credential used | SDK call |
|-------------|-------------|-----------------|----------|
| `cloud` (default) | Jira Cloud (atlassian.net) | Email + API token → HTTP Basic | `JIRA(basic_auth=(user, token))` |
| `server` | Jira Data Center / Server (self-hosted) | Personal Access Token (PAT) | `JIRA(token_auth=token)` |

For Jira Cloud, generate an API token at **Account Settings → Security → API tokens**.
For Jira Data Center/Server, generate a PAT under **Profile → Personal Access Tokens**.

### SSRF protection

`jira_url` is validated by QUIRK's `validate_external_url()` guard before any connection
is made. Loopback addresses (`127.x.x.x`), RFC1918 ranges (`10.x`, `172.16–31.x`,
`192.168.x`), and cloud metadata IPs (`169.254.169.254`) are blocked by default.

For self-hosted Jira deployed on an internal network, set `allow_internal: true`. This
allows RFC1918 `jira_url` values while still blocking cloud metadata IPs.

### CLI usage: `quirk ticket create`

Create Jira issues from a completed scan's findings file:

```bash
# Create issues from the most recent findings-*.json in the default output directory
quirk ticket create

# Specify an explicit findings file
quirk ticket create --input output/findings-2026-05-25-120000.json

# Specify the output directory to search for the latest findings file
quirk ticket create --output-dir /var/lib/quirk/output
```

**Prerequisites:**
- `pip install "quirk-scanner[tickets]"` (or `[all]`)
- `QUIRK_CONFIG_PATH` set and pointing to a YAML config with a valid `ticketing.jira` block
- `QUIRK_DB_PATH` set to the QUIRK SQLite database (used to write audit rows)
- `QUIRK_JIRA_USER` and `QUIRK_JIRA_TOKEN` set in the environment

Exit codes: `0` = all findings dispatched; `1` = config error; `2` = missing `[tickets]`
extra, no findings file found, or missing config.

### Dedup and rediscovery behavior

QUIRK computes a SHA-256 fingerprint for each finding using the formula
`SHA256(host:port::title)`. On every `quirk ticket create` run:

- **New finding** (fingerprint not seen): one Jira issue is created and the fingerprint is
  stored in the `integration_deliveries` audit table.
- **Rediscovery** (fingerprint already in `integration_deliveries`): a comment is added to
  the existing Jira issue noting the rediscovery. No duplicate issue is created.

Re-running `quirk ticket create` against the same findings file is safe — it produces
zero duplicate issues on all subsequent runs.

### Audit log

Every ticket dispatch attempt — successful or failed — writes one row to the
`integration_deliveries` SQLite table:

| Column | Description |
|--------|-------------|
| `scan_id` | Scan session identifier |
| `finding_hash` | SHA-256 fingerprint of the finding (`host:port::title`) |
| `destination` | `"jira"` |
| `status` | `"ok"` or `"failed"` |
| `attempted_at` | UTC timestamp of the dispatch attempt |
| `error_summary` | `safe_str(exc)` on failure — Authorization headers always scrubbed |

Query the audit log:

```bash
sqlite3 "$QUIRK_DB_PATH" \
  "SELECT finding_hash, status, attempted_at, error_summary FROM integration_deliveries WHERE destination='jira' ORDER BY attempted_at DESC LIMIT 20;"
```

---

## Compliance Frameworks

QUIRK's `COMPLIANCE_MAP` (in `quirk/compliance/__init__.py`) maps every finding
category to one or more of the following frameworks. As of Phase 52 (v4.7), all
frameworks are kept fresh by the `STALENESS_THRESHOLD_DAYS` gate and verified
by `quirk doctor` before each scan.

| Framework | Version | Builder helper |
|-----------|---------|----------------|
| PCI-DSS | 4.0.1 | `_pci(control)` |
| HIPAA | 2024-rev (45 CFR §164.312) | `_hipaa(control)` |
| FIPS 140-3 | NIST FIPS 140-3 | `_fips(control)` |
| SOC2 | 2017-rev (Trust Services Criteria) | `_soc2(control)` — Phase 52 |
| ISO 27001 | ISO 27001:2022 (8.x clause numbering) | `_iso(control)` — Phase 52 |

**ISO 27001:2022 control assignments** (Phase 52):
- `8.24` — Use of cryptography (algorithm/key-size findings)
- `8.26` — Application security requirements (TLS/protocol transport findings)
- `8.28` — Secure coding (source-code scanner findings)

**SOC2 CC6.x control assignments** (Phase 52):
- `CC6.6` — Logical access controls (authentication, key, certificate findings)
- `CC6.7` — Transmission encryption (cipher, protocol, transport findings)

CBOM algorithm components carry a `quirk:fips140-3-status` property
(`approved` or `non-approved`) derived from the NIST quantum security level.
The `certified` tier is reserved for a future phase that will ingest CMVP
module attestation.
