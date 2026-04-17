# Milestone v4.2 — Identity Crypto: Project Summary

**Generated:** 2026-04-16
**Purpose:** Team onboarding and project review

---

## 1. Project Overview

**QU.I.R.K.** (Quantum Infrastructure Readiness Kit) is a consulting-grade cryptographic inventory scanner that discovers, classifies, and scores an organization's full cryptographic surface — TLS endpoints, SSH services, API/JWT tokens, cloud KMS configurations, containers, source code, and now **identity protocols** (Kerberos, SAML/OIDC, DNSSEC). It produces a CycloneDX CBOM, quantum-readiness score, and prioritized remediation roadmap.

**Core value:** Produce a complete, defensible cryptographic inventory with a CBOM deliverable and quantum-readiness score that a consultant can hand to a client in under two hours.

**v4.2 Milestone Goal:** Expand QU.I.R.K.'s cryptographic inventory surface to cover identity protocols — Kerberos, SAML/OIDC, and DNSSEC — each with a new scanner module, CBOM integration, chaos lab profile, and a dedicated Identity tab in the dashboard.

**Stack:** Python 3.11+ (FastAPI backend, scanner modules), React + shadcn/ui + Tailwind CSS (dashboard), SQLite (persistence).

**Milestone status:** 5 of 6 phases complete (Phases 17-21 shipped; Phase 22 gap closure executed but pending live integration verification).

---

## 2. Architecture & Technical Decisions

### Scanner Architecture

- **Decision:** Three new scanner modules (`dnssec_scanner.py`, `saml_scanner.py`, `kerberos_scanner.py`) following the established `scan_<type>_targets() -> list[CryptoEndpoint]` entry point pattern
  - **Why:** Consistent interface allows uniform CBOM pipeline integration, scoring, and dashboard rendering for any protocol
  - **Phase:** Established in v3.9, extended by Phases 18-20

- **Decision:** Import guard pattern (`DNSPYTHON_AVAILABLE`, `LXML_AVAILABLE`, `IMPACKET_AVAILABLE`) for all three identity scanner optional dependencies
  - **Why:** Identity scanners require heavyweight optional libraries (impacket, dnspython, lxml) that shouldn't be core dependencies; guards allow graceful degradation when not installed
  - **Phase:** Phase 17 (extras group), Phases 18-20 (guards)

### Identity Infrastructure

- **Decision:** Inspector-first idempotent SQLAlchemy migration for `kerberos_scan_json`, `saml_scan_json`, `dnssec_scan_json` columns (no Alembic, no `except OperationalError`)
  - **Why:** Consultant deployments may have existing v4.1 databases; `sa_inspect()` is idiomatic SQLAlchemy for column introspection and avoids exceptions for control flow
  - **Phase:** Phase 17

- **Decision:** `impacket` kept in `[identity]` optional extras group only — not in core dependencies
  - **Why:** pyOpenSSL transitive conflict risk with the core cryptography stack; isolation prevents dependency hell for users who only need TLS/SSH scanning
  - **Phase:** Phase 17

### DNSSEC Scanner

- **Decision:** Direct authoritative NS query with DO bit set (never use system resolver for DNSKEY/DS records)
  - **Why:** System resolvers strip the DO bit and DNSKEY records, making DNSSEC algorithm auditing impossible through the default resolution path
  - **Phase:** Phase 18

- **Decision:** RFC 8624/9905 3-tier algorithm severity classification (CRITICAL: SHA-1/MD5/DSA/GOST; HIGH: RSA-only; SAFE: ECDSA/EdDSA)
  - **Why:** Aligns with IANA DNSSEC algorithm deprecation guidance and post-quantum readiness hierarchy
  - **Phase:** Phase 18

- **Decision:** Synthetic finding types (NONE/NSEC/DS-MISMATCH/SHA1-DS) excluded from CBOM algorithm registration
  - **Why:** These represent posture findings (unsigned zone, zone enumeration exposure, broken chain), not cryptographic algorithms
  - **Phase:** Phase 18

