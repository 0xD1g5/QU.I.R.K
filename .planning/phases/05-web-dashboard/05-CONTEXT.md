# Phase 5: Web Dashboard - Context

**Gathered:** 2026-03-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Expose QU.I.R.K. scan results through a local web dashboard (`quirk serve`) — executive summary
with score gauges, findings table, certificate inventory, CBOM viewer with graph visualization,
and one-click PDF export. FastAPI backend + React + shadcn/ui + Cytoscape.js frontend, bundled
as static assets inside the pip package. No new scanners (Phase 3). No documentation (Phase 6).
No visual identity/branding (Phase 7).

</domain>

<decisions>
## Implementation Decisions

### API Architecture (UI-01)
- **D-01:** FastAPI layer added under `quirk/dashboard/api/`. Launched via `quirk serve` CLI
  subcommand (new entry in pyproject.toml scripts or argparse subcommand in run_scan.py).
  FastAPI reads SQLite directly via SQLAlchemy — same `get_session()` / `get_engine()` from
  `quirk/db.py`. No new persistence layer.
- **D-02:** Primary endpoint: `GET /api/scan/latest` — returns the most recent scan session's
  endpoints, findings, scores, and CBOM summary. Response includes a `scan_id` field (derived
  from max `scanned_at` timestamp) so the API is shaped for future multi-scan navigation without
  breaking changes.
- **D-03:** Multi-scan navigation (scan selector dropdown) is deferred to BACK-02. v1 always
  shows the most recent scan. No scan session ID table needed — `scan_id` is derived at query
  time from `MAX(scanned_at)`.

### Frontend Bundling (UI-01, UI-02)
- **D-04:** React source lives under `src/dashboard/` (project root). Pre-built static assets
  committed to `quirk/dashboard/static/` (index.html + assets/). FastAPI mounts this directory
  as StaticFiles. End users need no Node.js — `pip install quirk` → `quirk serve` → open browser.
- **D-05:** Build toolchain: Vite + React + TypeScript. shadcn/ui for component library.
  `npm run build` outputs to `quirk/dashboard/static/` — run by developer, output committed.
- **D-06:** `quirk serve` starts uvicorn on `localhost:8512` (default, configurable via
  `--port`). Auto-opens browser on launch unless `--no-open` flag passed.

### Executive Dashboard (UI-02)
- **D-07:** Four radial/arc score gauges — one per intelligence subscore: Hygiene, Modern TLS,
  Identity, Agility. Values sourced from `compute_readiness_score()` in
  `quirk/intelligence/scoring.py`. Overall readiness score displayed prominently above gauges.
- **D-08:** Severity breakdown bar chart — CRITICAL / HIGH / MEDIUM / LOW / INFO counts from
  the findings list. shadcn/ui Chart (Recharts-based) or a lightweight Recharts component directly.
- **D-09:** Confidence badge shown alongside score — sourced from `compute_confidence()` in
  `quirk/intelligence/confidence.py`.

### Findings Table + Certificate Inventory (UI-03)
- **D-10:** Findings table: filterable by severity, searchable by title/host, sortable by
  severity. Each row expandable to show full finding detail. shadcn/ui DataTable with
  TanStack Table.
- **D-11:** Certificate inventory: table of TLS endpoints — host, port, cert subject, issuer,
  expiry date, pubkey algorithm, key size, quantum-safety badge. Sortable by expiry (soonest
  first by default). Sourced from `CryptoEndpoint` rows where `protocol = 'TLS'`.

### CBOM Viewer (UI-03)
- **D-12:** CBOM viewer has two tabs: **Table** (structured component view) and **Graph**
  (Cytoscape.js visualization). Both are in scope for Phase 5.
- **D-13:** Table tab — filterable/sortable columns: Algorithm, Type (hash/cipher/KEM/etc),
  Key Size, Quantum Safety badge (Safe ✓ / At Risk ⚠ / Vulnerable ✗), Source system(s).
  Quantum-safety values sourced from `quirk/cbom/classifier.py`.
- **D-14:** Graph tab — Cytoscape.js. Algorithm nodes connected to source system nodes
  (host:port or file path). Node color encodes quantum-safety: green = safe, amber = at risk,
  red = vulnerable. Edge weight encodes frequency (thicker = more systems using that algorithm).
  Layout: `cose` (force-directed) or `breadthfirst` with algorithm nodes as roots.
- **D-15:** Algorithm vulnerability thresholds: `config.yaml` `algorithm_overrides` section
  in v1 — allows marking specific algorithms as a different safety level than the NIST default.
  Dashboard UI config panel for this is deferred to BACK-01.

### Visualizations (UI-02)
- **D-16:** Migration dependency graph — directed Cytoscape.js graph showing what crypto
  changes need to happen first and what they unblock. Data sourced from `build_phased_roadmap()`
  in `quirk/intelligence/roadmap.py`. Lives on a dedicated "Migration Roadmap" tab or panel.
- **D-17:** Severity heatmap (grid of systems × severity level) is NOT in scope for Phase 5.
  Noted for future consideration.

