---
phase: 150-test-suite-green-baseline-ci-gate
plan: "08"
subsystem: ci
tags: [ci, pytest, github-actions, live-fire, blocker-resolution]

# Dependency graph
requires:
  - phase: 150-test-suite-green-baseline-ci-gate
    plan: "04"
    provides: "CI-parity venv + authoritative failure inventory"
  - phase: 150-test-suite-green-baseline-ci-gate
    plan: "05"
    provides: "chaos-lab cert auto-generation (Category E closed)"
  - phase: 150-test-suite-green-baseline-ci-gate
    plan: "06"
    provides: "35 extras-gap/gitignored-fixture skip guards (Categories A/B/C/D/F closed)"
  - phase: 150-test-suite-green-baseline-ci-gate
    plan: "07"
    provides: "corrected REQUIREMENTS.md/ROADMAP.md/UAT-SERIES.md status pending real proof"
provides: "real GitHub Actions proof of SUITE-02 (green baseline) and SUITE-03 (gate bites)"
affects: [150-09, SUITE-02, SUITE-03]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Live-fire CI gate proof: push to main for the green-run evidence, then a throwaway PR branch with one deliberately-failing, marker-free test for the red-run evidence, captured via gh run view --log-failed, then fully reverted (PR closed unmerged, branch deleted)"

key-files:
  created:
    - .planning/phases/150-test-suite-green-baseline-ci-gate/150-CI-EVIDENCE.md
  modified: []

key-decisions:
  - "Task 1's local full-suite precondition and the D-03 SIGSEGV quarantine for tests/test_lab_profile_certs.py (3 new tests) were applied by the orchestrator directly before this agent's execution began, as commit bbe8b55, following an explicit user choice at a checkpoint ('Apply D-03 xfail treatment') triggered by a fresh local parity-venv run surfacing 3 new failures reproducing the same macOS fork()-under-full-suite-load SIGSEGV signature already diagnosed for the 5-test Phase 149 cluster"
  - "Green-run and red-run evidence stored only on disk (.planning/ is gitignored on this public repo per the Phase 120 PUBREPO-01 decision) -- consistent with existing project convention; no git commit was possible or expected for 150-CI-EVIDENCE.md itself"

requirements-completed: [SUITE-02, SUITE-03]

# Metrics
duration: ~90min (incl. two ~22min real CI full-suite runs)
completed: 2026-08-13
---

# Phase 150 Plan 08: Live-Fire CI Gate Proof — SUITE-02 / SUITE-03 CLOSED

**Retried and completed what Plan 150-03 halted on: pushed the fully-remediated `main` to
`origin`, confirmed a genuinely green real `Linux Full Suite` GitHub Actions run
(0 failed, `.[all]`-only install, `ubuntu-latest`/Python 3.11), then live-fired the gate with a
deliberately failing test on a throwaway PR branch, captured the resulting real red run, reverted
cleanly, and got explicit human confirmation of both run URLs plus the closed-unmerged PR.**

## What Was Built

### Precondition (completed by the orchestrator before this agent's execution)

The first local CI-parity-venv full-suite confirmation run surfaced 3 new failures, all in
`tests/test_lab_profile_certs.py` (new in Plan 150-05), reproducing the identical
`returncode=-11` (SIGSEGV) signature from the `openssl` subprocess spawned by `./lab.sh certs`
already diagnosed and quarantined for 5 other tests in Phase 149
(`docs/test-triage-149.md`, D-03 — macOS `fork()`-under-full-suite-load instability). The user
was asked and chose "Apply D-03 xfail treatment" at a checkpoint; the orchestrator applied it
directly: `@pytest.mark.xfail(strict=False, ...)` added to all 3 test functions, 3 new
`tests/skip_registry.py` entries registered under `pre_existing_triage_149`, meta-gate verified
green, and the full CI-parity-venv suite reran to `0 failed` (3050 passed, 80 skipped, 80 xfailed,
3 xpassed). Committed as `bbe8b55` (`fix(150-08): quarantine test_lab_profile_certs.py SIGSEGV
cluster (D-03)`) before this agent's execution began.

### Task 1 — Green baseline on real CI (SUITE-02)

Verified preconditions (clean working tree, on `main`, `linux-full-suite` job present with its
`pip install -e ".[all]"` + `pytest -q -m ""` invocation unmodified, all 150-04 through 150-07
commits present), then pushed `main` to `origin`:

```
git push origin main
   2ba4519..bbe8b55  main -> main
```

