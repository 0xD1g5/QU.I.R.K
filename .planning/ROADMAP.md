# Roadmap: QU.I.R.K.

## Overview

QU.I.R.K. (Quantum Infrastructure Readiness Kit) starts from a solid v3.9 scanner core and
evolves into a consulting-grade cryptographic inventory platform. The journey: fix what exists
and deepen scanner accuracy (Phase 1), build the CBOM pipeline that is the product's key
differentiator (Phase 2), expand scanner coverage to every cryptographic surface a client
network exposes (Phase 3), validate every scanner against purpose-built chaos lab targets
(Phase 4), expose results through a polished web dashboard with PDF delivery (Phase 5),
document the tool well enough that a consultant with no prior exposure can hand a client
a defensible report within two hours of installation (Phase 6), then finish with professional
branding and packaging that makes it look like a product worth paying for (Phase 7).

## Phases

**Phase Numbering:**
- Integer phases (1-7): Planned milestone work
- Decimal phases (e.g., 2.1): Urgent insertions via `/gsd:insert-phase`

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Foundation Fixes** - Consolidate scoring, fix data bugs, rename to QU.I.R.K., upgrade SSH and TLS scanners
- [x] **Phase 2: CBOM Pipeline** - Integrate cyclonedx, map algorithms, enrich with NIST PQC classification, produce CBOM artifacts (completed 2026-03-29)
- [x] **Phase 3: Scanner Coverage** - Add JWT/API, container/binary, source code, and cloud connectors (AWS + Azure) (completed 2026-03-29)
- [x] **Phase 4: Chaos Lab Expansion** - Add jwt, registry, source, storage, ssh-weak, and ldaps lab profiles (completed 2026-03-30)
- [ ] **Phase 5: Web Dashboard** - FastAPI + React dashboard with findings viewer, CBOM viewer, and PDF report export
- [ ] **Phase 6: Documentation** - Getting Started, installation, configuration, connector guides, report and CBOM interpretation
- [ ] **Phase 7: Polish and Packaging** - Visual identity, CLI UX, professional report templates, pip-installable distribution

## Phase Details

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
**Plans:** 4 plans
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
**Plans**: TBD
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
**Plans**: TBD

### Phase 7: Polish and Packaging
**Goal**: QU.I.R.K. is installable in one command, presents a coherent visual identity, and produces reports that look like a commercial security product
**Depends on**: Phase 6
**Requirements**: BRAND-01, BRAND-02, BRAND-03, BRAND-04
**Success Criteria** (what must be TRUE):
  1. `pip install quirk` (or equivalent single command) produces a working installation on macOS and Linux
  2. All CLI output uses consistent formatting with rich progress indicators; `quirk --version` returns the current version
  3. HTML and PDF reports use the QU.I.R.K. visual identity (color palette, logo mark, report headers) — indistinguishable in quality from a commercial tool
  4. A new user who has never seen the tool can reach a completed, exportable scan from zero within 10 minutes of running the install command
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation Fixes | 0/4 | Planning complete | - |
| 2. CBOM Pipeline | 3/3 | Complete   | 2026-03-29 |
| 3. Scanner Coverage | 4/4 | Complete   | 2026-03-29 |
| 4. Chaos Lab Expansion | 5/5 | Complete   | 2026-03-30 |
| 5. Web Dashboard | 0/TBD | Not started | - |
| 6. Documentation | 0/TBD | Not started | - |
| 7. Polish and Packaging | 0/TBD | Not started | - |
