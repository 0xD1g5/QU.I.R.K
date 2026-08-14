---
phase: 151-phase-completion-artifact-gates
plan: 02
subsystem: testing
tags: [git-hooks, pytest, pyyaml, phase-lifecycle, contributor-docs]

# Dependency graph
requires: ["151-01 (check_phase_close(), check_destructive_archive(), and their loaders)"]
provides:
  - "main() — CLI glue reading git diff --cached + on-disk .planning/docs/ state, wiring it into check_phase_close()/check_destructive_archive() with a 0/1/2 exit-code convention"
  - ".githooks/pre-commit — installable git hook wrapper invoking scripts/verify_phase_gates.py"
  - "CONTRIBUTING.md 'Installing the pre-commit artifact gate' section — one-time install command + --no-verify bypass caveat"
affects: ["151-03 (if any follow-on plan exists in this phase)"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Injectable git_runner/repo_root seams on main() so its branching logic is unit-testable without a real git subprocess, while the real end-to-end wiring is proven separately by a subprocess-driven hook_integration test against a disposable temp git repo"
    - "0/1/2 exit-code convention mirroring scripts/release_tag_hygiene.py's main(): 0 = clean, 1 = gate violation, 2 = hard error (both abort the commit from the shell wrapper's perspective)"
    - "Thin POSIX-shell hook wrapper with zero logic beyond repo-root resolution + exit-code propagation — all real logic stays in the tested Python layer"

key-files:
  created:
    - .githooks/pre-commit
  modified:
    - scripts/verify_phase_gates.py
    - tests/test_verify_phase_gates.py
    - CONTRIBUTING.md

key-decisions:
  - "main()'s phase-close assembly path calls load_phase_plan_files_modified() against the triggered phase's real on-disk directory (never an empty-list placeholder) — proven by a dedicated assembly-level test using the real 150-01-PLAN.md fixture content inherited from 151-01"
  - "hook_integration tests copy scripts/verify_phase_gates.py and .githooks/pre-commit into a disposable tmp_path git repo (rather than pointing at the real checkout) so both the shell wrapper's git rev-parse --show-toplevel resolution and the script's own REPO_ROOT (computed from __file__) resolve to the temp repo, giving a fully self-contained, non-destructive integration proof"
  - "check_destructive_archive() is invoked unconditionally in main() (not diff-gated), matching RESEARCH.md's Open Question 1 resolution — only the phase-close checks are cheap-gated behind the ROADMAP.md diff trigger per D-03"

patterns-established:
  - "Git-hook-wiring pattern for a pure-decision-core script: main() assembles real disk state into the pure functions' arguments; the shell hook is a near-zero-logic wrapper; end-to-end correctness is proven by one subprocess-driven temp-repo test, not by mocking git"

requirements-completed: [ARTIFACT-01, ARTIFACT-02, ARTIFACT-03, ARTIFACT-04]

# Metrics
duration: 35min
completed: 2026-08-13
---

# Phase 151 Plan 02: Wire the Artifact Gate into an Installable Git Hook Summary

**Wired 151-01's pure decision functions into a real, installable `git commit` pre-commit hook — `main()` CLI glue + `.githooks/pre-commit` + `CONTRIBUTING.md` install instructions — proven end-to-end by a subprocess-driven integration test against a disposable temp git repo, not just unit tests of the decision logic in isolation.**

## Performance

- **Duration:** ~35 min
- **Started:** 2026-08-13T20:56:00-04:00 (approx)
- **Completed:** 2026-08-13T21:05:00-04:00 (approx)
- **Tasks:** 3 completed
- **Files modified:** 4 (1 created, 3 modified)

## Accomplishments

- `_extract_phase_close_trigger()` parses the real `b09c9bc` diff-hunk shape (Pattern 5) and correctly handles decimal sub-phase numbers (`64.1`-style, Open Question 2).
- `main()` assembles real on-disk state — `<N>-VERIFICATION.md` presence, `<N>-VALIDATION.md` frontmatter via `load_validation_frontmatter()`, the **mandatory** `load_phase_plan_files_modified()` call against the triggered phase's real directory, and `docs/UAT-SERIES.md` — into `check_phase_close()`'s five arguments on the diff-gated path, and separately assembles `.planning/STATE.md`'s phase map + `disk_phase_dirs_under()` + `archived_phase_dirs()` into `check_destructive_archive()`'s arguments unconditionally on every commit.
- Adopted the 0/1/2 exit-code convention exactly per `release_tag_hygiene.py`'s precedent (0 = clean, 1 = gate violation, 2 = hard error), with `_run_git()` using list-form `subprocess.run` argv (never `shell=True`).
- `.githooks/pre-commit` is a 15-line, near-zero-logic POSIX shell wrapper: resolves the repo root via `git rev-parse --show-toplevel`, invokes `python3 scripts/verify_phase_gates.py`, propagates its exit code.
- Real end-to-end proof via `hook_integration` tests: a green-path commit through the installed hook succeeds; a red-path commit — flipping a `.planning/ROADMAP.md` Phase-checkbox to complete against a fixture phase directory missing its `VERIFICATION.md` — is rejected with a non-zero exit and stderr mentioning `VERIFICATION.md`.
- `CONTRIBUTING.md` gained an "Installing the pre-commit artifact gate" section immediately after "Running the test suite" (not buried, per RESEARCH.md Pitfall 3), documenting the one-time `git config core.hooksPath .githooks` command and the explicit `--no-verify` bypass caveat.
- 34 tests total in `tests/test_verify_phase_gates.py` (22 from 151-01 + 12 new from 151-02), all green.

## Task Commits

Each task was committed atomically, TDD RED then GREEN for Task 1:

1. **Task 1: main() CLI glue — diff-gated phase-close trigger + unconditional destructive-archive check**
   - `1fc1a18` (test) — 9 RED tests for `_extract_phase_close_trigger()` and `main()`'s branching (confirmed red: `AttributeError` on undefined `_extract_phase_close_trigger`)
   - `35d2aab` (feat) — implementation, all 31 tests GREEN (151-01 + Task 1)
2. **Task 2: .githooks/pre-commit wrapper + real end-to-end hook_integration test**
   - `212821e` (feat) — `.githooks/pre-commit` (executable, `0o755`) + 3 `hook_integration` tests against a disposable `tmp_path` git repo; all 34 tests GREEN
3. **Task 3: CONTRIBUTING.md — one-time hook install instructions**
   - `9536aea` (docs) — new "Installing the pre-commit artifact gate" section; `grep -c "core.hooksPath .githooks"` = 1, `grep -c -- "--no-verify"` = 2

**Plan metadata:** this SUMMARY.md — docs-only, `.planning/` is gitignored so no code files are touched.

## Files Created/Modified

- `scripts/verify_phase_gates.py` (+186 lines) — added `_extract_phase_close_trigger()`, `_run_git()`, `_run_phase_close_check()`, `_run_destructive_archive_check()`, `main()`, and `if __name__ == "__main__": sys.exit(main())`
- `.githooks/pre-commit` (new, 15 lines, mode `0o755`) — thin POSIX shell wrapper
- `tests/test_verify_phase_gates.py` (+277 lines across Tasks 1-2) — 9 `_extract_phase_close_trigger()`/`main()` unit tests + 3 `hook_integration` subprocess-driven temp-repo tests
- `CONTRIBUTING.md` (+24 lines) — "Installing the pre-commit artifact gate" section

## Decisions Made

- `main()`'s `repo_root`/`git_runner` parameters are injectable seams defaulting to the real `REPO_ROOT` global and a real `_run_git()`-backed closure respectively — this lets the unit tests in Task 1 exercise `main()`'s full branching logic (including the mandatory real-loader-output assembly path) against `tmp_path` fixture directories without any git subprocess or mocking, while Task 2's `hook_integration` tests are the sole place a real git subprocess and a real installed hook are exercised end-to-end.
- The `hook_integration` fixture repo copies both `scripts/verify_phase_gates.py` and `.githooks/pre-commit` into the disposable `tmp_path` repo (rather than symlinking to or invoking the real checkout's copies), so `main()`'s own `REPO_ROOT` (computed from `__file__`) and the shell wrapper's `git rev-parse --show-toplevel` both correctly resolve to the temp repo — this is what makes the test fully self-contained and non-destructive to the real repository's git state.
- Manual verification (per the plan's `<verification>` block) was run against this real repo checkout: `git config core.hooksPath .githooks`, staged a throwaway file, attempted a commit. The hook correctly ran and — because this repo's real `.planning/STATE.md` genuinely lists several v5.10/v5.11 phases (139-144) as `Complete` with no live or archived directory — `check_destructive_archive()` correctly BLOCKED the commit. This is expected, correct behavior (not a bug in this plan's code) but surfaces a **pre-existing, out-of-scope data gap** in this repo's own `.planning/` history, unrelated to 151-02's task scope; documented under Deviations below rather than silently fixed, since remediating six historical Complete-marked phases with no archive is a data-hygiene task, not a code task, and touching `.planning/STATE.md`/archiving those phases is outside this plan's `files_modified` scope. `core.hooksPath` was unset again immediately after the manual check, per the plan's explicit instruction not to leave it installed for the executor's own session.

## Deviations from Plan

None affecting code scope — plan executed exactly as written; all three tasks' `<behavior>`/`<action>`/`<acceptance_criteria>` were followed directly.

**Process note (not a deviation, but worth recording):** during the manual `<verification>` step, an initial attempt to clean up a throwaway scratch commit used `git reset --hard HEAD~1` under the incorrect assumption that the scratch commit had succeeded. The scratch commit had actually been correctly *blocked* by the hook (see Decisions Made above), so `HEAD~1` pointed at the just-created Task 3 commit (`9536aea`) instead of a scratch commit — the reset briefly detached it from `HEAD`. It was immediately recovered via `git reflog` (`git reset --hard 9536aea`) before any further action; the recovery was verified by re-confirming the commit's presence in `git log`, `CONTRIBUTING.md`'s content, and a clean `git status`. No commits, working-tree files, or test state were permanently lost.

## Known Data Gap Surfaced (out of scope for this plan)

The manual hook verification against this repo's real `.planning/STATE.md` genuinely found six phases (144/v5.11, 139-143/v5.10) marked `Complete` in a Phase Map table with no matching live `.planning/phases/` directory and no matching `.planning/milestones/v5.10-phases/` or `v5.11-phases/` archive directory. This is real signal from the newly-built `check_destructive_archive()` working correctly against production data — not a bug in this plan. Remediating it (either restoring/archiving the missing directories or correcting `STATE.md`'s phase-map rows) is a separate data-hygiene task, out of this plan's `files_modified` scope (`scripts/verify_phase_gates.py`, `tests/test_verify_phase_gates.py`, `.githooks/pre-commit`, `CONTRIBUTING.md`), and is flagged here for a future backlog item rather than silently left undiscovered.

## Issues Encountered

See "Process note" under Deviations above — a `git reset --hard` recovery via `git reflog` during manual verification cleanup, fully resolved with no data loss.

## User Setup Required

Each contributor (including this session's own worktree, if it is later merged and its hook is to be used) must run `git config core.hooksPath .githooks` once per clone to activate the gate — documented in `CONTRIBUTING.md`. Not run persistently in this session (unset after manual verification, per the plan's explicit instruction).

## Next Phase Readiness

`scripts/verify_phase_gates.py` now has a fully wired, installable `main()` + `.githooks/pre-commit` hook, proven end-to-end by `hook_integration` tests. All four ARTIFACT requirements (ARTIFACT-01..04) are closed as working, installable enforcement — not just unit-tested decision logic. If Plan 151-03 exists in this phase, it can build on this working hook without further wiring. The out-of-scope data gap noted above (six historical Complete-marked phases with no archive) should be triaged as a follow-up backlog item — running `git config core.hooksPath .githooks` in the real repo today will block the *next* real commit until it is resolved.

---
*Phase: 151-phase-completion-artifact-gates*
*Completed: 2026-08-13*

## Self-Check: PASSED

- FOUND: scripts/verify_phase_gates.py (main(), _extract_phase_close_trigger(), _run_git())
- FOUND: .githooks/pre-commit (executable, mode 0o755)
- FOUND: tests/test_verify_phase_gates.py (34 tests, all passing)
- FOUND: CONTRIBUTING.md ("Installing the pre-commit artifact gate" section)
- FOUND: .planning/phases/151-phase-completion-artifact-gates/151-02-SUMMARY.md
- FOUND commit: 1fc1a18 (test — main()/trigger RED)
- FOUND commit: 35d2aab (feat — main()/trigger GREEN, 31 tests)
- FOUND commit: 212821e (feat — .githooks/pre-commit + hook_integration, 34 tests)
- FOUND commit: 9536aea (docs — CONTRIBUTING.md install section)
