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

**v5.4–v5.6 Distributed Scanner + Public Launch — SHIPPED 2026-05-26 → 2026-06-12**
- ✓ Sensor/console distributed architecture — per-segment scan → authenticated push → Option-A merge into one CBOM + one score — v5.4
- ✓ Per-sensor Bearer-token auth + revocation; automatic merge on full sensor check-in — v5.5
- ✓ Production Windows frozen sensor — `--onedir` PyInstaller build, smoke + E2E auth on `windows-latest` CI, zip + PowerShell Scheduled-Task installer, GitHub Release asset — v5.6
- ✓ Public repository — gitleaks-clean 3-pass history rewrite, branch protection with required `Windows Sensor Smoke` check, SSRF guard hardening, Actions SHA-pinning — v5.6
- ✓ Port-scope discovery control — common/top1000/all/custom scopes GUI→nmap + zero-result completion signal — v5.6
- ✓ 11-item audit tech-debt sweep (confidence bonus gate, production compliance-staleness gate, score clamp, redaction/rendering fixes) — v5.6

**v5.7 Hardening + Hardware Compatibility & Lifecycle Remediation — SHIPPED 2026-06-14**
- ✓ SSRF cluster closed — REST fuzzer via `PinnedIPAdapter` + raw-socket validation; GCP metadata aliases blocked; path-shaped image refs rejected before syft; console self-SSRF blocked before `allow_internal` short-circuit; DNS-rebinding mitigated via `resolved_ip` pinning — v5.7 Phase 123
- ✓ Scoring correctness — severity KeyError → LOW fallback; QRAMM partial-answer inflation resolved (0.0 injection before `min()`); EdDSA agility credit in ECDSA bucket; AES-CCM_8 classified as distinct truncated-tag AEAD; cross-tenant evidence contamination resolved via `session_created_at` anchor — v5.7 Phase 124
- ✓ Posture defaults — GCP/AWS IAM 403/AccessDenied surfaced as scan_error findings; same-second merge tiebreak via `MAX(id)`; notify fan-out isolated from auxiliary commit failures; POSTURE-01 (Phase 113) ledgered — v5.7 Phase 125
- ✓ Audit ledger drained — all 7 criticals remain closed; 29 warning rows dispositioned (fixes + wont-fix + deferred-v5.8 with rationale); FE-01/03/04 fixed; Dashboard Quality CI green — v5.7 Phase 126
- ✓ Hardware fingerprinting — agentless SSH-banner + HTTP-mgmt fingerprinting via 8-vendor PQC matrix (`hardware_meta.py`, 90-day CI staleness gate); `HardwareDevice` ORM + `hwcompat` chaos lab profile — v5.7 Phase 127
- ✓ CNSA 2.0 tier assignment — `assign_tier()` (Tier 1/2/3/N/A + confidence cap); advisory in HTML collapsible, executive narrative, DOCX table, `/hardware` dashboard tab; advisory-only (zero SCORE_WEIGHTS references) — v5.7 Phase 128
- ✓ Crypto-bridge detection + CBOM Pass 4 — /24 subnet heuristic annotates `partial_only`; CBOM Pass 4 emits `ComponentType.FIRMWARE` with `quirk:hw-*` properties; `HARDWARE` in Pass 2/3 skip-lists; CycloneDX 1.6 validates — v5.7 Phase 129

**v5.8 Audit Closeout + SNMP Fingerprinting — SHIPPED 2026-06-18**
- ✓ 15-row Wave A audit drain — codesign column rename, REST fuzzer per-scan dedup, Kerberos RFC 4120 TCP→UDP comment, DOCX exception logging with stack trace, SOURCE algo-hint granularity (RSA/AES variants preserved), rate-limit idle-bucket eviction, job target 422 validation, sensor-push UUID re-validation, SSRF TOCTOU accepted-risk doc, sensor CLI UUID guard, SIEM SSRF guard + CEF space escaping, console enroll single-session (no race), auth token sessionStorage + CSP header, HTML cover-page layout fix — v5.8 Phases 130–132
- ✓ SNMP fingerprinting — opt-in `[hw]` extras (pysnmp>=7.1.0,<8 + sysdescrparser); 3-OID probe per target (sysDescr/sysName/sysObjectID); dual-path vendor parsing; 4 HardwareDevice ORM columns; Cisco IOS Net-SNMP chaos lab container (port 20223/udp); CBOM quirk:hw-snmp-oid property; snmp_meta.py 90-day staleness gate — v5.8 Phase 133
- ✓ CBOM DEVICE/FIRMWARE hierarchy — DEVICE parent component + FIRMWARE children via Component.components; HardwareComponent Pydantic schema on /api/scan/latest; dashboard CBOM tab HardwareInventory with distinct DEVICE/FIRMWARE Badge rows — v5.8 Phase 134
- ✓ B-01 distributed path fix — merge/scan.py hw_devices_for_cbom dict now projects all 4 SNMP fields; quirk:hw-snmp-oid emitted on distributed/merge path — v5.8 post-audit fix (6eb512e)

