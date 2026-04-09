---
project: QU.I.R.K.
type: reference
status: active
source: docs/quirk-overview.md
updated: 2026-04-09
---

# QU.I.R.K. — Quantum Infrastructure Readiness Kit

## The Case for Cryptographic Inventory in the Post-Quantum Era

---

## The Clock Is Already Running

In August 2024, the National Institute of Standards and Technology (NIST) finalized the first three post-quantum cryptographic standards — ML-KEM, ML-DSA, and SLH-DSA. This was not a theoretical milestone. It was a starting gun.

Organizations now face a hard deadline with no fixed date. Quantum computers capable of breaking RSA-2048 and elliptic curve cryptography (ECC) may be five years away, or fifteen. But the threat does not wait for quantum computers to arrive. Adversaries are already executing *Harvest Now, Decrypt Later* (HNDL) campaigns — intercepting and storing encrypted traffic today with the intent to decrypt it once a sufficiently powerful quantum processor exists. Data protected today by classical encryption is not safe if it needs to remain confidential for more than a decade.

The urgency is compounded by the scale of the problem. Every organization that uses TLS, SSH, code signing, digital certificates, API tokens, cloud key management, or identity protocols has a cryptographic attack surface. The challenge is that most organizations have no idea how large that surface actually is.

This is the problem QU.I.R.K. was built to solve.

---

## What Is QU.I.R.K.?

**QU.I.R.K.** (Quantum Infrastructure Readiness Kit) is a consulting-grade cryptographic inventory scanner and quantum-readiness assessment platform. It discovers, classifies, and scores an organization's complete cryptographic posture across every major protocol surface — then delivers a Cryptographic Bill of Materials (CBOM), a quantum-readiness score, and a prioritized remediation roadmap.

QUIRK is designed for the security professional doing the work: the consultant running a two-hour assessment on a client network, the IT security engineer who needs to demonstrate compliance posture to an auditor, and the compliance officer who needs a defensible inventory to support a regulatory submission. It installs in minutes, requires no agents on target systems, and produces a professional deliverable without manual spreadsheet work.

The tool is delivered as a Python package with a command-line interface and a local web dashboard. It operates in fully offline, air-gapped environments — a critical requirement for the enterprise and government engagements where post-quantum readiness is most urgently needed.

---

## Why the Industry Needs It

### The Inventory Problem Is Unsolved

Ask most organizations where they use RSA-2048 and you will get silence, a spreadsheet that was accurate eighteen months ago, or an honest admission that nobody knows. Cryptographic assets are embedded everywhere — in TLS certificates, SSH host keys, JWT signing configurations, container images, source code, cloud KMS key specs, and identity infrastructure. They accumulate over years without centralized tracking.

NIST, NSA, and every major standards body now require organizations to begin their post-quantum transition with a complete cryptographic inventory. There is no migration without a map. QUIRK builds that map automatically.

### Consultants Need a Deliverable

The post-quantum readiness market is growing. Clients need assessments. Consultants need a tool that produces a professional, defensible deliverable without weeks of manual data gathering. QUIRK was designed with the consulting engagement model in mind: install, configure, scan, and hand the client a CBOM and readiness report within a single working session.

### Compliance Is Catching Up Fast

U.S. Office of Management and Budget (OMB) Memorandum M-23-02, NSA's Commercial National Security Algorithm Suite 2.0 (CNSA 2.0), and the evolving NIST SP 800-131A guidance all require organizations to inventory and transition their cryptographic implementations. The EU's ETSI quantum-safe standards and BSI TR-02102 (Germany) are moving in the same direction. Without an automated inventory tool, compliance with these mandates is a manual nightmare. QUIRK converts a compliance requirement into an executable workflow.

---

## Current Capabilities — v4.2

QU.I.R.K. v4.2 represents the culmination of the Identity Crypto milestone, expanding the platform's cryptographic discovery surface to cover every major protocol category in the modern enterprise stack.

### Cryptographic Discovery Engine

