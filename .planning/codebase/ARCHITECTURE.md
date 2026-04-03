# Architecture

**Analysis Date:** 2026-04-02

## Pattern Overview

**Overall:** Pipeline/Layered — a CLI-driven scan pipeline feeds a SQLite store, which is read
by both a file-output report layer and an optional FastAPI + React dashboard.

**Key Characteristics:**
- Single orchestrator (`run_scan.py`) drives the full scan lifecycle; no dependency injection
- All scanner modules return lists of `CryptoEndpoint` ORM objects — the shared data contract
- Intelligence/scoring is intentionally isolated from scan execution; scores are computed only
  during report generation
- Dashboard is strictly read-only against the database; it does not trigger scans

---

## Layers

**CLI / Entry Point:**
- Purpose: Parse arguments, coordinate config, sequence scan phases, call report layer
- Location: `run_scan.py` (root, 509 lines)
- Contains: All scan phase orchestration, timer wrappers, argparse for `init`, `serve`, and scan
- Depends on: All scanner modules, engine, reports, DB, config, CLI helpers
- Used by: `pyproject.toml` entry point `quirk = "run_scan:main"`

**Config:**
- Purpose: Load and validate YAML config; provide typed dataclasses to all layers
- Location: `quirk/config.py`, `quirk/interactive.py`
- Contains: `AppConfig`, `ScanCfg`, `TargetsCfg`, `ConnectorsCfg`, `OutputCfg`, `IntelligenceCfg`
- Depends on: PyYAML
- Used by: run_scan.py, all scanner modules, reports, dashboard API

**Persistence:**
- Purpose: SQLite-backed ORM storage for all scan results
- Location: `quirk/db.py`, `quirk/models.py`
- Contains: SQLAlchemy engine/session helpers; `CryptoEndpoint` ORM model (single table)
- Depends on: SQLAlchemy 2.0
- Used by: run_scan.py (write path), `quirk/dashboard/api/routes/scan.py` (read path)

**Discovery:**
- Purpose: Expand config targets to (host, port) pairs; optional nmap pre-scan
- Location: `quirk/discovery/nmap_provider.py`, `quirk/discovery/nmap_parser.py`
- Contains: nmap subprocess wrapper + XML parser; builtin expansion in `quirk/scanner/target_expander.py`
- Depends on: nmap binary (optional, only for `--discovery nmap` mode)
- Used by: run_scan.py only

**Scanner (active probing):**
- Purpose: Per-protocol cryptographic inspection; produce `CryptoEndpoint` objects
- Location: `quirk/scanner/` — 10 files
  - `tls_scanner.py` — primary TLS scanner with sslyze optional deep mode (478 lines)
  - `tls_capabilities.py` — TLS enumeration helper used by tls_scanner
  - `ssh_scanner.py` — SSH audit via ssh-audit subprocess
  - `fingerprint.py` — Protocol fingerprinting (TLS / SSH / HTTP / closed)
  - `target_expander.py` — Builtin target list expander (FQDN, CIDR, IP)
  - `jwt_scanner.py` — JWKS endpoint crawler
  - `container_scanner.py` — syft-based container image scanner
  - `source_scanner.py` — semgrep-based source code scanner
  - `aws_connector.py` — AWS ACM/KMS/ELB scanner (boto3)
  - `azure_connector.py` — Azure Key Vault/network scanner (azure-sdk)
- Depends on: cryptography, sslyze (optional), boto3, azure-sdk, httpx
- Used by: run_scan.py only

**Engine:**
- Purpose: Post-scan risk evaluation, scoring calibration, caching, rate limiting
- Location: `quirk/engine/` — 6 files
  - `risk_engine.py` — Evaluates all endpoints → findings list with severity
  - `profiles.py` — Applies quick/standard/deep scan profile overrides to `cfg.scan`
  - `cache.py` — JSON file cache for discovery and fingerprint phases
  - `rate_limiter.py` — Token bucket for rate-limited scans
  - `migration_planner.py` — Simple NOW/NEXT/LATER wave categoriser (used by writer.py only)
  - `rules.py` — Stub only; reserved for future YAML-driven rule engine
- Depends on: quirk.models, quirk.config
- Used by: run_scan.py, quirk/reports/writer.py

**Intelligence:**
- Purpose: Canonical scoring, confidence, evidence, and roadmap computation for reports
- Location: `quirk/intelligence/` — 7 files
  - `scoring.py` — Weighted `compute_readiness_score()` (the authoritative scorer)
  - `confidence.py` — `compute_confidence()` coverage/blocker analysis
  - `evidence.py` — `build_evidence_summary()` — structured evidence dict
  - `roadmap.py` — `build_phased_roadmap()` — wave-ordered remediation items
  - `calibration.py` — Score calibration overrides (lenient/balanced/strict)
  - `schema.py` — Frozen dataclasses: `ScoreInputs`, `ScoreResult`, `ConfidenceResult`, `RoadmapItem`, `IntelligenceReport`
  - `driver_text.py` — Human-readable labels for score driver keys
