# Roadmap: QU.I.R.K.

## Milestones

- ✅ **v3.9 Gap Closure** — Phases 1–11, 40 plans (shipped 2026-04-04) → `.planning/milestones/v3.9-ROADMAP.md`
- ✅ **v4.1 Foundation Polish** — Phases 12–16, 10 plans (shipped 2026-04-08) → `.planning/milestones/v4.1-ROADMAP.md`
- ✅ **v4.2 Identity Crypto** — Phases 17–24, 14 plans (shipped 2026-04-24) → `.planning/milestones/v4.2-ROADMAP.md`
- 📋 **v4.3 Data at Rest** — Phases 25–31 (active)

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

### 📋 v4.3 Data at Rest (Active)

**Milestone Goal:** Expand cryptographic inventory to cover data-at-rest encryption and cloud coverage depth — database encryption, object storage policies, Kubernetes secrets, HashiCorp Vault transit keys, GCP connector, and cross-session trend analysis. Phase 25 carries over identity accuracy fixes from v4.2.

- [ ] **Phase 25: Identity Findings Accuracy** - OIDC RS256 routing fix + ldap3 to [identity] extras; closes NEW-ISSUE-1 and ISSUE-2 from v4.2 audit
- [ ] **Phase 26: GCP Connector** - Cloud KMS key specs, Cloud SQL TLS enforcement, GCS bucket encryption; ADC credentials; GCS data passed to Phase 28
- [ ] **Phase 27: Database Encryption Detection** - PostgreSQL pg_stat_ssl, MySQL SSL status, RDS StorageEncrypted/StorageEncryptionType; installs dat_scan_json column and dar_ scoring infrastructure (CRITICAL PATH)
- [ ] **Phase 28: Object Storage Audit** - S3 SSE-S3/SSE-KMS/CMK, Azure Blob CMK/platform-managed, GCS CMEK via Phase 26 data; ThreadPoolExecutor S3 enumeration
- [ ] **Phase 29: Kubernetes Secrets Inspection** - EKS/GKE/AKS managed cluster encryption APIs; kube-apiserver pod spec; secret type count; encryption-config-inaccessible finding
- [ ] **Phase 30: HashiCorp Vault Connector** - Transit key type map (incl. ml-dsa/slh-dsa PQC positive), PKI mount CA cert, auth method list; hvac in [cloud] extras
- [ ] **Phase 31: Trend Analysis** - Score delta + new/resolved findings via scanned_at grouping; GET /api/trends; React Trends tab; no new SQLite table

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

### Phase 25: Identity Findings Accuracy
**Goal**: OIDC RS256 endpoints appear correctly in the Identity tab (not mislabeled as TLS-sourced in the Findings tab), and `ldap3` is installable via `pip install quirk[identity]` enabling Kerberos LDAP enumeration
**Depends on**: Phase 23
**Requirements**: SAML-04, IDENT-02, IDENT-03, KERB-03, INFRA-03
**Gap Closure:** Closes NEW-ISSUE-1 and ISSUE-2 from v4.2 milestone audit (2026-04-24)
**Success Criteria** (what must be TRUE):
  1. `_derive_identity_findings()` in `scan.py` produces `IdentityFinding(source="saml")` objects for OIDC endpoints with RS-family algorithms (RS256, RS384, RS512) using severity from `OIDC_ALG_SEVERITY`
  2. OIDC RS256 endpoints no longer appear in the Findings tab as TLS-sourced; they appear in the Identity tab under SAML/OIDC
  3. `pyproject.toml` `[identity]` extras group includes `ldap3>=2.9.1`; `pip install quirk[identity]` resolves ldap3 without conflicts
  4. Full test suite passes with no regressions
**Plans**: 3 plans
Plans:
- [x] 25-01-PLAN.md — TDD RED: failing tests for SAML-04, IDENT-02, IDENT-03, KERB-03
- [x] 25-02-PLAN.md — TDD GREEN: RS-family check in _derive_identity_findings(), TLS-bleed guard, ldap3 dep
- [x] 25-03-PLAN.md — Doc: identity chaos lab expected results for DNSSEC, SAML/OIDC, Kerberos

### Phase 26: GCP Connector
**Goal**: QU.I.R.K. can enumerate Google Cloud Platform cryptographic posture — Cloud KMS key specs, Cloud SQL TLS enforcement, and GCS bucket encryption — using Application Default Credentials, with GCS bucket data passed forward for object storage audit reuse
**Depends on**: Phase 25
**Requirements**: GCP-01, GCP-02, GCP-03
**Success Criteria** (what must be TRUE):
  1. Scanning a GCP project with Cloud KMS keys returns key specs (RSA-2048/4096, ECDSA P-256/P-384, AES-256, HMAC-SHA256, external/HSM variants) with quantum-safety classification in the CBOM output
  2. A Cloud SQL instance with TLS enforcement disabled produces a HIGH finding; an instance with require_ssl=true produces no TLS finding
  3. GCS bucket enumeration returns per-bucket encryption type (CMEK with customer key vs Google-managed key); this data is stored and made available to Phase 28 without re-fetching
  4. When GCP credentials are absent at runtime, scanner catches DefaultCredentialsError and emits a gcp-credentials-unavailable scan_error finding rather than crashing
  5. google-cloud-kms and google-cloud-storage are declared in [cloud] extras; pip install quirk[cloud] resolves without grpcio/protobuf conflict
