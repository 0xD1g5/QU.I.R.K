# QU.I.R.K. — Operator's Guide

*(Audience: enterprise administrators deploying and operating QU.I.R.K. on customer
estates. This is the single canonical entry point — read top-to-bottom for a deployment
walkthrough or jump to the section you need. Each section is short by design and links
to a deeper doc where one exists.)*

**Prerequisites:**
- Python 3.11+
- macOS / Linux host with outbound network reach to scan targets
- (Optional) Docker for the chaos lab smoke test

---

## 1. Install

QU.I.R.K. installs from PyPI. Use `pip install quirk` for the core scanner (TLS, SSH,
JWT, Discovery, Fingerprint), or `pip install quirk-scanner[all]` for a one-shot install of
every optional bundle except `[identity]`. The `[identity]` extra (Kerberos, SAML,
DNSSEC) is intentionally excluded from `[all]` because impacket transitively downgrades
the `cryptography` package, breaking the TLS scanner (Phase 45-01 D-07). Install
`pip install quirk-scanner[identity]` separately into its own environment if you need
identity-protocol coverage.

> See also: [`docs/installation.md`](installation.md) for full install reference,
> system requirements, and OS package prerequisites.

---

## 2. Configure

QU.I.R.K. reads `./config.yaml` by default and accepts `--config <path>` to point at
another file. The config has six top-level blocks: `assessment`, `scan`, `targets`,
`connectors`, `output`, and `intelligence`. The `connectors.enable_*` flags are gated
by optional extras — enabling a flag whose extra is missing does **not** fail the run;
it emits a `missing_extra` advisory finding (Phase 45 INSTALL-02).

### 2.1 Generate a starter config — `quirk init`

Run `quirk init` to scaffold a starter `config.yaml` in the current directory. The
command copies `quirk/config_template.yaml` and is the recommended starting point for
new deployments. Edit the generated file to set assessment metadata, target lists, and
connector enable flags before your first scan.

```bash
quirk init                  # writes ./config.yaml
quirk --config config.yaml  # use the generated config
```

### 2.2 Optional extras matrix

| Extra | Adds | Typical use |
|-------|------|-------------|
| `quirk-scanner[dashboard]` | FastAPI server + Playwright PDF rendering | Local web dashboard, PDF reports |
| `quirk-scanner[identity]` | impacket, dnspython, signxml | Kerberos / SAML / DNSSEC scanners (install separately — not in `[all]`) |
| `quirk-scanner[cloud]` | google-cloud-kms, hvac, kubernetes | GCP KMS, HashiCorp Vault, Kubernetes connectors |
| `quirk-scanner[db]` | psycopg, mysql-connector-python | Postgres / MySQL TLS-mode + RDS scanning |
| `quirk-scanner[motion]` | aiokafka, pika, redis, azure-servicebus, boto3 SQS | Email scanner + broker scanner (Kafka / AMQP / Redis / Service Bus / SQS) |
| `quirk-scanner[all]` | Everything above **except** `[identity]` | One-shot enterprise install |

> See also: [`docs/configuration.md`](configuration.md) for the full reference of every
> config block and flag, [`docs/sample-config.yaml`](sample-config.yaml) for an
> annotated example.

---

## 3. Scan

Two entry points: `quirk` (no args) launches the interactive wizard (recommended for first
use); `quirk --config config.yaml` runs non-interactively against a pre-authored
config (recommended for CI and customer engagements). Targets accept multi-line paste,
`@filepath` indirection, `--targets-file <path>`, and IPv4 CIDR ranges (Phase 47).
Outputs land in `output.directory` (default `./quirk-output/`): an HTML report, a PDF,
`executive.md`, `technical.md`, `findings-<ts>.json`, `intelligence-<ts>.json`, and
the CycloneDX CBOM as both `cbom-<ts>.json` and `cbom-<ts>.xml`.

### 3.1 Interpreting Results

Findings carry a severity, a quantum-readiness band (`safe` / `at-risk` / `vulnerable`),
and (where the title joins `COMPLIANCE_MAP`) PCI-DSS / HIPAA / FIPS 140-3 control
references. The CBOM enumerates every cryptographic asset discovered.

> See also: [`docs/getting-started.md`](getting-started.md) for a zero-to-first-scan
> walkthrough, [`docs/report-interpretation.md`](report-interpretation.md) for
> plain-English finding/score explanations and client-conversation guidance.

