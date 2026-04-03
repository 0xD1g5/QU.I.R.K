# Codebase Structure

**Analysis Date:** 2026-04-02

## Directory Layout

```
QUIRK/
├── run_scan.py                        # CLI entry point + full scan orchestrator
├── pyproject.toml                     # Package config; entry point: quirk = "run_scan:main"
├── config.yaml                        # Sample/default config (not committed as secrets)
├── quirk/                             # Main Python package
│   ├── __init__.py                    # Package version: 4.0.0
│   ├── config.py                      # Config dataclasses + YAML loader
│   ├── config_template.yaml           # Bundled template for `quirk init`
│   ├── db.py                          # SQLAlchemy engine/session helpers
│   ├── models.py                      # CryptoEndpoint ORM model
│   ├── interactive.py                 # Interactive CLI config prompts
│   ├── logging_util.py                # Logger wrapper (rich)
│   ├── validate.py                    # Output artefact validator (run as module only)
│   ├── util.py                        # Minimal utility stub
│   ├── cli/                           # CLI helpers
│   │   ├── banner.py                  # Print banner (rich)
│   │   └── init_cmd.py                # `quirk init` implementation
│   ├── scanner/                       # Active-probe scanners (all return CryptoEndpoint lists)
│   │   ├── fingerprint.py             # Protocol fingerprinting
│   │   ├── target_expander.py         # Builtin target list expansion
│   │   ├── tls_scanner.py             # TLS scanner + sslyze deep mode (478 lines)
│   │   ├── tls_capabilities.py        # TLS enumeration helper
│   │   ├── ssh_scanner.py             # SSH audit (ssh-audit subprocess)
│   │   ├── jwt_scanner.py             # JWKS endpoint scanner
│   │   ├── container_scanner.py       # Container image scanner (syft)
│   │   ├── source_scanner.py          # Source code scanner (semgrep)
│   │   ├── aws_connector.py           # AWS ACM/KMS/ELB connector (boto3)
│   │   └── azure_connector.py         # Azure Key Vault/network connector
│   ├── discovery/                     # Network discovery layer
│   │   ├── nmap_provider.py           # nmap subprocess wrapper
│   │   ├── nmap_parser.py             # nmap XML parser
│   │   ├── tls_scanner.py             # DEAD: legacy TLS scanner, never imported (111 lines)
│   │   └── coverage.py                # DEAD: primitive coverage scorer, never imported
│   ├── connectors/                    # DEAD: future connector stubs, never imported
│   │   ├── aws_stub.py                # 3-line stub (comment only)
│   │   ├── azure_stub.py              # 3-line stub (comment only)
│   │   └── windows_adcs_stub.py       # 3-line stub (comment only)
│   ├── engine/                        # Post-scan risk + operational engine
│   │   ├── risk_engine.py             # Findings evaluator + deduplicator
│   │   ├── profiles.py                # Scan profile applicator (quick/standard/deep)
│   │   ├── cache.py                   # JSON file cache (discovery + fingerprint)
│   │   ├── rate_limiter.py            # Token bucket rate limiter
│   │   ├── migration_planner.py       # Wave categoriser (NOW/NEXT/LATER)
│   │   └── rules.py                   # DEAD: 2-line stub, no implementation
│   ├── assessment/                    # Legacy scoring layer (partially superseded)
│   │   ├── readiness_score.py         # Older compute_readiness_score() → ReadinessScore dataclass
│   │   ├── confidence.py              # Older compute_confidence() → dict
│   │   ├── transition_planner.py      # Wave-based roadmap text generator
│   │   ├── migration_advisor.py       # Migration path recommender
│   │   ├── interpretation_engine.py   # Narrative interpretation builder
│   │   └── operator_context.py        # Context prompts + attachment
│   ├── intelligence/                  # Canonical scoring layer (active)
│   │   ├── __init__.py                # Re-exports all public functions
│   │   ├── schema.py                  # Frozen dataclasses (ScoreInputs, ScoreResult, etc.)
│   │   ├── scoring.py                 # compute_readiness_score() — authoritative scorer
│   │   ├── confidence.py              # compute_confidence() → ConfidenceResult
│   │   ├── evidence.py                # build_evidence_summary() → evidence dict
│   │   ├── roadmap.py                 # build_phased_roadmap() → List[RoadmapItem]
│   │   ├── calibration.py             # Score calibration (lenient/balanced/strict)
│   │   └── driver_text.py             # Human-readable score driver labels
│   ├── cbom/                          # CycloneDX CBOM generation
│   │   ├── __init__.py                # Re-exports build_cbom, write_cbom_files, classify_algorithm
│   │   ├── builder.py                 # build_cbom() (522 lines)
│   │   ├── classifier.py              # classify_algorithm(), quantum_safety_label()
│   │   └── writer.py                  # write_cbom_files() — JSON + XML output
│   ├── reports/                       # Report output layer
│   │   ├── writer.py                  # Main report orchestrator
│   │   ├── executive.py               # Executive summary Markdown
│   │   ├── technical.py               # Technical report Markdown
│   │   ├── scorecard.py               # Scorecard section builder
│   │   ├── html_renderer.py           # Jinja2 HTML + Playwright PDF
│   │   └── templates/                 # .j2 Jinja2 report templates
│   └── dashboard/                     # Web dashboard backend
│       ├── server.py                  # uvicorn launcher (`quirk serve`)
│       ├── static/                    # Vite build output (committed; auto-replaced by npm run build)
│       └── api/
│           ├── app.py                 # FastAPI factory
│           ├── deps.py                # DB session dependency
│           ├── schemas.py             # Pydantic response schemas
│           └── routes/
│               ├── scan.py            # All data endpoints (findings, certs, CBOM, score)
│               ├── health.py          # Health check
│               └── pdf.py             # PDF export
├── src/
│   └── dashboard/                     # React frontend source
│       ├── src/
│       │   ├── App.tsx                # BrowserRouter + 6 routes
│       │   ├── main.tsx               # React root
│       │   ├── pages/                 # Page components
│       │   │   ├── executive.tsx
│       │   │   ├── findings.tsx
│       │   │   ├── certificates.tsx
│       │   │   ├── cbom.tsx
│       │   │   ├── roadmap.tsx
│       │   │   └── print.tsx
│       │   ├── components/            # Shared UI components
│       │   │   ├── sidebar.tsx
│       │   │   ├── gauges/
│       │   │   └── ui/                # shadcn/ui primitives
│       │   ├── types/                 # TypeScript type definitions
│       │   └── hooks/                 # React hooks
│       ├── vite.config.ts             # Builds to ../../quirk/dashboard/static
│       ├── package.json
│       └── tailwind.config.ts
├── tests/                             # pytest test suite (165+ passing)
│   ├── conftest.py                    # Shared fixtures
│   └── test_*.py                      # 29 test files
├── quantum-chaos-enterprise-lab/      # Docker-based test lab
│   ├── docker-compose.yml             # Lab services (nginx, HAProxy, SSH, JWT, registry, etc.)
│   ├── lab.sh                         # Lab management script
│   └── expected_results_v3.md         # Expected scan results for lab
├── data/                              # Runtime data directory
│   └── _archive/                      # Legacy SQLite archive
├── output/                            # Scan output artefacts (gitignored)
│   └── .cache/                        # Discovery/fingerprint JSON cache
├── docs/                              # User-facing documentation
├── .planning/                         # GSD planning artifacts
│   ├── PROJECT.md
│   ├── ROADMAP.md
│   ├── REQUIREMENTS.md
│   ├── STATE.md
│   └── codebase/                      # Architecture docs (this directory)
└── RESTRUCTURE-AUDIT-2026-03-31.md   # Record of qcscan→quirk rename
```

