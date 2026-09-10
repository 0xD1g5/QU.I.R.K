# 194-PARITY-AUDIT: CLI config <-> dashboard-form field parity

**Audit date:** 2026-09-09
**Source files (git SHA `9af9d038bd7b4f207f3641cf31d6872c9e929a35`):**
- `quirk/config_template.yaml` (operator-facing field universe)
- `quirk/config.py` (dataclasses behind it: `AssessmentCfg`, `TimeoutsCfg`, `RetryCfg`, `ScanCfg`,
  `TargetsCfg`, `ConnectorsCfg`, `OutputCfg`, `IntelligenceCfg`, `SecurityCfg`, plus the top-level
  `AppConfig.broker_credentials` / `AppConfig.remediation_aliases` dict fields)
- `src/dashboard/src/pages/scan-new.tsx`, `src/dashboard/src/components/ConnectorsPanel.tsx`,
  `src/dashboard/src/components/AdvancedPanel.tsx` (the shipped form surface, post-194-05)
- `quirk/dashboard/api/schemas.py` (`AdvancedScanFields`, `ScanSubmitRequest`)

**Counted field-universe size: 121 operator-settable fields** across 9 dataclasses plus 2
top-level `AppConfig` dict fields. This replaces the `.planning/backlog/999.104-.../IDEA.md` /
`HORIZON.md` PM-era estimate of "~138 YAML fields" — that number was never derived by enumerating
`config.py`'s dataclass fields; the real count, enumerated field-by-field below, is 121.
`IntelligenceCfg.intelligence_version` is excluded from the 121 — it is a `field(default_factory=...)`
derived from `quirk.__version__`, never operator-set, so it is not part of the "operator-settable"
universe this audit tables.

**Reconciliation finding (config_template.yaml vs config.py):** `config_template.yaml` does NOT
show `scan.timeouts` / `scan.retry` as a written YAML block (their defaults live entirely in
`TimeoutsCfg`/`RetryCfg`'s dataclass field defaults and are undocumented in the generated template
comments) — a config-template documentation gap, not a code defect. Every `config.py` dataclass
field otherwise has a template comment or example line. No template key exists with zero backing
dataclass field, and no dataclass field is silently absent from this audit's enumeration.

## Summary counts

| Status | Count |
|---|---|
| `covered` | 35 |
| `covered-indirectly` | 6 |
| `intentional-gap` | 15 |
| `not-yet-covered` | 65 |
| **Total** | **121** |

## Field-by-field parity table

### `assessment` (AssessmentCfg) — 5 fields

| Config path | Type/values | Default | Dashboard surface | Status | Notes |
|---|---|---|---|---|---|
| `assessment.name` | str | `"My Organization"` | none | not-yet-covered | Org name is engagement-scoped, set once per install; no dashboard field. |
| `assessment.data_classification` | str | `"CONFIDENTIAL"` | `AdvancedPanel` "Data Classification" select | covered | Maps to `assessment_overlay` (194-02); D-21 4-value vocabulary (Public/Internal/Confidential/Regulated), no "Restricted". |
| `assessment.report_owner` | str | `"Security Team"` | none | not-yet-covered | Engagement metadata, not scan-behavior. |
| `assessment.timezone` | str | `"UTC"` | none | not-yet-covered | Report-rendering setting, not scan-behavior. |
| `assessment.logo_path` | str \| null | `null` | none | not-yet-covered | Local filesystem path — a browser-submitted value here would be a path-traversal surface if ever added. |

### `targets` (TargetsCfg) — 4 fields

| Config path | Type/values | Default | Dashboard surface | Status | Notes |
|---|---|---|---|---|---|
| `targets.fqdns` | list[str] | `[]` | scan-new.tsx "Targets" textarea | covered-indirectly | Free-text target string is parsed server-side into fqdns/cidrs/include_ips by type, not a dedicated fqdns field. |
| `targets.cidrs` | list[str] | `[]` | scan-new.tsx "Targets" textarea | covered-indirectly | Same parse-by-type as above. |
| `targets.include_ips` | list[str] | `["127.0.0.1"]` | scan-new.tsx "Targets" textarea | covered-indirectly | Same parse-by-type as above. |
| `targets.exclude_ips` | list[str] | `[]` | none | not-yet-covered | No "exclude" syntax in the single free-text Targets field. |