---

## 4. Validation / Smoke Test

Before pointing QU.I.R.K. at a production estate, run it against the bundled chaos
lab to confirm the install is healthy and findings render correctly. The lab spins up
intentionally weak TLS, SSH, JWT, container, broker, and email targets via Docker
Compose profiles, with an oracle of expected findings per profile.

> See also: [`docs/chaos-lab.md`](chaos-lab.md).

---

## 5. Troubleshooting

### 5.1 Scan failures

- **Permission denied on a target** — confirm the QU.I.R.K. host can reach the port;
  check firewall and security-group rules. TCP-connect failures surface as a
  `connection refused` / `timeout` finding rather than crashing the scan.
- **Timeouts** — adjust the relevant `scan.timeouts.<scanner>_seconds` knob
  (`tls_seconds`, `ssh_seconds`, `dnssec_seconds`, etc.). See
  [`docs/timeout-retry-audit.md`](timeout-retry-audit.md) for per-scanner defaults.
- **`missing_extra` advisory finding** — install the named extra
  (e.g. `pip install quirk-scanner[identity]` for Kerberos). Phase 45 INSTALL-02 surfaces
  these instead of silently skipping the scanner.
- **TLS handshake errors against modern endpoints** — confirm the installed
  `cryptography` package version. Do not let `quirk-scanner[identity]`'s impacket dependency
  downgrade it (Phase 45-01 D-07); install `[identity]` in a separate environment if
  necessary.

### 5.2 Database / output

- **`db_path` permission error** — confirm the directory is writable. Default is
  `./quirk.db` under the working directory.
- **Migrations** — schema migrations are additive only (`_ensure_*_columns` helpers
  in `quirk/db.py`); deleting `quirk.db` is safe but loses scan history.
- **CBOM file generation** — every run emits `cbom-<ts>.json` and `cbom-<ts>.xml`;
  both must validate against CycloneDX 1.6.
- **PDF render failure** — install `quirk-scanner[dashboard]` (which pulls Playwright) and run
  `playwright install chromium` once on the host.

### 5.3 Dashboard

- **Vite build errors** — only relevant when rebuilding the React SPA from source; the
  published wheel ships a built bundle at `quirk/dashboard/static/`.
- **Stale `.vite/`** — delete `.vite/` under `src/dashboard/` and rebuild.
- **Port conflict on 8512** — pass `quirk serve --port <other>`. The dashboard binds
  loopback only by default.
- **Data not loading** — confirm a recent scan has populated `quirk.db`; the dashboard
  reads SQLite directly.

### 5.4 Connector gotchas

For per-connector authentication and IAM-permission issues, see the dedicated connector
docs: [`docs/connectors/aws.md`](connectors/aws.md),
[`docs/connectors/azure.md`](connectors/azure.md),
[`docs/connectors/docker.md`](connectors/docker.md),
[`docs/connectors/git.md`](connectors/git.md).

---

## 6. Per-Scanner Reference

Each scanner emits findings into the same `crypto_endpoints` SQLite table; runtime
ordering is governed by `run_scan.py` phase timers. Cloud and infra connectors with
dedicated docs link out; protocol scanners that lack a connector doc get a short
inline subsection below the table.

### 6.1 Compact reference table

