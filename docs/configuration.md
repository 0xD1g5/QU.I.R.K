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
| `aws_region` | string | `"us-east-1"` | AWS region for cloud connector |
| `aws_profile` | string | `null` | AWS named profile; `null` uses the default credential chain |
| `azure_subscription_id` | string | `null` | Azure subscription UUID |
| `azure_keyvault_urls` | list[string] | `[]` | Key Vault base URLs (e.g. `https://myvault.vault.azure.net`) |
| `jwt_targets` | list[string] | `[]` | REST endpoint URLs for JWT scanner |
| `container_targets` | list[string] | `[]` | Docker image refs for container scanner |
| `source_targets` | list[string] | `[]` | Git repo paths or URLs for source scanner |

> **Note:** See [Connector Guides](connectors/) for per-connector credential setup and least-privilege templates.

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

output:
  directory: "output"
  db_path: "output/quirk.db"

intelligence:
  intelligence_version: "3.9.0"
  profile: "balanced"                   # lenient|balanced|strict
  calibration_overrides: {}
```
