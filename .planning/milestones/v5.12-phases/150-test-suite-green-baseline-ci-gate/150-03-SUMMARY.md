---
phase: 150-test-suite-green-baseline-ci-gate
plan: 03
subsystem: ci
tags: [ci, pytest, github-actions, blocker]

# Dependency graph
requires:
  - phase: 150-test-suite-green-baseline-ci-gate
    plan: "02"
    provides: "linux-full-suite CI job + local .venv full-suite green baseline"
provides: []
affects: [150-03-retry, SUITE-02, SUITE-03]

# Tech tracking
tech-stack:
  added: []
  patterns: []

key-files:
  created: []
  modified: []

key-decisions:
  - "Halted at Task 1's explicit stop condition: the push-to-main Linux Full Suite run concluded failure (38 failed), not success. Per 150-03-PLAN.md Task 1 instructions this is a hard STOP — do not proceed to the red-run/live-fire step and do not paper over with new markers."

requirements-completed: []

# Metrics
duration: ~35min (halted mid-Task-1)
completed: 2026-08-12
---

# Phase 150 Plan 03: Live-Fire CI Gate Proof — BLOCKED at Task 1

**Pushed local `main` to `origin/main` as instructed (D-07 live-fire precondition); the resulting real GitHub Actions `Linux Full Suite` run failed with 38 test failures, tripping the plan's explicit "STOP, do not proceed to red-run" gate before any live-fire smoke test was attempted.**

## What Happened

Task 1's preconditions were verified clean (working tree clean, on `main`, `linux-full-suite`
job present in `.github/workflows/python-ci.yml`, `gh` authenticated as `0xD1g5`). Per the
explicit user-confirmed authorization in this session's objective, local `main` was pushed to
`origin/main`:

- **Push:** `git push origin main` — `a6d9384..0aa6c5b main -> main` (fast-forward, no force
  needed; branch protection bypass was GitHub's own "Bypassed rule violations" system message
  for a direct-push-with-admin-bypass, not anything this agent configured)
- **SHA confirmation:** local `HEAD` (`0aa6c5b19b1a6cdb3ab1f0789d6753757b886c19`) matched
  `origin/main`'s SHA exactly post-push