| Scanner | Scans | Config flag(s) | Optional deps | Sample finding |
|---------|-------|----------------|---------------|----------------|
| Discovery (nmap) | TCP port discovery before fingerprinting | wizard prompt, `--targets-file`, `cidrs:` | `nmap` binary | (advisory) "Scanner skipped — optional extra not installed" |
| TLS | TLS handshake, cert chain, ciphers, key sizes | `scan.ports_tls`, `scan.include_sni`, `timeouts.tls_seconds` | `sslyze` (core) | "TLS certificate expired" |
| SSH | SSH banner + KEX/host-key/cipher audit | `timeouts.ssh_seconds` | `ssh-audit` | "SSH quantum planning advisory" |
| JWT/API | JWT signing-alg discovery | `connectors.enable_jwt`, `jwt_targets` | (none) | (algorithm-classification findings) |
| Container | Crypto libraries in Docker images via Syft SBOM | `connectors.enable_container`, `container_targets` | `syft` binary | "Container image uses quantum-vulnerable crypto library" |
| Source code | semgrep on git repos | `connectors.enable_source`, `source_targets` | `semgrep` | (semgrep-rule findings) |
| DNSSEC | DNSKEY / DS / RRSIG | `connectors.enable_dnssec`, `dnssec_targets`, `timeouts.dnssec_seconds` | `quirk-scanner[identity]` | (algorithm + chain findings) |
| Kerberos | KDC enctype enumeration (port 88) | `connectors.enable_kerberos`, `kerberos_targets`, `timeouts.kerberos_seconds` | `quirk-scanner[identity]` | (etype findings) |
| SAML | SAML IdP signing/digest algorithms | `connectors.enable_saml`, `saml_targets`, `timeouts.saml_seconds` | `quirk-scanner[identity]` | (signature-alg findings) |
| Email | 7-port email TLS probe (SMTP/IMAP/POP3 ± STARTTLS) | `timeouts.email_seconds` | `quirk-scanner[motion]` | "STARTTLS downgrade risk on SMTP" |
| Broker | Kafka / AMQP / Redis / Azure Service Bus / SQS | `connectors.enable_broker`, `broker_azure_namespaces`, `broker_sqs_regions`, `timeouts.broker_seconds` | `quirk-scanner[motion]` | "Plaintext Kafka listener detected" |
| AWS | ACM certs, KMS keys, CloudFront, ELB | `connectors.enable_aws`, `aws_region`, `aws_profile` | `boto3` (core) | (KMS / cert findings) — see [`docs/connectors/aws.md`](connectors/aws.md) |
| Azure | Key Vault keys + certs, App Gateway TLS | `connectors.enable_azure`, `azure_subscription_id`, `azure_keyvault_urls` | (varies) | — see [`docs/connectors/azure.md`](connectors/azure.md) |
| GCP | KMS + GCS storage encryption | `connectors.enable_gcp`, `gcp_project_id` | `quirk-scanner[cloud]` | (no dedicated doc yet) |
| Database | Postgres / MySQL ssl-mode + RDS encryption | `connectors.enable_db`, `pg_targets`, `mysql_targets`, scanner user/password | `quirk-scanner[db]` | (no dedicated doc yet) |
| Object storage | S3 bucket encryption + Azure Blob encryption | `connectors.enable_s3`, `enable_blob` | `quirk-scanner[cloud]` | (no dedicated doc yet) |
| Kubernetes | EKS/GKE/AKS encryption + secret enumeration | `connectors.enable_k8s`, `k8s_provider`, `k8s_cluster_name`, kubeconfig fields | `quirk-scanner[cloud]` | (no dedicated doc yet) |
| Vault | Transit keys + PKI + auth methods | `connectors.enable_vault`, `vault_addr`, `vault_token`, `vault_transit_mount` | `quirk-scanner[cloud]` (`hvac`) | (no dedicated doc yet) |
| Docker (image SBOM) | (uses container scanner) | (see Container row) | `syft` | [`docs/connectors/docker.md`](connectors/docker.md) |
| Git (semgrep) | (uses source scanner) | (see Source row) | `semgrep` | [`docs/connectors/git.md`](connectors/git.md) |

### 6.2 Protocol scanner details

#### TLS scanner

Probes every `(host, port)` pair in `scan.ports_tls`, performs a full TLS handshake
via `sslyze`, and walks the certificate chain. Findings include expired certificates,
weak signature algorithms (SHA-1, MD5), short RSA keys (<2048), deprecated TLS
versions (1.0, 1.1), and weak cipher suites. Activated by the core install — no extra
required.

#### SSH scanner

Pulls the SSH banner from each target, then runs `ssh-audit` to enumerate KEX
algorithms, host-key types, and cipher/MAC suites. Emits a "SSH quantum planning
advisory" when only classical KEX is offered, and surfaces specific weaknesses (e.g.
`diffie-hellman-group1-sha1`, `ssh-rsa` host keys with short moduli). Requires the
`ssh-audit` binary on `PATH`.

#### JWT/API scanner

Iterates over `jwt_targets` and inspects either local JWT samples or live token
endpoints to discover the signing algorithm declared in the JWT header. Classifies
each algorithm against the `algorithm-classification` ruleset and emits findings for
algorithms that fail post-quantum guidance per FIPS 203 / 204 / 205 and NIST IR 8547.
Gated by `connectors.enable_jwt`.

