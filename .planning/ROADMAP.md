# Roadmap: QU.I.R.K.

## Milestones

- ✅ **v3.9 Gap Closure** — Phases 1–11, 40 plans (shipped 2026-04-04) → `.planning/milestones/v3.9-ROADMAP.md`
- ✅ **v4.1 Foundation Polish** — Phases 12–16, 10 plans (shipped 2026-04-08) → `.planning/milestones/v4.1-ROADMAP.md`
- ✅ **v4.2 Identity Crypto** — Phases 17–24, 14 plans (shipped 2026-04-24) → `.planning/milestones/v4.2-ROADMAP.md`
- ✅ **v4.3 Data at Rest** — Phases 25–31, 24 plans (shipped 2026-04-26) → `.planning/milestones/v4.3-ROADMAP.md`
- ✅ **v4.4 Data in Motion** — Phases 32–37, 33 plans (shipped 2026-04-29) → `.planning/milestones/v4.4-ROADMAP.md`
- ✅ **v4.5 Reliability & Gap Closure** — Phases 38–44, 40 plans (shipped 2026-05-03) → `.planning/milestones/v4.5-ROADMAP.md`
- ✅ **v4.6 Enterprise Readiness** — Phases 45–50, 24 plans (shipped 2026-05-05) → `.planning/milestones/v4.6-ROADMAP.md`
- ✅ **v4.7 Governance & Compliance Platform** — Phases 51–56 + 56.1, 27 plans (shipped 2026-05-08)
- ✅ **v4.8 Pre-Primetime Hardening + Operating Model** — Phases 57–68 (shipped 2026-05-14) → `.planning/milestones/v4.8-ROADMAP.md`
- 🚧 **v4.9 Audit Depth** — Phases 69–77 (in progress)

## Phases

**Phase Numbering:**
- Integer phases (1-7): Planned milestone work
- Decimal phases (e.g., 2.1): Urgent insertions via `/gsd:insert-phase`

Decimal phases appear between their surrounding integers in numeric order.

<details>
<summary>✅ v3.9 Gap Closure (Phases 1–11) — SHIPPED 2026-04-04</summary>

- [x] **Phase 1: Foundation Fixes** - Consolidate scoring, fix data bugs, rename to QU.I.R.K., upgrade SSH and TLS scanners (completed 2026-03-29)
- [x] **Phase 2: CBOM Pipeline** - Integrate cyclonedx, map algorithms, enrich with NIST PQC classification, produce CBOM artifacts (completed 2026-03-29)
- [x] **Phase 3: Scanner Coverage** - Add JWT/API, container/binary, source code, and cloud connectors (AWS + Azure) (completed 2026-03-29)
- [x] **Phase 4: Chaos Lab Expansion** - Add jwt, registry, source, storage, ssh-weak, and ldaps lab profiles (completed 2026-03-30)
- [x] **Phase 5: Web Dashboard** - FastAPI + React dashboard with findings viewer, CBOM viewer, and PDF report export (completed 2026-03-31)
- [x] **Phase 6: Documentation** - Getting Started, installation, configuration, connector guides, report and CBOM interpretation (completed 2026-03-31)
- [x] **Phase 7: Polish and Packaging** - Visual identity, CLI UX, professional report templates, pip-installable distribution (completed 2026-04-01)
- [x] **Phase 8: Legacy Debt Cleanup** - Fix show-stopper bugs, dead code, broken CLI, and label/intent drift surfaced by codebase audit (completed 2026-04-03)
- [x] **Phase 9: Scoring Consolidation** - Eliminate dual scoring systems, make calibration profile functional, single authoritative score path (completed 2026-04-03)
- [x] **Phase 10: v3.9 Gap Closure** - Fix quantum safety label type mismatch, package dashboard static assets for pip distribution, add intelligence config block to template (completed 2026-04-04)
- [x] **Phase 11: Dashboard Wiring Fixes** - Close three integration gaps found by milestone audit: db_path default mismatch, QUIRK_SERVE_PORT not propagated to PDF exporter, SSH algorithms absent from dashboard CBOM viewer (completed 2026-04-04)

</details>

<details>
<summary>✅ v4.1 Foundation Polish (Phases 12–16) — SHIPPED 2026-04-08</summary>

- [x] **Phase 12: CLI Correctness** - Fix generated config field names, missing `quirk scan` subcommand, `[owner]` placeholder, and version number conflicts (completed 2026-04-06)
- [x] **Phase 13: Interactive Mode Overhaul** - Auto-detect timezone, remove stub prompts, fix connector labels, surface live scanners, add profile selection, expand port defaults, reorder prompts (completed 2026-04-06)
- [x] **Phase 14: Scoring & Intelligence Correctness** - Wire calibration profile into scoring, fix validate.py artifact list, fix migration_advisor patterns, propagate profile to dashboard (completed 2026-04-07)
- [x] **Phase 15: Code Hygiene** - Remove legacy connector stubs, add cfg.scan mutation guard, delete orphaned scorecard.py, update 11 Nyquist VALIDATION.md files (completed 2026-04-08)
- [x] **Phase 16: v4.1 Gap Closure** - Fix pyproject.toml version mismatch (CLI-04) and interactive mode output dir default mismatch (SCORE-04) — closes both audit gaps (completed 2026-04-08)

</details>

<details>
<summary>✅ v4.2 Identity Crypto (Phases 17–24) — SHIPPED 2026-04-24</summary>

**Milestone Goal:** Expand cryptographic inventory to cover identity protocols — Kerberos, SAML/OIDC, and DNSSEC — each with a scanner module, CBOM integration, chaos lab profile, and a dedicated Identity tab in the dashboard.

- [x] **Phase 17: Identity Infrastructure** - Schema columns, migration guard, [identity] extras group, and config flags for all three new scanners (completed 2026-04-08)
- [x] **Phase 18: DNSSEC Scanner** - dnspython scanner, RFC 8624/9905 algorithm classification, CBOM integration, BIND9 chaos lab (completed 2026-04-09)
- [x] **Phase 19: SAML/OIDC Scanner** - lxml metadata parser, OIDC discovery, classifier extension, SimpleSAMLphp chaos lab (completed 2026-04-09)
- [x] **Phase 20: Kerberos Scanner** - impacket AS-REQ probe, LDAP etype bitmap, classifier extension, Samba DC chaos lab (completed 2026-04-09)
- [x] **Phase 21: Identity Surface** - Intelligence layer counters, FastAPI IdentityFinding model, React Identity tab, findings table filter (completed 2026-04-10)
- [x] **Phase 22: v4.2 Identity Crypto Gap Closure** - Fix main_logger NameError in run_scan.py and SAML/KERBEROS Pass 2+3 skip list omissions in builder.py — closes DNSSEC-04, SAML-05, KERB-04 (completed 2026-04-16)
- [x] **Phase 23: DNSSEC CBOM Skip List Fix** - DNSSEC added to Pass 2 cert skip list, eliminating hollow X.509 CertificateProperties in CBOM output — closes DNSSEC-04 CBOM gap (completed 2026-04-24)
- [x] **Phase 24: Scan-Session Timestamp Isolation** - Shared session_start wired from run_scan.py into all 3 identity scanners, eliminating ISSUE-3 scan-window timing defect (completed 2026-04-24)

**Phase 25 deferred to v4.3:** Identity Findings Accuracy — RS-family branch for OIDC RS256 in _derive_identity_findings() + ldap3 to [identity] extras (closes NEW-ISSUE-1, ISSUE-2)

</details>

<details>
<summary>✅ v4.3 Data at Rest (Phases 25–31) — SHIPPED 2026-04-26</summary>

**Milestone Goal:** Expand cryptographic inventory to cover data-at-rest encryption and cloud coverage depth — database encryption, object storage policies, Kubernetes secrets, HashiCorp Vault transit keys, GCP connector, and cross-session trend analysis. Phase 25 carries over identity accuracy fixes from v4.2.

- [x] **Phase 25: Identity Findings Accuracy** - OIDC RS256 routing fix + ldap3 to [identity] extras; closes NEW-ISSUE-1 and ISSUE-2 from v4.2 audit (completed 2026-04-24)
- [x] **Phase 26: GCP Connector** - Cloud KMS key specs, Cloud SQL TLS enforcement, GCS bucket encryption; ADC credentials; GCS data passed to Phase 28 (completed 2026-04-25)
- [x] **Phase 27: Database Encryption Detection** - PostgreSQL pg_stat_ssl, MySQL SSL status, RDS StorageEncrypted/StorageEncryptionType; installs dat_scan_json column and dar_ scoring infrastructure (completed 2026-04-25)
- [x] **Phase 28: Object Storage Audit** - S3 SSE-S3/SSE-KMS/CMK, Azure Blob CMK/platform-managed, GCS CMEK via Phase 26 data; ThreadPoolExecutor S3 enumeration (completed 2026-04-26)
- [x] **Phase 29: Kubernetes Secrets Inspection** - EKS/GKE/AKS managed cluster encryption APIs; kube-apiserver pod spec; secret type count; encryption-config-inaccessible finding (completed 2026-04-26)
- [x] **Phase 30: HashiCorp Vault Connector** - Transit key type map (incl. ml-dsa/slh-dsa PQC positive), PKI mount CA cert, auth method list; hvac in [cloud] extras (completed 2026-04-26)
- [x] **Phase 31: Trend Analysis** - Score delta + new/resolved findings via scanned_at grouping; GET /api/trends; React Trends tab; no new SQLite table (completed 2026-04-26)

</details>

<details>
<summary>✅ v4.5 Reliability & Gap Closure (Phases 38–44) — SHIPPED 2026-05-03</summary>

**Milestone Goal:** Close v4.4 deferred items, harden scanner/CBOM/dashboard correctness, and automate the long-tail UAT debt — putting QU.I.R.K. in solid shape before the next capability and performance milestones.

- [x] **Phase 38: Identity API Regression Fix** - Restore SAML/OIDC entries in identity_findings, re-enable deferred SAML scan-window test, flip Phase 36 wave_0_complete (completed 2026-04-29)
- [x] **Phase 39: Data at Rest Dashboard Tab** - Ship the DASH-05 deferred Data at Rest tab in the React dashboard with DB/object-storage/K8s/Vault findings (completed 2026-04-29)
- [x] **Phase 40: Chaos Lab Parity** - Bring lab.sh, README, and expected-results oracle up to v4.4 parity so every shipped profile is documented, exercisable, and UAT-ready (completed 2026-04-29)
- [x] **Phase 41: CI Stability & Scanner Robustness** - Lock CI green, harden all scanners against missing extras/timeouts/unexpected exceptions, document consistent timeout/retry policy (completed 2026-04-29)
- [x] **Phase 42: CBOM Correctness Audit** - Validate CBOM JSON+XML against CycloneDX 1.6 spec, close classifier unknown-fallback gaps, review golden snapshot drift, unit-test Pass-2/3 skip lists (completed 2026-04-30)
- [x] **Phase 43: Dashboard Polish** - Eliminate browser console errors and React warnings across all routes, add explicit loading/empty states, meet WCAG AA baseline (completed 2026-05-01)
- [x] **Phase 44: UAT Debt Automation** - Automate Phase 27 DB, Phase 29 K8s, Phase 25 identity, and Phase 30 Vault UAT scenarios against existing chaos lab profiles (completed 2026-05-03)

</details>

<details>
<summary>✅ v4.6 Enterprise Readiness (Phases 45–50) — SHIPPED 2026-05-05</summary>

**Milestone Goal:** Make QUIRK credible and usable on real enterprise estates — fix install-day crashes, fill TLS finding gaps, enrich output with compliance context and PQC remediation guidance, and streamline the multi-target workflow.

- [x] **Phase 45: Install-Day UX** - Graceful ImportError degradation and `[all]` meta-extra so `pip install quirk` never crashes on first run (completed 2026-05-03)
- [x] **Phase 46: TLS Finding Gaps** - Emit CRITICAL/HIGH/MEDIUM findings for expired, self-signed, untrusted-CA, and weak-key TLS certificates with chaos lab verification (completed 2026-05-03)
- [x] **Phase 47: Nmap Discovery + Multi-Target Wizard** - Pre-scan nmap port discovery and comma/file/CIDR multi-target input in interactive mode and CLI (completed 2026-05-04)
- [x] **Phase 48: Rich Finding Context** - Populate `description` and `remediation` fields across all finding types with FIPS 203/204/205 guidance; purge stale PQC terminology (completed 2026-05-04)
- [x] **Phase 49: Compliance Mapping** - New `quirk/compliance/` module mapping findings to PCI-DSS/HIPAA/FIPS framework references; compliance section in HTML/PDF reports (completed 2026-05-05)
- [x] **Phase 50: Enterprise Documentation** - `docs/architecture.md` and `docs/operators-guide.md` synced to Obsidian vault (completed 2026-05-05)

</details>


### Phase 17: Identity Infrastructure
**Goal**: The codebase is structurally ready to receive three new identity scanners — schema columns exist and are idempotent, optional dependency group is declared, and config flags are wired
**Depends on**: Phase 16
**Requirements**: INFRA-01, INFRA-02, INFRA-03
**Success Criteria** (what must be TRUE):
  1. Running quirk against a v4.1 quirk.db does not raise any migration error — the three new nullable columns are added idempotently on startup
  2. `pip install quirk[identity]` resolves and installs impacket, dnspython[dnssec], lxml, defusedxml, and signxml without dependency conflicts
  3. A config.yaml with `enable_kerberos: true`, `enable_saml: true`, and `enable_dnssec: true` loads without validation errors; `quirk init` generates a template with these fields commented out
**Plans**: 2 plans
Plans:
- [x] 17-01-PLAN.md — TDD test scaffold (RED tests for INFRA-01, INFRA-02, INFRA-03)
- [x] 17-02-PLAN.md — Schema migration guard, ConnectorsCfg fields, pyproject.toml [identity] extras group

### Phase 18: DNSSEC Scanner
**Goal**: QU.I.R.K. can audit the DNSSEC posture of any domain — detecting unsigned zones, weak signing algorithms, NSEC zone enumeration exposure, and broken DS chains — with results in the CBOM
**Depends on**: Phase 17
**Requirements**: DNSSEC-01, DNSSEC-02, DNSSEC-03, DNSSEC-04, DNSSEC-05, DNSSEC-06, DNSSEC-07
**Success Criteria** (what must be TRUE):
  1. Scanning the BIND9 chaos lab RSASHA1-signed zone produces a CRITICAL finding for the weak algorithm and the finding appears in the CBOM output
  2. Scanning a domain with no DNSSEC produces a HIGH finding for unsigned zone; scanning a ECDSAP256SHA256 zone produces no algorithm severity finding
  3. NSEC record type detected and flagged as zone-enumerable exposure; DS broken chain (mismatched key tags) flagged as HIGH
  4. DNSSEC results appear in `dnssec_scan_json` in the database and produce `protocol="DNSSEC"` CryptoEndpoint rows
  5. `docker compose --profile dnssec up` starts the BIND9 container and the scanner successfully validates against it
**Plans**: 2 plans
Plans:
- [x] 18-01-PLAN.md — TDD test scaffold (RED tests for DNSSEC-01 through DNSSEC-07)
- [x] 18-02-PLAN.md — dnspython scanner, RFC 8624 classifier, CBOM integration, BIND9 chaos lab

### Phase 19: SAML/OIDC Scanner
**Goal**: QU.I.R.K. can audit SAML IdP metadata and OIDC discovery endpoints — detecting weak signing certificates and deprecated algorithm declarations — with results in the CBOM
**Depends on**: Phase 17
**Requirements**: SAML-01, SAML-02, SAML-03, SAML-04, SAML-05, SAML-06
**Success Criteria** (what must be TRUE):
  1. Scanning the SimpleSAMLphp chaos lab IdP produces a CRITICAL finding for the RSA-1024 signing certificate
  2. `<KeyDescriptor use="encryption">` certs parsed separately from signing certs with distinct findings; OIDC `id_token_signing_alg_values_supported` enumerated when endpoint is reachable
  3. RSA < 2048-bit signing keys flagged CRITICAL; SHA-1 algorithm URIs flagged HIGH
  4. SAML results appear in `saml_scan_json` in the database and produce `protocol="SAML"` CryptoEndpoint rows
  5. `docker compose --profile saml up` starts SimpleSAMLphp and the scanner successfully validates against it
**Plans**: 2 plans
Plans:
- [x] 19-01-PLAN.md — TDD test scaffold (RED tests for SAML-01 through SAML-06)
- [x] 19-02-PLAN.md — lxml metadata parser, OIDC discovery, classifier extension, SimpleSAMLphp chaos lab

### Phase 20: Kerberos Scanner
**Goal**: QU.I.R.K. can enumerate Kerberos encryption types from a KDC using an unauthenticated AS-REQ probe — detecting RC4 and DES etypes that represent classical and quantum cryptographic risk
**Depends on**: Phase 17
**Requirements**: KERB-01, KERB-02, KERB-03, KERB-04, KERB-05
**Success Criteria** (what must be TRUE):
  1. Scanning the Samba DC chaos lab produces a HIGH finding for RC4-HMAC (etype 23) without requiring any credentials
  2. DES etypes (1, 2, 3) are classified CRITICAL when present; AES-256 (etypes 18, 20) classified quantum-safe; UDP/88 blocked → TCP fallback or graceful `kerberos-unreachable` record
  3. Anonymous LDAP bind attempt on port 389 gracefully degrades (no crash, logged as skipped) if unreachable or auth required
  4. Kerberos results appear in `kerberos_scan_json` in the database and produce `protocol="KERBEROS"` CryptoEndpoint rows
  5. `docker compose --profile kerberos up` starts the Samba DC with `start_period: 90s` healthcheck; scanner probes port 88 successfully
**Plans**: 2 plans
Plans:
- [x] 20-01-PLAN.md — TDD test scaffold (RED tests for KERB-01 through KERB-05)
- [x] 20-02-PLAN.md — impacket AS-REQ probe, LDAP etype bitmap, classifier extension, Samba DC chaos lab

### Phase 21: Identity Surface
**Goal**: Identity protocol findings from all three scanners are surfaced in the quantum-readiness score, the dashboard Identity tab, and the findings table — giving consultants a complete view of the identity crypto attack surface
**Depends on**: Phase 18, Phase 19, Phase 20
**Requirements**: IDENT-01, IDENT-02, IDENT-03, IDENT-04
**Success Criteria** (what must be TRUE):
  1. A scan with RC4 Kerberos etypes, a weak SAML signing cert, and a DNSSEC RSASHA1 algorithm produces a lower readiness score than the same scan with only quantum-safe findings
  2. The dashboard displays an Identity tab with per-protocol summary cards showing finding counts for Kerberos, SAML/OIDC, and DNSSEC
  3. The findings table includes identity protocol rows and can be filtered to show only Kerberos, SAML, or DNSSEC findings
  4. `GET /api/scan/latest` returns an `identity_findings` array with `IdentityFinding` Pydantic objects for all three protocols
**Plans**: 2 plans
Plans:
- [x] 21-01-PLAN.md — TDD test scaffold (RED tests for IDENT-01 through IDENT-04) + FastAPI IdentityFinding model
- [x] 21-02-PLAN.md — evidence.py counters, scoring integration, React Identity tab
**UI hint**: yes

### Phase 22: v4.2 Identity Crypto Gap Closure
**Goal**: All three identity scanner requirements left unsatisfied at runtime are closed — scans with identity targets enabled no longer crash with NameError, and CBOM output contains no spurious TLS protocol components for SAML or Kerberos findings
**Depends on**: Phase 21
**Requirements**: DNSSEC-04, SAML-05, KERB-04
**Gap Closure:** Closes gaps from v4.2 milestone audit (2026-04-14)
**Success Criteria** (what must be TRUE):
  1. Running a scan with `enable_dnssec: true`, `enable_saml: true`, and `enable_kerberos: true` (with targets configured) completes without `NameError: name 'main_logger' is not defined`
  2. `dnssec_scan_json`, `saml_scan_json`, and `kerberos_scan_json` columns in the DB are populated after a scan with identity targets
  3. A CBOM generated from a scan with SAML and Kerberos findings contains no `crypto/protocol/tls/` components for those endpoints — only the correct identity protocol components
  4. Full test suite passes: 348+ tests, 0 failures
**Plans**: 1 plan
Plans:
- [ ] 22-01-PLAN.md — Fix main_logger -> logger in run_scan.py (6 occurrences) + add SAML/KERBEROS to builder.py Pass 2+3 skip lists + 7 new CBOM tests

### Phase 23: DNSSEC CBOM Skip List Fix
**Goal**: DNSSEC endpoints no longer generate hollow X.509 CertificateProperties components in the CycloneDX CBOM — the DNSSEC Config → Scanner → DB → CBOM → Report flow completes cleanly
**Depends on**: Phase 22
**Requirements**: DNSSEC-04
**Gap Closure:** Closes remaining gap from v4.2 milestone audit (2026-04-16)
**Success Criteria** (what must be TRUE):
  1. `builder.py` Pass 2 cert skip list includes `"DNSSEC"` — no hollow `CertificateProperties` generated for DNSKEY algorithm records
  2. A CBOM generated from a scan with DNSSEC findings contains zero `crypto/certificate/` components for DNSSEC endpoints
  3. Full test suite passes with no regressions
**Plans**: 1 plan
Plans:
- [x] 23-01-PLAN.md — TDD: 3 DNSSEC regression tests (RED) + add "DNSSEC" to Pass 2 cert skip tuple (GREEN)

### Phase 24: Scan-Session Timestamp Isolation
**Goal**: DNSSEC and SAML endpoints are never silently excluded from `GET /api/scan/latest` — a shared `session_start` timestamp passed from `run_scan.py` into each identity scanner ensures all endpoints share a single reference time regardless of sequential scan duration
**Depends on**: Phase 23
**Requirements**: KERB-04, SAML-05, DNSSEC-04, IDENT-02, IDENT-03
**Gap Closure:** Closes ISSUE-3 from v4.2 milestone audit (2026-04-24) — scan-window timing defect
**Success Criteria** (what must be TRUE):
  1. `run_scan.py` creates a single `session_start = datetime.now(timezone.utc)` before invoking any identity scanner and passes it as a parameter to each
  2. `dnssec_scanner.py`, `saml_scanner.py`, and `kerberos_scanner.py` each accept and stamp endpoints with the shared `session_start` instead of calling `datetime.now()` internally at endpoint construction time
  3. Tests demonstrate that a simulated scan with delayed Kerberos targets still returns DNSSEC and SAML endpoints in `GET /api/scan/latest` scan-window — none excluded by timestamp skew
  4. Full test suite passes with no regressions
**Plans**: 2 plans
Plans:
- [x] 24-01-PLAN.md — TDD RED: session_start acceptance tests for 3 identity scanners + ISSUE-3 API regression test
- [x] 24-02-PLAN.md — TDD GREEN: Add session_start parameter to scanners + wire in run_scan.py

## Phase Details

<details>
<summary>✅ v4.1 Foundation Polish — Phase Details (Phases 12–16)</summary>

### Phase 12: CLI Correctness
**Goal**: A new user who runs `quirk init`, follows the Getting Started guide, and executes their first scan encounters zero crashes, wrong commands, or inconsistent version strings
**Depends on**: Nothing (standalone correctness fixes)
**Requirements**: CLI-01, CLI-02, CLI-03, CLI-04
**Success Criteria** (what must be TRUE):
  1. `quirk init` generates a `config.yaml` where every field name matches the actual `ConnectorsCfg` and `ScanCfg` dataclass attributes — no `TypeError` on first run
  2. The Getting Started guide, config template comments, and `quirk init` output all instruct users to run `quirk --config config.yaml`, not `quirk scan --config config.yaml`
  3. `quirk init` generates a `config.yaml` with no `[owner]` placeholder — the documentation URL is either real or omitted
  4. `quirk --version`, CBOM metadata stamps, report section headers, and `writer.py` constants all show the same `4.x` version string
**Plans**: 2 plans
Plans:
- [x] 12-01-PLAN.md — TDD test scaffold (RED tests for all CLI correctness requirements)
- [x] 12-02-PLAN.md — Version bump to 4.1.0 + Getting Started install fix

