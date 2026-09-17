# Connector Field Reference

**Last Updated:** 2026-09-17

Every connector that needs more than its `enable_*` toggle, what to put in each field, and the
chaos-lab value that makes it produce findings.

This document is task-oriented and deliberately duplicates nothing:

- [`docs/configuration.md`](configuration.md) is the **YAML reference** — all 39 connector detail
  fields with types and defaults.
- [`docs/operators-guide.md`](operators-guide.md) §3.1.3 describes **how the Connectors panel
  behaves** in the dashboard.
- This file answers the question neither of those does: *what do I actually type to make this
  connector return findings, and what value does the chaos lab expect?*

It exists because the operators guide's scanner matrix carried `(no dedicated doc yet)` against
the Database and Vault rows, and because the knowledge needed to run a connector was split across
three places — the YAML reference, the chaos-lab profile tables, and the lab's `docker-compose.yml`
for credentials.

---

## The rule this document exists for

**Enabling a connector is not enough.** Sixteen of the twenty-five connectors take *detail
fields* — targets, endpoints, usernames — that render inline beneath the toggle in the dashboard's
Connectors panel once that connector is enabled.

These connectors **do not scan the main target list**. SAML wants an IdP metadata URL. PostgreSQL
wants its own host plus credentials. S3 wants an endpoint URL. Leave them blank and:

- the connector probes nothing,
- the scan still completes successfully,
- and the corresponding dashboard tab renders **empty, with no error explaining why**.

The multihost scan config states the consequence directly, in its own words:

> `pg_targets` + scanner credentials are likewise required — `enable_db: true` alone probes
> nothing, which is why the host returned INFO only and POSTGRESQL never reached
> `protocol_counts`.

and, for object storage:

> `aws_endpoint_url` is REQUIRED … Without it the connector never talks to MinIO, no endpoint is
> classified `S3`, and `_dar_assessed()` … returns False, so **the whole Data at Rest domain is
> dropped from the rollup as UNASSESSED** rather than scoring badly.

### A dashboard scan does not read any YAML config

`build_job_config_dict` (`quirk/dashboard/api/routes/jobs.py`) composes the job's config **from
scratch** out of the submitted form. It never reads `multihost-scan-config.yaml`,
`scan-configs/config-lab-*.yaml`, or the repo-root `config.yaml`. Those files apply to CLI runs
only (`quirk --config <file>`).

