# QU.I.R.K. — Operator's Guide

*(Audience: enterprise administrators deploying and operating QU.I.R.K. on customer
estates. This is the single canonical entry point — read top-to-bottom for a deployment
walkthrough or jump to the section you need. Each section is short by design and links
to a deeper doc where one exists.)*

QU.I.R.K. is dashboard-first and CLI-complete. Start a scan from the dashboard's **New Scan**
page, or run it from the command line against a config file. Both paths run the same scanner:
the dashboard writes a per-job config and launches `run_scan.py` with it. The CLI is the
supported route for automation, sensors and repeat engagements. This guide covers both; §3
starts with the dashboard.

**Prerequisites:**
- Python 3.10+ (CI tests 3.11)
- macOS / Linux host with outbound network reach to scan targets
- (Optional) Docker for the chaos lab smoke test

---

## 1. Install

QU.I.R.K. installs from PyPI as `quirk-scanner`. (The PyPI project named `quirk` is an
unrelated package; do not install it.) Use `pip install quirk-scanner` for the core scanner
(TLS, SSH, JWT, Discovery, Fingerprint), or `pip install 'quirk-scanner[all]'` for a one-shot
install of the optional bundles that are safe to combine. Quote the extras: zsh, the macOS
default shell, treats `[...]` as a glob and fails with `no matches found`. `[all]` leaves out
four extras: `[identity]` (Kerberos), `[hw]` (SNMP, Modbus and BACnet hardware scanning),
`[api]` (OpenAPI spec validation and the active REST fuzzer) and `[dev]` (build tooling).
`[identity]` is excluded because `impacket` depends on `pyOpenSSL`, whose own `cryptography`
requirement can make pip downgrade the `cryptography` package the TLS scanner relies on
(Phase 45-01 D-07). Install `pip install 'quirk-scanner[identity]'` separately, into its own
environment, if you need Kerberos coverage. SAML and DNSSEC need no extra: they run on `lxml`
and `dnspython`, which are core dependencies.

> See also: [`docs/installation.md`](installation.md) for full install reference,
> system requirements, and OS package prerequisites.

---

## 2. Configure

The CLI takes its settings from a YAML config file passed with `--config <path>`. It does not
read `./config.yaml` on its own: run without `--config` and the interactive wizard starts
instead. The dashboard's New Scan page does not build the scan from that file; it generates
a per-job config from the form (§3.1.2 previews it) and launches the scanner with it. Only the
`security.allow_internal_targets` and `security.trusted_targets` policy keys are read from the
server's own config file (`QUIRK_CONFIG_PATH`, default `./config.yaml`). A config file must
contain the `assessment`, `scan` and `output` blocks; `targets`, `connectors`, `intelligence`,
`security`, `report`, `broker_credentials` and `remediation_aliases` are optional. Some
`connectors.enable_*` flags need an optional extra. Enabling one whose extra is missing does
**not** fail the run. Most such connectors (for example Kerberos, database, GCP/Kubernetes/Vault,
AD CS, S/MIME, email and broker) then emit a `missing_extra` advisory finding (Phase 45
INSTALL-02). The `[hw]` connectors (SNMP, Modbus and BACnet) emit no advisory finding.

### 2.0 What a stock install scans out of the box (v5.19 — Phase 184.2)

Running `quirk init` then `quirk --config config.yaml` with no further edits scans more than
"nothing" — five connectors ship **armed but inert**, two ship **actively scanning**, and
everything else ships **off with a stated reason**:

- **Five target-guarded connectors are armed but inert:** `enable_jwt`, `enable_container`,
  `enable_source`, `enable_dnssec`, `enable_saml` all ship `true`, but each short-circuits on an
  empty target list — they do nothing until you populate `jwt_targets`, `container_targets`,
  `source_targets`, `dnssec_targets`, or `saml_targets` respectively.
- **Email and broker connectors (`enable_email`, `enable_broker`) are on, and unlike the five
  above they are NOT inert.** Both probe every host on which port fingerprinting found a TLS candidate port (skipped as `no-eligible-targets` when there is none). Email has no
  dedicated target list; broker now does — **`connectors.broker_targets`** (Phase 190, TRIAGE-06)
  lets you name explicit `host`/`host:port` entries that are probed *in addition to* each broker
  family's hardcoded default ports (`broker_azure_namespaces`/`broker_sqs_regions` similarly
  *add* cloud-broker probes rather than narrowing the host sweep). See
  [`docs/configuration.md`](configuration.md) § "`connectors.broker_targets` — explicit broker
  ports" for syntax and the ADDITIVE-semantics guarantee. This was already true before this
  phase for the base `enable_email`/`enable_broker` toggles: the `standard` profile (the CLI
  default) auto-enables both whenever they are unset, and an explicit `false` has always been
  respected via the `_user_set_fields` mechanism (Phase 72 D-02/WR-11).
- **Everything else ships `false`**, each with an inline reason: credentials required (AWS,
  Azure, GCP, database, S3, Blob, Kubernetes, Vault), an optional extras package required
  (Kerberos, S/MIME, AD CS, SNMP), the connector probes live OT/ICS equipment and needs
  explicit opt-in (Modbus, BACnet), or the key is not a scanner toggle at all (`enable_nmap`, `enable_codesign`, `enable_authenticated_mode`, `enable_recurring_otics`; each is driven by a CLI flag or the scheduler).
- **The default TLS port list widened from 3 ports to 17** — `scan.ports_tls` now matches the
  same `CONSULTING_TLS_PORTS` set the CLI wizard and the dashboard's "Common TLS ports" scope
  already used. This means a stock scan now also TLS-probes ports commonly used by PostgreSQL,
  MySQL, and Vault (5432, 3306, 8200) — at the TLS layer only, independent of whether the
  credentialed `db`/`vault` connectors are enabled.
- **Plaintext-HTTP classification no longer follows `scan.ports_tls` (Phase 186, TRIAGE-176-02).**
  Previously, any plaintext-HTTP finding on a port in `scan.ports_tls` was relabelled `"HTTP on
  TLS-designated port"` — this made every scanned-but-plaintext port look like a TLS
  misconfiguration. Findings are now relabelled only for the well-known TLS port set (443, 8443,
  9443, 10443, 4433, 5001) or ports you explicitly list in the new `scan.tls_designated_ports`
  option. If you relied on the old behavior to flag plaintext HTTP on a non-standard TLS port
  (e.g. 8444), add it to `scan.tls_designated_ports` to preserve that reporting. See
  [`docs/configuration.md`](configuration.md) § "TLS-designated ports override" for details.

**To narrow the out-of-the-box posture for an engagement:** edit `connectors.enable_email` /
`enable_broker` to `false` if you don't want those probed, and edit `scan.ports_tls` directly to
shrink the port list. See [`docs/configuration.md`](configuration.md) § "Connectors Block" for
the full 25-key disposition table (which flag means what, and why it ships the value it does) and
§ "Default TLS port list" for the complete 17-port list.

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
| `quirk-scanner[identity]` | impacket, ldap3 | Kerberos scanner (install separately — not in `[all]`). SAML / DNSSEC need no extra: `lxml` and `dnspython` are core dependencies. **Interacts with the core `sslyze` dependency:** sslyze caps `cryptography<47`. A *clean* install is unaffected — `pip install -e ".[all,identity]"` resolves cryptography 46.0.7 with pyOpenSSL 26.2.0, which accepts it. But an *incremental* `pip install sslyze` into an environment already holding a newer pyOpenSSL (26.4.0 requires `cryptography>=49`) downgrades cryptography and leaves pyOpenSSL unsatisfied, because pip's resolver does not reconsider already-installed distributions. If you see that warning, re-run the full install command to re-resolve the environment and confirm with `pip check`. QUIRK imports pyOpenSSL nowhere, so only impacket-backed Kerberos scanning is affected in the meantime. |
| `quirk-scanner[adcs]` | ldap3 | AD CS and S/MIME scanners (in `[all]`) |
| `quirk-scanner[cloud]` | google-api-python-client, google-auth, azure-mgmt-storage, kubernetes, google-cloud-container, azure-mgmt-containerservice, hvac | GCP, Azure Blob/AKS, Kubernetes and HashiCorp Vault connectors |
| `quirk-scanner[db]` | psycopg2-binary, PyMySQL | Postgres / MySQL TLS-mode scanning (RDS encryption is part of the AWS connector) |
| `quirk-scanner[motion]` | redis, kafka-python (via `[broker]` + `[kafka]`) | Broker scanner (Kafka / Redis). The email scanner and all broker **TLS** probing need no extra — `sslyze` is a core dependency since 5.25.0; earlier releases left it undeclared. |
| `quirk-scanner[hw]` | pysnmp, sysdescrparser, pymodbus, bacpypes3 | SNMP, Modbus and BACnet hardware scanning (not in `[all]`) |
| `quirk-scanner[api]` | openapi-spec-validator, schemathesis | OpenAPI spec scanning and the active REST fuzzer (not in `[all]`) |
| `quirk-scanner[docx]` | python-docx | DOCX report (in `[all]`) |
| `quirk-scanner[notify]` | slack-sdk | Slack notification channel (in `[all]`) |
| `quirk-scanner[tickets]` | jira | Jira ticketing (in `[all]`) |
| `quirk-scanner[all]` | `[dashboard]`, `[cloud]`, `[db]`, `[motion]`, `[adcs]`, `[docx]`, `[notify]`, `[tickets]`, `[cbom]` and `[redis]` | One-shot enterprise install; **excludes** `[identity]`, `[hw]`, `[api]` and `[dev]` |

### 2.3 Vertical editions (v5.6+)

The dashboard can run as an industry-specific edition (currently `general` or
`healthcare`). Set `QUIRK_VERTICAL=healthcare` in the server environment, or add a
top-level `vertical: healthcare` key to the YAML file `QUIRK_CONFIG_PATH` points at (default `./config.yaml`).
The env var wins; unknown values fall back silently to `general`. Verify the active
edition after startup with `curl http://127.0.0.1:8512/api/config` (unauthenticated,
returns `{"vertical": "..."}`).

The healthcare edition adds a "Healthcare Posture" page, sidebar badge, and an
EHR/PACS/portal scan preset; general installs are unchanged. See
[`docs/configuration.md`](configuration.md) § Vertical Editions for the full reference.

> See also: [`docs/configuration.md`](configuration.md) for the full reference of every
> config block and flag, [`docs/sample-config.yaml`](sample-config.yaml) for an
> annotated example.

### 2.4 Dashboard security tail (first released in 5.11.0 — Phase 143)

Three small operator-facing additions shipped in Phase 143:

- **Scan-date badge** — every page that has the dashboard sidebar (all except the sign-in screen
  and the `/print` export page) shows a persistent "Last scan: {date} {time}" (or "No scan yet")
  badge in the sidebar. It shows the newest scan in the database as of page load, not the scan
  picked in the scan selector, so it tells you how current the latest data is, not which scan you
  are viewing. See [`docs/report-interpretation.md`](report-interpretation.md) §11.
- **`security.trusted_targets` scan-consent allowlist** — an opt-in list of exact hosts/IPs and
  CIDR ranges QUIRK is authorized to scan. Empty/absent = allow-all (backward compatible). The
  two entry points check the same inputs. The CLI checks the config's `targets.fqdns`,
  `targets.cidrs`, `targets.include_ips` and every host-naming `connectors.*` field (checked
  whether or not that connector is enabled, and the explicit registry host of a container image
  reference). The dashboard's "New Scan" page checks the form targets and the Connectors-panel
  hosts against the server config's list, and writes that list into the job config so the scan
  enforces it too; an unreadable server config refuses the job with `QRK-DASHBOARD-014`. See
  [`docs/configuration.md`](configuration.md) § `security.trusted_targets`.
- **Windows Authenticode signing (build mechanism, not yet activated)** — the
  `windows-package` release CI job now contains the wiring to Authenticode-sign the Windows
  sensor `.exe` via `signtool.exe`, gated cleanly on the presence of
  `QUIRK_SIGNING_CERT_BASE64`/`QUIRK_SIGNING_CERT_PASSWORD` repo secrets. **No real signing
  certificate exists yet** — until one is provisioned and those secrets are added, released
  Windows binaries remain unsigned (the release notes' "UNSIGNED BINARY NOTICE" is accurate and
  unchanged). The signing step activates automatically, with no code changes, the moment a real
  certificate secret is configured; the release notes' unsigned-binary notice is static text and
  would then need editing.

### 2.4.1 `GET /api/config/effective` — auth-gated, unlike `GET /api/config` (PARITY-01, Phase 192)

The dashboard's pre-existing `GET /api/config` endpoint returns only the active vertical and does
not require the dashboard API token. The new `GET /api/config/effective` endpoint — added for the
New Scan page's Effective config panel (§3.1.2) — **does require the dashboard API token** when
`QUIRK_API_TOKEN` (or `security.api_token` in the server's config) is set, because it accepts caller-supplied form parameters (targets, profile,
etc.). A `security.api_token` is read from the server's config file even when the file holds only a
`security:` section. The endpoint returns the merged, redacted
config those parameters would produce, with two differences from the job a submission writes: its
`output.directory` is a temporary path rather than `output/jobs/<job id>`, and credential values never
reach it. It shows the server config's own `security.allow_internal_targets`, the value a real job takes. The preview receives credentials by name only: the New Scan page sends only the names of the credential fields you have filled, and the
response marks each as `set` or `not set`.
Treat it as an
authenticated preview endpoint, not a public config-read endpoint. Credential fields in its
response are always redacted to `•••• (set)` / `•••• (not set)` regardless of caller — there is no
authenticated mode that returns real credential values.

---

## 3. Scan

There are three ways to start a scan: the dashboard's **New Scan** page (§3.0), the
interactive CLI wizard, and the CLI against a pre-authored config file (§3.0.1). All three run
the same scanner.

### 3.0 Start a scan from the dashboard

1. Start the dashboard with `quirk serve`. It listens on `127.0.0.1:8512`, and it refuses a
   non-loopback `--host` unless a dashboard token is set or `--insecure` is passed. Open
   `http://127.0.0.1:8512` in a browser.
2. Click **New Scan** in the sidebar (route `/scan/new`).
3. Fill in the form, top to bottom: **Targets** (a hostname, IP address, CIDR range or a
   comma-separated list; a newline-separated list is rejected), **Scan Profile** (Quick,
   Standard or Deep), **Calibration** (Strict, Balanced or Lenient), **Port Scope** (Top 1000
   ports, Common TLS ports, All ports or Custom) and the **Enable nmap discovery** checkbox
   (forced on for Top 1000 and All ports). When the active vertical edition has a preset
   (§2.3), an **Apply** button fills the form from it. The collapsed **Connectors** (§3.1.4),
   **Advanced** (§3.1.5) and **Effective config** (§3.1.2) panels sit between these options
   and the button.
4. Click **Run Scan**. The dashboard validates the targets, starts the scan in the background
   and opens the job page (`/scan/job/<job id>`), which shows progress and, once the scan has
   completed, its Scan Coverage chips (§3.1.3). A dashboard-started scan writes its config, log
   and reports under `output/jobs/<job id>/`, relative to the directory `quirk serve` was started
   in. The Executive page's download buttons (§3.1.7) read the latest report set from the output
   directory named by the server's config file instead, so they do not offer the reports of a
   dashboard-started scan.

### 3.0.1 Start a scan from the CLI

