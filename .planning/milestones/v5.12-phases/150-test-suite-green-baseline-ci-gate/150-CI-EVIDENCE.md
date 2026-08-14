# Phase 150 CI Live-Fire Evidence (SUITE-02 / SUITE-03, D-07)

This artifact records the real GitHub Actions evidence for SUITE-02 (green baseline holds
on CI's own environment) and SUITE-03 (the gate genuinely bites on a real failure), gathered
per D-07's live-fire requirement — not a local-only simulation. It is the source
`150-VERIFICATION.md` cites for both requirements.

## Green run (SUITE-02) — `main`, `push` trigger

- **Run URL:** https://github.com/0xD1g5/QU.I.R.K/actions/runs/31723764281
- **Run ID:** `31723764281`
- **Trigger:** `push` to `main`
- **Commit SHA:** `bbe8b557bf25393b4ac88c27e1141bbc89d052d4`
- **`Linux Full Suite` job:** conclusion `success` (job ID `94526923118`), ran
  `2026-08-13T17:03:10Z` → `2026-08-13T17:25:35Z` (22m25s)
- **Runner / interpreter:** `ubuntu-latest`, Python `3.11.15` (`Setup Python 3.11` step)
- **Install step:** `pip install -e ".[all]"` (D-01 boundary — no `identity`/`hw`/`api` extras)
- **Pytest invocation:** `pytest -q -m ""` (D-04 — full suite, not the local `-m 'not slow'`
  default)
- **Pytest summary line:**
  ```
  3076 passed, 81 skipped, 73 xfailed, 10 xpassed, 299 warnings in 1302.33s (0:21:42)
  ```
  **0 failed.**
- **Windows jobs in the same run:** `Windows Sensor Smoke`, `Windows Packaging Spike`,
  `Windows Sensor Build`, `Windows Sensor E2E (frozen -> Linux-built console)` — all `success`.

No remediation cycle was needed for this run — it went green on the first push following the
`bbe8b55` D-03 SIGSEGV-cluster quarantine (see Remediation history below).

## Red run (SUITE-03) — `ci/smoke-check-150` PR branch, `pull_request` trigger

- **Run URL:** https://github.com/0xD1g5/QU.I.R.K/actions/runs/31725715958
- **Run ID:** `31725715958`
- **Branch:** `ci/smoke-check-150` (created from the green `main` commit `bbe8b55`, deleted after
  capture)
- **PR:** [#10](https://github.com/0xD1g5/QU.I.R.K/pull/10) — draft, **closed without merging**
- **Trigger:** `pull_request` against `main`
- **Commit SHA:** `6f13c3f7698332102303ad7836ebb4c01988abf4` (added exactly one file,
  `tests/test_ci_gate_smoke.py`, containing one unconditionally-failing `assert False` test with
  no skip/xfail/slow markers)
- **`Linux Full Suite` job:** conclusion **`failure`** (job ID `94533461221`), ran
  `2026-08-13T17:26:32Z` → `2026-08-13T17:48:21Z`
- **Pytest summary line:**
  ```
  1 failed, 3076 passed, 81 skipped, 74 xfailed, 9 xpassed, 299 warnings in 1269.69s (0:21:09)
  ```
  Exactly **1 failed** — the deliberately introduced test. All other counts match the green
  run's baseline (one test that was `xfailed` in the green run reports `xpassed` here instead of
  `xfailed`, an expected non-strict-xfail fluctuation unrelated to this proof — see D-03 below).
- **Log excerpt** (`gh run view 31725715958 --log-failed`):

  ```
  =================================== FAILURES ===================================
  __________ test_phase_150_d07_ci_gate_smoke_check_deliberately_fails ___________

      def test_phase_150_d07_ci_gate_smoke_check_deliberately_fails():
  >       assert False, "Phase 150 D-07 CI gate smoke check: deliberate failure to prove the gate bites"
  E       AssertionError: Phase 150 D-07 CI gate smoke check: deliberate failure to prove the gate bites
  E       assert False

  tests/test_ci_gate_smoke.py:13: AssertionError
  ...
  FAILED tests/test_ci_gate_smoke.py::test_phase_150_d07_ci_gate_smoke_check_deliberately_fails - AssertionError: Phase 150 D-07 CI gate smoke check: deliberate failure to prove the gate bites
  ```

- **Windows jobs in the same run:** all `success` — confirms the gate failure is isolated to
  `Linux Full Suite` and caused solely by the smoke test, not a workflow-wide problem.

## Revert confirmation

```
$ gh pr close 10 --delete-branch
✓ Closed pull request 0xD1g5/QU.I.R.K#10
✓ Deleted branch ci/smoke-check-150 and switched to branch main

$ git branch --list ci/smoke-check-150
(no output)

$ git ls-remote --heads origin ci/smoke-check-150
(no output)

$ test -f tests/test_ci_gate_smoke.py
(false — file absent from working tree)

$ git ls-tree origin/main tests/test_ci_gate_smoke.py | wc -l
0

$ git log origin/main --oneline -- tests/test_ci_gate_smoke.py
(no output — the file never touched main)

$ git status --porcelain
(clean)
```

PR #10 is closed and unmerged. The smoke test never landed on `main` at any point (it was
committed only on the now-deleted `ci/smoke-check-150` branch).