### `scan` top-level (ScanCfg) — 13 fields

| Config path | Type/values | Default | Dashboard surface | Status | Notes |
|---|---|---|---|---|---|
| `scan.concurrency` | int | 20 | none | not-yet-covered | Global scan worker concurrency. |
| `scan.ports_tls` | list[int] | 17-port `CONSULTING_TLS_PORTS` | AdvancedPanel "TLS Ports" input; also derived from Custom port-scope | covered | Phase 194-05 D-04: composes with the existing Custom-scope port input rather than duplicating it. |
| `scan.include_sni` | bool | true | AdvancedPanel switch | covered | |
| `scan.tls_enum_mode` | `off\|fast\|deep` | `"fast"` | AdvancedPanel select | covered | D-19: dashboard offers only `fast`/`deep` — `tls_scanner.py` silently coerces any other value (including `off`) to `fast`, so exposing `off` would be misleading. |
| `scan.fingerprint_concurrency` | int | 200 | none | not-yet-covered | |
| `scan.tls_concurrency` | int | 150 | none | not-yet-covered | |
| `scan.ssh_concurrency` | int | 100 | none | not-yet-covered | |
| `scan.motion_concurrency` | int | 50 | none | not-yet-covered | Shared email+broker ThreadPool `max_workers`. |
| `scan.openapi_spec_path` | str \| null | `null` | none | not-yet-covered | Local file path or scope-gated URL — same path-surface caution as `assessment.logo_path`. |
| `scan.nmap_port_scope` | `top1000\|all\|null` | `null` | scan-new.tsx Port Scope radio | covered-indirectly | Derived from the `top1000`/`all` radio choices; `common`/`custom` scopes write `ports_tls` directly instead. |
| `scan.hardware_history_retention_days` | int | 180 | none | not-yet-covered | Engagement-history retention policy, install-scoped. |
| `scan.hardware_drift_event_retention_days` | int | 365 | none | not-yet-covered | Same as above. |
| `scan.tls_designated_ports` | list[int] | `[]` | none | not-yet-covered | Operator override for the plaintext-on-TLS-port classifier (Phase 186 TRIAGE-176-02). |

### `scan.timeouts` (TimeoutsCfg) — 14 fields

| Config path | Type/values | Default | Dashboard surface | Status | Notes |
|---|---|---|---|---|---|
| `scan.timeouts.default_seconds` | int | 5 | AdvancedPanel "Default Timeout" | covered | |
| `scan.timeouts.fingerprint_seconds` | int | 4 | none | not-yet-covered | |
| `scan.timeouts.tls_seconds` | int | 6 | AdvancedPanel "TLS Timeout" | covered | |
| `scan.timeouts.ssh_seconds` | int | 6 | AdvancedPanel "SSH Timeout" | covered | |
| `scan.timeouts.jwt_seconds` | int | 10 | none | not-yet-covered | |
| `scan.timeouts.container_seconds` | int | 120 | none | not-yet-covered | |
| `scan.timeouts.source_seconds` | int | 300 | none | not-yet-covered | |
| `scan.timeouts.dnssec_seconds` | int | 10 | none | not-yet-covered | |
| `scan.timeouts.saml_seconds` | int | 10 | none | not-yet-covered | |
| `scan.timeouts.kerberos_seconds` | int | 10 | none | not-yet-covered | |
| `scan.timeouts.vault_seconds` | int | 10 | none | not-yet-covered | |
| `scan.timeouts.db_connect_seconds` | int | 5 | none | not-yet-covered | |
| `scan.timeouts.broker_seconds` | int | 10 | none | not-yet-covered | |
| `scan.timeouts.email_seconds` | int | 10 | none | not-yet-covered | |

### `scan.retry` (RetryCfg) — 3 fields

