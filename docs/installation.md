# Installation

Installation steps for macOS, Linux and Windows (via WSL2).

---

## System Requirements

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python 3.10 to 3.14 | — | Check: `python3 --version`. Python 3.15 is not yet supported: a dependency, nassl, ships no 3.15 build. CI tests Python 3.11 |
| pip | A current release | Run `pip install --upgrade pip` first (this guide's install was verified with pip 26.2.1). The repo's CI install tests use `pip install --report`, which needs pip 22.2 or newer |
| git | — | Only needed to clone the repo for a source install; the PyPI install does not use it |
| Docker | Optional | Needed to run the chaos lab. **Docker Desktop** on macOS/Windows; **Docker Engine + Compose plugin** on Linux — see [Docker on Linux](#docker-on-linux-chaos-lab-only) |
| Free disk | ~1.5 GB | Measured on macOS with Python 3.13: a venv with the `[all]` extra is 713 MB and the Chromium download for PDF export is about 520 MB. The chaos lab references 51 further container images across its profiles |
| OS (for PDF export) | Windows 11+ or WSL, macOS 14 or later, Debian 12 / 13, Ubuntu 22.04 / 24.04 / 26.04 | Playwright's published system requirements |

---

## macOS

**Install Python** (Homebrew recommended):

```bash
brew install python@3.12   # example: any of python3.10 … python3.14 works
```

**Clone and install:**

```bash
git clone https://github.com/0xD1g5/QU.I.R.K
cd QU.I.R.K
# e.g. python3.12; any of python3.10 ... python3.14 works
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e '.[dashboard]'
playwright install chromium
```

Homebrew's `python@3.12` puts `python3.12` on your PATH; it does not replace `python3`, which can still be Apple's older interpreter. Create the venv with `python3.12` (or any other supported version, python3.10 … python3.14; 3.12 is just the example used here). Inside the activated venv, `python` and `pip` are the venv's own.

Playwright installs Chromium to `~/Library/Caches/ms-playwright/` on macOS (one-time, a few hundred megabytes).

> **Note:** The repository name has no trailing dot (`QU.I.R.K`, not `QU.I.R.K.`). Microsoft's guidance is not to end a file or directory name with a period (the Windows shell and user interface do not support such names), so a checkout directory named with a trailing dot is a problem there. GitHub redirects the trailing-dot URL to the form shown above.

**Troubleshooting:**

- If `quirk` is not found after install, confirm your venv is activated: `source .venv/bin/activate`
- If `python3.12` is not found, ensure Homebrew's bin directory is in your PATH. On Apple Silicon: `export PATH="/opt/homebrew/bin:$PATH"`; on Intel Macs: `export PATH="/usr/local/bin:$PATH"`
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
playwright install-deps chromium   # Installs Chromium's system libraries with apt-get; asks for sudo itself
```

> **Run `install-deps` without a `sudo` prefix.** Playwright switches to root on its own (through `sudo`,
> or `su` when sudo is absent). With the default sudoers file on Debian 12 and 13 and Ubuntu 22.04 and 24.04,
> `sudo playwright ...` fails with `command not found`: sudo replaces your `PATH` with its
> `secure_path`, which does not include `.venv/bin` (unless another `playwright` happens to be
> installed in one of those system directories). To run it as root anyway, give the full path: `sudo .venv/bin/playwright install-deps chromium`.

> **Note:** For PDF export, use one of the Linux releases Playwright supports: Debian 12 / 13 or Ubuntu 22.04 / 24.04 / 26.04.

> **Debian / Kali (PEP 668):** Debian 12 and Kali (2024.4 and later) mark the system Python as
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

Eight numbered checks. The ones that matter most assert an observable outcome rather than an
exit code: a Chromium that actually launches, a `report-*.pdf` carrying real PDF magic bytes,
and every dashboard download returning HTTP 200 with a non-empty body. The system-package,
install and CLI checks (2, 3 and 5) still pass on exit codes. It also
reports where reality diverged from this document. Run it only on a throwaway
machine — it installs system packages.

---

## Docker on Linux (chaos lab only)

Skip this unless you are running the chaos lab. A scan needs no Docker.

The System Requirements table above says "Docker Desktop" for macOS and Windows —
**on Linux this guide installs Docker Engine plus the Compose plugin instead.** The lab scripts
call the `docker compose` plugin; `docker-compose` is the legacy standalone Compose binary,
which uses a different command.

These are the Ubuntu steps from Docker's own installation guide (Debian has its own page on
docs.docker.com):

```bash
# Add Docker's official GPG key:
sudo apt update
sudo apt install ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

# Add the repository to Apt sources:
sudo tee /etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF
sudo apt update

sudo apt install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

**Run Docker without sudo** (the lab scripts call `docker` directly, without `sudo`):

```bash
sudo usermod -aG docker "$USER"
```

Log out and back in so your group membership is re-evaluated. `newgrp docker`
activates the change for the current shell if you would rather not.

**Verify:**

```bash
docker run --rm hello-world
docker compose version        # must succeed; `docker-compose version` is the wrong binary
```

> **Check your free disk before starting the lab.** Across all of its profiles the lab references
> 51 container images.

See [Chaos Lab Operator Guide](chaos-lab.md) for profiles, ports and scanning.

---

## Parrot OS / Kali / Debian (PEP 668)

Debian 12 and Kali (2024.4 and later) enforce [PEP 668](https://peps.python.org/pep-0668/):
the system Python is *externally managed*, so a bare `pip install quirk-scanner[all]` fails with
`error: externally-managed-environment`. Parrot OS is Debian-based; this guide did not check whether a given Parrot
release marks its Python externally managed, and the steps below are correct either way. zsh also
glob-expands an unquoted `[all]` and fails with `zsh: no matches found`. Both problems are solved by
installing into a virtual environment and quoting the extras.

**1. System prerequisites:**

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip python3-full git build-essential libffi-dev
```

`build-essential` and `libffi-dev` are only needed if a dependency has to compile from source
(e.g. `cryptography` on an architecture without a prebuilt wheel); they are harmless to install
otherwise. The cryptography project's own Debian/Ubuntu list for a source build is
`build-essential libssl-dev libffi-dev python3-dev cargo pkg-config`, and it needs a Rust newer than
the one Debian versions before Trixie ship.

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
playwright install-deps chromium   # no sudo prefix: it asks for sudo itself
```

**Optional external tools** (`quirk doctor` flags each one that is missing and exits `1` while any of them is missing, but each is opt-in):

```bash
sudo apt install -y nmap     # richer host discovery (--discovery nmap)
pip install semgrep          # source scanning: known defect in 5.28.0, ruleset unavailable
# syft (container scanning): https://github.com/anchore/syft#installation
```

**Common errors:**

| Symptom | Cause / fix |
|---------|-------------|
| `error: externally-managed-environment` | venv not active — re-run step 2 and confirm the `(.venv)` prefix |
| `zsh: no matches found: quirk-scanner[all]` | quotes dropped — use `'quirk-scanner[all]'` |
| `command not found: quirk` | venv not active in this terminal — `source ~/quirk/.venv/bin/activate` |
| `sudo playwright install-deps` reports `command not found` | sudo's `secure_path` drops `.venv/bin` — run `playwright install-deps chromium` without `sudo` |
| `cryptography` / Rust build failure | upgrade pip first (`pip install --upgrade pip`), then install the build packages named under step 1 and retry |

---

## Windows (WSL2)

QU.I.R.K. runs on Windows via WSL2. The dashboard is accessible from your Windows browser.

**1. Enable WSL2:**

```powershell
wsl --install
```

Restart when prompted. The default distro is Ubuntu.

**2. Choose a distribution (optional):**

To install a specific distribution instead of the default, list the available ones and install by name.
Pick an Ubuntu release that Playwright supports (22.04, 24.04 or 26.04):

```powershell
wsl --list --online
wsl --install -d <DistroName>
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
| The `[all]` bundle (recommended for consultants) | `pip install 'quirk-scanner[all]'` — installs adcs + cbom + cloud + dashboard + db + docx + motion + notify + redis + tickets. That is **10 of the 17 extras**, plus `email`, `broker` and `kafka`, which `motion` pulls in; see the row below for what it leaves out. Installs the Playwright Python package via `[dashboard]`; the Chromium browser itself is a separate `playwright install chromium` download. |
| **What `[all]` does _not_ install** | Four extras are excluded: `[identity]`, `[api]`, `[hw]` and `[dev]`. `[identity]` and `[api]` are deliberate — see [Why `[all]` excludes `[identity]`](#why-all-excludes-identity) and the active-fuzzer opt-in. **`[hw]`** (pysnmp, sysdescrparser, pymodbus, bacpypes3 — hardware/SNMP/Modbus/BACnet scanning, and the chaos lab's `hwcompat` profile) is simply not in `[all]`, which surprises people. `[kafka]` (kafka-python) and `[broker]` (redis) are installed by `[all]` through `[motion]`; `[email]` has no dependencies at all; `[dev]` is build tooling. |
| Everything except `[identity]` | `pip install -e '.[all,hw,api]'` — the full scanner surface in one venv. Resolves cleanly. Add `,identity` only after reading the `[identity]` note below. |
| Web dashboard + PDF export | `pip install -e '.[dashboard]'` (used in the macOS and Linux install steps above) |
| Kerberos scanning | `pip install -e '.[identity]'` — adds `impacket` and `ldap3`; `lxml`, `signxml` and `dnspython[dnssec]` are already core dependencies |
| Container scanning | Install the Anchore Syft CLI and put it on your PATH: see [Syft's installation instructions](https://github.com/anchore/syft#installation) (the `syft` package on PyPI is an unrelated project) |
| Source code scanning (known defect in 5.28.0: ruleset unavailable) | `pip install semgrep` |
| AWS connector | Included in base install (boto3 is a core dependency) |
| Azure connector | Included in base install (azure-identity and azure-keyvault-* are core dependencies) |

### Why `[all]` excludes `[identity]`

The `[identity]` extra pulls `impacket`, which transitively depends on `pyOpenSSL`. `[all]`
intentionally **excludes `[identity]`** to keep the default consultant install safe.

> **The original reason for this exclusion no longer holds.** The exclusion was made because
> `impacket` pulls in `pyOpenSSL`, which was expected to downgrade `cryptography` and break the
> TLS scanner (this is recorded in `pyproject.toml`). The `pyOpenSSL` that pip resolves is 26.2.0, because `sslyze` caps `cryptography` below 47 and
> `pyOpenSSL` 26.3.0 and later require `cryptography` 49 or newer. 26.2.0 requires `cryptography>=46.0.0,<49`, a floor above this project's
> `>=44.0` base pin. Measured on 2026-10-12 in a fresh virtualenv holding `[all,hw,kafka,api,identity]`:
> `cryptography` resolved to 46.0.7 and `pip check` reported no broken requirements.
>
> The exclusion is **kept** as a conservative default. What changed is that the two-venv
> split below is now a **fallback, not a requirement**.

**Try one virtualenv first.** On current dependency versions you can usually install everything
together:

```bash
pip install -e '.[all,hw,api,identity]'
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


---

## Verify Installation

```bash
quirk --help         # Should show scan options
quirk serve --help   # Should show serve options
```

If both commands display help output, the console scripts are installed. That does not prove
reports render; the fresh-install validation script under **Verify properly** above checks that.

> **Coverage advisories.** When a scanner you enabled cannot run because its optional extra is
> missing (for example Kerberos without `[identity]`, AD CS or S/MIME without `[adcs]`, or GCP,
> Kubernetes or Vault without `[cloud]`), QUIRK records an INFO finding titled "Scanner skipped —
> optional extra not installed" instead of crashing. The `[dashboard]`, `[cbom]` and `[tickets]`
> checks run on every scan, and one advisory can stand for several scanners: `[cloud]` gives a single
> one for GCP, Kubernetes and Vault. Not every extra is covered: without `[hw]` the SNMP, Modbus and BACnet
> probes give no advisory (SNMP only logs a message), and `--openapi-spec` without `[api]` produces an INFO record that is not a finding. Each
> advisory names the extra (or, for nmap, the binary) to install so you can opt in to that capability
> without re-installing the world. The PyPI distribution is `quirk-scanner`, so install it as
> `pip install 'quirk-scanner[<extra>]'`. The advisory prints that same command.

---

## Next Steps

- [Getting Started](getting-started.md) — install and run your first scan from the dashboard
- [Configuration Reference](configuration.md) — all `config.yaml` options
- [Connector Guides](connectors/) — AWS, Azure, Docker, Git