### SAML/OIDC Scanner

- **Decision:** `defusedxml.lxml.fromstring()` for all XML parsing — XXE prevention is non-negotiable
  - **Why:** A security scanner with an XXE vulnerability would be an ironic and serious liability; defusedxml blocks entity expansion attacks
  - **Phase:** Phase 19

- **Decision:** lxml ElementPath subset (no XPath `not(@use)` predicate) — iterate and filter in Python
  - **Why:** lxml's ElementPath raises `invalid predicate` for `not()` function; Python-level filtering avoids the full XPath engine dependency
  - **Phase:** Phase 19

- **Decision:** OIDC endpoints share `saml_targets` list — no new config field
  - **Why:** Scanner auto-detects SAML vs OIDC by checking `.well-known` URL path and content-sniffing JSON vs XML; reduces consultant configuration burden
  - **Phase:** Phase 19

### Kerberos Scanner

- **Decision:** impacket `sendReceive()` + raw ASN.1 via `AS_REQ` for unauthenticated etype enumeration (not `getKerberosTGT()`)
  - **Why:** `getKerberosTGT()` is designed for authenticated flows and doesn't expose raw `KDC_ERR_PREAUTH_REQUIRED` error response parsing; raw AS-REQ mirrors impacket's own `GetNPUsers.py` internals
  - **Phase:** Phase 20

- **Decision:** TCP primary with UDP fallback for AS-REQ probe; per-etype CryptoEndpoint construction
  - **Why:** TCP is more reliable for modern KDCs; UDP fallback covers legacy deployments; one endpoint per etype enables per-finding severity in the CBOM and dashboard
  - **Phase:** Phase 20

- **Decision:** Anonymous LDAP bind on port 389 with graceful degradation — always returns a dict, never raises
  - **Why:** KERB-03 requires graceful degradation when LDAP is unreachable or auth required; scan must continue even if supplementary LDAP probe fails completely
  - **Phase:** Phase 20

### Identity Dashboard Surface

- **Decision:** Three identity evidence counters (`identity_weak_etype_count`, `saml_weak_signing_count`, `dnssec_weak_algo_count`) with scoring weight triples in `compute_readiness_score()`
  - **Why:** Identity weaknesses must reduce the quantum-readiness score; separate counters per protocol enable granular consultant reporting
  - **Phase:** Phase 21

- **Decision:** Protocol filter (`ALL/TLS/SSH/KERBEROS/SAML/DNSSEC`) on findings table alongside existing severity filter
  - **Why:** Consultants need to isolate identity findings from network findings; filter default is "ALL" for zero behavior change with existing users
  - **Phase:** Phase 21

### CBOM Pipeline

- **Decision:** Identity protocols (SAML, KERBEROS) skip Pass 2 (certificate) and Pass 3 (protocol) in CBOM builder — algorithm registration in Pass 1 is their only CBOM contribution
  - **Why:** Identity protocols don't carry X.509 cert metadata or represent TLS/SSH network protocols; `cert_pubkey_alg` for these protocols holds etype names or SHA-1 URI findings, not cert algorithms
  - **Phase:** Phase 22

---

## 3. Phases Delivered

| Phase | Name | Status | One-Liner |
|-------|------|--------|-----------|
| 17 | Identity Infrastructure | Complete | Inspector-first SQLAlchemy migration, ConnectorsCfg identity flags, pyproject.toml [identity] extras group |
| 18 | DNSSEC Scanner | Complete | Full DNSSEC scanner with RFC 8624/9905 classification, NSEC/DS-chain detection, CBOM integration, BIND9 chaos lab |
| 19 | SAML/OIDC Scanner | Complete | defusedxml XXE-safe SAML metadata parser, OIDC discovery, RSA-1024/SHA-1 detection, SimpleSAMLphp chaos lab |
| 20 | Kerberos Scanner | Complete | impacket AS-REQ TCP/UDP probe, 7-etype severity map, LDAP graceful degradation, Samba DC chaos lab |
| 21 | Identity Surface | Complete | Evidence counters in scoring, IdentityFinding API model, React Identity tab with protocol cards, findings protocol filter |
| 22 | v4.2 Gap Closure | Executed (human verification pending) | Fixed main_logger NameError, SAML/Kerberos CBOM Pass 2+3 skip lists, 7 new CBOM builder tests |