Anything a YAML config sets must be re-entered in the form for a dashboard-initiated scan. The one
exception is `security.allow_internal_targets` — see [Failure modes](#failure-modes-that-are-silent).

---

## Identity tab

### SAML — `enable_saml`

| Field | | Multihost lab |
|---|---|---|
| SAML Targets | **required** | `http://10.80.0.41:8080/simplesaml/saml2/idp/metadata.php` |

The value is a full **metadata URL**, not a host or IP. `10.80.0.41` alone yields nothing. In the
single-host lab, SimpleSAMLphp serves on port **8080**.

### Kerberos — `enable_kerberos`

| Field | | Value |
|---|---|---|
| Kerberos Targets | **required** | `10.80.0.42` (multihost, realm `QUIRK.LAB`) |

Requires `quirk-scanner[identity]` for impacket. Note `[all]` **deliberately excludes**
`[identity]`, so an `[all]`-only install — including the chaos lab's own `mh-prober` image —
cannot scan Kerberos. Install with `pip install -e ".[all,identity]"` as a single resolution
rather than adding `[identity]` incrementally; see the `sslyze`/`cryptography` note in
[configuration.md](configuration.md).

On macOS the standalone `kerberos` profile is skipped by `lab.sh`, because macOS runs its own
KDC on `:88` and that profile publishes the port. The multihost `mh-kdc` publishes no ports and
is unaffected.

### DNSSEC — `enable_dnssec`

| Field | | Value |
|---|---|---|
| DNSSEC Targets | **required** | zone name |
| DNSSEC Resolver | optional | resolver IP |

**Disabled in the multihost profile** — no bind9 resolver on that subnet.

### S/MIME — `enable_smime` · AD CS — `enable_adcs`

| Field | | Value |
|---|---|---|
| S/MIME Targets | **required** | LDAP host |
| S/MIME Search Base | **required** | e.g. `dc=example,dc=com` |
| S/MIME Timeout | optional | seconds |
| AD CS Targets | **required** | LDAP host |
| AD CS Search Base | **required** | e.g. `dc=example,dc=com` |
| AD CS Username | **required** | bind DN (password is a credential — see below) |
| AD CS Timeout | optional | seconds |

Both require `quirk-scanner[adcs]` for `ldap3`.

---

## Data at Rest tab

### Database — `enable_db`

| Field | | Multihost lab | Single-host `database` profile |
|---|---|---|---|
| PostgreSQL Targets | **required** | `10.80.0.30` | `localhost:25432` |
| PostgreSQL Username | **required** | `finance` | `quirk_scanner` |
| MySQL Targets | **required for MySQL** | `10.80.0.111` | `localhost:23306` |
| MySQL Username | **required for MySQL** | `root` | `quirk_scanner` |

Passwords are credentials, not config fields — see [Credentials](#credentials-travel-separately).

`enable_db: true` with only `pg_targets` set scans Postgres and silently ignores MySQL. Each
engine has its own target list; neither derives from the main scan targets.

### Object storage — `enable_s3` / `enable_aws`

| Field | | Multihost lab | Single-host `storage` profile |
|---|---|---|---|
| AWS S3/MinIO Endpoint URL | **required** | `http://10.80.0.50:9000` | `http://localhost:29000` |
| AWS Region | **required** | `us-east-1` | `us-east-1` |
| AWS Profile | optional | — | — |

Credentials come from the **environment**, not the form. Export before launching the dashboard or
running the CLI:

```bash
export AWS_ACCESS_KEY_ID=minioadmin
export AWS_SECRET_ACCESS_KEY=minioadmin
```

Omitting the endpoint URL drops the **entire Data at Rest domain** from the readiness rollup as
UNASSESSED — the score is then flatteringly high for the wrong reason.

### HashiCorp Vault — `enable_vault`

| Field | | Single-host `vault` profile |
|---|---|---|
| Vault Address | **required** | `http://localhost:28200` (single-host) · `http://10.80.0.61:8200` (multihost) |
| Vault Transit Mount | optional | `transit` |
| Verify Vault TLS certificate | optional | off for the dev-mode lab server |

The token is a credential; the lab's dev root token is `root`. Requires `quirk-scanner[cloud]` for
`hvac`. Expected findings: exportable transit key (MEDIUM), RSA<4096 PKI root (HIGH), dev-mode
token auth (HIGH), userpass auth (MEDIUM).

### Azure — `enable_azure` / `enable_blob`

| Field | | Value |
|---|---|---|
| Azure Subscription ID | **required** | subscription GUID |
| Azure Key Vault URLs | **required** | e.g. `https://vault.example.com/v1/kv` |

**No chaos-lab equivalent.** Azure authenticates ambiently through the host's Azure CLI session.
Live-subscription only.

### Kubernetes — `enable_k8s` · GCP — `enable_gcp`

| Field | | Value |
|---|---|---|
| K8s Provider | **required** | `eks` \| `gke` \| `aks` |
| K8s Cluster Name | **required** | cluster name |
| K8s Namespace | optional | defaults to all |
| K8s Context | optional | kubeconfig context |
| GCP Project ID | **required** | project id |

**Live-cluster only** — no chaos-lab profile exists for either.

---

## Motion tab

### Message broker — `enable_broker`

| Field | | Multihost lab | Single-host `broker190` profile |
|---|---|---|---|
| Additional Broker Targets | **required** | `10.80.0.31` | `localhost:29092`, `localhost:29093`, `localhost:25671`, `localhost:25672`, `localhost:26379`, `localhost:26380`, `localhost:29099` |
| Broker Azure Namespaces | optional | — | live Azure Service Bus only |
| Broker SQS Regions | optional | — | live AWS only |

A bare host is valid — the scanner's per-family default ports still apply, and an explicit port is
**added** to that list rather than replacing it.

Requires all three of `sslyze`, `kafka-python` and `redis` to be importable. If any is missing the
dashboard refuses the submission outright rather than degrading.

### Email — `enable_email`

No detail fields. The email scanner derives its hosts from the TLS-scanned target list and probes
its own fixed 7-port table (25, 465, 587, 143, 993, 110, 995). Requires `sslyze`.

**Because it derives hosts from the target list, the mail hosts must appear in `targets`** — in
the multihost profile that is `10.80.0.120` (Postfix: SMTP/SMTPS/submission) and `10.80.0.121`
(Dovecot: IMAP/POP3 ± TLS).

---

## Findings tab

### JWT / API endpoints — `enable_jwt`

| Field | | Single-host `jwt` profile |
|---|---|---|
| JWT Targets | **required** | `http://localhost:20001` … `20004` (single-host) · `http://10.80.0.90:8000` … `.93:8000` (multihost) |

**Base URLs, not token URLs.** The connector probes JWKS paths
(`/.well-known/jwks.json`, `/oauth/jwks`, `/.well-known/openid-configuration`) by
concatenating them onto each target, so a target ending in `/token` makes it request
`/token/.well-known/jwks.json` and find nothing.

Also requires `security.allow_internal_targets: true` for any private or loopback IdP —
the JWKS probe runs the SSRF guard on every candidate URL.

### Container images — `enable_container` · Source code — `enable_source`

| Field | | Value |
|---|---|---|
| Container Targets | **required** | image references |
| Source Targets | **required** | local paths |

Both gate on an external CLI binary — `syft` and `semgrep` respectively — not a Python package. The
dashboard reports them unavailable when the binary is absent from `PATH`.

---

## Credentials travel separately

Five connector credentials are carried on a dedicated request-scoped channel, never in the job
config:

| Credential | Used by | Chaos-lab value |
|---|---|---|
| `pg_scanner_password` | `enable_db` | `finance` (multihost) · `quirk_scanner` (`database` profile) |
| `mysql_scanner_password` | `enable_db` | `hr` (multihost, with user `root`) · `quirk_scanner` (`database` profile) |
| `vault_token` | `enable_vault` | `root` |
| `adcs_password` | `enable_adcs` | — |
| `snmp_community` | `enable_snmp` | `public` |

These are never assigned to a `ScanJob` column, never written to the job's `config.yaml`, and never
passed to a logger. They exist only to be injected into the scan subprocess's environment.

**They therefore do not appear in the Effective config panel.** That is deliberate, not a bug.

---

## Toggle-only connectors

Seven of the twenty-five take no detail fields at all — they derive targets from the main list,
gate on an external binary, or are pure behaviour switches:

`enable_email` · `enable_nmap` · `enable_modbus` · `enable_bacnet` · `enable_codesign` ·
`enable_authenticated_mode` · `enable_recurring_otics`

---

## Failure modes that are silent

### `allow_internal_targets` is server policy, not a form field

SAML, broker and JWKS fetches to RFC1918, loopback and link-local addresses are gated on
`security.allow_internal_targets`. The dashboard form **silently drops** any client-supplied value
(`ScanSubmitRequest` uses `extra="ignore"`).

The server sources it from `QUIRK_CONFIG_PATH`, falling back to `./config.yaml` **relative to the
directory `quirk serve` was launched from**, and defaults to `False` on any resolution failure.

Launching the dashboard from the wrong directory therefore fails safe — silently. Set it in the
config file next to where you launch:

```yaml
security:
  allow_internal_targets: true
```

Note this gates *connector fetches*, not TLS port scanning: a plain TLS scan of a private address
works regardless.

### Never target a whole lab subnet

For the multihost profile, use the 31 explicit `/32`s in `multihost-scan-config.yaml`. A measured
sweep of `10.80.0.0/24` returned **257 hosts and 2,572 findings** — 254 phantom addresses at 10
INFO findings each, plus the bridge gateway at `.1` reported as a CRITICAL. The real topology is
unreadable in that output.

### A missing optional dependency refuses the scan, it does not skip it

The dashboard availability gate rejects the whole submission at `POST /api/jobs` with a banner
naming the module flag (e.g. `quirk.scanner.email_scanner.SSLYZE_AVAILABLE is False`). The probe
is re-run fresh on every call, but module-level flags are evaluated at **import** time — so a
package installed after the server started still reads as missing until `quirk serve` restarts.

### Check Effective config before running

The New Scan page has a collapsed **Effective config** panel directly above the Run Scan button
showing the config the submission will actually produce. Confirm target lists and endpoint URLs
appear there before starting a long scan.

---

## Where these values come from

Field names and required/optional status are enumerated from
`src/dashboard/src/components/ConnectorsPanel.tsx`, the 37-key overlay allowlist in
`quirk/dashboard/api/schemas.py` (`_CONNECTOR_DETAIL_KEY_TYPES`), and the credential registry in
`quirk/config_redaction.py`.

Chaos-lab values are read from `quantum-chaos-enterprise-lab/docker-compose.yml`,
`quantum-chaos-enterprise-lab/multihost-scan-config.yaml`,
`quantum-chaos-enterprise-lab/scan-configs/`, and [`docs/chaos-lab.md`](chaos-lab.md).

When a connector's fields change, regenerate rather than hand-editing this list:

```bash
grep -oE '\{ key: "\w+"' src/dashboard/src/components/ConnectorsPanel.tsx | sort -u
```
