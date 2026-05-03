# Feature Research: Enterprise Readiness — v4.6 Milestone

**Domain:** Consulting-grade cryptographic scanner — enterprise usability, compliance output, PQC remediation guidance
**Milestone:** v4.6 Enterprise Readiness
**Researched:** 2026-05-03
**Confidence:** HIGH (NIST official docs, PCI-DSS 4.0 official docs, HIPAA HHS guidance, sslyze docs, python-nmap docs, PEP 771, NIST IR 8547 verified; OpenVAS/Nessus format patterns verified against official sources)

---

## Context: Existing Architecture (Do Not Rebuild)

v4.5 ships:
- 13 scan surfaces across 6 pillars (TLS, SSH, API/JWT, identity, data-at-rest, data-in-motion)
- `CryptoEndpoint` SQLite model with `*_scan_json` blob columns per scanner
- `Finding` Pydantic model with `host`, `protocol`, `finding_type`, `severity`, `service_detail` fields — no `description`, `remediation`, or `compliance_refs` fields yet
- sslyze as primary TLS scanner — `CertificateDeploymentAnalysisResult` exposes `verified_certificate_chain`, `leaf_certificate_subject_matches_hostname`, plus trust store validation results
- `run_scan.py` with `_wrapped_phase` BaseException helper — all scanner phases share this pattern
- `quirk/risk/engine.py` generates findings from sslyze results — current TLS findings: cipher-related only; cert validity, expiry, key-size findings are absent
- Optional extras pattern established: `[identity]`, `[motion]`, `[cloud]`, `[db]`, `[vault]`, `[k8s]` — graceful ImportError degradation is already the pattern but not consistently applied
- Interactive wizard in `quirk/cli/interactive.py` — single-target flow, consulting defaults, 17-port list
- `quirk/reports/` HTML/PDF renderer — finding rows rendered without extended context fields

---

## Feature 1: Install-Day UX — Extras by Default, Graceful Degradation (BACK-76)

### What This Feature Does

Ships `identity` and `motion` extras as included-by-default in `pip install quirk`, and wraps
every optional-dependency import in a consistent try/except pattern so that a plain
`pip install quirk` (without extras) degrades gracefully instead of crashing 4 scanners with
`ModuleNotFoundError` at runtime.

### Why This Is Broken Today

The 4 affected scanners (`kerberos_scanner`, `saml_scanner`, `dnssec_scanner`, and one broker
scanner) import their optional libraries at module top-level. When the extra is not installed,
the import fails at Python import time before `_wrapped_phase` can catch it. The user sees a raw
`ModuleNotFoundError` and no findings from that surface — a silent data quality hole.

### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Graceful ImportError degradation for all optional-dependency scanners | Every enterprise tool must install without crashing; a scanner that errors on import is broken, not optional | LOW | Pattern: `try: import foo; HAS_FOO = True except ImportError: HAS_FOO = False`; check `HAS_FOO` before scanner runs; emit a structured warning finding instead of crash |
| User-visible "scanner unavailable" warning (not silent skip) | User must know a surface was skipped, not assume it was clean | LOW | Emit a single `Finding(severity="INFO", finding_type="SCANNER_UNAVAILABLE", service_detail="Install quirk[identity] to enable Kerberos/SAML/DNSSEC scanning")` per affected surface |
| `identity` and `motion` extras included in default install | These surfaces are standard consulting deliverables; opt-out is better than opt-in for billable surfaces | LOW | Move `[identity]` and `[motion]` dep sets into `[default]` meta-extra or include in core `dependencies`; PEP 771 "default extras" is still a draft as of 2025 — use `dependencies` inclusion or a `[default]` meta-extra convention instead |
| `pip install quirk` documentation updated to reflect new default | Documentation must match install behavior | LOW | Update `docs/installation.md` and `quirk init` welcome message |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Scanner health check at `quirk init` time | Proactive: show which scanners are available vs missing extras before first scan | LOW | `quirk init` runs `python -c "import impacket"` etc. and emits a table of surface availability |
| `pip install quirk[all]` umbrella extra | Power users and CI pipelines want one command | LOW | Meta-extra over all sub-extras; existing `[motion]` meta-extra is the pattern |

### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Bundle all optional deps into core | "Simplify install" | impacket has known transitive conflicts with pyOpenSSL; pulling into core breaks other users | Keep extras structure; fix defaults by including the safe ones |
| Silent skip with no warning | "Clean output" | Creates false confidence — user thinks all surfaces were scanned | Always emit INFO finding when a surface is skipped due to missing dependency |

### Dependency Notes

- This is the **first phase** of v4.6 — it unblocks all subsequent testing because a clean install is required before validating scanner output
- Changes are additive to `pyproject.toml` and import guards; no new libraries

---

## Feature 2: TLS Finding Gaps (BACK-74)

### What This Feature Does

Adds three missing finding types to the TLS risk engine: expired certificates, self-signed
certificates (untrusted CA), and weak RSA key sizes (RSA-1024 and RSA-512). These are standard
findings in every TLS assessment tool and are required for NIST SP 800-52r2 and PCI-DSS 4.0
compliance reporting.

### Why These Are Currently Missing

sslyze's `CertificateDeploymentAnalysisResult` provides all three signals already:
- **Expired:** `received_certificate_chain[0].not_valid_after` vs `datetime.now()`
- **Self-signed:** `verified_certificate_chain` is `None` when trust validation fails; sslyze trust store validation result provides `was_validation_successful = False` with reason
- **Weak key:** `leaf_certificate_public_key.key_size` — RSA keys below 2048 bits are deprecated per NIST SP 800-131A and NIST IR 8547 (which deprecates all RSA by 2030; RSA-1024 was never NIST-recommended)

The sslyze data is available in `tls_capabilities_json`. The risk engine (`quirk/risk/engine.py`)
does not read these fields when generating findings.

### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Expired certificate finding (CRITICAL severity) | Expired certs break TLS handshake; PCI-DSS 4.0 §6.3.3 requires cert validity tracking; every TLS scanner flags this | LOW | Check `not_valid_after < datetime.utcnow()`; finding: `TLS-EXPIRED-CERT`; severity: CRITICAL |
| Near-expiry warning (HIGH severity, configurable threshold) | Proactive finding; standard in Qualys, Tenable, sslyze CLI — 30/60/90 day thresholds | LOW | Default threshold 30 days; configurable in `[scan]` config; finding: `TLS-CERT-EXPIRING-SOON`; severity: HIGH |
| Self-signed / untrusted CA finding (HIGH severity) | Self-signed certs bypass PKI chain of trust; PCI-DSS 4.0 requires trusted CA; NIST SP 1800-16 certificate management guidance explicitly flags self-signed | LOW | sslyze `was_validation_successful=False` + reason `SELF_SIGNED`; finding: `TLS-SELF-SIGNED-CERT`; severity: HIGH |
| RSA-1024 weak key finding (HIGH severity) | RSA-1024 provides ~80 bits of security — below NIST SP 800-131A minimum of 112 bits since 2014; never compliant | LOW | `leaf_certificate_public_key.key_size < 2048` for RSA; finding: `TLS-WEAK-KEY-RSA1024`; severity: HIGH |
| RSA-512 weak key finding (CRITICAL severity) | RSA-512 is factored trivially; represents a fundamental security failure | LOW | `key_size <= 512` for RSA; severity: CRITICAL |
| EC key size check (P-160, P-192 < NIST minimum) | Weak ECDSA curves below P-256 are deprecated | LOW | `key_size < 256` for EC keys; finding: `TLS-WEAK-KEY-EC`; severity: HIGH |
| Hostname mismatch finding (HIGH severity) | Cert CN/SAN does not match scanned hostname; breaks TLS guarantees | LOW | sslyze `leaf_certificate_subject_matches_hostname=False`; finding: `TLS-HOSTNAME-MISMATCH` |
| Chaos lab coverage for all new finding types | Regression prevention — chaos lab must exercise all new TLS findings | MEDIUM | Add a chaos lab profile or extend existing `tls-weak` profile with expired, self-signed, and RSA-1024 certs; update `expected_results_v4.md` oracle |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Certificate chain completeness check | Incomplete chain (missing intermediate) breaks some clients; common enterprise misconfiguration | LOW | sslyze `received_certificate_chain_has_anchor_in_it`, `received_certificate_chain` chain length vs `verified_certificate_chain`; finding: `TLS-INCOMPLETE-CHAIN` |
| SHA-1 signature algorithm finding | SHA-1 signatures are broken; deprecated by all major browsers; still seen on legacy internal CAs | LOW | Check `signature_hash_algorithm.name == 'sha1'` on leaf cert; finding: `TLS-SHA1-SIGNATURE`; severity: HIGH |
| Wildcard certificate detection (informational) | Wildcards increase blast radius of compromise; consultants note them | LOW | SAN contains `*.domain`; finding: `TLS-WILDCARD-CERT`; severity: INFO — informational, not a failure |

### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Certificate revocation (OCSP/CRL) check | Thorough PKI hygiene | OCSP responders in enterprise are often unreachable from scanner host; high false-negative rate; adds latency | Note as manual verification item in remediation guidance |
| CT log cross-checking | Transparency verification | Requires external CT log API calls; breaks offline mode | Out of scope for agentless offline scanner |

### Dependency Notes

- sslyze is already in the stack and provides all needed data fields — this is pure risk engine logic, no new dependencies
- All 3 finding types feed into the existing TLS subscore via `evidence.py` counters; new counters needed: `tls_expired_count`, `tls_self_signed_count`, `tls_weak_key_count`
- Chaos lab update is mandatory per CLAUDE.md: any new expected finding type requires oracle update

---

## Feature 3: Rich Finding Context — Per-Finding Risk Explanation and PQC Remediation (BACK-79)

### What This Feature Does

Adds three new fields to every finding in scan output, reports, and the dashboard API:
`risk_explanation` (why this finding matters in plain language), `severity_rationale` (why
this severity was assigned), and `remediation_path` (specific actionable steps, including
FIPS 203/204/205 PQC migration path where applicable).

### What Enterprise Users Expect

Enterprise security scanners universally provide remediation context. The Nessus `.nessus`
format has had `description`, `synopsis`, `solution`, and `see_also` fields since v2.
Qualys and Tenable both provide `remediation`, `consequence`, and `cvss_rationale` on findings.
SIEM integrations consume this context for automated triage.

The QUIRK finding model currently provides only `finding_type`, `severity`, `host`, and
`service_detail`. A consultant receiving a finding `TLS-WEAK-CIPHER: HIGH` with no explanation
must look up the cipher in external references before writing the client deliverable. This doubles
consultant time per finding.

### Remediation Path per Finding Category (NIST-Sourced, HIGH Confidence)

**Key establishment (RSA, ECDH, DH — quantum-vulnerable):**
Replace with ML-KEM (FIPS 203). Minimum parameter set: ML-KEM-768 for general use, ML-KEM-1024
for national security systems (CNSA 2.0). Deadline: NIST IR 8547 deprecates RSA-2048 by 2030,
disallows all RSA/ECC by 2035.

**Digital signatures (RSA-PKCS1, ECDSA — quantum-vulnerable):**
Replace with ML-DSA (FIPS 204, primary choice) or SLH-DSA (FIPS 205, conservative hash-based
fallback when lattice assumptions are a concern). ML-DSA-65 for general enterprise use,
ML-DSA-87 for national security. SLH-DSA relies only on hash function security — use where
algorithm diversity is required.

**Symmetric encryption (AES-128+ — quantum-adequate):**
No replacement needed. AES-128 provides ~64 bits of post-quantum security (Grover's algorithm
halves effective key length). AES-256 provides ~128 bits — sufficient. No migration required
before 2035.

**Hash functions (SHA-256+):**
SHA-256 provides ~128 bits of post-quantum security. SHA-384/SHA-512 preferred for signatures.
SHA-1 and MD5: replace immediately (classical weakness, not quantum).

