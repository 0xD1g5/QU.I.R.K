---
phase: 10-v39-gap-closure
plan: "02"
subsystem: packaging
tags: [pyproject, setuptools, package-data, config-template, intelligence, scoring, obsidian]

# Dependency graph
requires:
  - phase: 10-v39-gap-closure-01
    provides: MISMATCH-01 fix (quantum safety label type correction)
provides:
  - pyproject.toml includes dashboard/static/**/* glob so pip wheel ships React bundle (PACKAGE-01)
  - config_template.yaml has commented intelligence: block documenting strict/balanced/lenient profile (MISSING-01)
  - Regression tests confirming both gaps are closed and cannot regress
  - Obsidian Phase-10 note created; Roadmap vault note synced
affects: [packaging, pip-install, quirk-init, scoring-profile, dashboard-serve]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "setuptools package-data glob dashboard/static/**/* for recursive static asset inclusion"
    - "Commented YAML blocks in config_template.yaml to surface optional config knobs discoverable via quirk init"

key-files:
  created:
    - tests/test_gap_closure_packaging.py
  modified:
    - pyproject.toml
    - quirk/config_template.yaml

key-decisions:
  - "dashboard/static/**/* glob in pyproject.toml is relative to the quirk/ package root — setuptools >= 68 resolves it recursively"
  - "Intelligence block in config_template.yaml is fully commented so it has no effect on parsed YAML or runtime behavior — pure discoverability"
  - "Obsidian vault synced via direct file write (obsidian CLI API key not configured in worktree environment)"

patterns-established:
  - "TDD RED then GREEN: write failing tests first to confirm gaps are testable, then fix"
  - "config_template.yaml comment style: hash-prefix, inline value descriptions, section separator dashes"

requirements-completed: [UI-01, BRAND-04]

# Metrics
duration: 4min
completed: 2026-04-03
---

# Phase 10 Plan 02: v3.9 Gap Closure — PACKAGE-01 + MISSING-01 Summary

**Added `dashboard/static/**/*` to pyproject.toml package-data and commented `intelligence:` block to config_template.yaml, with regression tests for both gaps**

## Performance

- **Duration:** 4 minutes
- **Started:** 2026-04-04T03:24:03Z
- **Completed:** 2026-04-04T03:28:00Z
- **Tasks:** 3
- **Files modified:** 3 (tests/test_gap_closure_packaging.py, pyproject.toml, quirk/config_template.yaml)

## Accomplishments

- PACKAGE-01 closed: `dashboard/static/**/*` glob added to `[tool.setuptools.package-data]` so the React bundle is included in the pip wheel and `quirk serve` works after non-editable install
- MISSING-01 closed: Commented `intelligence:` block appended to `quirk/config_template.yaml` — users running `quirk init` can now discover the `profile: strict|balanced|lenient` scoring knob directly from the generated file
- 3 regression tests written (TDD RED then GREEN) confirming both gaps are testable and closed
- docs/configuration.md already had a complete Intelligence Block section (lines 160-201) — no change needed
- Obsidian Phase-10 vault note created; Roadmap vault note synced with Phase 10 content

## Task Commits

Each task was committed atomically:

1. **Task 1: Write regression tests (TDD RED)** - `ec7d089` (test)
2. **Task 2: Fix PACKAGE-01 + MISSING-01 (TDD GREEN)** - `0af7417` (feat)
3. **Task 3: Documentation + Obsidian sync** - no repo commit (docs/configuration.md already complete; vault files outside repo)

## Files Created/Modified

- `tests/test_gap_closure_packaging.py` - 3 regression tests: test_pyproject_includes_dashboard_static, test_config_template_has_intelligence_block, test_config_template_valid_yaml
- `pyproject.toml` - Added `"dashboard/static/**/*"` to `quirk` package-data list
- `quirk/config_template.yaml` - Appended commented `intelligence:` block with profile knob documentation (strict/balanced/lenient with multiplier values)

## Decisions Made

- `dashboard/static/**/*` glob is relative to the `quirk/` package root per setuptools convention — resolved recursively to include `assets/` subdirectory with JS/CSS chunks
- Intelligence block is entirely commented out so it does not change runtime behavior — pure discoverability for `quirk init` users
- Obsidian vault sync performed via direct file write to `/Users/digs/vaults/Digs/` since obsidian CLI API key was not available in the worktree environment; functionally equivalent result

## Deviations from Plan

None — plan executed exactly as written. docs/configuration.md already had a complete Intelligence Block section from Phase 6 documentation work, so no modification was required there (the plan included a conditional: "If it does not already have an Intelligence or Scoring Profile section").

## Issues Encountered

- Obsidian CLI (`obsidian` command) resolved to the macOS app binary, not the CLI tool. The `obsidian-cli` npm package required `OBSIDIAN_API_KEY` which was not configured in the worktree environment. Resolved by writing vault files directly to the vault path on disk — same end result.

## Known Stubs

None — all changes are functional (glob is real, YAML block is real content, tests pass against actual files).

## Next Phase Readiness

- Phase 10 plan 02 complete — all 3 gaps from the v3.9 milestone audit are now closed (MISMATCH-01 via plan 01, PACKAGE-01 and MISSING-01 via this plan)
- Phase 10 is complete pending STATE.md and ROADMAP.md update via gsd-tools

---
*Phase: 10-v39-gap-closure*
*Completed: 2026-04-03*

## Self-Check: PASSED

- FOUND: tests/test_gap_closure_packaging.py
- FOUND: pyproject.toml (with dashboard/static/**/* glob)
- FOUND: quirk/config_template.yaml (with intelligence: block)
- FOUND: .planning/phases/10-v39-gap-closure/10-02-SUMMARY.md
- FOUND commit: ec7d089 (TDD RED tests)
- FOUND commit: 0af7417 (GREEN fixes)
