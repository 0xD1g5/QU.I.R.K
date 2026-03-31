# Phase 7: Polish and Packaging - Context

**Gathered:** 2026-03-31
**Status:** Ready for planning

<domain>
## Phase Boundary

QU.I.R.K. is installable in one command, presents a coherent visual identity across all surfaces,
and produces reports that look like a commercial security product indistinguishable from a paid tool.

Scope: visual identity (wordmark + palette), CLI UX overhaul with `rich`, standalone HTML + PDF
report from CLI scan output, dashboard theme pass, GitHub-based pip install, `quirk init` sample
config, manual version bump to v4.0.0.

No new scanners, no new dashboard features beyond branding, no MkDocs build (plain Markdown stays).

</domain>

<decisions>
## Implementation Decisions

### Visual Identity (BRAND-01)
- **D-01:** Styled wordmark only — typography-based treatment, `QU.I.R.K.` in a monospace/tech
  font with electric-blue accent. No illustrative icon needed for v1.
- **D-02:** Color palette: dark backgrounds with electric-blue accent (navy/slate base, bright
  blue highlight). Complements the existing shadcn/ui dark theme.
- **D-03:** Branding appears on all surfaces: report headers (HTML/PDF), dashboard navbar +
  favicon, and CLI startup banner.

### CLI UX (BRAND-02)
- **D-04:** Add `rich` library as a core dependency (not optional). Replace tqdm + plain
  `print()` calls with rich progress bars, spinners, colored severity levels, and phase timing
  output. Full rich treatment throughout scan execution.
- **D-05:** Add a final scan summary table rendered by rich after every scan completes — shows
  hosts scanned, findings by severity, readiness score, output files written. Replaces the
  current scattered `print("✅ Wrote reports: ...")` lines.
- **D-06:** Add `--version` flag to CLI: `quirk --version` returns the current version string
  sourced from `quirk/__init__.py __version__`.
- **D-07:** Add CLI startup banner (ASCII/styled) displaying `QU.I.R.K.` wordmark and version
  when running `quirk scan` or `quirk serve`. Dismissible / suppressible with `--quiet`.

### Report HTML/PDF Templates (BRAND-03)
- **D-08:** New standalone HTML report template using Jinja2. `write_reports()` produces a
  self-contained single-file `report.html` (embedded CSS, no external dependencies) alongside
  the existing Markdown report. A consultant can open this file without a browser or dashboard.
- **D-09:** HTML report contains both executive and technical sections: executive summary
  (score gauges, severity breakdown, top findings, transition roadmap, CBOM summary) + full
  technical appendix (all endpoints, raw findings, cert inventory). Single file, scrollable.
- **D-10:** HTML report reuses existing data builders — `executive.py` and `technical.py`
  already assemble all required data. Phase 7 adds a Jinja2 renderer consuming the same data
  dicts. No refactor of data assembly logic.
- **D-11:** PDF = Playwright renders the standalone HTML report (same Playwright dependency
  already in `[dashboard]` optional group). PDF shares the same data as HTML — no separate
  PDF pipeline.
- **D-12:** QU.I.R.K. branding in report: wordmark header, electric-blue accent colors,
  professional layout with score band color coding (red/amber/green).

### Dashboard Branding (BRAND-01 + UI-02)
- **D-13:** Full theme pass of the React dashboard — audit every shadcn/ui component color
  token, update to the defined palette (dark + electric blue). Update navbar with QU.I.R.K.
  wordmark, set favicon.

### Distribution + Packaging (BRAND-04)
- **D-14:** GitHub-based install as the distribution target:
  ```
  pip install 'git+https://github.com/[owner]/quirk.git[dashboard]'
  ```
  No PyPI publication in Phase 7. Getting-started doc updated to use this as primary path
  (removes the "coming soon" callout from Phase 6 D-05).
- **D-15:** `quirk init` subcommand generates a `config.yaml` from a bundled template with
  sensible defaults and inline comments. Enables zero-to-scan without manual config editing.
  Generated config targets `127.0.0.1` with standard ports as the first-run default.
- **D-16:** Version bumped to `4.0.0` in `pyproject.toml` and `quirk/__init__.py` as part of
  this phase. Manual bump + `git tag v4.0.0`. No bump2version tooling added.

