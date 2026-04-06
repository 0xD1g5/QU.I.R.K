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

## Current Milestone: v4.1 Foundation Polish

**Goal:** Make v4.0.0 trustworthy enough that new scanner output is credible — exclusively closes P0/P1 correctness and trust gaps before any scanner expansion.

**Target features:**
- CLI Correctness: fix wrong config field names, missing `quirk scan` subcommand, `[owner]` placeholder in generated configs, version number conflicts in client-facing output (BACK-40, 41, 47, 48)
- Interactive Mode Overhaul: auto-detect timezone, remove stub prompts, fix AWS/Azure labels, surface JWT/container/source scanners, scan profile selection, port list expansion, prompt reordering (BACK-27–33, 36, 38, 39)
- Scoring & Intelligence Correctness: calibration profiles actually applied, validate.py fixed, migration_advisor matching fixed, dashboard profile propagation wired (BACK-43, 44, 46, 60)
- Code Hygiene: remove legacy connector stubs, cfg.scan mutation guard, delete orphaned scorecard.py, update 11 Nyquist VALIDATION.md files (BACK-37, 45, 61, 62)

### Active

**v4.1 Foundation Polish**
- [ ] CLI Correctness — wrong config field names crash first-run (BACK-40); `quirk scan` subcommand missing (BACK-41); `[owner]` placeholder in generated config (BACK-47); version number conflicts in client output (BACK-48)
- [ ] Interactive Mode — auto-detect timezone (BACK-27); remove SNI prompt (BACK-28); remove ADCS stub prompt (BACK-29); fix AWS/Azure labels + credential warnings (BACK-38); surface JWT/container/source scanners (BACK-32); scan profile selection replaces raw timeout/concurrency prompts (BACK-30); expand TLS port defaults (BACK-33); reorder prompts targets-first (BACK-36); remove `enable_windows_adcs` dead field (BACK-39); consolidate data_classification prompts (BACK-31)
- [ ] Scoring Correctness — calibration profile actually applied in compute_readiness_score() (BACK-43); validate.py artifact list fixed (BACK-44); migration_advisor pattern matching fixed (BACK-46); dashboard profile kwarg wired (BACK-60)
- [ ] Code Hygiene — remove legacy connector stub directory (BACK-37); cfg.scan mutation wrapped in try/finally (BACK-45); delete orphaned scorecard.py (BACK-61); update 9 stale + 2 missing Nyquist VALIDATION.md files (BACK-62)

**v4.2+ Scanner Expansion (Future Milestones)**
- Identity Crypto (v4.2): Kerberos etype enumeration, SAML/OAuth metadata, DNSSEC
- Data at Rest (v4.3): DB encryption, S3/Blob/GCS audit, K8s secrets, Vault connector
- Data in Motion (v4.4): Email SMTP/IMAP/POP3, message brokers (Kafka, RabbitMQ, Redis)
- API Depth (v4.5): OpenAPI spec analysis, Bearer token interception, active REST probing

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

- **Current version**: v4.0.0 — fully shipped (v3.9 Gap Closure milestone complete 2026-04-04)
- **Language**: Python 3.11+ (core scanner, FastAPI backend)
- **Frontend**: React + shadcn/ui + Tailwind CSS (built React bundle in `quirk/dashboard/static/`)
- **Database**: SQLite (local, `./quirk.db`); designed for Postgres migration at SaaS phase
- **Chaos lab**: Docker Compose, 10 profiles (core + 6 Phase 4 additions: jwt/registry/source/storage/ssh-weak/ldaps)
- **Business model**: Consulting deliverable — tool enables billable assessments
- **Delivery model**: `pip install` + `quirk init` + `quirk --config` + `quirk serve`; SaaS platform (future milestone)
- **Target users**: Security consultants (power), IT generalists (guided), compliance officers (reports)
- **Key differentiators**: CBOM output (CycloneDX 1.6 JSON+XML), quantum-readiness scoring with NIST PQC classification, chaos lab for client-side scanner validation, polished HTML/PDF reports
- **Test coverage**: 199 tests passing (pytest); VALIDATION.md Nyquist files stale (BACK-62)
- **Known tech debt**: Dashboard scoring profile gap (BACK-60), orphaned scorecard.py (BACK-61), Nyquist files (BACK-62)

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
| Intelligence profile kwarg not passed to dashboard | Dashboard scan.py:330 calls compute_readiness_score without profile= | ⚠ Revisit — dashboard always uses balanced; BACK-60 tracked |

---
*Last updated: 2026-04-06 — Phase 12 complete: CLI correctness — version strings unified at 4.1.0 across all locations, Getting Started docs corrected, 205 tests passing*

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
