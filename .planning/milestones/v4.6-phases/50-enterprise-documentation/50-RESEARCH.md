# Phase 50: Enterprise Documentation - Research

**Researched:** 2026-05-05
**Domain:** Documentation production (architecture reference + operator's guide); markdown + mermaid; Obsidian vault sync
**Confidence:** HIGH (all factual claims verified against the live tree on this branch)

## Summary

Phase 50 is a **pure documentation phase** with zero new runtime code. The deliverables are
two production-quality markdown files (`docs/architecture.md`, `docs/operators-guide.md`)
plus standard CLAUDE.md mandatory phase-completion artifacts (Obsidian phase note, vault
sync, UAT-SERIES.md update + sync, dedicated commits). All implementation decisions
(D-01..D-09) are locked in CONTEXT.md — research scope is to surface the **factual
substrate** that the doc-writer needs so neither doc drifts from the codebase.

The codebase is not what one might guess from older planning prose: there is **no
`quirk/scanners/` directory** — the actual package is `quirk/scanner/` (singular).
Discovery code lives separately in `quirk/discovery/`. The CLI entry point is
`run_scan:main` (not a `quirk.cli` submodule). The `quirk compliance status` subcommand
is intercepted directly inside `run_scan.py` (lines 223–244), not registered through a
sub-package. These are the kinds of facts that, if assumed wrong, would make
`docs/architecture.md` a fiction.

**Primary recommendation:** Plan the phase as 4 plans — (1) gather scanner inventory +
write `docs/architecture.md`, (2) write `docs/operators-guide.md`, (3) Obsidian vault
sync (Architecture, Operators-Guide, Hub MOC update, Phase-50 phase note), (4)
UAT-SERIES.md update + vault sync + final commits. Doc-writer must consult this
RESEARCH.md's Code Map and Scanner Inventory tables verbatim — they are the source of
truth.

## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** `docs/operators-guide.md` is a **hybrid narrative + links** doc. Continuous read flow (install → configure → scan → troubleshoot → per-scanner reference) with short canonical sections inline and "See also: `docs/<file>.md`" links for deep dives.
- **D-02:** Troubleshooting section covers all four areas: scan failures (perms, timeouts, missing optional deps, TLS handshake), database/output (db migrations, output dir perms, CBOM gen, PDF render), dashboard (Vite build, stale `.vite/`, port conflicts, data loading), plus a one-line pointer to per-connector gotchas in `docs/connectors/*`.
- **D-03:** `docs/architecture.md` framed for an **enterprise architect evaluating QUIRK** — data flow, trust boundaries, network surface, credential handling, SQLite schema overview, scanner-phase model, dashboard architecture, CBOM pipeline. NOT a code tour for new engineers.
- **D-04:** Diagrams are **mermaid code blocks** embedded in markdown. No SVG/PNG checked in.
- **D-05:** Per-scanner reference is a **compact table + linked details** pattern. One row per scanner: name, what it scans, config flags, optional deps, sample finding. Cloud/infra connectors link to existing `docs/connectors/*.md`. The protocol scanners get a 1–2 paragraph inline subsection beneath the table.
- **D-06:** No new `docs/scanners/<name>.md` files in this phase.
- **D-07:** Compliance Map Maintenance lives **inside `docs/operators-guide.md`** as a numbered runbook subsection.
- **D-08:** Compliance section structure: prose intro → numbered quarterly checklist → source URL table (PCI SSC, HHS.gov, NIST CSRC) → "How to detect drift" → "Upgrade path" worked example (PCI-DSS 4.0.1 → 4.1: bump `version` + `last_verified`, re-run gates).
- **D-09:** Runbook explicitly references Phase 49's existing CI mechanisms: `quirk compliance status` CLI, 12-month staleness gate via `STALENESS_THRESHOLD_DAYS`, schema gate, title-join gate, and cite `tests/test_compliance_freshness.py`.

### Claude's Discretion

- Exact section headings, ordering, tone, and prose density within each doc.
- Mermaid diagram count and granularity in `architecture.md` — at minimum: one system overview, one data flow (scan → DB → CBOM → reports), one dashboard architecture diagram. More if needed.
- Exact set of protocol scanners listed in the per-scanner table — researcher has now enumerated this against the live codebase below; doc-writer uses that enumeration verbatim.

### Deferred Ideas (OUT OF SCOPE)

- Docs site generator (mkdocs / docusaurus).
- `docs/scanners/<name>.md` per-protocol-scanner doc files.
- `CONTRIBUTING.md` / `docs/development.md` (engineer-onboarding audience).
- Video walkthroughs / screencasts.
- New connector docs for protocol scanners.
- Compliance map *content* changes (Phase 49 owns COMPLIANCE_MAP).

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DOCS-01 | `docs/architecture.md` documents scanner phases, data flow, SQLite schema, dashboard, CBOM pipeline | Code Map (below) gives every module path + entry point; Scanner Inventory enumerates all 17 scanner/connector modules; Data Flow section names the exact functions in run_scan.py / risk_engine / cbom/builder / reports/writer that move data between stages |
| DOCS-02 | `docs/operators-guide.md` covers install, configuration, scanning workflow, troubleshooting, and per-scanner reference for self-onboarding enterprise customers | Existing Docs Inventory tells the doc-writer exactly what each existing doc covers (so operators-guide links not duplicates); Config Flag Inventory enumerates every `enable_*` flag verbatim from `config_template.yaml`; Troubleshooting Sources lists where each failure mode is already documented |
| DOCS-03 | Both new docs synced to Obsidian vault under `20_Dev-Work/QUIRK/Reference/` with standard frontmatter | Vault Sync Mechanics section gives the exact `printf | cat | cp` pattern from CLAUDE.md and the four target paths |
| DOCS-04 | `docs/operators-guide.md` documents compliance map maintenance — quarterly review, source URLs, upgrade path | Phase 49 Compliance Surface section lists exact module paths, public symbols, CLI subcommand line numbers in run_scan.py, and the three test file paths to cite |

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Doc authoring | Repo (`docs/`) | — | Plain markdown; rendered by GitHub + Obsidian |
| Diagrams | Repo (mermaid blocks inline) | — | D-04: no external assets; mermaid renders in both GitHub and Obsidian |
| Knowledge mirror | Obsidian vault filesystem (`/Users/digs/vaults/Digs/...`) | — | CLAUDE.md mandates vault writes via `printf | cat | cp` for files too large for `obsidian CLI content=` |
| MOC integration | `_QUIRK-Hub.md` wikilinks | — | Hub note gets two new wikilinks under Reference |
| Validation | UAT-SERIES.md (gating doc) | pytest meta-tests (none required) | Phase is markdown-only; UAT criteria are file-presence + section-content greps |

## Code Map (Authoritative Module Inventory)

This is the substrate `docs/architecture.md` describes. **Every path here was verified
against the live `QUIRK-v4` working tree on 2026-05-05.** [VERIFIED: filesystem]

### Top-level package layout

```
QUIRK/
├── run_scan.py                      # CLI entry point (pyproject [project.scripts] = "quirk = run_scan:main")
├── pyproject.toml                   # Package metadata + optional-extras
├── config.yaml                      # Default config (user-edited)
├── quirk.db                         # Default SQLite path
├── quirk/
│   ├── __init__.py                  # Package version
│   ├── config.py                    # ScanCfg + TimeoutsCfg + RetryCfg dataclasses (YAML loader)
│   ├── config_template.yaml         # Generated by `quirk init`
│   ├── interactive.py               # Wizard (multi-target paste, @file, nmap y/N prompt)
│   ├── models.py                    # SQLAlchemy declarative_base() + CryptoEndpoint
│   ├── db.py                        # Engine factory + idempotent _ensure_*_columns migrations
│   ├── validate.py                  # Config validation
│   ├── logging_util.py              # Structured logging
│   ├── cli/                         # Banner + `quirk init` subcommand only
│   │   ├── __init__.py
│   │   ├── banner.py
│   │   └── init_cmd.py
│   ├── scanner/                     # ⚠️ SINGULAR — NOT scanners/
│   │   ├── tls_scanner.py
│   │   ├── tls_capabilities.py
│   │   ├── ssh_scanner.py
│   │   ├── jwt_scanner.py
│   │   ├── container_scanner.py
│   │   ├── source_scanner.py
│   │   ├── dnssec_scanner.py
│   │   ├── kerberos_scanner.py
│   │   ├── saml_scanner.py
│   │   ├── email_scanner.py
│   │   ├── broker_scanner.py
│   │   ├── aws_connector.py
│   │   ├── azure_connector.py
│   │   ├── gcp_connector.py
│   │   ├── db_connector.py
│   │   ├── k8s_connector.py
│   │   ├── vault_connector.py
│   │   ├── fingerprint.py           # Pre-scan port fingerprinting
│   │   └── target_expander.py       # CIDR / @file / CSV expansion (Phase 47)
│   ├── discovery/                   # Separate from scanner/ — nmap port discovery
│   │   ├── nmap_provider.py
│   │   ├── nmap_parser.py
│   │   ├── coverage.py
│   │   └── tls_scanner.py           # (note: discovery TLS shim — distinct from scanner/tls_scanner.py)
│   ├── engine/
│   │   ├── risk_engine.py           # _build_finding() chokepoint (Phase 48); _normalize_for_compliance() (Phase 49)
│   │   ├── profiles.py              # strict / balanced / lenient profile multipliers
│   │   ├── cache.py
│   │   ├── rate_limiter.py
│   │   └── migration_planner.py
│   ├── intelligence/
│   │   ├── scoring.py               # 6-subscore readiness score (incl. data_in_motion + data_at_rest)
│   │   ├── confidence.py
│   │   ├── roadmap.py
│   │   └── evidence.py
│   ├── compliance/
│   │   └── __init__.py              # COMPLIANCE_MAP, UNMAPPED_TITLES, STALENESS_THRESHOLD_DAYS, status_report()
│   ├── cbom/
│   │   ├── builder.py               # build_cbom(endpoints) -> Bom (CycloneDX 1.6)
│   │   ├── classifier.py            # Algorithm classification
│   │   └── writer.py                # write_cbom_files()
│   ├── reports/
│   │   ├── writer.py                # write_reports() — orchestrates HTML/PDF/JSON
│   │   ├── html_renderer.py         # Jinja render → HTML; PDF via Playwright
│   │   ├── executive.py             # Executive markdown
│   │   ├── technical.py             # Technical markdown
│   │   └── templates/
│   │       └── report.html.j2       # Single Jinja template (HTML + PDF)
│   ├── dashboard/                   # FastAPI server (Python tier of dashboard)
│   │   ├── server.py                # `quirk serve` — uvicorn launcher
│   │   ├── api/
│   │   │   ├── app.py               # FastAPI app factory
│   │   │   ├── deps.py
│   │   │   ├── schemas.py           # Pydantic DTOs (FindingItem, IdentityFinding, MotionFinding, DarFinding)
│   │   │   └── routes/
│   │   │       ├── health.py
│   │   │       ├── scan.py          # /api/scan/latest — derives findings from CryptoEndpoint rows
│   │   │       ├── trends.py        # /api/trends — multi-session deltas
│   │   │       └── pdf.py
│   │   └── static/                  # Built React bundle (output of src/dashboard build)
│   ├── assessment/
│   └── util/
├── src/
│   └── dashboard/                   # React 19 + Vite 8 + TypeScript + Tailwind + shadcn/ui (UI tier)
│       ├── package.json
│       ├── vite.config.ts
│       ├── tsconfig.json
│       ├── tailwind.config.ts
│       ├── components.json          # shadcn config
│       └── src/
│           ├── App.tsx
│           ├── main.tsx
│           ├── pages/               # /executive, /findings, /identity, /motion, /data-at-rest, /certificates, /cbom, /roadmap, /trends
│           ├── components/
│           ├── context/
│           ├── hooks/
│           └── lib/
├── tests/                           # pytest — 200+ test files
├── quantum-chaos-enterprise-lab/    # Docker Compose chaos lab (lab.sh + 18 profiles)
└── docs/                            # Markdown docs (this phase adds 2)
```

[VERIFIED: filesystem walk 2026-05-05]

### CLI entry-point flow (`run_scan.py`)

| Line | Behavior | Purpose |
|------|----------|---------|
| 82 | `_phase_timer(run_stats, name)` context manager | Each scanner runs inside a phase-timer span — feeds `run_stats` for the report metrics |
| 93 | `_wrapped_phase(run_stats, phase_name, scanner_label, fn, error_endpoints, logger)` | Phase 41 D-14: BaseException-safe wrapper around every scanner phase. Surfaces `missing_extra` + scan-error advisories without crashing the run |
| 176 | `def main()` | argparse entry point |
| 220 | `serve` subcommand handler | Calls `quirk.dashboard.server.serve()` |
| 223–244 | `compliance` subcommand interceptor | **Phase 50 compliance runbook cites this** — calls `quirk.compliance.status_report(format=...)` |
| 388 | `_phase_timer(run_stats, "discovery")` | Nmap discovery phase (Phase 47) |
| 462 | `_phase_timer(run_stats, "fingerprinting")` | Pre-scan port fingerprint |
| 546–584 | TLS + SSH `_run_*_phase` wrapped via `_wrapped_phase` | Plain-protocol scan loop |
| 593–937 | All other scanner phases — each in its own `_phase_timer` span | Architecture doc's "scanner phase model" diagram |
| 989 | `_phase_timer(run_stats, "risk_engine")` | Risk engine evaluates findings (Phase 48 `_build_finding` is invoked here) |

[VERIFIED: grep run_scan.py]

### SQLite schema source

- **Single declarative model:** `quirk/models.py` (92 LOC) — `Base = declarative_base()` and one table: `class CryptoEndpoint` (`__tablename__ = "crypto_endpoints"`).
- **Migration mechanism:** `quirk/db.py` exposes idempotent column-add functions (`_ensure_identity_columns`, `_ensure_gcp_columns`, `_ensure_v43_columns`, `_ensure_email_columns`, `_ensure_broker_columns`, `_ensure_phase41_columns`, `_ensure_phase46_columns`) — all called from `init_db()`. Backward-compatible additive migrations only — never drops or renames.
- **Per-scanner JSON aggregates:** large nested results (kerberos, saml, email, broker, dnssec, vault, db, k8s, etc.) are stored as `*_scan_json` Text columns on the same `crypto_endpoints` row, keyed by lowest-port endpoint per host.

[VERIFIED: read quirk/models.py + grep db.py]

### CBOM pipeline entry points

- **Build:** `quirk.cbom.builder.build_cbom(endpoints: list[CryptoEndpoint]) -> Bom` (612 LOC) — produces a CycloneDX 1.6 `Bom` object (`cyclonedx-python-lib` library).
- **Classify:** `quirk.cbom.classifier` — algorithm-name → primitive/NIST-level lookup; coverage report regenerated by `tests/test_cbom_classifier_coverage.py::test_regenerate_coverage_report`.
- **Write:** `quirk.cbom.write_cbom_files()` — emits `cbom-<timestamp>.json` and `.xml` in the configured output dir; post-write strict JSON validator runs (Phase 47 D-13–D-16).

[VERIFIED: grep cbom/builder.py classifier.py writer.py]

### Reports pipeline entry points

`quirk/reports/writer.py::write_reports(cfg, endpoints, findings, run_stats=None, *, error_endpoints=None)` is the single orchestrator. It calls:

- `compute_readiness_score()` (`quirk.intelligence.scoring`)
- `build_evidence_summary()` (`quirk.intelligence.evidence`)
- `build_phased_roadmap()` (`quirk.intelligence.roadmap`)
- `compute_confidence()` (`quirk.intelligence.confidence`)
- `build_cbom() → write_cbom_files()` (`quirk.cbom`)
- `categorize_waves()` (`quirk.engine.migration_planner`)
- `render_html_report()` and `render_pdf_report()` (`quirk.reports.html_renderer`)
- Writes `intelligence-<ts>.json`, `findings-<ts>.json`, executive + technical markdown.

`PLATFORM_VERSION = "4.4.0"`, `SCHEMA_VERSION = 2`, `INTELLIGENCE_VERSION = "4.4.0"` are
constants at the top of `writer.py` — note the version may need bumping to 4.6.0 for the
v4.6 milestone close (out of scope for Phase 50 but a fact to record).

The HTML and PDF outputs share **a single Jinja template:** `quirk/reports/templates/report.html.j2`. PDF is rendered by Playwright headless-Chromium printing the same HTML.

[VERIFIED: read writer.py header + grep reports/templates]

### Dashboard architecture (two tiers)

| Tier | Location | Tech | Role |
|------|----------|------|------|
| Backend | `quirk/dashboard/` | FastAPI + uvicorn (in `[dashboard]` extra) | Reads `quirk.db` (SQLAlchemy), derives `FindingItem` / `IdentityFinding` / `MotionFinding` / `DarFinding` Pydantic DTOs from `CryptoEndpoint` rows, serves `/api/*` |
| Frontend | `src/dashboard/` | React 19, Vite 8, TypeScript, Tailwind, shadcn/ui | SPA — pages: `/executive`, `/findings`, `/identity`, `/motion`, `/data-at-rest`, `/certificates`, `/cbom`, `/roadmap`, `/trends`. Built bundle is committed at `quirk/dashboard/static/` so `quirk serve` ships UI without a node toolchain |
| Launch | `quirk serve` (handler at `run_scan.py:220`) | calls `quirk.dashboard.server.serve(port=8512, host="127.0.0.1", no_open=False)` | Default port 8512, local-only, opens browser unless `--no-open` |

**Data flow (no separate ingest pipeline):** the React SPA fetches `/api/scan/latest`,
`/api/trends`, etc. The FastAPI route handlers query `quirk.db` directly (live
SQLAlchemy session) and derive the DTO shapes inline (`_derive_findings`,
`_derive_identity_findings`, `_derive_motion_findings`, `_derive_dar_findings` in
`routes/scan.py`). No JSON file mediates between Python and React in production.

[VERIFIED: read server.py, app.py, src/dashboard/package.json]

## Scanner Inventory (table substrate for operators-guide §Per-Scanner Reference)

This is the **D-05 compact table** the doc-writer fills in. Order of rows is roughly the
scan-phase execution order from `run_scan.py`. Cells are filled with verified facts;
"Sample finding" examples are pulled from `COMPLIANCE_MAP` keys in
`quirk/compliance/__init__.py` because those are guaranteed to be exact runtime title
strings (Phase 49 title-join gate proves it).

### Protocol scanners (inline subsection in operators-guide.md)

| Scanner | Module | Scans | Config flag(s) | Optional extra | Sample finding title |
|---------|--------|-------|----------------|----------------|----------------------|
| Discovery (nmap) | `quirk/discovery/nmap_provider.py` | TCP port discovery before TLS/SSH/etc. fingerprint | wizard prompt; `--targets-file <path>`; `cidrs:` / `include_ips:` / `fqdns:` | nmap binary (OS package) | (advisory) "Scanner skipped — optional extra not installed" if nmap absent |
| Fingerprint | `quirk/scanner/fingerprint.py` | Cheap protocol probe per (host, port) → routes to TLS/SSH/JWT/etc. | `scan.ports_tls`, `scan.timeouts.fingerprint_seconds` | (none) | (no findings — routing layer) |
| TLS | `quirk/scanner/tls_scanner.py` | TLS handshake, cert chain, cipher suites, key sizes | `scan.ports_tls`, `scan.include_sni`, `scan.timeouts.tls_seconds` | sslyze (in core deps) | "TLS certificate expired"; "Legacy TLS versions allowed (TLS 1.0/1.1)"; "TLS certificate uses undersized RSA key" |
| SSH | `quirk/scanner/ssh_scanner.py` | SSH banner + ssh-audit (KEX/host key/cipher) | `scan.timeouts.ssh_seconds` | ssh-audit (OS or pip) | "SSH quantum planning advisory" (informational) |
| JWT/API | `quirk/scanner/jwt_scanner.py` | JWT signing-alg discovery on REST endpoints | `connectors.enable_jwt`, `connectors.jwt_targets` | (none) | (algorithm-classification findings) |
| Container | `quirk/scanner/container_scanner.py` | Crypto libraries inside Docker images via Syft SBOM | `connectors.enable_container`, `connectors.container_targets` | syft binary | "End-of-life in container image"; "Container image uses quantum-vulnerable crypto library"; "Outdated pyOpenSSL package in container image" |
| Source code | `quirk/scanner/source_scanner.py` | semgrep on git repos for crypto antipatterns | `connectors.enable_source`, `connectors.source_targets` | semgrep | (semgrep-rule-driven findings) |
| DNSSEC | `quirk/scanner/dnssec_scanner.py` | DNSKEY / DS / RRSIG against named zone | `connectors.enable_dnssec`, `connectors.dnssec_targets`, `scan.timeouts.dnssec_seconds` | `quirk[identity]` (dnspython[dnssec]) | (algorithm + chain findings) |
| Kerberos | `quirk/scanner/kerberos_scanner.py` | KDC enctype enumeration on port 88 | `connectors.enable_kerberos`, `connectors.kerberos_targets`, `scan.timeouts.kerberos_seconds` | `quirk[identity]` (impacket) | (etype findings) |
| SAML | `quirk/scanner/saml_scanner.py` | SAML IdP metadata XML signing/digest algs | `connectors.enable_saml`, `connectors.saml_targets`, `scan.timeouts.saml_seconds` | `quirk[identity]` (lxml, defusedxml, signxml) | (signature-alg findings) |
| Email (SMTP/IMAP/POP3 ± STARTTLS) | `quirk/scanner/email_scanner.py` | 7-port email TLS probe | `connectors.enable_email`, `scan.timeouts.email_seconds` | `quirk[motion]` (= `[email] + [broker] + [kafka]`) | "STARTTLS downgrade risk on SMTP"; "Weak cipher suite on email TLS endpoint"; "Non-PFS cipher suite on email TLS endpoint" |
| Broker (Kafka / AMQP / Redis / Azure Service Bus / SQS) | `quirk/scanner/broker_scanner.py` | Plaintext + TLS listener probes | `connectors.enable_broker`, `connectors.broker_azure_namespaces`, `connectors.broker_sqs_regions`, `scan.timeouts.broker_seconds` | `quirk[motion]` | "Plaintext Kafka listener detected"; "Plaintext AMQP listener detected"; "Plaintext Redis listener (no auth)"; "Weak cipher suite on broker TLS endpoint" |

### Cloud / infra connectors (link to existing `docs/connectors/*.md`)

| Connector | Module | Scans | Config flag(s) | Optional extra | Existing doc |
|-----------|--------|-------|----------------|----------------|--------------|
| AWS | `quirk/scanner/aws_connector.py` | ACM certs, KMS keys, CloudFront, ELB | `connectors.enable_aws`, `connectors.aws_region`, `connectors.aws_profile` | boto3 (in core deps) | `docs/connectors/aws.md` |
| Azure | `quirk/scanner/azure_connector.py` | Key Vault keys + certs, App Gateway TLS | `connectors.enable_azure`, `connectors.azure_subscription_id`, `connectors.azure_keyvault_urls` | (azure-mgmt-* in `[cloud]` for some sub-features) | `docs/connectors/azure.md` |
| GCP | `quirk/scanner/gcp_connector.py` | GCP KMS + GCS storage encryption | `connectors.enable_gcp`, `connectors.gcp_project_id` | `quirk[cloud]` (google-api-python-client, google-auth) | (no dedicated doc — gap acknowledged) |
| Database | `quirk/scanner/db_connector.py` | PostgreSQL + MySQL ssl-mode + RDS encryption | `connectors.enable_db`, `connectors.pg_targets`, `connectors.mysql_targets`, plus user/password fields | `quirk[db]` (psycopg2-binary, PyMySQL) | (no dedicated doc — gap acknowledged) |
| Object storage (S3 + Blob) | within `aws_connector.py` / `azure_connector.py` | S3 bucket encryption, Azure Blob encryption | `connectors.enable_s3`, `connectors.aws_endpoint_url`, `connectors.enable_blob` | `quirk[cloud]` (azure-mgmt-storage) | (no dedicated doc — gap acknowledged) |
| Kubernetes | `quirk/scanner/k8s_connector.py` | EKS/GKE/AKS encryption + secret-type enumeration | `connectors.enable_k8s`, `connectors.k8s_provider`, `connectors.k8s_cluster_name`, `gke_clusters`, `aks_clusters`, kubeconfig fields | `quirk[cloud]` (kubernetes, google-cloud-container, azure-mgmt-containerservice) | (no dedicated doc — gap acknowledged) |
| Vault (HashiCorp) | `quirk/scanner/vault_connector.py` | Transit keys + PKI + auth methods | `connectors.enable_vault`, `connectors.vault_addr`, `connectors.vault_token`, `connectors.vault_transit_mount`, `connectors.vault_tls_verify` | `quirk[cloud]` (hvac) | (no dedicated doc — gap acknowledged) |
| Docker (image SBOM) | (uses `container_scanner.py` above) | (see Container row) | (see above) | syft binary | `docs/connectors/docker.md` |
| Git (semgrep) | (uses `source_scanner.py` above) | (see Source code row) | (see above) | semgrep | `docs/connectors/git.md` |

[VERIFIED: ls quirk/scanner + grep config_template.yaml + read pyproject.toml extras + grep COMPLIANCE_MAP keys]

**Scanner count:** 12 protocol/connector source modules under `quirk/scanner/` plus the
`quirk/discovery/` package. The "ASSUMED to be confirmed" list in CONTEXT.md D-05 is now
**confirmed** via this enumeration — there is no separate registry/manifest file; the
authoritative source is the import statements + `_phase_timer` calls in `run_scan.py`.

## Existing Docs Inventory (for operators-guide.md "See also" links — DO NOT duplicate)

| File | One-line summary | operators-guide should link from |
|------|------------------|----------------------------------|
| `docs/installation.md` | System requirements + install procedures (pip, extras, OS packages) | "Install" section — link, do not duplicate |
| `docs/configuration.md` | Reference for all six config blocks (assessment, scan, targets, connectors, output, intelligence) | "Configure" section — link |
| `docs/getting-started.md` | Zero-to-first-scan in 10 minutes | "First scan" section — link |
| `docs/chaos-lab.md` | Docker Compose chaos lab usage; profile reference | "Validation / smoke test" subsection — link |
| `docs/cbom-guide.md` | What CBOM is + how QUIRK builds it + audit citation language (NIST SP 800-208, CNSA 2.0, ISO 27001) | architecture.md cites for CBOM pipeline depth |
| `docs/cbom-classifier-coverage.md` | Generated coverage report — algorithms surfaced by `build_cbom()` across 18 chaos lab profiles | architecture.md cites for classifier coverage |
| `docs/intelligence-schema.md` | `intelligence-<ts>.json` schema reference (intelligence_version 1.0.0) | architecture.md cites for finding/scoring schema |
| `docs/timeout-retry-audit.md` | Per-scanner timeout + retry policy (post-Phase 41 refactor); single source of truth: `TimeoutsCfg` + `RetryCfg` | architecture.md cites; troubleshooting cites for timeout-related issues |
| `docs/quirk-overview.md` | Project pitch (frontmatter says `type: reference`, already has Obsidian-vault headers) | architecture.md should be consistent with framing |
| `docs/report-interpretation.md` | Maps every report number/label/finding to plain English + client-conversation sideboxes | operators-guide cites for "How to read your report" |
| `docs/sample-config.yaml` | Annotated example config | operators-guide cites in "Configure" |
| `docs/connectors/aws.md` | AWS connector setup + IAM permissions | per-scanner table links from AWS row |
| `docs/connectors/azure.md` | Azure connector setup | per-scanner table links from Azure row |
| `docs/connectors/docker.md` | Docker container connector + Syft setup | per-scanner table links from Container row |
| `docs/connectors/git.md` | Git/source connector + semgrep setup | per-scanner table links from Source code row |
| `docs/release-notes/4.4.0.md` | v4.4.0 release notes | architecture.md may footnote |
| `docs/UAT-SERIES.md` | Gating UAT document (this phase appends UAT-50-NN block) | (not linked from operators-guide; internal QA artifact) |

**Gaps the operators-guide must cover INLINE (no existing doc):**

1. **Troubleshooting** — there is **no `docs/troubleshooting.md`** today. operators-guide §Troubleshooting must be net-new content covering all four areas (D-02): scan failures, database/output, dashboard, plus pointer to per-connector gotchas.
2. **Per-scanner reference for protocol scanners** — TLS, SSH, JWT, DNSSEC, Kerberos, SAML, Email, Broker, Container, Source code have **no connector docs**. Inline 1–2 paragraph subsections per D-05.
3. **Compliance Map Maintenance** — net-new runbook content per D-07 / D-08 / D-09.
4. **GCP / Database / S3 / Vault / K8s connectors** — no `docs/connectors/<name>.md` for these. Per CONTEXT.md, this gap is **acknowledged but NOT filled in Phase 50**. The per-scanner table will simply not have a "Existing doc" link for those rows.

[VERIFIED: ls docs/, head of each]

## Phase 49 Compliance Surface (substrate for operators-guide §Compliance Map Maintenance)

The runbook must cite these by **exact path + symbol** so a future maintainer can follow
the pointer back into code without grepping. All confirmed against the live tree.

### Module + public symbols

- **File:** `quirk/compliance/__init__.py` (243 LOC; 5 exports)
- **Public exports** (`__all__` at line 237):
  - `COMPLIANCE_MAP: Dict[str, List[Dict[str, Any]]]` — 28 entry keys (line 101)
  - `UNMAPPED_TITLES: FrozenSet[str]` — 7 keys, each with inline justification (line 188)
  - `TITLE_PREFIX_ALIASES: Dict[str, str]` — f-string title prefix → canonical key (line 71)
  - `STALENESS_THRESHOLD_DAYS: int = 365` (line 22) — controls 12-month freshness gate
  - `status_report(format: str = "text") -> None` (line 207) — driver for `quirk compliance status`

### Source URLs (the runbook cites these verbatim)

| Framework | Constant | URL |
|-----------|----------|-----|
| PCI-DSS 4.0.1 | `_PCI_4_0_1_URL` | `https://docs-prv.pcisecuritystandards.org/PCI%20DSS/Standard/PCI-DSS-v4_0_1.pdf` |
| HIPAA 45 CFR §164.312 | `_HIPAA_164_312_URL` | `https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-C/part-164/subpart-C/section-164.312` |
| FIPS 140-3 | `_FIPS_140_3_URL` | `https://csrc.nist.gov/pubs/fips/140-3/final` |

For the D-08 runbook "source URL table" the operator-facing rendition should list the
**publisher home** (PCI SSC, ECFR/HHS, NIST CSRC) plus these direct links. The
publisher monitoring URLs:

- PCI SSC: `https://www.pcisecuritystandards.org/document_library/`
- HHS / ECFR: `https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-C/part-164`
- NIST CSRC: `https://csrc.nist.gov/publications/fips`

### CLI subcommand wiring

`quirk compliance status` is **NOT** a registered argparse sub-parser at the package
level — it is **intercepted by argv-sniffing** in `run_scan.py`:

- File: `run_scan.py`, lines 223–244 [VERIFIED]
- Trigger: `if len(_sys.argv) > 1 and _sys.argv[1] == "compliance"`
- Sub-action: `comp_sub.add_parser("status", ...)`
- Flag: `--format {text,json}` (default text)
- Action: imports `quirk.compliance.status_report` lazily and calls it.

The runbook should describe the user-facing command (`quirk compliance status` /
`quirk compliance status --format json`) but **not** the argv-sniffing implementation
detail (out of scope per audience D-03 — operator's guide, not engineer onboarding).

### Test files to cite

| Test file | Gate it enforces | Phase 49 requirement |
|-----------|------------------|----------------------|
| `tests/test_compliance_schema.py` | Every `COMPLIANCE_MAP` entry has `framework` + `control` + `version` + `last_verified` + `source_url` | COMPLY-06, COMPLY-07 |
| `tests/test_compliance_freshness.py` | No entry's `last_verified` is older than `STALENESS_THRESHOLD_DAYS` (365) | **COMPLY-08 — the 12-month staleness gate** |
| `tests/test_compliance_title_join.py` | Every emitted finding title is in `COMPLIANCE_MAP` or `UNMAPPED_TITLES` | COMPLY-02, COMPLY-03, COMPLY-04 |
| `tests/test_compliance_cli.py` | `quirk compliance status` smoke (text + JSON) | COMPLY-09 |
| `tests/test_compliance_report_section.py` | HTML/PDF "Compliance Summary" section content | COMPLY-05 |

The runbook should cite **at minimum** `tests/test_compliance_freshness.py` per D-09;
all five paths are valuable to list as "what CI enforces."

[VERIFIED: read quirk/compliance/__init__.py + run_scan.py:223-244 + ls tests/test_compliance_*]

### Worked upgrade-path example (substrate for D-08 "PCI-DSS 4.0.1 → 4.1")

The doc-writer should describe these exact steps for the worked example:

1. PCI SSC publishes PCI-DSS v4.1 (hypothetical) at the document library URL.
2. Maintainer reviews diff: control numbers may shift, requirement text may add new clauses.
3. Edit `quirk/compliance/__init__.py`:
   - Update `_PCI_4_0_1_URL` constant (line 29) → rename and re-point to the v4.1 PDF, or add `_PCI_4_1_URL` and update `_pci()` helper.
   - Update `_pci()` helper (line 39) — change `"version": "4.0.1"` → `"version": "4.1"`.
   - Update `_PHASE_49_VERIFIED` (line 26) → today's ISO date.
   - For any control numbers that moved (e.g., "4.2.1" → "4.2.2"): edit each affected `COMPLIANCE_MAP` entry's `_pci("X")` argument.
4. Run `pytest tests/test_compliance_schema.py tests/test_compliance_freshness.py tests/test_compliance_title_join.py` — all green.
5. Run `quirk compliance status` — confirm new version + today's `last_verified` print.
6. Commit and push; CI re-runs the full gate.

## Config Flag Inventory (substrate for operators-guide §Configure)

Verbatim from `quirk/config_template.yaml` [VERIFIED: read]. Doc-writer cross-references
this against the per-scanner table.

### Always-on (no extras gate)

```yaml
assessment:
  name, report_owner, data_classification, timezone
targets:
  include_ips, fqdns, cidrs, exclude_ips
scan:
  ports_tls: [443, 8443, 4443]
  timeout_seconds: 10
  concurrency: 20
  include_sni: true
  # (timeouts: + retry: sub-tables — see docs/timeout-retry-audit.md)
output:
  directory: "./quirk-output"
  db_path: "./quirk.db"
connectors:
  enable_aws | aws_region | aws_profile
  enable_azure | azure_subscription_id | azure_keyvault_urls
  enable_jwt | jwt_targets
  enable_container | container_targets
  enable_source | source_targets
```

### Behind `quirk[identity]`

```yaml
connectors:
  enable_kerberos | kerberos_targets
  enable_saml | saml_targets
  enable_dnssec | dnssec_targets
```

### Behind `quirk[cloud]`

```yaml
connectors:
  enable_gcp | gcp_project_id
  enable_s3 | aws_endpoint_url
  enable_blob
  enable_k8s | k8s_provider | k8s_cluster_name | k8s_namespace
              | k8s_kubeconfig | k8s_context | gke_clusters | aks_clusters
  enable_vault | vault_addr | vault_token | vault_transit_mount | vault_tls_verify
```

### Behind `quirk[db]`

```yaml
connectors:
  enable_db | pg_targets | pg_scanner_user | pg_scanner_password
            | mysql_targets | mysql_scanner_user | mysql_scanner_password
```

### Behind `quirk[motion]` (= `[email] + [broker] + [kafka]`)

```yaml
connectors:
  enable_broker | broker_azure_namespaces | broker_sqs_regions
  # email scanner uses scan.timeouts.email_seconds — no enable_email flag distinct from STARTTLS auto-detection
```

### Optional intelligence-scoring profile

```yaml
intelligence:
  profile: balanced     # strict | balanced | lenient
  # calibration_overrides: { ... }
```

### Optional extras matrix (`pyproject.toml` `[project.optional-dependencies]`)

| Extra | Includes | Purpose |
|-------|----------|---------|
| `dashboard` | fastapi, uvicorn[standard], python-multipart, playwright | `quirk serve` + PDF rendering |
| `identity` | impacket, ldap3 | Kerberos + SAML scanners (NB: dnspython[dnssec] separately) |
| `cloud` | google-api-python-client, google-auth, azure-mgmt-storage, kubernetes, google-cloud-container, azure-mgmt-containerservice, hvac | GCP + Azure Blob + K8s + Vault |
| `db` | psycopg2-binary, PyMySQL | DB connector |
| `email`, `broker`, `kafka` | (sub-extras) | Email + broker scanner pip groups |
| `motion` | `quirk[email] + quirk[broker] + quirk[kafka]` | Umbrella for data-in-motion scanners |
| `all` | All of above EXCEPT `[identity]` | One-shot install (impacket excluded — transitively downgrades cryptography per Phase 45-01 D-07) |

[VERIFIED: read pyproject.toml]

## Architecture Diagrams (Mermaid Substrate)

The doc-writer must produce **at minimum** these three diagrams per D-04 + CONTEXT.md
specifics. Below is the factual content each diagram must reflect — not the rendered
mermaid syntax (that's authoring).

### Diagram 1: System Overview

**Nodes:**
- User CLI (`quirk` command, `run_scan:main`)
- `interactive.py` wizard (multi-target paste, @file, nmap y/N)
- `quirk init` (`cli/init_cmd.py`) → `config.yaml`
- Scanner phases (12 entries) — TLS, SSH, JWT, Container, Source, AWS, Azure, GCP, DB, K8s, Vault, Email, Broker, DNSSEC, Kerberos, SAML
- `quirk.engine.risk_engine` — `_build_finding()` chokepoint
- `quirk.compliance` — eager attachment via `_normalize_for_compliance`
- `quirk.intelligence` — scoring + roadmap + evidence + confidence
- `quirk.cbom` — build_cbom + write_cbom_files
- `quirk.reports.writer.write_reports()` → HTML + PDF + JSON + executive.md + technical.md
- SQLite (`quirk.db`) ← all scanner phases persist via `quirk.models.CryptoEndpoint`
- `quirk serve` (uvicorn) → FastAPI → `/api/scan/latest` → React SPA at `:8512`

**Trust boundaries:**
- All scanner outbound network traffic goes through QUIRK process; nothing inbound except dashboard's loopback HTTP server.
- Cloud creds: AWS via `~/.aws/credentials` profile; Azure via subscription_id + DefaultAzureCredential chain; GCP via ADC; Vault via `VAULT_TOKEN` env var; Kerberos via host's existing krb5 ticket cache + impacket's password fallback.
- No outbound telemetry. No internet calls beyond explicit scan targets + chaos lab.

### Diagram 2: Scan-to-Output Data Flow

**Sequence:**
1. CLI parses argv → `ScanCfg`
2. (Optional) Interactive wizard fills target list / nmap toggle
3. Discovery phase (nmap) — emits port list (or skips with `missing_extra` advisory)
4. Fingerprinting — for each (host, port), classify protocol → route to scanner
5. Each scanner phase runs inside `_phase_timer(run_stats, name)` + `_wrapped_phase(...)` BaseException guard
6. Each scanner emits `CryptoEndpoint` rows → SQLAlchemy session → SQLite
7. `risk_engine` reads endpoints → calls `_build_finding(...)` chokepoint → eager `_normalize_for_compliance` attaches `compliance:` field per Phase 49 D-02
8. `intelligence.scoring.compute_readiness_score(findings)` → 6-subscore readiness score (data_in_motion, data_at_rest, agility, identity, ...)
9. `cbom.build_cbom(endpoints) → write_cbom_files()` → `cbom-<ts>.json` + `.xml` (CycloneDX 1.6)
10. `reports.writer.write_reports(...)` → HTML (Jinja `report.html.j2`) → Playwright PDF render → executive.md + technical.md + findings-<ts>.json + intelligence-<ts>.json
11. (Operator) `quirk serve` reads same SQLite → React SPA renders 9 dashboard pages

### Diagram 3: Dashboard Architecture

**Two tiers + persistence:**
- React SPA (`src/dashboard/`) — Vite 8 + React 19 + TypeScript + Tailwind + shadcn/ui — built into `quirk/dashboard/static/`
- FastAPI backend (`quirk/dashboard/api/app.py` factory + 4 route modules: health, scan, trends, pdf) — uvicorn on `127.0.0.1:8512`
- SQLite (`quirk.db`) — single source of truth; backend opens SQLAlchemy session per request and derives Pydantic DTOs (`FindingItem`, `IdentityFinding`, `MotionFinding`, `DarFinding`) inline in `routes/scan.py::_derive_*` functions
- 9 SPA pages: `/executive`, `/findings`, `/identity`, `/motion`, `/data-at-rest`, `/certificates`, `/cbom`, `/roadmap`, `/trends`
- PDF endpoint uses Playwright headless Chromium (same code path as report PDF render)

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Diagrams | SVG/PNG checked into `docs/` | Mermaid code blocks (D-04) | Renders in GitHub + Obsidian out of the box; diff-friendly; no asset management |
| Operator's guide structure | A new docs site (mkdocs/docusaurus) | Single hybrid markdown file linking existing docs (D-01) | Out-of-scope per CONTEXT.md; v4.6 timeline doesn't allow site-gen onboarding |
| Per-scanner doc files | `docs/scanners/<name>.md` per protocol scanner (12+ files) | Inline subsections under per-scanner table in operators-guide.md (D-06) | Out-of-scope per CONTEXT.md; future docs-split phase can extract |
| Vault sync for large markdown | `obsidian CLI content="..."` (shell-expansion limit) | `printf | cat docs/file.md >> /tmp/X.md && cp /tmp/X.md /Users/digs/vaults/Digs/...` (CLAUDE.md mandate) | Both new docs will exceed shell expansion limits |
| Compliance content rewrites | Editing `COMPLIANCE_MAP` entries / source URLs | Document the runbook only — Phase 49 owns the data | Out-of-scope per CONTEXT.md; phase 50 only documents the maintenance process |

## Common Pitfalls

### Pitfall 1: Calling the package "scanners" (plural)

**What goes wrong:** Doc says "see `quirk/scanners/tls_scanner.py`" — file does not exist; reader greps and finds nothing.

**Why it happens:** Older planning prose and several previous Phase context files use both spellings. Pre-existing knowledge biases toward "scanners".

**How to avoid:** The package is `quirk/scanner/` (singular). Discovery is a separate `quirk/discovery/` package. Use the Code Map above as the authoritative reference. Doc-writer should grep their own draft for `quirk/scanners` and replace.

**Warning signs:** any path in the new docs that includes the substring `quirk/scanners/` or `from quirk.scanners`.

### Pitfall 2: Treating `quirk compliance status` as a registered subcommand

**What goes wrong:** Architecture doc shows a clean argparse subparser tree with `compliance` as a child of the main parser. Reality is different.

**Why it happens:** Phase 49 D-05 implementation chose argv-sniffing in `run_scan.py:223–244` rather than restructuring the argparse hierarchy.

**How to avoid:** For the operator's guide, describe the **user-facing command** (`quirk compliance status`, `quirk compliance status --format json`), not the implementation. The architect-facing architecture doc *may* note that subcommand routing is intercepted in `run_scan.py:main()` for the `compliance` and `serve` paths, but should not draw a misleading subparser tree.

**Warning signs:** doc text that says "registered as a subparser" or "added via `subparsers.add_parser('compliance')` in the main argparse" — both false.

### Pitfall 3: Duplicating content from existing docs

**What goes wrong:** operators-guide.md ends up with full install instructions copied from `installation.md`; a future installation change requires two-place edits, drift accumulates, the gating doc lies.

**Why it happens:** "Hybrid narrative + links" (D-01) feels too sparse to a writer.

**How to avoid:** The rule per D-01 is **short canonical inline section + "See also: docs/<file>.md"**. Inline section gives a 2–4 sentence orientation; deep details go in the linked doc. If a writer feels the inline section is too short, the answer is "good — link instead." Net-new content goes inline (Troubleshooting, per-scanner protocol subsections, Compliance Maintenance runbook). Existing-doc topics get short orientation + link.

**Warning signs:** any inline section in operators-guide.md longer than ~10 sentences for a topic that already has a dedicated docs/* file.

### Pitfall 4: Vault sync via `obsidian CLI content=`

**What goes wrong:** The `obsidian CLI` skill receives a `content="..."` argument that exceeds the shell expansion limit; the call fails or truncates silently; the vault note is wrong.

**Why it happens:** It's the documented "small files" path in CLAUDE.md; both new docs are large enough to hit the limit.

**How to avoid:** Use the CLAUDE.md filesystem pattern verbatim:

```bash
printf "---\nproject: QU.I.R.K.\ntype: reference\nstatus: active\nsource: docs/architecture.md\nupdated: 2026-05-XX\n---\n\n" > /tmp/arch_vault.md
cat docs/architecture.md >> /tmp/arch_vault.md
cp /tmp/arch_vault.md "/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Reference/Architecture.md"
```

Same pattern for `Operators-Guide.md`. The `_QUIRK-Hub.md` MOC update *is* small and *can* use the obsidian CLI append — but the two new Reference notes themselves cannot.

**Warning signs:** plan task that calls `obsidian vault="Digs" create name="Architecture" path="..." content="<long string>"` for either of the two new docs.

### Pitfall 5: Stale `lab.sh ALL_PROFILES` references in architecture doc

**What goes wrong:** Doc shows a hardcoded `ALL_PROFILES=(...)` list — but lab.sh actually uses runtime `_derive_all_profiles()` (Phase 40 D-14) that parses docker-compose.yml. The doc-stated invariant ("update ALL_PROFILES when adding a profile") is out of date.

**Why it happens:** Pre-Phase-40 prose; older CLAUDE.md content; pre-existing knowledge.

**How to avoid:** When architecture doc covers chaos lab, state the **current** invariant: "lab.sh derives the profile list at runtime from docker-compose.yml; new profiles are auto-discovered. The CLAUDE.md `lab.sh` rule still applies — README.md and `expected_results_v4.md` must be updated when profiles change."

**Warning signs:** any inline reference to `ALL_PROFILES` as a hardcoded list in lab.sh.

### Pitfall 6: Using deprecated PQC terminology in architecture/operators docs

**What goes wrong:** Architecture doc uses "Kyber" or "Dilithium" or "when standards are adopted." Phase 48 CONTEXT-04 grep gate (`tests/test_pqc_terminology_gate.py`) is path-scoped to `risk_engine.py` and `routes/scan.py`, so it would NOT catch a regression in `docs/architecture.md` — but the user-facing docs are exactly where stale terms damage credibility most.

**Why it happens:** Pre-existing knowledge from training data biases to the legacy names.

**How to avoid:** Use **FIPS 203 (ML-KEM)**, **FIPS 204 (ML-DSA)**, **FIPS 205 (SLH-DSA)** consistently. Cite **NIST IR 8547** for deprecation deadlines (RSA/ECC deprecated 2030; disallowed 2035). Doc-writer should grep new drafts for "Kyber", "Dilithium", "when standards are adopted" before commit.

**Warning signs:** any of those three substrings in either new doc.

## Code Examples

### Vault sync invocation pattern (CLAUDE.md verbatim)

```bash
# Architecture vault sync
printf "---\nproject: QU.I.R.K.\ntype: reference\nstatus: active\nsource: docs/architecture.md\nupdated: 2026-05-05\n---\n\n" > /tmp/arch_vault.md
cat docs/architecture.md >> /tmp/arch_vault.md
cp /tmp/arch_vault.md "/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Reference/Architecture.md"

# Operators-Guide vault sync
printf "---\nproject: QU.I.R.K.\ntype: reference\nstatus: active\nsource: docs/operators-guide.md\nupdated: 2026-05-05\n---\n\n" > /tmp/ops_vault.md
cat docs/operators-guide.md >> /tmp/ops_vault.md
cp /tmp/ops_vault.md "/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Reference/Operators-Guide.md"
```

[Source: CLAUDE.md §"Mandatory Phase Completion Steps" — UAT-SERIES.md sync code block, generalized]

### gsd-tools commit pattern (CLAUDE.md mandate)

```bash
node "/Users/digs/.claude/get-shit-done/bin/gsd-tools.cjs" commit "docs(phase-50): add architecture.md" --files docs/architecture.md
node "/Users/digs/.claude/get-shit-done/bin/gsd-tools.cjs" commit "docs(phase-50): add operators-guide.md" --files docs/operators-guide.md
node "/Users/digs/.claude/get-shit-done/bin/gsd-tools.cjs" commit "docs(phase-50): sync architecture + operators-guide to vault" --files <vault paths absolute>
node "/Users/digs/.claude/get-shit-done/bin/gsd-tools.cjs" commit "docs(phase-50): update UAT-SERIES.md" --files docs/UAT-SERIES.md
```

Files outside the repo (vault paths) cannot be passed to `--files`; the vault sync commit
only commits any in-repo changes (UAT-SERIES sync timestamp). Vault files live in
`/Users/digs/vaults/Digs/...` which is **not** in the repo and not committed.

### Compliance status CLI smoke (substrate for operator-facing example)

```bash
# Text format (default)
quirk compliance status
# Framework            Version        Last Verified  Source URL
# --------------------------------------------------------------------------------
# FIPS 140-3           Final          2026-05-05     https://csrc.nist.gov/pubs/fips/140-3/final
# HIPAA 45 CFR         §164.312       2026-05-05     https://www.ecfr.gov/current/title-45/...
# PCI-DSS 4.0.1        4.0.1          2026-05-05     https://docs-prv.pcisecuritystandards.org/...

# JSON format (machine-readable; useful in CI)
quirk compliance status --format json
```

[Source: `quirk/compliance/__init__.py::status_report` lines 207–234, run_scan.py:223–244]

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `quirk/scanners/` (plural) | `quirk/scanner/` (singular) | Pre-v4.0 (well before this milestone) | Doc references the wrong path break grep |
| Hardcoded `ALL_PROFILES` in lab.sh | Runtime `_derive_all_profiles()` reads docker-compose.yml | Phase 40 (v4.5) | Architecture doc must not show ALL_PROFILES as hardcoded list |
| Hand-pinned scanner timeouts | `TimeoutsCfg` + `RetryCfg` sub-tables on `ScanCfg` | Phase 41 (v4.5) | docs/timeout-retry-audit.md is the canonical reference; operators-guide cites |
| Kyber / Dilithium / "when standards are adopted" prose | FIPS 203/204/205 + NIST IR 8547 | Phase 48 (v4.6) | New docs must use new terminology; CI grep gate covers source code but not docs |
| Compliance refs imported in renderers | Eager `_normalize_for_compliance` attaches `compliance:` to finding dict at `_build_finding()` | Phase 49 (v4.6) | Architecture doc data-flow diagram must show eager attachment, not late join |
| `[email]` / `[broker]` / `[kafka]` flat sub-extras | `[motion]` umbrella extra | Phase 37 (v4.4) | per-scanner table optional-deps column says `quirk[motion]` for email + broker scanners |

**Deprecated/outdated:**

- "Kyber", "Dilithium" — replaced by ML-KEM (FIPS 203), ML-DSA (FIPS 204), SLH-DSA (FIPS 205).
- "when standards are adopted" — replaced by NIST IR 8547 deprecation deadline language.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (Python 3.11+, no version pin found in pyproject) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (assumed — confirmed via existing `tests/` fleet runs cleanly) |
| Quick run command | `pytest -m 'not slow' tests/ -x` |
| Full suite command | `pytest tests/` |

### Phase Requirements → Test Map

For a docs-only phase, automated test coverage is **file-presence + section-content**
greps. Rich behavioral assertions don't apply (no new code). UAT-SERIES.md is the gating
human-verification doc per CLAUDE.md.

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DOCS-01 | `docs/architecture.md` exists and contains required sections (scanner phases, data flow, SQLite schema, dashboard, CBOM pipeline) | smoke | `test -f docs/architecture.md && grep -q "Scanner" docs/architecture.md && grep -q "SQLite" docs/architecture.md && grep -q "CBOM" docs/architecture.md && grep -q "Dashboard" docs/architecture.md` | Wave 0 |
| DOCS-02 | `docs/operators-guide.md` exists and contains required sections (Install, Configure, Scan, Troubleshoot, Per-scanner reference) | smoke | similar grep harness | Wave 0 |
| DOCS-03 | Both vault notes exist with required frontmatter | smoke | `test -f /Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Reference/Architecture.md && head -1 ... | grep -q "^---"` plus frontmatter line greps | Wave 0 (manual) |
| DOCS-04 | operators-guide.md "Compliance Map Maintenance" section names the three source URLs + cites `quirk compliance status` + cites `tests/test_compliance_freshness.py` | grep | `grep -q "pcisecuritystandards.org" docs/operators-guide.md && grep -q "ecfr.gov" docs/operators-guide.md && grep -q "csrc.nist.gov" docs/operators-guide.md && grep -q "quirk compliance status" docs/operators-guide.md && grep -q "tests/test_compliance_freshness.py" docs/operators-guide.md` | Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest -m 'not slow' tests/ -x` (existing test fleet — must remain green; no test changes from this phase)
- **Per wave merge:** full suite via `pytest tests/`
- **Phase gate:** UAT-50-NN block in `docs/UAT-SERIES.md` exercised manually before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] (Optional) `tests/test_phase50_docs_presence.py` — file-presence + section-grep harness for DOCS-01..04. **Recommended but not required** — UAT-50-NN block in UAT-SERIES.md provides the gating verification. Planner discretion: add this if they want CI-level enforcement; skip if they want pure docs phase.
- No framework install needed — pytest already in use.
- No new test infrastructure — no shared fixtures required.

## Security Domain

This is a docs-only phase. No code paths change; no new attack surface; no new auth/session/access-control logic. ASVS categories largely don't apply.

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | no | — (no input parsing changes) |
| V6 Cryptography | no | — (docs describe crypto but don't introduce it) |
| V7 Error Handling / Logging | no | — |
| V14 Configuration | partial | docs/operators-guide.md should NOT print real credentials in any example; use placeholders only (e.g., `vault_token: <set via VAULT_TOKEN env>`) |

### Threat Patterns for docs

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Doc example contains a real credential / IP / hostname from author's environment | Information Disclosure | Use only RFC 5737 documentation IPs (`192.0.2.0/24`, `198.51.100.0/24`, `203.0.113.0/24`), `example.com` / `example.org` hostnames, `<placeholder>` for tokens/passwords |
| Doc example shows a wide-open config (no password, IAM `*:*`) without "do not ship to prod" warning | Tampering | Annotate any minimum-permissions example with explicit "for development only — production should use least-privilege IAM" |
| Compliance runbook example accidentally edits live `COMPLIANCE_MAP` in the example block | Tampering | Worked example in §Compliance Map Maintenance must show diff-style edits, not actual file writes |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | pytest config lives in `pyproject.toml` `[tool.pytest.ini_options]` | Validation Architecture > Test Framework | LOW — pytest invocation works regardless; only matters if planner wants to add a new mark |
| A2 | Phase 49 SUMMARY.md exists per plan path `49-SUMMARY.md` | (referenced from CONTEXT.md canonical_refs only) | LOW — if it doesn't exist, doc-writer falls back to `quirk/compliance/__init__.py` docstring + Phase 49 CONTEXT.md, which are sufficient |
| A3 | The frontmatter `updated:` field should use `2026-05-05` (today) when the docs land; if execution is delayed, the actual landing date should be used | Vault sync | LOW — purely cosmetic; CLAUDE.md says `updated: <YYYY-MM-DD>` |

All other claims in this research were verified against the live tree (filesystem walk,
file reads, grep) on 2026-05-05.

## Open Questions

1. **Should architecture.md include a "credential storage" matrix?**
   - What we know: Cloud creds come from existing OS-level credential chains (AWS profile, Azure DefaultAzureCredential, GCP ADC, kubeconfig, VAULT_TOKEN env var). QUIRK never persists them.
   - What's unclear: Whether D-03 ("trust boundaries / credential handling") expects a full per-connector credential-source table or a single paragraph suffices.
   - Recommendation: include a small table (Connector | Credential source | Where stored). Cheap to write; high value for an enterprise architect doing a pre-deploy security review.

2. **Should operators-guide.md cover the `quirk init` flow explicitly?**
   - What we know: `cli/init_cmd.py` generates `config.yaml` from `quirk/config_template.yaml`; existing docs/installation.md or docs/getting-started.md may or may not document it (head check showed neither leads with it).
   - What's unclear: D-02 lists the four troubleshooting areas but `quirk init` could land in either Configure or Scan section.
   - Recommendation: short "Generate a starter config" subsection under Configure, linking to docs/configuration.md.

3. **Should `tests/test_phase50_docs_presence.py` be created (Wave 0 Gaps item)?**
   - What we know: UAT-50-NN block in UAT-SERIES.md is the gating mechanism per CLAUDE.md mandate.
   - What's unclear: whether a low-cost automated grep-harness would be valuable or noise.
   - Recommendation: planner discretion. Default: skip — UAT block is sufficient; adding a pytest harness for grep-style assertions is overkill for a docs phase.

4. **Should the v4.6.0 CHANGELOG.md / docs/release-notes/4.6.0.md be authored in this phase?**
   - What we know: Phase 50 is the last v4.6 phase. Phase 37 (v4.4 close) authored both `CHANGELOG.md` and `docs/release-notes/4.4.0.md` per STATE.md history.
   - What's unclear: whether v4.6 release-notes are a Phase 50 task or a separate milestone-close phase.
   - Recommendation: out of scope for Phase 50 (CONTEXT.md does not name it). Surface as a Deferred Item at phase close → milestone-close phase.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Markdown rendering (GitHub) | `docs/architecture.md`, `docs/operators-guide.md` | yes | — | — |
| Mermaid plugin (Obsidian) | Mermaid blocks render in vault | yes (assumed enabled) | — | Code blocks still display as text if plugin disabled — graceful degradation |
| `printf` / `cat` / `cp` | Vault sync filesystem pattern | yes | POSIX | — |
| `gsd-tools.cjs` | All commits per CLAUDE.md mandate | yes | (existing project tooling) | — |
| Vault filesystem path `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Reference/` | Vault sync | yes | — | If absent, mkdir parent then cp |
| pytest + existing test fleet | Pre-merge sanity that no docs-phase change broke anything (paranoia) | yes | — | — |

**No external blockers.** Phase 50 is purely a markdown authoring + filesystem operation
phase; the only software dependency outside the repo is the Obsidian app reading the
vault — and that's read-only consumer-side.

## Sources

### Primary (HIGH confidence)

- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/CLAUDE.md` — Mandatory Phase Completion Steps, Obsidian Vault Integration, Sync Workflows, Frontmatter Standards
- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/.planning/phases/50-enterprise-documentation/50-CONTEXT.md` — D-01..D-09 locked decisions
- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/.planning/REQUIREMENTS.md` — DOCS-01..04
- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/.planning/ROADMAP.md` lines 981–989 — Phase 50 success criteria
- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/quirk/compliance/__init__.py` (243 LOC, full read) — module surface for Phase 49 compliance runbook citations
- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/run_scan.py` lines 82–244 + scanner-phase grep — CLI entry-point + compliance subcommand wiring
- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/quirk/config_template.yaml` (full read) — config flag inventory
- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/quirk/models.py` (92 LOC) — single-table SQLite schema source
- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/quirk/db.py` `_ensure_*_columns` migration grep
- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/quirk/cbom/builder.py` + `classifier.py` + `writer.py` headers — CBOM pipeline entry points
- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/quirk/reports/writer.py` lines 1–35 — reports writer imports + version constants
- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/quirk/dashboard/server.py` + `api/app.py` + `routes/scan.py` — dashboard architecture
- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/src/dashboard/package.json` — React 19 + Vite 8 confirmation
- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/pyproject.toml` `[project.optional-dependencies]` — extras matrix
- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/docs/UAT-SERIES.md` (header + tail) — UAT block format
- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/docs/` — file inventory + first-line summaries
- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/.planning/STATE.md` — milestone state + accumulated decisions

### Secondary (MEDIUM confidence)

- `tests/test_compliance_freshness.py` and four sibling test files — existence verified by `ls`; gate semantics inferred from filename + COMPLY-NN requirement mapping.

### Tertiary (LOW confidence)

- (none — all factual claims verified against the working tree)

## Metadata

**Confidence breakdown:**

- Code Map / Module Inventory: HIGH — direct filesystem walk + reads on 2026-05-05
- Scanner Inventory table: HIGH — directory listing + COMPLIANCE_MAP keys (Phase 49 title-join gate guarantees runtime accuracy)
- Existing Docs Inventory: HIGH — read of every doc head
- Phase 49 Compliance Surface: HIGH — full `quirk/compliance/__init__.py` read + run_scan.py grep
- Config Flag Inventory: HIGH — full `config_template.yaml` read
- Architecture diagram substrate: HIGH — every node and edge cited to a verified source
- Pitfalls: HIGH — drawn from actual prior-phase decisions in STATE.md
- Validation Architecture: MEDIUM — pytest framework confirmed but exact `[tool.pytest.ini_options]` not re-read (A1)

**Research date:** 2026-05-05
**Valid until:** 2026-06-04 (30 days; codebase is in active v4.6 milestone — re-verify scanner inventory if any new scanner lands before phase execution)
