# Requirements — v4.6 Enterprise Readiness

**Milestone:** v4.6 Enterprise Readiness
**Started:** 2026-05-03
**Goal:** Make QUIRK credible and usable on real enterprise estates — fix install-day crashes, fill TLS finding gaps, enrich output with compliance context and PQC remediation guidance, and streamline the multi-target workflow.

---

## v4.6 Requirements

### Install-Day UX (BACK-76)

- [x] **INSTALL-01**: User can `pip install quirk` and run a TLS-only scan with no ImportError crashes from absent identity/db/vault/motion extras
- [x] **INSTALL-02**: User sees a `missing_extra` advisory finding in the report when a scanner phase is skipped due to an unavailable optional dependency (no silent skips)
- [x] **INSTALL-03**: User can install all optional extras at once via `pip install quirk[all]`
- [x] **INSTALL-04**: User receives clear install-time guidance pointing to the right extra when a scanner is unavailable (e.g. "install quirk[identity] for Kerberos scanning")

### TLS Finding Gaps (BACK-74)

- [ ] **TLS-FIND-01**: User receives a CRITICAL finding when QUIRK encounters an expired TLS certificate (`cert_not_after` in the past)
- [ ] **TLS-FIND-02**: User receives a HIGH finding when QUIRK encounters a self-signed TLS certificate (`issuer == subject` on the leaf cert)
- [ ] **TLS-FIND-03**: User receives a MEDIUM finding when QUIRK encounters a TLS certificate signed by an untrusted CA (chain verification fails AND issuer ≠ subject)
- [ ] **TLS-FIND-04**: User receives a HIGH finding when QUIRK encounters an RSA key smaller than 2048 bits in a TLS certificate
- [ ] **TLS-FIND-05**: User receives a HIGH finding when QUIRK encounters an EC key smaller than 256 bits in a TLS certificate
- [ ] **TLS-FIND-06**: TLS scanner falls back to the basic ssl_info path when sslyze CERTIFICATE_INFO returns ERROR (no half-populated CryptoEndpoint with `cert_not_after = None`)
- [ ] **TLS-FIND-07**: A new chaos lab profile (`tls-cert-defects`) serves expired, self-signed, untrusted-CA, and RSA-1024 certificates for end-to-end finding verification

### Rich Finding Context (BACK-79)

- [x] **CONTEXT-01**: Every finding emitted by QUIRK has a non-empty `description` field explaining the cryptographic risk in 1–3 sentences
- [x] **CONTEXT-02**: Every quantum-vulnerable finding includes a `remediation` field naming the appropriate FIPS 203/204/205 algorithm (ML-KEM/ML-DSA/SLH-DSA) — never legacy "Kyber"/"Dilithium" names
- [x] **CONTEXT-03**: Every quantum-vulnerable finding cites a NIST IR 8547 deprecation deadline (RSA/ECC deprecated 2030; disallowed 2035)
- [x] **CONTEXT-04**: A CI grep gate fails the build if any `risk_engine.py` or `routes/scan.py` string contains "Kyber", "Dilithium", or "when standards are adopted"

### Compliance Mapping (BACK-20)

- [x] **COMPLY-01**: A new `quirk/compliance/` Python module exposes a `COMPLIANCE_MAP` keyed by finding category, returning matching control references with `version` keys
- [x] **COMPLY-02**: Compliance mapping covers PCI-DSS 4.0.1 controls 4.2.1, 4.2.1.1, 6.3.3, 8.3.2 for relevant TLS/key-storage findings
- [x] **COMPLY-03**: Compliance mapping covers HIPAA 45 CFR §164.312(a)(2)(iv), §164.312(e)(1), §164.312(e)(2)(ii) for relevant findings
- [x] **COMPLY-04**: Compliance mapping covers FIPS 140-3 approved/not-approved algorithm classifications for findings touching algorithm choice
- [x] **COMPLY-05**: HTML and PDF reports include a "Compliance Summary" section listing finding-to-control references grouped by framework
- [x] **COMPLY-06**: A unit test enforces that every `COMPLIANCE_MAP` entry includes a `version` key
- [x] **COMPLY-07**: Each `COMPLIANCE_MAP` entry includes `last_verified` (ISO date) and `source_url` keys pointing to the authoritative regulator publication
- [x] **COMPLY-08**: A CI check warns when any entry's `last_verified` is older than 12 months (configurable threshold) so maintainers are alerted before staleness becomes a client-facing issue
- [x] **COMPLY-09**: A `quirk compliance status` CLI subcommand prints per-framework version, `last_verified` date, and `source_url` so operators can verify map freshness before client engagements

### Nmap Port Discovery (BACK-75)

- [x] **DISCOVER-01**: User is prompted in the interactive wizard to enable nmap-based port discovery for each target
- [x] **DISCOVER-02**: User receives a graceful warning (not a crash) when nmap discovery is requested but the `nmap` binary is not installed
- [x] **DISCOVER-03**: nmap discovery defaults include `--max-parallelism 100` to prevent macOS socket exhaustion on /24+ scopes
- [x] **DISCOVER-04**: User is warned before nmap invocation when target count × port count would exceed 10 000 probes

### Multi-Target Wizard (BACK-77)

- [x] **MULTI-01**: User can paste comma-separated targets (`host1,host2,host3`) into the interactive wizard and have all three scanned
- [x] **MULTI-02**: User can pass a file of targets via `@filepath` syntax in the wizard (one target per line, `#`-prefixed comments ignored)
- [x] **MULTI-03**: User can pass `--targets-file <path>` to the CLI for non-interactive bulk scans
- [x] **MULTI-04**: User can pass IPv4 CIDR notation (e.g. `192.0.2.0/24`) and have it expanded via stdlib `ipaddress`
- [x] **MULTI-05**: User receives a clear error (not a silent failure) when a target is malformed or the targets file does not exist

