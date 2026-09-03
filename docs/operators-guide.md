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

### 2.3 Vertical editions (v5.6+)

The dashboard can run as an industry-specific edition (currently `general` or
`healthcare`). Set `QUIRK_VERTICAL=healthcare` in the server environment, or add a
top-level `vertical: healthcare` key to the YAML file `QUIRK_CONFIG_PATH` points at.
The env var wins; unknown values fall back silently to `general`. Verify the active
edition after startup with `curl http://127.0.0.1:8512/api/config` (unauthenticated,
returns `{"vertical": "..."}`).

The healthcare edition adds a "Healthcare Posture" page, sidebar badge, and an
EHR/PACS/portal scan preset; general installs are unchanged. See
[`docs/configuration.md`](configuration.md) § Vertical Editions for the full reference.

> See also: [`docs/configuration.md`](configuration.md) for the full reference of every
> config block and flag, [`docs/sample-config.yaml`](sample-config.yaml) for an
> annotated example.

### 2.4 Dashboard security tail (v5.10+ — Phase 143)

Three small operator-facing additions shipped in Phase 143:

- **Scan-date badge** — every dashboard view now shows a persistent "Last scan: {date} {time}"
  (or "No scan yet") badge in the sidebar, so you always know at a glance how current the data
  you're looking at is. See [`docs/report-interpretation.md`](report-interpretation.md) §11.
- **`security.trusted_targets` scan-consent allowlist** — an opt-in list of exact hosts/IPs and
  CIDR ranges QUIRK is authorized to scan, enforced identically at both the CLI and the
  dashboard's "New Scan" entry point. Empty/absent = allow-all (backward compatible). See
  [`docs/configuration.md`](configuration.md) § `security.trusted_targets`.
- **Windows Authenticode signing (build mechanism, not yet activated)** — the
  `windows-package` release CI job now contains the wiring to Authenticode-sign the Windows
  sensor `.exe` via `signtool.exe`, gated cleanly on the presence of
  `QUIRK_SIGNING_CERT_BASE64`/`QUIRK_SIGNING_CERT_PASSWORD` repo secrets. **No real signing
  certificate exists yet** — until one is provisioned and those secrets are added, released
  Windows binaries remain unsigned (the release notes' "UNSIGNED BINARY NOTICE" is accurate and
  unchanged). The mechanism activates automatically, with no code changes, the moment a real
  certificate secret is configured.

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

### 3.2 Active REST fuzzing (`--fuzz`) — interactive-only by design

