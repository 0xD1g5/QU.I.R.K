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

```bash
git clone <repo-url>
cd quirk
python -m venv .venv && source .venv/bin/activate
pip install -e '.[dashboard]'
playwright install chromium   # Required for PDF export — one-time step
```

> **Note (coming in v4.0):** Once published to PyPI, the install will be:
> ```
> pip install 'quirk[dashboard]'
> ```
> For now, use the git clone path above.

Verify the install:

```bash
quirk --help
```

---

## 2. First Scan

Create a `config.yaml` in your working directory:

```yaml
assessment:
  name: "First Scan"
  data_classification: "internal"
  report_owner: "My Org"
  timezone: "America/New_York"
targets:
  cidrs: [127.0.0.1]
```

Run the scan:

```bash
quirk --config config.yaml
```

QU.I.R.K. will probe `127.0.0.1` for TLS and SSH services. For a single host this completes in under 30 seconds. Results are written to `./output/`.

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