| Config path | Type/values | Default | Dashboard surface | Status | Notes |
|---|---|---|---|---|---|
| `scan.retry.retry_count` | int | 0 | AdvancedPanel "Retry Count" | covered | |
| `scan.retry.backoff_base_seconds` | float | 1.0 | none | not-yet-covered | |
| `scan.retry.backoff_max_seconds` | float | 5.0 | none | not-yet-covered | |

### `output` (OutputCfg) — 2 fields

| Config path | Type/values | Default | Dashboard surface | Status | Notes |
|---|---|---|---|---|---|
| `output.directory` | str | `"./quirk-output"` | none | intentional-gap | Server-side filesystem path; per-scan browser control here is a path-injection surface, same class as `security.*` below. Install-scoped, set once by whoever deploys the server. |
| `output.db_path` | str | `"./quirk-output/quirk.db"` | none | intentional-gap | Same reasoning; also the canonical single-DB-path convention (see CLAUDE.md "Canonical DB path") depends on this NOT being per-scan-overridable. |

### `connectors` (ConnectorsCfg) — 71 fields

**Enable flags (25):**

| Config path | Default | Dashboard surface | Status | Notes |
|---|---|---|---|---|
| `connectors.enable_aws` | false | ConnectorsPanel "Cloud" toggle | covered | Ambient-auth (D-10): no credential field rendered. |
| `connectors.enable_azure` | false | ConnectorsPanel "Cloud" toggle | covered | Ambient-auth. |
| `connectors.enable_jwt` | true | ConnectorsPanel "Source & API" toggle | covered | |
| `connectors.enable_container` | true | ConnectorsPanel "Source & API" toggle | covered | |
| `connectors.enable_source` | true | ConnectorsPanel "Source & API" toggle | covered | |
| `connectors.enable_nmap` | false | scan-new.tsx top-level "Enable nmap discovery" checkbox (NOT in ConnectorsPanel) | covered | Pre-dates this phase; forced true when Port Scope is `top1000`/`all`. |
| `connectors.enable_kerberos` | false | ConnectorsPanel "Identity" toggle | covered | |
| `connectors.enable_saml` | true | ConnectorsPanel "Identity" toggle | covered | |
| `connectors.enable_dnssec` | true | ConnectorsPanel "Identity" toggle | covered | |
| `connectors.enable_smime` | false | ConnectorsPanel "Identity" toggle | covered | |
| `connectors.enable_adcs` | false | ConnectorsPanel "Identity" toggle | covered | |
| `connectors.enable_codesign` | false | none | intentional-gap | Template: "not-a-connector — driven entirely by the `--inventory-code-signing` CLI flag; this key changes zero scan behavior on its own." Dashboard has no equivalent CLI-flag concept for scan submission. |
| `connectors.enable_gcp` | false | ConnectorsPanel "Cloud" toggle | covered | Ambient-auth. |
| `connectors.enable_db` | false | ConnectorsPanel "Database" toggle | covered | |
| `connectors.enable_s3` | false | ConnectorsPanel "Cloud" toggle | covered | Ambient-auth. |
| `connectors.enable_blob` | false | ConnectorsPanel "Cloud" toggle | covered | Ambient-auth. |
| `connectors.enable_k8s` | false | ConnectorsPanel "Cloud" toggle | covered | |
| `connectors.enable_vault` | false | ConnectorsPanel "Cloud" toggle | covered | |
| `connectors.enable_email` | true | ConnectorsPanel "Email & Broker" toggle | covered | |
| `connectors.enable_broker` | true | ConnectorsPanel "Email & Broker" toggle | covered | |
| `connectors.enable_authenticated_mode` | false | none | intentional-gap | Template: "not-a-connector — driven by the credential CLI flags; the scheduler rejects any recurring config where this is true." No dashboard equivalent of CLI credential flags exists, and D-11 scheduler rejection makes this dashboard-inappropriate regardless. |
| `connectors.enable_snmp` | false | ConnectorsPanel "OT/ICS" toggle | covered | |
| `connectors.enable_modbus` | false | ConnectorsPanel "OT/ICS" toggle | covered | |
| `connectors.enable_bacnet` | false | ConnectorsPanel "OT/ICS" toggle | covered | |
| `connectors.enable_recurring_otics` | false | none | intentional-gap | Template: "a scheduler safety gate for recurring Modbus/BACnet probing, not a scanner toggle by itself" — applies to the recurring/cron scheduler surface, not the one-off scan-submit form this audit covers. |

