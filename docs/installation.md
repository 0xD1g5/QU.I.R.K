# Installation

Full installation reference for all supported platforms.

---

## System Requirements

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python 3.10 or higher | — | Check: `python3 --version` |
| pip | 21.3 or higher | Required for self-referential extras resolution (used by `pip install 'quirk-scanner[all]'`); pip 22.2+ recommended for the `--report` JSON test in CI |
| git | Any recent version | Required to clone the repo |
| Docker | Optional | Required only for the chaos lab. **Docker Desktop** on macOS/Windows; **Docker Engine + Compose plugin** on Linux — see [Docker on Linux](#docker-on-linux-chaos-lab-only) |
| Free disk (chaos lab) | ~25 GB | Only if running the chaos lab: its images total ~20 GB, the `multihost` prober alone is ~3.5 GB. The scanner itself needs ~2 GB |
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

## Docker on Linux (chaos lab only)

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

## Parrot OS / Kali / Debian (PEP 668)

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
| All optional scanners (recommended for consultants) | `pip install 'quirk-scanner[all]'` — installs adcs + cbom + cloud + dashboard + db + docx + motion + notify + redis + tickets. That is **10 of the 17 extras**; see the row below for what it leaves out. Includes Playwright browser binaries via `[dashboard]` (~250 MB). |
| **What `[all]` does _not_ install** | Seven extras are excluded. `[identity]` and `[api]` are deliberate — see [Why `[all]` excludes `[identity]`](#why-all-excludes-identity) and the active-fuzzer opt-in. **`[hw]`** (pysnmp, pymodbus, bacpypes3 — hardware/SNMP/Modbus/BACnet scanning, and the chaos lab's `hwcompat` profile) and **`[kafka]`** (kafka-python) are simply not in `[all]`, which surprises people. `[broker]` needs only `redis`, already present; `[email]` has no dependencies at all; `[dev]` is build tooling. |
| Everything except `[identity]` | `pip install -e '.[all,hw,kafka,api]'` — the full scanner surface in one venv. Resolves cleanly. Add `,identity` only after reading the `[identity]` note below. |
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
