# Requirements: QU.I.R.K.

## Project

Quantum Infrastructure Readiness Kit — consulting-grade cryptographic inventory scanner and
quantum-readiness assessment platform. Delivers a complete, defensible cryptographic inventory
with a CBOM deliverable and quantum-readiness score that a consultant can hand to a client
in under two hours.

## Scope

**Milestone:** v4.0 — Foundation to polished consulting tool
**Granularity:** Standard (5-8 phases)
**Baseline:** v3.9 (QuRisk) scanner core — TLS, SSH banner, HTTP detection, risk engine,
intelligence layer, SQLite persistence, scan profiles, chaos lab — all operational.

## Requirement Categories

### CORE — Core Fixes

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| CORE-01 | Scoring system consolidation — deprecate duplicate paths (assessment/readiness_score.py + intelligence/scoring.py), single authoritative path through writer.py evidence model | Must have | Correctness blocker |
| CORE-02 | Fix cert_pubkey_alg field propagation in writer.py (_extract_cert_key_type mismatch) | Must have | Data quality blocker |
| CORE-03 | Rename QuRisk → QU.I.R.K. / quirk throughout codebase, CLI, and all references | Must have | Brand identity |
| CORE-04 | SSH scanner thread-pool — replace sequential per-host scanning with concurrent thread pool | Must have | Performance blocker for large scans |

### SCAN — Scanner Capabilities

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| SCAN-01 | sslyze TLS deep scan integration — replace/augment capability enum with Python-native deep scanner | Must have | Python-native, programmatic API |
| SCAN-02 | ssh-audit KEX/hostkey/MAC full enumeration — replace banner-only SSH scan | Must have | Full algorithm inventory for CBOM |
| SCAN-03 | API/JWT scanner — REST endpoint discovery, JWKS fetch, JWT algorithm and key-size classification | Must have | New attack surface coverage |
| SCAN-04 | Container/binary crypto scanner — Syft + Trivy subprocess wrapper for crypto library inventory | Must have | Container surface coverage |
| SCAN-05 | Source code scanner — CBOMkit Hyperion / PQCA integration for code-level crypto detection | Must have | Code surface coverage |
| SCAN-06 | AWS cloud connector — ACM, KMS, CloudFront, ELB/ALB via boto3 | Must have | Cloud surface coverage |
| SCAN-07 | Azure cloud connector — Key Vault, App Gateway via azure-sdk-for-python | Must have | Cloud surface coverage |

### CBOM — Cryptographic Bill of Materials Pipeline

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| CBOM-01 | cyclonedx-python-lib integration — map all scan results to CycloneDX CBOM components | Must have | Key differentiator |
| CBOM-02 | Algorithm → CBOM component mapping layer (all scanner outputs → CycloneDX schema) | Must have | Required for CBOM output |
| CBOM-03 | NIST PQC quantum-safety classification enrichment per algorithm | Must have | Required for readiness scoring |
| CBOM-04 | CBOM JSON + XML output artifact per scan run | Must have | Consulting deliverable |

### LAB — Chaos Lab Expansion

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| LAB-01 | jwt profile — 4 JWT API services (RS256, HS256-weak, RSA1024, alg:none) + JWKS server | Must have | Validates SCAN-03 |
| LAB-02 | registry profile — Docker Registry v2 + test images with embedded crypto vulnerabilities | Must have | Validates SCAN-04 |
| LAB-03 | source profile — Gitea + pre-seeded repos with crypto anti-patterns | Must have | Validates SCAN-05 |
| LAB-04 | storage profile — LocalStack KMS, HashiCorp Vault, postgres-encrypted | Must have | Validates SCAN-06 cloud patterns |
| LAB-05 | ssh-weak service — OpenSSH with deliberately weak KEX/hostkey/MAC config | Must have | Validates SCAN-02 |
| LAB-06 | ldaps service — OpenLDAP over TLS (LDAPS on port 636) | Must have | Validates TLS/sslyze against directory services |

### UI — Web Dashboard

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| UI-01 | FastAPI API layer — scan job management, results API, serving scanner output | Must have | Backend for dashboard |
| UI-02 | React + shadcn/ui executive dashboard — score gauges, trend charts, severity heatmaps | Must have | Primary UI deliverable |
| UI-03 | Findings table, certificate inventory, CBOM viewer in dashboard | Must have | Core dashboard content |
| UI-04 | HTML report export + PDF generation via Playwright headless | Must have | Consulting deliverable |

