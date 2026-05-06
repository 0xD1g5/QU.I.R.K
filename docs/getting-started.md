# Getting Started

Zero to first scan in under 10 minutes.

---

## Prerequisites

Before you begin:

- **Python 3.10 or higher** — check with `python3 --version`
- **git**
- **Docker Desktop** — optional, only needed for the [chaos lab](chaos-lab.md)

---

## 1. Install

Clone the repository and install in editable mode:

```bash
git clone <your-repo-url>
cd quirk
pip install -e .
```

For dashboard support (PDF export, web UI):

```bash
pip install -e '.[dashboard]'
playwright install chromium   # Required for PDF export — one-time step
```

Verify the install:

```bash
quirk --help
```

---

## Quick Start

After installation, generate a starter configuration:

```bash
quirk init
```

This creates `config.yaml` in the current directory with sensible defaults.
Edit the `targets` section with your network, then run:

```bash
quirk --config config.yaml
```

Your reports will appear in `./quirk-output/`.

---

## 2. First Scan

Generate a config file and edit it for your environment:

```bash
quirk init
```

This creates `config.yaml` pre-populated with the `127.0.0.1` loopback target. Edit the `targets` section to point at your network, then run:

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
