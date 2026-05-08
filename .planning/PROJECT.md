# QU.I.R.K. — Quantum Infrastructure Readiness Kit

## What This Is

QU.I.R.K. is a consulting-grade cryptographic inventory scanner and readiness assessment platform
for enterprise networks. It discovers, classifies, and scores an organization's full cryptographic
surface — TLS endpoints, SSH services, API/JWT tokens, cloud KMS configurations, containers,
and source code — then produces a Cryptographic Bill of Materials (CBOM) and a prioritized
quantum-readiness roadmap. It is delivered as a CLI + local web dashboard, with a SaaS platform
on the strategic roadmap.

Primary users: security consultants, IT generalists, and compliance officers running
post-quantum readiness assessments as a billable service.

## Core Value

Produce a complete, defensible cryptographic inventory with a CBOM deliverable and
quantum-readiness score that a consultant can hand to a client in under two hours.

## Requirements

### Validated

**Baseline (pre-milestone)**
- ✓ TLS endpoint scanning (cert extraction, cipher enumeration, expiry detection) — existing
- ✓ SSH banner detection — existing
- ✓ HTTP/plaintext detection — existing
- ✓ Risk engine with findings (severity-ranked) — existing
- ✓ Intelligence layer (4-subscore readiness model, calibration, confidence, delta reports) — existing
- ✓ SQLite persistence — existing
- ✓ Scan profiles (quick/standard/deep) with caching and rate limiting — existing
- ✓ Docker-based chaos lab for scanner validation — existing

**v3.9 Gap Closure milestone (Phases 1–11)**
- ✓ Package renamed QuRisk → QU.I.R.K. / quirk (qcscan/ → quirk/) — Phase 1
- ✓ sslyze integration — primary TLS scanner with fallback (tls_capabilities_json) — Phase 1
- ✓ ssh-audit integration — threaded SSH scanner with full KEX/hostkey/MAC enumeration — Phase 1
- ✓ Single scoring path through intelligence/scoring.py (assessment/ imports removed) — Phase 1, 9
- ✓ cert_pubkey_alg correctly extracted as first probe in _extract_cert_key_type() — Phase 1
- ✓ CycloneDX CBOM pipeline — classifier, builder, writer producing JSON+XML per scan — Phase 2
- ✓ NIST PQC quantum-safety classification per algorithm (50+ entry lookup table) — Phase 2
- ✓ API/JWT scanner — REST endpoint discovery, JWKS fetch, JWT algorithm and key-size classification — Phase 3
- ✓ Container/binary scanner — Syft subprocess wrapper with 23-entry CRYPTO_LIB_ALLOWLIST — Phase 3
- ✓ Source code scanner — semgrep p/cryptography ruleset, file:line service_detail format — Phase 3
- ✓ Cloud connector (AWS) — ACM, KMS, CloudFront, ELBv2 via boto3, KMS_KEY_SPEC_MAP (13 entries) — Phase 3
- ✓ Cloud connector (Azure) — Key Vault + App Gateway via azure-sdk-for-python — Phase 3
- ✓ 6 Docker Compose chaos lab profiles (jwt, registry, source, storage, ssh-weak, ldaps) — Phase 4
- ✓ FastAPI + React SPA dashboard — exec summary, findings table, cert inventory, CBOM viewer, PDF export — Phase 5, 11
- ✓ 7-guide documentation suite including CBOM compliance guide — Phase 6
- ✓ v4.0.0 packaging — quirk init, HTML/PDF reports, visual identity, pip-installable — Phase 7
- ✓ Legacy debt cleanup — removed dead code, connectors, fixed CLI references, modernized datetime — Phase 8
- ✓ Profile-based weight multipliers (strict/balanced/lenient) in compute_readiness_score() — Phase 9
- ✓ E2E dashboard flow — db_path, port propagation, SSH CBOM entries all wired correctly — Phase 11

**v4.1 Foundation Polish (Phases 12–16)**
- ✓ CLI correctness — correct config field names, `quirk --config` command, no `[owner]` placeholder — Phase 12
- ✓ v4.1.0 version string consistent across CLI, reports, CBOM, pyproject.toml — Phase 12, 16
- ✓ Interactive mode rewritten — auto-TZ, profile selection, 17-port consulting defaults, scanner surfacing, targets-first order — Phase 13
- ✓ Calibration profiles (strict/balanced/lenient) applied end-to-end in scoring and dashboard — Phase 14
- ✓ validate.py and migration_advisor corrected — no false validation failures — Phase 14
- ✓ Dead code eliminated — legacy connector stubs, orphaned scorecard.py, SSH cfg.scan guard fixed — Phase 15
- ✓ All 16 Nyquist VALIDATION.md files up to date — Phase 15, 16
- ✓ Flow C (interactive wizard → scan → dashboard with correct profile) fully wired — Phase 16