**v5.9 Documentation Audit & Living Docs System — SHIPPED 2026-07-30**
- ✓ Core docs refresh — README v5.8.0 title/What's New/feature list, CHANGELOG [5.7.0]/[5.8.0] entries, getting-started.md Optional Hardware Scanning `[hw]` section, architecture.md §12 Hardware Scanning (signal chain, SNMP, CBOM hierarchy) — CORE-01/02/03, v5.9 Phase 135
- ✓ Operators guide hardware section — `docs/operators-guide.md` §9 (SNMP enable, CNSA 2.0 tiers, crypto-bridge) cross-checked verbatim against `hardware_tier.py`/`scan.py` source constants — OPS-01/02/03, v5.9 Phase 136
- ✓ Consultant + admin documentation — `docs/report-interpretation.md` §10 Hardware Inventory; new `docs/admin-guide.md` (console deploy, sensor enrollment, auth lifecycle, SNMP setup) — OPS-04/ADMIN-01/02/03, v5.9 Phase 137
- ✓ Chaos-lab hwcompat profile documented (§3.22) + living-docs governance — `CLAUDE.md` gains a mandatory Per-Phase Documentation Checklist and a Milestone-Boundary Doc Review Template — LAB-01/02/LIVE-01/02/03, v5.9 Phase 138
- ✓ Gap-closure self-test — audit found and closed 2 real defects via inserted phases: CORE-04 (architecture.md §12 CNSA 2.0 tier severity had shipped inverted vs. `hardware_tier.py` and operators-guide.md; Phase 138.1) and LIVE-03 (2 Obsidian vault guides stale vs. their `docs/` sources, re-synced with content-diff verification not just mtime; Phase 138.2) — proof the new CLAUDE.md governance machinery works, since 138.1/138.2 themselves followed it (UAT-SERIES.md updates, vault sync)

**v5.10 Hardware Lifecycle Depth — SHIPPED 2026-08-03**
- ✓ SNMPv3 auth (auth+priv) support, alongside existing v5.8 SNMPv2c — Phase 139
- ✓ `upstream_mitigated` SNMP-confirmed bridge detection (promotes from conservative `partial_only`) — Phase 140, evidence scoped to the specific gateway↔backend pair (CR-01 hardened post-review)
- ✓ OT/ICS fingerprinting (Modbus/BACnet) — Phase 141, required 2 gap-closure rounds (inner gate + outer SSH-gating bug) before genuinely end-to-end
- ✓ Firmware CVE correlation against fingerprinted hardware/firmware versions — Phase 142, advisory-only
- ✓ Dashboard & UX tail: persistent scan-date badge, scoped trusted-targets allowlist, Authenticode code-signing for the Windows sensor — Phase 143 (signing CI mechanism only; awaiting production cert)

**v5.11 Discovery at Scale + Backlog Drain — SHIPPED 2026-08-11**
- ✓ Large (>1024-host) range scans reachable end-to-end from the dashboard job-creation endpoint — both hard-reject gates relaxed in the same phase as the chunking that replaces them (DISC-01) — Phase 144
- ✓ Per-batch failure isolation: one unresponsive batch no longer fails the whole discovery job (DISC-02) — Phase 144
- ✓ TCP-SYN/ACK liveness pre-pass (not ICMP) skipping dead hosts while still counting them, with explicit SYN→connect privilege-fallback detection (DISC-03) — Phase 145
- ✓ Incremental discovery progress (batch N of M / hosts checked) on the dashboard via the existing poll loop (DISC-04) — Phase 146
- ✓ Discovery timeout and `-T` timing scaled to each batch's own size, replacing the hardcoded 300s (DISC-05) — Phase 146
- ✓ CLI `--discovery nmap` and dashboard converge on one shared chunked-discovery call site, locked by an AST regression test (DISC-06) — Phase 146
- ✓ Undetermined (unreachable/filtered) host counts disclosed across CLI markdown, HTML, DOCX and terminal summary (DISC-07) — Phase 146
- ✓ `--resume-scan-id` continuation fingerprints OT-only hosts even when the SSH stage was already checkpointed complete (DRAIN-01) — Phase 147
- ✓ BACnet vendor-ID + model-family resolution making the Johnson Controls / Facility Explorer CVE entry reachable (DRAIN-02) — Phase 147
- ✓ 2026-05-27 audit ledger reconciled to zero undecided/stale rows with verified commit citations; port-aware default CORS allowlist (DRAIN-03) — Phase 147
- ✓ STATE.md deferred human-UAT ledger re-triaged with dated dispositions (DRAIN-04) — Phase 147

**SaaS Platform (Future Milestone)**
- [ ] Multi-tenant architecture design
- [ ] Scan job queue (Celery + Redis or similar)
- [ ] User auth and org management
- [ ] Cloud deployment (Docker Compose → Kubernetes)
- [ ] Hosted reporting and CBOM storage

### Active

Defined by v5.12 Release & Verification Integrity — see Current Milestone section below.

