<picture>
<source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/0xD1g5/QU.I.R.K/v5.27.0/docs/brand/quirk-logo-dark.svg">
<source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/0xD1g5/QU.I.R.K/v5.27.0/docs/brand/quirk-logo.svg">
<img src="https://raw.githubusercontent.com/0xD1g5/QU.I.R.K/v5.27.0/docs/brand/quirk-logo.svg" alt="QU.I.R.K." height="64">
</picture>

[![Python Staleness Gate](https://img.shields.io/github/actions/workflow/status/0xD1g5/QU.I.R.K/python-staleness.yml?branch=main&label=staleness%20gate)](https://github.com/0xD1g5/QU.I.R.K/actions/workflows/python-staleness.yml)
[![PyPI version](https://img.shields.io/pypi/v/quirk-scanner.svg)](https://pypi.org/project/quirk-scanner/)
[![License: MIT](https://img.shields.io/github/license/0xD1g5/QU.I.R.K)](https://github.com/0xD1g5/QU.I.R.K/blob/v5.27.0/LICENSE)
[![Sigstore attested](https://img.shields.io/badge/sigstore-attested-blue)](https://github.com/0xD1g5/QU.I.R.K/blob/v5.27.0/docs/release-process.md#attestation-verification-for-downstream-consumers)
[![Security Policy](https://img.shields.io/badge/security-policy-blue)](https://github.com/0xD1g5/QU.I.R.K/blob/v5.27.0/SECURITY.md)

# QU.I.R.K. — v5.27.0

**Quantum Infrastructure Readiness Kit** is a consulting-grade cryptographic inventory and quantum-readiness assessment tool.

QU.I.R.K. is an agentless scanner that finds the cryptography running in an environment: TLS and SSH services, identity infrastructure (SAML, Kerberos, AD CS, JWT/OIDC), mail and message brokers, container images, source code, databases, cloud key management (AWS, Azure, GCP, HashiCorp Vault, Kubernetes), and network and OT/ICS hardware. QU.I.R.K. is dashboard-first and CLI-complete. Run a scan, review the results and download the deliverable in the browser, or script the same scans from the command line for automation, scheduling, sensors and repeat engagements.

It produces three things:

- a Cryptography Bill of Materials (CBOM) in CycloneDX JSON and XML;
- a 0–100 quantum-readiness score with six subscores;
- a prioritized migration roadmap, in client-ready PDF, DOCX and HTML reports.

> [!IMPORTANT]
> **Only scan systems you own or are explicitly authorized to assess.** QU.I.R.K. actively connects to the targets you give it: TLS handshakes, SSH negotiation, HTTP and SNMP requests, LDAP and Kerberos queries, and optional read-only OT/ICS probes. Get written authorization before scanning anyone else's infrastructure. The CLI and the dashboard's New Scan form can also check targets against an optional trusted-targets allowlist (`security.trusted_targets`), and the check covers `targets.include_ips` and the host-naming connector fields it recognizes, whether or not that connector is enabled. Known gaps in 5.28.0: a connector target field written as a single value instead of a list may not be checked, LDAP referrals returned to the AD CS, S/MIME and code-signing scanners are not checked, and a non-ASCII IPv6 zone id is not rejected. See the [Operator's Guide](https://github.com/0xD1g5/QU.I.R.K/blob/v5.27.0/docs/operators-guide.md).

![QU.I.R.K. dashboard — executive summary](https://raw.githubusercontent.com/0xD1g5/QU.I.R.K/v5.27.0/docs/images/dashboard-hero.png)
*The executive summary for a scan of the bundled chaos lab, which is deliberately weak. The score is capped at 20 because six CRITICAL findings are open, even though the computed score is 78. It shows the harvest-now-decrypt-later verdict, the first three remediation steps, and the six subscores.*

## For your role

**For the security consultant.** QU.I.R.K. produces the deliverable:
- a CycloneDX CBOM;
- a 0–100 quantum-readiness score with six subscores (Hygiene, Modern TLS, Identity, Agility, Data at Rest, Data in Motion);
- a written executive narrative;
- a prioritized remediation roadmap, in PDF, DOCX and HTML.

Nothing is installed on the systems being scanned.

**For the IT generalist.** Start with the simple question: *what crypto do we even have running?* QU.I.R.K. lists the TLS endpoints, SSH hosts, certificates, container images and cloud KMS keys it finds, and marks the quantum-vulnerable algorithms among them. Browse the results in the dashboard before committing to any remediation work.

**For the compliance officer.** QU.I.R.K. assigns network hardware a CNSA 2.0 remediation tier, maps its findings to FIPS 140-3 / CMVP, PCI-DSS 4.0.1, HIPAA, ISO 27001:2022 and SOC2 CC (the Trust Services Criteria), and tracks the US federal PQC transition deadlines (EO 14412). Each mapping is dated and re-verified on a CI-enforced review cadence. The output (CBOM JSON/XML, PDF reports) can be attached to an audit response.

## Quick Start

QU.I.R.K. supports Python 3.10 to 3.14. Python 3.15 is not supported yet, so check `python3 --version` first (Homebrew's default `python3` on macOS may already be 3.15). Use any of `python3.10` to `python3.14`; the example below uses `python3.12`.

Install into a virtual environment. This is recommended on every platform and **required** on Debian 12, Kali and other distributions that mark their system Python as externally managed (see the note below).

```bash
python3.12 -m venv .venv && source .venv/bin/activate   # any of python3.10 ... python3.14
pip install 'quirk-scanner[all]'
playwright install chromium    # needed for the PDF report; one-time download
quirk serve                    # opens the dashboard at http://127.0.0.1:8512
```

On Linux, Chromium also needs system libraries: run `playwright install-deps chromium` once, without a `sudo` prefix (Playwright asks for root itself; see [Installation](https://github.com/0xD1g5/QU.I.R.K/blob/v5.27.0/docs/installation.md#linux-ubuntu--debian) if you have no sudo). Without Chromium the scan still writes the HTML report and skips the PDF.

Then click **New Scan** in the sidebar, enter your targets and start the scan. Results appear in the dashboard when it finishes.

**Prefer a script?** Every scan also runs from the command line:

```bash
quirk init                     # writes a starter config.yaml — edit the targets
quirk --config config.yaml     # run the scan
```

> **Use a venv.** Debian 12, Kali and other distributions that mark their system Python as "externally managed" ([PEP 668](https://peps.python.org/pep-0668/)) reject a bare `pip install` into the system Python with `error: externally-managed-environment`. Keep the quotes around `'quirk-scanner[all]'`: zsh, the default shell on macOS 10.15 and later and on Kali's desktop images, otherwise treats `[all]` as a glob and fails with `no matches found`. Full walkthrough: [Installation → Parrot OS / Kali / Debian](https://github.com/0xD1g5/QU.I.R.K/blob/v5.27.0/docs/installation.md#parrot-os--kali--debian-pep-668).

The dashboard has no login by default and is meant for local use. To require one, run `quirk token generate --config config.yaml`, then start `quirk serve` from the same directory; see [Configuration → dashboard authentication](https://github.com/0xD1g5/QU.I.R.K/blob/v5.27.0/docs/configuration.md). For a walkthrough of each step, follow the [Getting Started guide](https://github.com/0xD1g5/QU.I.R.K/blob/v5.27.0/docs/getting-started.md).

## What QU.I.R.K. Scans

**Always on.** Every scan does these against its targets:
- **TLS / HTTPS**: certificate metadata and chain, cipher suites, protocol versions, and PQC-hybrid key exchange detection (X25519MLKEM768; needs a host `openssl` with ML-KEM).
- **SSH**: host key, key exchange, MAC and cipher algorithms, read by the `ssh-audit` binary. ssh-audit is not installed with QU.I.R.K.; without it on `PATH`, the scan records only each SSH server's banner.
- **Hardware fingerprinting**: for each SSH host, vendor, model and CNSA 2.0 remediation tier, from its SSH banner, its HTTP management page and, when neither identifies the vendor, an SNMP v2c `public` query (sent without `--enable-snmp` when the `[hw]` extra is installed). Firmware CVEs and end-of-life dates are matched against **built-in offline tables**.

**On by default in the `standard` and `deep` scan profiles** (the default profile is `standard`; `quick` leaves them off unless the config sets them (the starter config from `quirk init` does), and `enable_email: false` or `enable_broker: false` turns them off):
- **Email**: TLS / STARTTLS on the SMTP, submission, IMAP and POP3 ports of each host the TLS phase scanned. The dashboard flags STARTTLS-stripping risk on SMTP port 25.
- **Message brokers**: Kafka, RabbitMQ (AMQPS and management API) and Redis TLS on the same hosts and any `broker_targets`, plus the Azure Service Bus namespaces and AWS SQS regions you list.

**Opt-in.** Each of these is enabled with a config key or flag:

| Area | What it inspects | Needs |
|---|---|---|
| **JWT / OIDC APIs** | JWKS keys and signing algorithms, following OIDC discovery | `enable_jwt` |
| **OpenAPI specs** | Declared security schemes, plaintext servers, unauthenticated endpoints | `--openapi-spec` |
| **REST crypto fuzzing** | Active probing of an API's crypto posture, with an optional JWT algorithm-confusion probe (`--fuzz-jwt-alg-confusion`); asks for interactive confirmation and does not run without a terminal | `--fuzz` with a local `--openapi-spec` file, `[api]` extra |
| **SAML / OIDC identity providers** | IdP metadata signing and encryption certificates and algorithms | `enable_saml` |
| **Kerberos** | KDC encryption types, from an unauthenticated AS-REQ | `enable_kerberos`, `[identity]` extra |
| **AD CS** | CA certificates and templates, read over LDAP; checks templates for ESC1–ESC8 misconfigurations (ESC4/5/7/8 recorded as coverage gaps), which feed the score and the CBOM | `enable_adcs` |
| **S/MIME** | S/MIME certificates discovered via LDAP (reads no mail) | `enable_smime` |
| **Code signing** | Code-signing certificates from LDAP `userCertificate` and from the Code Signing EKU on leaf certificates the TLS phase captured | `--inventory-code-signing` |
| **DNSSEC** | DNSKEY / DS algorithms | `enable_dnssec` |
| **Container images** | Crypto libraries found in the image SBOM | `enable_container`, `syft` |
| **Source code** | Known defect in 5.28.0: the Semgrep `p/cryptography` ruleset is unavailable, so the source domain reads Not assessed | `enable_source`, `semgrep` |
| **Databases** | PostgreSQL / MySQL TLS enforcement | `enable_db` |
| **AWS** | ACM, KMS, CloudFront, ELB listeners, RDS and S3 encryption (EKS is under Kubernetes) | `enable_aws` / `enable_s3` |
| **Azure** | Application Gateway TLS policy and Blob encryption. Key Vault key scanning has a known defect and currently records no keys | `enable_azure` / `enable_blob` |
| **GCP** | Cloud KMS (including PQC algorithms), Cloud SQL TLS, GCS encryption | `enable_gcp` |
| **HashiCorp Vault** | Transit key types (including ML-DSA / SLH-DSA), PKI mounts, auth methods | `enable_vault` |
| **Kubernetes** | EKS / GKE / AKS secrets-encryption configuration; lists secret types but never reads secret data | `enable_k8s` with `k8s_provider` (`eks`, `gke` or `aks`) |
| **SNMP** | A sweep of the targets for device identity via SNMP v2c / v3 (auth + priv) | `--enable-snmp`, `[hw]` extra |
| **Modbus/TCP** | One read-only device-identification request | `--enable-modbus`, `[hw]` extra |
| **BACnet/IP** | Who-Is, then model name and firmware revision | `--enable-bacnet`, `[hw]` extra |

`[all]` covers the cloud, database, broker, email, AD CS, report and dashboard dependencies. It deliberately leaves out **`[hw]`** (SNMP, Modbus, BACnet), **`[api]`** (REST fuzzing) and **`[identity]`** (Kerberos). Install those explicitly, e.g. `pip install 'quirk-scanner[all,hw]'`. The [Configuration Reference](https://github.com/0xD1g5/QU.I.R.K/blob/v5.27.0/docs/configuration.md) documents every key.

## Output

- **Quantum-readiness score** (0–100) with six subscores: Hygiene, Modern TLS, Identity, Agility, Data at Rest, Data in Motion. The headline score (in the report and on the dashboard's Executive page) is capped while CRITICAL or HIGH findings remain open (the more CRITICAL findings, the lower the cap), and the trend, sensor-merge and per-segment scores apply that cap too. Known defects in 5.28.0: the dashboard and the report can still differ on the score for one scan, because some findings are raised on one surface only or at different severities. Those are the legacy TLS version finding (HIGH on the dashboard, LOW in the report), weak cipher suites (dashboard only; one such endpoint scores 84 in the report and 69 on the dashboard), undersized ECDSA certificate keys (HIGH in the report, MEDIUM on the dashboard), end-of-life crypto libraries in container images (report only), Kerberos weak-encryption and DNSSEC findings, and some other report-only HIGH or CRITICAL findings. Merged and notification scores also ignore a customized list of TLS-designated ports, and the scheduled-scan drift notification can show a different score than the dashboard's Trends page. No score reaches 100 unless a hybrid post-quantum key exchange is observed.
- **CBOM** in CycloneDX JSON and XML. Hardware is modelled as DEVICE components with FIRMWARE children.
- **Reports** in PDF, DOCX and HTML, plus CLI markdown. The HTML report (which the PDF prints), the DOCX report and the CLI executive summary take their executive content from one shared content model, and each carries a written executive narrative and a NOW / NEXT / LATER migration roadmap. The CLI also writes the roadmap on its own as `roadmap-*.md`. The PDF needs Playwright and its Chromium browser; without them the scan skips the PDF and still writes the HTML report.
- **Web dashboard** (`quirk serve`) with these views: executive summary, findings with a per-finding storyline, identity, data in motion, data at rest, certificates, hardware inventory, CBOM viewer, migration roadmap, quantum exposure map (endpoints linked by a shared key or a shared issuing CA), trends, scan history, scan comparison, schedules, sensors and QRAMM assessment, plus a New Scan page that starts a scan from the browser. Light and dark themes are included.
- **Distributed mode**: on-prem sensors scan isolated network segments and push their results to a central console. `quirk sensor merge` builds one CBOM and score from every endpoint of each sensor's latest push. A Windows sensor build ships as a GitHub Release asset.
- **Integrations**: notifications for scheduled scans and hardware lifecycle changes, SIEM CEF export, and Jira / ServiceNow ticket creation.

Four sample CBOMs live in [`examples/cbom/`](https://github.com/0xD1g5/QU.I.R.K/tree/v5.27.0/examples/cbom): TLS-only, identity, data at rest and data in motion. They are built from synthesized chaos-lab endpoints, not from a live scan.

## Documentation

| Guide | Description |
|-------|-------------|
| [Getting Started](https://github.com/0xD1g5/QU.I.R.K/blob/v5.27.0/docs/getting-started.md) | From install to first scan in three steps, using the dashboard |
| [Installation](https://github.com/0xD1g5/QU.I.R.K/blob/v5.27.0/docs/installation.md) | System requirements and install steps for macOS, Linux and Windows WSL |
| [Configuration Reference](https://github.com/0xD1g5/QU.I.R.K/blob/v5.27.0/docs/configuration.md) | Every config.yaml option and every flag in `quirk --help` |
| [Operator's Guide](https://github.com/0xD1g5/QU.I.R.K/blob/v5.27.0/docs/operators-guide.md) | Running engagements: scope, allowlists, scheduling, sensors |
| [Connector Guides](https://github.com/0xD1g5/QU.I.R.K/tree/v5.27.0/docs/connectors) | Setup for AWS, Azure, GCP, Kubernetes, HashiCorp Vault, databases, Docker and Git |
| [Cloud Console Deployment](https://github.com/0xD1g5/QU.I.R.K/blob/v5.27.0/docs/deployment-cloud-console.md) | Running the console on a cloud VM with internal sensors pushing to it |
| [Report Interpretation](https://github.com/0xD1g5/QU.I.R.K/blob/v5.27.0/docs/report-interpretation.md) | What the score, subscores and common findings mean, with Client Conversation notes |
| [CBOM Guide](https://github.com/0xD1g5/QU.I.R.K/blob/v5.27.0/docs/cbom-guide.md) | What a CBOM is and how to cite it as compliance evidence |
| [Chaos Lab Guide](https://github.com/0xD1g5/QU.I.R.K/blob/v5.27.0/docs/chaos-lab.md) | A Docker lab of **deliberately weak** crypto services to scan. Its compose file publishes almost every service port on all host interfaces, so we recommend running it on an isolated host that untrusted networks cannot reach |
| [Intelligence Schema](https://github.com/0xD1g5/QU.I.R.K/blob/v5.27.0/docs/intelligence-schema.md) | The `intelligence-*.json` output format |
| [Upgrade Guide](https://github.com/0xD1g5/QU.I.R.K/blob/v5.27.0/docs/upgrade-guide.md) | Cross-version upgrades with `quirk db migrate` |
| [Release Process](https://github.com/0xD1g5/QU.I.R.K/blob/v5.27.0/docs/release-process.md) | Publishing, and Sigstore attestation verification |

## What's New in v5.27

v5.27.0 is the first release since v5.25.0, so it carries both the v5.26 accessibility work and the v5.27 launch-readiness work. There are no score-model changes (`SCORING_VERSION` stays 3.0), so v5.27 scores are comparable with v5.25 scores.

- **Score gauges no longer draw mirrored.** A score of 20 out of 100 used to draw an arc that looked about 90% full.
- **Accessibility.** More dashboard badges meet WCAG AA contrast, and a dashboard table too wide or too tall for its space is a single Tab stop that the keyboard can scroll.
- **A brand identity.** The logo appears in this README, the report colophon, the PDF footer, the favicon and the dashboard sidebar, and the dashboard accent is now Ink-violet.
- **Every user-facing doc was reviewed claim by claim**, and the README hero image was retaken.
- **Security hardening** of configuration loading, URL fetching and sensor enrollment.
- **Upgrade notes.** `quirk serve` exits with an error when its config file exists but cannot be read, and protected API routes answer 503 in that state. `quirk sensor enroll` and `quirk sensor push` require an `https://` console URL for non-loopback hosts unless `--allow-insecure-console` is given, so re-enroll existing sensors that use an `http://` console.

The full per-release history is in [CHANGELOG.md](https://github.com/0xD1g5/QU.I.R.K/blob/v5.27.0/CHANGELOG.md).

## Install

- **PyPI:** `pip install 'quirk-scanner[all]'` (see Quick Start). Releases are published through PyPI Trusted Publishers with Sigstore attestations; verify them as described in [Release Process](https://github.com/0xD1g5/QU.I.R.K/blob/v5.27.0/docs/release-process.md#attestation-verification-for-downstream-consumers).
- **Windows sensor:** a zip with the frozen `quirk.exe` and PowerShell install and uninstall scripts is attached to each [GitHub Release](https://github.com/0xD1g5/QU.I.R.K/releases) from v5.12.0 onward. The installer registers a daily Scheduled Task. Known defect in 5.28.0: the installer writes a random sensor ID that the console does not recognise and gives the task no scan config, so the task's pushes are rejected until you set the console's sensor ID in the sensor config by hand; see [Operator's Guide → Windows sensor deployment](https://github.com/0xD1g5/QU.I.R.K/blob/v5.27.0/docs/operators-guide.md#88-windows-sensor-deployment-zip--scheduled-task).

> **No `curl | bash` installer.** This is deliberate. Piping HTTP into a shell bypasses the integrity guarantees of Sigstore attestations and Trusted Publishers. See [`docs/release-process.md`](https://github.com/0xD1g5/QU.I.R.K/blob/v5.27.0/docs/release-process.md).

<details>
<summary>Develop from source</summary>

```bash
git clone https://github.com/0xD1g5/QU.I.R.K
cd QU.I.R.K
python3 -m venv .venv && source .venv/bin/activate
pip install -e '.[dashboard]'
playwright install chromium
quirk --help
```

The editable install is for contributors. End users should install from PyPI.

</details>

## License

MIT. See [LICENSE](https://github.com/0xD1g5/QU.I.R.K/blob/v5.27.0/LICENSE).