**TLS protocol version:**
TLS 1.3 is quantum-adequate for symmetric components; key exchange still needs PQC hybrid
(X25519Kyber768 or MLKEM768X25519 are IETF-standardizing). TLS 1.2 acceptable with ECDHE
key exchange until 2030. TLS 1.0/1.1: replace immediately.

**Kerberos (RC4/DES enctypes):**
Replace RC4-HMAC and DES with AES-256-CTS-HMAC-SHA1-96 (RFC 8009) as bridge, then migrate to
AES-256-based Kerberos with PQC key wrap when RFC is finalized. RC4: CRITICAL finding.

**DNSSEC (RSASHA1, DSA):**
Migrate to ECDSAP256SHA256 (RFC 8624 — MUST implement) or ECDSAP384SHA384 now. Future:
watch IETF DNSOP working group for ML-DSA DNSSEC algorithm.

### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| `risk_explanation` field on Finding — 1-2 sentences why this finding matters | Every enterprise scanner provides this; without it consultants must look up implications manually | MEDIUM | Static lookup table keyed on `finding_type`; ~60 entry coverage for all current finding types; no LLM, no dynamic generation |
| `severity_rationale` field on Finding — why this severity (not one above/below) | Compliance auditors challenge severity assignments; rationale makes the report defensible | LOW | Append to static lookup; single sentence per finding type — e.g. "CRITICAL: RSA-512 keys can be factored with commodity hardware in hours." |
| `remediation_path` field on Finding — 1-3 actionable steps | Core consultant time-save; the entire point of a readiness scanner is to drive remediation | MEDIUM | Static lookup keyed on `finding_type`; for PQC findings, cite FIPS 203/204/205 and NIST IR 8547 deadline explicitly |
| PQC migration path for all quantum-vulnerable finding types | FIPS 203/204/205 are finalized (August 2024); including specific algorithm names is now authoritative | MEDIUM | Minimum: for every RSA/ECDSA/DH finding, state "Migrate to ML-KEM (FIPS 203) for key establishment; ML-DSA (FIPS 204) for signatures. Target: 2030 deprecation deadline per NIST IR 8547." |
| Finding context visible in HTML/PDF reports | Consultants hand reports to clients; context must appear in the deliverable | MEDIUM | Extend report renderer to include `risk_explanation` + `remediation_path` as a collapsed/expandable section per finding row |
| Finding context in `/api/scan/latest` JSON response | Dashboard and SIEM integration consumers expect these fields | LOW | Extend `Finding` Pydantic model to include new fields; old scans that lack context gracefully return empty strings |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| FIPS deadline callout per finding ("deprecated by 2030 per NIST IR 8547") | Regulatory urgency drives client prioritization; specific deadline is more compelling than "quantum-vulnerable" | LOW | Add `deprecation_deadline` field for NIST IR 8547 applicable findings: RSA-2048 → 2030, all RSA/ECC → 2035 |
| Algorithm-specific migration complexity rating (LOW/MEDIUM/HIGH) | Consultants need to scope remediation effort; replacing a TLS cipher is LOW complexity, replacing an internal CA is HIGH | LOW | Static field on remediation lookup; helps with roadmap sizing |
| `see_also` URLs field — link to authoritative standard | Auditors want to see primary source citations in reports | LOW | 1-2 URLs per finding type pointing to NIST.gov, PCI-DSS.org, or HHS.gov — standard practice in Nessus format |

### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| LLM-generated remediation text per finding | "Dynamic, contextual guidance" | Requires network call; breaks offline mode; LLM accuracy not auditable; regulatory reports require reproducible output | Static lookup table is 100% reproducible, auditable, offline-capable, and fast |
| Per-client customizable remediation text | "Tailored guidance" | Configuration complexity; maintenance burden; consultants already customize in their deliverable template | Provide clear, generic guidance; consultant adds client-specific context in their report |

### Dependency Notes

- No new pip dependencies — static lookup dict in `quirk/risk/remediation.py` (new file)
- `Finding` Pydantic model must gain 3 new optional fields (backward-compatible: default empty string)
- Report renderer changes affect both HTML and PDF paths
- This feature makes **BACK-20 (compliance mapping)** easier — remediation context and compliance controls are both attributes of the same finding

---

## Feature 4: Compliance Mapping (BACK-20)

### What This Feature Does

Maps each finding to the specific control IDs in FIPS 140-3, NIST SP 800-208, PCI-DSS 4.0,
and HIPAA/HITECH technical safeguards. Produces a compliance summary section in reports showing
which controls are satisfied, which have gaps, and a per-framework compliance posture table.

### What Good Compliance Mapping Looks Like (Enterprise Standard)

Enterprise vulnerability scanners (Nessus, Qualys, OpenVAS) all map findings to at least:
- CVE IDs (not applicable here — no CVEs)
- CIS Controls or NIST 800-53 control IDs
- PCI-DSS requirement numbers
- HIPAA regulation sections

A defensible compliance mapping for cryptographic findings needs:
1. **Finding → control reference** (one-to-many; a single finding may satisfy or violate multiple controls)
2. **Control coverage table** in the report: control ID, description, status (PASS/FAIL/NOT-TESTED), finding references
3. **Framework-level summary**: "PCI-DSS 4.0 — 8 of 12 assessed controls pass; 4 gaps identified"
4. **Framework filter**: only show controls relevant to frameworks the client actually cares about

### Key Framework Coverage (Verified Against Primary Sources)

**PCI-DSS 4.0 (HIGH confidence — verified against official PCI SCC documentation):**
- Req 4.2.1: TLS 1.2+ required for CHD transmission; TLS 1.0/1.1/SSL prohibited
- Req 4.2.1.1: Inventory of trusted keys and certs maintained (maps to cert inventory)
- Req 6.3.3: All software components protected against known vulnerabilities — weak ciphers qualify
- Req 8.3.2: Strong cryptography for authentication credentials at rest
- Req 8.6.1: System/application accounts managed with strong crypto
- Cipher suites: AES-128+, ECDHE, SHA-256+; RC4/DES/3DES prohibited; expired/self-signed certs = violation

