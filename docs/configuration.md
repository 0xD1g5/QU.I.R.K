# Configuration Reference

QU.I.R.K. is configured through a YAML file, conventionally named `config.yaml` (`quirk init` writes a starter one into the working directory). A CLI scan reads it only when you pass `--config /path/to/config.yaml`; without `--config` the CLI starts the interactive setup wizard and does not pick up a `config.yaml` from the working directory. The dashboard server (`quirk serve`) separately reads `./config.yaml` (or the path in `QUIRK_CONFIG_PATH`) for some settings: it reads `assessment.crown_jewels` on each Exposure Map request, and `security.cors_origins` once at startup (unless `QUIRK_CORS_ORIGINS` is set).

The file has six core top-level blocks: `assessment`, `scan`, `targets`, `connectors`, `output`, and `intelligence`. It also accepts optional `report`, `security`, `broker_credentials`, and `remediation_aliases` blocks, each documented below. Three blocks are required, and a config missing any of them fails to load: `assessment` (all four of `name`, `data_classification`, `report_owner`, `timezone`), `scan` (at least `concurrency` and `ports_tls`, which have no default), and `output` (both `directory` and `db_path`). The loader raises an uncoded `KeyError` or `TypeError` naming the missing block or key. `targets`, `connectors`, and `intelligence` use their defaults when omitted.

---

## Assessment Block (required)

The four required keys are used in the report headers: `name`, `report_owner`, and `data_classification` are printed on the HTML, DOCX, and Markdown reports, and `timezone` is recorded in the
intelligence JSON. `logo_path` and `crown_jewels` are optional.

| Key | Type | Example | Required | Description |
|-----|------|---------|----------|-------------|
| `name` | string | `"Quantum Crypto Readiness - ACME Corp"` | Yes | Assessment name — appears in the report headers |
| `data_classification` | string | `"confidential"` | Yes | Classification label printed on the reports. The setup wizard and the dashboard offer `public`, `internal`, `confidential`, `regulated`; the config loader does not validate the value |
| `report_owner` | string | `"ACME Corp"` | Yes | Client name as it appears in the report |
| `timezone` | string | `"America/New_York"` | Yes | Timezone label (e.g. `"Europe/London"`, `"UTC"`). It is recorded in the intelligence JSON; it is not validated and is not used to convert report timestamps |
| `logo_path` | string | `"/path/to/your-org-logo.png"` | No | Deprecated fallback for `report.branding.logo_path` (see "Report Block"). Honored only when `report.branding.logo_path` is unset. Default `null` |
| `crown_jewels` | list of strings | `["10.0.0.20", "payments.example.com"]` | No | Systems whose compromise actually matters. Highlighted on the dashboard's Quantum Exposure Map. Default `[]` |

```yaml
assessment:
  name: "Quantum Crypto Readiness - ACME Corp"
  data_classification: "confidential"
  report_owner: "ACME Corp"
  timezone: "America/New_York"
  # logo_path: /path/to/your-org-logo.png   # DEPRECATED fallback — see "Report Block" below.
  #   report.branding.logo_path is the preferred field as of Phase 200 (v5.25). This
  #   assessment.logo_path key is still honored when report.branding.logo_path is unset — it is
  #   not being removed — but new configs should set report.branding.logo_path instead.
  crown_jewels:
    - "10.0.0.20"
    - "payments.example.com"
```

### `crown_jewels` (optional)

The systems whose compromise actually matters for this engagement — hosts, IPs, or FQDNs.
They render with an accent ring on the dashboard's **Quantum Exposure Map**, so the graph
shows what is at stake rather than only what is connected.

**This is declared, never inferred.** No probe can discover which system a client cares
about, so QU.I.R.K. does not guess. Leaving the list empty marks nothing — the map says so by
marking nothing rather than nominating a "most important" host it has no basis to choose.

Matching is on the **host portion** of an endpoint, so `"10.0.0.20"` marks that host on every
port it was found on. A certificate-authority hub node is never marked, whatever is declared:
a crown jewel is a system the client owns, not an issuer identity.

If the config cannot be read, nothing is marked. Marking the wrong node is worse than marking
none.

---

## Report Block (Phase 200, v5.25 — RPT-01/RPT-02/RPT-03/RPT-04)

Controls report branding (cover logo, client/engagement identity text), an operator-supplied
Jinja2 template override directory, and a named report profile. **The entire block is optional —
omitting it, or any individual key inside it, reproduces today's rendering exactly.** Every field
defaults to unset/`None` and is rendered only when present.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `branding.logo_path` | string | `null` | Path to a logo image file embedded on the HTML/PDF and DOCX cover. Preferred over the deprecated `assessment.logo_path` fallback — if both are set, `report.branding.logo_path` wins. An unreadable/missing file degrades gracefully to no logo (warning logged), never a crash. |
| `branding.client_name` | string | `null` | Client/organization name rendered in the cover identity block and the running header/footer, in addition to `assessment.report_owner`. |
| `branding.engagement_name` | string | `null` | Engagement label (e.g. `"Q3 2026 Crypto Assessment"`) rendered on the cover and running header/footer. |
| `branding.prepared_by` | string | `null` | "Prepared By" line on the cover identity block. |
| `branding.cover_date` | string | `null` | Free-form cover date label (e.g. `"September 2026"`), rendered verbatim — not parsed as a date. |
| `branding.confidentiality_line` | string | `null` | Confidentiality legend (e.g. `"CONFIDENTIAL — Internal Use Only"`) rendered on the cover and the running footer. |
| `template_dir` | string | `null` | Directory that may contain an operator-authored `report.html.j2` override. That is the only template the HTML renderer requests by name; other files in the directory are read only if your `report.html.j2` includes or extends them. The directory is searched **first**, ahead of the packaged template, which remains the fallback when `report.html.j2` is not present in it. Must be an existing, usable directory — see the error-code note below. Templates render inside a sandboxed Jinja2 environment (`SandboxedEnvironment`) unconditionally; see `docs/operators-guide.md`'s "Report template overrides" section for the full security posture. |
| `profile` | string | `null` | Name of a saved report profile (`~/.quirk/report_profiles/<name>.yaml`, or `$QUIRK_PROFILES_DIR` if set) to merge onto this config. See `docs/operators-guide.md` for `quirk report profile save\|list` and the `--report-profile` CLI flag. |

```yaml
report:
  branding:
    logo_path: /path/to/your-org-logo.png
    client_name: "Acme Corp"
    engagement_name: "Q3 2026 Crypto Assessment"
    prepared_by: "Security Team"
    cover_date: "September 2026"
    confidentiality_line: "CONFIDENTIAL — Internal Use Only"
  template_dir: /path/to/custom/templates   # must be an existing directory, or the config fails to load (QRK-CONFIG-003)
  profile: my-profile
```

### Which surfaces render which fields

- **HTML/PDF and DOCX** render the full branding set, including the cover logo — cover identity
  block plus running header/footer identity text (client/engagement + confidentiality line).
- **CLI markdown (executive summary, scorecard) and the Rich console scan-summary table** render
  the identity text only (`client_name`, `engagement_name`, `prepared_by`, `cover_date`,
  `confidentiality_line`) — **no logo ever reaches a CLI surface.**

### Path guard and error codes

Every report path field (`report.branding.logo_path`, `report.template_dir`, and the legacy
`assessment.logo_path` fallback) is validated at config-load time by one named guard,
`validate_report_path_field()`:

- **`QRK-CONFIG-003`** — raised when a path field contains a `".."` traversal segment, or when
  `report.template_dir` does not point at an existing, usable directory. This is a hard,
  load-time failure — the config never loads with a traversal-shaped or unusable `template_dir`.
- **`QRK-CONFIG-004`** — raised when `report.profile` (or a `quirk report profile save`
  invocation) names an invalid profile — profile names accept only letters, digits, hyphens, and
  underscores. It is raised when the scan applies the profile, after the config has loaded, not by
  the config loader itself.
- **Asymmetric disposition for `logo_path` specifically:** a missing or unreadable logo file only
  **warns** and degrades to no logo on the affected surface — it does not fail config load. Only a
  traversal-shaped `logo_path` value fails hard; a legitimately-missing file does not.

See [`docs/error-codes.md`](error-codes.md) for the exact cause/fix text of both codes.

---

## Scan Block

Controls connection timeouts, concurrency, port selection, and TLS enumeration depth. `concurrency` and `ports_tls` are required (the loader gives them no default); every other key is optional.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `timeout_seconds` | int | `5` | Deprecated alias of `scan.timeouts.default_seconds`: the fallback timeout in seconds for any scanner without its own slot (see "Timeout & Retry Policy") |
| `concurrency` | int | *(required)* | Legacy global worker count. It must be present, but it caps nothing: the fingerprint, TLS, and SSH phases take their worker counts from `fingerprint_concurrency`, `tls_concurrency`, and `ssh_concurrency` below, which have their own defaults. The shipped `quirk/config_template.yaml` sets it to `20` |
| `ports_tls` | list[int] | *(required)* | Ports probed for TLS/HTTP/SSH. There is no loader default, so the key must be set. The shipped template and the CLI wizard use `[443, 8443, 9443, 10443, 4433, 5001, 636, 3269, 993, 995, 465, 6443, 2376, 5432, 3306, 1433, 8200]` — the 17-port `CONSULTING_TLS_PORTS` list, shared with the CLI wizard and the dashboard's "Common TLS ports" scope (Phase 184.2, D-04). See below for the D-05 note on 5432/3306/8200. YAML values are coerced to `int` on load, so a quoted `"8443"` behaves identically to a bare `8443`; a non-numeric entry is rejected at load time with `QRK-CONFIG-001` (Phase 189, TRIAGE-04). |
| `tls_designated_ports` | list[int] | `[]` | Operator-declared ports that should be classified `"HTTP on TLS-designated port"` rather than `"Plaintext HTTP service detected"` when plaintext HTTP is found there, in addition to the well-known TLS set. Distinct from `ports_tls` above: `ports_tls` is the scan TARGET list (what gets probed), not a TLS-designation signal. (Phase 186, TRIAGE-176-02) Same coercion rule applies: quoted digit-strings are accepted, non-numeric entries raise `QRK-CONFIG-001` at load time (Phase 189, TRIAGE-04). |
| `include_sni` | bool | `true` | Send SNI extension in TLS handshakes |
| `tls_enum_mode` | string | `"fast"` | TLS enumeration depth: `fast` or `deep`. Any other value, including `off`, is treated as `fast`. The `--profile` flag does not change it |
| `fingerprint_timeout_seconds` | int | `4` | Per-target fingerprint timeout. Deprecated alias of `scan.timeouts.fingerprint_seconds` |
| `fingerprint_concurrency` | int | `200` | Fingerprint phase worker count |
| `tls_timeout_seconds` | int | `6` | TLS scan phase connection timeout. Deprecated alias of `scan.timeouts.tls_seconds` |
| `tls_concurrency` | int | `150` | TLS scan phase worker count |
| `ssh_timeout_seconds` | int | `6` | SSH scan phase connection timeout. Deprecated alias of `scan.timeouts.ssh_seconds` |
| `ssh_concurrency` | int | `100` | SSH scan phase worker count |
| `hardware_history_retention_days` | int | `180` | Days of `hardware_devices` scan-history rows to retain per device (Phase 154, HWLC-03) |
| `hardware_drift_event_retention_days` | int | `365` | Days of `hardware_drift_events` rows to retain table-wide (Phase 157, HWLC-16) |
| `motion_concurrency` | int | `50` | Worker count shared by the email and broker ("motion") connector scanners. The dashboard accepts 1-500 |
| `openapi_spec_path` | string | `null` | OpenAPI spec file or scope-gated URL; equivalent to `--openapi-spec` (see "OpenAPI Spec Analysis") |
| `nmap_port_scope` | string | `null` | `top1000` or `all`: port-scope hint the dashboard writes into a job's config for nmap discovery. Leave it unset in a hand-written config |
| `timeouts`, `retry` | tables | see below | Per-scanner timeout and retry sub-tables (see "Timeout & Retry Policy") |

> **Note:** For large scans (1000+ hosts), lower `fingerprint_concurrency`, `tls_concurrency`, and `ssh_concurrency`, or use `--safe-mode`, which halves each of them (minimum 25) and raises the fingerprint, TLS, and SSH timeouts to at least 4, 6, and 6 seconds.

```yaml
scan:
  timeout_seconds: 5
  concurrency: 200
  ports_tls: [443, 8443, 9443, 10443, 4433, 5001, 636, 3269, 993, 995, 465, 6443, 2376, 5432, 3306, 1433, 8200]
  include_sni: true
  tls_enum_mode: fast   # fast|deep
  fingerprint_timeout_seconds: 4
  fingerprint_concurrency: 200
  tls_timeout_seconds: 6
  tls_concurrency: 150
  ssh_timeout_seconds: 6
  ssh_concurrency: 100
  hardware_history_retention_days: 180
  hardware_drift_event_retention_days: 365
```

### `hardware_history_retention_days` (Phase 154, HWLC-03)

Bounds how many days of `hardware_devices` scan-history rows QUIRK keeps **per device**
(identified by `host`/`port`). Unit is days; default is `180`.

- **Purge mechanism:** a **hard delete** (`DELETE ... synchronize_session=False`), run
  opportunistically at the end of each hardware scan run, scoped only to the `(host, port)`
  pairs present in that scan's own batch — it never sweeps the whole `hardware_devices` table
  and never touches devices not scanned this run.
- **No CLI purge command and no background worker.** The purge runs only when hardware rows are
  written: by a scan, by a `--check-in` run, and when sensor results are ingested (a sensor push
  or `quirk console import-results`). Sensor ingestion always uses the 180-day default, not this
  setting. There is no `quirk hardware purge` command and no
  scheduled/cron job that ages out rows independently.
- **Invalid values are skipped, not defaulted.** A zero, negative, or non-numeric value causes
  the purge to be **skipped entirely** for that run (a warning is logged) rather than silently
  falling back to `180` and deleting everything, or deleting nothing forever with no signal.
- **Not the same knob as `STALENESS_THRESHOLD_DAYS`.** The 180-day default deliberately does
  not reuse the catalog-freshness constants (`STALENESS_THRESHOLD_DAYS` is 30, 90, or 365 days
  depending on the catalog, e.g. in `quirk/scanner/hw_cve.py`, `quirk/qramm/model_meta.py`, and
  `quirk/compliance/__init__.py`) — those govern whether a *reference catalog* (QRAMM model,
  compliance mappings, firmware CVE table) is stale, while `hardware_history_retention_days`
  governs how long an *engagement's own scan history* is retained. They are unrelated knobs
  that happen to both be day-counts.

### `hardware_drift_event_retention_days` (Phase 157, HWLC-16)

Bounds how many days of `hardware_drift_events` rows QUIRK keeps **table-wide** (across every
device, not scoped to a single `(host, port)` pair). Unit is days; default is `365`.

- **Purge mechanism:** a table-wide calendar-cutoff sweep — `DELETE FROM hardware_drift_events
  WHERE detected_at < cutoff` — run once per scan, regardless of which devices that scan
  actually fingerprinted. Unlike `hardware_history_retention_days` (above), this purge is not
  scoped to the current scan's batch of devices; it evaluates every row in the table by age.
- **Not the same knob as `hardware_history_retention_days`, and deliberately so.**
  `hardware_history_retention_days` bounds per-device scan-snapshot history and is scoped to
  devices the scan actually touched this run. `hardware_drift_event_retention_days` bounds an
  append-only *event log* by age across the whole table. Sharing one knob between the two would
  mean an idle device's drift history gets purged (or preserved) on the wrong schedule —
  whichever schedule the *other* concern happened to be tuned for — so the two fields are kept
  fully independent.
- **Why 365 days:** matches this codebase's existing 365-day-cadence convention (see
  `quirk/compliance/__init__.py`, `quirk/scanner/bacnet_vendors.py`, `quirk/scanner/hardware_eol.py`)
  and gives a full year of drift history for year-over-year comparison during a long engagement.
- **Fail-closed behavior.** A non-integer, zero, or negative value causes the purge to be
  **skipped entirely** for that run (a warning is logged), never a wipe of the whole table and
  never a silent no-op with no log line. Invalid values never widen the deletion window.
- **No CLI purge command and no background worker.** Like `hardware_history_retention_days`,
  this purge runs automatically as a side effect of every scan — there is no separate command
  or cron job to schedule.

---

## Timeout & Retry Policy

