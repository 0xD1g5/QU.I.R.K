# Getting Started

Zero to first scan in under 10 minutes.

---

## 3-step quickstart

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install 'quirk-scanner[all]'
quirk init
quirk --config config.yaml
```

> **Use a venv + quote the extras.** Debian-based distros (Ubuntu 23.04+, Kali, Parrot) enforce [PEP 668](https://peps.python.org/pep-0668/) and reject a bare `pip install` with `externally-managed-environment`; the `.venv` avoids this. zsh (default on macOS, Kali, Parrot) treats an unquoted `[all]` as a glob and fails with `no matches found`, so keep the quotes. Full Parrot/Kali steps: [Installation → Parrot OS / Kali / Debian](installation.md#parrot-os--kali--debian-pep-668).

What each command does:

1. **`pip install 'quirk-scanner[all]'`** — installs the QU.I.R.K. distribution from PyPI (distribution name is `quirk-scanner`; the installed CLI binary is `quirk`). The `[all]` extra pulls in cloud (AWS, Azure, GCP), CBOM, database, motion (SMTP/IMAP/AMQP/Kafka TLS), Redis, dashboard, AD CS, DOCX, notification, and ticketing support. It excludes `[identity]` (impacket downgrades cryptography), `[api]` (schemathesis active fuzzer is opt-in), and `[hw]` (pysnmp hardware scanning is opt-in due to dependency size). Wheels are Sigstore-attested via PyPI Trusted Publishers; verify with `gh attestation verify` (see [release-process.md](release-process.md)).
2. **`quirk init`** — writes a starter `config.yaml` to the current directory with sensible defaults pre-populated with the `127.0.0.1` loopback target. Edit the `targets` section to point at your network before running a real scan.
3. **`quirk --config config.yaml`** — runs the scan against the configured targets. For a single host this completes in under 30 seconds; cloud scans take longer depending on account size. Results are written to `./quirk-output/`.

Once the scan is finished, run `quirk serve` and open [http://localhost:8512](http://localhost:8512) to browse the dashboard.

---

## Prerequisites

Before you begin:

- **Python 3.10 or higher** — check with `python3 --version`
- **Docker Desktop** — optional, only needed for the [chaos lab](chaos-lab.md)
- **Homebrew** *(macOS, optional alternative to pip)* — `brew install 0xD1g5/quirk/quirk` installs into a `pipx`-style venv

---

## 1. Install

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

## 2. First Scan

`quirk init` (step 2 of the quickstart) creates `config.yaml` in the current directory:

```bash
quirk init
```

Edit the `targets` section to point at your network, then run:

```bash
quirk --config config.yaml
```

QU.I.R.K. will probe the configured targets for TLS and SSH services. For a single host this completes in under 30 seconds. Results are written to `./quirk-output/`.

---

## 3. Open the Dashboard

```bash
quirk serve
```

The dashboard opens automatically at [http://localhost:8512](http://localhost:8512). Browse findings, explore the CBOM graph, and review the quantum-readiness score.

---

## 4. Export a PDF

In the dashboard, click **Export PDF** in the top-right corner. The report is saved to your downloads folder — ready to hand to a client.

---

---

## 5. Analyze a Bearer Token (standalone)

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

## 6. Analyze an OpenAPI Spec

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

## Optional: Hardware Scanning

Hardware scanning (SNMP fingerprinting, SSH/HTTP banner analysis for vendor/model/CNSA 2.0
tier classification) requires the `[hw]` extras, which are **not included** in `[all]` due to
the size of the pysnmp dependency:

```bash
pip install 'quirk-scanner[hw]'
```

With `[hw]` installed, QU.I.R.K. will probe network devices via SNMP (sysDescr, sysName,
sysObjectID) in addition to SSH banner and HTTP management interface fingerprinting, classifying
each discovered device with a CNSA 2.0 remediation tier.

---

## Next Steps

- [Installation](installation.md) — full install options, Windows WSL, system requirements
- [Configuration Reference](configuration.md) — all `config.yaml` options and CLI flags
- [Connector Guides](connectors/) — scan AWS, Azure, Docker containers, or Git repos
- [Upgrade Guide](upgrade-guide.md) — moving from v4.x to v4.10 (`quirk db migrate`)
- [Sample CBOM fixtures](../examples/) — deterministic CBOM outputs to inspect without running a scan
