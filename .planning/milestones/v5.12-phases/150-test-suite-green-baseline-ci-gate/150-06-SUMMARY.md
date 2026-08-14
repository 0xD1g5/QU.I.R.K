---
phase: 150-test-suite-green-baseline-ci-gate
plan: "06"
subsystem: test-infra
tags: [pytest, ci-parity, skip-registry, extras, hw, identity, api, gitignored-fixture]

# Dependency graph
requires:
  - phase: 150-test-suite-green-baseline-ci-gate
    plan: "04"
    provides: "CI-parity venv at $HOME/.cache/quirk-ci-parity-venv + authoritative failure inventory"
provides: "35 of 38 real-CI failures resolved (Categories A, B, C, D, F) via per-test skip guards"
affects: [150-07, 150-08, 150-09, SUITE-02, SUITE-03]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Per-test availability-flag guard (if not <MODULE>.<FLAG>_AVAILABLE: pytest.skip(...)) as the first statement after the docstring, matching test_aws_connector.py:172's idiom"
    - "Per-test try/except ImportError guard for extras with no existing module flag (impacket)"
    - "Per-test existence-check guard (if not <path>.exists(): pytest.skip(...)) for gitignored fixture reads"
    - "Two new skip_registry.py categories (ci_extras_gap, gitignored_planning_dir) kept independently greppable from pre-existing optional_extra/live_infra/pre_existing_triage_149 rows"

key-files:
  created: []
  modified:
    - tests/test_bacnet_scanner.py
    - tests/test_modbus_scanner.py
    - tests/test_snmp_scanner_contract.py
    - tests/test_identity_surface.py
    - tests/test_rest_fuzzer_cascade.py
    - tests/test_rest_fuzzer_dedup.py
    - tests/test_rest_fuzzer_pinned_session.py
    - tests/test_rest_fuzzer_probes.py
    - tests/test_openapi_scanner.py
    - tests/scanner/test_phase57_invariants.py
    - tests/test_audit_ledger_zero_open.py
    - tests/test_extras_concurrency_expander.py
    - tests/skip_registry.py

key-decisions:
  - "test_identity_surface.py's Issue3ScanWindowRegressionTest test does not reproduce as a failure in this python-3.14 parity venv (it never calls impacket directly — it inserts a KERBEROS CryptoEndpoint row and hits /api/scan/latest), but D-11 explicitly mandates the same try/except impacket treatment for consistency with the other 30 skips and with D-05's identity-extras precedent; guarded per D-11 despite the local non-reproduction (documented as a delta, not a special case)"
  - "test_rest_fuzzer_probes.py: parity-venv run found 11 failing tests, not the 9 estimated in 150-03-SUMMARY.md; guarded exactly the 11 that actually fail per the plan's 'parity-venv run is the authority' instruction — this matches 150-04-SUMMARY.md's later, more precise reconciliation (11) exactly, so it is a stale-estimate correction, not a new gap"
requirements-completed: []

# Metrics
duration: ~50min
completed: 2026-08-12
---

# Phase 150 Plan 06: Extras-Gap + Gitignored-Fixture Skip Guards Summary

**Closed Categories A, B, C, D and F of the real-CI 38-failure breakdown (35 tests total) by adding a per-test skip guard to each affected test — gated on the scanner module's own availability flag or an existence check — instead of hard-crashing when `.[all]` deliberately omits the `hw`/`identity`/`api` extras or when the gitignored `.planning/` fixture is absent, and registered every new skip under two new, independently greppable `skip_registry.py` categories.**

## What Was Built

### Task 1 — hw/identity extras guards (Categories B, F — D-09, D-10, D-11)

Ran `tests/test_bacnet_scanner.py`, `tests/test_modbus_scanner.py`,
`tests/test_snmp_scanner_contract.py`, `tests/test_identity_surface.py` in the
CI-parity venv (`$HOME/.cache/quirk-ci-parity-venv`, no `hw`/`identity` extras) and
found exactly the expected 6 hard-crashing tests: 2 in `test_bacnet_scanner.py`
(`test_parse_device_object`, `test_single_inflight_no_writes_unicast`), 3 in
`test_modbus_scanner.py` (`test_parse_device_id`,
`test_parse_device_id_decodes_bytes`, `test_single_inflight_no_writes`), 1 in
`test_snmp_scanner_contract.py`
(`test_arp_walk_import_guard_returns_empty_with_zero_network_calls`). All 6 fail
because they `patch.object(mod, "<SomeRealExtrasClass>")` on an attribute that
only exists in the module namespace when the try/except import guard succeeded
— when the extra is absent, that class name was never bound.