---

## Directory Purposes

**`quirk/scanner/`:**
- Purpose: All active network/API/filesystem probing; each module is an independent scanner
- Contains: 10 scanner files; all produce `List[CryptoEndpoint]`
- Key files: `tls_scanner.py` (primary), `fingerprint.py` (protocol classifier), `aws_connector.py`, `azure_connector.py`
- Note: Real cloud connectors live here; `quirk/connectors/` contains only stubs

**`quirk/discovery/`:**
- Purpose: Network target discovery (nmap path only); only `nmap_provider.py` and `nmap_parser.py` are live
- Contains: 4 files, 2 of which are dead (see Dead Modules below)
- Key files: `nmap_provider.py`, `nmap_parser.py`

**`quirk/connectors/`:**
- Purpose: Placeholder namespace for future native connectors (Windows AD CS, etc.)
- Contains: 3 files, all 3-line comment stubs — nothing is imported from this package
- Status: Dead namespace; no code to run

**`quirk/engine/`:**
- Purpose: Scan execution helpers and post-scan risk evaluation
- Contains: `risk_engine.py` (active), `profiles.py` (active), `cache.py` (active), `rate_limiter.py` (active), `migration_planner.py` (used by writer.py), `rules.py` (stub only)

**`quirk/assessment/`:**
- Purpose: First-generation scoring subsystem; still feeds `executive.py` and `technical.py`
- Contains: 6 Python modules (all have real implementations)
- Status: Partially superseded by `quirk/intelligence/` — see ARCHITECTURE.md dual scoring concern

