---
phase: 12-cli-correctness
plan: 02
subsystem: cli

tags: [version-bump, docs, cli, config]

requires:
  - phase: 12-cli-correctness
    plan: 01
    provides: RED contract tests for version consistency, config fallback, and [owner] placeholder

provides:
  - Version 4.1.0 consistently across all 5 locations (__init__, writer, builder, config default, config fallback)
  - docs/getting-started.md with dev-install workflow (git clone + pip install -e .) and no [owner] placeholder
  - All 6 Phase 12 contract tests GREEN

affects:
  - 13-interactive-mode (CLI version contract now 4.1.0)
  - 14-scoring-correctness (CBOM and report headers now show 4.1.0)

tech-stack:
  added: []
  patterns:
    - "Minimal targeted edits: 5 string replacements across 4 files, no refactoring"
    - "Dev-install pattern: git clone + pip install -e . replaces github pip URL with [owner] placeholder"

key-files:
  created: []
  modified:
    - quirk/__init__.py
    - quirk/reports/writer.py
    - quirk/cbom/builder.py
    - quirk/config.py
    - docs/getting-started.md
    - tests/test_packaging.py

key-decisions:
  - "Version strings updated individually in each file (no shared import) — circular import avoidance is intentional per RESEARCH.md"
  - "test_packaging.py::test_version_is_4_0_0 renamed and updated to 4.1.0 — stale Phase 7 test, updated as Rule 1 auto-fix"
  - "getting-started.md uses <your-repo-url> generic placeholder per D-06 — no specific GitHub handle hardcoded"

metrics:
  duration: 2min
  completed: 2026-04-06
  tasks: 2
  files_modified: 6
---

# Phase 12 Plan 02: CLI Correctness Fixes Summary

**Version bump to 4.1.0 across all 5 canonical locations and dev-install workflow replacing [owner] placeholder in Getting Started guide — all 6 Phase 12 contract tests GREEN, 205 total tests passing**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-06T12:27:29Z
- **Completed:** 2026-04-06T12:28:49Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Bumped version string in `quirk/__init__.py` from `4.0.0` to `4.1.0`
- Updated `quirk/reports/writer.py`: `PLATFORM_VERSION = "4.1.0"`, `INTELLIGENCE_VERSION = "4.1.0"` (was `"4.0"` and `"4.0.0"`)
- Updated `quirk/cbom/builder.py`: `PLATFORM_VERSION = "4.1.0"` (was `"4.0"`)
- Updated `quirk/config.py`: `IntelligenceCfg.intelligence_version` default and `config_from_dict` fallback both changed from `"4.0.0"` to `"4.1.0"`
- Replaced `docs/getting-started.md` install section: `pip install git+https://github.com/[owner]/quirk.git` replaced with `git clone <your-repo-url> && pip install -e .`
- All 6 `test_cli_correctness.py` tests now GREEN (3 were RED in Plan 01)
- Full suite: 205 tests passing, 0 failures

## Task Commits

1. **Task 1: Bump all version strings to 4.1.0** - `43d3f34` (feat)
2. **Task 2: Replace [owner] placeholder with dev-install workflow** - `53db75a` (feat)

## Files Created/Modified

- `quirk/__init__.py` - `__version__ = "4.1.0"`
- `quirk/reports/writer.py` - `PLATFORM_VERSION = "4.1.0"`, `INTELLIGENCE_VERSION = "4.1.0"`
- `quirk/cbom/builder.py` - `PLATFORM_VERSION = "4.1.0"`
- `quirk/config.py` - `IntelligenceCfg` default + `config_from_dict` fallback = `"4.1.0"`
- `docs/getting-started.md` - dev-install workflow, no `[owner]` placeholder
- `tests/test_packaging.py` - `test_version_is_4_0_0` renamed to `test_version_is_4_1_0`, assertion updated

## Decisions Made

- Version strings updated individually in each file rather than refactored to a shared import — circular import avoidance is intentional per RESEARCH.md D-01
- `<your-repo-url>` is the deliberate generic placeholder used in getting-started.md per D-06 — no specific GitHub handle hardcoded, suitable for any fork/clone
- `test_packaging.py::test_version_is_4_0_0` was a stale Phase 7 milestone test; updated to `4.1.0` as a Rule 1 auto-fix since the version bump is the intended change

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated stale test_version_is_4_0_0 in test_packaging.py**
- **Found during:** Task 2 (full suite run)
- **Issue:** `tests/test_packaging.py::test_version_is_4_0_0` hardcoded `4.0.0` as the expected version — this was written for the Phase 7 milestone and became incorrect after the version bump
- **Fix:** Renamed function to `test_version_is_4_1_0` and updated assertion to `"4.1.0"`
- **Files modified:** `tests/test_packaging.py`
- **Commit:** `53db75a` (included in Task 2 commit)

## Issues Encountered

None beyond the stale test auto-fixed above.

## Known Stubs

None — all version locations are now consistently `4.1.0`. No placeholder text remains in the docs.

## User Setup Required

None.

## Next Phase Readiness

- Phase 13 (Interactive Mode) can proceed: CLI correctness baseline is solid
- Phase 14 (Scoring Correctness) can proceed: version headers in CBOM and reports now accurate
- Phase 15 (Code Hygiene) can proceed: no file touched here will conflict with hygiene cleanup

---
*Phase: 12-cli-correctness*
*Completed: 2026-04-06*