Added a first-statement guard to each of the 6, checking the module's own
`_PYBACNET_AVAILABLE` / `_PYMODBUS_AVAILABLE` / `_PYSNMP_AVAILABLE` flag before
proceeding, with reasons naming the missing package exactly
("bacpypes3 not installed", "pymodbus not installed", "pysnmp not installed").

For `test_identity_surface.py::Issue3ScanWindowRegressionTest::test_issue3_scan_window_returns_all_identity_protocols`
(Category F), the parity venv did **not** reproduce a failure — the test never
imports impacket directly, it inserts a `KERBEROS` `CryptoEndpoint` row and
asserts it appears in `/api/scan/latest`'s `identity_findings`. Per D-11's
explicit instruction ("gets the same D-09 treatment ... do not special-case
it"), added a `try: import impacket / except ImportError: pytest.skip("impacket
not installed")` guard anyway, as the interfaces section required — documented
as a delta from local reproduction, not a plan deviation.

### Task 2 — api extras guards (Categories C, D — D-09, D-10)

Ran the 5 target files in the parity venv and found 24 failures: 18 across the
4 `rest_fuzzer` files (3 cascade, 3 dedup, 1 pinned_session, **11** probes — not
9 as `150-03-SUMMARY.md` estimated; matches `150-04-SUMMARY.md`'s later,
authoritative reconciliation exactly) and 6 in `test_openapi_scanner.py`. All
24 fail on the same root cause: `patch("quirk.scanner.rest_fuzzer.schemathesis")`
/ `from schemathesis.core.result import Ok` (rest_fuzzer files) or a call path
through `scan_openapi_spec` that silently degrades to a `missing_extra`
endpoint instead of raising/producing the asserted content (openapi file) when
`SCHEMATHESIS_AVAILABLE` / `OPENAPI_AVAILABLE` is `False`.

Added a `SCHEMATHESIS_AVAILABLE` / `OPENAPI_AVAILABLE` guard as the first
statement of each of the 24 failing tests (importing the flag alongside the
existing `run_fuzz_scan` / `scan_openapi_spec` import in each function, or
adding it to the file-level import in `test_rest_fuzzer_cascade.py`).
`test_rest_fuzzer_probes.py`'s remaining 10 non-guarded tests (of 21 total)
still execute and pass — the SSRF/scope-gate/budget-cap/rate-limiter/HSTS/TLS
fallback-path tests are untouched.

Re-synced the pre-existing `test_openapi_scanner.py` registry row (line 231
before edits, now 249 after 6 guards were inserted above it — beyond the +/-2
tolerance, confirmed via the meta-gate before finalizing).

### Task 3 — gitignored `.planning/` fixture guards (Category A — D-15)

Added an existence-check guard (`if not <path>.exists(): pytest.skip(...)`)
before each of the 4 direct `.read_text()` calls on
`.planning/audit-2026-05-08/AUDIT-TASKS.md` across
`tests/scanner/test_phase57_invariants.py::test_audit_tasks_six_blockers_closed`,
`tests/test_audit_ledger_zero_open.py::test_audit_ledger_has_zero_bare_open_rows`,
`tests/test_audit_ledger_zero_open.py::test_deferred_and_wontfix_rows_have_rationale`,
and `tests/test_extras_concurrency_expander.py::test_audit_rows_flipped_to_phase_71`.
Added `import pytest` to `test_audit_ledger_zero_open.py` (not previously
imported). Verified end-to-end by temporarily renaming the ledger file away:
the three-file run went from `40 passed` (present) to `36 passed, 4 skipped`
(absent), then back to `40 passed, 0 skipped` after restoring it — confirming
the assertions still fire when the private working copy has the file, and skip
cleanly when it does not (the real public-checkout condition).

Confirmed via `grep -rn "AUDIT-TASKS.md" tests/ | grep -v skip_registry` that
runtime reads exist only in these 3 guarded files (all other hits are comments,
docstrings, or the path constant itself).

### Skip registry finalization

Extended `tests/skip_registry.py`'s module docstring category enumeration to
list `ci_extras_gap` and `gitignored_planning_dir` alongside the 3 pre-existing
categories. Added 7 (Task 1) + 24 (Task 2) + 4 (Task 3) = **35 new rows**, kept
in dedicated, clearly-headed Phase 150 blocks distinct from the pre-existing
`optional_extra`/`live_infra`/`pre_existing_triage_149` rows — no existing row
was retro-categorized.

Ran `tests/test_skip_registry.py::test_no_unregistered_skips` (the AST-walking
meta-gate) after every task and at the end of Task 3 — `1 passed` throughout.
`LINE_TOLERANCE` (`2`) and `EXEMPT_FILES` (unchanged) were not touched.

## Verification

All 12 edited test files, run together in the CI-parity venv (`-m ""`, no
`hw`/`identity`/`api` extras):

```
92 passed, 35 skipped, 1 xfailed, 2 warnings in 1.45s
```

`0 failed`. `tests/test_skip_registry.py -q -m ""` → `1 passed`.

The same rest_fuzzer/openapi/bacnet/modbus/snmp/identity files, run in the
repo's broad `.venv` (which has all extras installed): all guarded tests PASS
(not skipped) — confirmed via `.venv/bin/python -m pytest ... -q -m ""` for
both extras-gap batches (48 passed/1 unrelated skip; 38 passed/1 unrelated
xfail), proving the guards gate on genuine availability, not unconditionally.

`grep -c "importorskip"` returns `0` for all 9 extras-gated files — no
module-level `pytest.importorskip()` was introduced anywhere, satisfying D-09's
core constraint. `python -m compileall -q tests/` exits `0`.

## Deviations from Plan

**None requiring Rule 1-4 action.** Two documented deltas from the plan's
written expectations, both explicitly anticipated and resolved per the plan's
own "parity-venv run is the authority" instruction:

1. **[Delta, not deviation] `test_identity_surface.py` Category F does not
   reproduce locally.** The parity venv shows this test passing even without
   impacket installed (it constructs its KERBEROS finding via direct DB
   insert, not by exercising the impacket-backed Kerberos scanner). Per D-11's
   explicit "do not special-case it" instruction and the interfaces section's
   exact guard specification, the guard was added anyway. No code was changed
   beyond the guard; the assertion text is untouched.
2. **[Delta, not deviation] `test_rest_fuzzer_probes.py` has 11 failing tests
   in the parity venv, not the 9 estimated in `150-03-SUMMARY.md`.** Guarded
   the 11 that actually fail, per the plan's explicit authority rule. This
   matches `150-04-SUMMARY.md`'s later, more precise reconciliation (11)
   exactly, confirming the earlier 150-03 count was a rough estimate later
   corrected, not a discrepancy introduced by this plan.

One minor counting note: the `grep -v '^ *#' tests/skip_registry.py | grep -c
"ci_extras_gap"` / `"gitignored_planning_dir"` acceptance-criteria checks each
count 1 higher than the number of guards added in their respective task,
because the module docstring's category-enumeration line (updated in Task 1,
non-comment text) also matches the grep pattern. The real gate —
`tests/test_skip_registry.py::test_no_unregistered_skips` — is unaffected by
this and passed throughout; this is a grep-pattern artifact in the plan's
verification command, not a registry defect.

