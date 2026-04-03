# Roadmap: QU.I.R.K.

## Overview

QU.I.R.K. (Quantum Infrastructure Readiness Kit) starts from a solid v3.9 scanner core and
evolves into a consulting-grade cryptographic inventory platform. The journey: fix what exists
and deepen scanner accuracy (Phase 1), build the CBOM pipeline that is the product's key
differentiator (Phase 2), expand scanner coverage to every cryptographic surface a client
network exposes (Phase 3), validate every scanner against purpose-built chaos lab targets
(Phase 4), expose results through a polished web dashboard with PDF delivery (Phase 5),
document the tool well enough that a consultant with no prior exposure can hand a client
a defensible report within two hours of installation (Phase 6), then finish with professional
branding and packaging that makes it look like a product worth paying for (Phase 7).

## Phases

**Phase Numbering:**
- Integer phases (1-7): Planned milestone work
- Decimal phases (e.g., 2.1): Urgent insertions via `/gsd:insert-phase`

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Foundation Fixes** - Consolidate scoring, fix data bugs, rename to QU.I.R.K., upgrade SSH and TLS scanners
- [x] **Phase 2: CBOM Pipeline** - Integrate cyclonedx, map algorithms, enrich with NIST PQC classification, produce CBOM artifacts (completed 2026-03-29)
- [x] **Phase 3: Scanner Coverage** - Add JWT/API, container/binary, source code, and cloud connectors (AWS + Azure) (completed 2026-03-29)
- [x] **Phase 4: Chaos Lab Expansion** - Add jwt, registry, source, storage, ssh-weak, and ldaps lab profiles (completed 2026-03-30)
- [x] **Phase 5: Web Dashboard** - FastAPI + React dashboard with findings viewer, CBOM viewer, and PDF report export (completed 2026-03-31)
- [x] **Phase 6: Documentation** - Getting Started, installation, configuration, connector guides, report and CBOM interpretation (completed 2026-03-31)
- [x] **Phase 7: Polish and Packaging** - Visual identity, CLI UX, professional report templates, pip-installable distribution (completed 2026-04-01)

## Phase Details

### Phase 1: Foundation Fixes
**Goal**: The scanner codebase is correct, consistent, and renamed — producing accurate data with deep TLS and SSH algorithm enumeration
**Depends on**: Nothing (first phase)
**Requirements**: CORE-01, CORE-02, CORE-03, CORE-04, SCAN-01, SCAN-02
**Success Criteria** (what must be TRUE):
  1. A scan run produces one score, sourced from one authoritative code path, with no silent override from a secondary scoring module
  2. Certificate public key algorithm appears correctly in all scan output (JSON, SQLite, Markdown report) for every cert encountered
  3. All CLI commands, output strings, config keys, file paths, and module names read "quirk" or "QU.I.R.K." — zero remaining "QuRisk" references
  4. Running a 100-host SSH scan completes meaningfully faster than sequential and does not drop results
  5. A TLS scan against a target returns cipher suite details, certificate chain, and protocol version sourced from sslyze
  6. An SSH scan returns KEX algorithms, host key types, and MAC algorithms — not just the banner string
**Plans:** 4 plans
Plans:
- [ ] 01-PLAN-scoring-fixes.md — Consolidate scoring to single intelligence path, fix cert_pubkey_alg extraction bug
- [ ] 02-PLAN-ssh-scanner.md — Replace sequential SSH scanner with threaded ssh-audit integration
- [ ] 03-PLAN-sslyze-integration.md — Integrate sslyze as primary TLS scanner with existing code as fallback
- [ ] 04-PLAN-package-rename.md — Rename qcscan to quirk across codebase, create pyproject.toml

### Phase 2: CBOM Pipeline
**Goal**: Every scan run produces a standards-compliant Cryptographic Bill of Materials as a first-class output artifact
**Depends on**: Phase 1
**Requirements**: CBOM-01, CBOM-02, CBOM-03, CBOM-04
**Success Criteria** (what must be TRUE):
  1. Running a scan produces a CBOM JSON file and a CBOM XML file in the output directory alongside the existing Markdown report
  2. Every algorithm found by any scanner (TLS, SSH, cert key type) appears as a named component in the CBOM
  3. Each CBOM component carries a quantum-safety classification (quantum-safe / quantum-vulnerable / hybrid / unknown) sourced from the NIST PQC catalog
  4. The CBOM validates against the CycloneDX 1.4+ schema without errors