The scanner operates as a multi-protocol discovery engine with no agents required on target hosts. It scans a defined network range or target list, probing each host across the protocols it is configured to examine. Results are persisted to a local SQLite database and are immediately available in the web dashboard.

Scan profiles — *quick*, *standard*, and *deep* — control the trade-off between scan speed and coverage depth. A standard scan of a typical enterprise subnet completes in under thirty minutes.

### TLS / SSL Analysis

QUIRK performs deep TLS analysis using sslyze as its primary engine, with a fallback path for environments where sslyze is unavailable. For each TLS endpoint, QUIRK extracts:

- Certificate public key algorithm and key size
- Certificate chain and authority information
- Expiry status and days-to-expiration
- Negotiated cipher suites and protocol versions
- Quantum vulnerability classification per NIST PQC standards

Every TLS certificate's key algorithm is evaluated against a 50-entry NIST PQC classification table that marks each algorithm as *quantum-safe*, *quantum-vulnerable*, or *hybrid-ready*. RSA and ECDSA keys are flagged as vulnerable. CRYSTALS-Kyber and ML-DSA implementations are recognized as quantum-safe.

### SSH Protocol Auditing

QUIRK integrates ssh-audit for comprehensive SSH posture analysis. Each SSH service is examined for:

- Host key algorithms and key sizes
- Key exchange (KEX) algorithms
- Message authentication codes (MAC)
- Encryption algorithm negotiation
- Quantum vulnerability status of each algorithm

Weak configurations — MD5 MACs, diffie-hellman-group1-sha1 KEX, RSA-1024 host keys — generate severity-classified findings that appear in both the dashboard and the CBOM.

### API & JWT Token Analysis

QUIRK discovers REST API endpoints and retrieves JWKS (JSON Web Key Set) documents to enumerate the signing algorithms and key sizes used for JWT authentication. SHA-1 HMAC tokens, RS256-signed JWTs, and API endpoints transmitting credentials over unencrypted transports are all flagged with appropriate severity ratings.

### Container & Binary Scanning

Using Syft as its underlying engine, QUIRK inventories cryptographic libraries embedded in container images and binaries. A 23-entry allowlist distinguishes quantum-safe cryptographic library versions from known-vulnerable ones. OpenSSL, libcrypto, and NSS library versions are identified and classified.

### Source Code Scanning

QUIRK runs static analysis against source code repositories using the semgrep cryptography ruleset. Hardcoded keys, insecure random number generator usage, deprecated cryptographic function calls, and weak algorithm specifications in code are all surfaced as findings with file and line number references — exactly the detail a developer needs to act on a finding.

### Cloud Key Management Connectors

Native connectors for **AWS** and **Azure** enumerate the cryptographic configuration of cloud-managed key infrastructure:

- **AWS**: ACM certificates, KMS key specs, CloudFront distribution TLS policies, ELBv2 listener certificates
- **Azure**: Key Vault keys and certificates, Application Gateway TLS configuration

Both connectors map cloud key specifications against the NIST PQC classification table, identifying RSA and ECC KMS keys as quantum-vulnerable and flagging them for migration to AES-256 or ML-KEM equivalents.

### Identity Protocol Scanning — New in v4.2

Version 4.2 adds dedicated scanners for the three most widely deployed identity protocols in enterprise environments. This is the category most often overlooked in quantum-readiness assessments.

**Kerberos Encryption Type Enumeration**

QUIRK probes Active Directory environments using AS-REQ requests (TCP and UDP with automatic fallback) to enumerate the encryption types a KDC advertises. The RC4-HMAC (arcfour-hmac) encryption type — still enabled by default in the vast majority of Windows domain environments — is classified as **CRITICAL** severity. A full seven-type severity map covers DES (CRITICAL), RC4-HMAC (CRITICAL), AES-128 (LOW), and AES-256-CTS-HMAC-SHA1-96 (SAFE). When LDAP is available, QUIRK enriches the probe with per-account `msDS-SupportedEncryptionTypes` bitmap data.

**SAML / OIDC Metadata Scanning**