### Phase 13: Interactive Mode Overhaul
**Goal**: Interactive mode guides a consultant to a correctly configured scan without surfacing broken prompts, missing scanner options, or confusing implementation details
**Depends on**: Phase 12
**Requirements**: INTER-01, INTER-02, INTER-03, INTER-04, INTER-05, INTER-06, INTER-07, INTER-08, INTER-09, INTER-10
**Success Criteria** (what must be TRUE):
  1. Running `quirk` in interactive mode never asks the user for timezone, SNI setting, or Windows ADCS — these are auto-detected or removed
  2. Interactive mode labels AWS and Azure as fully implemented connectors with credential requirement warnings; no connector is labeled "(stub)"
  3. A user can enable the JWT, container, and source scanners from interactive mode and provide their respective targets
  4. Interactive mode presents a single profile selection question (quick/standard/deep) instead of raw `timeout_seconds` and `concurrency` fields
  5. The generated config contains no `enable_windows_adcs` field and presents data classification as a single coherent prompt
**Plans**: 2 plans
Plans:
- [x] 13-01-PLAN.md — TDD test scaffold (RED tests for all 10 interactive mode requirements)
- [x] 13-02-PLAN.md — Rewrite interactive_config() with new prompt sequence, profile selection, and run_scan.py call site update

### Phase 14: Scoring & Intelligence Correctness
**Goal**: The readiness score a consultant presents to a client is accurate, profile-aware, and identical whether viewed from the CLI report or the dashboard
**Depends on**: Phase 12
**Requirements**: SCORE-01, SCORE-02, SCORE-03, SCORE-04
**Success Criteria** (what must be TRUE):
  1. Setting `profile: strict` in config produces measurably higher score weights on agility and identity subscores than `profile: lenient` on the same scan data
  2. `validate_run()` passes after every normal scan — no permanent validation failure caused by checking for artifacts that `write_reports()` never produces
  3. Legacy TLS migration recommendations appear in the `migration_advisor` output when `risk_engine.py` produces matching findings
  4. The readiness score shown in the dashboard matches the score in the CLI executive summary for the same scan when a non-default profile is configured
**Plans**: 2 plans
Plans:
- [x] 14-01-PLAN.md — RED test scaffold (failing tests for SCORE-01 through SCORE-04)
- [x] 14-02-PLAN.md — GREEN fixes (validate.py cleanup, dashboard profile propagation)


### Phase 15: Code Hygiene
**Goal**: The codebase contains no dead code that misleads contributors, no unsafe config mutation that corrupts multi-phase scans, and no stale phase records that misrepresent test coverage
**Depends on**: Phase 12
**Requirements**: HYGN-01, HYGN-02, HYGN-03, HYGN-04
**Success Criteria** (what must be TRUE):
  1. `quirk/connectors/` directory and all three stub files (`aws_stub.py`, `azure_stub.py`, `windows_adcs_stub.py`) are absent from the repo — zero broken imports result
  2. If an exception occurs mid-scan, `cfg.scan.timeout_seconds` and `cfg.scan.concurrency` are restored to their pre-scan values before the next phase executes
  3. `quirk/reports/scorecard.py` does not exist; the only scorecard implementation is the inline `_scorecard_markdown()` in `writer.py`
  4. All 11 Nyquist VALIDATION.md files accurately reflect phase completion status — no file reads `nyquist_compliant: false` for a phase whose tests are passing GREEN
**Plans:** 2/2 plans complete
Plans:
- [x] 15-01-PLAN.md — TDD test scaffold (RED tests for HYGN-01, HYGN-02, HYGN-03, HYGN-04)
- [x] 15-02-PLAN.md — Delete scorecard.py, fix SSH cfg.scan guard, update 13 VALIDATION.md files

### Phase 16: v4.1 Gap Closure
**Goal**: Both partial requirements identified by the v4.1 milestone audit are fully satisfied — `pip show quirk` returns 4.1.0 and interactive-mode users see their selected scan profile reflected in the dashboard
**Depends on**: Phase 15
**Requirements**: CLI-04, SCORE-04
**Gap Closure:** Closes gaps from v4.1 milestone audit (2026-04-08)
**Success Criteria** (what must be TRUE):
  1. `pyproject.toml` declares `version = "4.1.0"` — `pip show quirk` and `importlib.metadata.version("quirk")` both return "4.1.0" after install
  2. `interactive.py` output dir prompt defaults to `"quirk-output"` — interactive-mode users who accept all defaults find their intelligence JSON discovered correctly by the dashboard, and Flow C (wizard → scan → dashboard with correct profile) works end-to-end
**Plans**: 2 plans
Plans:
- [x] 16-01-PLAN.md — TDD test scaffold (RED tests for CLI-04 manifest version and SCORE-04 output dir alignment)
- [x] 16-02-PLAN.md — GREEN fixes (pyproject.toml version bump + interactive.py output dir default)

</details>


---

### Phase 8: Legacy Debt Cleanup
**Goal**: Every show-stopper bug, dead code artifact, and label/intent inconsistency surfaced by the codebase audit is resolved — the tool works correctly for new users out of the box and produces internally consistent output
**Depends on**: Nothing (standalone cleanup)
**Requirements**: Derived from CONCERNS.md audit 2026-04-02
**Success Criteria** (what must be TRUE):
  1. `quirk init` → edit targets → `quirk --config config.yaml` completes a scan without TypeError on any field in the generated template
  2. No documentation, help text, or generated file tells a user to run `quirk scan` — the correct invocation is used everywhere
  3. `quirk/connectors/` directory and all three stub files are deleted; zero broken imports result
  4. Interactive mode correctly labels AWS and Azure as active connectors; Windows ADCS prompt is removed
  5. `enable_windows_adcs` is removed from ConnectorsCfg and config schema
  6. `migration_advisor.py` string patterns match actual finding titles produced by `risk_engine.py`
  7. `cfg.scan` mutation in `run_scan.py` is wrapped in `try/finally` so timeouts restore on exception
  8. Version strings are consistent: `__version__`, CBOM `PLATFORM_VERSION`, `INTELLIGENCE_VERSION`, config default, and report section headers all agree
  9. `data/qcscan-legacy.sqlite` removed; `datetime.utcnow()` calls replaced; `quirk init` URL placeholder substituted
  10. `quirk/engine/rules.py` empty file removed; tqdm dead branch and dead assignment cleaned from `run_scan.py`
**Plans:** 2/2 plans complete

Plans:
- [x] 08-01-PLAN.md — Fix config template field names, subcommand references, and version string alignment (D-06, D-07, D-08, D-18)
- [x] 08-02-PLAN.md — Fix interactive mode labels, remove ADCS, add Phase 3 scanner prompts (D-03, D-04, D-05)
- [x] 08-03-PLAN.md — Delete dead code, fix migration_advisor, cfg.scan try/finally, datetime, tqdm (D-09..D-13, D-15, D-17, D-19..D-21)
- [x] 08-04-PLAN.md — Fix validate.py artifact checks + integration test (D-01, D-02)

### Phase 9: Scoring Consolidation
**Goal**: QUIRK produces one readiness score, one confidence value, and one roadmap per scan — sourced from a single authoritative code path — so a client cannot see two different numbers by reading different output artifacts
**Depends on**: Phase 8
**Requirements**: Derived from CONCERNS.md §4.1–4.3, §1.7, §12.1
**Success Criteria** (what must be TRUE):
  1. The readiness score in the executive summary markdown matches the score in the intelligence JSON and HTML report
  2. The roadmap in the executive summary markdown is the same data as the roadmap artifact files
  3. `quirk/assessment/readiness_score.py`, `quirk/assessment/confidence.py`, and `quirk/assessment/transition_planner.py` are either removed or clearly designated as deprecated aliases pointing to the intelligence layer
  4. Setting `profile: strict` in config produces measurably different score weights than `profile: lenient` on the same scan data
  5. `calibration_overrides` set in config are applied to the scoring engine weights at runtime
**Plans:** 3/3 plans complete

Plans:
- [x] 09-01-PLAN.md — Profile weight multipliers + Wave 0 test scaffolds (SC-04, SC-05)
- [x] 09-02-PLAN.md — Refactor executive.py to intelligence call sequence + wire calibration (SC-01, SC-02, SC-05)
- [x] 09-03-PLAN.md — Delete assessment compute modules + documentation update (SC-03)

### Phase 10: v3.9 Gap Closure
**Goal**: All three issues identified by the v3.9 milestone audit are resolved — quantum safety labels are semantically correct in the dashboard, the pip-installed package includes the React bundle, and users who run `quirk init` can discover the intelligence profile knob from the generated template
**Depends on**: Phase 9
**Requirements**: CBOM-03, UI-01, UI-03, BRAND-04
**Gap Closure**: Closes MISMATCH-01, PACKAGE-01, MISSING-01 from v3.9-MILESTONE-AUDIT.md
**Success Criteria** (what must be TRUE):
  1. The dashboard certificate inventory and findings table show correct quantum safety labels — RSA/DSA/DH certificates show `quantum-vulnerable`, not `quantum-safe`
  2. `pip install --no-editable .` followed by `quirk serve` loads the dashboard without 404 errors on UI routes
  3. `quirk init` generates a `config.yaml` with a commented `intelligence:` block showing the `profile:` knob

**Plans:** 2/2 plans complete
Plans:
- [x] 10-01-PLAN.md — Fix MISMATCH-01: quantum_safety_label() type confusion in scan.py _derive_findings and _cert_quantum_safety (CBOM-03, UI-03)
- [x] 10-02-PLAN.md — Fix PACKAGE-01 + MISSING-01: add dashboard/static glob to pyproject.toml, add intelligence config block to template (UI-01, BRAND-04)

### Phase 11: Dashboard Wiring Fixes
**Goal**: The default install→scan→serve E2E flow completes without errors — a fresh user who runs `quirk init`, scans, and serves sees their data in the dashboard; PDF export works at any port; SSH algorithms appear in the CBOM viewer tab
**Depends on**: Phase 10
**Requirements**: UI-01, UI-03, UI-04
**Gap Closure**: Closes GAP-INT-01, GAP-INT-02, GAP-INT-03 from v3.9-MILESTONE-AUDIT.md
**Success Criteria** (what must be TRUE):
  1. `quirk init` → edit config → `quirk --config config.yaml` → `quirk serve` → `/api/scan/latest` returns scan data (not 404) with default config and no env var overrides
  2. `quirk serve --port 9000` → PDF export button produces a valid PDF targeting port 9000, not port 8512
  3. An SSH-only scan shows algorithm components in the dashboard CBOM viewer tab (not an empty list)

Plans:
- [x] 11-01-PLAN.md — Fix db_path default mismatch and QUIRK_SERVE_PORT propagation (GAP-INT-01, GAP-INT-02)
- [x] 11-02-PLAN.md — Parse ssh_audit_json in _derive_cbom() for dashboard CBOM viewer (GAP-INT-03)

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
**Plans:** 2/2 plans complete
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



<details>
<summary>✅ v4.4 Data in Motion (Phases 32–37) — SHIPPED 2026-04-29</summary>

**Milestone Goal:** Extend QU.I.R.K.'s cryptographic inventory to cover network transport layers — auditing email protocol TLS (SMTP/IMAP/POP3, all 7 standard ports) and message broker TLS (Kafka, RabbitMQ, Redis) for weak ciphers, legacy TLS versions, plaintext listeners, and quantum-unsafe algorithms. Introduces the `data_in_motion` subscore as the 6th pillar of the quantum-readiness score.

- [x] **Phase 32: Email Scanner** — `email_scanner.py`: sslyze STARTTLS for SMTP/IMAP/POP3, stdlib fallback, STARTTLS downgrade finding, Postfix+Dovecot chaos lab (profile: email, ports 30025/30465/30587/30143/30993/30110/30995)
- [x] **Phase 33: Broker Scanner** — `broker_scanner.py`: Kafka (9092/9093/9094), RabbitMQ/AMQPS (5671/5672), Redis (6379/6380), Azure Service Bus, AWS SQS; broker chaos lab (profile: broker, ports 26379/26380/29092/29093/25671/25672) — SC-4 chaos-lab smoke deferred (scanner needs custom-port plumbing); 58-test pytest suite covers equivalent end-to-end logic
- [x] **Phase 34: Motion Intelligence** — Six `motion_` evidence counters in `evidence.py`, five `motion_` ratio entries in `scoring.py`, `PROFILE_MULTIPLIERS` motion_ prefix, `data_in_motion` as 6th named subscore in `compute_readiness_score()` (15/15 motion tests GREEN; commits: 4baeb3c → aa35696 → 2dc2515)
- [x] **Phase 35: CBOM Integration** — Pass 2+3 plaintext-broker skip tuples extended in `quirk/cbom/builder.py` (KAFKA-PLAIN/AMQP-PLAIN/REDIS-PLAIN); 6 email TLS labels (SMTP-STARTTLS, SMTPS, IMAP-STARTTLS, IMAPS, POP3-STARTTLS, POP3S) + 3 broker TLS labels (KAFKA-SSL, AMQPS, REDIS-TLS) emit crypto/protocol/tls components; lab-driven golden CBOM fixtures (`tests/fixtures/cbom/expected_*_cbom.json`) committed with structural verification test; REQUIREMENTS.md CBOM-01/CBOM-03 wording aligned to code; UAT-35-01..03 added (101/101 CBOM tests GREEN; verified PASS; commits: d99ddd2 → b76c818 → 7329e4b → 46960c0 → ca283ec → fc7e7d2)
- [x] **Phase 36: Dashboard Motion Tab** — React `/motion` route, Motion tab (email per-port table + STARTTLS warning badge, broker per-type summary + plaintext flag), 6th subscore in executive summary card, `MotionFinding` FastAPI schema in `/api/scan/latest`. **Wave_0_complete deferred** pending SAML scan-window regression (DEF-v4.4-01)
- [x] **Phase 37: Gap Closure and v4.4.0 Release** — Version bump to 4.4.0 across all 6 surfaces locked by `tests/test_version.py`; `[motion]` meta-extra over `[email]+[broker]+[kafka]`; `tests/test_infra03_nyquist_coverage.py` 18 explicit Nyquist tests GREEN; VALIDATION.md backfill (32/33/34/35/37 → `nyquist_compliant: true`, `wave_0_complete: true`); first top-level `CHANGELOG.md` + `docs/release-notes/4.4.0.md`. Deferrals: phase 36 `wave_0_complete` flip + SAML scan-window regression (Phase 24 ISSUE-3, out of scope). Per D-10/D-11, no git tag and no `/gsd-complete-milestone` invocation in-phase. (662 pytest passed, 7 skipped, 1 deferred; commits 9e21f30 → f13654a)

</details>


### Phase 32: Email Scanner
**Goal**: QU.I.R.K. can audit TLS posture on all seven standard email protocol ports — detecting weak ciphers, legacy TLS versions, expired certificates, and STARTTLS downgrade risk — stored in `email_scan_json` and producing `CryptoEndpoint` rows with correct `ep.protocol` labels
**Depends on**: Phase 31
**Requirements**: STRUCT-01, STRUCT-02, STRUCT-03, EMAIL-00, EMAIL-01, EMAIL-02, EMAIL-03, EMAIL-04, EMAIL-05, EMAIL-06, EMAIL-07, EMAIL-08, EMAIL-09, EMAIL-10, EMAIL-11, EMAIL-12
**Success Criteria** (what must be TRUE):
  1. Scanning a mail server on any of the 7 default email ports returns TLS version, negotiated cipher suite, cert subject/issuer/expiry, and key algorithm — accessible in the DB `email_scan_json` column and in the scan's `CryptoEndpoint` rows
  2. Port 25 STARTTLS endpoints emit a static MEDIUM `starttls-downgrade-risk` finding regardless of cipher strength; weak RSA key-exchange ciphers (`TLS_RSA_WITH_*`, 3DES, RC4) on any email port emit HIGH findings
  3. A `CONNECTION_REFUSED` on port 25 does not crash the scan — it is handled gracefully and logged (cloud VM egress constraint)
  4. When sslyze fails, the stdlib fallback (`smtplib`/`imaplib`/`poplib`) negotiates STARTTLS and extracts TLS version, cipher, and cert via the underlying SSLSocket
  5. `docker compose --profile email up` starts the Postfix+Dovecot container with weak TLS (TLS 1.1 minimum, RSA non-PFS ciphers, self-signed RSA-2048 cert); scanning produces at minimum one HIGH finding for weak cipher and one MEDIUM for STARTTLS risk; `labs/email/expected_results.md` documents expected findings
  6. `ep.service_detail` format follows `"SMTP-STARTTLS:587"`, `"SMTPS:465"`, `"IMAPS:993"`, `"POP3S:995"` convention (EMAIL-10)
**Plans**: 8 plans
- [x] 32-01-PLAN.md — Test scaffolding for email scanner (Wave 1, RED state)
- [x] 32-02-PLAN.md — DB schema + migration + config flag + pyproject [motion] group (Wave 1)
- [x] 32-03-PLAN.md — quirk/scanner/email_scanner.py canonical 4-function module (Wave 2)
- [x] 32-04-PLAN.md — Risk engine evaluate_email_endpoints + run_scan + profile gating (Wave 2)
- [x] 32-05-PLAN.md — labs/email/ Postfix+Dovecot chaos lab + email Docker Compose profile (Wave 2)
- [x] 32-06-PLAN.md — labs/email/expected_results.md from live lab scan (Wave 3)
- [x] 32-07-PLAN.md — UAT-SERIES update + Obsidian sync + commit (Wave 4)
- [x] 32-08-PLAN.md — Email scan JSON persistence (gap closure) + real-Logger smoke test (Wave 5)

### Phase 33: Broker Scanner
**Goal**: QU.I.R.K. can audit TLS posture on Kafka, RabbitMQ, Redis, Azure Service Bus, and AWS SQS — detecting plaintext listeners, weak TLS versions, and quantum-unsafe ciphers — in a single `broker_scanner.py` module following the `db_connector.py` architecture pattern
**Depends on**: Phase 31 (can develop in parallel with Phase 32)
**Requirements**: STRUCT-01, STRUCT-02, STRUCT-03, BROKER-00, BROKER-ARCH, KAFKA-01, KAFKA-02, KAFKA-03, KAFKA-04, RABBIT-01, RABBIT-02, RABBIT-03, RABBIT-04, RABBIT-05, REDIS-01, REDIS-02, REDIS-03, BROKER-LAB-01, BROKER-LAB-02
**Success Criteria** (what must be TRUE):
  1. Scanning Kafka on port 9093 returns cert chain, accepted cipher suites, and TLS version; scanning plaintext port 9092 emits a HIGH finding (`kafka-plaintext-listener`) when the port responds
  2. Scanning RabbitMQ on port 5671 (AMQPS) via sslyze returns full TLS probe results; plaintext port 5672 with a raw AMQP header probe emits HIGH (`amqp-plaintext-listener`) if the port responds with an AMQP frame
  3. Scanning Redis on port 6380 via raw `ssl.SSLContext` socket wrap returns TLS version, negotiated cipher, and cert; plaintext port 6379 emits HIGH (`redis-plaintext-no-auth`) if Redis responds; `redis-py` `CONFIG GET tls-*` degrades gracefully on `NOAUTH`/`NOPERM`
  4. `docker compose --profile broker up` starts all three broker containers; scanning chaos lab ports produces plaintext HIGH for all three brokers and weak cipher HIGH for at least two; `labs/broker/expected_results.md` documents expected findings
  5. All three scanner functions accept `session_start` parameter and stamp `ep.scanned_at` with it — no per-scanner `datetime.now()` calls (STRUCT-01)
  6. `broker_scan_json` column is present in the SQLite schema; `broker_scanner.py` is a single module exposing `scan_kafka_targets()`, `scan_rabbitmq_targets()`, `scan_redis_targets()`
**Plans**: 8 plans
- [x] 33-01-PLAN.md — DB schema: broker_scan_json column + idempotent migration (Wave 1)
- [x] 33-02-PLAN.md — Config + profile + pyproject [kafka]/[redis] sub-extras (Wave 1)
- [x] 33-03-PLAN.md — broker_scanner.py: imports, guards, Kafka KAFKA-01..04 (Wave 2)
- [x] 33-04-PLAN.md — broker_scanner.py: RabbitMQ + AMQP plaintext + Azure SB / AWS SQS host expansion (Wave 3)
- [x] 33-05-PLAN.md — broker_scanner.py: Redis raw ssl wrap + redis-py CONFIG GET tls-* (Wave 4)
- [x] 33-06-PLAN.md — run_scan.py wiring + risk_engine evaluate_broker_endpoints + integration tests (Wave 5)
- [x] 33-07-PLAN.md — labs/broker chaos lab + docker-compose broker profile + expected_results.md (Wave 5)
- [x] 33-08-PLAN.md — Smoke run + UAT-SERIES + Obsidian sync + ROADMAP close + commit (Wave 6)

**Closure Note (2026-04-28):** Phase 33 closed under Path B. Success Criterion 4 (chaos-lab smoke) is **deferred** — the scanner currently probes hardcoded broker default ports (9092/9093/9094, 5672/5671, 6379/6380) and cannot reach the lab's host-mapped ports (29092/29093/25671/25672/26379/26380). A follow-up plan should add custom-port plumbing to `scan_kafka_targets()` / `scan_rabbitmq_targets()` / `scan_redis_targets()` so UAT-33-03..07 can run live. Equivalent end-to-end verification is provided today by the 58-test pytest suite (`tests/test_broker_*`). Lab side-changes shipped in this wave: `apache/kafka:3.6` → `3.7.0` (image tag did not exist on Docker Hub); kafka healthcheck `--bootstrap-server localhost:29092` → `localhost:9092` (probes container-internal listener, not host-mapped port); ran `make certs` in `labs/broker/` to materialize the previously-empty cert mount points.

### Phase 34: Motion Intelligence
**Goal**: The quantum-readiness scoring engine recognizes email and broker TLS weaknesses as a distinct cryptographic surface — the `data_in_motion` subscore appears as the 6th named subscore in intelligence JSON alongside `tls`, `ssh`, `api`, `identity`, and `data_at_rest`
**Depends on**: Phase 32, Phase 33
**Requirements**: MOTION-01, MOTION-02, MOTION-03, MOTION-04
**Success Criteria** (what must be TRUE):
  1. A scan with plaintext Kafka and RabbitMQ listeners produces a lower `data_in_motion` subscore than a scan with only TLS-secured brokers — the `motion_broker_plaintext_ratio` weight (14.0) is applied correctly
  2. `evidence.py` `EvidenceCounters` dataclass contains all six `motion_` fields: `motion_email_starttls_missing_count`, `motion_email_plaintext_count`, `motion_email_weak_cipher_count`, `motion_broker_plaintext_count`, `motion_broker_weak_tls_count`, `motion_broker_weak_cipher_count`
  3. `scoring.py` `SCORE_WEIGHTS` contains all five `motion_` ratio entries with correct weights; `PROFILE_MULTIPLIERS` contains the `"motion_"` prefix key with strict/balanced/lenient values (MOTION-03)
  4. `compute_readiness_score()` returns `"data_in_motion"` as a named 6th subscore; the overall quantum-readiness score is measurably affected when motion_ counters are non-zero
**Plans**: 3 plans
- [ ] 34-01-PLAN.md — RED unit-test scaffold for motion_ evidence counters and data_in_motion subscore (Wave 1)
- [ ] 34-02-PLAN.md — Wire 6 motion_ counters in evidence.py + 5 SCORE_WEIGHTS entries, motion_ profile multiplier, motion_impacts block, data_in_motion 6th subscore in scoring.py (Wave 2)
- [ ] 34-03-PLAN.md — UAT-SERIES.md update + Obsidian phase note + vault sync + commit (Wave 3)

### Phase 35: CBOM Integration
**Goal**: Email and broker TLS endpoints appear correctly in the CycloneDX CBOM — algorithm components registered in Pass 1, cert components in Pass 2, protocol components in Pass 3 — with plaintext-only endpoints skipped to prevent hollow certificate entries
**Depends on**: Phase 32, Phase 33
**Requirements**: CBOM-01, CBOM-02, CBOM-03, CBOM-04
**Success Criteria** (what must be TRUE):
  1. A CBOM generated from a scan with email TLS findings contains algorithm components with `ep.protocol` values `"SMTP-STARTTLS"`, `"SMTPS"`, `"IMAPS"`, `"POP3S"` — distinguishable from HTTPS endpoints in the CBOM viewer
  2. A CBOM generated from a scan with broker TLS findings contains algorithm components with `ep.protocol` values `"AMQPS"`, `"KAFKA-TLS"`, `"REDIS-TLS"`; `TLS_RSA_WITH_*` suites classified `quantum-vulnerable` (HIGH) via `QUANTUM_SAFETY_MAP`
  3. Plaintext-only broker endpoints (`"AMQP"`, `"KAFKA-PLAIN"`, `"REDIS-PLAIN"`) are in the Pass 2 and Pass 3 skip lists — no hollow `CertificateProperties` entries exist for endpoints with no TLS cert (CBOM-03)
  4. Full test suite passes with no CBOM regressions; `builder.py` requires no structural changes — only skip list additions and `ep.protocol` string routing