**`quirk/intelligence/`:**
- Purpose: Canonical scoring subsystem; feeds `writer.py`, `scorecard.py`, and dashboard API
- Contains: 7 Python modules; `schema.py` defines the output type contract
- Status: Active; tests enforce `writer.py` must only use this layer

**`quirk/cbom/`:**
- Purpose: CycloneDX CBOM production; exposes three public functions via `__init__.py`
- Key files: `builder.py` (522 lines, main logic), `classifier.py` (quantum safety labelling)

**`quirk/reports/`:**
- Purpose: All output artefact generation — Markdown, JSON intelligence, HTML, PDF, CBOM files
- Key file: `writer.py` (orchestrates all outputs from a single `write_reports()` call)
- Contains: Jinja2 templates in `templates/`

**`quirk/dashboard/`:**
- Purpose: FastAPI backend + static file host for the React SPA
- Build input: `src/dashboard/` (React source)
- Build output: `quirk/dashboard/static/` (Vite output, committed to repo)
- Dashboard port: 8512 (default)

**`quantum-chaos-enterprise-lab/`:**
- Purpose: Docker Compose test environment providing real crypto endpoints for lab testing
- Contains: nginx configs with weak/strong TLS, HAProxy, SSH server, JWT service, container registry
- Key file: `docker-compose.yml`, `expected_results_v3.md`, `lab.sh`
- Note: Has its own `.env` file (not read here); lab is self-contained

**`tests/`:**
- Purpose: pytest suite — 29 test files, 165+ passing tests
- Structure: Flat; all test files in single directory, no subdirectories
- Key files: `conftest.py`, `test_scoring_consolidation.py` (enforces import boundaries)

---

## Key File Locations

**Entry Points:**
- `run_scan.py` — CLI entry; scan, init, and serve subcommands
- `quirk/dashboard/api/app.py` — FastAPI app factory (for dashboard)
- `quirk/dashboard/server.py` — uvicorn launcher

**Configuration:**
- `quirk/config.py` — Config dataclasses and YAML loader
- `quirk/config_template.yaml` — Bundled starter template
- `config.yaml` — Working config example (in repo root)
- `pyproject.toml` — Package metadata, dependencies, entry points

**Core Logic:**
- `quirk/models.py` — `CryptoEndpoint` (the central data object)
- `quirk/engine/risk_engine.py` — Findings generation
- `quirk/intelligence/scoring.py` — Canonical scoring
- `quirk/reports/writer.py` — All output file generation
- `quirk/cbom/builder.py` — CBOM assembly

**Testing:**
- `tests/conftest.py` — Shared fixtures
- `tests/test_scoring_consolidation.py` — Enforces `assessment` vs `intelligence` import boundaries
- `quantum-chaos-enterprise-lab/expected_results_v3.md` — Lab acceptance criteria

---

## Naming Conventions

**Files:**
- Python modules: `snake_case.py`
- Test files: `test_<module_name>.py` (e.g., `test_cbom_builder.py`)
- Config: `snake_case.yaml`
- Templates: `snake_case.j2`

**Directories:**
- Python packages: `snake_case/` with `__init__.py`
- All `__init__.py` files present; `quirk/intelligence/__init__.py` and `quirk/cbom/__init__.py`
  re-export public API; other `__init__.py` files are empty

**Classes:**
- ORM models: PascalCase (e.g., `CryptoEndpoint`)
- Config dataclasses: PascalCase with `Cfg` suffix (e.g., `ScanCfg`, `OutputCfg`)
- Schema dataclasses: PascalCase (e.g., `ScoreResult`, `RoadmapItem`)

