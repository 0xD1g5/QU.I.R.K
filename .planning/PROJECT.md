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

## Current Milestone: v4.5 Reliability & Gap Closure

**Goal:** Close v4.4 deferred items, harden scanner/CBOM/dashboard correctness, and automate the long-tail UAT debt — putting QU.I.R.K. in solid shape before the next capability and performance milestones.

**Target features:**

Gap closure
- Fix DEF-v4.4-02: restore SAML/OIDC entries in `/api/scan/latest` `identity_findings` (ISSUE-3 from Phase 24)
- Flip DEF-v4.4-01: Phase 36 `wave_0_complete` → `true` once the SAML fix lands
- Ship DASH-05: Data at Rest dashboard tab (deferred from Phase 27)

Reliability hardening
- Test flakiness / CI stability — resolve the deferred SAML scan-window test, eliminate intermittents, lock CI green
- Scanner robustness — graceful degradation under partial failures, missing extras, slow targets; timeout/retry audit across all scanners
- CBOM correctness audit — CycloneDX 1.6 spec validation, classifier coverage, golden-snapshot drift review
- Dashboard polish — console errors, accessibility, loading states across `/motion`, `/trends`, `/findings`

UAT debt burndown
- Automate where possible — CI-runnable Docker fixtures for items that don't truly need cloud creds (Phase 27 DB, Phase 29 minikube, etc.); cloud-bound items remain deferred

**Phase numbering:** continues from Phase 38 (default). v4.4 ended at Phase 37.

**Out of scope (this milestone):** new scanners, new cloud connectors, performance/scale work, SaaS, CBOM v2 schema work, mobile.

## Current State: v4.4.0 Shipped — v4.5 Phase 43 Complete (gap closure done)

v4.4 "Data in Motion" shipped 2026-04-29 (tag `v4.4.0`, commit `b72797a`). The cryptographic inventory now covers six pillars: TLS, SSH, API, Identity, Data at Rest, and Data in Motion. Email and broker TLS posture flow through scanning → intelligence → CBOM → dashboard end-to-end.

**v4.5 starting open items (in scope):**
- DEF-v4.4-01 — Phase 36 `wave_0_complete: false` flip (gated on SAML fix)
- DEF-v4.4-02 — SAML/OIDC missing from `/api/scan/latest` `identity_findings`
- DASH-05 — Data at Rest dashboard tab (deferred from Phase 27)
- 14 carry-over UAT/verification gaps — automate where possible

## Context

- **Current version**: v4.4.0 (shipped 2026-04-29); v4.3.0 shipped 2026-04-26
- **Language**: Python 3.11+ (core scanner, FastAPI backend)
- **Frontend**: React + shadcn/ui + Tailwind CSS (built React bundle in `quirk/dashboard/static/`)
- **Database**: SQLite (local, `./quirk.db`); designed for Postgres migration at SaaS phase
- **Chaos lab**: Docker Compose, 18 profiles (core + 6 Phase 4 + 3 v4.2 identity: dnssec/saml/kerberos + storage-s3 Phase 28 + database Phase 27 + vault Phase 30 + email Phase 32 + broker Phase 33)
- **Business model**: Consulting deliverable — tool enables billable assessments
- **Delivery model**: `pip install quirk[motion]` (single happy path) + `quirk init` + `quirk --config` + `quirk serve`; SaaS platform (future milestone)
- **Target users**: Security consultants (power), IT generalists (guided), compliance officers (reports)
- **Key differentiators**: CBOM output (CycloneDX 1.6 JSON+XML); 6-pillar quantum-readiness scoring with NIST PQC classification; identity protocol scanning (Kerberos/SAML/DNSSEC); data-at-rest coverage (databases, object storage, K8s secrets, Vault); data-in-motion coverage (email + broker TLS + cloud queues); chaos lab for client-side scanner validation; polished HTML/PDF reports
- **Test coverage**: 662 tests passing (pytest); all v4.4 Nyquist VALIDATION.md files declare `nyquist_compliant: true` and `wave_0_complete: true` (except Phase 36 — DEF-v4.4-01)
- **Known tech debt at v4.4 close**: SAML scan-window regression (DEF-v4.4-02), Phase 36 `wave_0_complete` gating (DEF-v4.4-01), 14 pre-v4.4 carry-over UAT/verification gaps in STATE.md `## Deferred Items`
- **v4.4 milestone shipped** (2026-04-29): 6 phases (32–37), 33 plans — email + broker TLS scanning, motion intelligence, motion CBOM, dashboard Motion tab, v4.4.0 release artifacts

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

---
*Last updated: 2026-05-02 — Phase 43 dashboard-polish gap closure complete; a11y harness, pagination guards, PDF sentinel all verified*

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