### Enterprise Documentation (BACK-65 + BACK-66)

- [ ] **DOCS-01**: `docs/architecture.md` documents the QUIRK system architecture: scanner phases, data flow, SQLite schema, dashboard, and CBOM pipeline
- [ ] **DOCS-02**: `docs/operators-guide.md` covers install, configuration, scanning workflow, troubleshooting, and a per-scanner reference for self-onboarding enterprise customers
- [ ] **DOCS-03**: Both new docs are synced to the Obsidian vault under `20_Dev-Work/QUIRK/Reference/` with the standard frontmatter
- [ ] **DOCS-04**: `docs/operators-guide.md` documents the compliance map maintenance process — quarterly review cadence, source URLs to monitor, and the upgrade path when a regulator publishes a revision (e.g. PCI-DSS 4.0.1 → 4.1)

---

## Future Requirements (deferred from v4.6)

These were considered for v4.6 but deferred to keep scope tight. Promote in v4.6.x or v4.7:

- **TLS-FIND-08**: Near-expiry warning (cert valid but expires within 30 days) — MEDIUM finding
- **TLS-FIND-09**: SHA-1 signature in TLS certificate detection
- **TLS-FIND-10**: Hostname mismatch (CN/SAN does not match scanned target) detection
- **CONTEXT-05**: `see_also` URL field per finding pointing to NIST/CSRC primary source
- **COMPLY-10**: FIPS 140-3 approved/not-approved annotations on every CycloneDX CBOM algorithm component
- **MULTI-06**: Exclude list (`!host` syntax) and trailing-comma input validation
- **DOCS-05**: `quirk doctor` pre-scan health check command (binary presence, network reachability, config validity)
- **COMPLY-11**: SOC 2 / ISO 27001 control mapping (out of v4.6 scope; bigger compliance research effort)

---

## Out of Scope (v4.6)

| Requirement | Reason |
|-------------|--------|
| LLM-generated remediation text | Breaks offline mode and is not auditable for client deliverables; static lookup tables only |
| Scan resume / checkpoint after partial failure | Significant orchestration change; defer to a later milestone focused on operational reliability |
| OCSP/CRL revocation checking | Network-heavy, slow, and orthogonal to PQC readiness; defer to dedicated TLS depth milestone |
| Service fingerprinting in nmap discovery (`-sV`) | Adds time and complexity for marginal benefit over port-only discovery |
| Mermaid diagrams in architecture doc | Markdown ascii-table sketches sufficient for v4.6; revisit if customers request |
| PEP 771 default-extras (when finalized) | Still a draft; the `[all]` meta-extra approach is the right v4.6 path |
| Promoting impacket out of `[identity]` extras | pyOpenSSL transitive conflict downgrades `cryptography` library and breaks TLS scanner |
| Compliance mapping as new dashboard page | Defer to v4.7 once compliance content stabilizes; v4.6 ships compliance via report-only |

---

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| INSTALL-01 | Phase 45 | Complete |
| INSTALL-02 | Phase 45 | Complete |
| INSTALL-03 | Phase 45 | Complete |
| INSTALL-04 | Phase 45 | Complete |
| TLS-FIND-01 | Phase 46 | Pending |
| TLS-FIND-02 | Phase 46 | Pending |
| TLS-FIND-03 | Phase 46 | Pending |
| TLS-FIND-04 | Phase 46 | Pending |
| TLS-FIND-05 | Phase 46 | Pending |
| TLS-FIND-06 | Phase 46 | Pending |
| TLS-FIND-07 | Phase 46 | Pending |
| DISCOVER-01 | Phase 47 | Complete |
| DISCOVER-02 | Phase 47 | Complete |
| DISCOVER-03 | Phase 47 | Complete |
| DISCOVER-04 | Phase 47 | Complete |
| MULTI-01 | Phase 47 | Complete |
| MULTI-02 | Phase 47 | Complete |
| MULTI-03 | Phase 47 | Complete |
| MULTI-04 | Phase 47 | Complete |
| MULTI-05 | Phase 47 | Complete |
| CONTEXT-01 | Phase 48 | Complete |
| CONTEXT-02 | Phase 48 | Complete |
| CONTEXT-03 | Phase 48 | Complete |
| CONTEXT-04 | Phase 48 | Complete |
| COMPLY-01 | Phase 49 | Complete |
| COMPLY-02 | Phase 49 | Complete |
| COMPLY-03 | Phase 49 | Complete |
| COMPLY-04 | Phase 49 | Complete |
| COMPLY-05 | Phase 49 | Complete (49-03) |
| COMPLY-06 | Phase 49 | Complete |
| COMPLY-07 | Phase 49 | Complete |
| COMPLY-08 | Phase 49 | Complete |
| COMPLY-09 | Phase 49 | Complete |
| DOCS-01 | Phase 50 | Pending |
| DOCS-02 | Phase 50 | Pending |
| DOCS-03 | Phase 50 | Pending |
| DOCS-04 | Phase 50 | Pending |
| CONTEXT-05 | Future (v4.7) | Deferred |
| COMPLY-10 | Future (v4.7) | Deferred |
| MULTI-06 | Future (v4.6.x) | Deferred |
| DOCS-05 | Future (v4.6.x) | Deferred |
| COMPLY-11 | Future (v4.7) | Deferred |

---

*Last updated: 2026-05-04 — Phase 47 closed; 5 deferred (v4.7 / v4.6.x) requirements added to traceability for lint coverage*