- Depends on: none outside `quirk.intelligence`
- Used by: `quirk/reports/writer.py`, `quirk/reports/scorecard.py`, `quirk/dashboard/api/routes/scan.py`

**CBOM:**
- Purpose: Build and serialize CycloneDX Cryptography Bill of Materials
- Location: `quirk/cbom/` — 4 files
  - `builder.py` — `build_cbom()` traverses endpoints → CycloneDX component tree (522 lines)
  - `classifier.py` — `classify_algorithm()`, `quantum_safety_label()` — per-algorithm tagging
  - `writer.py` — `write_cbom_files()` — outputs JSON + XML
  - `__init__.py` — re-exports all three public functions
- Depends on: cyclonedx-python-lib
- Used by: `quirk/reports/writer.py`, `quirk/dashboard/api/routes/scan.py`

**Reports:**
- Purpose: Materialise all output artefacts from scan results
- Location: `quirk/reports/` — 6 files
  - `writer.py` — Orchestrates all report outputs (JSON, Markdown, HTML, PDF, CBOM)
  - `executive.py` — Executive summary Markdown builder
  - `technical.py` — Technical report Markdown builder
  - `scorecard.py` — Scorecard section builder
  - `html_renderer.py` — Jinja2 HTML + Playwright PDF renderer
  - `templates/` — `.j2` Jinja2 templates
- Depends on: quirk.intelligence, quirk.cbom, quirk.assessment, jinja2, playwright (optional)
- Used by: run_scan.py

**Assessment (legacy scoring path — partially superseded):**
- Purpose: First-generation scoring and planning; still used by `executive.py` and `technical.py`
- Location: `quirk/assessment/` — 6 files
  - `readiness_score.py` — `compute_readiness_score()` — older dict-returning scorer
  - `confidence.py` — Older confidence scorer (returns dict, not dataclass)
  - `transition_planner.py` — Wave-based roadmap text generator
  - `migration_advisor.py` — Migration path recommender
  - `interpretation_engine.py` — Narrative interpretation builder
  - `operator_context.py` — Interactive context prompts + context attachment
- Depends on: None outside `quirk.assessment`
- Used by: `quirk/reports/executive.py`, `quirk/reports/technical.py`, `run_scan.py`
  (writer.py and scorecard.py explicitly do NOT use assessment — see CONCERNS)

**Dashboard (backend):**
- Purpose: FastAPI app serving scan results and CBOM data to the React frontend
- Location: `quirk/dashboard/` — `server.py`, `api/app.py`, `api/deps.py`, `api/schemas.py`, `api/routes/`
  - `server.py` — uvicorn launcher invoked by `quirk serve`
  - `api/app.py` — FastAPI factory; mounts API routes, static assets, SPA catch-all
  - `api/deps.py` — DB session dependency injection
  - `api/routes/scan.py` — All scan/findings/CBOM data endpoints (14,816 bytes)
  - `api/routes/health.py` — Health check endpoint
  - `api/routes/pdf.py` — PDF export endpoint (calls html_renderer)
  - `static/` — Vite build output (committed build artefacts land here)
- Depends on: fastapi, uvicorn, quirk.db, quirk.models, quirk.intelligence, quirk.cbom
- Used by: `quirk serve` subcommand

**Dashboard (frontend):**
- Purpose: React SPA for interactive scan result exploration
- Location: `src/dashboard/` — Vite + React + shadcn/ui + Tailwind
  - `src/App.tsx` — BrowserRouter with 6 routes
  - `src/pages/` — executive.tsx, findings.tsx, certificates.tsx, cbom.tsx, roadmap.tsx, print.tsx
  - `src/components/` — sidebar.tsx, gauges/, ui/ (shadcn), theme-provider.tsx
  - Builds to: `quirk/dashboard/static/` (via `vite.config.ts outDir`)
- Depends on: react-router-dom, recharts, cytoscape, @tanstack/table, lucide-react, shadcn/ui
- Used by: FastAPI SPA catch-all route

**CLI Helpers:**
- Purpose: Banner display, `init` subcommand
- Location: `quirk/cli/` — `banner.py`, `init_cmd.py`
- Depends on: rich
- Used by: run_scan.py

---

## Data Flow

**CLI Scan Flow:**

