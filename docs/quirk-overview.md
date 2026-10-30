# QU.I.R.K. — Quantum Infrastructure Readiness Kit

## The Case for Cryptographic Inventory in the Post-Quantum Era

---

## The Clock Is Already Running

On August 13, 2024, the National Institute of Standards and Technology (NIST) published the first three post-quantum cryptographic standards: FIPS 203 (ML-KEM), FIPS 204 (ML-DSA) and FIPS 205 (SLH-DSA).

NIST's draft transition report, IR 8547, describes the "harvest now, decrypt later" threat: adversaries collect encrypted data now with the goal of decrypting it once quantum technology matures. Because sensitive data often retains its value for many years, data protected today by classical public-key cryptography is exposed to that threat if it must stay confidential for a long time.

Every organization that uses TLS, SSH, code signing, digital certificates, API tokens, cloud key management or identity protocols has a cryptographic attack surface. This is the problem QU.I.R.K. was built to address.

---

## What Is QU.I.R.K.?

**QU.I.R.K.** (Quantum Infrastructure Readiness Kit) is a cryptographic inventory scanner and quantum-readiness assessment tool. It discovers and classifies the cryptography in use on the targets you point it at, then produces a Cryptographic Bill of Materials (CBOM), a quantum-readiness score, and a migration roadmap.

It works from the machine that runs it: it probes targets over the network, calls cloud provider APIs, and runs its scanning tools against the container images and local source directories you name. Nothing is installed on the target systems.

QU.I.R.K. is delivered as a Python package, `quirk-scanner`. Its local web dashboard (`quirk serve`) is the primary way to launch scans and review results; it needs the `[dashboard]` extra (`pip install 'quirk-scanner[dashboard]'`), and a plain install cannot start it. The command-line interface (`quirk`) stays fully supported for automation, scheduling and sensors. It is released under the MIT license; the source is at https://github.com/0xD1g5/QU.I.R.K.

---

## Why the Industry Needs It

### The Inventory Problem

Cryptographic assets are embedded in TLS certificates, SSH host keys, JWT signing configurations, container images, source code, cloud KMS key specs, and identity infrastructure. A migration plan starts from knowing where they are.

For U.S. federal agencies, OMB Memorandum M-23-02 "establishes requirements for agencies to inventory their active cryptographic systems, with a focus on High Value Assets (HVAs) and high impact systems." A QU.I.R.K. CBOM is a machine-readable record of the cryptography it observed on the targets you scanned; it does not by itself satisfy an agency's M-23-02 submission.

### Consultants Need a Deliverable

A single scan produces a CycloneDX CBOM, a readiness score, a migration roadmap, and HTML and Markdown reports (plus a DOCX report with the `[docx]` extra, and a PDF when Playwright and its Chromium browser are installed), so a client engagement ends with documents rather than a spreadsheet.

---

## Current Capabilities

### Cryptographic Discovery Engine

The scanner is a multi-protocol discovery engine. It scans a target list or network range, probing each host across the protocols it is configured to examine. Results are persisted to a local SQLite database. Scans launched from the dashboard write to the database the dashboard reads (by default `./quirk-output/quirk.db` under the directory where `quirk serve` was started; `QUIRK_DB_PATH` overrides it); a CLI scan appears there when its configured `db_path` is that same file.

Scan profiles — *quick*, *standard* (the default) and *deep* — are selected with `--profile`. They change the port-fingerprint timeout and whether email and message-broker scanning run: *quick* leaves both off, while *standard* and *deep* turn them on unless the config sets them.

### TLS / SSL Analysis

QU.I.R.K. uses sslyze as its primary TLS engine, with a fallback scanner for hosts where sslyze fails or is unavailable. For each TLS endpoint whose certificate has an RSA, ECDSA, Ed25519 or Ed448 key, it records:

- Certificate public key algorithm and key size
- Certificate issuer and expiry date
- Negotiated cipher suite and supported protocol versions

An ML-DSA (post-quantum) server certificate is not recorded yet: the scan of that endpoint ends in an error and stores no key algorithm, key size, expiry date or protocol-version list.

The CBOM, the dashboard and `quirk analyze-token` classify algorithms against a 120-entry table as *quantum-safe*, *quantum-vulnerable* or *unknown*; the CBOM records the result as a NIST quantum security level, where 0 means quantum-vulnerable. Names such as RSA, RSA-2048, RS256, ECDSA and ES256 are classified quantum-vulnerable, and the ML-KEM (FIPS 203) and ML-DSA (FIPS 204) parameter sets, such as ML-KEM-768 and ML-DSA-65, are classified quantum-safe. Known exceptions: the DNSSEC algorithm names ECDSAP256SHA256 and ECDSAP384SHA384 are currently rated quantum-safe, and RSASHA1, RSASHA256 and RSASHA512 are rated unknown.