`git rev-parse HEAD` (`bbe8b557bf25393b4ac88c27e1141bbc89d052d4`) matched `origin/main`'s SHA
exactly. This fired the `push: branches: [main]` trigger, producing real run
[31723764281](https://github.com/0xD1g5/QU.I.R.K/actions/runs/31723764281). Watched to
completion:

- **`Linux Full Suite`:** conclusion **`success`**, ran 22m25s on `ubuntu-latest`, Python 3.11.15
- **Pytest summary:** `3076 passed, 81 skipped, 73 xfailed, 10 xpassed, 299 warnings in 1302.33s
  (0:21:42)` — **0 failed**
- All four Windows jobs (`Windows Sensor Smoke`, `Windows Packaging Spike`,
  `Windows Sensor Build`, `Windows Sensor E2E`) also `success`

No remediation cycle was needed — the run was green on the first attempt following the D-03
quarantine. SUITE-02 is proven on CI's own real environment, not inferred from a local run.

### Task 2 — Live-fire the gate, capture the red run, revert (SUITE-03, D-07)

Created branch `ci/smoke-check-150` from the green `main` commit, added
`tests/test_ci_gate_smoke.py` containing exactly one unconditionally-failing
`assert False` test (no skip/xfail/slow markers, stdlib-only, module docstring stating it is
temporary), committed only on the branch, pushed, and opened draft PR
[#10](https://github.com/0xD1g5/QU.I.R.K/pull/10) against `main`.

The resulting `pull_request`-triggered run,
[31725715958](https://github.com/0xD1g5/QU.I.R.K/actions/runs/31725715958), concluded:

- **`Linux Full Suite`:** conclusion **`failure`**
- **Pytest summary:** `1 failed, 3076 passed, 81 skipped, 74 xfailed, 9 xpassed, 299 warnings in
  1269.69s (0:21:09)` — exactly 1 failed, matching the green run's baseline in every other count
- **Log excerpt confirms** the sole failure is
  `tests/test_ci_gate_smoke.py::test_phase_150_d07_ci_gate_smoke_check_deliberately_fails` with
  the expected `AssertionError` message — nothing else failed, and the job did appear correctly
  in the PR run (no workflow-wiring bug found)
- All four Windows jobs remained `success`, confirming the failure is isolated to the intended job

Reverted cleanly: `gh pr close 10 --delete-branch` closed PR #10 unmerged and deleted the remote
branch. Confirmed via `git branch --list`, `git ls-remote --heads origin ci/smoke-check-150`
(empty), `test -f tests/test_ci_gate_smoke.py` (false), `git ls-tree origin/main
tests/test_ci_gate_smoke.py` (empty), `git log origin/main --oneline --
tests/test_ci_gate_smoke.py` (empty) — the smoke test never touched `main` at any point.

Wrote `.planning/phases/150-test-suite-green-baseline-ci-gate/150-CI-EVIDENCE.md` recording both
run URLs, the pytest summary lines, runner OS/Python version, the failing-log excerpt, the revert
confirmation commands, a D-03 observation (10 and 9 `xpassed` on the green/red runs respectively,
consistent with most/all of the 8 `xfail(strict=False)`-marked SIGSEGV-cluster tests genuinely
passing outright on `ubuntu-latest` — recorded as fact only, no marker changed), and a
remediation-history paragraph linking the original failing run (31598809033) through Plans
150-04–150-07's fixes to this plan's green result.

### Task 3 — Human confirmation checkpoint

Presented both run URLs and the verification steps to the user. User confirmed all three items:
(1) the green run shows green checks, (2) the red run shows a red X at `Linux Full Suite` caused
by `test_ci_gate_smoke`, (3) PR #10 is closed and not merged. **Approved.**

## Task Commits

| Task | Commit | Message |
|---|---|---|
| (precondition, pre-agent) | `bbe8b55` | `fix(150-08): quarantine test_lab_profile_certs.py SIGSEGV cluster (D-03)` |
| 1 | none | Push-only (already-committed content); no new source/test files modified |
| 2 | `6f13c3f` (on now-deleted `ci/smoke-check-150` branch, never merged to `main`) | `test(150-08): Phase 150 D-07 CI gate smoke check (deliberately failing, temporary)` |

`150-CI-EVIDENCE.md` itself has no git commit — `.planning/` is gitignored on this public repo
(Phase 120 PUBREPO-01), matching existing project convention for all `.planning/` artifacts.

## Deviations from Plan

**None requiring Rule 1-4 action from this agent.** The plan's own precondition step (local
full-suite confirmation before push) surfaced 3 new SIGSEGV failures that were resolved by the
orchestrator, with explicit user approval, before this agent's execution began — documented above
under "Precondition," not re-litigated here. No new failure classes appeared on either real CI
run; both concluded exactly as expected (`success` for the green baseline, `failure` isolated to
the one deliberate test for the live-fire proof).

## Issues Encountered

None. Both real CI runs behaved exactly as the plan anticipated; no remediation-and-re-push cycle
was required for Task 1, and the workflow wiring correctly picked up the smoke test's failure on
the first PR run for Task 2 (no wiring bug to fix).

## User Setup Required

None. All git/gh operations (push, branch, PR create/close, branch delete) were performed by this
agent under the standing pre-authorization documented in the plan's `<user_approval>` context.

## Next Phase Readiness

SUITE-02 and SUITE-03 are now proven on real GitHub Actions, closing the blocker Plan 150-03 left
open. Phase 150's remaining scope is Plan 150-09 (final phase-close documentation/verification
pass, if any remains — REQUIREMENTS.md/ROADMAP.md status corrections were already applied by Plan
150-07 in anticipation of this proof landing). `150-CI-EVIDENCE.md` is ready for
`150-VERIFICATION.md` to cite directly.

## Self-Check: PASSED

- `.planning/phases/150-test-suite-green-baseline-ci-gate/150-CI-EVIDENCE.md` — FOUND, contains 4
  distinct `https://github.com` URLs, `test_ci_gate_smoke` appears 6 times
- Commit `bbe8b55` — FOUND via `git log --oneline --all | grep bbe8b55`
- Run `31723764281` — FOUND, confirmed `success` conclusion for `Linux Full Suite` via
  `gh run view`
- Run `31725715958` — FOUND, confirmed `failure` conclusion for `Linux Full Suite` via
  `gh run view`
- PR `#10` — FOUND, confirmed `closed`/`merged: false` via `gh pr close` output and repo state
- `git ls-remote --heads origin ci/smoke-check-150` — empty, CONFIRMED
- `git ls-tree origin/main tests/test_ci_gate_smoke.py` — empty, CONFIRMED
- `git status --porcelain` — clean, CONFIRMED