### DOC — Documentation

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| DOC-01 | Getting Started guide — zero-to-first-scan in under 10 minutes | Must have | Onboarding gate |
| DOC-02 | Installation guide — macOS, Linux, Windows via WSL; system requirements | Must have | Required for distribution |
| DOC-03 | Configuration reference — all config.yaml options documented | Must have | Power user reference |
| DOC-04 | Connector setup guides — AWS, Azure, Docker, Git with least-privilege credential templates | Must have | Required for cloud connectors |
| DOC-05 | Report interpretation guide — what each score/finding means, what to tell the client | Must have | Consultant enablement |
| DOC-06 | CBOM guide — what it is, how to use it for compliance evidence | Must have | Differentiator enablement |
| DOC-07 | Chaos lab operator guide — updated for all new profiles (jwt, registry, source, storage, ssh-weak, ldaps) | Must have | Lab usability |

### BRAND — Branding and Polish

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| BRAND-01 | QU.I.R.K. visual identity — name treatment, color palette, logo mark for reports and dashboard | Must have | Professional positioning |
| BRAND-02 | CLI UX polish — rich progress indicators, consistent output formatting, version command | Must have | Consultant UX |
| BRAND-03 | Professional report templates — HTML + PDF with QU.I.R.K. branding and consultant-grade layout | Must have | Consulting deliverable quality |
| BRAND-04 | Packaging + installer — pip install quirk or single-file distribution; zero-to-scan < 10 min on fresh machine | Must have | Distribution gate |

## Out of Scope (v1)

| Feature | Reason |
|---------|--------|
| Email / S/MIME scanning | Lower priority vs JWT/container/code surfaces; deferred to v2 |
| Windows AD CS live connector | Complex Kerberos/NTLM auth; stub remains; deferred to v2 |
| Network traffic capture (Zeek/Wireshark) | Requires passive tap; out of scope for agentless model |
| OpenVAS / Nessus integration | Full vuln scanner; different scope, heavy dependency |
| Mobile app | Web-first; SaaS phase determines mobile need |
| Real-time continuous monitoring | SaaS milestone, not v1 |
| SaaS platform (multi-tenant, Celery, hosted reporting) | Deferred to future milestone after v1 ships |
| Score trend charts in CLI | Dashboard handles visualization |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| CORE-01 | Phase 1 | Complete |
| CORE-02 | Phase 1 | Complete |
| CORE-03 | Phase 1 | Complete |
| CORE-04 | Phase 1 | Complete |
| SCAN-01 | Phase 1 | Complete |
| SCAN-02 | Phase 1 | Complete |
| CBOM-01 | Phase 2 | Complete |
| CBOM-02 | Phase 2 | Complete |
| CBOM-03 | Phase 10 | Pending |
| CBOM-04 | Phase 2 | Complete |
| SCAN-03 | Phase 3 | Complete |
| SCAN-04 | Phase 3 | Complete |
| SCAN-05 | Phase 3 | Complete |
| SCAN-06 | Phase 3 | Complete |
| SCAN-07 | Phase 3 | Complete |
| LAB-01 | Phase 4 | Complete |
| LAB-02 | Phase 4 | Complete |
| LAB-03 | Phase 4 | Complete |
| LAB-04 | Phase 4 | Complete |
| LAB-05 | Phase 4 | Complete |
| LAB-06 | Phase 4 | Complete |
| UI-01 | Phase 10 | Pending |
| UI-02 | Phase 5 | Complete |
| UI-03 | Phase 10 | Pending |
| UI-04 | Phase 5 | Complete |
| DOC-01 | Phase 6 | Complete |
| DOC-02 | Phase 6 | Complete |
| DOC-03 | Phase 6 | Complete |
| DOC-04 | Phase 6 | Complete |
| DOC-05 | Phase 6 | Complete |
| DOC-06 | Phase 6 | Complete |
| DOC-07 | Phase 6 | Complete |
| BRAND-01 | Phase 7 | Complete |
| BRAND-02 | Phase 7 | Complete |
| BRAND-03 | Phase 7 | Complete |
| BRAND-04 | Phase 10 | Pending |

**Coverage:** 36/36 v1 requirements mapped. No orphans. 4 requirements reassigned to Phase 10 (gap closure).