**Plans**: 3 plans
Plans:
- [x] 26-01-PLAN.md — Infrastructure: [cloud] extras, config fields, ORM column, DB migration, test scaffold
- [x] 26-02-PLAN.md — Core GCP connector: Cloud KMS, Cloud SQL, GCS scanning
- [x] 26-03-PLAN.md — Integration wiring: run_scan.py and CBOM builder extension

### Phase 27: Database Encryption Detection
**Goal**: QU.I.R.K. can detect encryption-at-rest posture for PostgreSQL, MySQL/MariaDB, and RDS instances — establishing the dat_scan_json column and dar_ scoring infrastructure that all subsequent data-at-rest scanner phases depend on
**Depends on**: Phase 25
**Requirements**: DB-01, DB-02, DB-03
**Success Criteria** (what must be TRUE):
  1. _ensure_v43_columns() in db.py idempotently adds dat_scan_json TEXT to crypto_endpoints — running against a v4.2 quirk.db does not raise any migration error
  2. RDS scanner detects StorageEncrypted flag and StorageEncryptionType (none / sse-rds / sse-kms) via the existing boto3 session; AWS-managed key vs CMK is distinguished in findings
  3. PostgreSQL scanner detects privilege level before querying pg_stat_ssl — when pg_read_all_stats role is absent, emits insufficient-privilege scan_error rather than a false "SSL enabled" result
  4. MySQL/MariaDB scanner reports SSL session status and emits a finding with the negotiated cipher when SSL is disabled or weak
  5. dar_ prefix evidence counters appear in evidence.py and flow into scoring.py as a 5th subscore prefix; psycopg2-binary and PyMySQL are declared in [db] extras
**Plans**: 4 plans
Plans:
- [x] 27-01-PLAN.md — RED scaffold: pyproject.toml [db] extras, ConnectorsCfg fields, models.py dat_scan_json, db.py _ensure_v43_columns, 14 failing tests
- [x] 27-02-PLAN.md — GREEN: quirk/scanner/db_connector.py (PostgreSQL + MySQL scanners), aws_connector.py _scan_rds_encryption
- [x] 27-03-PLAN.md — dar_ scoring infrastructure: evidence.py counters, scoring.py 5th subscore prefix (parallel with Plan 02)
- [x] 27-04-PLAN.md — Integration wiring: run_scan.py db_scanning block, CBOM skip lists, chaos lab database profile

### Phase 28: Object Storage Audit
**Goal**: QU.I.R.K. can determine per-bucket encryption policy for S3, Azure Blob, and GCS — consuming GCS enumeration data from Phase 26 rather than re-fetching, with parallel S3 probing via ThreadPoolExecutor
**Depends on**: Phase 26, Phase 27
**Requirements**: STOR-01, STOR-02, STOR-03
**Success Criteria** (what must be TRUE):
  1. S3 audit returns per-bucket encryption policy (SSE-S3, SSE-KMS with CMK vs AWS-managed key, or unencrypted) across all buckets using ThreadPoolExecutor(max_workers=10) — no OperationNotPageableError from attempting to paginate list_buckets
  2. Azure Blob audit returns per-container encryption configuration (platform-managed key vs customer-managed CMK) for a configured Azure subscription
  3. GCS bucket encryption audit reuses Phase 26 connector output — scanner logs confirm zero duplicate storage.buckets.list API calls in a single scan run
  4. Unencrypted S3 buckets produce HIGH findings; SSE-KMS with AWS-managed key produces MEDIUM; SSE-KMS with CMK produces no finding
  5. All object storage findings are stored in dat_scan_json and produce protocol="STORAGE" CryptoEndpoint rows; results appear in the CBOM
**Plans**: 3 plans
Plans:
- [x] 28-01-PLAN.md — RED scaffold: pyproject [cloud] extras, ConnectorsCfg fields, 5 RED test files
- [x] 28-02-PLAN.md — GREEN: _scan_s3_encryption, _scan_blob_encryption, run_scan.py wiring
- [x] 28-03-PLAN.md — Evidence/scoring/CBOM extensions, MinIO chaos lab, docs/UAT updates