### PDF Export (UI-04)
- **D-18:** PDF export via Playwright headless — `playwright install chromium` required
  (one-time, ~150MB). "Export PDF" button triggers a FastAPI endpoint that spawns a Playwright
  browser, renders the dashboard at a print-optimized URL, and saves as PDF. PDF = what you see
  in the browser — no separate template needed.
- **D-19:** Print-optimized URL: `GET /print` — same data as dashboard but with print CSS
  applied (no nav, no interactive controls, page breaks between sections). Playwright renders
  this URL.

### Claude's Discretion
- Exact Cytoscape.js layout algorithm selection (cose vs cola vs dagre) — choose based on
  graph density at runtime
- shadcn/ui component choices for specific UI elements (cards, badges, tabs)
- FastAPI response pagination strategy for large findings lists
- Recharts vs Victory vs shadcn Chart for score gauges and severity bars
- Whether `quirk serve` is a new argparse subcommand or a separate entry point in pyproject.toml
- Port number for uvicorn (8512 suggested — avoids common dev ports)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Data model and persistence
- `quirk/models.py` — CryptoEndpoint schema, all column names and types
- `quirk/db.py` — get_engine(), get_session(), init_db() — use these, don't reinvent
- `quirk/config.py` — ConnectorsCfg and config structure — extend for `serve` config

### Scoring and intelligence (API data sources)
- `quirk/intelligence/scoring.py` — compute_readiness_score() — 4-subscore model, score fields
- `quirk/intelligence/confidence.py` — compute_confidence() — confidence rating and score
- `quirk/intelligence/roadmap.py` — build_phased_roadmap() — migration roadmap data
- `quirk/intelligence/evidence.py` — build_evidence_summary() — evidence model structure

### CBOM (viewer data source)
- `quirk/cbom/builder.py` — build_cbom() — CycloneDX Bom object structure
- `quirk/cbom/classifier.py` — classify_algorithm(), quantum_safety_label() — safety labels
- `quirk/cbom/writer.py` — write_cbom_files() — JSON/XML output (already written per scan)

### Reports (existing output structure)
- `quirk/reports/writer.py` — write_reports() — current output artifacts and data assembly
- `quirk/reports/executive.py` — build_exec_markdown() — executive summary data fields
- `quirk/reports/scorecard.py` — scorecard data structure

### Requirements
- `.planning/REQUIREMENTS.md` §UI — UI-01 through UI-04 requirement definitions
- `.planning/ROADMAP.md` §Phase 5 — Success criteria (4 criteria to pass)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `quirk/db.py:get_session()` — SQLAlchemy session context manager, use directly in FastAPI dependencies
- `quirk/cbom/classifier.py:quantum_safety_label()` — returns Safe/At Risk/Vulnerable string, use for CBOM table badges
- `quirk/intelligence/scoring.py:compute_readiness_score()` — returns score dict with `total`, `breakdown`, `drivers` — these map directly to the gauge values
- `quirk/intelligence/roadmap.py:build_phased_roadmap()` — returns structured roadmap items with timeframe/title/why — source for migration dependency graph

### Established Patterns
- All scanners return `List[CryptoEndpoint]` — CBOM viewer queries this table directly
- Config via `quirk/config.py` dataclasses — extend `ConnectorsCfg` or add `ServeCfg` for dashboard port/host settings
- Subprocess pattern (ssh-audit, syft, semgrep) — Playwright follows same subprocess/graceful-degradation pattern

### Integration Points
- `run_scan.py:main()` — add `quirk serve` as a subcommand (argparse subparsers) or separate entry point
- `quirk/reports/writer.py:write_reports()` — existing output files (CBOM JSON, findings JSON) can be read directly by FastAPI as a fast path for the first implementation
- `pyproject.toml [project.scripts]` — add `quirk-serve` or extend `quirk` entry point with subcommands

</code_context>

<specifics>
## Specific Ideas

- "Cytoscape.js for the algorithm→system graph — cose layout for force-directed, algorithm
  nodes as roots in breadthfirst mode for the migration dependency view"
- PDF = what you see in the browser (Playwright renders /print URL) — no separate PDF template
- API shaped for future multi-scan: `scan_id` in response, `?scan_id=` param reserved
- `quirk serve` should auto-open the browser on launch (suppressible with `--no-open`)
- Algorithm threshold overrides via `algorithm_overrides:` in config.yaml for v1

</specifics>

<deferred>
## Deferred Ideas

- **BACK-01** (ROADMAP.md): Dashboard UI config panel for algorithm vulnerability thresholds —
  v1 uses config.yaml overrides only; UI panel is a v2 enhancement
- **BACK-02** (ROADMAP.md): Multi-scan navigation (scan selector dropdown) — API is shaped for
  this but the UI feature is deferred to v2
- **BACK-03**: Severity heatmap (grid of systems × severity) — not selected for Phase 5,
  candidate for Phase 7 polish or v2

</deferred>

---

*Phase: 05-web-dashboard*
*Context gathered: 2026-03-30*
