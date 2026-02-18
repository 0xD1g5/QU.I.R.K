# QuRisk Platform
A scanner that will review encryption used in an environment and identify concerns for when quantum computers become stable.  This application will be developed in Python for easy scale and modifiations.

# Plan and Roadmap
This will start as a headless scanner and then we will add UI elements for easier use later on in development.

## First Objectives
* a working scanner
* a repeatable data model
* credible reports
* a path to UI defined

# High Level Application Model
```
quantum-crypto-scanner/
├── scanner/              # Network + endpoint discovery
│   ├── tls_scanner.py
│   ├── ssh_scanner.py
│   ├── cert_parser.py
│   └── collector.py
├── engine/               # Normalization + risk logic
│   ├── models.py
│   ├── normalize.py
│   ├── quantum_risk.py
│   └── rules.yaml
├── api/                  # Optional REST API (future UI)
│   ├── main.py
│   └── routes.py
├── reports/              # Report generation
│   ├── executive.py
│   ├── technical.py
│   └── templates/
├── data/
│   └── scanner.db        # SQLite for MVP (Postgres later)
├── config.yaml
├── requirements.txt
└── run_scan.py
```
# Target Architecture
```
Discovery
   ↓
Scanning
   ↓
Crypto Posture Model
   ↓
Assessment Engine
   ↓
Outputs
  • Readiness Score
  • Transition Roadmap
  • Migration Guidance
  • Executive Narrative
```