- **Triggered run:** `push: branches: [main]` fired
  [run 31598809033](https://github.com/0xD1g5/QU.I.R.K/actions/runs/31598809033)

All 4 Windows jobs in that run (`Windows Sensor Smoke`, `Windows Packaging Spike`,
`Windows Sensor Build`, `Windows Sensor E2E`) completed `success`. The new
**`Linux Full Suite` job completed `failure`** after 1260.30s (21 minutes):

```
38 failed, 3074 passed, 46 skipped, 73 xfailed, 7 xpassed, 299 warnings in 1260.30s (0:21:00)
```

Per 150-03-PLAN.md Task 1's explicit instruction:

> Wait for that main run's `Linux Full Suite` job to conclude... If it concludes `failure`, STOP
> and report the failing tests as a blocker in the SUMMARY — do not proceed to the red-run step
> and do not paper over it with new markers. A failing green-baseline run means SUITE-02 is not
> met on the CI environment and the phase needs replanning, not a workaround.

This SUMMARY documents that stop. **Task 2 (revert/live-fire smoke test) and Task 3 (human
checkpoint) were NOT executed** — there is nothing to revert (no smoke-test branch was ever
created) and no meaningful live-fire proof to seek human confirmation on while the green
baseline itself is red on the real CI environment.

`local main` **is now pushed to `origin/main` and stays pushed** — this is not itself reversible
without a force-push, which is out of scope for an auto-fix and was not requested. The failing
CI run is real, public, and visible on GitHub; it does not block further work on `main` (no
merge/PR was created), but it does mean the repo's CI dashboard currently shows a red
`Linux Full Suite` check on the latest commit until this blocker is resolved and a follow-up
green run is pushed.

## Failure Analysis (38 failures, categorized)

None of these are failures introduced by Plan 03 itself (Plan 03 modified no source files before
this point). They are pre-existing gaps in Plan 02's/Phase 149's environment assumptions,
surfaced for the first time by actually running `pip install -e ".[all]"` (D-01's literal,
narrower extras surface) on a genuine `ubuntu-latest` runner rather than a broad local `[all]
+[identity]+[hw]+[api]` sandbox. Phase 149's and Plan 02's "0 failed" baselines were both run
locally with `identity`/`hw`/`api` extras all installed — nobody had exercised a real "`.[all]`
only" install before this run.

### Category A — `.planning/` gitignored in the public repo (4 failures)

Tests read `.planning/audit-2026-05-08/AUDIT-TASKS.md` directly, which does not exist in the
public repo checkout (Phase 120 excluded `.planning/` from the public repo via `.gitignore`;
see project memory `project_public_repo_gsd_gotchas`). These tests have never run successfully
in CI/on a fresh public clone — this predates Plan 03 and predates Phase 150 entirely.

- `tests/scanner/test_phase57_invariants.py::test_audit_tasks_six_blockers_closed`
- `tests/test_audit_ledger_zero_open.py::test_audit_ledger_has_zero_bare_open_rows`
- `tests/test_audit_ledger_zero_open.py::test_deferred_and_wontfix_rows_have_rationale`
- `tests/test_extras_concurrency_expander.py::test_audit_rows_flipped_to_phase_71`

### Category B — `hw` extras excluded per D-01, tests hard-fail instead of skip (6 failures)

D-01 deliberately excludes `hw` (pysnmp) from `.[all]`. These tests reference
`bacpypes3`/`pymodbus`/`pysnmp`-backed attributes unconditionally rather than gating on the
extra's presence with a documented `skip_registry.py` entry, so they raise `AttributeError`
instead of skipping.

- `tests/test_bacnet_scanner.py::test_parse_device_object`
- `tests/test_bacnet_scanner.py::test_single_inflight_no_writes_unicast`
- `tests/test_modbus_scanner.py::test_parse_device_id`
- `tests/test_modbus_scanner.py::test_parse_device_id_decodes_bytes`
- `tests/test_modbus_scanner.py::test_single_inflight_no_writes`
- `tests/test_snmp_scanner_contract.py::test_arp_walk_import_guard_returns_empty_with_zero_network_calls`

### Category C — `schemathesis` excluded from `api` extras per D-01, hard-fail instead of skip (18 failures)

Same shape as Category B — `rest_fuzzer.py`-adjacent tests reference `schemathesis` attributes
unconditionally.

- `tests/test_rest_fuzzer_cascade.py` — 3 tests (`test_exception_only_cascade_trips_pause`,
  `test_success_resets_cascade_counter`, `test_5xx_only_cascade_still_trips`)
- `tests/test_rest_fuzzer_dedup.py` — 3 tests (`TestHSTSDedup::test_multi_path_hsts_produces_single_finding`,
  `TestHttpCredsDedup::test_multi_path_http_creds_produces_single_finding`,
  `TestDedupDoesNotCollapseDifferentTypes::test_hsts_and_http_creds_both_capped_individually_after_dedup`)
- `tests/test_rest_fuzzer_pinned_session.py::test_main_dispatch_mounts_pinned_adapter`
- `tests/test_rest_fuzzer_probes.py` — 9 tests (`TestRawSocketProbePreventsSSRF`,
  `TestRawProbeUsesPinnedIP`, `TestDispatchUsesAsTransportKwargs`, `TestScopeGate`,
  `TestBudgetCap`, `TestRateLimiter`, `TestFiveXxCascadePause`,
  `TestAlgConfusionProbeAccepted` x2, `TestBudgetCeilingBoundsAllTraffic` x2)

### Category D — `openapi-spec-validator` not installed, hard-fail instead of skip (6 failures)

Same shape again, in `tests/test_openapi_scanner.py`: `test_local_file_parse`,
`test_local_file_security_scheme_rows`, `test_url_scope_rejected`, `test_oversize_rejected`,
`test_external_ref_ssrf_guard`, `test_openapi_plaintext_server_evidence_counter`.

### Category E — chaos-lab `email` profile cert bind-mount failure (1 failure)

`tests/test_chaos_lab_idempotency.py::test_profile_re_up_is_idempotent[email]` fails because
`labs/email/certs/*.key` is gitignored (`labs/email/.gitignore` excludes `certs/*.key`) and no
script anywhere in the repo regenerates it before tests run. Docker's bind-mount creates an
empty directory when the source path doesn't exist, then fails to mount that directory onto the
container's file destination:

```
Error response from daemon: failed to create task for container: failed to create shim task:
OCI runtime create failed: runc create failed: unable to start container process: error during
container init: error mounting ".../labs/email/certs/dovecot.key" to rootfs at
"/etc/dovecot/private/dovecot.key": mount src=..., dst=..., flags=MS_BIND|MS_REC:
not a directory
```

### Category F — `identity` extras excluded per D-01 (1 failure)

`tests/test_identity_surface.py::Issue3ScanWindowRegressionTest::test_issue3_scan_window_returns_all_identity_protocols`
expects a `KERBEROS` identity finding that requires the `identity` extras (impacket), which
D-01 deliberately excludes from `.[all]`.

### Category G — possible real regression (1 failure)

`tests/test_sensor_ingest.py::test_push_endpoint_exists` — `/api/sensor/push` not found in the
FastAPI route table on a genuine `.[all]`-only install. Not yet root-caused; could be a real
route-registration gap specific to the narrower install surface, or another environment-specific
false failure. **Flagged HIGH PRIORITY for the replanning pass** since it is the one failure in
this run that isn't cleanly explained by an already-known extras-exclusion or `.planning/`
gitignore boundary.

### Category H — package metadata missing (1 failure)

`tests/test_v41_gap_closure.py::TestV41GapClosure::test_package_manifest_version_is_4_1_0` —
`importlib.metadata.PackageNotFoundError: No package metadata was found for quirk`. The CI job's
`pip install -e ".[all]"` step may not be producing discoverable package metadata (dist-info)
under this runner/pip version, or the test's version-consistency check needs updating (per
`149-04-SUMMARY.md`'s prior TARGET-derivation fix, this test class has drifted before).

## Root Cause Summary

Two structural gaps, not one:

1. **Test-quality gap (Categories B/C/D/F, 31 of 38 failures):** a large cluster of tests assume
   optional extras (`hw`, `api`'s `schemathesis`, `identity`) are installed and raise hard
   `AttributeError`/`ModuleNotFoundError` instead of taking a documented `skip_registry.py` skip
   path when they aren't. D-01's `.[all]`-only CI install is the first time this assumption has
   been tested against reality — Phase 149's and Plan 02's local baselines both ran with a
   broader `[all]+[identity]+[hw]+[api]` sandbox that masked this gap entirely.
2. **Environment/infra gaps (Categories A, E, H, 6 of 38 failures):** `.planning/` being
   gitignored in the public repo, the `email` chaos-lab profile's certs never being generated in
   CI, and a possible packaging-metadata issue with editable installs on `ubuntu-latest`.
3. **One unexplained failure (Category G)** that needs direct investigation before it can be
   confidently bucketed with the others.

None of this is a Rule 1/2/3 auto-fixable set of issues within a single task — fixing 31 tests'
skip-gating alone is a scope change to the phase (D-01 anticipated the *install* boundary but not
that ~31 tests would need modification to honor it), and the `email` cert / route-404 items each
need their own investigation. This is exactly the class of finding the plan's Task 1 stop
condition exists to catch: **"a local-only... simulation cannot catch a workflow-YAML wiring bug"**
generalizes here to *cannot catch an environment-assumption gap either* — only the real run
surfaced it.

## Task Commits

None. Task 1 halted before any files were modified (the push of already-committed `main` content
is not a new commit; no source or test files were created/changed in this plan before the stop
condition triggered).

## Deviations from Plan

**Not a deviation** in the Rule 1-4 sense — this is the plan's own designed stop condition
firing as intended. No auto-fix was attempted per the plan's explicit "do not paper over it with
new markers" instruction.

## Issues Encountered

See "Failure Analysis" above — 38 CI failures across 8 categories, requiring a replanning pass
before Plan 03 (or a successor plan) can proceed to the D-07 live-fire smoke test.

## User Setup Required

None for this SUMMARY. The next step is a scoping/replanning decision (likely a new
150-04-PLAN.md or a phase-level context update) covering:
1. Whether to widen the ~31 extras-gated tests with proper `skip_registry.py`-registered skip
   markers (matching the existing Phase 41/149 quarantine pattern) so `.[all]`-only CI runs
   cleanly skip them instead of failing.
2. Whether/how to regenerate `labs/email/certs/*.key` in CI before the `email` chaos-lab profile
   test runs (a lab.sh pre-step, matching the "Chaos Lab Maintenance" CLAUDE.md guidance).
3. Root-causing the `.[all]`-only `test_v41_gap_closure.py` package-metadata failure.
4. Investigating `test_sensor_ingest.py::test_push_endpoint_exists` specifically — is this a real
   regression or another environment artifact?
5. Confirming Category A (`.planning/`-gitignored tests) should simply be marked
   `optional_extra`/environment-skipped for the public-repo CI context, matching existing
   precedent for other environment-gated tests.

## Next Phase Readiness

**BLOCKED.** SUITE-02 (green baseline on real CI) is not met — the real `Linux Full Suite` run on
`main` is red. SUITE-03 (prove the gate bites via live-fire) cannot be meaningfully attempted
until SUITE-02 is actually true, per the plan's own Task 1 stop condition. This phase cannot be
marked complete; STATE.md is being updated with a blocker entry, not a completion entry.

The good news: `Windows Sensor Smoke`/`Packaging Spike`/`Sensor Build`/`Sensor E2E` all remain
green, and the underlying `linux-full-suite` job wiring itself (D-02) is confirmed correct — it
ran, installed `.[all]`, executed the true full suite (`-m ""`), and reported an accurate,
detailed failure list. The gate mechanism works; the baseline it is gating does not yet hold on
real CI.

## Self-Check: PASSED

- Run [31598809033](https://github.com/0xD1g5/QU.I.R.K/actions/runs/31598809033) — FOUND, confirmed `failure` conclusion for `Linux Full Suite` job via `gh run view`
- `git rev-parse HEAD` == `origin/main` SHA (`0aa6c5b19b1a6cdb3ab1f0789d6753757b886c19`) — CONFIRMED via `git ls-remote`
- `git status --porcelain` clean, no stray files from this plan — CONFIRMED
