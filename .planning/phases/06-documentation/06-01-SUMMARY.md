---
phase: 06-documentation
plan: 01
subsystem: documentation
tags: [readme, getting-started, installation, markdown, docs, playwright, pip, pypi]

# Dependency graph
requires:
  - phase: 05-web-dashboard
    provides: quirk serve, quirk CLI entry point, dashboard at localhost:8512
  - phase: 01-foundation-fixes
    provides: package rename qcscan->quirk, pyproject.toml with quirk entry point
provides:
  - README.md — complete product intro with Quick Start and docs table
  - docs/getting-started.md — zero-to-first-scan walkthrough (macOS/Linux, <10 min)
  - docs/installation.md — full install guide covering macOS, Linux, Windows WSL
affects: [06-02, 06-03, 06-04, 06-05, 06-06, phase-07-packaging]

# Tech tracking
tech-stack:
  added: [docs/ directory at repo root]
  patterns: [plain Markdown per D-03, no build step, GitHub-compatible relative links]

key-files:
  created:
    - README.md (complete replacement)
    - docs/getting-started.md
    - docs/installation.md
    - docs/connectors/ (directory placeholder)
  modified: []

key-decisions:
  - "README fully replaced — zero qcscan/QuRisk/Quantum Crypto Scanner references remain"
  - "Getting Started primary path is git clone + pip install -e '.[dashboard]' + playwright install chromium"
  - "PyPI callout box added per D-05: 'coming in v4.0, use git clone path for now'"
  - "Windows WSL documented in installation.md only (not Getting Started main path) per D-07"
  - "Plain Markdown, no build step per D-03 — Phase 7 can layer MkDocs without restructuring"

patterns-established:
  - "docs/ at repo root — one Markdown file per guide, connectors/ subdirectory"
  - "Getting Started = minimal config.yaml (127.0.0.1 target) + quirk --config + quirk serve"
  - "Installation = System Requirements table + per-OS sections + Optional Dependencies table"

requirements-completed: [DOC-01, DOC-02]

# Metrics
duration: 12min
completed: 2026-03-31
---

# Phase 6 Plan 01: README and Entry-Point Guides Summary

**README fully replaced and docs/getting-started.md + docs/installation.md written: zero-to-first-scan consultant path in under 10 minutes covering macOS, Linux, and Windows WSL**

## Performance

- **Duration:** 12 min
- **Started:** 2026-03-31T21:43:49Z
- **Completed:** 2026-03-31T21:55:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- README.md completely replaced — removes all stale qcscan/Quantum Crypto Scanner content; adds product intro, Quick Start, Documentation table, What Scans section, Output Artifacts section
- docs/getting-started.md written — six-step walkthrough from install through PDF export, under 10 minutes on clean macOS or Linux; includes PyPI v4.0 callout per D-05
- docs/installation.md written — system requirements table, macOS (Homebrew), Linux (apt), and Windows WSL2 sections; playwright install-deps for Linux; optional dependencies table

## Task Commits

1. **Task 1: Replace README.md** — `a251109` (docs)
2. **Task 2: Write docs/getting-started.md and docs/installation.md** — `f620300` (docs)

## Files Created/Modified

- `README.md` — complete product intro: QU.I.R.K. description, Quick Start snippet, Documentation table, What Scans, Output Artifacts, License
- `docs/getting-started.md` — zero-to-scan walkthrough: install, minimal config.yaml, quirk --config, quirk serve, PDF export, next steps
- `docs/installation.md` — full install reference: system requirements, macOS, Linux, Windows WSL2, optional dependencies, verify installation

## Decisions Made

- README fully replaced (not patched) — stale content was pre-Phase 1 MVP, not salvageable
- Quick Start in README uses exact D-04 sequence: git clone → venv → pip install -e '.[dashboard]' → playwright install chromium → quirk --help
- PyPI callout placed in getting-started.md (not README) so README Quick Start stays clean; callout notes "coming in v4.0"
- "Python 3.10 or higher" placed as continuous string in installation.md system requirements table header cell for grep-ability

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

- Minor: grep check for "Python 3.10" failed on first write because the table had "Python | 3.10" across cells. Fixed by restructuring the table header cell to read "Python 3.10 or higher" as a single cell.

## User Setup Required

None — no external service configuration required.

## Known Stubs

None — all content is verified against pyproject.toml, config.yaml, and 06-CONTEXT.md decisions.

## Next Phase Readiness

- DOC-01 (Getting Started) and DOC-02 (Installation) are complete
- docs/ directory established at repo root; connectors/ subdirectory created
- Phase 6 Plans 02–06 can proceed with the docs/ structure in place
- docs/configuration.md, docs/connectors/*.md, docs/report-interpretation.md, docs/cbom-guide.md, docs/chaos-lab.md remain to be written

---
*Phase: 06-documentation*
*Completed: 2026-03-31*
