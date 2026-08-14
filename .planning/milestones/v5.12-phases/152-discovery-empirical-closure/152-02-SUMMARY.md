---
phase: 152-discovery-empirical-closure
plan: 02
subsystem: cli
tags: [interactive-cli, discovery, nmap, tdd, regression-test]

# Dependency graph
requires:
  - phase: 144-145 (chunked discovery + liveness pre-pass)
    provides: The nmap-discovery-first code path that this plan's default flip now routes
      default-accepting users into.
provides:
  - "enable_nmap interactive prompt now defaults to True"
  - "Static-source-check regression test locking the default in place"
affects: [interactive-mode, discovery-at-scale, v5.12-audit-closure]

# Tech tracking
tech-stack:
  added: []
  patterns: ["static source-text regression test to lock a config default in place"]

key-files:
  created: []
  modified:
    - quirk/interactive.py
    - tests/test_interactive_validate_routes.py

key-decisions:
  - "Preserved the D-06 single-global-toggle architecture and prompt copy exactly — only the default value changed, per CONTEXT.md."

patterns-established:
  - "Regex-anchored static source-check test (call-site + trailing comment marker) to regression-lock a specific keyword-argument default without depending on runtime prompt behavior."

requirements-completed: [DISC-11]

# Metrics
duration: 8min
completed: 2026-08-14
---

# Phase 152 Plan 02: Flip enable_nmap Interactive Default Summary

**One-line default flip in `quirk/interactive.py` (`default=False` → `default=True`) closes the v5.11 audit gap where accepting every interactive default silently skipped Phase 144/145 chunked discovery and the liveness pre-pass; locked in place by a new static-source-check regression test.**

## Performance

- **Duration:** 8 min
- **Started:** 2026-08-14T01:54:00Z
- **Completed:** 2026-08-14T02:02:15Z
- **Tasks:** 1 completed (TDD: RED + GREEN)
- **Files modified:** 2

## Accomplishments
- `enable_nmap` interactive prompt now defaults to `True` — a user accepting every default now exercises nmap port discovery and the Phase 145 liveness pre-pass automatically.
- New regression test statically asserts `default=True` (and not `default=False`) at the exact `enable_nmap = _prompt_bool(...)` call site, so a silent revert fails the build.
- D-06 single-global-toggle architecture and the "(recommended for >10 hosts)" prompt copy were left untouched, per CONTEXT.md guidance.

## Task Commits

Each task was committed atomically (TDD RED → GREEN):

1. **Task 1 (RED): add failing regression test for enable_nmap default=True** - `03f5901` (test)
2. **Task 1 (GREEN): flip enable_nmap default to True** - `6648cf7` (feat)

_No REFACTOR commit needed — no cleanup required after the one-line change._

## Files Created/Modified
- `quirk/interactive.py` - `enable_nmap = _prompt_bool(...)` call site: `default=False` → `default=True` (line ~178); D-06 comment and prompt text unchanged.
- `tests/test_interactive_validate_routes.py` - Added `test_interactive_py_enable_nmap_defaults_true`, a static source-text regression test anchored on the `enable_nmap = _prompt_bool(...)  # D-06` call site.

## Decisions Made
- Used a regex anchored to the trailing `# D-06` comment (rather than a naive non-greedy `.*?\)` match) because the prompt text itself contains a literal `)` in "(recommended for >10 hosts)", which would truncate a naive match before reaching the `default=` kwarg. Verified this by confirming RED failed with a legitimate assertion (matched substring lacked `default=True`) before the fix, not a regex bug.

## Deviations from Plan

None - plan executed exactly as written. The plan's example regex (`enable_nmap = _prompt_bool\((.*?)\)`) was adjusted during implementation to anchor on the `# D-06` trailing comment to avoid truncating at the parenthesis embedded in the prompt string; this is within the plan's stated latitude ("e.g. via a regex capturing the `_prompt_bool(...)` call arguments, or a bounded substring search") and does not change scope, files touched, or behavior.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## TDD Gate Compliance

Gate sequence verified in git log:
1. RED gate: `03f5901 test(152-02): add failing regression test for enable_nmap default=True` — confirmed failing against unflipped source before commit.
2. GREEN gate: `6648cf7 feat(152-02): default enable_nmap interactive prompt to True` — confirmed passing after the flip.
3. REFACTOR gate: not applicable (no cleanup needed).

## Next Phase Readiness

DISC-11 is closed. No blockers for remaining Phase 152 plans (152-03, 152-04). The static regression test guards against silent reversion, so downstream plans touching `quirk/interactive.py` will get immediate feedback if the default is ever reintroduced as `False`.

---
*Phase: 152-discovery-empirical-closure*
*Completed: 2026-08-14*

## Self-Check: PASSED

- FOUND: commit 03f5901 (test: RED regression test)
- FOUND: commit 6648cf7 (feat: default flip)
- FOUND: quirk/interactive.py
- FOUND: tests/test_interactive_validate_routes.py
- FOUND: SUMMARY.md (main-repo .planning path)