**HIPAA Technical Safeguards (MEDIUM confidence — HHS.gov verified; HIPAA is "addressable" not prescriptive on algorithms):**
- 45 CFR §164.312(a)(2)(iv): Encryption/decryption of ePHI (data at rest) — addressable
- 45 CFR §164.312(e)(2)(ii): Encryption of ePHI in transit — addressable
- NIST SP 800-111 (data at rest): AES-128+ required when encryption is implemented
- NIST SP 800-52r2 (TLS): TLS 1.2+ for ePHI transmission; cipher suite restrictions align with PCI-DSS
- Note: HIPAA does not mandate encryption but HHS states noncompliance with addressable specs requires documented alternative; "encrypt with a deprecated algorithm" is not an acceptable alternative

**NIST SP 800-208 (HIGH confidence — verified against NIST CSRC):**
- Applies to stateful hash-based signatures (LMS, HSS, XMSS, XMSSMT)
- Relevant to DNSSEC and code signing findings only
- Findings: use of RSASHA1 in DNSSEC = violation; ECDSAP256SHA256 = compliant

**FIPS 140-3 (HIGH confidence — verified against NIST CSRC):**
- Not a finding-level control in the traditional sense — FIPS 140-3 validates modules, not deployments
- Correct mapping: "This algorithm uses a FIPS 140-3 approved algorithm: AES-256, SHA-256, ECDSA P-256" or "NOT APPROVED: RC4, MD5, DES, RSA-1024"
- CMVP approved algorithm list is the authoritative source
- PQC: ML-KEM, ML-DSA, SLH-DSA are now FIPS 140-3 approved (added to CAVP in 2024)

**NIST IR 8547 / CNSA 2.0 (HIGH confidence):**
- RSA-2048 and ECC P-256: deprecated by 2030 (no new systems)
- All RSA/ECC: disallowed by 2035
- ML-KEM-768 (general) / ML-KEM-1024 (NSS): required for key establishment
- ML-DSA-65 (general) / ML-DSA-87 (NSS): required for signatures
- These are federal mandates; any federal contractor facing audit will need this mapping

### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Finding → control ID mapping (static lookup) | Every compliance-oriented scanner provides control references; without this, compliance officers cannot map to their audit framework | MEDIUM | Dict keyed on `finding_type` → list of `(framework, control_id, description)` tuples; ~60 finding types × 3-4 frameworks |
| Per-framework compliance summary in HTML/PDF report | Compliance officers present this section to auditors; it is the core deliverable for regulated industries | HIGH | New report section: framework name, total controls assessed, pass/fail/not-tested counts, gap list; conditional on which frameworks user enables in config |
| `compliance_refs` field on Finding in API/JSON output | SIEM and GRC tool integrations consume finding data programmatically; control IDs are how they cross-reference | LOW | Extend `Finding` Pydantic model: `compliance_refs: list[ComplianceRef]` where `ComplianceRef` has `framework`, `control_id`, `control_description` |
| Framework selection in config | Client A cares about PCI-DSS; Client B cares about HIPAA; show only relevant frameworks | LOW | `[compliance] frameworks = ["pci-dss-4", "hipaa", "fips-140-3"]` in `quirk.toml`; default: all frameworks |
| "FIPS 140-3 approved / NOT approved" classification per algorithm in CBOM | CBOM already classifies quantum-safety; add FIPS approved status as a second classification dimension | MEDIUM | Extend `classify_algorithm()` to return `fips_140_3_approved: bool`; known approved list: AES, SHA-2, SHA-3, ECDSA P-256/P-384/P-521, RSA-2048+, ML-KEM, ML-DSA, SLH-DSA |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| SOC 2 Type II crypto controls mapping | SOC 2 CC6.1 and CC6.7 cover encryption of data in transit/rest; growing demand for SOC 2 evidence packages | MEDIUM | CC6.1: logical access controls including encryption; CC6.7: transmission security; map TLS and DAR findings |
| ISO 27001:2022 Annex A.8.24 mapping | ISO 27001 updated in 2022; A.8.24 is "use of cryptography"; global standard for enterprise customers outside US | MEDIUM | A.8.24 requires crypto policy, key management lifecycle, algorithm selection — map directly to QUIRK finding types |
| Compliance posture trend — did compliance score improve between scans | Show compliance improvement over time for audit evidence | MEDIUM | Requires trend analysis (already built in v4.3); add per-framework pass rate to ScanSession snapshot |

### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Automated compliance attestation / certification | "Prove we're compliant" | No scanner can attest compliance — only human auditor can; claiming otherwise creates legal liability | Clearly label output as "compliance gap assessment" not "certification"; include disclaimer in reports |
| FedRAMP compliance mapping | Government clients want this | FedRAMP has hundreds of controls; crypto is a small subset; full FedRAMP coverage is a separate product surface | Note NIST SP 800-53 control IDs which FedRAMP inherits — this provides partial coverage |
| Real-time compliance dashboard with live audit trail | "Continuous compliance" | Requires persistent backend, auth, multi-tenant data — SaaS milestone scope | CLI + periodic scan + PDF report is the correct v1 compliance model |

### Dependency Notes

- New file `quirk/compliance/mapper.py` — pure Python dict lookups, no new pip dependencies
- Extends `Finding` Pydantic model (same pattern as BACK-79 `remediation_path`)
- Report renderer needs a new "Compliance Mapping" section — significant but contained
- BACK-79 (remediation context) and BACK-20 (compliance mapping) should ship in the same phase — they share the Finding model extension and static lookup infrastructure

---

## Feature 5: Nmap Port Discovery (BACK-75)

### What This Feature Does

Adds an optional pre-scan phase that probes each target host for open ports before running
the QUIRK scanner suite. Replaces the hardcoded 17-port consulting default list with discovered
open ports. This is critical for real enterprise estates where services run on non-standard ports.

### Pre-Scan vs In-Scan vs Post-Scan