---

## 4. Requirements Coverage

### Infrastructure (INFRA)
- [x] **INFRA-01**: SQLite schema gains `kerberos_scan_json`, `saml_scan_json`, `dnssec_scan_json` nullable columns with idempotent migration guard
- [x] **INFRA-02**: `ConnectorsCfg` gains identity enable flags and target list fields wired to config.yaml
- [x] **INFRA-03**: pyproject.toml gains `[identity]` optional extras group with impacket, dnspython, lxml, defusedxml, signxml

### DNSSEC
- [x] **DNSSEC-01**: Scanner queries DNSKEY/DS via dnspython with DO bit against authoritative NS directly
- [x] **DNSSEC-02**: RFC 8624/9905 algorithm classification — RSASHA1 CRITICAL
- [x] **DNSSEC-03**: Unsigned zone detected and flagged HIGH
- [x] **DNSSEC-04**: Results in dnssec_scan_json with DNSSEC CryptoEndpoints; classifier and builder updated
- [x] **DNSSEC-05**: NSEC vs NSEC3 detection; NSEC flagged as zone-enumerable
- [x] **DNSSEC-06**: DS broken chain detection — mismatched key tags flagged HIGH
- [x] **DNSSEC-07**: BIND9 chaos lab with 4 zones (weak/safe/broken/unsigned) on port 15353

### SAML/OIDC
- [x] **SAML-01**: Metadata XML parsing for signing cert key type, size, expiry with SAML_NS
- [x] **SAML-02**: Encryption KeyDescriptor certs parsed separately from signing certs
- [x] **SAML-03**: OIDC discovery for id_token_signing_alg_values_supported
- [x] **SAML-04**: RSA < 2048 CRITICAL; SHA-1 URIs HIGH
- [x] **SAML-05**: Results in saml_scan_json with SAML CryptoEndpoints; classifier and builder updated
- [x] **SAML-06**: SimpleSAMLphp chaos lab with RSA-1024 weak signing cert

### Kerberos
- [x] **KERB-01**: Unauthenticated AS-REQ to port 88 with TCP/UDP, PA-ETYPE-INFO2 parsing
- [x] **KERB-02**: RC4-HMAC HIGH; DES CRITICAL; AES-256 quantum-safe
- [x] **KERB-03**: Anonymous LDAP bind with graceful degradation
- [x] **KERB-04**: Results in kerberos_scan_json with KERBEROS CryptoEndpoints; classifier and builder updated
- [x] **KERB-05**: Samba DC chaos lab with RC4-enabled QUIRK.LAB realm, 90s healthcheck

### Identity Surface (IDENT)
- [x] **IDENT-01**: Evidence counters (weak etype, weak signing, weak algo) feed readiness scoring
- [x] **IDENT-02**: FastAPI IdentityFinding model and identity_findings array in GET /api/scan/latest
- [x] **IDENT-03**: React Identity tab with per-protocol summary cards (Kerberos/SAML/DNSSEC)
- [x] **IDENT-04**: Findings table includes identity rows with protocol column filter

**Coverage: 25/25 requirements satisfied.**

---

## 5. Key Decisions Log

