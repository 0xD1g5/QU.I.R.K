---
phase: 55-qramm-compliance-mapping-view
plan: "02"
subsystem: qramm-cli-staleness
tags: [qramm, staleness, cli, pytest, ci-gate]
dependency_graph:
  requires: [quirk/qramm/model_meta.py (Phase 51)]
  provides: [quirk/cli/qramm_cmd.py, run_scan.py qramm intercept, tests/test_qramm_staleness.py]
  affects: [run_scan.py argv dispatch, CI test suite]
tech_stack:
  added: []
  patterns: [argv-intercept, QUIRK_CI_STALENESS_OVERRIDE_DATE env-var override, exit-code-as-verdict]
key_files:
  created:
    - quirk/cli/qramm_cmd.py
    - tests/test_qramm_staleness.py
  modified:
    - run_scan.py
decisions:
  - "Used datetime.date.today() throughout — no datetime.utcnow() (DEBT-01 compliance)"
  - "Intercept ordering: init → serve → compliance → doctor → qramm → main argparse"
  - "QUIRK_CI_STALENESS_OVERRIDE_DATE env var shared by both CLI and pytest gate so the two paths agree on the verdict"
metrics:
  duration: "~10 minutes"
  completed: "2026-05-08"
  tasks_completed: 3
  files_changed: 3
requirements: [QRAMM-05, QRAMM-06, QRAMM-07]
---

# Phase 55 Plan 02: QRAMM Staleness CLI and CI Gate Summary

## One-liner

`quirk qramm status` CLI with exit-code staleness verdict, QUIRK_CI_STALENESS_OVERRIDE_DATE env-var override, and 6-test pytest gate covering shape/freshness/CLI smoke.

## What Was Built

### Task 1: quirk/cli/qramm_cmd.py

Created `quirk/cli/qramm_cmd.py` with `run_qramm_status()`. The function reads `QRAMM_MODEL` and `STALENESS_THRESHOLD_DAYS` from `quirk.qramm.model_meta`, computes days remaining, and prints a 4-column table (QRAMM Version, Last Verified, Days Remaining, Status). Exits 0 (FRESH) or 1 (STALE). `_resolve_today()` returns `datetime.date.today()` unless `QUIRK_CI_STALENESS_OVERRIDE_DATE` is set. No `datetime.utcnow()` per DEBT-01.

Commit: a099e77

### Task 2: run_scan.py qramm intercept

Inserted the `qramm` argv intercept block into `run_scan.py` immediately after the `doctor` intercept and before the main `argparse.ArgumentParser(...)` call. Intercept checks `_sys.argv[1] == "qramm"` and `_sys.argv[2] == "status"`, imports `run_qramm_status` lazily, and returns. Ordering: init → serve → compliance → doctor → qramm → main argparse.

`python run_scan.py qramm status` outputs FRESH table (exit 0) with current model dated 2026-05-05 (87 days remaining as of 2026-05-08).

Commit: 883c360

### Task 3: tests/test_qramm_staleness.py

Created 6-test pytest file covering:
- `test_qramm_model_shape` — QRAMM-05: required keys, ISO date parse, source_url, threshold type/value
- `test_qramm_model_not_stale` — QRAMM-06: production CI gate; respects `QUIRK_CI_STALENESS_OVERRIDE_DATE`
- `test_qramm_staleness_override_fresh` — +30 days yields FRESH
- `test_qramm_staleness_override_stale` — +100 days yields STALE
- `test_qramm_status_cli_smoke_fresh` — QRAMM-07: subprocess exits 0, stdout has FRESH
- `test_qramm_status_cli_smoke_stale_via_override` — subprocess with override exits 1, stdout has STALE

All 6 tests pass. `QUIRK_CI_STALENESS_OVERRIDE_DATE` appears 3 times — once in the gate test, once in the override-fresh test helper, once in the CLI stale smoke test.

Commit: 497f16a

## Deviations from Plan

None — plan executed exactly as written.

## Verification Results

```
pytest tests/test_qramm_staleness.py -x -q
...... 6 passed in 0.74s

python run_scan.py qramm status
QRAMM Version    Last Verified  Days Remaining   Status
----------------------------------------------------------------------
1.0              2026-05-05     87               FRESH
exit: 0

QUIRK_CI_STALENESS_OVERRIDE_DATE=2026-09-01 python run_scan.py qramm status
QRAMM Version    Last Verified  Days Remaining   Status
----------------------------------------------------------------------
1.0              2026-05-05     -29              STALE
exit: 1

python -m compileall quirk/cli/qramm_cmd.py run_scan.py
(clean)
```

## Known Stubs

None.

## Threat Flags

None — T-55-05 through T-55-08 all accepted/mitigated per plan threat model. No new unplanned security surface introduced.

## Self-Check: PASSED

- quirk/cli/qramm_cmd.py: FOUND
- tests/test_qramm_staleness.py: FOUND
- run_scan.py (modified): FOUND
- commit a099e77: FOUND
- commit 883c360: FOUND
- commit 497f16a: FOUND