**v4.2 Identity Crypto (Phases 17–24)**
- ✓ SQLite schema gains kerberos_scan_json, saml_scan_json, dnssec_scan_json columns; [identity] extras group in pyproject.toml — Phase 17
- ✓ DNSSEC scanner — dnspython authoritative NS query, DO-bit, RFC 8624/9905 3-tier classification (CRITICAL/HIGH/SAFE), NSEC/DS-chain detection, CBOM integration — Phase 18
- ✓ BIND9 chaos lab profile — 4 pre-signed DNSSEC zones (RSASHA1-weak, ECDSAP256SHA256-safe, broken-chain, unsigned) — Phase 18
- ✓ SAML/OIDC scanner — defusedxml XXE-safe parsing, RSA-1024/2048 cert extraction, SHA-1 URI detection, OIDC discovery, CBOM integration — Phase 19
- ✓ SimpleSAMLphp chaos lab profile — RSA-1024 signing cert for scanner validation — Phase 19
- ✓ Kerberos scanner — impacket AS-REQ unauthenticated probe, 7-etype severity map (RC4 HIGH, DES CRITICAL, AES-256 SAFE), LDAP graceful degradation, CBOM integration — Phase 20
- ✓ Samba DC chaos lab profile — QUIRK.LAB realm with RC4 enabled, start_period 90s healthcheck — Phase 20
- ✓ Identity surface — evidence.py counters (identity_weak_etype_count, saml_weak_signing_count, dnssec_weak_algo_count) wired into scoring; FastAPI IdentityFinding model; identity_findings[] in /api/scan/latest; React Identity tab — Phase 21
- ✓ Identity CBOM pass 2+3 skip lists — no spurious X.509 CertificateProperties or TLS protocol components for SAML/Kerberos/DNSSEC endpoints — Phase 22-23
- ✓ Scan-session timestamp isolation — shared session_start from run_scan.py into all 3 identity scanners; ISSUE-3 scan-window timing defect eliminated — Phase 24

**v4.3 Data at Rest (Phases 25–31) — SHIPPED 2026-04-26**
- ✓ Identity Findings Accuracy (Phase 25) — RS-family OIDC check in _derive_identity_findings(), TLS-bleed guard in _derive_findings(), ldap3>=2.9.1 in [identity] extras, chaos lab expected results — v4.3
- ✓ GCP connector — Cloud KMS (47-entry algorithm map including PQC), Cloud SQL TLS enforcement, GCS CMEK detection; `[cloud]` extras group; gcs_scan_json ORM column; CBOM Pass 1/2/3 integration — v4.3
- ✓ Database encryption detection — PostgreSQL 3-tier SSL probe (pg_has_role), MySQL Ssl_cipher scanner, RDS StorageEncrypted+KmsKeyId; `[db]` extras group; `dat_scan_json` ORM column; `dar_` evidence counters + `data_at_rest` as 5th subscore; CBOM Pass 1/2/3 integration; Docker chaos lab database profile (25432/23306) — v4.3
- ✓ Object storage audit — S3 severity ladder (HIGH/MEDIUM/None via ThreadPoolExecutor), Azure Blob keySource ladder (CMK/platform-managed), GCS sentinel reuse (zero duplicate API calls); dar_storage_* evidence counters + SCORE_WEIGHTS (12.0/4.0); CBOM Pass 1/2/3 skip-lists; MinIO chaos lab (storage-s3 profile) — v4.3
- ✓ Kubernetes secrets inspection — EKS/GKE/AKS managed encryption APIs, secret type enumeration, RBAC-403 degradation, K8S-03 inaccessible-finding invariant; dar_k8s_* evidence counters + CBOM integration — v4.3
- ✓ HashiCorp Vault connector — transit keys (VAULT-01 + PQC), PKI root+intermediate CA (VAULT-02), auth method risk tiering (VAULT-03); dar_vault_weak_count HIGH-only counter; CBOM Pass 1 algorithm registration, Pass 2+3 skip; dedicated --profile vault chaos lab (port 28200) — v4.3
- ✓ Trend analysis across scan sessions — score delta (D-01 match key), net-new/resolved findings by severity, scan error delta, React /trends dashboard page — v4.3