**Credential / endpoint / target sub-fields (46):**

| Config path | Default | Dashboard surface | Status | Notes |
|---|---|---|---|---|
| `connectors.aws_region` | `"us-east-1"` | none | not-yet-covered | |
| `connectors.aws_profile` | null | none | not-yet-covered | |
| `connectors.azure_subscription_id` | null | none | not-yet-covered | |
| `connectors.azure_keyvault_urls` | `[]` | none | not-yet-covered | |
| `connectors.jwt_targets` | `[]` | none | not-yet-covered | Tier-2 residue: `enable_jwt` is toggleable but the scan "short-circuits on an empty target list" per template comment — toggling it on alone does nothing until this list is populated, and there is no dashboard field for it. |
| `connectors.container_targets` | `[]` | none | not-yet-covered | Same tier-2 residue as `jwt_targets`. |
| `connectors.source_targets` | `[]` | none | not-yet-covered | Same tier-2 residue. |
| `connectors.kerberos_targets` | `[]` | none | not-yet-covered | Same tier-2 residue. |
| `connectors.saml_targets` | `[]` | none | not-yet-covered | Same tier-2 residue. |
| `connectors.dnssec_targets` | `[]` | none | not-yet-covered | Same tier-2 residue. |
| `connectors.dnssec_resolver` | null | none | not-yet-covered | |
| `connectors.smime_targets` | `[]` | none | not-yet-covered | Same tier-2 residue. |
| `connectors.smime_search_base` | null | none | not-yet-covered | |
| `connectors.smime_timeout` | 10 | none | not-yet-covered | |
| `connectors.adcs_targets` | `[]` | none | not-yet-covered | Same tier-2 residue. |
| `connectors.adcs_search_base` | null | none | not-yet-covered | |
| `connectors.adcs_user` | null | none | not-yet-covered | |
| `connectors.adcs_password` | null | ConnectorsPanel "AD CS Password" masked input | covered | |
| `connectors.adcs_timeout` | 10 | none | not-yet-covered | |
| `connectors.codesign_targets` | `[]` | none | intentional-gap | `enable_codesign` itself is intentional-gap (see above); its sub-fields inherit the same disposition. |
| `connectors.codesign_search_base` | null | none | intentional-gap | Same as above. |
| `connectors.codesign_timeout` | 10 | none | intentional-gap | Same as above. |
| `connectors.gcp_project_id` | null | none | not-yet-covered | |
| `connectors.pg_targets` | `[]` | none | not-yet-covered | |
| `connectors.pg_scanner_user` | null | none | not-yet-covered | |
| `connectors.pg_scanner_password` | null | ConnectorsPanel "PostgreSQL Password" masked input | covered | |
| `connectors.mysql_targets` | `[]` | none | not-yet-covered | |
| `connectors.mysql_scanner_user` | null | none | not-yet-covered | |
| `connectors.mysql_scanner_password` | null | ConnectorsPanel "MySQL Password" masked input | covered | |
| `connectors.aws_endpoint_url` | null | none | not-yet-covered | MinIO/LocalStack S3 endpoint override. |
| `connectors.k8s_provider` | null | none | not-yet-covered | |
| `connectors.k8s_cluster_name` | null | none | not-yet-covered | |
| `connectors.k8s_namespace` | `"default"` | none | not-yet-covered | |
| `connectors.k8s_kubeconfig` | null | none | not-yet-covered | |
| `connectors.k8s_context` | null | none | not-yet-covered | |
| `connectors.gke_clusters` | `[]` | none | not-yet-covered | |
| `connectors.aks_clusters` | `[]` | none | not-yet-covered | |
| `connectors.vault_addr` | null | none | not-yet-covered | |
| `connectors.vault_token` | null | ConnectorsPanel "Vault Token" masked input | covered | |
| `connectors.vault_transit_mount` | `"transit"` | none | not-yet-covered | |
| `connectors.vault_tls_verify` | true | none | not-yet-covered | |
| `connectors.broker_azure_namespaces` | `[]` | none | not-yet-covered | |
| `connectors.broker_sqs_regions` | `[]` | none | not-yet-covered | |
| `connectors.broker_targets` | `[]` | none | not-yet-covered | Additional explicit broker hosts (Phase 190); email/broker already sweep the general `targets:` block by default, so this is additive-only and lower priority than the identity-connector target lists above. |
| `connectors.snmp_community` | `"public"` | ConnectorsPanel "SNMP Community String" input | covered | |
| `connectors.snmp_v3_credentials` | `{}` | ConnectorsPanel "SNMPv3 Username/Auth/Priv (default host)" inputs | covered-indirectly | Panel simplifies the per-host-keyed dict to a single "default" host slot (documented design note, 193-07-SUMMARY.md) — real per-host SNMPv3 entries beyond "default" are not-yet-coverable from the dashboard. |