| ID | Decision | Phase | Rationale |
|----|----------|-------|-----------|
| D-17-01 | Inspector-first migration, not try/except OperationalError | 17 | Idiomatic SQLAlchemy; exceptions should not be control flow |
| D-17-02 | impacket in [identity] extras only | 17 | pyOpenSSL transitive conflict risk |
| D-17-03 | All ConnectorsCfg identity fields have safe defaults | 17 | v4.1 config.yaml loads without error |
| D-18-01 | DNSSEC_ALG_MAP in dnssec_scanner.py, not classifier.py | 18 | Scanner self-containment mirrors jwt_scanner pattern |
| D-18-02 | Direct authoritative NS query, never system resolver | 18 | System resolver strips DO bit and DNSKEY records |
| D-18-03 | Synthetic DNSSEC findings excluded from CBOM algo registration | 18 | Posture findings, not cryptographic algorithms |
| D-18-04 | Pre-signed zone files committed (not generated at build time) | 18 | dnssec-keygen unavailable locally; deterministic chaos lab |
| D-19-01 | defusedxml.lxml for XXE-safe XML parsing | 19 | Security scanner cannot have XXE vulnerability |
| D-19-02 | Python-level KeyDescriptor filtering, not XPath not(@use) | 19 | lxml ElementPath subset limitation |
| D-19-03 | OIDC shares saml_targets — no new config field | 19 | Auto-detection by URL pattern and content sniffing |
| D-20-01 | Raw AS-REQ via impacket, not getKerberosTGT() | 20 | Unauthenticated probe requires raw error response parsing |
| D-20-02 | TCP primary, UDP fallback for AS-REQ | 20 | Reliability for modern KDCs; legacy coverage |
| D-20-03 | _probe_ldap_anon always returns dict, never raises | 20 | KERB-03 graceful degradation requirement |
| D-20-04 | Per-etype CryptoEndpoint (one per etype per host) | 20 | Per-finding severity in CBOM and dashboard |
| D-21-01 | Three SCORE_WEIGHTS + identity_trust_impacts for identity | 21 | Granular per-protocol scoring impact |
| D-21-02 | Protocol filter default "ALL" on findings table | 21 | Zero behavior change for existing users |
| D-22-01 | SAML/KERBEROS in Pass 2+3 skip lists | 22 | Identity protocols don't carry cert/TLS metadata |

---

## 6. Tech Debt & Deferred Items

### Resolved in this milestone
- `main_logger` NameError in identity scanner blocks (fixed in Phase 22)
- CBOM spurious TLS/cert components for identity protocols (fixed in Phase 22)

### Known remaining items
- **defusedxml.lxml deprecation warning**: `defusedxml.lxml` is deprecated in newer defusedxml releases. Functional today but future work should migrate to `lxml.etree` with manual XXE mitigation (`resolve_entities=False`). (Info severity — Phase 19 verification)
- **datetime.utcnow() deprecation**: Used in test cert generation (`test_saml_scanner.py`). Deprecated in Python 3.12+. (Info severity)
- **Chaos lab integration tests require Docker**: Integration tests for all three identity scanners (`test_chaos_lab_integration`) are correctly skip-guarded but require Docker daemon and live services to execute. 3 integration tests remain skipped in CI.
- **Phase 22 live integration verification pending**: End-to-end scan with identity targets enabled and DB column population check requires live targets (DNS zone, SAML IdP, Kerberos KDC).

### Deferred to future milestones
- **KERB-ADV-01**: Per-account etype probing via authenticated LDAP `msDS-SupportedEncryptionTypes` (breaks agentless constraint; SaaS model)
- **SAML-ADV-01**: SAML assertion signature validation (requires SP context; SaaS model)
- **DNSSEC-ADV-01**: Post-quantum DNSSEC algorithm support — ML-DSA IANA numbers not yet registered
- **DNSSEC-ADV-02**: DNSKEY rollover monitoring (continuous; SaaS feature)

### Retrospective patterns (from v3.9 and v4.1)
- Schedule gap-closure phases explicitly at milestone end — defects deserve first-class planning
- Integration audit (`gsd:audit-milestone`) must run before `gsd:complete-milestone` — phase-level verification alone is insufficient
- Dead code deferred across two milestones becomes permanent — enforce deletion in the phase that discovers it