**v4.4 Data in Motion (Phases 32–37) — SHIPPED 2026-04-29**
- ✓ Email protocol scanning — SMTP/SMTPS, IMAP/IMAPS, POP3/POP3S TLS posture across 7 standard ports; STARTTLS-stripping detection on port 25; weak-cipher HIGH findings; Postfix+Dovecot chaos lab — Phase 32
- ✓ Message broker TLS — Kafka (9092/9093/9094) with optional AdminClient enrichment, RabbitMQ AMQPS (5671) + management API, Redis TLS (6380), Azure Service Bus, AWS SQS; plaintext-listener HIGH findings (KAFKA-PLAIN/AMQP-PLAIN/REDIS-PLAIN); Kafka+RabbitMQ+Redis chaos lab profile — Phase 33
- ✓ Data-in-motion intelligence — six `motion_*` evidence counters, three `motion_*_ratio` scoring weights with profile multipliers; `data_in_motion` 6th named subscore alongside `tls`/`ssh`/`api`/`identity`/`data_at_rest`; D-12 backward compatibility (legacy scans preserve full credit) — Phase 34
- ✓ Motion CBOM integration — Pass-1 algorithm components for email/broker TLS endpoints with quantum-safety classification; Pass-2/3 skip-lists for plaintext-only labels; golden snapshot fixtures; AMQPS/Azure-ServiceBus passthrough — Phase 35
- ✓ Dashboard Motion tab — `/motion` React route with email per-port table + STARTTLS warnings, broker per-family grouped sections + plaintext flags; "Data in Motion" 6th `ScoreGauge`; `motion_findings` field on `/api/scan/latest` — Phase 36 *(wave_0_complete deferred — DEF-v4.4-01)*
- ✓ v4.4.0 release artifacts — version locked across 6 surfaces by `tests/test_version.py`; `[motion]` meta-extra over `[email]+[broker]+[kafka]`; INFRA-03 18-test Nyquist coverage module; first top-level `CHANGELOG.md` + `docs/release-notes/4.4.0.md` — Phase 37

**v4.5 Reliability & Gap Closure (Phases 38–44) — SHIPPED 2026-05-03**
- ✓ Identity API regression fixed — 5-min backward SESSION_BRACKET restores SAML/OIDC in `/api/scan/latest`; DEF-v4.4-02 closed — Phase 38
- ✓ Phase 36 wave_0_complete flip — 36-VALIDATION.md restored from git history, `wave_0_complete: true`; DEF-v4.4-01 closed — Phase 38
- ✓ Data at Rest dashboard tab — 4 per-category tables (Database/ObjectStorage/Kubernetes/Vault) wired to DarFinding Pydantic model; DASH-05 closed — Phase 39
- ✓ Chaos lab parity — `_derive_all_profiles()` reads docker-compose.yml at runtime (zero-drift); `expected_results_v4.md` oracle for 13 listener profiles; docs/chaos-lab.md 8 new profile sections — Phase 40
- ✓ CI stability + scanner robustness — TimeoutsCfg/RetryCfg sub-tables on ScanCfg; `_wrapped_phase` BaseException wrapper; `scan_error_category` column; zero code-reason skips; `pytest` default run < 60s — Phase 41
- ✓ CBOM correctness — CycloneDX 1.6 schema validation gate for all 18 profiles; classifier coverage report (no unknown fallbacks); Pass-2/3 skip-list parametrized tests; MOTION_PLAINTEXT_PROTOCOLS + DAR_SKIP_PROTOCOLS constants — Phase 42
- ✓ Dashboard WCAG AA — zero browser console errors across all routes; visible focus rings; keyboard navigation; semantic heading order; axe-core baseline captured in GHA workflow — Phase 43
- ✓ UAT debt automation — Phase 27 DB integration tests (PostgreSQL/MySQL vs chaos lab); Phase 25/30 traceability annotations + Vault UAT-30-01 live test; Phase 31 seeded-DB /api/trends test; 7 of 14 carry-over items closed — Phase 44

