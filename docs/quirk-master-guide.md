# QU.I.R.K. — Complete Guide

> **Generated file — do not edit.** This document is assembled from the five
> operator guides listed below, which remain the canonical sources. Edit those,
> then regenerate:
>
> ```bash
> .venv/bin/python -m scripts.build_master_guide > docs/quirk-master-guide.md
> ```
>
> Editing this file directly loses the change on the next regeneration and puts
> two contradictory descriptions of the same behaviour in the repository.

Five guides, 6,364 lines, in reading order.

| Part | Source | Covers |
|------|--------|--------|
| [Getting Started](#getting-started) | `docs/getting-started.md` | First scan, first report, and what the output means. |
| [Installation](#installation) | `docs/installation.md` | Platform-by-platform install, optional extras, and PDF-export prerequisites. |
| [Configuration](#configuration) | `docs/configuration.md` | Every config key, connector, integration and environment variable. |
| [Operator's Guide](#operators-guide) | `docs/operators-guide.md` | Running scans in anger: per-scanner reference, troubleshooting, sensors, hardware. |
| [Administration](#administration) | `docs/admin-guide.md` | Console deployment, sensor enrolment, token lifecycle and hardening. |

Guides deliberately **not** merged here, because they are reference rather than
operation: [`chaos-lab.md`](chaos-lab.md), [`report-interpretation.md`](report-interpretation.md),
[`architecture.md`](architecture.md), [`error-codes.md`](error-codes.md) (generated),
and the connector guides under [`connectors/`](connectors/).

---

## Contents

- **[Getting Started](#getting-started)**
  - [3-step quickstart](#3-step-quickstart)
  - [Prerequisites](#prerequisites)
  - [1. Install](#1-install)
  - [2. First Scan](#2-first-scan)
  - [3. Open the Dashboard](#3-open-the-dashboard)
  - [4. Export a PDF](#4-export-a-pdf)
  - [5. Analyze a Bearer Token (standalone)](#5-analyze-a-bearer-token-standalone)
  - [6. Analyze an OpenAPI Spec](#6-analyze-an-openapi-spec)
  - [Optional: Hardware Scanning](#optional-hardware-scanning)
  - [Catalog Status Commands](#catalog-status-commands)
  - [Report Branding Quickstart (v5.23+)](#report-branding-quickstart-v523)
  - [Next Steps](#next-steps)
- **[Installation](#installation)**
  - [System Requirements](#system-requirements)
  - [macOS](#macos)
  - [Linux (Ubuntu / Debian)](#linux-ubuntu-debian)
  - [Docker on Linux (chaos lab only)](#docker-on-linux-chaos-lab-only)
  - [Parrot OS / Kali / Debian (PEP 668)](#parrot-os-kali-debian-pep-668)
  - [Windows (WSL2)](#windows-wsl2)
  - [Optional Dependencies](#optional-dependencies)
  - [Verify Installation](#verify-installation)
  - [Next Steps](#next-steps-1)
- **[Configuration](#configuration)**
  - [Assessment Block (required)](#assessment-block-required)
  - [Report Block (Phase 200, v5.23 — RPT-01/RPT-02/RPT-03/RPT-04)](#report-block-phase-200-v523-rpt-01rpt-02rpt-03rpt-04)
  - [Scan Block](#scan-block)
  - [Timeout & Retry Policy (v4.5+)](#timeout-retry-policy-v45)
  - [Targets Block](#targets-block)
  - [Connectors Block](#connectors-block)
  - [OpenAPI Spec Analysis (`[api]` extras)](#openapi-spec-analysis-api-extras)
  - [Authenticated Scanning (ephemeral credentials)](#authenticated-scanning-ephemeral-credentials)
  - [REST Fuzzing (active crypto-posture probes)](#rest-fuzzing-active-crypto-posture-probes)
  - [Output Block](#output-block)
  - [Intelligence Block](#intelligence-block)
  - [Remediation Aliases (v5.18+ — Phase 179)](#remediation-aliases-v518-phase-179)
  - [Scan Profiles (`--profile` flag)](#scan-profiles---profile-flag)
  - [Port Scope (v5.6+ — Phase 121)](#port-scope-v56-phase-121)
  - [CLI Flag Reference](#cli-flag-reference)
  - [Dashboard Authentication (Phase 102, AUTH-01..03)](#dashboard-authentication-phase-102-auth-0103)
  - [Vertical Editions (v5.6+)](#vertical-editions-v56)
  - [Minimal Valid Configuration](#minimal-valid-configuration)
  - [Full Reference Configuration](#full-reference-configuration)
  - [Notifications (v5.3+)](#notifications-v53)
  - [SIEM Export (syslog/CEF)](#siem-export-syslogcef)
  - [Jira Ticketing (v5.3+)](#jira-ticketing-v53)
  - [ServiceNow Ticketing (v5.3+)](#servicenow-ticketing-v53)
  - [Compliance Frameworks](#compliance-frameworks)
  - [Firmware CVE Catalog Staleness Cadence (Phase 142)](#firmware-cve-catalog-staleness-cadence-phase-142)
  - [OT/ICS Recurring-Scan Cadence Floor (v5.13+ — Phase 156)](#otics-recurring-scan-cadence-floor-v513-phase-156)
- **[Operator's Guide](#operators-guide)**
  - [1. Install](#1-install-1)
  - [2. Configure](#2-configure)
  - [3. Scan](#3-scan)
  - [4. Validation / Smoke Test](#4-validation-smoke-test)
  - [5. Troubleshooting](#5-troubleshooting)
  - [6. Per-Scanner Reference](#6-per-scanner-reference)
  - [7. Compliance Map Maintenance](#7-compliance-map-maintenance)
  - [8. Distributed Sensor Deployment](#8-distributed-sensor-deployment)
  - [9. Hardware Scanning](#9-hardware-scanning)
  - [10. Discovery Liveness Pre-Pass](#10-discovery-liveness-pre-pass)
  - [11. Chunked Discovery Progress and Per-Batch Scaling](#11-chunked-discovery-progress-and-per-batch-scaling)
  - [12. OT/ICS Recurring-Scan Safety](#12-otics-recurring-scan-safety)
  - [13. Discovery Batch Resume](#13-discovery-batch-resume)
  - [14. Ticketing Integration](#14-ticketing-integration)
  - [15. Remediation Tracking Scope (v5.18+ — Phase 179)](#15-remediation-tracking-scope-v518-phase-179)
  - [16. Closure Verification (v5.18+ — Phase 180-181)](#16-closure-verification-v518-phase-180-181)
  - [17. Rating Band Severity Floor (Phase 184.4, SCORE-04/SCORE-05)](#17-rating-band-severity-floor-phase-1844-score-04score-05)
  - [18. SPKI Fingerprint Capture and Key Reuse (Phase 191, SPKI-01/SPKI-02)](#18-spki-fingerprint-capture-and-key-reuse-phase-191-spki-01spki-02)
  - [19. Finding Storyline Drawer (Phase 202, v5.23 — STORY-01/STORY-02)](#19-finding-storyline-drawer-phase-202-v523-story-01story-02)
- **[Administration](#administration)**
  - [Prerequisites](#prerequisites-6)
  - [1. Deploy the Console](#1-deploy-the-console)
  - [2. Enroll Sensors](#2-enroll-sensors)
  - [3. Manage Sensor Auth](#3-manage-sensor-auth)
  - [3.5 Hardening Environment Variables](#35-hardening-environment-variables)
  - [4. SNMP Setup](#4-snmp-setup)


---

# Getting Started

*First scan, first report, and what the output means.*

Zero to first scan in under 10 minutes.

---

### 3-step quickstart

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install 'quirk-scanner[all]'
quirk init
quirk --config config.yaml
```

> **Use a venv + quote the extras.** Debian-based distros (Ubuntu 23.04+, Kali, Parrot) enforce [PEP 668](https://peps.python.org/pep-0668/) and reject a bare `pip install` with `externally-managed-environment`; the `.venv` avoids this. zsh (default on macOS, Kali, Parrot) treats an unquoted `[all]` as a glob and fails with `no matches found`, so keep the quotes. Full Parrot/Kali steps: [Installation → Parrot OS / Kali / Debian](#parrot-os--kali--debian-pep-668).

What each command does:

1. **`pip install 'quirk-scanner[all]'`** — installs the QU.I.R.K. distribution from PyPI (distribution name is `quirk-scanner`; the installed CLI binary is `quirk`). The `[all]` extra pulls in cloud (AWS, Azure, GCP), CBOM, database, motion (SMTP/IMAP/AMQP/Kafka TLS), Redis, dashboard, AD CS, DOCX, notification, and ticketing support. It excludes `[identity]` (impacket downgrades cryptography), `[api]` (schemathesis active fuzzer is opt-in), and `[hw]` (pysnmp hardware scanning is opt-in due to dependency size). Wheels are Sigstore-attested via PyPI Trusted Publishers; verify with `gh attestation verify` (see [release-process.md](release-process.md)).
2. **`quirk init`** — writes a starter `config.yaml` to the current directory with sensible defaults pre-populated with the `127.0.0.1` loopback target. Edit the `targets` section to point at your network before running a real scan.
3. **`quirk --config config.yaml`** — runs the scan against the configured targets. For a single host this completes in under 30 seconds; cloud scans take longer depending on account size. Results are written to `./quirk-output/`.

Once the scan is finished, run `quirk serve` and open [http://localhost:8512](http://localhost:8512) to browse the dashboard.

---

### Prerequisites

Before you begin:

- **Python 3.10 or higher** — check with `python3 --version`
- **Docker Desktop** — optional, only needed for the [chaos lab](chaos-lab.md)
- **Homebrew** *(macOS, optional alternative to pip)* — `brew install 0xD1g5/quirk/quirk` installs into a `pipx`-style venv

---

### 1. Install

The PyPI install in the 3-step quickstart above is the recommended path. For developers contributing to QU.I.R.K., an editable install is documented in the root `README.md` under *Develop from source*.

For dashboard support and PDF export (already included in `[all]`):

```bash
pip install 'quirk-scanner[all]'
playwright install chromium   # Required for PDF export — one-time step
```

Verify the install:

```bash
quirk --help
```

---

### 2. First Scan

`quirk init` (step 2 of the quickstart) creates `config.yaml` in the current directory:

```bash
quirk init
```

Edit the `targets` section to point at your network, then run:

```bash
quirk --config config.yaml
```

QU.I.R.K. will probe the configured targets for TLS and SSH services. For a single host this completes in under 30 seconds. Results are written to `./quirk-output/`.

**Re-checking known hardware between full scans?** If you've already fingerprinted a hardware
fleet (§ Optional: Hardware Scanning below) and just want to see whether anything drifted, use
the lightweight `--check-in` re-probe instead of a full re-scan:

```bash
quirk --config config.yaml --check-in
```

It re-probes only the devices QU.I.R.K. already knows about and never produces a new readiness
score — see `docs/operators-guide.md` §9.9 for the full behavior.

---

### 3. Open the Dashboard

```bash
quirk serve
```

The dashboard opens automatically at [http://localhost:8512](http://localhost:8512). Browse findings, explore the CBOM graph, and review the quantum-readiness score.

---

### 4. Export a PDF

In the dashboard, click **Export PDF** in the top-right corner. The report is saved to your downloads folder — ready to hand to a client.

---

---

### 5. Analyze a Bearer Token (standalone)

The `quirk analyze-token` command decodes and classifies a JWT or bearer token without running a full scan. Use it to inspect algorithm strength, expiry, and quantum-safety posture — or to gate CI pipelines on dangerous `alg:none` tokens.

```bash
# Positional token (short-lived use; avoid in scripts where argv is logged)
quirk analyze-token "eyJhbGciOiJSUzI1NiJ9...."

# @file reference (preferred — keeps the token out of argv / shell history)
echo "eyJhbGciOiJSUzI1NiJ9...." > /tmp/token.txt
quirk analyze-token @/tmp/token.txt

# Stdin (e.g. piped from a secrets manager CLI)
echo "eyJhbGciOiJSUzI1NiJ9...." | quirk analyze-token -

# Machine-readable JSON output (for CI integration)
quirk analyze-token @/tmp/token.txt --json
```

**Key behaviors:**

- **`alg:none` detection** — tokens with algorithm `none` (case-insensitive: `none`, `NONE`, `None`, `NonE`) print a **CRITICAL** banner and exit with code `1`. This lets you fail a pipeline on a dangerous unsigned token:
  ```bash
  quirk analyze-token @/tmp/token.txt || { echo "Token rejected — CRITICAL finding"; exit 1; }
  ```
- **Opaque tokens** — if the input is not a recognizable JWT (e.g. an API key or opaque session token), the command prints an INFO message and exits `0`. It does not error out.
- **`--json` output** — emits a JSON object with keys: `alg`, `is_alg_none`, `expired`, `exp`, `nist_level`, `quantum_safety`.
- **No DB writes** — the token is never persisted to `quirk.db`, the CBOM, or log files.

---

### 6. Analyze an OpenAPI Spec

Pass `--openapi-spec` to include an OpenAPI/Swagger spec in a scan. QUIRK inventories the spec's declared security schemes, plaintext `http://` server URLs, and unauthenticated path operations:

```bash
# Local file (default; no network required)
quirk --config config.yaml --openapi-spec docs/openapi.yaml

# URL within your configured scan scope (scope-gated; out-of-scope URLs are rejected)
quirk --config config.yaml --openapi-spec https://api.acme.com/openapi.json
```

**Security hardening applied by the scanner:**

- **SSRF guard** — any `$ref` pointing to an external or internal-network address (e.g. `http://169.254.169.254/`) raises a `SpecParsingError` *before* the validator sees the document. No outbound request is made.
- **10 MB size cap** — specs larger than 10 MB are rejected before parsing. This prevents billion-laughs and oversized-YAML denial-of-service attacks.
- **Scope gate** — spec URLs must start with a configured `targets.fqdns` entry. Out-of-scope URLs are rejected before any network request.
- **Graceful degradation** — if the `[api]` extras group is not installed, the scanner returns a single advisory finding (`missing_extra`) and continues; no error is raised.

Install the `[api]` extras group to enable spec validation:

```bash
pip install "quirk-scanner[api]"
# installs openapi-spec-validator (spec validation) + schemathesis (active REST fuzzing)
```

> **Note:** `pip install 'quirk-scanner[all]'` does **not** include `[api]` — the `[api]` group bundles `schemathesis`, an active REST fuzzer that requires explicit operator opt-in, so it is deliberately kept out of `[all]`. A CI guard (`tests/test_install_all_excludes_schemathesis.py`) enforces this boundary.

---

### Optional: Hardware Scanning

Hardware scanning (SNMP fingerprinting, SSH/HTTP banner analysis for vendor/model/CNSA 2.0
tier classification) requires the `[hw]` extras, which are **not included** in `[all]` due to
the size of the pysnmp dependency:

```bash
pip install 'quirk-scanner[hw]'
```

With `[hw]` installed, QU.I.R.K. will probe network devices via SNMP (sysDescr, sysName,
sysObjectID) in addition to SSH banner and HTTP management interface fingerprinting, classifying
each discovered device with a CNSA 2.0 remediation tier.

Fingerprinted devices are also checked against QU.I.R.K.'s curated, NVD-cited firmware CVE
catalog — an advisory-only signal that never affects your readiness score. See
`docs/operators-guide.md` §9.5 for details.

---

### Catalog Status Commands

QU.I.R.K. ships several curated data catalogs (compliance mappings, QRAMM governance model,
firmware CVE table), each with its own `status` command to confirm freshness before a client
engagement:

```bash
quirk compliance status   # PCI-DSS/HIPAA/FIPS 140-3/SOC2/ISO 27001 mapping freshness
quirk qramm status        # QRAMM CSNP governance model freshness
quirk cve status          # firmware CVE catalog freshness (30-day cadence)
```

All three print a `Last Verified` date and a FRESH/STALE verdict, and exit `1` if stale — safe
to wire into pre-engagement scripts or CI.

---

### Report Branding Quickstart (v5.23+)

Want your firm's logo and client name on the report cover instead of the default look? Add a
`report:` block to `config.yaml` (see [Configuration Reference](#report-block-phase-200-v523--rpt-01rpt-02rpt-03rpt-04)),
or save it once and reuse it on every future engagement:

```bash
quirk report profile save housestyle --config config.yaml
quirk --config config.yaml --report-profile housestyle
```

---

### Next Steps

- [Installation](#installation) — full install options, Windows WSL, system requirements
- [Configuration Reference](#configuration) — all `config.yaml` options and CLI flags
- [Connector Guides](connectors/) — scan AWS, Azure, Docker containers, or Git repos
- [Upgrade Guide](upgrade-guide.md) — moving from v4.x to v4.10 (`quirk db migrate`)
- [Sample CBOM fixtures](../examples/) — deterministic CBOM outputs to inspect without running a scan


---

# Installation

*Platform-by-platform install, optional extras, and PDF-export prerequisites.*

Full installation reference for all supported platforms.

---

### System Requirements

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python 3.10 or higher | — | Check: `python3 --version` |
| pip | 21.3 or higher | Required for self-referential extras resolution (used by `pip install 'quirk-scanner[all]'`); pip 22.2+ recommended for the `--report` JSON test in CI |
| git | Any recent version | Required to clone the repo |
| Docker | Optional | Required only for the chaos lab. **Docker Desktop** on macOS/Windows; **Docker Engine + Compose plugin** on Linux — see [Docker on Linux](#docker-on-linux-chaos-lab-only) |
| Free disk (chaos lab) | ~25 GB | Only if running the chaos lab: its images total ~20 GB, the `multihost` prober alone is ~3.5 GB. The scanner itself needs ~2 GB |
| OS (for PDF export) | macOS 10.15+, Ubuntu 20.04+, Windows 10 via WSL2 | Playwright Chromium requirement |

---

### macOS

**Install Python** (Homebrew recommended):

```bash
brew install python@3.12
```

**Clone and install:**

```bash
git clone https://github.com/0xD1g5/QU.I.R.K
cd QU.I.R.K
python3 -m venv .venv && source .venv/bin/activate
pip install -e '.[dashboard]'
playwright install chromium
```

Playwright installs Chromium to `~/Library/Caches/ms-playwright/` on macOS (one-time, approximately 150 MB).

> **Note:** The repository name has no trailing dot (`QU.I.R.K`, not `QU.I.R.K.`). The trailing-dot form caused a Windows checkout failure (Phase 117); the repo was renamed and the remote URL is the form shown above.

**Troubleshooting:**

- If `quirk` is not found after install, confirm your venv is activated: `source .venv/bin/activate`
- If `python3` is not found, ensure Homebrew Python is in your PATH. On Apple Silicon: `export PATH="/opt/homebrew/bin:$PATH"`; on Intel Macs: `export PATH="/usr/local/bin:$PATH"`
- macOS uses zsh by default, which treats `[...]` as a glob. Always quote extras in install commands (e.g. `pip install '.[dashboard]'`, `pip install 'quirk-scanner[all]'`) or zsh fails with `no matches found`.

**Verify:**

```bash
quirk --help
quirk serve --help
```

---

### Linux (Ubuntu / Debian)

**Install system packages:**

```bash
sudo apt-get update && sudo apt-get install -y python3 python3-pip python3-venv git
```

**Clone and install:**

```bash
git clone https://github.com/0xD1g5/QU.I.R.K
cd QU.I.R.K
python3 -m venv .venv && source .venv/bin/activate
pip install -e '.[dashboard]'
playwright install chromium
sudo playwright install-deps chromium   # Installs required system libraries (uses apt; needs sudo)
```

> **Note:** Playwright requires glibc 2.17 or higher. Ubuntu 20.04 and later meet this requirement. Ubuntu 18.04 is not supported for PDF export.

> **Debian / Kali / Parrot (PEP 668):** Recent Debian-based distros mark the system Python as
> *externally managed* and refuse `pip install` outside a virtual environment (error:
> `externally-managed-environment`). The `.venv` step above is therefore **mandatory**, not optional —
> always activate the venv before any `pip` or `quirk` command.

**Verify:**

```bash
quirk --help
quirk serve --help
```

**Verify properly (recommended on a fresh VM):**

`quirk --help` proves the console script installed; it does not prove the install
*works*. Report rendering in particular can fail silently — a scan will exit 0 and
write every artifact except the PDF if Chromium's system libraries are missing.

```bash
scripts/validate-fresh-install.sh --yes
```

Nine checks, each asserting an observable outcome rather than an exit code: a
Chromium that actually launches, a `report-*.pdf` carrying real PDF magic bytes,
and every dashboard download returning HTTP 200 with a non-empty body. It also
reports where reality diverged from this document. Run it only on a throwaway
machine — it installs system packages.

---

### Docker on Linux (chaos lab only)

Skip this unless you are running the chaos lab. The scanner itself needs no Docker.

The System Requirements table above says "Docker Desktop" for macOS and Windows —
**on Linux you want Docker Engine plus the Compose plugin instead.** Docker Desktop
for Linux exists but is not what the lab expects, and `docker-compose` (the old
standalone v1 binary) is not the same thing as the `docker compose` plugin the lab
scripts call.

```bash
sudo apt-get install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
  https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

**Run Docker without sudo** (the lab scripts assume this):

```bash
sudo usermod -aG docker "$USER"
```

Log out and back in — group membership is only applied at login. `newgrp docker`
works for the current shell if you would rather not.

**Verify:**

```bash
docker run --rm hello-world
docker compose version        # must succeed; `docker-compose version` is the wrong binary
```

> **Check your free disk before starting the lab.** Its images total roughly 20 GB
> and the `multihost` profile's prober image alone is ~3.5 GB. A VM sized for the
> scanner will run out of space partway through `docker pull`, which surfaces as a
> confusing mid-pull failure rather than a clear "out of disk" message. Give the
> volume 40 GB if you intend to run more than one profile.

See [Chaos Lab Operator Guide](chaos-lab.md) for profiles, ports and scanning.

---

### Parrot OS / Kali / Debian (PEP 668)

Debian-based security distros (Parrot, Kali) enforce [PEP 668](https://peps.python.org/pep-0668/):
the system Python is *externally managed*, so a bare `pip install quirk-scanner[all]` fails with
`error: externally-managed-environment`. The default shell on these distros is **zsh**, which also
glob-expands an unquoted `[all]` and fails with `zsh: no matches found`. Both problems are solved by
installing into a virtual environment and quoting the extras.

**1. System prerequisites:**

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip python3-full git build-essential libffi-dev
```

`build-essential` and `libffi-dev` are only needed if a dependency has to compile from source
(e.g. `cryptography` on an architecture without a prebuilt wheel); they are harmless to install
otherwise.

**2. Create and activate a virtual environment:**

```bash
mkdir -p ~/quirk && cd ~/quirk
python3 -m venv .venv
source .venv/bin/activate          # prompt now starts with (.venv)
```

Every `pip` and `quirk` command below must run with the venv active. In a new terminal, re-run
`cd ~/quirk && source .venv/bin/activate` first.

**3. Install from PyPI** (keep the quotes — required under zsh):

```bash
pip install --upgrade pip
pip install 'quirk-scanner[all]'
```

**4. Verify:**

```bash
quirk --version      # → QU.I.R.K. v<version>  (matches pyproject.toml)
quirk doctor         # health check: confirms the environment and lists optional tools
```

**5. Chromium + system libraries for PDF export:**

```bash
playwright install chromium
sudo playwright install-deps chromium
```

**Optional external tools** (`quirk doctor` flags these as missing — each is opt-in):

```bash
sudo apt install -y nmap     # richer host discovery (--discovery nmap)
pip install semgrep          # source-code crypto scanning
# syft (container scanning): https://github.com/anchore/syft#installation
```

**Common errors:**

| Symptom | Cause / fix |
|---------|-------------|
| `error: externally-managed-environment` | venv not active — re-run step 2 and confirm the `(.venv)` prefix |
| `zsh: no matches found: quirk-scanner[all]` | quotes dropped — use `'quirk-scanner[all]'` |
| `command not found: quirk` | venv not active in this terminal — `source ~/quirk/.venv/bin/activate` |
| `cryptography` / Rust build failure | install `build-essential libffi-dev` (step 1) and retry |

---

### Windows (WSL2)

QU.I.R.K. runs on Windows via WSL2. The dashboard is accessible from your Windows browser.

**1. Enable WSL2:**

```powershell
wsl --install
```

Restart when prompted. The default distro is Ubuntu.

**2. Set up Ubuntu 22.04 (recommended):**

If you want a specific version:

```powershell
wsl --install -d Ubuntu-22.04
```

**3. Inside WSL, follow the Linux instructions above.**

**4. Access the dashboard from Windows:**

`quirk serve` binds to `127.0.0.1:8512`. Open your Windows browser at [http://localhost:8512](http://localhost:8512).

**5. Chaos lab with Docker Desktop:**

If using the chaos lab, ensure Docker Desktop has WSL2 integration enabled:
Docker Desktop → Settings → Resources → WSL Integration → Enable for your distro.

---

### Optional Dependencies

Install only what you need:

| Capability | Install command |
|------------|----------------|
| All optional scanners (recommended for consultants) | `pip install 'quirk-scanner[all]'` — installs adcs + cbom + cloud + dashboard + db + docx + motion + notify + redis + tickets. That is **10 of the 17 extras**; see the row below for what it leaves out. Includes Playwright browser binaries via `[dashboard]` (~250 MB). |
| **What `[all]` does _not_ install** | Seven extras are excluded. `[identity]` and `[api]` are deliberate — see [Why `[all]` excludes `[identity]`](#why-all-excludes-identity) and the active-fuzzer opt-in. **`[hw]`** (pysnmp, pymodbus, bacpypes3 — hardware/SNMP/Modbus/BACnet scanning, and the chaos lab's `hwcompat` profile) and **`[kafka]`** (kafka-python) are simply not in `[all]`, which surprises people. `[broker]` needs only `redis`, already present; `[email]` has no dependencies at all; `[dev]` is build tooling. |
| Everything except `[identity]` | `pip install -e '.[all,hw,kafka,api]'` — the full scanner surface in one venv. Resolves cleanly. Add `,identity` only after reading the `[identity]` note below. |
| Web dashboard + PDF export | `pip install -e '.[dashboard]'` (included in Quick Start) |
| Identity surface scanners (Kerberos, SAML/OIDC, DNSSEC) | `pip install -e '.[identity]'` — installs `impacket`, `lxml`, `signxml`, `dnspython[dnssec]` |
| Container scanning | `pip install syft` (requires Syft CLI on PATH) |
| Source code scanning | `pip install semgrep` |
| AWS connector | Included in base install (boto3 is a core dependency) |
| Azure connector | Included in base install (azure-identity and azure-keyvault-* are core dependencies) |

#### Why `[all]` excludes `[identity]`

The `[identity]` extra pulls `impacket`, which transitively depends on `pyOpenSSL`. `[all]`
intentionally **excludes `[identity]`** to keep the default consultant install safe.

> **Corrected 2026-09-16 — the original reason for this exclusion no longer holds.** This section
> previously read: *"`pyOpenSSL`'s pin range forces a downgrade of the `cryptography` library that
> QUIRK ships with as a base dependency. That downgrade silently breaks the TLS scanner (loss of
> TLS 1.3 / X25519 cipher enumeration)."* That was almost certainly true when written — older
> `pyOpenSSL` releases did cap `cryptography` upward. **`pyOpenSSL` 26 requires
> `cryptography<47,>=46.0.0`, which is a floor, not a cap.** Measured in a virtualenv holding both
> `[all]` and `impacket`: `cryptography` resolved to 46.0.6 (above the `>=44.0` base pin),
> `pip check` reported no broken requirements, and a live scan enumerated `X25519MLKEM768` — the
> exact capability the old text said was lost.
>
> The exclusion is **kept** as a conservative default, and
> `tests/test_install_all_excludes_impacket.py` still guards it. What changed is that the two-venv
> split below is now a **fallback, not a requirement**.

**Try one virtualenv first.** On current dependency versions you can usually install everything
together:

```bash
pip install -e '.[all,hw,kafka,api,identity]'
pip check                                                    # expect: No broken requirements found
python -c "import cryptography; print(cryptography.__version__)"   # expect >= 44
```

If `pip check` reports a conflict, or `cryptography` resolves below 44, fall back to **two separate
virtual environments**:

```bash
# venv 1 — full scan surface (recommended default)
python3 -m venv .venv-quirk && source .venv-quirk/bin/activate
pip install 'quirk-scanner[all]'

# venv 2 — identity-only surface (deactivate the first venv first)
python3 -m venv .venv-quirk-identity && source .venv-quirk-identity/bin/activate
pip install 'quirk-scanner[identity]'
```

This isolation keeps the cryptography library in venv 1 at the version the TLS scanner
requires, while venv 2 can carry whatever version impacket's dependency chain resolves to.

**Verify rather than assume, in either arrangement.** `pip check` plus the `cryptography` version
print above is the test — the failure mode this section guards against is silent, so a green install
log is not evidence.

A CI regression test (`tests/test_install_all_excludes_impacket.py`) guards this exclusion;
attempts to add `quirk-scanner[identity]` to `[all]` will fail the test.

---

### Verify Installation

```bash
quirk --help         # Should show scan options
quirk serve --help   # Should show serve options
```

If both commands display help output, the installation is complete.

> **Coverage advisories.** If you enable a scanner whose optional extra is missing,
> QUIRK emits a single INFO advisory finding per skipped scanner instead of crashing.
> Each advisory names the exact `pip install quirk-scanner[<extra>]` command to run so you
> can opt in to that capability without re-installing the world.

---

### Next Steps

- [Getting Started](#getting-started) — zero to first scan in under 10 minutes
- [Configuration Reference](#configuration) — all `config.yaml` options
- [Connector Guides](connectors/) — AWS, Azure, Docker, Git


---

# Configuration

*Every config key, connector, integration and environment variable.*

QU.I.R.K. is configured through a `config.yaml` file in the working directory. Pass a custom path with `--config /path/to/config.yaml` to override the default location.

The file has six top-level blocks: `assessment`, `scan`, `targets`, `connectors`, `output`, and `intelligence`. Only the `assessment` block is required. All other blocks use sensible defaults.

---

### Assessment Block (required)

All four required keys appear in every report header and deliverable. `crown_jewels` is
optional.

| Key | Type | Example | Required | Description |
|-----|------|---------|----------|-------------|
| `name` | string | `"Quantum Crypto Readiness - ACME Corp"` | Yes | Assessment name — appears in all report headers |
| `data_classification` | string | `"confidential"` | Yes | One of: `public`, `internal`, `confidential`, `regulated` |
| `report_owner` | string | `"ACME Corp"` | Yes | Client name as it appears in the report |
| `timezone` | string | `"America/New_York"` | Yes | IANA timezone for report timestamps (e.g. `"Europe/London"`, `"UTC"`) |
| `crown_jewels` | list of strings | `["10.0.0.20", "payments.example.com"]` | No | Systems whose compromise actually matters. Highlighted on the dashboard's Quantum Exposure Map. Default `[]` |

```yaml
assessment:
  name: "Quantum Crypto Readiness - ACME Corp"
  data_classification: "confidential"
  report_owner: "ACME Corp"
  timezone: "America/New_York"
  # logo_path: /path/to/your-org-logo.png   # DEPRECATED fallback — see "Report Block" below.
  #   report.branding.logo_path is the preferred field as of Phase 200 (v5.23). This
  #   assessment.logo_path key is still honored when report.branding.logo_path is unset — it is
  #   not being removed — but new configs should set report.branding.logo_path instead.
  crown_jewels:
    - "10.0.0.20"
    - "payments.example.com"
```

#### `crown_jewels` (optional)

The systems whose compromise actually matters for this engagement — hosts, IPs, or FQDNs.
They render with an accent ring on the dashboard's **Quantum Exposure Map**, so the graph
shows what is at stake rather than only what is connected.

**This is declared, never inferred.** No probe can discover which system a client cares
about, so QU.I.R.K. does not guess. Leaving the list empty marks nothing — the map says so by
marking nothing rather than nominating a "most important" host it has no basis to choose.

Matching is on the **host portion** of an endpoint, so `"10.0.0.20"` marks that host on every
port it was found on. A certificate-authority hub node is never marked, whatever is declared:
a crown jewel is a system the client owns, not an issuer identity.

If the config cannot be read, nothing is marked. Marking the wrong node is worse than marking
none.

---

### Report Block (Phase 200, v5.23 — RPT-01/RPT-02/RPT-03/RPT-04)

Controls report branding (cover logo, client/engagement identity text), an operator-supplied
Jinja2 template override directory, and a named report profile. **The entire block is optional —
omitting it, or any individual key inside it, reproduces today's rendering exactly.** Every field
defaults to unset/`None` and is rendered only when present.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `branding.logo_path` | string | `null` | Path to a logo image file embedded on the HTML/PDF and DOCX cover. Preferred over the deprecated `assessment.logo_path` fallback — if both are set, `report.branding.logo_path` wins. An unreadable/missing file degrades gracefully to no logo (warning logged), never a crash. |
| `branding.client_name` | string | `null` | Client/organization name rendered in the cover identity block and the running header/footer, in addition to `assessment.report_owner`. |
| `branding.engagement_name` | string | `null` | Engagement label (e.g. `"Q3 2026 Crypto Assessment"`) rendered on the cover and running header/footer. |
| `branding.prepared_by` | string | `null` | "Prepared By" line on the cover identity block. |
| `branding.cover_date` | string | `null` | Free-form cover date label (e.g. `"September 2026"`), rendered verbatim — not parsed as a date. |
| `branding.confidentiality_line` | string | `null` | Confidentiality legend (e.g. `"CONFIDENTIAL — Internal Use Only"`) rendered on the cover and the running footer. |
| `template_dir` | string | `null` | Directory containing operator-authored `.j2` template overrides (only `.j2` files are consulted). Searched **first**, ahead of the packaged template, which remains the fallback for any template not present in this directory. Must be an existing, usable directory — see the error-code note below. Templates render inside a sandboxed Jinja2 environment (`SandboxedEnvironment`) unconditionally; see `docs/operators-guide.md`'s "Report template overrides" section for the full security posture. |
| `profile` | string | `null` | Name of a saved report profile (`~/.quirk/report_profiles/<name>.yaml`, or `$QUIRK_PROFILES_DIR` if set) to merge onto this config. See `docs/operators-guide.md` for `quirk report profile save\|list` and the `--report-profile` CLI flag. |

```yaml
report:
  branding:
    logo_path: /path/to/your-org-logo.png
    client_name: "Acme Corp"
    engagement_name: "Q3 2026 Crypto Assessment"
    prepared_by: "Security Team"
    cover_date: "September 2026"
    confidentiality_line: "CONFIDENTIAL — Internal Use Only"
  template_dir: /path/to/custom/templates
  profile: my-profile
```

#### Which surfaces render which fields

- **HTML/PDF and DOCX** render the full branding set, including the cover logo — cover identity
  block plus running header/footer identity text (client/engagement + confidentiality line).
- **CLI markdown (executive summary, scorecard) and the Rich console scan-summary table** render
  the identity text only (`client_name`, `engagement_name`, `prepared_by`, `cover_date`,
  `confidentiality_line`) — **no logo ever reaches a CLI surface.**

#### Path guard and error codes

Every report path field (`report.branding.logo_path`, `report.template_dir`, and the legacy
`assessment.logo_path` fallback) is validated at config-load time by one named guard,
`validate_report_path_field()`:

- **`QRK-CONFIG-003`** — raised when a path field contains a `".."` traversal segment, or when
  `report.template_dir` does not point at an existing, usable directory. This is a hard,
  load-time failure — the config never loads with a traversal-shaped or unusable `template_dir`.
- **`QRK-CONFIG-004`** — raised when `report.profile` (or a `quirk report profile save`/`list`
  invocation) names an invalid profile — profile names accept only letters, digits, hyphens, and
  underscores.
- **Asymmetric disposition for `logo_path` specifically:** a missing or unreadable logo file only
  **warns** and degrades to no logo on the affected surface — it does not fail config load. Only a
  traversal-shaped `logo_path` value fails hard; a legitimately-missing file does not.

See [`docs/error-codes.md`](error-codes.md) for the exact cause/fix text of both codes.

---

### Scan Block

Controls connection timeouts, concurrency, port selection, and TLS enumeration depth. All keys are optional — defaults are calibrated for typical enterprise networks.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `timeout_seconds` | int | `5` | Global connection timeout in seconds |
| `concurrency` | int | `200` | Maximum parallel workers (global cap) |
| `ports_tls` | list[int] | `[443, 8443, 9443, 10443, 4433, 5001, 636, 3269, 993, 995, 465, 6443, 2376, 5432, 3306, 1433, 8200]` | Ports probed for TLS/HTTP/SSH — the 17-port `CONSULTING_TLS_PORTS` list, shared with the CLI wizard and the dashboard's "Common TLS ports" scope (Phase 184.2, D-04). See below for the D-05 note on 5432/3306/8200. YAML values are coerced to `int` on load, so a quoted `"8443"` behaves identically to a bare `8443`; a non-numeric entry is rejected at load time with `QRK-CONFIG-001` (Phase 189, TRIAGE-04). |
| `tls_designated_ports` | list[int] | `[]` | Operator-declared ports that should be classified `"HTTP on TLS-designated port"` rather than `"Plaintext HTTP service detected"` when plaintext HTTP is found there, in addition to the well-known TLS set. Distinct from `ports_tls` above: `ports_tls` is the scan TARGET list (what gets probed), not a TLS-designation signal. (Phase 186, TRIAGE-176-02) Same coercion rule applies: quoted digit-strings are accepted, non-numeric entries raise `QRK-CONFIG-001` at load time (Phase 189, TRIAGE-04). |
| `include_sni` | bool | `true` | Send SNI extension in TLS handshakes |
| `tls_enum_mode` | string | `"fast"` | TLS enumeration depth: `off`, `fast`, `deep` |
| `fingerprint_timeout_seconds` | int | `2` | Per-target fingerprint timeout |
| `fingerprint_concurrency` | int | `200` | Fingerprint phase worker count |
| `tls_timeout_seconds` | int | `5` | TLS scan phase connection timeout |
| `tls_concurrency` | int | `150` | TLS scan phase worker count |
| `ssh_timeout_seconds` | int | `5` | SSH scan phase connection timeout |
| `ssh_concurrency` | int | `100` | SSH scan phase worker count |
| `hardware_history_retention_days` | int | `180` | Days of `hardware_devices` scan-history rows to retain per device (Phase 154, HWLC-03) |
| `hardware_drift_event_retention_days` | int | `365` | Days of `hardware_drift_events` rows to retain table-wide (Phase 157, HWLC-16) |

> **Note:** For large scans (1000+ hosts), reduce `concurrency` to `50` and use `--safe-mode` to prevent connection exhaustion.

```yaml
scan:
  timeout_seconds: 5
  concurrency: 200
  ports_tls: [443, 8443, 9443, 10443, 4433, 5001, 636, 3269, 993, 995, 465, 6443, 2376, 5432, 3306, 1433, 8200]
  include_sni: true
  tls_enum_mode: fast   # off|fast|deep
  fingerprint_timeout_seconds: 2
  fingerprint_concurrency: 200
  tls_timeout_seconds: 5
  tls_concurrency: 150
  ssh_timeout_seconds: 5
  ssh_concurrency: 100
  hardware_history_retention_days: 180
  hardware_drift_event_retention_days: 365
```

#### `hardware_history_retention_days` (Phase 154, HWLC-03)

Bounds how many days of `hardware_devices` scan-history rows QUIRK keeps **per device**
(identified by `host`/`port`). Unit is days; default is `180`.

- **Purge mechanism:** a **hard delete** (`DELETE ... synchronize_session=False`), run
  opportunistically at the end of each hardware scan run, scoped only to the `(host, port)`
  pairs present in that scan's own batch — it never sweeps the whole `hardware_devices` table
  and never touches devices not scanned this run.
- **No CLI purge command and no background worker.** Retention is enforced only as a
  side effect of running a hardware scan; there is no `quirk hardware purge` command and no
  scheduled/cron job that ages out rows independently.
- **Invalid values are skipped, not defaulted.** A zero, negative, or non-numeric value causes
  the purge to be **skipped entirely** for that run (a warning is logged) rather than silently
  falling back to `180` and deleting everything, or deleting nothing forever with no signal.
- **Not the same knob as `STALENESS_THRESHOLD_DAYS`.** The 180-day default deliberately does
  not reuse the project's 90-day catalog-freshness convention (see CLAUDE.md's "Staleness
  Review Cadence") — that constant governs whether a *reference catalog* (QRAMM model,
  compliance mappings, firmware CVE table) is stale, while `hardware_history_retention_days`
  governs how long an *engagement's own scan history* is retained. They are unrelated knobs
  that happen to both be day-counts.

#### `hardware_drift_event_retention_days` (Phase 157, HWLC-16)

Bounds how many days of `hardware_drift_events` rows QUIRK keeps **table-wide** (across every
device, not scoped to a single `(host, port)` pair). Unit is days; default is `365`.

- **Purge mechanism:** a table-wide calendar-cutoff sweep — `DELETE FROM hardware_drift_events
  WHERE detected_at < cutoff` — run once per scan, regardless of which devices that scan
  actually fingerprinted. Unlike `hardware_history_retention_days` (above), this purge is not
  scoped to the current scan's batch of devices; it evaluates every row in the table by age.
- **Not the same knob as `hardware_history_retention_days`, and deliberately so.**
  `hardware_history_retention_days` bounds per-device scan-snapshot history and is scoped to
  devices the scan actually touched this run. `hardware_drift_event_retention_days` bounds an
  append-only *event log* by age across the whole table. Sharing one knob between the two would
  mean an idle device's drift history gets purged (or preserved) on the wrong schedule —
  whichever schedule the *other* concern happened to be tuned for — so the two fields are kept
  fully independent.
- **Why 365 days:** matches this codebase's existing 365-day-cadence convention (see
  `quirk/compliance/__init__.py`, `quirk/scanner/bacnet_vendors.py`, `quirk/scanner/hardware_eol.py`)
  and gives a full year of drift history for year-over-year comparison during a long engagement.
- **Fail-closed behavior.** A non-integer, zero, or negative value causes the purge to be
  **skipped entirely** for that run (a warning is logged), never a wipe of the whole table and
  never a silent no-op with no log line. Invalid values never widen the deletion window.
- **No CLI purge command and no background worker.** Like `hardware_history_retention_days`,
  this purge runs automatically as a side effect of every scan — there is no separate command
  or cron job to schedule.

---

### Timeout & Retry Policy (v4.5+)

Phase 41 introduced canonical `[scan.timeouts]` and `[scan.retry]` sub-tables that supersede the
legacy flat fields. Every scanner — fingerprint, TLS, SSH, JWT, container, source, DNSSEC, SAML,
Kerberos, Vault, database, broker, email — reads its connection timeout and retry policy from
these sub-tables (canonical source: `quirk/config.py` `TimeoutsCfg` / `RetryCfg` dataclasses). The
flat fields documented above (`timeout_seconds`, `fingerprint_timeout_seconds`, `tls_timeout_seconds`,
`ssh_timeout_seconds`) remain readable for backward compatibility but emit `DeprecationWarning` on
read; new configurations should use the sub-tables.

#### `[scan.timeouts]` — per-scanner connection timeouts

| Slot | Type | Default (s) | Applies to |
|------|------|-------------|------------|
| `default_seconds` | int | `5` | Fallback for any scanner without a dedicated slot |
| `fingerprint_seconds` | int | `4` | Fingerprint phase TCP/banner probe |
| `tls_seconds` | int | `6` | TLS handshake / ciphersuite enumeration |
| `ssh_seconds` | int | `6` | SSH banner + KEX exchange |
| `jwt_seconds` | int | `10` | JWT/REST endpoint probes |
| `container_seconds` | int | `120` | Container image binary scans (per image) |
| `source_seconds` | int | `300` | Source-tree crypto scan (per repo) |
| `dnssec_seconds` | int | `10` | DNSSEC record + DS chain probe |
| `saml_seconds` | int | `10` | SAML metadata fetch |
| `kerberos_seconds` | int | `10` | Kerberos KDC probe |
| `vault_seconds` | int | `10` | HashiCorp Vault / KMS API call |
| `db_connect_seconds` | int | `5` | Database driver connect (Postgres, MySQL, …) |
| `broker_seconds` | int | `10` | Message broker probe (Kafka, RabbitMQ, Redis) |
| `email_seconds` | int | `10` | SMTP/IMAP/POP3 STARTTLS probe |

#### `[scan.retry]` — retry/backoff policy

| Slot | Type | Default | Description |
|------|------|---------|-------------|
| `retry_count` | int | `0` | Number of retries after the initial attempt (0 = no retry) |
| `backoff_base_seconds` | float | `1.0` | Initial backoff before the first retry |
| `backoff_max_seconds` | float | `5.0` | Backoff ceiling — exponential backoff caps here |

#### Deprecation notice

The legacy flat fields below are still accepted but emit `DeprecationWarning` on read:

| Legacy field | New canonical slot |
|--------------|--------------------|
| `scan.timeout_seconds` | `scan.timeouts.default_seconds` |
| `scan.fingerprint_timeout_seconds` | `scan.timeouts.fingerprint_seconds` |
| `scan.tls_timeout_seconds` | `scan.timeouts.tls_seconds` |
| `scan.ssh_timeout_seconds` | `scan.timeouts.ssh_seconds` |

Migrate at your earliest convenience — the flat fields will be removed in a future major release.

#### Overall scan upper-bound formula (D-10)

The total wall-clock upper bound for a single scan run is bounded by:

```
scan_upper_bound = (
  fingerprint_timeout * N_targets
  + tls_timeout       * N_tls_candidates
  + ssh_timeout       * N_ssh_candidates
  + max(jwt_timeout, container_timeout, source_timeout, ...) * N_connector_targets
) + 10s safety_margin
```

Where:
- `N_targets` = number of fingerprinted hosts
- `N_tls_candidates` = subset of targets with at least one TLS-eligible port open
- `N_ssh_candidates` = subset of targets with at least one SSH-eligible port open
- `N_connector_targets` = number of connector probes (JWT URLs, container images, source repos, etc.)
- The `max(...)` term reflects connector phases running in sequence — pick the longest active connector timeout
- `safety_margin` = 10s flat allowance for orchestration, report writing, and finalization

**Worked example — single-host scan, all phases enabled:**

```
fingerprint (4s) + tls (6s) + ssh (6s) + max(jwt=10s) + safety (10s)
= 4 + 6 + 6 + 10 + 10
≈ 36 seconds
```

For a 100-host scan with TLS+SSH on every host and no connectors:

```
4*100 + 6*100 + 6*100 + 10
= 400 + 600 + 600 + 10
≈ 1610 seconds (~27 min) worst case
```

Concurrency (`concurrency: 200`) reduces wall-clock substantially below the upper bound; the formula
is the consultant-quotable worst case, not the expected runtime.

#### Example TOML / YAML snippet

```yaml
scan:
  concurrency: 200
  ports_tls: [443, 8443]
  timeouts:
    default_seconds: 5
    fingerprint_seconds: 4
    tls_seconds: 6
    ssh_seconds: 6
    jwt_seconds: 10
    container_seconds: 120
    source_seconds: 300
    dnssec_seconds: 10
    saml_seconds: 10
    kerberos_seconds: 10
    vault_seconds: 10
    db_connect_seconds: 5
    broker_seconds: 10
    email_seconds: 10
  retry:
    retry_count: 0
    backoff_base_seconds: 1.0
    backoff_max_seconds: 5.0
```

See [`docs/timeout-retry-audit.md`](timeout-retry-audit.md) for the per-scanner audit table mapping
each scanner to its canonical timeout slot (ROBUST-04).

---

### Targets Block

Defines what to scan. At least one of `fqdns` or `cidrs` must have entries.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `fqdns` | list[string] | `[]` | Fully qualified domain names to include in the scan |
| `cidrs` | list[string] | `[127.0.0.1]` | CIDR ranges or single IP addresses |
| `include_ips` | list[string] | `[]` | Additional IPs to append to CIDR results |
| `exclude_ips` | list[string] | `[]` | IPs to exclude from scanning |

Example showing a typical client configuration:

```yaml
targets:
  fqdns:
    - api.acme.com
    - auth.acme.com
  cidrs:
    - 10.0.0.0/24
    - 192.168.1.0/28
  exclude_ips:
    - 10.0.0.1   # router — no services
```

---

### Connectors Block

Enables optional scanner extensions for cloud infrastructure, API endpoints, containers, and
source code. **As of v5.19 (Phase 184.2), not all connectors default to `false`.** The shipped
`quirk/config_template.yaml` — which `quirk init` copies verbatim, with no wizard or branching —
carries all 25 `enable_*` flags live, each with an inline machine-checked reason tag. Seven ship
`true` out of the box: `enable_jwt`, `enable_container`, `enable_source`, `enable_dnssec`,
`enable_saml` (all target-guarded and inert until you populate their `*_targets` list), plus
`enable_email` and `enable_broker` (already scanning by default via the `standard` profile's
auto-enable — see below). The remaining 18 ship `false` with a stated reason. See "Connector
disposition and reason tags" immediately below for the full 25-key table.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `enable_aws` | bool | `false` | Enable AWS cloud connector (ACM, KMS, CloudFront, ELBv2) |
| `enable_azure` | bool | `false` | Enable Azure cloud connector (Key Vault, App Gateway) |
| `enable_adcs` | bool | `false` | AD CS LDAP connector — inventories certificates issued by an Active Directory Certificate Services CA. Shipped since Phase 80; requires `quirk[adcs]` (ldap3). |
| `adcs_targets` | list[string] | `[]` | LDAP URLs for AD CS discovery (e.g. `ldap://dc.corp.com:389`) |
| `adcs_search_base` | string | `null` | LDAP search base DN (e.g. `dc=corp,dc=com`) |
| `adcs_user` | string | `null` | LDAP bind username (no example value shipped — do not template credential-shaped strings into a client config) |
| `adcs_password` | string | `null` | LDAP bind password — set via environment variable reference in real use, never inline |
| `adcs_timeout` | int | `10` | Per-connection timeout (seconds) for AD CS LDAP queries |
| `enable_jwt` | bool | `true` | Enable JWT/REST API scanner (target-guarded — inert until `jwt_targets` is populated) |
| `enable_container` | bool | `true` | Enable container/binary crypto scanner (target-guarded — inert until `container_targets` is populated) |
| `enable_source` | bool | `true` | Enable source code scanner (target-guarded — inert until `source_targets` is populated) |
| `enable_codesign` | bool | `false` | Enable code-signing certificate inventory (LDAP `userCertificate` + TLS EKU). **Not a connector toggle** — driven entirely by the `--inventory-code-signing` CLI flag; this key changes zero scan behavior on its own. |
| `codesign_targets` | list[string] | `[]` | LDAP URLs for code-signing certificate discovery (e.g. `ldap://dc.corp.com:389`) |
| `codesign_search_base` | string | `null` | LDAP search base DN for `userCertificate` discovery (e.g. `dc=corp,dc=com`) |
| `codesign_timeout` | int | `10` | Per-connection timeout (seconds) for code-signing LDAP queries |
| `enable_modbus` | bool | `false` | Enable Modbus/TCP OT/ICS fingerprinting (port 502, must be observed open); requires `quirk-scanner[hw]` extras. See `docs/operators-guide.md` §9.4 for the safety model. |
| `enable_bacnet` | bool | `false` | Enable BACnet/IP OT/ICS fingerprinting (47808/UDP); requires `quirk-scanner[hw]` extras. See `docs/operators-guide.md` §9.4 for the safety model. |
| `enable_recurring_otics` | bool | `false` | **Not a connector toggle** — a scheduler safety gate for recurring Modbus/BACnet probing, not a scanner enable by itself. Opt-in required before a *recurring* (scheduled) run may probe Modbus/BACnet. Gates recurring probing only — a one-off, operator-initiated scan with `enable_modbus`/`enable_bacnet` set is unaffected and needs no new flag. See [OT/ICS Recurring-Scan Cadence Floor](#ot-ics-recurring-scan-cadence-floor-v513-phase-156) below. |
| `enable_nmap` | bool | `false` | **Not a connector toggle** — a discovery driver, not a scan connector. Driven by the `--discovery nmap` CLI flag / the dashboard's nmap checkbox, either of which overwrites this value at scan start; it is not a durable config-file control. |
| `enable_authenticated_mode` | bool | `false` | **Not a connector toggle** — driven by the credential CLI flags (see "Authenticated Scanning" below); the scheduler rejects any recurring config where this is `true`. |
| `aws_region` | string | `"us-east-1"` | AWS region for cloud connector |
| `aws_profile` | string | `null` | AWS named profile; `null` uses the default credential chain |
| `azure_subscription_id` | string | `null` | Azure subscription UUID |
| `azure_keyvault_urls` | list[string] | `[]` | Key Vault base URLs (e.g. `https://myvault.vault.azure.net`) |
| `jwt_targets` | list[string] | `[]` | REST endpoint URLs for JWT scanner |
| `allow_insecure_jwks` | bool | `false` | Disable TLS cert verification for JWKS fetches. Use only for internal/dev endpoints with self-signed certs. When `true`, a `HIGH` advisory finding (`ADVISORY_JWKS_VERIFY_DISABLED`) is emitted for every JWKS URL fetched. |
| `container_targets` | list[string] | `[]` | Docker image refs for container scanner |
| `source_targets` | list[string] | `[]` | Git repo paths or URLs for source scanner |

> **Note:** See [Connector Guides](connectors/) for per-connector credential setup and least-privilege templates.

#### Connector detail fields settable from the dashboard (PARITY-05/06, Phase 197)

Before Phase 197, the dashboard's Connectors panel could only flip the 25 `enable_*` toggles above
— the target lists, endpoints, and identifiers that make most of those toggles actually *do*
anything (e.g. `enable_jwt`'s `jwt_targets`) were config-file-only. Phase 197 widens the same
delta-overlay path (`connectors` key of `POST /api/jobs` and `GET /api/config/effective`) to
accept these 37 additional non-secret fields, enforced by a single shared validator
(`quirk.dashboard.api.schemas.validate_connectors_overlay`,
`_CONNECTOR_DETAIL_KEY_TYPES`) called at all three enforcement points — submit, job-YAML merge,
and preview — so submit and preview can never disagree (PARITY-06). See
[`docs/operators-guide.md` §3.1.4](#314-connectors-panel--enabling-connectors-and-supplying-credentials-from-the-dashboard-parity-0203-phase-193-parity-0506-phase-197)
for how these fields render and behave from the New Scan page.

**Accepted wire types and bounds (D-09):** every `string` value is capped at 512 characters; every
`list[str]` is capped at 256 elements (each element also capped at 512 characters); every `int`
timeout is bounds-checked `1 <= value <= 300` seconds; a bare `true`/`false` is never accepted
where an `int` is expected (`type(value) is bool` is explicitly rejected for int fields, since
Python's `bool` is a subtype of `int`). An unrecognized key, or a key with the wrong wire type,
is rejected with an HTTP 422 naming only the offending key — never its value (T-197-03).

**`gke_clusters` / `aks_clusters` object shape:** unlike every other list field (plain strings),
these two are `list[dict]`. Each GKE element requires exactly `{"name": str, "location": str}`;
each AKS element requires exactly `{"name": str, "resource_group": str}` — a bare string element
is rejected (it would otherwise raise a late `TypeError` inside `quirk/scanner/k8s_connector.py`
at scan time). The dashboard's free-text list input accepts the more compact `name@location` /
`name@resource-group` pairlist syntax and parses it into this object shape client-side before
submission — see the operators guide for the exact textarea convention.

**`vault_tls_verify` defaults to `true`** (matches `hvac.Client(verify=...)`'s config default) —
the dashboard's Vault toggle renders this switch pre-checked, not blank, when the field is absent
from the submitted delta; explicitly unchecking it sends `vault_tls_verify: false`.

| Field | Type | Default | Gating `enable_*` flag | Purpose |
|-------|------|---------|-------------------------|---------|
| `jwt_targets` | list[str] | `[]` | `enable_jwt` | REST endpoint URLs for the JWT/API scanner |
| `container_targets` | list[str] | `[]` | `enable_container` | Docker image refs for the container/binary scanner |
| `source_targets` | list[str] | `[]` | `enable_source` | Git repo paths or URLs for the source scanner |
| `kerberos_targets` | list[str] | `[]` | `enable_kerberos` | KDC hosts for the Kerberos identity scanner |
| `saml_targets` | list[str] | `[]` | `enable_saml` | SAML IdP/SP metadata URLs |
| `dnssec_targets` | list[str] | `[]` | `enable_dnssec` | Zones to query for DNSSEC posture |
| `dnssec_resolver` | str | `null` | `enable_dnssec` | Resolver host used for DNSSEC lookups |
| `smime_targets` | list[str] | `[]` | `enable_smime` | LDAP URLs for S/MIME certificate discovery |
| `smime_search_base` | str | `null` | `enable_smime` | LDAP search base DN for S/MIME discovery |
| `smime_timeout` | int (1-300s) | `10` | `enable_smime` | Per-connection LDAP timeout for S/MIME queries |
| `adcs_targets` | list[str] | `[]` | `enable_adcs` | LDAP URLs for AD CS discovery |
| `adcs_search_base` | str | `null` | `enable_adcs` | LDAP search base DN for AD CS discovery |
| `adcs_user` | str | `null` | `enable_adcs` | LDAP bind username (identifier, not a secret — D-04) |
| `adcs_timeout` | int (1-300s) | `10` | `enable_adcs` | Per-connection LDAP timeout for AD CS queries |
| `aws_region` | str | `"us-east-1"` | `enable_aws` / `enable_s3` | AWS region for the cloud connector |
| `aws_profile` | str | `null` | `enable_aws` / `enable_s3` | AWS named profile; `null` uses the default credential chain |
| `aws_endpoint_url` | str | `null` | `enable_aws` / `enable_s3` | MinIO/LocalStack S3 endpoint override |
| `azure_subscription_id` | str | `null` | `enable_azure` / `enable_blob` | Azure subscription UUID |
| `azure_keyvault_urls` | list[str] | `[]` | `enable_azure` / `enable_blob` | Key Vault base URLs |
| `gcp_project_id` | str | `null` | `enable_gcp` | GCP project id used with application default credentials |
| `k8s_provider` | str | `null` | `enable_k8s` | `"eks"` \| `"gke"` \| `"aks"` |
| `k8s_cluster_name` | str | `null` | `enable_k8s` | Cluster name for the EKS path |
| `k8s_namespace` | str | `"default"` | `enable_k8s` | Namespace scope for the k8s connector |
| `k8s_kubeconfig` | str | `null` | `enable_k8s` | Server-filesystem path to a kubeconfig readable by the QU.I.R.K. server process (D-02 — not a file upload) |
| `k8s_context` | str | `null` | `enable_k8s` | kubeconfig context to use |
| `gke_clusters` | list[{name, location}] | `[]` | `enable_k8s` | GKE clusters, dashboard syntax `name@location` |
| `aks_clusters` | list[{name, resource_group}] | `[]` | `enable_k8s` | AKS clusters, dashboard syntax `name@resource-group` |
| `vault_addr` | str | `null` | `enable_vault` | HashiCorp Vault address, e.g. `http://localhost:8200` |
| `vault_transit_mount` | str | `"transit"` | `enable_vault` | Vault transit engine mount path |
| `vault_tls_verify` | bool | `true` | `enable_vault` | Verify the Vault server's TLS certificate |
| `pg_targets` | list[str] | `[]` | `enable_db` | PostgreSQL hosts for the database-encryption scanner |
| `pg_scanner_user` | str | `null` | `enable_db` | PostgreSQL bind username (identifier, not a secret — D-04) |
| `mysql_targets` | list[str] | `[]` | `enable_db` | MySQL hosts for the database-encryption scanner |
| `mysql_scanner_user` | str | `null` | `enable_db` | MySQL bind username (identifier, not a secret — D-04) |
| `broker_targets` | list[str] | `[]` | `enable_broker` | Explicit broker host/port entries (see the existing `broker_targets` subsection below) |
| `broker_azure_namespaces` | list[str] | `[]` | `enable_broker` | Azure Service Bus namespaces to probe |
| `broker_sqs_regions` | list[str] | `[]` | `enable_broker` | AWS regions to probe for SQS |

Bound-value violations, unknown keys, and type mismatches all raise the same 422 shape from every
one of the three enforcement points — see [`docs/operators-guide.md` §3.1.4](#314-connectors-panel--enabling-connectors-and-supplying-credentials-from-the-dashboard-parity-0203-phase-193-parity-0506-phase-197)
for what this looks like in the dashboard UI.

#### Credential environment variables (D-09, Phase 193)

The scanner honors an environment-variable fallback for every connector credential field in
`quirk/config_redaction.py`'s `CREDENTIAL_REGISTRY` — these are **not dashboard-internal**. A CLI
operator can export any of them instead of writing the secret into `config.yaml`:

| Config field | Environment variable | Falls back for |
|--------------|----------------------|-----------------|
| `connectors.vault_token` | `VAULT_TOKEN` | HashiCorp Vault transit/PKI connector (pre-existing, Phase 25) |
| `connectors.adcs_password` | `QUIRK_ADCS_PASSWORD` | AD CS LDAP bind password |
| `connectors.pg_scanner_password` | `QUIRK_PG_SCANNER_PASSWORD` | PostgreSQL database-encryption scanner |
| `connectors.mysql_scanner_password` | `QUIRK_MYSQL_SCANNER_PASSWORD` | MySQL database-encryption scanner |
| `connectors.snmp_community` | `QUIRK_SNMP_COMMUNITY` | SNMPv2c community string for hardware fingerprinting |

**The config-file value always wins when both are set.** These env vars are a fallback consulted
only when the corresponding `config.yaml` field is empty/unset — set the field directly in
`config.yaml` if you want it to take precedence over whatever is in the shell environment.

For a shared or multi-operator machine, prefer a secret manager or an untracked, gitignored env
file over exporting these inline in a shared shell session — anything placed in shell history or a
committed dotfile is a credential leak, not a convenience.

**Per-host broker and SNMPv3 credentials** use a related but distinct idiom: rather than one fixed
env-var name, the dashboard's job submission generates a per-host variable name (the
`pass_env` / `auth_key_env` / `priv_key_env` config fields, carrying the environment-variable NAME
only, never the secret) and injects the actual value into the scan subprocess's environment at
launch. This is the same non-persistence pattern the broker connector (Phase 57) and SNMPv3
(Phase 139) already used for their own credential fields — Phase 193 extends dashboard-submitted
scans to use it too, rather than inventing a new secret channel. See "Dashboard connector toggles"
above and `docs/operators-guide.md` §3.1.4 for how this looks from the Connectors panel.

**Credentials submitted from the dashboard are injected into the scan subprocess environment and
never persisted.** Whether a credential comes from the Connectors panel or from one of the env vars
above, it reaches the scanner only via the subprocess environment at scan-launch time — it is never
written to the SQLite `ScanJob` row, the job's stored `config.yaml`, or any log line. The job YAML
records only the environment-variable *name* that was used, never the value.

#### Connector disposition and reason tags (D-06, Phase 184.2)

Every `enable_*` line in the shipped `quirk/config_template.yaml` carries an inline, closed-vocabulary
reason tag as a trailing YAML comment, e.g.:

```yaml
enable_aws: false  # off: requires-credentials - needs AWS_ACCESS_KEY_ID or an IAM profile; a bare true attempts SDK client construction and credential lookup
enable_jwt: true   # on: requires-targets - armed but inert until jwt_targets is populated below; the scan short-circuits on an empty target list
```

The tag always follows an `on:` or `off:` prefix that must agree with the flag's actual boolean
value, and is one of five closed strings:

- **`requires-credentials`** — the connector attempts real work the moment it is `true` (SDK
  client construction, credential lookup, an authenticated API call). It ships `false` until you
  supply the credentials it names.
- **`requires-targets`** — the connector is target-guarded: with an empty `*_targets` list the
  scan short-circuits and does nothing, so shipping it `true` is safe. It only starts scanning
  once you populate its target list.
- **`requires-extra-install`** — the connector needs an optional `pip install quirk[...]` extra
  that is not bundled in `quirk-scanner[all]`. Setting the flag `true` without the extra installed
  does not fail the scan; it emits a non-fatal `missing_extra` advisory finding instead (Phase 45
  INSTALL-02).
- **`probes-live-equipment`** — the connector sends unsolicited protocol traffic at OT/ICS
  equipment that can disrupt production plant hardware. It requires explicit, informed opt-in.
- **`not-a-connector`** — the field exists on `ConnectorsCfg` but does not gate a scanner by
  itself; something else (a CLI flag, a scheduler safety check) actually drives the behavior. The
  detail names that real driver.

This vocabulary is machine-checked by `tests/test_config_connector_drift.py`, which fails if any
`enable_*` line uses a tag outside this set, has a stale `on:`/`off:` prefix, or is missing a
substantive (non-trivial) detail — so this table cannot silently rot out of sync with the shipped
template.

#### Full 25-key connector disposition table

| Field | Ships | Tag | Why |
|-------|-------|-----|-----|
| `enable_jwt` | `true` | `requires-targets` | target-guarded, inert until `jwt_targets` set |
| `enable_container` | `true` | `requires-targets` | target-guarded, inert until `container_targets` set |
| `enable_source` | `true` | `requires-targets` | target-guarded, inert until `source_targets` set |
| `enable_dnssec` | `true` | `requires-targets` | target-guarded, no extras install needed at all |
| `enable_saml` | `true` | `requires-targets` | target-guarded, inert until `saml_targets` set |
| `enable_email` | `true` | `requires-targets` | scans every host in the general `targets:` block, not a dedicated email target list; already on via the `standard` profile, written explicitly so the value is authoritative |
| `enable_broker` | `true` | `requires-targets` | like email, scans every host in the general `targets:` block; `broker_azure_namespaces`/`broker_sqs_regions` add cloud-broker probes rather than narrowing the host sweep |
| `broker_targets` | `[]` | `requires-targets` | (Phase 190, TRIAGE-06) an explicit list of `host` / `host:port` / `[ipv6]:port` entries probed **in addition to** each broker family's hardcoded default ports — see "`connectors.broker_targets` — explicit broker ports" below |
| `enable_kerberos` | `false` | `requires-extra-install` | `quirk[identity]` (impacket) is not in `[all]`; downgrades `cryptography` and breaks the TLS scanner |
| `enable_smime` | `false` | `requires-extra-install` | target-guarded like the identity connectors, but shipped off because `quirk[adcs]` (ldap3) is not installed by default |
| `enable_adcs` | `false` | `requires-extra-install` | ldap3 via `quirk[adcs]`; same pre-gate shape as S/MIME |
| `enable_snmp` | `false` | `requires-extra-install` | needs `quirk[hw]` (pysnmp) plus a community string or v3 USM credentials |
| `enable_aws` | `false` | `requires-credentials` | needs AWS credentials or an IAM profile |
| `enable_azure` | `false` | `requires-credentials` | needs an Azure subscription id plus Key Vault URLs |
| `enable_gcp` | `false` | `requires-credentials` | needs a GCP project id, application default credentials, and `quirk[cloud]` |
| `enable_db` | `false` | `requires-credentials` | needs a scanner DB user/password; the default TLS port list already probes 5432/3306 at the TLS layer (D-05) |
| `enable_s3` | `false` | `requires-credentials` | needs AWS credentials; requires `quirk[cloud]` |
| `enable_blob` | `false` | `requires-credentials` | needs Azure storage credentials; requires `quirk[cloud]` |
| `enable_k8s` | `false` | `requires-credentials` | needs kubeconfig or in-cluster credentials; requires `quirk[cloud]` |
| `enable_vault` | `false` | `requires-credentials` | needs `VAULT_TOKEN`/`VAULT_ADDR`; the default TLS port list already probes 8200 at the TLS layer (D-05) |
| `enable_modbus` | `false` | `probes-live-equipment` | unsolicited OT/ICS probing can disrupt production plant equipment |
| `enable_bacnet` | `false` | `probes-live-equipment` | same rationale as Modbus |
| `enable_nmap` | `false` | `not-a-connector` | driven by the `--discovery nmap` CLI flag, which overwrites this value at scan start |
| `enable_authenticated_mode` | `false` | `not-a-connector` | driven by the credential CLI flags; the scheduler rejects any recurring config where this is `true` |
| `enable_recurring_otics` | `false` | `not-a-connector` | a scheduler safety gate for recurring Modbus/BACnet probing, not a scanner toggle by itself |
| `enable_codesign` | `false` | `not-a-connector` | driven entirely by the `--inventory-code-signing` CLI flag |

Four fields are `not-a-connector`: `enable_nmap`, `enable_authenticated_mode`,
`enable_recurring_otics`, and `enable_codesign` — real config fields whose values do not by
themselves drive any scanner. Each is named above with the CLI flag or mechanism that actually
controls its behavior.

#### `connectors.broker_targets` — explicit broker ports (Phase 190, TRIAGE-06)

`enable_broker`'s three drivers (Kafka, RabbitMQ, Redis) each carry a fixed table of default
ports they probe on every host in `targets:`. Before Phase 190 there was no way to tell the
scanner "also check this non-default port" short of editing source — an operator running a
broker on a non-standard port (as this project's own chaos lab does, mapping Kafka/RabbitMQ/
Redis to 29092/29093, 25671/25672, 26379/26380) got silent zero-findings coverage of those
ports even with `enable_broker: true`.

`connectors.broker_targets` closes that gap:

```yaml
connectors:
  enable_broker: true
  broker_targets:
    - "broker.internal.example.com"        # bare host — probed on every family's default ports only
    - "broker.internal.example.com:29092"  # host:port — this port is probed IN ADDITION to defaults
    - "[2001:db8::1]:6380"                 # IPv6 requires bracket syntax when a port follows
```

- **Accepted syntax:** a bare host, `host:port`, or bracketed `[ipv6]:port`. An unbracketed
  entry with more than one colon is only accepted as a bare IPv6 literal (validated via
  `ipaddress.ip_address`) — anything else is rejected at load time.
- **ADDITIVE semantics, not a replacement (RQ-1).** A port named in `broker_targets` is probed
  *in addition to* each family's hardcoded defaults — declaring a port never narrows or replaces
  the default port sweep. This means an operator can never lose coverage by adding a port here;
  the config errs toward over-scanning, never under-scanning. Every family (Kafka, RabbitMQ,
  Redis) receives the same flat host→ports override map, so a port aimed at one broker family is
  also, harmlessly by design, probed by the other two families' drivers.
- **A host listed only in `broker_targets` is scanned even if the general TLS sweep
  (`targets:`/`scan.ports_tls`) never saw it.** The broker phase's host list is the union of
  hosts derived from the TLS-target sweep and the hosts named in `broker_targets`.
- **A malformed port fails the config load with `QRK-CONFIG-002`**, not a silent skip — see
  [`docs/error-codes.md`](error-codes.md). This mirrors the CONFIG-001 fail-fast precedent for
  the general `scan.ports_tls` list (TRIAGE-04, Phase 189).
- **Interaction with custom port scope (see "Custom port spec" below):** the dashboard's
  `custom` port scope explicitly disables `enable_email`/`enable_broker` so a narrow custom scan
  is not also widened by the fixed email/broker service-port tables. `broker_targets` does not
  change this — it cannot re-enable a connector the operator (or the custom-scope suppression)
  has disabled. Set `enable_broker: true` explicitly if you need both a custom port scope and
  broker probing.
- **Reachability advisory:** if an explicit `host:port` entry in `broker_targets` never responds
  to any probe, the scan records exactly one informational (`severity: INFO`) `ADVISORY` row
  (that is the `protocol` field value) naming the unreached target
  — distinct from the deliberate silence for default-port probes that find nothing. See
  [`docs/report-interpretation.md`](report-interpretation.md) for how this reads in a report.

#### Default TLS port list (D-04, widened v5.19 / Phase 184.2)

The shipped template's `scan.ports_tls` now defaults to the same 17-port `CONSULTING_TLS_PORTS`
list the CLI wizard and the dashboard's "Common TLS ports" scope already used — previously the
template alone stayed on a narrower 3-port list whose third entry was itself a typo for `4433`:

```
443, 8443, 9443, 10443, 4433, 5001, 636, 3269, 993, 995, 465, 6443, 2376, 5432, 3306, 1433, 8200
```

To narrow this for a specific engagement, edit `scan.ports_tls` in your `config.yaml` directly —
there is no separate CLI flag for it (the dashboard's port-scope selector, described later in this
document, is a dashboard-only control and does not affect CLI-driven scans).

**D-05 clarification:** `5432` (PostgreSQL), `3306` (MySQL), and `8200` (Vault) are already probed
at the **TLS layer** by this port list, even though the credentialed `db` and `vault` connectors
ship `false`. This is deliberate, not a contradiction — the TLS scanner still reports on the
certificate/cipher posture of a database or Vault listener bound to those ports; only the
*credentialed* connectors (which would additionally query the service for schema/secrets-level
data) require you to opt in separately.

#### TLS-designated ports override (D-08, Phase 186)

Before Phase 186, any plaintext-HTTP finding on any port listed in `scan.ports_tls` was
relabelled `"HTTP on TLS-designated port"` — because `ports_tls` is the scan TARGET list, not a
TLS-designation signal, this made a port that is plaintext by design (e.g. a scanned-but-plaintext
service) indistinguishable in reports from a genuine TLS misconfiguration. The classifier now
relabels a plaintext-HTTP finding only when its port is in the well-known TLS set:

```
443, 8443, 9443, 10443, 4433, 5001
```

or explicitly listed in `scan.tls_designated_ports`. Use the override for a non-standard TLS port
that should still be flagged as a TLS misconfiguration when found serving plaintext HTTP — for
example, a service running on port `8444`:

```yaml
scan:
  tls_designated_ports: [8444]
```

#### Port-list value coercion and `QRK-CONFIG-001` (Phase 189, TRIAGE-04)

Both `scan.ports_tls` and `scan.tls_designated_ports` accept YAML values as either bare integers
or quoted digit-strings — `8444` and `"8444"` are equivalent after `load_config()` runs. A
non-numeric entry (e.g. a typo like `"84a4"`), a non-integral number (e.g. `443.8443` from a
missing comma — never silently truncated to port 443), or a value outside the valid TCP port
range 1–65535 (e.g. `0` or `70000`) is rejected loudly at config-load time with a coded
`QRK-CONFIG-001` error naming the offending field and value; see
[`docs/error-codes.md`](error-codes.md) for the exact message text. One deliberate acceptance:
an integral float such as `443.0` is unambiguous and coerces to the equivalent integer.

**Before Phase 189, this was a silent no-op, not a crash.** A quoted port value in either list
would load without error but would never match the TLS-designation membership test in
`findings_evaluator.py` — the override looked active in the config file but had no effect on
report output. If you have used a quoted value in `scan.ports_tls` or `scan.tls_designated_ports`
in a past engagement's config, re-check that scan's report: the effective scan scope or
TLS-designation override may have been narrower than the config file implied. Configs written
after Phase 189 do not have this gap — a quoted value now either works identically to a bare
integer, or fails loudly with `QRK-CONFIG-001` rather than being silently ignored.

With that override in place, plaintext HTTP found on port 8444 is classified `"HTTP on
TLS-designated port"`; without it, the same finding is classified `"Plaintext HTTP service
detected"`.

#### Per-surface connector coverage (D-16, recorded 2026-09-04 — deferred, not closed)

Measured for Phase 184.2 as the starting baseline for a proposed future CLI↔UI configuration
parity phase (not yet in `ROADMAP.md`):

| Surface | Connector coverage |
|---------|---------------------|
| Config template (`quirk/config_template.yaml`) | 25 connector flags, all dispositioned |
| CLI wizard (`quirk/interactive.py`) | 5 — `jwt`, `container`, `source`, `aws`, `azure` |
| Dashboard New Scan (`src/dashboard/src/pages/scan-new.tsx`) | 0 connector toggles; 1 non-connector toggle (`enable_nmap`, a discovery driver — see the `not-a-connector` disposition above) |

This is a real, measured gap between what the config file can express and what either the CLI
wizard or the dashboard's New Scan page can set interactively. **Closing it is out of scope for
this phase** — it is recorded here only as the quantified starting point for whichever future
phase takes on CLI↔UI configuration parity.

**Phase 197 update (2026-09-10):** the dashboard's zero-connector-toggles measurement above is
now historical, not current. Phase 197 closed 999.104 Tier 2 for the dashboard surface: all 25
`enable_*` toggles were already dashboard-settable since Phase 193 (PARITY-02/03), and the 37
`connectors.*` detail sub-fields that make most of those toggles do anything (target lists,
endpoints, identifiers) are now dashboard-settable too (PARITY-05/06), via the field table in the
"Connector detail fields settable from the dashboard" subsection above. What remains open: the
CLI wizard's 5-connector subset (`jwt`, `container`, `source`, `aws`, `azure`) is unchanged by
this phase — CLI↔dashboard parity for the wizard's remaining 20 connectors is still out of scope
and is tracked as 999.104 Tier 3 residue (owned by Phase 198), not by this phase.

#### SNMPv3 Credentials (Phase 139, `[hw]` extras)

`connectors.snmp_v3_credentials` configures per-host SNMPv3 USM (User-based Security Model)
credentials for authenticated, encrypted SNMP scanning — an upgrade path alongside the
existing SNMPv2c `scan.snmp_community` string documented in `docs/operators-guide.md` §9.
Mirrors the shape of `broker_credentials`: only environment-variable **names** are stored in
config, never the passphrases themselves.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `username` | string | *(required)* | SNMPv3 USM username configured on the target device |
| `auth_key_env` | string | *(required)* | Name of the environment variable holding the authentication passphrase |
| `priv_key_env` | string | `""` | Name of the environment variable holding the privacy (encryption) passphrase. Omit or leave empty for `authNoPriv` mode |
| `auth_protocol` | string | `"SHA"` | Authentication protocol — SHA-family only (D-02): `SHA`, `SHA224`, `SHA256`, `SHA384`, `SHA512` |
| `priv_protocol` | string | `"AES"` | Privacy protocol — AES-family only (D-02): `AES`, `AES128`, `AES192`, `AES256` |

**D-02 (SHA/AES-only):** Weaker legacy USM protocols (MD5 auth, DES priv) are rejected at
config-load time with a `ValueError` naming the offending host and protocol — QUIRK never
silently falls back to a weaker negotiated protocol on your behalf.

```yaml
connectors:
  snmp_v3_credentials:
    "192.168.1.1":
      username: "quirk-readonly"
      auth_key_env: "QUIRK_SNMP_AUTH_KEY"    # env var NAME, not the passphrase
      priv_key_env: "QUIRK_SNMP_PRIV_KEY"    # env var NAME, not the passphrase
      auth_protocol: "SHA256"
      priv_protocol: "AES256"
```

Set the referenced environment variables before scanning (e.g.
`export QUIRK_SNMP_AUTH_KEY=...`) — passphrases must never appear inline in YAML. Hosts
without a `snmp_v3_credentials` entry are scanned with the existing SNMPv2c
`scan.snmp_community` path unchanged; see `docs/operators-guide.md` §9 for the full
v3→v2c→none fallback ladder and the SNMP version labels in `docs/report-interpretation.md`.

#### Code-Signing Certificate Connector (Phase 95)

The code-signing connector discovers X.509 certificates from Active Directory LDAP servers by
reading the `userCertificate` RFC 4523 attribute. It filters for certificates carrying the
`Code Signing` Extended Key Usage (EKU OID `1.3.6.1.5.5.7.3.3`) and classifies weak-algorithm
certificates (RSA < 2048-bit, EC < 256-bit key, or SHA-1 signature) as HIGH-severity findings.

Enable the connector in the `connectors` block and activate it at scan time with the
`--inventory-code-signing` CLI flag:

```yaml
connectors:
  codesign_targets:
    - "ldap://dc01.corp.com:389"
  codesign_search_base: "dc=corp,dc=com"
  codesign_timeout: 10    # seconds; default 10
```

```bash
quirk --config config.yaml --inventory-code-signing
```

The scanner performs an anonymous LDAP bind with a paged search (page size 500). All user DNs
and certificate subject CNs that appear in log output are sanitized via `safe_str()` (control
characters and newlines are removed). No certificate content is written or transmitted
beyond the existing scan database.

**In-process TLS EKU check:** Even without `codesign_targets` configured, the `--inventory-code-signing`
flag activates an in-process check that inspects TLS certificates already collected by the TLS
scanner for the Code Signing EKU. This path requires no additional network connections and runs
against the in-memory `tls_endpoints` list.

**CBOM integration:** Code-signing certificates are emitted as CycloneDX `certificate` components
with `bom_ref = crypto/certificate/codesign/<sha256-fingerprint>`. If the same certificate was
already discovered by the TLS scanner, the TLS-derived component wins and gains a
`quirk:code-signing-eku: true` property rather than creating a duplicate component.

**Scoring impact:** The code-signing connector contributes to the **Agility Signals** subscore.
Each certificate with a weak algorithm increments the `codesign_weak_algo_count` counter; the
resulting `agility_codesign_weak_algo_ratio` reduces the subscore by up to −6.0 points
(SCORE_WEIGHTS sum: 299.0, count: 40 — Phase 95 SCORE-01).

```yaml
connectors:
  enable_aws: true
  aws_region: "us-east-1"
  aws_profile: "quirk-readonly"   # optional; omit to use default AWS credential chain

  enable_azure: true
  azure_subscription_id: "00000000-0000-0000-0000-000000000000"
  azure_keyvault_urls:
    - "https://myvault.vault.azure.net"

  enable_jwt: true
  jwt_targets:
    - "https://api.acme.com"

  enable_container: true
  container_targets:
    - "myregistry.azurecr.io/myapp:latest"

  enable_source: true
  source_targets:
    - "/path/to/repo"
    - "https://github.com/acme/backend"
```

---

### OpenAPI Spec Analysis (`[api]` extras)

Phase 94 (v5.1) introduced passive OpenAPI/Swagger spec analysis. The scanner inventories declared security schemes, plaintext `http://` server URLs, and unauthenticated path operations, with hardened defenses against `$ref` SSRF and oversized-spec DoS.

#### Installing the `[api]` extras group

```bash
pip install "quirk-scanner[api]"
```

This installs `openapi-spec-validator>=0.9.0`. The `[api]` group is **not** included in `[all]` — it is opt-in to keep the base install lightweight.

> **Phase 96 update:** `schemathesis` is now included in the `[api]` extras group and powers the REST fuzzer (`--fuzz` flag). It is intentionally **excluded from `[all]`** — see [REST Fuzzing](#rest-fuzzing-active-crypto-posture-probes) below.

#### CLI flag

```bash
# Local file (no network required)
quirk --config config.yaml --openapi-spec /path/to/openapi.yaml

# URL within your configured scan targets
quirk --config config.yaml --openapi-spec https://api.acme.com/openapi.json
```

The `--openapi-spec` flag accepts either a local file path or a URL. URLs must fall within the configured `targets.fqdns` scope — out-of-scope URLs are rejected before any network request is made.

#### `openapi:` config block

The spec path can also be set in `config.yaml` under the `scan` block:

```yaml
scan:
  openapi_spec_path: "docs/openapi.yaml"   # local path or scope-gated URL
```

Setting `openapi_spec_path` in the config is equivalent to passing `--openapi-spec` on the CLI. A CLI flag overrides the config value.

#### Security hardening

| Guard | Behavior |
|-------|----------|
| **$ref SSRF** | External or internal-network `$ref` values (e.g. `http://169.254.169.254/...`) raise `SpecParsingError` *before* the OAS validator runs. Zero outbound requests on SSRF-shaped input. |
| **10 MB size cap** | Specs larger than 10 MB are rejected before `yaml.safe_load`. Prevents billion-laughs and oversized-YAML DoS. |
| **Scope gate** | Spec URLs must start with a configured `targets.fqdns` entry. Rejected before any network request. |
| **Graceful degradation** | When `[api]` is not installed (`OPENAPI_AVAILABLE = False`), the scanner returns a single `missing_extra` advisory endpoint and continues; no exception is raised. |

#### Findings produced

OpenAPI scan results appear in the standard findings table as `CryptoEndpoint(protocol="OpenAPI")` rows:

| Finding type | Severity | Description |
|-------------|----------|-------------|
| Security scheme declaration | INFO | JWT/OAuth2/API-key security scheme found in spec |
| Plaintext server | HIGH | `http://` (non-TLS) server URL declared in spec — feeds `agility_openapi_plaintext_ratio` scoring penalty |
| Unauthenticated endpoint | MEDIUM | Path operation with no security requirement declared |

---

### Authenticated Scanning (ephemeral credentials)

Phase 93 (v5.1) introduced per-scan ephemeral credential support, allowing QUIRK to attach an
HTTP-level credential to JWT/REST endpoint probes for a single scan run. Credentials are never
persisted to SQLite, the CBOM, log files, or the dashboard — they live only in-process for the
duration of the run.

#### Opt-in config flag

Add `enable_authenticated_mode: true` to the `connectors` block to enable the feature:

```yaml
connectors:
  enable_jwt: true
  jwt_targets:
    - "https://api.acme.com"
  enable_authenticated_mode: true
```

Without this flag (or a CLI `--auth-*` flag), authenticated scanning is disabled and all
credential-related CLI arguments are silently ignored.

#### CLI flags

| Flag | Credential scheme | Description |
|------|-------------------|-------------|
| `--auth-bearer [REF]` | Bearer token (OAuth2 / JWT) | Adds `Authorization: Bearer <token>` to probes |
| `--auth-api-key [REF]` | API-key header (`X-Api-Key`) | Adds `X-Api-Key: <key>` to probes |
| `--auth-api-key-query [REF]` | API-key query parameter | Appends `?api_key=<key>` to JWKS/probe URLs |
| `--auth-basic [REF]` | HTTP Basic (`user:password`) | Adds `Authorization: Basic <b64>` to probes |

Each flag accepts an optional `REF` argument. If `REF` is omitted the flag is treated as a bare
flag and triggers an interactive `getpass` prompt (see "Reference model" below).

#### Reference-not-secret model

**Raw credential values must never appear in the CLI argument.** Passing a credential as a bare
string (e.g. `--auth-bearer eyJhbGci…`) will be rejected with a clear error.

Instead, pass a *reference* to where the credential lives:

| Input form | Example | Resolved from |
|------------|---------|---------------|
| `@file` path | `--auth-bearer @/path/to/token.txt` | File contents (first line, stripped) |
| `ENV_VAR` name | `--auth-bearer QUIRK_AUTH_TOKEN` | Environment variable at resolution time; env var is **deleted after reading** to prevent subprocess inheritance |
| Bare flag (no REF) | `--auth-bearer` | Interactive `getpass` prompt — credential is never echoed to the terminal |

**Why the reference model?** Inline secrets in `argv` are visible to `ps aux`, the shell history
(`~/.bash_history`, `~/.zsh_history`), and process-listing tools. The `@file`/`ENV_VAR`/`getpass`
forms keep the raw credential out of the process argument list entirely.

**Source precedence** (highest to lowest): interactive prompt → environment variable → `@file`/bare-flag reference.

#### Ephemeral-only invariant

Credentials are held in a `bytearray` buffer (`CredentialContext`) for the scan run and
zeroed in-place via `CredentialContext.close()` on both normal exit and on any exception,
including `KeyboardInterrupt`. They are **never**:

- Written to the SQLite database (`quirk.db`)
- Included in the CBOM output (`cbom-*.json`)
- Included in log files
- Returned by the dashboard API
- Included in PDF exports

This invariant is enforced by an automated sentinel test suite (`tests/test_credential_leakage.py`,
25 tests) that injects a synthetic sentinel value across all 11 stored/rendered surfaces and asserts absence.

#### Scheduler rejection (QRK-SCHED-AUTH-001)

Scheduled scans cannot use authenticated mode. Running `quirk schedule add` against a config
file that contains `enable_authenticated_mode: true` exits immediately with:

```
[QRK-SCHED-AUTH-001] Authenticated scan configs cannot be scheduled.
Fix: Remove enable_authenticated_mode from config or use a non-authenticated config for scheduled runs.
```

Exit code: `2`. This is by design — storing scheduled-scan credentials would require persisting
a secret somewhere, which violates the ephemeral-only invariant.

#### Example: authenticated JWT scan

```bash
# Using a @file reference (preferred for automation)
echo "eyJhbGciOiJSUzI1NiJ9..." > /tmp/token.txt
quirk --config config.yaml --auth-bearer @/tmp/token.txt

# Using an environment variable reference
export QUIRK_AUTH_TOKEN="eyJhbGciOiJSUzI1NiJ9..."
quirk --config config.yaml --auth-bearer QUIRK_AUTH_TOKEN
unset QUIRK_AUTH_TOKEN   # QUIRK also deletes it after reading

# Interactive prompt (safest — credential never touches disk or env)
quirk --config config.yaml --auth-bearer

# API-key query parameter (appended to JWKS/probe URLs)
quirk --config config.yaml --auth-api-key-query @/tmp/apikey.txt
```

---

### REST Fuzzing (active crypto-posture probes)

Phase 96 (v5.1) introduced active REST endpoint fuzzing for crypto-posture assessment.
The fuzzer sends a bounded set of probes to discovered OpenAPI endpoints and checks for
TLS downgrade acceptance, weak cipher negotiation, missing HSTS headers, HTTP-only
credential transmission, and (behind a dedicated sub-flag) JWT RS256→HS256 algorithm
confusion. **Fuzzing is off by default and requires explicit opt-in.**

#### Installing the `[api]` extras group

```bash
pip install "quirk-scanner[api]"
```

This installs `openapi-spec-validator>=0.9.0` and `schemathesis` (the request-dispatch
engine). The `[api]` group is **not** included in `[all]` — it is opt-in to keep the base
install lightweight. Running `--fuzz` without `[api]` installed prints a missing-extra
advisory and exits cleanly.

#### CLI flags

| Flag | Default | Description |
|------|---------|-------------|
| `--fuzz` | `false` | Enable active REST crypto-posture fuzzing. Requires `--openapi-spec` (endpoint source) and an interactive `CONFIRM` prompt before any request is sent. |
| `--fuzz-jwt-alg-confusion` | `false` | Also run the JWT RS256→HS256 algorithm-confusion probe. Combines a Phase 93 bearer token with the target's JWKS public key to forge a symmetric token; acceptance yields a CRITICAL finding. |
| `--fuzz-budget N` | `50` | Maximum number of probe requests (hard max 500 — values above 500 are rejected before any request is sent). |

#### CONFIRM gate and non-TTY hard-abort (FUZZ-01, FUZZ-03)

When `--fuzz` is set in a TTY session, the scanner prints a budget summary and requires
the user to type the **literal word `CONFIRM`** before any request is dispatched:

```
Fuzzing will send up to 50 probe requests to 3 endpoint(s).
Target: https://api.acme.com
Type CONFIRM to proceed, or press Enter to abort:
```

Any input other than `CONFIRM` (including a bare Enter) aborts cleanly with **zero
requests sent**.

> **Non-TTY hard-abort:** When stdin is not a TTY (piped input, CI/CD, scheduled jobs),
> the scanner hard-aborts **before sending any request** and prints a clear
> non-interactive-mode error. Fuzzing **never runs headlessly**. This differs from the
> nmap discovery prompt, which auto-proceeds in non-TTY mode — the fuzz gate is stricter
> by design (T-96-03).

**As of v5.17 (Phase 172, SAFE-01):** this refusal fires at argument-validation time,
immediately after `--fuzz` is parsed and before any config load or scan phase begins —
not later, inside the fuzz phase itself. `--fuzz` on non-interactive stdin is treated as
a usage error: the scanner prints coded error `QRK-FUZZ-001` and exits `2`, regardless of
whether an OpenAPI spec resolves. Previously this could be silently bypassed (the scan
would complete and exit `0` with fuzzing quietly skipped); it no longer can be. See
[docs/error-codes.md](error-codes.md) for the `FUZZ` error domain's full cause/fix text.

#### Six safety guardrails (FUZZ-02)

| # | Guardrail | Behavior |
|---|-----------|----------|
| 1 | GET-only by default | Only HTTP `GET` endpoints are probed; other methods require explicit future opt-in |
| 2 | Hard budget ceiling | `--fuzz-budget` default 50, hard max **500** — values above 500 are rejected before any request |
| 3 | Rate cap 5 req/s | Probe requests are rate-limited to 5 per second using the nmap TokenBucket pattern |
| 4 | CONFIRM prompt | TTY: user must type the literal word `CONFIRM`; any other input aborts with zero requests sent |
| 5 | Per-request scope enforcement | Every probe URL is validated via `validate_external_url` + `cfg.targets` before dispatch — out-of-scope URLs are rejected |
| 6 | 5xx cascade pause | After 3 consecutive HTTP 5xx responses, the fuzzer pauses and emits a warning before continuing |

**As of v5.17 (Phase 172, SAFE-02):** the budget ceiling in guardrail #2 is enforced at
argument-validation time, before any config load or scan phase begins — a `--fuzz-budget`
above the hard max is **rejected with an error, not silently clamped down to 500**. The
boundary is inclusive: `500` is accepted, `501` is rejected. A request that exceeds the
ceiling prints coded error `QRK-FUZZ-002` and exits `2`. The default of `50` is unchanged.
See [docs/error-codes.md](error-codes.md) for the `FUZZ` error domain's full cause/fix
text.

#### Findings produced

REST fuzzing results appear as `CryptoEndpoint(protocol="REST_FUZZ")` rows in the
standard findings table:

| Finding type | Severity | Description |
|-------------|----------|-------------|
| TLS downgrade accepted | HIGH | Server accepted a downgraded TLS version on a REST endpoint |
| Weak cipher accepted | HIGH | Server negotiated a weak cipher suite on a REST endpoint |
| HSTS header missing | HIGH | `Strict-Transport-Security` header absent on an HTTPS endpoint |
| HTTP-only credential transmission | HIGH | Endpoint accepts credentials over plain `http://` — feeds `agility_fuzz_crypto_posture_ratio` scoring penalty |
| JWT alg-confusion acceptance | CRITICAL | Server accepted an RS256→HS256 forged token (requires `--fuzz-jwt-alg-confusion`) — feeds `agility_fuzz_crypto_posture_ratio` scoring penalty |

> **CBOM note:** REST_FUZZ endpoints are excluded from the CBOM TLS and certificate
> component builders (Pass-2 and Pass-3 skip lists) to prevent phantom
> `crypto/protocol/tls/*` and `crypto/certificate/*` components for endpoints that
> were not TLS-scanned.

#### Scoring impact

CRITICAL and HIGH REST fuzz findings feed the `agility_fuzz_crypto_posture_ratio` signal
in `SCORE_WEIGHTS` (weight: `4.0`, final step in the v5.1 weighted sum). The sum is
**303.0** across **41 entries** after Phase 96. INFO `probe_skipped` rows are excluded from
the finding count to prevent score drift when endpoints are unreachable.

#### Example: fuzz a local OpenAPI target

```bash
# Passive OpenAPI spec analysis + active REST fuzzing
quirk --config config.yaml \
  --openapi-spec https://api.acme.com/openapi.json \
  --fuzz

# Include the JWT algorithm-confusion probe
quirk --config config.yaml \
  --openapi-spec https://api.acme.com/openapi.json \
  --fuzz --fuzz-jwt-alg-confusion

# Set a custom request budget (max 500)
quirk --config config.yaml \
  --openapi-spec https://api.acme.com/openapi.json \
  --fuzz --fuzz-budget 100
```

---

### Output Block

Controls where QU.I.R.K. writes reports, CBOM files, and its internal database.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `directory` | string | `"output"` | Directory for reports, CBOM files, and logs |
| `db_path` | string | `"./quirk-output/quirk.db"` | SQLite database path for scan results. **Canonical path** (Phase 74 D-05) — the dashboard, `quirk doctor`, and `quirk console` all resolve here when `QUIRK_DB_PATH` is unset. Pointing `db_path` elsewhere means the scanner writes one database while the dashboard reads another. |

```yaml
output:
  directory: "quirk-output"
  db_path: "./quirk-output/quirk.db"
```

---

### Intelligence Block

Controls the quantum-readiness scoring calibration and version metadata.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `intelligence_version` | string | `"3.9.0"` | Intelligence layer version tag (informational) |
| `profile` | string | `"balanced"` | Score calibration profile: `lenient`, `balanced`, `strict` |
| `calibration_overrides` | dict | `{}` | Per-weight scoring overrides for advanced users |

**Score calibration profiles:**

- `lenient` — Reduces penalty weights. Use in immature environments where a score shock would be counterproductive. Suitable for a first engagement where you need to show progress rather than alarm.
- `balanced` — Default. Production-calibrated weights designed for typical enterprise networks.
- `strict` — Increases penalty weights. Use in high-compliance environments (FedRAMP, CNSA 2.0) where the client must demonstrate a tighter posture.

##### How Score Profiles Work

Score profiles adjust the weight of **crypto-agility** and **identity/certificate** scoring categories. Hygiene and TLS modernization weights are unchanged across all profiles.

| Profile | Agility Weight | Identity Weight | Use Case |
|---------|---------------|-----------------|----------|
| `strict` | 1.4x base | 1.4x base | Post-quantum readiness assessment — amplifies crypto-agility and certificate hygiene penalties |
| `balanced` | 1.0x (default) | 1.0x (default) | General-purpose assessment |
| `lenient` | 0.7x base | 0.7x base | Status-quo baseline — reduces agility and identity penalties for organizations not yet planning PQC migration |

Setting `calibration_overrides` in the intelligence section allows fine-grained per-weight adjustments that override profile defaults. For example:

```yaml
intelligence:
  profile: strict
  calibration_overrides:
    agility_rsa_only_penalty: 4.0  # Override strict's amplified RSA penalty
```

```yaml
intelligence:
  intelligence_version: "3.9.0"
  profile: "balanced"   # lenient|balanced|strict
  calibration_overrides: {}
```

---

### Remediation Aliases (v5.18+ — Phase 179)

Maps an old identity (host or IP from a prior engagement's scan) to its current identity, so
re-scan burndown can match findings that moved across DHCP churn, hostname-vs-IP drift, VIPs, and
container reassignment. Without an alias, a finding that "moved" between the baseline scan and the
re-scan reads as two unrelated findings — one still open on the old identity, one newly discovered
on the new identity — rather than one finding whose progress you can track.

| Key | Type | Default | Description |
|-----|------|---------|--------------|
| `remediation_aliases` | dict (string → string) | `{}` | Maps a prior-scan identity to its current identity, one entry per known rename/move |

```yaml
remediation_aliases:
  web01.corp.example: 10.0.0.15
  old-db-host.internal: db02.corp.example
```

**Parsing rules an operator can rely on:**

- The top-level value must be a mapping. Any other shape — a list, a bare string, `null` — yields
  an empty alias set rather than raising a config error; the scan proceeds with no aliases applied.
- Individual entries are dropped, not fatal, when malformed: an entry whose value is itself a
  nested `dict` or `list`, or whose value is `null`, is skipped.
- Both the key and the value are coerced to strings and `.strip()`-ed. An entry that strips to an
  empty key or empty value is dropped.
- A dropped or skipped entry does not stop the scan and does not raise — it is silently absent
  from the alias set, which is why the syntax above should be treated as exact rather than
  approximate.

**Two design constraints, because they are the reason this key exists rather than something
automatic:**

- QU.I.R.K. does **not** attempt automatic re-scan entity resolution. Matching purely on
  `(host, port)` breaks on DHCP lease changes, hostname-vs-IP recording drift, load-balancer VIPs,
  and container/pod churn between engagements — any of those would silently misattribute progress.
- Aliases are **never** learned automatically. The only source of truth is this file, reviewed by
  a human, and versioned alongside the rest of the scan config. If an identity isn't listed here,
  QU.I.R.K. treats it as a new, unrelated identity — never as an assumed match.

---

### Scan Profiles (`--profile` flag)

The `--profile` flag applies a preset combination of timeouts and TLS enumeration depth. Profiles override the corresponding `scan` block keys at runtime — `config.yaml` is not modified.

| Profile | Timeout | TLS enum mode | Use case |
|---------|---------|---------------|----------|
| `quick` | 2s | `off` | Discovery pass — find live hosts, no deep enum |
| `standard` | 5s | `fast` | Default — balances speed and depth |
| `deep` | 10s | `deep` | Full enumeration — slow, most thorough |

```bash
# Discovery pass to find live hosts quickly
quirk --config config.yaml --profile quick

# Default balanced scan
quirk --config config.yaml --profile standard

# Thorough enumeration for final deliverable
quirk --config config.yaml --profile deep
```

---

### Port Scope (v5.6+ — Phase 121)

Dashboard-initiated scans gain control over **port coverage** via a per-scan "port scope". Port scope controls which TCP ports are probed during the discovery phase. It is orthogonal to the scan profile (which controls timeout depth and TLS enumeration) — the two axes are independent.

> **TCP only.** Port scope applies to TCP discovery. UDP scanning is not supported.

#### Four scope values

| Scope | Description | nmap required? | Default? |
|-------|-------------|---------------|---------|
| `top1000` | nmap `--top-ports 1000` — most common 1000 TCP ports | Yes (forces nmap) | **Yes** |
| `common` | 17 curated `CONSULTING_TLS_PORTS` — fast, targets web/TLS/SSH services | No (builtin or nmap) | No |
| `all` | nmap `-p-` — all 65535 TCP ports; exhaustive, slow | Yes (forces nmap) | No |
| `custom` | User-specified port list (e.g. `443,8000-9000,15449`) | Honors nmap checkbox | No |

**Default is `top1000`** — it covers the most common services via nmap and works well for typical enterprise networks. The `common` scope is suitable when nmap is not installed or speed is the priority.

#### Wide scopes without nmap installed

If you select `top1000` or `all` but nmap is not available on the system PATH, the scan **fails with an advisory finding** and an actionable error message (install nmap or switch to the Common TLS scope). There is **no silent fallback** to a narrower port list — you always know what was actually scanned.

#### Custom port spec

The `custom` scope accepts a comma-separated list of ports and port ranges:

```
443,8000-9000,15449,16443
```

Rules:
- Ports must be in the range 1–65535.
- Ranges must be `low-high` with `low <= high`.
- The expansion cap is 2048 unique ports — specs that expand to more than 2048 ports are rejected with a 422 error (guards against accidentally specifying `1-65535` in the custom field).
- The nmap checkbox is honored: if you also enable nmap, custom ports are passed to nmap as `-p <csv>`; if nmap is off, the builtin fingerprinter probes each listed port directly.
- **Custom scope means exactly these ports.** The email and broker connectors (SMTP/IMAP/POP3 and Kafka/AMQP/Redis) probe their own fixed service-port tables, which the `standard` and `deep` profiles normally auto-enable independently of the port list. Under custom scope these connectors are explicitly disabled so the scan covers only the ports you specified — otherwise a 2-port custom scan would also probe the ~7 fixed email ports. To scan email/broker crypto, use the `common`, `top1000`, or `all` scope (the `common`/Consulting list already curates in the implicit-TLS email ports 993/995/465 by design).

#### Dashboard form vs. presets precedence

*(D-16, Phase 194 — the one canonical home for this precedence rule. Both the Connectors panel
(Phase 193) and the Advanced scan-fields panel (Phase 194) follow the exact mechanism described
here; if you are looking for connector-specific or advanced-field-specific precedence detail, read
this section first — the per-panel notes below only name what each panel additionally does, they
do not restate the mechanism.)*

The dashboard's New Scan form — both the Connectors panel and the Advanced scan-fields panel — and
the CLI's vertical presets / scan profiles resolve to a single effective config through one shared
mechanism, not two competing ones:

- **The dashboard writes a delta into the job YAML — only the fields you actually touched.**
  Leaving a field or toggle untouched submits no key for it at all; the submitted `advanced:` /
  `connectors:` block in the job config contains exactly the keys you changed, nothing more.
- **`load_config` records those keys in `_user_set_fields`, and `apply_profile` does not overwrite
  them.** An explicit operator value — whether typed into the Advanced panel or flipped in the
  Connectors panel — always beats the active vertical preset and always beats the scan profile
  (`lenient`/`balanced`/`strict` or `deep`/`standard`/`custom`), because the profile-application step
  checks `_user_set_fields` before it would otherwise set a default.
- **The overlay is merged last.** `build_job_config_dict` applies every `port_scope`-derived
  default first, then merges the Advanced/Connectors overlay on top — so an explicit advanced TLS
  port list always beats the port-scope default, never the reverse.
- **The Effective Config preview cannot disagree with the scan**, because it is not a
  client-side simulation — `GET /api/config/effective` resolves through the identical real
  `load_config` → `apply_profile` → overlay-merge path the scan itself uses. Whatever the preview
  shows is what the scan will actually run with, by construction, not by convention.

#### Connectors panel: explicit toggle vs. custom-port-scope suppression (D-13/D-14, Phase 193)

The "Custom port spec" section above describes the dashboard's `custom` port scope force-disabling
`enable_email`/`enable_broker` so a narrow custom scan doesn't also probe the fixed email/broker
service ports. As of Phase 193's Connectors panel (`docs/operators-guide.md` §3.1.4), that
suppression is no longer absolute — this is the connector-specific instance of the explicit-value-
beats-preset rule stated in the canonical precedence section immediately above:

- **D-14 — an explicit toggle beats custom-port-scope suppression.** If you explicitly turn
  `enable_email` or `enable_broker` back on in the Connectors panel while `custom` port scope is
  selected, your explicit toggle wins — the scan runs that connector even though custom scope would
  otherwise have suppressed it.
- **D-13 — only the toggles you touch are written to the job config.** The Connectors panel writes a
  delta-only overlay: flipping one connector's switch writes only that field into the submitted job
  YAML's `connectors:` block. Every connector you didn't touch keeps whatever the active vertical
  preset or profile default would otherwise set — so toggling on one connector never silently resets
  or overrides the other 24.

#### Advanced scan-fields reference (PARITY-04, Phase 194; PARITY-08/09, Phase 198)

The dashboard's collapsed "Advanced" section on the New Scan form (`docs/operators-guide.md`
§3.1.5) exposes **27 fields** (the original 8 from Phase 194, extended to the full 27-field
scan-behavior surface in Phase 198), each following the delta-only precedence rule above:

| Field | YAML path | Accepted values / bounds | Default |
|-------|-----------|---------------------------|---------|
| TLS Ports | `scan.ports_tls` | Comma-separated ports/ranges (e.g. `443,8443,9000-9010`); each value 1-65535 | 17-port `CONSULTING_TLS_PORTS` list — see "Default TLS port list" above |
| TLS Enumeration Mode | `scan.tls_enum_mode` | `fast` or `deep` only — see D-19 note below | `fast` |
| Send SNI | `scan.include_sni` | boolean | `true` |
| Default timeout | `scan.timeouts.default_seconds` | integer seconds, 1-300 | `5` |
| TLS timeout | `scan.timeouts.tls_seconds` | integer seconds, 1-300 | `6` |
| SSH timeout | `scan.timeouts.ssh_seconds` | integer seconds, 1-300 | `6` |
| Retry count | `scan.retry.retry_count` | integer attempts, 0-10 | `0` |
| Data Classification | `assessment.data_classification` | `public` / `internal` / `confidential` / `regulated` only — see D-21 note below | `confidential` for dashboard-dispatched scans |
| Fingerprint timeout | `scan.timeouts.fingerprint_seconds` | integer seconds, 1-600 | `4` |
| JWT timeout | `scan.timeouts.jwt_seconds` | integer seconds, 1-600 | `10` |
| Container timeout | `scan.timeouts.container_seconds` | integer seconds, 1-600 | `120` |
| Source timeout | `scan.timeouts.source_seconds` | integer seconds, 1-600 | `300` |
| DNSSEC timeout | `scan.timeouts.dnssec_seconds` | integer seconds, 1-600 | `10` |
| SAML timeout | `scan.timeouts.saml_seconds` | integer seconds, 1-600 | `10` |
| Kerberos timeout | `scan.timeouts.kerberos_seconds` | integer seconds, 1-600 | `10` |
| Vault timeout | `scan.timeouts.vault_seconds` | integer seconds, 1-600 | `10` |
| DB Connect timeout | `scan.timeouts.db_connect_seconds` | integer seconds, 1-600 | `5` |
| Broker timeout | `scan.timeouts.broker_seconds` | integer seconds, 1-600 | `10` |
| Email timeout | `scan.timeouts.email_seconds` | integer seconds, 1-600 | `10` |
| Backoff base | `scan.retry.backoff_base_seconds` | float seconds, must be > 0; server rejects `base > max` naming both fields | `1.0` |
| Backoff max | `scan.retry.backoff_max_seconds` | float seconds, must be > 0 and >= backoff base | `5.0` |
| Scan concurrency | `scan.concurrency` | integer workers, 1-500 | `20` (config template default; required in hand-authored YAML) |
| Fingerprint concurrency | `scan.fingerprint_concurrency` | integer workers, 1-500 | `200` |
| TLS concurrency | `scan.tls_concurrency` | integer workers, 1-500 | `150` |
| SSH concurrency | `scan.ssh_concurrency` | integer workers, 1-500 | `100` |
| Motion concurrency | `scan.motion_concurrency` | integer workers, 1-500 — shared pool for email + broker connector scanning | `50` |
| TLS-Designated Ports | `scan.tls_designated_ports` | Comma-separated ports/ranges (same format as TLS Ports), max 512 characters | empty list (no ports forced TLS-designated) |

**D-11 — the bounds asymmetry between the 3 Phase-194 timeout fields and the 11 new Phase-198
timeout fields is deliberate, not a typo.** `timeout_default_seconds`, `timeout_tls_seconds`, and
`timeout_ssh_seconds` keep their original 1-300 bound; all 11 new per-scanner timeout fields
(Fingerprint through Email above) use a wider 1-600 bound, because several of the underlying
scanners (Container, Source) already default well past 300 seconds — scoping the wider range to
only the new fields avoids silently loosening the three original fields' validation.

**D-04 — three intentional gaps: recorded, not rendered.** The following `scan.*` fields exist in
`quirk/config.py` but deliberately have **no** Advanced-panel control and no dashboard-settable
overlay path. This is a recorded design decision, not an oversight:

- `scan.openapi_spec_path` — a local filesystem path (or scope-gated URL) fed to the REST-fuzzing
  OpenAPI loader. It is the same trust-boundary class as `assessment.logo_path`: a
  path-traversal-capable input that is safe when hand-authored in `config.yaml` by an operator with
  filesystem access, but not safe to expose as a dashboard-submitted string from a browser.
- `scan.hardware_history_retention_days` and `scan.hardware_drift_event_retention_days` — these
  govern how long hardware-crypto engagement history and drift events are retained at the
  **install** level, not how a single scan behaves. They belong with install-scoped retention
  policy, not a per-scan Advanced form field.

If you need to set any of these three, hand-edit `config.yaml` directly — there is no dashboard
path for them, by design.

**D-19 — `tls_enum_mode` has no `off` behavior.** The config template comment historically read
`off|fast|deep` (see the `scan:` example block above), but `quirk/scanner/tls_scanner.py` coerces
any value outside `{fast, deep}` back to `fast` at scan time — `off` has never actually turned TLS
enumeration off. Because of this, the Advanced panel's TLS Enumeration Mode dropdown deliberately
offers only Fast and Deep; it does not offer a value that has never had an effect.

**D-21 — `data_classification`'s vocabulary is exactly four values.** `public`, `internal`,
`confidential`, `regulated` — the same four values the CLI wizard's `_DATA_CLASS_MAP` enforces
(see the "Assessment Block" table above). The Advanced panel's Data Classification dropdown offers
exactly these four; no fifth, legacy-named value exists anywhere in the codebase, and `confidential`
remains the default for dashboard-dispatched scans that don't touch this field.

**D-18 — there is no SSH port list setting, in the config file or the dashboard.** SSH targets are
never enumerated by a dedicated port list; they are derived from protocol-classified open ports
found during discovery (the same fingerprint pass that classifies a port as TLS-, SSH-, or
plaintext-HTTP-carrying). There is nothing to configure, which is why the Advanced panel renders no
"SSH Ports" field (tracked as backlog 999.106 if a dedicated SSH port list is ever wanted).

#### CLI `scan.ports_tls`: email/broker auto-enable is independent of your port list (v5.17 — Phase 173)

The section above documents the **dashboard's** `custom` port scope, which explicitly disables the
email and broker connectors so a narrow custom scan does not also probe the fixed email/broker
service ports. **There is no CLI equivalent of that suppression.** If you hand-author
`scan.ports_tls` in `config.yaml` — narrowing it to, say, a single TLS port — the `standard` and
`deep` profiles still auto-enable `connectors.enable_email` and `connectors.enable_broker`
independently of that list, exactly as they do when `ports_tls` is left at its default. This is
intentional, documented behavior (Phase 32 / Phase 33 D-10 / Phase 72 D-02): a CLI user who runs
`--profile standard` and never touches the `connectors` block should still get full default
crypto-posture coverage of any mail/broker services present, rather than silently missing them
because they didn't know to opt in.

**Operator note.** If you only want the ports you listed in `scan.ports_tls` scanned — no email or
broker probing beyond that list — you must say so explicitly:

```yaml
connectors:
  enable_email: false
  enable_broker: false
```

An explicit `false` here always wins over the profile auto-enable (Phase 72 D-02 / WR-11); this is
the correct, and currently the *only*, way to scope a CLI scan down to exactly your `ports_tls`
list. Narrowing `ports_tls` alone does **not** achieve that — email/broker connectors have their
own fixed service-port tables and are enabled or disabled independently of `scan.ports_tls`.

> **Provenance note (2026-08-29).** An earlier draft of this phase's fix attempted to *infer*
> "the user narrowed the scan" from `ports_tls` being present in config and suppress auto-enable
> automatically. That mechanism shipped, was live-verified, and was reverted the same day: because
> `ports_tls` is a *required* YAML key, the inference fired for every real CLI config, silently
> reversing the auto-enable coverage feature described above for every user — the exact outcome
> this feature exists to prevent. No code changes ship with this note; the underlying behavior is
> unchanged from before Phase 173. See `173-DISPOSITIONS.md` for the full argument.

#### `security.allow_internal_targets`

Added in Phase 121, the QUIRK config supports an explicit operator flag that controls whether internal/loopback targets (RFC1918 ranges, `127.x.x.x`) are allowed when submitting scans from the dashboard:

```yaml
security:
  allow_internal_targets: true   # Set to false on machines that also scan untrusted client environments
```

> **Operator note:** `allow_internal_targets: true` is the correct setting for a QUIRK instance
> that only ever scans your own infrastructure (e.g., a chaos lab or internal assessment server).
> If the same QUIRK instance is used to scan **untrusted client environments**, set this back to
> `false` — it prevents accidental scans of loopback or RFC1918 addresses on the client's network.

#### Port scope in the dashboard

The New Scan page exposes a "Port Scope" selector with the four options described above. Selecting `top1000` or `all` automatically checks and locks the "Enable nmap discovery" checkbox (nmap is required for those scopes). Selecting `common` or `custom` leaves the checkbox user-controlled.

---

#### `security.trusted_targets` (v5.10+ — Phase 143, TAIL-02)

Added in Phase 143, `security.trusted_targets` is a server-enforced scan-consent allowlist —
a list of exact hosts/IPs and CIDR ranges QU.I.R.K. is authorized to scan. It is enforced at a
single shared chokepoint used by **both** the CLI (`quirk`/`run_scan.py`) and the dashboard's
"New Scan" (`/scan/new`) entry point — neither can bypass the gate.

```yaml
security:
  trusted_targets:
    - api.acme.com
    - 10.0.0.5
    - 10.0.0.0/24
```

| Behavior | Rule |
|----------|------|
| **Empty or absent (default)** | Allow-all — backward compatible with every existing scan config/CLI invocation. No enforcement happens. |
| **Populated** | Only the listed hosts/IPs/CIDRs may be scanned. Any target outside the list is rejected **before any scan begins**. |
| **Matching semantics** | Exact host/IP string match, or CIDR containment for entries written as `a.b.c.d/nn`. No wildcard subdomain matching — `*.acme.com` is not supported; list every FQDN explicitly. |
| **CLI rejection** | `run_scan.py` raises `ValueError` naming the redacted out-of-allowlist target, aborting before `init_db()`/scan execution. |
| **Dashboard rejection** | The `/scan/new` → `POST /api/jobs` endpoint returns **HTTP 422** for an out-of-allowlist target — no `ScanJob` database row is created and no subprocess is spawned. |

> **Operator note:** This is an opt-in consent gate, not a security boundary against a malicious
> operator — it exists to prevent an operator (or an automated scheduler) from accidentally
> pointing a shared QUIRK instance at a host outside its authorized engagement scope. Leave it
> empty for single-engagement or lab use where every target is already trusted.

---

### CLI Flag Reference

#### `quirk` — Scan Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--config PATH` | (interactive) | Path to config.yaml; skips interactive prompts when provided |
| `--profile` | `standard` | Scan profile: `quick`, `standard`, `deep` |
| `--score-profile` | `balanced` | Scoring calibration: `lenient`, `balanced`, `strict` |
| `--verbose` | `false` | Verbose output during scan |
| `--progress` | `false` | Show tqdm progress bars |
| `--discovery` | `builtin` | Discovery mode: `builtin` or `nmap` |
| `--nmap-path` | `nmap` | Path to nmap executable |
| `--nmap-timeout` | `1800` | **Deprecated — has no effect** (Phase 146 DISC-05). Chunked discovery derives its per-batch budget from `discovery_timeout_for_batch()` = `min(300, 30 + 0.26 × batch_size)` seconds; no code path reads this flag. To change the budget, reduce discovery scope or adjust the `_DISCOVERY_TIMEOUT_*` constants in `quirk/discovery/nmap_provider.py`. See operators-guide.md §11.4. |
| `--nmap-extra-args` | `""` | Extra nmap arguments (pass as quoted string) |
| `--safe-mode` | `false` | Reduce concurrency and increase timeouts for fragile networks |
| `--rate-limit` | `0.0` | Targets per second rate limit (0 = disabled) |
| `--cache` | `false` | Enable discovery/fingerprint result cache |
| `--cache-ttl-hours` | `24` | Cache time-to-live in hours |
| `--resume` | `false` | Reuse cache if valid (skip re-discovery) |
| `--force-discovery` | `false` | Ignore existing discovery cache and re-run |
| `--inventory-code-signing` | `false` | Inventory code-signing certificates from LDAP `userCertificate` attributes and in-process TLS EKU check (Phase 95 CSIGN-01) |
| `--fuzz` | `false` | Enable active REST crypto-posture fuzzing (requires `--openapi-spec`; TTY `CONFIRM` prompt; hard-aborts in non-TTY) |
| `--fuzz-jwt-alg-confusion` | `false` | Also run JWT RS256→HS256 algorithm-confusion probe; acceptance = CRITICAL |
| `--fuzz-budget N` | `50` | Maximum probe requests (hard max **500**; values above 500 are rejected) |

#### `quirk serve` — Dashboard Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--port` | `8512` | Port to serve the dashboard on |
| `--host` | `127.0.0.1` | Host address to bind |
| `--no-open` | `false` | Suppress auto-opening of browser on startup |

```bash
# Start dashboard on default port
quirk serve

# Start on a different port without auto-opening the browser
quirk serve --port 9000 --no-open

# Bind to all interfaces (e.g. for a remote development server)
quirk serve --host 0.0.0.0 --port 8512
```

#### CORS Allowlist (v5.11 — Phase 147, DRAIN-03 / WR-02)

The dashboard API rejects cross-origin browser requests whose `Origin` header isn't in an allowlist. Resolution order:

1. `QUIRK_CORS_ORIGINS` (comma-separated list) — always wins if set.
2. `security.cors_origins` in your YAML config file (`QUIRK_CONFIG_PATH`, default `./config.yaml`).
3. **Port-aware default** — if neither is set, the allowlist is built from the port `quirk serve` actually bound (via `QUIRK_DASHBOARD_PORT`, set automatically by `serve()`), e.g. `http://127.0.0.1:9000` and `http://localhost:9000` for `quirk serve --port 9000`. The port-less `http://127.0.0.1` / `http://localhost` entries are always included too, so reverse-proxy-on-port-80 deployments keep working.

Before Phase 147, the default was a hardcoded port-less pair (`http://127.0.0.1`, `http://localhost`) that could never match a real browser `Origin` header for the product's own default bind (`127.0.0.1:8512`) — every out-of-box dashboard load hit a CORS rejection unless an operator manually set `QUIRK_CORS_ORIGINS`. This is fixed automatically now; no operator action required for the default single-machine case. For a real deployment behind a domain name, still set `QUIRK_CORS_ORIGINS` explicitly — see [Cloud Console Deployment](deployment-cloud-console.md#security-checklist).

#### `quirk token` — Dashboard API Token CLI (Phase 102, AUTH-01)

The `quirk token` subcommand manages the `security.api_token` key in your QUIRK YAML config. The token is used to authenticate requests to the dashboard API and browser login form.

| Subcommand | Description |
|------------|-------------|
| `quirk token generate` | Mint a new CSPRNG token (`secrets.token_urlsafe(32)`) and write it to `security.api_token` in your config file. Prints the token to stdout so you can copy it for browser login. |
| `quirk token rotate` | Identical to `generate` — overwrites `security.api_token` with a new token, immediately invalidating the previous one. Any active dashboard session using the old token will be returned to the login form on the next API request. |
| `quirk token show` | Print the currently persisted token from the YAML config file. Reads the raw YAML value; does **not** read `QUIRK_API_TOKEN`. Exits 1 if the config file is not found. |

Pass `--config /path/to/config.yaml` to any subcommand to target a non-default config location.

```bash
# Generate a token and write it to config.yaml
quirk token generate --config config.yaml

# Rotate the token (invalidates the old one immediately)
quirk token rotate --config config.yaml

# Show the currently configured token (reads YAML, not env var)
quirk token show --config config.yaml
```

> **Precedence note:** If `QUIRK_API_TOKEN` is set in the environment, it takes precedence over the `security.api_token` YAML value at runtime. `quirk token show` always displays the YAML-persisted value; if the env var is set, a reminder is printed indicating that the env var overrides the file value for the running dashboard process.

> **Security note:** `quirk token show` echoes the raw token to the terminal, which may appear in terminal scrollback. This is a local-operator tool convenience — the token is never transmitted over the network by this command. Never embed the token value in shell scripts, version-controlled config files, or URLs.

---

### Dashboard Authentication (Phase 102, AUTH-01..03)

The QUIRK dashboard (served by `quirk serve`) optionally enforces token-based authentication on all `/api/*` routes. Authentication is **off by default** — an empty or absent `security.api_token` means the dashboard is accessible without credentials (suitable for local development only).

#### Enabling authentication

Add a `security:` block to your QUIRK YAML config and populate `api_token`:

```yaml
security:
  api_token: ""   # populated by: quirk token generate --config config.yaml
```

Run `quirk token generate --config config.yaml` to write a random token into this field. Once the token is non-empty, the dashboard requires authentication on every `/api/*` request.

#### Token precedence

| Source | Precedence | Notes |
|--------|-----------|-------|
| `QUIRK_API_TOKEN` env var | **Highest** | Set this in production deployments; overrides YAML at startup |
| `security.api_token` in YAML | Default | Written by `quirk token generate` / `quirk token rotate` |

#### API authentication (programmatic clients)

All `/api/*` endpoints accept a token via two equivalent headers. **`X-API-Key` takes precedence** — if it is present, `Authorization: Bearer` is not consulted.

| Header | Format | Notes |
|--------|--------|-------|
| `X-API-Key` | `X-API-Key: <token>` | Preferred for API clients |
| `Authorization` | `Authorization: Bearer <token>` | Fallback; supported for compatibility |

Both paths use `hmac.compare_digest` for timing-safe comparison. An invalid or absent token on a protected route returns HTTP 401 with error code `DASHBOARD-001`.

```bash
# Using X-API-Key (preferred)
curl -H "X-API-Key: <your-token>" http://localhost:8512/api/scans

# Using bearer token (fallback)
curl -H "Authorization: Bearer <your-token>" http://localhost:8512/api/scans
```

#### Browser login flow

1. Open the dashboard in a browser (`http://localhost:8512` by default).
2. If authentication is enabled, you are presented with a "Dashboard Login" card. Paste your token (from `quirk token show`) into the password field and click **Unlock Dashboard**.
3. A correct token loads the full dashboard. An incorrect token shows an inline error ("Invalid token. Check your token and try again.") and clears the input — no page redirect occurs.
4. Click **Sign out** in the sidebar to clear the session and return to the login form. The token is removed from browser storage immediately.
5. **Mid-session token rotation:** If you run `quirk token rotate` while a browser session is open, the next API request from that session returns HTTP 401 and the dashboard automatically returns you to the login form. Re-enter the new token to resume.

#### Auth-disabled passthrough (development convenience)

When `security.api_token` is empty and `QUIRK_API_TOKEN` is not set, the dashboard serves all routes without authentication. This is intentional for local development and single-operator use. Do not deploy the dashboard on a network-accessible interface without setting a token.

---

### Vertical Editions (v5.6+)

The dashboard can run as a vertical-specific "edition" that tailors the UI for an
industry deployment. This is an **operator-side deployment setting, not a user-facing
picker** — the active vertical is resolved once at server startup and every browser
session sees the same edition. General installs are visually identical to
pre-vertical QU.I.R.K.

#### Allowed values

| Vertical | Effect |
|----------|--------|
| `general` | Default. No vertical-specific UI; identical to pre-vertical QU.I.R.K. |
| `healthcare` | Adds a "Healthcare Posture" sidebar nav item + HIPAA posture page (`/healthcare`), a "Healthcare Edition" badge under the wordmark, and an EHR/PACS/portal scan preset on the New Scan page |

#### Resolution order

| Source | Precedence | Notes |
|--------|-----------|-------|
| `QUIRK_VERTICAL` env var | **Highest** | Case-insensitive; whitespace trimmed |
| `vertical:` key in YAML config | Default | Read from the file at `QUIRK_CONFIG_PATH` (default `./config.yaml`) — **not** the `--config` CLI flag |
| Neither set | Fallback | `general` |

Unknown or invalid values **fall back silently to `general`** — they do not raise an
error. If you set `QUIRK_VERTICAL=healthcre` (typo), you get a general-edition
dashboard with no warning, so verify with the endpoint below after startup.

```yaml
# In config.yaml (must be the file QUIRK_CONFIG_PATH points at):
vertical: healthcare   # top-level key; allowed: general | healthcare
```

```bash
# Env var wins over YAML — useful for one-off sessions:
QUIRK_VERTICAL=healthcare quirk serve
```

#### Verifying the active vertical

`GET /api/config` returns the resolved vertical. Like `/api/health`, this endpoint is
**unauthenticated** (the frontend needs it before login) and exposes only the vertical
name — no secrets or scan data.

```bash
curl http://127.0.0.1:8512/api/config
# {"vertical":"healthcare"}
```

#### Adding a new vertical (developers)

All vertical UI reads from a single descriptor registry — there are no scattered
conditionals. A new vertical (e.g. Manufacturing, Retail) requires only:

1. A descriptor entry in `src/dashboard/src/lib/verticals.ts` (label, icon, accent
   color, optional nav item / scan preset / page component).
2. A page component, if the vertical has a dedicated route.
3. The vertical name added to `_ALLOWED_VERTICALS` in `quirk/config.py`.

---

### Minimal Valid Configuration

The minimum configuration to run a first scan. All other keys use their defaults.

```yaml
assessment:
  name: "Quantum Crypto Readiness - CLIENT NAME"
  data_classification: "confidential"
  report_owner: "CLIENT NAME"
  timezone: "America/New_York"

targets:
  cidrs: [127.0.0.1]
```

Save this as `config.yaml` in your working directory, then run:

```bash
quirk --config config.yaml
```

---

### Full Reference Configuration

A complete `config.yaml` showing all keys with their defaults, as a copy-pasteable template:

```yaml
assessment:
  name: "Quantum Crypto Readiness - CLIENT NAME"
  data_classification: "confidential"   # public|internal|confidential|regulated
  report_owner: "CLIENT NAME"
  timezone: "America/New_York"

scan:
  timeout_seconds: 5
  concurrency: 200
  ports_tls: [443, 8443, 9443, 10443, 4433, 5001, 636, 3269, 993, 995, 465, 6443, 2376, 5432, 3306, 1433, 8200]
  include_sni: true
  tls_enum_mode: fast                   # off|fast|deep
  fingerprint_timeout_seconds: 2
  fingerprint_concurrency: 200
  tls_timeout_seconds: 5
  tls_concurrency: 150
  ssh_timeout_seconds: 5
  ssh_concurrency: 100

targets:
  fqdns: []
  cidrs: [127.0.0.1]
  include_ips: []
  exclude_ips: []

connectors:
  enable_aws: false
  enable_azure: false
  enable_adcs: false
  adcs_targets: []
  adcs_search_base: null
  adcs_user: null
  adcs_password: null
  adcs_timeout: 10
  enable_jwt: true
  enable_container: true
  enable_source: true
  aws_region: "us-east-1"
  aws_profile: null
  azure_subscription_id: null
  azure_keyvault_urls: []
  jwt_targets: []
  container_targets: []
  source_targets: []
  codesign_targets: []
  codesign_search_base: null
  codesign_timeout: 10
  enable_modbus: false
  enable_bacnet: false
  enable_recurring_otics: false

output:
  directory: "quirk-output"
  db_path: "./quirk-output/quirk.db"

intelligence:
  intelligence_version: "3.9.0"
  profile: "balanced"                   # lenient|balanced|strict
  calibration_overrides: {}

remediation_aliases: {}
```

---

### Notifications (v5.3+)

Phase 101 introduces a global notification system that alerts operators after each scheduled scan when HIGH/CRITICAL findings appear or the quantum-readiness score regresses. Notifications are **off by default** — opt in by adding a `[notifications]` block to your QUIRK YAML config.

#### Prerequisites

**Set `QUIRK_CONFIG_PATH`** to the path of your QUIRK YAML config file before starting the scheduler. The scheduler's `--config` argument points to the SQLite database; the notification system reads its YAML config from `QUIRK_CONFIG_PATH`.

```bash
export QUIRK_CONFIG_PATH=/etc/quirk/config.yaml
export QUIRK_DB_PATH=/var/lib/quirk/quirk.db
quirk schedule run --config "$QUIRK_DB_PATH"
```

Both env vars must be set for scheduled notifications to work (Assumption A2).

#### Trigger rules (NOTIFY-02)

A notification fires when **either** of these conditions is met:

| Condition | Threshold |
|-----------|-----------|
| New HIGH or CRITICAL findings since the last scan | ≥ 1 new HIGH/CRITICAL |
| Readiness score regression | Score drops more than `trigger_score_floor` points |

Notifications are **never** sent on:
- The very first scan (no previous baseline to compare against)
- MEDIUM-only changes with score delta within the floor

#### Notification config block

Add a `notifications:` block at the top level of your QUIRK YAML config:

```yaml
notifications:
  trigger_score_floor: -5       # notify when score drops more than 5 points (default -5)
  notify_on_hardware_lifecycle: false   # hardware lifecycle alerts (HWLC-14, default false)

  # Optional: Slack incoming-webhook delivery (NOTIFY-03)
  slack:
    slack_webhook_env: QUIRK_SLACK_WEBHOOK      # env var NAME holding the webhook URL
    dashboard_base_url: https://quirk.internal  # optional link in Slack messages

  # Optional: Email delivery via SMTP (NOTIFY-04)
  email:
    smtp_host: smtp.corp.com
    smtp_port: 587              # 587 = STARTTLS (default), 465 = SSL
    smtp_from: quirk@corp.com
    recipients:
      - security@corp.com
      - oncall@corp.com
    smtp_user: quirk-svc        # omit for unauthenticated relay
    smtp_password_env: QUIRK_SMTP_PASSWORD  # env var NAME holding the password
    use_ssl: false              # true = SMTP_SSL (port 465); false = STARTTLS (port 587)
    timeout_seconds: 10

  # Optional: Generic outbound webhook (NOTIFY-05)
  webhook:
    url_env: QUIRK_WEBHOOK_URL          # env var NAME holding the target URL
    hmac_key_env: QUIRK_WEBHOOK_HMAC_KEY  # env var NAME for HMAC-SHA256 signing key (optional)
    timeout_seconds: 10
```

#### `notify_on_hardware_lifecycle` (Phase 161 — HWLC-14)

| Key | Type | Default | Scope |
|---|---|---|---|
| `notify_on_hardware_lifecycle` | boolean | `false` | Top-level key of the `notifications:` block |

Opts the deployment in to hardware lifecycle alerts. When a scan reconciles a
qualifying hardware drift event — a **worsening** remediation-tier crossing, or
any EOL/EOS state change — QUIRK delivers a notification describing it.

Three things to know before enabling it:

- **It is a global, deployment-level switch**, not a per-device or
  per-consultant preference. There is no per-host or per-vendor opt-in; the
  whole scanned estate participates or none of it does.
- **It fans out to email and webhook only.** Slack is deliberately not a
  destination for lifecycle alerts.
- **It requires no additional configuration.** Delivery reuses the existing
  `email:` and `webhook:` blocks and the same environment-variable credential
  model documented below. If neither is configured, enabling this key changes
  nothing.

Leaving the key absent is identical to setting it to `false`.

#### Environment variables for secrets

**Secrets must never appear in the YAML config.** The config stores only the *name* of the environment variable; the actual secret is read from the environment at delivery time and is never persisted.

| Env var name | Purpose | Example value |
|---|---|---|
| `QUIRK_SLACK_WEBHOOK` | Slack incoming-webhook URL | `https://hooks.slack.com/services/T.../B.../xxx` |
| `QUIRK_SMTP_PASSWORD` | SMTP account password | `s3cr3t` |
| `QUIRK_WEBHOOK_URL` | Target webhook endpoint | `https://siem.corp.com/api/events` |
| `QUIRK_WEBHOOK_HMAC_KEY` | HMAC-SHA256 signing key | `a-long-random-string` |
| `QUIRK_CONFIG_PATH` | Path to QUIRK YAML config | `/etc/quirk/config.yaml` |

> **Note on naming:** The config field `slack_webhook_env: QUIRK_SLACK_WEBHOOK` means "read the webhook URL from the env var named `QUIRK_SLACK_WEBHOOK`". You can use any env var name — the convention shown above is recommended.

#### Operational environment variables

These are not secrets — they change runtime behaviour and have no config-file equivalent.

| Env var name | Default | Purpose |
|---|---|---|
| `QUIRK_OUTPUT_DIR` | `output` | Base directory the **scheduler** writes run output to (`quirk/cli/scheduler_cmd.py`). Note this default is independent of `output.directory` in the YAML config — if you have moved `output.directory` to `quirk-output`, set this to match, or scheduled runs will write somewhere else. |
| `QUIRK_SERVE_HOST` | unset | Host the dashboard is reachable on, used when building the URL allowlist (`quirk/util/url_allowlist.py`). Set it when serving behind a reverse proxy whose hostname differs from the bind address. |
| `QUIRK_SERVE_PORT` | unset | Companion to `QUIRK_SERVE_HOST` for the same allowlist. |

Two further variables — `QUIRK_SENSOR_IP_ALLOWLIST` and `QUIRK_HSTS` — are **security** controls and
are documented in [Admin Guide §3.5](#35-hardening-environment-variables).

#### Security controls

| Control | Description |
|---------|-------------|
| **SSRF protection** | Every channel validates the destination URL/host via `validate_external_url()` before connecting — loopback, RFC1918, and cloud metadata IPs are blocked (ISEC-01). |
| **Secret scrubbing** | Any exception raised during delivery is passed through `safe_str()` before being written to the `integration_deliveries` audit log — Slack tokens (`xoxb-*`), SMTP passwords, and webhook URLs are redacted (ISEC-02). |
| **Failure isolation** | A delivery failure on one channel never blocks other channels or corrupts the scan record. The scheduler `_dispatch_schedule` wraps the entire notification call in `try/except` (NOTIFY-07). |
| **Optional Slack dep** | `slack_sdk` is an optional dependency. Missing `slack_sdk` logs a WARNING instead of raising `ImportError`. Install with `pip install quirk-scanner[notify]` (ISEC-04). |
| **Outbound whitelist** | Webhook payloads contain only drift-level aggregate fields (scores, counts). Host/IP/protocol topology is excluded from all outbound integration payloads (ISEC-03). |

#### Installing the Slack dependency

Slack delivery requires `slack_sdk`:

```bash
pip install "quirk-scanner[notify]"
```

This extra is included in `[all]`. Email and webhook delivery use Python stdlib only — no extra installation needed.

#### Audit log

Every delivery attempt — successful or failed — writes one row to the `integration_deliveries` SQLite table:

| Column | Description |
|--------|-------------|
| `scan_id` | ISO timestamp identifying the scan session |
| `destination` | `"slack"` / `"email"` / `"webhook"` |
| `status` | `"ok"` or `"failed"` |
| `attempted_at` | UTC timestamp of the delivery attempt |
| `error_summary` | `safe_str(exc)` on failure — secrets are always scrubbed |

Query the audit log from the QUIRK database:

```bash
sqlite3 "$QUIRK_DB_PATH" \
  "SELECT attempted_at, destination, status, error_summary FROM integration_deliveries ORDER BY attempted_at DESC LIMIT 20;"
```

---

### SIEM Export (syslog/CEF)

Phase 103 introduces SIEM export via syslog with Common Event Format (CEF). QUIRK formats each
finding as a CEF:0 event and delivers it to a syslog collector over UDP or TCP. Export is
**off by default** — opt in by adding a `siem:` block to your QUIRK YAML config.

> **Network placement:** syslog is plaintext (no TLS). Place your syslog collector on a trusted
> internal network segment. TLS-wrapped syslog (RFC 5425), Splunk HEC, and Elastic-native output
> are planned for a future release.

#### Prerequisites

**Set `QUIRK_CONFIG_PATH`** to the path of your QUIRK YAML config file before running the
scheduler. The scheduler's `--config` argument points to the SQLite database; the SIEM system
reads its YAML config from `QUIRK_CONFIG_PATH`.

```bash
export QUIRK_CONFIG_PATH=/etc/quirk/config.yaml
export QUIRK_DB_PATH=/var/lib/quirk/quirk.db
quirk schedule run --config "$QUIRK_DB_PATH"
```

#### `siem:` config block

Add a `siem:` block at the top level of your QUIRK YAML config:

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `host` | string | *(required)* | Hostname or IP of your syslog/CEF collector |
| `port` | int | `514` | UDP or TCP port of the collector |
| `protocol` | string | `"udp"` | Transport: `"udp"` or `"tcp"` |
| `export_after_scan` | bool | `false` | Automatically export findings after each scheduled scan completes |
| `timeout_seconds` | int | `5` | Socket send timeout in seconds |

```yaml
siem:
  host: siem.corp.example.com
  port: 514
  protocol: udp          # udp (default) or tcp
  export_after_scan: true
  timeout_seconds: 5
```

#### CLI usage: `quirk export --siem`

Export findings from the most recent scan to your SIEM at any time:

```bash
# Export the most recent findings-*.json in the default output directory
quirk export --siem

# Specify an explicit findings file
quirk export --siem --input quirk-output/findings-2026-05-25-120000.json

# Specify the output directory to search for the latest findings file
quirk export --siem --output-dir /var/lib/quirk/output
```

**Prerequisites:**
- `QUIRK_CONFIG_PATH` must be set and point to a YAML config with a valid `siem:` block.
- `QUIRK_DB_PATH` must point to the QUIRK SQLite database (used to write the audit row).

Exit codes: `0` = all events delivered; `1` = config/flag error; `2` = no findings file found.

#### CEF field mapping

Each finding produces one `CEF:0` event. QUIRK maps finding fields as follows:

| CEF field | Finding field | Notes |
|-----------|--------------|-------|
| Header severity | `severity` | `CRITICAL=10`, `HIGH=8`, `MEDIUM=5`, `LOW=3`; unknown defaults to 3 |
| `name` (header) | `title` | Pipe characters escaped as `\|`; backslash as `\\` |
| `signature` (header) | `category` → `id` → slugified title | Falls back when `category`/`id` absent |
| `dhost` | `host` | Scanned host |
| `dpt` | `port` | Scanned port |
| `cs1` | `category` | Finding category label |
| `cs2` | `description` | Truncated at 256 characters |
| `msg` | `recommendation` | Truncated at 256 characters |

**Payload safety:** The CEF payload contains only the fields listed above. Certificate PEM data,
certificate SANs, private key material, PKI topology details, and compliance control mappings are
**never** included in the CEF event. All extension field values are escaped: backslash becomes
`\\`, equals becomes `\=`, and newlines become the literal two-character sequence `\n`.

#### Semantics

- **One event per finding:** Each finding in the findings JSON produces one CEF event. A scan
  with 30 findings produces 30 events.
- **After-scan export:** When `export_after_scan: true`, the SIEM export hook fires automatically
  after each scheduled scan completes. The hook is isolated — a SIEM delivery failure never
  aborts the scan, corrupts the scan record, or blocks other integrations (NOTIFY-07 / SIEM-01).
- **Audit log:** Every export attempt — successful or failed — writes one row to the
  `integration_deliveries` SQLite table with `destination="siem"`, `status="ok"/"failed"`, and
  a scrubbed `error_summary` on failure.
- **TCP framing:** Raw TCP (no octet-count prefix, no TLS). Configure your receiver for
  traditional LF-terminated or raw-bytes syslog input.

#### Audit log

Query the audit log from the QUIRK database:

```bash
sqlite3 "$QUIRK_DB_PATH" \
  "SELECT attempted_at, destination, status, error_summary FROM integration_deliveries WHERE destination='siem' ORDER BY attempted_at DESC LIMIT 20;"
```

#### Deferred

The following SIEM delivery paths are planned for a future release and are **not** available in
Phase 103:
- TLS-wrapped syslog (RFC 5425)
- Splunk HTTP Event Collector (HEC)
- Elastic-native output (Elasticsearch ingest API)

---

### Jira Ticketing (v5.3+)

Phase 104 introduces per-finding Jira issue creation. QUIRK opens one Jira issue per
finding discovered during a scan, tags each issue with a SHA-256 fingerprint label for
dedup, and adds a rediscovery comment on re-runs instead of creating duplicate issues.
Ticketing is **off by default** — opt in by adding a `ticketing:` block to your QUIRK
YAML config.

> **Note:** ServiceNow ticketing (TICKET-02) arrives in Phase 105, reusing the same
> abstraction. The `ticketing.jira` block documented here does not change when ServiceNow
> is added.

#### Prerequisites

Install the `[tickets]` extras group before using `quirk ticket create`:

```bash
pip install "quirk-scanner[tickets]"
```

This installs `jira>=3.10.5`. The `[tickets]` group is included in `[all]`. Running
`quirk ticket create` without `[tickets]` installed prints a missing-extra advisory and
exits with code 2 — no ImportError traceback is raised.

**Set `QUIRK_CONFIG_PATH`** to your QUIRK YAML config before running the ticket command:

```bash
export QUIRK_CONFIG_PATH=/etc/quirk/config.yaml
export QUIRK_DB_PATH=/var/lib/quirk/quirk.db
quirk ticket create --input quirk-output/findings-2026-05-25-120000.json
```

#### `ticketing.jira` config block

Add a `ticketing:` block at the top level of your QUIRK YAML config:

| Key | Type | Default | Required | Description |
|-----|------|---------|----------|-------------|
| `jira_url` | string | *(required)* | Yes | Base URL of your Jira instance (e.g. `https://acme.atlassian.net`) |
| `jira_user_env` | string | *(required)* | Yes | **Name** of the env var holding your Jira username or email — not the value itself |
| `jira_token_env` | string | *(required)* | Yes | **Name** of the env var holding your Jira API token or PAT — not the value itself |
| `project_key` | string | *(required)* | Yes | Jira project key (e.g. `SEC`) |
| `issue_type` | string | `"Bug"` | No | Jira issue type to create (e.g. `"Bug"`, `"Task"`, `"Security Finding"`) |
| `auth_mode` | string | `"cloud"` | No | Authentication mode: `"cloud"` or `"server"` |
| `allow_internal` | bool | `false` | No | Set `true` for self-hosted Jira on RFC1918 networks (see SSRF note below) |

```yaml
ticketing:
  jira:
    jira_url: https://acme.atlassian.net
    jira_user_env: QUIRK_JIRA_USER      # env var NAME holding your Jira email
    jira_token_env: QUIRK_JIRA_TOKEN    # env var NAME holding your Jira API token or PAT
    project_key: SEC
    issue_type: Bug                     # default
    auth_mode: cloud                    # cloud (default) or server
    allow_internal: false               # set true for self-hosted Jira on RFC1918
```

#### Credential isolation model

**Credentials must never appear in the YAML config.** The config stores only the *name*
of the environment variable; QUIRK reads the actual credential from the environment at
run time. Credentials are never:

- Written to the YAML config or SQLite database
- Included in log files or exception messages (safe_str scrubs Authorization headers)
- Included in CBOM output, PDF exports, or dashboard API responses

| Field | Env var name you set | Example env var value |
|-------|---------------------|-----------------------|
| `jira_user_env: QUIRK_JIRA_USER` | `QUIRK_JIRA_USER` | `alice@acme.com` |
| `jira_token_env: QUIRK_JIRA_TOKEN` | `QUIRK_JIRA_TOKEN` | `ATATT3xFfGF0...` |

#### Cloud vs. server authentication

| `auth_mode` | Jira edition | Credential used | SDK call |
|-------------|-------------|-----------------|----------|
| `cloud` (default) | Jira Cloud (atlassian.net) | Email + API token → HTTP Basic | `JIRA(basic_auth=(user, token))` |
| `server` | Jira Data Center / Server (self-hosted) | Personal Access Token (PAT) | `JIRA(token_auth=token)` |

For Jira Cloud, generate an API token at **Account Settings → Security → API tokens**.
For Jira Data Center/Server, generate a PAT under **Profile → Personal Access Tokens**.

#### SSRF protection

`jira_url` is validated by QUIRK's `validate_external_url()` guard before any connection
is made. Loopback addresses (`127.x.x.x`), RFC1918 ranges (`10.x`, `172.16–31.x`,
`192.168.x`), and cloud metadata IPs (`169.254.169.254`) are blocked by default.

For self-hosted Jira deployed on an internal network, set `allow_internal: true`. This
allows RFC1918 `jira_url` values while still blocking cloud metadata IPs.

#### CLI usage: `quirk ticket create`

Create Jira issues from a completed scan's findings file:

```bash
# Create issues from the most recent findings-*.json in the default output directory
quirk ticket create

# Specify an explicit findings file
quirk ticket create --input quirk-output/findings-2026-05-25-120000.json

# Specify the output directory to search for the latest findings file
quirk ticket create --output-dir /var/lib/quirk/output
```

**Prerequisites:**
- `pip install "quirk-scanner[tickets]"` (or `[all]`)
- `QUIRK_CONFIG_PATH` set and pointing to a YAML config with a valid `ticketing.jira` block
- `QUIRK_DB_PATH` set to the QUIRK SQLite database (used to write audit rows)
- `QUIRK_JIRA_USER` and `QUIRK_JIRA_TOKEN` set in the environment

Exit codes: `0` = all findings dispatched; `1` = config error; `2` = missing `[tickets]`
extra, no findings file found, or missing config.

#### Dedup and rediscovery behavior

QUIRK computes a SHA-256 fingerprint for each finding using the formula
`SHA256(host:port::title)`. On every `quirk ticket create` run:

- **New finding** (fingerprint not seen): one Jira issue is created and the fingerprint is
  stored in the `integration_deliveries` audit table.
- **Rediscovery** (fingerprint already in `integration_deliveries`): a comment is added to
  the existing Jira issue noting the rediscovery. No duplicate issue is created.

Re-running `quirk ticket create` against the same findings file is safe — it produces
zero duplicate issues on all subsequent runs.

#### Audit log

Every ticket dispatch attempt — successful or failed — writes one row to the
`integration_deliveries` SQLite table:

| Column | Description |
|--------|-------------|
| `scan_id` | Scan session identifier |
| `finding_hash` | SHA-256 fingerprint of the finding (`host:port::title`) |
| `destination` | `"jira"` |
| `status` | `"ok"` or `"failed"` |
| `attempted_at` | UTC timestamp of the dispatch attempt |
| `error_summary` | `safe_str(exc)` on failure — Authorization headers always scrubbed |

Query the audit log:

```bash
sqlite3 "$QUIRK_DB_PATH" \
  "SELECT finding_hash, status, attempted_at, error_summary FROM integration_deliveries WHERE destination='jira' ORDER BY attempted_at DESC LIMIT 20;"
```

---

### ServiceNow Ticketing (v5.3+)

Phase 105 adds ServiceNow incident creation as a second ticketing backend, reusing the
same `TicketingChannel` abstraction as Jira. QUIRK opens one ServiceNow incident per
finding, stores a SHA-256 fingerprint in the `correlation_id` field for dedup, and
appends a `work_notes` journal entry on re-runs instead of creating duplicate incidents.
Ticketing is **off by default** — opt in by adding a `ticketing.servicenow` block to
your QUIRK YAML config.

> **Note:** Both `ticketing.jira` and `ticketing.servicenow` blocks can coexist in the
> same config file; the `--backend` flag selects which backend is used at runtime.

#### Prerequisites

Install the `[tickets]` extras group before using `quirk ticket create --backend servicenow`:

```bash
pip install "quirk-scanner[tickets]"
```

The `[tickets]` group is included in `[all]`. The ServiceNow backend uses only stdlib
`urllib` — no additional packages beyond `[tickets]` are required. Running
`quirk ticket create` without `[tickets]` installed prints a missing-extra advisory and
exits with code 2 — no ImportError traceback is raised.

**Set `QUIRK_CONFIG_PATH`** to your QUIRK YAML config before running the ticket command:

```bash
export QUIRK_CONFIG_PATH=/etc/quirk/config.yaml
export QUIRK_DB_PATH=/var/lib/quirk/quirk.db
quirk ticket create --backend servicenow --input quirk-output/findings-2026-05-25-120000.json
```

#### `ticketing.servicenow` config block

Add a `servicenow:` sub-block under the `ticketing:` section of your QUIRK YAML config:

| Key | Type | Default | Required | Description |
|-----|------|---------|----------|-------------|
| `instance_url` | string | *(required)* | Yes | Base URL of your ServiceNow instance — **must use `https://`** (http:// is rejected at parse time) |
| `user_env` | string | *(required)* | Yes | **Name** of the env var holding your ServiceNow username — not the value itself |
| `password_env` | string | *(required)* | Yes | **Name** of the env var holding your ServiceNow password — not the value itself |
| `table` | string | `"incident"` | No | ServiceNow table to create records in (default: `incident`) |
| `allow_internal` | bool | `false` | No | Set `true` for self-hosted ServiceNow on RFC1918 networks (see SSRF note below) |

```yaml
ticketing:
  servicenow:
    instance_url: https://acme.service-now.com  # MUST be https://; http:// is rejected
    user_env: QUIRK_SNOW_USER                   # env var NAME holding your ServiceNow username
    password_env: QUIRK_SNOW_PASSWORD           # env var NAME holding your ServiceNow password
    table: incident                             # optional; default is incident
    allow_internal: false                       # set true for self-hosted on RFC1918
```

#### Credential isolation model

**Credentials must never appear in the YAML config.** The config stores only the *name*
of the environment variable; QUIRK reads the actual credential from the environment at
run time. Credentials are never:

- Written to the YAML config or SQLite database
- Included in log files or exception messages (safe_str scrubs Authorization headers)
- Included in CBOM output, PDF exports, or dashboard API responses

| Field | Env var name you set | Example env var value |
|-------|---------------------|-----------------------|
| `user_env: QUIRK_SNOW_USER` | `QUIRK_SNOW_USER` | `quirk_scanner` |
| `password_env: QUIRK_SNOW_PASSWORD` | `QUIRK_SNOW_PASSWORD` | `S3cr3tP@ss!` |

Set these before running `quirk ticket create`:

```bash
export QUIRK_SNOW_USER=quirk_scanner
export QUIRK_SNOW_PASSWORD=S3cr3tP@ss!
quirk ticket create --backend servicenow
```

#### SSRF protection and https-only enforcement

`instance_url` is validated by two guards before any connection is made:

1. **https-only parse-time check** — `_parse_servicenow_cfg` returns `None` (config load
   fails) if `instance_url` does not start with `https://`. This check fires before any
   DNS lookup or TCP connection.
2. **`validate_external_url()` runtime guard** — Loopback addresses (`127.x.x.x`), RFC1918
   ranges (`10.x`, `172.16–31.x`, `192.168.x`), and cloud metadata IPs (`169.254.169.254`)
   are blocked by default.

For self-hosted ServiceNow deployed on an internal network, set `allow_internal: true`.
This allows RFC1918 `instance_url` values while still blocking cloud metadata IPs.

#### CLI usage: `quirk ticket create --backend servicenow`

Create ServiceNow incidents from a completed scan's findings file:

```bash
# Create incidents using the ServiceNow backend (default backend is jira)
quirk ticket create --backend servicenow

# Specify an explicit findings file
quirk ticket create --backend servicenow --input quirk-output/findings-2026-05-25-120000.json

# Specify the output directory to search for the latest findings file
quirk ticket create --backend servicenow --output-dir /var/lib/quirk/output
```

**Prerequisites:**
- `pip install "quirk-scanner[tickets]"` (or `[all]`)
- `QUIRK_CONFIG_PATH` set and pointing to a YAML config with a valid `ticketing.servicenow` block
- `QUIRK_DB_PATH` set to the QUIRK SQLite database (used to write audit rows)
- `QUIRK_SNOW_USER` and `QUIRK_SNOW_PASSWORD` set in the environment

Exit codes: `0` = all findings dispatched; `1` = config error; `2` = missing `[tickets]`
extra, no findings file found, or missing config.

#### Dedup and rediscovery behavior

QUIRK computes a SHA-256 fingerprint for each finding using the formula
`SHA256(host:port::title)` — identical to the Jira backend, ensuring cross-backend
identity consistency. On every `quirk ticket create --backend servicenow` run:

- **New finding** (fingerprint not seen): one ServiceNow incident is created, with the
  SHA-256 fingerprint stored in the `correlation_id` field. The incident's `sys_id`
  (not the INC-number) is used for subsequent PATCH operations.
- **Rediscovery** (fingerprint already in `integration_deliveries`): QUIRK issues a
  `PATCH` to the existing incident's `work_notes` field, appending a journal entry
  noting the rediscovery date and QUIRK run context. No duplicate incident is created.

Re-running `quirk ticket create --backend servicenow` against the same findings file is
safe — it produces zero duplicate incidents on all subsequent runs.

#### Audit log

Every ticket dispatch attempt — successful or failed — writes one row to the
`integration_deliveries` SQLite table:

| Column | Description |
|--------|-------------|
| `scan_id` | Scan session identifier |
| `finding_hash` | SHA-256 fingerprint of the finding (`host:port::title`) |
| `destination` | `"servicenow"` |
| `status` | `"ok"` or `"failed"` |
| `attempted_at` | UTC timestamp of the dispatch attempt |
| `error_summary` | `safe_str(exc)` on failure — Authorization headers always scrubbed |

Query the audit log:

```bash
sqlite3 "$QUIRK_DB_PATH" \
  "SELECT finding_hash, status, attempted_at, error_summary FROM integration_deliveries WHERE destination='servicenow' ORDER BY attempted_at DESC LIMIT 20;"
```

---

### Compliance Frameworks

QUIRK's `COMPLIANCE_MAP` (in `quirk/compliance/__init__.py`) maps every finding
category to one or more of the following frameworks. As of Phase 52 (v4.7), all
frameworks are kept fresh by the `STALENESS_THRESHOLD_DAYS` gate and verified
by `quirk doctor` before each scan.

| Framework | Version | Builder helper |
|-----------|---------|----------------|
| PCI-DSS | 4.0.1 | `_pci(control)` |
| HIPAA | 2024-rev (45 CFR §164.312) | `_hipaa(control)` |
| FIPS 140-3 | NIST FIPS 140-3 | `_fips(control)` |
| SOC2 | 2017-rev (Trust Services Criteria) | `_soc2(control)` — Phase 52 |
| ISO 27001 | ISO 27001:2022 (8.x clause numbering) | `_iso(control)` — Phase 52 |

**ISO 27001:2022 control assignments** (Phase 52):
- `8.24` — Use of cryptography (algorithm/key-size findings)
- `8.26` — Application security requirements (TLS/protocol transport findings)
- `8.28` — Secure coding (source-code scanner findings)

**SOC2 CC6.x control assignments** (Phase 52):
- `CC6.6` — Logical access controls (authentication, key, certificate findings)
- `CC6.7` — Transmission encryption (cipher, protocol, transport findings)

CBOM algorithm components carry a `quirk:fips140-3-status` property
(`approved` or `non-approved`) derived from the NIST quantum security level.
The `certified` tier is reserved for a future phase that will ingest CMVP
module attestation.

### Firmware CVE Catalog Staleness Cadence (Phase 142)

QUIRK's curated firmware-CVE catalog (`quirk/scanner/hw_cve.py::CVE_TABLE`, backing the
advisory-only CVE correlation described in `docs/operators-guide.md` §9.5) is gated by its
own `STALENESS_THRESHOLD_DAYS = 30` — deliberately shorter than QRAMM's 90-day cadence
(`quirk/qramm/model_meta.py`) and the compliance-mapping module's 365-day cadence
(`quirk/compliance/__init__.py`), because CVE data churns far faster than governance
frameworks or CSNP model revisions do.

**CI enforcement.** `.github/workflows/python-staleness.yml`'s single "Run staleness gates"
step includes `tests/test_cve_staleness.py` as its third assertion, alongside the existing
QRAMM and compliance staleness tests — no new job or CI step was added, just one more test
file in the existing pytest invocation. The workflow runs on every PR, every push to `main`,
and a weekly Monday 09:00 UTC cron, so a stale CVE catalog cannot silently ship.

**Bump procedure** (matches CLAUDE.md's Staleness Review Cadence exactly):

1. Re-verify each `CVE_TABLE` entry against its NVD source (`source_url` on the entry).
2. Bump `last_verified` in `CVE_TABLE_META` to today's ISO date.
3. Commit with message `chore: re-verify CVE catalog (YYYY-MM-DD)`.
4. Confirm `quirk cve status` prints `FRESH` and `pytest tests/test_cve_staleness.py -q`
   passes.

Operators can check current freshness at any time with `quirk cve status` (§9.5 of
`docs/operators-guide.md`) — no network access required, since the catalog is entirely local.

### OT/ICS Recurring-Scan Cadence Floor (v5.13+ — Phase 156)

Phase 156 adds a safety floor on top of the `enable_modbus`/`enable_bacnet` opt-in flags
(Connectors Block, above): a **recurring** (scheduled) run may only probe Modbus/BACnet when
both `connectors.enable_recurring_otics: true` is set AND the schedule's own cron expression
fires no more often than once every 168 hours (7 days).

**This is a floor, not a config key.** The 168-hour value is a named constant,
`OTICS_MIN_INTERVAL_HOURS`, in `quirk/otics_cadence.py` — there is deliberately no
`connectors.*` key, no environment variable, and no CLI flag that can lower it. Raising it
would require an intentional code change, not an operator override.

**How the floor is evaluated.** The floor is checked against the schedule's cron expression's
*minimum* firing gap, not its average. `min_gap_hours()` samples 10 consecutive firings (9
gaps) and takes the smallest one. This matters for irregular expressions: `0 0 * * 1,2` (every
Monday and Tuesday at midnight) has an average gap of roughly 84 hours across a week, but its
worst-case gap — Tuesday to the following Monday — is only 24 hours. QUIRK judges this schedule
on the 24-hour worst case, not the 84-hour average, because the worst case is what actually
determines how often a fragile OT/ICS device gets probed.

**Sub-floor schedules are not rejected — they succeed with an advisory.** Creating a schedule
with a cron interval below the floor does not fail. `POST /api/schedules` returns `201` and
`quirk schedule add` exits `0`; both surface a non-blocking advisory (see
`docs/operators-guide.md` §12) instead of a `422` rejection. This is deliberate: the scheduler
applies one shared `--scan-config` file to every schedule it dispatches, so at schedule-creation
time it has no way to know whether that shared config will ever have `enable_modbus`/
`enable_bacnet` turned on. Rejecting the schedule outright would be wrong for an operator who
has no intention of ever enabling OT/ICS scanning on it.

**Enforcement happens at dispatch time, not creation time.** When the scheduler actually
dispatches a run (`quirk scheduler run`), it strips `enable_modbus` and `enable_bacnet` from
the generated per-run config whenever the recurring-OT/ICS opt-in is off or the schedule's own
cron fires faster than the floor — while the rest of the scan proceeds normally. This is the
single, unconditional backstop: it catches every sub-floor schedule regardless of whether it was
created before this feature existed or edited directly in the database, not just schedules
created through the two write-time advisory surfaces. See `docs/operators-guide.md` §12 for
what an operator sees when this happens and where to find the suppression log line.


---

# Operator's Guide

*Running scans in anger: per-scanner reference, troubleshooting, sensors, hardware.*

*(Audience: enterprise administrators deploying and operating QU.I.R.K. on customer
estates. This is the single canonical entry point — read top-to-bottom for a deployment
walkthrough or jump to the section you need. Each section is short by design and links
to a deeper doc where one exists.)*

**Prerequisites:**
- Python 3.11+
- macOS / Linux host with outbound network reach to scan targets
- (Optional) Docker for the chaos lab smoke test

---

### 1. Install

QU.I.R.K. installs from PyPI. Use `pip install quirk` for the core scanner (TLS, SSH,
JWT, Discovery, Fingerprint), or `pip install quirk-scanner[all]` for a one-shot install of
every optional bundle except `[identity]`. The `[identity]` extra (Kerberos, SAML,
DNSSEC) is intentionally excluded from `[all]` because impacket transitively downgrades
the `cryptography` package, breaking the TLS scanner (Phase 45-01 D-07). Install
`pip install quirk-scanner[identity]` separately into its own environment if you need
identity-protocol coverage.

> See also: [`docs/installation.md`](#installation) for full install reference,
> system requirements, and OS package prerequisites.

---

### 2. Configure

QU.I.R.K. reads `./config.yaml` by default and accepts `--config <path>` to point at
another file. The config has six top-level blocks: `assessment`, `scan`, `targets`,
`connectors`, `output`, and `intelligence`. The `connectors.enable_*` flags are gated
by optional extras — enabling a flag whose extra is missing does **not** fail the run;
it emits a `missing_extra` advisory finding (Phase 45 INSTALL-02).

#### 2.0 What a stock install scans out of the box (v5.19 — Phase 184.2)

Running `quirk init` then `quirk --config config.yaml` with no further edits scans more than
"nothing" — five connectors ship **armed but inert**, two ship **actively scanning**, and
everything else ships **off with a stated reason**:

- **Five target-guarded connectors are armed but inert:** `enable_jwt`, `enable_container`,
  `enable_source`, `enable_dnssec`, `enable_saml` all ship `true`, but each short-circuits on an
  empty target list — they do nothing until you populate `jwt_targets`, `container_targets`,
  `source_targets`, `dnssec_targets`, or `saml_targets` respectively.
- **Email and broker connectors (`enable_email`, `enable_broker`) are on, and unlike the five
  above they are NOT inert.** Both scan every host in the general `targets:` block. Email has no
  dedicated target list; broker now does — **`connectors.broker_targets`** (Phase 190, TRIAGE-06)
  lets you name explicit `host`/`host:port` entries that are probed *in addition to* each broker
  family's hardcoded default ports (`broker_azure_namespaces`/`broker_sqs_regions` similarly
  *add* cloud-broker probes rather than narrowing the host sweep). See
  [`docs/configuration.md`](#configuration) § "`connectors.broker_targets` — explicit broker
  ports" for syntax and the ADDITIVE-semantics guarantee. This was already true before this
  phase for the base `enable_email`/`enable_broker` toggles: the `standard` profile (the CLI
  default) auto-enables both whenever they are unset, and an explicit `false` has always been
  respected via the `_user_set_fields` mechanism (Phase 72 D-02/WR-11).
- **Everything else ships `false`**, each with an inline reason: credentials required (AWS,
  Azure, GCP, database, S3, Blob, Kubernetes, Vault), an optional extras package required
  (Kerberos, S/MIME, AD CS, SNMP), or the connector probes live OT/ICS equipment and needs
  explicit opt-in (Modbus, BACnet).
- **The default TLS port list widened from 3 ports to 17** — `scan.ports_tls` now matches the
  same `CONSULTING_TLS_PORTS` set the CLI wizard and the dashboard's "Common TLS ports" scope
  already used. This means a stock scan now also TLS-probes ports commonly used by PostgreSQL,
  MySQL, and Vault (5432, 3306, 8200) — at the TLS layer only, independent of whether the
  credentialed `db`/`vault` connectors are enabled.
- **Plaintext-HTTP classification no longer follows `scan.ports_tls` (Phase 186, TRIAGE-176-02).**
  Previously, any plaintext-HTTP finding on a port in `scan.ports_tls` was relabelled `"HTTP on
  TLS-designated port"` — this made every scanned-but-plaintext port look like a TLS
  misconfiguration. Findings are now relabelled only for the well-known TLS port set (443, 8443,
  9443, 10443, 4433, 5001) or ports you explicitly list in the new `scan.tls_designated_ports`
  option. If you relied on the old behavior to flag plaintext HTTP on a non-standard TLS port
  (e.g. 8444), add it to `scan.tls_designated_ports` to preserve that reporting. See
  [`docs/configuration.md`](#configuration) § "TLS-designated ports override" for details.

**To narrow the out-of-the-box posture for an engagement:** edit `connectors.enable_email` /
`enable_broker` to `false` if you don't want those probed, and edit `scan.ports_tls` directly to
shrink the port list. See [`docs/configuration.md`](#configuration) § "Connectors Block" for
the full 25-key disposition table (which flag means what, and why it ships the value it does) and
§ "Default TLS port list" for the complete 17-port list.

#### 2.1 Generate a starter config — `quirk init`

Run `quirk init` to scaffold a starter `config.yaml` in the current directory. The
command copies `quirk/config_template.yaml` and is the recommended starting point for
new deployments. Edit the generated file to set assessment metadata, target lists, and
connector enable flags before your first scan.

```bash
quirk init                  # writes ./config.yaml
quirk --config config.yaml  # use the generated config
```

#### 2.2 Optional extras matrix

| Extra | Adds | Typical use |
|-------|------|-------------|
| `quirk-scanner[dashboard]` | FastAPI server + Playwright PDF rendering | Local web dashboard, PDF reports |
| `quirk-scanner[identity]` | impacket, dnspython, signxml | Kerberos / SAML / DNSSEC scanners (install separately — not in `[all]`) |
| `quirk-scanner[cloud]` | google-cloud-kms, hvac, kubernetes | GCP KMS, HashiCorp Vault, Kubernetes connectors |
| `quirk-scanner[db]` | psycopg, mysql-connector-python | Postgres / MySQL TLS-mode + RDS scanning |
| `quirk-scanner[motion]` | aiokafka, pika, redis, azure-servicebus, boto3 SQS | Email scanner + broker scanner (Kafka / AMQP / Redis / Service Bus / SQS) |
| `quirk-scanner[all]` | Everything above **except** `[identity]` | One-shot enterprise install |

#### 2.3 Vertical editions (v5.6+)

The dashboard can run as an industry-specific edition (currently `general` or
`healthcare`). Set `QUIRK_VERTICAL=healthcare` in the server environment, or add a
top-level `vertical: healthcare` key to the YAML file `QUIRK_CONFIG_PATH` points at.
The env var wins; unknown values fall back silently to `general`. Verify the active
edition after startup with `curl http://127.0.0.1:8512/api/config` (unauthenticated,
returns `{"vertical": "..."}`).

The healthcare edition adds a "Healthcare Posture" page, sidebar badge, and an
EHR/PACS/portal scan preset; general installs are unchanged. See
[`docs/configuration.md`](#configuration) § Vertical Editions for the full reference.

> See also: [`docs/configuration.md`](#configuration) for the full reference of every
> config block and flag, [`docs/sample-config.yaml`](sample-config.yaml) for an
> annotated example.

#### 2.4 Dashboard security tail (v5.10+ — Phase 143)

Three small operator-facing additions shipped in Phase 143:

- **Scan-date badge** — every dashboard view now shows a persistent "Last scan: {date} {time}"
  (or "No scan yet") badge in the sidebar, so you always know at a glance how current the data
  you're looking at is. See [`docs/report-interpretation.md`](report-interpretation.md) §11.
- **`security.trusted_targets` scan-consent allowlist** — an opt-in list of exact hosts/IPs and
  CIDR ranges QUIRK is authorized to scan, enforced identically at both the CLI and the
  dashboard's "New Scan" entry point. Empty/absent = allow-all (backward compatible). See
  [`docs/configuration.md`](#configuration) § `security.trusted_targets`.
- **Windows Authenticode signing (build mechanism, not yet activated)** — the
  `windows-package` release CI job now contains the wiring to Authenticode-sign the Windows
  sensor `.exe` via `signtool.exe`, gated cleanly on the presence of
  `QUIRK_SIGNING_CERT_BASE64`/`QUIRK_SIGNING_CERT_PASSWORD` repo secrets. **No real signing
  certificate exists yet** — until one is provisioned and those secrets are added, released
  Windows binaries remain unsigned (the release notes' "UNSIGNED BINARY NOTICE" is accurate and
  unchanged). The mechanism activates automatically, with no code changes, the moment a real
  certificate secret is configured.

#### 2.4.1 `GET /api/config/effective` — auth-gated, unlike `GET /api/config` (PARITY-01, Phase 192)

The dashboard's pre-existing `GET /api/config` endpoint returns the server's base config and does
not require the dashboard API token. The new `GET /api/config/effective` endpoint — added for the
New Scan page's Effective config panel (§3.1.2) — **does require the dashboard API token** when
`security.api_token` is set, because it accepts caller-supplied form parameters (targets, profile,
etc.) and returns the exact merged, redacted config those parameters would produce; treat it as an
authenticated preview endpoint, not a public config-read endpoint. Credential fields in its
response are always redacted to `•••• (set)` / `•••• (not set)` regardless of caller — there is no
authenticated mode that returns real credential values.

---

### 3. Scan

Two entry points: `quirk` (no args) launches the interactive wizard (recommended for first
use); `quirk --config config.yaml` runs non-interactively against a pre-authored
config (recommended for CI and customer engagements). Targets accept multi-line paste,
`@filepath` indirection, `--targets-file <path>`, and IPv4 CIDR ranges (Phase 47).
Outputs land in `output.directory` (default `./quirk-output/`): an HTML report, a PDF,
`executive.md`, `technical.md`, `findings-<ts>.json`, `intelligence-<ts>.json`, and
the CycloneDX CBOM as both `cbom-<ts>.json` and `cbom-<ts>.xml`.

#### 3.1 Interpreting Results

Findings carry a severity, a quantum-readiness band (`safe` / `at-risk` / `vulnerable`),
and (where the title joins `COMPLIANCE_MAP`) PCI-DSS / HIPAA / FIPS 140-3 control
references. The CBOM enumerates every cryptographic asset discovered.

> See also: [`docs/getting-started.md`](#getting-started) for a zero-to-first-scan
> walkthrough, [`docs/report-interpretation.md`](report-interpretation.md) for
> plain-English finding/score explanations and client-conversation guidance.

#### 3.1.1 Reading domain coverage in the headline score (SCORE-06, Phase 188)

As of scoring v2, the headline Quantum-Readiness Score is computed only from the domains a scan
actually assessed — an unassessed domain is excluded, never fabricated as a full 25/25 (see
[`docs/report-interpretation.md`](report-interpretation.md#36-coverage-exclude-and-rescale-and-the-not-computed-state-phase-188-score-06)
for the reader-facing explanation). Operators should know how to tell which domains were
unassessed and what to do about it:

- **Where to look.** Every report surface — CLI markdown, HTML, DOCX, the dashboard executive
  page, and `intelligence-{stamp}.json` — prints a `"N of 6 domains assessed"` disclosure next to
  the score. On the dashboard, an unassessed subscore renders as an em-dash (`—`) in place of its
  gauge rather than a `0`. A scan with zero assessed domains shows an explicit "Readiness score not
  computed" statement instead of a score.
- **What to scan to raise coverage.** The six domains are `hygiene`, `modern_tls`,
  `identity_trust`, `agility_signals`, `data_at_rest`, and `data_in_motion`. The first four are fed
  by the core TLS/certificate scan path and are assessed by nearly every scan. The two domains most
  often left unassessed are:
  - `data_at_rest` — needs the storage and vault connector scanners (§6) enabled and reachable.
  - `data_in_motion` — needs the email or broker scanners (§6.2) enabled and reachable.
  If a report consistently shows fewer than 6 of 6 domains assessed, check `connectors:` in your
  config for these scanners before treating the score as final.
- **Scores are not comparable across scoring versions.** A lower number after a scoring-version
  upgrade may simply reflect honest exclusion of previously-fabricated points, not a regression —
  do not compare trend lines across a scoring-version boundary. See `CHANGELOG.md`'s Unreleased
  entry for the full migration decision record.
- **Scoring v3 lowers scores substantially, by design.** Expect a large drop on estates carrying
  open CRITICAL/HIGH findings, and a cap at the top of GOOD on any estate with no observed hybrid
  post-quantum key exchange. Two changes drive it: consequence is now **absolute** rather than
  proportional (a high count of CRITICAL/HIGH findings sets a ceiling irrespective of estate size),
  and "no PQC, no 100" is enforced on a quantum-readiness product. On the project's 31-host
  reference estate the score moved 87 → 18. Whenever a ceiling binds, the score carries a reason
  naming the finding set that capped it and the uncapped figure, so a capped number is never
  mistaken for a computed one.

#### 3.1.2 Previewing what a scan will run with — the Effective config panel (PARITY-01, Phase 192)

The New Scan page in the dashboard has a collapsed "Effective config" panel above the Run Scan
button. Expanding it fetches `GET /api/config/effective` with your current form selections
(targets, profile, calibration, nmap toggle, port scope, custom ports, vertical) and previews the
**exact config that submission would run with** — not the server's base config file, and not a
static default. It re-fetches automatically as you change form fields while the panel stays open,
and never fetches at all if you leave it collapsed.

Two tabs render the same server response two ways:

- **Grouped** (default) — one card per config section (Targets, Scan, Connectors, Output,
  Assessment, Intelligence, Security), one row per field, with a provenance badge: "Overridden"
  (you changed it on the form) or "Preset: {vertical}" (a vertical preset applied it); a field with
  neither badge is a plain default.
- **Raw YAML** — the identical redacted payload rendered as YAML text, for operators who want to
  copy the exact config into a file.

**Credentials never leave the server.** Any credential-bearing field (e.g. `connectors.vault_token`,
broker credentials) renders only the literal placeholder text `•••• (set)` or `•••• (not set)` —
never a real value, in either tab, and never inside an editable input. If you ever see a real
credential value in the Raw YAML tab, that is a redaction bypass and should be reported
immediately.

A failed fetch renders an "Effective config unavailable" notice without blocking scan submission —
the panel is advisory-only and never gates the Run Scan button.

#### 3.1.3 Scan Coverage chips (OBS-02, Phase 192)

Both the scan-job page (while a scan is running/completed) and the scan-history page (per past
scan, via the row's expand chevron) show a "Scan Coverage" chip pair: `{N} ran` (green) /
`{M} skipped` (neutral outline), reading through `GET /api/scans/{scan_run_id}/coverage` (or the
`GET /api/jobs/{job_id}/coverage` convenience wrapper for an in-progress job). Both endpoints
require the dashboard API token like every other `/api/scans`/`/api/jobs` route.

Expanding "Show detail" reveals one row per scanner phase — ran rows show duration, skipped rows
show the reason and detail exactly as described in `docs/report-interpretation.md` §22's skip-reason
table, colored by severity (`missing-credentials` amber, `failed` red, the other three skip
reasons neutral, `ran` green).

**Scans from before this feature (pre-v5.21)** show an honest two-line notice — "Coverage data not
recorded" / "This scan predates per-phase coverage tracking (pre-v5.21). Re-scan to get full
coverage detail." — never a fabricated `0 ran / 0 skipped` pair. There is no backfill; the only
way to get coverage data for an older scan is to re-scan it.

#### 3.1.4 Connectors panel — enabling connectors and supplying credentials from the dashboard (PARITY-02/PARITY-03, Phase 193; PARITY-05/PARITY-06, Phase 197)

The New Scan page carries a "Connectors" panel above the Effective config panel (§3.1.2). Expanding
it (lazy-fetched on first expand only) loads `GET /api/connectors/availability` and renders all 25
connector toggles grouped into six fixed-order categories: Identity, Cloud, Database, Email &
Broker, OT/ICS, and Source & API — matching the CLI's `connectors.enable_*` surface field-for-field,
not a dashboard-only subset.

**Unavailable connectors are shown, never hidden.** A connector whose required optional extra is not
installed on the server appears as a disabled toggle with its reason and the verbatim
`pip install quirk[<extra>]` hint always visible — no hover required. This is advisory only: even if
you could somehow force the toggle on, submitting a job that would run an unavailable connector is
rejected server-side with an HTTP 422 that names the connector and the reason, including when the
request bypasses the dashboard entirely and calls the job-creation API directly. The disabled switch
is a convenience that saves you a failed submission; the actual guarantee is server-enforced.

**Credential entry.** Toggling on a connector that needs a credential (e.g. AD CS, PostgreSQL/MySQL
database scanning, SNMP community string, broker/SNMPv3 per-host auth) reveals a masked credential
input. Every credential field is:

- **masked** as you type, like a password field;
- **never saved** — the value is used only for that one scan submission, is not written to the job's
  stored config, and does not persist across page reloads;
- **empty again after submission** — you must re-enter it on every scan you submit, by design.

Cloud connectors (AWS, Azure, GCP) show an ambient-credentials note instead of a field — they use
your environment's or instance's own credential chain (IAM role, service principal, application
default credentials) and have no dashboard-fillable secret.

**Enabling a connector with no credential supplied is allowed, not blocked.** Submission succeeds; the
scan records a `missing-credentials` skip for that phase in its Scan Coverage disclosure (see
`docs/report-interpretation.md` §22) rather than the job being rejected. The panel shows a
non-blocking amber warning at submit time if you enable a connector and leave its credential blank,
so the outcome isn't a surprise, but it never stops you from submitting.

Also new this phase: **`GET /api/connectors/availability`**, the auth-gated endpoint the panel reads.
It requires the same dashboard bearer token as every other `/api/*` route, probes every connector's
real availability fresh on every call (no caching — a `pip install` you just ran is reflected on your
very next fetch), and returns each connector's `available` flag, `reason` (when unavailable), and
`install_hint` (the exact `pip install quirk[...]` string). `docs/api-reference.md` does not exist yet
as a project convention (per CLAUDE.md's documentation checklist); this section is the interim
documentation for that endpoint until that reference file is created.

**Setting connector targets and endpoints (PARITY-05/PARITY-06, Phase 197).** Toggling on a
connector that has target-list, endpoint, or identifier fields reveals them beneath its toggle —
in the same place a credential input would render, stacked below it when both are present. These
fields render **only when the connector is both available and ON** — the same visibility gate as
credential fields — so an OFF connector shows none of them.

- **List fields** (e.g. "JWT Targets", "Container Targets", "GKE Clusters") are one free-text
  `<textarea>`, comma- or newline-separated, matching the main scan-level Targets field's own
  convention. Clearing a list field back to blank **deletes the key from the submission** rather
  than sending an empty list — this delta-only semantics means an untouched form produces the
  exact same submit body and Effective Config query string as before this phase (D-08).
- **GKE/AKS clusters** use a compact pairlist syntax instead of plain hostnames:
  `name@location` for GKE (e.g. `prod-cluster-1@us-east1`), `name@resource-group` for AKS (e.g.
  `prod-aks@rg-prod`). An entry missing the `@` separator is dropped from the submitted list and
  surfaced with a visible amber "N entries are missing the required name@location format" count
  — it is never silently discarded and never silently submitted half-formed.
- **The amber "enabled with no targets configured" hint** appears when a connector with one or
  more list-typed fields is ON and every one of those fields is blank. It reads: "{Connector
  label} is enabled but has no targets configured. The scan will run but this connector's list is
  empty, so it has nothing to check. Add targets above, or submit anyway." This is the dashboard
  surfacing of the same "target-guarded, inert until populated" behavior documented in the
  `requires-targets` reason tag above (e.g. `enable_jwt` shipping `true` but doing nothing until
  `jwt_targets` is set) — toggling one of these connectors on alone is no longer silently a no-op,
  because the panel now tells you it needs targets.
- **`k8s_kubeconfig` is a server-side path, not a file upload.** Its helper text reads: "Path to a
  kubeconfig file readable by the QU.I.R.K. server process. Not a file upload — enter the
  server-side path." Whatever you type must already exist and be readable on the machine running
  `quirk serve`, not your own workstation.
- **`vault_tls_verify`** renders as a pre-checked Switch (the config default is `true`) — you must
  explicitly uncheck it to disable TLS verification for the Vault connector; the field is never
  silently defaulted off.
- **Identifier fields are never masked.** `adcs_user`, `pg_scanner_user`, and `mysql_scanner_user`
  are plain, visible text inputs — unlike the masked credential fields above, these are
  identifiers that land in the job's stored `config.yaml` in cleartext by design (D-04); only the
  matching password/token fields are masked and non-persisted.
- **A field you have touched shows a small teal "Set" badge** next to its label — the same visual
  language as the connector-level "Set" badge, now also available per-field.
- **Rejected values return a 422 naming the field**, at both submit and the Effective Config
  preview — e.g. an out-of-range timeout or a malformed cluster entry. The banner is prefixed
  "Scan rejected: " followed by the backend's message, such as
  `Unknown connector key(s): {key}` for a typo'd field name, or `{key!r} is not a recognized
  connector overlay field (must be a known enable_* toggle or one of the supported connector
  detail fields)` for a real-but-out-of-phase-scope field like a secret. Submit and preview are
  guaranteed to agree on every accept/reject decision (PARITY-06).

See [`docs/configuration.md`](#connector-detail-fields-settable-from-the-dashboard-parity-0506-phase-197)
for the full 37-field reference (types, defaults, bounds, gating flags).

#### 3.1.5 Advanced scan fields — TLS ports, enumeration depth, timeouts, retry, concurrency, data classification (PARITY-04, Phase 194; PARITY-08/09, Phase 198)

The New Scan page carries an "Advanced" section directly below the Connectors panel (§3.1.4) and
above the Effective config preview (§3.1.2). **It is collapsed by default** — clicking the
"Advanced" label with the chevron expands it; nothing inside is fetched or evaluated until you
open it. It remains a single panel — Phase 198 added two new field groups inside it, not a second
panel.

Inside, the panel exposes 27 controls, in these groups:

- **TLS Ports** — a free-text comma-separated port/range list (e.g. `443,8443,9000-9010`) that
  overrides `scan.ports_tls` for this scan only.
- **TLS Enumeration Mode** — a Fast/Deep dropdown. There is no "Off" option; see
  [`docs/configuration.md`](#advanced-scan-fields-reference-parity-04-phase-194-parity-0809-phase-198)
  for why (D-19).
- **Send SNI during TLS probes** — a switch controlling `scan.include_sni`.
- **Timeouts & Retry** — the original default/TLS/SSH timeout fields (seconds) and retry count,
  plus two new fields: **Backoff base (seconds)** and **Backoff max (seconds)**, both accepting
  decimals. Submitting a base greater than max returns a 422 naming both fields.
- **Per-Scanner Timeouts** — a new compact grid of 11 short-labeled numeric fields (Fingerprint,
  JWT, Container, Source, DNSSEC, SAML, Kerberos, Vault, DB Connect, Broker, Email), each
  overriding that scanner's individual timeout. Accepted range is 1-600 seconds — wider than the
  three original timeout fields' 1-300 bound; see D-11 in the configuration reference for why the
  bounds intentionally differ.
- **Concurrency** — a new group of 5 worker-pool-size fields (Scan, Fingerprint, TLS, SSH, Motion
  concurrency), 1-500 each. Motion concurrency is the shared worker pool for email and broker
  connector scanning.
- **TLS-Designated Ports** — a second port/range field beside TLS Ports, overriding
  `scan.tls_designated_ports`: ports listed here are treated as TLS even if plaintext is detected,
  overriding the plaintext-on-TLS-port classifier. Same comma-separated format and inline format
  validation as TLS Ports.
- **Data Classification** — a Public/Internal/Confidential/Regulated dropdown controlling
  `assessment.data_classification`; see D-21 in the configuration reference for why there is no
  fifth option.

No control exists for `scan.openapi_spec_path` or either hardware retention-days field — these are
recorded, intentional gaps (D-04); see the configuration reference for why.

**Every control here is advisory client-side only; the server's 422 response is authoritative.**
The Input field for TLS Ports shows a red hint if you type something that doesn't look like a
port/range list, but that hint is a courtesy — the actual validation happens server-side when you
submit, and a rejected value returns a full-width 422 banner naming the offending field.

**Every edit updates the Effective Config preview live**, badged `user` to distinguish it from a
value coming from the active vertical preset or scan profile — the same provenance-badge mechanism
`docs/report-interpretation.md` §22 documents for the Connectors panel. See "Dashboard form vs.
presets precedence" in [`docs/configuration.md`](#dashboard-form-vs-presets-precedence)
for the full mechanism (delta-only writes, `_user_set_fields`, overlay-merged-last) — this panel
follows it identically to the Connectors panel, it does not have a separate precedence rule of its
own.

#### 3.1.6 Exposure Map tab — attack-path visualization (MAP-02, Phase 195)

The dashboard sidebar carries a new "Exposure Map" nav entry, opening a read-only
`/exposure-map` tab (Tier A — no write actions, auth-gated like every other dashboard tab). It
renders a node/edge graph of verified-only relationships between scanned endpoints, sourced
exclusively from `GET /api/exposure-map`, with no client-side data fabrication — see
`docs/report-interpretation.md` §23 for the full client-facing explanation of what the graph shows
and how to read an edge's evidence tooltip.

Two things operators should know that are specific to how this tab behaves, not what it means to a
client:

- **A zero-edge graph is an honest, expected result, not a failure.** Most scans will not populate
  either edge type (shared SPKI fingerprints or confirmed hardware crypto-bridge chains) unless the
  target environment actually has that condition. Seeing the "No path data available" empty state
  after a scan completes normally does not indicate anything went wrong with the scan or the tab.
- **The tab is read-only in this release.** There is no "declare a reachability path" or
  "mark crown jewel" action anywhere in the UI — that declaration workflow was evaluated in a
  dedicated spike (`.planning/phases/195-quantum-exposure-map/195-SPIKE-DECISION.md`) and deferred
  to a future release given the added persistence/CRUD/UX cost. Everything currently on this tab is
  derived read-time from existing scan data; there is nothing to configure or maintain for it.

#### 3.1.7 Report deliverable downloads (DELIV-01/DELIV-02, Phase 209, v5.24)

The Executive page's header row carries a five-format download button group — HTML, PDF, DOCX,
CBOM (JSON), CBOM (XML) — beside the pre-existing Export PDF button. It is backed by two new,
auth-gated endpoints under `quirk/dashboard/api/routes/reports.py`. See
`docs/report-interpretation.md` §26 for what each format contains and the difference between these
downloads and the Export PDF button; this section documents the endpoints themselves.

**`GET /api/reports/latest/manifest`** — returns every format's availability, never empty and
never 404/500:

```json
{
  "scan_time": "2026-09-14T04:22:13.439767+00:00",
  "stamp": "20260914-041322",
  "formats": {
    "html":      {"available": true,  "reason": null},
    "pdf":       {"available": true,  "reason": null},
    "docx":      {"available": false, "reason": "DOCX requires the optional extra: pip install quirk[docx]"},
    "cbom-json": {"available": true,  "reason": null},
    "cbom-xml":  {"available": true,  "reason": null}
  }
}
```

An unreadable config or a missing output directory degrades to every format reporting `available:
false` with reason `"No scan has run yet."` rather than raising an error — the same
fail-to-safe-empty-value discipline `docs/report-interpretation.md` §23 documents for the Exposure
Map's crown-jewel loader.

**`GET /api/reports/latest/{format}`** — downloads one artifact. `{format}` accepts exactly five
values: `html`, `pdf`, `docx`, `cbom-json`, `cbom-xml`, returning `text/html`,
`application/pdf`, the DOCX OOXML media type, and `application/json`/`application/xml`
respectively. **Any other value returns 404, by design** — the route never accepts a filename or
path fragment from the client; it resolves the on-disk filename itself from a fixed
format-to-template map, so an unlisted or malformed value is a routing miss, not a validation
error to work around. There is no way to request an older scan's artifacts through this route (see
below).

**Auth is required, same as every other dashboard API route** (§2.4) — a Bearer token or
`X-API-Key` header. A plain browser navigation to the URL, or a naive `curl` without the header,
returns `401` — and a saved `401` response body looks exactly like a corrupt download. The correct
invocation:

```bash
curl -H "Authorization: Bearer $QUIRK_API_TOKEN" \
  -o report.pdf \
  "http://localhost:8000/api/reports/latest/pdf"
```

**Latest-scan-only, and why.** Both endpoints always resolve to the most recently rendered artifact
group — there is no scan-id or filename parameter, and none can be safely added without revisiting
this design. The report artifacts are stamped with the moment `write_reports()` rendered them, not
with `scan_run_id` (the scan's own start time); on a long scan those two instants can differ by the
scan's full duration, and **nothing on disk associates a `scan_run_id` with the artifact stamp it
produced**. Until that association exists, serving "the report for scan X" is not something this
API can do honestly, and a future scan-id-scoped route would need it built first, not just added to
this router's path.

#### 3.2 Active REST fuzzing (`--fuzz`) — interactive-only by design

`--fuzz` enables active REST crypto-posture probing against discovered OpenAPI
endpoints (see [`docs/configuration.md`](#rest-fuzzing-active-crypto-posture-probes)
for the full flag reference and guardrail table). Two things every operator scheduling
QU.I.R.K. runs needs to know before wiring `--fuzz` into automation:

- **`--fuzz` requires an interactive terminal.** If stdin is not a TTY — piped input, a
  CI/CD job, a cron job, any headless invocation — the scanner refuses to run fuzzing at
  all. It prints coded error `FUZZ-001` and **exits non-zero (exit 2)**, and it does this
  before any scan work begins. This is deliberate, not a bug: an unattended job must
  never be able to authorize active probing of a client's live API on its own. If you see
  a cron or CI run fail with `FUZZ-001`, that is the gate working as intended — drop
  `--fuzz` from unattended/scheduled invocations, or run it manually from an interactive
  session instead.
- **`--fuzz` is never silently skipped.** Earlier behaviour could let a non-interactive
  `--fuzz` invocation complete normally with fuzzing quietly disabled and no indication
  in the output. That is no longer possible — either fuzzing runs (interactive session,
  confirmed) or the scan refuses to start (non-interactive, `FUZZ-001`, exit 2). There is
  no third, quiet outcome.
- **`--fuzz-budget` is bounded, and out-of-range values are rejected, not clamped.** The
  default is 50 requests; values above the hard ceiling documented in
  [`docs/configuration.md`](#rest-fuzzing-active-crypto-posture-probes)
  are rejected up front with coded error `FUZZ-002` and exit 2 — the scan does not
  silently reduce an over-budget request down to the ceiling and proceed.

See [`docs/error-codes.md`](error-codes.md) for the full `FUZZ` error-domain cause/fix
text for `FUZZ-001` and `FUZZ-002`.

#### 3.3 Report Branding, Templates, and Profiles (Phase 200, v5.23 — RPT-01..RPT-04)

Reports can carry a client's own branding (cover logo, client/engagement identity text), an
operator-authored template override directory, and a named, reusable "report profile" that
bundles both. See [`docs/configuration.md`](#report-block-phase-200-v523--rpt-01rpt-02rpt-03rpt-04)
for the full `report:` config key reference.

##### Three similarly-named flags — do not confuse them

QU.I.R.K. has three separate `--*profile` concepts. They are unrelated to each other and each
controls a different axis of behavior:

| Flag / config key | Controls | Values |
|---|---|---|
| `--profile` (CLI) / preset applied by `apply_profile`| **Scan** behavior — timeouts and TLS enumeration depth | `quick` / `standard` / `deep` |
| `--score-profile` (CLI) / `intelligence.profile` | **Scoring calibration** — how heavily agility/identity findings are weighted | `lenient` / `balanced` / `strict` |
| `--report-profile` (CLI) / `report.profile` | **Report branding/templates** — which saved branding+template bundle to apply to this run's deliverables | any saved profile name |

None of the three overlap: `--profile deep` does not affect scoring or branding; `--score-profile
strict` does not affect timeouts or branding; `--report-profile housestyle` does not affect
timeouts or scoring.

##### Saving and applying a report profile

```bash
# Save the report: block of an existing config as a named, reusable profile
quirk report profile save housestyle --config /path/to/config.yaml

# List saved profiles
quirk report profile list

# Apply a saved profile to a scan run (selects it by name; does not require --config to carry a report: block)
quirk --config config.yaml --report-profile housestyle
```

Saved profiles live at `~/.quirk/report_profiles/<name>.yaml`, redirectable via the
`QUIRK_PROFILES_DIR` environment variable (useful for CI, containerized runs, or per-client profile
directories). `quirk report profile save` overwrites an existing profile of the same name and says
so explicitly on stdout rather than failing or silently overwriting.

**Precedence — one unambiguous rule:** a value set explicitly in the engagement's own `config.yaml`
always beats the same field coming from an applied report profile. A profile only *fills in* fields
the engagement config left unset; it can never override an explicit value. Selecting *which*
profile to apply follows the same CLI-over-config precedent as `--profile`: `--report-profile` on
the command line wins over a config-declared `report.profile` for which profile loads — but the
loaded profile's *values* still lose to any explicit config field regardless of how the profile was
selected.

##### Report template overrides — the honest security posture

`report.template_dir` lets an operator override the packaged Jinja2 report templates with their
own `.j2` files (the operator's directory is searched first; the packaged template is the fallback
for anything not present there). Templates render inside a **sandboxed Jinja2 environment**
(`SandboxedEnvironment`) unconditionally — there is no config flag to disable the sandbox, and no
second, "trusted" template environment exists anywhere in the codebase.

State the division of responsibility plainly, because it is easy to misread as one guarantee when
it is really three:

- **The sandbox protects the HOST.** `SandboxedEnvironment` blocks Server-Side Template Injection
  (SSTI) payloads that try to reach Python internals (`__class__`, `__globals__`, attribute-chain
  escapes) from breaking out to the machine running QU.I.R.K. This holds even for a hostile or
  compromised override template.
- **Autoescape protects against scan-data XSS in the rendered HTML.** Scan-derived values (host
  names, finding titles, certificate subjects) are escaped by default so they cannot inject
  executable markup into the report.
- **The `| sanitize` filter is a second, narrower layer used on branding and free-text fields
  specifically.** If you write a custom override template and remove `| sanitize` from a field that
  had it, you are **weakening scanner-data XSS hardening for your own report** — the sandbox still
  protects the host, but the rendered HTML you hand to a client can carry unsanitized scan-derived
  text. This is a real, honest tradeoff, not a theoretical one: do not strip `| sanitize` from an
  override template unless you understand and accept that consequence for that specific field.

#### 3.4 Score-Lift Badges and the Projected Score on the Remediation Roadmap (Phase 201, LIFT-01..LIFT-05)

Every roadmap item that can be quantified now carries a `(+N pts)` badge — the readiness score
this scan would have if that one item were resolved, computed by a real second call into the
scoring engine over a copy of the scan's evidence, never a fixed points table. Items whose
resolution changes no scoring input (process/governance work, and coverage/lifecycle items) show
no badge at all — a blank means "not measurable," never `0 pts`. A separate "Projected score if
all items resolved: {N}" figure is one additional independent rescore with everything resolved at
once — it is usually smaller than summing the individual badges, because the score's four
subscores are each capped and can only give up so much headroom. Neither number ever changes the
readiness score you see today; every surface that shows the projected number also shows, verbatim:
"Advisory — this projection is a simulation and does not affect the readiness score." See
`docs/report-interpretation.md` §7.1 for the full explanation, the exact list of unmodelable item
kinds, and worked examples across all report surfaces.

**Where it appears:** the CLI roadmap markdown and scorecard, the HTML/PDF and DOCX reports, and
the dashboard roadmap page — a per-item badge in the node detail panel, and a "Projected Score"
card directly above the Remediation Burndown card. The dashboard omits the card entirely (not a
placeholder) when the scan is unassessed or the projection could not be computed.

**The console "Migration Waves" table's second column changed meaning in the same phase
(BACK-51 / LIFT-04):** it now counts roadmap *items* per NOW/NEXT/LATER phase — labeled "Items" —
instead of raw findings bucketed by severity. This makes the console table agree with every other
roadmap surface, which already used the same categorization. A report generated before Phase 201
may show different NOW/NEXT/LATER counts than one generated after it for the same findings; that
is the intended effect of unifying the two previously-independent categorization systems into one.

---

### 4. Validation / Smoke Test

Before pointing QU.I.R.K. at a production estate, run it against the bundled chaos
lab to confirm the install is healthy and findings render correctly. The lab spins up
intentionally weak TLS, SSH, JWT, container, broker, and email targets via Docker
Compose profiles, with an oracle of expected findings per profile.

> See also: [`docs/chaos-lab.md`](chaos-lab.md).

---

### 5. Troubleshooting

#### 5.0 Looking up an error code

Scanner advisories and failures carry a bracketed code such as `[QRK-INSTALL-001]` or
`[QRK-CONFIG-001]`. To see the full catalogue — every code, its meaning, and its
remediation — without leaving the terminal:

```bash
quirk errors                 # human-readable table
quirk errors --dump-md       # the Markdown source of docs/error-codes.md
```

`docs/error-codes.md` is generated from this command, and a CI gate asserts the committed
file byte-matches the live output — so the catalogue and the code cannot drift apart. If
you are reading a code that is not in the file, regenerate rather than hand-editing:

```bash
quirk errors --dump-md > docs/error-codes.md
```

#### 5.1 Scan failures

- **Permission denied on a target** — confirm the QU.I.R.K. host can reach the port;
  check firewall and security-group rules. TCP-connect failures surface as a
  `connection refused` / `timeout` finding rather than crashing the scan.
- **Timeouts** — adjust the relevant `scan.timeouts.<scanner>_seconds` knob
  (`tls_seconds`, `ssh_seconds`, `dnssec_seconds`, etc.). See
  [`docs/timeout-retry-audit.md`](timeout-retry-audit.md) for per-scanner defaults.
- **`missing_extra` advisory finding** — install the named extra
  (e.g. `pip install quirk-scanner[identity]` for Kerberos). Phase 45 INSTALL-02 surfaces
  these instead of silently skipping the scanner. As of v5.17 (Phase 173), this signal — a
  `[QRK-INSTALL-001]` stderr advisory plus a `scan_error_category=missing_extra` finding — is
  emitted consistently across scanner families: the broker connector now checks all three of its
  optional dependencies (`sslyze`, `kafka-python`, `redis`), not just `sslyze`, and the smime/adcs
  connectors emit the signal for the first time (both previously failed silently with only a bare
  log line). If you enable a connector and see this advisory, install the named extra
  (`pip install quirk-scanner[motion]` for broker/email, `quirk-scanner[adcs]` for smime/adcs)
  or leave the connector disabled.
- **`[QRK-CONFIG-001]` on startup — non-numeric `scan.ports_tls` / `scan.tls_designated_ports`
  entry** — as of v5.20 (Phase 189, TRIAGE-04), a port-list value that isn't a bare integer or a
  quoted digit-string (e.g. a typo like `"84a4"`) is now rejected loudly at config-load time
  instead of being silently ignored. Fix the offending entry named in the error message. A quoted
  digit-string such as `"8444"` is valid and behaves identically to a bare `8444` — only truly
  non-numeric values raise this error. If you have an older config with a quoted port value that
  never triggered this error before upgrading, re-check that scan's report: prior to Phase 189
  such a value silently never matched the TLS-designation override, so its effective scope may
  have been narrower than intended. See [`docs/configuration.md`](#configuration) §
  "Port-list value coercion and `QRK-CONFIG-001`" for details.
- **A skipped scan phase leaves no `run_stats.timings_sec` key** — as of v5.17 (Phase 173), a
  phase that did not actually run (disabled connector, no targets, missing extra) omits its key
  from `run_stats.timings_sec` entirely, rather than recording a phantom near-zero duration. A
  phase that ran and legitimately found nothing still writes its key (with a real, possibly small,
  elapsed time) — the absence of a key means "did not run," not "ran fast." No consumer depends on
  a fixed key set; this is safe to rely on when auditing which phases actually executed.
- **TLS handshake errors against modern endpoints** — confirm the installed
  `cryptography` package version. Do not let `quirk-scanner[identity]`'s impacket dependency
  downgrade it (Phase 45-01 D-07); install `[identity]` in a separate environment if
  necessary.

#### 5.2 Database / output

- **`db_path` permission error** — confirm the directory is writable. Default is
  `./quirk.db` under the working directory.
- **Migrations** — schema migrations are additive only (`_ensure_*_columns` helpers
  in `quirk/db.py`); deleting `quirk.db` is safe but loses scan history.
- **CBOM file generation** — every run emits `cbom-<ts>.json` and `cbom-<ts>.xml`;
  both must validate against CycloneDX 1.6.
- **PDF render failure** — install `quirk-scanner[dashboard]` (which pulls Playwright) and run
  `playwright install chromium` once on the host.

#### 5.3 Dashboard

- **Vite build errors** — only relevant when rebuilding the React SPA from source; the
  published wheel ships a built bundle at `quirk/dashboard/static/`.
- **Stale `.vite/`** — delete `.vite/` under `src/dashboard/` and rebuild.
- **Port conflict on 8512** — pass `quirk serve --port <other>`. The dashboard binds
  loopback only by default.
- **CORS rejection in the browser (v5.11+)** — should no longer happen out of the box:
  `quirk serve` sets `QUIRK_DASHBOARD_PORT` to the actual bound port, and the default
  CORS allowlist (`quirk/config.py::get_cors_origins`) matches it automatically
  (Phase 147, DRAIN-03 / WR-02). If you still see a CORS error, you're likely accessing
  the dashboard through a different hostname/port than it bound to (e.g. a reverse
  proxy) — set `QUIRK_CORS_ORIGINS` explicitly. See
  [Configuration → CORS Allowlist](#cors-allowlist-v511--phase-147-drain-03--wr-02).
- **Data not loading** — confirm a recent scan has populated `quirk.db`; the dashboard
  reads SQLite directly.
- **`quirk serve` starts but every API call renders an empty state — check for multiple
  candidate DBs.** `_default_db_path()` (`quirk/dashboard/api/deps.py`) checks, in order,
  `QUIRK_DB_PATH`, then whether more than one of `./quirk.db`, `./output/quirk.db`,
  `./quirk-output/quirk.db` exists. If **more than one** of those three paths is present, it
  raises `ValueError: Multiple QU.I.R.K. DBs found` — and because this check runs inside a
  FastAPI `Depends()`, it fires on *every request*, not at startup. The server itself starts
  cleanly with no error printed to the console; the dashboard just silently renders empty
  states over the failed API calls, which reads exactly like "no scan data yet." Fix: set
  `QUIRK_DB_PATH=<path-to-the-db-you-want>` before running `quirk serve` to disambiguate
  explicitly. Also worth checking: a stray 0-byte `quirk.db` left over from an earlier run in
  the working directory counts toward this conflict even though it holds no data — delete it
  if it isn't the DB you intend to serve.
- **Appearance note (Phase 165, A11Y-03)** — primary and accent buttons, and the
  severity/quantum-safety badges described in
  [Report Interpretation](report-interpretation.md#4-severity-tiers), now render dark text
  instead of white. Muted label text is also very slightly lighter. All underlying colours
  (teal buttons, orange/red/green badges) are numerically unchanged — only the foreground text
  moved, to clear WCAG 2.1 AA contrast (teal buttons: 2.81:1 → 6.27:1). This is a contrast
  fix, not a redesign.
- **Accessibility gate (Phase 165, A11Y-01/A11Y-04)** — `npm run a11y:check` (and its
  `:empty`/`:loading` variants) in `src/dashboard/` now enforce a per-route, per-rule *count
  budget* rather than a selector snapshot: each baselined `(route, rule)` pair records a
  maximum node count, impact level, WCAG success criterion, and a written justification.
  The gate fails if a count goes **up**
  (new debt) — and, deliberately, also if a count goes **down** without the baseline being
  regenerated (`npm run a11y:baseline`), so a real fix always tightens the ledger instead of
  leaving a now-stale, looser number in place.
- **Regenerating a11y baselines — the sanctioned procedure (Phase 185, D-03).** Baselines
  **must** be generated on a Linux CI runner, not a contributor's local machine. Font metrics,
  overflow behavior, and other render-time properties differ enough between macOS and Linux that
  a rule which never fires locally can fire on Linux, and vice versa — this is exactly what
  happened when 33 baselines were batch-generated on macOS on 2026-08-27 and 31 of them were
  never checked against the Linux runner that actually enforces the gate. To regenerate:
  1. Dispatch the permanent `a11y-regenerate-baselines` job in
     `.github/workflows/dashboard-quality.yml` (`workflow_dispatch`, runs on `ubuntu-latest`):
     `gh workflow run dashboard-quality.yml --ref <branch>`. `workflow_dispatch` works from any
     branch that contains the workflow file — you do not need to be on `main`.
  2. Once the run completes, download its artifact:
     `gh run download <run-id> --name a11y-baselines-<run-id>`. The artifact contains both the
     regenerated `baseline-*.json` files and the regenerated `ACCEPTED-VIOLATIONS.md` — **both
     must be committed together**, since `ACCEPTED-VIOLATIONS.md` is a rendering of the baseline
     JSON and the two will silently disagree if only one is updated.
  3. If you are onboarding a brand-new route, its `routes.json` entry and its baseline files
     **must land in the same commit**. A `routes.json` entry with no matching baseline file is a
     hard, by-design CI error (`missing baseline file`), not a soft warning — this is intentional,
     so a route can never silently ship unswept.
- **The sanctioned response to a gate failure (Phase 185, D-10).** When `Axe + Console Gate`
  goes red on a PR: (1) dispatch `a11y-regenerate-baselines` per the procedure above; (2) download
  the artifact; (3) review **every** changed `(route, rule)` count — an increase requires a
  written per-entry triage naming the rule, the route, and why it is accepted (justified in the
  ledger) or being fixed; a decrease may be committed freely; (4) commit the reviewed baselines
  and ledger together. **Hand-patching a baseline count locally, without going through this
  procedure, is NOT sanctioned.** This is not a stylistic preference — it is how Phase 177 fixed
  three `data-at-rest` counts by hand after a first-ever remote CI run surfaced them, without
  regenerating on Linux CI or auditing the other 31 baselines, and that gap went unnoticed for
  9 days before a later phase (185) had to rediscover and close it. Hand-patching a count quiets
  the gate without ever establishing whether the change was a genuine environment artifact or a
  real regression slipping through — treat any future local count edit the same way: as a defect
  to be replaced with the CI-regeneration procedure above, not a shortcut to repeat.
- **CI pins Chrome; local runs deliberately do not (Phase 185, D-06/D-07/D-08/D-09).** All three
  `browser-actions/setup-chrome` usages in `dashboard-quality.yml` (`a11y`,
  `a11y-regenerate-baselines`, `e2e-smoke`) pin a concrete version
  (`chrome-version: '152.0.7977.82'` as of this writing), guarded by
  `src/dashboard/tests/a11y/pinned-deps.test.ts` so the three occurrences can never drift apart or
  regress to a floating channel name (`stable`/`beta`/`dev`/`latest`). Local `a11y:check` runs
  intentionally do **not** pin — `run-a11y.mjs` launches Puppeteer's `channel: 'chrome'`, whatever
  is locally installed — so a local a11y result is **diagnostic-only** and never decides a
  committed baseline; only the pinned, CI-run result does.
  - **Why the exact pin needs no scheduled staleness check.** A `chrome-version: stable` pin
    resolves against Google's rolling "current" distribution
    (`dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb`), which genuinely drops
    old builds as new ones ship. The exact pin above instead resolves against the **Chrome for
    Testing** archive (`storage.googleapis.com/chrome-for-testing-public/152.0.7977.82/...`),
    which is a *versioned, retained* archive — old builds do not disappear. An exact CfT pin is
    therefore **more durable** than `stable`, not less, and does not need a `last_verified`-style
    staleness gate; one was explicitly considered for this pin and declined as unnecessary scope.
  - **Recovery if the pinned build ever becomes unfetchable.** `pinned-deps.test.ts` can only
    detect "never floats to `stable`" and "all three occurrences agree" — it cannot detect an
    exact pin that CfT has stopped serving. If `setup-chrome` fails to acquire the pinned build in
    CI: (1) dispatch the regeneration job with `chrome-version: stable` temporarily; (2) read the
    resolved version from that run's "Record resolved Chrome version" step; (3) re-pin all three
    occurrences in `dashboard-quality.yml` to the newly resolved version; (4) regenerate baselines
    under the new pin per the D-03 procedure above; (5) triage any count changes per the D-10
    increase-triage rule.

#### 5.3.1 UAT corpus integrity gate

`tests/test_uat_zero_undispositioned_gate.py` fails the build the moment any case in
`docs/UAT-SERIES.md` (the 666-case UAT gating document) has an all-unchecked `**Result:**`
line — it rides the existing `Linux Full Suite` CI job rather than a pre-commit hook, so it
cannot be bypassed with `--no-verify`. If you add a new UAT case, give it a real disposition
(PASS/FAIL, or a checked SKIP with a `DEFERRED — covered by <test-node>` or `GAP — no substitute
coverage` annotation) before committing. Full rationale and worked fix instructions are in
`CLAUDE.md`'s "UAT Corpus Integrity Gate (UATREC-04)" section and in the gate test's own module
docstring.

#### 5.4 Connector gotchas

For per-connector authentication and IAM-permission issues, see the dedicated connector
docs: [`docs/connectors/aws.md`](connectors/aws.md),
[`docs/connectors/azure.md`](connectors/azure.md),
[`docs/connectors/docker.md`](connectors/docker.md),
[`docs/connectors/git.md`](connectors/git.md).

---

### 6. Per-Scanner Reference

Each scanner emits findings into the same `crypto_endpoints` SQLite table; runtime
ordering is governed by `run_scan.py` phase timers. Cloud and infra connectors with
dedicated docs link out; protocol scanners that lack a connector doc get a short
inline subsection below the table.

#### 6.1 Compact reference table

| Scanner | Scans | Config flag(s) | Optional deps | Sample finding |
|---------|-------|----------------|---------------|----------------|
| Discovery (nmap) | TCP port discovery before fingerprinting | wizard prompt, `--targets-file`, `cidrs:` | `nmap` binary | (advisory) "Scanner skipped — optional extra not installed" |
| TLS | TLS handshake, cert chain, ciphers, key sizes | `scan.ports_tls`, `scan.tls_designated_ports`, `scan.include_sni`, `timeouts.tls_seconds` | `sslyze` (core) | "TLS certificate expired" |
| SSH | SSH banner + KEX/host-key/cipher audit | `timeouts.ssh_seconds` | `ssh-audit` | "SSH quantum planning advisory" |
| JWT/API | JWT signing-alg discovery | `connectors.enable_jwt`, `jwt_targets` | (none) | (algorithm-classification findings) |
| Container | Crypto libraries in Docker images via Syft SBOM | `connectors.enable_container`, `container_targets` | `syft` binary | "Container image uses quantum-vulnerable crypto library" |
| Source code | semgrep on git repos | `connectors.enable_source`, `source_targets` | `semgrep` | (semgrep-rule findings) |
| DNSSEC | DNSKEY / DS / RRSIG | `connectors.enable_dnssec`, `dnssec_targets`, `timeouts.dnssec_seconds` | `quirk-scanner[identity]` | (algorithm + chain findings) |
| Kerberos | KDC enctype enumeration (port 88) | `connectors.enable_kerberos`, `kerberos_targets`, `timeouts.kerberos_seconds` | `quirk-scanner[identity]` | (etype findings) |
| SAML | SAML IdP signing/digest algorithms | `connectors.enable_saml`, `saml_targets`, `timeouts.saml_seconds` | `quirk-scanner[identity]` | (signature-alg findings) |
| Email | 7-port email TLS probe (SMTP/IMAP/POP3 ± STARTTLS) | `timeouts.email_seconds` | `quirk-scanner[motion]` | "STARTTLS downgrade risk on SMTP" |
| Broker | Kafka / AMQP / Redis / Azure Service Bus / SQS | `connectors.enable_broker`, `connectors.broker_targets`, `broker_azure_namespaces`, `broker_sqs_regions`, `timeouts.broker_seconds` | `quirk-scanner[motion]` | "Plaintext Kafka listener detected" |
| AWS | ACM certs, KMS keys, CloudFront, ELB | `connectors.enable_aws`, `aws_region`, `aws_profile` | `boto3` (core) | (KMS / cert findings) — see [`docs/connectors/aws.md`](connectors/aws.md) |
| Azure | Key Vault keys + certs, App Gateway TLS | `connectors.enable_azure`, `azure_subscription_id`, `azure_keyvault_urls` | (varies) | — see [`docs/connectors/azure.md`](connectors/azure.md) |
| GCP | KMS + GCS storage encryption | `connectors.enable_gcp`, `gcp_project_id` | `quirk-scanner[cloud]` | (no dedicated doc yet) |
| Database | Postgres / MySQL ssl-mode + RDS encryption | `connectors.enable_db`, `pg_targets`, `mysql_targets`, scanner user/password | `quirk-scanner[db]` | (no dedicated doc yet) |
| Object storage | S3 bucket encryption + Azure Blob encryption | `connectors.enable_s3`, `enable_blob` | `quirk-scanner[cloud]` | (no dedicated doc yet) |
| Kubernetes | EKS/GKE/AKS encryption + secret enumeration | `connectors.enable_k8s`, `k8s_provider`, `k8s_cluster_name`, kubeconfig fields | `quirk-scanner[cloud]` | (no dedicated doc yet) |
| Vault | Transit keys + PKI + auth methods | `connectors.enable_vault`, `vault_addr`, `vault_token`, `vault_transit_mount` | `quirk-scanner[cloud]` (`hvac`) | (no dedicated doc yet) |
| Docker (image SBOM) | (uses container scanner) | (see Container row) | `syft` | [`docs/connectors/docker.md`](connectors/docker.md) |
| Git (semgrep) | (uses source scanner) | (see Source row) | `semgrep` | [`docs/connectors/git.md`](connectors/git.md) |

#### 6.2 Protocol scanner details

##### TLS scanner

Probes every `(host, port)` pair in `scan.ports_tls`, performs a full TLS handshake
via `sslyze`, and walks the certificate chain. Findings include expired certificates,
weak signature algorithms (SHA-1, MD5), short RSA keys (<2048), deprecated TLS
versions (1.0, 1.1), and weak cipher suites. Activated by the core install — no extra
required.

##### SSH scanner

Pulls the SSH banner from each target, then runs `ssh-audit` to enumerate KEX
algorithms, host-key types, and cipher/MAC suites. Emits a "SSH quantum planning
advisory" when only classical KEX is offered, and surfaces specific weaknesses (e.g.
`diffie-hellman-group1-sha1`, `ssh-rsa` host keys with short moduli). Requires the
`ssh-audit` binary on `PATH`.

**Optional prerequisite — `ssh-audit`:** the SSH scanner's per-algorithm classification
(KEX, host-key, MAC breakdown) depends on the external `ssh-audit` binary
(`quirk/scanner/ssh_scanner.py`, `shutil.which("ssh-audit")`). It is not a `quirk-scanner`
dependency and is not installed by any `pip install quirk-scanner[...]` extra — install it
separately:

```bash
pip install ssh-audit
```

If `ssh-audit` is not on `PATH`, the scanner does not fail — it silently falls back to a raw
SSH banner grab and emits only a single generic "SSH quantum planning advisory" INFO finding,
with no per-algorithm KEX/host-key/MAC breakdown or per-algorithm NIST quantum level. Install
`ssh-audit` before scanning if you need that detail.

> **If you installed `ssh-audit` before 2026-08-31 and saw no additional detail, that was a
> bug, not your setup.** The scanner invoked `ssh-audit` with a malformed command line, so the
> silent-fallback path above ran on every scan regardless of whether the binary was present.
> Scans from affected versions recorded no SSH algorithm data, and their CBOMs contain no SSH
> algorithm components. Re-scan any SSH hosts you need per-algorithm inventory for.

Note that `ssh-audit` must be on the `PATH` of the process running the scan. If QU.I.R.K. is
installed in a virtualenv and you invoke it via an absolute interpreter path
(`/path/to/.venv/bin/python -m ...`) without activating the environment, the venv's `bin/`
directory is *not* added to `PATH` and `shutil.which("ssh-audit")` will not find it. Activate
the environment, or ensure the directory containing `ssh-audit` is on `PATH`.

##### JWT/API scanner

Iterates over `jwt_targets` and inspects either local JWT samples or live token
endpoints to discover the signing algorithm declared in the JWT header. Classifies
each algorithm against the `algorithm-classification` ruleset and emits findings for
algorithms that fail post-quantum guidance per FIPS 203 / 204 / 205 and NIST IR 8547.
Gated by `connectors.enable_jwt`.

**Security note — `allow_insecure_jwks`:** By default the JWT scanner verifies TLS
certificates when fetching JWKS endpoints (`allow_insecure_jwks: false`). Set
`allow_insecure_jwks: true` only when scanning internal or dev endpoints that use
self-signed or expired certificates. When this flag is enabled:

- TLS certificate verification is disabled for JWKS fetches only (other scan phases
  are unaffected).
- A `HIGH` severity advisory finding (`ADVISORY_JWKS_VERIFY_DISABLED`) is automatically
  emitted for every JWKS URL fetched, so the override is always visible in reports.
- QUIRK remains a passive inventory tool — it does not rely on JWKS key material for
  any authentication decision, so a MITM on the JWKS URI cannot escalate privileges.
  The threat model accepts this for controlled assessment environments.

See `docs/configuration.md` §Connectors for the full `allow_insecure_jwks` config key
reference.

##### Container scanner

For each entry in `container_targets`, generates a Syft SBOM of the named Docker
image and scans the resulting package list for crypto libraries flagged in the
quantum-readiness ruleset (e.g. legacy OpenSSL, vendored mbedTLS). Emits "Container
image uses quantum-vulnerable crypto library" findings with the image digest and
package version. Requires `syft` on `PATH` and `connectors.enable_container=true`.

##### Source-code scanner

Walks each git repository in `source_targets` (local clone or remote URL) and runs
semgrep with the QU.I.R.K. ruleset to detect hardcoded weak primitives, cipher
construction patterns, and PRNG misuse. Findings carry the file path and line range.
Requires `semgrep` on `PATH` and `connectors.enable_source=true`.

##### DNSSEC scanner

Resolves DNSKEY, DS, and RRSIG records for each domain in `dnssec_targets` and
classifies the signing algorithms (RSASHA1, RSASHA256, ECDSAP256SHA256, ED25519, etc.)
against the quantum-readiness rubric. Reports broken chains, missing DS records, and
signing algorithms misaligned with NIST IR 8547 guidance. Requires `quirk-scanner[identity]`.

##### Kerberos scanner

Connects to KDC port 88 on each entry in `kerberos_targets` and enumerates supported
encryption types (`aes256-cts-hmac-sha1-96`, `aes128-cts-hmac-sha1-96`,
`des-cbc-md5`, etc.). Findings flag any KDC still offering DES/RC4 enctypes and note
where AES-only enforcement is missing. Requires `quirk-scanner[identity]`.

##### SAML scanner

Fetches the SAML IdP metadata for each entry in `saml_targets` and inspects the
declared SignatureMethod and DigestMethod algorithms (`rsa-sha1`, `rsa-sha256`,
`ecdsa-sha256`, etc.). Findings flag IdPs still signing with SHA-1 or otherwise
non-conformant primitives. Requires `quirk-scanner[identity]`.

##### Email scanner

Probes 7 email-TLS ports per target — SMTP `25`/`465`/`587`, IMAP `143`/`993`, POP3
`110`/`995` — handling both implicit TLS and STARTTLS upgrades. Findings include
"STARTTLS downgrade risk on SMTP", missing implicit-TLS on submission, and weak
ciphers on the negotiated channel. Requires `quirk-scanner[motion]`.

##### Broker scanner

Probes message-broker endpoints across five protocol families: Kafka (configurable
listeners), AMQP (RabbitMQ), Redis, Azure Service Bus (per `broker_azure_namespaces`),
and Amazon SQS (per `broker_sqs_regions`). Findings include plaintext-listener
detection, weak TLS configuration, and missing authentication. Gated by
`connectors.enable_broker=true` and requires `quirk-scanner[motion]`.

**Non-default ports (Phase 190, TRIAGE-06):** each family's default port table is fixed; to
also probe a broker running on a non-standard port, list it in `connectors.broker_targets`
(`host` / `host:port` / `[ipv6]:port`). Declared ports are probed *in addition to* the
defaults — this can only widen coverage, never narrow it. An explicitly-named `host:port` that
never responds produces exactly one `ADVISORY`-severity row rather than failing silently. See
[`docs/configuration.md`](#configuration) for full syntax and semantics.

#### quirk doctor

Pre-engagement health check. Runs eight diagnostic probes and prints a
Rich-formatted dashboard. Exit code is the machine-readable signal:

- `0` — all non-informational checks pass; QUIRK is ready to scan
- `1` — one or more non-informational checks failed; address before scanning

##### Usage

```bash
quirk doctor
```

No flags are accepted. Invoke before each client engagement.

##### Categories

| # | Category | Severity | Failure exits 1? |
|---|----------|----------|------------------|
| 1 | Python environment (>= 3.11) | non-informational | yes |
| 2 | Scanner binaries (`nmap`, `syft`, `semgrep` in PATH) | non-informational | yes |
| 3 | Compliance framework freshness (within `STALENESS_THRESHOLD_DAYS`) | non-informational | yes |
| 4 | QRAMM module availability | informational | **no** |
| 5 | Database (`./quirk.db` reachable) | non-informational | yes |
| 6 | Configuration (`./config.yaml` parses) | non-informational | yes (malformed); informational only if file is absent |
| 7 | Network connectivity (DNS probe) | informational | **no** |
| 8 | Dashboard process (port 8512) | informational | **no** |

##### Symbols

- `[✓]` — check passed
- `[!]` — informational status (never causes exit 1)
- `[✗]` — check failed (causes exit 1 if non-informational)

##### Examples

```text
$ quirk doctor
                        QU.I.R.K. Health Check
┏━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Check                   ┃ Status                                        ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Python environment      │ [✓] Python 3.14                               │
│ Binary: nmap            │ [✓] /opt/homebrew/bin/nmap                    │
│ Binary: syft            │ [✓] /opt/homebrew/bin/syft                    │
│ Binary: semgrep         │ [✗] semgrep not found in PATH                 │
│ Compliance freshness    │ [✓] all frameworks within freshness window    │
│ QRAMM module            │ [!] QRAMM module not installed — Phase 51     │
│ Database (quirk.db)     │ [✓] ./quirk.db reachable                      │
│ Configuration           │ [✓] ./config.yaml parses cleanly              │
│ Network connectivity    │ [✓] outbound TCP to 8.8.8.8:53 OK             │
│ Dashboard process       │ [!] dashboard not running on port 8512        │
└─────────────────────────┴───────────────────────────────────────────────┘
$ echo $?
1
```

(In the example above, `semgrep` is missing — a non-informational failure that
exits 1.)

---

### 7. Compliance Map Maintenance

QU.I.R.K. ships a `COMPLIANCE_MAP` in `quirk/compliance/__init__.py` that joins
finding titles to PCI-DSS, HIPAA (45 CFR §164.312), and FIPS 140-3 controls.
Regulators publish revisions on their own cadences; this runbook documents how
QU.I.R.K. maintainers keep the map current and how operators can verify freshness on
demand.

#### 7.1 Quarterly review checklist

1. Run `quirk compliance status` and confirm every framework's `Last Verified` date is
   within the last 90 days.
2. Visit each publisher URL (table below) and check for newly published revisions.
3. If a revision exists, follow §7.4 "Upgrade path".
4. If no revision exists but `last_verified` is older than 90 days, update
   `last_verified` to today after re-reading the current source — this re-confirms our
   reading and resets the staleness clock.
5. Run `pytest tests/test_compliance_schema.py tests/test_compliance_freshness.py
   tests/test_compliance_title_join.py` — all green.
6. Commit and push.

#### 7.2 Source URLs to monitor

| Framework | Publisher | Monitor URL |
|-----------|-----------|-------------|
| PCI-DSS | PCI Security Standards Council | https://www.pcisecuritystandards.org/document_library/ |
| HIPAA 45 CFR §164.312 (publisher landing) | HHS / ECFR | https://www.hhs.gov/hipaa/for-professionals/index.html |
| HIPAA 45 CFR §164.312 (canonical regulation text) | HHS / ECFR | https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-C/part-164 |
| FIPS 140-3 | NIST CSRC | https://csrc.nist.gov/publications/fips |
| SOC 2 (Trust Services Criteria) | AICPA | https://www.aicpa-cima.com/resources/landing/aicpa-trust-services-criteria |
| ISO 27001:2022 | ISO / national body | https://www.iso.org/standard/27001 |

#### 7.3 How to detect drift

QU.I.R.K. ships several CI gates that fail the build before stale data ships to a
customer:

- **`tests/test_compliance_freshness.py`** — fails when any entry's `last_verified` is
  older than `STALENESS_THRESHOLD_DAYS` (currently 365 days; defined in
  `quirk/compliance/__init__.py`). This is the 12-month staleness gate (COMPLY-08).
- **`tests/test_compliance_schema.py`** — fails when any entry is missing `framework`,
  `control`, `version`, `last_verified`, or `source_url`.
- **`tests/test_compliance_title_join.py`** — fails when an emitted finding title is
  not in `COMPLIANCE_MAP` or `UNMAPPED_TITLES`.
- **`tests/test_compliance_cli.py`** — smoke for `quirk compliance status` (text +
  JSON).
- **`tests/test_compliance_report_section.py`** — verifies the HTML/PDF "Compliance
  Summary" section.

Operators can run `quirk compliance status` ad hoc before customer engagements to
print per-framework version, `last_verified` date, and `source_url`:

```bash
# Default text format
quirk compliance status

# JSON format (machine-readable; useful in CI)
quirk compliance status --format json
```

#### 7.4 Upgrade path: PCI-DSS 4.0.1 → 4.1 (worked example)

1. PCI SSC publishes PCI-DSS v4.1 at
   https://www.pcisecuritystandards.org/document_library/.
2. Maintainer reviews the diff: control numbers may shift; requirement text may add
   new clauses.
3. Edit `quirk/compliance/__init__.py`:
   - Update the `_PCI_4_0_1_URL` constant — rename and re-point to the v4.1 PDF, or
     add a `_PCI_4_1_URL` alongside.
   - Update the `_pci()` helper — change `"version": "4.0.1"` → `"version": "4.1"`.
   - Update `_PHASE_49_VERIFIED` to today's ISO date.
   - For any control numbers that moved (e.g. `4.2.1` → `4.2.2`): edit each affected
     `COMPLIANCE_MAP` entry's `_pci("X")` argument.
4. Run `pytest tests/test_compliance_schema.py tests/test_compliance_freshness.py
   tests/test_compliance_title_join.py` — confirm green.
5. Run `quirk compliance status` — confirm the new version and today's
   `last_verified` print.
6. Commit (e.g. `chore(compliance): upgrade PCI-DSS to 4.1`) and push; CI re-runs the
   full gate.

The same shape applies to HIPAA 45 CFR §164.312 revisions (edit `_HIPAA_164_312_URL`
+ `_hipaa()` helper) and FIPS 140-3 revisions (edit `_FIPS_140_3_URL` + the relevant
entries).

---

### 8. Distributed Sensor Deployment

*(Audience: operators deploying QU.I.R.K. across segmented enterprise networks where a single
scanner host cannot reach all segments. Two or more sensor nodes push their per-segment
findings to a shared console; the console merges them into one unified CBOM and one
quantum-readiness score.)*

**Architecture overview:**

```
[segment-a host]                 [console host]
  quirk sensor push ──────────→  quirk serve --host 0.0.0.0
                     HTTPS
[segment-b host]
  quirk sensor push ──────────→  (same console)
                                   │
                              quirk sensor merge
                                   │
                           one CBOM + one score
```

Each sensor is a standard `pip install quirk-scanner[all]` deployment. Sensors
communicate with the console over HTTPS using a shared HMAC key and a shared console
API token set at enrollment time.

#### 8.1 Provision the console

Install QU.I.R.K. on the console host and start the server. The console must bind a
routable address so sensors can reach it over the network:

```bash
# Console host (Linux / macOS)
pip install "quirk-scanner[all]"

# Set the shared API token BEFORE starting the server.
# Sensors must send this same token in every push request.
export QUIRK_API_TOKEN="<your-strong-random-token>"

# Start the server — bind to a specific interface or 0.0.0.0 for all interfaces.
# The console binds loopback by default; override for multi-host use.
quirk serve --host 0.0.0.0 --port 8512
```

> **Security note:** Do not expose the console port to untrusted networks without an
> HTTPS reverse proxy and IP allowlist in front of it. Set `QUIRK_API_TOKEN` to a
> strong random value before starting the server; `quirk serve` without this variable
> runs with authentication disabled (appropriate only for local dev/testing).
>
> As a guardrail, `quirk serve` now **refuses to start** on a network-reachable
> interface when no `QUIRK_API_TOKEN` is configured, unless you pass `--insecure` to
> explicitly acknowledge a token-less bind on a trusted, firewalled segment. When the
> console runs behind a reverse proxy, set `QUIRK_TRUST_PROXY` (default `127.0.0.1`)
> so per-IP rate limiting and the audit log see the real sensor address rather than
> the proxy's. For a **cloud-hosted console** (e.g. on Linode) with internal sensors
> pushing in, follow the hardened, end-to-end walkthrough in
> [`deployment-cloud-console.md`](deployment-cloud-console.md) and the ready-to-use
> files under [`deploy/`](../deploy/).

#### 8.1.1 v5.5 per-sensor authentication model (migration from v5.4)

In v5.5, every sensor authenticates `POST /api/sensor/push` with its **own per-sensor
token** issued by `quirk console enroll`. This replaces the v5.4 shared-token model
(where all sensors used the same `QUIRK_API_TOKEN`). The cutover is clean — there is no
dual-accept period (D-10).

| Component | Role |
|-----------|------|
| `QUIRK_API_TOKEN` env var (or `security.api_token` in `config.yaml`) | Console's shared token; governs operator/dashboard auth — **unaffected** |
| Enrollment token from `quirk console enroll` | **The per-sensor push credential.** Shown once; only its SHA-256 hash is stored in `sensor_tokens`. Place this raw value in `console_api_token` in `sensor.yaml` on the sensor host. |
| `console_api_token` in `sensor.yaml` | Must hold the sensor's per-sensor enrollment token (not the shared `QUIRK_API_TOKEN`) |

**What changed from v5.4:** Each sensor now uses its own revocable enrollment token to
authenticate push requests. The shared `QUIRK_API_TOKEN` no longer authenticates pushes.

**Migration steps (per sensor host):**

1. On the **console host**, print the enrollment token for the sensor:
   ```bash
   quirk console enroll --segment <label>
   # → Bearer token: <per-sensor-token>  (copy now — shown once)
   # → sensor_id: <uuid>
   ```
2. On each **sensor host**, open `sensor.yaml` and set:
   ```yaml
   console_api_token: <per-sensor-token>   # replace the old QUIRK_API_TOKEN value here
   ```
3. If the raw enrollment token was lost, revoke and re-enroll:
   ```bash
   # Console host — revoke the old token
   quirk console revoke-sensor <sensor_id>
   # Re-enroll to mint a fresh token + new sensor_id
   quirk console enroll --segment <label>
   ```

The shared `QUIRK_API_TOKEN` still controls operator CLI and dashboard access. It is
unaffected by per-sensor push tokens.

#### 8.2 Enroll each sensor

On the **console host**, provision a sensor row for each sensor. Each invocation creates
a new `sensors` row in the console database and prints a **per-sensor push token** to
stdout. This token **IS** the push credential — place it in `console_api_token` in
`sensor.yaml` on the sensor host. It is shown once and never recoverable; only its
SHA-256 hash is stored in `sensor_tokens`.

```bash
# Console host — run once per sensor
quirk console enroll --segment <label>
# e.g.:
quirk console enroll --segment segment-a
# → Bearer token (copy now — shown once, never recoverable): <per-sensor-token>
# → sensor_id: <uuid>
quirk console enroll --segment segment-b
```

On each **sensor host**, run `quirk sensor enroll` and set `console_api_token` to the
enrollment token printed above:

```bash
# Sensor host — Linux / macOS
quirk sensor enroll https://<console-host>:8512 \
  --segment <label>
# Then edit sensor.yaml: set console_api_token to the per-sensor enrollment token.
# e.g.:
quirk sensor enroll https://console.corp:8512 \
  --segment segment-a
# Edit ~/.config/quirk/sensor.yaml:
#   console_api_token: <per-sensor-token-from-quirk-console-enroll>
```

Enrollment writes `sensor.yaml` to the default platform config directory:
- **Linux / macOS:** `~/.config/quirk/sensor.yaml` (XDG `user_config_dir`)
- **Windows:** `%APPDATA%\quirk\sensor.yaml`

The file stores the `sensor_id` (UUID), `segment` label, HMAC key, console URL, and the
`console_api_token` used to authenticate push requests.

Use `--config <path>` to place `sensor.yaml` at a custom location (useful in CI or when
running multiple sensors on the same host).

#### 8.3 Push findings

On each sensor host, run a local scan and push the results to the console in a single
command:

```bash
# Sensor host
quirk sensor push
# With a custom scan config (recommended for enterprise targets):
quirk sensor push --scan-config /etc/quirk/sensor-scan.yaml
```

`quirk sensor push` runs a local scan using the target list in the scan config,
serialises the findings into a signed, compressed `.qpush` envelope, and delivers it to
the console over HTTPS. The console responds HTTP 200 on success.

If the console is temporarily unreachable, the payload is spooled to
`user_data_dir("quirk")/spool/` and retried automatically on the next invocation.

#### 8.4 Merge into a unified CBOM

On the **console host**, run the merge after all sensors have pushed:

```bash
# Console host
quirk sensor merge

# Optional flags:
quirk sensor merge --stale-days 7       # ignore sensors silent > 7 days
quirk sensor merge --output-dir ./out   # write CBOM / reports here
```

`quirk sensor merge` re-runs `compute_readiness_score()` and `build_cbom()` over the
union of all pushed `CryptoEndpoint` rows, producing:

- One merged CBOM (`cbom-<ts>.json` + `cbom-<ts>.xml`)
- One unified quantum-readiness score
- A `coverage_warning` if any enrolled sensor has not pushed within `stale_days`

**MERGE-03 behaviour:** If two or more sensors scanned the same logical hostname and port
(e.g. `crypto.internal:443` appearing in both a DMZ and a PCI segment), the CBOM will
contain **one component per sensor** — distinct by `sensor_id` — not a de-duplicated
single entry. The `(sensor_id, host, port)` uniqueness key is the correct model for
segmented networks where the same address exists in multiple security zones.

#### 8.5 Windows sensor installation

QU.I.R.K. sensors run on Windows with no additional configuration beyond the standard
Python install.

**Prerequisites:** Python 3.11+ for Windows, available from https://www.python.org/downloads/

**Install:**

```powershell
# PowerShell (run as the service account that will run the sensor)
pip install "quirk-scanner[all]"
```

**Enroll and push (PowerShell):**

```powershell
# Enroll (one-time)
quirk sensor enroll https://<console-host>:8512 `
  --segment segment-windows
# Then edit %APPDATA%\quirk\sensor.yaml:
#   console_api_token: <per-sensor-token-from-quirk-console-enroll>

# sensor.yaml written to: $env:APPDATA\quirk\sensor.yaml

# Push findings
quirk sensor push --scan-config C:\quirk\sensor-scan.yaml
```

**`sensor.yaml` path on Windows:** `%APPDATA%\quirk\sensor.yaml`
(resolved via `platformdirs.user_config_dir("quirk")` at runtime).

**SIGTERM note:** The QU.I.R.K. scheduler uses `signal.SIGTERM` for graceful shutdown on
Linux/macOS but guards it with `sys.platform != 'win32'` (`scheduler_cmd.py:283-284`).
On Windows, use Ctrl+C or the Windows Service stop API instead of SIGTERM.

**nmap dependency:** The TLS scanner requires `nmap` on `PATH`. Download the Windows
installer from https://nmap.org/download.html and confirm `nmap.exe` is accessible:

```powershell
nmap --version
```

#### 8.6 Air-gap path (offline sensor → console)

For sensors with no network path to the console, use file-based export/import:

```bash
# Sensor host (no console connectivity)
quirk sensor export-results
# → writes <sensor_id>-<payload_id>.qpush to the current directory (or --output-dir)
```

Transfer the `.qpush` file to the console host via USB, secure file share, or any
out-of-band channel, then import:

```bash
# Console host
quirk console import-results /path/to/<sensor_id>-<payload_id>.qpush
```

The console validates the HMAC signature, decompresses the envelope, deduplicates by
`payload_id` (idempotent re-import is safe), and ingests the findings. Run
`quirk sensor merge` afterwards to produce the unified CBOM.

---

#### 8.8 Windows sensor deployment (zip + Scheduled Task)

*(v5.6+ — frozen binary; no Python required on the sensor host)*

For Windows sensor hosts where a Python runtime is not available (or not desired),
download the pre-built `quirk-windows-<version>.zip` asset from the [GitHub Release](
https://github.com/0xD1g5/QU.I.R.K/releases) for your target version. The zip bundles
the frozen `quirk.exe` onedir executable together with `install.ps1`, `uninstall.ps1`,
and a `sensor.sample.yaml` reference config — no Python install required on the sensor
host.

##### Unsigned binary notice

The zip asset is **NOT Authenticode-signed**. Authenticode signing is deferred to a
future milestone. Operators may see a Windows SmartScreen prompt ("Windows protected your
PC") when running `install.ps1` or `quirk.exe` for the first time. To proceed: click
**More info**, then **Run anyway**. Operators who require signed binaries should build
from source until Authenticode signing is implemented.

##### Prerequisites

- **PowerShell 5.1+** (built in to Windows 10/11 and Windows Server 2016+).
- An enrollment token issued by `quirk console enroll` on the console host. See
  §8.1.1 for how to provision per-sensor push credentials via
  `quirk console enroll --segment <label>`.
- Network access from the Windows host to the QUIRK console on its listen port
  (default 8512).

##### Install

1. Download `quirk-windows-<version>.zip` from the GitHub Release and unpack it:

   ```powershell
   Expand-Archive -Path quirk-windows-<version>.zip -DestinationPath C:\quirk-install
   cd C:\quirk-install
   ```

2. Run `install.ps1`. The installer copies the bundle to
   `%LOCALAPPDATA%\Programs\QUIRK` (**no admin elevation required**), enrolls the
   sensor against the console, tightens the sensor config ACL to the current user,
   and registers a daily Scheduled Task named **"QUIRK Sensor Push"** that runs
   `quirk.exe sensor push` on the chosen cadence.

   Mandatory parameters:

   | Parameter | Description |
   |-----------|-------------|
   | `-ConsoleUrl` | Base URL of the QUIRK console (e.g. `https://quirk.example.com` or `https://10.0.0.5:8512`). |
   | `-EnrollmentToken` | Per-sensor opaque Bearer token from `quirk console enroll`. Passed directly to `quirk.exe sensor enroll --api-token`; never echoed to console or logs. |

   Optional parameters:

   | Parameter | Default | Description |
   |-----------|---------|-------------|
   | `-Segment` | `"windows"` | Network segment label written to the sensor config. |
   | `-Time` | `"03:00"` | Daily trigger time for the Scheduled Task (HH:MM format). |
   | `-AllowInternalConsole` | *(switch)* | Pass to allow the sensor to reach a console on a private/RFC1918 address (on-prem or lab). |

   Example — production console:

   ```powershell
   pwsh -File install.ps1 `
     -ConsoleUrl https://quirk.example.com `
     -EnrollmentToken <per-sensor-token>
   ```

   Example — on-prem lab console on a private IP, custom cadence and segment:

   ```powershell
   pwsh -File install.ps1 `
     -ConsoleUrl https://10.0.0.5:8512 `
     -EnrollmentToken <per-sensor-token> `
     -AllowInternalConsole `
     -Time 02:00 `
     -Segment corp-windows
   ```

   After `install.ps1` completes, the sensor is installed at
   `%LOCALAPPDATA%\Programs\QUIRK\quirk\quirk.exe` and the sensor config is written to
   `%LOCALAPPDATA%\Programs\QUIRK\config\sensor.yaml`. The config file is ACL-restricted
   to the current user immediately after enrollment.

##### Scheduled Task

`install.ps1` registers a Windows Scheduled Task named **"QUIRK Sensor Push"** that runs
`quirk.exe sensor push` daily at the configured time under the current user account
(**no admin elevation** — `RunLevel Limited`). To inspect or manage the task:

```powershell
# Confirm the task exists and its next run time
Get-ScheduledTask -TaskName "QUIRK Sensor Push" | Get-ScheduledTaskInfo

# Disable the task (without removing it)
Disable-ScheduledTask -TaskName "QUIRK Sensor Push"

# Run the push immediately (outside the schedule)
& "$env:LOCALAPPDATA\Programs\QUIRK\quirk\quirk.exe" sensor push `
    --config "$env:LOCALAPPDATA\Programs\QUIRK\config\sensor.yaml"
```

##### Uninstall

Run `uninstall.ps1` from any working directory (it does not need to be in the unpack
root — it always targets `%LOCALAPPDATA%\Programs\QUIRK`):

```powershell
# Full removal — unregisters the Scheduled Task and removes all installed files
pwsh -File uninstall.ps1

# Preserve the sensor config (re-install without re-enrolling)
pwsh -File uninstall.ps1 -KeepConfig
```

`-KeepConfig` removes the binary bundle but leaves `%LOCALAPPDATA%\Programs\QUIRK\config\`
intact so a future `install.ps1` run can reuse the existing sensor identity without
re-enrolling.

##### Security note — sensor config at rest

The sensor config file (`%LOCALAPPDATA%\Programs\QUIRK\config\sensor.yaml`) holds the
per-sensor push credential (`console_api_token`). `install.ps1` tightens its ACL to
grant **Read + Write to the current user only** immediately after enrollment. Do not
commit or share this file. If the token is compromised, revoke it on the console host
and re-enroll:

```bash
# Console host
quirk console revoke-sensor <sensor_id>
quirk console enroll --segment <label>
```

Then re-run `install.ps1` on the Windows host with the new enrollment token.

---

#### 8.9 Automatic Merge

*(v5.5+)*

When every enrolled (non-revoked) sensor has pushed its latest results, the console can
merge them automatically — eliminating the need to run `quirk sensor merge` manually in
the common deployment case.

##### Default behaviour

Auto-merge is **ON by default**. After each successful `POST /api/sensor/push`, the
console re-evaluates the trigger condition. When it is satisfied, a merge runs in the
background via a FastAPI `BackgroundTask` after the push response is already sent —
so push latency is unaffected and a merge failure can never block or roll back a
sensor push (AUTOMERGE-02).

##### Disabling auto-merge

Add the `console.auto_merge` block to your console `config.yaml`. Set `enabled` to
`false` for explicit manual-only control (v5.4 behaviour):

```yaml
console:
  auto_merge:
    enabled: false          # set to false to require manual 'quirk sensor merge'
    trigger_condition: all-sensors-in
    # cadence_window_minutes: 1440
```

The toggle is read at evaluation time (per push). Changing the setting takes effect on
the next push; any in-flight pushes or merge tasks that have already started are
unaffected.

##### Trigger conditions

`trigger_condition` selects how the console decides it is time to merge. Two values are
available:

**`all-sensors-in`** (default)

The merge fires once every non-revoked enrolled sensor has checked in with a push newer
than the latest `MergeRun`. This is the safest choice for fixed-fleet deployments — you
always get a full-coverage CBOM. Revoked sensors are excluded from the "all in" set
(Phase 113 `revoked_at`), so revoking a decommissioned sensor does not block the merge.

**`cadence-window`**

The merge fires when the elapsed time since the last `MergeRun` exceeds a configured
window. The push that crosses the window boundary triggers the merge with whatever has
arrived at that moment. Sensors that have not pushed by the window deadline are listed in
a `coverage_warning` on the merged CBOM. This mode suits deployments where not all
sensors push on the same cadence or where time-bounded merges are preferred over
full-coverage guarantees.

Set the window explicitly with `cadence_window_minutes` (integer, minutes). If omitted,
the console defaults to the per-sensor `expected_cadence_minutes` value (default 1440
— 24 hours).

```yaml
console:
  auto_merge:
    enabled: true
    trigger_condition: cadence-window
    cadence_window_minutes: 720    # merge every 12 hours
```

##### Idempotency and duplicate merges

On single-tenant deployments, a narrow race between two simultaneous final pushes can
produce a second `MergeRun` row before the first has committed. This is harmless — the
rows are identical and the `scanned_at` timestamps on sensor findings are never
rewritten. The background task re-checks the condition before merging, so most
near-simultaneous pushes coalesce to one merge.

##### Reading auto-merge outcomes

Every auto-merge writes an `IntegrationDelivery` audit row:

| Field | Success value | Failure value |
|-------|--------------|---------------|
| `destination` | `auto_merge` | `auto_merge` |
| `status` | `ok` | `failed` |
| `error_summary` | *(empty)* | Sanitised error message |

Query via the dashboard or directly in SQLite:

```sql
SELECT destination, status, error_summary, created_at
FROM integration_deliveries
WHERE destination = 'auto_merge'
ORDER BY created_at DESC
LIMIT 10;
```

A `status='failed'` row means the merge raised an exception after the sensor push
response was already sent — the push data is safe and fully ingested. Check the console
log (`logger.warning` is emitted alongside the audit row) to diagnose the merge failure,
then run `quirk sensor merge` manually to retry.

##### Manual merge is unchanged (AUTOMERGE-03)

The `quirk sensor merge` command remains available and works identically to v5.4 — the
same Option-A union CBOM, `coverage_warning`, and sensor-local `scanned_at`. Auto-merge
and manual merge call the same underlying `merge_scan()` function. Operators who need
explicit control, scripted post-push merge verification, or a one-off merge after
enabling `all-sensors-in` with auto-merge disabled can always run:

```bash
quirk sensor merge
# Or with custom options:
quirk sensor merge --stale-days 7 --output-dir /var/quirk/merge-out
```

---

#### 8.7 All-configurations / settings reference (999.59)

The table below covers every knob relevant to distributed sensor deployments, closing
the settings-coverage gap (999.59). For the full single-host config reference see
[`docs/configuration.md`](#configuration).

##### `scan.timeouts.*` — per-scanner timeout knobs

Set in `config.yaml` under the `scan.timeouts` block. All values are in seconds.

| Key | Default (s) | Scanner |
|-----|-------------|---------|
| `scan.timeouts.tls_seconds` | 6 | TLS / sslyze |
| `scan.timeouts.ssh_seconds` | 6 | SSH |
| `scan.timeouts.jwt_seconds` | 10 | JWT / API |
| `scan.timeouts.container_seconds` | 120 | Container (Syft) |
| `scan.timeouts.source_seconds` | 300 | Source code (Semgrep) |
| `scan.timeouts.dnssec_seconds` | 10 | DNSSEC |
| `scan.timeouts.saml_seconds` | 10 | SAML |
| `scan.timeouts.kerberos_seconds` | 10 | Kerberos |
| `scan.timeouts.vault_seconds` | 10 | HashiCorp Vault |
| `scan.timeouts.db_connect_seconds` | 5 | Postgres / MySQL |
| `scan.timeouts.broker_seconds` | 10 | Kafka / RabbitMQ / Redis |
| `scan.timeouts.email_seconds` | 10 | Email (SMTP / IMAP / POP3) |
| `scan.timeouts.fingerprint_seconds` | 4 | Fingerprint probe |
| `scan.timeouts.default_seconds` | 5 | Fallback for unlisted scanners |

See [`docs/timeout-retry-audit.md`](timeout-retry-audit.md) for retry policies and jitter.

##### `output.directory` — report output path

```yaml
output:
  directory: "./quirk-output"   # default; relative to CWD or absolute
```

All scan outputs (HTML/PDF/DOCX reports, CBOM JSON/XML, findings JSON,
`executive.md`, `technical.md`, `intelligence-*.json`) land here. On sensor nodes,
`quirk sensor push` uses a temporary directory for the local scan and discards it after
push; set `--scan-config` and a stable `output.directory` if you want per-push
artefacts retained on the sensor host.

##### Sensor identity fields in scan output

| Field | Location | Description |
|-------|----------|-------------|
| `sensor_id` | `CryptoEndpoint` DB column; CBOM component metadata | UUID assigned at `quirk sensor enroll`; `nullable=True` (NULL = implicit local sensor, backward-compatible with pre-v5.4 scans) |
| `segment` | `CryptoEndpoint` DB column; findings JSON | Network-segment label passed via `--segment` at enroll time; appears in `findings-<ts>.json` per-finding and in the merged CBOM |

These two fields are the differentiators for MERGE-03 — two findings with identical
`host:port` but different `sensor_id` values are intentional and correct; they represent
the same logical endpoint discovered independently in two network segments.

---

### 9. Hardware Scanning

Hardware scanning is an advanced, opt-in capability that fingerprints network devices
(switches, routers, access points) via SNMP, assigns CNSA 2.0 remediation tiers, and
annotates crypto-bridge topology. Operators who have not installed the `[hw]` extra and
do not manage network hardware can complete §1–§8 without interruption — the scanner
runs cleanly with the extra absent.

#### 9.1 Enable SNMP Scanning

**Step 1 — Install the `[hw]` extra.**

```bash
pip install 'quirk-scanner[hw]'
```

This extra adds `pysnmp` and the hardware fingerprinting engine. See the §2.2 optional
extras matrix for a full dependency list.

**Step 2 — Enable SNMP in your config.**

Add the following two keys under the `scan:` block in `config.yaml`:

```yaml
scan:
  enable_snmp: true          # default: false — must be explicitly set to opt in
  snmp_community: "public"   # SNMPv2c community string; default: "public"
```

`enable_snmp` defaults to `false`. If you omit the key or leave it as `false`, the
scan runs cleanly with no error and no hardware devices appear in the output — this is
the expected behaviour when `[hw]` is not installed or when SNMP coverage is not needed.

**Step 3 — Run the scan.** The SNMP probe executes **after all endpoint scans complete**
and targets every unique host IP discovered during the full scan (TLS, SSH, fingerprint,
etc.), not just SSH endpoints. No additional target list is required.

**What QUIRK probes.** Three SNMP OIDs are queried per host:

| OID | Name | Purpose |
|-----|------|---------|
| `1.3.6.1.2.1.1.1.0` | `sysDescr` | Vendor and model string — primary parse target |
| `1.3.6.1.2.1.1.5.0` | `sysName` | Device hostname |
| `1.3.6.1.2.1.1.2.0` | `sysObjectID` | Enterprise OID — fallback vendor identification |

**Sample output.** Discovered hardware devices appear as a separate findings block:

```text
Hardware Devices Found: 3

  192.168.1.1   Cisco Catalyst 9300    Tier 1  HIGH   Replace by 2030
  192.168.1.254 Juniper EX2300         Tier 2  MEDIUM Upgrade firmware 2030-2033
  10.0.0.1      Aruba 2930F            Tier 3  LOW    Accept + monitor, re-evaluate 2033+
```

For the full config-key reference (all `scan.*` defaults, type constraints, and
advanced options), see [`docs/configuration.md`](#configuration).

---

#### 9.1.1 SNMPv3 Auth+Priv Scanning (Phase 139)

QUIRK also supports authenticated, encrypted SNMPv3 scanning as an upgrade path alongside
the SNMPv2c community-string scanning above. SNMPv3 credentials are configured per-host, not
globally — a network may have a mix of v3-capable and v2c-only devices.

**Configure a v3 credential.** Add a `connectors.snmp_v3_credentials` entry keyed by host
(see `docs/configuration.md` for the full field reference):

```yaml
connectors:
  snmp_v3_credentials:
    "192.168.1.1":
      username: "quirk-readonly"
      auth_key_env: "QUIRK_SNMP_AUTH_KEY"
      priv_key_env: "QUIRK_SNMP_PRIV_KEY"
      auth_protocol: "SHA256"
      priv_protocol: "AES256"
```

Set the referenced env vars, then run the scan exactly as in Step 3 above (`--enable-snmp`).
No secret CLI flags exist for v3 credentials — passphrases come only from config + the
environment, never from the command line.

**The v3 → v2c → none fallback ladder.** For each host, QUIRK attempts SNMP in this order:

1. **v3 attempted** — if a `snmp_v3_credentials` entry exists for the host, QUIRK probes with
   those USM credentials first.
2. **v2c fallback** — if v3 fails (wrong credentials) or the host offers a weaker protocol
   than requested, QUIRK falls back to the SNMPv2c community-string probe (§9.1) so the
   vendor/model identification can still succeed.
3. **none** — if neither v3 nor v2c gets a response, no SNMP finding is recorded for that
   host.

Each outcome is recorded honestly, not collapsed into a generic "SNMP succeeded" label — see
`docs/report-interpretation.md` for the five distinct labels this produces in reports and the
dashboard, including the important distinction between an intentional v2c-only scan and a
genuine v3 credential failure (`v3-failed-fell-back`).

---

#### 9.2 CNSA 2.0 Remediation Tiers

Each discovered hardware device is assigned a tier derived from CNSA 2.0 (Commercial
National Security Algorithm Suite 2.0) guidance on post-quantum migration timelines.

| Tier | Severity | Deadline | Meaning |
|------|----------|----------|---------|
| Tier 1 | HIGH | Replace by 2030 | No PQC upgrade path — device must be replaced |
| Tier 2 | MEDIUM | Upgrade firmware 2030-2033 | PQC firmware upgrade path exists |
| Tier 3 | LOW | Accept + monitor, re-evaluate 2033+ | PQC roadmap exists but upgrade is distant |
| Tier N/A | INFO | EOL before PQC migration window | Device won't survive to the migration deadline |

**Client-facing action.** When presenting findings: Tier 1 devices require an active
replacement plan — no firmware path exists, so budget and procurement lead time need to
be on the remediation roadmap before 2030. Tier 2 devices need a vendor firmware roadmap
conversation; coordinate with the vendor to confirm the PQC upgrade timeline and track
it as a dated commitment. Tier N/A devices should be documented in the client's
decommission plan rather than the remediation backlog — they will reach end-of-life
before the PQC migration window opens, so a replacement is already warranted on standard
refresh cadence.

> **Note:** Hardware devices appear in the CBOM and on the dashboard hardware panel, but
> are advisory-only — they do not affect the quantum-readiness score. CNSA tiers are
> informational findings that inform the remediation roadmap.

---

#### 9.3 Crypto-Bridge Detection

A **crypto bridge** is a network topology where a PQC-capable gateway (e.g. a TLS
terminator or reverse proxy with hybrid-mode support) sits in front of a legacy backend
device that is itself still running quantum-vulnerable cipher suites. The gateway
mitigates the backend's exposure to the wider network, but the backend's own cipher
posture remains unremediated.

**`partial_only` — what it means and when it fires.** QUIRK flags a device with
`bridge_status: partial_only` when both a PQC-capable gateway and a legacy backend are
directly reachable on the same /24 subnet. QUIRK uses a proximity heuristic to detect
this condition: a `partial_only` assignment means both a PQC-capable device (with
`pqc_status: partial` or `supported`) and a legacy device (with `pqc_status:
unsupported`, `vendor-silent`, or `unknown`) appear within the same /24 subnet — a
proximity heuristic, not confirmed traffic-flow analysis. This is the answer to the
"how did you determine this?" question during client review.

**`upstream_mitigated` — SNMP-confirmed bridge evidence (Phase 140).** As of Phase 140,
`upstream_mitigated` is a reachable, evidence-gated status, not a reserved placeholder. It
is assigned when the sensor collects direct SNMP evidence from the PQC-capable gateway
itself: a bounded, credential-scrubbed walk of the gateway's `ipNetToMediaTable` (ARP
table, OID `1.3.6.1.2.1.4.22.1.2`) that lists the legacy backend's IP address. This is a
network-path signal, not active traffic tracing or packet-level flow confirmation — QUIRK
still does not perform active path verification (e.g. traceroute-style probing or traffic
inspection) to confirm data actually crosses the gateway.

The confirmation probe is **targeted, not exhaustive** (D-03): it only runs against
devices the sensor's own scan batch has already pre-flagged as a `partial_only` gateway
candidate (a PQC-capable device sharing a /24 with a legacy backend in the same batch) —
it does not walk the ARP table of every SNMP-enabled device on every scan. It reuses the
same SNMPv3 USM transport introduced in Phase 139 (`§9.1.1` fallback ladder) when v3
credentials are configured for that host, falling back to v2c otherwise. Each walk is
bounded by both an overall wall-clock timeout and a hard cap on the number of ARP entries
collected, so a large or adversarial ARP table cannot turn the probe into a denial-of-service
vector. If the walk returns no entries, or the evidence doesn't list the legacy backend's
IP, the pair silently stays `partial_only` — QUIRK never promotes on subnet co-presence
alone, and never fails a scan because evidence wasn't collected.

Every device carrying SNMP-derived evidence gets a per-device audit trail: the raw
(IP, MAC) facts observed on the gateway's ARP table are stored (never the community string
or SNMPv3 passphrase) alongside a timestamp of when the evidence was collected, so an
operator can trace exactly what evidence justified the `upstream_mitigated` promotion.

**Action.** Both `partial_only` and `upstream_mitigated` findings do **not** reduce the
device's remediation requirement. The device still needs replacement or firmware upgrade
per its CNSA tier (see §9.2 above). The bridge annotation — at either status — is advisory
context about network topology; it is not a mitigation credit and should not be presented
to a client as one. `upstream_mitigated` is a stronger signal than `partial_only`, but it
still carries a mandatory caveat on every rendered surface: "Based on SNMP-derived
network-path evidence; not independently confirmed by traffic inspection." See
`docs/report-interpretation.md` §10.5 for the full rendering/badge contract across HTML,
PDF, DOCX, and the dashboard `/hardware` tab.

---

#### 9.4 OT/ICS Fingerprinting (Modbus + BACnet, Phase 141)

> ## ⚠️ Risk Warning — Read Before Enabling
>
> **OT/ICS scanning is a materially different risk class than SNMP/SSH/HTTP hardware
> fingerprinting.** Industrial control gear — PLCs, RTUs, building-automation
> controllers — has a well-documented, industry-wide history of crashing, hanging, or
> otherwise misbehaving in response to even benign, read-only network queries. This is
> not a theoretical concern; it is the reason OT/ICS environments are conventionally
> scanned with far more caution than IT networks, if at all.
>
> **Obtain written authorization from the OT/ICS system owner before enabling
> `--enable-modbus` or `--enable-bacnet` against any production OT network.** QUIRK's
> read-only-only design and one-strike circuit breaker (below) reduce — but do not
> eliminate — this risk. Treat OT/ICS scanning as you would any other engagement
> requiring explicit, scoped, written client authorization, distinct from your general
> IT-network scanning authorization.

**What QUIRK probes.** Two independently-flagged, off-by-default protocols:

| Flag | Protocol | Port | What is sent |
|------|----------|------|---------------|
| `--enable-modbus` | Modbus/TCP | 502 (must be observed open) | A single FC 43/14 Read Device Identification request (Basic category — vendor/model/firmware strings only) |
| `--enable-bacnet` | BACnet/IP | 47808/UDP | A single directed-unicast Who-Is, followed by ReadProperty(model-name) and ReadProperty(firmware-revision) on the responding Device object |

Both flags default to `false` and must be explicitly set — QUIRK never probes Modbus or
BACnet unless the operator opts in. Modbus additionally requires port 502 to already be
observed open on the target (from the scan's own port-discovery phase) before the probe
fires at all; BACnet's single Who-Is/I-Am round trip is itself the confirmation signal
for this UDP-only protocol (there is no TCP-equivalent "confirmed open port" check for
UDP).

**Safety model.**

- **Read-only only.** Neither probe ever issues a write function/service code. Modbus
  sends only FC 43/14 (Read Device Identification); BACnet sends only Who-Is/I-Am
  discovery plus ReadProperty — no WriteProperty, no broadcast beyond the single
  directed-unicast Who-Is.
- **Single in-flight per host.** QUIRK never has more than one OT/ICS probe outstanding
  against a given host at a time.
- **One-strike circuit breaker.** Any anomalous response — timeout, malformed frame,
  connection reset, or exception — immediately aborts further OT/ICS probing of that host
  for the rest of the scan. There is no retry and no backoff, deliberately stricter than
  QUIRK's standard scan retry policy elsewhere.
- **Short, dedicated timeout.** Both probes use a conservative default timeout (2s),
  shorter than QUIRK's general scan timeout, to minimize the time spent holding a
  connection open against fragile embedded devices.

**Enable the flags:**

```bash
python run_scan.py --target 10.0.5.0/24 --enable-modbus --enable-bacnet
```

**Result labeling.** Every OT/ICS probe attempt resolves to one of five states, shown
distinctly in reports and the dashboard (never collapsed into a generic "scanned"/"not
scanned" binary):

| State | Meaning |
|-------|---------|
| Identified (Modbus / BACnet badge) | Vendor/model/firmware successfully read |
| No response | Host did not respond within the timeout |
| No match | A response was received but carried no usable vendor identity |
| **Probe aborted** | The one-strike circuit breaker fired — a real anomalous response, not "nothing happened" |
| Not attempted (em dash) | The flag was off, or (Modbus only) port 502 was never observed open |

The **"Probe aborted" state is operationally significant** — it tells the consultant the
device may be fragile or misbehaving and is worth a closer, more careful manual look,
rather than being silently indistinguishable from "no response." See
`docs/report-interpretation.md` for the full badge/column contract across the dashboard
and HTML/PDF/DOCX reports.

**Advisory-only.** Like all hardware fingerprinting signals (§9.1–§9.3), Modbus/BACnet
findings never affect the quantum-readiness score — they appear only in the advisory
hardware section of the report.

**Validate against the chaos lab.** `PROFILE_ARGS="--profile otics" ./lab.sh up` starts
two deliberately fragile Modbus/BACnet simulators that empirically exercise the safety
model above — see `docs/chaos-lab.md` and
`quantum-chaos-enterprise-lab/expected_results_otics.md`.

#### 9.5 Firmware CVE Correlation (Phase 142)

QUIRK correlates each fingerprinted device's `(vendor, model, firmware)` triple against a
small, curated, NVD-cited local CVE catalog (`quirk/scanner/hw_cve.py::CVE_TABLE`) — never a
live NVD API call, so correlation works fully offline and cannot be used to fingerprint the
scanning host to an external service. This is the fourth advisory-only hardware signal after
SNMP (§9.1), CNSA 2.0 tiers (§9.2), and Modbus/BACnet (§9.4).

**`quirk cve status` — catalog freshness.** Mirrors `quirk qramm status`/`quirk compliance
status` exactly:

```bash
quirk cve status
quirk cve status --format json
```

Reports the CVE snapshot's `last_verified` date, days elapsed, days remaining before the
30-day staleness threshold, and a FRESH/STALE verdict. Exit code `0` when fresh, `1` when
stale — the same 0/1 convention used by `quirk qramm status` (§7) so CI and pre-engagement
scripts can gate on it. Like the QRAMM and compliance catalogs, `QUIRK_CI_STALENESS_OVERRIDE_DATE`
overrides "today" for staleness-gate testing; a malformed override value is logged as a warning
and ignored, falling back to the real system date rather than crashing the command.

**The CVE advisory scanner signal.** During report/dashboard generation, QUIRK calls
`correlate_device(vendor, model, firmware)` for every device with a known (non-"Unknown")
vendor. Firmware comes from whatever protocol already fingerprinted the device (Modbus/BACnet
firmware strings preferred, SNMP/SSH/HTTP vendor+model otherwise). Two confidence levels:

- **high confidence** — the device's parsed firmware version falls inside a CVE entry's
  documented affected range (an NVD "prior to X" boundary, exclusive `<`).
- **medium confidence** — only a vendor+model match exists (the curated entry has no
  version boundary, or the device's firmware string could not be parsed); QUIRK does not
  guess whether the specific firmware is actually affected.

**Firmware CVE matches are advisory-only — never a severity finding, and never a score or
remediation-tier input.** This is a hard architectural boundary (CVE-01/CVE-04): the CVE
correlation module imports nothing from `intelligence/scoring.py` or `hardware_tier.py`, and
a dedicated regression test (`tests/test_cve_score_guard.py`) enforces this in CI. Operators
should treat CVE matches as "worth investigating," not as a scored risk the readiness score
already accounts for.

**BACnet vendor-name resolution (Phase 147, decision D-147-02-A).** BACnet's raw Who-Is/I-Am
probe returns only a numeric ASHRAE vendor ID and a raw model string — neither can match the
CVE catalog's `(vendor_name, product_family)` keys on its own. As of Phase 147,
`quirk/scanner/bacnet_vendors.py` — a curated-catalog + staleness-gate module mirroring
`hw_cve.py`'s own shape, on a **365-day cadence** (`quirk cve status`'s 30-day cadence does
not apply to this table; ASHRAE vendor-ID assignments are append-only/stable) — resolves the
numeric vendor ID and raw model to real vendor/product-family names *before* `correlate_device()`
is called. This is what makes the curated `("Johnson Controls", "Facility Explorer")` CVE
entry reachable for a real BACnet FX16 fingerprint. Coverage is intentionally curated, not
exhaustive: an unrecognized vendor ID displays the raw numeric value exactly as before this
phase, with no regression and no crash. See `docs/report-interpretation.md` §10.8 for the
consultant-facing rendering contract.

See `docs/report-interpretation.md` §10.7 for the report/dashboard rendering contract, and
`docs/configuration.md` for the 30-day staleness cadence and re-verification procedure.

---

#### 9.6 Device Re-Identification Fields (Phase 154)

As of Phase 154, every fingerprinted `HardwareDevice` row carries three new per-device fields
that improve re-identification across scans and honesty about probe outcomes. None of these
are rendered as report or dashboard columns yet (deferred to a later release) — they are
scanner-internal fields today, documented here so operators understand the underlying data
model and the retention/last-known-good behavior it drives.

- **`ssh_host_key_fingerprint`** — the SHA256 SSH host-key fingerprint QUIRK's existing
  `ssh-audit` run already captures for the device. Because a host key is tied to the device
  itself (not its current IP), this fingerprint is the stable secondary identity key that
  survives a DHCP lease renewal or a re-IP — something a `host:port` match alone cannot do.

- **`match_confidence`** — `high` when a `ssh_host_key_fingerprint` was captured for the
  device, `low` when the device could only be matched on `host:port`. `low` covers three
  distinct cases operators should be aware of: HTTP-only devices, SNMP-only devices, and —
  importantly — **SSH-reachable devices scanned from a host that does not have `ssh-audit`
  installed**. Operators who want `high`-confidence coverage across their SSH-reachable
  hardware should install `ssh-audit` on the scanning host (see §1).

- **`probe_status`** — `success` when the fingerprinting probe got any response at all,
  including an honest `vendor="Unknown"` result (an unrecognized device that still answered
  is a successful probe, not a failure). `failed` means the probe errored, timed out, or
  nothing on the device answered at all.

**`match_confidence` is not the same field as the pre-existing `confidence` column.**
`confidence` (used elsewhere in hardware fingerprinting, e.g. §9.5's CVE correlation) describes
confidence in a *probe result* — how sure QUIRK is about a parsed vendor/model/firmware value.
`match_confidence` describes confidence in *cross-scan device identity* — how sure QUIRK is
that two rows scanned at different times represent the same physical device. A device can have
high result confidence (a cleanly parsed vendor/model) and low match confidence (no SSH host
key to re-identify it by), or vice versa; the two fields are independent.

See `docs/report-interpretation.md` §10.9 for how `probe_status` drives which row is shown as
a device's current state, and `docs/configuration.md` for the retention window
(`hardware_history_retention_days`) that bounds how long old probe rows are kept.

**Tuning `hardware_drift_event_retention_days` (Phase 157, HWLC-16).** A separate retention
knob, `scan.hardware_drift_event_retention_days` (default `365`), bounds the age of rows in the
`hardware_drift_events` table described in §9.7 below — see `docs/configuration.md` for its
full mechanism.

- **Raise it** on long engagements where a client wants multi-year drift history for
  year-over-year lifecycle comparison — there is no hard ceiling.
- **Lower it** if disk pressure on a long-running console instance becomes a concern; a smaller
  window keeps the `hardware_drift_events` table smaller.
- **Lowering it deletes history irreversibly on the next scan.** The purge is a hard delete, not
  an archive — once a drift event ages past the configured window and a scan runs, that row is
  gone. Lower the value only when the older history is genuinely no longer needed.
- **No separate command or schedule.** The purge runs automatically as part of every scan's
  normal completion — there is no `quirk hardware purge` equivalent for drift events and no cron
  job to configure.

---

#### 9.7 Hardware EOL/EOS Catalog + Lifecycle Drift Events (Phase 155)

As of Phase 155, QUIRK tracks two additional advisory-only hardware lifecycle signals on top
of the fingerprinting/tier/CVE foundation from §9.1–§9.6: a curated vendor end-of-life catalog,
and cross-scan drift events derived by reconciling a device's fingerprint history.

**Hardware EOL/EOS catalog.** `quirk/scanner/hardware_eol.py::EOL_TABLE` maps each
`(vendor, model)` pair to a curated end-of-life / end-of-support date pair, mirroring the
existing curated-catalog + staleness-gate pattern used by `hw_cve.py` (§9.5),
`bacnet_vendors.py` (§9.5), `quirk/compliance/__init__.py`, and `quirk/qramm/model_meta.py`.
Unlike CVE disclosures — which are continuously published and gated on a 30-day cadence — vendor
EOL/EOS announcements are infrequent, pre-scheduled events published via dedicated lifecycle
bulletins months or years in advance. The EOL catalog is therefore gated on a **365-day**
cadence (`STALENESS_THRESHOLD_DAYS = 365` in `hardware_eol.py`), the same cadence used for the
compliance mappings and the BACnet vendor catalog. CI enforces this via
`tests/test_eol_staleness.py`, which fails once the catalog's `last_verified` date is more than
365 days old.

When CI (or a local `pytest` run) reports the EOL catalog stale, follow the same 3-step
re-verification procedure documented in `CLAUDE.md`'s Staleness Review Cadence section:

1. Re-verify each `EOL_TABLE` entry against its `source_url` — confirm the published EOL/EOS
   dates have not changed and are still cited to a live vendor or aggregator page.
2. Bump `EOL_TABLE_META["last_verified"]` in `quirk/scanner/hardware_eol.py` to today's ISO date.
3. Commit with `chore: re-verify hardware_eol catalog (YYYY-MM-DD)`.

**What EOL data changes about a scan.** As of Phase 155, `HardwareDevice.eol_date` is populated
from this catalog automatically during fingerprinting via `apply_eol_date()`. Most fingerprint
paths (SSH banner, HTTP management, SNMP, Modbus, BACnet) converge on a single call site inside
`fingerprint_one()`; the standalone SNMP-only bulk-discovery sweep in `run_scan.py` builds its own
`HardwareDevice` rows outside that waterfall and calls `apply_eol_date()` separately at its own
construction site, so every code path that creates a device row populates `eol_date` — not just
the ones routed through `fingerprint_one()`. This interacts with the pre-existing (Phase
128) CNSA 2.0 tier-assignment rule in `hardware_tier.py::assign_tier()`: a device whose EOL date
falls before 2030-01-01 is assigned **Tier N/A**, regardless of its PQC support status. Because
the EOL catalog was dormant before this phase, populating a real EOL date can legitimately move
a previously Tier 1/2/3 device to Tier N/A on its very next scan. **This is intended behavior,
not a regression** — a device whose vendor has already end-of-lifed it is not a candidate for
PQC remediation planning in the same sense as a supported device, so Tier N/A correctly routes
it toward replacement guidance instead. Operators who see a device's tier shift to Tier N/A after
upgrading to a build that includes this catalog should expect it, not file a bug.

**Lifecycle drift events.** Every hardware-device commit during a scan now triggers
`reconcile_device_history()` (`quirk/scanner/hardware_drift.py`), which compares a device's most
recent successful probe rows against its scan history and — when a change is corroborated —
persists a row to the `hardware_drift_events` table. Four event types are tracked
(`EVENT_TYPES` in `hardware_drift.py`):

- **`tier_crossing`** — the device's stored CNSA 2.0 remediation tier changed between scans
  (for example Tier 2 → Tier 1, or a shift to/from Tier N/A driven by the EOL catalog above).
- **`upstream_mitigated_change`** — the device's SNMP-confirmed crypto-bridge evidence state
  changed (see §9.3's `partial_only` → `upstream_mitigated` promotion).
- **`cve_delta`** — the set of correlated firmware CVEs (§9.5) changed between scans, e.g. a
  catalog update surfaced a newly-applicable CVE for the device's fingerprinted firmware.
- **`eol_state_change`** — the device's EOL classification (`"approaching"` — within 12 months
  of its EOL date — or `"passed"` — already past it) changed between scans.

**Confirmation window.** Tier, bridge-evidence, and EOL-state changes are gated by a **2-of-3
confirmation window**: a new value must be corroborated by at least 2 of the device's last 3
successful probes before it is recorded as a drift event. A single dropped packet or transient
network hiccup that produces one anomalous reading therefore does **not** generate a false drift
event — only a value that holds across the majority of the recent window does. (CVE-delta events
are the one exception: they are computed as a direct two-row diff, not N-of-M gated, since a CVE
catalog update should surface immediately rather than wait for confirmation.)

Drift events accumulate in the `hardware_drift_events` table and are **deduplicated per
`(host, port, event_type)`** — a stable value that holds across many consecutive scans is
recorded once, not once per scan. Like every other signal in this section, drift events are
**advisory-only**: `hardware_drift.py` is never imported by `quirk/intelligence/scoring.py`, and
a dedicated regression test (`tests/test_cve_score_guard.py`) enforces that boundary in CI. A
scan's readiness score is identical whether or not drift events were recorded during it.

Dashboard and report surfacing of `hardware_drift_events` rows shipped in Phase 156 — see §9.8
below and `docs/report-interpretation.md` §10.10.

#### 9.8 Recent Lifecycle Changes Dashboard Section (Phase 156)

As of Phase 156, the `/hardware` and `/compare` dashboard pages render a "Recent Lifecycle
Changes" section surfacing the `hardware_drift_events` rows persisted by §9.7's reconciliation
engine. It is a structurally and visually distinct advisory card — separate teal-accented chrome,
never reusing the tier/PQC/confidence/SNMP badge palette — so it reads as clearly different from
the scored-finding chrome elsewhere on the page.

**What appears.** Each row shows: an event-type icon and label, the device's identity
(`host:port` plus vendor/model), the literal `{old_value} → {new_value}` transition, a direction
indicator, and the detection date. The most recent events render inline; older ones are tucked
behind a collapsible "N historical events" disclosure so the section doesn't dominate the page on
a long-running device.

**The four event types** are the same ones recorded by §9.7's reconciliation engine, with these
display labels: Tier crossing, Bridge mitigation change, CVE correlation change, EOL/EOS state
change.

**Direction vocabulary.** Each event carries one of three direction labels — **Improved**,
**Worsened**, or **Changed** — derived from the CNSA 2.0 tier ordering (§9.2), not from a
severity ranking. "Changed" (backed by the internal `neutral` value) covers event types with no
inherent better/worse direction, such as a CVE-delta or an EOL-state change — those are simply
different, not improved or worsened.

**Two empty states, and how to tell them apart.** The section distinguishes "no prior scan
exists yet" (a device's very first scan, by construction, has no lifecycle history to show) from
"a prior scan exists but nothing changed" (the device has been re-scanned and its lifecycle
state has been stable). Both render as advisory copy in the same card location, with different
wording — never a blank space that could read as a missing feature.

**Where it appears.** On `/hardware`, the section renders as a sibling block after the device
table, visible even when the device table itself shows its own empty state. On `/compare`, the
same section renders sourced from the compared scan pair's drift events, after the existing
comparison tabs.

**Advisory-only, no score contribution.** Like every other signal in this section, drift events
shown here carry no severity and make no contribution to the quantum-readiness score — see
`docs/report-interpretation.md` §10.10 for the verbatim advisory caption and how it renders
across the HTML, PDF, and DOCX report formats.

#### 9.9 Check-in Scan Mode (`--check-in`, Phase 159)

As of Phase 159 (HWLC-13), `--check-in` is a lightweight, opt-in re-probe of the hardware fleet
QU.I.R.K. already knows about. It exists for the common between-engagements case: a consultant
wants to see whether anything on a previously fingerprinted fleet has drifted, without paying the
cost of a full scan.

```bash
python run_scan.py --config config.yaml --check-in
```

**`--check-in` is a bare boolean opt-in on `run_scan.py`, not a `--profile` value.** It cannot be
combined with `--profile`'s `quick`/`standard`/`deep` choices — it is a separate short-circuit
that fires immediately after database initialization, before any profile-driven scan logic runs.

**What it does and does not do:**

- **Targets** are the latest successful `HardwareDevice` row per `(host, port)` — the same
  last-known-good projection described in §9.6 — never a fresh network sweep.
- **No discovery.** Network/CIDR discovery, nmap liveness pre-passing, and target expansion are
  all skipped entirely.
- **No non-hardware scanner phases.** TLS, SSH, JWT/API, container, source-code, and cloud KMS
  scanning are all skipped. Only the hardware-fingerprinting probe family is re-run.
- **Only the device's own probe family is re-run.** Each device's stored `fingerprint_method`
  (`ssh_banner`, `http_mgmt`, `snmp`, `modbus`, or `bacnet`) determines which single probe
  re-fires — a device originally fingerprinted via SSH is re-probed via SSH only, never promoted
  to a different probe family.
- **`modbus`/`bacnet` devices are skipped** when `connectors.enable_modbus` /
  `connectors.enable_bacnet` are off, exactly as they are during a normal scan — a check-in never
  force-enables OT/ICS probing.
- **An empty fleet is a clean no-op.** If no `HardwareDevice` rows exist yet (no prior scan has
  ever fingerprinted a device), `--check-in` prints an operator message and exits `0` with **zero
  database writes** — it never errors out.
- **Persists only `HardwareDevice` and `hardware_drift_events` rows**, through the same
  `persist_and_reconcile()` chokepoint (§9.7) used by a full scan. Every row it writes carries
  **`is_partial_scan=True`**.
- **Never produces a readiness score or a full report.** A check-in run does not invoke the
  scoring engine, the HTML/PDF/DOCX report writer, or the CLI/markdown executive summary. Run a
  full scan (no `--check-in`) to get an updated readiness score.

**Example CLI summary** (printed to the log, advisory-only, no return value):

```
[Check-in re-probe - partial scan, not scored]
  Devices re-probed: 4 | Success: 3 | Failed: 1 | Drift events: 2
  Not scored - run a full scan for an updated readiness score.
```

**Where check-in-sourced data shows up afterward.** Devices and drift events written by a
check-in carry `is_partial_scan=True`. They stay visible everywhere the equivalent full-scan data
would be — the `/hardware` and `/compare` dashboard pages, `GET /api/hardware/drift`, and
`CompareResponse.hardware_drift` — badged rather than filtered out (see
`docs/report-interpretation.md`'s check-in section for the exact reader-facing wording and the
`/trends`/`/compare` readiness-score exclusion). A check-in run is never selectable as a scored
scan on `/api/scans` or `/api/trends`.

**Putting a check-in on a schedule (Phase 162, HWLC-20).** Rather than remembering to run
`--check-in` by hand, register it with the scheduler:

```bash
quirk schedule add --name nightly-checkin --cron "0 2 * * *" --check-in
quirk scheduler run      # the long-running dispatch loop
```

- **No `--target` is needed or accepted as meaningful.** A check-in re-probes the fleet already
  recorded in the database (`latest_successful_hardware_devices()`), so there is nothing to aim
  it at. The stored target reads `(known fleet)` in `quirk schedule list` and on the dashboard.
- **No `--profile` applies.** The dispatcher emits `run_scan --check-in` and deliberately no
  `--profile`, because check-in mode short-circuits before any profile is read. A dispatched
  command that named a profile would misrepresent what actually runs.
- **A scheduled check-in is the same code path as a manual one.** There is no second
  implementation, so every HWLC-13 guarantee above holds identically: `is_partial_scan=True`,
  the partial-scan banner, no readiness score, and exclusion from `/trends` and `/compare` as a
  scored session.
- **The dashboard marks them.** `/schedules` shows a `check-in` chip beside the schedule name so
  a lightweight re-probe is distinguishable at a glance from a scored profile scan.

Enable, disable and remove them exactly like any other schedule
(`quirk schedule enable|disable|remove <name>`).

#### 9.10 Catalog-Level PQC Vendor Trend Tracking (Phase 160, HWLC-17)

As of Phase 160, QUIRK tracks **vendor-scoped** PQC-status change over time, in addition to
the existing per-device drift tracked in `hardware_drift_events` (§9.7).

**What a vendor PQC trend event is.** A confirmed, fleet-wide change in a vendor's
catalog-assigned `pqc_status` (e.g. `unsupported` → `partial`), recorded as a discrete row in
the `vendor_pqc_trend_events` table. Each row carries the vendor, the event type
(`pqc_status_change`), the old and new `pqc_status` values, and the timestamps the change was
detected and confirmed.

**How it differs from per-device drift.** `hardware_drift_events` (§9.7) is per-`(host, port)`
— it tells you a specific device changed. `vendor_pqc_trend_events` is vendor-scoped, has no
`host`/`port` column at all (cross-device, cross-host). The two tables are structurally distinct
and serve different questions: "did this device change?" vs. "did this vendor's catalog posture
change?"

**Confirmation gate.** Like every other lifecycle signal in QUIRK, a vendor trend event only
fires after N-of-M confirmation (N=2 of M=3, the same defaults used everywhere else in QUIRK) —
but the window here samples the **3 most-recently-scanned distinct devices of that vendor**, not
repeated scans of one device and not the vendor's entire fleet. This means a single noisy or
repeatedly-rescanned host cannot, by itself, trigger a vendor-level event, but it also means the
signal reflects a recent sample rather than an exhaustive fleet-wide census — a vendor with many
active devices is judged on its 3 most-recently-seen ones. It also means a vendor's first-ever
observed device never produces an event — there is nothing to compare it against yet.

**Querying it.** `GET /api/hardware/vendor-trends` returns the bounded, newest-first list:

```bash
curl -H "Authorization: Bearer $QUIRK_API_TOKEN" \
  "http://localhost:8000/api/hardware/vendor-trends?limit=50"
```

- Authenticated the same way as every other dashboard API route (§2.4) — no separate
  credential.
- `limit` accepts 1–200 (default 50); a `truncated: true` flag in the response body indicates
  more rows exist than were returned.
- Each event exposes `vendor`, `event_type`, `old_value`, `new_value`, `detected_at`, and
  `confirmed_at` — no host/port, no score, no numeric field.

**Advisory-only, no score contribution.** Like `hardware_drift_events`, vendor PQC trend
events never affect the readiness score — `quirk/scanner/hardware_drift.py` and
`quirk/models_util.py` are never imported by `quirk/intelligence/scoring.py`, machine-enforced
by `tests/test_cve_score_guard.py`.

**Now rendered in every report format.** As of Phase 161 (HWLC-19) vendor PQC trend events are
rendered in the HTML, DOCX and CLI technical reports and on the dashboard `/hardware` page — see
§9.11 below. The endpoint above remains available for direct queries.

---

#### 9.11 Vendor PQC Status Trends on the Dashboard (Phase 161, HWLC-19)

The `/hardware` page carries a **Vendor PQC Status Trends** section immediately below Recent
Lifecycle Changes (§9.8). It renders the same `vendor_pqc_trend_events` rows the §9.10 endpoint
serves.

- **Advisory-only.** The section uses the non-severity advisory chrome — no red/amber/green
  severity colouring and no alert chips — because vendor trends never affect the readiness score.
  The caption "Advisory — vendor PQC status trends do not affect the readiness score." is always
  visible, never collapsed behind a disclosure.
- **Vendor-scoped.** Rows describe a vendor's fleet-wide posture, not a device, so there is no
  host, port or severity column. See `docs/report-interpretation.md` §10.13 for the column
  meanings and how to explain them to a client.
- **Independent of drift.** The section renders whether or not this scan produced device drift
  events, and shows a plain empty-state card — not a blank area or a spinner — when there are no
  trend events to show.
- **Truncation.** The API returns up to 50 events by default. When more exist, the section renders
  a plain-text note rather than pagination controls.

---

#### 9.12 Hardware Lifecycle Notifications (Phase 161, HWLC-14)

QUIRK can notify you when a scan detects that a device's lifecycle posture got *worse*. Enable it
with the `notify_on_hardware_lifecycle` key in your config's `notifications:` block — see
`docs/configuration.md`. It is **off by default**.

**What triggers a notification**

Exactly two things:

| Trigger | Notifies? |
|---|---|
| A **worsening** remediation-tier crossing (e.g. Tier 1 → Tier 2) | Yes |
| Any **EOL/EOS state change** | Yes |
| An **improving** tier crossing (e.g. Tier 2 → Tier 1) | **No — deliberately** |
| A CVE correlation change or bridge-mitigation change | No |
| A vendor PQC trend event (§9.11) | No — catalog-level, not device-level |

Improving crossings are deliberately silent. The feature exists to surface degradation that needs
action; paging an operator because a device got *better* trains them to ignore the channel.

**Where it delivers**

Email and webhook only — Slack is not a destination for lifecycle alerts. Delivery reuses the
existing `email:` and `webhook:` configuration and credential model; enabling the key without
either configured changes nothing.

**Audit trail**

Every delivery attempt — success or failure — is recorded in the `integration_deliveries` table
with a composite identifier of the form `{host}:{port}:{event_type}:{event_id}`, so a specific
alert can be traced back to the exact drift event that produced it.

**Failure isolation**

Notification delivery is advisory-only and can never abort a scan. The dispatch hook sits inside
`persist_and_reconcile()` and is wrapped so that a failing SMTP server, an unreachable webhook, a
misconfigured credential, or an entirely uninstalled notification extra is logged and audited but
leaves the scan, the sensor push, or the air-gap import completely unaffected. If you enable
notifications and see nothing arrive, check the `integration_deliveries` rows first — the attempt
will be recorded there with its error summary even when delivery failed.

---

### 10. Discovery Liveness Pre-Pass

As of Phase 145 (DISC-03), every nmap-discovery batch runs a cheap TCP-based liveness
pre-pass before its full port sweep. This shrinks scan time on large, sparse ranges by
skipping the expensive `-sT` sweep against hosts that never answer.

#### 10.1 What it does

Before `run_nmap_discovery()` sweeps a batch, QUIRK runs `run_nmap_liveness_check()`
against that same batch: an `nmap -sn -PS<ports>` probe (host discovery only — `-sn` —
using a TCP SYN ping on the given ports, `-PS`, with `-n` to skip DNS resolution). Hosts
that respond are swept normally; hosts that do not respond are excluded from the sweep
and recorded as `liveness_skip` rows (see §10.4 and `docs/report-interpretation.md`).

This is **TCP-based, not ICMP-based** — `-PS` sends a TCP packet with the SYN flag to
the probed ports rather than an ICMP echo request. That matters because segmented
enterprise networks routinely filter ICMP but still route TCP, so a TCP-based liveness
probe correctly detects hosts that an ICMP `ping`-style check would wrongly report as
dead.

#### 10.2 Which ports it probes (D-03)

The pre-pass reuses the same port list the sweep itself will use — a host that is
"live" only means it answered on at least one of those ports, which is exactly what the
sweep needs. For the `top1000` and `all` port scopes (see §3), `-PS` has no
`--top-ports` equivalent, so the pre-pass falls back to the full `-PS-` (1–65535) range
instead. A superset can never wrongly mark a host non-responsive, so this fallback is a
safe, reliability-first default (D-03) rather than a narrower approximation.

#### 10.3 Privilege fallback

nmap's SYN-ping probe (`-PS`) normally requires raw-socket privileges. When those
privileges are not available, nmap silently substitutes a TCP connect probe for the SYN
probe — and its XML output is byte-identical either way, so there is no way to detect
the substitution from the probe's own results.

QUIRK checks `os.geteuid()` exactly once per scan (via `_is_privileged()` in
`run_scan.py`) and, whenever the process is **not** confirmed to be running as root —
including on platforms that provide no way to check at all, such as the Windows sensor
build, where `os.geteuid` does not exist — it treats that as "not privileged" and
discloses the possible downgrade two ways:

- A logger message: *"liveness pre-pass may have silently degraded from a SYN probe to
  a TCP connect probe (no raw-socket privileges detected) — results remain valid but the
  pre-pass will run slower than intended."*
- A single persisted `privilege_fallback` advisory row in the scan artifact (one per
  scan, not one per batch — see §10.4).

**Results remain valid either way** — a TCP connect probe still correctly determines
host liveness, it is just slower than a raw SYN probe. Running the scan as root (or via
`sudo`) removes the advisory entirely, because `_is_privileged()` then returns `True`
and the fallback-disclosure call never fires.

#### 10.4 What happens on failure

If the pre-pass itself fails (nmap errors, times out, or is missing) for a batch, QUIRK
does not lose that batch's hosts: it logs the failure and sweeps the entire batch
unfiltered, exactly as if no pre-pass had run. A batch where every host is
non-responsive short-circuits entirely — the sweep subprocess is never spawned for a
fully-dead batch.

#### 10.5 Where to look afterward

Every liveness-skipped host produces its own `CryptoEndpoint` row in the scan artifact
with `scan_error_category="liveness_skip"` and the real host address, so a skipped host
is never silently dropped from the record. See `docs/report-interpretation.md` for how
to interpret `liveness_skip` and `privilege_fallback` rows in a delivered report.

> **Operator note:** the total number of undetermined (skipped) hosts is now surfaced
> as an aggregate "Hosts undetermined" count in every report surface — see
> `docs/report-interpretation.md` §13.

### 11. Chunked Discovery Progress and Per-Batch Scaling

As of Phase 146 (DISC-04/DISC-05/DISC-06), the chunked nmap discovery batch loop
introduced in Phase 144 reports its own progress in real time and scales each batch's
nmap subprocess timeout and timing aggressiveness to that batch's own size.

#### 11.1 Where batch progress appears (DISC-04)

- **Dashboard:** the scan-job page renders a muted sub-line beneath the stage progress
  bar — "Batch N of M — X hosts checked" — while the current stage is `discovery`. It
  appears only after the first batch completes and disappears once discovery finishes.
  This is driven entirely by the existing job-status poll; no separate endpoint or
  websocket is used.
- **CLI:** on `--discovery nmap` runs, a line prints to stdout once per completed batch:

  ```
  Discovery: batch N/M (X hosts checked)
  ```

  This line is suppressed when `--quiet` is set. Both the dashboard fields and the CLI
  line are written from the exact same batch-loop bookkeeping in `run_scan.py`, so the
  numbers always agree.

#### 11.2 Per-batch timeout scaling (DISC-05)

Each nmap subprocess call inside the batch loop (both the Phase 145 liveness pre-pass
and the full discovery sweep) now receives a timeout computed per batch instead of a
single fixed value for the whole scan:

```
timeout_seconds = min(300, 30 + 0.26 * batch_size)
```

- **Base:** 30 seconds.
- **Per-host scaling:** 0.26 seconds added per host in the batch.
- **Ceiling:** clamped to 300 seconds — the same ceiling the pre-Phase-146 fixed timeout
  used, so no batch can run longer than before. A small batch (e.g. one host) finishes
  its timeout budget in well under a second over the base; a full 1024-host batch stays
  at or below the 300s ceiling.

#### 11.3 Per-batch timing template (DISC-05/DISC-06/DISC-07)

Alongside the timeout, each batch also selects an nmap `-T` timing template based on its
own size: `-T4` (aggressive) for batches at or below 256 hosts, `-T3` (normal) for
batches larger than that. In practice this only changes nmap's RTT-probe timing —
`_default_nmap_args` already hardcodes `--max-retries 1`, `--host-timeout 10s`, and
`--max-parallelism 100`, and per verified nmap documentation those explicit flags
override the `-T` template's own defaults for those specific values regardless of argv
order.

#### 11.4 `--nmap-timeout` no longer governs chunked discovery

The CLI's `--nmap-timeout` flag no longer applies inside the Phase 144 chunked discovery
batch loop — the per-batch formula in §11.2 fully replaces it there. The dashboard's
spawned `run_scan.py` subprocess also no longer passes a static `--nmap-timeout 300`
argument, since that static value could otherwise silently override the per-batch
formula; the 300s ceiling is now enforced entirely by the formula's own clamp. The flag
remains meaningful for any future non-batched discovery code path and its `--help` text
reflects this.

#### 11.5 CLI and dashboard share one discovery implementation (DISC-06)

The dashboard does not run its own separate discovery logic — it spawns the same
`run_scan.py` CLI entry point as a subprocess, so both surfaces execute exactly one
discovery code path. This is locked by a static/AST-based regression test
(`tests/test_cli_dashboard_discovery_parity.py`) asserting a single call site each for
`run_nmap_discovery()` and `run_nmap_liveness_check()`, both lexically inside the Phase
144 batch loop, and confirming `jobs.py` never calls `run_nmap_discovery(` directly.

### 12. OT/ICS Recurring-Scan Safety

Phase 141 (§9.4) introduced Modbus/BACnet fingerprinting with a deliberately narrow safety
model — a single read-only request per probe, a one-strike circuit breaker, and off-by-default
flags. That safety model was designed and validated for a **one-off, operator-initiated scan**.
Phase 156 closes a gap that model didn't cover: what happens when those same flags are wired
into a *recurring*, unattended scheduled scan.

**Why the gate exists.** The Modbus and BACnet scanners were designed for exactly one read-only
request per engagement, run by a human who has obtained authorization and is watching the
outcome. Unbounded, unattended recurring probing against fragile production control systems —
PLCs, RTUs, building-automation controllers — is a real outage risk, not a theoretical one; this
is the same risk class documented in §9.4's risk warning, now compounded by removing the human
from the loop entirely.

**The two conditions a scheduled run must satisfy.** A `quirk scheduler run` dispatch will only
allow Modbus/BACnet probing to reach a device if **both** of these hold:

1. `connectors.enable_recurring_otics: true` is set in the scan config the scheduler dispatches
   with.
2. The schedule's own cron expression's minimum firing gap is at or above the 168-hour
   (7-day) floor — see `docs/configuration.md`'s [OT/ICS Recurring-Scan Cadence
   Floor](#ot-ics-recurring-scan-cadence-floor-v513-phase-156) section for
   exactly how that gap is derived.

If either condition fails, `enable_modbus`/`enable_bacnet` are silently stripped from that run's
generated config and the rest of the scheduled scan proceeds normally — the run is never failed
because of this.

**What an operator sees when creating a sub-floor schedule.** Creating the schedule always
succeeds — it is never rejected for this reason:

- Via `POST /api/schedules`: the response is `201`, with the new schedule's `advisories` array
  containing a message describing the sub-floor cron and the 168-hour floor it falls under.
- Via `quirk schedule add`: the schedule row is created as usual, and a yellow advisory line is
  printed directly beneath the normal "added" confirmation. Exit code stays `0`.

Neither surface returns a `422`/`400` for a sub-floor cron. This is intentional (see
`docs/configuration.md` for why): the scheduler applies one shared scan config to every schedule
it dispatches, so at creation time it cannot know whether OT/ICS will ever actually be enabled
for that schedule.

**Where to look when PLCs stop being fingerprinted.** If Modbus/BACnet devices that used to
appear in scheduled-scan results stop showing up, check the scheduler's log output for a line
matching this shape:

```
OT/ICS probing suppressed for schedule 'nightly-plant-scan' (cron='0 * * * *'): removed keys ('enable_modbus', 'enable_bacnet') — reason: ...
```

The literal text `OT/ICS probing suppressed` always appears, followed by the schedule name, the
exact keys that were stripped from the generated config, and the reason (cadence-floor violation
or the recurring opt-in being off). This line is emitted at INFO level on every suppressed
dispatch — it is the single place to look first when a scheduled scan silently stops covering
OT/ICS devices it used to cover.

### 13. Discovery Batch Resume

As of Phase 163 (DISC-08), a discovery scan interrupted mid-run and resumed via
`--resume-scan-id` skips the individual nmap-discovery batches that already completed
before the interruption, instead of re-probing every batch from zero.

#### 13.1 What changed

Before this phase, resume was stage-granular only: `--resume-scan-id` skipped an
entire completed *stage* (e.g. `discovery`), but if `discovery` itself was interrupted
partway through, the next run re-probed **every** batch in that stage from scratch. At
`_MAX_HOSTS_PER_CIDR = 1024`, a /16 interrupted at batch 60 of 64 previously re-probed
all ~65,000 hosts on resume. It now re-probes only the ~4,000 hosts in the unfinished
batches (batches 61-64).

#### 13.2 How to use it

1. Find the interrupted scan's ID with `--list-resumable`:

   ```bash
   python run_scan.py --config config.yaml --db-path output/quirk.db --list-resumable
   ```

   This prints every scan that has checkpoint rows but never reached a completed
   `reports` stage, newest first, with its last completed stage and age. Rows older
   than 72h are highlighted, but a run stays resumable until its batch cache files
   expire at 720h (see 13.4).

   The **Target** column reflects how the scan was started. For dashboard-dispatched
   `--job-id` runs, it shows the literal target string recorded at dispatch time
   (e.g. `10.0.0.0/24`). For `--targets-file` and other CLI runs — which have no such
   record — it shows a summary derived from the endpoints scanned so far for that run,
   e.g. `10.0.0.1, 10.0.0.2 (+3 more)`, truncated to the first 2 hosts. A run with no
   scanned endpoints yet (interrupted before any stage produced rows) shows
   `(no target recorded)` rather than a blank column.

2. Re-run the identical command with `--resume-scan-id <scan_run_id>` added.

Note that an interrupted scan does **not** print its own `scan_run_id` to the console
— `--list-resumable` is the supported way to recover it. The ID is echoed only on the
resumed run, in the `Resuming scan <id>: N stages complete` line.

`--cache` is not required for batch resume — batch resume does NOT require `--cache`.
Per-batch resume state is written on every run that has a `--db-path` set,
independently of the whole-discovery-stage `--cache` / `--cache-ttl-hours` cache. You
can omit `--cache` entirely and batch-level resume still works.

#### 13.3 Where the state lives

Each completed batch produces two artifacts:

- A `ScanCheckpoint` row with a synthetic stage name `discovery:batch-N` (no new table,
  no schema change — the existing checkpoint mechanism is reused with a structured
  stage string).
- A JSON payload at `{output_dir}/.cache/discovery-batch-{scan_run_id}-{N}.json`
  holding two things: that batch's discovered open-ports list (`ports`), and the
  per-host "undetermined" advisory records produced by its liveness pre-pass
  (`liveness`). Both are restored when the batch is skipped — see 13.4 for why the
  second one matters to your reported coverage.

#### 13.4 Disk usage is proportional to swept host count

Resume state now occupies disk space proportional to the batch count, not a single
file per scan as before. The batch count is `ceil(total_hosts / 1024)`: a /16 (~65,000
hosts) produces roughly 64 batch files; a /12 (~1,048,576 hosts) produces roughly
1,024.

Each batch file holds that batch's open-ports list plus one small advisory record per
non-responsive host — not raw nmap XML/stdout. The advisory records dominate the
footprint on a sparse network, at roughly 190 bytes per non-responsive host: a fully
dark 1024-host batch produces a file of about 190 KB, so a /20 costs well under 1 MB
and a /16 roughly 12 MB in total. Dense networks produce *smaller* files, since a
responsive host generates no advisory record.

Those advisory records are what let a resumed scan report the same coverage as an
uninterrupted one. They are the same "undetermined host" entries that appear in the
scan summary's `Hosts undetermined` count and as `ADVISORY` findings in the report.
Without them cached, a resumed run would silently under-report its own scope by one
batch's worth of hosts for every batch it skipped — the report would look like a
completed smaller scan rather than an interrupted larger one. If you need to reclaim
the space, delete the cache directory rather than individual files (see below); the
cost is a re-probe, never a wrong number.

Batch cache files are read back with a 720-hour (30-day) TTL. After 30 days, a batch
file is treated as expired and ignored on resume — that batch is re-probed instead of
skipped. `{output_dir}/.cache/` can be deleted at any time; the only consequence is
that a subsequent resume re-probes the batches whose cache files were removed. Deleting
it never corrupts or blocks a scan.

#### 13.5 Cache files carry the discovered inventory

The per-batch cache files under `{output_dir}/.cache/` contain the discovered
host/port inventory for their batch **and the address of every non-responsive host in
it** — in effect, a full record of which addresses were swept and which answered. They
live in the same `{output_dir}` that already holds the CBOM, the delivered report, and
the SQLite DB. Apply the same handling
(storage, retention, access control) to `{output_dir}/.cache/` that you already apply
to the rest of the output directory — it is not a separate trust tier.

#### 13.6 Limitation: resume assumes an unchanged target scope

Batch numbering is a pure ordinal over the expanded target list computed at scan
start. Resume assumes the target scope is unchanged since the original scan. If
CIDRs, include-IPs, or `exclude_ips` are edited between the original run and the
resumed run, batch alignment is **undefined** — the resumed scan may restore the
wrong hosts' results under the wrong batch numbers, silently corrupting the inventory
rather than merely re-probing extra hosts.

**Safe procedure:** if you need to change target scope, start a fresh scan rather than
resuming. This is the same assumption the pre-existing stage-level resume already
makes; batch-level resume does not add a new class of risk, but it does make the
existing one more granular.

#### 13.7 Skip/re-probe decision table

| Batch state | Cache file state | Resume behavior |
|---|---|---|
| Completed (checkpoint row exists) | Present and within the 720h TTL | Skipped — no nmap subprocess is spawned for this batch |
| Completed (checkpoint row exists) | Expired (>720h) or deleted | Re-probed — a checkpoint row alone never causes a skip; a live cache hit is also required |
| Failed with a `RuntimeError` | No checkpoint written | Re-attempted on resume; the batch's error endpoint from the failed attempt is still recorded in the scan artifact |
| Completed (checkpoint row exists) | Present, but written before the advisory records were cached | Skipped, and its open ports are restored, but its undetermined-host records are not — that run's reported `Hosts undetermined` will be low by roughly one batch per such file. Start a fresh scan if the coverage figure matters. |

---

### 14. Ticketing Integration

Jira and ServiceNow ticket dispatch (`quirk ticket create`) is configured under
`docs/configuration.md` §"Jira Ticketing" / §"ServiceNow Ticketing" — that is still the reference
for the `ticketing:` config block and CLI usage. This section covers one operator-visible behavior
change from Phase 178.

#### 14.1 One-time ticket re-key (v5.18 / IDENT-01)

Finding fingerprints — the dedup key used to decide "have I already opened a ticket for this" —
are now computed from a **normalized** title (`quirk/ticketing/base.py::compute_fingerprint`,
routed through `quirk.compliance.normalize_finding_title`). Before Phase 178, the fingerprint
hashed the raw title text, and one finding family interpolates a changing value into that title:
`"Certificate expiring in {N} day(s)"`, where `N` counts down every day. That meant a still-open
certificate-expiry finding minted a brand-new fingerprint — and therefore a brand-new Jira issue
or ServiceNow incident — on every single scan, instead of being recognized as the same finding it
was yesterday.

**The only affected family is certificate-expiry findings.** No other finding title changed its
fingerprint-relevant classification in this phase.

**What operators will see on the next `quirk ticket create` run:** any certificate-expiry finding
that already has an open ticket will look "new" exactly once, because its normalized fingerprint
no longer matches the fingerprint stored on the existing ticket. Jira stores the fingerprint as a Jira **label**
on the issue (`labels: [fp]`, matched via `JQL labels = "<fp>"`); ServiceNow stores it in the
incident's **`correlation_id`** field (matched via `sysparm_query=correlation_id=<fp>`). Neither
lookup finds the old-fingerprint record, so exactly ONE duplicate ticket is created per affected
finding. After that single miss, the new fingerprint is stable and dedup works normally on every
subsequent run — this is a one-time event, not a recurring duplication.

No migration or tracker readback is performed against already-issued tickets — reading back
existing Jira/ServiceNow state is explicitly out of scope (see `.planning/REQUIREMENTS.md`). If
you want to avoid seeing the duplicate, close the old certificate-expiry ticket manually before
running `quirk ticket create` again; QUIRK will open a fresh one under the new, stable fingerprint.

**This is not a dedup regression.** Two different vulnerable container-image libraries found at
the same host and port still produce two distinct tickets after this change, exactly as before —
fingerprinting deliberately does NOT collapse findings that differ only in which library or
package they name (T-178-01). Only the day-counting cert-expiry title was made fingerprint-stable;
everything else that already deduplicated correctly continues to do so.

### 15. Remediation Tracking Scope (v5.18+ — Phase 179)

Phase 179 changed what a remediation item *is*. Previously, roadmap items were computed fresh on
every scan from live evidence counters and existed only in memory — nothing was persisted, and
progress could only ever be reported as a boolean (an item is either present in the current
roadmap or it isn't). A remediation item is now a stable, kind-derived ID (e.g.
`plaintext-http-exposure`) with its constituent findings recorded explicitly, per scan, in the
database. That is what makes "6 of 8 verified closed" an expressible fact rather than an
approximation — fixing 1 of 8 affected endpoints no longer reads as "nothing happened," and fixing
the 8th no longer makes the item silently vanish with no closure record.

Three things operators should understand about how this tracking behaves:

- **A per-scan scope signature is recorded**, capturing what the scan actually covered — port
  scope, `--profile`, which optional extras were enabled, whether credentials were supplied, and
  which sensors contributed. Closure comparisons are refused outright when two scans' signatures
  don't match, rather than silently comparing scans that covered different ground. A re-engagement
  run with `--profile quick` cannot be misread as having verified — let alone closed — findings
  that only a deeper prior scan actually covered.
- **Probe health is asserted positively, per protocol family, not inferred from the scan exiting
  cleanly.** A scan can exit 0 while a specific probe (SSH, TLS, JWT, etc.) silently produced no
  usable evidence — this is precisely the failure mode a prior integration defect (TRIAGE-176-03)
  demonstrated for SSH. Health is now derived from whether that family actually produced evidence,
  not from the absence of an error.
- **`not_observed` is a real, persisted third state — distinct from both `open` and `closed`.** An
  item this scan did not see evidence for is recorded as `not_observed`, never inferred as
  `closed`. A report reading "9 closed, 4 open, 12 not observed" is telling you something true and
  useful: those 12 were not verified this scan, one way or the other. It does not mean nothing was
  found there — it means the question wasn't answered this run (a narrower port scope, a disabled
  connector, an unreachable host). Treat `not_observed` as "we did not check," never as "there's
  nothing there."

See `docs/configuration.md` §"Remediation Aliases" for the related `remediation_aliases:` config
key, which lets an operator manually declare that two identities across engagements are the same
asset — the human-in-the-loop mechanism this phase uses instead of automated re-scan matching.

#### Known limitation — sensor-origin findings are excluded from closure tracking

**Closure tracking is scoped to CLI scans.** Findings pushed from a distributed sensor
(`docs/operators-guide.md` §8, Distributed Sensor Deployment) arrive through a different ingestion
path — `quirk/cli/console_cmd.py::_ingest_envelope` — which records `sensor_id` and `segment` on
the resulting `CryptoEndpoint` row but does **not** set `scan_run_id`. The scope signature that
gates closure comparisons is keyed on `scan_run_id`. A row with no `scan_run_id` therefore has no
scope signature and no way to be evaluated for closure.

**What this means in practice:** in a hybrid or fully distributed deployment, sensor-origin
findings will never appear in remediation burndown or closure figures — not because nothing was
found, and not because of a bug, but because sensor pushes were structurally excluded from this
tracking mechanism by design decision (179-CONTEXT.md, "Sensor-Origin Coverage"). If you run a
distributed sensor fleet and expect to see sensor-discovered findings close out over time, you
will not — closure figures will only ever reflect CLI-scanned findings. This is worth knowing
*before* you plan a distributed engagement around burndown reporting, not after you notice the
number never moves.

**CLI-scanned findings are unaffected** — everything described above in this section applies to
them fully, regardless of whether the deployment also includes sensors elsewhere.

**Why not synthesize a scope signature for sensor pushes?** A sensor envelope is not a scan — its
port scope, `--profile`, and enabled extras were decided on the sensor at push time and are not
reliably recoverable centrally. Fabricating a signature for it would produce something that looks
structurally present but is semantically empty: it would pass the "scope signature exists"
mismatch check without ever having actually evaluated whether the compared scans were comparable.
That is worse than the current gap, because it would silently masquerade as a valid comparison
instead of visibly declining to compare.

A follow-up to revisit this — either by extending scope signatures to a per-sensor keying scheme,
or by permanently accepting the exclusion and surfacing it in reports instead — is tracked in
`.planning/ROADMAP.md` under `## Backlog` → "Remediation Coverage (post-v5.18)".

### 16. Closure Verification (v5.18+ — Phase 180-181)

Phase 179 gave a remediation item a stable identity and a per-scan record. Phase 180 adds the
piece that identity was missing: a machine-observed decision about whether that item is actually
fixed, computed from two consecutive comparable scans rather than asserted by anyone. Phase 181
surfaces that decision to the operator and the client — this section covers where it now appears
and how the dashboard behaves when there is nothing to show.

#### Where it surfaces

Closure state and the remediation burndown are now visible on every report surface:

- **CLI markdown, HTML, and DOCX reports** each render a "Remediation Burndown" section, per
  deadline, with a shared advisory caption held byte-identical across all three renderers by a
  test — see `docs/report-interpretation.md` §16 for how to read it with a client.
- **The CBOM** carries a `vulnerabilities` array (CycloneDX VEX), one entry per remediation item,
  with `not_observed` mapped to `in_triage` — never `not_affected`. See
  `docs/report-interpretation.md` §16 for the full state-mapping table.
- **The dashboard** shows closure state directly on the **existing roadmap items** it already
  displays, joined by the item's slug — **there is no new tab.** A closure `Badge` appears in the
  roadmap node detail panel (omitted entirely when no closure state is attached), and a
  "Remediation Burndown" table is rendered beneath the existing roadmap graph.

#### Dashboard behavior when closure data is absent

A scan that has no persisted closure data — no prior comparable scan, a freshly initialized
database, or a scan that predates Phase 179 — shows an **explicit "closure state was not computed
for this scan" message**, never a table of zeros and never a burndown row that reads as "0
closed." An operator seeing an empty panel must not report "all clear"; the panel is telling you
closure was not computed, not that nothing needs fixing.

**Any closure lookup failure degrades the panel to empty and is logged — the endpoint never returns a 500.**
The dashboard's `/api/scan/latest` response reuses the same advisory-only
firewall pattern already used for vendor PQC trends and hardware findings: the lookup runs inside
its own try/except, a failure is logged via `logger.exception(...)`, and the response falls back
to an empty/`null` burndown or closure field rather than raising. This means an advisory-surface
failure can never take down the score view or the rest of the roadmap mid-presentation — the worst
case is a missing badge or an empty burndown block, not a broken page.

#### The four states

A finding's closure state is always one of exactly four values (`quirk/intelligence/remediation.py`
`ITEM_STATES`):

- **`open`** — the finding was rechecked this scan and is still present.
- **`closed`** — the finding was present in a comparable prior scan and the current scan positively
  rechecked that same host:port with a healthy probe and did not find it there.
- **`not_observed`** — the question was not answered this scan, one way or the other. See the
  troubleshooting list below for the specific reasons this happens.
- **`resurfaced`** — an item that was previously `closed` has come back. It is counted as open for
  reporting purposes, but reported as its own line rather than folded silently into `open`, and its
  closure history is retained rather than discarded.

**Absence alone never closes an item.** A host that stops appearing in a scan — because it was
decommissioned, because the target list shrank, because a segment of the network was unreachable —
is not evidence anything was fixed. Closure requires the current scan to have positively rechecked
that specific host:port and found the finding gone, not merely to have not seen it. This mirrors
the guardrail vulnerability scanners such as Qualys, Tenable, and Orca already apply: a scanner
does not mark a finding closed unless it recheck that exact target.

#### Why an item reads `not_observed` — troubleshooting

If a client or colleague asks "why does this say `not_observed` instead of `closed`?", the answer
is always one of:

- **No comparable prior scan exists.** This is the first scan of this estate, or no prior scan's
  scope signature matches closely enough to compare against.
- **The scope signature is missing or mismatched.** Port scope, `--profile`, enabled optional
  extras, credential presence, sensor set, or the target set itself differ between the two scans —
  see `docs/operators-guide.md` §15 for what a scope signature captures. Two scans covering
  different ground are never treated as comparable, no matter how similar the counts look.
  Comparability now also depends on the **target set** — two different estates scanned with the
  same profile are not comparable, even if every other scope dimension matches, which is why the
  target-set digest exists.
- **The relevant probe family was unhealthy.** A specific protocol family (SSH, TLS, JWT, etc.) was
  `no_targets`, `not_run`, or `unhealthy` for the finding's host:port. A scan can exit cleanly while
  one probe family silently produced no usable evidence — probe health is asserted positively per
  family, never inferred from a clean exit.
- **No endpoint was rechecked at that host:port.** The current scan simply did not touch that
  address this run.

Treat `not_observed` as **"we did not verify"**, never as **"nothing was found."** These read
almost identically in a report, and the difference matters: telling a client "12 items came back
clean" when the true state is "we did not check 12 items this run" is the exact misreading this
state exists to prevent.

#### Troubleshooting — "the burndown block is empty / says not computed"

This is the same comparability gap as the `not_observed` troubleshooting list above, surfaced at
the whole-scan level instead of the per-item level. Check, in order:

- **No comparable prior scan exists** — this is the first scan of this estate, or nothing prior
  matches closely enough.
- **The scope signature differs** — port scope, `--profile`, enabled optional extras, credential
  presence, sensor set, **or the target set** — the five axes named verbatim in the report's
  refusal statement (e.g. "Closure not computed: scan scope differs from the prior scan.").

The report and dashboard both state the refusal explicitly rather than showing an all-zero table —
if you see the refusal message, the fix is to rerun with a scope that matches the prior scan you
want to compare against, not to look for a hidden toggle.

#### There is no closure override

**No flag, config key, or CLI option can mark an item closed.** This is deliberate (CLOSE-01), not
an oversight — an operator under client pressure to "just mark it fixed" has nothing to reach for,
because nothing exists. If a finding needs to be closed, the only path is a rescan that positively
observes it gone under comparable scope.

#### `resurfaced`

A `resurfaced` item was `closed` on a prior scan and has now been rechecked and found present
again. It counts toward `open`-style totals (so "how many open items do we have" stays accurate),
but it is reported as its own category — a report reading "2 open + 1 resurfaced" tells you
something "3 open" does not: one of those three was believed fixed and did not hold. The event
history behind a resurfaced item is retained, so a later re-closure is traceable against the full
sequence rather than looking like a first-time fix.

#### The EO 14412 deadline catalog

Burndown is computed per named deadline, never as one number. The catalog lives in
`quirk/scanner/pqc_deadlines.py` (`PQC_DEADLINES`) — this guide does not restate the dates as an
independent fact; it points at that module because a client challenging a date needs one source of
truth, not two that can drift apart. As of this writing that catalog carries:

- **Key establishment** — December 31, 2030 (FIPS 203 / ML-KEM), for HVAs and high-impact systems.
- **Digital signatures** — December 31, 2031 (FIPS 186-5 / DSS), for HVAs and high-impact systems.
- **NIST-owned/operated subset** — December 31, 2027, an earlier deadline for a narrower system
  set.

Source: Federal Register Vol. 91 No. 121 (2026-06-25), FR Doc 2026-12909, Executive Order 14412.
The catalog is re-verified on a 90-day cadence against that `source_url`, the same cadence as the
QRAMM and CMVP catalogs described at the top of this file.

**CNSA 2.0 dates are a deliberate, documented omission, not a gap that was missed.**
`media.defense.gov` returns HTTP 403 to non-browser user agents, so no CNSA 2.0 date literal has
been added anywhere in the codebase. Do not fill this in from a secondary source — a
transcription error in a compliance-adjacent date is the exact failure class this catalog exists to
prevent. If CNSA 2.0 dates become genuinely needed, they must be re-sourced directly and added with
the same `source_url` discipline the EO 14412 dates already follow.

#### Documented limits

Three things burndown and closure will never do, by design:

- **Sensor-origin findings are excluded from closure tracking.** See §15's "Known limitation"
  above — closure is scoped to CLI scans; findings arriving through the distributed sensor
  ingestion path never carry the scope signature closure comparison requires.
- **`evidence_only` items can never close.** Closure operates per constituent finding fingerprint;
  an item with zero constituent fingerprints has nothing to positively recheck, so it can never
  transition out of `not_observed`.
- **Findings whose only algorithm evidence lives in a JSON blob land in the `unmapped` burndown
  bucket**, not silently outside the count. `compute_burndown` reads only a matched endpoint's
  declared columns (certificate public-key algorithm, certificate signature algorithm, cipher
  suite); it deliberately does not re-implement the CBOM builder's protocol-specific JSON parsing a
  second time, so evidence that only exists in a blob resolves to `unmapped` rather than to a
  fabricated deadline. `unmapped` is reported, never dropped.

> **Client Conversation — Closure:**
> "This report's `not_observed` count is not 'nothing found' — it means we didn't recheck those
> items this run, usually because this scan's scope differed from the prior one, or a probe family
> came back unhealthy. Nothing here can be marked closed by a flag; a finding only closes when we
> positively recheck it and it's gone. And a `resurfaced` item means something we believed fixed
> came back — that's reported separately from ordinary open items so it isn't lost in the count."

---

### 17. Rating Band Severity Floor (Phase 184.4, SCORE-04/SCORE-05)

#### What changed for operators

A scan with an open **CRITICAL** finding — for example, an expired TLS certificate — now
**completes report generation successfully** instead of halting. Before this phase, a scan whose
numeric score placed it in `EXCELLENT`, `GOOD`, or `MODERATE` while a CRITICAL finding remained
open would fail every report-writing path (CLI, HTML/PDF, DOCX) with:

```
Report generation halted: executive headline 'EXCELLENT' is inconsistent with 1 CRITICAL
finding(s). Review findings before generating the report.
```

If you have seen this error in the field, it is fixed: the readiness **band** shown in the report
now automatically floors to `FAIR` whenever at least one CRITICAL finding is open, so it never
disagrees with the findings the report is also showing. The numeric score itself is unaffected —
see `docs/report-interpretation.md` §19, "The Severity Floor," for the full client-facing
explanation of why the number and the band can differ, and the exact worked example (89/100
scoring `FAIR`, not `EXCELLENT`).

#### Where operators will see it

- **CLI**, **HTML/PDF**, **DOCX**, and the **scorecard** all show a short `Cap reason` annotation
  beside the score/band headline whenever the band has been capped — never elsewhere in the
  document, and never present at all when the band is uncapped.
- **The dashboard Executive page and the print page** — the same screen the original defect
  (BACK-89) was filed against — now show the cap reason beside the readiness headline, next to the
  confidence badge. This closes the dashboard's copy of the same halt-on-generate defect: the
  dashboard's own scan-scoring path previously computed the band without seeing the scan's
  findings at all, which could show an uncapped `EXCELLENT` on the dashboard for the same scan
  whose exported report showed `FAIR` — those two views now always agree.
- No configuration change, migration, or re-scan is required. Historical scan sessions pick up the
  corrected band automatically the next time their report or dashboard view is rendered, because
  the band is recomputed at render time rather than stored.

#### Troubleshooting

If you still see `Report generation halted` on a current QU.I.R.K. version, that indicates a scan
whose evidence was assembled without its findings list attached to the scoring call — verify you
are running a version that includes Phase 184.4 (`v5.19` or later) and, if the error persists,
capture the full evidence/findings payload for the scan and file it, since every production call
site that renders a band is now required to pass its findings to the scorer.

### 18. SPKI Fingerprint Capture and Key Reuse (Phase 191, SPKI-01/SPKI-02)

#### What is captured

Every TLS scan now computes a SHA-256 hash of each leaf certificate's SubjectPublicKeyInfo (SPKI)
and stores it on `CryptoEndpoint.cert_spki_fingerprint`. This is captured at TLS certificate parse
only — the two `cryptography` x509 parse sites in `quirk/scanner/tls_scanner.py` (the `sslyze`
path and the stdlib-`ssl` fallback path). Scanners that persist raw `*_scan_json` blobs instead of
individual `cert_*` columns — broker, SAML, ADCS, and similar — are out of scope for this field;
SPKI-01 scopes strictly to TLS endpoints' `cert_*` fields.

Only the leaf certificate is fingerprinted — there is no chain fingerprinting or intermediate/root
hashing.

#### Fill path for pre-existing rows

The column is nullable and there is no backfill migration. Computing the SPKI hash requires the
raw certificate bytes, which QU.I.R.K. does not persist; a fingerprint cannot be derived after the
fact from the other `cert_*` fields already stored on a row. The only way to populate
`cert_spki_fingerprint` for an endpoint scanned before this release is to re-scan it — the next
TLS scan against that `(host, port)` writes the fingerprint going forward.

#### Sensor push path

`cert_spki_fingerprint` travels the full sensor→console path end-to-end: sensor-side serialization
(`quirk/cli/sensor_cmd.py::_endpoint_to_dict`), the push envelope, and console-side ingest
(`quirk/cli/console_cmd.py::_ingest_envelope`), which is also the function backing the
`POST /api/sensor/push` API route. An older sensor build that does not send the field is tolerated
— `_ingest_envelope` reads it with `.get()`, not a required key, so a missing field ingests as
`NULL` rather than raising an error. This matches the existing version-skew, warn-only policy for
sensor pushes.

#### Where key reuse appears

Key reuse — TLS endpoints sharing an identical SPKI fingerprint — is derived at report-generation
time by a `GROUP BY cert_spki_fingerprint HAVING COUNT(*) >= 2` query
(`quirk/intelligence/key_reuse.py::compute_key_reuse_clusters`); there is no stored cluster table
or denormalized "is shared" column to keep in sync. The resulting "Key Reuse" section renders in
the CLI technical markdown, the HTML report, and the DOCX report — **not** the dashboard UI in
this release. It is advisory-only and never affects the readiness score; see
`docs/report-interpretation.md` §21 for the client-facing explanation of how to read it.

### 19. Finding Storyline Drawer (Phase 202, v5.23 — STORY-01/STORY-02)

Every row in the dashboard findings table has a `Storyline` button in its rightmost column. Opening
it is fully keyboard-operable: `Tab` to the button and press `Enter` (or click it), and a drawer
opens in place without leaving the findings view. Pressing `Escape` closes the drawer and returns
focus to the row's `Storyline` button, so keyboard navigation is never lost.

If the button is disabled with a tooltip reading "Storyline unavailable — this finding has no
stable identifier in this scan," that finding has no addressable ID for this scan (a known case:
identity-protocol findings such as Kerberos/SAML/DNSSEC). No action fixes this from the UI — it is
a property of how that finding was derived, not a bug in this scan.

In brief: the drawer shows the finding's narrative (when the algorithm-keyword catalogs have one —
most findings legitimately do not, and a blank narrative is normal, not an error) plus its
score-lift attribution — the owning remediation theme's total lift, conditioned on every finding in
that theme being resolved, never this one finding's individual share. See
`docs/report-interpretation.md` §25 for the full explanation of the theme framing, why most
findings show no narrative, and the one-theme display rule.


---

# Administration

*Console deployment, sensor enrolment, token lifecycle and hardening.*

This guide covers deploying a multi-sensor QUIRK console, enrolling sensors using the
two-step workflow, managing per-sensor authentication (issuance, revocation, rotation,
and compromise response), and configuring SNMP hardware scanning with a troubleshooting
checklist. It is intended for IT administrators responsible for day-to-day QUIRK
operations on enterprise deployments.

### Prerequisites

Before following this guide, confirm the following:

- **(a) QUIRK is installed.** If this is a first-time setup, follow
  [Getting Started](#getting-started) to install and configure QUIRK before proceeding.
- **(b) `[hw]` extras installed** (hardware scanning only). SNMP hardware scanning
  requires `pip install 'quirk-scanner[hw]'`. This extra is **not included** in `[all]`
  due to the size of the pysnmp dependency. See
  [Operator's Guide §2.2](#22-optional-extras-matrix) for the full
  optional extras matrix and the install command.
- **(c) Port 8512 connectivity.** The console host must be reachable from each sensor
  host on port 8512 (the default QUIRK console API port). Sensors push scan results
  to the console over this port.
- **(d) Python 3.11+.** This guide assumes a Python 3.11 or higher environment on all
  hosts.

---

### 1. Deploy the Console

Install QU.I.R.K. on the console host. Use `pip install quirk-scanner` for the core
scanner, or `pip install 'quirk-scanner[all]'` for full scanner coverage including
optional extras (excludes `[identity]` and `[hw]`):

```bash
pip install 'quirk-scanner[all]'
```

Start the server. The console binds loopback only by default; pass `--host 0.0.0.0`
to make it reachable over the network from sensor hosts:

```bash
quirk serve --host 0.0.0.0 --port 8512
```

The default port is 8512. QUIRK refuses to start on a network-reachable interface
when no `QUIRK_API_TOKEN` environment variable is set, unless you pass `--insecure`
to explicitly acknowledge a token-less bind on a trusted, firewalled segment. For
reverse-proxy and cloud-hosted console deployments, see
[Operator's Guide §8.1](#81-provision-the-console).

**Verify reachability.** From a sensor host, confirm the console is accessible:

```bash
curl http://<console-host>:8512/api/health
```

Expect an HTTP 200 response. You can also open the URL in a browser. If the health
check fails, confirm port 8512 is permitted between the sensor and console hosts.

**Fields the sensor operator needs.** When you enroll a sensor (§2), the sensor's
`sensor.yaml` will contain two key fields required for push authentication:

- `console_url` — the base URL of the console (e.g. `https://console.corp:8512`)
- `console_api_token` — the per-sensor push credential minted by `quirk console enroll`

---

### 2. Enroll Sensors

Sensor enrollment is a two-step process: first provision the sensor on the **console
host**, then register the sensor configuration on the **sensor host**.

#### Step 1 — Console host: mint the sensor token

On the console host, run `quirk console enroll` with a segment label. This provisions
the sensor rows in the console database and prints the per-sensor bearer token to
stdout:

```bash
quirk console enroll --segment <label>
# e.g.:
quirk console enroll --segment segment-a
```

The output looks like:

```text
Bearer token (copy now — shown once, never recoverable):
<per-sensor-token>
```

> **WARNING:** This bearer token is shown **once** and is never recoverable. Copy it
> immediately. Only a SHA-256 hash of the token is stored on the console — the raw
> value is gone after this terminal session. If the token is lost, you must revoke
> the sensor and re-enroll (see §3.2 and §3.3).

The `sensor_id` (a UUID) for this sensor is printed to stderr and will also be stored
in the sensor's `sensor.yaml` after Step 2.

#### Step 2 — Sensor host: write the sensor configuration

On the sensor host, run `quirk sensor enroll` with the console URL, the matching
segment label, and the bearer token from Step 1:

```bash
quirk sensor enroll https://<console-host>:8512 \
  --segment <label> \
  --api-token <bearer-token-from-step-1>
```

The `--api-token` flag writes the console-minted token directly to the
`console_api_token` field in `sensor.yaml`. If you omit `--api-token`, that field is
written as empty and must be set manually before the sensor can push results.

**On-prem and RFC1918 console URLs:** Pass `--allow-internal-console` when the console
URL is a private or RFC1918 address:

```bash
quirk sensor enroll https://10.0.0.5:8512 \
  --segment segment-a \
  --api-token <bearer-token-from-step-1> \
  --allow-internal-console
```

**`sensor.yaml` default location:**
- Linux / macOS: `~/.config/quirk/sensor.yaml`
- Windows: `%APPDATA%\quirk\sensor.yaml`

Use `--config <path>` to write `sensor.yaml` to a custom location (useful in CI or
when running multiple sensors on the same host). After enrollment, the sensor is ready
to push scan results with `quirk sensor push`.

---

### 3. Manage Sensor Auth

#### 3.1 Token Issuance

Each sensor authenticates push requests with its own per-sensor bearer token, issued
at enrollment by `quirk console enroll --segment <label>`. The console stores only the
SHA-256 hash of the raw token in the `sensor_tokens` table — the raw token itself is
never persisted anywhere on the console. The only live copy of the raw token is the
`console_api_token` value in the sensor's `sensor.yaml`.

This model means:
- A sensor can be revoked independently without affecting other enrolled sensors.
- If the raw token is lost (e.g. `sensor.yaml` is deleted), the sensor cannot push
  until it is revoked and re-enrolled.

#### 3.2 Revoking a Sensor

To revoke a sensor's push access, run on the **console host**:

```bash
quirk console revoke-sensor <sensor_id>
```

`sensor_id` is a positional UUID argument (not a flag). The command stamps
`revoked_at = now` on all active token rows for that sensor and prints:

```text
Revoked token(s) for sensor_id: <sensor_id>
```

The command exits with an error if no active token exists for the given sensor ID.

**Finding the sensor_id:** The sensor_id is printed to stderr at enrollment time.
It is also stored in the sensor's `sensor.yaml` under the `sensor_id` key.

Once revoked, the sensor cannot push results to the console until it is re-enrolled
with a new token (see §3.3).

#### 3.3 Rotating a Token

Token rotation is a routine, non-alarming procedure. Use it when cycling credentials
on a scheduled basis or after a token has been inadvertently exposed. The procedure
has three steps:

1. **Revoke the old token** (console host):
   ```bash
   quirk console revoke-sensor <sensor_id>
   ```

2. **Mint a new token** (console host):
   ```bash
   quirk console enroll --segment <original-label>
   ```
   Copy the new bearer token printed to stdout. A new `sensor_id` is also issued and
   printed to stderr.

3. **Re-enroll the sensor** (sensor host):
   ```bash
   quirk sensor enroll https://<console-host>:8512 \
     --segment <original-label> \
     --api-token <new-bearer-token>
   ```
   This overwrites `sensor.yaml` with the new `sensor_id` and `console_api_token`.

#### 3.4 Responding to a Suspected Compromise

If a sensor token is suspected to have been compromised (for example, if `sensor.yaml`
was accessed by an unauthorised party), the response adds a log-review step to the
standard rotation procedure:

1. **Immediately revoke** (console host):
   ```bash
   quirk console revoke-sensor <sensor_id>
   ```
   Revocation takes effect immediately — the sensor cannot push as of this command.

2. **Treat the sensor as untrusted** until re-enrolled with a new token. Do not rely
   on scan results from the compromised `sensor_id`.

3. **Review scan/push logs** for anomalous pushes from that `sensor_id` in the time
   window before revocation. Look for unexpected push timing, unusual finding volumes,
   or pushes from unexpected IP addresses.

4. **Re-enroll with a new token** following the same three steps as §3.3.

The difference between routine rotation (§3.3) and compromise response is step 3 —
the log review. If no anomalies are found in the push history, re-enrollment completes
the response.

---

### 3.5 Hardening Environment Variables

Two security controls are configured only by environment variable — there is no config-file
equivalent and no CLI flag, so an operator who does not know they exist cannot switch them on.

| Variable | Default | Effect |
|----------|---------|--------|
| `QUIRK_SENSOR_IP_ALLOWLIST` | unset (no IP restriction) | Comma-separated IPs/CIDRs permitted to authenticate as a sensor. Read by `quirk/dashboard/api/middleware/sensor_auth.py`. With it unset, a valid token is accepted from **any** source address — token possession is the only control. Set it to your sensor subnets for defence in depth alongside the token. |
| `QUIRK_HSTS` | unset (header not sent) | Set to `1`/`true` to emit `Strict-Transport-Security` on dashboard responses. Read by `quirk/dashboard/api/middleware/security_headers.py`. **Only enable behind TLS** — HSTS on a plain-HTTP deployment locks browsers out of a host they cannot reach over HTTPS. |

```bash
export QUIRK_SENSOR_IP_ALLOWLIST="10.20.0.0/24,10.20.1.15"
export QUIRK_HSTS=1        # TLS-terminated deployments only
quirk serve --port 8512
```

Both are read at request time by middleware, so they must be set in the environment of the
`quirk serve` process — exporting them in a different shell has no effect.

See [Configuration](#configuration) for the non-security `QUIRK_*` variables
(`QUIRK_SERVE_HOST`, `QUIRK_SERVE_PORT`, `QUIRK_OUTPUT_DIR`).

---

### 4. SNMP Setup

#### 4.1 Network Requirements

SNMP hardware scanning requires the `[hw]` extras package, which is **not included**
in `[all]`:

```bash
pip install 'quirk-scanner[hw]'
```

Once installed, enable SNMP scanning and configure the community string in your
`config.yaml`. For the full config key reference including `enable_snmp` and
`snmp_community` defaults, placement under the `scan:` block, and sample output,
see [Operator's Guide §9.1](#91-enable-snmp-scanning).

**Network prerequisites:**

- **UDP 161** must be permitted inbound from the QUIRK console/scan host to each
  scan target. SNMP uses UDP — not TCP — so standard TCP firewall rules do not cover
  it.
- **Community string hygiene:** The default `snmp_community` value is `"public"`.
  Change this to match the read-only community string configured on your devices.
  Using `"public"` on networks with a custom community string will cause all probes
  to fail silently.

QUIRK attempts SNMPv3 auth+priv first (when a per-host credential is configured), falls
back to SNMPv2c, then to no-SNMP, and always reports which tier actually succeeded — see
[Operator's Guide §9.1.1](#911-snmpv3-authpriv-scanning-phase-139) for
configuring per-host SNMPv3 credentials.

#### 4.2 Troubleshooting SNMP Probes

SNMP uses UDP — a connectionless protocol that fails silently. When a probe does not
reach a device, or a device does not respond, no error is raised and no exception
appears in the QUIRK output. Instead, hardware devices either appear with
`vendor: unknown` / `model: unknown` in the HardwareInventory section of the
dashboard CBOM tab, or are absent from the output entirely. Hardware rows appear after
the full scan completes, not incrementally — if you check the dashboard mid-scan,
hardware results will not yet be present.

Use the checklist below to diagnose a missing or incomplete hardware inventory.

| Symptom | Check | Fix |
|---------|-------|-----|
| No hardware rows appear at all | Verify `[hw]` extras are installed: `pip show pysnmp` | Run `pip install 'quirk-scanner[hw]'` |
| Devices appear with `vendor: unknown` / `model: unknown` | UDP 161 may be blocked between the QUIRK host and scan targets | Open a firewall rule permitting UDP 161 from the QUIRK scan host to each scan target |
| Devices missing despite reachable network | Wrong community string — probes reach devices but are rejected | Set `snmp_community` to the device's configured read-only community (see [operators-guide.md §9.1](#91-enable-snmp-scanning)) |
| Probes fail on SNMPv3-only devices (no v2c community enabled) | No `snmp_v3_credentials` entry configured for this host | Configure a per-host SNMPv3 USM credential (see [operators-guide.md §9.1.1](#911-snmpv3-authpriv-scanning-phase-139)) |
| SNMP column shows `v3 failed → v2c` | SNMPv3 was attempted but authentication failed | Verify the configured `auth_key_env`/`priv_key_env` passphrases match the device's USM user |
| Target absent entirely from hardware results | Scan target is unreachable at layer 3 | Verify routing and confirm the host is reachable from the QUIRK scan host, and that the host is included in the configured scan scope |