QUIRK retrieves SAML metadata from standard well-known paths (`/saml/metadata`, `/.well-known/openid-configuration`, and others) and parses signing certificates and algorithm declarations. RSA-1024 signing certificates, SHA-1 assertion signing, and weak key sizes in federation metadata are surfaced as HIGH or CRITICAL findings. No authentication is required — SAML metadata is publicly accessible by design.

**DNSSEC Algorithm Audit**

Using dnspython, QUIRK queries DNSKEY and DS records for any domain in scope and classifies signing algorithms against both RFC 8624 and the updated RFC 9905 three-tier guidance. RSASHA1 signing is flagged as **CRITICAL**. Unsigned zones receive a HIGH severity finding. NSEC record presence — which enables zone enumeration — is identified as a separate exposure. Broken DS chains (mismatched key tags between parent and child) are detected and flagged.

### CycloneDX Cryptographic Bill of Materials (CBOM)

Every scan produces a fully compliant **CycloneDX 1.6 CBOM** in both JSON and XML formats. The CBOM captures all discovered cryptographic components — algorithms, certificates, key material, protocols — in the standardized format now required by major regulatory frameworks.

The CBOM is the primary compliance artifact. It answers the audit question "show me your cryptographic inventory" with a machine-readable, standards-compliant document that can be submitted directly to compliance reviewers or integrated into a software composition analysis (SCA) pipeline.

### Quantum-Readiness Scoring

The intelligence layer produces a composite quantum-readiness score from four weighted subscores:

1. **Cryptographic Hygiene** — algorithm strength, key sizes, protocol versions
2. **Certificate Health** — expiry, chain validity, public key quality
3. **Configuration Posture** — cipher suite selection, deprecated protocol usage
4. **Identity & Access Cryptography** — Kerberos etype exposure, SAML signing strength, DNSSEC integrity

Scores are calibrated against three organizational profiles — *strict*, *balanced*, and *lenient* — to account for different risk tolerances and regulatory obligations. Each profile applies weighted multipliers to the subscores, producing a final readiness rating on a 0–100 scale with an associated risk tier (LOW / MEDIUM / HIGH / CRITICAL).

### Web Dashboard

The local web dashboard provides immediate visual access to scan results without requiring any additional configuration. Five core views are available:

- **Executive Summary** — overall readiness score with gauge visualization, severity breakdown, top findings, and scan metadata
- **Findings** — full findings table with severity filtering, algorithm detail, and per-host drill-down
- **Certificate Inventory** — all discovered TLS certificates with expiry countdown, key algorithm, and quantum safety status
- **CBOM Viewer** — interactive bipartite graph of the cryptographic bill of materials, linking systems to algorithms and components
- **Migration Roadmap** — prioritized remediation DAG showing NOW / NEXT / LATER migration waves, dependency chains, and effort estimates

### Professional Report Export

QUIRK produces HTML and PDF reports suitable for direct client delivery. The PDF report is rendered by Playwright for pixel-accurate output and includes an executive summary, findings table, certificate inventory, CBOM summary, and migration roadmap. Reports include all metadata required for a professional deliverable: scan date, scope, target count, profile, and version.

---

## Who Uses QUIRK?

**Security Consultants** use QUIRK as their primary post-quantum readiness assessment tool. The zero-to-deliverable workflow — install, configure, scan, export PDF — fits inside a client engagement day. The CBOM and readiness score are immediately defensible consulting outputs.

**IT Security Engineers** use QUIRK for internal audits and continuous cryptographic hygiene. The local dashboard provides ongoing visibility into certificate expiry, weak ciphers, and protocol posture without requiring a full assessment engagement.

**Compliance Officers** use QUIRK's CBOM output and compliance-mapped findings as evidence for NIST PQC, CNSA 2.0, and emerging post-quantum regulatory requirements. The CycloneDX format is recognized by major GRC platforms.

---

## What's Coming

### v4.3 — Data at Rest

The next milestone expands QUIRK's coverage to encryption of stored data:

