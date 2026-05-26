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

**v4.8 Pre-Primetime Hardening + Operating Model (Phases 57–68) — SHIPPED 2026-05-14**
- ✓ Scanner security hardening — JWT JWKS TLS verification, SAML SSRF allowlist, semgrep/syft argument-injection guards, broker hardcoded-credential removal, broker TLS-required default — Phase 57
- ✓ Dashboard API hardening — single-user bearer auth + CSRF, CORS allowlist lockdown, per-route rate limiting, path-traversal guards for `quirk init` and `@file`, PDF SSRF clamp — Phase 58
- ✓ Credential leakage sweep — shared `safe_str(exc)` helper across all connectors/routes; AST-based pytest gate prevents regressions — Phase 59
- ✓ Score arithmetic correctness — readiness clamp ≤100, QRAMM multiplier guard, confidence-bonus zero-data guard, contiguous maturity threshold bands — Phase 60
- ✓ CBOM Pass-1 coverage + report sanitization — algorithm components for 12+ protocol families previously emitting zero; VAULT classification consistent across all passes; markdown report escaping — Phase 61
- ✓ React hook cancellation pattern — `if (!cancelled)` guards across all data-fetch hooks; QRAMM debounce coalescing; `confirmAnswer` flush; Vitest+MSW test infra; CI guard script — Phase 62
- ✓ Scheduled/continuous scanning — `scheduled_scans`/`scheduled_runs` SQLite tables; `quirk schedule` CRUD CLI; `quirk scheduler run` dispatcher; dashboard `/schedules` page — Phase 63
- ✓ Trend analysis foundation — `/api/trends/timeline` multi-scan endpoint; 7-series Recharts LineChart on `/trends`; `RegressionAlertChip` on executive dashboard with per-session localStorage dismissal — Phase 64
- ✓ Audit residual blockers — 5 code fixes (algo hints, staleness date, years clamp, ms-precision session window, non-transactional init_db); 14 D-06 structured dispositions for remaining BLOCKERs — Phase 64.1
- ✓ Dashboard-initiated scan — `/scan/new` form with Pydantic-shared validation; `/scan/job/:id` live stage polling; post-completion navigation; `ScanJob` backend model — Phase 65
- ✓ Scan history + clone/compare — `/scans` history list with enriched fields; Clone pre-fill with reconstruction notice for CLI scans; `/compare` diff view (score delta, 6 subscore pillars, findings diff) — Phase 66
- ✓ Resumable/partial-failure scans — `scan_checkpoints` table; `--resume-scan-id` CLI; per-scanner `_wrapped_phase()` uniform error capture; `ScannerStatusCard` on executive dashboard — Phase 67
- ✓ Operator error-message pass — `quirk/errors.py` stable registry (50 codes, cause+remediation); `quirk errors` CLI; `format_error()` applied across all CLI exits, dashboard 4xx/5xx, and install-day paths — Phase 68

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
- ✓ Executive Narrative + Score Transparency — shared `ExecContent` model; readiness narrative, top business risks, effort/impact remediation roadmap, subscore decomposition + ÷1.5 rollup; congruence guard; cross-surface parity (EXEC-01..04, TRANS-01..03) — v5.2 Phase 98
- ✓ Per-Finding Context + Code-Signing Expiry — `ALGO_IMPACT_MAP` 3-tuple + `REMEDIATION_CATALOG`; per-finding quantum-risk "so what" + weakness-specific remediation on every finding; code-signing expiry as a first-class finding via `evaluate_codesign_endpoints` (CTX-01/02/03) — v5.2 Phase 99
- ✓ Professional & Editable Report Delivery — branded PDF cover (configurable logo) + print CSS / clean pagination; editable DOCX export auto-emitted from the shared content model, `[docx]` optional extra with graceful skip (FMT-01/02/03) — v5.2 Phase 100

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

## Current State

**v5.4 Distributed On-Prem Scanner Architecture — SHIPPED 2026-05-26** (Phases 106–112, 20 plans, local tag `v5.4.0`). QU.I.R.K. now scans a segmented enterprise network segment-by-segment: lightweight sensors scan locally and push results outbound to a single-tenant console that merges them into one authoritative CBOM + one quantum-readiness score (Option A union scoring), with `coverage_warning` when sensors are missing, sensor/segment awareness across the dashboard, an OS-agnostic wire contract validated on `windows-latest`, and a multi-segment chaos-lab. Milestone audit PASSED (0 blockers, 7/7 phases, 33/33 requirements). Full record: `.planning/MILESTONES.md` + `.planning/milestones/v5.4-ROADMAP.md`.

**Next milestone continues from Phase 113** (run `/gsd:new-milestone`). Carry-forward: per-sensor token auth + revocation (TD-1), automatic merge-trigger (106 D-06), Windows packaging ceiling (106 D-05).

<details>
<summary>v5.4 milestone goal + target features (shipped — archived detail)</summary>