### `intelligence` (IntelligenceCfg) — 2 fields

| Config path | Type/values | Default | Dashboard surface | Status | Notes |
|---|---|---|---|---|---|
| `intelligence.profile` | `strict\|balanced\|lenient` | `"balanced"` | scan-new.tsx "Calibration" radio | covered-indirectly | The radio's value IS `intelligence.profile`'s value directly (submitted as `calibration`). |
| `intelligence.calibration_overrides` | dict \| null | `null` | none | not-yet-covered | Template marks this "(advanced)" — fine-tuning individual weight keys; a legitimate future-milestone scope item, not attempted here. |

### `security` (SecurityCfg) — 5 fields

| Config path | Type/values | Default | Dashboard surface | Status | Notes |
|---|---|---|---|---|---|
| `security.allow_internal_targets` | bool | false | none | intentional-gap | `ScanSubmitRequest` deliberately has no field for this — CR-04 SSRF safety override; a dashboard toggle would let any browser session disable an SSRF guard with no server-side gate. Server-policy, not per-scan. |
| `security.allow_cleartext_broker_probe` | bool | false | none | intentional-gap | CR-06, same reasoning as above. |
| `security.allow_insecure_jwks` | bool | false | none | intentional-gap | CR-01, same reasoning as above. |
| `security.api_token` | str | `""` | none | intentional-gap | Dashboard API bearer-auth secret — a dashboard field to change one's own auth token from inside an authenticated session is a self-referential security hazard, install-scoped by design. |
| `security.cors_origins` | list[str] | loopback-only | none | intentional-gap | Server startup CORS allowlist — not scan-request-scoped; changing it per-request would defeat its purpose. |

### `AppConfig` top-level dict fields — 2 fields

| Config path | Type/values | Default | Dashboard surface | Status | Notes |
|---|---|---|---|---|---|
| `broker_credentials` | dict[str, BrokerCredential] | `{}` | none | intentional-gap | Persistent host-keyed broker credential config (CR-05). The dashboard's own broker credential UI (ConnectorsPanel "Broker Username/Password (default host)") is a SEPARATE, request-scoped, ephemeral env-injection path (D-12) — it deliberately never writes to this persisted dict. Writing browser-submitted credentials into a persisted, host-keyed config structure would be a credential-persistence hazard the current design explicitly avoids. |
| `remediation_aliases` | dict[str, str] | `{}` | none | intentional-gap | Template (Phase 179 REMED-03): "Edited by a human between engagements — QU.I.R.K. never learns aliases automatically (D-10)." Explicitly out of scan-submission scope by design decision, not an oversight. |

## Intentional gaps (full list, with reasons)

1. **`ports_ssh` — NOT a `config.py` field at all.** No such config key exists anywhere in the
   codebase (`grep -rn "ports_ssh" quirk/ src/dashboard/src/` returns zero hits outside comments
   explaining its absence). It was a *candidate* dashboard field considered and explicitly rejected
   during Phase 194 discuss-phase. **Reason: no CLI-side equivalent exists to achieve parity
   with — SSH targets derive from protocol-classified open ports during discovery.** Cross-referenced
   to ledger item **999.106** (`.planning/HORIZON.md`), filed 2026-09-09, P3 someday/maybe, "real
   backend capability: config field + scanner targeting support" — i.e. building `ports_ssh` for real
   would require a NEW config field and scanner-targeting mechanism, not merely a form control wired
   to an existing one. `AdvancedPanel.tsx:33` and `:277` carry the same D-18 note in source.
