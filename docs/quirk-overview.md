---
project: QU.I.R.K.
type: reference
status: active
source: docs/quirk-overview.md
updated: 2026-05-28
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

## Current Capabilities — v5.5

QU.I.R.K. v5.5 builds on the v4.x enterprise foundation with the v5.x series of milestones: PQC-hybrid scoring ceiling (v5.0), authenticated scanning (v5.1), consulting-grade reporting (v5.2), notification / SIEM / ticketing integrations (v5.3), distributed on-prem sensor / console architecture (v5.4), and per-sensor authentication + revocation (v5.5). The result is a production-hardened platform with full cryptographic inventory across every major protocol surface, structured compliance mappings, enterprise-scale multi-target workflows, distributed scanning across isolated network segments, and rich finding context for remediation planning.

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

Every TLS certificate's key algorithm is evaluated against a 50-entry NIST PQC classification table that marks each algorithm as *quantum-safe*, *quantum-vulnerable*, or *hybrid-ready*. RSA and ECDSA keys are flagged as vulnerable. ML-KEM (FIPS 203) and ML-DSA (FIPS 204) implementations are recognized as quantum-safe.

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

### Identity Protocol Scanning (v4.2)

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

The intelligence layer produces a composite quantum-readiness score from six weighted subscores, each contributing 0–25 points (sum / 1.5 = overall 0–100):

1. **Hygiene** — algorithm strength, key sizes, protocol versions
2. **Modern TLS** — cipher suite modernity, TLS 1.3 adoption, deprecated protocol usage
3. **Identity** — Kerberos etype exposure, SAML / OIDC signing strength, DNSSEC integrity, JWT algorithm posture
4. **Agility** — code-signing posture, cryptographic agility signals, **+8.0 PQC-hybrid bonus** when X25519MLKEM768 / ML-DSA endpoints are detected (v5.0 ceiling)
5. **Data at Rest** — database, object storage, Kubernetes, Vault encryption posture
6. **Data in Motion** — email / message broker TLS posture (SMTPS, IMAPS, AMQPS, Kafka SSL)

Scores are calibrated against three organizational profiles — *strict*, *balanced*, and *lenient* — to account for different risk tolerances and regulatory obligations. Each profile applies weighted multipliers to the subscores, producing a final readiness rating on a 0–100 scale with an associated risk tier (LOW / MEDIUM / HIGH / CRITICAL).

### Data at Rest Encryption (v4.3)

QUIRK expanded coverage to encryption of stored data across four major surfaces:

- **Database encryption** — PostgreSQL `pg_stat_ssl`, MySQL `Ssl_cipher` status, RDS `StorageEncrypted` and encryption type. Plaintext connections and disabled SSL emit HIGH-severity findings.
- **Object storage** — S3 bucket SSE mode (SSE-S3 / SSE-KMS / unencrypted), Azure Blob CMK vs. platform-managed key, GCS CMEK configuration.
- **Kubernetes secrets at rest** — EKS/GKE/AKS managed encryption APIs and etcd `EncryptionConfiguration` provider detection.
- **HashiCorp Vault** — Transit key type classification (including ML-DSA and SLH-DSA as quantum-safe positives), PKI mount CA certificate algorithm, auth method enumeration.

A dedicated `data_at_rest` subscore joins the scoring composite, and a **Data at Rest tab** in the dashboard surfaces findings from all four surfaces.

### Data in Motion (v4.4)

QUIRK added full TLS posture scanning for email and message broker protocols, completing coverage of in-transit cryptographic surfaces:

- **Email** — SMTP/STARTTLS (port 25 stripping-risk detection), SMTPS, submission (587), IMAP/IMAPS (143/993), POP3/POP3S (110/995). Weak ciphers surface as HIGH; STARTTLS-downgrade capability surfaces as MEDIUM.
- **Message brokers** — Apache Kafka (PLAINTEXT / SSL / SASL_SSL), RabbitMQ (AMQP / AMQPS), Redis (plaintext / TLS). Plaintext listeners emit HIGH findings. Azure Service Bus and AWS SQS cloud broker surfaces are also dispatched.
- **`data_in_motion` subscore** — six `motion_*` intelligence counters feed a dedicated subscore on the executive summary card alongside TLS, SSH, API, Identity, and Data at Rest.

