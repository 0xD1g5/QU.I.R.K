---
phase: 150-test-suite-green-baseline-ci-gate
plan: 02
subsystem: ci
tags: [ci, pytest, github-actions, contributing-docs]

# Dependency graph
requires:
  - phase: 150-test-suite-green-baseline-ci-gate
    plan: "01"
    provides: "impacket>=0.13.0-tolerant _build_as_req + un-quarantined Kerberos tests (this plan's local baseline reflects that fix)"
provides:
  - "Gating linux-full-suite CI job in .github/workflows/python-ci.yml (SUITE-03)"
  - "Confirmed local full-suite green baseline evidence (SUITE-02)"
  - "Root CONTRIBUTING.md documenting the green-baseline testing standard (D-08)"
affects: [150-03]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "New ubuntu-latest/Python-3.11 Linux pytest job added additively to python-ci.yml, mirroring python-staleness.yml's role+platform shape but installing .[all] + running the true full suite"

key-files:
  created:
    - CONTRIBUTING.md
  modified:
    - .github/workflows/python-ci.yml

key-decisions:
  - "Local baseline verification uncovered an environment footgun, not a code defect: the shell's default `python`/`pip` resolve to different interpreters (python -> Homebrew Python 3.14, pip -> a stray ~/Library/Python/3.9 user install). Running `python -m pytest` against that mismatched pip's site-packages produced 11 false failures (bacnet_scanner/modbus_scanner/openapi_scanner) because pip had installed hw/api extras into the 3.9 site-packages pytest never sees. Re-run using the repo's `.venv/bin/python` (which has [all]+[hw]+[identity]+[api] all consistently installed) produced a clean 0-failed baseline. This is a local sandbox interpreter-mismatch issue, not a CI-relevant defect — CI's `actions/setup-python` + `pip install -e \".[all]\"` in the same job step guarantees interpreter/pip consistency, so this footgun cannot reproduce in the new linux-full-suite job."
  - "Job key linux-full-suite / display name 'Linux Full Suite', matching the existing Windows-job naming convention (windows-sensor-smoke -> Windows Sensor Smoke, etc.)"
  - "No job-level permissions: block added — the job inherits the workflow-level contents:read (IN-01), asserted by the Task 2 YAML check"

requirements-completed: [SUITE-02, SUITE-03]

# Metrics
duration: 40min
completed: 2026-08-12
---

# Phase 150 Plan 02: Linux Full-Suite CI Gate + Local Baseline Summary

**Added the first gating Linux/pytest job to `python-ci.yml` (installs `.[all]` only, runs `pytest -q -m ""`, no `continue-on-error`), confirmed a clean 0-failed local full-suite baseline, and documented the green-baseline testing standard in a new root `CONTRIBUTING.md`.**

## Performance

- **Duration:** ~40 min
- **Tasks:** 3
- **Files modified:** 2 (1 modified, 1 created)

## Accomplishments

- Confirmed a genuine 0-failed local full-suite baseline (Task 1), after diagnosing and
  working around a local sandbox `python`/`pip` interpreter-mismatch footgun that initially
  produced 11 false failures
- Added `linux-full-suite` (display name `Linux Full Suite`) to `.github/workflows/python-ci.yml`
  — `ubuntu-latest`, Python 3.11, `pip install -e ".[all]"` + `pip install pytest`, then
  `pytest -q -m ""`; no `continue-on-error`, no job-level `permissions:` override; purely
  additive to the file (verified via `git diff --unified=0 | grep -c '^-[^-]'` == 0)
- Created root `CONTRIBUTING.md` documenting the exact CI-matching local command
  (`pytest -q -m ""`), the "green means 0 failed" standard, the `skip_registry.py`
  registration requirement, and a pointer to `docs/test-triage-149.md`

## Task Commits

1. **Task 1: Establish the local full-suite green baseline (SUITE-02)** - no commit (evidence-gathering only, no files modified)
2. **Task 2: Add the gating Linux full-suite job to python-ci.yml (D-01, D-02, D-04)** - `3532c44` (feat)
3. **Task 3: Write CONTRIBUTING.md documenting the green-baseline standard (D-08)** - `0106a5f` (docs)

## Files Created/Modified

- `.github/workflows/python-ci.yml` — new `linux-full-suite` job appended under the existing
  `jobs:` mapping; `windows-sensor-smoke`, `windows-packaging-spike`, `windows-sensor-build`,
  `windows-sensor-e2e` and the top-of-file `name:`/`on:`/`permissions:` block are byte-unchanged
- `CONTRIBUTING.md` (new, 74 lines) — root-level contributor testing standard

## Local Full-Suite Baseline Evidence (Task 1, SUITE-02)

**Correct run** (using `.venv/bin/python`, which has `[all]` + `[identity]` + `[hw]` + `[api]`
all installed so no extras-gated test spuriously fails):

```
3089 passed, 42 skipped, 80 xfailed, 126 warnings in 307.37s (0:05:07)
```