2. `connectors.enable_codesign` + its 3 sub-fields (`codesign_targets`, `codesign_search_base`,
   `codesign_timeout`) — driven by the `--inventory-code-signing` CLI flag; the config key itself is
   inert (`config_template.yaml:95`). No dashboard equivalent of a CLI-invocation flag exists for
   scan-submit requests.
3. `connectors.enable_authenticated_mode` — driven by CLI credential flags; D-11 scheduler rejection
   makes it structurally scan-submit-inappropriate regardless.
4. `connectors.enable_recurring_otics` — a scheduler (recurring-scan) safety gate, not a one-off
   scan-submit toggle; out of this form's surface by definition.
5. `output.directory`, `output.db_path` — server-side filesystem paths; browser-writable paths here
   are a path-injection/path-traversal surface, and the canonical single-DB-path convention depends
   on this staying server-controlled.
6. `security.allow_internal_targets`, `security.allow_cleartext_broker_probe`,
   `security.allow_insecure_jwks`, `security.api_token`, `security.cors_origins` — server-side safety
   overrides and auth/CORS policy. `ScanSubmitRequest` has no field for any of these; a per-scan
   browser toggle for an SSRF/TLS-verification guard, or a self-service auth-token rewrite, is a
   security regression, not a parity gap.
7. `broker_credentials` (top-level persisted dict) — superseded by the request-scoped, ephemeral
   D-12 credential-injection path; writing browser-submitted secrets into a persisted config
   structure is the hazard D-12 was designed to avoid.
8. `remediation_aliases` (top-level persisted dict) — explicitly human-edited between engagements
   per Phase 179 D-10; not scan-submission scoped by design.

## Tier roll-up against 999.104

**Tier 1 — Visibility parity (floor).** Structurally satisfied: `EffectiveConfigPanel` (shipped
pre-Phase-194, extended in 194-02/194-05 to include the `connectors`/`advanced` deltas) renders the
server-resolved effective config for every field this audit tables that flows through
`resolve_effective_config` — i.e. every `covered`/`covered-indirectly` field. **Verdict: CLOSED**
for the fields this phase added; it was already closed for the pre-existing 6-knob set by the
pre-Phase-194 `GET /api/config/effective` route.

**Tier 2 — Connector parity.** Enable-flag coverage: **22/25 covered, 3/25 intentional-gap** (all
25 `enable_*` flags dispositioned, zero not-yet-covered). Credential/endpoint/target sub-field
coverage: **6/46 covered or covered-indirectly (5 covered + 1 covered-indirectly), 3/46
intentional-gap (inherit `enable_codesign`'s disposition), 37/46 not-yet-covered.** Combined
tier-2 total: **34/71 dispositioned as covered, covered-indirectly, or intentional-gap, 37/71
(52%) not-yet-covered.** **Verdict: PARTIALLY CLOSED.** The enable/disable
decision for every connector IS now dashboard-reachable — this closes 999.96's feature half (every
connector can be turned on or off from the UI). But toggling several connectors on
(`enable_jwt`/`enable_container`/`enable_source`/identity connectors) is currently a no-op without
also setting their dedicated target lists, and none of those target lists have a dashboard field
yet. This is a real, named residue, not a rounding error — see "Remaining not-yet-covered fields."

**Tier 3 — Scan-behavior parity.** Of the top-level `scan.*` + `scan.timeouts.*` + `scan.retry.*`
fields (13 + 14 + 3 = 30 total), **7 covered, 1 covered-indirectly, 22 not-yet-covered.** The
AdvancedPanel shipped in 194-05 covers the fields RESEARCH's proposed shape called out explicitly
(ports, TLS enum mode, SNI, the 3 most-operator-relevant timeouts, retry count, data classification)
but the majority of per-scanner timeout fields (11 of 14) and every concurrency knob (4) remain
uncovered. **Verdict: PARTIALLY CLOSED** — the "advanced collapsible" shape tier 3 called for exists
and covers the fields the plan scoped it to, but does not cover the full `scan.*` surface.