### Web Dashboard

The local web dashboard provides immediate visual access to scan results without requiring any additional configuration. Seven core views are available:

- **Executive Summary** — overall readiness score with gauge visualization, six subscores (Hygiene, Modern TLS, Identity, Agility, Data at Rest, Data in Motion), severity breakdown, and scan metadata
- **Findings** — full findings table with severity filtering, algorithm detail, compliance framework tag, and per-host drill-down
- **Certificate Inventory** — all discovered TLS certificates with expiry countdown, key algorithm, and quantum safety status
- **CBOM Viewer** — interactive bipartite graph of the cryptographic bill of materials, linking systems to algorithms and components
- **Migration Roadmap** — prioritized remediation DAG showing NOW / NEXT / LATER migration waves, dependency chains, and effort estimates
- **Data at Rest** — database, object storage, Kubernetes, and Vault findings with per-surface encrypted/unencrypted breakdown
- **Data in Motion** — email and broker TLS posture grid with per-port cipher weakness and plaintext-exposure flags; **Trends** — score deltas and new/resolved findings across scan sessions

### Reliability and Platform Hardening (v4.5)

The v4.5 milestone closed reliability gaps discovered after the initial feature build:

- All scanners are hardened against missing optional extras, connection timeouts, and unexpected exceptions — a scan never crashes due to a single unreachable endpoint.
- CBOM JSON and XML output validates against the CycloneDX 1.6 schema; classifier unknown-fallback gaps are closed.
- Dashboard meets WCAG AA accessibility baseline across all routes, with explicit loading and empty states on every view.
- The `quirk doctor` health check and timeout/retry policy are documented in the Operator's Guide.

### Enterprise Readiness (v4.6)

v4.6 makes QUIRK production-ready for enterprise deployments:

- **Install-Day UX** — `pip install quirk` and `pip install quirk-scanner[all]` complete without `ImportError` crashes; a centralized optional-extra registry emits advisory notices when a scanner extra is absent rather than raising an exception.
- **TLS Certificate Findings** — Expired certificates, self-signed certificates, untrusted/private-CA certificates, and weak RSA/EC key sizes now produce explicit findings with severity classification. Previously these conditions produced zero findings.
- **Multi-Target Wizard and Nmap Discovery** — Users can pass comma-separated hosts, `--targets-file`, or a CIDR range directly. An optional nmap-based port discovery step (`--nmap-discover`) pre-populates the target list without manual port enumeration — enabling real 50-host+ enterprise scans.
- **Rich Finding Context** — Every finding carries a plain-English risk description. Quantum-relevant findings include the FIPS 203/204/205 remediation path and NIST IR 8547 deprecation deadline. All Kyber/Dilithium pre-standardization terminology is purged.
- **Compliance Framework Mapping** — Findings carry machine-readable control references to PCI DSS 4.0.1 (Requirements 4.2.1 and 12.3.3), HIPAA 45 CFR § 164.312, and FIPS 140-3. The `quirk compliance status` CLI command reports coverage. A quarterly staleness check prevents mapping drift.
- **`quirk doctor` Pre-Scan Health Check** — The `quirk doctor` command validates dependencies, chaos lab connectivity, config syntax, and scanner readiness in a single pre-engagement step.

### Professional Report Export

QUIRK produces HTML and PDF reports suitable for direct client delivery. The PDF report is rendered by Playwright for pixel-accurate output and includes an executive summary, findings table, certificate inventory, CBOM summary, and migration roadmap. Reports include all metadata required for a professional deliverable: scan date, scope, target count, profile, and version.

---

## Who Uses QUIRK?

**Security Consultants** use QUIRK as their primary post-quantum readiness assessment tool. The zero-to-deliverable workflow — install, configure, scan, export PDF — fits inside a client engagement day. The CBOM and readiness score are immediately defensible consulting outputs.

**IT Security Engineers** use QUIRK for internal audits and continuous cryptographic hygiene. The local dashboard provides ongoing visibility into certificate expiry, weak ciphers, and protocol posture without requiring a full assessment engagement.