## D-03 observation (macOS fork()-SIGSEGV cluster on `ubuntu-latest`)

Per `docs/test-triage-149.md`, 8 tests carry `@pytest.mark.xfail(strict=False, ...)` for the
macOS `fork()`-under-full-suite-load SIGSEGV cluster: the original 5 from Phase 149
(`test_version.py::test_cli_version_subprocess`,
`test_vault_connector.py::test_pki_sha1_signed_ca_high_severity`,
`test_qramm_staleness.py::test_qramm_status_cli_smoke_fresh` and
`::test_qramm_status_cli_smoke_stale_via_override`,
`test_sensor_windows_smoke.py::TestCleanShutdownOnKeyboardInterrupt::test_keyboard_interrupt_in_run_sensor_exits_130`)
plus the 3 added in this plan's precondition step
(`tests/test_lab_profile_certs.py`, quarantined under the same D-03 disposition after
reproducing the identical SIGSEGV signature under macOS full-suite load).

Both real CI runs report **`xpassed` counts in the same range as the number of xfail(strict=False)
markers** (10 on the green run, 9 on the red run) — consistent with most or all of these tests
genuinely passing outright on the `ubuntu-latest` runner rather than exercising their `xfail`
path, exactly as D-03 predicted (the SIGSEGV cluster is macOS `fork()`-semantics-specific, not
expected to reproduce on Linux). This is recorded as an observation only, per D-03's explicit
instruction — `strict=False` tolerates either outcome and no marker was changed as a result of
this run.

## Remediation history

The first live-fire attempt (Plan 150-03) pushed `main` to `origin` and hit its own explicit stop
condition: the resulting real `Linux Full Suite` run,
[31598809033](https://github.com/0xD1g5/QU.I.R.K/actions/runs/31598809033), concluded `failure`
with `38 failed, 3074 passed, 46 skipped, 73 xfailed, 7 xpassed` across 8 root-cause categories
(extras-boundary test hard-failures instead of skips, gitignored `.planning/` fixture reads,
a chaos-lab cert bind-mount gap, a dead version-assertion test, and one FastAPI route-introspection
test-construction defect). Plans 150-04 through 150-07 closed every category: 150-04 stood up a
CI-parity venv and closed Categories G/H (D-16/D-17); 150-05 added idempotent chaos-lab cert
auto-generation for the `email`/`grpc-tls` profiles (D-12/D-13); 150-06 added 35 per-test skip
guards across Categories A/B/C/D/F (D-09/D-10/D-11/D-15); 150-07 corrected the
REQUIREMENTS.md/ROADMAP.md/UAT-SERIES.md status that had prematurely claimed SUITE-02/SUITE-03
complete. Immediately before this plan's push, the local CI-parity venv full-suite run surfaced 3
new failures in the just-added `tests/test_lab_profile_certs.py` (Plan 150-05), which reproduced
the same macOS fork()-under-full-suite-load SIGSEGV signature (`returncode=-11`) already
diagnosed and quarantined for the 5-test D-03 cluster; the user selected "Apply D-03 xfail
treatment" and it was applied directly (commit `bbe8b55`), after which the local parity-venv run
went `0 failed` (`3050 passed, 80 skipped, 80 xfailed, 3 xpassed`) and this plan's push produced
the genuinely green `31723764281` run recorded above — the first real, `.[all]`-only,
`ubuntu-latest` green baseline this phase has achieved.