## Issues Encountered

None beyond the two documented deltas above.

## User Setup Required

None. All verification ran against the existing CI-parity venv from Plan
150-04 (`$HOME/.cache/quirk-ci-parity-venv`) and the repo's own `.venv`; no new
setup was introduced.

## Next Phase Readiness

Categories B, C, D, F (31 tests, D-09/D-10/D-11) and A (4 tests, D-15) are now
fully closed — 35 of the 38 real-CI failures from `150-03-SUMMARY.md` are
resolved. Category E (chaos-lab `email`/`grpc-tls` cert generation, D-12/D-13)
was closed by Plan 150-05 (already complete). Categories G and H (D-16, D-17)
were closed by Plan 150-04 (already complete). Remaining phase work
(150-07/08/09) covers the new CI job itself (D-01 through D-04), the KDCOptions
bug fix (D-05), the live-fire CI proof (D-07), and `CONTRIBUTING.md` (D-08,
D-14) — none of which this plan's scope touched.

## Self-Check: PASSED

- `tests/test_bacnet_scanner.py` — FOUND, guards at lines 78, 108
- `tests/test_modbus_scanner.py` — FOUND, guards at lines 64, 103, 136
- `tests/test_snmp_scanner_contract.py` — FOUND, guard at line 711
- `tests/test_identity_surface.py` — FOUND, guard at line 484
- `tests/test_rest_fuzzer_cascade.py`, `test_rest_fuzzer_dedup.py`,
  `test_rest_fuzzer_pinned_session.py`, `test_rest_fuzzer_probes.py`,
  `test_openapi_scanner.py` — FOUND, 24 guards total confirmed via grep
- `tests/scanner/test_phase57_invariants.py`, `test_audit_ledger_zero_open.py`,
  `test_extras_concurrency_expander.py` — FOUND, 4 existence-check guards
  confirmed via grep
- `tests/skip_registry.py` — FOUND, 35 new rows + 2 new categories confirmed
- Commit `459d3b1` — FOUND via `git log --oneline --all | grep 459d3b1`
- Commit `9afe1a1` — FOUND via `git log --oneline --all | grep 9afe1a1`
- Commit `dd88598` — FOUND via `git log --oneline --all | grep dd88598`
- `tests/test_skip_registry.py::test_no_unregistered_skips` — `1 passed`
  confirmed after every task