**Security note — `allow_insecure_jwks`:** By default the JWT scanner verifies TLS
certificates when fetching JWKS endpoints (`allow_insecure_jwks: false`). Set
`allow_insecure_jwks: true` only when scanning internal or dev endpoints that use
self-signed or expired certificates. When this flag is enabled:

- TLS certificate verification is disabled for JWKS fetches only (other scan phases
  are unaffected).
- A `HIGH` severity advisory finding (`ADVISORY_JWKS_VERIFY_DISABLED`) is automatically
  emitted for every JWKS URL fetched, so the override is always visible in reports.
- QUIRK remains a passive inventory tool — it does not rely on JWKS key material for
  any authentication decision, so a MITM on the JWKS URI cannot escalate privileges.
  The threat model accepts this for controlled assessment environments.

See `docs/configuration.md` §Connectors for the full `allow_insecure_jwks` config key
reference.

#### Container scanner

For each entry in `container_targets`, generates a Syft SBOM of the named Docker
image and scans the resulting package list for crypto libraries flagged in the
quantum-readiness ruleset (e.g. legacy OpenSSL, vendored mbedTLS). Emits "Container
image uses quantum-vulnerable crypto library" findings with the image digest and
package version. Requires `syft` on `PATH` and `connectors.enable_container=true`.

#### Source-code scanner

Walks each git repository in `source_targets` (local clone or remote URL) and runs
semgrep with the QU.I.R.K. ruleset to detect hardcoded weak primitives, cipher
construction patterns, and PRNG misuse. Findings carry the file path and line range.
Requires `semgrep` on `PATH` and `connectors.enable_source=true`.

#### DNSSEC scanner

Resolves DNSKEY, DS, and RRSIG records for each domain in `dnssec_targets` and
classifies the signing algorithms (RSASHA1, RSASHA256, ECDSAP256SHA256, ED25519, etc.)
against the quantum-readiness rubric. Reports broken chains, missing DS records, and
signing algorithms misaligned with NIST IR 8547 guidance. Requires `quirk-scanner[identity]`.

#### Kerberos scanner

Connects to KDC port 88 on each entry in `kerberos_targets` and enumerates supported
encryption types (`aes256-cts-hmac-sha1-96`, `aes128-cts-hmac-sha1-96`,
`des-cbc-md5`, etc.). Findings flag any KDC still offering DES/RC4 enctypes and note
where AES-only enforcement is missing. Requires `quirk-scanner[identity]`.

#### SAML scanner

Fetches the SAML IdP metadata for each entry in `saml_targets` and inspects the
declared SignatureMethod and DigestMethod algorithms (`rsa-sha1`, `rsa-sha256`,
`ecdsa-sha256`, etc.). Findings flag IdPs still signing with SHA-1 or otherwise
non-conformant primitives. Requires `quirk-scanner[identity]`.

#### Email scanner

Probes 7 email-TLS ports per target — SMTP `25`/`465`/`587`, IMAP `143`/`993`, POP3
`110`/`995` — handling both implicit TLS and STARTTLS upgrades. Findings include
"STARTTLS downgrade risk on SMTP", missing implicit-TLS on submission, and weak
ciphers on the negotiated channel. Requires `quirk-scanner[motion]`.

#### Broker scanner

Probes message-broker endpoints across five protocol families: Kafka (configurable
listeners), AMQP (RabbitMQ), Redis, Azure Service Bus (per `broker_azure_namespaces`),
and Amazon SQS (per `broker_sqs_regions`). Findings include plaintext-listener
detection, weak TLS configuration, and missing authentication. Gated by
`connectors.enable_broker=true` and requires `quirk-scanner[motion]`.

### quirk doctor

Pre-engagement health check. Runs eight diagnostic probes and prints a
Rich-formatted dashboard. Exit code is the machine-readable signal:

- `0` — all non-informational checks pass; QUIRK is ready to scan
- `1` — one or more non-informational checks failed; address before scanning

#### Usage

```bash
quirk doctor
```

No flags are accepted. Invoke before each client engagement.

#### Categories

