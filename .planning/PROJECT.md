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

- ✓ TLS endpoint scanning (cert extraction, cipher enumeration, expiry detection) — existing
- ✓ SSH banner detection — existing
- ✓ HTTP/plaintext detection — existing
- ✓ Risk engine with findings (severity-ranked) — existing
- ✓ Intelligence layer (4-subscore readiness model, calibration, confidence, delta reports) — existing
- ✓ SQLite persistence — existing
- ✓ Scan profiles (quick/standard/deep) with caching and rate limiting — existing
- ✓ Docker-based chaos lab for scanner validation — existing
- ✓ Package renamed QuRisk → QU.I.R.K. / quirk (qcscan/ → quirk/) — Phase 1
- ✓ sslyze integration — primary TLS scanner with fallback (tls_capabilities_json) — Phase 1
- ✓ ssh-audit integration — threaded SSH scanner with full KEX/hostkey/MAC enumeration — Phase 1
- ✓ Single scoring path through intelligence/scoring.py (assessment/ imports removed) — Phase 1
- ✓ cert_pubkey_alg correctly extracted as first probe in _extract_cert_key_type() — Phase 1

### Active

**Product Identity & Branding**
- [ ] Define visual identity (palette, logo mark for reports/UI)

**Scanner Coverage Expansion**
- ✓ API/JWT scanner — REST endpoint discovery, JWKS fetch, JWT algorithm and key-size classification — Phase 3
- ✓ Container/binary scanner — Syft subprocess wrapper with 23-entry CRYPTO_LIB_ALLOWLIST — Phase 3
- ✓ Source code scanner — semgrep p/cryptography ruleset, file:line service_detail format — Phase 3
- ✓ Cloud connector (AWS) — ACM, KMS, CloudFront, ELBv2 via boto3, KMS_KEY_SPEC_MAP (13 entries) — Phase 3
- ✓ Cloud connector (Azure) — Key Vault + App Gateway via azure-sdk-for-python — Phase 3

**CBOM Pipeline**
- ✓ cyclonedx-python-lib integration — map all scan results to CycloneDX CBOM components — Phase 2
- ✓ Quantum-safety classification per algorithm (NIST PQC catalog enrichment) — Phase 2
- ✓ CBOM as first-class output artifact (JSON + XML) per scan run — Phase 2
- [ ] CBOM viewer in web dashboard

**Scoring Consolidation**
- ✓ Duplicate scoring systems removed — single path through intelligence/scoring.py — Phase 1
- ✓ cert_pubkey_alg field propagation fixed — Phase 1
- ✓ Profile-based weight multipliers (strict/balanced/lenient) in compute_readiness_score() — Phase 9
- ✓ executive.py refactored to intelligence/ call sequence; NOW/NEXT/LATER roadmap — Phase 9
- ✓ Four deprecated assessment compute modules deleted; zero live imports remain — Phase 9
- ✓ MISMATCH-01 fixed: quantum_safety_label() type confusion resolved in dashboard API — Phase 10
- ✓ PACKAGE-01 fixed: dashboard static assets included in pip wheel (pyproject.toml) — Phase 10
- ✓ MISSING-01 fixed: intelligence config block documented in config_template.yaml — Phase 10
- ✓ GAP-INT-01 fixed: deps.py default db_path aligned with config_template.yaml (./quirk.db) — Phase 11
- ✓ GAP-INT-02 fixed: server.py sets QUIRK_SERVE_PORT env var before uvicorn.run() — Phase 11
- ✓ GAP-INT-03 fixed: _derive_cbom() parses ssh_audit_json; SSH endpoints produce CBOM entries — Phase 11

**Web Dashboard (FastAPI + React + shadcn/ui)**
- [ ] FastAPI API layer serving scanner results and managing scan jobs
- [ ] React SPA with shadcn/ui — executive dashboard, findings table, certificate inventory, CBOM viewer
- [ ] Score gauges, trend charts, severity heatmaps
- [ ] Report generation: HTML export, PDF (Playwright headless), existing Markdown
- [ ] Scan configuration and job management UI