`--fuzz` enables active REST crypto-posture probing against discovered OpenAPI
endpoints (see [`docs/configuration.md`](configuration.md#rest-fuzzing-active-crypto-posture-probes)
for the full flag reference and guardrail table). Two things every operator scheduling
QU.I.R.K. runs needs to know before wiring `--fuzz` into automation:

- **`--fuzz` requires an interactive terminal.** If stdin is not a TTY — piped input, a
  CI/CD job, a cron job, any headless invocation — the scanner refuses to run fuzzing at
  all. It prints coded error `FUZZ-001` and **exits non-zero (exit 2)**, and it does this
  before any scan work begins. This is deliberate, not a bug: an unattended job must
  never be able to authorize active probing of a client's live API on its own. If you see
  a cron or CI run fail with `FUZZ-001`, that is the gate working as intended — drop
  `--fuzz` from unattended/scheduled invocations, or run it manually from an interactive
  session instead.
- **`--fuzz` is never silently skipped.** Earlier behaviour could let a non-interactive
  `--fuzz` invocation complete normally with fuzzing quietly disabled and no indication
  in the output. That is no longer possible — either fuzzing runs (interactive session,
  confirmed) or the scan refuses to start (non-interactive, `FUZZ-001`, exit 2). There is
  no third, quiet outcome.
- **`--fuzz-budget` is bounded, and out-of-range values are rejected, not clamped.** The
  default is 50 requests; values above the hard ceiling documented in
  [`docs/configuration.md`](configuration.md#rest-fuzzing-active-crypto-posture-probes)
  are rejected up front with coded error `FUZZ-002` and exit 2 — the scan does not
  silently reduce an over-budget request down to the ceiling and proceed.

See [`docs/error-codes.md`](error-codes.md) for the full `FUZZ` error-domain cause/fix
text for `FUZZ-001` and `FUZZ-002`.

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
  these instead of silently skipping the scanner. As of v5.17 (Phase 173), this signal — a
  `[QRK-INSTALL-001]` stderr advisory plus a `scan_error_category=missing_extra` finding — is
  emitted consistently across scanner families: the broker connector now checks all three of its
  optional dependencies (`sslyze`, `kafka-python`, `redis`), not just `sslyze`, and the smime/adcs
  connectors emit the signal for the first time (both previously failed silently with only a bare
  log line). If you enable a connector and see this advisory, install the named extra
  (`pip install quirk-scanner[motion]` for broker/email, `quirk-scanner[adcs]` for smime/adcs)
  or leave the connector disabled.
- **A skipped scan phase leaves no `run_stats.timings_sec` key** — as of v5.17 (Phase 173), a
  phase that did not actually run (disabled connector, no targets, missing extra) omits its key
  from `run_stats.timings_sec` entirely, rather than recording a phantom near-zero duration. A
  phase that ran and legitimately found nothing still writes its key (with a real, possibly small,
  elapsed time) — the absence of a key means "did not run," not "ran fast." No consumer depends on
  a fixed key set; this is safe to rely on when auditing which phases actually executed.
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
- **CORS rejection in the browser (v5.11+)** — should no longer happen out of the box:
  `quirk serve` sets `QUIRK_DASHBOARD_PORT` to the actual bound port, and the default
  CORS allowlist (`quirk/config.py::get_cors_origins`) matches it automatically
  (Phase 147, DRAIN-03 / WR-02). If you still see a CORS error, you're likely accessing
  the dashboard through a different hostname/port than it bound to (e.g. a reverse
  proxy) — set `QUIRK_CORS_ORIGINS` explicitly. See
  [Configuration → CORS Allowlist](configuration.md#cors-allowlist-v511--phase-147-drain-03--wr-02).
- **Data not loading** — confirm a recent scan has populated `quirk.db`; the dashboard
  reads SQLite directly.
- **`quirk serve` starts but every API call renders an empty state — check for multiple
  candidate DBs.** `_default_db_path()` (`quirk/dashboard/api/deps.py`) checks, in order,
  `QUIRK_DB_PATH`, then whether more than one of `./quirk.db`, `./output/quirk.db`,
  `./quirk-output/quirk.db` exists. If **more than one** of those three paths is present, it
  raises `ValueError: Multiple QU.I.R.K. DBs found` — and because this check runs inside a
  FastAPI `Depends()`, it fires on *every request*, not at startup. The server itself starts
  cleanly with no error printed to the console; the dashboard just silently renders empty
  states over the failed API calls, which reads exactly like "no scan data yet." Fix: set
  `QUIRK_DB_PATH=<path-to-the-db-you-want>` before running `quirk serve` to disambiguate
  explicitly. Also worth checking: a stray 0-byte `quirk.db` left over from an earlier run in
  the working directory counts toward this conflict even though it holds no data — delete it
  if it isn't the DB you intend to serve.
- **Appearance note (Phase 165, A11Y-03)** — primary and accent buttons, and the
  severity/quantum-safety badges described in
  [Report Interpretation](report-interpretation.md#4-severity-tiers), now render dark text
  instead of white. Muted label text is also very slightly lighter. All underlying colours
  (teal buttons, orange/red/green badges) are numerically unchanged — only the foreground text
  moved, to clear WCAG 2.1 AA contrast (teal buttons: 2.81:1 → 6.27:1). This is a contrast
  fix, not a redesign.
- **Accessibility gate (Phase 165, A11Y-01/A11Y-04)** — `npm run a11y:check` (and its
  `:empty`/`:loading` variants) in `src/dashboard/` now enforce a per-route, per-rule *count
  budget* rather than a selector snapshot: each baselined `(route, rule)` pair records a
  maximum node count, impact level, WCAG success criterion, and a written justification.
  The gate fails if a count goes **up**
  (new debt) — and, deliberately, also if a count goes **down** without the baseline being
  regenerated (`npm run a11y:baseline`), so a real fix always tightens the ledger instead of
  leaving a now-stale, looser number in place.

### 5.3.1 UAT corpus integrity gate

`tests/test_uat_zero_undispositioned_gate.py` fails the build the moment any case in
`docs/UAT-SERIES.md` (the 666-case UAT gating document) has an all-unchecked `**Result:**`
line — it rides the existing `Linux Full Suite` CI job rather than a pre-commit hook, so it
cannot be bypassed with `--no-verify`. If you add a new UAT case, give it a real disposition
(PASS/FAIL, or a checked SKIP with a `DEFERRED — covered by <test-node>` or `GAP — no substitute
coverage` annotation) before committing. Full rationale and worked fix instructions are in
`CLAUDE.md`'s "UAT Corpus Integrity Gate (UATREC-04)" section and in the gate test's own module
docstring.

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

**Optional prerequisite — `ssh-audit`:** the SSH scanner's per-algorithm classification
(KEX, host-key, MAC breakdown) depends on the external `ssh-audit` binary
(`quirk/scanner/ssh_scanner.py`, `shutil.which("ssh-audit")`). It is not a `quirk-scanner`
dependency and is not installed by any `pip install quirk-scanner[...]` extra — install it
separately:

```bash
pip install ssh-audit
```

If `ssh-audit` is not on `PATH`, the scanner does not fail — it silently falls back to a raw
SSH banner grab and emits only a single generic "SSH quantum planning advisory" INFO finding,
with no per-algorithm KEX/host-key/MAC breakdown or per-algorithm NIST quantum level. Install
`ssh-audit` before scanning if you need that detail.

> **If you installed `ssh-audit` before 2026-08-31 and saw no additional detail, that was a
> bug, not your setup.** The scanner invoked `ssh-audit` with a malformed command line, so the
> silent-fallback path above ran on every scan regardless of whether the binary was present.
> Scans from affected versions recorded no SSH algorithm data, and their CBOMs contain no SSH
> algorithm components. Re-scan any SSH hosts you need per-algorithm inventory for.

Note that `ssh-audit` must be on the `PATH` of the process running the scan. If QU.I.R.K. is
installed in a virtualenv and you invoke it via an absolute interpreter path
(`/path/to/.venv/bin/python -m ...`) without activating the environment, the venv's `bin/`
directory is *not* added to `PATH` and `shutil.which("ssh-audit")` will not find it. Activate
the environment, or ensure the directory containing `ssh-audit` is on `PATH`.

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
>
> As a guardrail, `quirk serve` now **refuses to start** on a network-reachable
> interface when no `QUIRK_API_TOKEN` is configured, unless you pass `--insecure` to
> explicitly acknowledge a token-less bind on a trusted, firewalled segment. When the
> console runs behind a reverse proxy, set `QUIRK_TRUST_PROXY` (default `127.0.0.1`)
> so per-IP rate limiting and the audit log see the real sensor address rather than
> the proxy's. For a **cloud-hosted console** (e.g. on Linode) with internal sensors
> pushing in, follow the hardened, end-to-end walkthrough in
> [`deployment-cloud-console.md`](deployment-cloud-console.md) and the ready-to-use
> files under [`deploy/`](../deploy/).

### 8.1.1 v5.5 per-sensor authentication model (migration from v5.4)

In v5.5, every sensor authenticates `POST /api/sensor/push` with its **own per-sensor
token** issued by `quirk console enroll`. This replaces the v5.4 shared-token model
(where all sensors used the same `QUIRK_API_TOKEN`). The cutover is clean — there is no
dual-accept period (D-10).

| Component | Role |
|-----------|------|
| `QUIRK_API_TOKEN` env var (or `security.api_token` in `config.yaml`) | Console's shared token; governs operator/dashboard auth — **unaffected** |
| Enrollment token from `quirk console enroll` | **The per-sensor push credential.** Shown once; only its SHA-256 hash is stored in `sensor_tokens`. Place this raw value in `console_api_token` in `sensor.yaml` on the sensor host. |
| `console_api_token` in `sensor.yaml` | Must hold the sensor's per-sensor enrollment token (not the shared `QUIRK_API_TOKEN`) |

**What changed from v5.4:** Each sensor now uses its own revocable enrollment token to
authenticate push requests. The shared `QUIRK_API_TOKEN` no longer authenticates pushes.

**Migration steps (per sensor host):**

1. On the **console host**, print the enrollment token for the sensor:
   ```bash
   quirk console enroll --segment <label>
   # → Bearer token: <per-sensor-token>  (copy now — shown once)
   # → sensor_id: <uuid>
   ```
2. On each **sensor host**, open `sensor.yaml` and set:
   ```yaml
   console_api_token: <per-sensor-token>   # replace the old QUIRK_API_TOKEN value here
   ```
3. If the raw enrollment token was lost, revoke and re-enroll:
   ```bash
   # Console host — revoke the old token
   quirk console revoke-sensor <sensor_id>
   # Re-enroll to mint a fresh token + new sensor_id
   quirk console enroll --segment <label>
   ```

The shared `QUIRK_API_TOKEN` still controls operator CLI and dashboard access. It is
unaffected by per-sensor push tokens.

### 8.2 Enroll each sensor

On the **console host**, provision a sensor row for each sensor. Each invocation creates
a new `sensors` row in the console database and prints a **per-sensor push token** to
stdout. This token **IS** the push credential — place it in `console_api_token` in
`sensor.yaml` on the sensor host. It is shown once and never recoverable; only its
SHA-256 hash is stored in `sensor_tokens`.

```bash
# Console host — run once per sensor
quirk console enroll --segment <label>
# e.g.:
quirk console enroll --segment segment-a
# → Bearer token (copy now — shown once, never recoverable): <per-sensor-token>
# → sensor_id: <uuid>
quirk console enroll --segment segment-b
```

On each **sensor host**, run `quirk sensor enroll` and set `console_api_token` to the
enrollment token printed above:

```bash
# Sensor host — Linux / macOS
quirk sensor enroll https://<console-host>:8512 \
  --segment <label>
# Then edit sensor.yaml: set console_api_token to the per-sensor enrollment token.
# e.g.:
quirk sensor enroll https://console.corp:8512 \
  --segment segment-a
# Edit ~/.config/quirk/sensor.yaml:
#   console_api_token: <per-sensor-token-from-quirk-console-enroll>
```

Enrollment writes `sensor.yaml` to the default platform config directory:
- **Linux / macOS:** `~/.config/quirk/sensor.yaml` (XDG `user_config_dir`)
- **Windows:** `%APPDATA%\quirk\sensor.yaml`

The file stores the `sensor_id` (UUID), `segment` label, HMAC key, console URL, and the
`console_api_token` used to authenticate push requests.

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
# Enroll (one-time)
quirk sensor enroll https://<console-host>:8512 `
  --segment segment-windows
# Then edit %APPDATA%\quirk\sensor.yaml:
#   console_api_token: <per-sensor-token-from-quirk-console-enroll>

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

### 8.8 Windows sensor deployment (zip + Scheduled Task)

*(v5.6+ — frozen binary; no Python required on the sensor host)*

For Windows sensor hosts where a Python runtime is not available (or not desired),
download the pre-built `quirk-windows-<version>.zip` asset from the [GitHub Release](
https://github.com/0xD1g5/QU.I.R.K/releases) for your target version. The zip bundles
the frozen `quirk.exe` onedir executable together with `install.ps1`, `uninstall.ps1`,
and a `sensor.sample.yaml` reference config — no Python install required on the sensor
host.

#### Unsigned binary notice

The zip asset is **NOT Authenticode-signed**. Authenticode signing is deferred to a
future milestone. Operators may see a Windows SmartScreen prompt ("Windows protected your
PC") when running `install.ps1` or `quirk.exe` for the first time. To proceed: click
**More info**, then **Run anyway**. Operators who require signed binaries should build
from source until Authenticode signing is implemented.

#### Prerequisites

- **PowerShell 5.1+** (built in to Windows 10/11 and Windows Server 2016+).
- An enrollment token issued by `quirk console enroll` on the console host. See
  §8.1.1 for how to provision per-sensor push credentials via
  `quirk console enroll --segment <label>`.
- Network access from the Windows host to the QUIRK console on its listen port
  (default 8512).

#### Install

1. Download `quirk-windows-<version>.zip` from the GitHub Release and unpack it:

   ```powershell
   Expand-Archive -Path quirk-windows-<version>.zip -DestinationPath C:\quirk-install
   cd C:\quirk-install
   ```

2. Run `install.ps1`. The installer copies the bundle to
   `%LOCALAPPDATA%\Programs\QUIRK` (**no admin elevation required**), enrolls the
   sensor against the console, tightens the sensor config ACL to the current user,
   and registers a daily Scheduled Task named **"QUIRK Sensor Push"** that runs
   `quirk.exe sensor push` on the chosen cadence.

   Mandatory parameters:

   | Parameter | Description |
   |-----------|-------------|
   | `-ConsoleUrl` | Base URL of the QUIRK console (e.g. `https://quirk.example.com` or `https://10.0.0.5:8512`). |
   | `-EnrollmentToken` | Per-sensor opaque Bearer token from `quirk console enroll`. Passed directly to `quirk.exe sensor enroll --api-token`; never echoed to console or logs. |

   Optional parameters:

   | Parameter | Default | Description |
   |-----------|---------|-------------|
   | `-Segment` | `"windows"` | Network segment label written to the sensor config. |
   | `-Time` | `"03:00"` | Daily trigger time for the Scheduled Task (HH:MM format). |
   | `-AllowInternalConsole` | *(switch)* | Pass to allow the sensor to reach a console on a private/RFC1918 address (on-prem or lab). |

   Example — production console:

   ```powershell
   pwsh -File install.ps1 `
     -ConsoleUrl https://quirk.example.com `
     -EnrollmentToken <per-sensor-token>
   ```

   Example — on-prem lab console on a private IP, custom cadence and segment:

   ```powershell
   pwsh -File install.ps1 `
     -ConsoleUrl https://10.0.0.5:8512 `
     -EnrollmentToken <per-sensor-token> `
     -AllowInternalConsole `
     -Time 02:00 `
     -Segment corp-windows
   ```

   After `install.ps1` completes, the sensor is installed at
   `%LOCALAPPDATA%\Programs\QUIRK\quirk\quirk.exe` and the sensor config is written to
   `%LOCALAPPDATA%\Programs\QUIRK\config\sensor.yaml`. The config file is ACL-restricted
   to the current user immediately after enrollment.

#### Scheduled Task

`install.ps1` registers a Windows Scheduled Task named **"QUIRK Sensor Push"** that runs
`quirk.exe sensor push` daily at the configured time under the current user account
(**no admin elevation** — `RunLevel Limited`). To inspect or manage the task:

```powershell
# Confirm the task exists and its next run time
Get-ScheduledTask -TaskName "QUIRK Sensor Push" | Get-ScheduledTaskInfo

# Disable the task (without removing it)
Disable-ScheduledTask -TaskName "QUIRK Sensor Push"

# Run the push immediately (outside the schedule)
& "$env:LOCALAPPDATA\Programs\QUIRK\quirk\quirk.exe" sensor push `
    --config "$env:LOCALAPPDATA\Programs\QUIRK\config\sensor.yaml"
```

#### Uninstall

Run `uninstall.ps1` from any working directory (it does not need to be in the unpack
root — it always targets `%LOCALAPPDATA%\Programs\QUIRK`):

```powershell
# Full removal — unregisters the Scheduled Task and removes all installed files
pwsh -File uninstall.ps1

# Preserve the sensor config (re-install without re-enrolling)
pwsh -File uninstall.ps1 -KeepConfig
```

`-KeepConfig` removes the binary bundle but leaves `%LOCALAPPDATA%\Programs\QUIRK\config\`
intact so a future `install.ps1` run can reuse the existing sensor identity without
re-enrolling.

#### Security note — sensor config at rest

The sensor config file (`%LOCALAPPDATA%\Programs\QUIRK\config\sensor.yaml`) holds the
per-sensor push credential (`console_api_token`). `install.ps1` tightens its ACL to
grant **Read + Write to the current user only** immediately after enrollment. Do not
commit or share this file. If the token is compromised, revoke it on the console host
and re-enroll:

```bash
# Console host
quirk console revoke-sensor <sensor_id>
quirk console enroll --segment <label>
```

Then re-run `install.ps1` on the Windows host with the new enrollment token.

---

### 8.9 Automatic Merge

*(v5.5+)*

When every enrolled (non-revoked) sensor has pushed its latest results, the console can
merge them automatically — eliminating the need to run `quirk sensor merge` manually in
the common deployment case.

#### Default behaviour

Auto-merge is **ON by default**. After each successful `POST /api/sensor/push`, the
console re-evaluates the trigger condition. When it is satisfied, a merge runs in the
background via a FastAPI `BackgroundTask` after the push response is already sent —
so push latency is unaffected and a merge failure can never block or roll back a
sensor push (AUTOMERGE-02).

#### Disabling auto-merge

Add the `console.auto_merge` block to your console `config.yaml`. Set `enabled` to
`false` for explicit manual-only control (v5.4 behaviour):

```yaml
console:
  auto_merge:
    enabled: false          # set to false to require manual 'quirk sensor merge'
    trigger_condition: all-sensors-in
    # cadence_window_minutes: 1440
```

The toggle is read at evaluation time (per push). Changing the setting takes effect on
the next push; any in-flight pushes or merge tasks that have already started are
unaffected.

#### Trigger conditions

`trigger_condition` selects how the console decides it is time to merge. Two values are
available:

**`all-sensors-in`** (default)

The merge fires once every non-revoked enrolled sensor has checked in with a push newer
than the latest `MergeRun`. This is the safest choice for fixed-fleet deployments — you
always get a full-coverage CBOM. Revoked sensors are excluded from the "all in" set
(Phase 113 `revoked_at`), so revoking a decommissioned sensor does not block the merge.

**`cadence-window`**

The merge fires when the elapsed time since the last `MergeRun` exceeds a configured
window. The push that crosses the window boundary triggers the merge with whatever has
arrived at that moment. Sensors that have not pushed by the window deadline are listed in
a `coverage_warning` on the merged CBOM. This mode suits deployments where not all
sensors push on the same cadence or where time-bounded merges are preferred over
full-coverage guarantees.

Set the window explicitly with `cadence_window_minutes` (integer, minutes). If omitted,
the console defaults to the per-sensor `expected_cadence_minutes` value (default 1440
— 24 hours).

```yaml
console:
  auto_merge:
    enabled: true
    trigger_condition: cadence-window
    cadence_window_minutes: 720    # merge every 12 hours
```

#### Idempotency and duplicate merges

On single-tenant deployments, a narrow race between two simultaneous final pushes can
produce a second `MergeRun` row before the first has committed. This is harmless — the
rows are identical and the `scanned_at` timestamps on sensor findings are never
rewritten. The background task re-checks the condition before merging, so most
near-simultaneous pushes coalesce to one merge.

#### Reading auto-merge outcomes

Every auto-merge writes an `IntegrationDelivery` audit row:

| Field | Success value | Failure value |
|-------|--------------|---------------|
| `destination` | `auto_merge` | `auto_merge` |
| `status` | `ok` | `failed` |
| `error_summary` | *(empty)* | Sanitised error message |

Query via the dashboard or directly in SQLite:

```sql
SELECT destination, status, error_summary, created_at
FROM integration_deliveries
WHERE destination = 'auto_merge'
ORDER BY created_at DESC
LIMIT 10;
```

A `status='failed'` row means the merge raised an exception after the sensor push
response was already sent — the push data is safe and fully ingested. Check the console
log (`logger.warning` is emitted alongside the audit row) to diagnose the merge failure,
then run `quirk sensor merge` manually to retry.

#### Manual merge is unchanged (AUTOMERGE-03)

The `quirk sensor merge` command remains available and works identically to v5.4 — the
same Option-A union CBOM, `coverage_warning`, and sensor-local `scanned_at`. Auto-merge
and manual merge call the same underlying `merge_scan()` function. Operators who need
explicit control, scripted post-push merge verification, or a one-off merge after
enabling `all-sensors-in` with auto-merge disabled can always run:

```bash
quirk sensor merge
# Or with custom options:
quirk sensor merge --stale-days 7 --output-dir /var/quirk/merge-out
```

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

## 9. Hardware Scanning

Hardware scanning is an advanced, opt-in capability that fingerprints network devices
(switches, routers, access points) via SNMP, assigns CNSA 2.0 remediation tiers, and
annotates crypto-bridge topology. Operators who have not installed the `[hw]` extra and
do not manage network hardware can complete §1–§8 without interruption — the scanner
runs cleanly with the extra absent.

### 9.1 Enable SNMP Scanning

**Step 1 — Install the `[hw]` extra.**

```bash
pip install 'quirk-scanner[hw]'
```

This extra adds `pysnmp` and the hardware fingerprinting engine. See the §2.2 optional
extras matrix for a full dependency list.

**Step 2 — Enable SNMP in your config.**

Add the following two keys under the `scan:` block in `config.yaml`:

```yaml
scan:
  enable_snmp: true          # default: false — must be explicitly set to opt in
  snmp_community: "public"   # SNMPv2c community string; default: "public"
```

`enable_snmp` defaults to `false`. If you omit the key or leave it as `false`, the
scan runs cleanly with no error and no hardware devices appear in the output — this is
the expected behaviour when `[hw]` is not installed or when SNMP coverage is not needed.

**Step 3 — Run the scan.** The SNMP probe executes **after all endpoint scans complete**
and targets every unique host IP discovered during the full scan (TLS, SSH, fingerprint,
etc.), not just SSH endpoints. No additional target list is required.

**What QUIRK probes.** Three SNMP OIDs are queried per host:

| OID | Name | Purpose |
|-----|------|---------|
| `1.3.6.1.2.1.1.1.0` | `sysDescr` | Vendor and model string — primary parse target |
| `1.3.6.1.2.1.1.5.0` | `sysName` | Device hostname |
| `1.3.6.1.2.1.1.2.0` | `sysObjectID` | Enterprise OID — fallback vendor identification |

**Sample output.** Discovered hardware devices appear as a separate findings block:

```text
Hardware Devices Found: 3

  192.168.1.1   Cisco Catalyst 9300    Tier 1  HIGH   Replace by 2030
  192.168.1.254 Juniper EX2300         Tier 2  MEDIUM Upgrade firmware 2030-2033
  10.0.0.1      Aruba 2930F            Tier 3  LOW    Accept + monitor, re-evaluate 2033+
```

For the full config-key reference (all `scan.*` defaults, type constraints, and
advanced options), see [`docs/configuration.md`](configuration.md).

---

### 9.1.1 SNMPv3 Auth+Priv Scanning (Phase 139)

QUIRK also supports authenticated, encrypted SNMPv3 scanning as an upgrade path alongside
the SNMPv2c community-string scanning above. SNMPv3 credentials are configured per-host, not
globally — a network may have a mix of v3-capable and v2c-only devices.

**Configure a v3 credential.** Add a `connectors.snmp_v3_credentials` entry keyed by host
(see `docs/configuration.md` for the full field reference):

```yaml
connectors:
  snmp_v3_credentials:
    "192.168.1.1":
      username: "quirk-readonly"
      auth_key_env: "QUIRK_SNMP_AUTH_KEY"
      priv_key_env: "QUIRK_SNMP_PRIV_KEY"
      auth_protocol: "SHA256"
      priv_protocol: "AES256"
```

Set the referenced env vars, then run the scan exactly as in Step 3 above (`--enable-snmp`).
No secret CLI flags exist for v3 credentials — passphrases come only from config + the
environment, never from the command line.

**The v3 → v2c → none fallback ladder.** For each host, QUIRK attempts SNMP in this order:

1. **v3 attempted** — if a `snmp_v3_credentials` entry exists for the host, QUIRK probes with
   those USM credentials first.
2. **v2c fallback** — if v3 fails (wrong credentials) or the host offers a weaker protocol
   than requested, QUIRK falls back to the SNMPv2c community-string probe (§9.1) so the
   vendor/model identification can still succeed.
3. **none** — if neither v3 nor v2c gets a response, no SNMP finding is recorded for that
   host.

Each outcome is recorded honestly, not collapsed into a generic "SNMP succeeded" label — see
`docs/report-interpretation.md` for the five distinct labels this produces in reports and the
dashboard, including the important distinction between an intentional v2c-only scan and a
genuine v3 credential failure (`v3-failed-fell-back`).

---

### 9.2 CNSA 2.0 Remediation Tiers

Each discovered hardware device is assigned a tier derived from CNSA 2.0 (Commercial
National Security Algorithm Suite 2.0) guidance on post-quantum migration timelines.

| Tier | Severity | Deadline | Meaning |
|------|----------|----------|---------|
| Tier 1 | HIGH | Replace by 2030 | No PQC upgrade path — device must be replaced |
| Tier 2 | MEDIUM | Upgrade firmware 2030-2033 | PQC firmware upgrade path exists |
| Tier 3 | LOW | Accept + monitor, re-evaluate 2033+ | PQC roadmap exists but upgrade is distant |
| Tier N/A | INFO | EOL before PQC migration window | Device won't survive to the migration deadline |

**Client-facing action.** When presenting findings: Tier 1 devices require an active
replacement plan — no firmware path exists, so budget and procurement lead time need to
be on the remediation roadmap before 2030. Tier 2 devices need a vendor firmware roadmap
conversation; coordinate with the vendor to confirm the PQC upgrade timeline and track
it as a dated commitment. Tier N/A devices should be documented in the client's
decommission plan rather than the remediation backlog — they will reach end-of-life
before the PQC migration window opens, so a replacement is already warranted on standard
refresh cadence.

> **Note:** Hardware devices appear in the CBOM and on the dashboard hardware panel, but
> are advisory-only — they do not affect the quantum-readiness score. CNSA tiers are
> informational findings that inform the remediation roadmap.

---

### 9.3 Crypto-Bridge Detection

A **crypto bridge** is a network topology where a PQC-capable gateway (e.g. a TLS
terminator or reverse proxy with hybrid-mode support) sits in front of a legacy backend
device that is itself still running quantum-vulnerable cipher suites. The gateway
mitigates the backend's exposure to the wider network, but the backend's own cipher
posture remains unremediated.

**`partial_only` — what it means and when it fires.** QUIRK flags a device with
`bridge_status: partial_only` when both a PQC-capable gateway and a legacy backend are
directly reachable on the same /24 subnet. QUIRK uses a proximity heuristic to detect
this condition: a `partial_only` assignment means both a PQC-capable device (with
`pqc_status: partial` or `supported`) and a legacy device (with `pqc_status:
unsupported`, `vendor-silent`, or `unknown`) appear within the same /24 subnet — a
proximity heuristic, not confirmed traffic-flow analysis. This is the answer to the
"how did you determine this?" question during client review.

**`upstream_mitigated` — SNMP-confirmed bridge evidence (Phase 140).** As of Phase 140,
`upstream_mitigated` is a reachable, evidence-gated status, not a reserved placeholder. It
is assigned when the sensor collects direct SNMP evidence from the PQC-capable gateway
itself: a bounded, credential-scrubbed walk of the gateway's `ipNetToMediaTable` (ARP
table, OID `1.3.6.1.2.1.4.22.1.2`) that lists the legacy backend's IP address. This is a
network-path signal, not active traffic tracing or packet-level flow confirmation — QUIRK
still does not perform active path verification (e.g. traceroute-style probing or traffic
inspection) to confirm data actually crosses the gateway.

The confirmation probe is **targeted, not exhaustive** (D-03): it only runs against
devices the sensor's own scan batch has already pre-flagged as a `partial_only` gateway
candidate (a PQC-capable device sharing a /24 with a legacy backend in the same batch) —
it does not walk the ARP table of every SNMP-enabled device on every scan. It reuses the
same SNMPv3 USM transport introduced in Phase 139 (`§9.1.1` fallback ladder) when v3
credentials are configured for that host, falling back to v2c otherwise. Each walk is
bounded by both an overall wall-clock timeout and a hard cap on the number of ARP entries
collected, so a large or adversarial ARP table cannot turn the probe into a denial-of-service
vector. If the walk returns no entries, or the evidence doesn't list the legacy backend's
IP, the pair silently stays `partial_only` — QUIRK never promotes on subnet co-presence
alone, and never fails a scan because evidence wasn't collected.

Every device carrying SNMP-derived evidence gets a per-device audit trail: the raw
(IP, MAC) facts observed on the gateway's ARP table are stored (never the community string
or SNMPv3 passphrase) alongside a timestamp of when the evidence was collected, so an
operator can trace exactly what evidence justified the `upstream_mitigated` promotion.

**Action.** Both `partial_only` and `upstream_mitigated` findings do **not** reduce the
device's remediation requirement. The device still needs replacement or firmware upgrade
per its CNSA tier (see §9.2 above). The bridge annotation — at either status — is advisory
context about network topology; it is not a mitigation credit and should not be presented
to a client as one. `upstream_mitigated` is a stronger signal than `partial_only`, but it
still carries a mandatory caveat on every rendered surface: "Based on SNMP-derived
network-path evidence; not independently confirmed by traffic inspection." See
`docs/report-interpretation.md` §10.5 for the full rendering/badge contract across HTML,
PDF, DOCX, and the dashboard `/hardware` tab.

---

### 9.4 OT/ICS Fingerprinting (Modbus + BACnet, Phase 141)

> ## ⚠️ Risk Warning — Read Before Enabling
>
> **OT/ICS scanning is a materially different risk class than SNMP/SSH/HTTP hardware
> fingerprinting.** Industrial control gear — PLCs, RTUs, building-automation
> controllers — has a well-documented, industry-wide history of crashing, hanging, or
> otherwise misbehaving in response to even benign, read-only network queries. This is
> not a theoretical concern; it is the reason OT/ICS environments are conventionally
> scanned with far more caution than IT networks, if at all.
>
> **Obtain written authorization from the OT/ICS system owner before enabling
> `--enable-modbus` or `--enable-bacnet` against any production OT network.** QUIRK's
> read-only-only design and one-strike circuit breaker (below) reduce — but do not
> eliminate — this risk. Treat OT/ICS scanning as you would any other engagement
> requiring explicit, scoped, written client authorization, distinct from your general
> IT-network scanning authorization.

**What QUIRK probes.** Two independently-flagged, off-by-default protocols:

| Flag | Protocol | Port | What is sent |
|------|----------|------|---------------|
| `--enable-modbus` | Modbus/TCP | 502 (must be observed open) | A single FC 43/14 Read Device Identification request (Basic category — vendor/model/firmware strings only) |
| `--enable-bacnet` | BACnet/IP | 47808/UDP | A single directed-unicast Who-Is, followed by ReadProperty(model-name) and ReadProperty(firmware-revision) on the responding Device object |

Both flags default to `false` and must be explicitly set — QUIRK never probes Modbus or
BACnet unless the operator opts in. Modbus additionally requires port 502 to already be
observed open on the target (from the scan's own port-discovery phase) before the probe
fires at all; BACnet's single Who-Is/I-Am round trip is itself the confirmation signal
for this UDP-only protocol (there is no TCP-equivalent "confirmed open port" check for
UDP).

**Safety model.**

- **Read-only only.** Neither probe ever issues a write function/service code. Modbus
  sends only FC 43/14 (Read Device Identification); BACnet sends only Who-Is/I-Am
  discovery plus ReadProperty — no WriteProperty, no broadcast beyond the single
  directed-unicast Who-Is.
- **Single in-flight per host.** QUIRK never has more than one OT/ICS probe outstanding
  against a given host at a time.
- **One-strike circuit breaker.** Any anomalous response — timeout, malformed frame,
  connection reset, or exception — immediately aborts further OT/ICS probing of that host
  for the rest of the scan. There is no retry and no backoff, deliberately stricter than
  QUIRK's standard scan retry policy elsewhere.
- **Short, dedicated timeout.** Both probes use a conservative default timeout (2s),
  shorter than QUIRK's general scan timeout, to minimize the time spent holding a
  connection open against fragile embedded devices.

**Enable the flags:**

```bash
python run_scan.py --target 10.0.5.0/24 --enable-modbus --enable-bacnet
```

**Result labeling.** Every OT/ICS probe attempt resolves to one of five states, shown
distinctly in reports and the dashboard (never collapsed into a generic "scanned"/"not
scanned" binary):

| State | Meaning |
|-------|---------|
| Identified (Modbus / BACnet badge) | Vendor/model/firmware successfully read |
| No response | Host did not respond within the timeout |
| No match | A response was received but carried no usable vendor identity |
| **Probe aborted** | The one-strike circuit breaker fired — a real anomalous response, not "nothing happened" |
| Not attempted (em dash) | The flag was off, or (Modbus only) port 502 was never observed open |

The **"Probe aborted" state is operationally significant** — it tells the consultant the
device may be fragile or misbehaving and is worth a closer, more careful manual look,
rather than being silently indistinguishable from "no response." See
`docs/report-interpretation.md` for the full badge/column contract across the dashboard
and HTML/PDF/DOCX reports.

**Advisory-only.** Like all hardware fingerprinting signals (§9.1–§9.3), Modbus/BACnet
findings never affect the quantum-readiness score — they appear only in the advisory
hardware section of the report.

**Validate against the chaos lab.** `PROFILE_ARGS="--profile otics" ./lab.sh up` starts
two deliberately fragile Modbus/BACnet simulators that empirically exercise the safety
model above — see `docs/chaos-lab.md` and
`quantum-chaos-enterprise-lab/expected_results_otics.md`.

### 9.5 Firmware CVE Correlation (Phase 142)

QUIRK correlates each fingerprinted device's `(vendor, model, firmware)` triple against a
small, curated, NVD-cited local CVE catalog (`quirk/scanner/hw_cve.py::CVE_TABLE`) — never a
live NVD API call, so correlation works fully offline and cannot be used to fingerprint the
scanning host to an external service. This is the fourth advisory-only hardware signal after
SNMP (§9.1), CNSA 2.0 tiers (§9.2), and Modbus/BACnet (§9.4).

**`quirk cve status` — catalog freshness.** Mirrors `quirk qramm status`/`quirk compliance
status` exactly:

```bash
quirk cve status
quirk cve status --format json
```

Reports the CVE snapshot's `last_verified` date, days elapsed, days remaining before the
30-day staleness threshold, and a FRESH/STALE verdict. Exit code `0` when fresh, `1` when
stale — the same 0/1 convention used by `quirk qramm status` (§7) so CI and pre-engagement
scripts can gate on it. Like the QRAMM and compliance catalogs, `QUIRK_CI_STALENESS_OVERRIDE_DATE`
overrides "today" for staleness-gate testing; a malformed override value is logged as a warning
and ignored, falling back to the real system date rather than crashing the command.

**The CVE advisory scanner signal.** During report/dashboard generation, QUIRK calls
`correlate_device(vendor, model, firmware)` for every device with a known (non-"Unknown")
vendor. Firmware comes from whatever protocol already fingerprinted the device (Modbus/BACnet
firmware strings preferred, SNMP/SSH/HTTP vendor+model otherwise). Two confidence levels:

- **high confidence** — the device's parsed firmware version falls inside a CVE entry's
  documented affected range (an NVD "prior to X" boundary, exclusive `<`).
- **medium confidence** — only a vendor+model match exists (the curated entry has no
  version boundary, or the device's firmware string could not be parsed); QUIRK does not
  guess whether the specific firmware is actually affected.

**Firmware CVE matches are advisory-only — never a severity finding, and never a score or
remediation-tier input.** This is a hard architectural boundary (CVE-01/CVE-04): the CVE
correlation module imports nothing from `intelligence/scoring.py` or `hardware_tier.py`, and
a dedicated regression test (`tests/test_cve_score_guard.py`) enforces this in CI. Operators
should treat CVE matches as "worth investigating," not as a scored risk the readiness score
already accounts for.

**BACnet vendor-name resolution (Phase 147, decision D-147-02-A).** BACnet's raw Who-Is/I-Am
probe returns only a numeric ASHRAE vendor ID and a raw model string — neither can match the
CVE catalog's `(vendor_name, product_family)` keys on its own. As of Phase 147,
`quirk/scanner/bacnet_vendors.py` — a curated-catalog + staleness-gate module mirroring
`hw_cve.py`'s own shape, on a **365-day cadence** (`quirk cve status`'s 30-day cadence does
not apply to this table; ASHRAE vendor-ID assignments are append-only/stable) — resolves the
numeric vendor ID and raw model to real vendor/product-family names *before* `correlate_device()`
is called. This is what makes the curated `("Johnson Controls", "Facility Explorer")` CVE
entry reachable for a real BACnet FX16 fingerprint. Coverage is intentionally curated, not
exhaustive: an unrecognized vendor ID displays the raw numeric value exactly as before this
phase, with no regression and no crash. See `docs/report-interpretation.md` §10.8 for the
consultant-facing rendering contract.

See `docs/report-interpretation.md` §10.7 for the report/dashboard rendering contract, and
`docs/configuration.md` for the 30-day staleness cadence and re-verification procedure.

---

### 9.6 Device Re-Identification Fields (Phase 154)

As of Phase 154, every fingerprinted `HardwareDevice` row carries three new per-device fields
that improve re-identification across scans and honesty about probe outcomes. None of these
are rendered as report or dashboard columns yet (deferred to a later release) — they are
scanner-internal fields today, documented here so operators understand the underlying data
model and the retention/last-known-good behavior it drives.

- **`ssh_host_key_fingerprint`** — the SHA256 SSH host-key fingerprint QUIRK's existing
  `ssh-audit` run already captures for the device. Because a host key is tied to the device
  itself (not its current IP), this fingerprint is the stable secondary identity key that
  survives a DHCP lease renewal or a re-IP — something a `host:port` match alone cannot do.

- **`match_confidence`** — `high` when a `ssh_host_key_fingerprint` was captured for the
  device, `low` when the device could only be matched on `host:port`. `low` covers three
  distinct cases operators should be aware of: HTTP-only devices, SNMP-only devices, and —
  importantly — **SSH-reachable devices scanned from a host that does not have `ssh-audit`
  installed**. Operators who want `high`-confidence coverage across their SSH-reachable
  hardware should install `ssh-audit` on the scanning host (see §1).

- **`probe_status`** — `success` when the fingerprinting probe got any response at all,
  including an honest `vendor="Unknown"` result (an unrecognized device that still answered
  is a successful probe, not a failure). `failed` means the probe errored, timed out, or
  nothing on the device answered at all.

**`match_confidence` is not the same field as the pre-existing `confidence` column.**
`confidence` (used elsewhere in hardware fingerprinting, e.g. §9.5's CVE correlation) describes
confidence in a *probe result* — how sure QUIRK is about a parsed vendor/model/firmware value.
`match_confidence` describes confidence in *cross-scan device identity* — how sure QUIRK is
that two rows scanned at different times represent the same physical device. A device can have
high result confidence (a cleanly parsed vendor/model) and low match confidence (no SSH host
key to re-identify it by), or vice versa; the two fields are independent.

See `docs/report-interpretation.md` §10.9 for how `probe_status` drives which row is shown as
a device's current state, and `docs/configuration.md` for the retention window
(`hardware_history_retention_days`) that bounds how long old probe rows are kept.

**Tuning `hardware_drift_event_retention_days` (Phase 157, HWLC-16).** A separate retention
knob, `scan.hardware_drift_event_retention_days` (default `365`), bounds the age of rows in the
`hardware_drift_events` table described in §9.7 below — see `docs/configuration.md` for its
full mechanism.

- **Raise it** on long engagements where a client wants multi-year drift history for
  year-over-year lifecycle comparison — there is no hard ceiling.
- **Lower it** if disk pressure on a long-running console instance becomes a concern; a smaller
  window keeps the `hardware_drift_events` table smaller.
- **Lowering it deletes history irreversibly on the next scan.** The purge is a hard delete, not
  an archive — once a drift event ages past the configured window and a scan runs, that row is
  gone. Lower the value only when the older history is genuinely no longer needed.
- **No separate command or schedule.** The purge runs automatically as part of every scan's
  normal completion — there is no `quirk hardware purge` equivalent for drift events and no cron
  job to configure.

---

### 9.7 Hardware EOL/EOS Catalog + Lifecycle Drift Events (Phase 155)

As of Phase 155, QUIRK tracks two additional advisory-only hardware lifecycle signals on top
of the fingerprinting/tier/CVE foundation from §9.1–§9.6: a curated vendor end-of-life catalog,
and cross-scan drift events derived by reconciling a device's fingerprint history.

**Hardware EOL/EOS catalog.** `quirk/scanner/hardware_eol.py::EOL_TABLE` maps each
`(vendor, model)` pair to a curated end-of-life / end-of-support date pair, mirroring the
existing curated-catalog + staleness-gate pattern used by `hw_cve.py` (§9.5),
`bacnet_vendors.py` (§9.5), `quirk/compliance/__init__.py`, and `quirk/qramm/model_meta.py`.
Unlike CVE disclosures — which are continuously published and gated on a 30-day cadence — vendor
EOL/EOS announcements are infrequent, pre-scheduled events published via dedicated lifecycle
bulletins months or years in advance. The EOL catalog is therefore gated on a **365-day**
cadence (`STALENESS_THRESHOLD_DAYS = 365` in `hardware_eol.py`), the same cadence used for the
compliance mappings and the BACnet vendor catalog. CI enforces this via
`tests/test_eol_staleness.py`, which fails once the catalog's `last_verified` date is more than
365 days old.

When CI (or a local `pytest` run) reports the EOL catalog stale, follow the same 3-step
re-verification procedure documented in `CLAUDE.md`'s Staleness Review Cadence section:

1. Re-verify each `EOL_TABLE` entry against its `source_url` — confirm the published EOL/EOS
   dates have not changed and are still cited to a live vendor or aggregator page.
2. Bump `EOL_TABLE_META["last_verified"]` in `quirk/scanner/hardware_eol.py` to today's ISO date.
3. Commit with `chore: re-verify hardware_eol catalog (YYYY-MM-DD)`.

**What EOL data changes about a scan.** As of Phase 155, `HardwareDevice.eol_date` is populated
from this catalog automatically during fingerprinting via `apply_eol_date()`. Most fingerprint
paths (SSH banner, HTTP management, SNMP, Modbus, BACnet) converge on a single call site inside
`fingerprint_one()`; the standalone SNMP-only bulk-discovery sweep in `run_scan.py` builds its own
`HardwareDevice` rows outside that waterfall and calls `apply_eol_date()` separately at its own
construction site, so every code path that creates a device row populates `eol_date` — not just
the ones routed through `fingerprint_one()`. This interacts with the pre-existing (Phase
128) CNSA 2.0 tier-assignment rule in `hardware_tier.py::assign_tier()`: a device whose EOL date
falls before 2030-01-01 is assigned **Tier N/A**, regardless of its PQC support status. Because
the EOL catalog was dormant before this phase, populating a real EOL date can legitimately move
a previously Tier 1/2/3 device to Tier N/A on its very next scan. **This is intended behavior,
not a regression** — a device whose vendor has already end-of-lifed it is not a candidate for
PQC remediation planning in the same sense as a supported device, so Tier N/A correctly routes
it toward replacement guidance instead. Operators who see a device's tier shift to Tier N/A after
upgrading to a build that includes this catalog should expect it, not file a bug.

**Lifecycle drift events.** Every hardware-device commit during a scan now triggers
`reconcile_device_history()` (`quirk/scanner/hardware_drift.py`), which compares a device's most
recent successful probe rows against its scan history and — when a change is corroborated —
persists a row to the `hardware_drift_events` table. Four event types are tracked
(`EVENT_TYPES` in `hardware_drift.py`):

- **`tier_crossing`** — the device's stored CNSA 2.0 remediation tier changed between scans
  (for example Tier 2 → Tier 1, or a shift to/from Tier N/A driven by the EOL catalog above).
- **`upstream_mitigated_change`** — the device's SNMP-confirmed crypto-bridge evidence state
  changed (see §9.3's `partial_only` → `upstream_mitigated` promotion).
- **`cve_delta`** — the set of correlated firmware CVEs (§9.5) changed between scans, e.g. a
  catalog update surfaced a newly-applicable CVE for the device's fingerprinted firmware.
- **`eol_state_change`** — the device's EOL classification (`"approaching"` — within 12 months
  of its EOL date — or `"passed"` — already past it) changed between scans.

**Confirmation window.** Tier, bridge-evidence, and EOL-state changes are gated by a **2-of-3
confirmation window**: a new value must be corroborated by at least 2 of the device's last 3
successful probes before it is recorded as a drift event. A single dropped packet or transient
network hiccup that produces one anomalous reading therefore does **not** generate a false drift
event — only a value that holds across the majority of the recent window does. (CVE-delta events
are the one exception: they are computed as a direct two-row diff, not N-of-M gated, since a CVE
catalog update should surface immediately rather than wait for confirmation.)

Drift events accumulate in the `hardware_drift_events` table and are **deduplicated per
`(host, port, event_type)`** — a stable value that holds across many consecutive scans is
recorded once, not once per scan. Like every other signal in this section, drift events are
**advisory-only**: `hardware_drift.py` is never imported by `quirk/intelligence/scoring.py`, and
a dedicated regression test (`tests/test_cve_score_guard.py`) enforces that boundary in CI. A
scan's readiness score is identical whether or not drift events were recorded during it.

Dashboard and report surfacing of `hardware_drift_events` rows shipped in Phase 156 — see §9.8
below and `docs/report-interpretation.md` §10.10.

### 9.8 Recent Lifecycle Changes Dashboard Section (Phase 156)

As of Phase 156, the `/hardware` and `/compare` dashboard pages render a "Recent Lifecycle
Changes" section surfacing the `hardware_drift_events` rows persisted by §9.7's reconciliation
engine. It is a structurally and visually distinct advisory card — separate teal-accented chrome,
never reusing the tier/PQC/confidence/SNMP badge palette — so it reads as clearly different from
the scored-finding chrome elsewhere on the page.

**What appears.** Each row shows: an event-type icon and label, the device's identity
(`host:port` plus vendor/model), the literal `{old_value} → {new_value}` transition, a direction
indicator, and the detection date. The most recent events render inline; older ones are tucked
behind a collapsible "N historical events" disclosure so the section doesn't dominate the page on
a long-running device.

**The four event types** are the same ones recorded by §9.7's reconciliation engine, with these
display labels: Tier crossing, Bridge mitigation change, CVE correlation change, EOL/EOS state
change.

**Direction vocabulary.** Each event carries one of three direction labels — **Improved**,
**Worsened**, or **Changed** — derived from the CNSA 2.0 tier ordering (§9.2), not from a
severity ranking. "Changed" (backed by the internal `neutral` value) covers event types with no
inherent better/worse direction, such as a CVE-delta or an EOL-state change — those are simply
different, not improved or worsened.

**Two empty states, and how to tell them apart.** The section distinguishes "no prior scan
exists yet" (a device's very first scan, by construction, has no lifecycle history to show) from
"a prior scan exists but nothing changed" (the device has been re-scanned and its lifecycle
state has been stable). Both render as advisory copy in the same card location, with different
wording — never a blank space that could read as a missing feature.

**Where it appears.** On `/hardware`, the section renders as a sibling block after the device
table, visible even when the device table itself shows its own empty state. On `/compare`, the
same section renders sourced from the compared scan pair's drift events, after the existing
comparison tabs.

**Advisory-only, no score contribution.** Like every other signal in this section, drift events
shown here carry no severity and make no contribution to the quantum-readiness score — see
`docs/report-interpretation.md` §10.10 for the verbatim advisory caption and how it renders
across the HTML, PDF, and DOCX report formats.

### 9.9 Check-in Scan Mode (`--check-in`, Phase 159)

As of Phase 159 (HWLC-13), `--check-in` is a lightweight, opt-in re-probe of the hardware fleet
QU.I.R.K. already knows about. It exists for the common between-engagements case: a consultant
wants to see whether anything on a previously fingerprinted fleet has drifted, without paying the
cost of a full scan.

```bash
python run_scan.py --config config.yaml --check-in
```

**`--check-in` is a bare boolean opt-in on `run_scan.py`, not a `--profile` value.** It cannot be
combined with `--profile`'s `quick`/`standard`/`deep` choices — it is a separate short-circuit
that fires immediately after database initialization, before any profile-driven scan logic runs.

**What it does and does not do:**

- **Targets** are the latest successful `HardwareDevice` row per `(host, port)` — the same
  last-known-good projection described in §9.6 — never a fresh network sweep.
- **No discovery.** Network/CIDR discovery, nmap liveness pre-passing, and target expansion are
  all skipped entirely.
- **No non-hardware scanner phases.** TLS, SSH, JWT/API, container, source-code, and cloud KMS
  scanning are all skipped. Only the hardware-fingerprinting probe family is re-run.
- **Only the device's own probe family is re-run.** Each device's stored `fingerprint_method`
  (`ssh_banner`, `http_mgmt`, `snmp`, `modbus`, or `bacnet`) determines which single probe
  re-fires — a device originally fingerprinted via SSH is re-probed via SSH only, never promoted
  to a different probe family.
- **`modbus`/`bacnet` devices are skipped** when `connectors.enable_modbus` /
  `connectors.enable_bacnet` are off, exactly as they are during a normal scan — a check-in never
  force-enables OT/ICS probing.
- **An empty fleet is a clean no-op.** If no `HardwareDevice` rows exist yet (no prior scan has
  ever fingerprinted a device), `--check-in` prints an operator message and exits `0` with **zero
  database writes** — it never errors out.
- **Persists only `HardwareDevice` and `hardware_drift_events` rows**, through the same
  `persist_and_reconcile()` chokepoint (§9.7) used by a full scan. Every row it writes carries
  **`is_partial_scan=True`**.
- **Never produces a readiness score or a full report.** A check-in run does not invoke the
  scoring engine, the HTML/PDF/DOCX report writer, or the CLI/markdown executive summary. Run a
  full scan (no `--check-in`) to get an updated readiness score.

**Example CLI summary** (printed to the log, advisory-only, no return value):

```
[Check-in re-probe - partial scan, not scored]
  Devices re-probed: 4 | Success: 3 | Failed: 1 | Drift events: 2
  Not scored - run a full scan for an updated readiness score.
```

**Where check-in-sourced data shows up afterward.** Devices and drift events written by a
check-in carry `is_partial_scan=True`. They stay visible everywhere the equivalent full-scan data
would be — the `/hardware` and `/compare` dashboard pages, `GET /api/hardware/drift`, and
`CompareResponse.hardware_drift` — badged rather than filtered out (see
`docs/report-interpretation.md`'s check-in section for the exact reader-facing wording and the
`/trends`/`/compare` readiness-score exclusion). A check-in run is never selectable as a scored
scan on `/api/scans` or `/api/trends`.

**Putting a check-in on a schedule (Phase 162, HWLC-20).** Rather than remembering to run
`--check-in` by hand, register it with the scheduler:

```bash
quirk schedule add --name nightly-checkin --cron "0 2 * * *" --check-in
quirk scheduler run      # the long-running dispatch loop
```

- **No `--target` is needed or accepted as meaningful.** A check-in re-probes the fleet already
  recorded in the database (`latest_successful_hardware_devices()`), so there is nothing to aim
  it at. The stored target reads `(known fleet)` in `quirk schedule list` and on the dashboard.
- **No `--profile` applies.** The dispatcher emits `run_scan --check-in` and deliberately no
  `--profile`, because check-in mode short-circuits before any profile is read. A dispatched
  command that named a profile would misrepresent what actually runs.
- **A scheduled check-in is the same code path as a manual one.** There is no second
  implementation, so every HWLC-13 guarantee above holds identically: `is_partial_scan=True`,
  the partial-scan banner, no readiness score, and exclusion from `/trends` and `/compare` as a
  scored session.
- **The dashboard marks them.** `/schedules` shows a `check-in` chip beside the schedule name so
  a lightweight re-probe is distinguishable at a glance from a scored profile scan.

Enable, disable and remove them exactly like any other schedule
(`quirk schedule enable|disable|remove <name>`).

### 9.10 Catalog-Level PQC Vendor Trend Tracking (Phase 160, HWLC-17)

As of Phase 160, QUIRK tracks **vendor-scoped** PQC-status change over time, in addition to
the existing per-device drift tracked in `hardware_drift_events` (§9.7).

**What a vendor PQC trend event is.** A confirmed, fleet-wide change in a vendor's
catalog-assigned `pqc_status` (e.g. `unsupported` → `partial`), recorded as a discrete row in
the `vendor_pqc_trend_events` table. Each row carries the vendor, the event type
(`pqc_status_change`), the old and new `pqc_status` values, and the timestamps the change was
detected and confirmed.

**How it differs from per-device drift.** `hardware_drift_events` (§9.7) is per-`(host, port)`
— it tells you a specific device changed. `vendor_pqc_trend_events` is vendor-scoped, has no
`host`/`port` column at all (cross-device, cross-host). The two tables are structurally distinct
and serve different questions: "did this device change?" vs. "did this vendor's catalog posture
change?"

**Confirmation gate.** Like every other lifecycle signal in QUIRK, a vendor trend event only
fires after N-of-M confirmation (N=2 of M=3, the same defaults used everywhere else in QUIRK) —
but the window here samples the **3 most-recently-scanned distinct devices of that vendor**, not
repeated scans of one device and not the vendor's entire fleet. This means a single noisy or
repeatedly-rescanned host cannot, by itself, trigger a vendor-level event, but it also means the
signal reflects a recent sample rather than an exhaustive fleet-wide census — a vendor with many
active devices is judged on its 3 most-recently-seen ones. It also means a vendor's first-ever
observed device never produces an event — there is nothing to compare it against yet.

**Querying it.** `GET /api/hardware/vendor-trends` returns the bounded, newest-first list:

```bash
curl -H "Authorization: Bearer $QUIRK_API_TOKEN" \
  "http://localhost:8000/api/hardware/vendor-trends?limit=50"
```

- Authenticated the same way as every other dashboard API route (§2.4) — no separate
  credential.
- `limit` accepts 1–200 (default 50); a `truncated: true` flag in the response body indicates
  more rows exist than were returned.
- Each event exposes `vendor`, `event_type`, `old_value`, `new_value`, `detected_at`, and
  `confirmed_at` — no host/port, no score, no numeric field.

**Advisory-only, no score contribution.** Like `hardware_drift_events`, vendor PQC trend
events never affect the readiness score — `quirk/scanner/hardware_drift.py` and
`quirk/models_util.py` are never imported by `quirk/intelligence/scoring.py`, machine-enforced
by `tests/test_cve_score_guard.py`.

**Now rendered in every report format.** As of Phase 161 (HWLC-19) vendor PQC trend events are
rendered in the HTML, DOCX and CLI technical reports and on the dashboard `/hardware` page — see
§9.11 below. The endpoint above remains available for direct queries.

---

### 9.11 Vendor PQC Status Trends on the Dashboard (Phase 161, HWLC-19)

The `/hardware` page carries a **Vendor PQC Status Trends** section immediately below Recent
Lifecycle Changes (§9.8). It renders the same `vendor_pqc_trend_events` rows the §9.10 endpoint
serves.

- **Advisory-only.** The section uses the non-severity advisory chrome — no red/amber/green
  severity colouring and no alert chips — because vendor trends never affect the readiness score.
  The caption "Advisory — vendor PQC status trends do not affect the readiness score." is always
  visible, never collapsed behind a disclosure.
- **Vendor-scoped.** Rows describe a vendor's fleet-wide posture, not a device, so there is no
  host, port or severity column. See `docs/report-interpretation.md` §10.13 for the column
  meanings and how to explain them to a client.
- **Independent of drift.** The section renders whether or not this scan produced device drift
  events, and shows a plain empty-state card — not a blank area or a spinner — when there are no
  trend events to show.
- **Truncation.** The API returns up to 50 events by default. When more exist, the section renders
  a plain-text note rather than pagination controls.

---

### 9.12 Hardware Lifecycle Notifications (Phase 161, HWLC-14)

QUIRK can notify you when a scan detects that a device's lifecycle posture got *worse*. Enable it
with the `notify_on_hardware_lifecycle` key in your config's `notifications:` block — see
`docs/configuration.md`. It is **off by default**.

**What triggers a notification**

Exactly two things:

| Trigger | Notifies? |
|---|---|
| A **worsening** remediation-tier crossing (e.g. Tier 1 → Tier 2) | Yes |
| Any **EOL/EOS state change** | Yes |
| An **improving** tier crossing (e.g. Tier 2 → Tier 1) | **No — deliberately** |
| A CVE correlation change or bridge-mitigation change | No |
| A vendor PQC trend event (§9.11) | No — catalog-level, not device-level |

Improving crossings are deliberately silent. The feature exists to surface degradation that needs
action; paging an operator because a device got *better* trains them to ignore the channel.

**Where it delivers**

Email and webhook only — Slack is not a destination for lifecycle alerts. Delivery reuses the
existing `email:` and `webhook:` configuration and credential model; enabling the key without
either configured changes nothing.

**Audit trail**

Every delivery attempt — success or failure — is recorded in the `integration_deliveries` table
with a composite identifier of the form `{host}:{port}:{event_type}:{event_id}`, so a specific
alert can be traced back to the exact drift event that produced it.

**Failure isolation**

Notification delivery is advisory-only and can never abort a scan. The dispatch hook sits inside
`persist_and_reconcile()` and is wrapped so that a failing SMTP server, an unreachable webhook, a
misconfigured credential, or an entirely uninstalled notification extra is logged and audited but
leaves the scan, the sensor push, or the air-gap import completely unaffected. If you enable
notifications and see nothing arrive, check the `integration_deliveries` rows first — the attempt
will be recorded there with its error summary even when delivery failed.

---

## 10. Discovery Liveness Pre-Pass

As of Phase 145 (DISC-03), every nmap-discovery batch runs a cheap TCP-based liveness
pre-pass before its full port sweep. This shrinks scan time on large, sparse ranges by
skipping the expensive `-sT` sweep against hosts that never answer.

### 10.1 What it does

Before `run_nmap_discovery()` sweeps a batch, QUIRK runs `run_nmap_liveness_check()`
against that same batch: an `nmap -sn -PS<ports>` probe (host discovery only — `-sn` —
using a TCP SYN ping on the given ports, `-PS`, with `-n` to skip DNS resolution). Hosts
that respond are swept normally; hosts that do not respond are excluded from the sweep
and recorded as `liveness_skip` rows (see §10.4 and `docs/report-interpretation.md`).

This is **TCP-based, not ICMP-based** — `-PS` sends a TCP packet with the SYN flag to
the probed ports rather than an ICMP echo request. That matters because segmented
enterprise networks routinely filter ICMP but still route TCP, so a TCP-based liveness
probe correctly detects hosts that an ICMP `ping`-style check would wrongly report as
dead.

### 10.2 Which ports it probes (D-03)

The pre-pass reuses the same port list the sweep itself will use — a host that is
"live" only means it answered on at least one of those ports, which is exactly what the
sweep needs. For the `top1000` and `all` port scopes (see §3), `-PS` has no
`--top-ports` equivalent, so the pre-pass falls back to the full `-PS-` (1–65535) range
instead. A superset can never wrongly mark a host non-responsive, so this fallback is a
safe, reliability-first default (D-03) rather than a narrower approximation.

### 10.3 Privilege fallback

nmap's SYN-ping probe (`-PS`) normally requires raw-socket privileges. When those
privileges are not available, nmap silently substitutes a TCP connect probe for the SYN
probe — and its XML output is byte-identical either way, so there is no way to detect
the substitution from the probe's own results.

QUIRK checks `os.geteuid()` exactly once per scan (via `_is_privileged()` in
`run_scan.py`) and, whenever the process is **not** confirmed to be running as root —
including on platforms that provide no way to check at all, such as the Windows sensor
build, where `os.geteuid` does not exist — it treats that as "not privileged" and
discloses the possible downgrade two ways:

- A logger message: *"liveness pre-pass may have silently degraded from a SYN probe to
  a TCP connect probe (no raw-socket privileges detected) — results remain valid but the
  pre-pass will run slower than intended."*
- A single persisted `privilege_fallback` advisory row in the scan artifact (one per
  scan, not one per batch — see §10.4).

**Results remain valid either way** — a TCP connect probe still correctly determines
host liveness, it is just slower than a raw SYN probe. Running the scan as root (or via
`sudo`) removes the advisory entirely, because `_is_privileged()` then returns `True`
and the fallback-disclosure call never fires.

### 10.4 What happens on failure

If the pre-pass itself fails (nmap errors, times out, or is missing) for a batch, QUIRK
does not lose that batch's hosts: it logs the failure and sweeps the entire batch
unfiltered, exactly as if no pre-pass had run. A batch where every host is
non-responsive short-circuits entirely — the sweep subprocess is never spawned for a
fully-dead batch.

### 10.5 Where to look afterward

Every liveness-skipped host produces its own `CryptoEndpoint` row in the scan artifact
with `scan_error_category="liveness_skip"` and the real host address, so a skipped host
is never silently dropped from the record. See `docs/report-interpretation.md` for how
to interpret `liveness_skip` and `privilege_fallback` rows in a delivered report.

> **Operator note:** the total number of undetermined (skipped) hosts is now surfaced
> as an aggregate "Hosts undetermined" count in every report surface — see
> `docs/report-interpretation.md` §13.

## 11. Chunked Discovery Progress and Per-Batch Scaling

As of Phase 146 (DISC-04/DISC-05/DISC-06), the chunked nmap discovery batch loop
introduced in Phase 144 reports its own progress in real time and scales each batch's
nmap subprocess timeout and timing aggressiveness to that batch's own size.

### 11.1 Where batch progress appears (DISC-04)

- **Dashboard:** the scan-job page renders a muted sub-line beneath the stage progress
  bar — "Batch N of M — X hosts checked" — while the current stage is `discovery`. It
  appears only after the first batch completes and disappears once discovery finishes.
  This is driven entirely by the existing job-status poll; no separate endpoint or
  websocket is used.
- **CLI:** on `--discovery nmap` runs, a line prints to stdout once per completed batch:

  ```
  Discovery: batch N/M (X hosts checked)
  ```

  This line is suppressed when `--quiet` is set. Both the dashboard fields and the CLI
  line are written from the exact same batch-loop bookkeeping in `run_scan.py`, so the
  numbers always agree.

### 11.2 Per-batch timeout scaling (DISC-05)

Each nmap subprocess call inside the batch loop (both the Phase 145 liveness pre-pass
and the full discovery sweep) now receives a timeout computed per batch instead of a
single fixed value for the whole scan:

```
timeout_seconds = min(300, 30 + 0.26 * batch_size)
```

- **Base:** 30 seconds.
- **Per-host scaling:** 0.26 seconds added per host in the batch.
- **Ceiling:** clamped to 300 seconds — the same ceiling the pre-Phase-146 fixed timeout
  used, so no batch can run longer than before. A small batch (e.g. one host) finishes
  its timeout budget in well under a second over the base; a full 1024-host batch stays
  at or below the 300s ceiling.

### 11.3 Per-batch timing template (DISC-05/DISC-06/DISC-07)

Alongside the timeout, each batch also selects an nmap `-T` timing template based on its
own size: `-T4` (aggressive) for batches at or below 256 hosts, `-T3` (normal) for
batches larger than that. In practice this only changes nmap's RTT-probe timing —
`_default_nmap_args` already hardcodes `--max-retries 1`, `--host-timeout 10s`, and
`--max-parallelism 100`, and per verified nmap documentation those explicit flags
override the `-T` template's own defaults for those specific values regardless of argv
order.

### 11.4 `--nmap-timeout` no longer governs chunked discovery

The CLI's `--nmap-timeout` flag no longer applies inside the Phase 144 chunked discovery
batch loop — the per-batch formula in §11.2 fully replaces it there. The dashboard's
spawned `run_scan.py` subprocess also no longer passes a static `--nmap-timeout 300`
argument, since that static value could otherwise silently override the per-batch
formula; the 300s ceiling is now enforced entirely by the formula's own clamp. The flag
remains meaningful for any future non-batched discovery code path and its `--help` text
reflects this.

### 11.5 CLI and dashboard share one discovery implementation (DISC-06)

The dashboard does not run its own separate discovery logic — it spawns the same
`run_scan.py` CLI entry point as a subprocess, so both surfaces execute exactly one
discovery code path. This is locked by a static/AST-based regression test
(`tests/test_cli_dashboard_discovery_parity.py`) asserting a single call site each for
`run_nmap_discovery()` and `run_nmap_liveness_check()`, both lexically inside the Phase
144 batch loop, and confirming `jobs.py` never calls `run_nmap_discovery(` directly.

## 12. OT/ICS Recurring-Scan Safety

Phase 141 (§9.4) introduced Modbus/BACnet fingerprinting with a deliberately narrow safety
model — a single read-only request per probe, a one-strike circuit breaker, and off-by-default
flags. That safety model was designed and validated for a **one-off, operator-initiated scan**.
Phase 156 closes a gap that model didn't cover: what happens when those same flags are wired
into a *recurring*, unattended scheduled scan.

**Why the gate exists.** The Modbus and BACnet scanners were designed for exactly one read-only
request per engagement, run by a human who has obtained authorization and is watching the
outcome. Unbounded, unattended recurring probing against fragile production control systems —
PLCs, RTUs, building-automation controllers — is a real outage risk, not a theoretical one; this
is the same risk class documented in §9.4's risk warning, now compounded by removing the human
from the loop entirely.

**The two conditions a scheduled run must satisfy.** A `quirk scheduler run` dispatch will only
allow Modbus/BACnet probing to reach a device if **both** of these hold:

1. `connectors.enable_recurring_otics: true` is set in the scan config the scheduler dispatches
   with.
2. The schedule's own cron expression's minimum firing gap is at or above the 168-hour
   (7-day) floor — see `docs/configuration.md`'s [OT/ICS Recurring-Scan Cadence
   Floor](configuration.md#ot-ics-recurring-scan-cadence-floor-v513-phase-156) section for
   exactly how that gap is derived.

If either condition fails, `enable_modbus`/`enable_bacnet` are silently stripped from that run's
generated config and the rest of the scheduled scan proceeds normally — the run is never failed
because of this.

**What an operator sees when creating a sub-floor schedule.** Creating the schedule always
succeeds — it is never rejected for this reason:

- Via `POST /api/schedules`: the response is `201`, with the new schedule's `advisories` array
  containing a message describing the sub-floor cron and the 168-hour floor it falls under.
- Via `quirk schedule add`: the schedule row is created as usual, and a yellow advisory line is
  printed directly beneath the normal "added" confirmation. Exit code stays `0`.

Neither surface returns a `422`/`400` for a sub-floor cron. This is intentional (see
`docs/configuration.md` for why): the scheduler applies one shared scan config to every schedule
it dispatches, so at creation time it cannot know whether OT/ICS will ever actually be enabled
for that schedule.

**Where to look when PLCs stop being fingerprinted.** If Modbus/BACnet devices that used to
appear in scheduled-scan results stop showing up, check the scheduler's log output for a line
matching this shape:

```
OT/ICS probing suppressed for schedule 'nightly-plant-scan' (cron='0 * * * *'): removed keys ('enable_modbus', 'enable_bacnet') — reason: ...
```

The literal text `OT/ICS probing suppressed` always appears, followed by the schedule name, the
exact keys that were stripped from the generated config, and the reason (cadence-floor violation
or the recurring opt-in being off). This line is emitted at INFO level on every suppressed
dispatch — it is the single place to look first when a scheduled scan silently stops covering
OT/ICS devices it used to cover.

## 13. Discovery Batch Resume

As of Phase 163 (DISC-08), a discovery scan interrupted mid-run and resumed via
`--resume-scan-id` skips the individual nmap-discovery batches that already completed
before the interruption, instead of re-probing every batch from zero.

### 13.1 What changed

Before this phase, resume was stage-granular only: `--resume-scan-id` skipped an
entire completed *stage* (e.g. `discovery`), but if `discovery` itself was interrupted
partway through, the next run re-probed **every** batch in that stage from scratch. At
`_MAX_HOSTS_PER_CIDR = 1024`, a /16 interrupted at batch 60 of 64 previously re-probed
all ~65,000 hosts on resume. It now re-probes only the ~4,000 hosts in the unfinished
batches (batches 61-64).

### 13.2 How to use it

1. Find the interrupted scan's ID with `--list-resumable`:

   ```bash
   python run_scan.py --config config.yaml --db-path output/quirk.db --list-resumable
   ```

   This prints every scan that has checkpoint rows but never reached a completed
   `reports` stage, newest first, with its last completed stage and age. Rows older
   than 72h are highlighted, but a run stays resumable until its batch cache files
   expire at 720h (see 13.4).

   The **Target** column reflects how the scan was started. For dashboard-dispatched
   `--job-id` runs, it shows the literal target string recorded at dispatch time
   (e.g. `10.0.0.0/24`). For `--targets-file` and other CLI runs — which have no such
   record — it shows a summary derived from the endpoints scanned so far for that run,
   e.g. `10.0.0.1, 10.0.0.2 (+3 more)`, truncated to the first 2 hosts. A run with no
   scanned endpoints yet (interrupted before any stage produced rows) shows
   `(no target recorded)` rather than a blank column.

2. Re-run the identical command with `--resume-scan-id <scan_run_id>` added.

Note that an interrupted scan does **not** print its own `scan_run_id` to the console
— `--list-resumable` is the supported way to recover it. The ID is echoed only on the
resumed run, in the `Resuming scan <id>: N stages complete` line.

`--cache` is not required for batch resume — batch resume does NOT require `--cache`.
Per-batch resume state is written on every run that has a `--db-path` set,
independently of the whole-discovery-stage `--cache` / `--cache-ttl-hours` cache. You
can omit `--cache` entirely and batch-level resume still works.

### 13.3 Where the state lives

Each completed batch produces two artifacts:

- A `ScanCheckpoint` row with a synthetic stage name `discovery:batch-N` (no new table,
  no schema change — the existing checkpoint mechanism is reused with a structured
  stage string).
- A JSON payload at `{output_dir}/.cache/discovery-batch-{scan_run_id}-{N}.json`
  holding two things: that batch's discovered open-ports list (`ports`), and the
  per-host "undetermined" advisory records produced by its liveness pre-pass
  (`liveness`). Both are restored when the batch is skipped — see 13.4 for why the
  second one matters to your reported coverage.

### 13.4 Disk usage is proportional to swept host count

Resume state now occupies disk space proportional to the batch count, not a single
file per scan as before. The batch count is `ceil(total_hosts / 1024)`: a /16 (~65,000
hosts) produces roughly 64 batch files; a /12 (~1,048,576 hosts) produces roughly
1,024.

Each batch file holds that batch's open-ports list plus one small advisory record per
non-responsive host — not raw nmap XML/stdout. The advisory records dominate the
footprint on a sparse network, at roughly 190 bytes per non-responsive host: a fully
dark 1024-host batch produces a file of about 190 KB, so a /20 costs well under 1 MB
and a /16 roughly 12 MB in total. Dense networks produce *smaller* files, since a
responsive host generates no advisory record.

Those advisory records are what let a resumed scan report the same coverage as an
uninterrupted one. They are the same "undetermined host" entries that appear in the
scan summary's `Hosts undetermined` count and as `ADVISORY` findings in the report.
Without them cached, a resumed run would silently under-report its own scope by one
batch's worth of hosts for every batch it skipped — the report would look like a
completed smaller scan rather than an interrupted larger one. If you need to reclaim
the space, delete the cache directory rather than individual files (see below); the
cost is a re-probe, never a wrong number.

Batch cache files are read back with a 720-hour (30-day) TTL. After 30 days, a batch
file is treated as expired and ignored on resume — that batch is re-probed instead of
skipped. `{output_dir}/.cache/` can be deleted at any time; the only consequence is
that a subsequent resume re-probes the batches whose cache files were removed. Deleting
it never corrupts or blocks a scan.

### 13.5 Cache files carry the discovered inventory

The per-batch cache files under `{output_dir}/.cache/` contain the discovered
host/port inventory for their batch **and the address of every non-responsive host in
it** — in effect, a full record of which addresses were swept and which answered. They
live in the same `{output_dir}` that already holds the CBOM, the delivered report, and
the SQLite DB. Apply the same handling
(storage, retention, access control) to `{output_dir}/.cache/` that you already apply
to the rest of the output directory — it is not a separate trust tier.

### 13.6 Limitation: resume assumes an unchanged target scope

Batch numbering is a pure ordinal over the expanded target list computed at scan
start. Resume assumes the target scope is unchanged since the original scan. If
CIDRs, include-IPs, or `exclude_ips` are edited between the original run and the
resumed run, batch alignment is **undefined** — the resumed scan may restore the
wrong hosts' results under the wrong batch numbers, silently corrupting the inventory
rather than merely re-probing extra hosts.

**Safe procedure:** if you need to change target scope, start a fresh scan rather than
resuming. This is the same assumption the pre-existing stage-level resume already
makes; batch-level resume does not add a new class of risk, but it does make the
existing one more granular.

### 13.7 Skip/re-probe decision table

| Batch state | Cache file state | Resume behavior |
|---|---|---|
| Completed (checkpoint row exists) | Present and within the 720h TTL | Skipped — no nmap subprocess is spawned for this batch |
| Completed (checkpoint row exists) | Expired (>720h) or deleted | Re-probed — a checkpoint row alone never causes a skip; a live cache hit is also required |
| Failed with a `RuntimeError` | No checkpoint written | Re-attempted on resume; the batch's error endpoint from the failed attempt is still recorded in the scan artifact |
| Completed (checkpoint row exists) | Present, but written before the advisory records were cached | Skipped, and its open ports are restored, but its undetermined-host records are not — that run's reported `Hosts undetermined` will be low by roughly one batch per such file. Start a fresh scan if the coverage figure matters. |

---

## 14. Ticketing Integration

Jira and ServiceNow ticket dispatch (`quirk ticket create`) is configured under
`docs/configuration.md` §"Jira Ticketing" / §"ServiceNow Ticketing" — that is still the reference
for the `ticketing:` config block and CLI usage. This section covers one operator-visible behavior
change from Phase 178.

### 14.1 One-time ticket re-key (v5.18 / IDENT-01)

Finding fingerprints — the dedup key used to decide "have I already opened a ticket for this" —
are now computed from a **normalized** title (`quirk/ticketing/base.py::compute_fingerprint`,
routed through `quirk.compliance.normalize_finding_title`). Before Phase 178, the fingerprint
hashed the raw title text, and one finding family interpolates a changing value into that title:
`"Certificate expiring in {N} day(s)"`, where `N` counts down every day. That meant a still-open
certificate-expiry finding minted a brand-new fingerprint — and therefore a brand-new Jira issue
or ServiceNow incident — on every single scan, instead of being recognized as the same finding it
was yesterday.

**The only affected family is certificate-expiry findings.** No other finding title changed its
fingerprint-relevant classification in this phase.

**What operators will see on the next `quirk ticket create` run:** any certificate-expiry finding
that already has an open ticket will look "new" exactly once, because its normalized fingerprint
no longer matches the fingerprint stored on the existing ticket. Jira stores the fingerprint as a Jira **label**
on the issue (`labels: [fp]`, matched via `JQL labels = "<fp>"`); ServiceNow stores it in the
incident's **`correlation_id`** field (matched via `sysparm_query=correlation_id=<fp>`). Neither
lookup finds the old-fingerprint record, so exactly ONE duplicate ticket is created per affected
finding. After that single miss, the new fingerprint is stable and dedup works normally on every
subsequent run — this is a one-time event, not a recurring duplication.

No migration or tracker readback is performed against already-issued tickets — reading back
existing Jira/ServiceNow state is explicitly out of scope (see `.planning/REQUIREMENTS.md`). If
you want to avoid seeing the duplicate, close the old certificate-expiry ticket manually before
running `quirk ticket create` again; QUIRK will open a fresh one under the new, stable fingerprint.

**This is not a dedup regression.** Two different vulnerable container-image libraries found at
the same host and port still produce two distinct tickets after this change, exactly as before —
fingerprinting deliberately does NOT collapse findings that differ only in which library or
package they name (T-178-01). Only the day-counting cert-expiry title was made fingerprint-stable;
everything else that already deduplicated correctly continues to do so.

## 15. Remediation Tracking Scope (v5.18+ — Phase 179)

Phase 179 changed what a remediation item *is*. Previously, roadmap items were computed fresh on
every scan from live evidence counters and existed only in memory — nothing was persisted, and
progress could only ever be reported as a boolean (an item is either present in the current
roadmap or it isn't). A remediation item is now a stable, kind-derived ID (e.g.
`plaintext-http-exposure`) with its constituent findings recorded explicitly, per scan, in the
database. That is what makes "6 of 8 verified closed" an expressible fact rather than an
approximation — fixing 1 of 8 affected endpoints no longer reads as "nothing happened," and fixing
the 8th no longer makes the item silently vanish with no closure record.

Three things operators should understand about how this tracking behaves:

- **A per-scan scope signature is recorded**, capturing what the scan actually covered — port
  scope, `--profile`, which optional extras were enabled, whether credentials were supplied, and
  which sensors contributed. Closure comparisons are refused outright when two scans' signatures
  don't match, rather than silently comparing scans that covered different ground. A re-engagement
  run with `--profile quick` cannot be misread as having verified — let alone closed — findings
  that only a deeper prior scan actually covered.
- **Probe health is asserted positively, per protocol family, not inferred from the scan exiting
  cleanly.** A scan can exit 0 while a specific probe (SSH, TLS, JWT, etc.) silently produced no
  usable evidence — this is precisely the failure mode a prior integration defect (TRIAGE-176-03)
  demonstrated for SSH. Health is now derived from whether that family actually produced evidence,
  not from the absence of an error.
- **`not_observed` is a real, persisted third state — distinct from both `open` and `closed`.** An
  item this scan did not see evidence for is recorded as `not_observed`, never inferred as
  `closed`. A report reading "9 closed, 4 open, 12 not observed" is telling you something true and
  useful: those 12 were not verified this scan, one way or the other. It does not mean nothing was
  found there — it means the question wasn't answered this run (a narrower port scope, a disabled
  connector, an unreachable host). Treat `not_observed` as "we did not check," never as "there's
  nothing there."

See `docs/configuration.md` §"Remediation Aliases" for the related `remediation_aliases:` config
key, which lets an operator manually declare that two identities across engagements are the same
asset — the human-in-the-loop mechanism this phase uses instead of automated re-scan matching.

### Known limitation — sensor-origin findings are excluded from closure tracking

**Closure tracking is scoped to CLI scans.** Findings pushed from a distributed sensor
(`docs/operators-guide.md` §8, Distributed Sensor Deployment) arrive through a different ingestion
path — `quirk/cli/console_cmd.py::_ingest_envelope` — which records `sensor_id` and `segment` on
the resulting `CryptoEndpoint` row but does **not** set `scan_run_id`. The scope signature that
gates closure comparisons is keyed on `scan_run_id`. A row with no `scan_run_id` therefore has no
scope signature and no way to be evaluated for closure.

**What this means in practice:** in a hybrid or fully distributed deployment, sensor-origin
findings will never appear in remediation burndown or closure figures — not because nothing was
found, and not because of a bug, but because sensor pushes were structurally excluded from this
tracking mechanism by design decision (179-CONTEXT.md, "Sensor-Origin Coverage"). If you run a
distributed sensor fleet and expect to see sensor-discovered findings close out over time, you
will not — closure figures will only ever reflect CLI-scanned findings. This is worth knowing
*before* you plan a distributed engagement around burndown reporting, not after you notice the
number never moves.

**CLI-scanned findings are unaffected** — everything described above in this section applies to
them fully, regardless of whether the deployment also includes sensors elsewhere.

**Why not synthesize a scope signature for sensor pushes?** A sensor envelope is not a scan — its
port scope, `--profile`, and enabled extras were decided on the sensor at push time and are not
reliably recoverable centrally. Fabricating a signature for it would produce something that looks
structurally present but is semantically empty: it would pass the "scope signature exists"
mismatch check without ever having actually evaluated whether the compared scans were comparable.
That is worse than the current gap, because it would silently masquerade as a valid comparison
instead of visibly declining to compare.

A follow-up to revisit this — either by extending scope signatures to a per-sensor keying scheme,
or by permanently accepting the exclusion and surfacing it in reports instead — is tracked in
`.planning/ROADMAP.md` under `## Backlog` → "Remediation Coverage (post-v5.18)".

## 16. Closure Verification (v5.18+ — Phase 180-181)

Phase 179 gave a remediation item a stable identity and a per-scan record. Phase 180 adds the
piece that identity was missing: a machine-observed decision about whether that item is actually
fixed, computed from two consecutive comparable scans rather than asserted by anyone. Phase 181
surfaces that decision to the operator and the client — this section covers where it now appears
and how the dashboard behaves when there is nothing to show.

### Where it surfaces

Closure state and the remediation burndown are now visible on every report surface:

- **CLI markdown, HTML, and DOCX reports** each render a "Remediation Burndown" section, per
  deadline, with a shared advisory caption held byte-identical across all three renderers by a
  test — see `docs/report-interpretation.md` §16 for how to read it with a client.
- **The CBOM** carries a `vulnerabilities` array (CycloneDX VEX), one entry per remediation item,
  with `not_observed` mapped to `in_triage` — never `not_affected`. See
  `docs/report-interpretation.md` §16 for the full state-mapping table.
- **The dashboard** shows closure state directly on the **existing roadmap items** it already
  displays, joined by the item's slug — **there is no new tab.** A closure `Badge` appears in the
  roadmap node detail panel (omitted entirely when no closure state is attached), and a
  "Remediation Burndown" table is rendered beneath the existing roadmap graph.

### Dashboard behavior when closure data is absent

A scan that has no persisted closure data — no prior comparable scan, a freshly initialized
database, or a scan that predates Phase 179 — shows an **explicit "closure state was not computed
for this scan" message**, never a table of zeros and never a burndown row that reads as "0
closed." An operator seeing an empty panel must not report "all clear"; the panel is telling you
closure was not computed, not that nothing needs fixing.

**Any closure lookup failure degrades the panel to empty and is logged — the endpoint never returns a 500.**
The dashboard's `/api/scan/latest` response reuses the same advisory-only
firewall pattern already used for vendor PQC trends and hardware findings: the lookup runs inside
its own try/except, a failure is logged via `logger.exception(...)`, and the response falls back
to an empty/`null` burndown or closure field rather than raising. This means an advisory-surface
failure can never take down the score view or the rest of the roadmap mid-presentation — the worst
case is a missing badge or an empty burndown block, not a broken page.

### The four states

A finding's closure state is always one of exactly four values (`quirk/intelligence/remediation.py`
`ITEM_STATES`):

- **`open`** — the finding was rechecked this scan and is still present.
- **`closed`** — the finding was present in a comparable prior scan and the current scan positively
  rechecked that same host:port with a healthy probe and did not find it there.
- **`not_observed`** — the question was not answered this scan, one way or the other. See the
  troubleshooting list below for the specific reasons this happens.
- **`resurfaced`** — an item that was previously `closed` has come back. It is counted as open for
  reporting purposes, but reported as its own line rather than folded silently into `open`, and its
  closure history is retained rather than discarded.

**Absence alone never closes an item.** A host that stops appearing in a scan — because it was
decommissioned, because the target list shrank, because a segment of the network was unreachable —
is not evidence anything was fixed. Closure requires the current scan to have positively rechecked
that specific host:port and found the finding gone, not merely to have not seen it. This mirrors
the guardrail vulnerability scanners such as Qualys, Tenable, and Orca already apply: a scanner
does not mark a finding closed unless it recheck that exact target.

### Why an item reads `not_observed` — troubleshooting

If a client or colleague asks "why does this say `not_observed` instead of `closed`?", the answer
is always one of:

- **No comparable prior scan exists.** This is the first scan of this estate, or no prior scan's
  scope signature matches closely enough to compare against.
- **The scope signature is missing or mismatched.** Port scope, `--profile`, enabled optional
  extras, credential presence, sensor set, or the target set itself differ between the two scans —
  see `docs/operators-guide.md` §15 for what a scope signature captures. Two scans covering
  different ground are never treated as comparable, no matter how similar the counts look.
  Comparability now also depends on the **target set** — two different estates scanned with the
  same profile are not comparable, even if every other scope dimension matches, which is why the
  target-set digest exists.
- **The relevant probe family was unhealthy.** A specific protocol family (SSH, TLS, JWT, etc.) was
  `no_targets`, `not_run`, or `unhealthy` for the finding's host:port. A scan can exit cleanly while
  one probe family silently produced no usable evidence — probe health is asserted positively per
  family, never inferred from a clean exit.
- **No endpoint was rechecked at that host:port.** The current scan simply did not touch that
  address this run.

Treat `not_observed` as **"we did not verify"**, never as **"nothing was found."** These read
almost identically in a report, and the difference matters: telling a client "12 items came back
clean" when the true state is "we did not check 12 items this run" is the exact misreading this
state exists to prevent.

### Troubleshooting — "the burndown block is empty / says not computed"

This is the same comparability gap as the `not_observed` troubleshooting list above, surfaced at
the whole-scan level instead of the per-item level. Check, in order:

- **No comparable prior scan exists** — this is the first scan of this estate, or nothing prior
  matches closely enough.
- **The scope signature differs** — port scope, `--profile`, enabled optional extras, credential
  presence, sensor set, **or the target set** — the five axes named verbatim in the report's
  refusal statement (e.g. "Closure not computed: scan scope differs from the prior scan.").

The report and dashboard both state the refusal explicitly rather than showing an all-zero table —
if you see the refusal message, the fix is to rerun with a scope that matches the prior scan you
want to compare against, not to look for a hidden toggle.

### There is no closure override

**No flag, config key, or CLI option can mark an item closed.** This is deliberate (CLOSE-01), not
an oversight — an operator under client pressure to "just mark it fixed" has nothing to reach for,
because nothing exists. If a finding needs to be closed, the only path is a rescan that positively
observes it gone under comparable scope.

### `resurfaced`

A `resurfaced` item was `closed` on a prior scan and has now been rechecked and found present
again. It counts toward `open`-style totals (so "how many open items do we have" stays accurate),
but it is reported as its own category — a report reading "2 open + 1 resurfaced" tells you
something "3 open" does not: one of those three was believed fixed and did not hold. The event
history behind a resurfaced item is retained, so a later re-closure is traceable against the full
sequence rather than looking like a first-time fix.

### The EO 14412 deadline catalog

Burndown is computed per named deadline, never as one number. The catalog lives in
`quirk/scanner/pqc_deadlines.py` (`PQC_DEADLINES`) — this guide does not restate the dates as an
independent fact; it points at that module because a client challenging a date needs one source of
truth, not two that can drift apart. As of this writing that catalog carries:

- **Key establishment** — December 31, 2030 (FIPS 203 / ML-KEM), for HVAs and high-impact systems.
- **Digital signatures** — December 31, 2031 (FIPS 186-5 / DSS), for HVAs and high-impact systems.
- **NIST-owned/operated subset** — December 31, 2027, an earlier deadline for a narrower system
  set.

Source: Federal Register Vol. 91 No. 121 (2026-06-25), FR Doc 2026-12909, Executive Order 14412.
The catalog is re-verified on a 90-day cadence against that `source_url`, the same cadence as the
QRAMM and CMVP catalogs described at the top of this file.

**CNSA 2.0 dates are a deliberate, documented omission, not a gap that was missed.**
`media.defense.gov` returns HTTP 403 to non-browser user agents, so no CNSA 2.0 date literal has
been added anywhere in the codebase. Do not fill this in from a secondary source — a
transcription error in a compliance-adjacent date is the exact failure class this catalog exists to
prevent. If CNSA 2.0 dates become genuinely needed, they must be re-sourced directly and added with
the same `source_url` discipline the EO 14412 dates already follow.

### Documented limits

Three things burndown and closure will never do, by design:

- **Sensor-origin findings are excluded from closure tracking.** See §15's "Known limitation"
  above — closure is scoped to CLI scans; findings arriving through the distributed sensor
  ingestion path never carry the scope signature closure comparison requires.
- **`evidence_only` items can never close.** Closure operates per constituent finding fingerprint;
  an item with zero constituent fingerprints has nothing to positively recheck, so it can never
  transition out of `not_observed`.
- **Findings whose only algorithm evidence lives in a JSON blob land in the `unmapped` burndown
  bucket**, not silently outside the count. `compute_burndown` reads only a matched endpoint's
  declared columns (certificate public-key algorithm, certificate signature algorithm, cipher
  suite); it deliberately does not re-implement the CBOM builder's protocol-specific JSON parsing a
  second time, so evidence that only exists in a blob resolves to `unmapped` rather than to a
  fabricated deadline. `unmapped` is reported, never dropped.

> **Client Conversation — Closure:**
> "This report's `not_observed` count is not 'nothing found' — it means we didn't recheck those
> items this run, usually because this scan's scope differed from the prior one, or a probe family
> came back unhealthy. Nothing here can be marked closed by a flag; a finding only closes when we
> positively recheck it and it's gone. And a `resurfaced` item means something we believed fixed
> came back — that's reported separately from ordinary open items so it isn't lost in the count."