### Phase 29: Kubernetes Secrets Inspection
**Goal**: QU.I.R.K. can detect etcd encryption status and enumerate secret types on managed Kubernetes clusters — using managed cloud APIs without requiring direct etcd access or agent installation on cluster nodes
**Depends on**: Phase 27
**Requirements**: K8S-01, K8S-02, K8S-03
**Success Criteria** (what must be TRUE):
  1. EKS encryptionConfig API, GKE databaseEncryption.state API, and AKS Key Vault integration API each return etcd encryption status when valid cluster credentials are configured — three distinct API call paths returning a consistent encryption finding schema
  2. Secret type count enumeration returns Opaque, kubernetes.io/tls, kubernetes.io/dockerconfigjson, and other types for a configured cluster namespace without reading any secret values
  3. When etcd encryption state cannot be determined via available managed-cluster APIs, scanner emits an explicit encryption-config-inaccessible finding with remediation guidance — never silently skips
  4. kubernetes>=35.0.0 is declared in [cloud] extras; RBAC 403 errors are caught and produce insufficient-rbac-privileges findings rather than unhandled exceptions
**Plans**: 4 plans
Plans:
- [x] 29-01-PLAN.md — RED scaffold: pyproject.toml + ConnectorsCfg + failing tests for k8s_connector and ISSUE-2/3 invariants
- [x] 29-02-PLAN.md — GREEN implementation: k8s_connector.py (GKE+AKS+secret enum) + EKS in aws_connector.py + run_scan.py wiring
- [x] 29-03-PLAN.md — Intelligence + CBOM + dar_k8s tests + lab docs + UAT-SERIES.md updates
- [x] 29-04-PLAN.md — Gap closure (CR-01/CR-02/CR-03 from 29-VERIFICATION.md): evidence.py scan_error counter; AKS credential failure inaccessible emit; service_detail aligned to docs

### Phase 30: HashiCorp Vault Connector
**Goal**: QU.I.R.K. can enumerate HashiCorp Vault cryptographic posture — transit key types (including PQC key types as positive findings), PKI mount CA certificate algorithm, and auth method risk assessment
**Depends on**: Phase 27
**Requirements**: VAULT-01, VAULT-02, VAULT-03
**Success Criteria** (what must be TRUE):
  1. Vault transit key enumeration returns key types with quantum-safety classification via VAULT_TRANSIT_KEY_MAP; ml-dsa and slh-dsa key types produce positive quantum-safe findings in the CBOM
  2. PKI mount CA certificate extraction detects RSA signing keys below 4096 bits or SHA-1 signing algorithms and produces HIGH findings
  3. Active auth method list flags higher-risk methods (token, LDAP root bind) with remediation guidance; token is sourced from VAULT_TOKEN env var or config
  4. hvac>=2.4.0 is declared in [cloud] extras; connection errors (invalid token, unreachable Vault) produce scan_error findings rather than unhandled exceptions
  5. All Vault findings are stored in dat_scan_json and produce protocol="VAULT" CryptoEndpoint rows
**Plans**: 3 plans
Plans:
- [x] 30-01-PLAN.md — RED scaffold: pyproject.toml + ConnectorsCfg + failing tests for vault_connector and DAR scoring
- [x] 30-02-PLAN.md — GREEN scanner: implement vault_connector.py (transit + PKI + auth) and wire into run_scan.py
- [x] 30-03-PLAN.md — Intelligence + CBOM + chaos lab seed + UAT-SERIES.md updates

### Phase 31: Trend Analysis
**Goal**: The intelligence layer can compare the current scan session against the most recent previous session — surfacing score delta, net-new findings, and resolved findings — with results in the dashboard and reports
**Depends on**: Phase 27, Phase 28, Phase 29, Phase 30
**Requirements**: TREND-01, TREND-02, TREND-03, TREND-04
**Success Criteria** (what must be TRUE):
  1. compute_trend_report() in intelligence/trends.py returns a score delta between the two most recent distinct scan sessions using scanned_at-based grouping from list_scans() — no new SQLite table is required
  2. Trend report identifies net-new findings (present in current scan, absent in previous) with counts by severity
  3. Trend report identifies resolved findings (present in previous scan, absent in current) with counts by severity
  4. GET /api/trends returns trend data that the dashboard Trends tab surfaces: readiness score delta and new/resolved finding counts for the two most recent sessions; NULL collision with v4.2-era scan sessions is documented as expected behavior, not treated as a bug
**Plans**: 0 plans
Plans:
**UI hint**: yes

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

---

## Progress

**Execution Order:**
v3.9 complete. v4.1 complete. v4.2 complete. v4.3 active: 25 -> 26 -> 27 -> 28/29/30 (parallel) -> 31

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
| 30. HashiCorp Vault Connector | v4.3 | 3/3 | Complete   | 2026-04-26 |
| 31. Trend Analysis | v4.3 | 0/0 | Planned | — |