**Requirements & Access Definition**
- [ ] Minimum system requirements documented (OS, Python version, RAM, disk)
- [ ] Network access requirements documented (ports, protocols, firewall rules)
- [ ] Privilege requirements documented (agentless by default; optional elevated for SSH host-key, cloud IAM)
- [ ] Cloud credential requirements (AWS IAM policy, Azure RBAC roles defined as least-privilege)
- [ ] Container scanning requirements (Docker socket access, registry credentials)
- [ ] Source code scanning requirements (git access, language runtimes)

**Documentation** — Validated in Phase 6
- ✓ Getting Started guide — zero-to-first-scan in under 10 minutes — Phase 6
- ✓ Installation guide (macOS, Linux, Windows via WSL) — Phase 6
- ✓ Configuration reference (all config.yaml options + 16 CLI flags) — Phase 6
- ✓ Connector setup guides (AWS, Azure, Docker, Git) with least-privilege credential templates — Phase 6
- ✓ Report interpretation guide — score bands, severity tiers, Client Conversation sideboxes — Phase 6
- ✓ Chaos lab operator guide — all 10 profiles, 38-port reference table — Phase 6
- ✓ CBOM guide — three sections: compliance officers, technical readers, auditors — Phase 6

**Chaos Lab Expansion**
- [ ] `jwt` profile — 4 JWT API services (RS256, HS256-weak, RSA1024, alg:none) + JWKS server
- [ ] `registry` profile — Docker Registry v2 + test images with embedded crypto vulnerabilities
- [ ] `source` profile — Gitea + pre-seeded repos with crypto anti-patterns
- [ ] `storage` profile enhancements — LocalStack KMS, HashiCorp Vault, postgres-encrypted
- [ ] `ssh-weak` service — OpenSSH with deliberately weak KEX/hostkey/MAC config
- [ ] `ldaps` service — OpenLDAP over TLS (LDAPS on 636)

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

- **Language**: Python 3.11+ (core scanner, FastAPI backend)
- **Frontend**: React + shadcn/ui + Tailwind CSS
- **Database**: SQLite (local); designed for Postgres migration at SaaS phase
- **Existing version**: v3.9 (QuRisk) — scanner pipeline solid, needs coverage expansion + CBOM + UI
- **Chaos lab**: Docker Compose, profiles (core/phaseA/cloud/identity/pki) — needs jwt/registry/source/storage additions
- **Business model**: Consulting deliverable — tool enables billable assessments
- **Delivery model**: CLI + local web dashboard (v1); SaaS platform (future milestone)
- **Target users**: Security consultants (power), IT generalists (guided), compliance officers (reports)
- **Key differentiators**: CBOM output, quantum-readiness scoring, chaos lab for client-side validation,
  polished reports that don't look like they came from a basement

## Constraints

- **Python-native where possible**: Prefer pip-installable libraries (sslyze, cyclonedx-python, paramiko) over subprocess wrappers
- **Agentless default**: Scanner must work without installing agents on target hosts
- **Consultant UX**: Zero-to-scan in under 10 minutes on a fresh machine; guided setup
- **Offline capable**: Core scan + reporting must work with no internet access (critical for air-gapped client engagements)
- **Existing SQLite schema**: New fields must be additive; no breaking schema migrations in v1

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| FastAPI + React (shadcn/ui) for dashboard | Richest ecosystem for polished security dashboards; SaaS-ready; Playwright PDF | — Pending |
| sslyze over testssl.sh | Python-native, programmatic API, no bash dependency | — Pending |
| ssh-audit over raw paramiko | JSON output, full algorithm enumeration, maps to CBOM | — Pending |
| cyclonedx-python-lib for CBOM | Only Python SDK with full CycloneDX 1.4+ CBOM schema support | — Pending |
| IBMKit Hyperion over QSE | Open source, CBOM-native output, no proprietary lock-in | — Pending |
| Consulting deliverable model | Tool enables billable services; lower GTM friction than SaaS | — Pending |
| SaaS on roadmap (not v1) | Avoid premature infrastructure; prove value with CLI first | — Pending |
| Rename QuRisk → QU.I.R.K. | Brand identity aligned with product scope and market positioning | — Pending |

---
*Last updated: 2026-04-04 after Phase 11 completion — dashboard wiring fixes complete; GAP-INT-01, GAP-INT-02, GAP-INT-03 all resolved; all 5 Phase 11 wiring tests passing, 199-test suite green*

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