| # | Category | Severity | Failure exits 1? |
|---|----------|----------|------------------|
| 1 | Python environment (>= 3.11) | non-informational | yes |
| 2 | Scanner binaries (`nmap`, `syft`, `semgrep` in PATH) | non-informational | yes |
| 3 | Compliance framework freshness (within `STALENESS_THRESHOLD_DAYS`) | non-informational | yes |
| 4 | QRAMM module availability | informational | **no** |
| 5 | Database (`./quirk.db` reachable) | non-informational | yes |
| 6 | Configuration (`./config.yaml` parses) | non-informational | yes (malformed); informational only if file is absent |
| 7 | Network connectivity (DNS probe) | informational | **no** |
| 8 | Dashboard process (port 8512) | informational | **no** |

#### Symbols

- `[✓]` — check passed
- `[!]` — informational status (never causes exit 1)
- `[✗]` — check failed (causes exit 1 if non-informational)

#### Examples

```text
$ quirk doctor
                        QU.I.R.K. Health Check
┏━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Check                   ┃ Status                                        ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Python environment      │ [✓] Python 3.14                               │
│ Binary: nmap            │ [✓] /opt/homebrew/bin/nmap                    │
│ Binary: syft            │ [✓] /opt/homebrew/bin/syft                    │
│ Binary: semgrep         │ [✗] semgrep not found in PATH                 │
│ Compliance freshness    │ [✓] all frameworks within freshness window    │
│ QRAMM module            │ [!] QRAMM module not installed — Phase 51     │
│ Database (quirk.db)     │ [✓] ./quirk.db reachable                      │
│ Configuration           │ [✓] ./config.yaml parses cleanly              │
│ Network connectivity    │ [✓] outbound TCP to 8.8.8.8:53 OK             │
│ Dashboard process       │ [!] dashboard not running on port 8512        │
└─────────────────────────┴───────────────────────────────────────────────┘
$ echo $?
1
```

(In the example above, `semgrep` is missing — a non-informational failure that
exits 1.)

---

## 7. Compliance Map Maintenance

QU.I.R.K. ships a `COMPLIANCE_MAP` in `quirk/compliance/__init__.py` that joins
finding titles to PCI-DSS, HIPAA (45 CFR §164.312), and FIPS 140-3 controls.
Regulators publish revisions on their own cadences; this runbook documents how
QU.I.R.K. maintainers keep the map current and how operators can verify freshness on
demand.

### 7.1 Quarterly review checklist

1. Run `quirk compliance status` and confirm every framework's `Last Verified` date is
   within the last 90 days.
2. Visit each publisher URL (table below) and check for newly published revisions.
3. If a revision exists, follow §7.4 "Upgrade path".
4. If no revision exists but `last_verified` is older than 90 days, update
   `last_verified` to today after re-reading the current source — this re-confirms our
   reading and resets the staleness clock.
5. Run `pytest tests/test_compliance_schema.py tests/test_compliance_freshness.py
   tests/test_compliance_title_join.py` — all green.
6. Commit and push.

### 7.2 Source URLs to monitor

| Framework | Publisher | Monitor URL |
|-----------|-----------|-------------|
| PCI-DSS | PCI Security Standards Council | https://www.pcisecuritystandards.org/document_library/ |
| HIPAA 45 CFR §164.312 (publisher landing) | HHS / ECFR | https://www.hhs.gov/hipaa/for-professionals/index.html |
| HIPAA 45 CFR §164.312 (canonical regulation text) | HHS / ECFR | https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-C/part-164 |
| FIPS 140-3 | NIST CSRC | https://csrc.nist.gov/publications/fips |
| SOC 2 (Trust Services Criteria) | AICPA | https://www.aicpa-cima.com/resources/landing/aicpa-trust-services-criteria |
| ISO 27001:2022 | ISO / national body | https://www.iso.org/standard/27001 |

### 7.3 How to detect drift

QU.I.R.K. ships several CI gates that fail the build before stale data ships to a
customer:

- **`tests/test_compliance_freshness.py`** — fails when any entry's `last_verified` is
  older than `STALENESS_THRESHOLD_DAYS` (currently 365 days; defined in
  `quirk/compliance/__init__.py`). This is the 12-month staleness gate (COMPLY-08).
- **`tests/test_compliance_schema.py`** — fails when any entry is missing `framework`,
  `control`, `version`, `last_verified`, or `source_url`.
- **`tests/test_compliance_title_join.py`** — fails when an emitted finding title is
  not in `COMPLIANCE_MAP` or `UNMAPPED_TITLES`.
- **`tests/test_compliance_cli.py`** — smoke for `quirk compliance status` (text +
  JSON).
