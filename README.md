# QU.I.R.K. — v4.0.0

**Quantum Infrastructure Readiness Kit** — consulting-grade cryptographic inventory and quantum-readiness assessment.

QU.I.R.K. is an agentless scanner that discovers crypto material across TLS endpoints, SSH services, JWT-issuing APIs, container images, Git repositories, AWS cloud resources, and Azure cloud resources. It produces a Cryptography Bill of Materials (CBOM) in CycloneDX JSON and XML, computes a quantum-readiness score (0–100), and generates a professional PDF report a consultant can hand directly to a client.

## Quick Start

```bash
git clone https://github.com/0xD1g5/QU.I.R.K.
cd QU.I.R.K.
python -m venv .venv && source .venv/bin/activate
pip install -e '.[dashboard]'
playwright install chromium
quirk --help
```

Then follow the [Getting Started guide](docs/getting-started.md) to run your first scan in under 10 minutes.

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

## What's New in v4.3

- **GCP Connector (Phase 26)** — Cloud KMS key classification (47-entry algorithm map including PQC), Cloud SQL TLS enforcement, and GCS CMEK detection.
- **Database Encryption Detection (Phase 27)** — PostgreSQL, MySQL, and RDS encryption posture surfaced via a new `data_at_rest` subscore.
- **Object Storage Audit (Phase 28)** — S3 SSE-S3/SSE-KMS/CMK, Azure Blob CMK/platform-managed, GCS CMEK using zero duplicate API calls.
- **Kubernetes Secrets Inspection (Phase 29)** — EKS/GKE/AKS managed cluster encryption APIs; RBAC-403 graceful degradation.
- **HashiCorp Vault Connector (Phase 30)** — Transit key type classification (including ml-dsa/slh-dsa PQC positive), PKI mount CA cert auditing, and auth method risk tiering.
- **Trend Analysis (v4.3, Phase 31)** — `quirk/intelligence/trends.py` produces a session-over-session score delta plus per-severity new/resolved finding counts between the two most recent scan sessions. Surfaced via `GET /api/trends` and a new dashboard `/trends` tab. No new SQLite table — uses existing scanned_at grouping.

## License

Proprietary. All rights reserved.