Carried into next-milestone scoping (from the v5.11 audit's remaining tech debt):
- [ ] **Windows release asset for v5.12** — v5.11.0 published to PyPI but shipped no Windows
      asset: the signing self-test failed by construction (fixed in `1a6effc`, unexercised until
      the next tag). The v5.12 release is the first run that will prove the repaired path.
      Consider also normalizing tag hygiene — `v5.9` never matched `release.yml`'s `v*.*.*` glob
      and `v5.10.0` was never pushed, so three milestones went out with no Windows build.
- [ ] **DISC-09** segmented-network chaos lab profile — deferred from v5.11; also the environment
      needed to settle the Phase 144 nmap timing-engine artifact. Schedule the two together.
- [ ] **DISC-08** sub-batch (mid-discovery) checkpoint/resume granularity — deferred as an
      accepted boundary; revisit only if batch cost grows.
- [ ] Stabilization pass on the ~102 pre-existing full-suite test failures (version-locked
      assertions, Python 3.14 dev-env drift) — aging since Phase 97, unrelated to v5.11.

### Out of Scope (v1)

| Feature | Reason |
|---------|--------|
| S/MIME message-content scanning | Email *transport* TLS shipped in v4.4; S/MIME *content* (signed/encrypted email at rest) remains out of scope — agentless model cannot inspect mailbox content |
| Windows AD CS live connector | Complex Kerberos/NTLM auth; stub remains, deferred to v2 |
| Network traffic capture (Zeek/Wireshark) | Requires passive tap; out of scope for agentless model |
| OpenVAS / Nessus integration | Full vuln scanner; different scope, heavy dependency |
| Mobile app | Web-first; SaaS phase determines mobile need |
| Real-time continuous monitoring | SaaS milestone, not v1 |

## Current Milestone: v5.13 Continuous Hardware Lifecycle Monitoring

**Goal:** Extend v5.10's hardware-fingerprinting foundation (`HardwareDevice` table,
`hw_cve.py`, CNSA 2.0 tier assignment) from a point-in-time scan into ongoing lifecycle
tracking — detecting drift in firmware/EOL/vendor-PQC-status over time and alerting when a
device crosses a CNSA 2.0 tier boundary.

**Target features:** TBD — this milestone opens with a research pass before requirements are
scoped, per HORIZON.md's flagged open question.

**Why this shape (PM review 2026-08-14):** the last substantial unbuilt backlog theme, deferred
since v5.10 as "needs its own research pass" — restores the 2:1 capability/ops cadence after
v5.12's ops cycle. The open question (new scanner surface vs. scheduling/diffing layer over
existing data) changes this milestone's size by roughly 3x, so it must be answered before
requirements can be scoped, not guessed at.

**Explicitly out of scope (carried from HORIZON.md):** SaaS multi-tenancy (still parked, no
business-model signal).

**Progress:** Phase 154 (Identity & Data-Model Foundation) complete 2026-08-14 — HWLC-01/02/03
validated. `HardwareDevice` now carries a stable SSH host-key-fingerprint secondary match key
(with explicit low-confidence fallback to host:port), a truthful `probe_status` distinguishing
a failed re-probe from an honestly-unrecognized vendor, a genuine per-device latest-successful-row
projection at all four read sites (dashboard, CBOM merge, CLI/PDF/DOCX reports) so a failing
probe never erases a device's last-known-good state, and a configurable opportunistic retention
purge (`hardware_history_retention_days`, default 180) bounding per-device history growth. This
is the blocking foundation Phases 155 (drift detection) and 156 (reporting) build on.

**Phase 155 (Drift Detection + EOL Tracking) complete 2026-08-14** — HWLC-04/05/06/07/08/09
validated. Two-scan reconciliation now surfaces CNSA 2.0 tier crossings, bridge/upstream-mitigation
status shifts, CVE-set deltas, and EOL/EOS state changes as four distinct, N-of-M-confirmed,
deduplicated event types persisted to `hardware_drift_events`; a new curated EOL/EOS catalog
(`hardware_eol.py`, 4th staleness-gated instance) finally populates the previously-dormant
`HardwareDevice.eol_date` column. Advisory-only — zero scoring-visible effect, machine-enforced.
Next: Phase 156.

---

## Previous Milestone: v5.12 Release & Verification Integrity — SHIPPED 2026-08-14

**Goal:** Make QU.I.R.K.'s own signals trustworthy again — cutting a tag produces a complete,
verified artifact set without supervision; a phase cannot be marked complete while its
verification artifacts are missing; and a green test suite means something.

**Shipped:** 6 phases (148–153), 36 plans, 14/14 requirements. Version 5.12.0 — real tag cut,
pushed, PyPI published, Windows operator zip attached to the GitHub Release. Release pipeline
repair + tag-hygiene guard proven live (148); ~102 pre-existing test failures each explicitly
dispositioned, then a green `pytest -q` baseline held by a CI gate (149/150); a phase-completion
artifact gate (`scripts/verify_phase_gates.py` + `.githooks/pre-commit`, now installed and live
in this checkout) that blocks a phase close missing VERIFICATION.md/stale VALIDATION.md/missing
UAT-SERIES.md entry, plus a destructive-archive guard (151); the Phase 144 nmap timing-engine
artifact empirically settled — does not reproduce on a realistic segmented-network chaos lab
profile — and the interactive nmap-discovery default flipped to Yes (152); the real `v5.12.0`
tag cut and independently verified against live GitHub Actions and PyPI, including one real,
human-approved recovery from a silently-dropped tag-push event (153).

