---
phase: 150-test-suite-green-baseline-ci-gate
verified: 2026-08-13T21:15:00Z
status: passed
score: 4/4 success criteria verified
overrides_applied: 0
---

# Phase 150: Test Suite Green Baseline + CI Gate Verification Report

**Phase Goal:** `pytest -q` produces a green baseline on a clean supported environment, and CI
holds that baseline so a newly introduced failure is visible as a new failure instead of joining
the red background.
**Verified:** 2026-08-13T21:15:00Z
**Status:** passed
**Re-verification:** No — initial verification

This report is written against `150-CI-EVIDENCE.md` — the artifact recording the real GitHub
Actions run URLs, pytest summary lines, and log excerpts this phase's live-fire proof produced.
No criterion below is marked PASS from memory or from a local-only run; every PASS cites a run
URL, a file path with a line reference, or a command's captured output.

## Success Criteria (verbatim from ROADMAP.md, Phase 150)

### Criterion 1 — `pytest -q` run on a clean environment matching CI's Python version exits 0

**Verdict: PASS**

Primary evidence is the real CI run, not a local run — this phase's entire subject is refusing to
treat a local baseline as CI proof (the exact mistake Plan 150-03 caught itself making).

- **Real CI run:** [31723764281](https://github.com/0xD1g5/QU.I.R.K/actions/runs/31723764281),
  `push` trigger on `main`, commit `bbe8b557bf25393b4ac88c27e1141bbc89d052d4`. `Linux Full Suite`
  job concluded `success` on `ubuntu-latest`, Python `3.11.15` — the exact CI Python version
  (`.github/workflows/python-ci.yml`'s `Setup Python 3.11` step). Pytest summary:
  `3076 passed, 81 skipped, 73 xfailed, 10 xpassed, 299 warnings in 1302.33s (0:21:42)` —
  **0 failed**. (`150-CI-EVIDENCE.md` lines 8-29.)
- **Corroboration (not primary evidence):** Plan 150-04's CI-parity venv run — `.[all]`-only
  install outside the repo tree, same install boundary as CI — reproduced 32 of the original
  38 CI failures exactly, with the remaining 6 explained by concrete local-vs-CI environment
  differences (working-copy `.planning/` presence, Docker availability, stale egg-info). After
  Plans 150-05/150-06 fixed all 8 categories, the CI-parity venv's own final full-suite run went
  `0 failed` (`150-08-SUMMARY.md` "Precondition" section: `3050 passed, 80 skipped, 80 xfailed,
  3 xpassed`) — corroborating, not substituting for, the real CI green run above. That venv was
  built on Python 3.14.6 (no 3.11 interpreter available locally), a documented, accepted parity
  gap for interpreter version only (`150-04-SUMMARY.md` key-decisions) — the extras/install-step
  boundary this criterion actually depends on was still faithfully reproduced.

### Criterion 2 — CI runs the same full-suite gate (not a narrower `-m 'not slow'` subset) on every PR and every push to `main`

**Verdict: PASS**

- **File:** `.github/workflows/python-ci.yml` lines 397-421, `linux-full-suite` job.
  - Triggers: the job runs under the workflow's `pull_request` and `push: branches: [main]`
    events (same trigger set as the file's other jobs — no job-level trigger override).
  - No `continue-on-error` — the job comment at line 399-400 states explicitly: `"No
    continue-on-error — this job must gate (SUITE-03: a newly introduced failing test must fail
    the build)"`.
  - Install step (line 415-418): `pip install -e ".[all]"` + `pip install pytest` — matches D-01's
    documented extras boundary (no `identity`/`hw`/`api`).
  - Invocation (line 420-421): `pytest -q -m ""` — the explicit empty-marker override that
    includes `slow`-marked tests, not the repo-wide `pyproject.toml` default of
    `addopts = "-m 'not slow'"`.
- **Live confirmation the trigger set is real, not just declared:** both the green run
  (`31723764281`, `push` to `main`) and the red run (`31725715958`, `pull_request` against
  `main` from PR #10) actually fired from their respective real GitHub events — this is
  behavioral proof the workflow triggers are wired correctly, not just YAML that looks right.

### Criterion 3 — A newly introduced failing test, added deliberately as a smoke check during this phase, fails the CI build

**Verdict: PASS**

- **Red run:** [31725715958](https://github.com/0xD1g5/QU.I.R.K/actions/runs/31725715958),
  `pull_request` trigger, PR [#10](https://github.com/0xD1g5/QU.I.R.K/pull/10), branch
  `ci/smoke-check-150` (created from the green `main` commit, deleted after capture), commit
  `6f13c3f7698332102303ad7836ebb4c01988abf4`. `Linux Full Suite` job concluded **`failure`**.
  Pytest summary: `1 failed, 3076 passed, 81 skipped, 74 xfailed, 9 xpassed, 299 warnings in
  1269.69s (0:21:09)` — exactly one failure, matching the green run's baseline in every other
  count. (`150-CI-EVIDENCE.md` lines 31-68.)
- **Log excerpt** (`gh run view 31725715958 --log-failed`, `150-CI-EVIDENCE.md` lines 51-65)
  confirms the sole failure is
  `tests/test_ci_gate_smoke.py::test_phase_150_d07_ci_gate_smoke_check_deliberately_fails` with
  the expected `AssertionError` — no workflow-wiring bug (wrong path, wrong trigger) was found;
  the job appeared correctly on the PR and went red for the intended reason.
- **Revert confirmed:** `gh pr close 10 --delete-branch`; `git ls-remote --heads origin
  ci/smoke-check-150` empty; `git ls-tree origin/main tests/test_ci_gate_smoke.py` empty;
  `git log origin/main --oneline -- tests/test_ci_gate_smoke.py` empty — the smoke test never
  touched `main` at any point (`150-CI-EVIDENCE.md` lines 70-97; `150-08-SUMMARY.md` Self-Check).
- **Plan 150-08 Task 3 human approval:** user was presented both run URLs and confirmed all
  three items — green checks on the green run, a red `Linux Full Suite` X caused by
  `test_ci_gate_smoke` on the red run, and PR #10 closed/unmerged. Approved
  (`150-08-SUMMARY.md`, "Task 3 — Human confirmation checkpoint").

### Criterion 4 — The green-baseline standard and how to run it locally are documented for future contributors

**Verdict: PASS**

- **File:** root `CONTRIBUTING.md` (created Plan 150-02, extended Plan 150-05 D-14). Contains:
  the exact CI-matching command (`pytest -q -m ""`), why the empty `-m ""` matters relative to
  `pyproject.toml`'s `-m 'not slow'` default, the `.[all]` install step, a "Docker containers
  during `-m \"\"` runs" section (chaos-lab containers spin up under Docker, `./lab.sh certs`
  pre-generates certs without touching Docker), an explicit "green means 0 failed, skips/xfails
  are expected" statement, a pointer to `docs/test-triage-149.md` for why specific tests are
  quarantined, and a "CI" section naming the `Linux Full Suite` job and its no-`continue-on-error`
  gating behavior verbatim.
- Not duplicated into the Obsidian vault sync table per D-08 — `CONTRIBUTING.md` is a new,
  standalone root file, not one of CLAUDE.md's mapped `docs/*.md` → `20_Dev-Work/QUIRK/Guides/*.md`
  pairs; this is an intentional scope boundary, not a gap.

## Findings

### The 8 failure categories from run 31598809033, and which plan closed each

Run [31598809033](https://github.com/0xD1g5/QU.I.R.K/actions/runs/31598809033) (Plan 150-03's
first live-fire push) concluded `failure` with `38 failed, 3074 passed, 46 skipped, 73 xfailed,
7 xpassed` across 8 root-cause categories:

| Category | Count | Root cause | Closed by | Mechanism |
|---|---|---|---|---|
| A | 4 | Direct `.read_text()` on gitignored `.planning/audit-2026-05-08/AUDIT-TASKS.md`, no existence check | Plan 150-06 (D-15) | Existence-check skip guard, `gitignored_planning_dir` registry category |
| B | 6 | `hw` extras (pysnmp/pymodbus/bacpypes3) excluded from `.[all]` per D-01, tests hard-crashed instead of skipping | Plan 150-06 (D-09/D-10) | Per-test module-availability-flag skip guard, `ci_extras_gap` registry category |
| C | 18 | `api`/`schemathesis` extras excluded from `.[all]` per D-01 | Plan 150-06 (D-09/D-10) | Per-test `SCHEMATHESIS_AVAILABLE` guard, `ci_extras_gap` registry category |
| D | 6 | `openapi-spec-validator` absent (same `api` extras boundary) | Plan 150-06 (D-09/D-10) | Per-test `OPENAPI_AVAILABLE` guard, `ci_extras_gap` registry category |
| E | 1 | Chaos-lab `email` profile Docker bind-mount failure — `labs/email/certs/dovecot.{key,crt}` gitignored with no generator | Plan 150-05 (D-12/D-13) | New `ensure_profile_certs()` in `lab.sh`, wired into `up`/`all`/`reset`/`certs` |
| F | 1 | `identity` extras excluded from `.[all]` per D-01 | Plan 150-06 (D-09/D-11) | Per-test `impacket` import guard, `ci_extras_gap` registry category (applied per D-11 despite non-reproduction in the local parity venv) |
| G | 1 | `/api/sensor/push` route-existence test returned a false 404 | Plan 150-04 (D-17) | Root-caused as a test-construction defect — fastapi 0.141/starlette 1.6 stopped flattening `include_router()` routes; fixed with a recursive `_IncludedRouter`-aware route-path walker, no skip registered |
| H | 1 | Dead Phase-16-era test hardcoding `importlib.metadata.version("quirk") == "4.4.0"` against the pre-rename package name | Plan 150-04 (D-16) | Deleted outright |

Total: 4+6+18+6+1+1+1+1 = 38, matching the real run's failure count exactly.

A ninth item surfaced only in Plan 150-08's own precondition step (not part of the original 38):
3 new SIGSEGV failures in `tests/test_lab_profile_certs.py` (new in Plan 150-05), reproducing the
same macOS `fork()`-under-full-suite-load signature already diagnosed for the Phase 149 5-test
D-03 cluster. Closed via the same D-03 `xfail(strict=False)` treatment, user-approved at a
checkpoint, committed as `bbe8b55` before the final green push.

### D-03 observation — macOS fork()-SIGSEGV cluster on `ubuntu-latest`

Recorded as an observation only, per D-03's explicit instruction — no marker was changed as a
result. Both real CI runs report `xpassed` counts in the same range as the number of
`xfail(strict=False)`-marked SIGSEGV-cluster tests (10 on the green run, 9 on the red run,
against 8 total cluster tests), consistent with most or all of that cluster genuinely passing
outright on `ubuntu-latest` rather than exercising their `xfail` path — expected, since the
SIGSEGV signature is macOS `fork()`-semantics-specific and was never expected to reproduce on
Linux (`150-CI-EVIDENCE.md` "D-03 observation" section).

### D-06 items explicitly deferred to backlog (not silently dropped)

Four items flagged in `149-11-SUMMARY.md`'s "Next Phase Readiness" section were explicitly kept
out of this phase's scope and sent to backlog, per D-06 in `150-CONTEXT.md`:

1. The macOS fork()-SIGSEGV cluster's root-cause fix itself (a `multiprocessing` start-method
   change or CI-runner-level mitigation) — not blocking since D-03 means Linux CI sidesteps it
   entirely.
2. Widening `test_safe_filter_audit.py`'s `_has_upstream_sanitize`.
3. Widening `test_scan_error_gate.py`'s `_classify_rhs()` for `ast.IfExp` support.
4. An `otics` synthesizer for `tests/_cbom_profiles.py::PROFILE_ENDPOINTS` / a `googleapiclient`
   sandbox-parity note.

None of these block SUITE-02/SUITE-03 — all are already correctly quarantined/documented, and
pulling them in would have widened this phase beyond its roadmap-scoped boundary.

### Deviations recorded in Plans 150-04 through 150-08, including the D-17 disposition

- **Plan 150-04 (D-16):** `test_package_manifest_version_is_4_1_0` deleted outright, not fixed in
  place — its local-only pass traced to a stale, gitignored `quirk.egg-info` directory absent
  from any fresh checkout.
- **Plan 150-04 (D-17):** `/api/sensor/push` 404 disposed as a **test-construction defect**, not a
  production regression — `fastapi 0.141.1`/`starlette 1.6.0` changed `include_router()`'s
  internal representation to a lazy `_IncludedRouter` wrapper; confirmed via `TestClient` that the
  route dispatches correctly end-to-end (401/200). Fixed with a version-resilient recursive route
  walker; the assertion itself is unchanged.
- **Plan 150-06:** Two documented deltas from written plan estimates, both resolved per the plan's
  own "parity-venv run is the authority" instruction — `test_identity_surface.py`'s Category F
  test did not reproduce locally but was guarded anyway per D-11's explicit "do not special-case
  it," and `test_rest_fuzzer_probes.py` had 11 failing tests in the parity venv, not the 9
  estimated in `150-03-SUMMARY.md` (later confirmed as the accurate count by 150-04's independent
  reconciliation).
- **Plan 150-07:** ROADMAP.md's Phase 150 header corrected to "9 plans" (not the plan's literal
  "6 plans" instruction) to match the file's actual 9-entry plan list.
- **Plan 150-08:** No Rule 1-4 deviations from this agent's own execution scope — the 3-test
  SIGSEGV precondition fix (D-03 treatment) was applied by the orchestrator with explicit user
  approval before this agent's execution began, documented under "Precondition," not re-litigated
  as a deviation of the plan itself.

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `150-CI-EVIDENCE.md` | Real run URLs, pytest summary lines, log excerpt, revert confirmation | ✓ VERIFIED | 4 distinct `https://github.com` URLs (2 run URLs + repo/PR references), both green and red pytest summary lines, full log excerpt, revert command transcript |
| `.github/workflows/python-ci.yml` | `linux-full-suite` job, `.[all]`-only install, `pytest -q -m ""`, no `continue-on-error` | ✓ VERIFIED | Lines 397-421 confirmed |
| `CONTRIBUTING.md` | Green-baseline standard documented | ✓ VERIFIED | Root file, all D-08/D-14 content present |
| `docs/test-triage-149.md` | Phase 150 CI-parity addendum (35 new skips + D-16/D-17/D-12/D-13 notes) | ✓ VERIFIED (Plan 150-07) | 31 `ci_extras_gap` rows + 4 `gitignored_planning_dir` rows, matching `tests/skip_registry.py`'s Phase 150 block exactly |

## Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
|-------------|-------------|--------------|--------|----------|
| SUITE-02 | 150-01 through 150-08 | `pytest -q` on a clean supported environment produces a green baseline | ✓ SATISFIED | Real CI run 31723764281, `Linux Full Suite` `success`, 0 failed |
| SUITE-03 | 150-01 through 150-08 | The green baseline is held by CI — a newly-introduced failing test fails the build | ✓ SATISFIED | Real CI run 31725715958, `Linux Full Suite` `failure`, isolated to the deliberate smoke test; PR #10 closed unmerged, branch deleted |

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | None found — no criterion in this report is marked PASS without a citable run URL, file/line reference, or command output | — | — |

## Human Verification Required

None beyond what already occurred. Plan 150-08 Task 3's human checkpoint (both run URLs + PR
closed-unmerged state) was already presented to and approved by the user during that plan's
execution (2026-08-13) — this verification report cites that approval rather than re-requesting
it.

## Gaps Summary

No gaps. All four ROADMAP success criteria are PASS with real, citable evidence — the real CI
green run (31723764281) is the primary evidence for Criterion 1, not the corroborating local
CI-parity venv run. All 8 original failure categories are mapped to the plan that closed them,
the D-03 macOS-SIGSEGV observation is recorded as observation-only per its own instruction, and
the D-06 backlog deferrals are explicit rather than silently dropped. The phase's own defining
discipline — refusing to claim a green state that was never observed — held through to close:
Plan 150-03 caught itself mid-execution when the first live-fire push came back genuinely red,
and this report's Criterion 1 verdict is anchored to the second, real live-fire push's actual
result, not to any of the intermediate local/venv runs that preceded it.

---

_Verified: 2026-08-13T21:15:00Z_
_Verifier: Claude (gsd-executor, Task 1 of 150-09)_