### Claude's Discretion
- Jinja2 template layout details (section ordering, table styling, fonts)
- Rich theme/style specifics (exact colors, spinner style)
- ASCII banner art style and dimensions
- Playwright PDF page size and margins

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` — BRAND-01 through BRAND-04 full requirement definitions

### Phase 5 context (dashboard infrastructure)
- `.planning/phases/05-web-dashboard/05-CONTEXT.md` — D-04 (static asset structure),
  D-06 (uvicorn port 8512), D-15 (PDF via Playwright), D-05 (Vite build → committed assets)

### Phase 6 context (docs impact)
- `.planning/phases/06-documentation/06-CONTEXT.md` — D-03 (plain Markdown stays, no build
  step), D-04/D-05 (getting-started install path — Phase 7 removes the PyPI callout)

### Key source files
- `pyproject.toml` — current version, deps, optional groups, entry point
- `quirk/__init__.py` — `__version__` string
- `run_scan.py` — CLI entry point, argparse setup, main() function
- `quirk/reports/writer.py` — `write_reports()` function where HTML output hooks in
- `quirk/reports/executive.py` — executive data builder (reused by HTML renderer)
- `quirk/reports/technical.py` — technical data builder (reused by HTML renderer)
- `quirk/dashboard/api/` — FastAPI routes (dashboard branding does not touch API)
- `src/dashboard/src/` — React source for dashboard theme pass

No external specs — requirements fully captured in decisions above.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `quirk/reports/executive.py`: `build_exec_markdown()` returns data already assembled for score,
  findings, roadmap, CBOM summary — Jinja2 renderer can consume this directly
- `quirk/reports/technical.py`: `build_tech_markdown()` has full endpoint and cert data
- `quirk/reports/writer.py`: `write_reports()` orchestrates all report generation — HTML output
  slots in as a new step alongside existing Markdown write
- `quirk/dashboard/api/routes/` + `src/dashboard/src/`: Phase 5 dashboard infrastructure —
  React + shadcn/ui + Tailwind, Vite build → `quirk/dashboard/static/`
- `quirk/__init__.py`: `__version__ = "3.9.0"` — single source of truth for version string

### Established Patterns
- Markdown reports use f-string builders (`build_exec_markdown`, `build_tech_markdown`) that
  return strings — HTML renderer is an additional renderer, not a replacement
- CLI uses argparse (not Click/Typer) — `--version` adds as `add_argument('--version', action='version')`
- Phase 5 Playwright PDF: `quirk/dashboard/api/routes/scan.py` has the PDF generation logic —
  Phase 7 standalone PDF reuses Playwright but renders local HTML file instead of dashboard URL
- shadcn/ui uses CSS variables for theming — color palette changes go in `src/dashboard/src/index.css`
  or shadcn theme config

### Integration Points
- `write_reports()` in `quirk/reports/writer.py`: HTML/PDF steps insert here (after existing
  Markdown writes, before final print summary)
- `run_scan.py main()`: `--version` flag and startup banner go here; `init` subcommand pattern
  mirrors existing `serve` subcommand intercept (lines 80–108)
- `pyproject.toml [project.scripts]`: `quirk = "run_scan:main"` — entry point stays the same
- `src/dashboard/src/index.css` or `tailwind.config.js`: palette overrides for dashboard theme

</code_context>

<specifics>
## Specific Ideas

- Color direction: dark/slate base with electric-blue (navy + bright blue) — "enterprise security
  look (Splunk, Elastic vibes)" as described
- Report: single-file self-contained HTML — no CDN dependencies, must work offline (critical for
  air-gapped client engagements per project constraints)
- `quirk init` generates config.yaml targeting `127.0.0.1` — makes the 10-minute getting-started
  path work without manual config editing

</specifics>

<deferred>
## Deferred Ideas

- MkDocs/Material skin for docs/ — Phase 6 D-03 noted this as possible Phase 7 work, but user
  confirmed out of scope: plain Markdown stays
- PyPI publication — deferred post-Phase 7; GitHub-based install is sufficient for v1 consulting
  delivery
- CHANGELOG / semantic-release tooling — not added; manual version bump only

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 07-polish-and-packaging*
*Context gathered: 2026-03-31*