- **Database encryption detection** — PostgreSQL SSL mode, MySQL/MariaDB TLS, RDS encryption-at-rest, MSSQL Transparent Data Encryption
- **Object storage audit** — S3 bucket encryption policies (SSE-S3, SSE-KMS, no encryption), Azure Blob CMK vs. platform key, GCS bucket settings
- **Kubernetes secrets at rest** — etcd EncryptionConfiguration provider detection (aescbc, aesgcm, secretbox, KMS)
- **HashiCorp Vault connector** — transit key specs, PKI mount signing algorithms, auth method crypto configuration

### v4.4 — Data in Motion

Protocol coverage extends to the remaining communication channels:

- **Email protocol scanning** — SMTP/STARTTLS, IMAPS, POP3S cipher and protocol analysis via sslyze integration
- **Message broker TLS** — Kafka (9092/9093), RabbitMQ (5672/5671), Redis (6379/6380) TLS negotiation and cipher audit

### QRAMM Governance Integration

QUIRK is integrating the **CSNP QRAMM (Quantum Readiness Assurance Maturity Model)** framework directly into the dashboard. QRAMM evaluates organizational maturity across four governance dimensions — Cryptographic Visibility & Inventory, Strategic Governance & Risk Management, Data Protection Engineering, and Implementation & Technical Readiness — using a 120-question structured assessment.

The integration introduces a unique capability: QUIRK's scan results will **automatically pre-populate QRAMM answers** based on technical evidence. An organization running QUIRK at Level 3 automated discovery automatically satisfies multiple CVI dimension criteria. The combined output — a technical CBOM alongside a governance maturity scorecard — produces a consulting deliverable that addresses both the technical and organizational sides of a post-quantum readiness engagement. Compliance mappings to NIST PQC, CNSA 2.0, ISO/IEC 27001:2022, PCI DSS v4.0, CMMC 2.0, and five other frameworks are included.

*(QRAMM v1.0 framework by CSNP — qramm.org. Used with attribution.)*

### Compliance Framework Mapping

A standalone compliance mapping module will map QUIRK findings directly to FIPS 140-3, NIST SP 800-57, PCI DSS 4.0 requirement 4.2.1, and HIPAA technical safeguards. The classifier already knows quantum-vulnerability severity; the mapping layer translates that knowledge into the language auditors speak.

### Authenticated Scan Mode

A first-class optional credential model will enable deeper probing where credentials are available. Kerberos scanners will access per-account encryption type bitmaps via authenticated LDAP bind. SSH scanners will retrieve sshd_config directly from authenticated hosts. All credentials are stored with environment variable substitution — no plaintext secrets in configuration files.

### Trend Analysis & Continuous Monitoring

QUIRK currently treats each scan as an independent point-in-time assessment. A forthcoming intelligence layer will generate delta insights across scan sessions: score change since last scan, newly introduced findings, resolved findings, and hosts with degraded posture. Scheduled continuous scanning mode will transform QUIRK from an audit tool into an ongoing monitoring capability.

### SaaS Platform

The long-term roadmap includes a multi-tenant SaaS platform for organizations that need centralized scan management, hosted reporting, and multi-site visibility — the operational model most enterprise clients need for sustained post-quantum assurance programs.

---

## The Bottom Line

The post-quantum transition is the largest cryptographic migration in the history of computing. Every organization with a meaningful digital presence will need to complete it. The organizations that begin with a complete, accurate inventory will complete it on their schedule. Those that do not will be reactive, exposed, and expensive to fix.

QU.I.R.K. provides the foundation: an automated, agentless, consultant-ready cryptographic inventory platform that speaks the language of both technical teams and compliance programs. It does not require a six-month engagement to deploy. It does not require agents on every host. It produces a standards-compliant CBOM, a prioritized remediation roadmap, and a professional report in a single session.

The quantum clock is running. QUIRK helps you understand exactly what you are racing against.

---

*QU.I.R.K. is developed by the Quantum Apps team. For more information, visit the project repository or contact the development team.*
