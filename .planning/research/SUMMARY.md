# Project Research Summary

**Project:** QU.I.R.K. — Quantum Infrastructure Readiness Kit
**Domain:** Enterprise cryptographic scanner — v4.6 incremental enterprise readiness additions
**Researched:** 2026-05-03
**Confidence:** HIGH

## Executive Summary

v4.6 Enterprise Readiness is an incremental hardening milestone, not a rewrite. The seven backlog items (BACK-76, -74, -79, -20, -75, -77, -65/66) are uniformly lower complexity than their backlog descriptions implied. The most important discovery across all four research areas is that the infrastructure already exists: `nmap_provider.py` is implemented end-to-end, TLS finding generation logic for expired/self-signed/weak-key certs already exists in both `risk_engine.py` and `routes/scan.py`, all three enrichment fields (`description`, `remediation`, `quantum_risk`) are already on `FindingItem`, and `_prompt_list()` already splits comma-separated input. The work is closing specific wiring gaps and building one new pure-Python module (`quirk/compliance/`). Net new pip dependencies for v4.6: zero.

The recommended approach is strictly sequential where dependencies exist: BACK-76 (install-day UX) first because ImportError crashes block all other testing; BACK-74 (TLS finding gaps) second because new finding types must exist before their remediation guidance (BACK-79) and compliance mappings (BACK-20) can be authored; BACK-79 in a dedicated phase because it shares the `FindingItem` model extension with BACK-20 and both touch the report renderer; BACK-75 and BACK-77 grouped in one phase because they are independent of the Finding model work and both touch `interactive.py`/`run_scan.py`; BACK-65+66 (docs) last. Six phases total.

The primary risks are subtle correctness traps. The most dangerous is the impacket/pyOpenSSL transitive conflict — moving impacket into a default or `[all]` meta-extra silently downgrades the `cryptography` library and breaks the TLS scanner. The second critical risk is the sslyze `verified_certificate_chain is None` ambiguity — this fires for internal enterprise CA certs as well as self-signed certs, producing incorrect client-deliverable findings. The third is stale PQC naming in `risk_engine.py` ("Kyber", "Dilithium", "when standards are adopted") — all factually wrong since FIPS 203/204/205 finalized August 2024. All three are containable with targeted fixes and chaos lab verification.

## Key Findings

### Recommended Stack

Zero new pip dependencies for all seven features. The only external addition is the `nmap` binary (already wired; needs operator documentation). All features use existing libraries (sslyze, cryptography, stdlib) or new internal modules with static Python dicts. No authoritative pip-installable library exists for FIPS 203/204/205-to-algorithm mapping or PCI-DSS/HIPAA control references — curated internal modules are the correct approach.

**Core technologies (all existing):**
- `sslyze` — all three BACK-74 data points (`cert_not_after`, `cert_pubkey_size`, `chain_verified`) already captured on `CryptoEndpoint`
- `quirk/discovery/nmap_provider.py` — subprocess nmap wrapper; fully implemented; only needs wizard wiring
- `quirk/engine/risk_engine.py` + `quirk/dashboard/api/routes/scan.py` — dual finding derivation paths; both need BACK-79 text enrichment
- `quirk/compliance/` (new module) — pure-Python static dicts; zero deps; finding-to-control-ID mapping
- `pyproject.toml` — add `[all]` meta-extra; impacket stays in `[identity]` only (pyOpenSSL conflict)

### Expected Features

**Must have (table stakes for v4.6):**
- BACK-76: Graceful ImportError degradation for kerberos/vault/db scanners; user-visible `missing_extra` advisory (not silent skip); `[all]` meta-extra
- BACK-74: Expired cert (CRITICAL), self-signed (HIGH), untrusted CA (MEDIUM), RSA-1024 weak key (HIGH) findings; chaos lab coverage
- BACK-79: `description` and `remediation` fields fully populated across all finding types; FIPS 203/204/205 migration guidance with NIST IR 8547 2030/2035 deadlines; stale "Kyber"/"Dilithium" terminology purged
- BACK-20: `quirk/compliance/` module; COMPLIANCE_MAP covering PCI-DSS 4.0.1, HIPAA 45 CFR §164.312, FIPS 140-3, NIST IR 8547; compliance summary section in HTML/PDF reports
- BACK-75: nmap discovery prompt in interactive wizard; graceful fallback when nmap binary absent; `--max-parallelism 100` in defaults
- BACK-77: Comma-separated and `@file`-based multi-target input; CIDR expansion via stdlib `ipaddress`; `--targets-file` CLI flag
- BACK-65+66: `docs/architecture.md` and `docs/operators-guide.md`; both Obsidian-synced

**Should have (v4.6 if time permits; else v4.6.x):**
- BACK-74: Near-expiry 30-day warning, SHA-1 signature finding, hostname mismatch finding
- BACK-79: `see_also` URLs, deprecation deadline callout per PQC finding
- BACK-20: FIPS 140-3 approved/not-approved on CBOM algorithm entries
- BACK-77: Exclude list, trailing-comma input validation
- BACK-66: `quirk doctor` pre-scan health check command