**Plans:** 3/3 plans complete
Plans:
- [x] 02-01-PLAN.md — Algorithm classifier with NIST PQC quantum-safety lookup table (CBOM-02, CBOM-03)
- [x] 02-02-PLAN.md — CBOM builder converting CryptoEndpoints to deduplicated CycloneDX Bom (CBOM-01, CBOM-02)
- [x] 02-03-PLAN.md — CBOM writer (JSON+XML serialization) and integration into write_reports() (CBOM-01, CBOM-04)

### Phase 3: Scanner Coverage
**Goal**: QU.I.R.K. discovers cryptographic material across every major attack surface — APIs, containers, source code, and cloud key management
**Depends on**: Phase 2
**Requirements**: SCAN-03, SCAN-04, SCAN-05, SCAN-06, SCAN-07
**Success Criteria** (what must be TRUE):
  1. A scan of a JWT-issuing API endpoint returns the signing algorithm, key size, and JWKS key IDs — and these appear in the CBOM
  2. Running the container scanner against a Docker image returns the crypto libraries embedded in that image with versions
  3. Running the source code scanner against a Git repository returns algorithm usage findings with file and line references
  4. The AWS connector returns ACM certificates, KMS key specs, and CloudFront/ELB TLS policies for a configured AWS account
  5. The Azure connector returns Key Vault key types and App Gateway TLS policies for a configured Azure subscription
**Plans:** 4/4 plans complete
Plans:
- [x] 03-01-PLAN.md — Foundation: schema columns, config extension, dependencies, test scaffolds (SCAN-03..07)
- [x] 03-02-PLAN.md — JWT scanner, container scanner, source code scanner (SCAN-03, SCAN-04, SCAN-05)
- [x] 03-03-PLAN.md — AWS connector, Azure connector (SCAN-06, SCAN-07)
- [x] 03-04-PLAN.md — CBOM classifier/builder extension, run_scan.py integration (all)

### Phase 4: Chaos Lab Expansion
**Goal**: Every new scanner type has a purpose-built, Docker-based target that produces known, reproducible findings for validation
**Depends on**: Phase 3
**Requirements**: LAB-01, LAB-02, LAB-03, LAB-04, LAB-05, LAB-06
**Success Criteria** (what must be TRUE):
  1. `docker compose --profile jwt up` starts 4 JWT services and a JWKS endpoint; the JWT scanner finds at least 2 weak-algorithm findings
  2. `docker compose --profile registry up` starts a Docker Registry with vulnerable test images; the container scanner detects embedded crypto library issues
  3. `docker compose --profile source up` starts Gitea with seeded repos; the source code scanner returns at least one algorithm finding per seeded anti-pattern
  4. `docker compose --profile storage up` starts LocalStack, Vault, and postgres-encrypted; the AWS connector and storage targets respond to scan queries
  5. The ssh-weak service starts and the SSH scanner returns weak KEX/hostkey/MAC findings against it
  6. The ldaps service starts on port 636 and sslyze returns TLS findings against it
**Plans:** 5/5 plans complete
Plans:
- [x] 04-01-PLAN.md — jwt profile: 4 FastAPI JWT microservices (RS256, HS256-weak, RSA1024, alg:none) on ports 20001-20004 (LAB-01)
- [x] 04-02-PLAN.md — registry profile: Docker Registry v2 + 3 test images with old crypto libs + seed (LAB-02)
- [x] 04-03-PLAN.md — source profile: Gitea + seed script with 4 anti-pattern categories across 3 repos (LAB-03)
- [x] 04-04-PLAN.md — storage profile: LocalStack KMS + HashiCorp Vault + postgres-pgcrypto + seed scripts (LAB-04)
- [x] 04-05-PLAN.md — ssh-weak + ldaps profiles + expected_results_v3.md update (LAB-05, LAB-06)

### Phase 5: Web Dashboard
**Goal**: Scan results are accessible through a local web dashboard that produces a professional PDF report a consultant can hand directly to a client
**Depends on**: Phase 2
**Requirements**: UI-01, UI-02, UI-03, UI-04
**Success Criteria** (what must be TRUE):
  1. Running `quirk serve` starts a local web server and the dashboard loads in a browser without additional setup
  2. The dashboard displays an executive summary with quantum-readiness score gauges and severity breakdown for the most recent scan
  3. A findings table, certificate inventory, and CBOM viewer are all navigable from the dashboard
  4. Clicking "Export PDF" produces a PDF file that renders correctly and contains the full scan summary, findings, and CBOM reference