**Goal:** An agent/console split — sensors scan locally inside each network segment and push results *outbound* to a single-tenant console that merges them into one CBOM + one quantum-readiness score, with no inbound access to any segment required.

**Target features:**
- **Architecture document + data-model design (ANCHOR — Phase 1, folds in 999.58):** the sensor/console contract, enrollment/auth model, and the `sensor_id`/segment dimension on `CryptoEndpoint` (same RFC1918 IP can legitimately exist in two segments). Design input for everything downstream; no code until this lands.
- **Authenticated results-ingestion API (console side):** sensors push scan results to the console over an authenticated endpoint, reusing v5.3's token-auth + outbound-push + delivery-audit + SSRF/`safe_str` discipline.
- **Sensor mode + enrollment:** a scan-local, push-outbound runtime that a consultant drops into each segment; enrollment binds a sensor to a console.
- **Cross-sensor merge:** the console merges results from N sensors into one CBOM + one authoritative quantum-readiness score across all segments.
- **Cross-platform sensors — Windows in scope:** the sensor (ideally the full tool) must run on Windows, not just Linux. Windows runtime host (Service/Scheduled Task, not cron/systemd), packaging for Python-less locked-down boxes (frozen exe / container), a POSIX-ism audit, and a Windows CI smoke-test validation path. **Sizing risk** — the arch-doc phase decides whether full Windows-sensor support lands in v5.4 or splits to a v5.5 fast-follow; v5.4 floor is keeping the sensor↔console contract OS-agnostic.
- **Stabilization tail:** 999.59 (operators-guide all-configurations coverage), extract duplicated `_NoRedirectHandler` → `quirk/util/no_redirect.py`, residual dep hygiene.