---

## 7. Getting Started

### Run the project
```bash
# Install core + identity scanner dependencies
pip install -e ".[identity]"

# Generate config template
quirk init

# Edit config.yaml — enable identity scanners:
#   connectors:
#     enable_dnssec: true
#     dnssec_targets: ["example.com"]
#     enable_saml: true
#     saml_targets: ["https://idp.example.com/metadata.xml"]
#     enable_kerberos: true
#     kerberos_targets: ["dc01.corp.local"]

# Run a scan
quirk --config config.yaml

# Start the dashboard
quirk serve
```

### Key directories
```
quirk/                          # Core Python package
  scanner/                      # Scanner modules
    dnssec_scanner.py           # DNSSEC (new in v4.2)
    saml_scanner.py             # SAML/OIDC (new in v4.2)
    kerberos_scanner.py         # Kerberos (new in v4.2)
    jwt_scanner.py              # JWT/API (v3.9)
    ssh_scanner.py              # SSH (v3.9)
  cbom/                         # CycloneDX CBOM pipeline
    builder.py                  # CBOM builder (identity branches added)
    classifier.py               # Algorithm classifier (identity entries added)
  intelligence/                 # Scoring and evidence
    evidence.py                 # Evidence summary (identity counters added)
    scoring.py                  # Readiness scoring (identity weights added)
  dashboard/                    # FastAPI backend
    api/routes/scan.py          # API routes (identity_findings added)
    api/schemas.py              # Pydantic models (IdentityFinding added)
    static/                     # Built React bundle
src/dashboard/                  # React source (dev)
  src/pages/identity.tsx        # Identity tab (new in v4.2)
  src/pages/findings.tsx        # Findings table (protocol filter added)
quantum-chaos-enterprise-lab/   # Docker-based validation lab
  bind9/                        # DNSSEC chaos lab (BIND9, 4 zones)
  simplesamlphp/                # SAML chaos lab (RSA-1024 cert)
  samba/                        # Kerberos chaos lab (Samba DC, QUIRK.LAB)
run_scan.py                     # Scan orchestrator (identity phases added)
```

### Tests
```bash
# Full test suite
python -m pytest tests/ -q

# Identity-specific tests
python -m pytest tests/test_identity_infra.py tests/test_dnssec_scanner.py tests/test_saml_scanner.py tests/test_kerberos_scanner.py tests/test_identity_surface.py tests/test_cbom_builder.py -v

# Chaos lab integration (requires Docker)
cd quantum-chaos-enterprise-lab
docker compose --profile dnssec --profile saml --profile kerberos up -d
QUIRK_INTEGRATION_TESTS=1 QUIRK_KERBEROS_INTEGRATION=1 python -m pytest tests/ -k integration -v
```

### Where to look first
- **Scan orchestration**: `run_scan.py` — the `main()` function shows the full scan pipeline including all identity scanner invocations
- **Scanner pattern**: `quirk/scanner/dnssec_scanner.py` — cleanest example of the identity scanner pattern (import guard, severity map, CryptoEndpoint construction)
- **CBOM integration**: `quirk/cbom/builder.py` — `build_cbom()` shows how identity endpoints flow through the 3-pass pipeline
- **Dashboard wiring**: `quirk/dashboard/api/routes/scan.py` — `_derive_identity_findings()` shows how scanner output becomes API response data
- **React Identity tab**: `src/dashboard/src/pages/identity.tsx` — per-protocol summary cards with findings table

---

## Stats

- **Timeline:** 2026-04-08 -> 2026-04-15 (8 days)
- **Phases:** 6 (5 complete + 1 pending human verification)
- **Plans:** 11 (10 complete + 1 executed pending verification)
- **Commits:** 76
- **Files changed:** 109 (+15,765 / -350)
- **Test suite:** 354 tests passing (+ 7 new CBOM builder tests in Phase 22)
- **Contributors:** Digs
