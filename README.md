[![Python Staleness Gate](https://img.shields.io/github/actions/workflow/status/0xD1g5/QU.I.R.K./python-staleness.yml?branch=main&label=CI)](https://github.com/0xD1g5/QU.I.R.K./actions/workflows/python-staleness.yml)
[![PyPI version](https://img.shields.io/pypi/v/qu-i-r-k.svg)](https://pypi.org/project/qu-i-r-k/)
[![License: MIT](https://img.shields.io/github/license/0xD1g5/QU.I.R.K.)](LICENSE)
[![Sigstore attested](https://img.shields.io/badge/sigstore-attested-blue)](docs/release-process.md#attestation-verification)
[![Security Policy](https://img.shields.io/badge/security-policy-blue)](SECURITY.md)

# QU.I.R.K. — v4.10.0

**Quantum Infrastructure Readiness Kit** — consulting-grade cryptographic inventory and quantum-readiness assessment.

QU.I.R.K. is an agentless scanner that discovers crypto material across TLS endpoints, SSH services, JWT-issuing APIs, container images, Git repositories, AWS cloud resources, and Azure cloud resources. It produces a Cryptography Bill of Materials (CBOM) in CycloneDX JSON and XML, computes a quantum-readiness score (0–100), and generates a professional PDF report a consultant can hand directly to a client.

## For your role

**For the security consultant.** QU.I.R.K. produces the deliverable you bill for: a CycloneDX CBOM, a 0–100 quantum-readiness score with four subscores (Hygiene, Modern TLS, Identity, Agility), and a client-ready PDF report. Point it at a client's TLS endpoints, SSH services, JWT-issuing APIs, and cloud accounts; hand back the findings and the prioritized remediation roadmap. No agents to deploy, no software for the client to install.

**For the IT generalist.** Start with the simple question — *what crypto do we even have running?* — and end with an answerable inventory. QU.I.R.K. walks your environment, names every TLS endpoint, SSH host, container image, and KMS key it can reach, and tells you which ones are quantum-vulnerable. The dashboard at `http://localhost:8512` lets you browse the findings interactively before you commit to any remediation work.

**For the compliance officer.** Quantum-readiness is on the audit radar (NIST PQC, CNSA 2.0, FIPS 140-3 transitions). QU.I.R.K. ships compliance mappings against CMVP / FIPS 140-3 with documented staleness review cadence, surfaces algorithm classifications that map to those frameworks, and produces artifact-grade output (CBOM JSON/XML, PDF reports) you can attach to an audit response.

![QU.I.R.K. dashboard against the chaos lab](docs/images/dashboard-hero.png)
*Dashboard view of a scan against the chaos lab — quantum-readiness score, subscores, findings, and CBOM browser.*

<!-- TODO(LAUNCH-01): replace docs/images/dashboard-hero.png with a real screenshot captured against a running dashboard. The current file is a placeholder (1×1 transparent PNG) per Phase 85-05 deviation; capture a real screenshot post-merge from a live macOS arm64 run against the chaos lab `phaseA` (tls-weak) profile. -->

## Quick Start

Three commands to a working scan:

```bash
pip install qu-i-r-k[all]
quirk init
quirk --config config.yaml
```

Watch a 60-second run: `<asciinema-link-here>` *(recording is a manual post-merge task — see `.planning/phases/85-public-launch-polish/85-05-SUMMARY.md`)*.

Then follow the [Getting Started guide](docs/getting-started.md) for a walkthrough of the 3-step quickstart with explanations of each command.

## Documentation

| Guide | Description |
|-------|-------------|
| [Getting Started](docs/getting-started.md) | Zero to first scan in under 10 minutes |
| [Installation](docs/installation.md) | System requirements, macOS, Linux, Windows WSL |
| [Configuration Reference](docs/configuration.md) | All config.yaml options and CLI flags |
| [Connector Guides](docs/connectors/) | AWS, Azure, Docker, Git setup with credential templates |
| [Report Interpretation](docs/report-interpretation.md) | What every score and finding means, client conversation guide |
| [CBOM Guide](docs/cbom-guide.md) | What a CBOM is and how to cite it as compliance evidence |
| [Chaos Lab Operator Guide](docs/chaos-lab.md) | Lab profiles, port matrix, expected findings |
| [Intelligence Schema](docs/intelligence-schema.md) | `intelligence-*.json` output format reference |
| [Upgrade Guide](docs/upgrade-guide.md) | v4.x → v4.10 upgrade procedure with `quirk db migrate` |
| [Release Process](docs/release-process.md) | PyPI / GHCR / Homebrew tap publish procedure + Sigstore attestation verification |
| [UAT Test Series](docs/UAT-SERIES.md) | Full user acceptance testing guide — CLI, lab, dashboard |

## What QU.I.R.K. Scans

- **TLS/HTTPS endpoints** — certificate metadata, cipher suites, TLS version, chain trust
- **SSH services** — host key algorithms, KEX algorithms, MAC algorithms, cipher suites
- **JWT-issuing APIs** — algorithm discovery via JWKS and OIDC endpoints
- **Docker container images** — crypto libraries detected via Syft SBOM analysis
- **Git repositories / source code** — cryptographic API usage via Semgrep analysis
- **AWS** — ACM certificates, KMS key specs, CloudFront distributions, ELBv2 listeners
- **Azure** — Key Vault keys and certificates, Application Gateway TLS policies

## Output Artifacts

- **Quantum-readiness score** (0–100) — overall score with four subscores: Hygiene, Modern TLS, Identity, Agility
- **CBOM** in CycloneDX JSON + XML — inventory of all discovered cryptographic components
- **Web dashboard** at `http://localhost:8512` — interactive findings browser and CBOM graph
- **PDF report** — client-ready export from the dashboard

Sample CBOM fixtures live in [`examples/cbom/`](examples/) — one per major scan profile (TLS-only, identity, data-at-rest, data-in-motion), deterministic and committed to the repo.

## What's New in v4.3

- **GCP Connector (Phase 26)** — Cloud KMS key classification (47-entry algorithm map including PQC), Cloud SQL TLS enforcement, and GCS CMEK detection.
- **Database Encryption Detection (Phase 27)** — PostgreSQL, MySQL, and RDS encryption posture surfaced via a new `data_at_rest` subscore.
- **Object Storage Audit (Phase 28)** — S3 SSE-S3/SSE-KMS/CMK, Azure Blob CMK/platform-managed, GCS CMEK using zero duplicate API calls.
- **Kubernetes Secrets Inspection (Phase 29)** — EKS/GKE/AKS managed cluster encryption APIs; RBAC-403 graceful degradation.
- **HashiCorp Vault Connector (Phase 30)** — Transit key type classification (including ml-dsa/slh-dsa PQC positive), PKI mount CA cert auditing, and auth method risk tiering.
- **Trend Analysis (v4.3, Phase 31)** — `quirk/intelligence/trends.py` produces a session-over-session score delta plus per-severity new/resolved finding counts between the two most recent scan sessions. Surfaced via `GET /api/trends` and a new dashboard `/trends` tab. No new SQLite table — uses existing scanned_at grouping.

## Install From Other Channels

- **PyPI (recommended):** `pip install qu-i-r-k[all]` — see Quick Start above. The release is signed and attestation-verified via Sigstore + PyPI Trusted Publishers (`gh attestation verify`).
- **Homebrew (macOS):** `brew install 0xD1g5/quirk/quirk` — installs into an isolated `pipx`-style venv under `libexec`. *(Tap bootstrap is a manual post-release task; becomes functional once the `0xD1g5/homebrew-quirk` tap repo is published with the first signed sdist sha256.)* See [Homebrew Tap](docs/release-process.md#homebrew-tap-launch-02) for the bootstrap procedure.
- **Docker (GHCR, multi-arch):** `docker run ghcr.io/0xd1g5/quirk:latest --help` — `linux/amd64` + `linux/arm64`. See [Container Image](docs/release-process.md#container-image-launch-03).

> **No `curl | bash` installer.** This is a deliberate non-feature, not an oversight — see [`docs/release-process.md` → `curl | bash` Non-Decision](docs/release-process.md). Piping HTTP to a shell defeats the integrity guarantees of Sigstore attestations and PyPI Trusted Publishers; install via pip / brew / docker only.

<details>
<summary>Develop from source</summary>

```bash
git clone https://github.com/0xD1g5/QU.I.R.K.
cd QU.I.R.K.
python -m venv .venv && source .venv/bin/activate
pip install -e '.[dashboard]'
playwright install chromium
quirk --help
```

Editable install is for contributors — end users should prefer the PyPI / Homebrew / GHCR paths above.

</details>

## License

MIT. See [LICENSE](LICENSE).
