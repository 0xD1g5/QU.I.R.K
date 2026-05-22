# Getting Started

Zero to first scan in under 10 minutes.

---

## 3-step quickstart

```bash
pip install quirk-scanner[all]
quirk init
quirk --config config.yaml
```

What each command does:

1. **`pip install quirk-scanner[all]`** — installs the QU.I.R.K. distribution from PyPI (distribution name is `quirk-scanner`; the installed CLI binary is `quirk`). The `[all]` extra pulls in cloud (AWS, Azure, GCP), database, motion (SMTP/IMAP/AMQP/Kafka TLS), Redis, and dashboard support. Wheels are Sigstore-attested via PyPI Trusted Publishers; verify with `gh attestation verify` (see [release-process.md](release-process.md)).
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
pip install quirk-scanner[all]
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

## Next Steps

- [Installation](installation.md) — full install options, Windows WSL, system requirements
- [Configuration Reference](configuration.md) — all `config.yaml` options and CLI flags
- [Connector Guides](connectors/) — scan AWS, Azure, Docker containers, or Git repos
- [Upgrade Guide](upgrade-guide.md) — moving from v4.x to v4.10 (`quirk db migrate`)
- [Sample CBOM fixtures](../examples/) — deterministic CBOM outputs to inspect without running a scan