- **`tests/test_compliance_report_section.py`** — verifies the HTML/PDF "Compliance
  Summary" section.

Operators can run `quirk compliance status` ad hoc before customer engagements to
print per-framework version, `last_verified` date, and `source_url`:

```bash
# Default text format
quirk compliance status

# JSON format (machine-readable; useful in CI)
quirk compliance status --format json
```

### 7.4 Upgrade path: PCI-DSS 4.0.1 → 4.1 (worked example)

1. PCI SSC publishes PCI-DSS v4.1 at
   https://www.pcisecuritystandards.org/document_library/.
2. Maintainer reviews the diff: control numbers may shift; requirement text may add
   new clauses.
3. Edit `quirk/compliance/__init__.py`:
   - Update the `_PCI_4_0_1_URL` constant — rename and re-point to the v4.1 PDF, or
     add a `_PCI_4_1_URL` alongside.
   - Update the `_pci()` helper — change `"version": "4.0.1"` → `"version": "4.1"`.
   - Update `_PHASE_49_VERIFIED` to today's ISO date.
   - For any control numbers that moved (e.g. `4.2.1` → `4.2.2`): edit each affected
     `COMPLIANCE_MAP` entry's `_pci("X")` argument.
4. Run `pytest tests/test_compliance_schema.py tests/test_compliance_freshness.py
   tests/test_compliance_title_join.py` — confirm green.
5. Run `quirk compliance status` — confirm the new version and today's
   `last_verified` print.
6. Commit (e.g. `chore(compliance): upgrade PCI-DSS to 4.1`) and push; CI re-runs the
   full gate.

The same shape applies to HIPAA 45 CFR §164.312 revisions (edit `_HIPAA_164_312_URL`
+ `_hipaa()` helper) and FIPS 140-3 revisions (edit `_FIPS_140_3_URL` + the relevant
entries).

---

## 8. Distributed Sensor Deployment

*(Audience: operators deploying QU.I.R.K. across segmented enterprise networks where a single
scanner host cannot reach all segments. Two or more sensor nodes push their per-segment
findings to a shared console; the console merges them into one unified CBOM and one
quantum-readiness score.)*

**Architecture overview:**

```
[segment-a host]                 [console host]
  quirk sensor push ──────────→  quirk serve --host 0.0.0.0
                     HTTPS
[segment-b host]
  quirk sensor push ──────────→  (same console)
                                   │
                              quirk sensor merge
                                   │
                           one CBOM + one score
```

Each sensor is a standard `pip install quirk-scanner[all]` deployment. Sensors
communicate with the console over HTTPS using a shared HMAC key and a shared console
API token set at enrollment time.

### 8.1 Provision the console

Install QU.I.R.K. on the console host and start the server. The console must bind a
routable address so sensors can reach it over the network:

```bash
# Console host (Linux / macOS)
pip install "quirk-scanner[all]"

# Set the shared API token BEFORE starting the server.
# Sensors must send this same token in every push request.
export QUIRK_API_TOKEN="<your-strong-random-token>"

# Start the server — bind to a specific interface or 0.0.0.0 for all interfaces.
# The console binds loopback by default; override for multi-host use.
quirk serve --host 0.0.0.0 --port 8512
```

> **Security note:** Do not expose the console port to untrusted networks without an
> HTTPS reverse proxy and IP allowlist in front of it. Set `QUIRK_API_TOKEN` to a
> strong random value before starting the server; `quirk serve` without this variable
> runs with authentication disabled (appropriate only for local dev/testing).

### 8.1.1 v5.4 shared-token authentication model

In v5.4, push authentication uses a **shared API token** on the console.

| Component | Role |
|-----------|------|
| `QUIRK_API_TOKEN` env var (or `security.api_token` in `config.yaml`) | The console's shared token; authenticates every `POST /api/sensor/push` request |
| `console_api_token` in `sensor.yaml` | Must equal the console's `QUIRK_API_TOKEN`; set via `quirk sensor enroll --api-token <value>` |
| Enrollment token from `quirk console enroll` | One-time provisioning record stored (as SHA-256 hash) in `sensor_tokens` for audit; **NOT the push credential** |

The enrollment token printed by `quirk console enroll` identifies the sensor row and is
shown once for your records. It does **not** authenticate push requests — that is the
console's shared `QUIRK_API_TOKEN`.

