# Installation

Full installation reference for all supported platforms.

---

## System Requirements

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python 3.10 or higher | — | Check: `python3 --version` |
| pip | 21.0 or higher | Usually bundled with Python |
| git | Any recent version | Required to clone the repo |
| Docker Desktop | Optional | Required only for the chaos lab |
| OS (for PDF export) | macOS 10.15+, Ubuntu 20.04+, Windows 10 via WSL2 | Playwright Chromium requirement |

---

## macOS

**Install Python** (Homebrew recommended):

```bash
brew install python@3.12
```

**Clone and install:**

```bash
git clone <repo-url>
cd quirk
python3 -m venv .venv && source .venv/bin/activate
pip install -e '.[dashboard]'
playwright install chromium
```

Playwright installs Chromium to `~/.local/share/ms-playwright/` (one-time, approximately 150 MB).

**Troubleshooting:**

- If `quirk` is not found after install, confirm your venv is activated: `source .venv/bin/activate`
- If `python3` is not found, ensure Homebrew Python is in your PATH: `export PATH="/opt/homebrew/bin:$PATH"`

**Verify:**

```bash
quirk --help
quirk serve --help
```

---

## Linux (Ubuntu / Debian)

**Install system packages:**

```bash
sudo apt-get update && sudo apt-get install -y python3 python3-pip python3-venv git
```

**Clone and install:**

```bash
git clone <repo-url>
cd quirk
python3 -m venv .venv && source .venv/bin/activate
pip install -e '.[dashboard]'
playwright install chromium
playwright install-deps chromium   # Installs required system libraries
```

> **Note:** Playwright requires glibc 2.17 or higher. Ubuntu 20.04 and later meet this requirement. Ubuntu 18.04 is not supported for PDF export.

**Verify:**

```bash
quirk --help
quirk serve --help
```

---

## Windows (WSL2)

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

## Optional Dependencies

Install only what you need:

| Capability | Install command |
|------------|----------------|
| Web dashboard + PDF export | `pip install -e '.[dashboard]'` (included in Quick Start) |
| Identity surface scanners (Kerberos, SAML/OIDC, DNSSEC) | `pip install -e '.[identity]'` — installs `impacket`, `lxml`, `signxml`, `dnspython[dnssec]` |
| Container scanning | `pip install syft` (requires Syft CLI on PATH) |
| Source code scanning | `pip install semgrep` |
| AWS connector | Included in base install (boto3 is a core dependency) |
| Azure connector | Included in base install (azure-identity and azure-keyvault-* are core dependencies) |

---

## Verify Installation

```bash
quirk --help         # Should show scan options
quirk serve --help   # Should show serve options
```

If both commands display help output, the installation is complete.

---

## Next Steps

- [Getting Started](getting-started.md) — zero to first scan in under 10 minutes
- [Configuration Reference](configuration.md) — all `config.yaml` options
- [Connector Guides](connectors/) — AWS, Azure, Docker, Git