**Tier 4 — Config-file parity (ceiling).** **Explicitly OUT of milestone scope**, per the HORIZON
v5.21 rationale row: "a new security surface deserving its own threat-model decision, not a rider."
No work in Phase 194 touches server-side `config.yaml` read/write. Confirmed zero dashboard route
exists for loading or persisting the install's `config.yaml` from the browser.

**Overall:** Tiers 1-3 are **not fully closed** by this phase — tier 1 is closed, tiers 2 and 3 are
honestly partial. The gap is concentrated in exactly the field classes the tier definitions predicted
would be harder (per-connector target lists, per-scanner-type timeout knobs) — this is a scoped,
named residue for a future milestone, not evidence of a missed requirement: PARITY-04's own plan
text (194-05) scoped its deliverable to "TLS Ports, TLS Enumeration Mode, Discovery Options
(`include_sni`), Timeouts & Retry (4 numeric fields), Data Classification" and delivered exactly
that set.

## Remaining not-yet-covered fields (65 total, for the next milestone to scope)

Grouped by theme, not padded or shrunk. Field-class counts here are derived directly from the
field-by-field table above (the table is the source of truth); totals tie to the 65
`not-yet-covered` fields in the Summary counts table.

- **Assessment metadata (4):** `assessment.name`, `report_owner`, `timezone`, `logo_path`.
- **Target exclusion (1):** `targets.exclude_ips`.
- **Scan concurrency knobs (5):** `scan.concurrency`, `fingerprint_concurrency`, `tls_concurrency`,
  `ssh_concurrency`, `motion_concurrency`.
- **Scan misc (4):** `scan.openapi_spec_path`, `hardware_history_retention_days`,
  `hardware_drift_event_retention_days`, `tls_designated_ports`.
- **Per-scanner timeouts (11):** `scan.timeouts.fingerprint_seconds`, `jwt_seconds`,
  `container_seconds`, `source_seconds`, `dnssec_seconds`, `saml_seconds`, `kerberos_seconds`,
  `vault_seconds`, `db_connect_seconds`, `broker_seconds`, `email_seconds`.
- **Retry backoff (2):** `scan.retry.backoff_base_seconds`, `backoff_max_seconds`.
- **Connector target lists — the tier-2 residue (14):** `jwt_targets`, `container_targets`,
  `source_targets`, `kerberos_targets`, `saml_targets`, `dnssec_targets`, `dnssec_resolver`,
  `smime_targets`, `smime_search_base`, `smime_timeout`, `adcs_targets`, `adcs_search_base`,
  `adcs_user`, `adcs_timeout`.
- **Cloud provider identity (6):** `aws_region`, `aws_profile`, `azure_subscription_id`,
  `azure_keyvault_urls`, `gcp_project_id`, `aws_endpoint_url`.
- **Database targets/users (4):** `pg_targets`, `pg_scanner_user`, `mysql_targets`,
  `mysql_scanner_user`.
- **K8s connector config (7):** `k8s_provider`, `k8s_cluster_name`, `k8s_namespace`,
  `k8s_kubeconfig`, `k8s_context`, `gke_clusters`, `aks_clusters`.
- **Vault connector config (3):** `vault_addr`, `vault_transit_mount`, `vault_tls_verify`.
- **Broker cloud extensions (3):** `broker_azure_namespaces`, `broker_sqs_regions`,
  `broker_targets`.
- **Intelligence advanced tuning (1):** `intelligence.calibration_overrides`.

## Verdict

D-15's field-universe enumeration is now a committed, source-derived artifact. Tier 1 is closed.
Tiers 2 and 3 are honestly partial, with the residue concentrated in per-connector target/endpoint
configuration and per-scanner-type timeout tuning — both legitimate scope for a future milestone
phase, not defects in this phase's delivered work. Tier 4 remains explicitly out of scope.