### SSH Protocol Auditing

When the `ssh-audit` tool is installed and on `PATH`, QU.I.R.K. runs ssh-audit against each SSH service it finds and records its host key, key exchange (KEX), encryption and MAC algorithms. Each algorithm is classified for quantum vulnerability and appears in the CBOM. `ssh-audit` is an optional prerequisite that is not installed with QU.I.R.K. and is not a declared dependency. Without it, the scanner records only the server's SSH banner, and no SSH algorithms reach the CBOM.

### API & JWT Token Analysis

QU.I.R.K. fetches JWKS (JSON Web Key Set) documents from the base URLs you configure (at `/.well-known/jwks.json` or `/oauth/jwks`, or through `/.well-known/openid-configuration`) and records each key's algorithm (its key type when the key declares no `alg`) and, for RSA and EC keys, its key size. `quirk analyze-token` decodes a single token and reports its algorithm, flagging `alg:none` as CRITICAL. A scan run with a bearer credential (`--auth-bearer`) whose JWT declares `alg: none`, or declares no `alg`, also reports the CRITICAL finding "Bearer token is unsigned (alg:none)".

### Container Image Scanning

When the `syft` tool is installed (it is not installed with QU.I.R.K.), QU.I.R.K. runs it against each configured container image and keeps only the packages on a 25-name allowlist of cryptographic libraries, such as `openssl` and `libgcrypt`. It does not output the image's full package list (an SBOM), and these library records add no algorithm components to the CBOM.

### Source Code Scanning

When the `semgrep` tool is installed (it is not installed with QU.I.R.K.), QU.I.R.K. asks it for the `p/cryptography` ruleset against local source directories; repository URLs are rejected as invalid input. Each result is recorded with its file path and line number. Known defect: that ruleset is unavailable (the Semgrep registry returns HTTP 404 for it, checked 2026-10-13), so semgrep exits 7, QU.I.R.K. records a "ruleset unavailable" scan error, the source domain reads Not assessed, and source scanning produces no findings. When semgrep is not installed but `source_targets` is set, the phase is wrongly recorded as ran with no findings, so the source domain shows as assessed and clean; see the [Git connector page](connectors/git.md).

### Cloud Key Management Connectors

Native connectors for **AWS**, **Azure** and **GCP** enumerate the cryptographic configuration of cloud-managed key infrastructure (the GCP connector needs the `[cloud]` extra):

- **AWS**: ACM certificates, KMS keys, CloudFront distributions and ELB listeners
- **Azure**: Application Gateway TLS policies. Key Vault key enumeration is implemented but currently records no keys; see the [Azure connector page](connectors/azure.md)
- **GCP**: Cloud KMS keys, Cloud SQL TLS enforcement and Cloud Storage bucket encryption

In the CBOM, AWS KMS and GCP Cloud KMS key specifications are normalized to algorithm names (for example `RSA_2048` to RSA) and classified by the same classifier table as every other algorithm.

### Identity Protocol Scanning

**Kerberos** (needs the `[identity]` extra, which `[all]` does not include). QU.I.R.K. sends an unauthenticated AS-REQ over TCP (retrying over UDP if the TCP probe fails) to read the encryption types the KDC advertises, and rates them with a fixed map: the DES types are CRITICAL, RC4-HMAC and AES-128 are HIGH, and AES-256 types are SAFE. It also attempts an anonymous LDAP bind to read `msDS-SupportedEncryptionTypes`.

**SAML / OIDC.** QU.I.R.K. fetches SAML metadata and OIDC discovery documents and parses the signing certificates (SAML) and signing-algorithm declarations (OIDC) they contain.

**DNSSEC.** Using dnspython, QU.I.R.K. queries DNSKEY and DS records and rates each signing algorithm with a fixed map: for example, RSASHA1 and RSASHA1-NSEC3-SHA1 are CRITICAL, RSASHA256 is HIGH, and the ECDSA and EdDSA algorithms are SAFE. RFC 9905 ("Deprecating the Use of SHA-1 in DNSSEC Signature Algorithms") deprecates RSASHA1 and RSASHA1-NSEC3-SHA1; QU.I.R.K. rates RSASHA1 CRITICAL.

The weak Kerberos and DNSSEC results (for example RC4-HMAC, the DES types and RSASHA1) appear as findings in the dashboard and lower the Identity subscore; the CLI's findings file and reports do not list Kerberos or DNSSEC findings yet.

### CycloneDX Cryptographic Bill of Materials (CBOM)