**Plans**: 4 plans
Plans:
- [x] 35-01-PLAN.md — RED synthesized-endpoint tests for email + broker CBOM wiring (Wave 1)
- [x] 35-02-PLAN.md — GREEN: add KAFKA-PLAIN/AMQP-PLAIN/REDIS-PLAIN to builder Pass 2+3 skip tuples (Wave 2)
- [x] 35-03-PLAN.md — Golden CBOM snapshots for email + broker labs + integration test (Wave 3)
- [x] 35-04-PLAN.md — REQUIREMENTS.md edits (CBOM-01/CBOM-03) + UAT-SERIES.md UAT-35-01..03 + Obsidian phase note + vault sync + commit (Wave 4)

### Phase 36: Dashboard Motion Tab
**Goal**: Consultants can view email and broker TLS posture in the dashboard — a dedicated Motion tab shows per-port email summaries with STARTTLS warning badges and per-broker type summaries with plaintext-exposed flags; the executive summary card shows the `data_in_motion` subscore as the 6th line
**Depends on**: Phase 34, Phase 35
**Requirements**: DASH-01, DASH-02, DASH-03, DASH-04, DASH-05
**Success Criteria** (what must be TRUE):
  1. The dashboard navigation shows a "Motion" tab that loads the `/motion` React route without errors, alongside the existing Identity and Trends tabs
  2. The Motion tab Email section shows a per-port table: port, protocol label, TLS version, cipher suite, cert expiry, quantum risk tier; port-25 endpoints display a STARTTLS stripping warning badge
  3. The Motion tab Broker section shows a per-broker-type summary: endpoint, port, TLS version, cipher suite, and a plaintext-exposed flag (red badge) when the plaintext port responded
  4. The executive summary card shows a "Data in Motion" score line as the 6th entry; the score is non-zero when motion_ counters are populated from a scan
  5. `GET /api/scan/latest` response includes `motion_findings: list[MotionFinding]` — a Pydantic-validated array parallel to `identity_findings`
**Plans**: 4 plans
- [x] 36-01-PLAN.md — Backend Pydantic schema (MotionFinding, SubScores.data_in_motion, ScanLatestResponse.motion_findings) + _derive_motion_findings + Pitfall 1 SubScores constructor fix + 5 pytest cases (Wave 1)
- [x] 36-02-PLAN.md — Frontend TS types + executive 6th ScoreGauge + sidebar Motion entry + /motion route registration (Wave 2)
- [x] 36-03-PLAN.md — Motion page implementation: EmailTable + BrokerGroupedSections (Kafka/AMQP/Redis) + STARTTLS/plaintext badges + cloud chip (Wave 3)
- [x] 36-04-PLAN.md — UAT-36-01..05 cases + manual UAT sign-off + vault sync + Obsidian phase note + commit (Wave 4)
**UI hint**: yes

### Phase 37: Gap Closure and v4.4.0 Release
**Goal**: All v4.4 requirements are verifiably satisfied, Nyquist VALIDATION.md files accurately reflect phase completion, and the version string is bumped to 4.4.0 across all output artifacts
**Depends on**: Phase 36
**Requirements**: STRUCT-01, STRUCT-02, STRUCT-03, INFRA-01, INFRA-02, INFRA-03
**Success Criteria** (what must be TRUE):
  1. `quirk/__init__.py` and `pyproject.toml` declare version `4.4.0`; `quirk --version`, CBOM metadata, and report section headers all return `4.4.0`
  2. `pyproject.toml` `[motion]` extras group is declared with all direct dependencies; no dependency added retroactively outside a plan (INFRA-02)
  3. All six scanner entry points have Nyquist VALIDATION.md coverage for: happy path (TLS found), graceful degradation (connection refused), and plaintext-only detection (INFRA-03)
  4. All 6 phase VALIDATION.md files for v4.4 read `nyquist_compliant: true` and `wave_0_complete: true`
  5. Full test suite passes (504+ tests, 0 failures); no open CRITICAL or HIGH unresolved issues