**Plans**: 6 plans
Plans:
- [x] 05-01-PLAN.md — Wave 0 test scaffolds and backend Python dependencies
- [x] 05-02-PLAN.md — FastAPI backend skeleton, health endpoint, Pydantic schemas, quirk serve CLI
- [x] 05-03-PLAN.md — React frontend scaffold: Vite + shadcn/ui, ThemeProvider, Sidebar, TypeScript types
- [x] 05-04-PLAN.md — GET /api/scan/latest endpoint, Executive, Findings, and Certificates pages
- [x] 05-05-PLAN.md — CBOM Viewer (Table + Graph tabs), Migration Roadmap Cytoscape DAG, App.tsx wiring
- [x] 05-06-PLAN.md — PDF export backend (Playwright), /print React page, App.tsx /print route
**UI hint**: yes

### Phase 6: Documentation
**Goal**: A consultant with no prior QU.I.R.K. experience can install the tool, run a scan, and explain the report to a client — entirely from the documentation
**Depends on**: Phase 5
**Requirements**: DOC-01, DOC-02, DOC-03, DOC-04, DOC-05, DOC-06, DOC-07
**Success Criteria** (what must be TRUE):
  1. Following the Getting Started guide from a clean macOS or Linux machine produces a completed scan in under 10 minutes
  2. The installation guide covers system requirements, Python version, and OS-specific steps for macOS, Linux, and Windows WSL
  3. The connector guides include copy-pasteable least-privilege IAM policy (AWS) and RBAC role definition (Azure)
  4. The report interpretation guide maps every score label and severity tier to a plain-English client explanation
  5. The CBOM guide explains what a CBOM is, how it was produced, and how to cite it as compliance evidence
  6. The chaos lab operator guide documents all profiles including the six added in Phase 4
**Plans**: 6 plans
Plans:
- [x] 06-01-PLAN.md — README.md replacement + Getting Started guide + Installation guide (DOC-01, DOC-02)
- [x] 06-02-PLAN.md — Configuration reference: all config.yaml keys + CLI flags (DOC-03)
- [x] 06-03-PLAN.md — Connector guides: AWS, Azure, Docker, Git with credential templates (DOC-04)
- [x] 06-04-PLAN.md — Report interpretation guide: score tables + severity tiers + Client Conversation sideboxes (DOC-05)
- [x] 06-05-PLAN.md — CBOM guide: what/how/cite — compliance evidence language (DOC-06)
- [x] 06-06-PLAN.md — Chaos lab operator guide: all 10 profiles + port matrix + lab README update (DOC-07)

### Phase 7: Polish and Packaging
**Goal**: QU.I.R.K. is installable in one command, presents a coherent visual identity, and produces reports that look like a commercial security product
**Depends on**: Phase 6
**Requirements**: BRAND-01, BRAND-02, BRAND-03, BRAND-04
**Success Criteria** (what must be TRUE):
  1. `pip install quirk` (or equivalent single command) produces a working installation on macOS and Linux
  2. All CLI output uses consistent formatting with rich progress indicators; `quirk --version` returns the current version
  3. HTML and PDF reports use the QU.I.R.K. visual identity (color palette, logo mark, report headers) — indistinguishable in quality from a commercial tool
  4. A new user who has never seen the tool can reach a completed, exportable scan from zero within 10 minutes of running the install command
**Plans:** 5/5 plans complete
Plans:
- [x] 07-01-PLAN.md — Wave 0: test scaffolds, Jinja2 + rich dependency installation
- [x] 07-02-PLAN.md — CLI UX overhaul: --version, startup banner, rich scan summary (BRAND-02)
- [x] 07-03-PLAN.md — HTML/PDF report templates: Jinja2 renderer + write_reports() wiring (BRAND-03)
- [x] 07-04-PLAN.md — Dashboard branding pass: favicon, page title, sidebar wordmark (BRAND-01)
- [x] 07-05-PLAN.md — Packaging: version 4.0.0, quirk init, GitHub install path (BRAND-04)

## Backlog (Future Enhancements)

