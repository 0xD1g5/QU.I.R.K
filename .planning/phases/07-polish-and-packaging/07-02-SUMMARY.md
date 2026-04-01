---
phase: 07-polish-and-packaging
plan: 02
subsystem: cli
tags: [rich, cli, banner, argparse, progress, terminal-ux]

# Dependency graph
requires:
  - phase: 07-01
    provides: Wave 0 TDD scaffold — test stubs for test_cli_version.py and test_rich_output.py

provides:
  - quirk/cli/banner.py with print_banner() using rich Panel
  - quirk/cli/init_cmd.py stub (raises NotImplementedError until Plan 05)
  - --version flag on run_scan.py main argparse (outputs QU.I.R.K. vX.Y.Z)
  - --quiet flag to suppress banner output
  - init subcommand intercept in run_scan.py
  - rich Console + Table scan summary replacing print() block in writer.py
  - tqdm import removed from run_scan.py (D-04)

affects: [07-03, 07-04, 07-05]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "print_banner(version, quiet) called once after args.parse_args() and once in serve intercept"
    - "init/serve subcommand intercepts live before main argparse to avoid option conflicts"
    - "rich Console + Table used for all write_reports() terminal output"

key-files:
  created:
    - quirk/cli/__init__.py
    - quirk/cli/banner.py
    - quirk/cli/init_cmd.py
  modified:
    - run_scan.py
    - quirk/reports/writer.py

key-decisions:
  - "init subcommand intercept placed before serve intercept — mirrors serve pattern exactly"
  - "tqdm import block replaced with tqdm=None comment to preserve residual references during transition (D-04)"
  - "run_init() stub raises NotImplementedError to fail loudly if called before Plan 05 overwrites it"
  - "rich imports placed at module top in writer.py — always available, no lazy import needed"

patterns-established:
  - "Subcommand intercept pattern: check _sys.argv[1], build sub-parser, parse _sys.argv[2:], return"
  - "Banner always suppressed via quiet=True; serve path passes quiet=False explicitly"

requirements-completed:
  - BRAND-02

# Metrics
duration: 12min
completed: 2026-03-31
---

# Phase 7 Plan 02: CLI UX Overhaul Summary

**Rich Panel startup banner, --version/--quiet flags, and rich scan summary table replacing tqdm/print output in QU.I.R.K. CLI**

## Performance

- **Duration:** 12 min
- **Started:** 2026-03-31T00:40:00Z
- **Completed:** 2026-03-31T00:52:00Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Created `quirk/cli/` package with banner.py (print_banner using rich Panel) and init_cmd.py stub
- Added `--version` action to run_scan.py argparse — outputs `QU.I.R.K. v3.9.0`
- Added `--quiet` flag to suppress banner in non-interactive/CI contexts
- Added `init` subcommand intercept before `serve` intercept in run_scan.py
- Replaced tqdm import block with rich Progress comment (tqdm=None kept for residual refs)
- Replaced all print() calls in writer.py summary block with rich Console + Table output

## Task Commits

Each task was committed atomically:

1. **Task 1: CLI banner, --version/--quiet, init stub** - `3ddbadd` (feat)
2. **Task 2: Replace writer.py print block with rich summary table** - `58b1841` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `quirk/cli/__init__.py` - Empty package marker for quirk.cli
- `quirk/cli/banner.py` - print_banner(version, quiet) using rich Panel with styled BANNER_ART
- `quirk/cli/init_cmd.py` - Stub run_init() raising NotImplementedError (Plan 05 overwrites)
- `run_scan.py` - --version, --quiet args; init/serve intercepts; banner call; tqdm removal
- `quirk/reports/writer.py` - rich Console + Table replacing print() scan summary block

## Decisions Made
- init subcommand intercept placed before serve intercept — mirrors serve pattern exactly
- tqdm=None retained after import removal to preserve any residual references during transition
- run_init() stub raises NotImplementedError to fail loudly if called before Plan 05 overwrites it
- rich imports placed at module top in writer.py — always available, no lazy import needed

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- CLI banner and --version flag fully functional
- test_cli_version.py: 1/1 passing
- test_rich_output.py: 2/2 passing
- Full suite: 158 passed, 7 pre-existing failures (test_cli_init, test_html_report, test_packaging — not caused by this plan)
- Plan 03 can proceed: HTML report implementation

---
*Phase: 07-polish-and-packaging*
*Completed: 2026-03-31*