Per-sensor token auth (where each sensor has its own revocable credential validated
against `sensor_tokens`) is planned for v5.5.

### 8.2 Enroll each sensor

On the **console host**, provision a sensor row for each sensor. Each invocation creates
a new `sensors` row in the console database and prints a **one-time enrollment token** to
stdout. This token is a provisioning/audit record — it is stored as its SHA-256 hash in
`sensor_tokens`. It is **not** the push credential (see §8.1.1).

```bash
# Console host — run once per sensor
quirk console enroll --segment <label>
# e.g.:
quirk console enroll --segment segment-a
# → prints a one-time enrollment token (provisioning audit record — not the push credential)
quirk console enroll --segment segment-b
```

On each **sensor host**, run `quirk sensor enroll` with the **console's shared API token**
(the value of `QUIRK_API_TOKEN` on the console), not the enrollment token above:

```bash
# Sensor host — Linux / macOS
# --api-token is the CONSOLE'S SHARED API TOKEN (QUIRK_API_TOKEN on the console),
# NOT the enrollment token printed above.
quirk sensor enroll https://<console-host>:8512 \
  --segment <label> \
  --api-token <console-QUIRK_API_TOKEN>
# e.g.:
quirk sensor enroll https://console.corp:8512 \
  --segment segment-a \
  --api-token my-strong-shared-token
```

Enrollment writes `sensor.yaml` to the default platform config directory:
- **Linux / macOS:** `~/.config/quirk/sensor.yaml` (XDG `user_config_dir`)
- **Windows:** `%APPDATA%\quirk\sensor.yaml`

The file stores the `sensor_id` (UUID), `segment` label, HMAC key, console URL, and the
`console_api_token` used to authenticate push requests. The one-time enrollment token
from `quirk console enroll` is **never** written to `sensor.yaml`.

Use `--config <path>` to place `sensor.yaml` at a custom location (useful in CI or when
running multiple sensors on the same host).

### 8.3 Push findings

On each sensor host, run a local scan and push the results to the console in a single
command:

```bash
# Sensor host
quirk sensor push
# With a custom scan config (recommended for enterprise targets):
quirk sensor push --scan-config /etc/quirk/sensor-scan.yaml
```

`quirk sensor push` runs a local scan using the target list in the scan config,
serialises the findings into a signed, compressed `.qpush` envelope, and delivers it to
the console over HTTPS. The console responds HTTP 200 on success.

If the console is temporarily unreachable, the payload is spooled to
`user_data_dir("quirk")/spool/` and retried automatically on the next invocation.

### 8.4 Merge into a unified CBOM

On the **console host**, run the merge after all sensors have pushed:

```bash
# Console host
quirk sensor merge

# Optional flags:
quirk sensor merge --stale-days 7       # ignore sensors silent > 7 days
quirk sensor merge --output-dir ./out   # write CBOM / reports here
```

`quirk sensor merge` re-runs `compute_readiness_score()` and `build_cbom()` over the
union of all pushed `CryptoEndpoint` rows, producing:

- One merged CBOM (`cbom-<ts>.json` + `cbom-<ts>.xml`)
- One unified quantum-readiness score
- A `coverage_warning` if any enrolled sensor has not pushed within `stale_days`

**MERGE-03 behaviour:** If two or more sensors scanned the same logical hostname and port
(e.g. `crypto.internal:443` appearing in both a DMZ and a PCI segment), the CBOM will
contain **one component per sensor** — distinct by `sensor_id` — not a de-duplicated
single entry. The `(sensor_id, host, port)` uniqueness key is the correct model for
segmented networks where the same address exists in multiple security zones.

### 8.5 Windows sensor installation

QU.I.R.K. sensors run on Windows with no additional configuration beyond the standard
Python install.

**Prerequisites:** Python 3.11+ for Windows, available from https://www.python.org/downloads/

**Install:**

```powershell
# PowerShell (run as the service account that will run the sensor)
pip install "quirk-scanner[all]"
```

**Enroll and push (PowerShell):**

```powershell
# Enroll (one-time — --api-token is the CONSOLE'S QUIRK_API_TOKEN, not the enrollment token)
quirk sensor enroll https://<console-host>:8512 `
  --segment segment-windows `
  --api-token <console-QUIRK_API_TOKEN>

# sensor.yaml written to: $env:APPDATA\quirk\sensor.yaml

# Push findings
quirk sensor push --scan-config C:\quirk\sensor-scan.yaml
```