**Key context:**
- **SaaS multi-tenancy stays PARKED** — distributed on-prem is a network-topology / engagement-completeness necessity (segmented enterprise nets a single host can't reach), NOT a business-model bet. The "multi-segment customer ask" gate that held 999.22 is now satisfied (PM review 2026-05-25); SaaS remains gated on a business-model signal that does not yet exist.
- **Single-tenant only; architecture doc first (Phase 1) before any code.** This is the largest architectural change in the project's history (new service role + data-model change + cross-platform sensors) — research-first milestone.
- **Groundwork is freshest now:** v5.3 just built the console-side primitives (token-auth ingestion, outbound-push, delivery-audit, SSRF discipline); a sensor→console push is their mirror image.
- **Cadence note:** v5.4 deliberately breaks the 2:1 capability/ops rhythm — it's a capability cliff for the ICP, and v5.3 closed low-debt, so the stabilization breather defers and its items fold into v5.4's tail instead.
- **Parked, NOT entry conditions:** the 19 v5.3 live-delivery human-UAT items (Slack/email/webhook/syslog/Jira/ServiceNow) stay deferred — no test environment. Do not block v5.4 on them.
- Numbering continues at **Phase 106**. Source of truth for forward outlook: `.planning/HORIZON.md`.

</details>

## Previous Milestone: v5.3 Adoption & Integration Surface — SHIPPED 2026-05-25

**Delivered:** QU.I.R.K. is now load-bearing in others' workflows. Scheduled-scan drift fans out to Slack/email/webhook (101); findings push to any SIEM as syslog/CEF (103); per-finding tickets auto-open in both Jira (104) and ServiceNow (105) with idempotent SHA256 dedup behind one shared `TicketingChannel` abstraction; and a team can share a single-tenant dashboard via a rotatable API token + login form (102, which also fixed the CLI score-source tax). All integrations sit on one SSRF-safe, secret-scrubbing delivery layer established by the Phase 101 anchor. **Audit PASSED** (21/21 requirements, 18/18 cross-phase integration, 3/3 E2E flows; all 5 phases Nyquist-compliant). 20 plans, 50 tasks. 19 live-delivery items remain as human-UAT (network sends unit-tested with mocked transports). Local tag `v5.3.0`.

**Original goal:** Make QU.I.R.K. load-bearing inside someone else's workflow — findings and scheduled-scan drift events flow into the tools security teams already use, rather than living only in QU.I.R.K.'s own reports.

**Delivered features:**
- **Notification fan-out (ANCHOR):** Slack / email / webhook delivery of scheduled-scan drift events. Drift events are already emitted internally but never delivered — half-built, so this is the lowest-risk, highest-signal starting point. Finish this first as the North Star before adding breadth.
- **SIEM / observability export:** one export integration (Splunk HEC / Elastic / generic syslog+CEF) so findings surface in existing security stacks.
- **Ticketing integration:** one of Jira / ServiceNow — auto-ticket per finding carrying QRAMM evidence, closing the remediation loop.
- **Dashboard team auth:** API-key / token-based single-tenant dashboard auth for team sharing — explicitly NOT SaaS multi-tenancy (that stays deferred to v5.4, gated on a real adoption signal).
- **Tax (folded from v5.2):** thread `exec_content.score_total/score_band/subscores` into the CLI executive markdown instead of re-deriving locally, and add a score-number cross-surface parity test.

**Key context:**
- **Anchor-first to avoid grab-bag sprawl.** HORIZON's explicit risk for this milestone is integration sprawl; mitigation is to finish notification fan-out first, then add exactly ONE export + ONE ticketing integration — not all of everything.
- **Single-tenant only.** SaaS multi-tenancy stays parked (gated on a business-model signal). Distributed multi-node (999.22, on-prem agent/console split) was decoupled from the SaaS gate on 2026-05-25 — the multi-segment on-prem ask surfaced and it's now the committed **v5.4 anchor** (network-topology necessity for segmented enterprise engagements, not a SaaS bet). See HORIZON.md.
- Third-party integration APIs (Slack/webhooks, Splunk HEC/Elastic/CEF, Jira/ServiceNow) are unfamiliar external surfaces with real auth/format/rate-limit pitfalls — research-first milestone.
- 2:1 cadence holds: v5.2 deliverable → **v5.3 adoption/ops** → v5.4 stabilization + SaaS-validation. Numbering continues at Phase 101. Source of truth for forward outlook: `.planning/HORIZON.md`.

## Previous Milestone: v5.2 Consulting-Grade Reporting — SHIPPED 2026-05-24

**Delivered:** The report is now a consulting-grade deliverable. From one scan and a single shared content model (`build_exec_content` / `ExecContent` + the findings dict), QU.I.R.K. produces a CISO-readable executive narrative with transparent scoring (subscore decomposition + ÷1.5 rollup), a finding list enriched into an advisory document (per-finding quantum-risk "so what" + weakness-specific remediation), code-signing certificate expiry as a first-class finding, a branded client-ready PDF (configurable logo, clean pagination), and an editable DOCX export — the same story across CLI, HTML, PDF, and DOCX. 4 phases (97–100), 12 plans, audit PASSED (13/13 requirements). Local `v5.2.0` tag. Next-up: v5.3 Adoption & Integration (continues at Phase 101).

<details>
<summary>v5.2 original scope (as opened)</summary>

**Goal:** Make the artifact a consultant hands a client genuinely client-ready — a narrative, defensible, professionally-formatted deliverable — rather than a raw finding dump.

**Target features:**
- **Narrative executive report (ANCHOR):** a CISO-readable executive summary that leads with the quantum-readiness *story* (posture, trajectory, top risks, recommended actions) rather than a finding list.
- **Rich per-finding context (999.72):** every finding carries a quantum-risk "so what" explanation + actionable remediation guidance — turning a finding list into an advisory document a non-cryptographer can act on.
- **Score-transparency in executive reports (999.56):** show how the readiness number is built (subscore decomposition, weighting) so the client can trust *and understand* the score.
- **Executive-summary score↔severity consistency (999.82):** fix the latent inconsistency where the exec summary can contradict the detail tables — a correctness/credibility gap for a paid deliverable.
- **Professional PDF formatting / layout / branding (999.2):** presentation quality as the credibility signal for a billable artifact.
- **Code-signing cert expiry as a finding (WR-05 carry-over):** v5.1 computed `not_after`/expired but never surfaced it — a report-content gap that folds naturally into the finding-quality theme.
- **v5.1 tech-debt cleanup (WR-02/03/04/06):** small dedicated phase — env-var all-caps contract, per-call str copies in `CredentialContext`, `_append_query_param` overwrite, sentinel test pre-scrubbed assertions, scheduler `.yml` heuristic, 5xx-cascade-counter connection-exception reset.

**Key context:**
- **The deliverable IS the product.** v4.x–v5.1 built a deep, broad detection engine across six scanner families; no milestone has owned the *output layer*. Reporting compounds every prior detection investment and is the engagement moment-of-truth. Explicit user-anchored North Star.
- **Render consistency across three surfaces** (CLI markdown / HTML / PDF) is a hard constraint — the v4.10.1 lesson: report render paths are physics-coupled, so a change to the score narrative must land identically in all three or it displays a *different* wrong story. The existing single-canonical-scoring-engine + ÷1.5 rollup (v5.0/v4.10.1) is the source of truth to render from.
- **Risk — scope creep into endless visual polish.** Mitigation: anchor on the executive narrative + prioritized remediation roadmap as the must-ship core; treat branding/theming as nice-to-have, time-boxed.
- Numbering continues at Phase 97 (v5.1 ended at Phase 96). Deliverable/output milestone; holds the HORIZON 2:1 capability/ops cadence (v5.0 ops → v5.1 capability → v5.2 deliverable). Selected via the 2026-05-23 product-lens re-prioritization (see `.planning/HORIZON.md`); next-up after v5.2 is v5.3 Adoption & Integration.

</details>

## Previous Milestone: v5.1 Authenticated Scanning + API Surface Depth — SHIPPED 2026-05-23

**Shipped 2026-05-23** — 4 phases (93–96), 16 plans, 21/21 requirements; audit PASSED; local `v5.1.0` tag. Delivered an optional ephemeral credential model (Bearer/OAuth2 + API-key header/query + HTTP Basic, in-memory-only, never persisted) with an 11-surface security-review gate; `analyze-token` JWT classifier; `$ref`-SSRF-hardened OpenAPI spec scanner; LDAP `userCertificate` + TLS-EKU code-signing inventory with cross-source CBOM dedup; and `CONFIRM`-gated/non-TTY-aborted active REST fuzzing (alg-confusion + crypto-posture probes) under an unbypassable budget ceiling. `[api]` extras excluded from `[all]` with a CI guard; `SCORE_WEIGHTS` walked 283.0 → 303.0/41 via the existing `agility_signals` subscore (no 7th pillar). Carried to v5.2: WR-05 (cert-expiry finding) + WR-02/03/04/06 cleanup; 6 environment/TTY-gated human-UAT deferred (non-blocking). Archive: `.planning/v5.1-MILESTONE-AUDIT.md` + `.planning/milestones/v5.1-ROADMAP.md`.

## Previous Milestone: v5.0 — Stabilization + Tech Debt Sweep — SHIPPED 2026-05-22

**Shipped 2026-05-22** — 6 phases (87–92), 16 plans, 21/21 requirements satisfied. Audit PASSED (4/4 integration seams, 0 blockers); local `v5.0.0` tag. Headline: a demoable post-quantum scoring ceiling (digest-pinned OQS-nginx X25519MLKEM768 hybrid profile + raw-openssl PQC probe → genuine quantum-safe CBOM component + agility bonus). Also: Node 20→24 + defusedxml→hardened-lxml; scoring transparency (six /25 subscores + ÷1.5 rollup across CLI/HTML/PDF) and the 5 zero-algo CBOM profiles fixed; 5 new weak-TLS chaos-lab profiles + identity evidence verified; vulture-confirmed dead-code cleanup + permanent conftest DB-isolation. 4 human-UAT deferred (non-blocking, environment-gated). Archive: `.planning/milestones/v5.0-ROADMAP.md` + `v5.0-REQUIREMENTS.md`. **Next:** v5.1 capability work via `/gsd:new-milestone`.

<details><summary>Original v5.0 goal + scoping (historical)</summary>

**Goal:** A deliberate "breathe" milestone after four heavy capability cycles (v4.7 QRAMM, v4.8 Pre-Primetime, v4.9 Audit Depth, v4.10 Launch Readiness). Close chaos-lab coverage gaps, sweep dead code and dependency hygiene, and fix the v4.10/v4.10.1 scoring residuals. No new capability surface. Numbering continues at **Phase 87**; HORIZON guardrail caps scope at **≤6 phases** so v5.1 capability work can start within ~2 weeks.

**Target features (candidate bundles — scoped via requirements pass after research):**
- **Dependency hygiene (deadline-driven, sequenced FIRST as Phase 87):** Node.js 20→24 in `.github/workflows/release-container.yml` action versions — hard GitHub deadline **2026-06-02**; `defusedxml.lxml` → `lxml` migration with manual XXE controls (BACK-67)
- **Scoring residuals:** EVIDENCE-TALLY-01 (3 subscores show 25 despite HIGH/CRITICAL findings — evidence-summarizer root cause), RENDER-CLI-01 + RENDER-PDF-01 (CLI/HTML/PDF report same-bug-class scoring audit, deferred from v4.10.1), Phase 42 OBS-1 CBOM Pass-1 fix (5 profiles emit zero algo components), BACK-63 score transparency
- **Chaos lab targets:** BACK-80 postgres-tls + redis-tls, BACK-81 OQS-nginx PQC-hybrid (scoring-ceiling anchor — the only profile that scores *above* good classical TLS), BACK-82 SMTP/STARTTLS, BACK-83 gRPC TLS, BACK-84 Kafka TLS
- **Identity lab gap:** BACK-78 identity scoring evidence keys (Kerberos KDC, SAML SP, DNSSEC zone)
- **Code cleanup:** BACK-49–57 dead code, deprecation, version drift (CI guards against regression)
- **Bookkeeping:** BACK-62 Nyquist VALIDATION.md updates; BACK-58 JWT `verify=False` docs

**Key context:**
- Theme locked in `.planning/HORIZON.md` 2026-05-22 (Candidate C, pulled forward from v5.2). Done-when criteria: every listed chaos lab profile up + scanner-verified; BACK-49–57 dead code gone with CI guards; lxml/XXE migration shipped; Node 24 bump landed before 2026-06-02; Phase 42 OBS-1 fix lands so the 5 vacuously-passing profiles emit real algo components.
- Approach: research-first (full 4-agent sweep) → full-sweep requirements scoping, trimmed per-category to ≤6 phases.
- BACK-81 OQS-nginx is the strategic centerpiece — grounds the post-quantum side of the score in a concrete demoable artifact.
- **Risk (from HORIZON):** doesn't move adoption forward; could feel like marking time if customer feedback arrives mid-cycle. Mitigation: tight scope, fast turnaround.

</details>

## Previous Milestone: v4.10.1 SHIPPED 2026-05-22

v4.10.1 "Scoring Correctness Hotfix" shipped 2026-05-22 — 1 phase (86), 3 plans, 8/8 requirements. Patched the marquee overall-readiness score that always rendered `100 / EXCELLENT` regardless of posture — a triple-layer scale collision (backend summed six 0–25 subscores then clamped at 100; the frontend gauge declared its input as 0–100 and colored red < 50). Fixed as a single-phase vertical MVP slice because backend and frontend are physics-coupled — fixing only one half would have displayed a *different* wrong number.

**What changed:** backend aggregator at `quirk/intelligence/scoring.py` rewritten `_clamp(sum, 0, 100)` → `int(round(sum / 1.5))` (canonical `25+25+23+3+25+19 = 120` → **80 GOOD**, not **100 EXCELLENT**); `ScoreGauge.tsx` gained a `maxValue?: number` prop with `_gaugeColor()` rewritten onto a normalized 0–1 fraction (red < 50 %, amber 50–79 %, green ≥ 80 %), wired `maxValue={25}` into six executive subscore radials + the Data at Rest tab gauge; version bumped 4.10.0 → 4.10.1 with an operator-language towncrier changelog documenting the accepted 100 → ~80 visual jump. The underlying penalty model (`SCORE_WEIGHTS`, `_apply_weighted_impacts`) is unchanged. Verifier PASSED 5/5; HUMAN-UAT closed PASS (4/4 criteria, post-hard-refresh).

**Backwards compat:** stored SQLite score values untouched; historical scans display the new math when re-rendered (no migration).

**Deferred to v5.0 Phase 01 (Stabilization):** EVIDENCE-TALLY-01 (3 subscores show exactly 25 despite HIGH/CRITICAL findings — separate root cause in the evidence summarizer), RENDER-CLI-01 + RENDER-PDF-01 (same backend-scale vs render-scale audit for the CLI/HTML/PDF report renderers, which likely carry the same bug class). Captured as Future Requirements so the v5.0 plan absorbs them without re-discovery.

Archive: `.planning/milestones/v4.10.1-ROADMAP.md` + `.planning/milestones/v4.10.1-REQUIREMENTS.md`.

**Next milestone (v5.0 — Stabilization):** theme locked 2026-05-22; not yet scoped. Run `/gsd-new-milestone` to open it (Phase 01 should pre-load the three deferred requirements above).

## Previous Milestone: v4.10 SHIPPED 2026-05-21

v4.10 "Launch Readiness" shipped 2026-05-21 — 8 phases (78–85), 31 plans, 52/52 requirements satisfied. Coverage gap closure for S/MIME (LDAP-only `userCertificate`/`userSMIMECertificate`) and Windows AD CS (impacket LDAP enumeration, ESC1–ESC8 observable crypto properties); CMVP attestation feed wired as informational coverage list (never `certified: true`); HTML/PDF injection hardening via `nh3` chokepoint + `| safe` CI gate; SCORE_WEIGHTS invariant flipped green (sum 275.0, count 36).

**Release engineering foundation:** PyPI distribution name `quirk-scanner` registered; Trusted Publishers (GitHub OIDC) + Sigstore attestations wired in `release.yml`; multi-arch GHCR image build in `release-container.yml`; Homebrew tap formula at `0xD1g5/homebrew-quirk`; towncrier+changelog.d/; version single-source-of-truth in `pyproject.toml [project.version]`; SECURITY.md (90-day disclosure SLA), CODE_OF_CONDUCT.md (Contributor Covenant v2.1), docs/release-process.md (semver policy + release runbook + attestation verification + curl|bash non-decision).

**Public-launch polish:** README augmented with badge row + persona triptych (security consultant / IT generalist / compliance officer) + 3-command quickstart; v4.x → v4.10 upgrade guide + `quirk db migrate` CLI (idempotent, additive-only); 4 deterministic sample CBOM fixtures under `examples/cbom/`.

**Deferred to release dry-run (5 human UAT items):** real dashboard hero screenshot, asciinema demo recording, end-to-end quickstart test on clean macOS arm64, first `v4.10.0` tag-push verification (PyPI/GHCR/Sigstore), Homebrew tap repo bootstrap with real sdist sha256.

**Tech debt → v4.10.1:** 6 user-facing docs still reference legacy `pip install quirk[…]`; documentation sweep to use `quirk-scanner`.

Archive: `.planning/milestones/v4.10-ROADMAP.md` + `.planning/milestones/v4.10-REQUIREMENTS.md`.

**Next milestone:** not yet defined — run `/gsd-new-milestone` to open scope.

## Previous Milestone: v4.9 SHIPPED 2026-05-15

v4.9 "Audit Depth" shipped 2026-05-15 — 9 phases (69–77) + inserted Phase 69.1, 38 plans, 210 commits, 339 files changed (+37,658 / −2,359). All 169 findings from the 2026-05-08 audit ledger are dispositioned: 166 `[x] closed`, 2 `[ ] deferred-*` with rationale, 4 `[ ] wont-fix` with rationale. The zero-bare-open invariant is locked forward via `tests/test_audit_ledger_zero_open.py` (Phase 77 D-31), which fails CI on any regression and additionally enforces that deferred/wont-fix rows carry inline rationale.

Subsystem coverage shipped by phase: Phase 69 (scanner/cloud resource correctness — sslyze cleanup, GCP Cloud SQL severity routing, K8s empty-cluster guards, Azure Blob 3-way branch, cache TTL semantics, TokenBucket capacity), Phase 70 (API/QRAMM FK retrofit + DDL allowlist), Phase 71 (protocol scanner WARNINGs — coverage clamp, case-insensitive severity, nmap hardening, identity bounds), Phase 72 (cloud scanner WARNINGs — AWS/Azure/GCP correctness, Cache, profiles mutation guards, Vault PEM hardening), Phase 73 (CBOM/intel/reports — PDF cleanup, weak-crypto helper consolidation via `quirk/util/weak_crypto.py`, SCORE_WEIGHTS normalization), Phase 74 (QRAMM/compliance — practice score validation, TZ-safe evidence bridge, migration advisor precision), Phase 75 (API/CLI/core — doctor actionability, microsecond-safe scan-id window, list_scans grouping, interactive/validate/route input hardening), Phase 76 (React frontend — useScanList error surfacing, localStorage allowlist, PDF unmount cleanup, cert regex, Cytoscape typing, Scorecard math), Phase 77 (29 INFO rows + LEDGER-01 closure + D-31 CI gate).

**Next milestone (v5.0):** not yet defined. v4.9 closes the 2026-05-08 audit ledger entirely; the next milestone scope should be opened via `/gsd-new-milestone`. Backlog candidates include Phase 999.83 (Chaos Lab Service Config Drift — gitea/minio/vault/mysql config drift bugs filed during BACK-89 verification), plus the standing Future Requirements in REQUIREMENTS.md (HTML/PDF injection hardening, migration_planner.py deletion, CMVP attestation feed, S/MIME, Windows AD CS).

## Previous Milestone: v4.8 SHIPPED 2026-05-14

v4.8 shipped 2026-05-14 — 13 phases (57–68), 53 plans, 122 tasks. All 15 audit blockers closed (Wave A) and 6 operating-model features shipped (Wave B). QU.I.R.K. now supports auth-gated dashboard, scheduled scans, trend regression alerts, dashboard-initiated scans, scan history with clone/compare, resumable partial-failure scans, and a stable error-code registry across all operator-facing surfaces.

Phase 64.1 complete (2026-05-10) — audit residual blockers: 5 code fixes with regression tests (algo hints CR-03, staleness date comparison BL-03, years clamp BL-04, sub-second session window CR-05 corrected to ms precision, db init idempotency CR-08); 14 structured D-06 dispositions for remaining BLOCKERs (13 deferred-v4.9, 1 wont-fix); AUDIT-TASKS.md now has zero bare-open BLOCKERs. 32/32 regression tests pass.

Phase 62 complete (2026-05-10) — React hook cancellation pattern: all post-await state setters in useScanData, useScanList, useQRAMMSession wrapped in `if (!cancelled)`; synchronous stale-data clear before each refetch; QRAMMProvider debounce coalescing (1 POST per 300ms window); confirmAnswer flush method; unmount cleanup; print sentinel; reactive system theme. Vitest+MSW test infra added; 2 regression tests (scan-switch stale-data + debounce coalescing); check-cancelled-guards.sh CI script. All 9 audit rows BR-01..BR-06/WR-01/WR-03/WR-14 closed; HOOK-01..04 requirements closed. Code review found 4 warnings (WR-01 setArchiving after navigate, WR-02 narrow CI setter allowlist, WR-03 fetchApi header type gap, WR-04 npm test missing from CI) — advisory.

Phase 60 complete (2026-05-10) — score arithmetic correctness: readiness score clamped to [0,100] (SCORE-01), TLS confidence bonus zeroed on absent TLS data (SCORE-02), QRAMM multiplier guard fires as explicit 400 before DB access (SCORE-03), maturity-band sweep confirmed (SCORE-04). Code-review fix CR-01 also applied: QRAMM overall score clamped to CSNP [0,4.0] scale. 45/45 tests pass. Audit ledger rows BL-01, BL-02, CR-04, CR-06, WR-05 closed.

Phase 59 complete (2026-05-10) — credential leakage sweep: `safe_str()` scrubbing helper built (LEAK-01), applied to all 9 leaky callsites across scanner/discovery/CBOM modules (LEAK-02), AST CI gate enforcing no-raw-exc in `scan_error` writes (LEAK-03). 32/32 tests pass.

v4.8 "Pre-Primetime Hardening + Operating Model" initialized 2026-05-09 following the comprehensive pre-v4.8 codebase audit (2026-05-08). Audit findings: 41 blockers, 91 warnings, 22 info across 116 files in 6 subsystems; top-15 blockers triaged as gating for primetime cutover. Wave A (6 hardening phases) blocks Wave B (6 operating-model phases) — shipping operating-model features on top of unhardened security/correctness foundations would invert the primetime quality goal.

v4.7 "Governance & Compliance Platform" shipped 2026-05-08: 6 phases + 1 close-out (51, 52, 53, 54, 55, 56, 56.1), 27 plans. QRAMM data model, evidence bridge, assessment UI, scorecard, compliance mapping view, PDF export with governance section, and CI staleness gate all delivered. SOC2 + ISO 27001 mappings shipped alongside FIPS 140-3 annotations and `quirk doctor` health-check CLI.

v4.6 "Enterprise Readiness" shipped 2026-05-05 (tag `v4.6.0`). 6 phases, 24 plans, 3-day execution. QUIRK can now be installed with `pip install quirk` without crashes, surfaces 5 new TLS certificate-defect finding types, accepts multi-target and CIDR input with optional nmap discovery, enriches every finding with FIPS-compliant PQC remediation guidance, maps findings to PCI-DSS/HIPAA/FIPS 140-3 controls, and ships two enterprise reference documents. Compliance mapping introduces staleness infrastructure (quarterly review cadence enforced by CI gate).

## Context

- **Current version**: v4.8.0 (shipped 2026-05-14); v4.7.0 shipped 2026-05-08
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
| Wave A hard-gates Wave B (v4.8 D-01) | Shipping operating-model features on top of unhardened security/correctness foundations would invert the primetime quality goal | ✓ Good — all 15 audit blockers closed before any Wave B phase started; no audit finding escaped to Wave B |
| Wave A internally parallel (v4.8 D-02) | Phases 57–62 touch disjoint code paths; independent agents can execute concurrently | ✓ Good — 6 phases completed on 2026-05-09/10 with subagent parallelism |
| `safe_str(exc)` shared helper over per-site scrubbing (v4.8 Phase 59) | 9 leaky callsites; fixing individually would leave gaps; AST gate prevents regression | ✓ Good — LEAK-01/02/03 closed; 32 tests pass; CI gate catches future bypasses |
| `if (!cancelled)` guard pattern from useTrendsData.ts as canonical (v4.8 Phase 62) | Selecting one hook as canonical prevents per-hook interpretation drift; CI script enforces it | ✓ Good — 4 hooks migrated; 2 Vitest tests; check-cancelled-guards.sh exits 1 on violation |
| `quirk errors` registry with stable error codes (v4.8 Phase 68) | Operator-facing errors need stable codes for runbook references; raw exceptions are unusable in production | ✓ Good — 50 codes, cause+remediation for each; `format_error()` applied at all exit points |
| Markdown injection in HTML/PDF deferred to v4.9+ (v4.8 D-06) | REPORT-SAN-01 covers markdown tables only; HTML/PDF injection is a separate attack surface shape | — Pending — deferred intentionally; AUDIT-TASKS.md tracks the open WARNING rows |
| PyPI distribution name `qu-i-r-k` (v4.10 D-01 / Phase 84-01) | `pip index versions quirk` on 2026-05-16 returned 0.1.1/0.1.2/0.1.3 — the bare `quirk` name is already claimed by an unrelated package on PyPI; fallback `qu-i-r-k` per pre-registered D-84-R1 plan | ⚠ Superseded 2026-05-22 by v4.10-D-06 — PyPI Pending Publisher form rejected `qu-i-r-k` with PEP 541 "too similar to existing project" (the `quirk` squatter); renamed to `quirk-scanner` at release time. See D-06 below. |
| pyproject.toml `[project.version]` is canonical version SoT (v4.10 D-02 / D-84-R1 / Phase 84-01) | Modern Python packaging best practice (PEP 621 + importlib.metadata); REVERSES legacy RELENG-08 wording that named `__init__.py` as canonical | ✓ Good — `quirk/__init__.py::__version__` resolves dynamically via `importlib.metadata.version(_DIST_NAME)` (currently `quirk-scanner` per D-06) with a `tomllib` fallback for unpackaged dev runs; `quirk/config.py:279` `IntelligenceCfg.intelligence_version` derives from `quirk.__version__`; `tests/test_version.py` enforces parity in the new direction |
| PyPI distribution name `quirk-scanner` (v4.10 D-06 / supersedes D-01 / UAT-85-11 release-time) | UAT-85-11 Gate 5.5 surfaced PyPI's PEP 541 typosquat rejection of `qu-i-r-k` — too similar to the existing `quirk` squatter project. `quirk-scanner` is a compound name with a semantic suffix; PEP 541 distance is high; Pending Publisher form accepted dry-run on 2026-05-22. Identifiers UNCHANGED: CLI command, Python import name, GHCR image, Homebrew tap repo — D-06 only touches the PyPI namespace identifier. | ✓ Good — Pending Publisher dry-run passed; sweep applied to 15 active production + planning files; archived milestone snapshots under `.planning/milestones/v4.10-*` preserved as historical record (they reflect milestone-close state of `qu-i-r-k`). Lesson for BACK-90 / Phase 86: future PyPI name verification must include Pending Publisher dry-run, not just `pip index versions`. |
| Overall readiness aggregation `int(round(sum / 1.5))` replaces `_clamp(sum, 0, 100)` (v4.10.1 / 86-01-D-01) | Six 0–25 subscores sum to 0–150; clamping at 100 hid all real posture above the clamp, always rendering `100 / EXCELLENT`. `sum / 1.5` maps 0–150 → 0–100 linearly. Canonical 120 → 80. Penalty model (`SCORE_WEIGHTS`) unchanged — this is an aggregation fix, not a re-weighting. | ✓ Good — boundary tests assert 100 only at all-25 ceiling, 0 only at all-zero; verifier PASSED 5/5; HUMAN-UAT PASS |
| Single-phase atomic ship — backend + frontend + release coupled (v4.10.1-D-01) | The bug spans backend aggregation and frontend gauge math; fixing only one half displays a *different* wrong number. Splitting would yield contradictory half-fixes. | ✓ Good — one phase, 3 plans, shipped as one unit; gauge value + color matched backend post-fix |
| No stored-score migration (v4.10.1-D-02) | SQLite score values are untouched; old scans display the new math when re-rendered. The 100 → ~80 visual jump is documented in CHANGELOG.md as an accepted trade-off. | ✓ Good — zero migration risk; release notes set operator expectations |
| Render-side + evidence-tally fixes deferred to v5.0 Phase 01 (v4.10.1-D-03 / D-04) | Same bug class likely lives in CLI/HTML/PDF renderers (RENDER-CLI-01/PDF-01); the evidence-tally gap (3 subscores at 25 despite findings) is a separate root cause in the summarizer (EVIDENCE-TALLY-01). A full-stack scoring sweep is the right shape; mixing into a hotfix risks new bugs. | — Pending — captured as Future Requirements in archived v4.10.1-REQUIREMENTS.md; v5.0 Phase 01 pre-loads them |

---
*Last updated: 2026-05-25 — v5.4 Distributed On-Prem Scanner Architecture IN PROGRESS — Phase 107 Distributed Data Model COMPLETE (2/2 plans, verification passed 9/9, MODEL-01..04): the SQLite schema now carries nullable `sensor_id`(indexed)/`segment` on `CryptoEndpoint` plus `sensors`/`sensor_tokens`/`sensor_pushes` tables (CASCADE FKs, unique `payload_id`) via the existing `_ADDITIVE_MIGRATIONS`/`_ensure_columns` pattern, with a proven backward-compatible + score-stable migration. Next: Phase 108 (Sensor Push CLI + Windows CI). Anchor: agent/console split — sensors scan locally per network segment and push outbound to a single-tenant console that merges into one CBOM + one score. Architecture doc first (Phase 1, folds 999.58); reuses v5.3 console-side auth/push/delivery-audit primitives. Windows sensor support in scope (size at arch-doc phase; may split to v5.5). SaaS multi-tenancy stays PARKED (topology necessity, not a business-model bet). Stabilization tail: 999.59, `_NoRedirectHandler` extract, dep hygiene. 19 v5.3 live-delivery human-UAT items parked (no test env) — NOT entry conditions. — Earlier: v5.3 Adoption & Integration Surface SHIPPED (Phases 101–105, 20 plans, audit PASSED 21/21, local `v5.3.0` tag). QU.I.R.K. now delivers drift notifications (Slack/email/webhook), SIEM CEF export, and Jira+ServiceNow ticketing on one shared SSRF-safe/secret-scrubbing integration layer, plus single-tenant dashboard token auth. 19 live-delivery human-UAT items deferred; 1 LOW tech-debt (extract duplicated _NoRedirectHandler). Next: v5.4 (stabilization + SaaS-validation) per HORIZON.md, continues at Phase 106. — Earlier: v5.3 OPENED 2026-05-24 (continued at Phase 101). Theme per HORIZON.md: make QU.I.R.K. load-bearing in others' workflows — notification fan-out (anchor: drift events are emitted but undelivered) + one SIEM export + one ticketing integration + single-tenant dashboard auth; folds in the v5.2 CLI-score-source tax. Research-first (unfamiliar third-party APIs). SaaS/multi-tenant stays deferred to v5.4 pending adoption signal. — v5.2 Consulting-Grade Reporting SHIPPED (Phases 97–100, 12 plans, local `v5.2.0` tag). The report deliverable now leads with a narrative exec summary, transparent scoring, advisory per-finding context, code-signing expiry findings, a branded PDF, and an editable DOCX — all from one shared content model across CLI/HTML/PDF/DOCX. Audit PASSED 13/13. One non-blocking tech-debt item carried to backlog (CLI score should source `exec_content` rather than re-derive). Next-up: v5.3 Adoption & Integration (continues at Phase 101). Previous: v5.1 Authenticated Scanning SHIPPED 2026-05-23 (Phases 93–96, local `v5.1.0` tag).*

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
