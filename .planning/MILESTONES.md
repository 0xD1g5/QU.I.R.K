# Milestones

## v3.9 Gap Closure (Shipped: 2026-04-04)

**Phases completed:** 13 phases, 40 plans, 75 tasks

**Key accomplishments:**

- Consolidated writer.py onto single intelligence-layer scoring path and fixed cert_pubkey_alg field extraction bug — both were silent data quality blockers
- Threaded SSH scanner with ssh-audit subprocess integration storing full KEX/hostkey/MAC JSON in new ssh_audit_json column, replacing sequential banner-only scan
- One-liner:
- Full qcscan -> quirk rename with pyproject.toml: zero remaining qcscan/QuRisk references in .py files, all 56 tests pass, `python3 -c "import quirk; print(quirk.__version__)"` prints 3.9.0
- classify_algorithm() lookup table mapping 50+ algorithm strings from TLS/SSH/cert scanners to CycloneDX CryptoPrimitive enum values and NIST PQC quantum security levels via cyclonedx-python-lib 11.7.0
- CycloneDX Bom builder with TLS cipher suite decomposition, SSH kex/key/enc/mac parsing, certificate components, and bom_ref deduplication via in-memory registry
- CycloneDX 1.6 JSON+XML file output with write_cbom_files() wired into write_reports() as step 5, producing cbom-{stamp}.cdx.{json,xml} alongside every scan run
- CryptoEndpoint extended with four JSON blob columns (jwt/container/source/cloud), ConnectorsCfg extended with Phase 3 flags and cloud config, all eight Phase 3 dependencies installed, and Wave 0 test scaffolds defining contracts for SCAN-03 through SCAN-07
- Three new CryptoEndpoint-producing scanners (JWT/JWKS via httpx, container images via syft, source code via semgrep) expanding QU.I.R.K. from 2 to 5 scan surfaces with graceful degradation when tools are absent
- AWS boto3 connector (ACM/KMS/CloudFront/ELBv2) and Azure SDK connector (KeyVault/AppGateway) with paginator-based enumeration and graceful SDK degradation
- quirk/cbom/classifier.py
- 4 FastAPI JWT microservices (RS256/2048-bit, HS256-weak/128-bit, RSA-1024, alg:none) deployed as docker-compose jwt profile on ports 20001-20004 with JWKS + /token endpoints matching SCAN-03 scanner field expectations
- Docker Registry v2 profile on port 20005 with 3 seeded test images containing openssl, cryptography==2.9.2, and pyOpenSSL==19.1.0 that Syft's CRYPTO_LIB_ALLOWLIST will detect
- Gitea instance seeded with 3 repos (Python/Go/Java) covering all 4 D-08 crypto anti-pattern categories for semgrep p/cryptography validation
- LocalStack KMS + HashiCorp Vault transit engine + postgres-pgcrypto storage profile with 5 Docker Compose services seeded with real crypto key material for scanner validation
- ubuntu:18.04 OpenSSH ssh-weak service (port 20022) with group1-sha1/ssh-dss/hmac-md5 weak config, osixia/openldap ldaps service (port 636) with TLS via modern.crt, and expected_results_v3.md updated with all 6 Phase 4 scanner oracle sections
- One-liner:
- GET /api/scan/latest endpoint wired to SQLite intelligence functions, with Executive (5 arc gauges + severity chart), Findings (TanStack Table + Sheet), and Certificate Inventory (expiry color-coded + quantum-safety badges) pages
- Cytoscape.js CBOM bipartite graph and migration DAG pages with shadcn/ui table, full route wiring in App.tsx
- POST /api/export/pdf Playwright headless PDF generation from /print React page with white-bg print layout and graceful 503 degradation when chromium absent
- README fully replaced and docs/getting-started.md + docs/installation.md written: zero-to-first-scan consultant path in under 10 minutes covering macOS, Linux, and Windows WSL
- Complete config.yaml and CLI flag reference in docs/configuration.md — all 6 top-level blocks, scan profiles, score profiles, and copy-pasteable minimal and full config templates
- Four copy-paste-ready connector guides covering AWS IAM policy (7 actions), Azure RBAC roles, Syft-based container scanning, and semgrep p/cryptography source scanning — all permissions derived from the actual connector source code.
- Consultant-facing report interpretation guide with exact scoring thresholds, all four subscore driver tables, severity tier definitions, and Client Conversation sideboxes for live client meetings
- Three-section CBOM guide for compliance officers, consultants, and auditors — covering what a CBOM is, QU.I.R.K.'s five-step CycloneDX pipeline, and copy-pasteable audit language for NIST SP 800-208, CNSA 2.0, and ISO 27002:2022
- Authoritative chaos lab operator guide covering all 10 profiles (core through ldaps) with per-profile port matrices, copy-pasteable start commands, and connector config snippets
- One-liner:
- Rich Panel startup banner, --version/--quiet flags, and rich scan summary table replacing tqdm/print output in QU.I.R.K. CLI
- quirk/reports/html_renderer.py
- SVG redesigned:
- Version bumped to 4.0.0 across __init__.py, pyproject.toml, and writer.py; quirk init implemented using importlib.resources with bundled config_template.yaml; getting-started.md updated to git+https install path
- 1. [Rule 1 - Bug] Cleaned stale version tag in code comment
- Removed enable_windows_adcs from ConnectorsCfg and interactive.py; added JWT/container/source scanner prompts with correct AWS/Azure labels
- One-liner:
- One-liner:
- PROFILE_MULTIPLIERS constant (strict=1.4x, balanced=1.0x, lenient=0.7x) added to compute_readiness_score() with prefix-based agility/identity weight scaling, plus 7 Wave 0 expectedFailure stubs for executive.py migration
- executive.py fully migrated from assessment/ imports to intelligence call sequence with ported _build_interpretation(), NOW/NEXT/LATER roadmap, and profile+calibration wired at both call sites
- One-liner:
- Added `dashboard/static/
- Two-line fix closes GAP-INT-01 and GAP-INT-02: deps.py default db_path aligned to './quirk.db' (config_template.yaml) and server.py now sets QUIRK_SERVE_PORT before uvicorn starts so PDF export inherits the correct port
- SSH algorithm parsing added to _derive_cbom() in scan.py: kex/key/enc/mac sections from ssh_audit_json now produce classified CbomComponent entries in the dashboard CBOM viewer, closing GAP-INT-03

---
