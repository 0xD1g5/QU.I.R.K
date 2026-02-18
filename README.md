# Quantum Crypto Scanner (qcscan)

Agentless crypto discovery + quantum readiness reporting (MVP).

## What it does (v1)
- Scans TLS endpoints (CIDRs and FQDNs)
- Extracts certificate metadata (subject/issuer/SAN, sig algorithm, key type/size, validity)
- Produces initial findings (TLS deprecations, expiring certs, quantum-transition flags)
- Writes reports (JSON + Markdown) to ./output
- Stores endpoint inventory in SQLite (./data/qcscan.sqlite)

## Quick start
```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
python run_scan.py
```

## Configure targets
Edit `config.yaml`:
- Add CIDRs / FQDNs
- Adjust ports and concurrency
- Enable connectors later (AWS/Azure/AD CS stubs provided)

## Output
Reports are generated in `./output/`:
- findings-<timestamp>.json
- executive-summary-<timestamp>.md
- technical-findings-<timestamp>.md

## Notes
- This MVP uses **agentless** TLS scanning with optional SNI.
- Some endpoints may refuse connections or require client auth; those are logged as INFO scan errors.
- Future increments: SSH scanning, cipher-suite enumeration, AWS/Azure/ADCS connectors, HTML/PDF reporting.
