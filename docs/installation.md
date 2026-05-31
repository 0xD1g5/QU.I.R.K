# Installation

Full installation reference for all supported platforms.

---

## System Requirements

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python 3.10 or higher | — | Check: `python3 --version` |
| pip | 21.3 or higher | Required for self-referential extras resolution (used by `pip install 'quirk-scanner[all]'`); pip 22.2+ recommended for the `--report` JSON test in CI |
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

## Linux (Ubuntu / Debian)

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
| All optional scanners (recommended for consultants) | `pip install 'quirk-scanner[all]'` — installs cloud + cbom + db + motion + redis + dashboard + adcs + docx + notify + tickets. **Excludes `[identity]`** because impacket transitively downgrades the cryptography library and breaks the TLS scanner, and **excludes `[api]`** because the schemathesis active fuzzer requires explicit opt-in. Includes Playwright browser binaries via `[dashboard]` (~250 MB). |
| Web dashboard + PDF export | `pip install -e '.[dashboard]'` (included in Quick Start) |
| Identity surface scanners (Kerberos, SAML/OIDC, DNSSEC) | `pip install -e '.[identity]'` — installs `impacket`, `lxml`, `signxml`, `dnspython[dnssec]` |
| Container scanning | `pip install syft` (requires Syft CLI on PATH) |
| Source code scanning | `pip install semgrep` |
| AWS connector | Included in base install (boto3 is a core dependency) |
| Azure connector | Included in base install (azure-identity and azure-keyvault-* are core dependencies) |

### Why `[all]` excludes `[identity]`

The `[identity]` extra pulls `impacket`, which transitively depends on `pyOpenSSL`. `pyOpenSSL`'s
pin range forces a downgrade of the `cryptography` library that QUIRK ships with as a base
dependency. That downgrade silently breaks the TLS scanner (loss of TLS 1.3 / X25519 cipher
enumeration), so `[all]` intentionally **excludes `[identity]`** to keep the default consultant
install safe.

If you need both the full scanner surface **and** Kerberos / impacket-backed scanners,
install them in **two separate virtual environments**:

```bash
# venv 1 — full scan surface (recommended default)
python3 -m venv .venv-quirk && source .venv-quirk/bin/activate
pip install 'quirk-scanner[all]'

# venv 2 — identity-only surface (deactivate the first venv first)
python3 -m venv .venv-quirk-identity && source .venv-quirk-identity/bin/activate
pip install 'quirk-scanner[identity]'
```

This isolation keeps the cryptography library in venv 1 at the version the TLS scanner
requires, while venv 2 can carry the older pinned version impacket needs.

A CI regression test (`tests/test_install_all_excludes_impacket.py`) guards this exclusion;
attempts to add `quirk-scanner[identity]` to `[all]` will fail the test.

---

## Verify Installation

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

## Next Steps

- [Getting Started](getting-started.md) — zero to first scan in under 10 minutes
- [Configuration Reference](configuration.md) — all `config.yaml` options
- [Connector Guides](connectors/) — AWS, Azure, Docker, Git