Ideas captured during planning — not in scope for v1, but not lost.

| ID | Enhancement | Origin | Notes |
|----|-------------|--------|-------|
| BACK-01 | Dashboard UI config panel for algorithm vulnerability thresholds | Phase 5 discuss | Allow users to override quantum-safety classifications per algorithm (e.g., mark RSA-4096 as "org-approved") without editing config.yaml. v1 ships config.yaml overrides only; this is the UI surface for the same feature. Target: v2 or Phase 7 polish. |
| BACK-02 | Multi-scan navigation in dashboard | Phase 5 discuss | Scan selector dropdown to browse and compare historical scan sessions. API is shaped for this (latest scan returns scan_id, future endpoint accepts ?scan_id= param). Target: v2. |
| BACK-03 | Severity heatmap visualization | Phase 5 discuss | Grid of systems × severity level — dense overview for large scans, lets a consultant instantly spot where exposure is concentrated. Candidate for Phase 7 polish or v2 dashboard expansion. |
| BACK-04 | Light/dark mode toggle for web dashboard | Phase 5 post-UI-SPEC | User-selectable theme. UI-SPEC locks dark-first (Zinc 950/900); Phase 7 branding layers cleanly. Light mode would need a parallel token set. Capture before Phase 5 planning — can be incorporated into Phase 5 or deferred to Phase 7 polish. Phase dir: `.planning/phases/999.1-light-dark-mode-toggle-for-the-web-dashboard-ui/` |
| BACK-05 | PDF report formatting improvements | Phase 5 UAT | Current output is functional but needs significant work on layout, typography, and information hierarchy. Items: cover page branding, executive summary formatting, findings table pagination, CBOM section with visual elements, proper page breaks, headers/footers with scan metadata. Phase dir: `.planning/phases/999.2-pdf-report-formatting-improvements/` |
| BACK-06 | CBOM graph node colors by system type | Phase 5 UAT | System nodes currently all grey. Color by endpoint type: TLS/HTTPS (blue), SSH/device (teal), API/service (green), certificate (purple). Requires backend change to include protocol/type in CBOM source_systems data, plus frontend color mapping. Phase dir: `.planning/phases/999.3-cbom-graph-node-colors-by-system-type/` |
| BACK-07 | Migration Roadmap visual overhaul | Phase 5 UAT | Current DAG is functional but lacks substance for a client-facing deliverable. Needs a comprehensive rethink across several dimensions: (1) **Information density** — nodes show title only; should surface priority score, effort estimate, risk reduction impact, and blocking dependencies inline or on hover; (2) **Visual structure** — flat DAG doesn't convey phases well; consider horizontal swimlane bands (NOW / NEXT / LATER rows) so temporal grouping is immediately readable without clicking; (3) **Actionability** — each node should answer "what do I do, who owns it, what does it unblock"; owner role tags, dependency chains, and estimated impact (e.g., "reduces CRITICAL findings by 2") would make this consultant-ready; (4) **Color scheme** — extend beyond timeframe coloring to also encode risk type (quantum-vuln migration vs. hygiene vs. compliance) or effort level; (5) **Edge semantics** — current edges are structural only; should distinguish "blocks" vs "enables" vs "parallel" relationships; (6) **Interactivity** — click should reveal a rich detail card: why this item, what it fixes, what it enables, who should own it, and a suggested acceptance criterion. Phase dir: `.planning/phases/999.4-roadmap-visual-color-scheme-improvements/` |
| BACK-08 | Full narrative report onboarding guide | Phase 6 discuss | Prose walkthrough of a complete engagement from first install through scan to client report delivery. Designed as a training document for bringing new team members or junior consultants up to speed — not a quick reference, a story. Covers: what QU.I.R.K. is measuring and why, how to run a first scan, how to interpret every section of the report in context, how to prepare a client conversation, and how to use the CBOM for compliance evidence. Origin: user note during Phase 6 context discussion: "would be a good training tool for bringing new team members into the project." |
| BACK-09 | Active REST API fuzzing for crypto posture | API scanning gap | QUIRK currently inspects JWKS endpoints passively. Add active probing: test API endpoints for weak cipher negotiation, detect deprecated TLS versions on REST APIs, enumerate authentication schemes (Basic, Bearer, API key in header/query), and flag endpoints that transmit credentials over non-TLS transports. Phase dir: `.planning/phases/999.5-active-rest-api-fuzzing/` |
| BACK-10 | OpenAPI/Swagger spec analysis | API scanning gap | Parse OpenAPI 3.x / Swagger 2.0 spec files (local or fetched from /openapi.json) to enumerate security schemes, identify endpoints that declare no authentication, and flag algorithms referenced in securitySchemes (e.g., RS256, HS256 JWTs). Produces CBOM components from spec-declared algorithms even before a live scan. Phase dir: `.planning/phases/999.6-openapi-swagger-spec-analysis/` |
| BACK-11 | Bearer token interception and analysis | API scanning gap | Capture and decode live Bearer tokens observed during a scan (TLS-terminated traffic via MITM proxy or from provided sample tokens) to extract signing algorithm, key size, expiry policy, and claim structure. Flag tokens signed with quantum-vulnerable algorithms (RS256, ES256) or with no expiry. Complements the passive JWKS scanner with evidence from tokens actually in use. Phase dir: `.planning/phases/999.7-bearer-token-interception/` |
| BACK-12 | Database encryption detection | Data at rest gap | Probe PostgreSQL `pg_hba.conf` SSL mode, MySQL/MariaDB SSL status, RDS encryption-at-rest flag, and MSSQL TDE (Transparent Data Encryption). Implementable via SSH + remote command or native DB connection probe. Every enterprise audit asks whether databases are encrypted; QUIRK currently has no answer. Phase dir: `.planning/phases/999.8-database-encryption-detection/` |
| BACK-13 | S3 / Blob storage encryption policy audit | Data at rest gap | AWS connector scans KMS keys but never checks whether S3 buckets use them (SSE-S3, SSE-KMS, or no encryption). Same gap for Azure Blob (SSE with CMK vs platform key) and GCS. Single API call per bucket; significant finding generator for cloud-heavy clients. Phase dir: `.planning/phases/999.9-s3-blob-storage-encryption-policy-audit/` |
| BACK-14 | GCP connector | Cloud coverage gap | Google Cloud Platform is the third major cloud and is entirely absent. Scope: Cloud KMS key specs, Cloud SQL TLS config, GCS bucket encryption policies, Secret Manager encryption. Same pattern as the existing AWS and Azure connectors. Phase dir: `.planning/phases/999.10-gcp-connector/` |
| BACK-15 | Kubernetes secrets encryption at rest | Data at rest gap | Determine whether etcd encryption is enabled and which provider is configured (aescbc, aesgcm, secretbox, KMS). Checkable via kubeconfig + API server flags or encryption config manifest inspection. Critical finding for cloud-native clients. Phase dir: `.planning/phases/999.11-kubernetes-secrets-encryption-at-rest/` |
| BACK-16 | Email protocol scanning (SMTP/STARTTLS/IMAP/POP3) | Data in motion gap | Port 25/465/587 STARTTLS is one of the most commonly misconfigured crypto surfaces in enterprise — many mail servers still negotiate TLS 1.0 or accept plaintext. sslyze already handles deep TLS scanning; this adds SMTP/IMAP/POP3 protocol handlers. Findings map directly into the existing scoring model. Phase dir: `.planning/phases/999.12-email-protocol-scanning-smtp-starttls/` |
| BACK-17 | Message broker TLS (Kafka, RabbitMQ, Redis, AMQP) | Data in motion gap | Modern infrastructure commonly deploys Kafka (9092/9093), RabbitMQ (5672/5671), and Redis (6379/6380) with plaintext or misconfigured TLS. Port-based heuristic with TLS negotiation attempt would surface a class of findings most scanners miss. Phase dir: `.planning/phases/999.13-message-broker-tls-kafka-rabbitmq-redis/` |
| BACK-18 | Kerberos encryption type enumeration | Identity crypto gap | Active Directory environments use RC4 (arcfour-hmac) for Kerberos by default — quantum-vulnerable and still the default in millions of enterprise environments. AS-REQ probing enumerates supported encryption types (DES, RC4, AES128, AES256) without credentials. Highest quantum-risk surface for most enterprise clients and currently invisible to QUIRK. Phase dir: `.planning/phases/999.14-kerberos-encryption-type-enumeration/` |
| BACK-19 | SAML / OAuth metadata scanning | Identity crypto gap | Corporate SSO endpoints publish metadata at well-known paths (`/saml/metadata`, `/.well-known/oauth-authorization-server`) containing signing certificates and algorithm declarations. Parsing these surfaces RSA-1024 signing certs or SHA1 assertion signing that is invisible to every other scanner. No authentication required — public metadata only. Phase dir: `.planning/phases/999.15-saml-oauth-metadata-scanning/` |
| BACK-20 | Compliance framework mapping | Intelligence gap | Map findings to FIPS 140-3, NIST SP 800-57, PCI DSS 4.0 (requirement 4.2.1), and HIPAA. The classifier already knows quantum-vulnerability levels; adding a compliance mapping layer converts a quantum-readiness report into a billable compliance engagement. Mostly a lookup table plus a new report section. Phase dir: `.planning/phases/999.16-compliance-framework-mapping/` |
| BACK-21 | Trend analysis across scan sessions | Intelligence gap | QUIRK stores every scan in SQLite but each is treated independently. The intelligence layer should generate delta insights: score change since last scan, new findings introduced, findings resolved, hosts with degraded posture. Complements the dashboard multi-scan navigation (BACK-02) by producing the analytical layer beneath it. Phase dir: `.planning/phases/999.17-trend-analysis-across-scan-sessions/` |
| BACK-22 | DNSSEC algorithm audit | Infrastructure gap | Query whether DNSSEC is enabled for scanned domains and enumerate the signing algorithm (RSASHA1 is quantum-vulnerable; ECDSA P-256/P-384 and Ed25519 are preferred). Simple DNS query; maps cleanly to CBOM algorithm components. Phase dir: `.planning/phases/999.18-dnssec-algorithm-audit/` |
| BACK-23 | HashiCorp Vault live connector | Secrets management gap | A chaos lab target exists but no real Vault connector. Vault is widely deployed in enterprise for secrets management. Scope: enumerate secret engines, transit encryption key specs, PKI mount signing algorithms, and auth method crypto configuration. Phase dir: `.planning/phases/999.19-hashicorp-vault-live-connector/` |
| BACK-24 | Code signing certificate inventory | Supply chain gap | Inventory codesigning certificates used in CI/CD pipelines, package signing (npm, pip, maven), and binary signing. Bridges the source scanner toward supply chain security. Would surface RSA-1024 or SHA1-signed artifacts that are quantum-vulnerable in the software supply chain. Phase dir: `.planning/phases/999.20-code-signing-certificate-inventory/` |
| BACK-25 | Scheduled / continuous scanning mode | Operational gap | Run scans on a configurable schedule, persist results in SQLite, and trigger alerts on certificate expiry or newly discovered findings. Transforms QUIRK from a point-in-time audit tool into an ongoing monitoring tool — the operational model most enterprise clients actually need for sustained assurance. Phase dir: `.planning/phases/999.21-scheduled-continuous-scanning-mode/` |
| BACK-26 | Distributed multi-node scanner architecture | Scale gap | Deploy lightweight scanner nodes in different network segments (DMZ, internal VLANs, cloud VPCs, air-gapped zones) that scan locally and ship findings to a central QUIRK console. Modeled after Nessus/Qualys sensor architecture. Core additions: agent mode (scan + POST results), console mode (FastAPI ingestion endpoint + node registry), agent auth tokens, per-node topology view in dashboard. FastAPI backend and SQLite multi-scan storage are already shaped for this; BACK-02 (multi-scan navigation) and BACK-21 (trend analysis) are natural foundation pieces. This is a v2 milestone-level capability — promotes QUIRK from a single-host tool to an enterprise platform. Phase dir: `.planning/phases/999.22-distributed-multi-node-scanner-architecture/` |
| BACK-27 | Auto-detect timezone from system | CLI UX / startup | **Priority: P0 — trivial, remove immediately.** `interactive_config()` prompts for timezone with a hardcoded `America/New_York` default. Derive from `datetime.now().astimezone().tzname()` instead. No user should ever have to answer this question. Phase dir: `.planning/phases/999.23-auto-detect-timezone-from-system/` |
| BACK-28 | Remove SNI prompt — hardcode True for FQDN targets | CLI UX / startup | **Priority: P0 — footgun, remove immediately.** SNI must always be `True` for FQDNs — that is literally what SNI is for. Surfacing it as a question implies it is a meaningful choice. Hardcode `True`, remove the prompt entirely. Phase dir: `.planning/phases/999.24-remove-sni-prompt-hardcode-true/` |
| BACK-29 | Remove connector stub prompts from interactive mode | CLI UX / startup | **Priority: P0 — misleading, remove immediately.** Interactive mode asks three yes/no questions for AWS, Azure, and Windows ADCS connectors, all labeled `(stub)`. Stubs do nothing. Asking users to enable non-functional features erodes trust. Remove all three until the connectors ship real functionality. Phase dir: `.planning/phases/999.26-remove-connector-stub-prompts-from-interactive-mode/` |
| BACK-30 | Replace timeout/concurrency prompts with scan profile selection | CLI UX / startup | **Priority: P1.** Interactive mode asks for raw `timeout_seconds` (default 4) and `concurrency` (default 200) — implementation details most operators cannot reason about. The `--profile quick|standard|deep` CLI flag already handles this via `apply_profile()`. Replace with a single profile selection question; let `apply_profile()` set the underlying values. Phase dir: `.planning/phases/999.25-replace-timeout-concurrency-prompts-with-profile-selection/` |
| BACK-31 | Consolidate `data_classification` and `data_types` into single block | CLI UX / startup | **Priority: P1.** The flow asks `data_classification` (public/internal/confidential/regulated) in `interactive_config()`, then `data_types` (PCI, PHI, FINANCIAL…) separately in `prompt_for_context()`. These are overlapping answers to the same question. Merge into one coherent block. Phase dir: `.planning/phases/999.31-consolidate-data-classification-and-data-types/` |
| BACK-32 | Surface live scanner prompts — JWT, container, source | CLI UX / startup | **Priority: P1 — feature parity gap.** Interactive mode asks about three stub connectors but never asks about three fully-implemented live scanners: JWT, container, and source. They are silently unreachable in interactive mode. Add enable + target-list prompts for each. Phase dir: `.planning/phases/999.29-surface-live-scanner-prompts-jwt-container-source/` |
| BACK-33 | Expand TLS port defaults and stop prompting | CLI UX / startup | **Priority: P1 — coverage gap.** Current defaults (`443, 8443, 9443, 10443, 4433, 5001`) miss significant enterprise surface: LDAPS (636, 3269), IMAPS/POP3S/SMTPS (993, 995, 465), Kubernetes API (6443), Docker TLS (2376), common DB TLS ports (5432, 3306, 1433), Vault (8200). Expand to a consulting-grade default list and remove the interactive port prompt — let config files override. Phase dir: `.planning/phases/999.27-expand-tls-port-defaults-stop-prompting/` |
| BACK-34 | Add SSH port prompt to interactive mode | CLI UX / startup | **Priority: P2 — consistency gap.** Config template defines `ports_ssh: [22, 2222]` but `interactive_config()` never asks about SSH ports. SSH is a first-class scanner. Align interactive mode with the config schema. Phase dir: `.planning/phases/999.28-add-ssh-port-prompt-to-interactive-mode/` |
| BACK-35 | Surface `tls_enum_mode` in interactive mode | CLI UX / startup | **Priority: P2 — hidden capability.** `ScanCfg.tls_enum_mode` accepts `off|fast|deep` and meaningfully changes scan depth. It is never surfaced interactively. Add a prompt (or fold into the profile question) so operators can discover deep TLS enumeration. Phase dir: `.planning/phases/999.30-surface-tls-enum-mode-in-interactive-mode/` |
| BACK-36 | Reorder interactive prompts — targets first | CLI UX / startup | **Priority: P2 — UX flow.** Currently: assessment metadata → scan tuning → targets. For a scanning tool, targets should be first. Correct mental model: "what to scan → scan options → output → metadata." Phase dir: `.planning/phases/999.32-reorder-interactive-prompts-targets-first/` |

---

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation Fixes | 0/4 | Planning complete | - |
| 2. CBOM Pipeline | 3/3 | Complete   | 2026-03-29 |
| 3. Scanner Coverage | 4/4 | Complete   | 2026-03-29 |
| 4. Chaos Lab Expansion | 5/5 | Complete   | 2026-03-30 |
| 5. Web Dashboard | 6/6 | Complete   | 2026-03-31 |
| 6. Documentation | 6/6 | Complete   | 2026-03-31 |
| 7. Polish and Packaging | 5/5 | Complete   | 2026-04-01 |