- **Exit code:** 0
- **`python -V`:** `Python 3.14.6`
- **Platform:** macOS (Darwin), local dev sandbox — CI itself runs `ubuntu-latest`/Python 3.11
  via `actions/setup-python`, per D-02
- **`^FAILED` line count in the scratchpad log:** 0
- **`git status --porcelain`:** clean before and after the run — no files modified by Task 1
- Counts are close to but not identical to Phase 149's final reconciliation
  (3088 passed / 42 skipped / 81 xfailed) because Plan 01 of this phase un-quarantined 2
  Kerberos tests (`KDCOptions` fix) that now run as real passes in an `[identity]`-installed
  sandbox instead of taking their old `xfail` path — expected drift, not a regression. Per
  the plan's explicit instruction, these numbers are not hardcoded anywhere outside this
  SUMMARY (they drift over time).

**Initial run (misleading, environment mismatch — NOT the reported baseline):** an earlier
run using the bare `python -m pytest` (i.e., the shell's default `python`, which resolves to
Homebrew's `/opt/homebrew/opt/python@3.14/bin/python3.14`) reported 11 failures across
`tests/test_bacnet_scanner.py`, `tests/test_modbus_scanner.py`, and `tests/test_openapi_scanner.py`.
Root-caused as a local sandbox footgun, not a code defect or a new flake class: the shell's
default `pip` resolves to a *different*, stray interpreter
(`~/Library/Python/3.9/lib/python/site-packages`, matching the known Phase 141 gotcha already
recorded in project memory — "pip install must target .venv explicitly"). That mismatched
`pip` had `bacpypes3`/`pymodbus`/`openapi-spec-validator` installed into Python 3.9's
site-packages, which the Python 3.14 interpreter running pytest never sees, so the affected
tests hit `ModuleNotFoundError`-driven `AttributeError`/assertion failures instead of the
expected pass (mirroring `tests/test_openapi_scanner.py`'s own already-documented "6 unrelated
`openapi-spec-validator not installed` failures... out of scope, logged in `deferred-items.md`"
finding from Phase 149 Plan 06). Re-running the identical suite via `.venv/bin/python`
(the repo's actual, fully-provisioned venv) eliminated all 11 failures with no code changes.
This is purely a local interpreter-selection issue: `.github/workflows/python-ci.yml`'s new
job runs `pip install -e ".[all]"` immediately after `actions/setup-python` sets up the exact
Python 3.11 interpreter the job uses for every subsequent step, so `pip`/`python` cannot
diverge in CI the way they can in an unmanaged local shell — this footgun does not reproduce
there. No SUMMARY blocker is raised for these 11 initially-observed failures since they are
not a real defect, not caused by this phase's changes, and confirmed to disappear entirely
under the correct interpreter.

## Decisions Made

- Job key/display name: `linux-full-suite` / `Linux Full Suite`, matching the existing
  `windows-*` naming convention in the same file.
- No pip caching added — executor discretion per CONTEXT.md/PATTERNS.md; kept the job as
  simple as the `python-staleness.yml` analog it mirrors.
- Used the local-baseline discovery (the `python`/`pip` interpreter mismatch) as confirmation
  that the CI job's own `actions/setup-python` + immediately-following `pip install -e ".[all]"`
  step ordering is the correct, footgun-proof pattern — no change was needed to the Task 2
  job design as a result, but it validates the design choice.

## Deviations from Plan

None — plan executed exactly as written. The 11 initially-observed local failures during
Task 1 were investigated per the task's own instructions ("If the run reports failures,
triage each...") and root-caused to a local sandbox environment issue outside the code and
outside this phase's scope, not a defect requiring a Rule 1/2/3 auto-fix. No files were
modified as a result — Task 1 remains an evidence-gathering-only task with zero file changes,
as `git status --porcelain` confirms.

## Issues Encountered

- Local shell's default `python`/`pip` resolve to different interpreters (documented above).
  Not fixed as part of this plan (no production or test code was wrong) — noted here and in
  `key-decisions` for future executors in this same sandbox: always use `.venv/bin/python` for
  full-suite baseline runs in this repo, matching the pre-existing Phase 141 memory note.

## User Setup Required

None — no external service configuration required. The new CI job requires no repository
secrets (D-07's live-fire proof, if performed, is Plan 03's concern per this phase's plan split;
this plan only wires the job and records the local baseline).

## Next Phase Readiness

- The `linux-full-suite` job is wired and additive; Plan 03 (if it proves the gate bites via a
  live-fire failing-test smoke check, D-07) can proceed independently — no blockers from this
  plan.
- `CONTRIBUTING.md` is in place for any future plan that needs to reference the testing
  standard.

## Self-Check: PASSED

- `CONTRIBUTING.md` — FOUND on disk
- `.github/workflows/python-ci.yml` — FOUND on disk, contains `linux-full-suite` job
- Commit `3532c44` — FOUND in `git log`
- Commit `0106a5f` — FOUND in `git log`