**Defer (v4.6.x or v4.7):**
- SOC 2 / ISO 27001 compliance mapping, nmap service fingerprinting (`-sV`), scan resume, OCSP/CRL revocation checking, Mermaid diagrams

### Architecture Approach

All seven features integrate into the existing two-path architecture without adding a third derivation path. The new `quirk/compliance/` module is the only net-new package directory. The data flow is unchanged: `run_scan.py` → scanner phases → `CryptoEndpoint[]` → risk engine → SQLite → reports + dashboard API. BACK-75 inserts a pre-scan discovery step; BACK-20 compliance lookup is called at report write time and optionally via a new `GET /api/compliance` endpoint.

**Files modified per feature:**
- BACK-76: `run_scan.py`, `pyproject.toml`
- BACK-74: `quirk/scanner/tls_scanner.py` only (risk engine and dashboard route finding generators are already correct)
- BACK-79: `quirk/engine/risk_engine.py`, `quirk/dashboard/api/routes/scan.py`
- BACK-20: create `quirk/compliance/`; modify `quirk/reports/technical.py`, `quirk/reports/executive.py`; optionally new `quirk/dashboard/api/routes/compliance.py`
- BACK-75: `quirk/interactive.py`, `run_scan.py`
- BACK-77: `quirk/interactive.py`, `run_scan.py`
- BACK-65+66: create `docs/architecture.md`, `docs/operators-guide.md`

### Critical Pitfalls

1. **impacket in meta-extra silently downgrades cryptography** — Keep impacket in `[identity]` only. BACK-76 fix is ImportError degradation, not extras promotion. Verify in clean venv.
2. **sslyze `verified_certificate_chain is None` conflated with self-signed** — Three cases: `issuer == subject` (self-signed), `chain_verified == False AND issuer != subject` (untrusted CA, MEDIUM finding), chain-failed + expired (suppress chain finding). Single `chain_verified == False` check produces false positives on private PKI clients.
3. **sslyze partial-success returns half-populated `CryptoEndpoint`** — When `CERTIFICATE_INFO` attempt status is ERROR, return `None` from `_scan_one_sslyze()` to trigger fallback, not a partially-populated endpoint with `cert_not_after = None`.
4. **Stale PQC terminology in existing remediation strings** — Audit `risk_engine.py` for "Kyber", "Dilithium", "when standards are adopted" before BACK-79. Add CI grep check. Use only: "ML-KEM (FIPS 203)", "ML-DSA (FIPS 204)", "SLH-DSA (FIPS 205)".
5. **Compliance map without version keys** — Every `COMPLIANCE_MAP` entry needs a `version` key. Current version is PCI-DSS 4.0.1 (June 2024), not 4.0. HIPAA uses 45 CFR citations, not numbered control IDs. Enforce with a unit test.
6. **Nmap socket exhaustion on macOS with large scopes** — Add `--max-parallelism 100` to `_default_nmap_args()` and a target count guard before invocation (warn if `len(targets) * len(ports) > 10_000`).

## Implications for Roadmap

Suggested phases: **6**

1. **Install-Day UX (BACK-76)** — unblocks all testing; wiring fix to three scanner phases
2. **TLS Finding Gaps (BACK-74)** — scanner correctness; `_scan_one_sslyze()` fix + chaos lab oracle
3. **Nmap + Multi-Target (BACK-75 + BACK-77)** — two independent features sharing file touches
4. **Rich Finding Context (BACK-79)** — text enrichment + PQC terminology audit/correction
5. **Compliance Mapping (BACK-20)** — new `quirk/compliance/` module; no external deps
6. **Enterprise Docs (BACK-65 + BACK-66)** — reflects completed feature set; Obsidian sync

Research flags: **none** — skip `/gsd-research-phase` for all phases; codebase inspection resolved all unknowns.

Confidence: **HIGH** overall. All critical implementation decisions are backed by direct codebase inspection or official NIST/PCI-DSS/HHS primary sources.

### Gaps to Address During Implementation

- **PCI-DSS 4.0.1 control numbering:** Cross-verify Req 4.2.1, 4.2.1.1, 6.3.3, 8.3.2 against official PCI SSC document before finalizing COMPLIANCE_MAP in Phase 5.
- **sslyze CERTIFICATE_INFO partial-success behavior:** Confirm as root cause at the start of Phase 2 before applying the fix.
- **Chaos lab cert coverage:** The existing `tls-weak` profile likely needs a new profile with expired/self-signed/RSA-1024 certs. Scope as a required task in Phase 2 per CLAUDE.md.
- **NIST SP 800-208 applicability:** Narrow scope (LMS/XMSS only; rare in enterprise TLS). Include in COMPLIANCE_MAP for DNSSEC findings only.