**v4.7 Governance & Compliance Platform (Phases 51–56) — In Progress**
- ✓ QRAMM core infrastructure — `QRAMMSession`/`QRAMMAnswer`/`QRAMMProfile` ORM models; 120-question CSNP catalog; weakest-link scoring engine; 5-endpoint FastAPI CRUD router at `/api/qramm/`; 35-test suite; DEBT-01 `datetime.utcnow` deprecation closed — Phase 51
- ✓ Compliance uplift & health check — SOC2/ISO 27001:2022 mappings; CBOM FIPS 140-3 2-tier annotations (approved/non-approved; `certified` deferred to CMVP attestation phase per D-01); `quirk doctor` pre-engagement health dashboard with Rich table; lab.sh PROFILE_ARGS CLI override fix; `ports_scanned`/`hosts_scanned` in run-stats JSON; DEBT-02/03/04 closed — Phase 52
- ✓ QRAMM Evidence Bridge — `quirk/qramm/evidence_bridge.py` auto-populates 30 CVI dimension questions with `suggested_answer` from the SESSION_BRACKET scan cohort; D-05/D-06/D-07 quartile derivation; `confirmed_at` auto-set in `save_answers` (D-09); badge signal via `suggested_answer IS NOT NULL AND answer_value IS NULL` (QRAMM-14); zero `risk_engine` imports; 8-test TDD suite all GREEN — Phase 53

**v4.6 Enterprise Readiness (Phases 45–50) — SHIPPED 2026-05-05**
- ✓ Install-Day UX — `[all]` meta-extra + `quirk.util.optional_extra` probe registry; coverage-gap advisory findings for missing scanner extras; zero ImportError crashes on `pip install quirk` — Phase 45
- ✓ TLS Finding Gaps — 5 new finding types (expired CRITICAL, self-signed HIGH, untrusted-CA MEDIUM, RSA<2048/EC<256 HIGH); `chain_verified` DB column; `tls-cert-defects` chaos lab profile — Phase 46
- ✓ Nmap Discovery + Multi-Target Wizard — comma/`@file`/CIDR target ingestion; optional nmap pre-scan with 10,000-probe budget guard; `--targets-file` CLI flag; `quirk.util.targets` module — Phase 47
- ✓ Rich Finding Context — `_build_finding` chokepoint enforces non-empty `description`/`remediation`; FIPS 203/204/205 algorithm names replace stale Kyber/Dilithium; CI grep gate — Phase 48
- ✓ Compliance Mapping — `quirk/compliance/` module maps 24 finding categories to PCI-DSS 4.0.1/HIPAA/FIPS 140-3; staleness CI gate; `quirk compliance status` CLI; Compliance Summary in HTML/PDF reports — Phase 49
- ✓ Enterprise Documentation — `docs/architecture.md` + `docs/operators-guide.md` with compliance runbook; both synced to Obsidian vault Reference/ — Phase 50

**SaaS Platform (Future Milestone)**
- [ ] Multi-tenant architecture design
- [ ] Scan job queue (Celery + Redis or similar)
- [ ] User auth and org management
- [ ] Cloud deployment (Docker Compose → Kubernetes)
- [ ] Hosted reporting and CBOM storage

### Out of Scope (v1)

| Feature | Reason |
|---------|--------|
| S/MIME message-content scanning | Email *transport* TLS shipped in v4.4; S/MIME *content* (signed/encrypted email at rest) remains out of scope — agentless model cannot inspect mailbox content |
| Windows AD CS live connector | Complex Kerberos/NTLM auth; stub remains, deferred to v2 |
| Network traffic capture (Zeek/Wireshark) | Requires passive tap; out of scope for agentless model |
| OpenVAS / Nessus integration | Full vuln scanner; different scope, heavy dependency |
| Mobile app | Web-first; SaaS phase determines mobile need |
| Real-time continuous monitoring | SaaS milestone, not v1 |

## Current Milestone: v4.7 Governance & Compliance Platform

**Goal:** Extend QUIRK from a compliance-tagged scanner into a full governance platform by completing the compliance framework and integrating the QRAMM maturity model — making QUIRK's primary consulting deliverable a scored governance assessment grounded in live scanner findings.

