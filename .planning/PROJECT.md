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

## Current Milestone: v4.3 Data at Rest

**Goal:** Expand QU.I.R.K.'s cryptographic inventory to cover data-at-rest encryption and cloud coverage depth — database encryption settings, object storage policies, Kubernetes secrets, HashiCorp Vault transit keys, GCP connector, and cross-session trend analysis for delta reporting. First milestone to include Phase 25 (Identity Findings Accuracy) carried from v4.2.

### Active

**v4.3 Data at Rest (Phases 25+)**
- [ ] Identity Findings Accuracy (Phase 25 — carried from v4.2) — RS-family branch in _derive_identity_findings() for OIDC RS256; ldap3 added to [identity] extras
- [ ] Database encryption detection — PostgreSQL, MySQL, RDS encryption settings
- [ ] Object storage audit — S3 (SSE-S3/SSE-KMS), Azure Blob (CMK/platform key), GCS bucket encryption policies
- [ ] Kubernetes secrets inspection — etcd EncryptionConfiguration, secret types
- [ ] HashiCorp Vault connector — transit keys, PKI mounts, auth method audit
- [ ] GCP connector — Cloud KMS key specs, Cloud SQL TLS config, GCS bucket encryption (BACK-14)
- [ ] Trend analysis across scan sessions — score delta, new/resolved findings, degraded host tracking (BACK-21)

**v4.4 Data in Motion (Planned)**
- [ ] Email protocol scanning — SMTP/STARTTLS, IMAP, POP3 via sslyze handoff
- [ ] Message broker TLS — Kafka, RabbitMQ, Redis, AMQP connection audit

**SaaS Platform (Future Milestone)**
- [ ] Multi-tenant architecture design
- [ ] Scan job queue (Celery + Redis or similar)
- [ ] User auth and org management
- [ ] Cloud deployment (Docker Compose → Kubernetes)
- [ ] Hosted reporting and CBOM storage

### Out of Scope (v1)

| Feature | Reason |
|---------|--------|
| Email / S/MIME scanning | Lower priority vs JWT/container/code surfaces; deferred |
| Windows AD CS live connector | Complex Kerberos/NTLM auth; stub remains, deferred to v2 |
| Network traffic capture (Zeek/Wireshark) | Requires passive tap; out of scope for agentless model |
| OpenVAS / Nessus integration | Full vuln scanner; different scope, heavy dependency |
| Mobile app | Web-first; SaaS phase determines mobile need |
| Real-time continuous monitoring | SaaS milestone, not v1 |

## Context

- **Current version**: v4.2.0 — shipped 2026-04-24 (v4.2 Identity Crypto milestone complete)
- **Language**: Python 3.11+ (core scanner, FastAPI backend)
- **Frontend**: React + shadcn/ui + Tailwind CSS (built React bundle in `quirk/dashboard/static/`)
- **Database**: SQLite (local, `./quirk.db`); designed for Postgres migration at SaaS phase
- **Chaos lab**: Docker Compose, 13 profiles (core + 6 Phase 4 additions + 3 v4.2 identity: dnssec/saml/kerberos)
- **Business model**: Consulting deliverable — tool enables billable assessments
- **Delivery model**: `pip install` + `quirk init` + `quirk --config` + `quirk serve`; SaaS platform (future milestone)
- **Target users**: Security consultants (power), IT generalists (guided), compliance officers (reports)
- **Key differentiators**: CBOM output (CycloneDX 1.6 JSON+XML), quantum-readiness scoring with NIST PQC classification, identity protocol scanning (Kerberos/SAML/DNSSEC), chaos lab for client-side scanner validation, polished HTML/PDF reports
- **Test coverage**: 352 tests passing (pytest); all Nyquist VALIDATION.md files up to date
- **Known tech debt**: ISSUE-2 (ldap3 absent from pyproject.toml — KERB-03 LDAP always inerts), NEW-ISSUE-1 (OIDC RS256 findings mislabeled as TLS-sourced) — both Phase 25 targets in v4.3
- **v4.2 milestone shipped** (2026-04-24): 8 phases (17–24), 14 plans — full identity protocol surface: DNSSEC + SAML/OIDC + Kerberos scanners, 3 chaos lab profiles, Identity tab in dashboard, CBOM integration, scan-session timestamp isolation

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
| ldap3 deferred to Phase 25 | ldap3 was absent from pyproject.toml at v4.2 ship; KERB-03 LDAP path always degrades gracefully | ⚠ Revisit — fix is one dependency line in v4.3 Phase 25; LDAP enumeration inert until then |

---
*Last updated: 2026-04-24 after v4.3 Data at Rest milestone started — 7 features scoped: Phase 25 identity carry-over, database encryption, object storage, K8s secrets, HashiCorp Vault, GCP connector (BACK-14), trend analysis (BACK-21).*

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