Phase 41 introduced canonical `[scan.timeouts]` and `[scan.retry]` sub-tables that supersede the
legacy flat fields. The fingerprint, TLS, SSH, JWT, container, source, Vault, database, broker,
and email scanners read their connection timeout from `scan.timeouts` (canonical source:
`quirk/config.py` `TimeoutsCfg` / `RetryCfg` dataclasses). The DNSSEC, SAML, and Kerberos scanners
do not: they use a fixed 10-second timeout, so their three slots below currently have no effect.
No scanner reads `scan.retry` yet, so no scanner retries a failed probe whatever `retry_count` is
set to. The flat fields documented above (`timeout_seconds`, `fingerprint_timeout_seconds`, `tls_timeout_seconds`,
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
| `dnssec_seconds` | int | `10` | DNSSEC record + DS chain probe (not read: the DNSSEC scanner uses a fixed 10 s) |
| `saml_seconds` | int | `10` | SAML metadata fetch (not read: the SAML scanner uses a fixed 10 s) |
| `kerberos_seconds` | int | `10` | Kerberos KDC probe (not read: the Kerberos scanner uses a fixed 10 s) |
| `vault_seconds` | int | `10` | HashiCorp Vault / KMS API call |
| `db_connect_seconds` | int | `5` | Database driver connect (Postgres, MySQL, …) |
| `broker_seconds` | int | `10` | Message broker probe (Kafka, RabbitMQ, Redis) |
| `email_seconds` | int | `10` | SMTP/IMAP/POP3 STARTTLS probe |

### `[scan.retry]` — retry/backoff policy

These three keys load and validate, but no scanner reads them yet, so they currently change nothing.

| Slot | Type | Default | Description |
|------|------|---------|-------------|
| `retry_count` | int | `0` | Number of retries after the initial attempt (0 = no retry); not yet read by any scanner |
| `backoff_base_seconds` | float | `1.0` | Initial backoff before the first retry |
| `backoff_max_seconds` | float | `5.0` | Backoff ceiling — exponential backoff caps here |

### Deprecation notice

The legacy flat fields below are still accepted but emit `DeprecationWarning` on read. If a `scan.timeouts` table is also present, the flat timeout keys in the YAML are ignored:

| Legacy field | New canonical slot |
|--------------|--------------------|
| `scan.timeout_seconds` | `scan.timeouts.default_seconds` |
| `scan.fingerprint_timeout_seconds` | `scan.timeouts.fingerprint_seconds` |
| `scan.tls_timeout_seconds` | `scan.timeouts.tls_seconds` |
| `scan.ssh_timeout_seconds` | `scan.timeouts.ssh_seconds` |

Migrate at your earliest convenience: the flat fields are deprecated.

### Overall scan upper-bound formula (D-10)

A rough worst-case estimate of the wall-clock time of one scan run, assuming every probe runs to its timeout one after another (an estimate, not a hard bound):

```
scan_upper_bound = (
  fingerprint_timeout * N_targets
  + tls_timeout       * N_tls_candidates
  + ssh_timeout       * N_ssh_candidates
  + max(jwt_timeout, container_timeout, source_timeout, ...) * N_connector_targets
) + 10s safety_margin
```

Where:
- `N_targets` = number of (host, port) targets fingerprinted
- `N_tls_candidates` = number of (host, port) pairs probed for TLS (a host with several open TLS ports counts once per port)
- `N_ssh_candidates` = number of (host, port) pairs probed for SSH
- `N_connector_targets` = number of connector probes (JWT URLs, container images, source repos, etc.)
- The `max(...)` term approximates the connector phases by the longest active connector timeout. Connector phases run one after another, so with several connectors enabled the true worst case is higher
- `safety_margin` = a flat 10s allowance this estimate adds for orchestration, report writing, and finalization (an assumption, not a measured value)

**Worked example — single-host scan, all phases enabled:**

```
fingerprint (4s) + tls (6s) + ssh (6s) + max(jwt=10s) + safety (10s)
= 4 + 6 + 6 + 10 + 10
≈ 36 seconds
```

For a 100-host scan with one TLS port and one SSH port per host and no connectors:

```
4*100 + 6*100 + 6*100 + 10
= 400 + 600 + 600 + 10
≈ 1610 seconds (~27 min) worst case
```

Concurrency (`fingerprint_concurrency`, `tls_concurrency`, and `ssh_concurrency`) reduces wall-clock
substantially below this estimate; the formula is the consultant-quotable worst case, not the
expected runtime.

### Example YAML snippet

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

Defines what to scan. The block is optional, but give at least one of `fqdns`, `cidrs`, or `include_ips` some entries, or pass `--targets-file` (which replaces `fqdns` and `cidrs`). With none, the scan logs "No targets provided" (with `--discovery nmap`, "No CIDRs/FQDNs/IPs provided for Nmap discovery") and exits 0 without scanning anything.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `fqdns` | list[string] | `[]` | Fully qualified domain names to include in the scan |
| `cidrs` | list[string] | `[]` | CIDR ranges or single IP addresses |
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

Enables optional scanner extensions for cloud infrastructure, API endpoints, containers, and
source code. **As of v5.19 (Phase 184.2), not all connectors default to `false`.** The shipped
`quirk/config_template.yaml` — which `quirk init` copies verbatim, with no wizard or branching —
carries all 25 `enable_*` flags live, each with an inline machine-checked reason tag. Seven ship
`true` out of the box: `enable_jwt`, `enable_container`, `enable_source`, `enable_dnssec`,
`enable_saml` (all target-guarded and inert until you populate their `*_targets` list), plus
`enable_email` and `enable_broker` (already scanning by default via the `standard` profile's
auto-enable — see below). The remaining 18 ship `false` with a stated reason. See "Full 25-key
connector disposition table" below for all 25 keys.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `enable_aws` | bool | `false` | Enable AWS cloud connector (ACM, KMS, CloudFront, ELBv2) |
| `enable_azure` | bool | `false` | Enable Azure cloud connector (Key Vault, App Gateway) |
| `enable_adcs` | bool | `false` | AD CS LDAP connector — inventories certificates issued by an Active Directory Certificate Services CA. The `enable_adcs` key is honored from release 5.19.0; earlier releases silently dropped it. Requires `quirk-scanner[adcs]` (ldap3). |
| `adcs_targets` | list[string] | `[]` | LDAP URLs for AD CS discovery (e.g. `ldap://dc.corp.com:389`) |
| `adcs_search_base` | string | `null` | LDAP search base DN (e.g. `dc=corp,dc=com`) |
| `adcs_user` | string | `null` | LDAP bind username (no example value shipped — do not template credential-shaped strings into a client config) |
| `adcs_password` | string | `null` | LDAP bind password — in real use leave it unset and export `QUIRK_ADCS_PASSWORD` instead (see "Credential environment variables"); never write it inline |
| `adcs_timeout` | int | `10` | Per-connection timeout (seconds) for AD CS LDAP queries |
| `enable_jwt` | bool | `false` | Enable JWT/REST API scanner (target-guarded — inert until `jwt_targets` is populated). The loader default is `false`; the shipped `config_template.yaml` sets it `true` |
| `enable_container` | bool | `false` | Enable container/binary crypto scanner (target-guarded — inert until `container_targets` is populated). The loader default is `false`; the shipped template sets it `true` |
| `enable_source` | bool | `false` | Enable source code scanner (target-guarded — inert until `source_targets` is populated). The loader default is `false`; the shipped template sets it `true` |
| `enable_codesign` | bool | `false` | Enable code-signing certificate inventory (LDAP `userCertificate`, plus the TLS phase's own leaf-certificate EKU capture; see below). **Not a connector toggle** — driven entirely by the `--inventory-code-signing` CLI flag; this key changes zero scan behavior on its own. |
| `codesign_targets` | list[string] | `[]` | LDAP URLs for code-signing certificate discovery (e.g. `ldap://dc.corp.com:389`) |
| `codesign_search_base` | string | `null` | LDAP search base DN for `userCertificate` discovery (e.g. `dc=corp,dc=com`) |
| `codesign_timeout` | int | `10` | Per-connection timeout (seconds) for code-signing LDAP queries |
| `enable_modbus` | bool | `false` | Enable Modbus/TCP OT/ICS fingerprinting (port 502, must be observed open); requires `quirk-scanner[hw]` extras. See `docs/operators-guide.md` §9.4 for the safety model. |
| `enable_bacnet` | bool | `false` | Enable BACnet/IP OT/ICS fingerprinting (47808/UDP); requires `quirk-scanner[hw]` extras. See `docs/operators-guide.md` §9.4 for the safety model. |
| `enable_recurring_otics` | bool | `false` | **Not a connector toggle** — a scheduler safety gate for recurring Modbus/BACnet probing, not a scanner enable by itself. Opt-in required before a *recurring* (scheduled) run may probe Modbus/BACnet. Gates recurring probing only — a one-off, operator-initiated scan with `enable_modbus`/`enable_bacnet` set is unaffected and needs no new flag. See [OT/ICS Recurring-Scan Cadence Floor](#otics-recurring-scan-cadence-floor-phase-156) below. |
| `enable_nmap` | bool | `false` | **Not a connector toggle** — a discovery driver, not a scan connector. Driven by the `--discovery nmap` CLI flag / the dashboard's nmap checkbox, either of which overwrites this value at scan start; it is not a durable config-file control. |
| `enable_authenticated_mode` | bool | `false` | **Not a connector toggle** — driven by the credential CLI flags (see "Authenticated Scanning" below). `quirk schedule add` refuses a `--config` file where this is `true` (`SCHED-AUTH-001`); `quirk scheduler run` refuses to start when its `--scan-config` enables it, and strips it from each recurring run. |
| `aws_region` | string | `"us-east-1"` | AWS region for cloud connector |
| `aws_profile` | string | `null` | AWS named profile; `null` uses the default credential chain |
| `azure_subscription_id` | string | `null` | Azure subscription UUID |
| `azure_keyvault_urls` | list[string] | `[]` | Key Vault base URLs (e.g. `https://myvault.vault.azure.net`) |
| `jwt_targets` | list[string] | `[]` | REST endpoint URLs for JWT scanner |
| `security.allow_insecure_jwks` | bool | `false` | A `security:` key, not a `connectors:` key (under `connectors:` it is ignored with a warning). Disables TLS cert verification for JWKS fetches; also settable per run with `--allow-insecure-jwks`. Use only for internal/dev endpoints with self-signed certs. When `true`, each JWKS URL fetched with verification disabled appears as a `HIGH` finding titled `JWKS fetched with TLS certificate verification disabled`; it is counted in the findings totals but does not change the readiness score. |
| `container_targets` | list[string] | `[]` | Docker image refs for container scanner |
| `source_targets` | list[string] | `[]` | Local repository directory paths for the source scanner (URLs are rejected — clone first) |
| `snmp_community` | string | `"public"` | SNMPv2c community string for hardware fingerprinting (requires `quirk-scanner[hw]`). An explicit value in `config.yaml` wins; when the key is absent, `QUIRK_SNMP_COMMUNITY` overrides the `public` default |
| `snmp_v3_credentials` | dict (host → credential) | `{}` | Per-host SNMPv3 USM credentials (environment-variable names only); see "SNMPv3 Credentials" below |
| `vault_token` | string | `null` | Vault token. When unset, the `VAULT_TOKEN` environment variable is used |
| `pg_scanner_password` | string | `null` | PostgreSQL scanner password. When unset, `QUIRK_PG_SCANNER_PASSWORD` is used. Never write it inline |
| `mysql_scanner_password` | string | `null` | MySQL scanner password. When unset, `QUIRK_MYSQL_SCANNER_PASSWORD` is used. Never write it inline |

> **Note:** See [Connector Guides](connectors/) for per-connector credential setup and least-privilege templates.

### Connector detail fields settable from the dashboard (PARITY-05/06, Phase 197)

Before Phase 197, the dashboard's Connectors panel could only flip the 25 `enable_*` toggles above
— the target lists, endpoints, and identifiers that make most of those toggles actually *do*
anything (e.g. `enable_jwt`'s `jwt_targets`) were config-file-only. Phase 197 widens the same
delta-overlay path (`connectors` key of `POST /api/jobs` and `GET /api/config/effective`) to
accept these 37 additional non-secret fields, enforced by a single shared validator
(`quirk.dashboard.api.schemas.validate_connectors_overlay`,
`_CONNECTOR_DETAIL_KEY_TYPES`) called at all three enforcement points — submit, job-YAML merge,
and preview — so submit and preview apply the same rules (PARITY-06). One exception: the submit
request model converts a whole-number float such as `10.0` to an integer before that check, so
submit accepts it where preview rejects it. See
[`docs/operators-guide.md` §3.1.4](operators-guide.md#314-connectors-panel--enabling-connectors-and-supplying-credentials-from-the-dashboard-parity-02parity-03-phase-193-parity-05parity-06-phase-197)
for how these fields render and behave from the New Scan page.

**Accepted wire types and bounds (D-09):** every `string` value is capped at 512 characters; every
`list[str]` is capped at 256 elements (each element also capped at 512 characters); every `int`
timeout is bounds-checked `1 <= value <= 300` seconds; a bare `true`/`false` is never accepted
where an `int` is expected (`type(value) is bool` is explicitly rejected for int fields, since
Python's `bool` is a subtype of `int`). An unrecognized key, or a key with the wrong wire type,
is rejected with an HTTP 422. The error message names only the offending key, not its value
(T-197-03), but the `POST /api/jobs` 422 body also carries FastAPI's `input` field, which echoes
the submitted overlay back to the caller.

**`gke_clusters` / `aks_clusters` object shape:** unlike every other list field (plain strings),
these two are `list[dict]`. Each GKE element requires exactly `{"name": str, "location": str}`;
each AKS element requires exactly `{"name": str, "resource_group": str}` — a bare string element
is rejected with an HTTP 422 when it arrives through the dashboard or `POST /api/jobs`.
`config.yaml` does not check this shape when it loads. A bare string there loads without error and
fails at scan time inside `quirk/scanner/k8s_connector.py`: that cluster and every cluster listed
after it are not checked (GKE and AKS alike), and the error is logged only in verbose runs.
The dashboard's free-text list input accepts the more compact `name@location` /
`name@resource-group` pairlist syntax and parses it into this object shape client-side before
submission — see the operators guide for the exact textarea convention.

**`vault_tls_verify` defaults to `true`** (matches `hvac.Client(verify=...)`'s config default) —
the dashboard's Vault toggle renders this switch pre-checked, not blank, when the field is absent
from the submitted delta; explicitly unchecking it sends `vault_tls_verify: false`.

| Field | Type | Default | Gating `enable_*` flag | Purpose |
|-------|------|---------|-------------------------|---------|
| `jwt_targets` | list[str] | `[]` | `enable_jwt` | REST endpoint URLs for the JWT/API scanner |
| `container_targets` | list[str] | `[]` | `enable_container` | Docker image refs for the container/binary scanner |
| `source_targets` | list[str] | `[]` | `enable_source` | Local repository directory paths for the source scanner (URLs are rejected — clone first) |
| `kerberos_targets` | list[str] | `[]` | `enable_kerberos` | KDC hosts for the Kerberos identity scanner. List each KDC by FQDN (for example `dc.corp.example.com`): the realm is taken from the last two labels, uppercased, and an IP address is used as the realm as-is, which a real KDC rejects |
| `kerberos_probe_principal` | str | `Administrator` | `enable_kerberos` | Client principal the etype probe names in its AS-REQ. It exists by default on Active Directory and Samba AD DC. It is a principal name, not a secret. An AS-REQ with no pre-authentication data is not a failed logon, so the probe cannot lock the account out. Set it to an account that exists if the KDC answers that the principal is unknown. YAML only; must be a non-empty string |
| `saml_targets` | list[str] | `[]` | `enable_saml` | SAML IdP/SP metadata URLs |
| `dnssec_targets` | list[str] | `[]` | `enable_dnssec` | Zones to query for DNSSEC posture |
| `dnssec_resolver` | str | `null` | `enable_dnssec` | Resolver host used for DNSSEC lookups |
| `smime_targets` | list[str] | `[]` | `enable_smime` | LDAP URLs for S/MIME certificate discovery |
| `smime_search_base` | str | `null` | `enable_smime` | LDAP search base DN for S/MIME discovery |
| `smime_timeout` | int (1-300s) | `10` | `enable_smime` | Per-connection LDAP timeout for S/MIME queries |
| `adcs_targets` | list[str] | `[]` | `enable_adcs` | LDAP URLs for AD CS discovery |
| `adcs_search_base` | str | `null` | `enable_adcs` | LDAP search base DN for AD CS discovery |
| `adcs_user` | str | `null` | `enable_adcs` | LDAP bind username (identifier, not a secret — D-04) |
| `adcs_timeout` | int (1-300s) | `10` | `enable_adcs` | Per-connection LDAP timeout for AD CS queries |
| `aws_region` | str | `"us-east-1"` | `enable_aws` / `enable_s3` / `enable_k8s` | AWS region for the cloud connector |
| `aws_profile` | str | `null` | `enable_aws` / `enable_s3` / `enable_k8s` | AWS named profile; `null` uses the default credential chain |
| `aws_endpoint_url` | str | `null` | `enable_s3` | MinIO/LocalStack S3 endpoint override |
| `azure_subscription_id` | str | `null` | `enable_azure` / `enable_blob` | Azure subscription UUID |
| `azure_keyvault_urls` | list[str] | `[]` | `enable_azure` | Key Vault base URLs |
| `gcp_project_id` | str | `null` | `enable_gcp` / `enable_k8s` | GCP project id used with application default credentials |
| `k8s_provider` | str | `null` | `enable_k8s` | `"eks"` \| `"gke"` \| `"aks"` |
| `k8s_cluster_name` | str | `null` | `enable_k8s` | Cluster name for the EKS path |
| `k8s_namespace` | str | `"default"` | `enable_k8s` | Namespace scope for the k8s connector |
| `k8s_kubeconfig` | str | `null` | `enable_k8s` | Server-filesystem path to a kubeconfig readable by the QU.I.R.K. server process (D-02 — not a file upload) |
| `k8s_context` | str | `null` | `enable_k8s` | kubeconfig context to use |
| `gke_clusters` | list[{name, location}] | `[]` | `enable_k8s` | GKE clusters, dashboard syntax `name@location` |
| `aks_clusters` | list[{name, resource_group}] | `[]` | `enable_k8s` | AKS clusters, dashboard syntax `name@resource-group` |
| `vault_addr` | str | `null` | `enable_vault` | HashiCorp Vault address, e.g. `http://localhost:8200` |
| `vault_transit_mount` | str | `"transit"` | `enable_vault` | Vault transit engine mount path |
| `vault_tls_verify` | bool | `true` | `enable_vault` | Verify the Vault server's TLS certificate |
| `pg_targets` | list[str] | `[]` | `enable_db` | PostgreSQL hosts for the database-encryption scanner |
| `pg_scanner_user` | str | `null` | `enable_db` | PostgreSQL bind username (identifier, not a secret — D-04) |
| `mysql_targets` | list[str] | `[]` | `enable_db` | MySQL hosts for the database-encryption scanner |
| `mysql_scanner_user` | str | `null` | `enable_db` | MySQL bind username (identifier, not a secret — D-04) |
| `broker_targets` | list[str] | `[]` | `enable_broker` | Explicit broker host/port entries (see the existing `broker_targets` subsection below) |
| `broker_azure_namespaces` | list[str] | `[]` | `enable_broker` | Azure Service Bus namespaces to probe |
| `broker_sqs_regions` | list[str] | `[]` | `enable_broker` | AWS regions to probe for SQS |

Bound-value violations, unknown keys, and type mismatches are rejected with HTTP 422 at both submit
and preview, but the bodies differ: preview returns `detail` as one message string, while submit
returns FastAPI's validation-error list. See [`docs/operators-guide.md` §3.1.4](operators-guide.md#314-connectors-panel--enabling-connectors-and-supplying-credentials-from-the-dashboard-parity-02parity-03-phase-193-parity-05parity-06-phase-197)
for what this looks like in the dashboard UI.

### Credential environment variables (D-09, Phase 193)

The scanner honors an environment-variable fallback for every connector credential field in
`quirk/config_redaction.py`'s `CREDENTIAL_REGISTRY` — these are **not dashboard-internal**. A CLI
operator can export any of them instead of writing the secret into `config.yaml`:

| Config field | Environment variable | Falls back for |
|--------------|----------------------|-----------------|
| `connectors.vault_token` | `VAULT_TOKEN` | HashiCorp Vault transit/PKI connector (pre-existing, Phase 25) |
| `connectors.adcs_password` | `QUIRK_ADCS_PASSWORD` | AD CS LDAP bind password |
| `connectors.pg_scanner_password` | `QUIRK_PG_SCANNER_PASSWORD` | PostgreSQL database-encryption scanner |
| `connectors.mysql_scanner_password` | `QUIRK_MYSQL_SCANNER_PASSWORD` | MySQL database-encryption scanner |
| `connectors.snmp_community` | `QUIRK_SNMP_COMMUNITY` | SNMPv2c community string for hardware fingerprinting |

**The config-file value always wins when both are set.** These env vars are a fallback consulted
only when the corresponding `config.yaml` field is empty/unset — set the field directly in
`config.yaml` if you want it to take precedence over whatever is in the shell environment.

For a shared or multi-operator machine, prefer a secret manager or an untracked, gitignored env
file over exporting these inline in a shared shell session — anything placed in shell history or a
committed dotfile is a credential leak, not a convenience.

**Per-host broker and SNMPv3 credentials** use a related but distinct idiom: rather than one fixed
env-var name, the dashboard's job submission generates a per-host variable name (the
`pass_env` / `auth_key_env` / `priv_key_env` config fields, carrying the environment-variable NAME
only, never the secret) and injects the actual value into the scan subprocess's environment at
launch. This is the same non-persistence pattern the broker connector (Phase 57) and SNMPv3
(Phase 139) already used for their own credential fields — Phase 193 extends dashboard-submitted
scans to use it too, rather than inventing a new secret channel. See "Connector detail fields settable from the dashboard"
above and `docs/operators-guide.md` §3.1.4 for how this looks from the Connectors panel.

**Credentials submitted from the dashboard are injected into the scan subprocess environment and
never persisted.** Whether a credential comes from the Connectors panel or from one of the env vars
above, it reaches the scanner only via the subprocess environment at scan-launch time — it is never
written to the SQLite `ScanJob` row, the job's stored `config.yaml`, or any log line. The job YAML
records only the environment-variable *name* that was used, never the value.

### Connector disposition and reason tags (D-06, Phase 184.2)

Every `enable_*` line in the shipped `quirk/config_template.yaml` carries an inline, closed-vocabulary
reason tag as a trailing YAML comment, e.g.:

```yaml
enable_aws: false  # off: requires-credentials - needs AWS_ACCESS_KEY_ID or an IAM profile; a bare true attempts SDK client construction and credential lookup
enable_jwt: true   # on: requires-targets - armed but inert until jwt_targets is populated below; the scan short-circuits on an empty target list
```

The tag always follows an `on:` or `off:` prefix that must agree with the flag's actual boolean
value, and is one of five closed strings:

- **`requires-credentials`** — the connector attempts real work the moment it is `true` (SDK
  client construction, credential lookup, an authenticated API call). It ships `false` until you
  supply the credentials it names.
- **`requires-targets`** — the connector is target-guarded: with an empty `*_targets` list the
  scan short-circuits and does nothing, so shipping it `true` is safe. It only starts scanning
  once you populate its target list.
- **`requires-extra-install`** — the connector needs an optional `pip install quirk-scanner[...]` extra
  (for example `[identity]` or `[hw]`, neither of which is part of `quirk-scanner[all]`). Setting the flag `true` without the extra installed
  does not fail the scan. For `enable_kerberos`, `enable_smime` and `enable_adcs` it emits a
  non-fatal `missing_extra` advisory finding instead (Phase 45 INSTALL-02). For `enable_snmp`
  there is no advisory: each SNMP probe only logs a warning that `pysnmp` is missing.
- **`probes-live-equipment`** — the connector sends unsolicited protocol traffic at OT/ICS
  equipment that can disrupt production plant hardware. It requires explicit, informed opt-in.
- **`not-a-connector`** — the field exists on `ConnectorsCfg` but does not gate a scanner by
  itself; something else (a CLI flag, a scheduler safety check) actually drives the behavior. The
  detail names that real driver.

This vocabulary is machine-checked by `tests/test_config_connector_drift.py`, which fails if any
`enable_*` line uses a tag outside this set, has a stale `on:`/`off:` prefix, or is missing a
substantive (non-trivial) detail. The test reads only the shipped template, not this page, so the
lists on this page are kept in step with the template by hand.

### Full 25-key connector disposition table

The table lists the 25 `enable_*` flags plus `broker_targets`.

| Field | Ships | Tag | Why |
|-------|-------|-----|-----|
| `enable_jwt` | `true` | `requires-targets` | target-guarded, inert until `jwt_targets` set |
| `enable_container` | `true` | `requires-targets` | target-guarded, inert until `container_targets` set |
| `enable_source` | `true` | `requires-targets` | target-guarded, inert until `source_targets` set |
| `enable_dnssec` | `true` | `requires-targets` | target-guarded, no extras install needed at all |
| `enable_saml` | `true` | `requires-targets` | target-guarded, inert until `saml_targets` set |
| `enable_email` | `true` | `requires-targets` | has no target list of its own: it probes the email ports on every host where the port scan found a TLS listener; already on via the `standard` profile, written explicitly so the value is authoritative |
| `enable_broker` | `true` | `requires-targets` | like email, probes every host where the port scan found a TLS listener, plus any `broker_targets` hosts; `broker_azure_namespaces`/`broker_sqs_regions` add cloud-broker probes rather than narrowing the host sweep |
| `broker_targets` | `[]` | `requires-targets` | (Phase 190, TRIAGE-06) an explicit list of `host` / `host:port` / `[ipv6]:port` entries probed **in addition to** each broker family's hardcoded default ports — see "`connectors.broker_targets` — explicit broker ports" below |
| `enable_kerberos` | `false` | `requires-extra-install` | `quirk-scanner[identity]` (impacket) is not in `[all]`: impacket pulls in pyOpenSSL, which can leave an incrementally-installed environment with an inconsistent `cryptography` version (re-resolve and run `pip check`) |
| `enable_smime` | `false` | `requires-extra-install` | target-guarded like the identity connectors, but shipped off because `quirk-scanner[adcs]` (ldap3) is not installed by default |
| `enable_adcs` | `false` | `requires-extra-install` | ldap3 via `quirk-scanner[adcs]`; same pre-gate shape as S/MIME |
| `enable_snmp` | `false` | `requires-extra-install` | needs `quirk-scanner[hw]` (pysnmp) plus a community string or v3 USM credentials |
| `enable_aws` | `false` | `requires-credentials` | needs AWS credentials or an IAM profile |
| `enable_azure` | `false` | `requires-credentials` | needs Azure credentials and an Azure subscription id or Key Vault URLs |
| `enable_gcp` | `false` | `requires-credentials` | needs a GCP project id, application default credentials, and `quirk-scanner[cloud]` |
| `enable_db` | `false` | `requires-credentials` | needs a scanner DB user/password; the default TLS port list already probes 5432/3306 at the TLS layer (D-05) |
| `enable_s3` | `false` | `requires-credentials` | needs AWS credentials; boto3 is a core dependency, so no extra is required |
| `enable_blob` | `false` | `requires-credentials` | needs Azure storage credentials; requires `quirk-scanner[cloud]` |
| `enable_k8s` | `false` | `requires-credentials` | needs kubeconfig or in-cluster credentials; requires `quirk-scanner[cloud]` |
| `enable_vault` | `false` | `requires-credentials` | needs `VAULT_TOKEN`/`VAULT_ADDR`; the default TLS port list already probes 8200 at the TLS layer (D-05) |
| `enable_modbus` | `false` | `probes-live-equipment` | unsolicited OT/ICS probing can disrupt production plant equipment |
| `enable_bacnet` | `false` | `probes-live-equipment` | same rationale as Modbus |
| `enable_nmap` | `false` | `not-a-connector` | driven by the `--discovery nmap` CLI flag, which overwrites this value at scan start |
| `enable_authenticated_mode` | `false` | `not-a-connector` | driven by the credential CLI flags; `quirk schedule add` refuses a `--config` file where this is `true`; `quirk scheduler run` refuses a `--scan-config` that enables it and strips it from each run |
| `enable_recurring_otics` | `false` | `not-a-connector` | a scheduler safety gate for recurring Modbus/BACnet probing, not a scanner toggle by itself |
| `enable_codesign` | `false` | `not-a-connector` | driven entirely by the `--inventory-code-signing` CLI flag |

Four fields are `not-a-connector`: `enable_nmap`, `enable_authenticated_mode`,
`enable_recurring_otics`, and `enable_codesign` — real config fields whose values do not by
themselves drive any scanner. Each is named above with the CLI flag or mechanism that actually
controls its behavior.

### `connectors.broker_targets` — explicit broker ports (Phase 190, TRIAGE-06)

`enable_broker`'s three drivers (Kafka, RabbitMQ, Redis) each carry a fixed table of default
ports they probe on every host where the port scan found a TLS listener. Before Phase 190
there was no way to tell the
scanner "also check this non-default port" short of editing source — an operator running a
broker on a non-standard port (as this project's own chaos lab does, mapping Kafka/RabbitMQ/
Redis to 29092/29093, 25671/25672, 26379/26380) got silent zero-findings coverage of those
ports even with `enable_broker: true`.

`connectors.broker_targets` closes that gap:

```yaml
connectors:
  enable_broker: true
  broker_targets:
    - "broker.internal.example.com"        # bare host — probed on every family's default ports only
    - "broker.internal.example.com:29092"  # host:port — this port is probed IN ADDITION to defaults
    - "[2001:db8::1]:6380"                 # IPv6 requires bracket syntax when a port follows
```

- **Accepted syntax:** a bare host, `host:port`, or bracketed `[ipv6]:port`. An unbracketed
  entry with more than one colon is only accepted as a bare IPv6 literal (validated via
  `ipaddress.ip_address`) — anything else is rejected at load time.
- **ADDITIVE semantics, not a replacement (RQ-1).** A port named in `broker_targets` is probed
  *in addition to* each family's hardcoded defaults — declaring a port never narrows or replaces
  the default port sweep. This means an operator can never lose coverage by adding a port here;
  the config errs toward over-scanning, never under-scanning. Every family (Kafka, RabbitMQ,
  Redis) receives the same flat host→ports override map, so a port aimed at one broker family is
  also, harmlessly by design, probed by the other two families' drivers.
- **A host listed only in `broker_targets` is scanned even if the general TLS sweep
  (`targets:`/`scan.ports_tls`) never saw it.** The broker phase's host list is the union of
  hosts derived from the TLS-target sweep and the hosts named in `broker_targets`.
- **A malformed port fails the config load with `QRK-CONFIG-002`**, not a silent skip — see
  [`docs/error-codes.md`](error-codes.md). This mirrors the CONFIG-001 fail-fast precedent for
  the general `scan.ports_tls` list (TRIAGE-04, Phase 189).
- **Interaction with custom port scope (see "Custom port spec" below):** the dashboard's
  `custom` port scope explicitly disables `enable_email`/`enable_broker` so a narrow custom scan
  is not also widened by the fixed email/broker service-port tables. `broker_targets` does not
  change this — it cannot re-enable a connector the operator (or the custom-scope suppression)
  has disabled. Set `enable_broker: true` explicitly if you need both a custom port scope and
  broker probing.
- **Reachability advisory:** if an explicit `host:port` entry in `broker_targets` never responds
  to any probe, the scan records exactly one informational (`severity: INFO`) `ADVISORY` row
  (that is the `protocol` field value) naming the unreached target
  — distinct from the deliberate silence for default-port probes that find nothing. See
  [`docs/report-interpretation.md`](report-interpretation.md) for how this reads in a report.

### Default TLS port list (D-04, widened v5.19 / Phase 184.2)

The shipped template's `scan.ports_tls` now defaults to the same 17-port `CONSULTING_TLS_PORTS`
list the CLI wizard and the dashboard's "Common TLS ports" scope already used — previously the
template alone stayed on a narrower 3-port list whose third entry was itself a typo for `4433`:

```
443, 8443, 9443, 10443, 4433, 5001, 636, 3269, 993, 995, 465, 6443, 2376, 5432, 3306, 1433, 8200
```

To narrow this for a specific engagement, edit `scan.ports_tls` in your `config.yaml` directly —
there is no separate CLI flag for it (the dashboard's port-scope selector, described later in this
document, is a dashboard-only control and does not affect CLI-driven scans).

**D-05 clarification:** `5432` (PostgreSQL), `3306` (MySQL), and `8200` (Vault) are in this port
list, so the port sweep checks them even though the credentialed `db` and `vault` connectors ship
`false`. The TLS scanner sends a direct TLS handshake, so it reports the certificate and cipher
posture of a Vault listener that serves TLS on `8200`. PostgreSQL and MySQL negotiate TLS inside
their own protocol, which the TLS scanner does not speak, so it does not get their certificate or
ciphers; the credentialed `db` connector reports whether TLS is on.

### TLS-designated ports override (D-08, Phase 186)

Before Phase 186, any plaintext-HTTP finding on any port listed in `scan.ports_tls` was
relabelled `"HTTP on TLS-designated port"` — because `ports_tls` is the scan TARGET list, not a
TLS-designation signal, this made a port that is plaintext by design (e.g. a scanned-but-plaintext
service) indistinguishable in reports from a genuine TLS misconfiguration. The classifier now
relabels a plaintext-HTTP finding only when its port is in the well-known TLS set:

```
443, 8443, 9443, 10443, 4433, 5001
```

or explicitly listed in `scan.tls_designated_ports`. Use the override for a non-standard TLS port
that should still be flagged as a TLS misconfiguration when found serving plaintext HTTP — for
example, a service running on port `8444`:

```yaml
scan:
  tls_designated_ports: [8444]
```

### Port-list value coercion and `QRK-CONFIG-001` (Phase 189, TRIAGE-04)

Both `scan.ports_tls` and `scan.tls_designated_ports` accept YAML values as either bare integers
or quoted digit-strings — `8444` and `"8444"` are equivalent after `load_config()` runs. A
non-numeric entry (e.g. a typo like `"84a4"`), a non-integral number (e.g. `443.8443` from a
missing comma — never silently truncated to port 443), or a value outside the valid TCP port
range 1–65535 (e.g. `0` or `70000`) is rejected loudly at config-load time with a coded
`QRK-CONFIG-001` error naming the offending field and value; see
[`docs/error-codes.md`](error-codes.md) for the exact message text. One deliberate acceptance:
an integral float such as `443.0` is unambiguous and coerces to the equivalent integer.

**Before Phase 189, this was a silent no-op, not a crash.** A quoted port value in either list
would load without error but would never match the TLS-designation membership test in
`findings_evaluator.py` — the override looked active in the config file but had no effect on
report output. If you have used a quoted value in `scan.ports_tls` or `scan.tls_designated_ports`
in a past engagement's config, re-check that scan's report: the effective scan scope or
TLS-designation override may have been narrower than the config file implied. Configs written
after Phase 189 do not have this gap — a quoted value now either works identically to a bare
integer, or fails loudly with `QRK-CONFIG-001` rather than being silently ignored.

With that override in place, plaintext HTTP found on port 8444 is classified `"HTTP on
TLS-designated port"`; without it, the same finding is classified `"Plaintext HTTP service
detected"`.

### Per-surface connector coverage

Which surface can set which connectors:

| Surface | Connector coverage |
|---------|---------------------|
| Config template (`quirk/config_template.yaml`) | 25 `enable_*` connector flags, all dispositioned |
| CLI wizard (`quirk/interactive.py`) | 5 — `jwt`, `container`, `source`, `aws`, `azure` |
| Dashboard New Scan (the Connectors panel, `src/dashboard/src/components/ConnectorsPanel.tsx`) | all 25 `enable_*` toggles, plus the 37 detail fields in "Connector detail fields settable from the dashboard" above; `enable_nmap` and `enable_codesign` have no effect on a dashboard scan (see below) |

The CLI wizard sets only its 5-connector subset, plus `enable_nmap` from its separate nmap-discovery
prompt; the other 19 connectors are set in the config file (or from the dashboard).

`run_scan.py` sets `enable_nmap` from `--discovery` whenever it runs with `--config`, which every
dashboard job does, so an `enable_nmap` value in a config file or in the Connectors panel is
ignored. On the dashboard, the "Enable nmap discovery" checkbox controls nmap. `enable_codesign` is
not read anywhere, and the dashboard never passes `--inventory-code-signing`.

### SNMPv3 Credentials (Phase 139, `[hw]` extras)

`connectors.snmp_v3_credentials` configures per-host SNMPv3 USM (User-based Security Model)
credentials for authenticated, encrypted SNMP scanning — an upgrade path alongside the
existing SNMPv2c `connectors.snmp_community` string documented in `docs/operators-guide.md` §9.
Mirrors the shape of `broker_credentials`: only environment-variable **names** are stored in
config, never the passphrases themselves.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `username` | string | *(none)* | SNMPv3 USM username configured on the target device. Not checked at load time: omitting it loads as an empty string, which cannot authenticate |
| `auth_key_env` | string | *(none)* | Name of the environment variable holding the authentication passphrase. Not checked at load time: omitting it loads as an empty string |
| `priv_key_env` | string | `""` | Name of the environment variable holding the privacy (encryption) passphrase. Omit or leave empty for `authNoPriv` mode |
| `auth_protocol` | string | `"SHA"` | Authentication protocol — SHA-family only (D-02): `SHA`, `SHA224`, `SHA256`, `SHA384`, `SHA512` |
| `priv_protocol` | string | `"AES"` | Privacy protocol — AES-family only (D-02): `AES`, `AES128`, `AES192`, `AES256` |

**D-02 (SHA/AES-only):** Weaker legacy USM protocols (MD5 auth, DES priv) are rejected at
config-load time with a `ValueError` naming the offending host and protocol — QUIRK never
silently falls back to a weaker negotiated protocol on your behalf. `priv_protocol` is only
checked when `priv_key_env` is set (in `authNoPriv` mode there is no privacy protocol to check).

```yaml
connectors:
  snmp_v3_credentials:
    "192.168.1.1":
      username: "quirk-readonly"
      auth_key_env: "QUIRK_SNMP_AUTH_KEY"    # env var NAME, not the passphrase
      priv_key_env: "QUIRK_SNMP_PRIV_KEY"    # env var NAME, not the passphrase
      auth_protocol: "SHA256"
      priv_protocol: "AES256"
```

Set the referenced environment variables before scanning (e.g.
`export QUIRK_SNMP_AUTH_KEY=...`) — passphrases must never appear inline in YAML. Hosts
without their own `snmp_v3_credentials` entry use the `"default"` entry when there is one (the
dashboard stores its single SNMPv3 credential under `"default"`). Otherwise the `--enable-snmp`
phase scans them with the existing SNMPv2c `connectors.snmp_community` path unchanged; hardware
fingerprinting's own SNMP query always uses the community `public`. See
`docs/operators-guide.md` §9 for the full
v3→v2c→none fallback ladder and the SNMP version labels in `docs/report-interpretation.md`.

### Code-Signing Certificate Connector (Phase 95)

The code-signing connector discovers X.509 certificates from Active Directory LDAP servers by
reading the `userCertificate` RFC 4523 attribute. It filters for certificates carrying the
`Code Signing` Extended Key Usage (EKU OID `1.3.6.1.5.5.7.3.3`) and classifies weak-algorithm
certificates (RSA < 2048-bit, EC < 256-bit key, or SHA-1 signature) as HIGH-severity findings.

Declare the LDAP targets in the `connectors` block and activate the connector at scan time with the
`--inventory-code-signing` CLI flag (the `enable_codesign` key alone changes nothing):

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

The scanner performs an anonymous LDAP bind with a paged search (page size 500). User DNs, hosts and
certificate subject CNs that appear in log output or stored fields have control characters
removed, including newlines and terminal escape sequences; exception text in log lines goes
through `safe_str()`. The scanner makes no network request other than its LDAP queries, and certificate
details flow only into the normal scan outputs (database, CBOM, and reports).

**In-process TLS EKU check:** Even without `codesign_targets` configured, the `--inventory-code-signing`
flag runs an in-process check over the in-memory `tls_endpoints` list, with no additional network
connections. The TLS scanner records each leaf certificate's Extended Key Usage OIDs (on both the
sslyze path and the fallback path, and they survive a resumed scan), and this check reports a
`CODE_SIGNING` endpoint for any leaf whose EKU includes Code Signing (1.3.6.1.5.5.7.3.3). Use
`codesign_targets` as well to find code-signing certificates held in LDAP.

**CBOM integration:** Code-signing certificates are emitted as CycloneDX `certificate` components
with `bom_ref = crypto/certificate/codesign/<sha256-fingerprint>`. If the same certificate was
already discovered by the TLS scanner, the TLS-derived component wins and gains a
`quirk:code-signing-eku: true` property rather than creating a duplicate component.

**Scoring impact:** The code-signing connector contributes to the **Agility Signals** subscore.
Each certificate with a weak algorithm increments the `codesign_weak_algo_count` counter; the
resulting `agility_codesign_weak_algo_ratio` reduces the subscore by up to −6.0 points
(its weight in `SCORE_WEIGHTS`).

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
    - "/path/to/another-checkout"   # local directories only; clone remote repos first
```

---

## OpenAPI Spec Analysis (`[api]` extras)

Phase 94 (available since release 5.0.0) introduced passive OpenAPI/Swagger spec analysis. The scanner inventories declared security schemes, plaintext `http://` server URLs, and unauthenticated path operations, with hardened defenses against `$ref` SSRF and oversized-spec DoS.

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

The `--openapi-spec` flag accepts either a local file path or a URL. A URL's host must equal one of the configured `targets.fqdns` entries — out-of-scope URLs are rejected before any network request is made. The fetch follows at most 5 redirects, and each hop must pass the same host-scope gate and URL check.

### `scan.openapi_spec_path` config key

The spec path can also be set in `config.yaml` under the `scan` block (there is no separate `openapi:` block):

```yaml
scan:
  openapi_spec_path: "docs/openapi.yaml"   # local path or scope-gated URL
```

Setting `openapi_spec_path` in the config is equivalent to passing `--openapi-spec` on the CLI. A CLI flag overrides the config value.

### Security hardening

| Guard | Behavior |
|-------|----------|
| **$ref SSRF** | Any `$ref` that does not start with `#` (e.g. `http://169.254.169.254/...`) raises `SpecParsingError` *before* the OAS validator runs. Zero outbound requests on SSRF-shaped input. |
| **10 MB size cap** | Specs larger than 10 MB are rejected before `yaml.safe_load`. Prevents billion-laughs and oversized-YAML DoS. |
| **Scope gate** | A spec URL's host must equal a configured `targets.fqdns` entry. Rejected before any network request. After the scope check, the URL also passes the SSRF guard (`validate_external_url`): a spec URL on the cloud-metadata address `169.254.169.254` is refused, and loopback and private addresses are blocked unless `--allow-internal-targets` is set. The fetch follows at most 5 redirects, and each hop must pass the same host-scope gate and URL check. |
| **Graceful degradation** | When `[api]` is not installed (`OPENAPI_AVAILABLE = False`), the scanner returns a single `missing_extra` advisory endpoint and continues; no exception is raised. |

### Findings produced

OpenAPI scan results appear in the standard findings table as `CryptoEndpoint(protocol="OPENAPI")` rows:

| Finding type | Severity | Description |
|-------------|----------|-------------|
| Security scheme declaration | INFO | JWT/OAuth2/API-key security scheme found in spec |
| Plaintext server | HIGH | `http://` (non-TLS) server URL declared in spec — feeds `agility_openapi_plaintext_ratio` scoring penalty |
| Unauthenticated endpoint | MEDIUM | Path operation with no security requirement declared |

---

## Authenticated Scanning (ephemeral credentials)

Phase 93 (available since release 5.0.0) introduced per-scan ephemeral credential support,
through the `--auth-*` flags below, for the JWT/JWKS probe. The credential is sent to the JWKS
target with the request; only logged URLs have the `api_key` query value replaced with `REDACTED`.
The credential goes only to URLs on the same origin (scheme, host and port) as the configured JWT
target. When the target's OIDC discovery document names a `jwks_uri` on a different origin, QUIRK
fetches that URL without the credential and logs one WARNING naming both origins. A JWT target
given as `http://` still receives the credential, in cleartext, and QUIRK logs one WARNING that
names the origin (never the secret).
The REST fuzzer does not attach the credential to its probes. It uses a bearer token only to forge
the `--fuzz-jwt-alg-confusion` test token. Credentials are never
persisted to SQLite, the CBOM, log files, or the dashboard — they live only in-process for the
duration of the run.

### Opt-in config flag

Authenticated mode is switched on by passing any `--auth-*` flag; setting `enable_authenticated_mode`
to `true` in the `connectors` block is not needed for that, and on its own (with no `--auth-*` flag) it builds no
credential and sends nothing. Its practical effect is on the scheduler, which refuses to schedule a
config that sets it (see "Scheduler rejection" below). The key looks like this:

```yaml
connectors:
  enable_jwt: true
  jwt_targets:
    - "https://api.acme.com"
  enable_authenticated_mode: true
```

Without any `--auth-*` flag, no credential is attached to any probe.

### CLI flags

| Flag | Credential scheme | Description |
|------|-------------------|-------------|
| `--auth-bearer [REF]` | Bearer token (OAuth2 / JWT) | Builds an `Authorization: Bearer <token>` header sent with the JWKS fetch. Also feeds `--fuzz-jwt-alg-confusion`, and the token's declared algorithm is recorded as a `BEARER_TOKEN` row |
| `--auth-api-key [REF]` | API-key header (`X-Api-Key`) | Builds an `X-Api-Key: <key>` header sent with the JWKS fetch |
| `--auth-api-key-query [REF]` | API-key query parameter | Appends `?api_key=<key>` to the JWKS URLs; the value is sent to the target and replaced with `REDACTED` only in log output |
| `--auth-basic [REF]` | HTTP Basic | Reads the secret as `user:password` (QUIRK base64-encodes it, per RFC 7617; do not pre-encode) and sends `Authorization: Basic <base64>` with the JWKS fetch. A value with no colon is rejected |

Each flag accepts an optional `REF` argument. If `REF` is omitted the flag is treated as a bare
flag and triggers an interactive `getpass` prompt (see "Reference model" below).

### Reference-not-secret model

**Raw credential values must never appear in the CLI argument.** Passing a credential as a bare
string (e.g. `--auth-bearer eyJhbGci…`) is rejected with an error. A value typed on the command line is already in your shell
history, so treat a secret pasted this way as exposed.

Instead, pass a *reference* to where the credential lives:

| Input form | Example | Resolved from |
|------------|---------|---------------|
| `@file` path | `--auth-bearer @token.txt` | The file's non-blank lines that do not start with `#`, stripped and joined with commas, so keep the secret on a single line. The file must be inside the current working directory (not under `/etc`, `/proc`, `/sys`, or `/dev`) |
| `ENV_VAR` name | `--auth-bearer QUIRK_AUTH_TOKEN` | Environment variable at resolution time; env var is **deleted after reading** to prevent subprocess inheritance |
| Bare flag (no REF) | `--auth-bearer` | Interactive `getpass` prompt — credential is never echoed to the terminal |

**Why the reference model?** Inline secrets in `argv` are visible to `ps aux`, the shell history
(`~/.bash_history` in bash, or the file named by `HISTFILE` in zsh), and process-listing tools. The `@file`/`ENV_VAR`/`getpass`
forms keep the raw credential out of the process argument list entirely.

**How a reference is read:** an empty or bare flag prompts; a value starting with `@` is read as a file; any other value must be the name of a set environment variable, otherwise the scan stops with an error.

### Ephemeral-only invariant

Credentials are held in a `bytearray` buffer (`CredentialContext`) for the scan run and
zeroed in-place via `CredentialContext.close()` on both normal exit and on any exception,
including `KeyboardInterrupt`. They are **never**:

- Written to the SQLite database (`quirk.db`)
- Included in the CBOM output (`cbom-*.json`)
- Included in log files
- Returned by the dashboard API
- Included in PDF exports

This invariant is enforced by an automated sentinel test suite (`tests/test_credential_leakage.py`)
that injects a synthetic sentinel value across all 11 stored/rendered surfaces and asserts absence.

### Scheduler rejection (QRK-SCHED-AUTH-001)

Scheduled scans cannot use authenticated mode. Running `quirk schedule add` against a config
file that contains `enable_authenticated_mode: true` exits immediately, and `quirk scheduler run`
refuses to start when its `--scan-config` enables it (and strips the flag from each recurring run
in case the file changes later). Both print:

```
[QRK-SCHED-AUTH-001] Authenticated scan configs cannot be scheduled — credentials are ephemeral and cannot be persisted. Fix: Run an authenticated scan interactively with `quirk --auth-bearer` (or `--auth-api-key` / `--auth-basic`).
```

Exit code: `2`. This is by design — storing scheduled-scan credentials would require persisting
a secret somewhere, which violates the ephemeral-only invariant.

### Example: authenticated JWT scan

```bash
# Using a @file reference (preferred for automation; the file must be inside the current directory)
echo "eyJhbGciOiJSUzI1NiJ9..." > token.txt
quirk --config config.yaml --auth-bearer @token.txt

# Using an environment variable reference
export QUIRK_AUTH_TOKEN="eyJhbGciOiJSUzI1NiJ9..."
quirk --config config.yaml --auth-bearer QUIRK_AUTH_TOKEN
unset QUIRK_AUTH_TOKEN   # QUIRK also deletes it after reading

# Interactive prompt (safest — credential never touches disk or env)
quirk --config config.yaml --auth-bearer

# API-key query parameter (appended to JWKS/probe URLs)
quirk --config config.yaml --auth-api-key-query @apikey.txt
```

---

## REST Fuzzing (active crypto-posture probes)

Phase 96 (available since release 5.0.0) introduced active REST endpoint fuzzing for crypto-posture assessment.
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
install lightweight. Running `--fuzz` without `[api]` installed sends no fuzz requests: after the
`CONFIRM` prompt the fuzzer records one `missing_extra` advisory row, and the scan continues.

### CLI flags

| Flag | Default | Description |
|------|---------|-------------|
| `--fuzz` | `false` | Enable active REST crypto-posture fuzzing. Requires `--openapi-spec` (endpoint source) naming a local spec file: with a URL spec the fuzz phase cannot re-read the spec and sends no fuzz requests. Also requires an interactive `CONFIRM` prompt before any request is sent. |
| `--fuzz-jwt-alg-confusion` | `false` | Also run the JWT RS256→HS256 algorithm-confusion probe. Combines a Phase 93 bearer token with the target's JWKS public key to forge a symmetric token; acceptance yields a CRITICAL finding. |
| `--fuzz-budget N` | `50` | Maximum number of probe requests (hard max 500 — values above 500 are rejected before any request is sent). |

### CONFIRM gate and non-TTY hard-abort (FUZZ-01, FUZZ-03)

When the fuzz phase starts in a TTY session, the scanner prints a budget summary and requires
the user to type the **literal word `CONFIRM`** before any request is dispatched:

```
[QUIRK FUZZ] About to send up to 50 active requests to 3 endpoint(s).
Type CONFIRM to proceed (any other input aborts):
```

Any input other than exactly `CONFIRM` (including a bare Enter, or `CONFIRM` with leading or
trailing whitespace) aborts cleanly with **zero requests sent**.

> **Non-TTY hard-abort:** When stdin is not a TTY (piped input, CI/CD, scheduled jobs),
> the scanner hard-aborts **before sending any request** and prints a clear
> non-interactive-mode error. Fuzzing **never runs headlessly**. This differs from the
> nmap discovery prompt, which auto-proceeds in non-TTY mode — the fuzz gate is stricter
> by design (T-96-03).

**As of 5.18.0 (Phase 172, SAFE-01):** this refusal fires at argument-validation time,
immediately after `--fuzz` is parsed and before any config load or scan phase begins —
not later, inside the fuzz phase itself. `--fuzz` on non-interactive stdin is treated as
a usage error: the scanner prints coded error `QRK-FUZZ-001` and exits `2`, regardless of
whether an OpenAPI spec resolves. Previously this could be silently bypassed (the scan
would complete and exit `0` with fuzzing quietly skipped); it no longer can be. See
[docs/error-codes.md](error-codes.md) for the `FUZZ` error domain's full cause/fix text.

### Six safety guardrails (FUZZ-02)

| # | Guardrail | Behavior |
|---|-----------|----------|
| 1 | GET-only by default | Only HTTP `GET` endpoints are probed; other methods require explicit future opt-in |
| 2 | Hard budget ceiling | `--fuzz-budget` default 50, hard max **500** — values above 500 are rejected before any request |
| 3 | Rate cap 5 req/s | Probe requests are rate-limited to 5 per second using the nmap TokenBucket pattern |
| 4 | CONFIRM prompt | TTY: user must type the literal word `CONFIRM`; any other input aborts with zero requests sent |
| 5 | Per-request scope enforcement | Every probe URL is validated via `validate_external_url` before dispatch: a probe URL on the cloud-metadata address `169.254.169.254` is rejected, and loopback or private addresses are rejected unless `--allow-internal-targets` is set. The base URL is built from the first `targets.fqdns` entry (`https://localhost` when there is none) |
| 6 | 5xx cascade stop | After 3 consecutive failures (HTTP 5xx responses or request errors), the fuzzer stops sending probes and logs a warning |

**As of 5.18.0 (Phase 172, SAFE-02):** the budget ceiling in guardrail #2 is enforced at
argument-validation time when `--fuzz` is set, before any config load or scan phase begins — a
`--fuzz-budget` above the hard max is **rejected with an error, not silently clamped down to 500**. The
boundary is inclusive: `500` is accepted, `501` is rejected. A request that exceeds the
ceiling prints coded error `QRK-FUZZ-002` and exits `2`. The default of `50` is unchanged.
See [docs/error-codes.md](error-codes.md) for the `FUZZ` error domain's full cause/fix
text.

### Findings produced

REST fuzzing results appear as `CryptoEndpoint(protocol="REST_FUZZ")` rows in the
standard findings table:

| Finding type | Severity | Description |
|-------------|----------|-------------|
| TLS downgrade accepted | HIGH | Server accepted a downgraded TLS version on a REST endpoint |
| Weak cipher accepted | HIGH | Server negotiated a weak cipher suite on a REST endpoint |
| HSTS header missing | HIGH | `Strict-Transport-Security` header absent on an HTTPS endpoint |
| HTTP-only credential transmission | HIGH | The spec declares a plain `http://` endpoint and the scan was given an `--auth-*` credential. QUIRK does not send the credential to test whether the endpoint accepts it — feeds `agility_fuzz_crypto_posture_ratio` scoring penalty |
| JWT alg-confusion acceptance | CRITICAL | Server accepted an RS256→HS256 forged token (requires `--fuzz-jwt-alg-confusion`) — feeds `agility_fuzz_crypto_posture_ratio` scoring penalty |

> **CBOM note:** REST_FUZZ endpoints are excluded from the CBOM TLS and certificate
> component builders (Pass-2 and Pass-3 skip lists) to prevent phantom
> `crypto/protocol/tls/*` and `crypto/certificate/*` components for endpoints that
> were not TLS-scanned.

### Scoring impact

CRITICAL and HIGH REST fuzz findings feed the `agility_fuzz_crypto_posture_ratio` signal
in `SCORE_WEIGHTS` (weight: `4.0`). INFO `probe_skipped` rows are excluded from
the finding count to prevent score drift when endpoints are unreachable.

### Example: fuzz a local OpenAPI target

```bash
# Passive OpenAPI spec analysis + active REST fuzzing
quirk --config config.yaml \
  --openapi-spec ./openapi.json \
  --fuzz

# Include the JWT algorithm-confusion probe
quirk --config config.yaml \
  --openapi-spec ./openapi.json \
  --fuzz --fuzz-jwt-alg-confusion

# Set a custom request budget (max 500)
quirk --config config.yaml \
  --openapi-spec ./openapi.json \
  --fuzz --fuzz-budget 100
```

---

## Output Block

Controls where QU.I.R.K. writes reports, CBOM files, and its internal database. Both keys are required: the loader gives them no default, and the values below are what the shipped template sets.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `directory` | string | *(required)* | Directory for the HTML/DOCX reports, Markdown reports, CBOM files, and the findings, intelligence, and run-stats JSON (and the discovery/fingerprint caches when `--cache` is used). The shipped template sets `"./quirk-output"` |
| `db_path` | string | *(required)* | SQLite database path for scan results. The shipped template sets the **canonical path** `"./quirk-output/quirk.db"` (Phase 74 D-05) — the dashboard, `quirk doctor`, and `quirk console` resolve to it when `QUIRK_DB_PATH` is unset (all three use `./quirk.db` or `./output/quirk.db` instead when that is the only one of the three files present, and report an error when more than one is present). Pointing `db_path` elsewhere means the scanner writes one database while the dashboard reads another. |

```yaml
output:
  directory: "quirk-output"
  db_path: "./quirk-output/quirk.db"
```

---

## Intelligence Block

Controls the quantum-readiness scoring calibration and version metadata.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `intelligence_version` | string | `"4.2.0"` | Accepted and stored, but nothing reads it: the intelligence JSON stamps the platform version instead |
| `profile` | string | `"balanced"` | Score calibration profile: `lenient`, `balanced`, `strict` |
| `calibration_overrides` | dict | `{}` | Per-weight scoring overrides for advanced users |

**Score calibration profiles:**

- `lenient` — Reduces penalty weights. Use in immature environments where a score shock would be counterproductive. Suitable for a first engagement where you need to show progress rather than alarm.
- `balanced` — Default. The weights as shipped (multiplier 1.0).
- `strict` — Increases penalty weights. Use in high-compliance environments (FedRAMP, CNSA 2.0) where the client must demonstrate a tighter posture.

#### How Score Profiles Work

Score profiles scale the weights of the **crypto-agility**, **identity/certificate**, **data-at-rest**, and **data-in-motion** scoring categories. Hygiene and TLS modernization weights are unchanged across all profiles. A profile name other than `lenient`, `balanced`, or `strict` falls back to `balanced`.

| Profile | Weight multiplier (agility, identity, data-at-rest, data-in-motion) | Use Case |
|---------|------------------------------------------------------------------|----------|
| `strict` | 1.4x base | Post-quantum readiness assessment — amplifies the penalties in those categories |
| `balanced` | 1.0x (default) | General-purpose assessment |
| `lenient` | 0.7x base | Status-quo baseline — reduces those penalties for organizations not yet planning PQC migration |

Setting `calibration_overrides` in the intelligence section allows fine-grained per-weight adjustments: an override replaces the final weight, after the profile multiplier is applied. For example:

```yaml
intelligence:
  profile: strict
  calibration_overrides:
    agility_rsa_only_penalty: 4.0  # Override strict's amplified RSA penalty
```

```yaml
intelligence:
  intelligence_version: "4.2.0"
  profile: "balanced"   # lenient|balanced|strict
  calibration_overrides: {}
```

---

## Remediation Aliases (Phase 179; first released in 5.19.0)

Maps an old identity (host or IP from a prior engagement's scan) to its current identity. It is
meant to let re-scan burndown match findings that moved across DHCP churn, hostname-vs-IP drift,
VIPs, and container reassignment. **Today the mapping is only parsed and validated: no report,
burndown, or other code reads it yet, so setting it changes nothing.** Without an alias, a finding
that "moved" between the baseline scan and the re-scan reads as two unrelated findings — one still
open on the old identity, one newly discovered on the new identity.

| Key | Type | Default | Description |
|-----|------|---------|--------------|
| `remediation_aliases` | dict (string → string) | `{}` | Maps a prior-scan identity to its current identity, one entry per known rename/move. Parsed and validated, but not yet applied by any report or burndown |

```yaml
remediation_aliases:
  web01.corp.example: 10.0.0.15
  old-db-host.internal: db02.corp.example
```

**Parsing rules an operator can rely on:**

- The top-level value must be a mapping. Any other shape — a list, a bare string, `null` — yields
  an empty alias set rather than raising a config error; the scan proceeds with no aliases applied.
- Individual entries are dropped, not fatal, when malformed: an entry whose value is itself a
  nested `dict` or `list`, or whose value is `null`, is skipped.
- Both the key and the value are coerced to strings and `.strip()`-ed. An entry that strips to an
  empty key or empty value is dropped.
- A dropped or skipped entry does not stop the scan and does not raise — it is silently absent
  from the alias set, which is why the syntax above should be treated as exact rather than
  approximate.

**Two design constraints, because they are the reason this key exists rather than something
automatic:**

- QU.I.R.K. does **not** attempt automatic re-scan entity resolution. Matching purely on
  `(host, port)` breaks on DHCP lease changes, hostname-vs-IP recording drift, load-balancer VIPs,
  and container/pod churn between engagements — any of those would silently misattribute progress.
- Aliases are **never** learned automatically. The only source of truth is this file, reviewed by
  a human, and versioned alongside the rest of the scan config. If an identity isn't listed here,
  QU.I.R.K. treats it as a new, unrelated identity — never as an assumed match.

---

## Scan Profiles (`--profile` flag)

The `--profile` flag (`quick`, `standard`, or `deep`; default `standard`) adjusts a few `scan` values and the email and broker connectors for the run — `config.yaml` is not modified. A profile only replaces a value that is unset or still equals its default.

| Profile | `fingerprint_timeout_seconds` | `fingerprint_concurrency` | Email and broker connectors | Use case |
|---------|-------------------------------|---------------------------|------------------------------|----------|
| `quick` | `3` | `300` | not auto-enabled | Discovery pass — faster fingerprinting of live hosts |
| `standard` | `4` (unchanged) | `200` (unchanged) | enabled unless the YAML sets `enable_email` / `enable_broker` | Default |
| `deep` | `6` | `150` | enabled unless the YAML sets `enable_email` / `enable_broker` | Slower fingerprinting with fewer workers |

With the current defaults a profile does not change `tls_enum_mode`, the TLS and SSH timeouts, or the TLS and SSH worker counts. Set `tls_enum_mode: deep` and those keys in the `scan` block yourself.

```bash
# Discovery pass to find live hosts quickly
quirk --config config.yaml --profile quick

# Default balanced scan
quirk --config config.yaml --profile standard

# Thorough enumeration for final deliverable
quirk --config config.yaml --profile deep
```

---

## Port Scope (v5.6+ — Phase 121)

Dashboard-initiated scans gain control over **port coverage** via a per-scan "port scope". Port scope controls which TCP ports are probed during the discovery phase. It is separate from the scan profile, which sets the fingerprint timeout and worker count and whether the email and broker connectors are auto-enabled (see Scan Profiles). The one overlap: `custom` scope turns the email and broker connectors off (see below).

> **TCP only.** Port scope applies to TCP discovery. It does not cover UDP: the opt-in SNMP (`--enable-snmp`, UDP/161) and BACnet/IP (`--enable-bacnet`) hardware probes are separate and ignore the port scope.

### Four scope values

| Scope | Description | nmap required? | Default? |
|-------|-------------|---------------|---------|
| `top1000` | nmap `--top-ports 1000` — most common 1000 TCP ports | Yes (forces nmap) | **Yes** |
| `common` | 17 curated `CONSULTING_TLS_PORTS` — fast, targets web/TLS/SSH services | No (builtin or nmap) | No |
| `all` | nmap `-p-` — all 65535 TCP ports; exhaustive, slow | Yes (forces nmap) | No |
| `custom` | User-specified port list (e.g. `443,8000-9000,15449`) | Honors nmap checkbox | No |

**Default is `top1000`** — it covers the most common services via nmap and works well for typical enterprise networks. The `common` scope is suitable when nmap is not installed or speed is the priority.

Port scope is a dashboard (New Scan) setting. The CLI has no port-scope flag: for `top1000` and `all` the dashboard writes `scan.nmap_port_scope` into the job YAML and starts the scan with `--discovery nmap`; for `common` and `custom` it writes the port list into `scan.ports_tls`.

### Wide scopes without nmap installed

If you select `top1000` or `all` but nmap is not available on the system PATH, the scan job **fails** with an actionable error message (install nmap and make sure it is on `PATH`, or select the Common TLS scope). There is **no silent fallback** to a narrower port list — you always know what was actually scanned.

### Custom port spec

The `custom` scope accepts a comma-separated list of ports and port ranges:

```
443,8000-9000,15449,16443
```

Rules:
- Ports must be in the range 1–65535.
- Ranges must be `low-high` with `low <= high`.
- The expansion cap is 2048 unique ports — specs that expand to more than 2048 ports are rejected with a 422 error (guards against accidentally specifying `1-65535` in the custom field).
- The nmap checkbox is honored: if you also enable nmap, your custom ports are passed to nmap as `-p <csv>` together with four extra ports (22, 80, 8000 and 8080) that nmap discovery always adds; if nmap is off, builtin discovery probes the listed ports (plus 502 when Modbus is enabled).
- **Custom scope turns the email and broker connectors off.** The email and broker connectors (SMTP/IMAP/POP3 and Kafka/AMQP/Redis) probe their own fixed service-port tables, which the `standard` and `deep` profiles normally auto-enable independently of the port list. Under custom scope the dashboard writes `enable_email: false` and `enable_broker: false` into the job, so a 2-port custom scan does not also probe the 7 fixed email ports. Other probes can still reach ports outside your list (see "CLI `scan.ports_tls`" below). To scan email/broker crypto, use the `common`, `top1000`, or `all` scope, or turn the connector back on in the Connectors panel (the `common`/Consulting list already curates in the implicit-TLS email ports 993/995/465 by design).

### Dashboard form vs. presets precedence

*(D-16, Phase 194 — the one canonical home for this precedence rule. Both the Connectors panel
(Phase 193) and the Advanced scan-fields panel (Phase 194) follow the exact mechanism described
here; if you are looking for connector-specific or advanced-field-specific precedence detail, read
this section first — the per-panel notes below only name what each panel additionally does, they
do not restate the mechanism.)*

The dashboard's New Scan form — both the Connectors panel and the Advanced scan-fields panel — and
the CLI's scan profiles resolve to a single effective config through one shared load path
(`load_config`, then `apply_profile`), not two competing ones:

- **The dashboard writes a delta into the job YAML — only the fields you actually touched.**
  Leaving a field or toggle untouched submits no key for it at all; the `advanced` and
  `connectors` objects in the `POST /api/jobs` payload carry only the keys you changed (under
  `custom` scope the form also copies your port spec into `advanced.ports_tls`). Those keys are
  merged into the job YAML's `scan:`, `assessment:` and `connectors:` blocks on top of the
  port-scope defaults.
- **Connector toggles are recorded in `_user_set_fields`, and `apply_profile` honors them.**
  `load_config` records the keys present under `connectors:` in `ConnectorsCfg._user_set_fields`, and
  the profile-application step checks that set before it auto-enables `enable_email` and
  `enable_broker` (the `standard` and `deep` profiles), so an explicit `true` or `false` from the
  Connectors panel always beats the scan profile. The scan profiles are `quick`, `standard` and
  `deep`; `lenient`, `balanced` and `strict` are the scoring calibration, which does not touch scan
  behavior.
- **Scan fields are different: `apply_profile` only fills a scan value that is unset or equal to
  the profile's baseline default.** An explicit value that happens to equal that baseline is
  replaced — for example `scan.fingerprint_concurrency: 200` under `--profile quick` becomes `300`.
  Treat the Advanced panel's timeout and concurrency values as a request that a profile can
  override when it equals the baseline default.
- **Vertical presets never touch the config.** A vertical's scan preset (for example the Healthcare
  edition's targets, `standard` profile and `strict` calibration) only pre-fills the New Scan
  form; whatever the form submits is what the delta contains.
- **The overlay is merged last.** `build_job_config_dict` applies every `port_scope`-derived
  default first, then merges the Advanced/Connectors overlay on top — so an explicit advanced TLS
  port list always beats the port-scope default, never the reverse. (Under `top1000` and `all`,
  nmap discovery runs `--top-ports 1000` or `-p-` and does not read `scan.ports_tls`.)
- **The Effective Config preview resolves through the scan's own path**, not a client-side
  simulation: `GET /api/config/effective` builds the job dict with the same `build_job_config_dict`,
  then runs `load_config` and `apply_profile`, as a real submission does. Its scan, connector-toggle
  and assessment values are the ones the scan runs with. It shows the server config's own
  `security.allow_internal_targets`, as a real job does. Its `output` paths point at a temporary
  directory, and it never receives credential values typed into the form: for each credential the
  form has filled it shows `set` (the form sends only the field names), and for the rest it shows
  whether the server's config or environment holds one.

### Connectors panel: explicit toggle vs. custom-port-scope suppression (D-13/D-14, Phase 193)

The "Custom port spec" section above describes the dashboard's `custom` port scope force-disabling
`enable_email`/`enable_broker` so a narrow custom scan doesn't also probe the fixed email/broker
service ports. As of Phase 193's Connectors panel (`docs/operators-guide.md` §3.1.4), that
suppression is no longer absolute — this is the connector-specific instance of the explicit-value-
beats-preset rule stated in the canonical precedence section immediately above:

- **D-14 — an explicit toggle beats custom-port-scope suppression.** If you explicitly turn
  `enable_email` or `enable_broker` back on in the Connectors panel while `custom` port scope is
  selected, your explicit toggle wins — the scan runs that connector even though custom scope would
  otherwise have suppressed it.
- **D-13 — only the toggles you touch are written to the job config.** The Connectors panel writes a
  delta-only overlay: flipping one connector's switch writes only that field into the submitted job
  YAML's `connectors:` block. Every connector you didn't touch keeps whatever the active scan
  profile's default would otherwise set — so toggling on one connector never silently resets
  or overrides the other 24.

### Advanced scan-fields reference (PARITY-04, Phase 194; PARITY-08/09, Phase 198)

The dashboard's collapsed "Advanced" section on the New Scan form (`docs/operators-guide.md`
§3.1.5) exposes **27 fields** (the original 8 from Phase 194, extended to the full 27-field
scan-behavior surface in Phase 198), each following the delta-only precedence rule above:

| Field | YAML path | Accepted values / bounds | Default |
|-------|-----------|---------------------------|---------|
| TLS Ports | `scan.ports_tls` | Comma-separated ports/ranges (e.g. `443,8443,9000-9010`); each value 1-65535 | 17-port `CONSULTING_TLS_PORTS` list — see "Default TLS port list" above |
| TLS Enumeration Mode | `scan.tls_enum_mode` | `fast` or `deep` only — see D-19 note below | `fast` |
| Send SNI | `scan.include_sni` | boolean | `true` |
| Default timeout | `scan.timeouts.default_seconds` | integer seconds, 1-300 | `5` |
| TLS timeout | `scan.timeouts.tls_seconds` | integer seconds, 1-300 | `6` |
| SSH timeout | `scan.timeouts.ssh_seconds` | integer seconds, 1-300 | `6` |
| Retry count | `scan.retry.retry_count` | integer attempts, 0-10 (accepted, but no scanner reads `scan.retry` yet, so it changes nothing — see Timeout & Retry Policy) | `0` |
| Data Classification | `assessment.data_classification` | `public` / `internal` / `confidential` / `regulated` only — see D-21 note below | `confidential` for dashboard-dispatched scans |
| Fingerprint timeout | `scan.timeouts.fingerprint_seconds` | integer seconds, 1-600 | `4` |
| JWT timeout | `scan.timeouts.jwt_seconds` | integer seconds, 1-600 | `10` |
| Container timeout | `scan.timeouts.container_seconds` | integer seconds, 1-600 | `120` |
| Source timeout | `scan.timeouts.source_seconds` | integer seconds, 1-600 | `300` |
| DNSSEC timeout | `scan.timeouts.dnssec_seconds` | integer seconds, 1-600 (accepted, but the DNSSEC scanner uses a fixed 10 s, so it has no effect) | `10` |
| SAML timeout | `scan.timeouts.saml_seconds` | integer seconds, 1-600 (accepted, but the SAML scanner uses a fixed 10 s, so it has no effect) | `10` |
| Kerberos timeout | `scan.timeouts.kerberos_seconds` | integer seconds, 1-600 (accepted, but the Kerberos scanner uses a fixed 10 s, so it has no effect) | `10` |
| Vault timeout | `scan.timeouts.vault_seconds` | integer seconds, 1-600 | `10` |
| DB Connect timeout | `scan.timeouts.db_connect_seconds` | integer seconds, 1-600 | `5` |
| Broker timeout | `scan.timeouts.broker_seconds` | integer seconds, 1-600 | `10` |
| Email timeout | `scan.timeouts.email_seconds` | integer seconds, 1-600 | `10` |
| Backoff base | `scan.retry.backoff_base_seconds` | float seconds, must be > 0; server rejects `base > max` naming both fields (no scanner reads `scan.retry` yet, so it changes nothing) | `1.0` |
| Backoff max | `scan.retry.backoff_max_seconds` | float seconds, must be > 0 and >= backoff base (no scanner reads `scan.retry` yet, so it changes nothing) | `5.0` |
| Scan concurrency | `scan.concurrency` | integer workers, 1-500; caps nothing (the fingerprint, TLS and SSH phases use their own worker counts below) | `100` for dashboard-dispatched scans (the job YAML always writes it); required in hand-authored YAML, where the shipped template uses `20` |
| Fingerprint concurrency | `scan.fingerprint_concurrency` | integer workers, 1-500 | `200` |
| TLS concurrency | `scan.tls_concurrency` | integer workers, 1-500 | `150` |
| SSH concurrency | `scan.ssh_concurrency` | integer workers, 1-500 | `100` |
| Motion concurrency | `scan.motion_concurrency` | integer workers, 1-500 — shared pool for email + broker connector scanning | `50` |
| TLS-Designated Ports | `scan.tls_designated_ports` | Comma-separated ports/ranges (same format as TLS Ports), max 512 characters | empty list (no ports forced TLS-designated) |

**D-11 — the bounds asymmetry between the 3 Phase-194 timeout fields and the 11 new Phase-198
timeout fields is deliberate, not a typo.** `timeout_default_seconds`, `timeout_tls_seconds`, and
`timeout_ssh_seconds` keep their original 1-300 bound; all 11 new per-scanner timeout fields
(Fingerprint through Email above) use a wider 1-600 bound, because the container and source
scanners already default to 120 and 300 seconds, which leaves a 1-300 bound no headroom — scoping
the wider range to only the new fields avoids silently loosening the three original fields' validation.

**D-04 — three intentional gaps: recorded, not rendered.** The following `scan.*` fields exist in
`quirk/config.py` but deliberately have **no** Advanced-panel control and no dashboard-settable
overlay path. This is a recorded design decision, not an oversight:

- `scan.openapi_spec_path` — a local filesystem path (or scope-gated URL) fed to the REST-fuzzing
  OpenAPI loader. It is the same trust-boundary class as `assessment.logo_path`: a
  path-traversal-capable input that is safe when hand-authored in `config.yaml` by an operator with
  filesystem access, but not safe to expose as a dashboard-submitted string from a browser.
- `scan.hardware_history_retention_days` and `scan.hardware_drift_event_retention_days` — these
  govern how long hardware-crypto engagement history and drift events are retained at the
  **install** level, not how a single scan behaves. They belong with install-scoped retention
  policy, not a per-scan Advanced form field.

If you need to set any of these three, hand-edit `config.yaml` directly — there is no dashboard
path for them, by design.

**D-19 — `tls_enum_mode` has no `off` behavior.** The config template comment historically read
`off|fast|deep` (see the `scan:` example block above), but `quirk/scanner/tls_scanner.py` coerces
any value outside `{fast, deep}` back to `fast` at scan time — `off` does not turn TLS
enumeration off. Because of this, the Advanced panel's TLS Enumeration Mode dropdown deliberately
offers only Fast and Deep; it does not offer a value that has no effect.

**D-21 — the wizard and the dashboard offer exactly four `data_classification` values.** `public`,
`internal`, `confidential`, `regulated` — the same four values the CLI wizard's `_DATA_CLASS_MAP`
offers (see the "Assessment Block" table above). The Advanced panel's Data Classification dropdown
offers exactly these four, and `confidential` remains the default for dashboard-dispatched scans
that don't touch this field. A hand-authored `config.yaml` is not checked: the loader accepts any
string, and the shipped template writes `CONFIDENTIAL`.

**D-18 — there is no SSH port list setting, in the config file or the dashboard.** SSH targets are
never enumerated by a dedicated port list; they are derived from protocol-classified open ports
found during discovery (the same fingerprint pass that classifies a port as TLS-, SSH-, or
plaintext-HTTP-carrying). There is nothing to configure, which is why the Advanced panel renders no
"SSH Ports" field.

### CLI `scan.ports_tls`: email/broker auto-enable is independent of your port list (Phase 173)

The section above documents the **dashboard's** `custom` port scope, which explicitly disables the
email and broker connectors so a narrow custom scan does not also probe the fixed email/broker
service ports. **There is no CLI equivalent of that suppression.** If you hand-author
`scan.ports_tls` in `config.yaml` — narrowing it to, say, a single TLS port — the `standard` and
`deep` profiles still auto-enable `connectors.enable_email` and `connectors.enable_broker`
independently of that list, exactly as they do when `ports_tls` is left at its default. This is
intentional, documented behavior (Phase 32 / Phase 33 D-10 / Phase 72 D-02): a CLI user who runs
`--profile standard` and never touches the `connectors` block should still get full default
crypto-posture coverage of any mail/broker services present, rather than silently missing them
because they didn't know to opt in.

**Operator note.** If you want no email or broker probing beyond the ports you listed in
`scan.ports_tls`, you must say so explicitly:

```yaml
connectors:
  enable_email: false
  enable_broker: false
```

An explicit `false` here always wins over the profile auto-enable (Phase 72 D-02 / WR-11), so it
stops the `standard` and `deep` profiles from probing the email and broker service ports.
Narrowing `ports_tls` alone does **not** do that: the email and broker connectors have their
own fixed service-port tables and are enabled or disabled independently of `scan.ports_tls`.

This does **not** limit the scan to exactly your `ports_tls` list. Other probes still reach ports
outside it:
- With nmap discovery, the port sweep adds 22, 80, 8080 and 8000 to your `ports_tls` list.
- `--enable-modbus` (or `connectors.enable_modbus: true`) adds port 502, with or without nmap
  discovery.
- Hardware fingerprinting probes ports 443, 8443, 8080 and 80 for a management page on any SSH
  host whose vendor it could not identify from the banner. When `pysnmp` is installed, it also sends
  an SNMP query to UDP/161.

### `security.allow_internal_targets`

`security.allow_internal_targets` (default `false`) controls whether the scanners that fetch a URL, namely the JWT/JWKS, OpenAPI spec and SAML metadata probes and the REST fuzzer, may contact internal and loopback addresses (RFC1918 ranges, `127.x.x.x`, link-local). A URL on the cloud-metadata address `169.254.169.254` is still refused when it is `true`. The dashboard reads this flag from the server's own config file (`QUIRK_CONFIG_PATH`, default `./config.yaml`) and copies it into each job it dispatches; a browser cannot set it. The CLI equivalent is `--allow-internal-targets`. It does **not** restrict which targets you can scan: the core TLS, SSH and fingerprint scans, and the dashboard's New Scan form, accept loopback and RFC1918 targets either way.

```yaml
security:
  allow_internal_targets: true   # Set to false on machines that also scan untrusted client environments
```

> **Operator note:** `allow_internal_targets: true` is the correct setting for a QUIRK instance
> that only ever scans your own infrastructure (e.g., a chaos lab or internal assessment server),
> where the JWT, OpenAPI, SAML and fuzzing probes must reach internal hosts.
> If the same QUIRK instance is used to scan **untrusted client environments**, set this back to
> `false` — it stops those probes from following a client-controlled URL (for example a JWKS or
> SAML metadata address) to loopback or RFC1918 addresses on your own network. To restrict
> *which hosts can be scanned at all*, use `security.trusted_targets` below.

### Port scope in the dashboard

The New Scan page exposes a "Port Scope" selector with the four options described above. Selecting `top1000` or `all` automatically checks and locks the "Enable nmap discovery" checkbox (nmap is required for those scopes). Selecting `common` or `custom` leaves the checkbox user-controlled.

---

### `security.trusted_targets` (Phase 143, TAIL-02)

First released in 5.11.0, `security.trusted_targets` is a server-enforced scan-consent allowlist —
a list of exact hosts/IPs and CIDR ranges QU.I.R.K. is authorized to scan. It is enforced at a
check used by **both** the CLI (`quirk`/`run_scan.py`) and the dashboard's "New Scan"
(`/scan/new`) entry point, with the same matching function. Both entry points check the
same inputs: `targets.fqdns`, `targets.cidrs`, `targets.include_ips`, and every host-naming
`connectors.*` field (such as `broker_targets`, `jwt_targets` or `vault_addr`), whether or not
the connector is enabled. For a container image reference the explicit registry host is checked.
Each `azure_keyvault_urls` entry is checked by its host. For `k8s_kubeconfig`, every cluster `server`
host in the named kubeconfig is checked, and a file that cannot be read as a kubeconfig is refused.
The dashboard checks the targets typed into the form and the Connectors-panel hosts against the
server's own config file (`QUIRK_CONFIG_PATH`), and writes the server's `trusted_targets` list
into the generated job config, so the scan subprocess enforces it as well. If the server config
cannot be read, job creation is refused with `QRK-DASHBOARD-014` instead of running unchecked. Scheduled
scans (added on the Schedules page or with `quirk schedule add`) are checked against the server's
`trusted_targets` when they are created, when they are enabled again, and when `quirk schedule add`
runs (an unreadable server config refuses with `QRK-DASHBOARD-014`). A recurring run started
without `--scan-config` carries the server's `trusted_targets` and `allow_internal_targets` into
its generated config, so the scan enforces them; with `--scan-config`, that file's own `security`
block applies.
If the server config cannot be read when a recurring run started without `--scan-config` is due, the
run is marked failed and no scan starts. Once the scheduler has read the file with settings in it, the
file going missing or empty is treated the same way until it is restored or the scheduler is restarted.

```yaml
security:
  trusted_targets:
    - api.acme.com
    - 10.0.0.5
    - 10.0.0.0/24
```

| Behavior | Rule |
|----------|------|
| **Empty or absent (default)** | Allow-all — backward compatible with every existing scan config/CLI invocation. No enforcement happens. |
| **Populated** | Only the listed hosts/IPs/CIDRs may be scan targets. A checked target outside the list is rejected **before any scan begins** (see above for which inputs each entry point checks). |
| **Matching semantics** | Exact, case-sensitive string match against a listed entry, or CIDR containment for entries written as `a.b.c.d/nn`: an IP target (or the DNS-resolved addresses of a hostname target) inside a listed CIDR is allowed. A CIDR scan target is only allowed when that exact CIDR string is listed. No wildcard subdomain matching — `*.acme.com` is not supported; list every FQDN explicitly. Connector host fields are matched the same way on the CLI and in the dashboard. |
| **CLI rejection** | `run_scan.py` raises `ValueError` naming the redacted out-of-allowlist target, aborting before `init_db()`/scan execution. |
| **Dashboard rejection** | The `/scan/new` → `POST /api/jobs` endpoint returns **HTTP 422** for an out-of-allowlist target — no `ScanJob` database row is created and no subprocess is spawned. |

> **Operator note:** This is an opt-in consent gate, not a security boundary against a malicious
> operator — it exists to prevent an operator (or an automated scheduler) from accidentally
> pointing a shared QUIRK instance at a host outside its authorized engagement scope. Leave it
> empty for single-engagement or lab use where every target is already trusted.

### `security:` block reference

The optional top-level `security:` block has six keys. An absent block, or an absent key, takes the
default shown; unknown keys under `security:` are ignored.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `allow_internal_targets` | bool | `false` | Let the URL-fetching scanners (JWT/JWKS, OpenAPI spec, SAML metadata, REST fuzzer) contact RFC1918, loopback and link-local addresses; a URL on the cloud-metadata address `169.254.169.254` is still refused. CLI: `--allow-internal-targets`. See `security.allow_internal_targets` above. |
| `allow_cleartext_broker_probe` | bool | `false` | Permit broker management-API probes over plain HTTP and Redis probes with `ssl_cert_reqs=none`. CLI: `--allow-cleartext-broker-probe`. Each RabbitMQ host scanned gets a HIGH advisory; Redis targets get none. |
| `allow_insecure_jwks` | bool | `false` | Disable TLS certificate verification for JWKS fetches. CLI: `--allow-insecure-jwks`. Each JWKS URL fetched this way appears as a HIGH finding titled `JWKS fetched with TLS certificate verification disabled` (counted in the findings totals, not in the readiness score). This is a `security:` key, not a `connectors:` key. |
| `api_token` | string | `""` | Dashboard API token; empty means dashboard authentication is off. Written by `quirk token generate`; the `QUIRK_API_TOKEN` environment variable overrides it. See Dashboard Authentication. |
| `cors_origins` | list of strings | `[]` | Dashboard CORS allowlist. Empty falls back to the port-aware loopback default; `QUIRK_CORS_ORIGINS` overrides it. See CORS Allowlist. |
| `trusted_targets` | list of strings | `[]` | Scan-consent allowlist of hosts, IPs and CIDRs; empty allows every target. See `security.trusted_targets` above. |

---

## CLI Flag Reference

### `quirk` — Scan Flags

The table lists every flag that `run_scan.py --help` prints, grouped by topic rather than in help order.
Authenticated-scanning, fuzzing and OpenAPI flags are covered in more depth in their own sections above.

| Flag | Default | Description |
|------|---------|-------------|
| `-h`, `--help` | | Show the help message and exit |
| `--version` | | Print the program version and exit |
| `--quiet` | `false` | Suppress banner and decorative output |
| `--config PATH` | (interactive) | Path to config.yaml; skips interactive prompts when provided |
| `--targets-file PATH` | none | File of targets, one per line, `#` comments allowed. Replaces the config's `targets.fqdns` and `targets.cidrs` (does not merge); `targets.include_ips` and `targets.exclude_ips` from the config still apply |
| `--profile` | `standard` | Scan profile: `quick`, `standard`, `deep` |
| `--score-profile` | unset (the config's `intelligence.profile`, default `balanced`) | Scoring calibration: `lenient`, `balanced`, `strict`. Overrides `intelligence.profile`; does not affect scan behavior |
| `--report-profile NAME` | none | Named report branding/template profile to apply (see `quirk report profile list`). Only fills unset `report.branding.*` / `report.template_dir` values; does not affect scan behavior or scoring |
| `--verbose` | `false` | Verbose output during scan |
| `--progress` | `false` | Show tqdm progress bars |
| `--discovery` | `builtin` | Discovery mode: `builtin` or `nmap` |
| `--nmap-path` | `nmap` | Path to nmap executable |
| `--nmap-timeout` | `1800` | **Deprecated — has no effect** (Phase 146 DISC-05). Chunked discovery derives its per-batch budget from `discovery_timeout_for_batch()` = `min(300, 30 + 0.26 × batch_size)` seconds; no code path reads this flag. To change the budget, reduce discovery scope or adjust the `_DISCOVERY_TIMEOUT_*` constants in `quirk/discovery/nmap_provider.py`. See operators-guide.md §11.4. |
| `--nmap-extra-args` | `""` | Extra nmap arguments (pass as quoted string) |
| `--safe-mode` | `false` | Reduce concurrency and increase timeouts for fragile networks |
| `--check-in` | `false` | Lightweight check-in re-probe of already-known hardware devices only; skips network discovery, all non-hardware scanner phases, scoring and report generation |
| `--rate-limit` | `0.0` | Targets per second rate limit (0 = disabled) |
| `--cache` | `false` | Enable discovery/fingerprint result cache |
| `--cache-ttl-hours` | `24` | Cache time-to-live in hours |
| `--resume` | `false` | Reuse cache if valid (skip re-discovery); the discovery cache is only read when `--cache` is also set |
| `--force-discovery` | `false` | Ignore existing discovery cache and re-run |
| `--resume-scan-id SCAN_RUN_ID` | none | Resume an interrupted scan from its last completed stage; use `--list-resumable` to find valid IDs. Only a scan run with `--db-path` writes the stage checkpoints this needs |
| `--list-resumable` | `false` | List interrupted scans that can be resumed with `--resume-scan-id`, then exit |
| `--azure-servicebus-namespace NAME` | none (repeatable) | Azure Service Bus namespace to probe; may be given more than once |
| `--aws-sqs-region REGION` | none (repeatable) | AWS SQS region to probe; may be given more than once |
| `--allow-internal-targets` | `false` | Let the JWT/JWKS, OpenAPI spec URL, SAML metadata and REST-fuzzer fetches reach RFC1918, loopback and link-local IPs; a URL on the cloud-metadata address `169.254.169.254` is still refused. The SAML scanner emits a HIGH advisory for each internal target it fetches. Same as `security.allow_internal_targets` |
| `--allow-cleartext-broker-probe` | `false` | Permit broker management-API probes over HTTP (no TLS) and Redis `ssl_cert_reqs=none`. Emits one HIGH advisory per RabbitMQ host scanned; Redis targets get none. Same as `security.allow_cleartext_broker_probe` |
| `--allow-insecure-jwks` | `false` | Disable TLS certificate verification for JWKS fetches. Each JWKS URL fetched this way appears as a HIGH finding titled `JWKS fetched with TLS certificate verification disabled` (counted in the findings totals, not in the readiness score). Same as `security.allow_insecure_jwks` |
| `--job-id ID` | none | Dashboard job ID for progress reporting; does nothing when absent (set by the dashboard) |
| `--db-path PATH` | none | SQLite path for dashboard job-progress writes and for the stage checkpoints `--resume-scan-id` needs; without it no checkpoints are written. Job progress is written only when `--job-id` is also set; nothing checks that the two are given together (set by the dashboard) |
| `--auth-bearer [REF]` | none | Bearer token reference for the JWT/API scanner: an environment variable name or `@/path/to/file` (the file must be inside the current directory); the bare flag prompts for the value. The header is sent with the JWKS request |
| `--auth-api-key [REF]` | none | API-key reference for the `X-Api-Key` header; same reference forms as `--auth-bearer`. The header is sent with the JWKS request |
| `--auth-api-key-query [REF]` | none | API-key reference for the `api_key` query parameter on the JWKS/endpoint fetch URL, never a header; same reference forms. The value is sent to the target and replaced with `REDACTED` only in log output |
| `--auth-basic [REF]` | none | HTTP Basic credential reference; the resolved value must be `user:password` (QUIRK base64-encodes it; do not pre-encode; a value with no colon is rejected); same reference forms. The header is sent with the JWKS request |
| `--openapi-spec FILE_OR_URL` | none | Local OpenAPI/Swagger spec file, or an HTTP(S) URL within the configured scan targets (scope gate enforced before any fetch). Overrides `scan.openapi_spec_path` |
| `--inventory-code-signing` | `false` | Inventory code-signing certificates from LDAP `userCertificate` attributes (Phase 95 CSIGN-01) and from the Code Signing EKU on leaf certificates the TLS phase captured |
| `--fuzz` | `false` | Enable active REST crypto-posture fuzzing (needs a local OpenAPI spec file from `--openapi-spec` or `scan.openapi_spec_path`; a URL spec is not fuzzed; TTY `CONFIRM` prompt; hard-aborts in non-TTY) |
| `--fuzz-jwt-alg-confusion` | `false` | Also run the JWT RS256→HS256 algorithm-confusion probe; it needs `--auth-bearer` carrying an RS256 token. Acceptance = CRITICAL |
| `--fuzz-budget N` | `50` | Maximum probe requests (hard max **500**; with `--fuzz`, values above 500 are rejected, never clamped) |
| `--enable-snmp` | `false` | Enable SNMP hardware fingerprinting: probes discovered hosts on UDP/161 with SNMP v2c for `sysDescr`/`sysName`/`sysObjectID`. Needs the `quirk-scanner[hw]` extra |
| `--enable-modbus` | `false` | Enable Modbus/TCP fingerprinting (one read-only Read Device Identification request to port 502). Targets PLCs and RTUs: get written authorization before enabling on production OT networks. Needs the `quirk-scanner[hw]` extra |
| `--enable-bacnet` | `false` | Enable BACnet/IP fingerprinting (a directed-unicast Who-Is over the standard BACnet/IP UDP port, then two ReadProperty requests, for model name and firmware revision, to a device that answers). Targets building-automation controllers: get written authorization before enabling on production OT networks. Needs the `quirk-scanner[hw]` extra |

### `quirk serve` — Dashboard Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--port` | `8512` | Port to serve the dashboard on |
| `--host` | `127.0.0.1` | Host address to bind |
| `--no-open` | `false` | Suppress auto-opening of browser on startup |
| `--insecure` | `false` | Allow binding a network-reachable interface with no API token configured (`QUIRK_API_TOKEN` or `security.api_token`). Without it, `quirk serve` refuses (exit code 2) to bind a non-loopback host unless an API token is configured. Use only on trusted, firewalled segments |

```bash
# Start dashboard on default port
quirk serve

# Start on a different port without auto-opening the browser
quirk serve --port 9000 --no-open

# Bind to all interfaces (e.g. for a remote development server).
# Refused unless an API token is configured (QUIRK_API_TOKEN or security.api_token)
# or you add --insecure.
QUIRK_API_TOKEN="<your-token>" quirk serve --host 0.0.0.0 --port 8512
```

### CORS Allowlist (v5.11 — Phase 147, DRAIN-03 / WR-02)

The dashboard API checks browser `Origin` headers against an allowlist: a CORS preflight from an unlisted origin gets HTTP 400, and responses to an unlisted origin carry no `Access-Control-Allow-Origin` header. Resolution order:

1. `QUIRK_CORS_ORIGINS` (comma-separated list) — wins whenever it is set to a non-empty value.
2. `security.cors_origins` in your YAML config file (`QUIRK_CONFIG_PATH`, default `./config.yaml`).
3. **Port-aware default** — if neither is set, the allowlist is built from the port `quirk serve` actually bound (via `QUIRK_DASHBOARD_PORT`, set automatically by `serve()`), e.g. `http://127.0.0.1:9000` and `http://localhost:9000` for `quirk serve --port 9000`. The port-less `http://127.0.0.1` / `http://localhost` entries are always included too, so reverse-proxy-on-port-80 deployments keep working.

Before Phase 147, the default was a hardcoded port-less pair (`http://127.0.0.1`, `http://localhost`) that could never match a real browser `Origin` header for the product's own default bind (`127.0.0.1:8512`). For a real deployment behind a domain name, set `QUIRK_CORS_ORIGINS` explicitly — see [Cloud Console Deployment](deployment-cloud-console.md#6-hardening-checklist).

### `quirk token` — Dashboard API Token CLI (Phase 102, AUTH-01)

The `quirk token` subcommand manages the `security.api_token` key in your QUIRK YAML config. The token is used to authenticate requests to the dashboard API and browser login form.

| Subcommand | Description |
|------------|-------------|
| `quirk token generate` | Mint a new CSPRNG token (`secrets.token_urlsafe(32)`) and write it to `security.api_token` in your config file. Prints the token to stdout so you can copy it for browser login. |
| `quirk token rotate` | Identical to `generate` — overwrites `security.api_token` with a new token. A server reading this file rejects the old token from its next request, and any active dashboard session using it is returned to the login form. A `QUIRK_API_TOKEN` set in the server's environment takes precedence over the file and is not changed by this command. |
| `quirk token show` | Print the currently persisted token from the YAML config file. Reads the raw YAML value; does **not** read `QUIRK_API_TOKEN`. Exits 1 if the config file is not found. |

Pass `--config /path/to/config.yaml` to any subcommand to target a non-default config location (the default is `config.yaml` in the current directory). `generate` and `rotate` re-write the whole file as YAML, so comments and key ordering in the config are lost (a warning is printed to stderr), and they create the file if it does not exist.

```bash
# Generate a token and write it to config.yaml
quirk token generate --config config.yaml

# Rotate the token (a server reading this file rejects the old one from its next request)
quirk token rotate --config config.yaml

# Show the currently configured token (reads YAML, not env var)
quirk token show --config config.yaml
```

> **Precedence note:** If `QUIRK_API_TOKEN` is set in the environment, it takes precedence over the `security.api_token` YAML value at runtime. `quirk token show` always displays the YAML-persisted value; if the env var is set, a reminder is printed indicating that the env var overrides the file value for the running dashboard process.

> **Security note:** `quirk token show` echoes the raw token to the terminal, which may appear in terminal scrollback. This is a local-operator tool convenience — the token is never transmitted over the network by this command. Never embed the token value in shell scripts, version-controlled config files, or URLs.

---

## Sensor Config (`sensor.yaml`)

`quirk sensor enroll` writes `sensor.yaml` for a sensor host; the full enrollment walk-through is in the
[Operator's Guide §8](operators-guide.md). Two keys record how the console URL was accepted:

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `allow_internal_console` | bool | `false` | Written by `--allow-internal-console`; lets the console URL resolve to a private/RFC1918 address. |
| `allow_insecure_console` | bool | `false` | Written by `--allow-insecure-console`; accepts an `http://` console URL for a non-loopback host. `quirk sensor push` reads it, so an enrollment made with the flag keeps working. An `https://` URL, or an `http://` URL on a loopback host, does not need it. |

## Dashboard Authentication (Phase 102, AUTH-01..03)

The QUIRK dashboard (served by `quirk serve`) optionally enforces token-based authentication on its `/api/*` routes, with two exceptions: `GET /api/health` and `GET /api/config` are always open (the login page needs them before a token exists). `POST /api/sensor/push` is separate: it always requires a per-sensor token and does not accept the dashboard token. Authentication is **off by default** — an empty or absent `security.api_token` means the dashboard is accessible without credentials (suitable for local development only). `quirk serve` refuses to bind a network-reachable host without a token unless you pass `--insecure`.

### Enabling authentication

Add a `security:` block to your QUIRK YAML config and populate `api_token`:

```yaml
security:
  api_token: ""   # populated by: quirk token generate --config config.yaml
```

Run `quirk token generate --config config.yaml` to write a random token into this field. Once the token is non-empty, the dashboard requires authentication on every `/api/*` request except the two open routes above. The dashboard reads the YAML token from the file named by `QUIRK_CONFIG_PATH` (default `./config.yaml` in the server's working directory), not from the `--config` you gave `quirk token`, so make sure both name the same file. A file that does not exist, or an empty one, means authentication is off. A token in the file enables authentication even when the file holds only a `security:` section. A file that exists but cannot be read or parsed (malformed YAML, a top level or `security` entry that is not a mapping, a path that is a directory or a dangling symlink, or a directory the server cannot enter) stops `quirk serve` with exit code 2 and makes every protected `/api/*` route answer 503 (`DASHBOARD-014`) until the file is fixed. Once the running server has read the file with settings in it, the file going missing or empty is treated the same way: protected routes answer 503 until the file is restored or the server is restarted. For production deployments, set `QUIRK_API_TOKEN`.

### Token precedence

| Source | Precedence | Notes |
|--------|-----------|-------|
| `QUIRK_API_TOKEN` env var | **Highest** | Set this in production deployments; checked first on every request, so it overrides the YAML value |
| `security.api_token` in YAML | Default | Written by `quirk token generate` / `quirk token rotate`; re-read from disk on every request, so a rotation takes effect without restarting the server |

### API authentication (programmatic clients)

All protected `/api/*` endpoints except `POST /api/sensor/push` accept a token via two equivalent headers. **`X-API-Key` takes precedence** — if it is present, `Authorization: Bearer` is not consulted.

| Header | Format | Notes |
|--------|--------|-------|
| `X-API-Key` | `X-API-Key: <token>` | Preferred for API clients |
| `Authorization` | `Authorization: Bearer <token>` | Fallback; supported for compatibility |

Both paths use `hmac.compare_digest` for timing-safe comparison. An invalid or absent token on a protected route returns HTTP 401 with error code `DASHBOARD-001`. Despite the hint text in that error ("Send the dashboard auth token in the X-Quirk-Auth header"), no `X-Quirk-Auth` header exists: send `X-API-Key` or `Authorization: Bearer` as shown below.

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
5. **Mid-session token rotation:** If you run `quirk token rotate` while a browser session is open, the next API request from that session returns HTTP 401 and the dashboard automatically returns you to the login form. Re-enter the new token to resume. A `QUIRK_API_TOKEN` set in the server's environment keeps its value, so rotate that variable where the server runs.

### Auth-disabled passthrough (development convenience)

When `security.api_token` is empty and `QUIRK_API_TOKEN` is not set, the dashboard serves every route except `POST /api/sensor/push` without authentication. This is intentional for local development and single-operator use. Do not deploy the dashboard on a network-accessible interface without setting a token.

---

## Vertical Editions (v5.6+)

The dashboard can run as a vertical-specific "edition" that tailors the UI for an
industry deployment. This is an **operator-side deployment setting, not a user-facing
picker** — the active vertical comes from the server's environment and config file and every
browser session sees the same edition. General installs add no vertical nav item, page, edition
badge or scan preset.

### Allowed values

| Vertical | Effect |
|----------|--------|
| `general` | Default. No vertical nav item, page, edition badge or scan preset |
| `healthcare` | Adds a "Healthcare Posture" sidebar nav item + HIPAA posture page (`/healthcare`), a "Healthcare Edition" badge beside the brand logo in the wide sidebar header and on the Scan Results page header, and an EHR/PACS/portal scan preset on the New Scan page |

### Resolution order

| Source | Precedence | Notes |
|--------|-----------|-------|
| `QUIRK_VERTICAL` env var | **Highest** | Case-insensitive; whitespace trimmed |
| `vertical:` key in YAML config | Default | Read from the file at `QUIRK_CONFIG_PATH` (default `./config.yaml`) — **not** the `--config` CLI flag. The server re-reads it on every `GET /api/config`, and the dashboard asks once per page load, so a YAML edit shows after a reload without restarting `quirk serve` |
| Neither set | Fallback | `general` |

Unknown or invalid values **fall back silently to `general`** — they do not raise an
error, and an unrecognised `QUIRK_VERTICAL` does not fall through to the YAML key. If you set `QUIRK_VERTICAL=healthcre` (typo), you get a general-edition
dashboard with no warning, so verify with the endpoint below after startup.

```yaml
# In config.yaml (must be the file QUIRK_CONFIG_PATH points at):
vertical: healthcare   # top-level key; allowed: general | healthcare
```

```bash
# Env var wins over YAML — useful for one-off sessions:
QUIRK_VERTICAL=healthcare quirk serve
```

### Verifying the active vertical

`GET /api/config` returns the resolved vertical. Like `/api/health`, this endpoint is
**unauthenticated** (the frontend needs it before login) and exposes only the vertical
name — no secrets or scan data.

```bash
curl http://127.0.0.1:8512/api/config
# {"vertical":"healthcare"}
```

### Adding a new vertical (developers)

All vertical UI reads from a single descriptor registry. No component checks for a vertical by
name; the sidebar and Scan Results edition badges check only `vertical.id !== "general"`.
A new vertical (e.g. Manufacturing, Retail) requires only:

1. A descriptor entry in `src/dashboard/src/lib/verticals.ts` (label, icon, accent
   color, optional nav item / scan preset / page component).
2. A page component, if the vertical has a dedicated route.
3. The vertical name added to `_ALLOWED_VERTICALS` in `quirk/config.py`.

---

## Minimal Valid Configuration

The minimum configuration to run a first scan. The loader gives no default to `assessment` (all four
keys), `scan.concurrency`, `scan.ports_tls`, `output.directory` or `output.db_path`, so a file that
omits any of them fails to load (with a `TypeError` or `KeyError`, not a coded error). Every other
key uses its default.

```yaml
assessment:
  name: "Quantum Crypto Readiness - CLIENT NAME"
  data_classification: "confidential"
  report_owner: "CLIENT NAME"
  timezone: "America/New_York"

scan:
  concurrency: 20
  ports_tls: [443]

targets:
  cidrs: [127.0.0.1]

output:
  directory: "quirk-output"
  db_path: "./quirk-output/quirk.db"
```

Save this as `config.yaml` in your working directory, then run:

```bash
quirk --config config.yaml
```

---

## Full Reference Configuration

A complete `config.yaml` showing the keys of every core block at their loader defaults, as a
copy-pasteable template. The keys marked `required` have no loader default; their values here come
from the shipped template. The `connectors:` block shows a representative subset; every
connector key is listed in the Connectors Block above, and the optional `report`,
`notifications`, `siem` and `ticketing` blocks are documented in their own sections.

```yaml
assessment:
  name: "Quantum Crypto Readiness - CLIENT NAME"      # required
  data_classification: "confidential"   # required; public|internal|confidential|regulated
  report_owner: "CLIENT NAME"           # required
  timezone: "America/New_York"          # required

scan:
  concurrency: 20                       # required; caps nothing (see the Scan Block)
  ports_tls: [443, 8443, 9443, 10443, 4433, 5001, 636, 3269, 993, 995, 465, 6443, 2376, 5432, 3306, 1433, 8200]  # required
  include_sni: true
  tls_enum_mode: fast                   # fast|deep
  fingerprint_concurrency: 200
  tls_concurrency: 150
  ssh_concurrency: 100
  motion_concurrency: 50
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
  tls_designated_ports: []
  hardware_history_retention_days: 180
  hardware_drift_event_retention_days: 365

targets:
  fqdns: []
  cidrs: []
  include_ips: []
  exclude_ips: []

connectors:
  enable_aws: false
  enable_azure: false
  enable_adcs: false
  adcs_targets: []
  adcs_search_base: null
  adcs_user: null
  adcs_password: null
  adcs_timeout: 10
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
  enable_modbus: false
  enable_bacnet: false
  enable_recurring_otics: false

output:
  directory: "quirk-output"             # required
  db_path: "./quirk-output/quirk.db"    # required

intelligence:
  intelligence_version: "4.2.0"
  profile: "balanced"                   # lenient|balanced|strict
  calibration_overrides: {}

security:
  allow_internal_targets: false
  allow_cleartext_broker_probe: false
  allow_insecure_jwks: false
  api_token: ""
  cors_origins: []
  trusted_targets: []

remediation_aliases: {}
```

---

## Notifications (first released in 5.5.0)

Phase 101 introduces a global notification system that alerts operators after each scheduled scan when HIGH/CRITICAL findings appear or the quantum-readiness score regresses. Notifications are **off by default** — opt in by adding a `notifications:` block to your QUIRK YAML config.

### Prerequisites

**Set `QUIRK_CONFIG_PATH`** to the path of your QUIRK YAML config file before starting the scheduler. The scheduler's `--config` argument points to the SQLite database; the notification system reads its YAML config from `QUIRK_CONFIG_PATH`.

```bash
export QUIRK_CONFIG_PATH=/etc/quirk/config.yaml
export QUIRK_DB_PATH=/var/lib/quirk/quirk.db
quirk scheduler run --config "$QUIRK_DB_PATH"
```

`QUIRK_CONFIG_PATH` is required: without it (or if the file has no `notifications:` block) notifications are silently off. `QUIRK_DB_PATH` is only one way to name the scheduler's database; `--config` takes precedence and the default is `./quirk.db`.

### Trigger rules (NOTIFY-02)

A notification fires when **either** of these conditions is met:

| Condition | Threshold |
|-----------|-----------|
| New HIGH or CRITICAL findings since the last scan | ≥ 1 new HIGH/CRITICAL |
| Readiness score regression | Score drops by more than `abs(trigger_score_floor)` points (default floor `-5`) |

Notifications are **never** sent on:
- The very first scan (no previous baseline to compare against)
- MEDIUM-only changes with score delta within the floor

The notifier compares the two most recent scan runs. Rows are grouped by scan run, and each run is
represented by its earliest endpoint timestamp; older rows that carry no scan run id are grouped by
millisecond. This is the same grouping the dashboard's Trends page uses. A sensor push that lands between
two scheduled scans counts as its own session, so it can become the "previous" session for the next drift
comparison, exactly as it does on the Trends page.

### Notification config block

Add a `notifications:` block at the top level of your QUIRK YAML config:

```yaml
notifications:
  trigger_score_floor: -5       # notify when score drops more than 5 points (default -5)
  notify_on_hardware_lifecycle: false   # hardware lifecycle alerts (HWLC-14, default false)

  # Optional: Slack incoming-webhook delivery (NOTIFY-03)
  slack:
    slack_webhook_env: QUIRK_SLACK_WEBHOOK      # env var NAME holding the webhook URL
    dashboard_base_url: https://quirk.internal  # optional dashboard link in drift Slack/email messages (not lifecycle alerts)

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
    use_ssl: false              # true = SMTP_SSL (set smtp_port to 465 yourself); false = STARTTLS
    timeout_seconds: 10

  # Optional: Generic outbound webhook (NOTIFY-05)
  webhook:
    url_env: QUIRK_WEBHOOK_URL          # env var NAME holding the target URL
    hmac_key_env: QUIRK_WEBHOOK_HMAC_KEY  # env var NAME for HMAC-SHA256 signing key (optional)
    timeout_seconds: 10
```

### `notify_on_hardware_lifecycle` (Phase 161 — HWLC-14)

| Key | Type | Default | Scope |
|---|---|---|---|
| `notify_on_hardware_lifecycle` | boolean | `false` | Top-level key of the `notifications:` block |

Opts the deployment in to hardware lifecycle alerts. When a scan reconciles a
qualifying hardware drift event — a **worsening** remediation-tier crossing, or
any EOL/EOS state change — QUIRK delivers a notification describing it.

Three things to know before enabling it:

- **It is a global, deployment-level switch**, not a per-device or
  per-consultant preference. There is no per-host or per-vendor opt-in; the
  whole scanned estate participates or none of it does.
- **It fans out to email and webhook only.** Slack is deliberately not a
  destination for lifecycle alerts.
- **It requires no additional configuration.** Delivery reuses the existing
  `email:` and `webhook:` blocks and the same environment-variable credential
  model documented below. If neither is configured, enabling this key changes
  nothing.

Leaving the key absent is identical to setting it to `false`.

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

### Operational environment variables

These are not secrets — they change runtime behaviour and have no config-file equivalent.

| Env var name | Default | Purpose |
|---|---|---|
| `QUIRK_OUTPUT_DIR` | `output` | Base directory the **scheduler** writes run output to when it runs without `--scan-config` (`quirk/cli/scheduler_cmd.py`). With `quirk scheduler run --scan-config <config.yaml>` the directory is that config's `output.directory` instead and this variable is ignored. |
| `QUIRK_SERVE_HOST` | unset | Set by `quirk serve` to the `--host` it binds; any value you export is overwritten. `quirk/util/url_allowlist.py` uses it with `QUIRK_SERVE_PORT` to refuse scans and URL fetches aimed at the dashboard's own address and port. |
| `QUIRK_SERVE_PORT` | unset | Set by `quirk serve` to the `--port` it binds (exported values are overwritten); companion to `QUIRK_SERVE_HOST`, and the port the PDF export route uses to reach the dashboard. |

Two further variables — `QUIRK_SENSOR_IP_ALLOWLIST` and `QUIRK_HSTS` — are **security** controls and
are documented in [Admin Guide §3.5](admin-guide.md#35-hardening-environment-variables).

### Security controls

| Control | Description |
|---------|-------------|
| **SSRF protection** | Every channel validates the destination URL/host via `validate_external_url()` before connecting — loopback and RFC1918 addresses are blocked, and a destination on the cloud-metadata address `169.254.169.254` is refused (ISEC-01). There is no `allow_internal` option for notification channels, so an SMTP relay or webhook on a private address is refused. |
| **Secret scrubbing** | Any exception raised during delivery is passed through `safe_str()` before being written to the `integration_deliveries` audit log. When the message matches a credential pattern (Slack `xox*` tokens, `hooks.slack.com` webhook URLs, `smtp://user:pass@` strings, `Authorization` headers and similar), the whole message is replaced by the exception class name (ISEC-02). Other text is kept as is. |
| **Failure isolation** | A delivery failure on one channel never blocks other channels or corrupts the scan record. The scheduler `_dispatch_schedule` wraps the entire notification call in `try/except` (NOTIFY-07). |
| **Optional Slack dep** | `slack_sdk` is an optional dependency. Missing `slack_sdk` logs a WARNING instead of raising `ImportError`. Install with `pip install quirk-scanner[notify]` (ISEC-04). |
| **Outbound whitelist** | The drift-alert webhook payload contains only aggregate fields (scores, counts, session timestamps). Hardware lifecycle alerts (email and webhook) do name the affected host, port and event; Slack messages may name hosts; SIEM events carry host and port (`dhost`, `dpt`); Jira and ServiceNow tickets carry `host:port` (ISEC-03). |

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
| `error_summary` | `safe_str(exc)` on failure — credential-shaped messages are reduced to the exception class name |

A Slack delivery skipped because `slack_sdk` is not installed or the webhook env var is unset
still writes a row with `status="ok"`. Hardware lifecycle alerts write `scan_id` as
`host:port:event_type:event_id` instead of a timestamp.

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
> are not supported.

### Prerequisites

**Set `QUIRK_CONFIG_PATH`** to the path of your QUIRK YAML config file before running the
scheduler. The scheduler's `--config` argument points to the SQLite database; the SIEM system
reads its YAML config from `QUIRK_CONFIG_PATH`.

```bash
export QUIRK_CONFIG_PATH=/etc/quirk/config.yaml
export QUIRK_DB_PATH=/var/lib/quirk/quirk.db
quirk scheduler run --config "$QUIRK_DB_PATH"
```

### `siem:` config block

Add a `siem:` block at the top level of your QUIRK YAML config:

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `host` | string | *(required)* | Hostname or IP of your syslog/CEF collector. An empty or missing host loads as an empty string and every send then fails with `ValueError: host must be a non-empty string` |
| `port` | int | `514` | UDP or TCP port of the collector |
| `protocol` | string | `"udp"` | Transport: `"udp"` or `"tcp"` (lower-cased at load; any other value makes every send fail) |
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
# Export the most recent findings-*.json in ./output (the default --output-dir)
quirk export --siem

# Specify an explicit findings file
quirk export --siem --input quirk-output/findings-2026-05-25-120000.json

# Specify the output directory to search for the latest findings file
quirk export --siem --output-dir /var/lib/quirk/output
```

**Prerequisites:**
- `QUIRK_CONFIG_PATH` must be set and point to a YAML config with a `siem:` block.
- `QUIRK_DB_PATH` must point to an initialised QUIRK SQLite database (used to write the audit row). When it is unset the command uses `./quirk.db`; if that file is not an initialised QUIRK database the events are still sent, but the audit write fails and the command exits `2`. A default scan's database is `quirk-output/quirk.db`.
- A default scan writes `findings-*.json` to `quirk-output/`, while `quirk export` searches `./output` unless you pass `--output-dir quirk-output` or `--input`.

Exit codes: `0` = all events delivered; `1` = `--siem` was not given (the help is printed); `2` = no findings file, an unreadable or non-list findings file, no `siem:` config, no event delivered, or an export failure; `3` = some but not all events delivered.

### CEF field mapping

Each finding produces one `CEF:0` event. QUIRK maps finding fields as follows:

| CEF field | Finding field | Notes |
|-----------|--------------|-------|
| Header severity | `severity` | `CRITICAL=10`, `HIGH=8`, `MEDIUM=5`, `LOW=3`; unknown defaults to 3 |
| `name` (header) | `title` | Pipe characters escaped as `\|`; backslash as `\\`; newlines removed |
| `signature` (header) | `category` → `id` → slugified title | Falls back when `category`/`id` absent |
| `dhost` | `host` | Scanned host |
| `dpt` | `port` | Scanned port (omitted when the port is missing or not 1-65535) |
| `cs1` | `category` | Finding category label |
| `cs2` | `description` | Truncated at 256 characters |
| `msg` | `recommendation` (falls back to `description` when empty) | Truncated at 256 characters |

**Payload safety:** The CEF payload contains only the fields listed above. Certificate PEM data,
certificate SANs, private key material, PKI topology details, and compliance control mappings are
**never** included in the CEF event. All extension field values are escaped: backslash becomes
`\\`, equals becomes `\=`, newlines become the literal two-character sequence `\n`, and spaces become `\s`.

### Semantics

- **One event per finding:** Each finding in the findings JSON produces one CEF event. A scan
  with 30 findings produces 30 events.
- **After-scan export:** When `export_after_scan: true`, the SIEM export hook fires automatically
  after each scheduled scan completes. The hook is isolated — a SIEM delivery failure never
  aborts the scan, corrupts the scan record, or blocks other integrations (NOTIFY-07 / SIEM-01).
- **Audit log:** Every export attempt — successful or failed — writes one row per delivered or
  failed batch to the `integration_deliveries` SQLite table with `destination="siem"`,
  `status="ok"/"failed"`, and a scrubbed `error_summary` on failure. For `quirk export --siem`,
  `scan_id` is the findings file name; for the after-scan export it is the scheduled run's
  `scan_id` (set by the notifier when it fires) or, failing that, the run's output directory name.
- **TCP framing:** Raw TCP (no octet-count prefix, no TLS). Configure your receiver for
  traditional LF-terminated or raw-bytes syslog input.

### Audit log

Query the audit log from the QUIRK database:

```bash
sqlite3 "$QUIRK_DB_PATH" \
  "SELECT attempted_at, destination, status, error_summary FROM integration_deliveries WHERE destination='siem' ORDER BY attempted_at DESC LIMIT 20;"
```

### Deferred

The following SIEM delivery paths are **not** available:
- TLS-wrapped syslog (RFC 5425)
- Splunk HTTP Event Collector (HEC)
- Elastic-native output (Elasticsearch ingest API)

---

## Jira Ticketing (first released in 5.5.0)

Phase 104 introduces per-finding Jira issue creation. QUIRK opens one Jira issue per
finding discovered during a scan, tags each issue with a SHA-256 fingerprint label for
dedup, and adds a rediscovery comment on re-runs instead of creating duplicate issues.
Ticketing is **off by default** — opt in by adding a `ticketing:` block to your QUIRK
YAML config.

> **Note:** ServiceNow ticketing (TICKET-02) is documented below and reuses the same
> abstraction. The `ticketing.jira` block documented here is unaffected by it.

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
quirk ticket create --input quirk-output/findings-2026-05-25-120000.json
```

### `ticketing.jira` config block

Add a `ticketing:` block at the top level of your QUIRK YAML config:

| Key | Type | Default | Required | Description |
|-----|------|---------|----------|-------------|
| `jira_url` | string | *(required)* | Yes | Base URL of your Jira instance (e.g. `https://acme.atlassian.net`) |
| `jira_user_env` | string | *(required)* | Yes | **Name** of the env var holding your Jira username or email — not the value itself |
| `jira_token_env` | string | *(required)* | Yes | **Name** of the env var holding your Jira API token or PAT — not the value itself |
| `project_key` | string | *(required)* | Yes | Jira project key (e.g. `SEC`); must be uppercase letters and digits starting with a letter, 2-100 characters (`^[A-Z][A-Z0-9]{1,99}$`) or the block is treated as not configured |
| `issue_type` | string | `"Bug"` | No | Jira issue type to create (e.g. `"Bug"`, `"Task"`, `"Security Finding"`) |
| `auth_mode` | string | `"cloud"` | No | Authentication mode: `"cloud"` or `"server"` (case-insensitive); any other value makes the block count as not configured |
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
is made. Loopback addresses (`127.x.x.x`) and RFC1918 ranges (`10.x`, `172.16–31.x`,
`192.168.x`) are blocked by default, and a `jira_url` on the cloud-metadata address
`169.254.169.254` is refused.

For self-hosted Jira deployed on an internal network, set `allow_internal: true`. This
allows RFC1918 `jira_url` values; a `jira_url` on `169.254.169.254` is still refused.

### CLI usage: `quirk ticket create`

Create Jira issues from a completed scan's findings file:

```bash
# Create issues from the most recent findings-*.json in ./output (the default --output-dir)
quirk ticket create

# Specify an explicit findings file
quirk ticket create --input quirk-output/findings-2026-05-25-120000.json

# Specify the output directory to search for the latest findings file
quirk ticket create --output-dir /var/lib/quirk/output
```

**Prerequisites:**
- `pip install "quirk-scanner[tickets]"` (or `[all]`)
- `QUIRK_CONFIG_PATH` set and pointing to a YAML config with a valid `ticketing.jira` block
- `QUIRK_DB_PATH` set to the QUIRK SQLite database (used to write audit rows)
- `QUIRK_JIRA_USER` and `QUIRK_JIRA_TOKEN` set in the environment

Exit codes: `0` = the run finished; `2` = an error before dispatch (missing `[tickets]` extra,
no findings file or an unreadable one, no `ticketing` config, the `ticketing.jira` block missing or
invalid, backend start-up failure such as an SSRF block), or audit rows that could not be saved
after dispatch, in which case the issues were already created.
Exit `1` is not used on purpose, but a Jira server that cannot be reached when the run starts ends it
with a traceback and exit 1. A per-finding delivery failure is recorded in the audit log
(`status="failed"`) and does **not** change the exit code, so check the audit log (below) rather
than the exit code to see whether every ticket was created.

### Dedup and rediscovery behavior

QUIRK computes a SHA-256 fingerprint for each finding using the formula
`SHA256(host:port::title)`, where the title is first passed through a small normalisation table so
that titles differing only in an embedded day count or package version (for example "Certificate
expiring in N days") share one fingerprint. On every `quirk ticket create` run it asks Jira whether the fingerprint is
already present:

- **New finding** (no Jira issue in the project carries the fingerprint as a label): one Jira
  issue is created with the fingerprint as its label, and an audit row is written.
- **Rediscovery** (a Jira issue in the project already carries that label, found by JQL): a
  comment is added to the existing Jira issue noting the rediscovery. No duplicate issue is created.

Re-running `quirk ticket create` against the same findings file adds rediscovery comments instead
of new issues, provided Jira's search already returns the issues the earlier run labelled.

### Audit log

Every ticket dispatch attempt — successful or failed — writes one row to the
`integration_deliveries` SQLite table:

| Column | Description |
|--------|-------------|
| `scan_id` | Findings file name without `.json` (truncated to 64 characters) |
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

## ServiceNow Ticketing (first released in 5.5.0)

Phase 105 adds ServiceNow incident creation as a second ticketing backend, reusing the
same `TicketingChannel` abstraction as Jira. QUIRK opens one ServiceNow incident per
finding, stores a SHA-256 fingerprint in the `correlation_id` field for dedup, and
appends a `work_notes` journal entry on re-runs instead of creating duplicate incidents.
Ticketing is **off by default** — opt in by adding a `ticketing.servicenow` block to
your QUIRK YAML config.

> **Note:** Both `ticketing.jira` and `ticketing.servicenow` blocks can coexist in the
> same config file; the `--backend` flag selects which backend is used at runtime.

### Prerequisites

Install the `[tickets]` extras group before using `quirk ticket create --backend servicenow`:

```bash
pip install "quirk-scanner[tickets]"
```

The `[tickets]` group is included in `[all]`. The ServiceNow backend uses only stdlib
`urllib` — no additional packages beyond `[tickets]` are required. Running
`quirk ticket create` without `[tickets]` installed prints a missing-extra advisory and
exits with code 2 — no ImportError traceback is raised.

**Set `QUIRK_CONFIG_PATH`** to your QUIRK YAML config before running the ticket command:

```bash
export QUIRK_CONFIG_PATH=/etc/quirk/config.yaml
export QUIRK_DB_PATH=/var/lib/quirk/quirk.db
quirk ticket create --backend servicenow --input quirk-output/findings-2026-05-25-120000.json
```

### `ticketing.servicenow` config block

Add a `servicenow:` sub-block under the `ticketing:` section of your QUIRK YAML config:

| Key | Type | Default | Required | Description |
|-----|------|---------|----------|-------------|
| `instance_url` | string | *(required)* | Yes | Base URL of your ServiceNow instance — **must use `https://`** (http:// is rejected at parse time) |
| `user_env` | string | *(required)* | Yes | **Name** of the env var holding your ServiceNow username — not the value itself |
| `password_env` | string | *(required)* | Yes | **Name** of the env var holding your ServiceNow password — not the value itself |
| `table` | string | `"incident"` | No | ServiceNow table to create records in (default: `incident`); lowercase letters, digits and underscores, starting with a letter or underscore, at most 80 characters (`^[a-z_][a-z0-9_]{0,79}$`) or the block counts as not configured |
| `allow_internal` | bool | `false` | No | Set `true` for self-hosted ServiceNow on RFC1918 networks (see SSRF note below) |

```yaml
ticketing:
  servicenow:
    instance_url: https://acme.service-now.com  # MUST be https://; http:// is rejected
    user_env: QUIRK_SNOW_USER                   # env var NAME holding your ServiceNow username
    password_env: QUIRK_SNOW_PASSWORD           # env var NAME holding your ServiceNow password
    table: incident                             # optional; default is incident
    allow_internal: false                       # set true for self-hosted on RFC1918
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
| `user_env: QUIRK_SNOW_USER` | `QUIRK_SNOW_USER` | `quirk_scanner` |
| `password_env: QUIRK_SNOW_PASSWORD` | `QUIRK_SNOW_PASSWORD` | `S3cr3tP@ss!` |

Set these before running `quirk ticket create`:

```bash
export QUIRK_SNOW_USER=quirk_scanner
export QUIRK_SNOW_PASSWORD=S3cr3tP@ss!
quirk ticket create --backend servicenow
```

### SSRF protection and https-only enforcement

`instance_url` is validated by two guards before any connection is made:

1. **https-only parse-time check** — `_parse_servicenow_cfg` returns `None` (the
   `ticketing.servicenow` block is treated as not configured) if `instance_url` does not start
   with `https://`. This check fires before any DNS lookup or TCP connection.
2. **`validate_external_url()` runtime guard** — Loopback addresses (`127.x.x.x`) and RFC1918
   ranges (`10.x`, `172.16–31.x`, `192.168.x`) are blocked by default, and an `instance_url` on
   the cloud-metadata address `169.254.169.254` is refused.

For self-hosted ServiceNow deployed on an internal network, set `allow_internal: true`.
This allows RFC1918 `instance_url` values; an `instance_url` on `169.254.169.254` is still refused.

### CLI usage: `quirk ticket create --backend servicenow`

Create ServiceNow incidents from a completed scan's findings file:

```bash
# Create incidents using the ServiceNow backend (default backend is jira)
quirk ticket create --backend servicenow

# Specify an explicit findings file
quirk ticket create --backend servicenow --input quirk-output/findings-2026-05-25-120000.json

# Specify the output directory to search for the latest findings file
quirk ticket create --backend servicenow --output-dir /var/lib/quirk/output
```

**Prerequisites:**
- `pip install "quirk-scanner[tickets]"` (or `[all]`)
- `QUIRK_CONFIG_PATH` set and pointing to a YAML config with a valid `ticketing.servicenow` block
- `QUIRK_DB_PATH` set to the QUIRK SQLite database (used to write audit rows)
- `QUIRK_SNOW_USER` and `QUIRK_SNOW_PASSWORD` set in the environment

Exit codes: `0` = the run finished; `2` = an error before dispatch (missing `[tickets]` extra,
no findings file or an unreadable one, no `ticketing` config, the `ticketing.servicenow` block
missing or invalid, backend start-up failure such as an SSRF block), or audit rows that could not
be saved after dispatch, in which case the incidents were already created. Exit `1` is not used.
A per-finding delivery failure is recorded in the audit log
(`status="failed"`) and does **not** change the exit code.

### Dedup and rediscovery behavior

QUIRK computes a SHA-256 fingerprint for each finding using the formula
`SHA256(host:port::title)` (with the same title normalisation as the Jira backend) — identical to
the Jira backend, ensuring cross-backend identity consistency. On every
`quirk ticket create --backend servicenow` run it asks ServiceNow whether an incident with that
`correlation_id` already exists:

- **New finding** (no record in the table has that `correlation_id`): one ServiceNow incident
  is created, with the SHA-256 fingerprint stored in the `correlation_id` field. The incident's
  `sys_id` (not the INC-number) is used for subsequent PATCH operations.
- **Rediscovery** (a record with that `correlation_id` exists): QUIRK issues a
  `PATCH` to the existing incident's `work_notes` field, appending a fixed journal entry
  ("Rediscovery: QUIRK re-detected this finding on a subsequent scan." plus the fingerprint).
  No duplicate incident is created.

Re-running `quirk ticket create --backend servicenow` against the same findings file is
safe — it produces zero duplicate incidents on all subsequent runs.

### Audit log

Every ticket dispatch attempt — successful or failed — writes one row to the
`integration_deliveries` SQLite table:

| Column | Description |
|--------|-------------|
| `scan_id` | Findings file name without `.json` (truncated to 64 characters) |
| `finding_hash` | SHA-256 fingerprint of the finding (`host:port::title`) |
| `destination` | `"servicenow"` |
| `status` | `"ok"` or `"failed"` |
| `attempted_at` | UTC timestamp of the dispatch attempt |
| `error_summary` | `safe_str(exc)` on failure — Authorization headers always scrubbed |

Query the audit log:

```bash
sqlite3 "$QUIRK_DB_PATH" \
  "SELECT finding_hash, status, attempted_at, error_summary FROM integration_deliveries WHERE destination='servicenow' ORDER BY attempted_at DESC LIMIT 20;"
```

---

## Compliance Frameworks

QUIRK's `COMPLIANCE_MAP` (in `quirk/compliance/__init__.py`) maps 24 of the finding titles QUIRK
emits to one or more of the following frameworks; the other titles carry no compliance mapping.
Since Phase 52, all
frameworks are kept fresh by the `STALENESS_THRESHOLD_DAYS` gate (a CI test) and can be
checked at any time with `quirk doctor` or `quirk compliance status`.

| Framework | Version | Builder helper |
|-----------|---------|----------------|
| PCI-DSS | 4.0.1 | `_pci(control)` |
| HIPAA | 2024-rev (45 CFR §164.312) | `_hipaa(control)` |
| FIPS 140-3 | NIST FIPS 140-3 | `_fips(control)` |
| SOC2 | 2017-rev (Trust Services Criteria) | `_soc2(control)` — Phase 52 |
| ISO 27001 | ISO 27001:2022 (8.x clause numbering) | `_iso(control)` — Phase 52 |

**ISO 27001:2022 control assignments** (Phase 52). Only two clauses are assigned today:
- `8.24` — Use of cryptography (certificate and key findings: expired, expiring, self-signed or untrusted certificates and undersized or quantum-vulnerable RSA/ECDSA keys)
- `8.26` — Application security requirements (TLS/protocol transport findings: plaintext HTTP, legacy TLS versions and ciphers, STARTTLS downgrade and similar)

**SOC2 CC6.x control assignments** (Phase 52):
- `CC6.6` — Logical access controls (certificate and key findings, legacy TLS versions, plaintext Redis, container-image crypto libraries)
- `CC6.7` — Transmission encryption (cipher, protocol and transport findings)

CBOM algorithm components carry a `quirk:fips140-3-status` property
(`approved` or `non-approved`) derived from the NIST quantum security level.
The CBOM never emits a `certified` value; CMVP module coverage is reported
separately in a `quirk:cmvp-coverage` property when a validated module is known
for the algorithm.

## Firmware CVE Catalog Staleness Cadence (Phase 142)

QUIRK's curated firmware-CVE catalog (`quirk/scanner/hw_cve.py::CVE_TABLE`, backing the
advisory-only CVE correlation described in `docs/operators-guide.md` §9.5) is gated by its
own `STALENESS_THRESHOLD_DAYS = 30` — deliberately shorter than QRAMM's 90-day cadence
(`quirk/qramm/model_meta.py`) and the compliance-mapping module's 365-day cadence
(`quirk/compliance/__init__.py`), because CVE data churns far faster than governance
frameworks or CSNP model revisions do.

**CI enforcement.** `.github/workflows/python-staleness.yml`'s single "Run staleness gates"
step includes `tests/test_cve_staleness.py` alongside the QRAMM, compliance and other catalog
staleness tests — it is one more test file in the existing pytest invocation, not a separate job. The workflow runs on every PR, every push to `main`,
and a weekly Monday 09:00 UTC cron, so a stale CVE catalog turns this workflow red. The workflow is
not a release gate: `release.yml` runs no tests.

**Bump procedure** (the same as for every other date-gated catalog; never bump `last_verified`
without actually re-verifying the entries against their source):

1. Re-verify each `CVE_TABLE` entry against its NVD source (`source_url` on the entry).
2. Bump `last_verified` in `CVE_TABLE_META` to today's ISO date.
3. Commit with message `chore: re-verify CVE catalog (YYYY-MM-DD)`.
4. Confirm `quirk cve status` prints `FRESH` and `pytest tests/test_cve_staleness.py -q`
   passes.

Operators can check current freshness at any time with `quirk cve status` (§9.5 of
`docs/operators-guide.md`) — no network access required, since the catalog is entirely local.

## OT/ICS Recurring-Scan Cadence Floor (Phase 156)

First released in 5.15.0, Phase 156 adds a safety floor on top of the `enable_modbus`/`enable_bacnet` opt-in flags
(Connectors Block, above): a **recurring** (scheduled) run may only probe Modbus/BACnet when
both `connectors.enable_recurring_otics: true` is set AND the schedule's own cron expression
fires no more often than once every 168 hours (7 days).

**This is a floor, not a config key.** The 168-hour value is a named constant,
`OTICS_MIN_INTERVAL_HOURS`, in `quirk/otics_cadence.py` — there is deliberately no
`connectors.*` key, no environment variable, and no CLI flag that can lower it. Raising it
would require an intentional code change, not an operator override.

**How the floor is evaluated.** The floor is checked against the schedule's cron expression's
*minimum* firing gap, not its average. `min_gap_hours()` samples 10 consecutive firings (9
gaps) and takes the smallest one. This matters for irregular expressions: `0 0 * * 1,2` (every
Monday and Tuesday at midnight) has an average gap of roughly 84 hours across a week, but its
worst-case gap — Monday to Tuesday — is only 24 hours. QUIRK judges this schedule
on the 24-hour worst case, not the 84-hour average, because the worst case is what actually
determines how often a fragile OT/ICS device gets probed.

**Sub-floor schedules are not rejected — they succeed with an advisory.** Creating a schedule
with a cron interval below the floor does not fail. `POST /api/schedules` returns `201` and
`quirk schedule add` exits `0`; both surface a non-blocking advisory (see
`docs/operators-guide.md` §12) instead of a `422` rejection. This is deliberate: the scheduler
applies one shared `--scan-config` file to every schedule it dispatches, so at schedule-creation
time it has no way to know whether that shared config will ever have `enable_modbus`/
`enable_bacnet` turned on. Rejecting the schedule outright would be wrong for an operator who
has no intention of ever enabling OT/ICS scanning on it.

**Enforcement happens at dispatch time, not creation time.** When the scheduler actually
dispatches a run (`quirk scheduler run`), it strips `enable_modbus` and `enable_bacnet` from
the generated per-run config whenever the recurring-OT/ICS opt-in is off or the schedule's own
cron fires faster than the floor — while the rest of the scan proceeds normally. This is the
single, unconditional backstop: it catches every sub-floor schedule regardless of whether it was
created before this feature existed or edited directly in the database, not just schedules
created through the two write-time advisory surfaces. See `docs/operators-guide.md` §12 for
what an operator sees when this happens and where to find the suppression log line.