**Compliance Officers** use QUIRK's CBOM output and compliance-mapped findings as evidence for NIST PQC, CNSA 2.0, and emerging post-quantum regulatory requirements. The CycloneDX format is recognized by major GRC platforms.

---

## What Shipped Since v4.6

### v4.7 — Governance & Compliance Platform (shipped)

v4.7 integrated the **CSNP QRAMM (Quantum Readiness Assurance Maturity Model)** framework as a first-class governance layer alongside the technical inventory: 120-question maturity catalog, weakest-link scoring, QRAMM evidence bridge (auto-populating CVI dimension answers from scanner findings), QRAMM assessment UI with radar-chart scorecard, an 8-framework compliance coverage table (NIST PQC, CNSA 2.0, PCI DSS 4.0.1, HIPAA, FIPS 140-3, SOC 2, ISO 27001:2022, CMMC 2.0), and a combined PDF export merging technical CBOM and QRAMM scorecard. *(QRAMM v1.0 framework by CSNP — qramm.org. Used with attribution.)*

### v5.0 — PQC-Hybrid Scoring Ceiling (shipped)

OQS-nginx PQC-hybrid chaos-lab profile (port 39444) serving TLS 1.3 with X25519MLKEM768 hybrid KEM and ML-DSA-65 certificates; agility scoring gains a `+8.0` PQC-hybrid bonus that anchors the scoring ceiling for post-quantum readiness. Six-subscore N/25 decomposition exposed across CLI, executive markdown, and HTML/PDF report surfaces. Four weak-TLS chaos-lab profiles added (postgres-tls, redis-tls, kafka-tls, grpc-tls).

### v5.1 — Authenticated Scanning (shipped)

Ephemeral credential model for cloud connector and JWT-issuing API scans (no long-lived secret storage in scheduled scan rows). Query-param API-key CLI flag wired through to JWT scanner URL credential consumption. Code-signing posture via LDAP+TLS-EKU classification, folded into the agility subscore.

### v5.2 — Consulting-Grade Reporting (shipped)

One shared content model now drives CLI markdown, HTML, PDF, and a new DOCX renderer for client-editable Word deliverables. Executive narrative blocks added across all surfaces; render-parity tests lock invariant content across renderers.

### v5.3 — Adoption & Integration Surface (shipped)

Notification fan-out (webhook / email / Slack), SIEM CEF dispatch (Splunk / QRadar / ArcSight ingestion), and Jira / ServiceNow ticketing on a single shared SSRF-safe / secret-scrubbing layer. Dashboard token authentication added. Finding fingerprint formula = `SHA256(host:port::title)`.

### v5.4 — Distributed On-Prem Scanner (shipped)

Sensor / console architecture for isolated network segments. On-prem sensors scan per segment and push findings to a central console; console performs Option-A merge (keep newest-per-fingerprint, never rewrite `scanned_at`) into a single CBOM + readiness score. Sensor enrollment via `quirk enroll --sensor-id` workflow.

### v5.5 — Distributed Hardening (current)

Per-sensor opaque Bearer tokens with individual issuance + revocation via `quirk revoke-sensor`; `revoked_at` migration on the sensors table. Failure-isolated auto-merge: when one sensor fails mid-scan the console merges the remaining successful results rather than discarding the batch. Live-UAT stabilization sweep + new weak-TLS chaos-lab target.

### SaaS Platform (long-term roadmap)

A multi-tenant SaaS platform for organizations that need centralized scan management, hosted reporting, and multi-site visibility remains on the long-term roadmap.

---

## The Bottom Line

The post-quantum transition is the largest cryptographic migration in the history of computing. Every organization with a meaningful digital presence will need to complete it. The organizations that begin with a complete, accurate inventory will complete it on their schedule. Those that do not will be reactive, exposed, and expensive to fix.

QU.I.R.K. provides the foundation: an automated, agentless, consultant-ready cryptographic inventory platform that speaks the language of both technical teams and compliance programs. It does not require a six-month engagement to deploy. It does not require agents on every host. It produces a standards-compliant CBOM, a prioritized remediation roadmap, and a professional report in a single session.

The quantum clock is running. QUIRK helps you understand exactly what you are racing against.

---

*QU.I.R.K. is developed by the Quantum Apps team. For more information, visit the project repository or contact the development team.*