Enterprise security tools use three models:
- **Pre-scan discovery** (correct for QUIRK): Run port scan before any application-layer scanner; feed results into scanner as target list. Tools like Nessus and Qualys do this — port discovery is the first phase of every scan policy.
- **In-scan discovery**: Port scan during application scanning in parallel. Adds complexity, harder to reason about.
- **Post-scan discovery**: Not used — defeats the purpose (you've already missed services on unknown ports).

QUIRK should use **pre-scan discovery**: at the start of `run_scan.py`, if nmap is available and discovery is enabled, probe each target for open ports, build a `{host: [port_list]}` dict, and pass it to each scanner phase as the target port list instead of the hardcoded defaults.

### Root vs Non-Root Operation

This is the key enterprise constraint. SYN scan (`-sS`) requires raw packet privileges (root/sudo
on Unix, administrator on Windows). TCP connect scan (`-sT`) requires no elevated privileges —
it uses the OS `connect()` system call. The tradeoffs:

| Scan Type | Root Required | Speed | Stealth | Recommendation |
|-----------|---------------|-------|---------|----------------|
| SYN scan (`-sS`) | YES | Fast | High | Use when available (sudo/root context) |
| TCP connect (`-sT`) | NO | Slower | Low (full handshake) | Default for non-root |

**Enterprise recommendation:** Default to TCP connect scan (no root); detect if running as root
and upgrade to SYN scan automatically. Consultants running from their laptop will not have root;
enterprise environments where QUIRK runs in a privileged scan container can benefit from SYN.

`python-nmap` wraps nmap correctly for both modes. It handles the privilege check at the nmap
layer, not the Python layer.

### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Optional pre-scan port discovery using nmap subprocess via `python-nmap` | Enterprise estates don't use standard ports; hardcoded defaults miss services on non-standard ports | MEDIUM | `python-nmap` (`nmap` PyPI package) wraps nmap; `nmap.PortScanner().scan(hosts, ports='1-65535', arguments='-sT --open')` for TCP connect; requires `nmap` binary installed on scanner host |
| TCP connect scan as non-root default (`-sT`) | Consultants run from their laptop; cannot assume root/sudo | LOW | Detect `os.geteuid() == 0` and set `-sS` vs `-sT` automatically |
| Discovery scope config: port range, timeout, parallelism | Enterprise estates vary; some allow only specific port ranges | LOW | Config section `[discovery]`: `enabled = true`, `port_range = "1-65535"`, `timeout_sec = 300`, `max_parallel_hosts = 10` |
| Graceful degradation when nmap binary not found | `nmap` is not installed by default; scanner must fall back to consulting defaults | LOW | Try `nmap.PortScanner()` on import; catch `nmap.PortScannerError`; fall back to hardcoded port list with INFO log "nmap not found, using consulting defaults" |
| `python-nmap` in `[discovery]` extras group | Keep nmap dependency optional — many users don't need port discovery | LOW | `pip install quirk[discovery]`; `python-nmap` is the only new dependency |
| Discovery results cached and logged | Users need audit trail of what ports were found on which hosts | LOW | Write discovery results to scan output JSON; log per-host open ports at INFO level |
| `-Pn` flag when hosts don't respond to ICMP ping | Enterprise firewalls commonly block ICMP; scanner must not skip hosts silently | LOW | Add `-Pn` to nmap arguments by default; most enterprise scanners do this |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Service fingerprinting via nmap `-sV` | Detect service on non-standard port (e.g., SSH on port 2222 vs 22) — scanner routes to correct scanner module | MEDIUM | `-sV` adds service version detection; `nmap_result[host]['tcp'][port]['name']` gives service hint; feed into scanner routing logic |
| Target range expansion: CIDR input in discovery phase | Discovery can scan a /24 at once; individual targets derived from open hosts | MEDIUM | nmap handles CIDR natively; this is the setup for BACK-77 multi-target |
| Scan pacing / rate limiting for IDS-friendly scanning | Enterprise IDS/IPS will flag aggressive port scans | LOW | `--scan-delay 100ms` or `--max-rate 100` as configurable options in `[discovery]` |

### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| UDP port scanning | "Complete" coverage | UDP scanning is extremely slow, unreliable, and creates false negatives on filtered ports; requires root | Focus on TCP which covers all crypto services; note UDP DTLS as out of scope |
| OS fingerprinting via nmap `-O` | Network inventory value | Requires root; not relevant to crypto posture | Out of scope |
| Use Masscan for speed | "Faster than nmap" | Masscan requires root always; different output format; adds another external binary dependency | python-nmap with nmap is sufficient and one binary to manage |

### Dependency Notes

- `python-nmap` pip package wraps the `nmap` binary (external system dependency)
- nmap binary is **not** pip-installable — installation instructions must cover system package (`brew install nmap`, `apt install nmap`, etc.)
- This is the only v4.6 feature with a non-pip system dependency — documentation investment required
- Pre-scan phase must complete before any scanner phase starts; `run_scan.py` orchestration change needed

---

## Feature 6: Multi-Target Wizard (BACK-77)

### What This Feature Does

Fixes the interactive wizard and CLI to accept multiple targets via comma-separated input,
a newline-delimited hosts file, CIDR notation, and IP ranges. Currently the interactive
wizard accepts only a single hostname/IP string. Enterprise customers scan 50-500 hosts in
a single assessment.

### What Enterprise Scanners Accept (HIGH confidence — Greenbone/OpenVAS docs verified, Nessus format verified)

All major enterprise vulnerability scanners support:
1. **Single host**: `192.168.1.1` or `host.example.com`
2. **Comma-separated**: `host1,host2,host3` or `192.168.1.1,192.168.1.2`
3. **CIDR notation**: `192.168.1.0/24` (Nessus, OpenVAS, nmap all handle this natively)
4. **IP ranges**: `192.168.1.1-254` (nmap `--exclude-host` style)
5. **Hosts file**: `@/path/to/hosts.txt` (nmap convention) or `--targets-file hosts.txt`
6. **Mixed**: One target per line in a file, which may itself be CIDR or individual IPs

QUIRK should support all 5 formats. The common enterprise workflow for a 200-host assessment is
a `hosts.txt` file derived from a network inventory (CMDB export or nmap discovery output).

### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Comma-separated targets in interactive wizard and `--targets` CLI flag | Most immediate fix; power-users paste comma-delimited target lists from spreadsheets | LOW | Parse `targets_str.split(',')` and strip whitespace; existing wizard prompt becomes multi-value |
| Hosts file input (`--targets-file /path/to/hosts.txt`) | Standard enterprise workflow for large target sets; each line = one host, IP, or CIDR | LOW | `argparse` adds `--targets-file`; read file, parse lines, skip `#` comments and blank lines |
| CIDR expansion (e.g., `192.168.1.0/24` → host list) | Network admins think in subnets; CIDR input is expected | LOW | Python stdlib `ipaddress.ip_network('192.168.1.0/24').hosts()` — no new dependency |
| IP range expansion (e.g., `192.168.1.1-254`) | Common nmap-style range notation | LOW | Parse `start-end` pattern; expand with `ipaddress`; limited to /24-scale ranges |
| Target deduplication before scan | Prevent scanning same host twice when target lists overlap | LOW | `list(dict.fromkeys(targets))` preserves order while deduplicating |
| Progress indication for multi-host scans | 50-host scan takes minutes; user needs to see progress | LOW | Existing `tqdm` or print progress; `Scanning host N of M: {host}` |
| `--max-targets` safety limit with override flag | Prevent accidental 65000-host CIDR expansion | LOW | Default limit 500 hosts; `--max-targets 0` for unlimited; warn + confirm in interactive mode |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Mixed format file (hosts file with CIDR lines and individual IPs) | Realistic enterprise target files contain both | LOW | Line-by-line: try CIDR parse first, then range, then single host |
| Exclude list (`--exclude host1,host2` or `--exclude-file`) | Enterprise scans need to skip honeypot hosts, known-dead IPs | LOW | Standard nmap-style exclusion; subtract from expanded list |
| Scan resume from partial results | Large scans interrupted midway; resume from last completed host | HIGH | Requires scan state persistence per host; significant complexity; defer to v4.7 |

### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Domain-to-IP resolution expansion | "Scan all IPs for a domain" | DNS can return many IPs; changes target semantics unexpectedly; creates scan scope creep | Scan the hostname as provided; let the TLS scanner handle multi-cert virtual hosting |
| Automatic network topology discovery | "Find all hosts on the network" | Network enumeration without explicit scope is out of scope for an agentless consulting tool; legal risk | Use BACK-75 (nmap discovery) with explicit CIDR input; user defines scope |

### Dependency Notes

- `ipaddress` is Python stdlib — no new pip dependencies for CIDR/range expansion
- Interacts with BACK-75 (port discovery): once multi-target is supported, port discovery should run per-host in the multi-target list
- `run_scan.py` loop over targets already exists in some form — this extends it; interactive wizard needs the most work
- Phase ordering: BACK-77 should come after BACK-75 because port discovery per expanded target list is the natural next step

---

## Feature 7: Architecture Reference + Operator's Guide (BACK-65 + BACK-66)

### What This Feature Does

Produces two documentation artifacts for enterprise self-onboarding:
- **Architecture reference** (BACK-65): System architecture, component diagram, data flow, scan session lifecycle, SQLite schema reference, API contract
- **Operator's guide** (BACK-66): Day-1 through Day-N operational runbook — install, configure, first scan, interpret results, generate report, schedule recurring scans, upgrade, troubleshoot

### What Enterprise Operators Expect (MEDIUM confidence — runbook patterns well-established)

Enterprise security tools that expect self-onboarding (no vendor hand-holding) need:

**Architecture reference sections:**
1. System overview diagram — components, their relationships, data flow direction
2. Component inventory — CLI, FastAPI backend, React dashboard, SQLite, report renderer
3. Scanner surface inventory — what each surface scans, protocol, required credentials/access
4. Data model — key SQLite tables, what is stored, retention model
5. API contract — FastAPI endpoint list with request/response shapes (OpenAPI spec)
6. Security model — what data leaves the machine (nothing; all local), credentials handling

**Operator's guide sections (runbook format):**
1. Prerequisites — Python version, OS support, nmap binary for discovery
2. Installation — `pip install quirk[all]` + `quirk init`
3. Configuration — `quirk.toml` reference with all fields annotated
4. First scan — `quirk scan` with a real target, viewing output
5. Dashboard — `quirk serve`, what each tab shows, how to export PDF
6. Multi-target workflow — hosts file, CIDR, progress monitoring
7. Compliance reporting — enabling frameworks in config, reading the compliance section
8. Recurring scan setup — cron pattern, result retention
9. Upgrade path — `pip install --upgrade quirk`, schema migration notes
10. Troubleshooting — common errors with root cause and fix

### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Architecture reference doc in `docs/architecture.md` | Enterprise IT teams need to understand the system before deploying; security review requires architecture doc | MEDIUM | Text-based is acceptable; ASCII or Mermaid diagram for system overview; no complex tooling needed |
| Operator's guide in `docs/operator-guide.md` | Self-onboarding without vendor support requires step-by-step runbook | HIGH | This is the highest-effort doc artifact — needs to cover all 10 sections above; must be accurate for v4.6 feature set |
| Scanner surface reference table (one row per surface: what it scans, credentials required, extras needed) | Enterprise operators need to know what they're enabling and what access to grant | LOW | Table in architecture doc or operator's guide; 13 rows × 5 columns |
| Configuration reference (all `quirk.toml` fields annotated with type, default, example) | Config documentation is table-stakes for any enterprise tool | MEDIUM | Auto-generate from config dataclass if possible; otherwise maintain manually; common failure is docs drift |
| Troubleshooting section with top-10 error scenarios | Self-service support; reduces consultant support burden | MEDIUM | Cover: missing extras, nmap not found, credential errors, DB locked, port already in use, scan timeout |
| Obsidian vault sync of both docs | Per CLAUDE.md: all docs must sync to vault | LOW | Standard vault sync pattern; write to `20_Dev-Work/QUIRK/Guides/` |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Mermaid system diagram in architecture doc | Visual architecture is faster to review than prose; Mermaid renders in GitHub and Obsidian | LOW | Mermaid `graph LR` for component topology; `sequenceDiagram` for scan session lifecycle |
| Scanner surface decision matrix (when to use each scanner, required credentials, risk of running agentlessly) | Operators need to scope which surfaces to enable for a given engagement | LOW | 3-column table per surface: "when to enable", "what access is needed", "what it can't detect" |
| `quirk doctor` command — diagnose installation and config health | Self-service pre-scan check that catches common misconfigurations before the scan fails | MEDIUM | Check Python version, nmap availability, extras installed, config file validity, SQLite write access, scanner credentials present |

### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Video walkthrough / screencasts | "More approachable onboarding" | Production cost is high; becomes stale after each feature release | Written guide with screenshot callouts is more maintainable |
| Interactive tutorial mode | In-product guided tour | Implementation complexity high; tutorial state management; scope creep | `quirk init` with guided prompts is sufficient; operator's guide is the external reference |

### Dependency Notes

- No code dependencies — documentation artifacts only (except `quirk doctor` which is code)
- Architecture reference should be written first (BACK-65); operator's guide references architecture
- Both docs must be Obsidian-synced per CLAUDE.md
- `quirk doctor` (differentiator) touches the CLI and should be scoped separately if it slips

---

## Feature Dependencies

```
[BACK-76: Install-day UX]
    └──unblocks──> ALL other features (stable install required before testing anything)
    └──requires──> pyproject.toml extras restructure

[BACK-74: TLS Finding Gaps]
    └──requires──> sslyze data already in tls_capabilities_json (already present)
    └──feeds──> BACK-79 (new findings need remediation context)
    └──feeds──> BACK-20 (new findings need compliance mapping)

[BACK-79: Rich Finding Context]
    └──requires──> Finding model extended with new fields
    └──requires──> new quirk/risk/remediation.py static lookup
    └──enhances──> BACK-74 findings (first users of remediation_path)
    └──shares model extension with──> BACK-20

[BACK-20: Compliance Mapping]
    └──requires──> Finding model extended (same extension as BACK-79)
    └──requires──> new quirk/compliance/mapper.py
    └──enhances──> report renderer (new section)
    └──best shipped with──> BACK-79 (shared Finding model extension)

[BACK-75: Nmap Port Discovery]
    └──requires──> python-nmap pip dep + nmap binary
    └──feeds──> BACK-77 (multi-target discovery uses nmap per host)
    └──modifies──> run_scan.py orchestration (pre-scan phase)

[BACK-77: Multi-Target Wizard]
    └──requires──> BACK-75 for port discovery per host
    └──requires──> ipaddress stdlib (no new dep)
    └──modifies──> interactive.py wizard + run_scan.py target loop

[BACK-65+66: Architecture + Operator Docs]
    └──requires──> all other features complete (docs must reflect final feature set)
    └──requires──> nothing code-level
```

### Dependency Notes

- **BACK-79 and BACK-20 are tightly coupled**: both extend `Finding` Pydantic model and both feed the report renderer with new sections. Ship in the same phase to avoid double-touching the model.
- **BACK-74 should precede BACK-79**: you need the new finding types to exist before writing their remediation guidance.
- **BACK-75 should precede BACK-77**: multi-target without port discovery is useful but less valuable; discovery + multi-target together is the complete enterprise workflow.
- **BACK-76 is phase 1 of the milestone**: nothing else should be developed or tested until install-day UX is stable.
- **BACK-65+66 is the final phase**: docs reflect the full v4.6 feature set.

---

## MVP Definition

### Launch With (v4.6)

All 7 backlog items are in scope for v4.6. Priority order if forced to cut:

- [x] **BACK-76**: Install-day UX — blocks everything; must ship
- [x] **BACK-74**: TLS finding gaps — core scanner correctness; missing findings undermine credibility
- [x] **BACK-79**: Rich finding context — highest consultant time-save; drives billable efficiency
- [x] **BACK-20**: Compliance mapping — primary enterprise sales differentiator; HIPAA/PCI clients require this
- [x] **BACK-75**: Nmap port discovery — required for real estate scans; hardcoded ports are the #1 consultant complaint
- [x] **BACK-77**: Multi-target wizard — required for 50-host+ engagements; currently broken for multi-host
- [x] **BACK-65+66**: Enterprise docs — self-onboarding gate; without docs, enterprise deployment requires vendor support

### Cut If Necessary (v4.6.x)

- Compliance mapping for SOC 2 and ISO 27001 (differentiators — defer the less common frameworks)
- `quirk doctor` command (differentiator — useful but not blocking)
- Service fingerprinting in nmap pre-scan (nmap `-sV` adds scan time; basic port discovery is sufficient)
- Mermaid diagram in architecture doc (nice to have; prose architecture is acceptable)

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| BACK-76: Graceful ImportError degradation | HIGH | LOW | P1 — phase 1 |
| BACK-76: identity+motion in default install | HIGH | LOW | P1 — phase 1 |
| BACK-74: Expired cert finding | HIGH | LOW | P1 |
| BACK-74: Self-signed cert finding | HIGH | LOW | P1 |
| BACK-74: RSA-1024/512 weak key finding | HIGH | LOW | P1 |
| BACK-79: `risk_explanation` field | HIGH | MEDIUM | P1 |
| BACK-79: `remediation_path` field with FIPS 203/204/205 | HIGH | MEDIUM | P1 |
| BACK-20: Finding → control mapping (PCI + HIPAA) | HIGH | MEDIUM | P1 |
| BACK-20: Compliance summary in HTML/PDF report | HIGH | HIGH | P1 |
| BACK-75: TCP connect pre-scan (non-root) | HIGH | MEDIUM | P1 |
| BACK-75: Graceful fallback when nmap missing | HIGH | LOW | P1 |
| BACK-77: Comma-separated targets | HIGH | LOW | P1 |
| BACK-77: Hosts file input | HIGH | LOW | P1 |
| BACK-77: CIDR expansion | MEDIUM | LOW | P1 |
| BACK-65: Architecture reference doc | HIGH | MEDIUM | P1 |
| BACK-66: Operator's guide | HIGH | HIGH | P1 |
| BACK-74: Near-expiry warning (30-day) | MEDIUM | LOW | P2 |
| BACK-74: SHA-1 signature finding | MEDIUM | LOW | P2 |
| BACK-74: Hostname mismatch finding | MEDIUM | LOW | P2 |
| BACK-74: Chain completeness check | MEDIUM | LOW | P2 |
| BACK-74: Chaos lab coverage for new TLS findings | MEDIUM | MEDIUM | P2 |
| BACK-79: `see_also` URLs on findings | MEDIUM | LOW | P2 |
| BACK-79: FIPS deadline callout per finding | MEDIUM | LOW | P2 |
| BACK-20: FIPS 140-3 approved/not-approved per algorithm | MEDIUM | MEDIUM | P2 |
| BACK-20: SOC 2 / ISO 27001 mapping | LOW | MEDIUM | P3 |
| BACK-75: Service fingerprinting (`-sV`) | MEDIUM | MEDIUM | P2 |
| BACK-75: Scan pacing / rate limiting | LOW | LOW | P3 |
| BACK-77: Exclude list | MEDIUM | LOW | P2 |
| BACK-66: `quirk doctor` command | MEDIUM | MEDIUM | P2 |
| BACK-66: Mermaid diagram | LOW | LOW | P3 |

**Priority key:**
- P1: Ships in v4.6 milestone core
- P2: Ships in v4.6 if time permits; else v4.6.x
- P3: v4.6.x or v4.7

---

## Consultant-Value Framing Per Feature

| Feature | Consultant Time Saved | Client Deliverable Impact | Priority Driver |
|---------|----------------------|--------------------------|-----------------|
| BACK-76: clean install | 30-60 min per engagement setup | None (invisible) | Credibility: crashes on install kill sales |
| BACK-74: expired/self-signed findings | 1-2 hr (manual cert check eliminated) | HIGH — new critical findings in report | Scanner completeness |
| BACK-79: remediation context | 2-4 hr per report (lookup + writing eliminated) | HIGH — findings become actionable without extra research | Billable efficiency multiplier |
| BACK-20: compliance mapping | 3-6 hr per report (control cross-ref eliminated) | HIGH — compliance officers can present to auditors | Enterprise sales gate |
| BACK-75: port discovery | 1-2 hr per engagement (no manual port list) | MEDIUM — catches services on non-standard ports | Scanner coverage |
| BACK-77: multi-target | 0.5-1 hr per engagement (no manual host loop) | MEDIUM — enables 50+ host assessments | Engagement scale |
| BACK-65+66: docs | N/A (enables self-service) | LOW direct / HIGH strategic | Enterprise deployment gate |

---

## Sources

- [NIST FIPS 203: ML-KEM Standard](https://csrc.nist.gov/pubs/fips/203/final) — HIGH confidence
- [NIST FIPS 204: ML-DSA Standard](https://csrc.nist.gov/pubs/fips/204/final) — HIGH confidence
- [NIST IR 8547: Transition to PQC Standards (2024)](https://csrc.nist.gov/pubs/ir/8547/ipd) — HIGH confidence; RSA-2048 deprecated 2030, all RSA/ECC disallowed 2035
- [NIST SP 800-52r2: TLS Guidelines](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-52r2.pdf) — HIGH confidence
- [NIST SP 800-208: Stateful Hash-Based Signatures](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-208.pdf) — HIGH confidence; scope is LMS/XMSS only
- [PCI-DSS 4.0 Requirement 4 — TLS requirements](https://www.isms.online/pci-dss/requirement-4/) — HIGH confidence; TLS 1.2+ required, expired/self-signed certs = violation
- [PCI-DSS 4.0 Cryptographic Requirements — AppViewX analysis](https://www.appviewx.com/blogs/decoding-the-pci-dss-v4-0-cryptographic-requirements/) — MEDIUM confidence
- [HHS HIPAA Encryption Requirements](https://www.hipaajournal.com/hipaa-encryption-requirements/) — HIGH confidence; 45 CFR §164.312 technical safeguards
- [HHS.gov HIPAA Encryption FAQ](https://www.hhs.gov/hipaa/for-professionals/faq/encryption/index.html) — HIGH confidence; primary source
- [sslyze documentation — Certificate Info scan command](https://blog.adqt.fr/sslyze/documentation/available-scan-commands.html) — HIGH confidence; verified field names
- [python-nmap PyPI — TCP connect scan](https://pypi.org/project/python-nmap/) — HIGH confidence
- [Nmap port scanning techniques — TCP connect vs SYN](https://nmap.org/book/man-port-scanning-techniques.html) — HIGH confidence; root requirement confirmed
- [Greenbone/OpenVAS — multi-target input formats](https://docs.greenbone.net/GSM-Manual/gos-22.04/en/scanning.html) — HIGH confidence; comma and file-based import confirmed
- [Nessus file format — finding fields (description, solution, see_also)](https://docs.tenable.com/quick-reference/nessus-file-format/Nessus-File-Format.pdf) — HIGH confidence; industry standard structure
- [PEP 771: Default Extras](https://peps.python.org/pep-0771/) — MEDIUM confidence; still draft as of 2025; use meta-extra pattern instead
- [NIST NCCoE PQC Migration Project](https://pages.nist.gov/nccoe-migration-post-quantum-cryptography/FAQ/index.html) — HIGH confidence
- [NIST IR 8547 explained — 2030/2035 deadlines](https://www.pqcinformation.com/nist-ir-8547-explained-the-2030-and-2035-algorithm-deprecation-deadlines-every-compliance-officer-must-understand/) — MEDIUM confidence (secondary source but consistent with primary)

---

*Feature research for: QU.I.R.K. v4.6 Enterprise Readiness milestone*
*Researched: 2026-05-03*
