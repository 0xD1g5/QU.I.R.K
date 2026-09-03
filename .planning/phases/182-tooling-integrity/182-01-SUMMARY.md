---
phase: 182-tooling-integrity
plan: 01
subsystem: testing
tags: [pytest, gsd-tools, subprocess, regression-fixture, node]

# Dependency graph
requires: []
provides:
  - "Confirmed and documented `state begin-phase` argv/cwd contract"
  - "Behavioural regression fixture for Bug A (unanchored bold-field regex in state-document.generated.cjs)"
  - "Sensitivity-proving negative control for that fixture"
  - "tests/test_gsd_state_patch.py inside GATE-03's _COVERED_FILES from birth"
affects: [182-02, 182-03, 182-05]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "GSD_TOOLCHAIN_AVAILABLE skip-guard idiom (copied verbatim from VITEST_TOOLCHAIN_AVAILABLE)"
    - "unpatched_gsd_tree: session-scoped temp-copy fixture with a defensive pristine-source marker assertion"

key-files:
  created: [tests/test_gsd_state_patch.py]
  modified: [tests/test_cli_helper_usage.py, .planning/STATE.md, .planning/ROADMAP.md]

key-decisions:
  - "Resolved the argv contract by live verification: --cwd is a native global flag on gsd-tools.cjs (spliced pre-dispatch), not a subprocess cwd kwarg, so no tension with run_fork_safe's no-cwd-kwarg rule"
  - "Pristine source for the negative control falls back to state-document.generated.cjs.bak since gsd-pristine/ (182-03's deliverable) does not exist yet"
  - "Bug B (frontmatter reconstruction) explicitly out of scope for this plan/file — Wave 2 (182-02) owns it"

requirements-completed: []  # TOOL-01 spans plans 01/03 — deliberately NOT marked complete here

duration: 45min
completed: 2026-09-03
---

# Phase 182 Plan 01: Argv Contract Lock-Down + Bug A Fixture Summary

**Proved the `state begin-phase --cwd` argv contract live and landed a behavioural (not presence-only) regression fixture for Bug A's `.generated.cjs` patch, with a sensitivity-proving negative control run against a throwaway toolchain copy.**

## Performance

- **Duration:** ~45 min
- **Started:** 2026-09-03T12:35:00Z
- **Completed:** 2026-09-03T13:20:00Z
- **Tasks:** 2 completed
- **Files modified:** 2 (tests/test_gsd_state_patch.py created, tests/test_cli_helper_usage.py extended) + hand-edited STATE.md/ROADMAP.md

## Accomplishments

