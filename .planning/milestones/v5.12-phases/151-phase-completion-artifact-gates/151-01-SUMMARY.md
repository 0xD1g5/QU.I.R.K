---
phase: 151-phase-completion-artifact-gates
plan: 01
subsystem: testing
tags: [pytest, pyyaml, git-hooks-precursor, phase-lifecycle, markdown-parsing]

# Dependency graph
requires: []
provides:
  - "check_phase_close() — pure ARTIFACT-01/02/03 decision function (VERIFICATION.md presence, VALIDATION.md staleness incl. Pitfall-4 legend-line guard, UAT-SERIES.md coverage)"
  - "check_destructive_archive() — pure ARTIFACT-04 decision function (Complete-marked phase content vanished with no matching milestone archive, incl. Pitfall-1 untracked-file-deletion guard)"
  - "load_validation_frontmatter(), load_phase_plan_files_modified(), disk_phase_dirs_under(), archived_phase_dirs(), parse_state_phase_maps() — impure loader/parser helpers, tmp_path-tested"
affects: ["151-02 (git hook wiring — consumes these functions in main())"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pure-function/loader split mirroring scripts/release_tag_hygiene.py: decision functions take already-parsed data and return (blocked, reasons, summary_markdown); loaders read from disk and never raise on missing/malformed input"
    - "importlib.util.spec_from_file_location module loading for scripts/ (no __init__.py) — exact mirror of tests/test_release_tag_hygiene.py"
    - "Verbatim-embedded fixture strings instead of on-disk .planning/ reads in tests, because .planning/ is entirely gitignored and not guaranteed present in every checkout/worktree"

key-files:
  created:
    - scripts/verify_phase_gates.py
    - tests/test_verify_phase_gates.py
  modified: []

key-decisions:
  - "Embedded the real 147-VALIDATION.md and 150-01-PLAN.md fixture content as literal triple-quoted strings in the test file rather than reading from .planning/ at test time — .planning/ is entirely gitignored (.gitignore: PUBREPO-PLANNING-EXCL), so a fixture path under .planning/ is not guaranteed to exist in every checkout, including this session's own worktree, which had only a partial snapshot of .planning/phases/150-.../"
  - "check_destructive_archive()'s docstring explicitly scopes the guarantee to 'the next commit after an unarchived deletion is blocked,' never 'the delete never happens' — a git hook has zero visibility into non-git filesystem operations (Pitfall 2, RESEARCH.md)"
  - "user_facing_plan_match() glob list: src/dashboard/, quirk/cli/, quirk/reports/, quirk/scanner/, quirk/hardware — per CONTEXT.md D-05 and RESEARCH.md Assumption A1"

patterns-established:
  - "Phase-completion artifact gate pure-decision-core pattern: parse-then-decide split keeps all four ARTIFACT gates unit-testable without subprocess/network/live-git, ready for a thin CLI/hook wrapper in 151-02"

requirements-completed: [ARTIFACT-01, ARTIFACT-02, ARTIFACT-03, ARTIFACT-04]

# Metrics
duration: 25min
completed: 2026-08-13
---

# Phase 151 Plan 01: Phase-Completion Artifact Gate Decision Core Summary

**Built the pure, unit-tested decision core (`check_phase_close()` + `check_destructive_archive()`) that would have caught all three v5.11 phase-close documentation gaps and the `phases.clear` ARCHIVE-MANIFEST.md incident — not yet wired to a git hook.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-08-13T20:45:00-04:00 (approx)
- **Completed:** 2026-08-13T20:53:00-04:00 (approx)
- **Tasks:** 2 completed
- **Files modified:** 2 (both newly created)

## Accomplishments

- `check_phase_close()` aggregates ARTIFACT-01 (VERIFICATION.md presence), ARTIFACT-02 (VALIDATION.md staleness via `is_validation_stale()`, with the Pitfall-4 legend-line false-positive guard verified against real, verbatim `147-VALIDATION.md` content), and ARTIFACT-03 (UAT-SERIES.md coverage via `user_facing_plan_match()` + `uat_series_has_entry()`) into one `(blocked, reasons, summary_markdown)` verdict, one reason string per violated gate.
- `check_destructive_archive()` reproduces the exact ARCHIVE-MANIFEST.md incident shape as a unit test and blocks on it, using working-tree directory-listing comparison (`disk_phase_dirs_under()`) rather than git-diff-based detection — proven git-tracking-independent via a plain-filesystem-write-then-delete test with zero `git add`/`git rm` involved (Pitfall 1 closed).
- `load_phase_plan_files_modified()` parses real `*-NN-PLAN.md` frontmatter on disk (tested against the real, verbatim `150-01-PLAN.md` `files_modified:` block) and feeds `check_phase_close()`'s ARTIFACT-03 gate with real loader output end-to-end within this plan's pure layer, not a hand-typed literal.
- 22 unit tests across both gate families, all passing, no subprocess/network/live-git-repo dependency.

## Task Commits

Each task was committed atomically, TDD RED then GREEN:

1. **Task 1: ARTIFACT-01/02/03 — check_phase_close() and its loaders**
   - `75fff16` (test) — 16 RED tests for check_phase_close(), is_validation_stale(), user_facing_plan_match(), uat_series_has_entry(), load_validation_frontmatter(), load_phase_plan_files_modified()
   - `4e0e6b6` (feat) — implementation, all 16 tests GREEN
2. **Task 2: ARTIFACT-04 — check_destructive_archive() and its loaders**
   - `22ec9df` (test) — 6 RED tests for check_destructive_archive(), disk_phase_dirs_under(), archived_phase_dirs(), parse_state_phase_maps(); confirmed red (AttributeError on undefined functions)
   - `62a1233` (feat) — implementation, all 22 tests GREEN (both tasks together)

**Plan metadata:** (this commit, docs-only — `.planning/` is gitignored so no code files are touched)

## Files Created/Modified

- `scripts/verify_phase_gates.py` (357 lines) — pure decision functions `check_phase_close()` and `check_destructive_archive()`, plus loaders `load_validation_frontmatter()`, `load_phase_plan_files_modified()`, `disk_phase_dirs_under()`, `archived_phase_dirs()`, `parse_state_phase_maps()`, and pure helpers `is_validation_stale()`, `user_facing_plan_match()`, `uat_series_has_entry()`
- `tests/test_verify_phase_gates.py` (502 lines) — 22 unit tests, including two real-fixture tests embedded verbatim (147-VALIDATION.md legend-line guard, 150-01-PLAN.md files_modified parsing)

## Decisions Made

- Fixture content for `.planning/`-sourced test cases (147-VALIDATION.md, 150-01-PLAN.md) is embedded as literal triple-quoted strings in the test file rather than read from disk at test time, because `.planning/` is entirely gitignored (`.gitignore: .planning/` under the "PUBREPO-PLANNING-EXCL" comment) and is not guaranteed complete in every checkout — confirmed empirically: this execution's own worktree had only a partial snapshot of `.planning/milestones/v5.12-phases/150-test-suite-green-baseline-ci-gate/` (missing `150-01-PLAN.md` and `147-VALIDATION.md` entirely). Content was copied verbatim from the main checkout before embedding, satisfying the plan's "reuse real fixture content, don't hand-invent a synthetic shape" instruction while keeping the test suite portable to any checkout/CI environment.
- `check_destructive_archive()`'s docstring explicitly states the achievable guarantee ("the next commit after an unarchived deletion is blocked") rather than the unachievable stronger claim ("the delete never happens") per RESEARCH.md Pitfall 2 — a git hook has no visibility into non-git filesystem operations like `gsd-sdk query phases.clear`.

## Deviations from Plan

None — plan executed exactly as written. Both tasks' `<behavior>` test lists, `<action>` implementation instructions, and `<acceptance_criteria>` were followed directly; only adaptation was the fixture-embedding approach above, which is faithful to the plan's underlying intent (reuse real content) while correcting for the gitignored-`.planning/` environment constraint this specific worktree surfaced.

## Issues Encountered

Initial test-file draft referenced `.planning/` fixture files by absolute path and failed with `FileNotFoundError` because this execution's worktree has only a partial `.planning/` snapshot (`.planning/` is gitignored repo-wide, so no checkout is guaranteed to have it complete — not unique to this worktree). Resolved by embedding the real file content as literal strings in the test file (see Decisions Made above) instead of reading from disk at test time.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

`scripts/verify_phase_gates.py`'s `check_phase_close()` and `check_destructive_archive()` are implemented, unit-tested, and ready to be wired into a `pre-commit` git hook in Plan 151-02, which will call `load_validation_frontmatter()`, `load_phase_plan_files_modified()`, `disk_phase_dirs_under()`, `archived_phase_dirs()`, and `parse_state_phase_maps()` against real repo state and pass their output into the two pure decision functions built here. No blockers.

---
*Phase: 151-phase-completion-artifact-gates*
*Completed: 2026-08-13*

## Self-Check: PASSED

- FOUND: scripts/verify_phase_gates.py
- FOUND: tests/test_verify_phase_gates.py
- FOUND: .planning/phases/151-phase-completion-artifact-gates/151-01-SUMMARY.md
- FOUND commit: 75fff16 (test — ARTIFACT-01/02/03 RED)
- FOUND commit: 4e0e6b6 (feat — ARTIFACT-01/02/03 GREEN)
- FOUND commit: 22ec9df (test — ARTIFACT-04 RED)
- FOUND commit: 62a1233 (feat — ARTIFACT-04 GREEN)