Milestone audit (`.planning/milestones/v5.12-MILESTONE-AUDIT.md`) scored `passed`. One real
integration gap was found and fixed during the audit itself: Phase 151's own VALIDATION.md docs
(and Phase 153's) had been left in their pre-execution draft state even though the underlying
work was genuinely done — because the pre-commit hook the phase built was never actually
installed in this working copy. Fixed, and `core.hooksPath` is now live going forward.

Full rationale: `.planning/HORIZON.md`. Archive: `.planning/milestones/v5.12-ROADMAP.md`.

---

## Previous Milestone: v5.11 Discovery at Scale + Backlog Drain — SHIPPED 2026-08-11

**Goal:** Make QU.I.R.K. able to scan large, sparse IP ranges from the dashboard's
nmap-discovery path — closing backlog item 999.90 — while draining the small debt
accumulated since v5.8/v5.10 (audit-ledger reconciliation, two small hardware bugs,
deferred-UAT re-triage) so it doesn't keep aging across milestones.

**Target features:**
- Chunked nmap discovery with partial-result tolerance (batch large ranges, don't fail
  the whole job on one slow batch)
- Cheap liveness pre-pass to filter sparse ranges before the expensive port sweep
- Visible per-batch discovery progress instead of binary pass/fail
- Timeout/parallelism scaled to actual batch size, not one hardcoded guess
- OT/ICS `--resume-scan-id` checkpoint gap fix
- CVE table BACnet key coverage decision
- 2026-05-27 audit ledger reconciliation (flip already-fixed rows, resolve WR-02/CD-03)
- Deferred human-UAT re-triage from the STATE.md Deferred Items table

**Key context:**
- Anchor is backlog item 999.90 (`.planning/backlog/999.90-nmap-discovery-chunking-large-ranges/IDEA.md`)
  — a real user-reported failure with a fail-fast stopgap already shipped (commit `9bfdd6e`),
  not yet a real capability fix.
  This closes the gap directly rather than continuing to reject large ranges.
- Backlog item 999.91 (Modbus Step4 gate) was independently confirmed already fixed by
  Phase 141's gap-closure rounds (141-08/141-09/141-11) — folder should be closed/removed,
  not carried forward.
  SaaS multi-tenancy stays PARKED (unchanged).
- Numbering continues from Phase 143. Source of truth for forward outlook: `.planning/HORIZON.md`
  (needs a revision pass at this milestone's close — it was last updated pre-v5.10-ship).

## Previous Milestone: v5.10 Hardware Lifecycle Depth — SHIPPED 2026-08-03

**Shipped (Phases 139–143, 36 plans, 23/23 requirements):** SNMPv3 auth+priv fingerprinting with a
v3→v2c→none fallback ladder and zero credential leakage (139); SNMP-confirmed bridge mitigation —
`partial_only` → `upstream_mitigated` only on real gateway-specific ARP evidence, never scored
(140); OT/ICS fingerprinting for Modbus/TCP + BACnet/IP, requiring two gap-closure rounds after
initial ship — an inner unsatisfiable-gate bug (141-08) and a deeper outer SSH-gating bug
(141-11) that silently skipped OT/ICS-only devices with zero SSH endpoints — both fixed and
live-validated together against the real chaos-lab containers (141); firmware CVE correlation,
advisory-only and staleness-gated (142); a dashboard/security tail — scan-date badge,
server-enforced trusted-targets allowlist, Windows Authenticode signing CI mechanism (secret-gated,
awaiting a production cert) — with dedicated `/gsd-secure-phase` reviews for both security-relevant
changes (143). Audit: tech_debt disposition, 0 blockers, integration clean (20/20). Full record:
`.planning/milestones/v5.10-ROADMAP.md`.

**Key decisions:** Continues the Hardware Compatibility & Lifecycle Remediation arc anchored in
v5.7/v5.8. Continuous hardware lifecycle monitoring stays deferred to v5.11+. Numbering continued
from Phase 138 (+ gap-closure 138.1/138.2) at **Phase 139**. The Phase 141 gap-closure history is a
notable case study: a live human-verify checkpoint caught a real defect (the outer SSH-gating bug)
that three rounds of plan-checker review focused on the narrower inner-gate fix had not surfaced.

## Previous Milestone: v5.8 Audit Closeout + SNMP Fingerprinting — SHIPPED 2026-06-18

**Shipped (Phases 130–134, 21 plans, tag `v5.8.0`):** Wave A drained 15 deferred audit rows across scanner quality (codesign rename, fuzzer dedup, Kerberos RFC comment, DOCX exception logging, SOURCE algo-hints), API/dashboard hardening (rate-limit eviction, target validation, sensor UUID guards, console enroll race, SIEM SSRF guard, CEF escaping), and frontend polish (sessionStorage + CSP, HTML cover-page fix). Wave B shipped SNMP fingerprinting as the third hardware detection signal (pysnmp 7, `[hw]` extras, sysdescrparser dual-path, Cisco IOS chaos lab container, CBOM quirk:hw-snmp-oid property, snmp_meta staleness gate) and the CBOM DEVICE/FIRMWARE hierarchy (DEVICE parent + FIRMWARE children, HardwareComponent schema, dashboard HardwareInventory). B-01 distributed SNMP field projection gap fixed before tag (6eb512e). Full record: `.planning/milestones/v5.8-ROADMAP.md`.

## Previous Milestone: v5.9 Documentation Audit & Living Docs System — SHIPPED 2026-07-30

**Shipped (Phases 135–138 + gap-closure phases 138.1, 138.2; 10 plans; 16/16 requirements):** Every top-level doc entry point (README, getting-started, architecture) now accurately reflects v5.4–v5.8's distributed architecture, SNMP/hardware fingerprinting, CNSA 2.0 tiers, and CBOM DEVICE/FIRMWARE hierarchy. `docs/operators-guide.md` gained a full §9 Hardware Scanning section cross-checked verbatim against source constants. A brand-new `docs/admin-guide.md` covers console deployment, sensor enrollment, auth lifecycle, and SNMP setup — closing the admin-facing gap the distributed architecture (v5.4+) had left undocumented. `docs/chaos-lab.md` documents the hwcompat SNMP profile, and `CLAUDE.md` now carries a mandatory Per-Phase Documentation Checklist + Milestone-Boundary Doc Review Template — permanent governance machinery, not a one-time doc sweep.

**Self-proving governance:** the first milestone audit found 2 real defects the phases had shipped — CORE-04 (architecture.md §12 had the CNSA 2.0 tier severity *inverted* relative to the shipping code and operators-guide.md) and LIVE-03 (2 Obsidian vault guides gone stale). Both were closed by inserted gap-closure phases (138.1, 138.2), and a re-audit independently re-verified both fixes end-to-end against source code, not just against the phases' own claims. 138.1 and 138.2 also demonstrated the new CLAUDE.md checklist actually gets followed by later phases (UAT-SERIES.md updates, vault re-sync), not just documented in principle.

**Audit:** tech_debt disposition — 16/16 requirements satisfied, integration clean, 0 blockers. Remaining debt is entirely deferred human-UAT prose/visual reviews (README rendering, admin-guide/report-interpretation readability, live sensor-enroll walkthrough) plus one missing SUMMARY.md artifact — no content gaps. Full record: `.planning/v5.9-MILESTONE-AUDIT.md`.

**Key decisions:** Numbering continued at Phase 136 (135 pre-existed). Docs-only milestone — zero code changes except the two gap-closure doc fixes. `.planning/REQUIREMENTS.md` ledger edits for gap-closure phases were applied on-disk only (not committed) per the Phase 120 `.planning/`-exclusion policy for the public repo.

## Previous Milestone: v5.6 Distributed Completion + Public Launch — SHIPPED 2026-06-12

**Shipped (Phases 117–122, version 5.6.0):** Production Windows `--onedir` frozen sensor binary + PowerShell Scheduled Task installer + GitHub Release asset (117–118); public-repo cutover — forensic git-history rewrite (12 path categories stripped, gitleaks 0/2652 commits), Actions SHA-pinning, SECURITY_CHECKLIST canonicalization, branch protection + `Windows Sensor Smoke` required CI check (119–120); port-scope discovery control — four-option GUI selector, nmap layer decoupled from 6-port hardcode, zero-result signal (121); 11-item tech-debt sweep from 2026-05-27 audit + version bump to 5.6.0 (122). Full record: `.planning/milestones/v5.6-ROADMAP.md`.

**Goal:** Ship the production Windows sensor binary that v5.5's spike sized, and take the repo public with enforced CI — finishing the cross-platform + launch story the distributed architecture (v5.4/v5.5) began.

**Key context:**
- Carry-forward drain (HORIZON priority) before the net-new Hardware Compatibility & Lifecycle Remediation capability (HWCOMPAT-01..06), which anchors v5.7.
- Numbering continues at **Phase 117**. Authenticode code-signing and HWCOMPAT are OUT of scope; SaaS stays parked. Research skipped — the one unknown (Windows freezing) was the v5.5 spike. Forward outlook: `.planning/HORIZON.md`.

## Previous Milestone: v5.5 Distributed Hardening + Stabilization — SHIPPED 2026-05-27

**Shipped (Phases 113–116, 11 plans, local tag `v5.5.0`):** per-sensor opaque Bearer-token auth + revocation (113), automatic merge on full sensor check-in via a failure-isolated BackgroundTask (114), a live-UAT stabilization sweep — idempotent enroll, importlib.resources cmvp packaging, scheduler arg fix with target preservation, phantom-row elimination + a weak-TLS segment-b lab target (115), and a GO-conditional Windows packaging PyInstaller spike (116). Audit PASSED-with-tech-debt: 13/13 requirements satisfied, 0 blockers, integration 12/12 + 3/3 E2E flows clean. Security audit added for 113 (threats_open 0). Code review caught + fixed real defects in 114/115/116 (inverted revoked-sensor filter, cron-loop crash, overbroad hardgate test). 2 human-UAT deferred (doc review, live windows-latest CI build). Full record: `.planning/MILESTONES.md` + `.planning/milestones/v5.5-ROADMAP.md`.

**Goal:** Harden the v5.4 distributed scanner into production shape — per-sensor authentication, automatic merge, and a clean re-runnable lab — while sweeping the defects the live distributed E2E surfaced. Honors the 2:1 stabilization breather that v5.4 deliberately deferred.

**Target features:**
- **Per-sensor token auth + revocation (TD-1):** replace the shared-token model with per-sensor tokens that can be individually revoked. The one net-new security surface in this milestone; reuses v5.3/v5.4 token-auth + delivery-audit primitives.
- **Automatic merge-trigger (106 D-06):** the console merges sensor results into one CBOM + one score without a manual `quirk sensor merge` — poll-on-full-check-in or equivalent trigger.
- **Live-UAT bug sweep (999.85–89):**
  - `quirk console enroll` idempotent so `lab.sh distributed e2e` is re-runnable without `down -v` (999.86)
  - `cmvp_cache.json` shipped in the installed package — no more "CMVP cache unavailable" on merge (999.87)
  - `quirk scheduler` stops passing unsupported `--output`/`--target` to `run_scan` (same class as the fixed sensor bug — scheduled scans may exit 2) (999.88)
  - Investigate/fix stray `scanned_at=None` / port-0 `email_scanner`/`broker_scanner` rows in the console DB after e2e (999.89)
  - Weak-crypto target in the distributed lab so the Phase 111 segment filter can be exercised E2E (999.85, testability)
- **Windows packaging — SPIKE ONLY (106 D-05):** one research/spike phase sizes the PyInstaller frozen-EXE + Windows Scheduled Task host effort and proves feasibility; the full build splits to v5.6 if it's deep. Caps the documented balloon risk.

**Key context:**
- **Public-repo cutover is OUT of scope** — repo stays private this milestone; `windows-sensor-smoke` stays non-blocking CI; enforcing it as a required status check is deferred until the public-repo launch decision is made separately (ops decision, 2026-05-26).
- **Full Windows frozen-binary build is OUT of scope** — gated on the spike outcome → v5.6 fast-follow if deep.
- **SaaS multi-tenancy stays PARKED** — unchanged from v5.4; gated on a business-model signal that does not yet exist.
- **Cadence:** v5.4 broke the 2:1 capability/ops rhythm deliberately; v5.5 is the owed stabilization/hardening breather. Numbering continues at **Phase 113**. Source of truth for forward outlook: `.planning/HORIZON.md`.
- **Live human-UAT keeps catching real bugs** that automated verification (which injected matching in-memory rows) missed — the entire 999.85–89 set came from the post-ship live distributed E2E. Treat live E2E as a first-class gate this milestone.

## Current State

**Phase 155 (drift-detection-eol-tracking) complete 2026-08-14** — 6/6 plans, verification 11/11
must-haves (5/5 ROADMAP Success Criteria + 6/6 HWLC-04..09 requirements). Delivered
`quirk/scanner/hardware_eol.py` (4th curated-catalog + staleness-gate instance, 365-day cadence)
and `quirk/scanner/hardware_drift.py` (N-of-M confirmation gate, 4 distinct drift event types
persisted to a new `hardware_drift_events` table, CVE delta via `hw_cve.py` correlation),
wired into the live scan pipeline. Code review found 1 Critical defect (CR-01: the standalone
SNMP-only bulk-fingerprint path in `run_scan.py` never called `apply_eol_date()`, silently
leaving `eol_date` unpopulated for that entire path) and 1 non-blocking Warning (WR-01: missing
session rollback in `reconcile_device_history()`'s exception handler) — both fixed post-execution
with a regression test added for CR-01. Advisory-only firewall (never scoring-visible) confirmed
and machine-tested. One human-verification item (documentation prose clarity) approved by user;
`155-HUMAN-UAT.md` persists as `status: partial` pending a formal `/gsd:verify-work` pass.
Dashboard/report surfacing of drift events is explicitly Phase 156's scope, not built here.

**v5.12 Release & Verification Integrity — SHIPPED and archived 2026-08-14.** All 6 phases
(148–153) complete, 36 plans, 14/14 requirements satisfied, version 5.12.0 — genuinely tagged,
pushed, published to PyPI, and Windows operator zip attached to the GitHub Release, all
independently re-verified against live GitHub Actions and PyPI's own JSON API. Milestone audit
(`.planning/milestones/v5.12-MILESTONE-AUDIT.md`) scored `passed`; one real integration gap
(stale VALIDATION.md docs on Phases 151/153, and the pre-commit hook they built never actually
installed) was found and fixed during the audit itself, and `core.hooksPath` is now live in this
checkout going forward. Two order-dependent local test failures in the new hook-integration test
file (`tests/test_verify_phase_gates.py`) are carried forward as non-blocking tech debt — CI's
hosted Linux runner is green on the same commit; local macOS full-suite ordering is the only
place they reproduce. Awaiting next milestone via `/gsd:new-milestone`.

**Phase 153 (release-tag-cut) complete 2026-08-14** — 5/5 plans, verification 12/13 must-haves
live-verified (2 `human_needed` items both closed same-session: local commits pushed,
human-attendance of the tag-push checkpoints confirmed directly). One real deviation: the initial
combined `git push origin main --tags` silently didn't fire `release.yml`'s push-event trigger —
a documented GitHub Actions limitation — caught by the executor, independently verified by the
orchestrator, and fixed via a human-approved standalone tag re-push. RELEASE-01 satisfied.

**Phase 152 (discovery-empirical-closure) complete 2026-08-13** — 4/4 plans, verification 4/4
must-haves. Built a genuine two-subnet routed chaos-lab topology (iptables REJECT gateway, not
loopback aliases) to settle the Phase 144 nmap timing-engine artifact once and for all: verdict
**does not reproduce** across 3 independent live-fire runs. `enable_nmap` interactive default
flipped to `True`. DISC-09/10/11 satisfied.

**Phase 151 (phase-completion-artifact-gates) complete 2026-08-13** — 3/3 plans, verification
4/4 must-haves. `scripts/verify_phase_gates.py` + `.githooks/pre-commit` block a phase-close
commit missing VERIFICATION.md, stale VALIDATION.md, or a missing UAT-SERIES.md entry, plus a
destructive-archive guard scoped to `(phase_num, milestone_tag)` with a narrow, documented
exemption for Phase 144's permanent historical gap. ARTIFACT-01..04 satisfied.

**Phase 150 (test-suite-green-baseline-ci-gate) complete 2026-08-13** — 9/9 plans, verification
4/4 must-haves, live-fire proven on real GitHub Actions (green run + a deliberate red-smoke run).
SUITE-02/03 satisfied.

**Phase 149 (test-suite-triage) complete 2026-08-12** — 11/11 plans, verification passed 3/3
must-haves. All 116 pre-existing full-suite failures individually investigated and
dispositioned (fixed / quarantined-xfail / quarantined-skip) across 9 clusters in
`docs/test-triage-149.md`; 2 genuine production bugs fixed in place (sslyze `__version__`
submodule-shape drift silently discarding every sslyze result on sslyze>=6.3; impacket
`MethodData`→`METHOD_DATA` rename silently disabling all Kerberos scanning on the current
pin). A systemic macOS `fork()`-under-full-suite-load SIGSEGV cluster (5 tests) was traced to
one shared root cause rather than 5 independent defects. Code review caught a real gap before
close (CR-01: an orphaned `test_dashboard_trends.py` flake the reconciliation sweep missed,
same shared-cache SQLite class as Cluster 5) — fixed in follow-up commit before verification.
Final ledger: 117 rows, fresh `pytest -q -m ""` is 0 failed (3087 passed, 82 xfailed, 42
skipped). SUITE-01 satisfied.

**Phase 148 (release-pipeline-repair-windows-asset-backfill) complete 2026-08-11** — 4/4 plans,
verification passed 5/5 must-haves. RELEASE-02/03/04 proven against live GitHub Actions (real
`workflow_dispatch` dry-run, real tag-hygiene guard run, real `v5.11.0` GitHub Release with
zero assets and the PyPI-only disposition body) rather than by code inspection alone.

**v5.11 Discovery at Scale + Backlog Drain — SHIPPED and archived 2026-08-11.** All 4 phases
(144–147) complete, 16 plans, 11/11 requirements satisfied, version 5.11.0. Milestone audit
(`.planning/milestones/v5.11-MILESTONE-AUDIT.md`) scored `passed` — 4/4 phases verified, 8/8
cross-phase seams wired, 3/3 E2E flows complete, Nyquist compliant. All six audit findings were
closed during closeout; only one required a code change (WR-02, per-batch SQLAlchemy engine
disposal). Five remaining tech-debt items are non-blocking and either deferred by explicit scope
decision (DISC-08, DISC-09), accepted by design (IN-01), or unresolvable without hardware the dev
machine doesn't have (the Phase 144 nmap timing-engine artifact, which needs a real routed
network segment). Awaiting next milestone via `/gsd:new-milestone`.

**Notable for next-milestone planning:** the release workflow (`release.yml`, holding the
`windows-package` job and its Authenticode signing step) fires only on a `v*.*.*` tag push, and
the newest remote tag before v5.11 was `v5.9`. Cutting the v5.11.0 tag is therefore the action
that exercises the Windows build path for all Phase 139–147 work for the first time.

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

- **Current version**: v5.7.0 (shipped 2026-06-14, tag `v5.7.0`); repo PUBLIC at github.com/0xD1g5/QU.I.R.K with branch protection + required `Windows Sensor Smoke` check; Windows sensor zip on GitHub Releases
- **Language**: Python 3.11+ (core scanner, FastAPI backend)
- **Frontend**: React + shadcn/ui + Tailwind CSS (built React bundle in `quirk/dashboard/static/`)
- **Database**: SQLite (local, `./quirk.db`); designed for Postgres migration at SaaS phase
- **Chaos lab**: Docker Compose, 20 profiles (core + 6 Phase 4 + 3 v4.2 identity: dnssec/saml/kerberos + storage-s3 + database + vault + email + broker + tls-cert-defects Phase 46 + hwcompat Phase 127)
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
| Three-pass git-filter-repo history rewrite before going public (v5.6 / 120-04) | Tracked PEM keys + 1314 `.planning/` files + dev-only artifacts in history were a posture BLOCK for the public flip; rewrite is the only way to remove them from history. Two-step pattern locked: `git rm --cached` + commit FIRST, then filter-repo (pass-2 on still-tracked paths deleted 86 working-tree files — recovered from mirror). | ✓ Good — gitleaks 0 findings post-rewrite; 989→901 files, 6260→2952 commits; recovery mirror at `~/Backups/QUIRK-pre-rewrite-2026-05-28.git` |
| Branch-protection required check uses GitHub check-run DISPLAY name, not YAML job key (v5.6 / 579f6bf) | GitHub matches required-status contexts against check-run display names (`Windows Sensor Smoke`), not workflow YAML job keys (`windows-sensor-smoke`); the key form would have made the requirement unsatisfiable on every PR. | ✓ Good — live `gh api` shows the context enforced and satisfiable; verified on the v5.6.0 tagged commit |
| `.planning/` + CLAUDE.md excluded from the public repo (gitignore + history strip) (v5.6 / 120-03/04) | Planning internals and agent instructions are not part of the public product surface. Consequence accepted: worktree subagents can't see them (absolute main-repo paths required) and planning docs are disk-only/uncommitted. | ✓ Good — public HEAD clean; GSD workflows adapted (absolute paths, no docs commits) |
| Tag release gated on the required check only, not all workflows (v5.6 / 122-04) | Dashboard Quality was red on main from pre-existing a11y/E2E failures unrelated to the release; the protection contract names `Windows Sensor Smoke` as the gate. Human checkpoint approved with full CI picture presented. | ✓ Good — v5.6.0 released with green required check; redness ledgered for v5.7 |
| HWCOMPAT advisory-only lock (v5.7 / 127-01-D-01) | Hardware device remediation is a multi-year procurement decision with a different timescale than crypto-hygiene calibration; mixing it into the readiness score would mislead clients into thinking they can act on it immediately. CI-verifiable via grep on `SCORE_WEIGHTS`. | ✓ Good — zero hardware counter in SCORE_WEIGHTS; `test_score_weights_invariant.py` CI gate unchanged |
| CBOM Pass 4 uses `ComponentType.FIRMWARE` (v5.7 / 129-02-D-08) | The detectable artifact is the device firmware version string reported in SSH banner or HTTP management headers; DEVICE+firmware child hierarchy requires richer data (serial numbers, hardware model IDs) not available from agentless probing. `ComponentType.DEVICE` is the v5.8 refinement. | ✓ Good — FIRMWARE components validate against CycloneDX 1.6 schema; procurement teams can filter by bom_ref prefix `hw/` |
| Bridge detection `/24` heuristic only (v5.7 / 129-01) | Full CIDR routing table knowledge requires SNMP (deferred to v5.8); the /24 heuristic is zero-install-footprint, correct for the common single-broadcast-domain case, and conservative on misses (unknown = no pairing = no false positive). | ✓ Good — 6/6 contract tests pass; `partial_only` is conservative by design; `upstream_mitigated` reserved for v5.8 SNMP path |
| Jinja2 `\| safe` required on pre-rendered hardware HTML (v5.7 / 128-02) | `select_autoescape(["html", "j2"])` escapes all `{{ }}` output by default; pre-rendered HTML from `render_hardware_section()` must use `\| safe` or it displays as literal `&lt;details&gt;` text in the browser. | ✓ Good — UAT-128-02 confirmed advisory block appears; `| safe` is the canonical Jinja2 pattern for pre-rendered content |
| `CLAUDE.md` Per-Phase Documentation Checklist + Milestone-Boundary Doc Review Template as structural enforcement (v5.9 / 138-02, LIVE-01/02/03) | Doc staleness had accumulated silently across v5.4–v5.8 (distributed architecture, SNMP, CBOM hierarchy all shipped with no admin-guide, stale README/architecture); discipline alone hadn't prevented drift, so the fix is a checklist that's non-skippable at phase and milestone boundaries | ✓ Good — self-proven: the same audit that verified this section landing also caught CORE-04/LIVE-03 drift, and the follow-up gap-closure phases (138.1/138.2) both correctly followed the new checklist (UAT-SERIES.md + vault sync) |
| Cross-document consistency verification over presence-only checks (v5.9 / 138.1) | The CORE-04 defect (inverted CNSA 2.0 tier severity in architecture.md) shipped and passed Phase 135's verification because that pass checked the section *existed*, not that its content agreed with `hardware_tier.py` and operators-guide.md | ✓ Good — 138.1's verifier explicitly cross-referenced code + both docs; the milestone re-audit repeated this cross-reference independently and found zero re-inversion or drift anywhere else |
| Obsidian vault sync verified by content diff, not mtime (v5.9 / 138.2) | LIVE-03 shipped believing vault guides were "synced" based on file-exists + timestamp checks; two guides were actually stale despite passing that check | ✓ Good — 138.2 diffed vault body against `docs/` source byte-for-byte; the milestone re-audit repeated the diff check on all six vault guides and confirmed zero content drift |

| Relax reject gates in the SAME phase as the chunking that replaces them (v5.11 / 144-01) | Splitting gate-relaxation from the chunking core risks a repeat of the Phase 141 outer-gating bug shape — a feature fully built, fully tested, and never reachable in production because an outer gate still rejects the input | ✓ Good — live end-to-end submission confirmed 201 acceptance and job completion; had the gates been deferred, every unit test would still have passed against unreachable code |
| Dedicated `discovery_exception` category, never the generic `"exception"` (v5.11 / 146 CR-01) | `_wrapped_phase()` emits `scan_error_category="exception"` with a scanner-name label (not a host) at 20+ call sites; filtering on it for the undetermined-host count conflates an unrelated TLS/SSH crash with host unreachability in a consulting deliverable | ✓ Good — caught by code review, not CI: the phase's own regression test asserted the wrong exclusion case and passed straight over the bug |
| Fail open when nmap's liveness accounting doesn't reconcile (v5.11 / 145-03) | Real `-sn -PS` subnet sweeps emit `<host>` elements only for hosts nmap can positively report on, so an absent host is ambiguous; inferring "down" from absence is only safe when `<runstats>` proves `exit=success` AND `total == len(targets)` | ✓ Good — the D-06 non-root human gate caught the pre-pass filtering zero hosts on every real sweep; the fix preserves the reliability-first rule that a live host must never be wrongly marked dead |
| Do not tune nmap timing flags to make one synthetic live check pass (v5.11 / 144-03) | Changing default `-T`/RTT bounds alters behavior for every production scan, trading false negatives on slow real networks against a artifact only reproducible on unassigned macOS loopback aliases | — Pending — accepted via signed override; resolution deferred to a real routed segment, best paired with DISC-09's lab profile |

---
*Last updated: 2026-08-14 — Phase 155 (drift-detection-eol-tracking) complete, HWLC-04..09 validated*

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