- Resolved the sole open Wave 0 blocker: `--cwd <path>` is `gsd-tools.cjs`'s own native global flag, spliced out of argv before dispatch, and `state begin-phase` takes named flags (`--phase`/`--name`/`--plans`) only — positionals silently no-op.
- Manually reproduced both the patched (survives) and unpatched (corrupts) behaviour of Bug A directly against the real toolchain before writing any test, confirming the exact repro text from the upstream report byte-for-byte.
- Landed `tests/test_gsd_state_patch.py` with 3 passing tests, all skipping honestly (via `GSD_TOOLCHAIN_AVAILABLE`) when `~/.claude/get-shit-done/` is absent (e.g. CI's `Linux Full Suite` job).
- Proved the negative control is genuinely sensitive, not vacuous, via a manual RED proof (see below), then reverted the temporary changes before committing.
- Extended GATE-03's `_COVERED_FILES` in `tests/test_cli_helper_usage.py` so the new file is inside the fork-safety AST gate from birth — additive only, does not raise Phase 183's unlisted-call-site count.

## Task Commits

Each task was committed atomically:

1. **Task 1: Lock down and prove the begin-phase argv/cwd contract** - `1e09f570` (test)
2. **Task 2: Bug A prose-survival fixture with a sensitivity-proving negative control** - `c593864a` (test)

## Files Created/Modified

- `tests/test_gsd_state_patch.py` - New file: toolchain guard, `_run_begin_phase`/`_seed_planning` helpers, `test_begin_phase_cwd_contract_is_honoured`, `unpatched_gsd_tree` fixture, `test_bug_a_prose_line_survives_begin_phase`, `test_bug_a_fixture_is_sensitive_to_the_unpatched_regex`
- `tests/test_cli_helper_usage.py` - Added `tests/test_gsd_state_patch.py` to `_COVERED_FILES`
- `.planning/STATE.md` - Hand-edited: Current focus, new 182-01 accumulated-notes entry, Current Position section, frontmatter status/progress
- `.planning/ROADMAP.md` - Hand-edited: 182-01-PLAN.md checkbox checked, Phase 182 progress table row updated to `1/5`

## Decisions Made

- **Argv contract resolution confirmed live, not just by static read:** ran `node gsd-tools.cjs state begin-phase --cwd <tmp> --phase 901 --name demo --plans 3` against both the installed (patched) toolchain and a throwaway `.bak`-swapped copy before writing any fixture, to see the exact before/after bytes.
- **Pristine-source fallback order implemented exactly as specified:** `~/.claude/gsd-pristine/get-shit-done/bin/lib/state-document.generated.cjs` first (182-03's future deliverable — does not exist yet, confirmed by `ls`), falling back to `~/.claude/get-shit-done/bin/lib/state-document.generated.cjs.bak` (present, and does not carry the `LOCAL PATCH (2026-09-03)` marker — confirmed by `diff` against the patched file, which shows exactly the one-line regex hunk).
- **STATE.md/ROADMAP.md hand-edited, no `gsd-sdk`/`gsd-tools` verb invoked** — per this phase's hard constraint (the verbs are literally the thing under test and not yet proven safe by this plan alone; 182-05 formally retires the workaround).

## Deviations from Plan

None — plan executed exactly as written. Both tasks landed with their required assertions; no Rule 1-4 auto-fixes were needed.

## Manual RED Proof (negative-control sensitivity)

Per the plan's Task 2 acceptance criteria, temporarily proved the negative control fails:

1. Temporarily redirected `_PRISTINE_CANDIDATES`'s second entry to point at the **patched** `state-document.generated.cjs` instead of the `.bak`, and re-ran `-k sensitive`. Result: `1 skipped` — the fixture's own defensive marker-assertion (`_LOCAL_PATCH_MARKER not in ...`) correctly detected the accidentally-patched source and skipped rather than running vacuously. This is itself proof that mitigation T-182-07 (pristine-source marker check) is live.
2. To force execution past that guard and observe the actual corruption assertions, additionally short-circuited the marker-skip check (`if False and ...`) so the fixture would proceed with the patched file as its "pristine" source. Re-ran `-k sensitive`:

```
E       assert 'LOCAL PATCH (2026-09-03)' not in "'use strict...Numbers };\n"
E         'LOCAL PATCH (2026-09-03)' is contained here:
E           );
E               // LOCAL PATCH (2026-09-03): anchor the bold pattern to line start with /m.
...
tests/test_gsd_state_patch.py:260: AssertionError
=========================== short test summary info ============================
ERROR tests/test_gsd_state_patch.py::test_bug_a_fixture_is_sensitive_to_the_unpatched_regex
2 deselected, 1 error in 0.09s
```

   The fixture's internal defensive assertion fired first (before the test body's own corruption assertions could even run), confirming that the guard machinery is genuinely load-bearing rather than a tautology that always passes. Both temporary edits were reverted immediately after capturing this output; `git diff --stat tests/test_gsd_state_patch.py` showed zero uncommitted changes before the real Task 2 commit was made, and no file under `~/.claude/get-shit-done/` was ever mutated (all copying happened under `tmp_path_factory`/manual scratch dirs, never in place).

## Verification Evidence

```
$ .venv/bin/pytest tests/test_gsd_state_patch.py -q
...                                                                      [100%]
3 passed in 0.22s

$ .venv/bin/pytest tests/test_cli_helper_usage.py -q
..                                                                       [100%]
2 passed in 0.08s

$ grep -c "subprocess\." tests/test_gsd_state_patch.py
0

$ grep -c "tests/test_gsd_state_patch.py" tests/test_cli_helper_usage.py
1

$ git diff --stat .planning/STATE.md   # taken before any hand-edit in this plan
(no output — clean)
```

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- 182-02 (Bug B preserve-unknown-keys merge) can proceed independently; this plan's `_seed_planning`/`_run_begin_phase` helpers and the confirmed argv contract are directly reusable there.
- 182-03 (`gsd-local-patches/` + `gsd-pristine/`) should populate
  `~/.claude/gsd-pristine/get-shit-done/bin/lib/state-document.generated.cjs` — once it does, this
  plan's `_resolve_pristine_state_document()` will prefer that path automatically (already first in
  `_PRISTINE_CANDIDATES`), no code change needed.
- TOOL-01 remains open (spans plans 01/03) — not marked complete in REQUIREMENTS.md per this plan's explicit constraint.

## Self-Check: PASSED

- `tests/test_gsd_state_patch.py` — FOUND
- `tests/test_cli_helper_usage.py` — FOUND (modified)
- Commit `1e09f570` — FOUND (`git log --oneline --all | grep 1e09f570`)
- Commit `c593864a` — FOUND (`git log --oneline --all | grep c593864a`)

---
*Phase: 182-tooling-integrity*
*Completed: 2026-09-03*
