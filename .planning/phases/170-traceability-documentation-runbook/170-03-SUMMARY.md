---
phase: 170-traceability-documentation-runbook
plan: 03
subsystem: test-infrastructure
tags: [testing, lab.sh, qramm, traceability]
dependency-graph:
  requires: []
  provides:
    - tests/test_lab_profile_args_precedence.py
    - src/dashboard/src/pages/__tests__/qramm-assessment-dimension-coverage.test.tsx
  affects:
    - tests/test_cli_helper_usage.py
tech-stack:
  added: []
  patterns:
    - "run_fork_safe with cd-in-shell-string (not cwd kwarg) to control subprocess working directory"
    - "MSW + RTL render test generating a 120-item fixture programmatically from DIMENSION_PRACTICE_AREAS"
key-files:
  created:
    - tests/test_lab_profile_args_precedence.py
    - src/dashboard/src/pages/__tests__/qramm-assessment-dimension-coverage.test.tsx
  modified:
    - tests/test_cli_helper_usage.py
decisions:
  - "Registered the new pytest file in test_cli_helper_usage.py's _COVERED_FILES per the mandatory fork-safety gate, even though the file itself never calls subprocess directly (only run_fork_safe) — matches the plan's explicit instruction and keeps future direct-subprocess regressions caught."
  - "Did not mark TRACE-03 complete via state.requirements.mark-complete — the plan shares that requirement with 170-04, which owns final annotation/closure."
metrics:
  duration: "~35m"
  completed: 2026-08-28
---

# Phase 170 Plan 03: DEBT-02 and QRAMM-08 real tests Summary

Wrote two genuinely new, currently-passing tests closing the "no discoverable test" gap RVW-010
flagged for DEBT-02 (`lab.sh` PROFILE_ARGS CLI-over-.env precedence) and QRAMM-08 (the 120-question,
4-dimension-tab QRAMM assessment page), using real assertions against the actual script and
component per locked decision D-02 — no hollow smoke tests, no new test infrastructure, no live
Docker.

## What Was Built

### Task 1: DEBT-02 — `tests/test_lab_profile_args_precedence.py`

Three real subprocess tests that invoke the actual `quantum-chaos-enterprise-lab/lab.sh` script's
`help` branch (which calls only `usage()` and never touches Docker) via
`bash -x lab.sh help`, spawned fork-safely through `tests/cli_helpers.py::run_fork_safe` (never a
raw `subprocess.run`/`Popen` — this file is registered in `tests/test_cli_helper_usage.py`'s
`_COVERED_FILES` AST forward-locking gate, alphabetically placed after
`test_db_migrate_cli.py`). The tests parse the `-x` xtrace output on stderr for the LAST top-level
`+ PROFILE_ARGS=` line (distinguishing it from the `++` nested trace produced while sourcing
`.env`) and assert:

1. A CLI-supplied `PROFILE_ARGS` environment variable beats a conflicting `.env` value
   (`--profile identity` wins over `--profile core`).
2. `.env`'s value is honored when no CLI override is set.
3. The resolved value is empty when neither is present.

Because `run_fork_safe` never accepts a `cwd` kwarg (forbidden by the AST gate), the working
directory is set inside the shell command text itself
(`cd '<tmp_path>' && exec '<bash>' -x '<lab.sh>' help`), with the temp `.env` written into a
pytest `tmp_path`-backed `tempfile.TemporaryDirectory()` — never touching a developer's real
`.env` at `quantum-chaos-enterprise-lab/`.

**What would break this test:** removing or reordering the snapshot-before-source lines in
`lab.sh` (i.e. reintroducing the original bug where `.env` could silently overwrite a CLI-supplied
`PROFILE_ARGS`) would flip test 1's assertion from `--profile identity` to `--profile core`,
failing loudly.

### Task 2: QRAMM-08 — `qramm-assessment-dimension-coverage.test.tsx`

A real React Testing Library render test of `AssessmentPage` (imported from
`@/pages/qramm-assessment`), using the same MSW `setupServer` / `vi.mock("@/lib/api", ...)` /
`vi.mock("@/hooks/useQRAMMSession", ...)` pattern as the sibling
`qramm-profile-submit-error.test.tsx`. The 120-question MSW fixture is generated programmatically
in a loop from the real `DIMENSION_PRACTICE_AREAS` constant (4 dimensions × 3 practice areas × 10
questions each), not hand-written. Three assertions:

1. Fixture sanity check — 120 total questions, 30 per dimension (matching the backend invariant
   already established by `test_qramm_questions.py`).
2. All 4 dimension `TabsTrigger`s (CVI/SGRM/DPE/ITR) plus Scorecard and Compliance Map render.
3. Clicking each dimension `TabsTrigger` in turn (Radix unmounts inactive `TabsContent` by
   default) reveals a `DimensionTab` whose `aria-label` reads `0 of 30 questions answered`; the 4
   per-tab totals are summed in the test itself and asserted to equal exactly 120.

**What would break this test:** any change that moves a question to a different dimension's
practice area, changes the per-dimension question count away from 30, or removes/renames a
`TabsTrigger` would fail assertion 2 or 3 (the sibling
`qramm-assessment-tab-comment.test.tsx`, by contrast, only checks a code comment string and would
not catch any of these regressions — that gap is exactly what this test closes).

## Verification

- `python -m pytest tests/test_lab_profile_args_precedence.py tests/test_cli_helper_usage.py -v`
  — 5 passed.
- `cd src/dashboard && npx vitest run src/pages/__tests__/qramm-assessment-dimension-coverage.test.tsx`
  — 3 passed.
- `cd src/dashboard && npm run lint` — clean (eslint + hook-cancellation-guard check).
- `grep -in docker` on both new files — only docstring/comment mentions of "Docker" (explaining
  what is NOT invoked); no `docker compose up`/`all`/`reset` command anywhere.

## Deviations from Plan

None — plan executed exactly as written. The interfaces note's option (b) for controlling the
subprocess working directory (shell `cd` inside the command string, not a `cwd` kwarg) was used as
specified.

## Requirement Status

TRACE-03 is intentionally NOT marked complete by this plan — per the plan's explicit instruction,
it is shared with 170-04 (which handles the requirement-ID annotation half), and
`state.requirements.mark-complete` has no per-phase granularity (it has falsely over-flipped a
requirement twice already this milestone). 170-04 or 170-07 owns TRACE-03's final closure.

## Self-Check: PASSED

- FOUND: tests/test_lab_profile_args_precedence.py
- FOUND: src/dashboard/src/pages/__tests__/qramm-assessment-dimension-coverage.test.tsx
- FOUND: tests/test_cli_helper_usage.py (modified, _COVERED_FILES entry present)
- FOUND commit 216052a (DEBT-02 test)
- FOUND commit 931ee46 (QRAMM-08 test)
