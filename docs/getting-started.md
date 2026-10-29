# Getting Started

From install to first scan in three steps, using the dashboard.

---

## Quickstart: the dashboard

```bash
python3.12 -m venv .venv && source .venv/bin/activate   # any of python3.10 ... python3.14
pip install 'quirk-scanner[all]'
playwright install chromium    # needed for the PDF report; one-time download
quirk serve
```

QU.I.R.K. supports Python 3.10 to 3.14 (3.15 is not supported yet); `python3.12` is only an example. On Linux, also run `playwright install-deps chromium` once (see [Installation](installation.md#linux-ubuntu--debian)).

> **Use a venv + quote the extras.** Debian 12, Kali (2024.4 and later), and other distributions that mark their system Python as "externally managed" ([PEP 668](https://peps.python.org/pep-0668/)) reject a bare `pip install` with `externally-managed-environment`; the `.venv` avoids this. zsh treats an unquoted `[all]` as a glob and fails with `no matches found`, so keep the quotes. Full Parrot/Kali steps: [Installation → Parrot OS / Kali / Debian](installation.md#parrot-os--kali--debian-pep-668).

What each step does:

1. **`pip install 'quirk-scanner[all]'`** — installs the QU.I.R.K. distribution from PyPI (distribution name is `quirk-scanner`; the installed CLI binary is `quirk`). The `[all]` extra pulls in cloud (GCP, Kubernetes, HashiCorp Vault, and Azure Blob storage and AKS; AWS and Azure Key Vault support is already in the base install), CBOM, database, motion (SMTP/IMAP/AMQP/Kafka TLS), Redis, dashboard, AD CS, DOCX, notification, and ticketing support. It excludes `[identity]` (impacket; kept out as a conservative default, see [Why `[all]` excludes `[identity]`](installation.md#why-all-excludes-identity)), `[api]` (schemathesis active fuzzer is opt-in), and `[hw]` (pysnmp hardware scanning is opt-in). Wheels are Sigstore-attested via PyPI Trusted Publishers; verify with `pypi-attestations`, as described in [release-process.md](release-process.md#attestation-verification-for-downstream-consumers).
2. **`quirk serve`** — starts the dashboard on `127.0.0.1:8512` by default (change with `--host` and `--port`) and opens it in your browser; pass `--no-open` to skip the browser. On the default loopback address no API token is needed. Run it from the directory where you want scan output kept: the dashboard keeps its database at `./quirk-output/quirk.db`.
3. **Click New Scan** (the button at the top of the sidebar), enter the targets to scan (IPs, CIDR ranges or hostnames, comma-separated), choose a scan profile, and start the scan. The dashboard shows live progress, then findings, the CBOM graph and the quantum-readiness score when it finishes (the score shows as a dash when the scan found nothing it could score).

The command line is fully supported and suits scripted or scheduled scans: see section 3 below.

---

## Prerequisites

Before you begin:

- **Python 3.10 to 3.14** (3.15 is not yet supported: a dependency, nassl, ships no 3.15 build) — check with `python3 --version`
- **Docker** — optional; needed only to run the [chaos lab](chaos-lab.md) (Docker Desktop on macOS and Windows, Docker Engine with the Compose plugin on Linux)

---

## 1. Install

The PyPI install in the quickstart above is the recommended path. For developers contributing to QU.I.R.K., an editable install is documented in the root `README.md` under *Develop from source*.

For dashboard support and PDF export (already included in `[all]`):

```bash
pip install 'quirk-scanner[all]'
playwright install chromium   # Required for PDF export — one-time step
```

On Linux, Chromium also needs system libraries: run `playwright install-deps chromium` once. Run it without `sudo`: it asks for sudo permissions itself. See [Installation](installation.md#linux-ubuntu--debian).

Verify the install:

```bash
quirk --help
```

---

## 2. First Scan in the dashboard

With `quirk serve` running (see the quickstart), open **New Scan** from the sidebar:

- **Targets** — one or more IPs, CIDR ranges or hostnames, for example `192.168.1.0/24, api.example.com`.
- **Scan Profile** — Quick, Standard or Deep.
- **Calibration** — Strict, Balanced or Lenient scoring calibration.
- **Port Scope** — Top 1000 ports, Common TLS ports, All ports, or a Custom port list.

Start the scan and the dashboard follows it live. When it finishes, browse findings, explore the CBOM graph, and review the quantum-readiness score on the home page.

---

## 3. Scripted scans from the CLI

The CLI is fully supported and drives the same scanner the dashboard does. Use it for scripted, scheduled or CI scans. `quirk init` creates `config.yaml` in the current directory:

```bash
quirk init
```

It pre-fills the `127.0.0.1` loopback target. Edit the `targets` section to point at your network, then run:

```bash
quirk --config config.yaml
```

QU.I.R.K. will probe the configured targets for TLS and SSH services. The default `127.0.0.1` target completes in a few seconds. Results are written to `./quirk-output/`. Run `quirk serve` afterwards to browse them in the dashboard.

**Re-checking known hardware between full scans?** If you've already fingerprinted a hardware
fleet (§ Optional: Hardware Scanning below) and just want to see whether anything drifted, use
the lightweight `--check-in` re-probe instead of a full re-scan:

```bash
quirk --config config.yaml --check-in
```

It re-probes only the devices QU.I.R.K. already knows about and never produces a new readiness
score — see `docs/operators-guide.md` §9.9 for the full behavior.

---

## 4. Reports and PDF export

A scan writes its report files (HTML, DOCX and the CBOM as JSON and XML, plus a PDF once the Chromium step from section 1 has been done) to disk:

- **CLI scans** write them to the output directory in `config.yaml`, `./quirk-output/` by default.
- **Scans started from New Scan** write them to `output/jobs/<job-id>/`, relative to the directory where you ran `quirk serve`.

On the dashboard home page, the buttons in the page header download the newest report files found in the output directory of the `config.yaml` in the directory where `quirk serve` is running, which is where CLI scans put them. A button is greyed out, with the reason as a tooltip, when its file does not exist. These buttons do not list reports from scans started with New Scan; open those files from `output/jobs/<job-id>/` on disk.

**Export PDF**, in the same page header, is a separate feature: it prints the dashboard's own print view to a PDF and saves it to your browser's downloads folder as `quirk-report-<date>.pdf`. It needs the one-time Chromium step from section 1. It is a snapshot of the dashboard view, not the generated report file.

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

- **`alg:none` detection** — tokens with algorithm `none` (case-insensitive: `none`, `NONE`, `None`, `NonE`) exit with code `1`, and in text mode print a **CRITICAL** banner (`--json` mode exits `1` without the banner). A token with no `alg` header at all is treated the same way. This lets you fail a pipeline on a dangerous unsigned token:
  ```bash
  quirk analyze-token @/tmp/token.txt || { echo "Token rejected — CRITICAL finding"; exit 1; }
  ```
- **Opaque tokens** — if the input is not a recognizable JWT (e.g. an API key or opaque session token), the command prints an INFO message and exits `0`. It does not error out.
- **`--json` output** — emits a JSON object with keys: `alg`, `is_alg_none`, `is_alg_missing`, `expired`, `exp`, `nist_level`, `quantum_safety`.
- **No DB writes** — the command does not write to `quirk.db` and does not echo or log the token value.

---

## 6. Analyze an OpenAPI Spec

Pass `--openapi-spec` to include an OpenAPI/Swagger spec in a scan. QUIRK inventories the spec's declared security schemes, plaintext `http://` server URLs, and unauthenticated path operations:

```bash
# Local file (default; no network required)
quirk --config config.yaml --openapi-spec path/to/openapi.yaml

# URL whose host is one of your configured targets.fqdns (scope-gated; other hosts are rejected)
quirk --config config.yaml --openapi-spec https://api.acme.com/openapi.json
```

**Security hardening applied by the scanner:**

- **SSRF guard** — any `$ref` that is not an intra-document reference (`#/...`), such as `http://169.254.169.254/`, raises a `SpecParsingError` *before* the validator sees the document. No outbound request is made. The scan logs the error and continues without spec findings.
- **10 MB size cap** — specs larger than 10 MB are rejected before parsing. This is a size guard against oversized-spec denial of service.
- **Scope gate** — the host of the spec URL you pass must equal a configured `targets.fqdns` entry; any other host is rejected before any network request. A host that resolves to a private or loopback address is also rejected unless you pass `--allow-internal-targets`. The spec fetch follows at most 5 redirects, and each hop must pass the same host-scope gate and URL check.
- **Graceful degradation** — if the `[api]` extras group is not installed, the scanner returns a single INFO record marked `missing_extra` (it produces no finding) and the scan continues; no error is raised.

Install the `[api]` extras group to enable spec validation:

```bash
pip install "quirk-scanner[api]"
# installs openapi-spec-validator (spec validation) + schemathesis (active REST fuzzing)
```

> **Note:** `pip install 'quirk-scanner[all]'` does **not** include `[api]` — the `[api]` group bundles `schemathesis`, an active REST fuzzer that requires explicit operator opt-in, so it is deliberately kept out of `[all]`.

---

## Optional: Hardware Scanning

Hardware fingerprinting (SSH banner and HTTP management-interface analysis for
vendor/model/CNSA 2.0 tier classification) needs no extra package. SNMP fingerprinting
requires the `[hw]` extras, which are **not included** in `[all]` because pysnmp is an
explicit opt-in:

```bash
pip install 'quirk-scanner[hw]'
```

With `[hw]` installed and SNMP enabled (the `--enable-snmp` flag, or `enable_snmp` under
`connectors` in `config.yaml`), QU.I.R.K. will probe network devices via SNMP (sysDescr, sysName,
sysObjectID) in addition to SSH banner and HTTP management interface fingerprinting. In a full
scan, devices fingerprinted from an SSH banner or HTTP management interface are classified with a
CNSA 2.0 remediation tier. A device found only through SNMP, and a device re-probed by `--check-in`,
is not classified yet: it is stored with the label `Tier N/A`, which otherwise means end-of-life
before 2030, so read that label with care.

Fingerprinted devices whose vendor was identified are also checked against QU.I.R.K.'s curated,
NVD-cited firmware CVE catalog — an advisory-only signal that never affects your readiness score. See
`docs/operators-guide.md` §9.5 for details.

---

## Catalog Status Commands

QU.I.R.K. ships several curated data catalogs (compliance mappings, QRAMM governance model,
firmware CVE table), each with its own `status` command to confirm freshness before a client
engagement:

```bash
quirk compliance status   # PCI-DSS/HIPAA/FIPS 140-3/SOC2/ISO 27001 mapping freshness
quirk qramm status        # QRAMM CSNP governance model freshness
quirk cve status          # firmware CVE catalog freshness (30-day cadence)
```

`quirk qramm status` and `quirk cve status` print a `Last Verified` date and a FRESH/STALE
verdict, and exit `1` if stale — safe to wire into pre-engagement scripts or CI.
`quirk compliance status` prints each framework's version, `Last Verified` date and source URL,
and prints a warning above the table when a mapping is stale, but it always exits `0`.

---

## Report Branding Quickstart

Want your firm's logo and client name on the report cover instead of the default look? Add a
`report:` block to `config.yaml` (see the report block in the [Configuration Reference](configuration.md)),
or save it once and reuse it on every future engagement:

```bash
quirk report profile save housestyle --config config.yaml
quirk --config config.yaml --report-profile housestyle
```

---

## Next Steps

- [Installation](installation.md) — full install options, Windows WSL, system requirements
- [Configuration Reference](configuration.md) — all `config.yaml` options and CLI flags
- [Connector Guides](connectors/) — scan AWS, Azure, Docker containers, or Git repos
- [Upgrade Guide](upgrade-guide.md) — moving from v4.10 or later to the latest release (`quirk db migrate`)
- [Sample CBOM fixtures](../examples/) — sample CBOM outputs to inspect without running a scan