Run `quirk` with no arguments to launch the interactive wizard (recommended for first use), or
`quirk --config config.yaml` to run non-interactively against a pre-authored config
(recommended for CI and customer engagements). Targets accept a comma-separated list,
`@filepath` indirection (the file must sit under the current directory),
`--targets-file <path>` (which replaces the config's targets), and CIDR ranges (Phase 47).
Outputs land in `output.directory` (`./quirk-output` in the starter config): an HTML report, a
DOCX report, a PDF (when Playwright's Chromium is installed), `executive-summary-<ts>.md`,
`technical-findings-<ts>.md`, `scorecard-<ts>.md`, `roadmap-<ts>.md`, `findings-<ts>.json`,
`intelligence-<ts>.json`, `run-stats-<ts>.json`, and the CycloneDX CBOM as both
`cbom-<ts>.cdx.json` and `cbom-<ts>.cdx.xml`. The SQLite database is `output.db_path`.

### 3.1 Interpreting Results

Findings carry a severity and, where the finding title joins `COMPLIANCE_MAP`, control
references from PCI-DSS, HIPAA, FIPS 140-3, SOC 2 and ISO 27001; the dashboard classifies each
endpoint's quantum safety as Safe, At Risk, Vulnerable or Unknown. The CBOM lists the
cryptographic assets the scan discovered.

> See also: [`docs/getting-started.md`](getting-started.md) for a zero-to-first-scan
> walkthrough, [`docs/report-interpretation.md`](report-interpretation.md) for
> plain-English finding/score explanations and client-conversation guidance.

### 3.1.1 Reading domain coverage in the headline score (SCORE-06, Phase 188)

As of scoring v2, the headline Quantum-Readiness Score is computed only from the domains a scan
actually assessed — an unassessed domain is excluded, never fabricated as a full 25/25 (see
[`docs/report-interpretation.md`](report-interpretation.md#36-coverage-exclude-and-rescale-and-the-not-computed-state-phase-188-score-06)
for the reader-facing explanation). Operators should know how to tell which domains were
unassessed and what to do about it:

- **Where to look.** Every report surface — CLI markdown, HTML, DOCX, the dashboard executive
  page, and `intelligence-{stamp}.json` — prints a `"N of 6 domains assessed"` disclosure next to
  the score. On the dashboard, an unassessed subscore renders as an em-dash (`—`) in place of its
  gauge rather than a `0`. A scan with zero assessed domains shows an explicit "Readiness score not
  computed" statement instead of a score.
- **What to scan to raise coverage.** The six domains are `hygiene`, `modern_tls`,
  `identity_trust`, `agility_signals`, `data_at_rest`, and `data_in_motion`. `hygiene`,
  `modern_tls` and `agility_signals` are assessed whenever the scan finds at least one assessable
  endpoint; `identity_trust` also needs an observed certificate or a Kerberos, SAML, DNSSEC,
  S/MIME or AD CS endpoint. The two domains most often left unassessed are:
  - `data_at_rest` — needs a database, RDS, S3, Azure Blob, Kubernetes or Vault connector
    scanner (§6) enabled and reachable.
  - `data_in_motion` — needs the email or broker scanners (§6.2) enabled and reachable.
  If a report consistently shows fewer than 6 of 6 domains assessed, check `connectors:` in your
  config for these scanners before treating the score as final.
- **Scores are not comparable across scoring versions.** A lower number after a scoring-version
  upgrade may simply reflect honest exclusion of previously-fabricated points, not a regression —
  do not compare trend lines across a scoring-version boundary. See `CHANGELOG.md`'s 5.25.0
  entry for the full migration decision record.
- **Scoring v3 lowers scores substantially, by design.** Expect a large drop on estates carrying
  open CRITICAL/HIGH findings, and a cap at the top of GOOD on any estate with no observed hybrid
  post-quantum key exchange. Two changes drive it: consequence is now **absolute** rather than
  proportional (a high count of CRITICAL/HIGH findings sets a ceiling irrespective of estate size),
  and "no PQC, no 100" is enforced on a quantum-readiness product. On the project's 31-host
  reference estate the score moved 87 → 18. Whenever a ceiling binds, the score carries a reason
  naming the finding set that capped it and the uncapped figure, so a capped number is never
  mistaken for a computed one.

### 3.1.2 Previewing what a scan will run with — the Effective config panel (PARITY-01, Phase 192)

The New Scan page in the dashboard has a collapsed "Effective config" panel above the Run Scan
button. Expanding it fetches `GET /api/config/effective` with your current form selections
(targets, profile, calibration, nmap toggle, port scope, custom ports, vertical, and any Connectors
or Advanced fields you touched) and previews the **config that submission would run with**, apart
from the output directory §2.4.1 lists — not the server's base config file, and not a static default. It re-fetches automatically as you
change form fields while the panel stays open, and never fetches at all if you leave it collapsed.

Two tabs render the same server response two ways:

- **Grouped** (default) — one table per config section (Targets, Scan, Connectors, Output,
  Assessment, Intelligence, Security), one row per field, with a provenance badge: "Overridden"
  (the job config the form generates sets the value, rather than the built-in default) or
  "Preset: {profile}" (the scan profile's preset applied it, for example "Preset: standard"); a
  field with neither badge is a plain default.
- **Raw YAML** — the identical redacted payload, rendered as indented JSON text under the "Raw
  YAML" tab label (JSON is valid YAML), for operators who want to copy the exact config into a file.

**Credentials never leave the server.** Any credential-bearing field (e.g. `connectors.vault_token`,
`security.api_token`) renders only the literal placeholder text `•••• (set)` or `•••• (not set)` —
never a real value, in either tab, and never inside an editable input. If you ever see a real
credential value in the Raw YAML tab, that is a redaction bypass and should be reported
immediately.

The preview shows `•••• (set)` for a credential field you have filled in on the New Scan form, even
though the form's value never leaves the browser through this panel: the page sends only the
field names, not the values, and the server marks each named credential as set. A field you have
left empty shows the server's own state (its config file or environment).

A failed fetch renders an "Effective config unavailable" notice without blocking scan submission —
the panel is advisory-only and never gates the Run Scan button. If the server's own config file
cannot be read, the preview answers 503 (`DASHBOARD-014`) and shows this notice, and a submission
is refused with the same code until the file is fixed.

### 3.1.3 Scan Coverage chips (OBS-02, Phase 192)

Both the scan-job page (once the job has completed) and the scan-history page (per past
scan, via the row's expand chevron) show a "Scan Coverage" chip pair: `{N} ran` (green) /
`{M} skipped` (neutral outline), reading through `GET /api/scans/{scan_run_id}/coverage` (or the
`GET /api/jobs/{job_id}/coverage` convenience wrapper that resolves a job's scan run). Both endpoints
require the dashboard API token like every other `/api/scans`/`/api/jobs` route.

Expanding "Show detail" reveals one row per scanner phase — ran rows show duration, skipped rows
show the reason and detail exactly as described in `docs/report-interpretation.md` §22's skip-reason
table, colored by severity (`missing-credentials` amber, `failed` red, the other three skip
reasons neutral, `ran` green).

**Scans from before this feature (pre-v5.21)** show an honest two-line notice — "Coverage data not
recorded" / "This scan predates per-phase coverage tracking (pre-v5.21). Re-scan to get full
coverage detail." — never a fabricated `0 ran / 0 skipped` pair. There is no backfill; the only
way to get coverage data for an older scan is to re-scan it.

### 3.1.4 Connectors panel — enabling connectors and supplying credentials from the dashboard (PARITY-02/PARITY-03, Phase 193; PARITY-05/PARITY-06, Phase 197)

The New Scan page carries a "Connectors" panel above the Effective config panel (§3.1.2). Expanding
it (lazy-fetched on first expand only) loads `GET /api/connectors/availability` and renders all 25
connector toggles grouped into six fixed-order categories: Identity, Cloud, Database, Email &
Broker, OT/ICS, and Source & API — matching the CLI's `connectors.enable_*` surface field-for-field,
not a dashboard-only subset.

**Unavailable connectors are shown, never hidden.** A connector whose required optional extra is not
installed on the server appears as a disabled toggle with its reason always visible, followed by
the server's install hint where one is mapped to the connector — no hover required. (The hint text
currently spells the package `quirk`; the PyPI package is `quirk-scanner`, so install
`'quirk-scanner[<extra>]'`.) This is advisory only: even if
you could somehow force the toggle on, submitting a job that would run an unavailable connector is
rejected server-side with an HTTP 422 that names the connector and the reason, including when the
request bypasses the dashboard entirely and calls the job-creation API directly. The disabled switch
is a convenience that saves you a failed submission; the actual guarantee is server-enforced.

**Credential entry.** Toggling on a connector that needs a credential (e.g. AD CS, PostgreSQL/MySQL
database scanning, SNMP community string, broker or SNMPv3 credentials for the default host)
reveals a masked credential input. Every credential field is:

- **masked** as you type, like a password field;
- **never saved** — the value is used only for that one scan submission, is not written to the job's
  stored config, and does not persist across page reloads;
- **empty again after submission** — you must re-enter it on every scan you submit, by design.

Cloud connectors (AWS, Azure, GCP) show an ambient-credentials note instead of a field — they use
your environment's or instance's own credential chain (IAM role, service principal, application
default credentials) and have no dashboard-fillable secret.

**Enabling a connector with no credential supplied is allowed, not blocked.** Submission succeeds
rather than the job being rejected. Two checks run before launch, and both only warn. The panel
shows a non-blocking amber note beneath a connector that is enabled with every credential field
blank. At submit time the server also returns blank-credential warnings for AD CS, Database and
SNMP (not Vault or Broker), and the job page repeats them. Neither warning stops you from submitting.
Once the scan is running, the Vault phase is the only one that skips for a missing credential: with
Vault enabled, a Vault address set, and neither `vault_token` nor a `VAULT_TOKEN` environment
variable, the scan records a `missing-credentials` skip for that phase in its Scan Coverage
disclosure (see `docs/report-interpretation.md` §22). Other credentialed connectors run without a
credential and report their own errors.

**`GET /api/connectors/availability`** is the auth-gated endpoint the panel reads. Once a dashboard
API token is configured it requires that token, like every `/api/*` route except `/api/health` and
`/api/config` (with no token configured, it answers without credentials), re-probes
every connector on each call (the response is not cached; connectors that gate on a scanner module's
import-time flag, such as GCP, Kubernetes and Vault, only notice a package you just installed after
`quirk serve` restarts), and returns each connector's `available` flag, `reason` (when unavailable),
and `install_hint`. There is no `docs/api-reference.md` yet; this section is the interim
documentation for that endpoint.

**Setting connector targets and endpoints (PARITY-05/PARITY-06, Phase 197).** Toggling on a
connector that has target-list, endpoint, or identifier fields reveals them beneath its toggle —
in the same place a credential input would render, stacked below it when both are present. These
fields render **only when the connector is both available and ON**, so an OFF connector shows none
of them.

- **List fields** (e.g. "JWT Targets", "Container Targets", "GKE Clusters") are one free-text
  `<textarea>`, comma- or newline-separated (unlike the main scan-level Targets field, which is
  comma-separated only). Clearing a list field back to blank **deletes the key from the submission**
  rather than sending an empty list — this delta-only semantics means an untouched form produces the
  exact same submit body and Effective Config query string as before this phase (D-08).
- **GKE/AKS clusters** use a compact pairlist syntax instead of plain hostnames:
  `name@location` for GKE (e.g. `prod-cluster-1@us-east1`), `name@resource-group` for AKS (e.g.
  `prod-aks@rg-prod`). An entry missing the `@` separator is dropped from the submitted list and
  surfaced with a visible amber "N entries are missing the required name@location format" count
  — it is never silently discarded and never silently submitted half-formed.
- **The amber "enabled with no targets configured" hint** appears when a connector with one or
  more list-typed fields is ON and every one of those fields is blank. It reads: "{Connector
  label} is enabled but has no targets configured. The scan will run but this connector's list is
  empty, so it has nothing to check. Add targets above, or submit anyway." This is the dashboard
  surfacing of the same "target-guarded, inert until populated" behavior documented in the
  `requires-targets` reason tag above (e.g. `enable_jwt` shipping `true` but doing nothing until
  `jwt_targets` is set) — toggling one of these connectors on alone is no longer silently a no-op,
  because the panel now tells you it needs targets.
- **`k8s_kubeconfig` is a server-side path, not a file upload.** Its helper text reads: "Path to a
  kubeconfig file readable by the QU.I.R.K. server process. Not a file upload — enter the
  server-side path." Whatever you type must already exist and be readable on the machine running
  `quirk serve`, not your own workstation.
- **`vault_tls_verify`** renders as a pre-checked Switch (the config default is `true`) — you must
  explicitly uncheck it to disable TLS verification for the Vault connector; the field is never
  silently defaulted off.
- **Identifier fields are never masked.** `adcs_user`, `pg_scanner_user`, and `mysql_scanner_user`
  are plain, visible text inputs — unlike the masked credential fields above, these are
  identifiers that land in the job's stored `config.yaml` in cleartext by design (D-04); only the
  matching password/token fields are masked and non-persisted.
- **A field you have touched shows a small accent-coloured "Set" badge (teal in 5.25.0, violet from
  5.27.0)** next to its label — the same visual language as the connector-level "Set" badge,
  now also available per-field.
- **Rejected values return a 422 naming the field**, at both submit and the Effective Config
  preview — e.g. an out-of-range timeout or a malformed cluster entry. At submit, an unavailable
  connector is rejected with a "Scan rejected: " banner that names the connector and the reason;
  a malformed value is rejected with an inline error that starts "Value error, ", such as
  `'smime_timeout' must be between 1 and 300`, `Unknown connector key(s): {key}` for a typo'd field
  name, or `'{key}' is not a recognized connector overlay field (must be a known enable_* toggle or
  one of the supported connector detail fields)` for a real-but-out-of-scope field like a secret.
  The preview returns the same 422 for the same values, but its panel shows only the generic
  "Effective config unavailable" notice. Submit and preview share one validator, so they agree on
  every accept/reject decision (PARITY-06).

See [`docs/configuration.md`](configuration.md#connector-detail-fields-settable-from-the-dashboard-parity-0506-phase-197)
for the full 37-field reference (types, defaults, bounds, gating flags).

### 3.1.5 Advanced scan fields — TLS ports, enumeration depth, timeouts, retry, concurrency, data classification (PARITY-04, Phase 194; PARITY-08/09, Phase 198)

The New Scan page carries an "Advanced" section directly below the Connectors panel (§3.1.4) and
above the Effective config preview (§3.1.2). **It is collapsed by default** — clicking the
"Advanced" label with the chevron expands it; nothing inside is fetched or evaluated until you
open it. It remains a single panel — Phase 198 added two new field groups inside it, not a second
panel.

Inside, the panel exposes 27 controls, in these groups:

- **TLS Ports** — a free-text comma-separated port/range list (e.g. `443,8443,9000-9010`) that
  overrides `scan.ports_tls` for this scan only.
- **TLS Enumeration Mode** — a Fast/Deep dropdown. There is no "Off" option; see
  [`docs/configuration.md`](configuration.md#advanced-scan-fields-reference-parity-04-phase-194-parity-0809-phase-198)
  for why (D-19).
- **Send SNI during TLS probes** — a switch controlling `scan.include_sni`.
- **Timeouts & Retry** — the original default/TLS/SSH timeout fields (seconds) and retry count,
  plus two new fields: **Backoff base (seconds)** and **Backoff max (seconds)**, both accepting
  decimals. Submitting a base greater than max returns a 422 naming both fields. The retry count
  and both backoff fields are validated and written to the job config, but no scanner reads them
  yet, so they currently change nothing.
- **Per-Scanner Timeouts** — a new compact grid of 11 short-labeled numeric fields (Fingerprint,
  JWT, Container, Source, DNSSEC, SAML, Kerberos, Vault, DB Connect, Broker, Email), each
  overriding that scanner's individual timeout (the DNSSEC, SAML and Kerberos fields are accepted
  but those three scanners do not read them yet, so they currently change nothing). Accepted range
  is 1-600 seconds — wider than the three original timeout fields' 1-300 bound; see D-11 in the
  configuration reference for why the bounds intentionally differ.
- **Concurrency** — a new group of 5 worker-pool-size fields (Scan, Fingerprint, TLS, SSH, Motion
  concurrency), 1-500 each. Motion concurrency is the shared worker pool for email and broker
  connector scanning.
- **TLS-Designated Ports** — a second port/range field beside TLS Ports, overriding
  `scan.tls_designated_ports`: a plaintext HTTP service found on a port listed here is reported
  as the HIGH "HTTP on TLS-designated port" finding, in addition to the well-known TLS ports. Same
  comma-separated format and inline format validation as TLS Ports.
- **Data Classification** — a Public/Internal/Confidential/Regulated dropdown controlling
  `assessment.data_classification`; see D-21 in the configuration reference for why there is no
  fifth option.

No control exists for `scan.openapi_spec_path` or either hardware retention-days field — these are
recorded, intentional gaps (D-04); see the configuration reference for why.

**Every control here is advisory client-side only; the server's 422 response is authoritative.**
The Input field for TLS Ports shows an amber hint if you type something that doesn't look like a
port/range list, but that hint is a courtesy — the actual validation happens server-side when you
submit, and a rejected value returns a full-width 422 banner naming the offending field.

**While the Effective Config preview is expanded, every edit updates it live.** A value you set
appears badged "Overridden" to distinguish it from a built-in default or a scan-profile preset
(§3.1.2); clearing a field removes the override, and a value the server rejects turns the panel
into the "Effective config unavailable" notice. The Advanced panel does not share the
Connectors panel's precedence rule: an explicit connector toggle always beats the scan profile, but
a scan value that equals the profile's baseline default (for example `fingerprint_concurrency:
200` under the quick profile) is replaced by the profile. See "Dashboard form vs. presets
precedence" in [`docs/configuration.md`](configuration.md#dashboard-form-vs-presets-precedence)
for the full mechanism (delta-only writes, `_user_set_fields`, overlay-merged-last).

### 3.1.6 Exposure Map tab — attack-path visualization (MAP-02, Phase 195)

The dashboard sidebar carries an "Exposure Map" nav entry, opening a read-only
`/exposure-map` tab (no write actions, auth-gated like every other dashboard tab). It
renders a node/edge graph of verified-only relationships between scanned endpoints, sourced
exclusively from `GET /api/exposure-map`, with no client-side data fabrication — see
`docs/report-interpretation.md` §23 for the full client-facing explanation of what the graph shows
and how to read an edge's evidence tooltip.

Two things operators should know that are specific to how this tab behaves, not what it means to a
client:

- **A zero-edge graph is an honest, expected result, not a failure.** Most scans will not populate
  any edge type (shared SPKI fingerprints, confirmed hardware crypto-bridge chains, or a shared
  certificate authority) unless the target environment actually has that condition. Seeing the
  "No path data available" empty state after a scan completes normally does not indicate anything
  went wrong with the scan or the tab.
- **The tab is read-only.** There is no "declare a reachability path" or "mark crown jewel"
  action anywhere in the UI. Crown jewels are declared in the config file as
  `assessment.crown_jewels` (hosts, IPs or FQDNs) and are highlighted on the map; everything else
  on this tab is derived at read time from existing scan data, so there is nothing else to
  configure or maintain for it.

### 3.1.7 Report deliverable downloads (DELIV-01/DELIV-02, Phase 209, first released in 5.25.0)

The Executive page's header row carries a five-format download button group — HTML, PDF, DOCX,
CBOM (JSON), CBOM (XML) — beside the pre-existing Export PDF button. It is backed by two
auth-gated endpoints under `quirk/dashboard/api/routes/reports.py`. See
`docs/report-interpretation.md` §26 for what each format contains and the difference between these
downloads and the Export PDF button; this section documents the endpoints themselves.

**`GET /api/reports/latest/manifest`** — returns every format's availability, never empty and
never 404/500:

```json
{
  "scan_time": "2026-09-14T04:22:13.439767+00:00",
  "stamp": "20260914-041322",
  "formats": {
    "html":      {"available": true,  "reason": null},
    "pdf":       {"available": true,  "reason": null},
    "docx":      {"available": false, "reason": "DOCX requires the optional extra: ..."},
    "cbom-json": {"available": true,  "reason": null},
    "cbom-xml":  {"available": true,  "reason": null}
  }
}
```

(The real `docx` reason ends with an install hint that currently spells the package `quirk`; the
PyPI package is `quirk-scanner`, so install `'quirk-scanner[docx]'`.) An unreadable config or a
missing output directory degrades to every format reporting `available:
false` with reason `"No scan has run yet."` rather than raising an error — the same
fail-to-safe-empty-value approach the Exposure Map's crown-jewel loader takes
(`quirk/dashboard/api/routes/exposure_map.py`).

**`GET /api/reports/latest/{format}`** — downloads one artifact. `{format}` accepts exactly five
values: `html`, `pdf`, `docx`, `cbom-json`, `cbom-xml`, returning `text/html`,
`application/pdf`, the DOCX OOXML media type, and `application/json`/`application/xml`
respectively. **Any other value returns 404, by design** — the route never accepts a filename or
path fragment from the client; it resolves the on-disk filename itself from a fixed
format-to-template map, so an unlisted or malformed value is a routing miss, not a validation
error to work around. There is no way to request an older scan's artifacts through this route (see
below).

**Auth is required once a dashboard API token is configured, same as every other dashboard API
route except `/api/health` and `/api/config`** (see `docs/configuration.md` § Dashboard
Authentication) — a Bearer token or `X-API-Key` header. With a token configured, a plain browser
navigation to the URL, or a naive `curl` without the header, returns `401` — and a saved `401`
response body looks exactly like a corrupt download. With no token configured (which `quirk serve`
allows on a loopback bind), these routes, like the rest of the dashboard API except
`/api/sensor/push`, answer without credentials. The correct
invocation:

```bash
curl -H "Authorization: Bearer $QUIRK_API_TOKEN" \
  -o report.pdf \
  "http://127.0.0.1:8512/api/reports/latest/pdf"
```

**Latest-scan-only, and why.** Both endpoints resolve to the newest `run-stats-<stamp>.json` group
in the output directory named by the server's config file (`QUIRK_CONFIG_PATH`, default
`./config.yaml`). If that directory has no `run-stats-*.json` file, they fall back to the newest
`report-<stamp>.html` group and report `scan_time` as `null`. There is no scan-id or filename parameter. The report artifacts are stamped with
the moment `write_reports()` rendered them, not with `scan_run_id` (the scan's own start time); on
a long scan those two instants can differ by the scan's full duration. `run-stats-<stamp>.json`
records `started_utc`, which equals the scan's `scan_run_id`, but these routes never read it, so
serving "the report for scan X" would need a route built on that field.

**Score parity across the two pipelines (Phase 210 XSURF-01..04, Phase 211 legacy-TLS/plaintext-HTTP
fix).** These download endpoints and the Export PDF button read different artifacts (see
`docs/report-interpretation.md` §26 for the full account). For one persisted scan the report
pipeline and the dashboard pipeline are asserted to agree on the **headline score**, the
**CRITICAL finding count** and the **certificate count**
(`tests/test_cross_surface_parity.py`), and on the Modern TLS subscore for the legacy-TLS and
plaintext-HTTP vocabulary (`tests/test_evidence_finding_vocabulary_parity.py`).

**A scoring input changed, which matters if you compare an old scan's score to a new one.** The
"Legacy TLS versions present" Modern TLS contributor is no longer derived from the count of ALL
LOW-severity findings (a proxy any newly-added LOW-severity finding class could silently inflate);
it is now derived from which endpoints actually accept TLS 1.0/1.1. **If you re-run an older scan
and its Modern TLS subscore moves relative to what was reported before this change, that is
expected and correct** — not a regression.

**A known finding-vocabulary gap remains.** The finding title `"HTTP on TLS-designated port"` has no
dashboard-side emission site and cannot be bridged the way the two fixed legs above were, so a
report-side scan that finds a plaintext-HTTP service on a TLS-designated port will show a
Hygiene-category score the dashboard pipeline cannot reproduce. Tracked at
`.planning/todos/pending/211-http-on-tls-designated-port-has-no-dashboard-equivalent.md`.

This agreement is regression-gated for a scan scored with the default calibration, not a guarantee
the two pipelines can never diverge. If an operator observes the **headline score, a subscore, the
CRITICAL count, or the certificate count** differing between a downloaded report and the
dashboard's live view for the same scan, check first for the known causes of a score difference:
the report contains an `"HTTP on TLS-designated port"` finding; the scan includes Kerberos or DNSSEC
rows, whose findings only the dashboard derives (the report pipeline evaluates SAML identity rows
but not Kerberos or DNSSEC); the scan has legacy-TLS or weak-cipher findings, which the dashboard
rates HIGH where the report rates them lower or not at all (tracked under 999.132); the config sets
`intelligence.calibration_overrides`, which the report applies and the dashboard does not; or the
scan is an older one, because the dashboard's Executive view scores every scan, including an older
one opened by scan id, with the profile recorded in the newest intelligence file in the output
directory. Other dashboard pages score differently: Scan History uses each dashboard job's own
calibration (`balanced` for a CLI-launched scan), and Compare and Trends score with the default
`balanced` profile. Any other divergence is a defect to file.

### 3.2 Active REST fuzzing (`--fuzz`) — interactive-only by design

`--fuzz` enables active REST crypto-posture probing against discovered OpenAPI endpoints. It
requires an OpenAPI spec (`--openapi-spec`) and the `[api]` extra (see
[`docs/configuration.md`](configuration.md#rest-fuzzing-active-crypto-posture-probes) for the full
flag reference and guardrail table). Three things every operator scheduling QU.I.R.K. runs needs
to know before wiring `--fuzz` into automation:

- **`--fuzz` requires an interactive terminal.** If stdin is not a TTY — piped input, a
  CI/CD job, a cron job, any headless invocation — the scanner refuses to run fuzzing at
  all. It prints coded error `FUZZ-001` and **exits non-zero (exit 2)**, and it does this
  before any scan work begins. This is deliberate, not a bug: an unattended job must
  never be able to authorize active probing of a client's live API on its own. If you see
  a cron or CI run fail with `FUZZ-001`, that is the gate working as intended — drop
  `--fuzz` from unattended/scheduled invocations, or run it manually from an interactive
  session instead.
- **A non-interactive `--fuzz` is refused, not skipped.** Releases up to 5.15.0 let a
  non-interactive `--fuzz` invocation complete with exit code 0 and fuzzing disabled, with only a
  stderr line saying so. Since 5.18.0 a non-interactive run refuses to start (`FUZZ-001`, exit 2).
  In an interactive session the scan does start, and fuzzing still needs something to fuzz: with
  no `--openapi-spec` (or no OpenAPI endpoints discovered) the fuzz phase is skipped with no console
  message and the scan exits 0. The skip is recorded only as a `no-eligible-targets` entry in the
  scan's Scan Coverage disclosure. Answering the `CONFIRM` prompt with anything else also skips
  fuzzing while the rest of the scan continues.
- **`--fuzz-budget` has a hard ceiling, and values above it are rejected, not clamped.** The
  default is 50 requests; with `--fuzz`, values above the hard ceiling documented in
  [`docs/configuration.md`](configuration.md#rest-fuzzing-active-crypto-posture-probes)
  are rejected up front with coded error `FUZZ-002` and exit 2 — the scan does not
  silently reduce an over-budget request down to the ceiling and proceed. There is no lower
  bound check: `0` or a negative value passes the budget check, and the fuzzer then dispatches no
  budgeted probe requests (with `--fuzz-jwt-alg-confusion` it can still fetch the target's JWKS
  once, which is not counted against the budget).

See [`docs/error-codes.md`](error-codes.md) for the full `FUZZ` error-domain cause/fix
text for `FUZZ-001` and `FUZZ-002`.

### 3.3 Report Branding, Templates, and Profiles (Phase 200, first released in 5.25.0 — RPT-01..RPT-04)

Reports can carry a client's own branding (cover logo, client/engagement identity text), an
operator-authored template override directory, and a named, reusable "report profile" that
bundles both. See [`docs/configuration.md`](configuration.md#report-block-phase-200-v525--rpt-01rpt-02rpt-03rpt-04)
for the full `report:` config key reference.

#### Three similarly-named flags — do not confuse them

QU.I.R.K. has three separate `--*profile` concepts. They are unrelated to each other and each
controls a different axis of behavior:

| Flag / config key | Controls | Values |
|---|---|---|
| `--profile` (CLI) / preset applied by `apply_profile`| **Scan** behavior — timeouts, concurrency, TLS enumeration depth, and whether email/broker scanning runs when the config leaves them unset | `quick` / `standard` / `deep` |
| `--score-profile` (CLI) / `intelligence.profile` | **Scoring calibration** — how heavily the agility, identity, data-at-rest and data-in-motion penalties are weighted (x0.7 lenient, x1.0 balanced, x1.4 strict) | `lenient` / `balanced` / `strict` |
| `--report-profile` (CLI) / `report.profile` | **Report branding/templates** — which saved branding+template bundle to apply to this run's deliverables | any saved profile name |

The three settings do not overlap: `--profile deep` does not change the scoring calibration or
branding; `--score-profile strict` does not affect timeouts or branding; `--report-profile housestyle`
does not affect timeouts or scoring. The scan profile can still move the score indirectly: a deeper
TLS enumeration, or the email and broker phases `standard`/`deep` turn on, can find more to score.

#### Saving and applying a report profile

```bash
# Save the report: block of an existing config as a named, reusable profile
quirk report profile save housestyle --config /path/to/config.yaml

# List saved profiles
quirk report profile list

# Apply a saved profile to a scan run (selects it by name; does not require --config to carry a report: block)
quirk --config config.yaml --report-profile housestyle
```

Saved profiles live at `~/.quirk/report_profiles/<name>.yaml`, redirectable via the
`QUIRK_PROFILES_DIR` environment variable (useful for CI, containerized runs, or per-client profile
directories). `quirk report profile save` overwrites an existing profile of the same name and says
so explicitly on stdout rather than failing or silently overwriting.

**Precedence — one unambiguous rule:** a value set explicitly in the engagement's own `config.yaml`
always beats the same field coming from an applied report profile. A profile only *fills in* fields
the engagement config left unset; it can never override an explicit value. Selecting *which*
profile to apply follows the same CLI-over-config precedent as `--profile`: `--report-profile` on
the command line wins over a config-declared `report.profile` for which profile loads — but the
loaded profile's *values* still lose to any explicit config field regardless of how the profile was
selected.

#### Report template overrides — the honest security posture

`report.template_dir` lets an operator override the packaged Jinja2 report templates with their
own `.j2` files (the operator's directory is searched first; the packaged template is the fallback
for anything not present there). Templates render inside a **sandboxed Jinja2 environment**
(`SandboxedEnvironment`) unconditionally — there is no config flag to disable the sandbox, and no
second, "trusted" template environment exists anywhere in the codebase.

State the division of responsibility plainly, because it is easy to misread as one guarantee when
it is really three:

- **The sandbox protects the HOST.** `SandboxedEnvironment` blocks Server-Side Template Injection
  (SSTI) payloads that try to reach Python internals (`__class__`, `__globals__`, attribute-chain
  escapes) from breaking out to the machine running QU.I.R.K. This holds even for a hostile or
  compromised override template.
- **Autoescape protects against scan-data XSS in the rendered HTML.** Scan-derived values (host
  names, finding titles, certificate subjects) are escaped by default so they cannot inject
  executable markup into the report.
- **The `| sanitize` filter is a second, narrower layer used on branding and free-text fields
  specifically.** If you write a custom override template and remove `| sanitize` from a field that
  had it, you are **weakening scanner-data XSS hardening for your own report** — the sandbox still
  protects the host, but the rendered HTML you hand to a client can carry unsanitized scan-derived
  text. This is a real, honest tradeoff, not a theoretical one: do not strip `| sanitize` from an
  override template unless you understand and accept that consequence for that specific field.

### 3.4 Score-Lift Badges and the Projected Score on the Remediation Roadmap (Phase 201, LIFT-01..LIFT-05)

A roadmap item whose resolution would raise the score carries a `(+N pts)` badge — the number of
readiness-score points this scan would gain if that one item were resolved, computed by a real second call into the
scoring engine over a copy of the scan's evidence, never a fixed points table. Items whose
resolution changes no scoring input (the three process/governance items, "Increase TLS
enumeration coverage" and "Standardize mTLS lifecycle operations") show no badge at all, and neither
does a modelable item whose rescore gains nothing. A badge is shown only for a positive gain, never
as `0 pts`. A separate "Projected score if all items resolved:
{N}" figure is one additional independent rescore with everything resolved at once — it is
usually smaller than summing the individual badges, because the score's six domain subscores are
each capped at 25 and can only give up so much headroom. Neither number ever changes the
readiness score you see today; every surface that shows the projected number also shows, verbatim:
"Advisory — this projection is a simulation and does not affect the readiness score." See
`docs/report-interpretation.md` §7.1 for the full explanation, the exact list of unmodelable item
kinds, and worked examples across all report surfaces.

**Where it appears:** the CLI roadmap markdown and scorecard, the HTML/PDF and DOCX reports, and
the dashboard roadmap page — a per-item badge in the node detail panel, and a "Projected Score"
card directly above the Remediation Burndown card. The dashboard omits the card entirely (not a
placeholder) when the scan is unassessed or the projection could not be computed.

**The console "Migration Waves" table's second column changed meaning in the same phase
(BACK-51 / LIFT-04):** it now counts roadmap *items* per NOW/NEXT/LATER phase — labeled "Items" —
instead of raw findings bucketed by severity. This makes the console table agree with every other
roadmap surface, which already used the same categorization. A report generated before Phase 201
may show different NOW/NEXT/LATER counts than one generated after it for the same findings; that
is the intended effect of unifying the two previously-independent categorization systems into one.

---

## 4. Validation / Smoke Test

Before pointing QU.I.R.K. at a production estate, run it against the chaos lab in the
repository (`quantum-chaos-enterprise-lab/`; it is not part of the PyPI package) to confirm the
install is healthy and findings render correctly. The lab spins up
intentionally weak TLS, SSH, JWT, container, broker, and email targets via Docker
Compose profiles, with an oracle of expected findings per profile.

> See also: [`docs/chaos-lab.md`](chaos-lab.md).

---

## 5. Troubleshooting

### 5.0 Looking up an error code

Scanner advisories and failures carry a bracketed code such as `[QRK-INSTALL-001]` or
`[QRK-CONFIG-001]`. To see the full catalogue — every code, its meaning, and its
remediation — without leaving the terminal:

```bash
quirk errors                 # human-readable table
quirk errors --dump-md       # the Markdown source of docs/error-codes.md
```

In a source checkout, `docs/error-codes.md` is generated from this command, and a CI gate
asserts the committed file byte-matches the live output — so a drift between the catalogue
and the code fails CI on the next pull request or push to `main`. If you are reading a code that is not in the file, regenerate rather than
hand-editing:

```bash
quirk errors --dump-md > docs/error-codes.md
```

### 5.1 Scan failures

- **Permission denied on a target** — confirm the QU.I.R.K. host can reach the port;
  check firewall and security-group rules. TCP-connect failures surface as an INFO
  "Informational protocol observation" finding whose detail reads `CLOSED: REFUSED`,
  `CLOSED: TIMEOUT` or `CLOSED: UNREACHABLE`, rather than crashing the scan.
- **Timeouts** — adjust the relevant `scan.timeouts.<scanner>_seconds` knob
  (`tls_seconds`, `ssh_seconds`, `jwt_seconds`, etc.; the `dnssec_seconds`, `saml_seconds` and
  `kerberos_seconds` knobs are not read yet). See
  [`docs/timeout-retry-audit.md`](timeout-retry-audit.md) for per-scanner defaults.
- **`missing_extra` advisory finding** — install the named extra
  (e.g. `pip install 'quirk-scanner[identity]'` for Kerberos). Phase 45 INSTALL-02 surfaces
  these instead of silently skipping the scanner. As of 5.18.0 (Phase 173), this signal — a
  `[QRK-INSTALL-001]` stderr advisory plus a `scan_error_category=missing_extra` finding — is
  emitted consistently across scanner families: the broker connector now checks all three of its
  optional dependencies (`sslyze`, `kafka-python`, `redis`), not just `sslyze`, and the smime/adcs
  connectors emit the signal for the first time (both previously failed silently with only a bare
  log line). If you enable a connector and see this advisory, install the named extra
  (`pip install 'quirk-scanner[motion]'` for the broker's Kafka/Redis clients,
  `'quirk-scanner[adcs]'` for smime/adcs; a missing `sslyze` means a broken install —
  it is a core dependency, so reinstall `quirk-scanner` rather than adding an extra)
  or leave the connector disabled.
- **`[QRK-CONFIG-001]` on startup — invalid `scan.ports_tls` / `scan.tls_designated_ports`
  entry** — as of 5.21.0 (Phase 189, TRIAGE-04), a port-list value that isn't a valid TCP port is
  now rejected loudly at config-load time instead of being silently ignored: a non-numeric value
  (e.g. a typo like `"84a4"`), a non-integral number such as `8444.5`, or a number outside
  1-65535 (`0`, `-1`, `70000`). Fix the offending entry named in the error message. A quoted
  digit-string such as `"8444"` is valid and behaves identically to a bare `8444`.
  If you have an older config with a quoted port value that
  never triggered this error before upgrading, re-check that scan's report: prior to Phase 189
  such a value silently never matched the TLS-designation override, so its effective scope may
  have been narrower than intended. See [`docs/configuration.md`](configuration.md) §
  "Port-list value coercion and `QRK-CONFIG-001`" for details.
- **A skipped scan phase leaves no `run_stats.timings_sec` key** — as of 5.18.0 (Phase 173), a
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

- **`output.db_path` permission error** — confirm the directory is writable. The key has no
  built-in default; the starter config sets `./quirk-output/quirk.db`.
- **Migrations** — schema migrations run automatically at start-up and are additive
  (`_ensure_columns` and `_ensure_*_table` helpers in `quirk/db.py`; one QRAMM table is rebuilt
  once to add a foreign key); deleting the database file is safe but loses scan history.
- **CBOM file generation** — every scan that reaches the reporting stage writes
  `cbom-<ts>.cdx.json` and `cbom-<ts>.cdx.xml` (a `--check-in` re-probe writes neither). The JSON
  file is validated against the CycloneDX 1.6 schema as it is written; a validation failure adds a
  coverage-gap advisory row instead of stopping the scan.
  The XML file is not validated by the scanner.
- **PDF render failure** — install `'quirk-scanner[dashboard]'` (which pulls Playwright) and run
  `playwright install chromium` once on the host.

### 5.3 Dashboard

- **Vite build errors** — only relevant when rebuilding the React SPA from source; the
  published wheel ships a built bundle at `quirk/dashboard/static/`.
- **Stale Vite cache** — delete `node_modules/.vite` under `src/dashboard/` and rebuild.
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
- **`quirk serve` exits at start-up with `Multiple QU.I.R.K. DBs found` — check for multiple
  candidate DBs.** `_default_db_path()` (`quirk/dashboard/api/deps.py`) checks, in order,
  `QUIRK_DB_PATH`, then whether more than one of `./quirk.db`, `./output/quirk.db`,
  `./quirk-output/quirk.db` exists. If exactly one exists it is used, and if none exists the
  dashboard falls back to `./quirk-output/quirk.db`. If **more than one** of those three paths is
  present, creating the app raises `ValueError: Multiple QU.I.R.K. DBs found at [...]; set
  QUIRK_DB_PATH explicitly`, so `quirk serve` prints that traceback and exits with status 1
  instead of starting. Fix: set `QUIRK_DB_PATH=<path-to-the-db-you-want>` before running
  `quirk serve` to disambiguate explicitly. Also worth checking: a stray 0-byte `quirk.db` left
  over from an earlier run in the working directory counts toward this conflict even though it
  holds no data — delete it if it isn't the DB you intend to serve.
- **Certificates page — Expiry column is sortable (Phase 213, v5.25 — UIFIX-01).** Click the
  Expiry column header to sort the certificate inventory ascending (soonest-expiring first); click
  again to reverse to descending. Certificates with no recorded expiry sort to the end in both
  directions. The sort key is the parsed date, not the rendered date string, so ordering is always
  chronological. See
  [Report Interpretation → Certificates Page Expiry Sorting](report-interpretation.md#28-certificates-page-expiry-sorting-phase-213-v525--uifix-01).
- **Dashboard colours now follow the active theme everywhere, including the graph pages (Phase
  213, v5.25 — UIFIX-02).** The Roadmap, CBOM Graph tab, and Exposure Map pages re-resolve their
  Cytoscape colours immediately on a theme toggle — no reload needed. The exported PDF remains
  intentionally theme-independent: it always renders in a fixed light palette regardless of the
  live dashboard's theme at export time. See
  [Report Interpretation → Dashboard Colours Follow the Active Theme](report-interpretation.md#29-dashboard-colours-follow-the-active-theme-phase-213-v525--uifix-02).
- **Appearance note (Phase 165, A11Y-03, released in 5.18.0)** — primary and accent buttons now
  render dark text instead of white, and so do the orange HIGH badges (severity tiers are
  described in [Report Interpretation](report-interpretation.md#4-severity-tiers)) on the
  Findings, Trends, Data at Rest and Identity pages and some green status badges, such as the
  Data at Rest encryption and TLS chips. Red CRITICAL and Vulnerable badges, and the green Safe
  badges in the Findings, CBOM and Certificates quantum-safety columns, kept white text. Muted
  label text is also very slightly lighter. The button and badge background colours were
  numerically unchanged — only the foreground text moved, to clear WCAG 2.1 AA contrast (teal
  buttons: 2.81:1 → 6.06:1). This is a contrast fix, not a redesign. From 5.27.0,
  the orange badges on Compare, Scan History, Hardware and Motion, and the green badges on
  Certificates and Hardware, also switched to dark text.
  Since Phase 222.1 the accent is Ink-violet (#af89f5 dark, #6933cc light) on the unchanged
  grounds, per BRAND-GUIDELINES v2; primary buttons show Ink text in dark and white text in light
  (7.39:1 and 7.13:1).
- **Accessibility gate (Phase 165, A11Y-01/A11Y-04; theme dimension added Phase 216,
  HARNESS-01)** — `npm run a11y:check` (and its `:empty`/`:loading` variants) in
  `src/dashboard/` now enforce a per-route, per-rule *count budget* rather than a selector
  snapshot: each baselined `(route, rule)` pair records a maximum node count, impact level,
  WCAG success criterion, and a written justification. The gate fails if a count goes **up**
  (new debt) — and, deliberately, also if a count goes **down** without the baseline being
  regenerated (`npm run a11y:baseline`), so a real fix always tightens the ledger instead of
  leaving a now-stale, looser number in place.
  - **The sweep now has an explicit theme dimension (216 D-01/D-02).** Every route in
    `routes.json` is swept in both themes: `npm run a11y:check:dark` / `npm run
    a11y:check:light` (and the baseline-regenerating `npm run a11y:baseline:dark` / `npm run
    a11y:baseline:light`). The unsuffixed `a11y:check` / `a11y:baseline` remain aliases for the
    `:dark` form — existing scripts and CI steps that name them keep working. The harness seeds
    the real `quirk-ui-theme` `localStorage` key before navigation (the same path the live
    application's theme provider reads), not a forced CSS class and not a `prefers-color-scheme`
    media emulation, so the sweep exercises the actual app code path.
  - **Baseline filenames now name the theme explicitly — there is no implicit default
    (216 D-02).** Every baseline file is `baseline-{slug}-{variant}-{theme}.json`, including the
    dark ones (`baseline-root-default-dark.json`, not `baseline-root-default.json`). A light
    sweep with a missing light baseline is a hard error, exactly like a missing dark baseline
    always was — it never silently falls back to reading the dark file for that route.
  - **The `empty`/`loading` fixture variants stay dark-only, on purpose (216 D-03).** Neither
    variant renders a themed badge, so a second, light-theme sweep of them would add real CI
    cost for near-zero signal. A light-theme sweep requested against `empty`/`loading` is
    **refused loudly** (the harness exits non-zero before starting the preview server or
    browser) rather than silently skipped or silently run against the wrong theme.
  - **The `empty`/`loading` legs now measure what their names say (Phase 221, HARNESS-03).**
    Until Phase 221, on Linux CI every sweep after the first silently measured the first
    sweep's preview server, so the empty and loading baselines actually held default-variant
    numbers. The harness now refuses to run if port 4173 already answers, starts its own
    `vite preview --strictPort`, confirms the server's identity through a `/__a11y-variant`
    endpoint (a server reporting the wrong variant fails the sweep), and stops the whole
    server process group afterwards, asserting the port is free. Under `empty`, each route's
    declared per-endpoint markers (`variantMarkers` in `routes.json`) must be **absent**.
    Under `loading`, the fixture holds the requests open, the harness waits for the skeleton
    (`.animate-pulse` or a route's `loadingSelector`), and the markers must again be absent.
    A leg that renders default content therefore fails loudly instead of passing vacuously.
    Every fixture endpoint carries an explicit empty and loading decision in
    `tests/a11y/fixture-handlers.mjs`, enforced by `variant-contract.test.ts`.
  - **What is deliberately not measured is a named row, not silence (Phase 221).**
    `src/dashboard/tests/a11y/UNMEASURED-EXCLUSIONS.md` is hand-maintained, but
    `unmeasured-exclusions.test.ts` derives the set of required rows from source at run time,
    so a blind spot is either swept or listed with a reason, an owner (a `999.NNN` backlog
    item) and a date. The `/scans` and `/sensors` routes joined the sweep in Phase 221; the
    `/scans` loading leg is a recorded exclusion (UX-12) because `/api/scans` doubles as the
    auth probe and cannot be held open without blanking the shell.
  - **Per-entry count tolerance (Phase 216, HARNESS-03).** Tolerance is **opt-in and
    per-entry**, via a two-element `countRange: [floor, ceiling]` on a baseline entry. An entry
    with no `countRange` keeps today's exact-integer semantics unchanged — this is the default
    for all baselined rules. The existing stale-entry ratchet still fires against the range's
    **lower bound**, so a `countRange` is not a one-way ratchet that only ever loosens: a live
    count below the declared floor still fails as "Baseline is stale," exactly as an exact-count
    entry would. The only range ever declared — `data-at-rest`'s `scrollable-region-focusable`
    entry, absorbing a real macOS-vs-Linux render disagreement — was **retired** in Phase 219
    (KBD-01): once
    `components/ui/table.tsx` gained conditional `tabIndex`/`role` (applied only while the
    wrapper actually overflows), the rule's render-dependence vanished and it dropped out of
    every baseline entirely in CI run `36795176372`. No committed baseline currently declares a
    `countRange`. The mechanism itself is not retired — it remains available, opt-in, for a
    future entry that is genuinely render-dependent; it simply has no live user today. A
    `countRange` is hand-added once to a baseline entry and is then carried forward automatically
    across every later CI regeneration — declaring one is **not** the "hand-patching a baseline count" the
    next bullet forbids; it declares a bound in advance, it does not edit an already-observed
    count after the fact.
- **Regenerating a11y baselines — the sanctioned procedure (Phase 185, D-03).** Baselines
  **must** be generated on a Linux CI runner, not a contributor's local machine. Font metrics,
  overflow behavior, and other render-time properties differ enough between macOS and Linux that
  a rule which never fires locally can fire on Linux, and vice versa — the `data-at-rest`
  baselines were bumped by hand in September 2026 with commit messages reading
  "macOS-generated, Linux-enforced". To regenerate:
  1. Dispatch the permanent `a11y-regenerate-baselines` job in
     `.github/workflows/dashboard-quality.yml` (`workflow_dispatch`, runs on `ubuntu-latest`):
     `gh workflow run dashboard-quality.yml --ref <branch>`. `workflow_dispatch` works from any
     branch that contains the workflow file — you do not need to be on `main`.
  2. Once the run completes, download its artifact:
     `gh run download <run-id> --name a11y-baselines-<run-id>`. The artifact now contains
     **per-theme** `baseline-*-dark.json` / `baseline-*-light.json` files, plus the regenerated
     `ACCEPTED-VIOLATIONS.md` — **both must be committed together**, since `ACCEPTED-VIOLATIONS.md`
     is a rendering of the baseline JSON: if only one is updated the two disagree, and the
     `accepted-violations-freshness` test in the Dashboard Quality `Test` step fails.
     As of Phase 216, `ACCEPTED-VIOLATIONS.md` is produced by `npm run a11y:ledger` — a
     browser-free command that re-renders the ledger straight from the committed baseline JSON on
     disk (no preview server, no Chrome launch, ~0.2s). CI runs `a11y:ledger` itself as the final
     step of `a11y-regenerate-baselines`, after all `a11y:baseline*` steps and before the artifact
     upload, so the downloaded artifact already reflects every theme that run produced. You can
     also run `npm run a11y:ledger` locally at any time to re-check the committed ledger against
     the committed baselines without launching a browser.
  3. If you are onboarding a brand-new route, its `routes.json` entry and its baseline files
     **must land in the same commit**. A `routes.json` entry with no matching baseline file is a
     hard, by-design CI error (`missing baseline file`), not a soft warning — this is intentional,
     so a route can never silently ship unswept.
- **The sanctioned response to a gate failure (Phase 185, D-10).** When `Axe + Console Gate`
  goes red on a PR: (1) dispatch `a11y-regenerate-baselines` per the procedure above; (2) download
  the artifact; (3) review **every** changed `(route, rule)` count — an increase requires a
  written per-entry triage naming the rule, the route, and why it is accepted (justified in the
  ledger) or being fixed; a decrease may be committed freely; (4) commit the reviewed baselines
  and ledger together. **Hand-patching a baseline count locally, without going through this
  procedure, is NOT sanctioned.** This is not a stylistic preference — Phase 177 fixed three
  `data-at-rest` counts by hand (default, empty and loading baselines, 2026-09-02) without
  regenerating on Linux CI, and Phase 185 (2026-09-06) had to add the regeneration job to close
  that gap. Hand-patching a count quiets
  the gate without ever establishing whether the change was a genuine environment artifact or a
  real regression slipping through — treat any future local count edit the same way: as a defect
  to be replaced with the CI-regeneration procedure above, not a shortcut to repeat.
- **CI pins Chrome; local runs deliberately do not (Phase 185, D-06/D-07/D-08/D-09; amended
  Phase 216, HARNESS-03).** All three `browser-actions/setup-chrome` usages in
  `dashboard-quality.yml` (`a11y`, `a11y-regenerate-baselines`, `e2e-smoke`) pin a concrete
  version (`chrome-version: '152.0.7977.82'` as of this writing), guarded by
  `src/dashboard/tests/a11y/pinned-deps.test.ts` so the three occurrences can never drift apart or
  regress to a floating channel name (`stable`/`beta`/`dev`/`latest`). Local `a11y:check` runs
  intentionally do **not** pin — `run-a11y.mjs` launches Puppeteer's `channel: 'chrome'`, whatever
  is locally installed — so a local a11y result is **diagnostic-only** and must not decide a
  committed baseline; only the pinned, CI-run result should. This is a procedure, not a guard:
  `npm run a11y:baseline` still writes baseline files on a local machine. **Amendment:** the pin makes
  comparison sound **between CI runs** — it does not, and was never claimed to, make a local
  macOS run agree with a Linux CI run for a genuinely render-dependent count. The one entry that
  needed such a range — `data-at-rest`'s `scrollable-region-focusable` — was retired in Phase 219
  (KBD-01), so no committed baseline relies on a `countRange` today; the pin's rationale is
  unchanged, this just states its actual scope rather than an implied broader one.
  - **Why the exact pin needs no scheduled staleness check.** The exact pin resolves against the
    **Chrome for Testing** archive
    (`storage.googleapis.com/chrome-for-testing-public/152.0.7977.82/...`), whose
    `known-good-versions.json` lists the versions for which all assets are available for download
    (152.0.7977.82 is listed). A versioned download is a more durable pin than a floating channel
    name, so no `last_verified`-style staleness gate was added for it.
  - **Recovery if the pinned build ever becomes unfetchable.** `pinned-deps.test.ts` can only
    detect "never floats to `stable`" and "all three occurrences agree" — it cannot detect an
    exact pin that CfT has stopped serving. If `setup-chrome` fails to acquire the pinned build in
    CI: (1) on a branch, temporarily set the regeneration job's `chrome-version` to `stable` (the
    job takes no input for it) and dispatch the workflow; (2) read the
    resolved version from that run's "Record resolved Chrome version" step; (3) re-pin all three
    occurrences in `dashboard-quality.yml` to the newly resolved version; (4) regenerate baselines
    under the new pin per the D-03 procedure above; (5) triage any count changes per the D-10
    increase-triage rule.

### 5.3.1 UAT corpus integrity gate

`tests/test_uat_zero_undispositioned_gate.py` fails the build the moment any case in
`docs/UAT-SERIES.md` (the UAT gating document) has an all-unchecked `**Result:**`
line — it rides the existing `Linux Full Suite` CI job rather than a pre-commit hook, so it
cannot be bypassed with `--no-verify`. If you add a new UAT case, give it a real disposition
(PASS/FAIL, or a checked SKIP with a `DEFERRED — covered by <test-node>` or `GAP — no substitute
coverage` annotation) before committing. Full rationale and worked fix instructions are in the
gate test's own module docstring.

### 5.4 Connector gotchas

For per-connector authentication and IAM-permission issues, see the dedicated connector
docs: [`docs/connectors/aws.md`](connectors/aws.md),
[`docs/connectors/azure.md`](connectors/azure.md),
[`docs/connectors/docker.md`](connectors/docker.md),
[`docs/connectors/git.md`](connectors/git.md).

---

## 6. Per-Scanner Reference

Each scanner runs inside `run_scan.py` and, apart from the hardware, SNMP and OT/ICS
fingerprinting scanners, records its results as rows in the same `crypto_endpoints` SQLite table
(those fingerprinting scanners write advisory rows to a separate `hardware_devices` table).
Cloud and infra connectors with dedicated docs link out; protocol scanners that lack a
connector doc get a short inline subsection below the table. Every scanner in the
product has a row in the table: the identity, OT/ICS, API and hardware scanners follow
the connector rows.

### 6.1 Compact reference table

| Scanner | Scans | Config flag(s) | Optional deps | Sample finding |
|---------|-------|----------------|---------------|----------------|
| Discovery | TCP port discovery before fingerprinting: nmap by default in the dashboard (its default Top 1000 scope forces nmap) and in the interactive wizard; built-in by default for a `--config` run unless `--discovery nmap` | `--discovery builtin\|nmap`, `--targets-file`, `targets.cidrs` | `nmap` binary (only when nmap discovery runs) | — |
| TLS | TLS handshake, cert chain, ciphers, key sizes | `scan.ports_tls`, `scan.tls_designated_ports`, `scan.include_sni`, `timeouts.tls_seconds` | `sslyze` (core) | "TLS certificate expired" |
| SSH | SSH banner + KEX/host-key/cipher audit | `timeouts.ssh_seconds` | `ssh-audit` | "SSH quantum planning advisory" |
| JWT/API | JWKS key discovery (algorithm and key size per key) at each base URL | `connectors.enable_jwt`, `jwt_targets`, `timeouts.jwt_seconds` | (none, core) | `JWKS fetched with TLS certificate verification disabled` HIGH finding when `allow_insecure_jwks` is on |
| Container | Crypto libraries in Docker images via Syft SBOM | `connectors.enable_container`, `container_targets` | `syft` binary | "Container image uses quantum-vulnerable crypto library" |
| Source code | semgrep (registry pack `p/cryptography`; see the known issue in [`docs/connectors/git.md`](connectors/git.md)) on local repository directories | `connectors.enable_source`, `source_targets` | `semgrep` | (semgrep rule id plus `file:line`) |
| DNSSEC | DNSKEY / DS records | `connectors.enable_dnssec`, `dnssec_targets`, `timeouts.dnssec_seconds` | (none, core: `dnspython`) | `ds-chain-broken`, `sha1-ds-digest` |
| Kerberos | KDC enctype enumeration (port 88) | `connectors.enable_kerberos`, `kerberos_targets`, `kerberos_probe_principal`, `timeouts.kerberos_seconds` | `quirk-scanner[identity]` (`impacket`) | (DES / RC4 / AES-128 etype findings) |
| SAML | SAML IdP metadata: signing certificates and SHA-1 algorithm URIs | `connectors.enable_saml`, `saml_targets`, `timeouts.saml_seconds` | (none, core: `lxml`) | "SHA-1 algorithm URI detected in SAML metadata" |
| Email | 7-port email TLS probe (SMTP/IMAP/POP3 ± STARTTLS) | `connectors.enable_email`, `timeouts.email_seconds` | `sslyze` (core) | "STARTTLS downgrade risk on SMTP" |
| Broker | Kafka / AMQP / Redis / Azure Service Bus / SQS | `connectors.enable_broker`, `connectors.broker_targets`, `broker_azure_namespaces`, `broker_sqs_regions`, `timeouts.broker_seconds` | `sslyze` (core) + `quirk-scanner[motion]` | "Plaintext Kafka listener detected" |
| AWS | ACM certs, KMS keys, CloudFront, ELB, RDS encryption at rest | `connectors.enable_aws`, `aws_region`, `aws_profile` | `boto3` (core) | (KMS / cert findings) — see [`docs/connectors/aws.md`](connectors/aws.md) |
| Azure | Key Vault keys (known limitation: currently emits no endpoints), App Gateway TLS policies | `connectors.enable_azure`, `azure_subscription_id`, `azure_keyvault_urls` | (none, core) | — see [`docs/connectors/azure.md`](connectors/azure.md) |
| GCP | Cloud KMS, Cloud SQL TLS enforcement, GCS bucket encryption | `connectors.enable_gcp`, `gcp_project_id` | `quirk-scanner[cloud]` | [connector-field-reference.md](connector-field-reference.md#kubernetes--enable_k8s--gcp--enable_gcp) |
| Database | Postgres / MySQL server SSL enforcement | `connectors.enable_db`, `pg_targets`, `mysql_targets`, `pg_scanner_user`/`pg_scanner_password`, `mysql_scanner_user`/`mysql_scanner_password` | `quirk-scanner[db]` | [connector-field-reference.md](connector-field-reference.md#database--enable_db) |
| Object storage | S3 bucket encryption + Azure Blob encryption | `connectors.enable_s3`, `enable_blob` | `boto3` (core) for S3; `quirk-scanner[cloud]` for Blob | [connector-field-reference.md](connector-field-reference.md#object-storage--enable_s3--enable_aws) |
| Kubernetes | EKS/GKE/AKS encryption + secret type enumeration | `connectors.enable_k8s`, `k8s_provider`, `k8s_cluster_name`, `k8s_kubeconfig`, `k8s_context` | `quirk-scanner[cloud]` | [connector-field-reference.md](connector-field-reference.md#kubernetes--enable_k8s--gcp--enable_gcp) |
| Vault | Transit keys + PKI + auth methods | `connectors.enable_vault`, `vault_addr`, `vault_token`, `vault_transit_mount` | `quirk-scanner[cloud]` (`hvac`) | [connector-field-reference.md](connector-field-reference.md#hashicorp-vault--enable_vault) |
| Docker (image SBOM) | (uses container scanner) | (see Container row) | `syft` | [`docs/connectors/docker.md`](connectors/docker.md) |
| Git (semgrep) | (uses source scanner) | (see Source row) | `semgrep` | [`docs/connectors/git.md`](connectors/git.md) |
| PQC probe | Negotiates `X25519MLKEM768` against every TLS target (post-quantum hybrid key exchange) | none: runs with the TLS phase | host `openssl` with ML-KEM support (advisory fallback without it) | `pqc-hybrid-detected` |
| S/MIME | S/MIME signing certificates in AD `userCertificate` / `userSMIMECertificate` over anonymous LDAP | `connectors.enable_smime`, `smime_targets`, `smime_search_base`, `smime_timeout` | `quirk-scanner[adcs]` (`ldap3`) | (weak-signing-alg / weak-rsa-key / expired certificate rows, protocol `SMIME`) |
| AD CS | Read-only LDAP enumeration of AD CS certificate authorities and templates (ESC1, ESC2, ESC3, ESC6) | `connectors.enable_adcs`, `adcs_targets`, `adcs_search_base`, `adcs_user`, `adcs_password` or `QUIRK_ADCS_PASSWORD`, `adcs_timeout` | `quirk-scanner[adcs]` (`ldap3`) | `coverage-gap\|ESC4\|reason=not-ldap-observable` |
| Code signing | Code-signing certificates (CodeSigning EKU) from LDAP `userCertificate` and from the leaf certificates the TLS phase captured | `--inventory-code-signing`, `connectors.codesign_targets`, `codesign_search_base`, `codesign_timeout` | `quirk-scanner[adcs]` (`ldap3`) | (HIGH for SHA-1, RSA < 2048, EC < 256, or expired; protocol `CODE_SIGNING`) |
| OpenAPI spec | Security schemes, plaintext `http://` servers and unauthenticated paths in a local or in-scope OpenAPI/Swagger spec | `--openapi-spec FILE_OR_URL` | `quirk-scanner[api]` | `plaintext_server` |
| REST fuzzing | Active crypto-posture fuzzing of the API described by the spec (TLS downgrade, weak ciphers, HSTS, JWT alg confusion) | `--openapi-spec` plus `--fuzz`, `--fuzz-jwt-alg-confusion`, `--fuzz-budget`; see [§3.2](#32-active-rest-fuzzing---fuzz--interactive-only-by-design) | `quirk-scanner[api]` | `tls_downgrade_accepted` |
| Hardware fingerprint | Vendor, model, firmware and CNSA 2.0 tier of SSH-reachable devices (SSH banner, HTTP management interface) | none: runs in the SSH phase; see [§9](#9-hardware-scanning) | (none, core) | (advisory device row; no score impact) |
| SNMP | sysDescr / sysName / sysObjectID device fingerprinting (SNMPv2c; SNMPv3 per host) | `--enable-snmp`, `connectors.enable_snmp`, `snmp_community`, `snmp_v3_credentials`; see [§9.1](#91-enable-snmp-scanning) | `quirk-scanner[hw]` | (advisory device row) |
| Modbus / BACnet | One read-only Modbus FC 43/14 exchange, or one BACnet Who-Is plus ReadProperty requests for model name and firmware revision, per host (OT/ICS) | `--enable-modbus`, `--enable-bacnet`, `connectors.enable_modbus`, `enable_bacnet`, `enable_recurring_otics`; see [§9.4](#94-otics-fingerprinting-modbus--bacnet-phase-141) and [§12](#12-otics-recurring-scan-safety) | `quirk-scanner[hw]` | (advisory device row) |

### 6.2 Protocol scanner details

#### TLS scanner

With built-in discovery it fingerprints every `(host, port)` pair built from the targets and
`scan.ports_tls` (plus port 502 when Modbus is enabled). When nmap discovery runs, it fingerprints only
the open pairs nmap found, and nmap's port list goes beyond `scan.ports_tls` (it adds 22, 80, 8080
and 8000, or uses the top 1000 or all ports for those scopes). In both cases
the ports that answer TLS get a full handshake via `sslyze`, and the scanner reads the
received certificate chain and whether it verifies. Findings include expired and
soon-to-expire certificates, self-signed certificates, certificates from an untrusted
CA, undersized or quantum-vulnerable RSA and ECDSA keys, legacy TLS versions (1.0 and
1.1), and legacy cipher suites. Activated by the core install — no extra required.

#### SSH scanner

Runs `ssh-audit` against each target to enumerate KEX algorithms, host-key types, and
cipher/MAC suites, taking the SSH banner from its output (without `ssh-audit` it grabs the raw
banner instead; see below). Every SSH endpoint scanned without an error gets an INFO
"SSH quantum planning advisory", and the CBOM classifier assigns each algorithm a NIST
quantum security level (0 for the classical KEX and signature algorithms) and a classical
strength (e.g. `diffie-hellman-group1-sha1` 80 bits, `ssh-rsa` 112 bits). The per-algorithm
detail requires the `ssh-audit` binary on `PATH`.

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

> **If you scanned SSH hosts with a release before 2026-08-31 (PyPI 5.15.0 or earlier; fixed in
> 5.18.0), check the SSH detail of any host on a non-standard port.** Those releases passed the
> port to `ssh-audit` as a separate argument instead of as `host:port`. With `ssh-audit` 3.3.0
> that extra argument is ignored and port 22 is audited, so a service on port 22 was recorded
> correctly. A service on any other port got the algorithms of the same host's port 22 when that
> port runs SSH, and otherwise fell back to the banner grab with no per-algorithm data. Re-scan
> any SSH hosts on non-standard ports that you need per-algorithm inventory for.

Note that `ssh-audit` must be on the `PATH` of the process running the scan. If QU.I.R.K. is
installed in a virtualenv and you invoke it via an absolute interpreter path
(`/path/to/.venv/bin/python -m ...`) without activating the environment, the venv's `bin/`
directory is *not* added to `PATH` and `shutil.which("ssh-audit")` will not find it. Activate
the environment, or ensure the directory containing `ssh-audit` is on `PATH`.

#### JWT/API scanner

Iterates over `jwt_targets` (API base URLs), probes `/.well-known/jwks.json`,
`/oauth/jwks` and the OIDC discovery document in that order, stopping at the first that
returns keys, and emits one `JWT` endpoint per key with the key's algorithm and, for RSA
and EC keys, its size. Gated by `connectors.enable_jwt`.

**Security note — `allow_insecure_jwks`:** By default the JWT scanner verifies TLS
certificates when fetching JWKS endpoints (`security.allow_insecure_jwks: false`). Set
`security.allow_insecure_jwks: true` (or pass `--allow-insecure-jwks`) only when scanning
internal or dev endpoints that use self-signed or expired certificates. It is a
`security:` key, not a `connectors:` key. When this flag is enabled:

- TLS certificate verification is disabled for JWKS fetches only (other scan phases
  are unaffected).
- A `HIGH`-severity `ADVISORY` endpoint row (`ADVISORY_JWKS_VERIFY_DISABLED`, recorded as
  `JWKS/verify-disabled`) is stored for every JWKS URL fetched.
- Each of those URLs also appears as a `HIGH` finding titled `JWKS fetched with TLS
  certificate verification disabled`, on the CLI report and on the dashboard Findings
  page. It is counted in the findings totals but does not change the readiness score.
- The HTML report's Endpoint Inventory shows the row only as an `ADVISORY` row for the
  JWKS URL, without the label or the severity.
- QUIRK remains a passive inventory tool — it does not rely on JWKS key material for
  any authentication decision, so a MITM on the JWKS URI cannot escalate privileges.
  The threat model accepts this for controlled assessment environments.

See the `security:` block reference in `docs/configuration.md` for the full
`allow_insecure_jwks` config key reference.

#### Container scanner

For each entry in `container_targets`, generates a Syft SBOM of the named image and
keeps the packages whose names are on a fixed crypto-library allowlist (OpenSSL and
its `libssl`/`libcrypto` packages, mbedTLS, wolfSSL, GnuTLS, NSS, libgcrypt, Botan, and
the Python `cryptography`, `pyopenssl`, `pycryptodome`, `bcrypt` and `pynacl`
packages). Emits "Container image uses quantum-vulnerable crypto library (name@version)"
findings. Requires `syft` on `PATH` and `connectors.enable_container=true`.

#### Source-code scanner

Runs semgrep with the registry pack `p/cryptography` against each directory in
`source_targets`. As of 2026-10-12 the Semgrep registry answered HTTP 404 for that pack
name (details in [`docs/connectors/git.md`](connectors/git.md)). Each entry must be a
path to an existing local directory (for example a clone); remote URLs are not fetched,
and a path that is missing or contains `..` or shell metacharacters is rejected with an
`invalid_input` row. Findings carry the semgrep rule id and `file:line`. Requires
`semgrep` on `PATH` and `connectors.enable_source=true`.

#### DNSSEC scanner

Resolves DNSKEY and DS records for each domain in `dnssec_targets` and classifies the
signing algorithms (RSASHA1, RSASHA256, ECDSAP256SHA256, ED25519, etc.) against RFC
8624 / RFC 9905 severities. Reports unsigned zones (`unsigned-zone`), NSEC exposure
(`nsec-exposure`), a DS record that matches no DNSKEY (`ds-chain-broken`), and SHA-1 DS
digests (`sha1-ds-digest`). Requires no extra — `dnspython` is a core dependency.

#### Kerberos scanner

Sends an unauthenticated AS-REQ to KDC port 88 on each entry in `kerberos_targets`
(over TCP, falling back to UDP if the TCP probe fails) and reads the supported encryption types
(`aes256-cts-hmac-sha1-96`, `aes128-cts-hmac-sha1-96`, `des-cbc-md5`, etc.). DES
enctypes are CRITICAL, `rc4-hmac` and `aes128-cts-hmac-sha1-96` are HIGH, and the AES-256
enctypes are SAFE. Requires `quirk-scanner[identity]` (`impacket`).

The probe names a client principal in its AS-REQ, set by `connectors.kerberos_probe_principal`
(default `Administrator`, which exists by default on Active Directory and Samba AD DC). It is a
principal name, not a secret. An AS-REQ with no pre-authentication data is not a failed logon,
so the probe carries no lockout risk. A KDC that requires pre-authentication answers that
request with an error that lists its supported encryption types, and the scanner now reads
that list. This was observed against a real Samba AD DC KDC on 2026-10-23 (lab `kerberos`
profile, reached on a remapped host port because the macOS KDC holds port 88): the default
principal returned `aes256-cts-hmac-sha1-96` only. The same lab KDC drops about one TCP
connection in three without a reply; the scanner then falls back to UDP, and a UDP probe
that fails is still reported as `kerberos-no-preauth`. That row can therefore be a probe
failure and not proof the KDC does not require pre-authentication. It is tracked as an
open todo (`261023-detect-kerberos-udp-failure-reads-as-no-preauth`).

If the KDC answers that the probe principal is unknown, the scanner emits the row
`kerberos-etypes-unavailable-principal-unknown`. This is an assessment gap: it derives no
finding and no direct score penalty, and it is not a statement that the KDC is safe. Two
effects it shares with the `kerberos-no-preauth` row are pre-existing and are not intended
(open todo `261023-detect-kerberos-placeholder-rows-count-as-assessed`): the row counts as
Kerberos evidence, so the identity domain is treated as assessed, and it counts as an
assessed endpoint, so it raises the scan's coverage (and therefore its confidence) although
no Kerberos crypto was assessed. To resolve it, set `kerberos_probe_principal` to an account
that exists.

If the KDC answers that pre-authentication is required but its reply lists no encryption types
(no error data, error data that cannot be decoded, or error data that carries only other
pre-authentication hints such as a timestamp request), the scanner emits the row
`kerberos-etypes-unavailable-preauth-no-etype-info`. That reply proves the KDC requires
pre-authentication, so it is never reported as `kerberos-no-preauth`. It is treated the same way
as the principal-unknown row: an assessment gap with no finding, no weak-etype count and no UDP
retry.

If something answers on port 88 but not as a KDC, the scanner emits the row
`kerberos-etypes-unavailable-unrecognised-reply` and records the error on it. This covers a reply
that decodes as neither a Kerberos error nor an AS-REP, an AS-REP for a different realm or
principal than the probe's (realm and principal are compared without regard to case), and a
reply that breaks Kerberos TCP framing: an HTTP or other non-Kerberos service, a truncated reply,
or a declared reply length over 64 KiB. That row is never reported as `kerberos-no-preauth`, derives no finding, and is not
retried over UDP. Only a TCP probe that received no reply byte at all (connection refused, a
timeout, or a close before replying) falls back to UDP. The TCP probe, including its reply, is
bounded by the Kerberos timeout (a fixed 10 s), so a silent or misbehaving listener cannot stall
the scan.

Kerberos targets need an FQDN whose last two labels are the realm (for example
`dc.corp.example.com` gives realm `CORP.EXAMPLE.COM`). An IP-literal target is used as the
realm as-is, and a real KDC answers that the principal is unknown in that realm, so a bare
IP address yields the principal-unknown row, never the etypes (measured against Samba on
2026-10-23). There is no separate realm setting; this is tracked as an open todo.

#### SAML scanner

Fetches the SAML IdP metadata (or OIDC discovery document) for each entry in
`saml_targets`, classifies the signing and encryption certificates by key algorithm
and size, and flags SHA-1 algorithm URIs in `SignatureMethod` and `alg:SigningMethod`
elements ("SHA-1 algorithm URI detected in SAML metadata"). Requires no extra —
`lxml` is a core dependency.

#### Email scanner

Probes 7 email-TLS ports per target — SMTP `25`/`465`/`587`, IMAP `143`/`993`, POP3
`110`/`995` — handling both implicit TLS and STARTTLS upgrades. Gated by
`connectors.enable_email`. Findings include "STARTTLS downgrade risk on SMTP" (port 25
only, when TLS was actually negotiated), "Weak cipher suite on email TLS endpoint", and
"Non-PFS cipher suite on email TLS endpoint". Requires no extra — `sslyze` is a core
dependency.

#### Broker scanner

Probes message-broker endpoints across five protocol families: Kafka (configurable
listeners), AMQP (RabbitMQ), Redis, Azure Service Bus (per `broker_azure_namespaces`),
and Amazon SQS (per `broker_sqs_regions`). Findings include plaintext-listener
detection ("Plaintext Kafka listener detected", "Plaintext AMQP listener detected",
"Plaintext Redis listener (no auth)") and weak TLS configuration ("Weak cipher suite on
broker TLS endpoint"). Gated by `connectors.enable_broker=true` and requires
`quirk-scanner[motion]` for its Kafka/Redis clients (`sslyze`, which drives the TLS probe
itself, is a core dependency).

**Non-default ports (Phase 190, TRIAGE-06):** each family's default port table is fixed; to
also probe a broker running on a non-standard port, list it in `connectors.broker_targets`
(`host` / `host:port` / `[ipv6]:port`). Declared ports are probed *in addition to* the
defaults — this can only widen coverage, never narrow it. An explicitly-named `host:port` that
never responds produces exactly one `ADVISORY` row (severity `INFO`,
`BROKER/target-unreached`) rather than failing silently. See
[`docs/configuration.md`](configuration.md) for full syntax and semantics.

#### PQC-hybrid probe

Runs as its own phase and never through `sslyze`, whose bundled OpenSSL cannot complete
a hybrid handshake. For every TLS target it runs one `openssl s_client` subprocess and
records a TLS endpoint tagged `pqc-hybrid-detected` when the negotiated TLS 1.3 group is
`X25519MLKEM768`; the probe has an 8-second timeout and there is no config key to
disable it. If the scanning host's own `openssl` does not list ML-KEM
(`openssl list -kem-algorithms`), the probe cannot test the target, and it emits an
`ADVISORY` row (`pqc-hybrid-detected|advisory=openssl-too-old`) instead. That advisory
row is counted in `pqc_hybrid_endpoint_count`, the same evidence counter a real
detection feeds, so on such a host the probe can count as a hybrid endpoint in the
PQC readiness score without having detected one.

#### S/MIME scanner

Binds anonymously to each LDAP entry in `smime_targets` (`ldap://host:port`,
`ldaps://host:port`, or a bare `host[:port]`) and pages through the AD
`userCertificate` and `userSMIMECertificate` attributes. The search base is
`smime_search_base`, or a base DN derived from the target's Kerberos realm; with
neither, the target is skipped. Only certificates that fail a check are emitted (one
row per certificate, protocol `SMIME`): HIGH for a weak signature algorithm or an RSA
key under 2048 bits, MEDIUM for an expired certificate that is otherwise sound. A target that
cannot be bound or searched gets one `smime-unreachable` row carrying the error instead. It reads
no mailbox content or message envelope data. Gated by `connectors.enable_smime`; needs
`ldap3` from `quirk-scanner[adcs]`.

#### AD CS scanner

Enumerates the CA and certificate-template objects under the target domain's
`CN=Public Key Services` container with read-only LDAP; it never enrolls, requests, or
writes anything. A CA with a weak signing algorithm or RSA key is HIGH. Templates are
checked for the LDAP-observable ESC1, ESC2, ESC3 and ESC6 conditions (HIGH). ESC4, ESC5,
ESC7 and ESC8 cannot be observed over LDAP, so each target gets one LOW
`coverage-gap|ESC<n>|reason=not-ldap-observable` row per class, and a target that
cannot be bound or searched gets one LOW `adcs-unreachable` row. Gated by
`connectors.enable_adcs`; credentials come from `adcs_user` and `adcs_password` (or the
`QUIRK_ADCS_PASSWORD` environment variable); needs `ldap3` from `quirk-scanner[adcs]`.

#### Code-signing inventory

Opt-in through the `--inventory-code-signing` CLI flag; `connectors.enable_codesign` does
not change scan behaviour. It finds code-signing certificates from two sources: LDAP
`userCertificate` attributes on `codesign_targets`, read with an anonymous bind, and the
Extended Key Usage OIDs the TLS scanner records for each leaf certificate it captures, so a
scanned server whose certificate carries the CodeSigning EKU is reported even with no LDAP
target configured. Findings use
protocol `CODE_SIGNING`: HIGH for a SHA-1 signature, an RSA key under 2048 bits, an EC
key under 256 bits, or an expired certificate, and MEDIUM when expiry is within 90 days.
The LDAP source needs `ldap3` from `quirk-scanner[adcs]`.

#### OpenAPI spec scanner

`--openapi-spec FILE_OR_URL` parses a local spec file, or an HTTP(S) URL that is inside the
scan targets, and emits `OPENAPI` rows for each security scheme
(`security_scheme:<name>`), each plaintext `http://` server (`plaintext_server`), and each
operation with no security requirement (`unauthenticated_endpoint:<METHOD> <path>`). A
spec containing an external `$ref` is refused, and specs over 10 MB are rejected before
parsing. Without the `[api]` extra the scanner returns a single `missing_extra` row
instead of scanning. See §3.2 for the interactive active fuzzer that builds on the same
spec.

#### REST crypto-posture fuzzer

`--fuzz` (with `--openapi-spec`) sends a bounded number of live requests to the API:
it checks for accepted TLS downgrades (`tls_downgrade_accepted`), weak ciphers
(`cipher_weak`), a missing HSTS header (`hsts_missing`) and, when credentials are
supplied, a spec-declared `http://` endpoint they would be sent to (`http_creds`), and, with `--fuzz-jwt-alg-confusion`, JWT algorithm-confusion
(`alg_confusion`). It refuses to run unless an operator types `CONFIRM` at a terminal,
and `--fuzz-budget` is capped at 500 requests. The full behaviour, including why it is
interactive-only, is in §3.2. Needs `quirk-scanner[api]`.

#### Hardware, SNMP and OT/ICS fingerprinting

These scanners identify network devices rather than crypto endpoints, and they write
advisory `hardware_devices` rows with no score impact. Hardware fingerprinting needs no
flag: while an SSH target is scanned, the SSH banner is matched against the hardware
catalog; when the banner does not identify the vendor, a best-effort probe of the device's
HTTP management interface is tried instead. SNMP (`--enable-snmp`) and Modbus/BACnet
(`--enable-modbus`, `--enable-bacnet`) are opt-in, need `quirk-scanner[hw]`, and are covered, with their safety rules, in §9.

### quirk doctor

Pre-engagement health check. Runs eight diagnostic categories (the scanner-binaries
category checks three binaries) and prints a Rich-formatted table. Exit code is the
machine-readable signal:

- `0` — all non-informational checks pass; QUIRK is ready to scan
- `1` — one or more non-informational checks failed; address before scanning

#### Usage

```bash
quirk doctor
```

It takes no flags (extra arguments are ignored). Invoke before each client engagement.

#### Categories

| # | Category | Severity | Failure exits 1? |
|---|----------|----------|------------------|
| 1 | Python environment (>= 3.11) | non-informational | yes |
| 2 | Scanner binaries (`nmap`, `syft`, `semgrep` in PATH) | non-informational | yes |
| 3 | Compliance framework freshness (within `STALENESS_THRESHOLD_DAYS`) | non-informational | yes |
| 4 | QRAMM module availability | informational | **no** |
| 5 | Database (`QUIRK_DB_PATH` if set, else `./quirk-output/quirk.db`, or the one existing legacy `./quirk.db` / `./output/quirk.db`; more than one legacy file is a failure) | non-informational | yes |
| 6 | Configuration (`./config.yaml` parses) | non-informational | yes (malformed); informational only if file is absent |
| 7 | Network connectivity (DNS lookup of `example.com`) | informational | **no** |
| 8 | Dashboard process (HTTP HEAD to `http://127.0.0.1:8512/`) | informational | **no** |

The Python check requires 3.11 or newer, although the package metadata (`requires-python`)
allows 3.10.

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
│ Binary: semgrep         │ [✗] [QRK-INSTALL-008] `semgrep` binary not…   │
│ Compliance freshness    │ [✓] all frameworks within freshness window    │
│ QRAMM module            │ [✓] QRAMM module available                    │
│ Database (quirk.db)     │ [✓] DB at ./quirk-output/quirk.db reachable   │
│ Configuration           │ [✓] ./config.yaml parses cleanly              │
│ Network connectivity    │ [✓] DNS lookup succeeded for example.com      │
│ Dashboard process       │ [!] Dashboard unreachable at 127.0.0.1:8512   │
└─────────────────────────┴───────────────────────────────────────────────┘
$ echo $?
1
```

(In the example above, `semgrep` is missing — a non-informational failure that
exits 1. Real failure cells carry the full error code and a `Fix:` hint, and wrap across
several lines; they are truncated here.)

---

## 7. Compliance Map Maintenance

QU.I.R.K. ships a `COMPLIANCE_MAP` in `quirk/compliance/__init__.py` that joins
finding titles to PCI-DSS 4.0.1, HIPAA (45 CFR §164.312), FIPS 140-3, SOC 2 and
ISO 27001:2022 controls.
Regulators publish revisions on their own cadences; this runbook documents how
QU.I.R.K. maintainers keep the map current and how operators can verify freshness on
demand.

### 7.1 Quarterly review checklist

1. Run `quirk compliance status` and confirm every framework's `Last Verified` date is
   within the last 90 days (the maintainers' quarterly target; the CI gate in §7.3 only
   fails past 365 days).
2. Visit each publisher URL (table below) and check for newly published revisions.
3. If a revision exists, follow §7.4 "Upgrade path".
4. If no revision exists but `last_verified` is older than 90 days, update
   `last_verified` to today only after re-reading the current source — the date attests
   that someone did, and bumping it to clear a failing gate without re-reading is not a
   re-verification.
5. Run `pytest tests/test_compliance_schema.py tests/test_compliance_freshness.py
   tests/test_compliance_title_join.py` — all green.
6. Commit and push.

### 7.2 Source URLs to monitor

| Framework | Publisher | Monitor URL |
|-----------|-----------|-------------|
| PCI-DSS | PCI Security Standards Council | https://www.pcisecuritystandards.org/document_library/ |
| HIPAA 45 CFR §164.312 (publisher landing) | HHS / ECFR | https://www.hhs.gov/hipaa/for-professionals/index.html (answers HTTP 403 to non-browser clients; open it in a browser) |
| HIPAA 45 CFR §164.312 (canonical regulation text) | HHS / ECFR | https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-C/part-164 |
| FIPS 140-3 | NIST CSRC | https://csrc.nist.gov/publications/fips |
| SOC 2 (Trust Services Criteria) | AICPA | https://www.aicpa-cima.com/resources/landing/aicpa-trust-services-criteria |
| ISO 27001:2022 | ISO / national body | https://www.iso.org/standard/27001 (answers HTTP 403 to non-browser clients; open it in a browser) |

### 7.3 How to detect drift

QU.I.R.K. ships several CI gates that fail the build before stale data ships to a
customer:

- **`tests/test_compliance_freshness.py`** — fails when any entry's `last_verified` is
  older than `STALENESS_THRESHOLD_DAYS` (currently 365 days; defined in
  `quirk/compliance/__init__.py`). This is the 12-month staleness gate (COMPLY-08).
- **`tests/test_compliance_schema.py`** — fails when any entry is missing `framework`,
  `control`, `version`, `last_verified`, or `source_url`.
- **`tests/test_compliance_title_join.py`** — is meant to fail when an emitted finding
  title is not in `COMPLIANCE_MAP` or `UNMAPPED_TITLES`. That check is currently marked
  as an expected failure (non-strict `xfail`) because emitted titles are unmapped (seven
  today: three code-signing, three SAML and one OIDC), so it does not block the build.
- **`tests/test_compliance_cli.py`** — smoke for `quirk compliance status` (text +
  JSON).
- **`tests/test_compliance_report_section.py`** — verifies the HTML report's "Compliance
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

1. When PCI SSC publishes a revision of PCI-DSS (this example assumes a v4.1; the map
   currently carries 4.0.1), it appears at
   https://www.pcisecuritystandards.org/document_library/.
2. Maintainer reviews the diff: control numbers may shift; requirement text may add
   new clauses.
3. Edit `quirk/compliance/__init__.py`:
   - Update the `_PCI_4_0_1_URL` constant — rename and re-point to the v4.1 PDF, or
     add a `_PCI_4_1_URL` alongside.
   - Update the `_pci()` helper — change `"version": "4.0.1"` → `"version": "4.1"`.
   - Update `_PHASE_49_VERIFIED` to today's ISO date. That constant is shared by the
     `_pci()`, `_hipaa()` and `_fips()` helpers, so bumping it re-dates all three
     frameworks: re-verify HIPAA and FIPS 140-3 first, or give the revised framework its
     own constant. SOC 2 and ISO 27001 use `_PHASE_52_VERIFIED`.
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

### 7.5 CMVP validated-modules cache

The CMVP attestation feed is a separate catalog, `quirk/compliance/cmvp_cache.json`, with
its own `last_verified` date and a 90-day staleness threshold
(`quirk/compliance/cmvp.py`). Re-verify it by reading its `source_url` (the NIST CSRC
validated-modules search page) and editing `last_verified` by hand; do not use
`quirk compliance cmvp refresh` for this. An earlier version of that command wrote an
empty algorithm list over the cache entries it could not parse (fixed from 5.15.0,
commit `a7cf302`), and a hand check is the only re-verification the date attests.

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

Each sensor is a standard `pip install "quirk-scanner[all]"` deployment. Sensors
communicate with the console over HTTPS (use an `https://` console URL) and authenticate each
push with their own per-sensor token (§8.1.1). Each push also carries an HMAC-SHA256
value made with a key the sensor generates locally at enrollment.

### 8.1 Provision the console

Install QU.I.R.K. on the console host and start the server. The console must bind a
routable address so sensors can reach it over the network:

```bash
# Console host (Linux / macOS)
pip install "quirk-scanner[all]"

# Set the operator API token BEFORE starting the server. It protects the dashboard and
# the operator API; sensors do not use it (each sensor pushes with its own token, §8.1.1).
export QUIRK_API_TOKEN="<your-strong-random-token>"

# Start the server — bind to a specific interface or 0.0.0.0 for all interfaces.
# The console binds loopback by default; override for multi-host use.
quirk serve --host 0.0.0.0 --port 8512
```

> **Security note:** Do not expose the console port to untrusted networks without an
> HTTPS reverse proxy and IP allowlist in front of it. Set `QUIRK_API_TOKEN` to a
> strong random value before starting the server; `quirk serve` with neither this variable
> nor a `security.api_token` in the config it reads (`QUIRK_CONFIG_PATH`, else
> `./config.yaml`) runs with authentication disabled (appropriate only for local dev/testing). A config file that
> exists but cannot be read or parsed stops `quirk serve` (exit code 2) and makes protected `/api/*` routes
> answer 503 (`DASHBOARD-014`).
>
> As a guardrail, `quirk serve` **refuses to start** on a network-reachable
> interface when neither token is configured, unless you pass `--insecure` to
> explicitly acknowledge a token-less bind on a trusted, firewalled segment. When the
> console runs behind a reverse proxy, set `QUIRK_TRUST_PROXY` (default `127.0.0.1`)
> so per-IP rate limiting and the sensor IP allowlist see the real sensor address rather
> than the proxy's. For a **cloud-hosted console** (e.g. on Linode) with internal sensors
> pushing in, follow the hardened, end-to-end walkthrough in
> [`deployment-cloud-console.md`](deployment-cloud-console.md) and the ready-to-use
> files under [`deploy/`](../deploy/). To restrict which source addresses may push, set
> `QUIRK_SENSOR_IP_ALLOWLIST` (comma-separated IPs or CIDRs; unset allows any source),
> described in the [admin guide](admin-guide.md).

`quirk serve`, `quirk console enroll`, `quirk console revoke-sensor` and `quirk sensor
merge` all use the same console database: `QUIRK_DB_PATH` if set, otherwise
`./quirk-output/quirk.db` relative to the directory you run them from. One exception: if
that directory holds exactly one legacy database (`./quirk.db` or `./output/quirk.db`) and
no `./quirk-output/quirk.db`, they use the legacy file, and if it holds more than one of the
three they stop with a "Multiple QU.I.R.K. DBs found" error. Run them from the
same directory (or export `QUIRK_DB_PATH`) so a sensor enrolled with `quirk console enroll`
is known to the server that receives its pushes.

### 8.1.1 Per-sensor authentication model

Every sensor authenticates `POST /api/sensor/push` with its **own per-sensor
token** issued by `quirk console enroll`. The shared `QUIRK_API_TOKEN` is not accepted on
this route, and there is no dual-accept period. Builds from before 5.5.0 used that shared
token for pushes; the first PyPI release with the sensor commands is 5.5.0, which already
uses per-sensor tokens, so a PyPI install never had the shared-token model.

| Component | Role |
|-----------|------|
| `QUIRK_API_TOKEN` env var (or `security.api_token` in `config.yaml`) | Console's shared token; governs operator/dashboard auth, not sensor pushes |
| Enrollment token from `quirk console enroll` | **The per-sensor push credential.** Shown once; only its SHA-256 hash is stored in `sensor_tokens`. Place this raw value in `console_api_token` in `sensor.yaml` on the sensor host. |
| `console_api_token` in `sensor.yaml` | Must hold the sensor's per-sensor enrollment token (not the shared `QUIRK_API_TOKEN`) |

**Provisioning steps (per sensor host):**

1. On the **console host**, print the enrollment token for the sensor:
   ```bash
   quirk console enroll --segment <label>
   # → Bearer token: <per-sensor-token>  (copy now — shown once)
   # → sensor_id: <uuid>
   ```
2. On the **sensor host**, run `quirk sensor enroll` with that `sensor_id` and token
   (§8.2) so `sensor.yaml` carries both. The `sensor_id` must match: a push whose envelope
   `sensor_id` differs from the one the token belongs to is rejected with HTTP 403.
   ```yaml
   console_api_token: <per-sensor-token>   # written by --api-token, or edit it in by hand
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

On the **console host**, provision a sensor row for each sensor. Each invocation without
`--sensor-id` creates a new `sensors` row in the console database and prints a
**per-sensor push token** to stdout (the generated `sensor_id` goes to stderr). This
token **IS** the push credential — place it in `console_api_token` in `sensor.yaml` on the
sensor host. It is shown once and never recoverable; only its SHA-256 hash is stored in
`sensor_tokens`.

```bash
# Console host — run once per sensor
quirk console enroll --segment <label>
# e.g.:
quirk console enroll --segment segment-a
# → Bearer token (copy now — shown once, never recoverable): <per-sensor-token>
# → sensor_id: <uuid>
quirk console enroll --segment segment-b
```

On each **sensor host**, run `quirk sensor enroll` with the `sensor_id` and the token
printed above. `--sensor-id` binds this sensor to the console-side row (without it
the sensor invents a random UUID that the token does not belong to, and every push is
rejected with HTTP 403), and `--api-token` writes the token into `console_api_token`:

```bash
# Sensor host — Linux / macOS
quirk sensor enroll https://<console-host>:8512 \
  --segment <label> \
  --sensor-id <sensor_id-from-quirk-console-enroll> \
  --api-token <per-sensor-token-from-quirk-console-enroll>
# e.g.:
quirk sensor enroll https://console.corp:8512 \
  --segment segment-a \
  --sensor-id 022ca970-c50c-460e-9940-fdef9f29edce \
  --api-token <per-sensor-token>
```

To keep the token out of shell history, omit `--api-token` and edit `console_api_token`
into `sensor.yaml` by hand instead.

`quirk sensor enroll` never contacts the console. It checks the console URL (the host
must resolve; a private or loopback address needs `--allow-internal-console`, which is
remembered in `sensor.yaml` for later pushes; a console URL on the cloud-metadata address
`169.254.169.254` is refused). The console URL must use `https://` unless its host is loopback;
pass `--allow-insecure-console` to accept `http://` for another host (isolated lab networks). The
flag prints a warning and is remembered in `sensor.yaml` as `allow_insecure_console` (default
`false`), and `quirk sensor push` applies the same rule to an existing `sensor.yaml`: re-enroll
with an `https://` URL, or with the flag. `--allow-insecure-console` is separate from
`--allow-internal-console` (scheme versus address range). `quirk sensor enroll` then generates the sensor's HMAC key and writes `sensor.yaml`.
It also prints an "Enrollment
token" of its own; that value is generated locally, stored nowhere and is not the push
credential, so ignore it and use the token that `quirk console enroll` printed. Running
`enroll` again with the same `--sensor-id` leaves an existing `sensor.yaml` untouched.

Enrollment writes `sensor.yaml` to the default platform config directory:
- **Linux:** `~/.config/quirk/sensor.yaml` (`$XDG_CONFIG_HOME/quirk/sensor.yaml` when that variable is set)
- **macOS:** `~/Library/Application Support/quirk/sensor.yaml` (`$XDG_CONFIG_HOME/quirk/sensor.yaml` when that variable is set)
- **Windows:** `%LOCALAPPDATA%\quirk\quirk\sensor.yaml`

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

`quirk sensor push` runs a local scan using the target list in the scan config
(`--scan-config` defaults to `config.yaml` in the current directory),
serialises the findings into a zstd-compressed JSON envelope carrying an HMAC value made with the sensor's HMAC
key (the same payload `quirk sensor export-results` writes to a `.qpush` file, §8.6), and
delivers it to the console over HTTPS. The console responds HTTP 200 on success. If the
sensor was enrolled with `--allow-internal-console`, the local scan is also started with
`--allow-internal-targets`, so private-address targets in the segment can be scanned.

The push is retried up to 5 attempts with exponential backoff on connection errors,
timeouts and HTTP 5xx responses. Its exit code tells a scheduler what happened: `0`
delivered (HTTP 200) or already accepted (HTTP 409), `1` `sensor.yaml` missing or invalid,
`2` rejected by the console with a 4xx status, `3` console unreachable, `4` any other
push failure. In the `2`, `3` and `4` cases the payload is spooled. The console also
rejects a push whose `pushed_at` differs from its own clock by more than 15 minutes
(HTTP 422, `replay_window_exceeded`), so keep sensor clocks in sync.

If the console is temporarily unreachable, the payload is spooled to
`user_data_dir("quirk")/spool/` (Linux `~/.local/share/quirk/spool/`, macOS
`~/Library/Application Support/quirk/spool/`) and re-sent first-in first-out at the start
of the next invocation. The spool keeps at most 100 files or 500 MB; beyond that the
oldest payloads are evicted with a warning.

### 8.4 Merge into a unified CBOM

On the **console host**, run the merge after all sensors have pushed:

```bash
# Console host
quirk sensor merge

# Optional flags:
quirk sensor merge --stale-days 7       # ignore sensors silent > 7 days (default 30)
quirk sensor merge --db /path/to/quirk.db   # merge a database other than the default
```

`quirk sensor merge` has no output-directory flag: the CBOM files are written next to the
console database. It re-runs `compute_readiness_score()` and `build_cbom()` over the
console's own latest local scan session (`CryptoEndpoint` rows with no sensor) plus **every
endpoint from each sensor's latest push**. A sensor that pushed many endpoints contributes
all of them to the merged CBOM and score. Rows that sensors ingested before this release carry
no push marker, so for those the merge falls back to the rows within five minutes of that
sensor's newest row. Local scan rows are unchanged. The merge produces:

- One merged CBOM (`cbom-<YYYYMMDDTHHMMSS>.cdx.json` + `cbom-<YYYYMMDDTHHMMSS>.cdx.xml`)
- One unified quantum-readiness score
- A `coverage_warning` if any enrolled sensor is overdue, meaning it has not pushed within
  twice its expected cadence (`expected_cadence_minutes`, default 1440). Sensors silent
  for longer than `--stale-days` are treated as decommissioned and left out of the warning.

**Import air-gapped results in order.** When you carry results to the console as `.qpush` files,
import them oldest first. The most recently imported file becomes that sensor's latest push, even
if it is older than one you imported before it, and the merge then uses the older data.

With no endpoints at all (no sensor has pushed), the command prints `Score: None (None)` and
writes no CBOM. Its warning names any sensor enrolled within the last `--stale-days` days
that has not pushed as overdue; with no such sensor it reads "No endpoints found".

**MERGE-03 behaviour:** If two or more sensors scanned the same logical hostname and port
(e.g. `crypto.internal:443` appearing in both a DMZ and a PCI segment), the CBOM will
contain **one component per sensor** — distinct by `sensor_id` — not a de-duplicated
single entry. The CBOM builder embeds the `sensor_id` in the `bom_ref` of each host:port
component (for example `crypto/certificate/<sensor_id>:crypto.internal:443`), which is the
correct model for segmented networks where the same address exists in multiple security
zones.

The dashboard's **Sensors** page (`/sensors`) lists every enrolled sensor with its segment,
version and last push time, and a status of `current`, `stale` (no push within twice its
expected cadence) or `unknown` (never pushed). The **Executive** page shows the latest
merge's coverage warning when a sensor did not contribute, and a score gauge for each
segment. The gauges are recomputed from the current sensor rows each time the page loads
(from every endpoint of each sensor's latest push), not read back from the stored merge.

### 8.5 Windows sensor installation

QU.I.R.K. sensors run on Windows with no additional configuration beyond the standard
Python install.

**Prerequisites:** Python 3.10 or newer for Windows (the package declares `requires-python >=3.10`; CI exercises the Windows sensor on Python 3.11), available from https://www.python.org/downloads/

**Install:**

```powershell
# PowerShell (run as the service account that will run the sensor)
pip install "quirk-scanner[all]"
```

**Enroll and push (PowerShell):**

```powershell
# Enroll (one-time)
quirk sensor enroll https://<console-host>:8512 `
  --segment segment-windows `
  --sensor-id <sensor_id-from-quirk-console-enroll> `
  --api-token <per-sensor-token-from-quirk-console-enroll>

# sensor.yaml written to: $env:LOCALAPPDATA\quirk\quirk\sensor.yaml

# Push findings
quirk sensor push --scan-config C:\quirk\sensor-scan.yaml
```

**`sensor.yaml` path on Windows:** `%LOCALAPPDATA%\quirk\quirk\sensor.yaml`
(resolved via `platformdirs.user_config_dir("quirk")` at runtime, which on Windows is the
per-user local application-data folder with the application name repeated as the author folder).

**SIGTERM note:** The QU.I.R.K. scheduler uses `signal.SIGTERM` for graceful shutdown on
Linux/macOS but guards it with `sys.platform != 'win32'` (`quirk/cli/scheduler_cmd.py`).
On Windows, stop it with Ctrl+C instead of SIGTERM.

**nmap dependency:** `nmap` is used only when nmap discovery is selected: `--discovery nmap`
(which the dashboard passes for its nmap and wide port-scope options), or a yes to the
interactive wizard's nmap prompt, whose default is yes. The default built-in discovery of a
`--config` scan needs no `nmap` binary. If you use it, download the Windows
installer from https://nmap.org/download.html and confirm `nmap.exe` is accessible on `PATH`:

```powershell
nmap --version
```

### 8.6 Air-gap path (offline sensor → console)

For sensors with no network path to the console, use file-based export/import:

```bash
# Sensor host (no console connectivity)
quirk sensor export-results
# → writes <sensor_id>-<payload_id>.qpush to the current directory (or the --output directory)
```

Transfer the `.qpush` file to the console host via USB, secure file share, or any
out-of-band channel, then import:

```bash
# Console host
quirk console import-results /path/to/<sensor_id>-<payload_id>.qpush
```

The console decompresses the envelope, checks its required fields, rejects a `payload_id`
it has already imported (a second import of the same file exits with status 1 and ingests
nothing), and ingests the findings. The sensor must already be enrolled on the console
(`quirk console enroll --sensor-id <uuid>`, §8.2) or the import fails. Move the `.qpush` file
over a channel you trust. Run `quirk sensor merge` afterwards to produce the unified CBOM.

---

### 8.8 Windows sensor deployment (zip + Scheduled Task)

*(5.5.1 and later — frozen binary; no Python required on the sensor host)*

For Windows sensor hosts where a Python runtime is not available (or not desired),
download the pre-built `quirk-windows-<version>.zip` asset from the [GitHub Release](
https://github.com/0xD1g5/QU.I.R.K/releases) for your target version. Most releases from
5.5.1 on carry one (5.11.0 does not), and the version in the file name does not always
match the release tag, so take the asset attached to the release you want. The zip bundles
the frozen `quirk.exe` onedir executable together with `install.ps1`, `uninstall.ps1`,
and a `sensor.sample.yaml` reference config — no Python install required on the sensor
host.

#### Unsigned binary notice

The zip asset is **NOT Authenticode-signed**: the `quirk.exe` in the 5.25.0 asset has no
signature, and Authenticode signing is deferred. Windows SmartScreen or your endpoint
protection may therefore warn when you run `install.ps1` or `quirk.exe` for the first
time; approve it according to your organisation's policy. Operators who require signed
binaries should build from source until Authenticode signing is implemented.

#### Prerequisites

- **PowerShell 5.1+** (built in to Windows 10/11 and Windows Server 2016+). The examples
  below use `pwsh` (PowerShell 7); with the built-in Windows PowerShell run
  `powershell -File install.ps1 ...` instead.
- An enrollment token and `sensor_id` issued by `quirk console enroll` on the console host.
  See §8.1.1 for how to provision per-sensor push credentials via
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
   `%LOCALAPPDATA%\Programs\QUIRK` (**no admin elevation required**), runs
   `quirk.exe sensor enroll` to write the sensor config (this does not contact the
   console), tightens the sensor config ACL to the current user,
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
   | `-AllowInsecureConsole` | *(switch)* | Pass to accept an `http://` console URL for a non-loopback host (isolated lab networks); passes `--allow-insecure-console` to enroll. |

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

   Two things the installer does not do for you. First, `install.ps1` has no `-SensorId`
   parameter, so the `sensor.yaml` it writes holds a random `sensor_id` that the token does
   not belong to, and every push is rejected with HTTP 403 until they match. Open
   `sensor.yaml` in an editor and replace the value of `sensor_id:` with the UUID that
   `quirk console enroll` printed (editing the file in place keeps the ACL it was given).
   Second, it does not give the Scheduled Task a scan config. The task runs
   `quirk.exe sensor push --config "<sensor.yaml>"` with no `--scan-config`, and the default
   is a relative `config.yaml`, which will not normally exist in the task's working
   directory: the local scan then fails with a warning and an empty result set is pushed,
   so the console shows the sensor as current while nothing was scanned. Point the task
   at a scan config by its full path:

   ```powershell
   $cfg = "$env:LOCALAPPDATA\Programs\QUIRK\config\sensor.yaml"
   $exe = "$env:LOCALAPPDATA\Programs\QUIRK\quirk\quirk.exe"
   $action = New-ScheduledTaskAction -Execute $exe `
       -Argument "sensor push --config `"$cfg`" --scan-config `"C:\quirk\sensor-scan.yaml`""
   Set-ScheduledTask -TaskName "QUIRK Sensor Push" -Action $action
   ```

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
    --config "$env:LOCALAPPDATA\Programs\QUIRK\config\sensor.yaml" `
    --scan-config C:\quirk\sensor-scan.yaml
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
intact. A later `install.ps1` run does not reuse that identity, though: it always runs
`sensor enroll` without `--sensor-id`, and enroll keeps an existing `sensor.yaml` only
when its `sensor_id` matches the one being enrolled, so a reinstall writes a fresh random
`sensor_id` and HMAC key. Restore the console's `sensor_id` in `sensor.yaml` afterwards
(or keep a copy of the file and put it back).

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

Then re-run `install.ps1` on the Windows host with the new enrollment token and set `sensor_id` in `sensor.yaml` to the new UUID, as above.

---

### 8.9 Automatic Merge

*(5.5.0 and later)*

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
`false` for explicit manual-only control:

```yaml
console:
  auto_merge:
    enabled: false          # set to false to require manual 'quirk sensor merge'
    trigger_condition: all-sensors-in
    # cadence_window_minutes: 1440
```

The toggle is read at evaluation time (per push). Changing the setting takes effect on
the next push; any in-flight pushes or merge tasks that have already started are
unaffected. The console process reads the file named by the `QUIRK_CONFIG_PATH`
environment variable, or `./config.yaml` in its working directory when that is unset; if
the file is absent or unreadable the defaults apply (enabled, `all-sensors-in`).

#### Trigger conditions

`trigger_condition` selects how the console decides it is time to merge. Two values are
available:

**`all-sensors-in`** (default)

The merge fires once every sensor that still has an unrevoked token has pushed at least
once and the newest push is later than the latest `MergeRun`. This is the safest choice for
fixed-fleet deployments — you get a full-coverage CBOM as soon as the whole fleet has
reported. Revoked sensors are excluded from the "all in" set
(Phase 113 `revoked_at`), so revoking a decommissioned sensor does not block the merge.

**`cadence-window`**

The merge fires when the elapsed time since the last `MergeRun` reaches a configured
window (or immediately when no merge has run yet). The push that crosses the window
boundary triggers the merge with whatever has arrived at that moment. Sensors that are
overdue (never pushed, or no push within twice their expected cadence) are listed in the
merge run's `coverage_warning`, which the dashboard Executive page shows; a sensor silent
for more than 30 days is treated as decommissioned and left out. This mode suits deployments where not all
sensors push on the same cadence or where time-bounded merges are preferred over
full-coverage guarantees.

Set the window explicitly with `cadence_window_minutes` (integer, minutes). If omitted,
the console uses the `expected_cadence_minutes` of the first enrolled sensor (1440 — 24
hours — for every sensor enrolled with `quirk console enroll`).

```yaml
console:
  auto_merge:
    enabled: true
    trigger_condition: cadence-window
    cadence_window_minutes: 720    # merge on the first push 12+ hours after the last merge
```

#### Idempotency and duplicate merges

The `scanned_at` timestamps on sensor findings are never rewritten by a merge. The
background task re-checks, before merging, whether a `MergeRun` already covers the latest
push and does nothing if so, so near-simultaneous pushes normally coalesce to one merge.

#### Reading auto-merge outcomes

Every auto-merge writes an `IntegrationDelivery` audit row:

| Field | Success value | Failure value |
|-------|--------------|---------------|
| `destination` | `auto_merge` | `auto_merge` |
| `status` | `ok` | `failed` |
| `error_summary` | *(empty)* | Sanitised error message |

Query it directly in SQLite (the dashboard does not display these rows):

```sql
SELECT destination, status, error_summary, attempted_at
FROM integration_deliveries
WHERE destination = 'auto_merge'
ORDER BY attempted_at DESC
LIMIT 10;
```

A `status='failed'` row means the merge raised an exception after the sensor push
response was already sent — the push data is safe and fully ingested. Check the console
log (`logger.warning` is emitted alongside the audit row) to diagnose the merge failure,
then run `quirk sensor merge` manually to retry.

#### Manual merge is unchanged (AUTOMERGE-03)

The `quirk sensor merge` command remains available — the
same Option-A union CBOM, `coverage_warning`, and sensor-local `scanned_at`. Auto-merge
and manual merge call the same underlying `merge_scan()` function. Operators who need
explicit control, scripted post-push merge verification, or a one-off merge after
enabling `all-sensors-in` with auto-merge disabled can always run:

```bash
quirk sensor merge
# Or with custom options:
quirk sensor merge --stale-days 7 --db /var/quirk/quirk.db
```

---

### 8.7 All-configurations / settings reference (999.59)

This section covers the per-scanner timeouts, the output paths and the sensor identity
fields of a scan (999.59). Other sensor settings are documented where they are used: the
`console.auto_merge` block in §8.9, `QUIRK_SENSOR_IP_ALLOWLIST` in §8.1, and the
`sensor.yaml` written by `quirk sensor enroll` in §8. For the full single-host config reference see
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

These are the values used when a key is absent. The `fingerprint_seconds` default of 4
is the `standard` scan profile's value (`quick` 3, `deep` 6); the others do not change
with the profile. `dnssec_seconds`, `saml_seconds` and `kerberos_seconds` are accepted
but not currently read: the DNSSEC, SAML and Kerberos scanners always use 10 seconds.

See [`docs/timeout-retry-audit.md`](timeout-retry-audit.md) for retry policies and jitter.

#### `output.directory` — report output path

```yaml
output:
  directory: "./quirk-output"   # relative to CWD or absolute
  db_path: "./quirk-output/quirk.db"
```

`output.directory` and `output.db_path` are both required keys of a scan config (the
interactive wizard proposes `quirk-output` and `quirk-output/quirk.db`). All scan outputs
(HTML/PDF/DOCX reports, `cbom-<stamp>.cdx.json` and `.cdx.xml`, `findings-<stamp>.json`,
`executive-summary-<stamp>.md`, `technical-findings-<stamp>.md`,
`intelligence-<stamp>.json`) land in `output.directory`. On sensor nodes,
`quirk sensor push` runs the local scan with a temporary directory as its working
directory and discards it after the push, so a relative `output.directory` is deleted with
it; use an absolute `output.directory` if you want per-push artefacts retained on the
sensor host. Keep `output.db_path` relative and ending in `.db`: the push looks for the
scan database as `*.db` under that temporary directory, and a database anywhere else (or
named `*.sqlite`) is not found, so the push carries no findings.

#### Sensor identity fields in scan output

| Field | Location | Description |
|-------|----------|-------------|
| `sensor_id` | `CryptoEndpoint` DB column; embedded in the `bom_ref` of each host:port CBOM component | UUID minted by `quirk console enroll` and passed to the sensor with `quirk sensor enroll --sensor-id` (a random UUID if omitted); `nullable=True` (NULL = implicit local sensor, backward-compatible with scans from before sensors existed, i.e. before 5.5.0) |
| `segment` | `CryptoEndpoint` DB column | Network-segment label passed via `--segment` at enroll time; the Executive page shows a score gauge per segment of the latest merge |

These two fields are the differentiators for MERGE-03 — two findings with identical
`host:port` but different `sensor_id` values are intentional and correct; they represent
the same logical endpoint discovered independently in two network segments.

---

## 9. Hardware Scanning

Hardware scanning fingerprints network and infrastructure devices (switches, routers,
firewalls, load balancers, HSMs, management controllers), assigns CNSA 2.0 remediation
tiers, and annotates crypto-bridge topology. Two fingerprinting methods need no extra and
no flag: SSH-banner matching runs for every SSH endpoint a scan finds, and HTTP-management
probing follows for each one whose banner names no known vendor. The SNMP sweep, Modbus/TCP and BACnet/IP probing are opt-in and need
the `[hw]` extra; with `[hw]` installed, an SSH host those two methods leave unidentified also
gets an SNMP probe even when SNMP is off (§9.1). Operators who have not installed the `[hw]` extra and do not manage network
hardware can complete §1–§8 without interruption — the scanner runs cleanly with the
extra absent.

### 9.1 Enable SNMP Scanning

**Step 1 — Install the `[hw]` extra.**

```bash
pip install 'quirk-scanner[hw]'
```

This extra adds `pysnmp` and `sysdescrparser` (SNMP) and `pymodbus` and `bacpypes3`
(Modbus/TCP and BACnet/IP). See the §2.2 optional extras matrix for a full dependency list.

**Step 2 — Enable SNMP in your config.**

Add the following two keys under the `connectors:` block in `config.yaml` (the `--enable-snmp`
command-line flag turns the first one on without editing the file):

```yaml
connectors:
  enable_snmp: true          # default: false — must be explicitly set to opt in
  snmp_community: "public"   # SNMPv2c community string; default: "public"
```

Under `scan:` these keys do not load: the config loader rejects them with
`TypeError: ScanCfg.__init__() got an unexpected keyword argument 'enable_snmp'`. When
`snmp_community` is not set in the YAML, the `QUIRK_SNMP_COMMUNITY` environment variable
(which the dashboard's Connectors panel uses) supplies it; an explicit YAML value wins.

`enable_snmp` defaults to `false`. If you omit the key or leave it as `false`, the
scan runs cleanly with no error and the SNMP sweep of every scanned host does not run.
Devices fingerprinted from SSH banners or HTTP management pages still appear. With `[hw]`
installed, though, `enable_snmp: false` does not stop all SNMP traffic: hardware
fingerprinting still probes each SSH host whose banner and management page identified no
vendor (SNMPv2c with the community `public`, or SNMPv3 when a credential matches the host),
and records any vendor it reads. Without `[hw]` no SNMP probe is sent.

**Step 3 — Run the scan.** The SNMP probe executes **after the TLS, SSH and PQC-probe phases
complete** and targets every unique host that produced a TLS, SSH or PQC-probe endpoint,
not just SSH hosts. No additional target list is required. Each probe uses the
`scan.timeouts.default_seconds` timeout (5 seconds unless you change it).

**What QUIRK probes.** Three SNMP OIDs are queried per host:

| OID | Name | Purpose |
|-----|------|---------|
| `1.3.6.1.2.1.1.1.0` | `sysDescr` | Vendor and model string — primary parse target |
| `1.3.6.1.2.1.1.5.0` | `sysName` | Device hostname |
| `1.3.6.1.2.1.1.2.0` | `sysObjectID` | Enterprise OID — fallback vendor identification |

**Sample output.** Discovered hardware devices are summarised in the executive summary
(`executive-summary-<stamp>.md`) under a Hardware PQC Advisory heading; the per-device
rows are in the HTML and DOCX reports and on the dashboard's Hardware page:

```text
### Hardware PQC Advisory

> **Advisory only — not included in readiness score.** 3 hardware device(s) fingerprinted. Tier 1 (replace by 2030): 1, Tier 2 (firmware upgrade 2030–2033): 1, Tier 3 (monitor, re-evaluate 2033+): 1, N/A (EOL before migration window): 0. See full report for device-level detail.
```

For the full config-key reference (all `scan.*` defaults, type constraints, and
advanced options), see [`docs/configuration.md`](configuration.md).

---

### 9.1.1 SNMPv3 Auth+Priv Scanning (Phase 139)

QUIRK also supports authenticated, encrypted SNMPv3 scanning as an upgrade path alongside
the SNMPv2c community-string scanning above. SNMPv3 credentials are configured per-host, not
globally — a network may have a mix of v3-capable and v2c-only devices.

**Configure a v3 credential.** Add a `connectors.snmp_v3_credentials` entry keyed by host
(see `docs/configuration.md` for the full field reference). An entry keyed `default`
applies to every host that has no entry of its own. `auth_protocol` accepts `SHA`
(the default), `SHA224`, `SHA256`, `SHA384` or `SHA512`; `priv_protocol` accepts `AES`
(the default), `AES128`, `AES192` or `AES256`. Any other `auth_protocol` is rejected when
the config loads, and so is any other `priv_protocol` on an entry that sets `priv_key_env`
(an entry without a privacy key never uses its `priv_protocol`):

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
3. **none** — if neither v3 nor v2c gets a response, no vendor or model is identified from
   SNMP. The host still gets a hardware row: an existing fingerprinted row whose vendor is
   still `Unknown` has its SNMP column set (`none`, or `v3-failed-fell-back` /
   `v3-protocol-mismatch` when v3 was tried), and a host with no row gets a new `Unknown`
   device row on port 161 marked Tier N/A.

Each outcome gets its own label rather than a generic "SNMP succeeded", with one known
exception: an authenticated but unencrypted v3 session (authNoPriv) is labelled
`v3 noAuthNoPriv`, the same as an unauthenticated one. See
`docs/report-interpretation.md` for the distinct labels this produces in reports and the
dashboard, including the important distinction between an intentional v2c-only scan and a
genuine v3 credential failure (`v3-failed-fell-back`).

---

### 9.2 CNSA 2.0 Remediation Tiers

Each hardware device fingerprinted from an SSH endpoint or by the Modbus/BACnet OT pass is
assigned a tier derived from CNSA 2.0 (Commercial National Security Algorithm Suite 2.0)
guidance on post-quantum migration timelines. A device found only by the SNMP probe skips this derivation and is stored as
Tier N/A whatever its vendor or EOL date, so read Tier N/A on a port-161 row as "not tiered".

| Tier | Severity | Deadline | Meaning |
|------|----------|----------|---------|
| Tier 1 | HIGH | Replace by 2030 | No PQC upgrade path — device must be replaced |
| Tier 2 | MEDIUM | Upgrade firmware 2030-2033 | PQC firmware upgrade path exists |
| Tier 3 | LOW | Accept + monitor, re-evaluate 2033+ | The catalog records PQC support (or the vendor is silent and the match is high confidence) |
| Tier N/A | INFO | EOL before PQC migration window | Device won't survive to the migration deadline |

**How the tier is derived** (`quirk/scanner/hardware_tier.py`). A device whose EOL date is
before 2030-01-01 is Tier N/A, checked first. Otherwise a low or unknown fingerprint
confidence caps the tier at Tier 2 (Tier 3 only when the catalog says PQC is supported).
At medium or high confidence the catalog's `pqc_status` decides: `unsupported` is Tier 1,
`partial` is Tier 2, `supported` is Tier 3, and `vendor-silent` is Tier 3 at high
confidence and Tier 2 otherwise.

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
still carries a mandatory caveat: "Based on SNMP-derived network-path evidence; not
independently confirmed by traffic inspection." (verbatim in the HTML and DOCX reports and
the dashboard `/hardware` tab; the executive summary carries an equivalent sentence). See
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
- **One request at a time per fingerprinted endpoint.** For each endpoint it fingerprints,
  QUIRK runs the Modbus probe and then the BACnet probe in sequence, each sending one request
  at a time. Endpoints are fingerprinted in parallel, though, so a host with more than one
  SSH endpoint is probed once per endpoint and can have two OT/ICS probes outstanding at once.
- **One-strike circuit breaker.** Any anomalous response — a timeout after contact was
  made, a malformed frame, a connection reset, or an exception — ends that probe on the
  spot and records "Probe aborted". There is no retry and no backoff, deliberately
  stricter than QUIRK's standard scan retry policy elsewhere. The Modbus and BACnet probes
  are independent of each other: an aborted Modbus probe does not stop the BACnet probe of
  the same host.
- **Short, dedicated timeout.** Both probes use a conservative default timeout (2s),
  shorter than QUIRK's general scan timeout, to minimize the time spent holding a
  connection open against fragile embedded devices.

**Enable the flags** (targets come from the config's `targets` block, or from `--targets-file`; there is no `--target` flag):

```bash
python run_scan.py --config config.yaml --enable-modbus --enable-bacnet
```

**Result labeling.** Every OT/ICS probe attempt resolves to one of five states, shown
distinctly in reports and the dashboard (never collapsed into a generic "scanned"/"not
scanned" binary):

| State | Meaning |
|-------|---------|
| Identified (Modbus / BACnet badge) | Vendor/model/firmware successfully read |
| No response | Nothing usable answered: for Modbus the TCP connection was never established (port closed or host unreachable); for BACnet no I-Am came back within the timeout |
| No match | A response was received but carried no usable vendor identity |
| **Probe aborted** | The one-strike circuit breaker fired — a real anomalous response, including a timeout after the Modbus connection opened or during the BACnet ReadProperty, not "nothing happened" |
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

**`quirk cve status` — catalog freshness.** Same table shape as `quirk qramm status` (source,
last verified, days remaining, status); `quirk compliance status` prints a different, per-framework table:

```bash
quirk cve status
quirk cve status --format json
```

The text form prints one row: the source (`NVD`), the snapshot's `last_verified` date, the
days remaining before the 30-day staleness threshold, and a FRESH/STALE status. With
`--format json` it prints the source, `last_verified`, a `verdict` and the catalog entries
(vendor, model, CVE id, severity, `affected_before`, source URL). Exit code `0` when fresh,
`1` when stale — the same 0/1 convention used by `quirk qramm status` (§7) so CI and
pre-engagement scripts can gate on it. As with `quirk qramm status` (but not
`quirk compliance status`, which always uses the real date),
`QUIRK_CI_STALENESS_OVERRIDE_DATE` overrides "today" for staleness-gate testing; a malformed
override value is logged as a warning and ignored, falling back to the real system date
rather than crashing the command. The override moves the text output and the exit code, but
the `verdict` printed by `--format json` always uses the real date, so read the exit code when
you use the override.

**The CVE advisory scanner signal.** During report/dashboard generation, QUIRK calls
`correlate_device(vendor, model, firmware)` for every device with a known (non-"Unknown")
vendor. Firmware comes from whatever protocol already fingerprinted the device (Modbus/BACnet
firmware strings only; devices fingerprinted by SNMP, SSH or HTTP carry no firmware string, so
only catalog entries without a version boundary can match them). Two confidence levels:

- **high confidence** — the device's parsed firmware version falls inside a CVE entry's
  documented affected range (an NVD "prior to X" boundary, exclusive `<`).
- **medium confidence** — only a vendor+model match exists (the curated entry has no
  version boundary); QUIRK does not guess whether the specific firmware is actually
  affected. An entry that does have a version boundary never matches a device whose
  firmware string is missing or cannot be parsed.

**Firmware CVE matches are advisory-only — never a severity finding, and never a score or
remediation-tier input.** This is a hard architectural boundary (CVE-01/CVE-04): the CVE
correlation module imports nothing from `intelligence/scoring.py` or `hardware_tier.py` (it
imports only standard-library modules), and a dedicated regression test
(`tests/test_cve_score_guard.py`) enforces in CI that no score weight is CVE-derived and that
`assign_tier()` ignores CVE attributes. Operators
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
that record device-identity evidence and honest probe outcomes. None of these
are rendered as report or dashboard columns yet (deferred to a later release) — they are
scanner-internal fields today, documented here so operators understand the underlying data
model and the retention/last-known-good behavior it drives.

- **`ssh_host_key_fingerprint`** — the SHA256 SSH host-key fingerprint QUIRK's existing
  `ssh-audit` run already captures for the device. Because a host key is tied to the device
  itself (not its current IP), this fingerprint is an identity signal that would survive a
  DHCP lease renewal or a re-IP, which a `host:port` match alone cannot. QUIRK records it but
  does not yet match devices on it: drift reconciliation, the last-known-good projection and
  history retention all key on `(host, port)`.

- **`match_confidence`** — `high` when a `ssh_host_key_fingerprint` was captured for the
  device, `low` when the device could only be matched on `host:port`. `low` covers three
  distinct cases operators should be aware of: HTTP-only devices, SNMP-only devices, and —
  importantly — **SSH-reachable devices scanned from a host that does not have `ssh-audit`
  installed**. Operators who want `high`-confidence coverage across their SSH-reachable
  hardware should install `ssh-audit` on the scanning host (see §6.2). A device found only by
  the standalone bulk SNMP sweep (a port-161 row built outside `fingerprint_one()`) gets no
  `match_confidence` value at all (NULL), not `low`.

- **`probe_status`** — `success` when the fingerprinting probe got any response at all,
  including an honest `vendor="Unknown"` result (an unrecognized device that still answered
  is a successful probe, not a failure). `failed` means the probe errored, timed out, or
  nothing on the device answered at all.

**`match_confidence` is not the same field as the pre-existing `confidence` column.**
`confidence` (used elsewhere in hardware fingerprinting, e.g. §9.2's tier-assignment cap) describes
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
- **No separate command or schedule.** The purge runs automatically during every full scan's
  hardware-persistence step (a `--check-in` re-probe does not run it) — there is no
  `quirk hardware purge` equivalent for drift events and no cron job to configure.

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
re-verification procedure the other date-gated catalogs use (never bump the date without
actually re-verifying it against the sources):

1. Re-verify each `EOL_TABLE` entry against its `source_url` — confirm the published EOL/EOS
   dates have not changed and are still cited to a live vendor or aggregator page.
2. Bump `EOL_TABLE_META["last_verified"]` in `quirk/scanner/hardware_eol.py` to today's ISO date.
3. Commit with `chore: re-verify hardware_eol catalog (YYYY-MM-DD)`.

**What EOL data changes about a scan.** As of Phase 155, `HardwareDevice.eol_date` is populated
from this catalog automatically during fingerprinting via `apply_eol_date()`. Most fingerprint
paths (SSH banner, HTTP management, SNMP, Modbus, BACnet) converge on a single call site inside
`fingerprint_one()`; the standalone SNMP-only bulk-discovery sweep in `run_scan.py` builds its own
`HardwareDevice` rows outside that waterfall and calls `apply_eol_date()` separately at its own
construction site, so rows from both paths get `eol_date` from the catalog, not just the ones
routed through `fingerprint_one()`. (If a fingerprint raises before that terminal step, the
`failed` row it returns has no `eol_date`.) This interacts with the pre-existing (Phase
128) CNSA 2.0 tier-assignment rule in `hardware_tier.py::assign_tier()`: a device whose EOL date
falls before 2030-01-01 is assigned **Tier N/A**, regardless of its PQC support status. Because
the EOL catalog was dormant before this phase, populating a real EOL date can legitimately move
a previously Tier 1/2/3 device to Tier N/A on its very next scan. **This is intended behavior,
not a regression** — a device whose vendor has already end-of-lifed it is not a candidate for
PQC remediation planning in the same sense as a supported device, so Tier N/A takes it out of
the PQC tiers: the dashboard and the reports label it "EOL before PQC migration window" (an INFO
advisory on the dashboard) instead of giving it a PQC deadline. Operators who see a device's tier shift to Tier N/A after
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
behind a collapsible "Show older lifecycle changes (N)" disclosure so the section doesn't dominate the page on
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

**`--check-in` is a bare boolean opt-in on `run_scan.py`, not a `--profile` value.** If you pass
`--profile` with it, the profile has no effect — `--check-in` is a separate short-circuit that
fires immediately after database initialization, and none of the timeout, concurrency or
connector defaults a profile sets are read by the check-in re-probe.

**What it does and does not do:**

- **Targets** are the latest successful `HardwareDevice` row per `(host, port)` — the same
  last-known-good projection described in §9.6 — never a fresh network sweep.
- **No discovery.** Network/CIDR discovery, nmap liveness pre-passing, and target expansion are
  all skipped entirely.
- **No non-hardware scanner phases.** TLS, SSH, JWT/API, container, source-code, and cloud KMS
  scanning are all skipped. Only the hardware-fingerprinting probe family is re-run.
- **The device's stored `fingerprint_method` decides where re-probing starts.** An `ssh_banner`
  device gets a fresh SSH banner grab followed by the normal fingerprint waterfall, so the
  HTTP-management and SNMP probes still fire when the new banner no longer identifies the
  vendor; an `snmp` device skips the HTTP-management probe; a `modbus` or `bacnet` device gets
  only the OT/ICS probes; an `http_mgmt` device, or one with no recorded method, gets the full
  waterfall. With `connectors.enable_bacnet` on, the BACnet probe also runs against every
  re-probed device, as it does in a normal scan.
- **`modbus`/`bacnet` devices are skipped** when `connectors.enable_modbus` /
  `connectors.enable_bacnet` are off, exactly as they are during a normal scan — a check-in never
  force-enables OT/ICS probing.
- **An empty fleet is a clean no-op.** If no `HardwareDevice` rows exist yet (no prior scan has
  ever fingerprinted a device), `--check-in` prints an operator message and exits `0` with **zero
  hardware or drift rows written** — it never errors out (the database file itself is still
  created and migrated first, because the short-circuit runs after database initialization).
- **Persists only hardware rows** — `HardwareDevice`, `hardware_drift_events` and
  `vendor_pqc_trend_events` — through the same `persist_and_reconcile()` chokepoint (§9.7)
  used by a full scan, which also applies the history-retention purge and the lifecycle
  notifications of §9.12 (when those are configured, each delivery attempt also adds an
  `integration_deliveries` audit row). Every `HardwareDevice` and drift row it writes carries
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
check-in carry `is_partial_scan=True`. They stay visible where the equivalent full-scan data
would be — the `/hardware` and `/compare` dashboard pages, `GET /api/hardware/drift`, and
`CompareResponse.hardware_drift` — marked rather than filtered out: drift events show a
"Partial re-probe" badge on the dashboard, and the HTML and DOCX reports and the executive
summary add a partial re-probe banner when check-in device rows are present (see
`docs/report-interpretation.md`'s check-in section for the exact reader-facing wording). A
check-in never writes a scan record (no `crypto_endpoints` rows), so it does not appear in the
scan lists that feed `/api/scans` or `/api/trends`.

**Putting a check-in on a schedule (Phase 162, HWLC-20).** Rather than remembering to run
`--check-in` by hand, register it with the scheduler:

```bash
quirk schedule add --name nightly-checkin --cron "0 2 * * *" --check-in
quirk scheduler run      # the long-running dispatch loop
```

- **No `--target` is needed or accepted as meaningful.** A check-in re-probes the fleet already
  recorded in the database (`latest_successful_hardware_devices()`), so there is nothing to aim
  it at. With `--target` omitted, the stored target reads `(known fleet)` in
  `quirk schedule list` and on the dashboard; a `--target` you do pass is stored but ignored.
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

**Confirmation gate.** Like the tier, bridge-evidence and EOL-state drift events of §9.7 (CVE-delta
events are not gated), a vendor trend event only fires after N-of-M confirmation (N=2 of M=3,
the same `DEFAULT_N`/`DEFAULT_M` the drift events use) —
but the window here samples the **3 most-recently-scanned distinct devices of that vendor**, not
repeated scans of one device and not the vendor's entire fleet. This means a single noisy or
repeatedly-rescanned host cannot, by itself, trigger a vendor-level event, but it also means the
signal reflects a recent sample rather than an exhaustive fleet-wide census — a vendor with many
active devices is judged on its 3 most-recently-seen ones. It also means a vendor's first-ever
observed device never produces an event — there is nothing to compare it against yet.

**Querying it.** `GET /api/hardware/vendor-trends` returns the bounded, newest-first list:

```bash
curl -H "Authorization: Bearer $QUIRK_API_TOKEN" \
  "http://127.0.0.1:8512/api/hardware/vendor-trends?limit=50"
```

- Authenticated with the same dashboard bearer token as the other authenticated dashboard API
  routes (§2.4; `/api/health` and `/api/config` are open, and the sensor push route takes a sensor
  token instead) — no separate credential.
- `limit` accepts 1–200 (default 50); a `truncated: true` flag in the response body indicates
  more rows exist than were returned.
- Each event exposes `vendor`, `event_type`, `old_value`, `new_value`, `detected_at`, and
  `confirmed_at` — no host/port, no score, no numeric field.

**Advisory-only, no score contribution.** Like `hardware_drift_events`, vendor PQC trend
events never affect the readiness score — `quirk/intelligence/scoring.py` imports neither
`quirk/scanner/hardware_drift.py` nor `quirk/models_util.py`, and `tests/test_cve_score_guard.py`
enforces in CI that the scoring module never references `hardware_drift` and that no
vendor-trend module imports the scoring engine or references its weights.

**Now rendered in the reports.** As of Phase 161 (HWLC-19) vendor PQC trend events are
rendered in the HTML (and the PDF made from it), DOCX and CLI technical reports and on the dashboard `/hardware` page — see
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
with the `notify_on_hardware_lifecycle` key in the `notifications:` block of the YAML file that
`QUIRK_CONFIG_PATH` names in the scanning process's environment — the scan's own `--config` is
not consulted, so with `QUIRK_CONFIG_PATH` unset nothing is sent and nothing is audited. See
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
(one row per configured channel). Qualifying events from one hardware-persistence batch are sent
as one summary (a scan run with SNMP enabled persists, and notifies, its SNMP-only devices as a
second batch), and the `scan_id` column carries a composite identifier of the form
`{host}:{port}:{event_type}:{event_id}` naming the first qualifying drift event of that
summary, so an alert can be traced back to the drift event that produced it.

**Failure isolation**

Notification delivery is advisory-only and can never abort a scan. The dispatch hook sits inside
`persist_and_reconcile()` and is wrapped so that a failing SMTP server, an unreachable webhook, a
misconfigured credential, or an entirely uninstalled notification extra is logged (and a failed
send is also audited) but
leaves the scan, the sensor push, or the air-gap import completely unaffected. If you enable
notifications and see nothing arrive, check the `integration_deliveries` rows first — the attempt
will be recorded there with its error summary even when delivery failed. No rows at all after a
qualifying change means `QUIRK_CONFIG_PATH` does not name the config that enables the key, that
config has neither an `email:` nor a `webhook:` block, or the file failed to parse (a malformed
YAML file disables notifications silently, with no log line).

---

## 10. Discovery Liveness Pre-Pass

As of Phase 145 (DISC-03), every nmap-discovery batch (a scan run with `--discovery nmap`) runs a cheap TCP-based liveness
pre-pass before its full port sweep. This shrinks scan time on large, sparse ranges by
skipping the expensive `-sT` sweep against hosts that never answer. A run that reuses cached
discovery results (`--cache --resume`) runs no pre-pass at all (see §10.5).

### 10.1 What it does

Before `run_nmap_discovery()` sweeps a batch, QUIRK runs `run_nmap_liveness_check()`
against that same batch: an `nmap -sn -PS<ports>` probe (host discovery only — `-sn` —
using a TCP SYN ping on the given ports, `-PS`, with `-n` to skip DNS resolution). Hosts
that respond are swept normally; hosts that do not respond are excluded from the sweep
and recorded as `liveness_skip` rows (see §10.5 and `docs/report-interpretation.md`).

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
privileges are not available, nmap automatically substitutes a TCP `connect` call for the
SYN probe. QUIRK does not try to detect the substitution from the probe's results; it
decides from the scanning process's own privileges instead.

QUIRK checks `os.geteuid()` exactly once per scan (via `_is_privileged()` in
`run_scan.py`) and, whenever the process is **not** confirmed to be running as root —
including on platforms that provide no way to check at all, such as the Windows sensor
build, where `os.geteuid` does not exist — it treats that as "not privileged" and
discloses the possible downgrade two ways:

- A logger message: *"liveness pre-pass may have silently degraded from a SYN probe to
  a TCP connect probe (no raw-socket privileges detected) — results remain valid but the
  pre-pass will run slower than intended."*
- A single persisted `privilege_fallback` advisory row in the scan artifact (one per
  scan, not one per batch — see §10.5).

**Results remain valid either way** — a TCP connect probe still correctly determines
host liveness, it is just slower than a raw SYN probe. Running the scan as root (or via
`sudo`) removes the advisory entirely, because `_is_privileged()` then returns `True`
and the fallback-disclosure call never fires.

### 10.4 What happens on failure

If the pre-pass itself fails (nmap errors or times out) for a batch, QUIRK
does not lose that batch's hosts: it logs the failure and sweeps the entire batch
unfiltered, exactly as if no pre-pass had run. (When nmap is not installed at all, the batch
loop never starts: the scan falls back to builtin discovery, or fails for the `top1000`/`all`
port scopes.) A batch where every host is
non-responsive short-circuits entirely — the sweep subprocess is never spawned for a
fully-dead batch.

### 10.5 Where to look afterward

Every liveness-skipped host produces its own `CryptoEndpoint` row in the scan artifact
with `scan_error_category="liveness_skip"` and the real host address, so a skipped host
is never silently dropped from that scan's record. The exception is a rerun that reuses cached
discovery results (`--cache --resume`): it replays only the cached targets, runs no pre-pass,
and records no `liveness_skip` or `privilege_fallback` rows, so hosts the original run skipped
are absent from the rerun's record. See `docs/report-interpretation.md` for how
to interpret `liveness_skip` and `privilege_fallback` rows in a delivered report.

> **Operator note:** the total number of undetermined (skipped) hosts is now surfaced
> as an aggregate "Hosts undetermined" count in the HTML (and PDF) and DOCX reports, the
> executive summary and the CLI summary table (not the technical summary or the dashboard) — see
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
  numbers agree. One exception: on a resumed scan, a batch skipped as already complete
  prints `Discovery: batch N/M — skipped (completed on a prior run)` and does not update
  the dashboard line until the next batch that actually runs.

### 11.2 Per-batch timeout scaling (DISC-05)

Each nmap subprocess call inside the batch loop (both the Phase 145 liveness pre-pass
and the full discovery sweep) now receives a timeout computed per batch instead of a
single fixed value for the whole scan:

```
timeout_seconds = min(300, 30 + 0.26 * batch_size)
```

- **Base:** 30 seconds.
- **Per-host scaling:** 0.26 seconds added per host in the batch.
- **Ceiling:** clamped to 300 seconds per nmap call — the value the dashboard passed on every
  call before Phase 146 (the CLI's old `--nmap-timeout` default was 1800 seconds). A small batch (e.g. one host) finishes
  its timeout budget in well under a second over the base; a full 1024-host batch stays
  at or below the 300s ceiling.

### 11.3 Per-batch timing template (DISC-05/DISC-06/DISC-07)

Alongside the timeout, each batch also selects an nmap `-T` timing template for its port
sweep (the liveness pre-pass does not get one) based on its own size: `-T4` (aggressive)
for batches at or below 256 hosts, `-T3` (normal, nmap's default) for batches larger than
that. In practice `-T4` only changes nmap's RTT timeouts and caps its TCP scan delay at
10 ms — `_default_nmap_args` already hardcodes `--max-retries 1`, `--host-timeout 10s`,
and `--max-parallelism 100`, and per the nmap documentation explicit fine-grained options
take precedence over the template's defaults for those values.

### 11.4 `--nmap-timeout` no longer governs chunked discovery

The CLI's `--nmap-timeout` flag is deprecated and has no effect: nmap discovery always runs
through the chunked batch loop, whose per-batch formula in §11.2 replaces it, and no code
path reads the flag any more (its `--help` text says so). The dashboard's spawned
`run_scan.py` subprocess also no longer passes a static `--nmap-timeout 300` argument; the
300s ceiling is enforced entirely by the formula's own clamp.

### 11.5 CLI and dashboard share one discovery implementation (DISC-06)

The dashboard does not run its own separate discovery logic — it spawns the same
`run_scan.py` CLI entry point as a subprocess, so both surfaces execute exactly one
discovery code path. This is locked by a static/AST-based regression test
(`tests/test_cli_dashboard_discovery_parity.py`) asserting a single call site each for
`run_nmap_discovery()` and `run_nmap_liveness_check()`, both lexically inside the Phase
144 batch loop, and confirming `jobs.py` never calls `run_nmap_discovery(` directly.

## 12. OT/ICS Recurring-Scan Safety

Phase 141 (§9.4) introduced Modbus/BACnet fingerprinting with a deliberately narrow safety
model — read-only requests only (one Modbus Read Device Identification request; one BACnet
Who-Is plus two ReadProperty requests), a one-strike circuit breaker, and off-by-default
flags. That safety model was designed and validated for a **one-off, operator-initiated scan**.
Phase 156 closes a gap that model didn't cover: what happens when those same flags are wired
into a *recurring*, unattended scheduled scan.

**Why the gate exists.** The Modbus and BACnet scanners were designed for one read-only
probe per host in a single engagement, run by a human who has obtained authorization and is watching the
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
   Floor](configuration.md#otics-recurring-scan-cadence-floor-phase-156) section for
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
appear in scheduled-scan results stop showing up, open that run's generated config,
`scan-config.generated.yaml`, in `<output directory>/scheduled/<schedule name>/<timestamp>/`. A
suppressed run has no `enable_modbus`/`enable_bacnet` keys under `connectors` there. Each
suppressed dispatch also logs a line of this shape at INFO level (logger `quirk.cli.scheduler_cmd`):

```
OT/ICS probing suppressed for schedule 'nightly-plant-scan' (cron='0 * * * *'): removed keys ['enable_modbus', 'enable_bacnet'] — reason: cadence floor
```

It names the schedule, the exact keys stripped from the generated config, and the reason
(`cadence floor`, or `opt-in not enabled` when the recurring opt-in is off). `quirk scheduler run`
configures no log handler, so this INFO line is not printed to the terminal by default; the
generated config is the record you can always check.

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
   `reports` stage, newest first, with the stage and status of its most recent checkpoint
   and its age. Rows older
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
resumed run, in the `Resuming scan <id>: N stages complete` line. A batch that is skipped on resume
prints `Discovery: batch N/M — skipped (completed on a prior run)` instead of the usual progress line.

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
scan summary's `Hosts undetermined` count and, in the scan's findings, as INFO
`Informational protocol observation` findings with the detail `liveness pre-pass: no response`.
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
(at the config template's default `db_path`) the SQLite DB. Apply the same handling
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

### 14.1 One-time ticket re-key (first released in 5.19.0 / IDENT-01)

Finding fingerprints — the dedup key used to decide "have I already opened a ticket for this" —
are now computed from a **normalized** title (`quirk/ticketing/base.py::compute_fingerprint`,
routed through `quirk.compliance.normalize_finding_title`). Before Phase 178 (5.18.0 and earlier),
the fingerprint hashed the raw title text. The normalization drops the label or version that five
container-image finding titles interpolate: `End-of-life <label> in container image`,
`Severely outdated Python cryptography package (<version>) in container image`,
`Outdated Python cryptography package (<version>) in container image`,
`Outdated pyOpenSSL package (<version>) in container image`, and
`Outdated libgcrypt (<version>) in container image`. The table also maps the dashboard's
`"Certificate expiring in {N} day(s)"` title, but `quirk ticket create` reads the scan's
`findings-*.json`, whose certificate-expiry title (`TLS certificate expiring within 30 days`) never
carried a day count, so ticketed certificate-expiry findings keep their fingerprint.

**The affected families are those five container-image titles.** Every other title the scan
writes hashes to the same fingerprint as before.

**What operators will see on the next `quirk ticket create` run:** any finding from those five
families that already has an open ticket will look "new" exactly once, because its normalized fingerprint
no longer matches the fingerprint stored on the existing ticket. Jira stores the fingerprint as a Jira **label**
on the issue (`labels: [fp]`, matched via the JQL `project = "<key>" AND labels = "<fp>"`); ServiceNow stores it in the
incident's **`correlation_id`** field (matched via `sysparm_query=correlation_id=<fp>`). Neither
lookup finds the old-fingerprint record, so exactly ONE duplicate ticket is created per affected
finding. After that single miss, the new fingerprint is stable and dedup works normally on every
subsequent run — this is a one-time event, not a recurring duplication.

No migration is performed against already-issued tickets: QUIRK does not rewrite the
fingerprint stored on existing Jira issues or ServiceNow incidents. If
you want to avoid seeing the duplicate, close the old ticket for that finding manually before
running `quirk ticket create` again; QUIRK will open a fresh one under the new, stable fingerprint.

**This is not a dedup regression.** Two different vulnerable container-image libraries found at
the same host and port still produce two distinct tickets after this change, exactly as before —
fingerprinting deliberately does NOT collapse findings that differ only in which library or
package they name (T-178-01). Only the five container-image titles above changed fingerprint;
everything else that already deduplicated correctly continues to do so.

## 15. Remediation Tracking Scope (first released in 5.19.0 — Phase 179)

Phase 179 changed what a remediation item *is*. Previously, roadmap items were computed fresh on
every scan from live evidence counters and were never stored in the database (only written into
that scan's report files), and
progress could only ever be reported as a boolean (an item is either present in the current
roadmap or it isn't). A remediation item is now a stable, kind-derived ID (e.g.
`plaintext-http-exposure`) with its constituent findings recorded explicitly, per scan, in the
database. That is what makes "6 of 8 verified closed" an expressible fact rather than an
approximation, and fixing the 8th leaves a closure record instead of the item silently vanishing.
A closure is recorded on the scan that observed the fix, and the earlier scan's record of that
finding is marked closed too (see §16, "The four states").

Three things operators should understand about how this tracking behaves:

- **A per-scan scope signature is recorded**, capturing what the scan actually covered — port
  scope, `--profile`, which optional extras were enabled, whether credentials were supplied, and
  which sensors are enrolled with the console (the enrolled fleet, not the sensors whose data is in
  this scan, so enrolling or removing a sensor between two scans makes them non-comparable). Closure
  comparisons are refused outright when two scans' signatures
  don't match, rather than silently comparing scans that covered different ground. A re-engagement
  run with `--profile quick` cannot be misread as having verified — let alone closed — findings
  that only a deeper prior scan actually covered.
- **Probe health is asserted positively, per protocol family, not inferred from the scan exiting
  cleanly.** A scan can exit 0 while a specific probe (SSH, TLS, JWT, etc.) silently produced no
  usable evidence — this is precisely the failure mode a prior integration defect
  demonstrated for SSH. Health is now derived from whether that family actually produced evidence,
  not from the absence of an error.
- **A detected finding is `open`; `not_observed` means nothing was verified.** A finding is never
  inferred `closed` from absence. A finding the scan detected is recorded `open`. `not_observed`
  is kept for items where nothing was checked, such as counter-only roadmap items, and for scans
  stored before this release, which are not rewritten and so still show their detected findings
  as Not Verified (see §16, "The four states"). Never read `not_observed` as "there's nothing
  there".

See `docs/configuration.md` §"Remediation Aliases" for the related `remediation_aliases:` config
key, which is meant to let an operator manually declare that two identities across engagements
are the same asset. Today the key is parsed and validated only; nothing applies it yet, so a
finding that moved to a new host or IP still reads as two unrelated findings.

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
tracking mechanism by design. If you run a
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

Revisiting this — either by extending scope signatures to a per-sensor keying scheme, or by
permanently accepting the exclusion and surfacing it in reports instead — is an open question,
not a scheduled change.

## 16. Closure Verification (first released in 5.19.0 — Phases 180-181)

Phase 179 gave a remediation item a stable identity and a per-scan record. Phase 180 adds the
piece that identity was missing: a machine-observed decision about whether that item is actually
fixed, computed from two consecutive comparable scans rather than asserted by anyone. Phase 181
surfaces that decision to the operator and the client — this section covers where it now appears
and how the dashboard behaves when there is nothing to show.

### Where it surfaces

Closure state and the remediation burndown appear on the surfaces below. They do not appear in
any markdown file the CLI writes (executive summary, technical findings, scorecard, roadmap) or on
the dashboard's `/print` page, which the dashboard's Export PDF renders:

- **The HTML report (and the PDF printed from it) and the DOCX report** each render a "Remediation
  Burndown" section, per deadline, with an advisory caption — see `docs/report-interpretation.md`
  §16 for how to read it with a client. The technical-markdown renderer has the same section, and a
  test holds its caption byte-identical with the other two, but the CLI never passes it closure
  data, so the `technical-findings-*.md` file carries no burndown and no refusal.
- **The CBOM** carries a `vulnerabilities` array (CycloneDX VEX), one entry per remediation item,
  with `not_observed` mapped to `in_triage` — never `not_affected`. See
  `docs/report-interpretation.md` §16 for the full state-mapping table.
- **The dashboard** shows closure state directly on the **existing roadmap items** it already
  displays, joined by the item's slug — **there is no new tab.** A closure `Badge` appears in the
  roadmap node detail panel (omitted entirely when no closure state is attached), and a
  "Remediation Burndown" table is rendered beneath the existing roadmap graph.

### Dashboard behavior when closure data is absent

A scan with no persisted remediation fingerprints — a scan that predates Phase 179, or one whose
findings feed no fingerprint-tracked remediation item — shows an **explicit "closure state was not
computed for this scan" message** instead of a table of zeros. An operator seeing that message must
not report "all clear"; the panel is telling you closure was not computed, not that nothing needs
fixing. A scan that has fingerprints but no comparable prior scan still shows the table, not this
message (see "the burndown block is empty / says not computed" below).

**Any closure lookup failure degrades the panel to empty and is logged — the endpoint never returns a 500.**
The dashboard's `/api/scan/latest` response reuses the same advisory-only
firewall pattern already used for vendor PQC trends and hardware findings: the lookup runs inside
its own try/except, a failure is logged via `logger.exception(...)`, and the response falls back
to an empty/`null` burndown or closure field rather than raising. This means an advisory-surface
failure can never take down the score view or the rest of the roadmap mid-presentation — the worst
case is a missing badge or an empty burndown block, not a broken page.

### The four states

`ITEM_STATES` in `quirk/intelligence/remediation.py` defines four closure states:

- **`open`** — a finding the scan detected. It is written when the scan is stored.
- **`closed`** — written on the scan that observed the fix, when the finding was present in a
  comparable prior scan and this scan positively rechecked the same host:port and did not find it.
  The earlier scan's record of that finding is also marked closed, so the earlier scan's burndown
  reads the closure as well once the later scan has run. Closed rows are not carried forward: a
  third scan that rechecks the same estate counts only its own rows, which show no closure.
  When a finding closes on a later scan, after a scan that could not recheck it, the scan that
  detected it is marked closed too, and its roadmap item closes once all of that item's findings
  have closed. If every finding of the item is then closed and the closing scan has no item of
  its own, the closing scan gets a closed item, so its CBOM VEX entry reads `resolved`.
  A finding that had resurfaced and closes this way is recorded as reclosed.
- **`not_observed`** — nothing was verified. Counter-only roadmap items use it, and so do scans
  stored before this release, which keep their detected findings as Not Verified and are not
  rewritten. A finding that a scan could not recheck, for example because its port timed out, is
  also written to that scan as `not_observed`. It stays in that scan's burndown, and a later scan
  that rechecks it can usually still close it. The exceptions are listed under "Known limitations"
  below.
- **`resurfaced`** — written to the current scan's record when a finding whose most recent earlier
  record is `closed` is detected again. It is counted as open-like for reporting, but reported as
  its own line rather than folded into `open`, and its closure history is retained.

A finding closes only when all of the following hold:

- The current scan has the same scope as the prior one (see §15).
- Every probe that reported that host:port has a live row at that same host:port in this scan. A
  probe that is healthy elsewhere in the scan does not count. One timed-out, refused,
  unreachable or errored row at the host:port blocks closure for every finding there, even when a
  SAML or JWT probe answered. A mail port that timed out or refused the connection counts the
  same way. Placeholder rows are not evidence of a recheck.
- No row at that host:port is a service the scan could not identify, such as the `UNKNOWN` row
  written when the HTTP probe times out. One such row blocks closure for every finding at that
  host:port, even when another probe there, such as SAML or JWT, answered normally.
- Every probe family that originally reported that host:port was rechecked in this scan. A run
  that reused cached fingerprint results does not count as a recheck.
- The current scan's remediation record was written. If writing it failed, closure is skipped for
  that scan, because a missing record cannot be told apart from every finding being gone.

Plaintext HTTP findings close when the scan's service identification now reports at that port a
service, TLS or SSH, that was not there when the finding was detected, for example TLS after the
port is moved to HTTPS. That still holds after an intermediate scan whose TLS check failed. A
live plaintext HTTP row at the port also counts as a recheck. No plaintext endpoint remaining
elsewhere in the scan counts as an HTTP recheck only together with one of these. A SAML or JWT
row at the port is not evidence that the port stopped serving plaintext.

A finding that a scan could not recheck is carried forward as `not_observed` and judged on the
next scan by every probe that reported its port, in the scan that detected it and in the scan in
between.

In a test of eight plaintext hosts with one moved to HTTPS, the next scan read 7 open and 1
closed for that item, and when all eight were fixed it read 8 closed.

TLS findings close only on deep TLS scans. A fast-mode scan does not produce the evidence needed
to show a TLS finding is gone, so it leaves the finding open (tracked in HORIZON 999.138).

A probe family that is healthy elsewhere in the scan is not enough for one host. A finding closes
only when a live row at its own host:port carries that family's evidence. For a TLS finding that
means the deep TLS enumeration of that host succeeded; if it failed there and the scanner fell
back to a basic handshake, the finding stays `not_observed` even though TLS is healthy on other
hosts. For a plaintext HTTP finding that is still answered by an HTTP row, the row must carry the
service identification. The HTTP-moved-to-TLS or SSH rule above needs no such evidence.

Two cases are deliberate under-claims, listed here side by side so the reason is not a surprise:

- A port that serves both HTTP and SAML closes only when both probes recheck it.
- An errored or timed-out row from any probe at a port blocks every finding there.
- A port whose HTTP probe returned nothing while only SAML or JWT answered stays `not_observed`.
- A finding at a host:port where a probe with no recheck signal also reported, in the prior scan
  or the current one, such as the REST fuzzer, OpenAPI, Vault, AD CS, Kubernetes or cloud
  connectors, does not close, because that probe cannot be shown to have rechecked the port. This also covers a host:port that reported
  HTTP together with the REST fuzzer.

The same plaintext HTTP finding can count under two remediation items (`plaintext-http-exposure`
and `high-impact-findings`), and the burndown places plaintext HTTP in the `unmapped` bucket,
because plain HTTP carries no algorithm. Do not add the item rows together.

**Absence alone never closes an item.** A host that stops appearing in a scan — because it was
decommissioned, because the target list shrank, because a segment of the network was unreachable —
is not evidence anything was fixed. Closure requires the current scan to have positively rechecked
that specific host:port and found the finding gone, not merely to have not seen it.

### Known limitations

These cases can leave a fixed finding reading `not_observed` when it could have closed. None of
them can mark a finding closed that is not fixed.

- **Cached fingerprint results.** A scan that reused cached fingerprint results did not recheck
  the port, so a plaintext HTTP finding whose port moved to TLS in that scan stays `not_observed`.
  If a scan could not recheck a plaintext HTTP finding because the HTTP probe timed out, and the
  next scan finds the port on TLS, the finding closes: it is judged by the scan that detected it.
- **A scan whose closure was refused as a whole.** If closure is not computed for a scan, for
  example because its scope differs from the prior scan or its remediation record failed to
  write, that scan carries no pending findings forward. Findings it did not detect, including
  ones that were `not_observed` before it, drop out of later scans' burndowns and can no longer
  close.
- **Findings carried from scans recorded before this release.** A finding whose only record is a
  `not_observed` row from a scan stored before this release has no record of which probe raised
  it, so it can never close on its own. It stays `not_observed`, whatever later scans see at its
  host:port, until a scan detects it again and writes a real `open` row. From then on the normal
  closure rules apply. A different service answering there, such as SAML or JWT, never closes it.
- **An endpoint that leaves service.** A finding at a host:port that stops answering is carried
  as `not_observed` on every later scan. There is no action to retire it yet.

### Why an item reads `not_observed` — troubleshooting

If a client or colleague asks "why does this say `not_observed` instead of `closed`?", the answer
is one of:

- **The scan predates this release.** Scans stored before this release keep their detected
  findings as `not_observed` and are not rewritten. Rescan to get `open` and `closed` states.
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
  address this run, every row there was a timeout, refusal, placeholder or error, or one of the
  rows there is a service the scan could not identify (`UNKNOWN`).
- **It is one of the known limitations above.** For example, the port changed service while the
  finding was waiting to be rechecked, or a scan in between had its closure refused as a whole.
- **The scan reused cached fingerprint results.** A cached run does not count as a recheck.
- **The host's own probe returned no evidence.** For a TLS finding, the deep TLS enumeration of
  that host failed and only a basic handshake row was recorded.
- **It is a TLS finding and the scan ran in fast mode.** Only deep TLS scans can close TLS
  findings (HORIZON 999.138).

Treat `not_observed` as **"not verified"**, never as **"nothing was found."** Telling a client
"12 items came back clean" when the true state is "12 items were not verified" is the exact
misreading this state exists to prevent. A finding that is still `open` was detected and is still
there.

### Troubleshooting — "the burndown block is empty / says not computed"

This is the same comparability gap as the `not_observed` troubleshooting list above, surfaced at
the whole-scan level instead of the per-item level. A fully fixed estate is not an
empty block: it shows closed rows on the scan that observed the fixes. Check, in order:

- **No comparable prior scan exists** — this is the first scan of this estate, or nothing prior
  matches closely enough.
- **The scope signature is missing, from a different signature version, or differs** — port
  scope, `--profile`, enabled optional extras, credential presence, sensor set, **or the target
  set** (the scope signature, §15). The report's refusal statement names which of five reasons
  applied: "Closure not computed: no comparable prior scan exists.", "...a scope signature is
  missing on one side of the comparison.", "...the scope signature version differs between the two
  scans.", "...the target-set digest is absent.", or "...scan scope differs from the prior scan."

The exported report (HTML and the PDF printed from it, and DOCX) states
the refusal explicitly rather than showing an all-zero table. The dashboard Roadmap page does not
read the refusal: a refused scan still stores its remediation fingerprints, so the page draws the
burndown table with every item counted as Not Verified and no refusal statement. Read the reason
from the exported report. If you see the refusal message, the fix is to rerun with a scope that
matches the prior scan you want to compare against, not to look for a hidden toggle.

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
- **FAR contractor amendment** — December 31, 2030, the date by which covered contractors must
  comply with NIST FIPS that incorporate PQC algorithms.

The burndown itself uses the two algorithm-class deadlines (key establishment and digital
signatures) plus the `unmapped` bucket; the two organisation-scoped dates are catalogued but are
not burned down.

Source: Federal Register Vol. 91 No. 121 (2026-06-25), FR Doc 2026-12909, Executive Order 14412.
The catalog is re-verified on a 90-day cadence against that `source_url`, the same cadence as the
QRAMM and CMVP catalogs described in §7.

**CNSA 2.0 dates are a deliberate, documented omission, not a gap that was missed.**
`media.defense.gov` returns HTTP 403 to non-browser user agents, so no CNSA 2.0 date literal has
been added to this catalog or to the burndown. The hardware PQC advisory is separate and does carry
years: its tier text hard-codes 2030 and 2033 targets (labelled "CNSA 2.0 deadline" in the HTML
report, and used as the remediation text of the dashboard's hardware advisory findings), so do not
read those as catalog dates. Do not fill this in from a secondary source — a
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
> "This report's `not_observed` count is not 'nothing found' — it means none of those items was
> verified, either because the scan predates this release or because we could not recheck them:
> this scan's scope differed from the prior one or a probe family came back unhealthy. Items we
> found again are shown as open, not as clean. Nothing here can
> be marked closed by a flag; a finding only closes when we
> positively recheck it and it's gone. And a `resurfaced` item means something we believed fixed
> came back — that's reported separately from ordinary open items so it isn't lost in the count."

---

## 17. Rating Band Severity Floor (Phase 184.4, SCORE-04/SCORE-05)

### What changed for operators

A scan with an open **CRITICAL** finding — for example, an expired TLS certificate —
**completes report generation successfully** instead of halting. Before Phase 184.4 (first
released in 5.19.0), a scan whose numeric score placed it in `EXCELLENT`, `GOOD`, or `MODERATE`
while a CRITICAL finding remained open would fail every report-writing path (CLI, HTML/PDF, DOCX)
with:

```
Report generation halted: executive headline 'EXCELLENT' is inconsistent with 1 CRITICAL
finding(s). Review findings before generating the report.
```

If you have seen this error in the field, it is fixed: Phase 184.4 gave the readiness **band** a
severity floor, so the band shown in the report floors to `FAIR` whenever at least one CRITICAL
finding is open and never disagrees with the findings the report is also showing.

**Since 5.25.0 the number is limited as well.** Scoring v3 applies the same protection to the
score itself: open CRITICAL and HIGH findings set an absolute ceiling that the score is compressed
into — 1 or more CRITICAL at most 34 (`POOR`), 5 or more CRITICAL at most 25, 3 or more HIGH at
most 54, 1 or 2 HIGH at most 69 (the lowest applicable ceiling wins) — and an estate with no
observed hybrid post-quantum key exchange is held to the top of `GOOD` (84). A capped score
always carries its reason, for example "1 open CRITICAL finding — score limited to 32 (computed
93)". The band is derived from the capped number, and the band floor stays in place as a second,
independent guarantee. See `docs/report-interpretation.md` §19, "The Severity Floor," for the
client-facing explanation (its band-only worked example describes the behaviour before 5.25.0).

### Where operators will see it

- **CLI**, **HTML/PDF**, **DOCX**, and the **scorecard** all show a short `Cap reason` annotation
  beside the score/band headline whenever the score or band has been capped — never elsewhere in
  the document, and never present at all when nothing is capped.
- **The dashboard Executive page and the print page** — the same screen the original defect
  (BACK-89) was filed against — now show the cap reason beside the readiness headline. On the
  Executive page it sits directly under the confidence badge; the print page shows it under the
  Overall Readiness score and prints confidence on a separate line below the score row. The
  dashboard computes this score itself, with the same scoring function as the exported report but
  from the scan's stored endpoints and the findings it derives from them, so it is a separate
  computation: nothing checks that the dashboard's cap reason matches the report's.
- No configuration change or migration is required. Historical scan sessions show the corrected
  band in the dashboard the next time they are viewed, because the dashboard recomputes the score
  and band from stored scan data on every request rather than storing them. Report files already
  written to disk are not re-rendered; a new scan writes a new report with the corrected band.

### Troubleshooting

If you still see `Report generation halted` on a current QU.I.R.K. version, that indicates a scan
whose evidence was assembled without its findings list attached to the scoring call — verify you
are running a version that includes Phase 184.4 (5.19.0 or later) and, if the error persists,
capture the full evidence/findings payload for the scan and file it, since the report writers and
the dashboard's scan views pass their findings to the scorer. Since Phase 228,
`quirk sensor merge`'s `Score: N (BAND)` and the Slack drift notification's `Score Band:` header
apply the CRITICAL and HIGH consequence ceilings, like the headline score.

## 18. SPKI Fingerprint Capture and Key Reuse (Phase 191, SPKI-01/SPKI-02)

### What is captured

Every TLS scan (5.21.0 and later) computes a SHA-256 hash of each leaf certificate's SubjectPublicKeyInfo (SPKI)
and stores it on `CryptoEndpoint.cert_spki_fingerprint`. This is captured at TLS certificate parse
only — the two `cryptography` x509 parse sites in `quirk/scanner/tls_scanner.py` (the `sslyze`
path and the stdlib-`ssl` fallback path). Scanners that persist raw `*_scan_json` blobs instead of
individual `cert_*` columns — broker, SAML, ADCS, and similar — are out of scope for this field;
SPKI-01 scopes strictly to TLS endpoints' `cert_*` fields.

Only the leaf certificate is fingerprinted — there is no chain fingerprinting or intermediate/root
hashing.

### Fill path for pre-existing rows

The column is nullable and there is no backfill migration. Computing the SPKI hash requires the
raw certificate bytes, which QU.I.R.K. does not persist; a fingerprint cannot be derived after the
fact from the other `cert_*` fields already stored on a row. The only way to populate
`cert_spki_fingerprint` for an endpoint scanned before this release is to re-scan it — the next
TLS scan against that `(host, port)` writes the fingerprint going forward.

### Sensor push path

`cert_spki_fingerprint` travels the full sensor→console path end-to-end: sensor-side serialization
(`quirk/cli/sensor_cmd.py::_endpoint_to_dict`), the push envelope, and console-side ingest
(`quirk/cli/console_cmd.py::_ingest_envelope`), which is also the function backing the
`POST /api/sensor/push` API route. An older sensor build that does not send the field is tolerated
— `_ingest_envelope` reads it with `.get()`, not a required key, so a missing field ingests as
`NULL` rather than raising an error. This matches the existing version-skew, warn-only policy for
sensor pushes.

### Where key reuse appears

Key reuse — TLS endpoints sharing an identical SPKI fingerprint — is derived at report-generation
time by a `GROUP BY cert_spki_fingerprint HAVING COUNT(*) >= 2` query
(`quirk/intelligence/key_reuse.py::compute_key_reuse_clusters`); there is no stored cluster table
or denormalized "is shared" column to keep in sync. The resulting "Key Reuse" section renders in
the CLI technical markdown, the HTML report, and the DOCX report; the dashboard's Exposure Map
page also draws key-reuse clusters (scoped to the displayed scan, where the reports aggregate
across every scan in the database). It is advisory-only and never affects the readiness score; see
`docs/report-interpretation.md` §21 for the client-facing explanation of how to read it.

## 19. Finding Storyline Drawer (Phase 202, first released in 5.25.0 — STORY-01/STORY-02)

Every row in the dashboard findings table has a `Storyline` button in its rightmost column. Opening
it is fully keyboard-operable: `Tab` to the button and press `Enter` (or click it), and a drawer
opens in place without leaving the findings view. Pressing `Escape` closes the drawer and returns
focus to the row's `Storyline` button, so keyboard navigation is never lost.

If the button is disabled with a tooltip reading "Storyline unavailable — this finding has no
stable identifier in this scan," that finding has no addressable ID for this scan (a known case:
identity-protocol findings such as Kerberos/SAML/DNSSEC). No action fixes this from the UI — it is
a property of how that finding was derived, not a bug in this scan.

In brief: the drawer shows the finding's narrative (when the algorithm-keyword catalogs have one —
most findings legitimately do not, and a blank narrative is normal, not an error) plus its
score-lift attribution — the owning remediation theme's total lift, conditioned on every finding in
that theme being resolved, never this one finding's individual share. See
`docs/report-interpretation.md` §25 for the full explanation of the theme framing, why most
findings show no narrative, and the one-theme display rule.

---

## 20. Browser E2E Tests (Phase 207, first released in 5.25.0 — COV-05, COV-10)

Six UAT cases are structurally impossible to cover with the jsdom-based dashboard test runner —
they need a real browser engine. They are now covered by real Playwright tests:

| Case | What it proves |
|---|---|
| `UAT-7-01` | The dashboard SPA mounts — no blank screen, no console errors on first load |
| `UAT-7-32` | Zero console errors across all seven routes, plus the CBOM Table/Graph switch |
| `UAT-7-17` | Clicking **Export PDF** yields a genuinely valid downloaded PDF |
| `UAT-88-03` | The six score-decomposition rows survive HTML-to-PDF conversion, asserted by value |
| `UAT-7-23` | The sidebar collapses at the 1024px breakpoint — asserted as **measured** `aside` box width (240px / 48px), never as the `class` attribute |
| `UAT-7-29` | A real Cytoscape node drags and its visible edge's endpoint follows **mid-drag**, not merely after release |

They live in `tests/test_browser_e2e.py` and `tests/test_pdf_decomposition_render.py`, with shared
setup in `tests/browser_e2e_harness.py`. `tests/test_browser_e2e.py` also holds later additions that
need a real browser: `test_222_export_pdf_carries_colophon_logo` and two keyboard-scroll nodes,
`test_kbd_01_keyboard_only_table_region_scroll` and its control.

**`UAT-7-23` and `UAT-7-29` (Phase 207.1, COV-10) each ship with a dedicated red-proof control
node** — `test_uat_7_23_control_no_viewport_change` and `test_uat_7_29_control_no_mousedown`. A
control performs the identical mount and setup with only the triggering interaction omitted (no
viewport resize; no `mouse.down()`) and asserts the observed value stays unmoved. Its purpose is to
prove the main test's assertions are capable of failing — a green result on a test that would also
be green if nothing happened is the vacuous-pass trap this module's own D-04 exists to catch. Each
control is its own pytest node with its own PASS/FAIL line, not a comment or sub-assertion inside
the main test.

### Running them locally

One-time setup (it downloads Chromium; on macOS the browser and its headless shell take about
0.5 GB on disk):

```bash
.venv/bin/python -m playwright install chromium
```

Then:

```bash
.venv/bin/python -m pytest tests/test_browser_e2e.py tests/test_pdf_decomposition_render.py -q -m ""
```

The `-m ""` is harmless but not needed: `pyproject.toml` sets `addopts = -m 'not slow'`, and
neither file carries a `slow` marker, so the same 11 nodes are collected with or without it.

**Read this before trusting a green local run.** Without that Chromium install these tests
**SKIP** — they do not fail. A green run that never installed Chromium has proven *nothing*, and
that is by far the most likely way to misread this suite. Always confirm a numeric passed count,
and check the skip lines: each one names whether the Chromium executable was actually found on
disk, precisely so an expected "no browser here" skip can be told apart from a transient launch
failure on a machine where the browser *is* installed.

No `npm run build` is needed. The built SPA bundle is committed under `quirk/dashboard/static`, and
its freshness is enforced by the separate `bundle-freshness` CI job.

### How they run in CI

They execute for real in a dedicated **Browser E2E** job, which installs Chromium. That job is
**non-gating** (`continue-on-error: true`) on purpose: browser tests carry a flake class that must
not be able to redden the check every pull request has to pass. Isolation is also the structural
cure for a known root cause — a shared Playwright singleton torn down by an earlier test in the
same process, which had previously quarantined 14 unrelated tests.

In the required **Linux Full Suite** job these same nodes **skip**, because that job deliberately
installs no Chromium. A skip there is not a pass; the coverage claim rests entirely on the Browser
E2E job's real execution, and each case's recorded disposition says exactly that.

One node behaves differently and it is not a fault: `UAT-88-03` can skip in a full-suite run even
where Chromium is installed, because an earlier test in the same process can tear down the shared
Playwright singleton; its skip reason then names TRIAGE-149 Cluster 2. It passes standalone and in
the Browser E2E job, whose run step lists its file first. If you are reading a Linux Full Suite log
and expecting it to pass there, you will think something has broken — it has not.

---

## 21. Command Reference

The CLI covers every scan capability (the dashboard launches `run_scan.py` itself) and is the supported path for automation, scheduling, sensors and repeat engagements; the dashboard is the primary interactive path.

This table was enumerated from the argv dispatch in `run_scan.py` and from each command's `--help`; "CLI only" means no `/api` route of the dashboard backs the command.

| Command | Purpose | Key flags | Dashboard counterpart |
|---------|---------|-----------|-----------------------|
| `quirk init` | Generate a starter config.yaml | `--output` | CLI only |
| `quirk serve` | Start the QU.I.R.K. web dashboard | `--port`, `--host`, `--no-open`, `--insecure` | This command starts the dashboard |
| `quirk compliance` | Inspect QUIRK's compliance mapping data (FIPS 140-3, HIPAA, ISO 27001, PCI-DSS, SOC 2); actions `status` and `cmvp` | `status`, `cmvp` | CLI only |
| `quirk compliance status` | Print per-framework version, last_verified date, and source URL | `--format` (`text` or `json`) | CLI only |
| `quirk compliance cmvp` | Inspect the CMVP attestation cache (actions `status` and `refresh`; use only `status`) | `status`, `refresh` | CLI only |
| `quirk compliance cmvp status` | Print CMVP cache freshness (read-only) | `--format` (`text` or `json`) | CLI only |
| `quirk compliance cmvp refresh` | Refresh CMVP cache from NIST. **Do not run it**: see the warning below the table | `--dry-run` | CLI only |
| `quirk doctor` | Pre-engagement health check: Python, nmap, syft and semgrep binaries, compliance freshness, QRAMM module, database, configuration, DNS and dashboard reachability | none (arguments are ignored) | CLI only |
| `quirk schedule` | Manage scheduled scans | `add`, `list`, `enable`, `disable`, `remove` | Schedules page (list, enable, disable, delete); the page cannot create a schedule |
| `quirk schedule add` | Add a new scheduled scan | `--name`, `--cron`, `--target`, `--check-in` | `POST /api/schedules` also creates one, but no page calls it: the Schedules page's Add Schedule sheet only prints this command |
| `quirk schedule list` | List all scheduled scans | `--config` | Schedules page: `GET /api/schedules` |
| `quirk schedule enable` | Enable a scheduled scan | `name`, `--config` | Schedules page toggle: `PATCH /api/schedules/{schedule_id}` |
| `quirk schedule disable` | Disable a scheduled scan | `name`, `--config` | Schedules page toggle: `PATCH /api/schedules/{schedule_id}` |
| `quirk schedule remove` | Remove a scheduled scan | `name`, `--config` | Schedules page delete: `DELETE /api/schedules/{schedule_id}` |
| `quirk scheduler` | Run the scheduled-scan dispatcher (action `run`) | `run` | CLI only |
| `quirk scheduler run` | Start the scheduler dispatch loop | `--config`, `--scan-config`, `--once` | CLI only |
| `quirk qramm` | Dispatcher for `quirk qramm status`; it has no help of its own | `status` | CLI only |
| `quirk qramm status` | Print the QRAMM model version, last_verified date, days remaining and freshness status | none | CLI only |
| `quirk cve` | Dispatcher for `quirk cve status`; it has no help of its own | `status` | CLI only |
| `quirk cve status` | Print the firmware CVE catalog source, last_verified date, days remaining and freshness status | `--format json` | CLI only |
| `quirk analyze-token` | Decode and classify a bearer/JWT token; passive: no signature verification, no network requests, no DB writes | `--json`, `TOKEN`, `@FILE` or `-` (stdin) | CLI only |
| `quirk token` | Dashboard API token management (actions `generate`, `rotate`, `show`) | `generate`, `rotate`, `show` | CLI only |
| `quirk token generate` | Generate and persist a new dashboard API token | `--config` | CLI only |
| `quirk token rotate` | Write a new `security.api_token` to the `--config` file; a server reading that file rejects the old token from its next request, but a `QUIRK_API_TOKEN` set in the server's environment takes precedence and stays valid | `--config` | CLI only |
| `quirk token show` | Show the persisted YAML token (not the env-var value) | `--config` | CLI only |
| `quirk export` | Export scan findings to an external destination; needs at least one destination flag | `--siem`, `--input`, `--output-dir` | CLI only |
| `quirk ticket` | Create tickets from scan findings (action `create`) | `create`, `--backend`, `--input`, `--output-dir` | CLI only |
| `quirk ticket create` | Create Jira or ServiceNow tickets from the latest (or a named) findings file; per-finding delivery failures are recorded as failed and do not change the exit status, but an unreachable backend or a database without the audit table fails the run | `--backend`, `--input`, `--output-dir` | CLI only |
| `quirk sensor` | Distributed sensor management | `enroll`, `push`, `export-results`, `merge` | Sensors page lists enrolled sensors (read-only); every action is CLI |
| `quirk sensor enroll` | Write the sensor's local `sensor.yaml` (console URL, `sensor_id`, segment, push token, HMAC key); it does not contact the console | `console_url` (`https://`, or `http://` for loopback), `--segment`, `--sensor-id`, `--api-token`, `--allow-internal-console`, `--allow-insecure-console` | CLI only |
| `quirk sensor push` | Run a local scan and push the results to the console | `--config`, `--scan-config` | Sending is CLI only; the console receives pushes at `POST /api/sensor/push` |
| `quirk sensor export-results` | Export results to a .qpush file for air-gap transfer | `--config`, `--scan-config`, `--output` | CLI only |
| `quirk sensor merge` | Merge sensor data into a unified CBOM and score (see section 8) | `--db`, `--stale-days` | Read-only: `GET /api/merge/latest` feeds the Executive page; the merge itself is CLI only |
| `quirk console` | Console-side management for distributed sensors | `import-results`, `enroll`, `revoke-sensor` | Sensors page lists enrolled sensors (read-only); every action is CLI |
| `quirk console import-results` | Import a .qpush air-gap file into the console | `file`, `--config` | CLI only |
| `quirk console enroll` | Provision a new sensor: write the sensor and token rows and mint a bearer token | `--segment`, `--sensor-id`, `--engagement`, `--config` | CLI only |
| `quirk console revoke-sensor` | Revoke the active token(s) for a sensor | `sensor_id`, `--config` | CLI only |
| `quirk errors` | Print the QU.I.R.K. operator error code reference | `code`, `--domain`, `--dump-md` | CLI only |
| `quirk report` | Manage named report branding/template profiles (action `profile`) | `profile` | CLI only |
| `quirk report profile` | Save or list report branding/template profiles | `save`, `list` | CLI only |
| `quirk report profile save` | Save the current config's report branding/template settings as a named profile | `name`, `--config` | CLI only |
| `quirk report profile list` | List saved report profile names | none | CLI only |
| `quirk db` | Database maintenance subcommands (action `migrate`) | `migrate` | CLI only |
| `quirk db migrate` | Idempotent, additive-only schema migration of an existing quirk.db; see the warning below the table | `--db`, `--config`, `--dry-run` | CLI only |

**Three commands do not print help.** `quirk doctor --help` ignores its arguments and runs the health check (exit status 1 when a check fails); `quirk qramm --help` and `quirk cve --help` print the scan CLI usage instead, and `quirk qramm status --help` and `quirk cve status --help` run the status report; `quirk cve status` takes `--format json` through hand-written argument handling, so no usage text lists it.

**Never run `quirk compliance cmvp refresh`.** It rewrites the CMVP attestation cache from NIST, and an earlier version of it silently emptied algorithm lists it could not parse (RVW-022, fixed in commit `a7cf302`); re-verify the cache by hand against its source URL instead, and use `quirk compliance cmvp status` for the read-only check.

**Scheduling needs the dispatcher.** There is no `quirk schedule run`; the long-running dispatch loop is `quirk scheduler run`. The dashboard stores, toggles and deletes schedules but never dispatches them, so a stored schedule fires only while `quirk scheduler run` is running.

**`quirk db migrate` needs an explicit `--db`.** Without `--db` or `--config` it falls back to `./quirk.db`, not the dashboard's `./quirk-output/quirk.db`, and creates an empty database there; pass `--db quirk-output/quirk.db`. `--dry-run` can stop with `NoSuchTableError` on a database created by an older release (see the upgrade guide).

**Flag and path gotchas.** `quirk export` and `quirk ticket create` search `./output` for the latest `findings-*.json` unless `--input` or `--output-dir` is given; `quirk sensor enroll` needs the `--sensor-id` that `quirk console enroll` printed; `quirk sensor merge` has no `--output-dir` option.