1. `run_scan.main()` parses args, loads/prompts config
2. `apply_profile()` adjusts `cfg.scan` defaults
3. Target discovery: `expand_targets(cfg)` or `run_nmap_discovery()` → `List[Tuple[str,int]]`
4. Fingerprinting: `fingerprint_service()` per target (ThreadPoolExecutor) → protocol classification
5. Per-protocol scan phases (TLS, SSH, JWT, container, source, AWS, Azure) → `List[CryptoEndpoint]`
6. `evaluate_endpoints(cfg, endpoints)` → `List[Dict]` findings with severity
7. `get_session()` → persist all endpoints to SQLite `crypto_endpoints` table
8. `write_reports(cfg, endpoints, findings, run_stats)` → JSON, Markdown, HTML, PDF, CBOM files

**Dashboard Read Flow:**

1. `quirk serve` starts uvicorn on `quirk.dashboard.api.app:app`
2. React SPA loads from `quirk/dashboard/static/`
3. All data fetched via `/api/*` routes from `quirk/dashboard/api/routes/scan.py`
4. Route handlers query SQLite directly via SQLAlchemy; compute scores/CBOM on-demand
5. PDF export via `/api/pdf` triggers Playwright headless render of `/print`

**State Management (Frontend):**
- No Redux/Zustand; React state and API calls per-page
- Theme persisted in localStorage under key `quirk-ui-theme`

---

## Key Abstractions

**CryptoEndpoint:**
- Purpose: Single ORM row representing one scanned service; shared contract across all scanner outputs
- Location: `quirk/models.py`
- Pattern: SQLAlchemy declarative model; all scanner functions accept config + target list,
  return `List[CryptoEndpoint]`. Protocol-specific data stored as JSON blobs in Text columns
  (`ssh_audit_json`, `jwt_scan_json`, `container_scan_json`, `cloud_scan_json`).

**AppConfig:**
- Purpose: Typed config tree passed to almost every function
- Location: `quirk/config.py`
- Pattern: Nested dataclasses loaded from YAML via `load_config()` or built by `interactive_config()`

**IntelligenceReport:**
- Purpose: Canonical structured output of the intelligence layer
- Location: `quirk/intelligence/schema.py`
- Pattern: Frozen dataclasses (`ScoreInputs`, `ScoreResult`, `ConfidenceResult`, `RoadmapItem`)
  assembled into `IntelligenceReport.to_dict()` / `.to_json()`

---

## Entry Points

**`quirk` (scan):**
- Location: `run_scan.py:main()`
- Triggers: `quirk` CLI command (pyproject.toml scripts entry)
- Responsibilities: Full scan pipeline; interactive or config-file driven

**`quirk init`:**
- Location: `run_scan.py:main()` → `quirk/cli/init_cmd.py:run_init()`
- Triggers: `quirk init [--output path]`
- Responsibilities: Copy `quirk/config_template.yaml` to output path

**`quirk serve`:**
- Location: `run_scan.py:main()` → `quirk/dashboard/server.py:serve()`
- Triggers: `quirk serve [--port] [--host] [--no-open]`
- Responsibilities: Launch uvicorn dashboard on port 8512 (default)

**`python -m quirk.validate`:**
- Location: `quirk/validate.py`
- Triggers: Direct Python module invocation only
- Responsibilities: Validate JSON output artefacts in an output directory

---

## Error Handling

**Strategy:** Scan errors are captured per-endpoint, not raised. Fatal config/init errors use
`sys.exit(1)`. Dashboard API errors return HTTP 4xx/5xx.

**Patterns:**
- All scanner `scan_one()` functions wrap the probe in `try/except Exception as e` and store
  `ep.scan_error = str(e)` — scan never aborts on a single endpoint failure
- `risk_engine.py` normalises and deduplicates findings; never raises
- Dashboard routes use FastAPI's exception handling; DB session cleanup via `contextmanager`

---

## Cross-Cutting Concerns

**Logging:** `quirk/logging_util.py` provides a `Logger` class wrapping `rich.console.Console`.
Verbose output gated on `Logger.v()`. Progress bars use `rich.progress`, not tqdm (tqdm removed,
`tqdm = None` placeholder remains in run_scan.py as a residual comment).

**Validation:** Config validated by dataclass `**unpacking` in `config_from_dict()` — missing
required keys raise `TypeError` at load time.

**Authentication:** None (local tool). Dashboard binds to 127.0.0.1 only by default.

---

## Dual Scoring Architecture (Key Concern)

Two parallel scoring subsystems exist:

| Layer | Location | Returns | Used by |
|-------|----------|---------|---------|
| `quirk.intelligence` | `quirk/intelligence/scoring.py` | `Dict[str,Any]` (newer, weighted) | `writer.py`, `scorecard.py`, dashboard API |
| `quirk.assessment` | `quirk/assessment/readiness_score.py` | `ReadinessScore` dataclass (older) | `executive.py`, `technical.py` |

`test_scoring_consolidation.py` enforces that `writer.py` and `scorecard.py` must NOT import
from `quirk.assessment` — but `executive.py` and `technical.py` still do. The split is live.

---

*Architecture analysis: 2026-04-02*
