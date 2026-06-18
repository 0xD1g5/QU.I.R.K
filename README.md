[![Python Staleness Gate](https://img.shields.io/github/actions/workflow/status/0xD1g5/QU.I.R.K/python-staleness.yml?branch=main&label=CI)](https://github.com/0xD1g5/QU.I.R.K/actions/workflows/python-staleness.yml)
[![PyPI version](https://img.shields.io/pypi/v/quirk-scanner.svg)](https://pypi.org/project/quirk-scanner/)
[![License: MIT](https://img.shields.io/github/license/0xD1g5/QU.I.R.K)](LICENSE)
[![Sigstore attested](https://img.shields.io/badge/sigstore-attested-blue)](docs/release-process.md#attestation-verification)
[![Security Policy](https://img.shields.io/badge/security-policy-blue)](SECURITY.md)

# QU.I.R.K. — v5.8.0

**Quantum Infrastructure Readiness Kit** — consulting-grade cryptographic inventory and quantum-readiness assessment.

QU.I.R.K. is an agentless scanner that discovers crypto material across TLS endpoints, SSH services, JWT-issuing APIs, container images, Git repositories, and major cloud providers (AWS, Azure, GCP, HashiCorp Vault, Kubernetes). It produces a Cryptography Bill of Materials (CBOM) in CycloneDX JSON and XML, computes a quantum-readiness score (0–100) with six subscores, and generates client-ready PDF / DOCX / HTML reports. Distributed mode (v5.4+) splits scanning across on-prem sensors that push findings to a central console for merged reporting.

## For your role

**For the security consultant.** QU.I.R.K. produces the deliverable: a CycloneDX CBOM, a 0–100 quantum-readiness score with six subscores (Hygiene, Modern TLS, Identity, Agility, Data at Rest, Data in Motion), and client-ready PDF / DOCX / HTML reports. Point it at a client's TLS endpoints, SSH services, JWT-issuing APIs, and cloud accounts; hand back the findings, the prioritized remediation roadmap, and a written executive narrative. No agents to deploy, no software for the client to install.

**For the IT generalist.** Start with the simple question — *what crypto do we even have running?* — and end with an answerable inventory. QU.I.R.K. walks your environment, names every TLS endpoint, SSH host, container image, and KMS key it can reach, and tells you which ones are quantum-vulnerable. The dashboard at `http://localhost:8512` lets you browse the findings interactively before you commit to any remediation work.

**For the compliance officer.** Quantum-readiness is on the audit radar (NIST PQC, CNSA 2.0, FIPS 140-3 transitions). QU.I.R.K. ships compliance mappings against CMVP / FIPS 140-3 with documented staleness review cadence, surfaces algorithm classifications that map to those frameworks, and produces artifact-grade output (CBOM JSON/XML, PDF reports) you can attach to an audit response.

![QU.I.R.K. dashboard against the chaos lab](docs/images/dashboard-hero.png)
*Dashboard view of a scan against the chaos lab — quantum-readiness score, subscores, findings, and CBOM browser.*

## Quick Start

From a virtual environment (recommended on every platform, **required** on Debian/Ubuntu/Kali/Parrot — see note below):

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install 'quirk-scanner[all]'
quirk init
quirk --config config.yaml
```

> **Use a venv.** Modern Debian-based distros (Ubuntu 23.04+, Kali, Parrot) enforce [PEP 668](https://peps.python.org/pep-0668/) and reject a bare `pip install` into the system Python with `error: externally-managed-environment`. Installing into the `.venv` above avoids this. Keep the quotes around `'quirk-scanner[all]'` — zsh (the default shell on macOS, Kali, and Parrot) otherwise treats `[all]` as a glob and fails with `no matches found`. Full Parrot/Kali walkthrough: [Installation → Parrot OS / Kali / Debian](docs/installation.md#parrot-os--kali--debian-pep-668).

Then follow the [Getting Started guide](docs/getting-started.md) for a walkthrough with explanations of each command.

## Documentation

| Guide | Description |
|-------|-------------|
| [Getting Started](docs/getting-started.md) | Zero to first scan in under 10 minutes |
| [Installation](docs/installation.md) | System requirements, macOS, Linux, Windows WSL |
| [Configuration Reference](docs/configuration.md) | All config.yaml options and CLI flags |
| [Connector Guides](docs/connectors/) | AWS, Azure, Docker, Git setup with credential templates |
| [Cloud Console Deployment](docs/deployment-cloud-console.md) | Run the console on a cloud VM (Linode/EC2/GCP) with internal sensors pushing in — hardened, with ready-to-use `deploy/` files |
| [Report Interpretation](docs/report-interpretation.md) | What every score and finding means, client conversation guide |
| [CBOM Guide](docs/cbom-guide.md) | What a CBOM is and how to cite it as compliance evidence |
| [Chaos Lab Operator Guide](docs/chaos-lab.md) | Lab profiles, port matrix, expected findings |
| [Intelligence Schema](docs/intelligence-schema.md) | `intelligence-*.json` output format reference |
| [Upgrade Guide](docs/upgrade-guide.md) | Cross-version upgrade procedure with `quirk db migrate` |
| [Release Process](docs/release-process.md) | PyPI / GHCR / Homebrew tap publish procedure + Sigstore attestation verification |
| [UAT Test Series](docs/UAT-SERIES.md) | Full user acceptance testing guide — CLI, lab, dashboard |

## What QU.I.R.K. Scans

- **TLS/HTTPS endpoints** — certificate metadata, cipher suites, TLS version, chain trust, PQC-hybrid KEM detection
- **SSH services** — host key algorithms, KEX algorithms, MAC algorithms, cipher suites
- **JWT-issuing APIs** — algorithm discovery via JWKS and OIDC endpoints; query-param API-key auth supported
- **Email protocols** — SMTP/SMTPS, submission, IMAP/IMAPS, POP3/POP3S with STARTTLS-stripping detection
- **Message brokers** — Kafka, RabbitMQ AMQPS, Redis TLS
- **Docker container images** — crypto libraries detected via Syft SBOM analysis; signature/attestation verification
- **Git repositories / source code** — cryptographic API usage via Semgrep analysis
- **Code-signing posture** — LDAP-based certificate discovery + EKU classification
- **AWS** — ACM certificates, KMS key specs, CloudFront distributions, ELBv2 listeners
- **Azure** — Key Vault keys and certificates, Application Gateway TLS policies
- **GCP** — Cloud KMS algorithm classification (incl. PQC), Cloud SQL TLS enforcement, GCS CMEK
- **HashiCorp Vault** — Transit key types (incl. ml-dsa / slh-dsa), PKI mounts, auth method risk
- **Kubernetes** — EKS / GKE / AKS managed cluster encryption APIs
- **Databases & object storage** — PostgreSQL / MySQL / RDS at-rest encryption; S3 / Blob / GCS CMEK posture
- **Network devices / hardware fingerprinting** — SSH banner, HTTP management interface, and SNMP probes (pysnmp, requires `[hw]` extras) classify hardware vendor, model, and CNSA 2.0 remediation tier; crypto-bridge detection flags hardware devices where upstream TLS mitigates a quantum-vulnerable on-device cipher

## Output Artifacts

- **Quantum-readiness score** (0–100) — overall score with six subscores: Hygiene, Modern TLS, Identity, Agility, Data at Rest, Data in Motion
- **CBOM** in CycloneDX JSON + XML — inventory of all discovered cryptographic components; hardware endpoints are promoted to a CycloneDX DEVICE parent component with FIRMWARE children for hardware/firmware crypto separation
- **Web dashboard** at `http://localhost:8512` — interactive findings browser, CBOM graph, trend analysis, score breakdowns
- **Reports** — client-ready PDF / DOCX / HTML / CLI markdown from one shared content model; written executive narrative for consultant deliverables
- **Distributed mode** — on-prem sensors scan isolated network segments, push findings to a central console which merges into a single CBOM + score (v5.4+)
- **Integrations** — notification fan-out, SIEM CEF dispatch, Jira / ServiceNow ticket creation on findings (v5.3+)

Sample CBOM fixtures live in [`examples/cbom/`](examples/) — one per major scan profile (TLS-only, identity, data-at-rest, data-in-motion), deterministic and committed to the repo.

## What's New in v5.8

Highlights from the v5.x series — see [CHANGELOG.md](CHANGELOG.md) for the full per-release breakdown.

- **SNMP hardware fingerprinting + CBOM DEVICE/FIRMWARE hierarchy (v5.8)** — SSH banner → HTTP management interface → SNMP cascade classifies network hardware vendor, model, and CNSA 2.0 remediation tier; crypto-bridge detection; CBOM now emits a DEVICE parent component with FIRMWARE children; dashboard "Hardware Inventory" section in the CBOM tab; requires `[hw]` extras (pysnmp, not included in `[all]`).
- **Hardening + Hardware Compatibility (v5.7)** — SSRF cluster hardening, scoring correctness fixes, audit drain; hardware fingerprinting via SSH/HTTP banner with CNSA 2.0 remediation tier classification and crypto-bridge detection.
- **Public launch + Windows frozen build (v5.6)** — open-source public repo on GitHub with branch protection and gitleaks history scan; frozen Windows sensor binary (`quirk.exe`) + PowerShell Scheduled Task installer as a GitHub Release asset; port-scope discovery control (Common TLS / Top 1000 / All ports / Custom).
- **Distributed sensor hardening (v5.5)** — per-sensor opaque Bearer tokens, sensor revocation, failure-isolated auto-merge across sensors, weak-TLS chaos-lab targets.
- **On-prem sensor / console split (v5.4)** — scan per segment, push findings, merged into one CBOM + score; sensor / console enroll workflow.
- **Notification & integration surface (v5.3)** — notification fan-out, SIEM CEF dispatch, Jira / ServiceNow ticket integration on one shared SSRF-safe / secret-scrubbing layer; dashboard token auth.
- **Consulting-grade reporting (v5.2)** — one shared content model drives CLI / HTML / PDF / DOCX renderers; written executive narrative; corrected score sourcing across surfaces.
- **Authenticated scanning (v5.1)** — ephemeral credentials for cloud + JWT-issuing API scans; LDAP+TLS-EKU code-signing posture; folded into agility subscore.
- **PQC-hybrid scoring ceiling (v5.0)** — OQS-nginx PQC-hybrid chaos-lab profile with X25519MLKEM768 + ML-DSA-65; agility scoring gains a `+8.0` PQC-hybrid bonus that anchors the ceiling for post-quantum readiness.

## Install From Other Channels

- **PyPI (recommended):** `pip install 'quirk-scanner[all]'` — see Quick Start above. The release is signed and attestation-verified via Sigstore + PyPI Trusted Publishers (`gh attestation verify`).
- **Homebrew (macOS):** `brew install 0xD1g5/quirk/quirk` — installs into an isolated `pipx`-style venv under `libexec`. *(Tap bootstrap is a manual post-release task; becomes functional once the `0xD1g5/homebrew-quirk` tap repo is published with the first signed sdist sha256.)* See [Homebrew Tap](docs/release-process.md#homebrew-tap-launch-02) for the bootstrap procedure.
- **Docker (GHCR, multi-arch):** `docker run ghcr.io/0xd1g5/quirk:latest --help` — `linux/amd64` + `linux/arm64`. See [Container Image](docs/release-process.md#container-image-launch-03).

> **No `curl | bash` installer.** This is a deliberate non-feature, not an oversight — see [`docs/release-process.md` → `curl | bash` Non-Decision](docs/release-process.md). Piping HTTP to a shell defeats the integrity guarantees of Sigstore attestations and PyPI Trusted Publishers; install via pip / brew / docker only.

<details>
<summary>Develop from source</summary>

```bash
git clone https://github.com/0xD1g5/QU.I.R.K
cd QU.I.R.K
python -m venv .venv && source .venv/bin/activate
pip install -e '.[dashboard]'
playwright install chromium
quirk --help
```

Editable install is for contributors — end users should prefer the PyPI / Homebrew / GHCR paths above.

</details>

## License

MIT. See [LICENSE](LICENSE).