Each completed scan writes a CycloneDX 1.6 CBOM in both JSON and XML formats (a `--check-in` hardware re-probe is not a full scan and writes none). The CBOM contains algorithm, certificate and protocol components. See the [CBOM guide](cbom-guide.md) for its structure and for what it can and cannot be cited as evidence of.

### Quantum-Readiness Scoring

The readiness score combines six subscores, each on a 0–25 scale:

1. **Hygiene**
2. **Modern TLS**
3. **Identity**
4. **Agility** — includes a PQC-hybrid bonus (`+8.0` under the default *balanced* profile) when the scan observes an X25519MLKEM768 key exchange. Known issue: when the scanning machine's `openssl` cannot test for it (for example, the LibreSSL build that macOS ships), a scan with any TLS target currently gets the bonus anyway, and the below-85 cap described next is not applied
5. **Data at Rest**
6. **Data in Motion**

The overall 0–100 score is computed over the subscores that had evidence to assess: a subscore with nothing to assess is excluded and the total is rescaled, rather than being counted as a full 25. The result is then scaled down when CRITICAL or HIGH findings are open, and kept below 85 when no PQC-hybrid key exchange was observed; the scorecard states why (for example, `1 open HIGH finding — score limited to 52 (computed 76)`). Three score profiles — *strict*, *balanced* (the default) and *lenient* — are selected with `--score-profile`; each applies a multiplier (1.4, 1.0 and 0.7) to the agility, identity, data-at-rest and data-in-motion weights. The rating is one of EXCELLENT (85 and above), GOOD, MODERATE, FAIR or POOR, or NOT_ASSESSED when nothing could be assessed.

### Data at Rest and Data in Motion

Connectors and scanners cover stored-data encryption (databases, S3 and Azure Blob object storage, Kubernetes, HashiCorp Vault) and in-transit TLS posture for email (SMTP, IMAP, POP3) and message brokers (Kafka, RabbitMQ, Redis); several of these need an optional extra (`[db]`, `[cloud]` or `[motion]`). Results from these surfaces feed the Data at Rest and Data in Motion subscores.

### Web Dashboard

`quirk serve` starts the local dashboard. Its sidebar offers these views: Executive Summary, Findings, Identity, Motion, Hardware, Data at Rest, Certificates, CBOM Viewer, Migration Roadmap, Exposure Map, Trends, Scan History, Sensors, Schedules and QRAMM Assessment.

### Reports

A scan writes an HTML report, a Markdown executive summary, scorecard and roadmap, and JSON findings alongside the CBOM. The DOCX report requires the `[docx]` extra (`python-docx`) and the PDF report requires Playwright (in the `[dashboard]` extra) and its Chromium browser; without them the HTML report is still written.

### Compliance Mapping and QRAMM

Most finding types carry control references for five frameworks — FIPS 140-3, HIPAA 45 CFR, ISO 27001:2022, PCI-DSS 4.0.1 and SOC 2 CC — and `quirk compliance status` lists each framework's version and last-verified date. Code-signing, SAML and OIDC findings carry none yet.

QU.I.R.K. also includes the QRAMM (Quantum Readiness Assurance Maturity Model) governance layer: a 120-question catalog, weakest-link scoring, and an evidence bridge that suggests answers for the CVI dimension from the latest scan's results. Its coverage map covers eight frameworks: NIST PQC Standards, NSM-10, CNSA 2.0, ISO 27001:2022, ETSI Quantum-Safe, PCI-DSS v4.0, Common Criteria and BSI TR-02102. *(QRAMM is a framework by CSNP — https://github.com/csnp/qramm. Used with attribution.)*

### Integrations and Distributed Scanning

- **Notifications** to webhook, email and Slack channels after a scheduled scan that finds new HIGH or CRITICAL findings or lowers the score past a threshold; **SIEM** output in CEF format over syslog (`quirk export --siem`, or after each scheduled scan when `export_after_scan` is set); and **ticketing** in Jira and ServiceNow (`quirk ticket create`)
- **Distributed scanning**: sensors scan isolated network segments and push results to a central console (`quirk sensor` and `quirk console`); `quirk console revoke-sensor` revokes a sensor
- `quirk doctor` runs a pre-scan health check

---

## Who Uses QU.I.R.K.?

**Security consultants** can use the CBOM, readiness score and reports as engagement deliverables.

**IT security engineers** can use the dashboard, including the Certificates view, for ongoing visibility into certificates and cryptographic posture.

**Compliance officers** can use the CBOM and the framework-tagged findings as inputs to their evidence packages.

---

## The Bottom Line

QU.I.R.K. is an agentless cryptographic inventory scanner: nothing is installed on the systems it scans. A scan produces a CycloneDX CBOM, a quantum-readiness score, a migration roadmap and reports, so that a post-quantum transition can start from a measured inventory.