**`sensor.yaml` path on Windows:** `%APPDATA%\quirk\sensor.yaml`
(resolved via `platformdirs.user_config_dir("quirk")` at runtime).

**SIGTERM note:** The QU.I.R.K. scheduler uses `signal.SIGTERM` for graceful shutdown on
Linux/macOS but guards it with `sys.platform != 'win32'` (`scheduler_cmd.py:283-284`).
On Windows, use Ctrl+C or the Windows Service stop API instead of SIGTERM.

**nmap dependency:** The TLS scanner requires `nmap` on `PATH`. Download the Windows
installer from https://nmap.org/download.html and confirm `nmap.exe` is accessible:

```powershell
nmap --version
```

### 8.6 Air-gap path (offline sensor → console)

For sensors with no network path to the console, use file-based export/import:

```bash
# Sensor host (no console connectivity)
quirk sensor export-results
# → writes <sensor_id>-<payload_id>.qpush to the current directory (or --output-dir)
```

Transfer the `.qpush` file to the console host via USB, secure file share, or any
out-of-band channel, then import:

```bash
# Console host
quirk console import-results /path/to/<sensor_id>-<payload_id>.qpush
```

The console validates the HMAC signature, decompresses the envelope, deduplicates by
`payload_id` (idempotent re-import is safe), and ingests the findings. Run
`quirk sensor merge` afterwards to produce the unified CBOM.

---

### 8.7 All-configurations / settings reference (999.59)

The table below covers every knob relevant to distributed sensor deployments, closing
the settings-coverage gap (999.59). For the full single-host config reference see
[`docs/configuration.md`](configuration.md).

#### `scan.timeouts.*` — per-scanner timeout knobs

Set in `config.yaml` under the `scan.timeouts` block. All values are in seconds.

| Key | Default (s) | Scanner |
|-----|-------------|---------|
| `scan.timeouts.tls_seconds` | 6 | TLS / sslyze |
| `scan.timeouts.ssh_seconds` | 6 | SSH |
| `scan.timeouts.jwt_seconds` | 10 | JWT / API |
| `scan.timeouts.container_seconds` | 120 | Container (Syft) |
| `scan.timeouts.source_seconds` | 300 | Source code (Semgrep) |
| `scan.timeouts.dnssec_seconds` | 10 | DNSSEC |
| `scan.timeouts.saml_seconds` | 10 | SAML |
| `scan.timeouts.kerberos_seconds` | 10 | Kerberos |
| `scan.timeouts.vault_seconds` | 10 | HashiCorp Vault |
| `scan.timeouts.db_connect_seconds` | 5 | Postgres / MySQL |
| `scan.timeouts.broker_seconds` | 10 | Kafka / RabbitMQ / Redis |
| `scan.timeouts.email_seconds` | 10 | Email (SMTP / IMAP / POP3) |
| `scan.timeouts.fingerprint_seconds` | 4 | Fingerprint probe |
| `scan.timeouts.default_seconds` | 5 | Fallback for unlisted scanners |

See [`docs/timeout-retry-audit.md`](timeout-retry-audit.md) for retry policies and jitter.

#### `output.directory` — report output path

```yaml
output:
  directory: "./quirk-output"   # default; relative to CWD or absolute
```

All scan outputs (HTML/PDF/DOCX reports, CBOM JSON/XML, findings JSON,
`executive.md`, `technical.md`, `intelligence-*.json`) land here. On sensor nodes,
`quirk sensor push` uses a temporary directory for the local scan and discards it after
push; set `--scan-config` and a stable `output.directory` if you want per-push
artefacts retained on the sensor host.

#### Sensor identity fields in scan output

| Field | Location | Description |
|-------|----------|-------------|
| `sensor_id` | `CryptoEndpoint` DB column; CBOM component metadata | UUID assigned at `quirk sensor enroll`; `nullable=True` (NULL = implicit local sensor, backward-compatible with pre-v5.4 scans) |
| `segment` | `CryptoEndpoint` DB column; findings JSON | Network-segment label passed via `--segment` at enroll time; appears in `findings-<ts>.json` per-finding and in the merged CBOM |

These two fields are the differentiators for MERGE-03 — two findings with identical
`host:port` but different `sensor_id` values are intentional and correct; they represent
the same logical endpoint discovered independently in two network segments.

---