**Plans**: 6 plans
- [ ] 37-01-PLAN.md — INFRA-01: bump version to 4.4.0 across all surfaces; create tests/test_version.py
- [ ] 37-02-PLAN.md — INFRA-02: restructure pyproject.toml [motion] meta-extra topology
- [ ] 37-03-PLAN.md — INFRA-03: 18 Nyquist coverage tests (6 entry points × 3 scenarios)
- [ ] 37-04-PLAN.md — VALIDATION.md backfill for phases 32-37 (D-04/D-05/D-06)
- [ ] 37-05-PLAN.md — CHANGELOG.md 4.4.0 entry + docs/release-notes/4.4.0.md
- [ ] 37-06-PLAN.md — Phase closure: Obsidian note, UAT-SERIES update, vault sync, final commit

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
| BACK-37 | Remove `quirk/connectors/` legacy dead code directory | Legacy debt | **Priority: P0 — dead code, remove immediately.** `quirk/connectors/` contains three stub files (`aws_stub.py`, `azure_stub.py`, `windows_adcs_stub.py`) that are never imported anywhere in the codebase. They are artifacts from the original abandoned project. The real implementations live in `quirk/scanner/`. The directory's existence is actively misleading — it implies these are the connector implementations when they aren't. Phase dir: `.planning/phases/999.33-remove-legacy-connectors-dead-code-directory/` |
| BACK-38 | Fix interactive mode connector labels — AWS/Azure are real, not stubs | Legacy debt | **Priority: P0 — wrong label causes trust issue.** `interactive_config()` labels both AWS and Azure as "(stub)" but both are fully implemented connectors in `quirk/scanner/`. A user who enables AWS in interactive mode will get real boto3 calls against their AWS account — not stub behavior. Fix the labels; add credential requirement warnings; surface the `aws_region` and `aws_profile` config fields that are never prompted for. Phase dir: `.planning/phases/999.34-fix-interactive-mode-aws-azure-stub-labels/` |
| BACK-39 | Remove or implement `enable_windows_adcs` dead config field | Legacy debt | **Priority: P1.** `enable_windows_adcs` is defined in `ConnectorsCfg`, prompted in `interactive_config()`, stored in config — and never checked in `run_scan.py`. No code path acts on it. Either remove the field + prompt entirely (clean) or implement the Windows ADCS scanner (implement). Until one of those happens it is dead configuration that creates a false impression of ADCS support. Phase dir: `.planning/phases/999.35-remove-or-implement-windows-adcs-dead-config-field/` |
| BACK-40 | Fix `quirk init` broken config template | **P0 — show-stopper** | The template generated by `quirk init` uses wrong field names that crash the tool on startup with `TypeError`: `scan.timeout` → `scan.timeout_seconds`, `scan.max_workers` → `scan.concurrency`, `targets.ips` → `targets.include_ips`, connector block structure is entirely wrong. Any new user following the documented workflow hits this immediately. Source: CONCERNS.md §3.4, §10.1. Phase dir: `.planning/phases/999.36-fix-quirk-init-broken-config-template/` |
| BACK-41 | Fix `quirk scan` nonexistent command in docs and template | **P0 — show-stopper** | `quirk/config_template.yaml`, `quirk/cli/init_cmd.py`, and `docs/getting-started.md` all instruct users to run `quirk scan --config config.yaml`. This command does not exist — argparse throws an error. The correct invocation is `quirk --config config.yaml`. First thing any new user tries. Source: CONCERNS.md §5.1. Phase dir: `.planning/phases/999.37-fix-quirk-scan-nonexistent-command-in-docs-and-template/` |
| BACK-42 | Consolidate dual scoring systems into single authoritative path | **P0 — credibility** | Every scan run produces two different readiness scores, two confidence values, and two roadmaps from separate algorithms. Executive summary markdown uses `quirk/assessment/` layer; intelligence JSON and HTML report use `quirk/intelligence/` layer. A client who reads both sees different numbers with no explanation. There are also two roadmap builders and two confidence engines in parallel. Source: CONCERNS.md §4.1–4.3. Phase dir: `.planning/phases/999.38-consolidate-dual-scoring-systems-single-authoritative-path/` |
| BACK-43 | Fix scoring calibration profile — currently cosmetic, never applied | P1 | `lenient/balanced/strict` profile appears in config and output JSON but `get_calibration()` is never called and `calibration_overrides` are loaded then discarded. Score weights are never altered regardless of profile setting. Source: CONCERNS.md §1.7, §12.1. Phase dir: `.planning/phases/999.39-fix-scoring-calibration-profile-cosmetic-not-applied/` |
| BACK-44 | Fix `validate.py` — expects artifacts that `write_reports()` never produces | P1 | `validate_run()` checks for `assessment-*.json` and `calibration-*.json` which are never written. Every real scan run will fail validation permanently. Source: CONCERNS.md §3.5. Phase dir: `.planning/phases/999.40-fix-validate-py-wrong-artifact-expectations/` |
| BACK-45 | Guard `cfg.scan` in-place mutation with `try/finally` | P1 | `run_scan.py` mutates `cfg.scan.timeout_seconds` and `cfg.scan.concurrency` around TLS and SSH phases without a `try/finally`. If an exception occurs, remaining scan phases (JWT, container, etc.) inherit the wrong values. Source: CONCERNS.md §10.2. Phase dir: `.planning/phases/999.41-guard-cfg-scan-mutation-with-try-finally/` |
| BACK-46 | Fix `migration_advisor.py` dead string patterns | P1 | `recommend_migration_paths()` checks for `"deprecated tls"` and `"public key"` in finding titles. Neither string appears in any finding produced by `risk_engine.py`. Migration recommendations for legacy TLS are silently skipped. Source: CONCERNS.md §2.2–2.3. Phase dir: `.planning/phases/999.42-fix-migration-advisor-dead-string-patterns/` |
| BACK-47 | Fix `quirk init` URL placeholder never substituted | P1 | `quirk/config_template.yaml` line 4 contains `https://github.com/[owner]/quirk/...` — the `[owner]` placeholder was never substituted. Appears in every config file generated by `quirk init`. Source: CONCERNS.md §8.3. Phase dir: `.planning/phases/999.43-fix-quirk-init-url-placeholder-owner-substitution/` |
| BACK-48 | Fix version number disagreements across codebase | P1 | `INTELLIGENCE_VERSION = "4.0.0"` in `writer.py` vs `"3.9.0"` in config default; CBOM stamps `PLATFORM_VERSION = "3.9"` while CLI is `4.0.0`; report section headers read `v3.6` and `v3.7` verbatim in client-facing output. Source: CONCERNS.md §2.4, §2.5, §2.6, §2.7. Phase dir: `.planning/phases/999.44-fix-version-number-disagreements-across-codebase/` |
| BACK-49 | Remove `quirk/engine/rules.py` empty reserved file | P2 | Single-line comment: `# Reserved for future: load YAML rules…`. Never imported. Severity logic it was meant to replace is hardcoded in `risk_engine.py`. Source: CONCERNS.md §1.2. Phase dir: `.planning/phases/999.45-remove-quirk-engine-rules-py-empty-reserved-file/` |
| BACK-50 | Remove dead helper functions in `writer.py` and orphaned `scorecard.py` | P2 | Five private helpers in `writer.py` (lines 37–102) never called. `build_scorecard_markdown()` in `scorecard.py` only called from tests — the scan path uses an inline `_scorecard_markdown()` in `writer.py` instead. Two separate scorecard implementations exist. Source: CONCERNS.md §1.4, §1.8. Phase dir: `.planning/phases/999.46-remove-dead-functions-in-writer-py-scorecard-orphan/` |
| BACK-51 | Fix `migration_planner.py` dual categorization vs intelligence roadmap | P2 | `categorize_waves()` in `engine/migration_planner.py` produces `NOW/NEXT/LATER` for terminal output while `intelligence/roadmap.py` produces a different phased roadmap for file artifacts. Same findings, different categorizations, no reconciliation. Source: CONCERNS.md §1.3. Phase dir: `.planning/phases/999.47-fix-migration-planner-dual-categorization-vs-intelligence-roadmap/` |
| BACK-52 | Remove dead intelligence modules: `driver_text`, schema dataclasses, `calibration` | P2 | `driver_text.polish_drivers()` is never called and uses wrong key names. Schema dataclasses (`ScoreInputs` etc.) are exported but production code returns plain dicts. `calibration.get_calibration()` never called. Source: CONCERNS.md §1.5, §1.6, §1.7. Phase dir: `.planning/phases/999.48-remove-dead-intelligence-modules-driver-text-schema-calibration/` |
| BACK-53 | Remove `data/qcscan-legacy.sqlite` | P2 | Database artifact using the old `qcscan` package name from the pre-rename era. Source: CONCERNS.md §6.1. Phase dir: `.planning/phases/999.49-remove-data-qcscan-legacy-sqlite/` |
| BACK-54 | Clean up `tqdm` dead branch and audit dependency | P2 | `tqdm = None` assignment in `run_scan.py` followed by `if tqdm:` branch that can never execute. `tqdm>=4.67` still listed as production dependency. Source: CONCERNS.md §6.2. Phase dir: `.planning/phases/999.50-clean-up-tqdm-dead-branch-and-dependency/` |
| BACK-55 | Clean internal D-reference ticket comments from source | P2 | `D-04`, `D-05`, `D-15`, `D-16` etc. scattered through source; `v3.5`, `v3.6`, `v3.7` version tags appear verbatim in generated client reports. Source: CONCERNS.md §6.3. Phase dir: `.planning/phases/999.51-clean-d-reference-comments-from-source/` |
| BACK-56 | Fix `datetime.utcnow()` deprecation | P2 | `quirk/logging_util.py:43` and `quirk/discovery/nmap_provider.py:50` use deprecated `datetime.utcnow()`. Raises `DeprecationWarning` in Python 3.12+. Rest of codebase uses `datetime.now(timezone.utc)`. Source: CONCERNS.md §6.4. Phase dir: `.planning/phases/999.52-fix-datetime-utcnow-deprecation/` |
| BACK-57 | Add tests for `run_scan.py`, `validate.py`, and `interactive.py` | P2 | Main entry point, validation module, and interactive config have zero test coverage. The cfg mutation bug, wrong subcommand dispatch, and broken interactive prompts are all untestable in the current state. Source: CONCERNS.md §11. Phase dir: `.planning/phases/999.53-add-tests-run-scan-validate-interactive/` |
| BACK-58 | Document JWT scanner `verify=False` behavior | P2 | JWKS endpoint requests disable TLS verification. Acceptable trade-off for a scanner but should be documented; risk of MITM on JWKS URI is real in adversarial environments. Source: CONCERNS.md §8.1. Phase dir: `.planning/phases/999.54-document-jwt-scanner-verify-false-behavior/` |
| BACK-59 | Fix port 22 listed as TLS port in sample config | P2 | `docs/sample-config.yaml` lists port 22 in `ports_tls`. Creates wasted TLS/HTTP probe attempts against SSH ports. Source: CONCERNS.md §9.1. Phase dir: `.planning/phases/999.55-fix-port-22-in-tls-port-list-sample-config/` |
| BACK-60 | Propagate scan-time scoring profile to dashboard | P2 | `quirk/dashboard/api/routes/scan.py:330` calls `compute_readiness_score(evidence)` without `profile=` kwarg, always using `balanced` default. CLI report correctly passes `cfg.intelligence.profile`. A user with `profile: strict` sees different scores in dashboard vs CLI report. Fix: store scan-time profile in `CryptoEndpoint` DB or read `intelligence-*.json` at serve time. Source: v3.9 milestone audit INT-01. Phase dir: `.planning/phases/999.56-propagate-scoring-profile-to-dashboard/` |
| BACK-61 | Delete or fix orphaned `scorecard.py` production module | P3 | `quirk/reports/scorecard.py::build_scorecard_markdown()` is never called in production — `writer.py` uses its own inline `_scorecard_markdown()` instead. Module is also missing `profile=` kwarg, making it a stale profile-unaware call site. Only imported in `tests/test_reports_scorecard.py`. Either delete the file or align it with the production path. Source: v3.9 milestone audit INT-02. Phase dir: `.planning/phases/999.57-delete-orphaned-scorecard-module/` |
| BACK-62 | Update Nyquist VALIDATION.md files post-execution | P3 | 9 phases have VALIDATION.md with `nyquist_compliant: false` and `wave_0_complete: false` — these are stale (created at planning time, never updated after tests passed GREEN). Phases 02 and 08 have no VALIDATION.md at all. All phase verifications passed — the files just weren't updated. Run `/gsd:validate-phase N` for each phase to generate accurate Nyquist coverage records. Source: v3.9 milestone audit Nyquist section. |
| BACK-63 | Score transparency in executive reports | Medium | Add a scoring methodology section to the executive summary explaining: how profile weights (strict/balanced/lenient) affect the score, what subscores contributed most, and what score ranges map to readiness levels (high/medium/low). User wants to review Phase 14 output first — score drivers are already present in the executive summary — before deciding if additional methodology explanation is needed. Phase dir: `.planning/phases/999.56-score-transparency-executive-reports/` |
| BACK-64 | Authenticated scan mode — optional credential store for deeper probing | Platform / v4.5+ | Add a first-class optional credential model to config.yaml (env-var substitution, no plaintext, per-target mapping) enabling scanners to attempt deeper authenticated probing when credentials are available, with graceful fallback to unauthenticated when not. Scanners that benefit: Kerberos (LDAP bind → `msDS-SupportedEncryptionTypes` per-account etype bitmap), SSH (key-based login → sshd_config host crypto inspection), JWT/API (OAuth client creds → token endpoint scanning). DNSSEC and TLS have no meaningful authenticated path. SAML assertion-level inspection deferred to SaaS milestone (requires SP context). Requires a credential security review as a gate — credential storage is a platform concern, not a per-scanner concern. Design once, all scanners adopt uniformly. Natural home: v4.5 or pre-SaaS milestone. Related: KERB-ADV-01 in REQUIREMENTS.md Future Requirements. Phase dir: `.planning/phases/999.57-authenticated-scan-mode/` |
| BACK-65 | Comprehensive Architecture Document | Post-v4.2 | Produce a deep-dive architecture document covering: how QU.I.R.K. is built (component map, data flow, module boundaries), connector and scanner diagrams (each protocol scanner's capabilities and detection scope), the quantum-readiness scoring model (evidence weights, profile variants, subscores), what problems it solves (threat landscape, PQC transition rationale, compliance use cases), and CycloneDX CBOM structure. Audience: architects, security engineers, and technically informed consultants. To be authored after v4.2 identity surface scanners are complete so the full scanner roster is stable. Phase dir: `.planning/phases/999.58-comprehensive-architecture-document/` |
| BACK-66 | Operator's Guide — all configurations and settings | Post-v4.2 | Produce a comprehensive operator's guide covering every config.yaml key (with valid values, defaults, and examples), all CLI flags and subcommands, connector setup and credential templates for each supported platform (AWS, Azure, Docker, Git, TLS, SSH, JWT, DNSSEC, SAML, Kerberos), scoring profile selection, interactive mode walkthrough, chaos lab operation, dashboard usage, CBOM export options, and operational troubleshooting. Goal: an operator who has never used QU.I.R.K. can configure and run a full engagement scan from this guide alone, without reading source code. To be authored after v4.2 is complete so all identity-surface connectors are included. Phase dir: `.planning/phases/999.59-operators-guide-all-configurations-and-settings/` |
| BACK-67 | Migrate `defusedxml.lxml` to raw `lxml` with manual XXE controls | P2 | `quirk/scanner/saml_scanner.py` uses `defusedxml.lxml` (deprecated in newer defusedxml releases) via `defused_ET.fromstring()`. Migration path: switch to raw `lxml.etree` with `resolve_entities=False` and `no_network=True` parser options to maintain XXE safety without the deprecated wrapper. Non-blocking today — all 25 SAML tests pass — but will break on a future defusedxml release that removes the lxml submodule. Source: Phase 19 VERIFICATION.md advisory. Phase dir: `.planning/phases/999.60-migrate-defusedxml-lxml-to-lxml-with-manual-xxe-controls/` |
| BACK-68 | Broker scanner custom-port plumbing (unblock live UAT-33-03..07) | Phase 33 closure deferral (SC-4) | **Priority: P1 — testability gap.** `broker_scanner.py` currently probes hardcoded broker default ports per protocol: Kafka (9092/9093/9094), RabbitMQ (5671/5672), Redis (6379/6380). The broker chaos lab maps these to non-conflicting host ports (29092/29093 for Kafka, 25671/25672 for RabbitMQ, 26379/26380 for Redis), so scanner-to-lab traffic does not connect today and SC-4 (chaos-lab end-to-end smoke) was deferred at Phase 33 closure. Add custom-port arguments to `scan_kafka_targets()` / `scan_rabbitmq_targets()` / `scan_redis_targets()` (mirror `--kafka-host host:port` parsing already accepted by `run_scan.py`) so the scanner can target arbitrary host:port pairs and live UAT-33-03..07 can run against the broker chaos lab. 58-test pytest suite stands in for end-to-end verification today. Source: Phase 33 closure note + 33-08-SUMMARY.md. Phase dir: `.planning/phases/999.61-broker-scanner-custom-port-plumbing/` |
| BACK-68 | QRAMM Data Model & Backend API | Compliance / governance integration | Foundational phase for integrating the CSNP QRAMM (Quantum Readiness Assurance Maturity Model) framework into QUIRK. Scope: SQLite tables (`qramm_sessions`, `qramm_answers`, `qramm_profiles`) plus FastAPI CRUD endpoints for assessment lifecycle (create/load/save/score session). `qramm_answers` stores per-question responses (Q# 1–120, dimension, practice, stream, answer 1–4, optional evidence note). `qramm_profiles` stores org profile multiplier inputs (industry, size, geo scope, data sensitivity, regulatory requirements → multiplier 0.8–1.5×). `qramm_sessions` tracks completion state and cached dimension scores. Required foundation for all BACK-69 through BACK-73 phases. Attribution: QRAMM v1.0 framework by CSNP (qramm.org); open-source with attribution. Phase dir: `.planning/phases/999.61-qramm-data-model-and-backend-api/` |
| BACK-69 | QRAMM Assessment UI — Profile & Question Wizard | Compliance / governance integration | React UI for running a QRAMM assessment inside the QUIRK dashboard. New sidebar nav item "QRAMM Assessment" (or under a Governance section). Two-stage flow: (1) **Org Profile** — form collecting industry, size, geo scope, data sensitivity, and regulatory requirements to compute the profile multiplier; (2) **Assessment Wizard** — tabbed layout with one tab per dimension (CVI, SGRM, DPE, ITR), each showing Foundation and Advanced stream questions. Per-question UI: question text, explanation, 1–4 radio scale with maturity-level labels (Basic / Developing / Established / Optimizing), evidence note text field, pre-population badge when auto-filled from scan data. Progress tracker showing X of 120 answered. Built on existing shadcn/ui components (Card, Tabs, Progress, Badge). Depends on BACK-68. Phase dir: `.planning/phases/999.62-qramm-assessment-ui-profile-and-question-wizard/` |
| BACK-70 | QRAMM Scorecard & Visualizations | Compliance / governance integration | Scorecard view that mirrors the QRAMM toolkit output inside the QUIRK dashboard. Components: (1) **Dimension summary table** — Raw Score, Weighted Score (raw × profile multiplier), Industry Benchmark, Maturity Level, Completion % for each of the 4 dimensions; (2) **Radar chart** — weighted dimension scores vs. industry benchmarks (4 axes — CVI, SGRM, DPE, ITR) using Recharts RadarChart already in the vendor bundle; (3) **Bar chart** — raw dimension scores side-by-side; (4) **Maturity distribution donut** — count of practices at each maturity level (Basic/Developing/Established/Advanced/Optimizing); (5) **Highlights panel** — top 3 strengths and top 3 improvement areas by practice score. Maturity thresholds: 1.0–1.5 Basic, 1.6–2.5 Developing, 2.6–3.5 Established, 3.6–3.9 Advanced, 4.0 Optimizing. Depends on BACK-68, BACK-69. Phase dir: `.planning/phases/999.63-qramm-scorecard-and-visualizations/` |
| BACK-71 | QRAMM Evidence Bridge — Scan-to-Assessment Auto-population | Compliance / governance integration | The killer feature: QUIRK's scanner findings automatically pre-populate QRAMM question answers based on detected evidence, reducing manual assessment effort and grounding governance scores in technical reality. Mapping logic: CVI-1.1 (Cryptographic Discovery & Inventory) — if QUIRK ran automated TLS/SSH/JWT/container/source discovery across the target environment, auto-answer L3-4; CVI-1.2 (Vulnerability Assessment) — if QUIRK produced severity-classified findings with NIST PQC labels, auto-answer L3; DPE-1.1 (Encryption Implementation) — if QUIRK found TLS 1.3 or AES-256 in use, positive evidence; ITR-1.1 (Network Security Architecture) — surface TLS coverage rate and weak-cipher rate as evidence. Pre-populated answers are flagged with a "Auto-filled from scan" badge and remain editable. All 4 CVI foundation questions can be partially auto-populated; SGRM and most advanced questions remain manual (they assess governance processes, not technical artifacts). Requires scan data in DB. Depends on BACK-68. Phase dir: `.planning/phases/999.64-qramm-evidence-bridge-scan-to-assessment-auto-population/` |
| BACK-72 | QRAMM Compliance Mapping View | Compliance / governance integration | Interactive compliance mapping that shows how QRAMM practice scores translate into coverage across 8 major frameworks: NIST Post-Quantum Cryptography Standards, U.S. NSM 10, NSA CNSA 2.0, ISO/IEC 27001:2022, ETSI Quantum-Safe Standards, PCI DSS v4.0, Common Criteria, and BSI TR-02102 (CMMC 2.0 also present in the toolkit). UI: framework selector dropdown, coverage summary (Full Coverage / Partial Coverage / No Coverage counts), detailed mapping table per practice with relevance score and priority (HIGH/MEDIUM/LOW). Relevance scores are static weights from the QRAMM framework (e.g., ITR_2 System Hardening has 1.0 relevance to CMMC 2.0). Scores are dynamic — computed from the active assessment session. This view turns QUIRK's dashboard into a compliance evidence artifact a consultant can screenshot or export. Depends on BACK-68, BACK-70. Phase dir: `.planning/phases/999.65-qramm-compliance-mapping-view/` |
| BACK-73 | QRAMM Report Export — Combined Governance + Technical PDF | Compliance / governance integration | Extend QUIRK's existing PDF export (Playwright-based `/print` route) to include a QRAMM section alongside the existing CBOM/findings report. The combined deliverable is the primary consulting artifact: (1) Executive QRAMM Summary — overall score, maturity level, top 3 strengths/gaps; (2) Dimension Scorecard — table with raw/weighted scores and maturity levels; (3) Radar chart PNG (screenshotted from the scorecard page); (4) Compliance framework mapping summary for 1–2 selected frameworks (consultant picks at export time); (5) Attribution block — "QRAMM v1.0 framework by CSNP (qramm.org), used with attribution." Standalone QRAMM PDF export (without full QUIRK findings) also supported for governance-only delivery. Depends on BACK-70, BACK-72. Phase dir: `.planning/phases/999.66-qramm-report-export/` |
| BACK-74 | TLS finding coverage gaps in risk engine | P1 — UAT validation | Four missing finding rules discovered during chaos lab UAT (2026-04-14). All four bugs share the same root cause: TLS scanner collects rich endpoint data (cert dates, issuer, pubkey alg/size, legacy_suites_present) but `risk_engine.evaluate_endpoints()` has no rules to convert that data into findings. **BUG-01:** `ep.tls_legacy_suites_present=True` (AES128-SHA, AES256-SHA accepted) generates no finding — risk engine only checks for TLS 1.0/1.1. Fix: add LOW finding when `tls_legacy_suites_present=True`. **BUG-02:** `ep.cert_not_after` is extracted but never compared to `datetime.now(UTC)`. Port 9443 (expired cert) produces zero findings. Fix: add HIGH when `cert_not_after < now`; MEDIUM when `cert_not_after < now + 30d`. **BUG-03:** `ep.cert_issuer == ep.cert_subject` (self-signed) is never checked; `chain_verified=False` from sslyze path is never used. Port 10443 generates no finding. Fix: add MEDIUM when self-signed or chain unverified. **BUG-04:** `ep.cert_pubkey_alg` and `ep.cert_pubkey_size` are extracted but risk engine has no quantum-vulnerability rule for TLS cert keys. All four chaos lab TLS ports use RSA. Fix: add MEDIUM for RSA/ECDSA keys; upgrade to HIGH for key sizes below classical minimums (RSA < 2048, ECDSA < 256). Phase dir: `.planning/phases/999.67-tls-finding-coverage-gaps-risk-engine/` |
| BACK-75 | Nmap pre-scan port discovery integration | P1 — scan coverage gap | Port discovery gap found during chaos lab UAT (2026-04-14). Interactive wizard uses a static 17-port `CONSULTING_TLS_PORTS` list; non-standard lab/enterprise ports (11443, 12443, 8000, 8444, 2222, 5555, etc.) are never probed. The fix is to integrate the existing-but-unwired nmap infrastructure (`quirk/discovery/nmap_provider.py` + `nmap_parser.py`) as an optional pre-scan discovery step. Design: before `expand_targets()` builds the `(host, port)` target list, run `run_nmap_discovery()` against all target hosts with a profile-scaled port sweep (`quick` → `--top-ports 100`, `standard` → `--top-ports 1000`, `deep` → `--top-ports 5000`). Use discovered open ports as the actual `ports_tls` input, replacing the static list. Fallback: if nmap is not in PATH, fall back to `CONSULTING_TLS_PORTS` with a console warning. Integration point: add an `enable_port_discovery` flag to `ScanCfg` (default `True`) and wire into the main scan pipeline between config resolution and `expand_targets()`. Add a wizard prompt: "Use nmap for port discovery (recommended)? [Y]". Phase dir: `.planning/phases/999.68-nmap-pre-scan-port-discovery/` |
| BACK-76 | Install identity extras by default / fix identity scanner availability | **P0 — UAT blocker** | UAT-1-07 found that `pip install quirk` does not install the `identity` optional group (`impacket>=0.13`, `lxml>=6.0`, `signxml>=4.4`, `dnspython[dnssec]>=2.8`). Until a user runs `pip install -e ".[identity]"`, all four identity surface scanners (Kerberos, SAML, DNSSEC, OIDC) fail with `ImportError` at startup and UAT series 8 identity scoring tests cannot run. Root cause is a design decision: either (a) promote identity deps to core `[project.dependencies]` — correct if they are first-class shipped scanners, not plugins; or (b) implement graceful degradation — CLI detects missing extras, emits a `pip install quirk[identity]` prompt, and continues with non-identity scans rather than raising uncaught ImportErrors. Decision gate: evaluate impacket build overhead on Python 3.11+ before promoting to core. **Immediate workaround applied 2026-04-13: `pip install -e ".[identity]"` in local venv.** Phase dir: `.planning/phases/999.69-identity-extras-installation-fix/` |
| BACK-77 | Fix multi-target input in interactive wizard | P2 — UAT gap | UAT-2-03 confirmed that the interactive wizard (`quirk` with no args) rejects multiple targets. Both space-separated (`192.168.1.1 192.168.1.2`) and comma-separated (`192.168.1.1,192.168.1.2`) formats produce exit code 1. The wizard was overhauled in Phase 13 but multi-target entry was never explicitly tested. Fix: (1) audit `quirk/interactive.py` prompt handler — find the validation regex or split logic; (2) accept comma- or space-separated hostnames/CIDRs/IPs and produce the correct `targets.fqdns` / `targets.cidrs` / `targets.include_ips` structure; (3) add a regression test. Phase dir: `.planning/phases/999.70-fix-multi-target-interactive-wizard/` |
| BACK-78 | Identity scoring evidence keys missing from intelligence.json | P2 — UAT gap | UAT-8-09/10/11 failed because `identity_kerberos_weak_etype_ratio`, `identity_saml_weak_signing_ratio`, and `identity_dnssec_weak_algo_ratio` were absent from `intelligence-*.json`. Root cause: the chaos lab scan targeted `127.0.0.1` on TLS/SSH ports only — Kerberos KDC (port 88/749), SAML/OIDC endpoints, and DNSSEC resolvers from the identity containers were never scanned. These keys only appear when the respective scanner finds weak algorithms. Fix: (1) add identity-profile containers to `quantum-chaos-enterprise-lab` (Kerberos KDC with DES/RC4 etypes, SAML SP with SHA-1 signing, DNSSEC zone with MD5/SHA-1 RRSIGs); (2) extend `config.yaml` to include identity ports and targets; (3) re-run UAT-8-09/10/11. Scoring code is correct — this is a lab coverage gap, not a code bug. Related: BACK-74, BACK-75. Phase dir: `.planning/phases/999.71-identity-scoring-evidence-lab-targets/` |
| BACK-79 | Rich finding context — per-finding quantum risk explanation, severity rationale, and PQC remediation | Dashboard / Intelligence | Each finding in the dashboard and reports should carry: (1) a plain-language explanation of what the detected weakness is and why it matters cryptographically; (2) a severity rationale explaining why it was rated CRITICAL/HIGH/MEDIUM/LOW (e.g., "rated CRITICAL because RSA-1024 falls below NIST minimum and is broken by Shor's algorithm in polynomial time on a fault-tolerant quantum computer"); (3) a quantum-specific remediation roadmap entry — not just "upgrade TLS" but "migrate to CRYSTALS-Kyber (ML-KEM) for key exchange and CRYSTALS-Dilithium (ML-DSA) for signatures per NIST FIPS 203/204" with a timeframe. This functions like a vulnerability scanner advisory but anchored to the NIST PQC migration timeline. Backend: extend `FindingItem` schema with `risk_explanation`, `severity_rationale`, and `pqc_remediation` fields; populate in `_derive_findings()` and `_derive_identity_findings()` per finding type. Frontend: expand finding cards in the Findings and Identity pages to surface these fields — collapsed by default, expandable on click. Phase dir: `.planning/phases/999.72-rich-finding-context-per-finding-quantum-risk-explanation-se/` |
| BACK-80 | Chaos lab — PostgreSQL with TLS target | Chaos lab gap | Add a `postgres-tls` service to `docker-compose.yml` (profile: `db-tls`) running PostgreSQL 16 with SSL enabled using the lab's existing `modern.crt`/`modern.key` certs. Also add a `postgres-tls-weak` variant using the SHA-1 or RSA-1024 scenario certs from `certs/scenarios/` to exercise the database TLS weak-cipher finding path. `postgres-plain` and `redis-plain` already exist in the lab but neither exercises the TLS scanner against a database endpoint — a very common real-world gap. Pair with a `redis-tls` service (Redis 7 with `--tls-port 6380`) for completeness. Updates needed: `docker-compose.yml`, lab README, relevant `config.yaml` profiles. Phase dir: `.planning/phases/999.73-chaos-lab-postgres-redis-tls/` |
| BACK-81 | Chaos lab — OQS-nginx PQC-hybrid TLS endpoint | Chaos lab gap — quantum scoring ceiling | Add an `oqs-nginx` service (profile: `pqc`) using the Open Quantum Safe project's pre-built `openquantumsafe/nginx` image. Configure it to negotiate `X25519Kyber768` (hybrid ECDH + ML-KEM) in TLS 1.3, serving the lab's CA-signed cert. This is the only chaos lab target that would score *above* "good classical TLS" in QUIRK's quantum readiness model — it demonstrates what a PQC-capable endpoint looks like to the scanner and grounds the scoring ceiling in a concrete, testable artifact. Critical for client demos: shows the before/after contrast. Port: `25443`. Also requires a QUIRK scanner update to detect and reward PQC-hybrid key exchange in the scoring model (currently no rule exists for this). Related: BACK-12 (database encryption detection). Phase dir: `.planning/phases/999.74-chaos-lab-oqs-nginx-pqc-hybrid/` |
| BACK-82 | Chaos lab — SMTP/STARTTLS service | Chaos lab gap | Add a `postfix-starttls` service (profile: `smtp`) running Postfix configured for STARTTLS on port 587, with a weak TLS configuration (TLS 1.0/1.1 enabled, legacy cipher suite). Email infrastructure is among the most commonly misconfigured TLS surfaces in enterprise environments and currently has no representation in the lab. QUIRK's TLS scanner should be able to probe SMTP STARTTLS negotiation (sslyze supports this via `--starttls smtp`). Add a second `postfix-tls-modern` variant on port 465 (implicit TLS) as the "good" baseline. Updates needed: `docker-compose.yml`, lab README, `config.yaml` smtp profile. Related: BACK-16 (email protocol scanning feature). Phase dir: `.planning/phases/999.75-chaos-lab-smtp-starttls/` |
| BACK-83 | Chaos lab — gRPC service with TLS | Chaos lab gap | Add a `grpc-tls` service (profile: `grpc`) — a minimal gRPC echo server (Go or Python) with TLS 1.3 using the lab's CA-signed cert on port `50051`. gRPC (HTTP/2 + TLS) is the dominant internal microservice protocol in cloud-native stacks and has its own TLS negotiation fingerprint that differs from HTTPS. Also add a `grpc-insecure` variant on port `50052` (gRPC without TLS, plaintext) to trigger a plaintext-on-service-port finding. Both targets let QUIRK validate that the TLS scanner handles HTTP/2 ALPN negotiation correctly. Updates: `docker-compose.yml`, lab README, scanner probe to send HTTP/2 ClientHello via sslyze. Phase dir: `.planning/phases/999.76-chaos-lab-grpc-tls/` |
| BACK-84 | Chaos lab — Kafka with TLS | Chaos lab gap | Add a `kafka-tls` service (profile: `kafka`) using `confluentinc/cp-kafka` or `bitnami/kafka` with TLS listener on port `9093` (plaintext `PLAINTEXT://9092` also exposed). Configure with the lab's CA-signed cert for the broker. Kafka TLS is extremely common in data/platform engineering stacks and is frequently misconfigured (plaintext fallback left enabled, weak cipher suites, no mutual TLS between brokers). The lab already has RabbitMQ (plaintext) and Redis (plaintext) — Kafka closes the message-broker picture. Requires a Zookeeper or KRaft controller container alongside the broker. Updates: `docker-compose.yml`, lab README, `config.yaml` kafka profile. Phase dir: `.planning/phases/999.77-chaos-lab-kafka-tls/` |
| BACK-85 | Add `ports_scanned` list to run-stats output | **P1 — UAT observability gap** | `run-stats-*.json` records `targets_total: 17` (count) but not which ports were actually probed, making UAT pass criteria like "ports 636, 6443, 8200 present in scanned set" unverifiable from the output file alone. Fix: in `run_scan.py` at the `run_stats["counts"]` block (line 337), add `"ports_scanned": sorted(set(p for _, p in targets))` so the stats file explicitly lists every port that entered the scan pipeline. Also add `"hosts_scanned": sorted(set(h for h, _ in targets))` for symmetry. Both fields are derivable from the existing `targets` list — no new data collection required. This closes a UAT verification gap (UAT-3-02 port list check) and makes `run-stats` genuinely useful as a machine-readable scan manifest. Phase dir: `.planning/phases/999.78-run-stats-ports-scanned-field/` |
| BACK-86 | Dashboard-initiated scan configuration, launch, and reporting | Dashboard / UX — broaden user reach | Not every consultant or IT generalist is comfortable in a terminal, no matter how good the CLI documentation is. Add a guided "New Scan" flow to the web dashboard so a user can configure a scan, launch it, watch it run, and read the report without ever touching the command line. **Primary target: SaaS model** (where dashboard-driven scans are table-stakes); **secondary target: standalone version** as a nice-to-have for the local CLI+dashboard install. Three surfaces to design: (1) **Configuration** — a wizard UI mirroring the interactive CLI prompts (targets via single host / comma list / file upload / CIDR; scan profile selection; optional extras enable/disable; nmap discovery toggle) writing a `ScanCfg` JSON the backend can consume; persist named scan configs ("Customer X TLS audit", "Kerberos sweep") for re-use. (2) **Launch & live status** — POST to a scan-launch API endpoint, stream progress (current target, phase, finding count) over WebSocket or SSE, surface per-scanner status including any `coverage_gap` advisories from Phase 45 in real time. Cancellation control. (3) **Reporting** — auto-route to the existing dashboard report views when the run completes; one-click HTML/PDF export from the same UI; scan history list with re-run / clone / compare-to-previous actions. **Auth & multi-tenancy considerations apply only in SaaS** — for standalone, single-user assumed. **Dependencies:** existing `quirk/dashboard/api/` FastAPI surface, existing report renderers (`quirk/reports/html_renderer.py`, `quirk/dashboard/api/routes/pdf.py`), `quirk/interactive.py` as the reference for the wizard's question set. **Caveats:** standalone mode needs the dashboard to run a scan in a subprocess (today's CLI flow assumes foreground execution); SaaS mode needs job queueing + per-tenant data isolation. Likely splits into multiple phases when promoted (one for config UI, one for launch+streaming, one for SaaS-only auth/multi-tenancy). Phase dir: `.planning/phases/999.79-dashboard-scan-config-launch-reporting/` |
| BACK-87 | Fix `lab.sh` so command-line `PROFILE_ARGS` overrides `.env` defaults | P2 — chaos lab harness bug | Discovered during Phase 46 Plan 03 live-fire verification (2026-05-03). `quantum-chaos-enterprise-lab/lab.sh` sources `.env` with `set -a` (lines 4–9) BEFORE the `PROFILE_ARGS="${PROFILE_ARGS:-}"` default-fallback line. Because `.env` sets `PROFILE_ARGS="--profile phaseA --profile cloud --profile identity --profile pki"`, any inline `PROFILE_ARGS=... ./lab.sh up` invocation is silently overwritten by the `.env` value — the `:-` fallback never fires because `PROFILE_ARGS` is no longer empty. **Symptom:** `PROFILE_ARGS="--profile tls-cert-defects" ./lab.sh up` brings up the four default profiles instead of the user-requested one; new profile services never start; ports 13444–13447 don't bind. **Impact:** Violates the CLAUDE.md chaos-lab maintenance rule that says "New profiles must be runnable via `PROFILE_ARGS=\"--profile <name>\" ./lab.sh up` with no further script edits needed." Currently every Phase 46+ chaos-lab profile addition requires hand-editing `.env` to use it, defeating the purpose of the env-var contract. **Fix (one-liner):** snapshot the inbound env value before sourcing `.env`, then prefer the snapshot if non-empty, e.g. `_USER_PROFILE_ARGS="${PROFILE_ARGS:-}"; source .env; PROFILE_ARGS="${_USER_PROFILE_ARGS:-${PROFILE_ARGS:-}}"`. Add a smoke test: `PROFILE_ARGS="--profile tls-cert-defects" ./lab.sh up` should print `profiles='--profile tls-cert-defects'` in its header and start exactly the 4 cert-defect services. **Workaround until fixed:** invoke docker compose directly — `docker compose -p chaoslab --profile tls-cert-defects up -d <services>`. Source: Phase 46 Wave 2 verification step. Phase dir: `.planning/backlog/999.80-lab-sh-profile-args-cli-precedence/` |
| BACK-88 | **[P1 — UI] Obsidian Pro design system — full dashboard implementation** | Dashboard / UX — visual polish & consulting-grade presentation | Implement the Obsidian Pro design system across the QUIRK React dashboard. Design source: `digs-design-system` bundle (exported 2026-05-07 from claude.ai/design). Foundation tokens were applied in 2026-05-07 hotfix (teal accent, dark palette alignment, JetBrains Mono @font-face, --ds-* custom properties, utility classes). The remaining work spans five component areas: **(1) Stat card redesign** — replace the current executive page metric cards with the Obsidian Pro three-layer pattern: 10px ALL-CAPS eyebrow label (`.label-eyebrow`), large bold mono metric (`.stat-metric`, 30px–40px), delta caption; severity-tinted border on critical cards (`--ds-critical-bdr`). **(2) Findings table rows** — add severity dot indicator (4px circle, `--ds-critical/high/ok/medium`), tabular figures on all numeric cells (`font-feature-settings: 'tnum'`), row hover using `--ds-bg-surface`, and severity-chip badges using the new `.severity-*-chip` utility classes. **(3) Detail drawer** — slide-in panel from the right when a findings row is clicked (mirrors the `DetailDrawer.jsx` in `ui_kits/command/`); shows host, protocol, finding title, algorithm, severity badge, evidence, and action buttons (Investigate / Assign / Dismiss). **(4) Nav rail** — align sidebar with Obsidian Pro's 52px icon-only collapsed rail and 200px expanded state; active item gets `--ds-accent` left border + icon tint; scan selector moves to a header bar above main content. **(5) CBOM page table** — all algorithm name cells use `.font-data` (JetBrains Mono, tnum); NIST level rendered as a severity chip instead of plain text; FIPS status annotation rendered as a chip (COMPLY-10 field). **Design source files preserved at:** `/tmp/design_extracted/digs-design-system/` — copy to a stable project location before implementing (e.g. `design/obsidian-pro/`). Reference `ui_kits/command/` for component patterns; `ds-tokens.css` and `colors_and_type.css` for token values; `preview/` HTMLs for visual ground-truth. **Scope note:** the 0xD1g5 brand mark SVG (`assets/0xD1g5_128.svg`) may replace the QU.I.R.K. text wordmark in the sidebar; discuss with stakeholder before swapping. Phase dir: `.planning/phases/999.81-obsidian-pro-dashboard-implementation/` |

---

## Progress

**Execution Order:**
v3.9 complete. v4.1 complete. v4.2 complete. v4.3 complete. v4.4 complete (shipped 2026-04-29, tag v4.4.0). v4.5 complete (shipped 2026-05-03, tag v4.5.0). v4.6 complete (shipped 2026-05-05, tag v4.6.0).

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Foundation Fixes | v3.9 | 4/4 | Complete | 2026-03-29 |
| 2. CBOM Pipeline | v3.9 | 3/3 | Complete | 2026-03-29 |
| 3. Scanner Coverage | v3.9 | 4/4 | Complete | 2026-03-29 |
| 4. Chaos Lab Expansion | v3.9 | 5/5 | Complete | 2026-03-30 |
| 5. Web Dashboard | v3.9 | 6/6 | Complete | 2026-03-31 |
| 6. Documentation | v3.9 | 6/6 | Complete | 2026-03-31 |
| 7. Polish and Packaging | v3.9 | 5/5 | Complete | 2026-04-01 |
| 8. Legacy Debt Cleanup | v3.9 | 4/4 | Complete | 2026-04-03 |
| 9. Scoring Consolidation | v3.9 | 3/3 | Complete | 2026-04-03 |
| 10. v3.9 Gap Closure | v3.9 | 2/2 | Complete | 2026-04-04 |
| 11. Dashboard Wiring Fixes | v3.9 | 2/2 | Complete | 2026-04-04 |
| 12. CLI Correctness | v4.1 | 2/2 | Complete | 2026-04-06 |
| 13. Interactive Mode Overhaul | v4.1 | 2/2 | Complete | 2026-04-06 |
| 14. Scoring & Intelligence Correctness | v4.1 | 2/2 | Complete | 2026-04-07 |
| 15. Code Hygiene | v4.1 | 2/2 | Complete | 2026-04-08 |
| 16. v4.1 Gap Closure | v4.1 | 2/2 | Complete | 2026-04-08 |
| 17. Identity Infrastructure | v4.2 | 2/2 | Complete | 2026-04-08 |
| 18. DNSSEC Scanner | v4.2 | 2/2 | Complete | 2026-04-09 |
| 19. SAML/OIDC Scanner | v4.2 | 2/2 | Complete | 2026-04-09 |
| 20. Kerberos Scanner | v4.2 | 2/2 | Complete | 2026-04-09 |
| 21. Identity Surface | v4.2 | 2/2 | Complete | 2026-04-10 |
| 22. v4.2 Gap Closure | v4.2 | 1/1 | Complete | 2026-04-16 |
| 23. DNSSEC CBOM Skip Fix | v4.2 | 1/1 | Complete | 2026-04-24 |
| 24. Scan-Session Timestamp Isolation | v4.2 | 2/2 | Complete | 2026-04-24 |
| 25. Identity Findings Accuracy | v4.3 | 3/3 | Complete    | 2026-04-24 |
| 26. GCP Connector | v4.3 | 3/3 | Complete    | 2026-04-25 |
| 27. Database Encryption Detection | v4.3 | 4/4 | Complete    | 2026-04-25 |
| 28. Object Storage Audit | v4.3 | 3/3 | Complete    | 2026-04-26 |
| 29. Kubernetes Secrets Inspection | v4.3 | 4/4 | Complete    | 2026-04-26 |
| 30. HashiCorp Vault Connector | v4.3 | 3/3 | Complete    | 2026-04-26 |
| 31. Trend Analysis | v4.3 | 4/4 | Complete    | 2026-04-26 |
| 32. Email Scanner | v4.4 | 8/8 | Complete   | 2026-04-27 |
| 33. Broker Scanner | v4.4 | 8/8 | Complete   | 2026-04-28 |
| 34. Motion Intelligence | v4.4 | 3/3 | Complete   | 2026-04-28 |
| 35. CBOM Integration | v4.4 | 4/4 | Complete   | 2026-04-28 |
| 36. Dashboard Motion Tab | v4.4 | 4/4 | Complete*  | 2026-04-29 |
| 37. Gap Closure and v4.4.0 Release | v4.4 | 6/6 | Complete   | 2026-04-29 |
| 38. Identity API Regression Fix | v4.5 | 4/4 | Complete   | 2026-04-29 |
| 39. Data at Rest Dashboard Tab | v4.5 | 5/5 | Complete   | 2026-04-29 |
| 40. Chaos Lab Parity | v4.5 | 6/6 | Complete   | 2026-04-29 |
| 41. CI Stability & Scanner Robustness | v4.5 | 7/7 | Complete   | 2026-04-29 |
| 42. CBOM Correctness Audit | v4.5 | 6/6 | Complete   | 2026-04-30 |
| 43. Dashboard Polish | v4.5 | 6/6 | Complete   | 2026-05-01 |
| 44. UAT Debt Automation | v4.5 | 6/6 | Complete   | 2026-05-03 |
| 45. Install-Day UX | v4.6 | 4/4 | Complete | 2026-05-03 |
| 46. TLS Finding Gaps | v4.6 | 4/4 | Complete | 2026-05-03 |
| 47. Nmap Discovery + Multi-Target Wizard | v4.6 | 3/3 | Complete | 2026-05-04 |
| 48. Rich Finding Context | v4.6 | 3/3 | Complete | 2026-05-04 |
| 49. Compliance Mapping | v4.6 | 5/5 | Complete | 2026-05-05 |
| 50. Enterprise Documentation | v4.6 | 5/5 | Complete | 2026-05-05 |

## Phase Details (v4.5) — SHIPPED 2026-05-03

### Phase 38: Identity API Regression Fix
**Goal**: SAML and OIDC findings are restored in the `/api/scan/latest` `identity_findings[]` response, the deferred SAML scan-window pytest passes GREEN, and Phase 36 wave_0_complete is flipped to `true`
**Depends on**: Phase 37
**Requirements**: GAP-01, GAP-02, GAP-03
**Success Criteria** (what must be TRUE):
  1. A scan against the SimpleSAMLphp chaos lab profile returns SAML entries in `identity_findings[]` from `GET /api/scan/latest` — no empty array when SAML findings exist
  2. The previously `skip`/`xfail` SAML scan-window pytest runs without skip markers and passes GREEN in CI
  3. `36-VALIDATION.md` reads `nyquist_compliant: true, wave_0_complete: true` — DEF-v4.4-01 closed
  4. Full test suite passes with no regressions after the SAML fix (662+ tests, 0 failures)
**Plans**: 4 plans
  - [x] 38-01-PLAN.md — Fix scan-window in scan.py (SESSION_BRACKET 5-min backward bracket) + extend regression test (GAP-01, GAP-02)
  - [x] 38-02-PLAN.md — Restore 36-VALIDATION.md from commit 99f48d2 and flip wave_0_complete: true (GAP-03)
  - [x] 38-03-PLAN.md — Scope test_all_completed_phase_validations_nyquist_compliant to skip-on-missing (full suite green)
  - [x] 38-04-PLAN.md — STATE.md + UAT-SERIES.md + Obsidian phase note + commit (mandatory close-out per CLAUDE.md)

### Phase 39: Data at Rest Dashboard Tab
**Goal**: The React dashboard has a "Data at Rest" tab that surfaces DB encryption, object storage policy, Kubernetes secrets, and Vault findings from the existing v4.3 data shape — consultants can review the full DAR surface without leaving the dashboard
**Depends on**: Phase 37 (can run parallel to Phase 38 — no shared code)
**Requirements**: GAP-04
**Success Criteria** (what must be TRUE):
  1. A "Data at Rest" tab is visible in the dashboard navigation alongside Identity, Motion, Trends, and Findings
  2. The tab displays per-category sections for database encryption, object storage, Kubernetes secrets, and Vault findings drawn from the existing v4.3 `dat_scan_json` / `dar_*` evidence fields
  3. Empty state is shown when no DAR scan data exists — no crash, no blank panel
  4. The DAR tab route appears in the browser console with zero errors
**Plans**: 5 plans
Plans:
- [x] 39-01-PLAN.md — Wave 0 RED test scaffold (tests/test_dar_dashboard.py with 8 failing tests + extended _ep fixture)
- [x] 39-02-PLAN.md — Backend: DarFinding schema + _derive_dar_findings projection + TS type mirror
- [x] 39-03-PLAN.md — Frontend skeleton: data-at-rest.tsx + App.tsx route + sidebar.tsx NAV_ITEMS (lockstep)
- [x] 39-04-PLAN.md — Per-category tables: DatabaseTable, ObjectStorageTable, KubernetesTable, VaultTable
- [x] 39-05-PLAN.md — Validation, UAT-SERIES.md update, Obsidian sync, commit
**UI hint**: yes

### Phase 40: Chaos Lab Parity
**Goal**: `lab.sh`, the README, and a new `expected_results_v4.md` oracle document fully cover every profile shipped through v4.4 so consultants running the lab see complete scanner-equivalent coverage and UAT can reference a stable oracle
**Depends on**: Phase 37
**Requirements**: LAB-01, LAB-02, LAB-03, LAB-04
**Success Criteria** (what must be TRUE):
  1. `./lab.sh all` starts every profile defined in `docker-compose.yml` including v4.3 additions (`database`, `storage-s3`, `vault`) and v4.4 additions (`email`, `broker`) — no missing or broken profile names
  2. `./lab.sh status` and `./lab.sh logs <service>` work cleanly against all v4.3 and v4.4 profiles with no orphan containers or broken service name references
  3. `quantum-chaos-enterprise-lab/README.md` documents every shipped profile (v4.0 through v4.4) with port assignments, expected scanner findings, and any required setup steps
  4. `expected_results_v4.md` exists and contains the expected-output oracle for all v4.3 and v4.4 profiles (DB, object storage, K8s, Vault, email, broker) — usable as a UAT reference
**Plans**: 6 plans
  - [x] 40-01-PLAN.md — lab.sh dynamic profile parser + profiles subcommand (LAB-01, LAB-02)
  - [x] 40-02-PLAN.md — expected_results_v4.md listener-profile sections (LAB-03)
  - [x] 40-03-PLAN.md — expected_results_v4.md DAR + messaging sections (LAB-03)
  - [x] 40-04-PLAN.md — README.md rewrite with Profile Summary Table (LAB-02)
  - [x] 40-05-PLAN.md — docs/chaos-lab.md extension for v4.2/v4.3/v4.4 (LAB-02)
  - [x] 40-06-PLAN.md — UAT-SERIES update + Obsidian sync + LAB-04 smoke + close (LAB-01..04)

### Phase 41: CI Stability & Scanner Robustness
**Goal**: The CI test suite runs green with zero skipped-for-code-reasons tests and completes deterministically in under 60 seconds; all scanners degrade gracefully under missing extras, slow targets, and unexpected exceptions with a consistent, documented timeout/retry policy
**Depends on**: Phase 38, Phase 40
**Requirements**: CI-01, CI-02, CI-03, ROBUST-01, ROBUST-02, ROBUST-03, ROBUST-04
**Success Criteria** (what must be TRUE):
  1. `pytest` runs to completion with zero `skip`/`xfail` markers on tests deferred for code reasons (live-infra skips remain acceptable); the SAML scan-window test from Phase 38 is GREEN
  2. Running a scan with `[motion]` not installed produces a clear advisory message and completes normally using the remaining scanners — no ImportError crash
  3. A scan against a target that exceeds the per-scanner timeout budget does not stall indefinitely; the overall scan finishes within the documented upper-bound time
  4. An unexpected scanner exception is captured in `scan_errors[]` with scanner name, target, and reason — the scan continues and other scanners produce normal output
  5. Timeout, retry count, and backoff defaults are defined in a single location and documented; divergences found in the audit are reconciled
  6. The default `pytest` run (excluding `pytest.mark.slow`) finishes in under 60 seconds on a developer machine
**Plans**: 7 plans
- [x] 41-01-PLAN.md — Wave 0 test infrastructure: pytest config, skip registry + AST-walk meta-gate, scan_error_category column, ROBUST/Timeouts test stubs
- [x] 41-02-PLAN.md — TimeoutsCfg / RetryCfg sub-tables on ScanCfg with deprecation-alias properties (D-06/D-07)
- [x] 41-03-PLAN.md — Remove BACK-45 cfg.scan mutation in run_scan.py (D-08); fix run_scan.py:743 cfg.scan.profile bug; route all timeouts through cfg.scan.timeouts
- [x] 41-04-PLAN.md — D-14 BaseException wrapper around every scanner phase; D-12 missing-extra advisories; D-15 trends.py category-aware error counting
- [x] 41-05-PLAN.md — Delete 13 stale code-reason skips; convert defensive skips to pytest.fail; mark 9 slow-test candidates; meta-gate green
- [x] 41-06-PLAN.md — docs/configuration.md timeout/retry policy + upper-bound formula (D-10); docs/timeout-retry-audit.md (ROBUST-04); lab.sh down+reset profile-sweep fix (D-18)
- [ ] 41-07-PLAN.md — Phase closure: docs/UAT-SERIES.md update + vault sync; Obsidian phase note; ROADMAP/STATE complete

### Phase 42: CBOM Correctness Audit
**Goal**: CycloneDX CBOM output is spec-valid, every in-scope algorithm is classified (no unknown fallbacks), golden snapshot drift is intentional and documented, and Pass-2/3 skip-list logic is fully unit-tested
**Depends on**: Phase 40
**Requirements**: CBOM-01, CBOM-02, CBOM-03, CBOM-04
**Success Criteria** (what must be TRUE):
  1. Automated pytest checks validate CBOM JSON and XML against the official CycloneDX 1.6 schema for every shipped chaos lab profile — zero schema violations
  2. A classifier coverage report shows every algorithm name observed in test fixtures and chaos labs is mapped to a NIST PQC classification with no `unknown` fallback for any in-scope case
  3. All golden snapshot differences between v4.4 and v4.5 are intentional: each changed snapshot has a rationale comment and an accompanying commit message explaining why
  4. Pass-2 and Pass-3 skip-list logic has unit tests covering all motion plaintext labels and all v4.3 DAR skip cases — no untested skip paths remain
**Plans:** 6/6 complete
Plans:
- [x] 42-01-PLAN.md — Wave 0 prerequisites: pyproject.toml [validation] extras pin + extract MOTION_PLAINTEXT_PROTOCOLS / DAR_SKIP_PROTOCOLS constants in builder.py (CBOM-01, CBOM-04)
- [x] 42-02-PLAN.md — Schema validation harness: per-profile JSON+XML CycloneDX 1.6 gate + docker-compose drift sentinel (CBOM-01)
- [x] 42-03-PLAN.md — Shape goldens: 3 new endpoint synthesizers (pki/vault/saml), 3 new snapshot tests, fixtures + CHANGELOG.md (CBOM-03)
- [x] 42-04-PLAN.md — Classifier coverage gate + regen report (docs/cbom-classifier-coverage.md); close any _ALGORITHM_TABLE gaps (CBOM-02)
- [x] 42-05-PLAN.md — Pass-2/Pass-3 skip-list parametrized unit tests driven off MOTION_PLAINTEXT_PROTOCOLS | DAR_SKIP_PROTOCOLS (CBOM-04)
- [x] 42-06-PLAN.md — Phase closeout: docs/UAT-SERIES.md UAT-42-01..04 + vault sync + Obsidian phase note + final compileall+pytest + commit

### Phase 43: Dashboard Polish
**Goal**: All top-level dashboard routes render cleanly — zero browser console errors, zero React warnings, explicit loading states on first paint, explicit empty states when data is absent, and WCAG AA baseline accessibility
**Depends on**: Phase 39, Phase 42
**Requirements**: DASH-01, DASH-02, DASH-03
**Success Criteria** (what must be TRUE):
  1. Opening `/motion`, `/trends`, `/findings`, `/data-at-rest`, and all other top-level routes in a browser shows zero console errors and zero React warnings
  2. Each route displays an explicit loading spinner or skeleton on first paint and an explicit "no data" empty state when scan data is missing — no flash of raw empty content
  3. All interactive dashboard elements (tabs, buttons, table filters, navigation links) are reachable and operable via keyboard navigation with visible focus indicators
  4. Semantic heading hierarchy is correct on all routes and color contrast on findings tables passes WCAG AA — verified by automated axe-core or equivalent check
**Plans**: 4 plans
Plans:
- [x] 43-01-PLAN.md — Test harness infrastructure: @axe-core/puppeteer + console capture + Vite fixture middleware + routes/fixtures/allowlist (DASH-01, DASH-02, DASH-03)
- [x] 43-02-PLAN.md — Page polish sweep: extract EmptyStateCard, create PageSpinner, layout-matched skeletons, heading hierarchy across 9 routes (DASH-01, DASH-02, DASH-03)
- [x] 43-03-PLAN.md — Sidebar focus-visible utilities + color-contrast audit via CSS variable tokens (DASH-03)
- [x] 43-04-PLAN.md — Capture axe baselines, expand allowlist, GHA dashboard-quality workflow, UAT-SERIES + vault + validation flip close-out (DASH-01, DASH-02, DASH-03)
**UI hint**: yes

### Phase 44: UAT Debt Automation
**Goal**: Phase 27 DB, Phase 29 K8s, Phase 25 identity, and Phase 30 Vault UAT scenarios that are automatable against existing chaos lab profiles are moved from `deferred` to `passing`; the STATE.md Deferred Items table reflects at least a 50% net reduction in carry-over items
**Depends on**: Phase 40, Phase 41, Phase 42, Phase 43
**Requirements**: UAT-01, UAT-02, UAT-03, UAT-04
**Success Criteria** (what must be TRUE):
  1. Phase 27 DB UAT scenarios that the existing `database` chaos lab profile can simulate run in CI and pass — items move from `pending`/`partial` to `passing`
  2. Phase 29 K8s UAT scenarios that a local minikube or kind fixture can simulate run in CI and pass; cloud-managed encryption (EKS/GKE/AKS) cases are explicitly documented as cloud-only
  3. Phase 25 identity and Phase 30 Vault UAT scenarios with existing chaos lab profiles are re-run; failing scenarios receive fixes or explicit `cloud-only` justification with rationale
  4. The `## Deferred Items` table in `STATE.md` shows a net reduction of at least 50% of the 14 pre-v4.5 carry-over items — each closed item shows `automated` or `cloud-only` disposition
**Plans**: 6 plans
  - [x] 44-01-PLAN.md — Phase 27 DB UAT live integration tests against `database` chaos lab profile (PostgreSQL :25432, MySQL :23306) with skip_registry entries
  - [x] 44-02-PLAN.md — Phase 25 identity UAT traceability annotations on existing test_kerberos_scanner + test_saml_scanner integration tests
  - [x] 44-03-PLAN.md — Phase 30 Vault UAT live integration test (UAT-30-01 5-finding spec) against `vault` chaos lab profile (vault-30 :28200)
  - [x] 44-04-PLAN.md — Phase 31 VERIFICATION seeded-DB test for /api/trends flat wire format
  - [x] 44-05-PLAN.md — Phase 43 CR fixes (CR-02 ValueError, WR-01 finally block, WR-03 data_in_motion subscore, WR-04 scope=col on TableHead)
  - [x] 44-06-PLAN.md — STATE.md Deferred Items closure (7 rows, ≥50% net reduction)

---

## Phase Details — v4.6 Enterprise Readiness

### Phase 45: Install-Day UX
**Goal**: Users can install QUIRK with `pip install quirk` or `pip install quirk[all]` and run a scan without ImportError crashes, receiving visible advisory notices when optional scanner extras are absent
**Depends on**: Phase 44 (v4.5 complete)
**Requirements**: INSTALL-01, INSTALL-02, INSTALL-03, INSTALL-04
**Success Criteria** (what must be TRUE):
  1. User runs `pip install quirk` in a clean venv, executes a TLS-only scan, and receives a scan report with zero ImportError tracebacks
  2. User runs a full scan with identity/db/vault/motion extras absent and sees a `missing_extra` advisory finding in the report for each skipped scanner — no silent skips
  3. User runs `pip install quirk[all]` and all scanner extras install successfully; impacket is NOT in `[all]` — it stays in `[identity]` only to avoid the pyOpenSSL transitive conflict
  4. The advisory message for each unavailable scanner names the exact extra to install (e.g., "install quirk[identity] for Kerberos scanning")
**Plans**: 4 plans
  - [x] 45-01-PLAN.md — `[all]` meta-extra + impacket-exclusion regression
  - [x] 45-02-PLAN.md — Centralized optional-extra registry + probe wiring
  - [x] 45-03-PLAN.md — Risk engine, renderer, dashboard DTO, score exclusion (Wave 2)
  - [x] 45-04-PLAN.md — Manual checkpoint + UAT-SERIES.md + vault sync + phase note (Wave 3)

### Phase 46: TLS Finding Gaps
**Goal**: Users receive actionable security findings for expired certificates, self-signed certificates, untrusted-CA certificates, and weak RSA/EC keys — certificate defects that previously produced zero findings in the report
**Depends on**: Phase 45
**Requirements**: TLS-FIND-01, TLS-FIND-02, TLS-FIND-03, TLS-FIND-04, TLS-FIND-05, TLS-FIND-06, TLS-FIND-07
**Success Criteria** (what must be TRUE):
  1. Scanning an expired TLS certificate produces a CRITICAL finding; scanning a self-signed certificate produces a HIGH finding; scanning a cert where issuer != subject and chain verification fails produces a MEDIUM untrusted-CA finding (three distinct finding types, three distinct severity levels)
  2. Scanning a TLS endpoint with an RSA key < 2048 bits produces a HIGH finding; scanning one with an EC key < 256 bits produces a HIGH finding
  3. When sslyze `CERTIFICATE_INFO` returns ERROR, the scanner falls back to the ssl_info path cleanly — no half-populated `CryptoEndpoint` with `cert_not_after = None` reaches the database
  4. The `tls-cert-defects` chaos lab profile is running and QUIRK scanning it produces all expected findings: expired cert CRITICAL, self-signed HIGH, untrusted-CA MEDIUM, and RSA-1024 weak-key HIGH
**Plans**: 4 plans
  - [x] 46-01-PLAN.md — Schema + scanner wiring (chain_verified column, ALTER TABLE migration, sslyze + fallback plumbing, D-01 validation gate)
  - [x] 46-02-PLAN.md — Risk engine refactor: severities (TLS-FIND-01 CRITICAL, TLS-FIND-02 HIGH) + D-04 mutual exclusivity branch split + existing-test updates
  - [x] 46-03-PLAN.md — Chaos lab `tls-cert-defects` profile (4 services on 13444-13447, untrusted-CA cert generation, README + expected_results sync)
  - [x] 46-04-PLAN.md — UAT-SERIES.md + Obsidian phase note + Roadmap/Hub sync + live-fire end-to-end UAT

### Phase 47: Nmap Discovery + Multi-Target Wizard
**Goal**: Users can feed QUIRK comma-separated hosts, a target file, or a CIDR range, and optionally pre-discover open ports with nmap — enabling real enterprise 50-host+ scans without manual port enumeration
**Depends on**: Phase 45 (parallel to Phase 46)
**Requirements**: DISCOVER-01, DISCOVER-02, DISCOVER-03, DISCOVER-04, MULTI-01, MULTI-02, MULTI-03, MULTI-04, MULTI-05
**Success Criteria** (what must be TRUE):
  1. User enters `host1,host2,host3` in the interactive wizard prompt and all three hosts are scanned in a single run
  2. User enters `@/path/to/targets.txt` in the wizard (one host per line, `#`-prefixed comment lines ignored) and all listed hosts are scanned; `--targets-file <path>` CLI flag achieves the same for non-interactive bulk runs
  3. User enters a CIDR range (e.g., `192.0.2.0/24`) and QUIRK expands it via stdlib `ipaddress` and scans all resulting hosts
  4. User enables nmap discovery in the interactive wizard prompt; nmap runs with `--max-parallelism 100`; if nmap binary is absent, a clear warning is printed and scanning proceeds on default ports (no crash)
  5. User is warned before nmap invocation when `len(targets) × len(ports) > 10,000`; a malformed target or missing targets file produces a clear error message, not a silent failure or unhandled exception
**Plans**: 3 plans
  - [ ] 45-01-PLAN.md — `[all]` meta-extra + impacket-exclusion regression
  - [ ] 45-02-PLAN.md — Centralized optional-extra registry + probe wiring
  - [ ] 45-03-PLAN.md — Risk engine, renderer, dashboard DTO, score exclusion, docs sync

### Phase 48: Rich Finding Context
**Goal**: Every finding emitted by QUIRK carries a non-empty plain-English risk description and, where quantum-relevant, a FIPS 203/204/205 remediation path with NIST IR 8547 deprecation deadlines — with all stale "Kyber"/"Dilithium" terminology purged from the codebase
**Depends on**: Phase 46
**Requirements**: CONTEXT-01, CONTEXT-02, CONTEXT-03, CONTEXT-04
**Success Criteria** (what must be TRUE):
  1. Every finding rendered in the HTML and PDF reports has a non-empty `description` field containing 1–3 sentences that explain the cryptographic risk in plain English
  2. Every quantum-vulnerable finding in the report names the replacement algorithm using FIPS 203/204/205 designations only: ML-KEM, ML-DSA, or SLH-DSA — the strings "Kyber", "Dilithium", and "when standards are adopted" do not appear in any finding text
  3. Every quantum-vulnerable finding cites the NIST IR 8547 deprecation timeline: RSA/ECC deprecated 2030, disallowed 2035
  4. A CI test (grep-based gate) fails the build if "Kyber", "Dilithium", or "when standards are adopted" appear anywhere in `risk_engine.py` or `routes/scan.py`
**Plans**: 3 plans
  - [x] 48-01-PLAN.md — Risk engine: _build_finding helper + NIST_IR_8547_DEPRECATION constant + producer migration + dedup safety
  - [x] 48-02-PLAN.md — Renderer (HTML All Findings + technical Markdown) + dashboard wiring + JSON export verification + recommendation/remediation guardrail
  - [x] 48-03-PLAN.md — CI grep gate (tests/test_pqc_terminology_gate.py) + docs purge + UAT-SERIES.md + Obsidian phase note

### Phase 49: Compliance Mapping
**Goal**: QUIRK findings are mapped to PCI-DSS 4.0.1, HIPAA 45 CFR, and FIPS 140-3 control references via a new `quirk/compliance/` module, and a "Compliance Summary" section appears in HTML/PDF reports — making QUIRK output directly usable as evidence in compliance assessments. Mappings include freshness metadata so they don't silently rot when regulators publish revisions
**Depends on**: Phase 48
**Requirements**: COMPLY-01, COMPLY-02, COMPLY-03, COMPLY-04, COMPLY-05, COMPLY-06, COMPLY-07, COMPLY-08, COMPLY-09
**Success Criteria** (what must be TRUE):
  1. A `quirk/compliance/__init__.py` module exists with a `COMPLIANCE_MAP` dict keyed by finding category; every entry includes `version`, `last_verified` (ISO date), and `source_url` keys (e.g., "PCI-DSS 4.0.1", "2026-05-03", "https://docs-prv.pcisecuritystandards.org/...")
  2. Relevant TLS/key-storage findings map to PCI-DSS 4.0.1 controls 4.2.1, 4.2.1.1, 6.3.3, and 8.3.2
  3. Relevant findings map to HIPAA 45 CFR §164.312(a)(2)(iv), §164.312(e)(1), and §164.312(e)(2)(ii)
  4. Algorithm-choice findings map to FIPS 140-3 approved/not-approved classification
  5. HTML and PDF reports contain a "Compliance Summary" section listing finding-to-control references grouped by framework (PCI-DSS, HIPAA, FIPS 140-3)
  6. A unit test asserts every `COMPLIANCE_MAP` entry includes `version`, `last_verified`, and `source_url` keys; build fails if any entry is missing them
  7. A CI staleness check warns when any entry's `last_verified` is older than 12 months (configurable threshold) so maintainers are alerted before client-facing staleness
  8. `quirk compliance status` CLI subcommand prints per-framework version, `last_verified` date, and `source_url` for operator pre-engagement verification
**Plans**: 5 plans
  - [x] 49-01-PLAN.md — Wave 0 RED test scaffold (5 test files + chaos-lab fixture aggregator)
  - [x] 49-02-PLAN.md — quirk/compliance/ module + _build_finding compliance injection + FindingItem DTO field
  - [x] 49-03-PLAN.md — Compliance Summary Jinja2 block in report.html.j2 (HTML + PDF inheritance)
  - [x] 49-04-PLAN.md — run_scan.py compliance status subcommand intercept (text + json formats)
  - [x] 49-05-PLAN.md — Docs (report-interpretation.md + UAT-SERIES.md) + Obsidian phase note + UAT vault sync + hub refresh + commit

### Phase 50: Enterprise Documentation
**Goal**: Enterprise customers can self-onboard QUIRK using two production-quality reference documents — an architecture reference and an operator's guide — both available in the repo and synced to the Obsidian vault. Operator's guide also documents the compliance map maintenance process so QUIRK's regulatory references stay current as standards evolve
**Depends on**: Phase 49
**Requirements**: DOCS-01, DOCS-02, DOCS-03, DOCS-04
**Success Criteria** (what must be TRUE):
  1. `docs/architecture.md` exists and covers scanner phases, data flow, SQLite schema, dashboard architecture, and CBOM pipeline — sufficient for an engineer to understand the full system without reading source code
  2. `docs/operators-guide.md` exists and covers install, configuration, scanning workflow, troubleshooting, and a per-scanner reference — sufficient for an enterprise admin to deploy and operate QUIRK independently
  3. Both documents are synced to the Obsidian vault under `20_Dev-Work/QUIRK/Reference/` with correct frontmatter (`type: reference`, `source: docs/<filename>.md`, `updated: 2026-05-XX`)
  4. `docs/operators-guide.md` includes a "Compliance Map Maintenance" section documenting the quarterly review cadence, list of source URLs to monitor (PCI SSC, HHS.gov, NIST CSRC), and the upgrade path when a regulator publishes a revision (e.g. PCI-DSS 4.0.1 → 4.1)
**Plans:** 5/5 plans executed
  - [x] 50-01-PLAN.md — Wave 0 RED docs-presence gate test (tests/test_phase50_docs_presence.py)
  - [x] 50-02-PLAN.md — Author docs/architecture.md (enterprise-architect framing, mermaid diagrams, credential matrix)
  - [x] 50-03-PLAN.md — Author docs/operators-guide.md (install/configure/scan/troubleshoot/per-scanner ref + Compliance Map Maintenance runbook)
  - [x] 50-04-PLAN.md — Obsidian vault sync: Reference/Architecture.md, Reference/Operators-Guide.md, hub MOC update, Phase-50 phase note
  - [x] 50-05-PLAN.md — UAT-SERIES.md Series 19 + vault sync + ROADMAP/STATE close + commits

## Phase Details — v4.6 Enterprise Readiness — SHIPPED 2026-05-05

See `.planning/milestones/v4.6-ROADMAP.md` for full phase details, plans, and milestone summary.

## Phases — v4.7 Governance & Compliance Platform

<details>
<summary>✅ v4.7 Governance & Compliance Platform (Phases 51–56) — SHIPPED 2026-05-08</summary>

**Milestone Goal:** Extend QUIRK from a compliance-tagged scanner into a full governance platform by completing the compliance framework and integrating the QRAMM maturity model — making QUIRK's primary consulting deliverable a scored governance assessment grounded in live scanner findings.

- [x] **Phase 51: QRAMM Core Infrastructure** - SQLite tables, FastAPI CRUD, 120-question catalog, scoring engine, and datetime.utcnow fix — the backend foundation all QRAMM phases depend on (completed 2026-05-06)
- [x] **Phase 52: Compliance Uplift & Health Check** - SOC2/ISO 27001 framework extensions, CBOM FIPS 140-3 annotations, `quirk doctor` CLI, and four tech debt items (parallel to Phase 51) (completed 2026-05-06)
- [x] **Phase 53: QRAMM Evidence Bridge** - Auto-populate CVI dimension answers from live scanner findings via SESSION_BRACKET scan-window; suggested_answer storage with confirmation workflow (completed 2026-05-07)
- [x] **Phase 54: QRAMM Assessment UI & Scorecard** - Org Profile wizard, 120-question dimension tabs, answer persistence, radar chart scorecard (completed 2026-05-08)
- [x] **Phase 55: QRAMM Compliance Mapping View** - 8-framework coverage table, per-practice relevance scores, staleness CLI and CI gate (completed 2026-05-08)
- [x] **Phase 56: PDF Export & Staleness Enforcement** - Combined governance + technical PDF, QRAMM section with radar chart, quarterly CI staleness gate (completed 2026-05-08)

</details>

## Phase Details — v4.7 Governance & Compliance Platform

### Phase 51: QRAMM Core Infrastructure
**Goal**: The backend is fully equipped to run QRAMM assessments — three new SQLite tables, a complete FastAPI CRUD router, the versioned 120-question catalog, and a unit-tested weakest-link scoring engine; datetime.utcnow deprecation warning eliminated
**Depends on**: Phase 50 (v4.6 complete)
**Requirements**: QRAMM-01, QRAMM-02, QRAMM-03, QRAMM-04, DEBT-01
**Success Criteria** (what must be TRUE):
  1. Running `quirk serve` against a fresh database creates `qramm_sessions`, `qramm_answers`, and `qramm_profiles` tables idempotently via `_ensure_qramm_tables()` — no migration error on an existing v4.6 `quirk.db`
  2. `POST /api/qramm/sessions`, `GET /api/qramm/sessions/{id}`, `POST /api/qramm/sessions/{id}/answers`, `POST /api/qramm/sessions/{id}/score`, and `DELETE /api/qramm/sessions/{id}` all respond with correct HTTP status codes and Pydantic-validated payloads
  3. `quirk/qramm/questions.py` exports `QRAMM_QUESTIONS` as a list of exactly 120 entries; each entry carries `question_number`, `dimension`, `practice_area`, `text`, and `maturity_labels`; a unit test verifies count and schema
  4. Scoring a session with deliberately weakest-link answers produces dimension scores equal to the minimum of its 3 practice scores (not the average); a unit test asserts exact numeric agreement with a CSNP QRAMM reference calculation
  5. Running the test suite produces zero `DeprecationWarning: datetime.utcnow()` messages — `datetime.now(timezone.utc)` is used throughout `quirk/logging_util.py`, `quirk/discovery/nmap_provider.py`, and any other affected module
**Plans**: 5 plans
  - [x] 51-01-PLAN.md — ORM models (QRAMMSession/Answer/Profile) + _ensure_qramm_tables() in db.py
  - [x] 51-02-PLAN.md — quirk/qramm/ package: questions.py (120 entries) + scoring.py + model_meta.py + __init__.py
  - [x] 51-03-PLAN.md — FastAPI CRUD router at /api/qramm/ + app.py registration
  - [x] 51-04-PLAN.md — Test suite: test_qramm_questions.py + test_qramm_scoring.py + test_qramm_router.py
  - [x] 51-05-PLAN.md — DEBT-01: replace datetime.utcnow() in test_saml_scanner.py and test_broker_scanner_redis.py

### Phase 52: Compliance Uplift & Health Check
**Goal**: The compliance module gains SOC2 and ISO 27001:2022 framework mappings; CBOM algorithm components carry FIPS 140-3 status annotations; `quirk doctor` gives operators a pre-engagement health dashboard; four backlog tech debt items are closed — this phase runs in parallel with Phase 51
**Depends on**: Phase 50 (v4.6 complete; Phase 51 is a parallel sibling with zero shared dependencies)
**Requirements**: COMPLY-10, COMPLY-11, COMPLY-12, DOCS-05, DEBT-02, DEBT-03, DEBT-04
**Success Criteria** (what must be TRUE):
  1. CBOM JSON output contains a `properties` array on every algorithm component with a `quirk:fips140-3-status` property set to `approved` or `non-approved` based on algorithm classification (`nist_level >= 1` → `approved`; `nist_level == 0` or `None` → `non-approved`); a unit test verifies annotation presence for components in both tiers (per Phase 52 D-01: the `certified` tier is reserved for a future CMVP attestation phase and is never emitted in v4.7)
  2. `COMPLIANCE_MAP` in `quirk/compliance/__init__.py` contains a `_soc2()` helper that maps relevant finding categories to SOC2 CC6.x controls following the existing `_pci()` / `_hipaa()` / `_fips()` builder pattern; a unit test asserts at least three CC6.x control IDs are present
  3. `COMPLIANCE_MAP` contains a `_iso()` helper with ISO 27001:2022 Annex A controls using 8.x clause numbering; a unit test rejects any 2013-style `A.x.x` control ID with an explicit assertion error
  4. `quirk doctor` runs and exits code 0 when all non-informational checks pass; exits code 1 if Python version is unsupported, a required binary is missing, compliance or QRAMM frameworks are stale, or `quirk.db` is unreachable; output uses `[✓]` / `[!]` / `[✗]` symbols
  5. `PROFILE_ARGS="--profile <name>" ./lab.sh up` correctly overrides `.env` defaults — the fix is verified with a smoke test showing the correct profile name in `lab.sh` startup output
  6. `run-stats-*.json` output includes `ports_scanned` (sorted list) and `hosts_scanned` (sorted list) derived from the actual scan pipeline targets
  7. `quirk/scanner/saml_scanner.py` imports raw `lxml.etree` with `resolve_entities=False` and `no_network=True`; all 27 existing SAML tests pass GREEN
**Plans**: 6 plans
**Wave 0**
- [x] 52-01-PLAN.md — Wave 0 test scaffolding (FIPS, SOC2/ISO, doctor, run-stats stubs)

**Wave 1** *(blocked on Wave 0 completion)*
- [x] 52-02-PLAN.md — CBOM FIPS 140-3 status annotation (COMPLY-10)
- [x] 52-03-PLAN.md — SOC2 + ISO 27001:2022 COMPLIANCE_MAP extension (COMPLY-11/12)
- [x] 52-04-PLAN.md — quirk doctor CLI subcommand (DOCS-05)
- [x] 52-05-PLAN.md — Tech debt closures: lab.sh PROFILE_ARGS, run-stats fields, lxml migration (DEBT-02/03/04)

**Wave 2** *(blocked on Wave 1 completion)*
- [x] 52-06-PLAN.md — Documentation, UAT-SERIES, Obsidian phase note + sync

**Cross-cutting constraints:**
- Every CBOM algorithm component must carry `quirk:fips140-3-status` (Wave 1 → Wave 2 verification dependency)
- `quirk doctor` depends on `quirk.compliance.status_report()` being fully extended before doctor tests pass GREEN

### Phase 53: QRAMM Evidence Bridge
**Goal**: When a QRAMM assessment session is created, up to 30 CVI dimension questions are auto-populated with `suggested_answer` values derived from the latest scan's `CryptoEndpoint` rows — reducing manual assessment effort and grounding the governance score in live scanner evidence
**Depends on**: Phase 51
**Requirements**: QRAMM-12, QRAMM-13, QRAMM-14
**Success Criteria** (what must be TRUE):
  1. `POST /api/qramm/sessions` triggers `evidence_bridge.py` to read `CryptoEndpoint` rows within the SESSION_BRACKET scan-window and sets `suggested_answer` on up to 30 CVI-dimension rows; `quirk/qramm/evidence_bridge.py` does NOT import `risk_engine` (circular import prevention is unit-tested by checking `sys.modules`)
  2. Auto-populated rows have `answer_value = null`, `suggested_answer = <1-4>`, and `requires_confirmation = true`; calling `POST .../score` with unconfirmed rows excludes them from maturity calculation; calling it after `confirmed_at` is set includes them — both behaviors are asserted by tests
  3. A scan with RC4-HMAC Kerberos findings produces lower CVI auto-suggested answers than a scan with only AES-256 findings — the bridge correctly translates cryptographic weakness to lower QRAMM maturity
**Plans**: 4 plans
  - [x] 53-01-PLAN.md — Wave 0 RED test scaffold: tests/test_qramm_evidence_bridge.py with 8 contract tests + seed helpers
  - [x] 53-02-PLAN.md — quirk/qramm/evidence_bridge.py: SESSION_BRACKET, classify_algorithm integration, D-05/06/07 derivation
  - [x] 53-03-PLAN.md — Wire bridge into qramm.py router (create_session pre-creates 30 CVI rows + calls bridge; save_answers auto-sets confirmed_at)
  - [x] 53-04-PLAN.md — Phase completion: Obsidian Phase-53 note + docs/UAT-SERIES.md update + vault sync + commit

### Phase 54: QRAMM Assessment UI & Scorecard
**Goal**: A consultant can complete a QRAMM assessment entirely within the QUIRK dashboard — filling out the Org Profile, answering all 120 questions across 4 dimension tabs, viewing auto-filled suggestions with confirmation badges, and seeing a live-rendered scorecard with radar chart and dimension table
**Depends on**: Phase 51, Phase 53
**Requirements**: QRAMM-08, QRAMM-09, QRAMM-10, QRAMM-11
**Success Criteria** (what must be TRUE):
  1. The Org Profile wizard page collects industry sector, organization size, geographic scope, data sensitivity, and regulatory obligations; submitting the form stores a `qramm_profiles` row and redirects to the assessment tab view
  2. The assessment view renders 120 questions across 4 dimension tabs (CVI, SGRM, DPE, ITR); each question displays a 1–4 radio scale with `Basic / Developing / Established / Optimizing` labels and an optional evidence note field; a per-dimension progress counter updates as questions are answered
  3. Navigating away from the assessment and returning (or refreshing the browser) restores all previously entered answers without data loss — answers are persisted via debounced `POST /api/qramm/assessment/draft` to the backend
  4. The QRAMM Scorecard page displays a 4-axis `RadarChart` (CVI, SGRM, DPE, ITR), a dimension summary table with raw score / weighted score / industry benchmark / maturity level / completion %, and a maturity distribution showing practice counts at each level; scores update only when the user clicks "Calculate Score" (not in real time)
**Plans**: 5 plans
  - [x] 54-01-PLAN.md — Backend foundation: evidence_note column migration + 4 missing QRAMM API endpoints (sessions list, profile create with multiplier, draft answer, answers read) + pytest coverage
  - [x] 54-02-PLAN.md — Frontend foundation: shadcn primitives (radio-group, collapsible, label) + QRAMMContext/QRAMMProvider with debounced draft persister + useQRAMMSession hook + static lookups (industry benchmarks, practice area names, option lists)
  - [x] 54-03-PLAN.md — Org Profile wizard page (/qramm) + App.tsx provider wiring + sidebar nav entry with startsWith active state
  - [x] 54-04-PLAN.md — Assessment view (/qramm/assessment): 5 tabs, 120 questions across 12 default-open Collapsible sections, RadioGroup + evidence note per card, two-step Confirm UX for auto-filled questions, restore-on-reload
  - [x] 54-05-PLAN.md — Scorecard tab: RadarChart (isAnimationActive=false), dimension summary table, maturity distribution, explicit Calculate Score action, a11y route registration + fixture
**UI hint**: yes

### Phase 55: QRAMM Compliance Mapping View
**Goal**: Consultants can see exactly which of 8 governance frameworks each QRAMM practice contributes to — backed by a live assessment session — and can run a CLI command to verify QRAMM model freshness before client engagements
**Depends on**: Phase 52, Phase 54
**Requirements**: QRAMM-05, QRAMM-06, QRAMM-07, QRAMM-15
**Success Criteria** (what must be TRUE):
  1. The QRAMM Compliance Mapping view shows a table covering all 8 frameworks (NIST PQC Standards, NSM-10, CNSA 2.0, ISO 27001:2022, ETSI Quantum-Safe, PCI-DSS v4.0, Common Criteria, BSI TR-02102) with per-practice relevance scores derived from the active assessment session; the view never shows a "fully compliant" badge and never shows a coverage percentage above the scanner's actual coverage ceiling
  2. `quirk qramm status` exits code 0 when `QRAMM_MODEL.last_verified` is within 90 days; exits code 1 when stale; output shows version, `last_verified`, days remaining, and verdict — consistent with the `quirk compliance status` pattern
  3. A pytest gate fails if `QRAMM_MODEL.last_verified` in `quirk/qramm/model_meta.py` is more than 90 days old; the `QUIRK_CI_STALENESS_OVERRIDE_DATE` environment variable allows CI boundary testing without touching source
  4. `quirk/qramm/model_meta.py` exports `QRAMM_MODEL` with `qramm_version`, `last_verified` (ISO date string), and `source_url = "https://qramm.org"` — mirroring the compliance staleness pattern from v4.6
**Plans**: 3 plans
- [x] 55-01-PLAN.md — Backend: compliance_map.py module, GET /api/qramm/sessions/{id}/compliance-map endpoint, endpoint tests
- [x] 55-02-PLAN.md — CLI: quirk qramm status subcommand, run_scan.py intercept, pytest staleness gate with QUIRK_CI_STALENESS_OVERRIDE_DATE
- [x] 55-03-PLAN.md — Frontend: QRAMMComplianceMapRow type, ComplianceMapTab component, 6th tab wiring in qramm-assessment.tsx
**UI hint**: yes

### Phase 56: PDF Export & Staleness Enforcement
**Goal**: The combined PDF export includes a QRAMM section (executive summary, dimension scorecard, static SVG radar chart, compliance framework mapping summary) that starts on a new page — and the quarterly staleness CI gate rejects builds when QRAMM model metadata is more than 90 days old
**Depends on**: Phase 54, Phase 55
**Requirements**: QRAMM-16
**Success Criteria** (what must be TRUE):
  1. The PDF produced via the `/print` route includes a QRAMM section starting on a new page (via `@media print { page-break-before: always }`) containing: executive QRAMM summary paragraph, dimension scorecard table, the static SVG radar chart rendered at print resolution, and a compliance framework mapping summary for the 8 frameworks
  2. The existing Technical Findings section layout is not regressed — pagination, finding table column widths, and cert inventory layout in the PDF are unchanged from v4.6 output; a visual regression fixture or plan comparison confirms this
  3. A consultant running a full QRAMM assessment and clicking "Export PDF" receives a single file containing both the governance assessment and the technical scanner findings — the primary consulting deliverable
**Plans**: 3 plans
- [x] 56-01-PLAN.md — useQRAMMPrintData hook (most-recent-scored session + parallel score/compliance-map fetch)
- [x] 56-02-PLAN.md — print.tsx PrintQRAMM section: PRINT_CSS additions, inline SVG radar, dimension scorecard, 8-row compliance summary, per-framework practice detail, data-ready gate
- [x] 56-03-PLAN.md — Docs + Obsidian: UAT-SERIES.md cases, report-interpretation.md QRAMM section, Phase-56 vault note
**UI hint**: yes

## Progress — v4.7 Phases

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 51. QRAMM Core Infrastructure | v4.7 | 6/6 | Complete    | 2026-05-06 |
| 52. Compliance Uplift & Health Check | v4.7 | 6/6 | Complete    | 2026-05-06 |
| 53. QRAMM Evidence Bridge | v4.7 | 4/4 | Complete    | 2026-05-07 |
| 54. QRAMM Assessment UI & Scorecard | v4.7 | 5/5 | Complete   | 2026-05-08 |
| 55. QRAMM Compliance Mapping View | v4.7 | 3/3 | Complete   | 2026-05-08 |
| 56. PDF Export & Staleness Enforcement | v4.7 | 3/3 | Complete    | 2026-05-08 |

### Phase 56.1: Close QRAMM-06/07 — wire CI staleness gate workflow (INSERTED)

**Goal:** Wire the QRAMM staleness gate, the compliance freshness gate, and the QRAMM CLI smoke tests into a new GitHub Actions workflow so that QRAMM-06's 90-day pytest gate is actually enforced on every PR, every push to `main`, and weekly via cron — and document the cadence in `CLAUDE.md`.
**Requirements**: QRAMM-06, QRAMM-07, COMPLY-08
**Depends on:** Phase 56
**Plans:** 3/3 plans complete

Plans:
- [x] 56.1-01-PLAN.md — Create .github/workflows/python-staleness.yml
- [x] 56.1-02-PLAN.md — CLAUDE.md cadence section + REQUIREMENTS.md / ROADMAP.md closure + model_meta.py pointer
- [x] 56.1-03-PLAN.md — UAT-SERIES.md update + Obsidian phase note + UAT commit

---

## Phases — v4.8 Pre-Primetime Hardening + Operating Model

> **Wave gating:** Wave A (Phases 57–62) is the **mandatory hardening gate** for v4.8. **No Wave B phase (63–68) may start until every Wave A phase is `[x]` complete.** This is the v4.8 cornerstone — operating-model features must sit on top of an audited, hardened security and correctness foundation, not the other way round.
>
> **Wave A internal parallelism:** Phases 57, 58, 59, 60, 61, and 62 touch disjoint code paths (protocol scanners / dashboard route layer / shared util / scoring engine / CBOM builder / React hooks). They MAY be executed in parallel by independent agents. The wave-gate is the *completion barrier*, not the *execution barrier*.
>
> **Wave B critical path:** 65 → 66 (history needs scan launch); 65 depends on 58 (dashboard auth must exist before dashboard launches scans). Phase 63 (scheduled scans) has a **soft dependency** on Phase 67 (resumable scans) — schedulable scans benefit from resumable infra but can ship without; if 67 lands first, 63 inherits the resume capability for free.
>
> **Audit traceability:** Every Wave A phase goal explicitly names the audit-2026-05-08 blocker IDs it closes so traceability is self-documenting against `.planning/audit-2026-05-08/AUDIT-SUMMARY.md`.

<details>
<summary>✅ v4.8 Pre-Primetime Hardening + Operating Model (Phases 57–68) — SHIPPED 2026-05-14</summary>

**Milestone Goal:** Close all 15 audit-identified blockers (Wave A) and ship the operating-model features that turn QU.I.R.K. into a deploy-and-forget platform (Wave B). v4.8 is the primetime cutover — after this milestone a customer can install, schedule, and operate QU.I.R.K. without operator hand-holding, on top of a hardened security and correctness foundation.

**Wave A — Pre-Primetime Hardening (gates Wave B):**

- [x] **Phase 57: Scanner Security Hardening** - JWKS TLS verification, SAML SSRF allowlist, semgrep/syft argument-injection guards, broker hardcoded-credential removal, broker TLS-required default — closes audit blockers 1–6 (`scanners-protocol/CR-01..CR-06`) (completed 2026-05-09)
- [x] **Phase 58: Dashboard API Hardening** - Single-user bearer auth + CSRF, CORS allowlist lockdown, per-route rate limiting, `quirk init` path-traversal guard, PDF SSRF clamp, `@file` allowlist + size cap — closes audit blockers 7–10 (`api-cli-core/CR-01, CR-02, CR-03, CR-09`) (completed 2026-05-10)
- [x] **Phase 59: Credential Leakage Sweep** - Shared `quirk/util/safe_exc.py::safe_str(exc)` helper applied across every connector and route handler that persists `scan_error`; AST-based pytest gate prevents future bypasses — closes audit blocker 11 + Pattern A (completed 2026-05-10)
- [x] **Phase 60: Score Arithmetic Correctness** - Top-level readiness clamp ≤100, server-side QRAMM profile multiplier clamp `[0.8, 1.5]`, confidence-bonus zero-data guard, contiguous QRAMM maturity threshold bands — closes audit blockers 12, 15 + Pattern E (completed 2026-05-10)
- [x] **Phase 61: CBOM Coverage + Report Sanitization** - CBOM Pass-1 algorithm components for the 12+ protocol families currently emitting zero algos, VAULT classification consistent across Pass-1/2/3, markdown report tables escape `|` / `\n` / control chars on adversary-controllable strings — closes audit blockers 13, 14 (completed 2026-05-10)
- [x] **Phase 62: React Hook Cancellation Pattern** - Standardized `useCancellableFetch` (or equivalent) across every data-fetch hook in `src/dashboard/src/hooks/`, QRAMM debounce coalescing fix, auto-fill confirm round-trip preserves badge contract, ESLint/codemod guard rule — closes Pattern C (completed 2026-05-10)

**Wave B — Operating Model (gated on Wave A complete):**

- [x] **Phase 63: Scheduled / Continuous Scanning** - `quirk schedule add` CLI + `scheduled_scans` SQLite table + `quirk scheduler run` long-running dispatcher + dashboard `/schedules` listing (BACK-25) (completed 2026-05-10)
- [x] **Phase 64: Trend Analysis Foundation** - Multi-scan timeline of overall + per-pillar scores and finding counts on `/trends`, regression alert chips on dashboard home with deep-links to the regressing scan (BACK-21) (completed 2026-05-10)
- [x] **Phase 64.1: Audit Residual Blockers** - Triage all 19 open BLOCKERs from the 2026-05-08 audit (record deferred-v4.9 / wont-fix dispositions); fix the 5 that directly undermine Phase 64 UAT or Phase 65 foundations: trend session-window disambiguation (CR-05), non-transactional `init_db` migrations (api-cli-core/CR-08), QRAMM staleness date comparison (BL-03), QRAMM negative-years guard (BL-04), SOURCE algo hint DES→3DES collapse (cbom-intel-reports/CR-03) (completed 2026-05-11)
- [x] **Phase 65: Dashboard-Initiated Scan** - `/scan/new` form, Pydantic-shared validation, backend job spawn, live status polling, post-completion navigation (BACK-86 slice 1) (completed 2026-05-13)
- [x] **Phase 66: Dashboard Scan History + Clone/Compare** - `/scans` list + "Clone configuration" prefill + side-by-side compare diff view (BACK-86 slice 2) (completed 2026-05-14)
- [x] **Phase 67: Resumable / Partial-Failure Scans** - `scan_checkpoints` SQLite table + `quirk scan --resume <id>` continuation + per-scanner partial-failure isolation with dashboard panel (completed 2026-05-14)
- [x] **Phase 68: Operator Error-Message Pass** - Stable error codes with one-line cause + one-line remediation across every CLI exit, dashboard 4xx/5xx, and `scan_error_category` row; first-run install-day errors follow the same format (completed 2026-05-14)

</details>

## Phase Details — v4.8 Pre-Primetime Hardening + Operating Model

### Phase 57: Scanner Security Hardening
**Goal**: Every protocol scanner is safe to point at an untrusted target — TLS verification is on by default, SSRF is gated by an explicit allowlist, subprocess wrappers reject shell-metacharacter input, and no scanner ships hardcoded credentials to the network. Closes audit blockers 1–6 (`scanners-protocol/CR-01..CR-06`).
**Wave**: A (gating)
**Depends on**: Phase 56.1 (v4.7 close-out)
**Requirements**: HARDEN-SCAN-01, HARDEN-SCAN-02, HARDEN-SCAN-03, HARDEN-SCAN-04, HARDEN-SCAN-05, HARDEN-SCAN-06
**Success Criteria** (what must be TRUE):
  1. JWKS fetches in `quirk/scanner/api_scanner.py` use `verify=True` by default; if the operator opts into disabled verification via an explicit config knob, the scan emits a HIGH advisory finding naming the affected JWKS URL
  2. The SAML scanner refuses to fetch URLs resolving to RFC1918, link-local, loopback, `file://`, or cloud metadata IPs (169.254.169.254, fd00:ec2::254) unless `--allow-internal-targets` is set; a unit test feeds each forbidden category and asserts the scan never issues an outbound HTTP request
  3. `quirk/scanner/source_scanner.py` and `quirk/scanner/container_scanner.py` reject `repo_path` / `image_ref` containing shell metacharacters, `..`, or `dir:/` / `file://` prefixes before invoking semgrep / syft; rejected inputs produce a structured `scan_error_category="invalid_input"` row, never a subprocess call
  4. The broker scanner sends NO credentials by default — no `guest:guest`, no Basic-auth header — and TLS-required is the default for management API + Redis probes; cleartext probes require an explicit `--allow-cleartext-broker-probe` flag and emit a HIGH advisory finding
  5. Running the full scanner test suite plus the chaos-lab smoke (`./lab.sh up && quirk scan --target <lab>`) produces zero outbound requests with `verify=False`, zero hardcoded credentials in any captured HTTP body, and zero subprocess invocations with un-sanitized arguments
**Plans**: 6 plans
- [x] 57-01-PLAN.md — Shared util helpers (url_allowlist + subprocess_input) + tests
- [x] 57-02-PLAN.md — SecurityCfg + BrokerCredential config wiring + CLI flags + models.py docstring (D-06)
- [x] 57-03-PLAN.md — JWT scanner CR-01 (verify=True default + JWKS advisory) + ROADMAP D-11 correction
- [x] 57-04-PLAN.md — SAML scanner CR-04 (validate_external_url SSRF guard + internal-target advisory)
- [x] 57-05-PLAN.md — Source + container scanners CR-02/CR-03 (subprocess input validation + argv `--`)
- [x] 57-06-PLAN.md — Broker scanner CR-05/CR-06 (no guest:guest, TLS-required default, advisories) + AUDIT-TASKS.md flip

### Phase 58: Dashboard API Hardening
**Goal**: The dashboard API is safe to expose beyond the loopback interface — every mutating route requires auth, CORS is locked down, rate limiting throttles abuse, and operator-supplied paths cannot escape their allowlists. Closes audit blockers 7–10 (`api-cli-core/CR-01, CR-02, CR-03, CR-09`).
**Wave**: A (gating)
**Depends on**: Phase 56.1 (v4.7 close-out)
**Requirements**: HARDEN-API-01, HARDEN-API-02, HARDEN-API-03, HARDEN-API-04, HARDEN-API-05, HARDEN-API-06
**Success Criteria** (what must be TRUE):
  1. Every mutating dashboard route returns 401 (with no business-logic execution) when the bearer token is missing or invalid; a CSRF token is required on browser-form requests; auth coverage is asserted by an automated route-introspection test that fails if a new mutating route is added without auth
  2. The CORS preflight from a non-allowlisted origin returns 403 with no body; the allowlist defaults to `127.0.0.1` + `localhost` and is overridable via config; an integration test exercises both allowed and denied origins
  3. The 61st mutating request from one IP within a minute returns 429 with a `Retry-After` header; informational routes are exempt; a load test demonstrates the limit and exemption
  4. `quirk init --output <path>` rejects `..`, absolute paths outside the allowlist, and symlinks pointing outside the allowlist with a clear error; a fuzz test feeds 50+ traversal patterns and asserts each is rejected
  5. `routes/pdf.py` rejects `QUIRK_SERVE_PORT` outside `1024–65535`, binds outbound fetches to `localhost`, and refuses to follow redirects to non-loopback hosts; `@file` target loading enforces the path allowlist, 1 MB size cap, and 10,000-line cap with explicit error messages on each violation
**Plans**: 7 plans
Plans:
**Wave 1**
- [x] 58-01-PLAN.md — Auth middleware + config extension (require_auth, require_csrf, SecurityCfg.api_token)
- [x] 58-02-PLAN.md — CORS + rate-limit middleware registration in app factory
- [x] 58-03-PLAN.md — CLI path-traversal guard, PDF port clamp, @file target guards

**Wave 2** *(blocked on Wave 1 completion)*
- [x] 58-04-PLAN.md — TDD: Wire auth/CSRF to routers + full integration test suite
- [x] 58-05-PLAN.md — TDD: CLI init fuzz corpus + TargetFileError reason-code tests
- [x] 58-06-PLAN.md — React fetchApi() utility + migrate all raw fetch() call sites

**Wave 3** *(blocked on Wave 2 completion)*
- [ ] 58-07-PLAN.md — Audit ledger closure (CR-01, CR-02, CR-03, CR-09) + UAT-SERIES.md update
**UI hint**: yes

### Phase 59: Credential Leakage Sweep
**Goal**: No exception text leaks credentials into `scan_error`, logs, or report output. A single `safe_str(exc)` chokepoint replaces every raw `f"...: {exc}"` interpolation across connectors and route handlers, and an AST-based CI gate prevents future regressions. Closes audit blocker 11 + Pattern A.
**Wave**: A (gating)
**Depends on**: Phase 56.1 (v4.7 close-out)
**Requirements**: LEAK-01, LEAK-02, LEAK-03
**Success Criteria** (what must be TRUE):
  1. `quirk/util/safe_exc.py::safe_str(exc)` exists, returns `f"{type(exc).__name__}"` by default, and scrubs known-sensitive substrings (token-like base64 strings, connection-string passwords, GCP ADC paths, Vault tokens) — covered by a unit test corpus of representative leaky exception messages
  2. Every connector that writes `scan_error` (vault, GCP, AWS, DB, broker, email, identity) routes exception text through `safe_str(exc)`; an end-to-end test seeds each connector with a synthesized credential-bearing exception and asserts the resulting `scan_error` row contains only the exception class name
  3. A pytest gate enumerates `scan_error` writes via AST scan and fails the build if any caller bypasses `safe_str(exc)` — mirroring the `_build_finding` chokepoint pattern from v4.6 Phase 48
  4. Replaying a corpus of v4.7 scan databases through a leak detector finds zero credential-shaped substrings in any `scan_error` value
**Plans**: 3 plans
  - [x] 59-01-PLAN.md — Build safe_str helper + unit corpus (LEAK-01)
  - [x] 59-02-PLAN.md — Apply safe_str to 8 leaky callsites + unify db_connector (LEAK-02)
  - [x] 59-03-PLAN.md — AST CI gate + corpus replay regression (LEAK-03)

### Phase 60: Score Arithmetic Correctness
**Goal**: Every score path is bounded and defensible — total readiness is clamped to `[0, 100]`, the QRAMM profile multiplier is clamped server-side, the confidence bonus is gated on actual data, and QRAMM maturity thresholds are contiguous with no scoring gaps. Closes audit blockers 12, 15 + Pattern E.
**Wave**: A (gating)
**Depends on**: Phase 56.1 (v4.7 close-out)
**Requirements**: SCORE-01, SCORE-02, SCORE-03, SCORE-04
**Success Criteria** (what must be TRUE):
  1. Reports, JSON output, and the dashboard never display a readiness score above 100 or below 0; a property test driving synthesized evidence rows asserts the invariant across 1,000 randomized inputs
  2. `POST /api/qramm/sessions/{id}/score` with a client-supplied multiplier outside `[0.8, 1.5]` returns 400 with a documented error code; values inside the range are accepted unchanged; the canonical range is documented in the OpenAPI schema
  3. A scan with zero TLS endpoints scanned receives a confidence bonus of exactly 0, not the previous 20-point default; a unit test fixes the regression
  4. A parametrized test sweeps the `[0, 100]` range at 0.5-point increments and asserts every score maps to exactly one QRAMM maturity level — no gaps, no overlaps, no silent fall-throughs
**Plans**: TBD

### Phase 61: CBOM Coverage + Report Sanitization
**Goal**: CBOM Pass-1 emits at least one algorithm component for every protocol family the scanner produces evidence for, VAULT is classified consistently across all three CBOM passes, and markdown reports cannot be broken or injected by adversary-controllable strings (host, cipher, cert subject, banner, finding text). Closes audit blockers 13, 14.
**Wave**: A (gating)
**Depends on**: Phase 56.1 (v4.7 close-out)
**Requirements**: CBOM-COVER-01, CBOM-COVER-02, REPORT-SAN-01, REPORT-SAN-02
**Success Criteria** (what must be TRUE):
  1. A per-profile CBOM emission test asserts at least one algorithm component for each of the 12+ previously-zero-algo protocol families (database, registry, source, ssh-weak, storage-s3, broker subfamilies, email subfamilies, vault, identity-secondary); the test fails loudly if any family regresses to zero
  2. VAULT is routed through a vault-specific Pass-1 branch (not the TLS branch) and Pass-2 / Pass-3 emit consistent evidence claims about the same vault endpoint; a golden snapshot fixture for a chaos-lab vault scan is byte-identical across runs
  3. Rendering both the technical and executive markdown reports against an adversarial corpus (pipes, newlines, backticks, HTML entities, control characters in host / cipher / cert subject / cert issuer / banner / finding text / evidence note fields) produces output that parses as valid GFM tables with no row-break or injection escape
  4. CycloneDX 1.6 schema validation continues to pass for every chaos-lab profile post-fix — no new validation regressions introduced by Pass-1 expansion
**Plans**: 3 plans
- [x] 61-01-PLAN.md — CBOM Pass-1 coverage branches + per-family coverage test + VAULT golden snapshot
- [x] 61-02-PLAN.md — md_cell escape utility + technical.py wrapping + adversarial corpus test
- [x] 61-03-PLAN.md — Audit ledger flip (CR-01/02/07) + UAT-SERIES sync + Obsidian phase note

### Phase 62: React Hook Cancellation Pattern
**Goal**: Every data-fetch hook in the dashboard is cancellation-safe — switching scans mid-fetch never overwrites newer data with stale results, QRAMM debounce coalesces rapid edits into one request, the auto-fill confirm round-trip preserves the badge contract, and a CI guard rule prevents future regressions. Closes Pattern C.
**Wave**: A (gating)
**Depends on**: Phase 56.1 (v4.7 close-out)
**Requirements**: HOOK-01, HOOK-02, HOOK-03, HOOK-04
**Success Criteria** (what must be TRUE):
  1. Every hook in `src/dashboard/src/hooks/` (`useScanData`, `useQRAMMSession`, `useTrendData`, etc.) uses the standardized cancellation pattern (`useCancellableFetch` or equivalent) and gates each `setState` call after an async boundary with an `if (!cancelled)` guard; a Playwright scenario rapidly switches between two scans and asserts the displayed scan ID always matches the most recently selected one
  2. Typing 20 rapid answer changes within a single 300 ms debounce window POSTs exactly one coalesced batch to `/api/qramm/assessment/draft` (verified by a network-recorder test); per-keystroke partial writes never reach the backend
  3. Auto-filling a CVI question and confirming it removes the "Auto-filled from scan" badge in-place without triggering a full QRAMM session refetch — `confirmed_at` round-trips correctly through the existing optimistic-update path
  4. A custom ESLint rule (or codemod check in CI) flags any new `useEffect` block calling `setState` from an async branch without an `if (!cancelled)` guard; the rule fires on a deliberately broken fixture and is silent on a correct fixture
**Plans**: 5 plans

Wave 1 *(Plans 01/02/03 run in parallel — fully disjoint file sets)*
  - [ ] 62-01-PLAN.md — Hook cancellation guards: useScanData (BR-03/BR-04) + useScanList (WR-02)
  - [ ] 62-02-PLAN.md — Hook cancellation guards: useQRAMMSession error branches (WR-01)
  - [ ] 62-03-PLAN.md — QRAMM provider coalescing + confirmAnswer flush + print sentinel + reactive theme (BR-01/02/05/06, WR-03/14)

Wave 2 *(blocked on Wave 1 completion)*
  - [x] 62-04-PLAN.md — Vitest+MSW tests, CI guard script, audit + REQUIREMENTS ledger closure

Wave 3 *(blocked on Wave 2 completion)*
  - [x] 62-05-PLAN.md — docs/UAT-SERIES.md update, Obsidian vault sync, phase note creation (CLAUDE.md mandatory steps)
**UI hint**: yes

### Phase 63: Scheduled / Continuous Scanning
**Goal**: An operator can register a recurring scan via a cron expression, leave QUIRK running, and trust that scans dispatch on schedule with results visible in the dashboard — turning QUIRK from a one-shot CLI into a continuously-running posture monitor (BACK-25).
**Wave**: B (gated on full Wave A completion)
**Depends on**: Wave A complete (Phases 57–62); soft dependency on Phase 67 (scheduled scans benefit from resumable infrastructure)
**Requirements**: SCHED-01, SCHED-02, SCHED-03
**Success Criteria** (what must be TRUE):
  1. `quirk schedule add --name "weekly-prod" --cron "0 2 * * 1" --target prod.example.com --profile balanced` persists a row to a new `scheduled_scans` SQLite table and the row is visible via `quirk schedule list`
  2. `quirk scheduler run` (long-running mode) wakes at the cron time, dispatches the scan, writes results to the standard scan output path, and surfaces dispatch status (`pending` / `running` / `completed` / `failed`) to the dashboard `/schedules` route
  3. The dashboard `/schedules` route lists all scheduled scans with name, target, profile, cron expression, next-run time, last-run timestamp + status, and provides enable/disable toggles that round-trip to the backend
**Plans**: 3 plans
Plans:
**Wave 1**
- [x] 63-01-PLAN.md — DB models (ScheduledScan/ScheduledRun), `quirk schedule` CLI CRUD, run_scan.py interception, croniter dependency (SCHED-01)

**Wave 2** *(blocked on Wave 1 completion)*
- [x] 63-02-PLAN.md — `quirk scheduler run` 60s sleep-loop dispatcher with subprocess invocation, signal handling, startup recovery (SCHED-02)
- [x] 63-03-PLAN.md — FastAPI `/api/schedules` CRUD router (auth+csrf) and React `/schedules` dashboard page with toggle/delete (SCHED-01 API, SCHED-03)
**UI hint**: yes

### Phase 64: Trend Analysis Foundation
**Goal**: Consultants and operators can see how cryptographic posture has moved across the last N scans — overall score, per-pillar subscores, and finding counts on a single timeline — and are alerted when posture regresses (BACK-21).
**Wave**: B (gated on full Wave A completion)
**Depends on**: Wave A complete (Phases 57–62); benefits from Phase 63 data volume
**Requirements**: TREND-01, TREND-02
**Success Criteria** (what must be TRUE):
  1. The `/trends` route renders a multi-scan timeline (default last 30 scans) showing overall readiness, the six pillar subscores (TLS, SSH, API, Identity, Data-at-Rest, Data-in-Motion), and finding counts by severity tier; hovering a point reveals the underlying scan ID and timestamp
  2. A regression — score drop ≥ 5 points OR a new HIGH/CRITICAL finding category vs the previous scan — surfaces as an alert chip on the dashboard home with a deep-link to the regressing scan; the chip is dismissible and the dismissal is per-scan, not global
**Plans**: 3 plans
**Wave 1** *(parallel)*
- [x] 64-01-PLAN.md — Backend: Wave 0 tests + TrendTimelineResponse schemas + GET /api/trends/timeline?n=30 endpoint (TREND-01 backend)
- [x] 64-03-PLAN.md — RegressionAlertChip component + ExecutivePage insertion (TREND-02; consumes existing /api/trends, no Plan 01 dependency)
**Wave 2** *(blocked on 64-01)*
- [x] 64-02-PLAN.md — Frontend: TrendTimeline types + useTimelineData hook + Recharts LineChart on TrendsPage (TREND-01 frontend)
**UI hint**: yes

### Phase 64.1: Audit Residual Blockers
**Goal**: Clear the audit ledger before Phase 65 extends the code paths it documents — record formal dispositions for all 19 open BLOCKERs from the 2026-05-08 audit, and fix the five that either directly undermine Phase 64's already-in-UAT trend feature or land in Phase 65's exact foundations.
**Wave**: B (bridge between Phase 64 and Phase 65)
**Depends on**: Phase 64 complete (human UAT signed off)
**Requirements**: Audit triage of `.planning/audit-2026-05-08/AUDIT-TASKS.md` open rows
**Success Criteria** (what must be TRUE):
  1. `cbom-intel-reports/CR-05` fixed: two scans created within 1 second are no longer merged into the same session window; the trend timeline correctly shows them as distinct data points
  2. `api-cli-core/CR-08` fixed: every `ALTER TABLE` in `init_db()` executes inside a transaction; a failed migration rolls back cleanly with no partial column additions
  3. `qramm-compliance/BL-03` fixed: `last_verified` staleness check uses `datetime.date` comparison, not lexicographic string comparison
  4. `qramm-compliance/BL-04` fixed: `int(years_raw)` input is clamped to `>= 1` before use; negative or zero values raise a validation error with a clear message
  5. `cbom-intel-reports/CR-03` fixed: SOURCE scanner algo hint correctly distinguishes DES from 3DES and preserves AES variant specificity (AES-128 ≠ AES-256)
  6. All remaining 14 open BLOCKERs have a recorded disposition (`deferred-v4.9` or `wont-fix`) with rationale in `AUDIT-TASKS.md` — zero rows remain as bare `[ ] open`
**Plans**: 2 plans
- [x] 64.1-01-PLAN.md — Fix 5 audit BLOCKERs (CR-03, CR-05, BL-03, BL-04, api-cli-core/CR-08) + regression tests + close 5 ledger rows
- [x] 64.1-02-PLAN.md — Apply formal dispositions to remaining 14 open BLOCKERs (deferred-v4.9 / wont-fix) and close 2 Phase-59-mapped rows

### Phase 65: Dashboard-Initiated Scan
**Goal**: An operator who never opens a terminal can configure, launch, and watch a scan progress to completion entirely from the dashboard — closing the primetime gap that currently forces every customer to use the CLI (BACK-86 slice 1).
**Wave**: B (gated on full Wave A completion)
**Depends on**: Phase 64.1 complete, Phase 58 (dashboard auth must exist before the dashboard can dispatch scans), Wave A complete
**Requirements**: UI-SCAN-01, UI-SCAN-02, UI-SCAN-03
**Success Criteria** (what must be TRUE):
  1. A `/scan/new` route presents a form for target spec (single host, comma list, CIDR, `@file`), profile (quick/standard/deep), and options (calibration, scanner toggles); validation errors render against the same Pydantic schema the CLI uses, never silently re-shapes input
  2. Submitting the form creates a scan job and returns a job ID; a live status page polls progress and streams scanner-stage transitions (Discovery → TLS → SSH → … → Reports) to the UI; the page is cancellation-safe per Phase 62 pattern
  3. On scan completion the UI navigates to the new scan's results view and the new scan is selectable from the existing scan switcher; the scan is indistinguishable from a CLI-launched scan in storage and reporting
**Plans**: 6 plans
  - [x] 65-01-PLAN.md — Wave 0 foundation: ScanJob model, DB migration, Checkbox install, pytest stubs
  - [x] 65-02-PLAN.md — quirk/cli/job_progress.py helper + run_scan.py --job-id/--db-path wiring
  - [x] 65-03-PLAN.md — Pydantic schemas + /api/jobs router (POST/GET/DELETE) + 10 test bodies
  - [x] 65-04-PLAN.md — app.py FastAPI lifespan + create_app(db_path) + jobs router mount
  - [x] 65-05-PLAN.md — React types + useJobStatus hook + ScanNewPage + ScanJobPage + routes + sidebar CTA
  - [x] 65-06-PLAN.md — Human UAT walkthrough + ARCHITECTURE.md update + UAT-SERIES.md + Obsidian sync
**UI hint**: yes

### Phase 66: Dashboard Scan History + Clone/Compare
**Goal**: Operators can browse every scan QUIRK has ever produced, re-launch any prior scan with one click ("Clone configuration"), and side-by-side compare any two scans to see exactly what changed (BACK-86 slice 2).
**Wave**: B (gated on full Wave A completion)
**Depends on**: Phase 65
**Requirements**: UI-HIST-01, UI-HIST-02
**Success Criteria** (what must be TRUE):
  1. A `/scans` route lists every scan with date, target, profile, overall score, finding counts by severity, and a "Clone configuration" button that pre-fills `/scan/new` with the source scan's exact configuration
  2. Selecting two scans via "Compare" mode renders a diff view showing readiness score delta, per-pillar subscore deltas, added findings (with severity badges), removed findings, and changed endpoint posture (e.g., a host's cipher list changed); the diff handles scans with disjoint target sets gracefully
**Plans**: 3 plans
  - [x] 66-01-PLAN.md — Wave 0 pytest scaffold (9 failing tests for /api/scans + /api/compare contracts)
  - [x] 66-02-PLAN.md — Backend: extend /api/scans (no LIMIT, enriched fields, clone data) + new /api/compare endpoint
  - [x] 66-03-PLAN.md — Frontend: types + useCompareData hook + /scans + /compare pages + scan-new clone preload + sidebar + build
**UI hint**: yes

### Phase 67: Resumable / Partial-Failure Scans
**Goal**: A scan that crashes mid-run can be resumed from its last completed scanner stage, and a single unreachable target or one cloud connector failure no longer aborts an entire engagement scan — partial results are preserved with explicit per-scanner status.
**Wave**: B (gated on full Wave A completion)
**Depends on**: Wave A complete (Phases 57–62)
**Requirements**: RESUME-01, RESUME-02
**Success Criteria** (what must be TRUE):
  1. A scan that crashes between scanner stages leaves a recoverable checkpoint in a new `scan_checkpoints` SQLite table; `quirk scan --resume <scan-id>` continues from the last completed scanner stage and produces results indistinguishable from an uninterrupted run for the same inputs
  2. A simulated failure of a single connector (e.g., GCP credentials missing) during a multi-connector scan completes the scan with a `partial_failures` array in the output JSON and a per-scanner status panel in the dashboard; remaining scanners' findings are preserved and contribute to the score normally
**Plans**: 5 plans
Plans:
- [x] 67-01-PLAN.md — DB layer: ScanCheckpoint model + _ensure_scan_checkpoints_table + write_scan_checkpoint() helper
- [x] 67-02-PLAN.md — Incremental persistence: per-stage checkpoint writes + partial_failures accumulation in run_scan.py
- [x] 67-03-PLAN.md — _wrapped_phase migration: migrate all inline try/except scanner invocations to _wrapped_phase
- [x] 67-04-PLAN.md — Resume CLI: --resume-scan-id flow + --list-resumable command + partial_failures in output JSON
- [x] 67-05-PLAN.md — Dashboard: PartialFailureEntry schema + partial_failures on ScanLatestResponse + Scanner Status card
**UI hint**: yes

### Phase 68: Operator Error-Message Pass
**Goal**: Every error an operator can encounter — CLI exit codes, dashboard 4xx/5xx responses, persisted `scan_error_category` rows, first-run install-day failures — emits a stable error code, a one-line cause, and a one-line remediation hint, with a single reference page documenting all codes.
**Wave**: B (gated on full Wave A completion)
**Depends on**: Wave A complete (Phases 57–62)
**Requirements**: UX-01, UX-02
**Success Criteria** (what must be TRUE):
  1. Every operator-facing error path (CLI non-zero exit, dashboard 4xx/5xx, `scan_error_category` row) carries a stable error code (e.g., `QRK-NMAP-001`), a one-line cause, and a one-line remediation hint; an `quirk errors` reference page (and `docs/error-codes.md`) lists every code with cause and fix
  2. First-run install-day errors (missing extras, missing nmap binary, port-conflict on `quirk serve`, unreadable `quirk.db`) render with the same one-line-cause + one-line-fix format and reference a specific `QRK-INSTALL-NNN` code; a smoke test exercises each scenario on a fresh venv and asserts the format
**Plans**: 5 plans
Plans:
**Wave 1**
- [x] 68-01-PLAN.md — Create quirk/errors.py canonical error registry + unit tests

**Wave 2** *(blocked on Wave 1 completion)*
- [x] 68-02-PLAN.md — Build quirk errors CLI command + wire run_scan.py argparse + generate docs/error-codes.md

**Wave 3** *(blocked on Wave 2 completion)*
- [x] 68-03-PLAN.md — Migrate CLI error paths (run_scan inline, doctor, schedule, optional_extra, kerberos) + update test_scan_robustness
- [x] 68-04-PLAN.md — Migrate dashboard error paths (middleware, routes, server.py port-conflict) + update affected API tests

**Wave 4** *(blocked on Wave 3 completion)*
- [x] 68-05-PLAN.md — Add install-day smoke tests + docs/error-codes.md freshness CI gate

## Progress — v4.8 Phases

| Phase | Wave | Plans Complete | Status | Completed |
|-------|------|----------------|--------|-----------|
| 57. Scanner Security Hardening | A | 6/6 | Complete   | 2026-05-09 |
| 58. Dashboard API Hardening | A | 6/7 | In Progress|  |
| 59. Credential Leakage Sweep | A | 3/3 | Complete    | 2026-05-10 |
| 60. Score Arithmetic Correctness | A | 2/2 | Complete    | 2026-05-10 |
| 61. CBOM Coverage + Report Sanitization | A | 3/3 | Complete    | 2026-05-10 |
| 62. React Hook Cancellation Pattern | A | 2/5 | Complete    | 2026-05-10 |
| 63. Scheduled / Continuous Scanning | B | 3/3 | Complete   | 2026-05-10 |
| 64. Trend Analysis Foundation | B | 3/3 | Complete   | 2026-05-10 |
| 64.1. Audit Residual Blockers | B | 2/2 | Complete    | 2026-05-11 |
| 65. Dashboard-Initiated Scan | B | 5/6 | In Progress|  |
| 66. Dashboard Scan History + Clone/Compare | B | 3/3 | Complete    | 2026-05-14 |
| 67. Resumable / Partial-Failure Scans | B | 5/5 | Complete    | 2026-05-14 |
| 68. Operator Error-Message Pass | B | 5/5 | Complete    | 2026-05-14 |

---

## v4.9 Audit Depth — Phases 69–77

**Milestone Goal:** Systematically close the 121 remaining open findings from the 2026-05-08 audit (13 deferred BLOCKERs + 92 WARNINGs + 29 INFOs), hardening correctness, resource management, input validation, and code quality across all six scanner subsystems. AUDIT-TASKS.md reaches zero bare-open rows.

### Phase Checklist

- [x] **Phase 69: Deferred BLOCKERs — Scanner + Cloud** - Fix resource leaks (ThreadPool, socket) and cloud data correctness bugs (GCP SQL, K8s, Azure Blob, Cache, TokenBucket) (completed 2026-05-15)
- [x] **Phase 69.1: K8s Test Fixture Hardening (INSERTED)** - Add autouse `*_AVAILABLE` fixture to `tests/test_k8s_connector.py` so the canonical `.venv` (Python 3.14) runs the full k8s_connector suite green regardless of optional cloud-SDK installation. Unblocks Phase 69-03 test + 4 pre-existing failures (completed 2026-05-15)
- [x] **Phase 70: Deferred BLOCKERs — API + QRAMM Model** - Enforce DB-level FK constraint on QRAMMProfile; replace bare except in classifier and harden DDL interpolation (completed 2026-05-15)
- [x] **Phase 71: Protocol Scanner WARNINGs** - Coverage clamp, case-insensitive severity, bare except removal, nmap hardening, identity scanner input bounds, extras/ThreadPool/dedup fixes (completed 2026-05-15)
- [ ] **Phase 72: Cloud Scanner WARNINGs** - AWS/Azure/GCP data correctness, Cache/scope_hash robustness, profiles.py mutations, Vault/DB connector hardening
- [ ] **Phase 73: CBOM + Intelligence + Reports WARNINGs** - PDF resource cleanup, weak-crypto predicate consistency, score weight normalization, cipher label correctness
- [ ] **Phase 74: QRAMM + Compliance WARNINGs** - Practice score validation, evidence bridge TZ safety, migration advisor precision, model_meta helper, stale comment removal
- [x] **Phase 75: API + CLI + Core WARNINGs** - doctor checks, scan-id microsecond safety, list_scans grouping, QRAMM error handling, interactive/validate/route input hardening (completed 2026-05-15)
- [ ] **Phase 76: React Frontend WARNINGs** - API error surfacing, localStorage validation, PDF revoke-on-unmount, ComplianceMapTab dep fix, cert regex, CBOM typing, scorecard math
- [ ] **Phase 77: INFO/Code Quality + Audit Ledger Closure** - Protocol/CBOM/API/React INFOs, AUDIT-TASKS.md fully triaged to zero bare-open rows

### Phase Details

### Phase 69: Deferred BLOCKERs — Scanner + Cloud
**Goal**: The six highest-priority deferred BLOCKERs in the scanner and cloud subsystems are fixed — resource leaks eliminated, cloud data written to correct fields, and rate-limiting primitives safe under all inputs. Closes audit findings scanners-protocol/CR-07, CR-08 and scanners-cloud/CR-02, CR-03, CR-06, CR-07, CR-08, CR-09, CR-10.
**Depends on**: Phase 68 (v4.8 complete)
**Requirements**: BLOCK-01, BLOCK-02, BLOCK-03, BLOCK-04, BLOCK-05, BLOCK-06
**Success Criteria** (what must be TRUE):
  1. An sslyze scan under simulated network error completes without leaving orphaned threads or open sockets; a pytest fixture asserts the ThreadPoolExecutor and tcp_connect socket are closed on all exception paths
  2. A GCP Cloud SQL scan writes SSL enforcement status to `severity` and `description` fields (not `cert_pubkey_alg`); a test asserts `cert_pubkey_alg` is absent from the Cloud SQL finding dict
  3. A K8s scan with `azure_cred=None` returns a K8S-03-conformant empty result (no AttributeError); an empty target list returns `[]` without raising
  4. An Azure Blob finding for a platform-managed key (Microsoft.Storage) contains distinct severity and description from a finding where `key_source` is absent; a test covers both branches
  5. `Cache._is_fresh` with `ttl_hours=0` returns `False` on every call (never fresh); `TokenBucket.acquire(n)` where `n > capacity` raises immediately (no infinite loop)
**Plans**:
  - 69-01 (Wave B): BLOCK-01 — sslyze try/finally cleanup + fingerprint socket close on all exception paths
  - 69-02 (Wave A): BLOCK-02 — GCP Cloud SQL severity → severity column; rewrite 3 existing tests
  - 69-03 (Wave B, depends on 69-01): BLOCK-03 — K8s empty-aks_clusters short-circuit (returns [] per D-09); hosts closing tasks (compileall, full pytest, AUDIT-TASKS flip, Obsidian phase note)
  - 69-04 (Wave A): BLOCK-04 — Azure Blob 3-way branch (BLOB-CMK / BLOB-PLATFORM / BLOB-UNKNOWN) via service_detail + dat_scan_json.finding_id (no schema change)
  - 69-05 (Wave A): BLOCK-05 — cache.py ttl_hours<=0 returns None; UAT-SERIES API contract note
  - 69-06 (Wave A): BLOCK-06 — TokenBucket capacity guard + threading.Condition + rate=0 fast path; new tests/test_rate_limiter.py

### Phase 70: Deferred BLOCKERs — API + QRAMM Model
**Goal**: The two deferred BLOCKERs in the API/QRAMM subsystem are resolved — the `QRAMMProfile` table has a real DB-level FK constraint with safe session deletion, and the classifier no longer uses a bare `except` or interpolates unvalidated strings into DDL. Closes audit findings api-cli-core/CR-04, CR-05, CR-06, CR-07.
**Depends on**: Phase 69
**Requirements**: BLOCK-07, BLOCK-08
**Success Criteria** (what must be TRUE):
  1. The `qramm_profiles` table has a `FOREIGN KEY (session_id) REFERENCES qramm_sessions(id)` constraint; calling `delete_session` nulls the corresponding `profile_id` pointer before deletion, preventing a FK violation
  2. The classifier `except` clause catches a specific exception type (not bare `except`) and logs the error with a structured message; the `col_type` string is validated against an allowlist before interpolation into any `ALTER TABLE` statement
  3. A pytest fixture that attempts to delete a QRAMM session with an active profile verifies the operation completes cleanly (no FK error, no dangling row)
**Plans**: 3 plans
  - [x] 70-01-PLAN.md — FK retrofit on qramm_profiles.session_id + per-connection PRAGMA foreign_keys=ON + delete_session reorder (BLOCK-07, closes CR-04/05)
  - [x] 70-02-PLAN.md — Narrow _qs_for_alg except + module logger in scan.py (BLOCK-08 partial, closes CR-06)
  - [x] 70-03-PLAN.md — _SAFE_COL_TYPE_RE allowlist in 4 _ensure_* helpers + AUDIT-TASKS row flips for CR-04/05/06/07 (BLOCK-08 partial, closes CR-07)

### Phase 71: Protocol Scanner WARNINGs
**Goal**: All five WARNING clusters in the protocol scanner subsystem are resolved — coverage percentages are bounded, severity comparisons are case-insensitive, subprocess errors are logged not swallowed, nmap inputs are validated and parsed safely, identity scanner inputs are bounded, and the extras/ThreadPool/dedup issues are fixed. Closes audit findings scanners-protocol/WR-01 through WR-14.
**Depends on**: Phase 69
**Requirements**: PROTO-01, PROTO-02, PROTO-03, PROTO-04, PROTO-05
**Success Criteria** (what must be TRUE):
  1. `coverage.calculate_coverage` returns a value in `[0.0, 100.0]` (percent) under any input; `quantum_readiness_score` severity comparison passes with mixed-case severity strings (e.g., `"High"`, `"HIGH"`)
  2. A subprocess failure in any protocol scanner emits a logged error (not a bare `except` swallow); the error appears in the scan log and the scan continues with a partial result
  3. `nmap_provider.run_nmap_discovery` validates `extra_args` against a character allowlist and raises on violation; nmap XML is parsed via `defusedxml` (not stdlib ET); default port CSV is correct
  4. DNSSEC `_parse_dnskeys` key_bytes access is bounded; Kerberos decode errors are logged; Kerberos nonce uses `secrets.token_bytes`; SAML JSON parse has a byte-size cap
  5. Optional-dep extras messaging is consistent across email/broker/container/source scanners; email/broker `ThreadPool max_workers` is configurable via `ScanCfg`; `discovery/tls_scanner.py` duplicate is deleted; `target_expander` dedup is stable, CIDR expansion bounded, type confusion resolved
**Plans**: 5 plans
  - [x] 71-01-PLAN.md — calculate_coverage clamp + case-insensitive severity in quantum_readiness_score (PROTO-01, closes WR-01/02)
  - [x] 71-02-PLAN.md — Narrow WR-03 subprocess except + module logger in fingerprint scanner (PROTO-02, closes WR-03)
  - [x] 71-03-PLAN.md — nmap default port CSV + extra_args allowlist + defusedxml parser (PROTO-03, closes WR-04/05/06)
  - [x] 71-04-PLAN.md — DNSSEC bound + Kerberos decode-log + secrets nonce + SAML JSON byte cap (PROTO-04, closes WR-07/08/09/10)
  - [x] 71-05-PLAN.md — Unified extras messaging + ScanCfg.motion_concurrency + delete tls_scanner dup + target_expander cap/dedup/normalize (PROTO-05, closes WR-11/12/13/14)

### Phase 72: Cloud Scanner WARNINGs ✅
**Goal**: All five WARNING clusters in the cloud scanner subsystem are resolved — AWS/Azure/GCP data correctness, Cache and scope_hash robustness, profiles.py mutation guards, and Vault/DB connector hardening. Closes audit findings scanners-cloud/WR-01 through WR-24.
**Depends on**: Phase 69
**Requirements**: CLOUD-01, CLOUD-02, CLOUD-03, CLOUD-04, CLOUD-05
**Success Criteria** (what must be TRUE):
  1. ✅ An AWS ACM scan with an empty ARN does not raise; KMS skips disabled/pending-deletion keys; S3 `executor.map` propagates classifier exceptions; EKS `enc_cfg` reads from the entire list not index 0
  2. ✅ Azure KeyVault `key_size` is populated for all key types; K8s `cluster_name` has colons stripped; K8s `Counter` excludes `None` values; K8s `key_name` is omitted in unencrypted path in `dat_scan_json`
  3. ✅ GCP KMS pagination loop has a cap; UNSPECIFIED/UNKNOWN key handling is consistent; GCP Cloud SQL description is surfaced in `service_detail`
  4. ✅ `Cache._read_json` handles malformed JSON gracefully; `scope_hash` includes connector enable flags; `profiles.py` file verified complete (`# eof` marker)
  5. ✅ All 10 miscellaneous cloud WARNING fixes landed: risk_engine→findings_evaluator rename, profiles.py mutation guard via `_user_set_fields`, standard profile re-apply suppressed, vault VAULT_TOKEN env order, DB password handling, DB exception `safe_str`, AWS ThreadPoolExecutor at module level, Vault PKI PEM via `cryptography.x509`, `_postprocess_findings` safe iteration, `_dedupe_findings` stable sort
**Plans**: 5/5 complete (72-01 AWS, 72-02 Azure/K8s, 72-03 GCP, 72-04 Cache/profiles, 72-05 Misc)
**Status**: ✅ Complete (2026-05-15) — 24/24 WR rows closed, 119/119 targeted tests green

### Phase 73: CBOM + Intelligence + Reports WARNINGs ✅
**Goal**: All three WARNING clusters in the CBOM/intelligence/reports subsystem are resolved — PDF resources are cleaned up, weak-crypto predicates are consistent, and score weights, roadmap output, and cipher labels are corrected. Closes audit findings cbom-intel-reports/WR-01 through WR-14.
**Depends on**: Phase 69
**Requirements**: INTEL-01, INTEL-02, INTEL-03
**Success Criteria** (what must be TRUE):
  1. PDF render exceptions are caught by type (not a blanket `except`); Playwright resources are released in a `finally` block; a PDF generation failure prints a user-visible warning without crashing the scan
  2. `motion_broker_weak_tls_count` predicate is uppercase-consistent; ECDSA detection matches `cert_pubkey_alg` conventions; SAML weak detection handles mixed-case SHA-1; email/broker weak-cipher predicates are unified via shared helper
  3. `SCORE_WEIGHTS` are documented and normalized; the roadmap double-period artifact is removed; executive `_build_interpretation` guards `score['score']` access; TLS 1.2 non-PFS cipher KEX returns the correct `RSA-kex` label; confidence weight overrides pass through clamp and validation
**Plans**: TBD

### Phase 74: QRAMM + Compliance WARNINGs ✅
**Goal**: All three WARNING clusters in the QRAMM/compliance subsystem are resolved — practice scores reject out-of-range inputs, the evidence bridge is TZ-safe and idempotent, and migration advisor precision, coverage disambiguation, and stale comments are fixed. Closes audit findings qramm-compliance/WR-01 through WR-13.
**Depends on**: Phase 70
**Requirements**: QWARN-01, QWARN-02, QWARN-03
**Success Criteria** (what must be TRUE):
  1. `compute_practice_score` raises a clear validation error for answers outside the defined range; Practice 1.1 Discovery score incorporates endpoint count; `vuln_pct` denominator is guarded against zero; the Maturity label `>= 4.0` is either reachable or documented as intentional
  2. Evidence bridge date comparison uses `datetime.date` (not string comparison) and is TZ-safe; `synchronize_session` is idempotent under repeated calls; `db.commit` failures are handled and logged; `attach_context` `AttributeError` is logged not swallowed
  3. Migration advisor substring matching false positives are reduced; `_walk_json_for_alg_strings` covers all `ALG_KEYS`; compliance weight `0.0` vs not-yet-covered is disambiguated in output; `model_meta.py` has `is_qramm_model_stale()` helper; stale Phase 50 TODO comment removed
**Plans**: TBD

### Phase 75: API + CLI + Core WARNINGs
**Goal**: All four WARNING clusters in the API/CLI/core subsystem are resolved — doctor checks return meaningful data, scan-id time-window is microsecond-safe, list_scans grouping is correct, and QRAMM/interactive/validate/route input hardening is complete. Closes audit findings api-cli-core/WR-01 through WR-17.
**Depends on**: Phase 70
**Requirements**: APCL-01, APCL-02, APCL-03, APCL-04
**Success Criteria** (what must be TRUE):
  1. `quirk doctor` `_check_dashboard` and `_check_network` return status objects with actionable content; `_check_db` uses `QUIRK_DB_PATH` env var; `_default_db_path` selects deterministically
  2. `get_latest_scan ?scan_id=` time-window handles microsecond-precision timestamps correctly (no off-by-one exclusion); `list_scans` groups by parsed `datetime` not formatted string; `compute_overall_score` multiplier is validated server-side before DB access
  3. `routes/qramm read_session` returns a structured error on JSON corruption (not a 500 with raw traceback); `_derive_dar_findings` bare `except` is replaced with logged exception; `list_questions` handles `QRAMM_QUESTIONS` schema drift gracefully
  4. Interactive `_prompt_int` handles `EOF` without infinite loop; exposure default is validated; `setattr` nmap injection replaced with `ConnectorsCfg` field; `validate.py` artifact list includes `intelligence-{stamp}.json`; `qramm_cmd` env override has try/except; `routes/scan QUIRK_OUTPUT_DIR` input validated; `parse_target_tokens` validates hostname format
**Plans**: TBD

### Phase 76: React Frontend WARNINGs
**Goal**: All three WARNING clusters in the React frontend are resolved — API error surfacing, localStorage/PDF/ComplianceMapTab correctness, and cert regex/CBOM typing/scorecard math are fixed. Closes audit findings react-frontend/WR-02, WR-04 through WR-13.
**Depends on**: Phase 75
**Requirements**: REACT-01, REACT-02, REACT-03
**Success Criteria** (what must be TRUE):
  1. `useScanList` surfaces non-OK API responses as user-visible error state (not silent empty list); executive `body.detail` coercion is checked before access; print data-ready sentinel is not set when QRAMM has errored; QRAMM `submitError` exposes the actual error message from the API response
  2. `localStorage` Theme value is validated before cast (invalid values fall back to default); executive PDF download `setTimeout` revoke runs on unmount (no leaked timer); `ComplianceMapTab` re-fetches only on targeted dependency change (no spurious refetch loop)
  3. Certificate Subject CN regex handles RFC 2253-escaped commas correctly; CBOM Cytoscape registration cast is replaced with proper TypeScript typing; `ScorecardTab` Maturity Distribution width math and badge classes produce the correct visual output
**Plans**: TBD
**UI hint**: yes

### Phase 77: INFO/Code Quality + Audit Ledger Closure
**Goal**: All four INFO/code-quality requirement groups are addressed across the four subsystems (protocol scanner, CBOM/intelligence, API/CLI, React frontend), and AUDIT-TASKS.md is brought to zero bare-open rows — every one of the 169 findings carries an explicit closed, deferred, or wont-fix disposition. Closes audit findings scanners-protocol/IN-01..06, cbom-intel-reports/IN-01..09, api-cli-core/IN-01..07, react-frontend/IN-01..07, and LEDGER-01.
**Depends on**: Phase 71, Phase 72, Phase 73, Phase 74, Phase 75, Phase 76
**Requirements**: INFO-01, INFO-02, INFO-03, INFO-04, LEDGER-01
**Success Criteria** (what must be TRUE):
  1. All 6 protocol scanner INFOs are closed: TLS SSLContext downgrade is commented, DNSSEC_ALG_MAP includes reserved algorithms 9 and 11, SHA1_INDICATORS is precise, fingerprint Host header is correct, `_is_pfs`/`_is_weak` are deduplicated, Kerberos realm IPv4 detection is hardened
  2. All 9 CBOM/intelligence INFOs are closed: `PLATFORM_VERSION` is centralized, SSH algorithms JSONDecodeError is logged, trend session fetch is batched, `_PROTOCOL_KEYS` is complete, roadmap baseline governance is documented, migration paths truncation indicator added, dead timeframe branch removed, hosts_count falsy handled, `IntelligenceReport` dataclass used or removed
  3. All 7 API/CLI INFOs are closed: QRAMM endpoint types tightened, `_FACES` banner escape corrected, interactive TZ fallback uses IANA name, QRAMM magic numbers extracted to constants, `app.py` closure capture corrected, `db.py` helpers collapsed, `targets.py` CIDR host-list materialisation bounded
  4. All 7 React frontend INFOs are closed: qramm-assessment tab count comment corrected, cbom extension error logged, findings/identity columns memoized, `useQRAMMSession` seededRef reset on New Assessment, cbom compByAlg variance tracked, print `createElement` replaced, `useScanData` propagates fetch URL into errors
  5. `AUDIT-TASKS.md` has zero rows in `[ ] open` state — every finding is `[x] closed`, `[ ] deferred-*`, or `[ ] wont-fix` with rationale
**Plans**: TBD

## Progress — v4.9 Phases

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 69. Deferred BLOCKERs — Scanner + Cloud | 0/TBD | Not started | - |
| 70. Deferred BLOCKERs — API + QRAMM Model | 3/3 | Complete   | 2026-05-15 |
| 71. Protocol Scanner WARNINGs | 5/5 | Complete   | 2026-05-15 |
| 72. Cloud Scanner WARNINGs | 5/5 | Complete   | 2026-05-15 |
| 73. CBOM + Intelligence + Reports WARNINGs | 3/3 | Complete   | 2026-05-15 |
| 74. QRAMM + Compliance WARNINGs | 3/3 | Complete   | 2026-05-15 |
| 75. API + CLI + Core WARNINGs | 4/4 | Complete   | 2026-05-15 |
| 76. React Frontend WARNINGs | 0/TBD | Not started | - |
| 77. INFO/Code Quality + Audit Ledger Closure | 0/TBD | Not started | - |