**Target features:**
- COMPLY-10: CBOM FIPS 140-3 algorithm-level annotations
- COMPLY-11: SOC 2 / ISO 27001 compliance framework mapping (extends PCI-DSS/HIPAA/FIPS 140-3)
- DOCS-05: `quirk doctor` health-check CLI command
- QRAMM Data Model & Backend API — SQLite tables, FastAPI CRUD, qramm_version/last_verified/source_url staleness metadata
- QRAMM Assessment UI — Org Profile wizard + 120-question dimension assessment
- QRAMM Scorecard & Visualizations — radar chart, maturity distribution, dimension summary
- QRAMM Evidence Bridge — auto-populate QRAMM answers from live scanner findings
- QRAMM Compliance Mapping View — 8 frameworks, coverage table, relevance scores
- QRAMM Report Export — combined governance + technical PDF
- QRAMM staleness enforcement — quarterly CI gate (90-day threshold); `quirk qramm status` CLI
- Tech debt: BACK-56 (datetime.utcnow deprecation), BACK-67 (defusedxml.lxml migration), BACK-87 (lab.sh PROFILE_ARGS bug), BACK-85 (ports_scanned in run-stats)

## Current State: v4.7 In Progress — Phase 53 Complete
Phase 56 complete — QRAMM Governance Assessment section added to PDF export (QRAMM-16)

v4.7 "Governance & Compliance Platform" is underway. Phase 53 (QRAMM Evidence Bridge) complete 2026-05-07: `quirk/qramm/evidence_bridge.py` auto-populates 30 CVI dimension questions with `suggested_answer` values derived from the SESSION_BRACKET scan cohort on session create; D-05/D-06/D-07 quartile/threshold derivation rules implemented; `confirmed_at` auto-set when a human confirms a bridge suggestion (D-09); badge signal is implicit in `suggested_answer IS NOT NULL AND answer_value IS NULL` (QRAMM-14); zero `risk_engine` coupling; 8-test TDD suite all GREEN with 36/36 total passing. Phase 54 (QRAMM Assessment UI & Scorecard) is next on the critical path.

v4.6 "Enterprise Readiness" shipped 2026-05-05 (tag `v4.6.0`). 6 phases, 24 plans, 3-day execution. QUIRK can now be installed with `pip install quirk` without crashes, surfaces 5 new TLS certificate-defect finding types, accepts multi-target and CIDR input with optional nmap discovery, enriches every finding with FIPS-compliant PQC remediation guidance, maps findings to PCI-DSS/HIPAA/FIPS 140-3 controls, and ships two enterprise reference documents. Compliance mapping introduces staleness infrastructure (quarterly review cadence enforced by CI gate).

## Context

- **Current version**: v4.6.0 (shipped 2026-05-05); v4.5.0 shipped 2026-05-03
- **Language**: Python 3.11+ (core scanner, FastAPI backend)
- **Frontend**: React + shadcn/ui + Tailwind CSS (built React bundle in `quirk/dashboard/static/`)
- **Database**: SQLite (local, `./quirk.db`); designed for Postgres migration at SaaS phase
- **Chaos lab**: Docker Compose, 19 profiles (core + 6 Phase 4 + 3 v4.2 identity: dnssec/saml/kerberos + storage-s3 + database + vault + email + broker + tls-cert-defects Phase 46)
- **Business model**: Consulting deliverable — tool enables billable assessments
- **Delivery model**: `pip install quirk[all]` (meta-extra, excludes impacket) or `pip install quirk` (TLS-only minimal); `quirk init` + `quirk --config` + `quirk serve`; SaaS platform (future milestone)
- **Target users**: Security consultants (power), IT generalists (guided), compliance officers (reports)
- **Key differentiators**: CBOM output (CycloneDX 1.6 JSON+XML); 6-pillar quantum-readiness scoring with NIST PQC classification; compliance mapping to PCI-DSS/HIPAA/FIPS 140-3; identity protocol scanning; data-at-rest + data-in-motion coverage; enterprise-grade TLS certificate defect detection; nmap-backed multi-target scanning; chaos lab for client-side scanner validation; polished HTML/PDF reports
- **Test coverage**: ~750+ tests passing (pytest); CI runs in < 60s
- **Known tech debt at v4.6 close**: Phase 46 VERIFICATION.md not authored (code verified live); Phase 47 4 manual TTY tests pending; `test_cbom_schema_validation.py` fails in envs missing cyclonedx json-validation extra; BACK-87 lab.sh PROFILE_ARGS override bug; 7 carry-over UAT items from v4.5
- **v4.6 milestone shipped** (2026-05-05): 6 phases (45–50), 24 plans — install-day UX, TLS finding gaps, nmap/multi-target, rich finding context, compliance mapping, enterprise docs

