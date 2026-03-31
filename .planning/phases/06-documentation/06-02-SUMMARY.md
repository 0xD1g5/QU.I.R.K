---
phase: 06-documentation
plan: 02
subsystem: docs
tags: [documentation, configuration, cli, markdown]

# Dependency graph
requires:
  - phase: 06-documentation
    provides: docs/ directory established by plan 06-01 (getting-started.md, installation.md)
provides:
  - Complete docs/configuration.md: all config.yaml keys, CLI flags, scan profiles, score profiles
affects: [06-03, 06-04, 06-05, 06-06]

# Tech tracking
tech-stack:
  added: []
  patterns: ["Configuration reference with verified data from RESEARCH.md — do not re-derive from source"]

key-files:
  created:
    - docs/configuration.md
  modified: []

key-decisions:
  - "All config.yaml keys documented with type, default, and description — verified against config.yaml and ConnectorsCfg dataclass"
  - "CLI flag tables derived verbatim from RESEARCH.md (pre-verified from run_scan.py argparse)"
  - "Scan profiles (quick/standard/deep) and score profiles (lenient/balanced/strict) documented with use-case guidance"
  - "Full reference config template included as copy-pasteable block for consultant use"

patterns-established:
  - "Pattern: Reference tables for config docs pair Key/Type/Default/Description — use this format for any config doc"
  - "Pattern: Minimal valid config snippet + full annotated template — both included for quick and power users"

requirements-completed: [DOC-03]

# Metrics
duration: 2min
completed: 2026-03-31
---

# Phase 6 Plan 02: Configuration Reference Summary

**Complete config.yaml and CLI flag reference in docs/configuration.md — all 6 top-level blocks, scan profiles, score profiles, and copy-pasteable minimal and full config templates**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-31T21:47:55Z
- **Completed:** 2026-03-31T21:49:16Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Created `docs/configuration.md` covering all 6 config.yaml top-level blocks (assessment, scan, targets, connectors, output, intelligence)
- Documented all 16 `quirk` scan flags and 3 `quirk serve` flags with defaults and descriptions
- Explained scan profiles (quick/standard/deep) and score calibration profiles (lenient/balanced/strict) with use cases
- Included minimal valid config and full annotated reference template for consultant use

## Task Commits

Each task was committed atomically:

1. **Task 1: Write docs/configuration.md** - `18fa5e2` (feat)

## Files Created/Modified

- `docs/configuration.md` - Complete configuration reference (327 lines): 6 config.yaml blocks, CLI flag reference, scan profiles table, score profile descriptions, minimal valid config, and full annotated template

## Decisions Made

- Used verified data from RESEARCH.md verbatim for all key names, defaults, and flag tables — no re-derivation from source files to avoid transcription errors
- Full reference config template placed at end of document as a single copy-pasteable block for rapid client scan setup

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `docs/configuration.md` complete and verified against all acceptance criteria
- `docs/connectors/` directory exists (created in plan 06-01) — connector guides (aws.md, azure.md, docker.md, git.md) will be written in plan 06-03
- All cross-references to `connectors/` link correctly

---
*Phase: 06-documentation*
*Completed: 2026-03-31*