**Functions:**
- Public: `snake_case` (e.g., `build_cbom`, `compute_readiness_score`)
- Private helpers: `_snake_case` prefix (e.g., `_pubkey_info`, `_dedupe_findings`)

---

## Where to Add New Code

**New scanner (new protocol or source type):**
- Implementation: `quirk/scanner/<protocol>_scanner.py`
- Add enable flag to `ConnectorsCfg` in `quirk/config.py`
- Add target list field to `ConnectorsCfg` if needed
- Wire into `run_scan.py` scan phase sequence
- Tests: `tests/test_<protocol>_scanner.py`

**New report section:**
- Implementation: `quirk/reports/<section>.py`
- Call from `quirk/reports/writer.py:write_reports()`
- Use `quirk.intelligence` for scoring; do NOT use `quirk.assessment`

**New dashboard API endpoint:**
- Implementation: `quirk/dashboard/api/routes/scan.py` (or new route file)
- Register router in `quirk/dashboard/api/app.py`
- Add Pydantic schemas to `quirk/dashboard/api/schemas.py`

**New frontend page:**
- Implementation: `src/dashboard/src/pages/<name>.tsx`
- Add route to `src/dashboard/src/App.tsx`
- Add nav item to `src/dashboard/src/components/sidebar.tsx`
- Rebuild: `cd src/dashboard && npm run build`

**New config field:**
- Add to appropriate dataclass in `quirk/config.py`
- Set a default value for backward compatibility
- Add to `quirk/config_template.yaml`

**New intelligence scoring component:**
- Implementation: `quirk/intelligence/<component>.py`
- Export from `quirk/intelligence/__init__.py`
- Do NOT add to `quirk/assessment/`

**Utilities:**
- Shared Python helpers: `quirk/util.py` (currently a minimal stub — expand as needed)
- Shared frontend helpers: `src/dashboard/src/lib/`

---

## Special Directories

**`quirk/dashboard/static/`:**
- Purpose: Vite build output (React SPA compiled assets)
- Generated: Yes — by `cd src/dashboard && npm run build`
- Committed: Yes — so `quirk serve` works without a Node.js build step

**`output/`:**
- Purpose: Scan artefact output directory (JSON, Markdown, HTML, PDF, CBOM, SQLite)
- Generated: Yes — created at runtime
- Committed: No (gitignored)
- Cache: `output/.cache/` — JSON cache files for discovery/fingerprint phases

**`data/`:**
- Purpose: Persistent database directory
- Key file: `data/quirk.db` (SQLite, created by `init_db()`)
- Legacy: `data/_archive/qcscan-legacy.sqlite` — pre-rename archive, harmless

**`tmp/`:**
- Purpose: Temporary file landing zone
- Generated: Yes
- Committed: No (gitignored)

**`.planning/`:**
- Purpose: GSD planning artifacts — project state, roadmap, requirements, phase plans
- Committed: Yes

**`quantum-chaos-enterprise-lab/`:**
- Purpose: Self-contained Docker test environment
- Committed: Yes (configs, certs, scripts — not outputs)

---

## Dead Modules (Never Imported in Production Path)

| File | Reason Dead |
|------|-------------|
| `quirk/discovery/tls_scanner.py` | Legacy TLS scanner predating `quirk/scanner/tls_scanner.py`; has its own `scan_tls_targets()` but is never imported anywhere in the active codebase |
| `quirk/discovery/coverage.py` | Primitive `quantum_readiness_score()` stub with hardcoded penalties; replaced by `quirk/intelligence/scoring.py`; never imported |
| `quirk/connectors/aws_stub.py` | 3-line comment; real AWS connector is `quirk/scanner/aws_connector.py` |
| `quirk/connectors/azure_stub.py` | 3-line comment; real Azure connector is `quirk/scanner/azure_connector.py` |
| `quirk/connectors/windows_adcs_stub.py` | 3-line comment; no implementation exists |
| `quirk/engine/rules.py` | 2-line comment stub; severity logic is hardcoded in `risk_engine.py` |
| `quirk/validate.py` | Standalone validator; not imported by any other module — invoked only via `python -m quirk.validate` |

---

*Structure analysis: 2026-04-02*