## Constraints

- **Python-native where possible**: Prefer pip-installable libraries (sslyze, cyclonedx-python, paramiko) over subprocess wrappers
- **Agentless default**: Scanner must work without installing agents on target hosts
- **Consultant UX**: Zero-to-scan in under 10 minutes on a fresh machine; guided setup
- **Offline capable**: Core scan + reporting must work with no internet access (critical for air-gapped client engagements)
- **Existing SQLite schema**: New fields must be additive; no breaking schema migrations in v1

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| FastAPI + React (shadcn/ui) for dashboard | Richest ecosystem for polished security dashboards; SaaS-ready; Playwright PDF | ✓ Good — dashboard ships with exec summary, findings, cert inventory, CBOM viewer, PDF export |
| sslyze over testssl.sh | Python-native, programmatic API, no bash dependency | ✓ Good — sslyze primary path with fallback; tls_capabilities_json column captures deep cipher data |
| ssh-audit over raw paramiko | JSON output, full algorithm enumeration, maps to CBOM | ✓ Good — ssh_audit_json feeds both CBOM builder and dashboard CBOM viewer correctly |
| cyclonedx-python-lib for CBOM | Only Python SDK with full CycloneDX 1.4+ CBOM schema support | ✓ Good — CycloneDX 1.6 JSON+XML outputs validate; CBOM viewer in dashboard renders bipartite graph |
| IBMKit Hyperion over QSE | Open source, CBOM-native output, no proprietary lock-in | ✓ Good — semgrep p/cryptography ruleset used; Hyperion not yet integrated (deferred) |
| Consulting deliverable model | Tool enables billable services; lower GTM friction than SaaS | ✓ Good — CLI + local dashboard is the right v1 model; zero infra cost |
| SaaS on roadmap (not v1) | Avoid premature infrastructure; prove value with CLI first | ✓ Good — SaaS remains future milestone; v4.0 ships without it |
| Rename QuRisk → QU.I.R.K. | Brand identity aligned with product scope and market positioning | ✓ Good — rename complete (Phase 1+7); zero stale references in live codebase |
| Intelligence profile kwarg wired to dashboard | Dashboard reads calibration.profile from intelligence JSON at request time (Phase 14 fix) | ✓ Good — dashboard profile now matches CLI report for same scan; interactive users get correct profile via quirk-output dir alignment (Phase 16) |
| Direct authoritative NS query for DNSSEC | System resolver strips DO bit and DNSKEY records — must query NS directly via dnspython | ✓ Good — scanner correctly retrieves DNSSEC records; authoritative query is the only reliable path |
| impacket in [identity] extras only | pyOpenSSL transitive conflict risk prevents placing impacket in core deps | ✓ Good — identity extras group keeps core install lightweight; consultants opt in with pip install quirk[identity] |
| SAML_NS dict constant required | lxml XPath produces empty results without explicit namespace dict — silent failure without it | ✓ Good — SAML_NS as module-level constant is the correct lxml pattern; discovered during RED test debugging |
| Shared session_start from run_scan.py | Per-scanner datetime.now() at endpoint creation time caused scan-window timing to exclude early-stamped identity endpoints | ✓ Good — ISSUE-3 eliminated; all identity endpoints from one scan share one scanned_at timestamp |
| ldap3 added in Phase 25 | ldap3 was absent from pyproject.toml at v4.2 ship; fixed as first task of v4.3 | ✓ Good — ldap3>=2.9.1 in [identity] extras; KERB-03 LDAP path is now reachable |
| `[motion]` as a meta-extra over `[email]+[broker]+[kafka]` (v4.4 INFRA-02) | `pip install quirk[motion]` becomes one command for the full data-in-motion surface; sub-extras stay independently installable for narrow deployments | ✓ Good — `email = []` (zero non-core deps), `broker = ["redis>=5.0"]`, `kafka = ["kafka-python>=2.0"]`; legacy `[redis]` preserved for back-compat |
| Single auditable Nyquist coverage module (v4.4 INFRA-03) | Spreading 18 Nyquist tests across phase-VALIDATION matrices fragments review; collecting them in one file (`tests/test_infra03_nyquist_coverage.py`) makes coverage trivially auditable | ✓ Good — 18 explicit functions (6 entry points × 3 scenarios) all GREEN; matrices in 32/33-VALIDATION.md cite them |
| Azure Service Bus + AWS SQS dispatched through `scan_rabbitmq_targets` | Cloud broker probes share AMQPS/HTTPS-only TLS posture path with on-prem RabbitMQ; separate top-level functions would duplicate code | ✓ Good — `azure_namespaces=`/`sqs_regions=` parameters route to the same probe pipeline; protocol labels (`AMQPS/Azure-ServiceBus`, `HTTPS/AWS-SQS`) distinguish provenance |
| `data_in_motion` legacy-scan backward compatibility (v4.4 D-12) | Re-loading a v4.3 scan in v4.4 should not artificially deflate the score — pre-Phase-34 scans have no `motion_*` keys | ✓ Good — absence of `motion_*` keys is detected and treated as "full credit" rather than "zero findings" |
| No git-tag and no `/gsd-complete-milestone` inside Phase 37 (D-10/D-11) | Tagging and milestone close are visible-to-others actions; reserve them for explicit user trigger after Phase 37 lands | ✓ Good — Phase 37 closed cleanly, then user triggered tag and `/gsd-complete-milestone v4.4` separately |
| `_derive_all_profiles()` reads docker-compose.yml at runtime (v4.5 Phase 40) | Hardcoded ALL_PROFILES list in lab.sh drifted 3 times in one milestone — structural fix more durable than discipline | ✓ Good — profile names are now always in sync; grep pattern extended to `[a-zA-Z0-9_-]` to handle uppercase (phaseA) profile names |
| `_wrapped_phase` BaseException helper in run_scan.py (v4.5 Phase 41) | Per-scanner try/except was inconsistent — 12 scanner phases, 12 different patterns; single helper enforces D-14 uniformly | ✓ Good — KeyboardInterrupt/SystemExit re-raised; all other exceptions captured as `scan_error_category='exception'`; trends.py excludes `missing_extra` from regression counts |
| TimeoutsCfg/RetryCfg as ScanCfg sub-tables with deprecation aliases (v4.5 Phase 41) | 4 flat timeout fields on ScanCfg with no single source of truth; BACK-45 cfg.scan mutation spread across callers | ✓ Good — `@dataclass(init=False)` + custom `__init__` makes legacy kwarg routing self-documenting; BACK-45 dissolved by passing explicit kwargs |
| CycloneDX 1.6 schema validation in CI via `[validation]` umbrella extra (v4.5 Phase 42) | Schema validation was missing — silent output drift between releases; `jsonschema` + `lxml` already present, gating was the gap | ✓ Good — per-profile JSON+XML validated in pytest; docker-compose drift sentinel added to catch profile-name changes without oracle update |
| MOTION_PLAINTEXT_PROTOCOLS + DAR_SKIP_PROTOCOLS as module-level frozensets (v4.5 Phase 42) | Duplicated inline sets across Pass-2/3 skip logic were invisible to parametrized testing | ✓ Good — constants extracted; skip-list parametrized unit tests cover all 14 motion labels and 7 DAR protocols |
| `_build_finding` chokepoint as single finding dict emitter (v4.6 Phase 48) | Per-branch description drift was invisible — 20+ call sites, no enforcement; helper enforces non-empty description/remediation | ✓ Good — CI grep gate + chokepoint together prevent stale PQC terminology from re-entering |
| `COMPLIANCE_MAP` keyed by finding category string (v4.6 Phase 49) | Finding category (title prefix) is the stable API surface shared by risk_engine and compliance module | ✓ Good — `_normalize_for_compliance` longest-prefix-first matching; UNMAPPED_TITLES allow-list covers 7 intentionally unmapped cases |
| `[all]` meta-extra excludes `[identity]` (v4.6 Phase 45) | impacket pyOpenSSL transitive conflict downgrades `cryptography`, breaking TLS scanner | ✓ Good — `[all]` is safe for most users; `[identity]` requires explicit opt-in; documented in operators-guide |
| Hybrid docs structure: canonical sections + "See also" links (v4.6 Phase 50) | Avoids duplicating connector guides while keeping operators-guide self-contained | ✓ Good — operators-guide stays under 1,000 lines; existing connector docs remain authoritative |

---
*Last updated: 2026-05-08

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state
