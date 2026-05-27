---
phase: 114-automatic-merge-trigger
plan: "02"
subsystem: auto-merge / acceptance-tests
tags: [automerge, background-task, acceptance-tests, regression, fastapi]
dependency_graph:
  requires: [114-01]
  provides: [automerge-acceptance-tests, AUTOMERGE-01-test, AUTOMERGE-02-test, AUTOMERGE-03-test]
  affects: [tests/test_auto_merge_trigger.py]
tech_stack:
  added: []
  patterns: [file-backed SQLite test isolation, BackgroundTasks synchronous TestClient assertion, monkeypatch merge_scan failure injection]
key_files:
  created:
    - tests/test_auto_merge_trigger.py
  modified: []
decisions:
  - "File-backed SQLite used instead of in-memory for test DB — background task run_auto_merge uses get_session(db_path) so both the test client and the task must share the same file (QUIRK_DB_PATH tmp file)"
  - "7 tests implemented (6 CONTEXT acceptance tests + test_revoked_sensor_excluded split out as a discrete D-04 test for readability)"
  - "test_merge_failure_isolated patches quirk.merge.scan.merge_scan directly at module level via monkeypatch.setattr — run_auto_merge imports it locally so the module-level patch is what the background task sees"
  - "test_double_fire_harmless asserts MergeRun count <= count+1 (not exactly unchanged) per D-06 accepted TOCTOU tolerance"
  - "test_cadence_window_triggers uses cadence_window_minutes=0 so elapsed >= 0 is always true — avoids any timing fragility"
  - "test_manual_merge_regression calls merge_scan() directly (mirrors _cmd_merge internals) without sys.exit"
metrics:
  duration: "~15 minutes"
  completed: "2026-05-27"
  tasks_completed: 3
  files_changed: 1
---

# Phase 114 Plan 02: Auto-Merge Trigger Acceptance Tests Summary

Seven acceptance tests in `tests/test_auto_merge_trigger.py` gating AUTOMERGE-01/02/03, D-04, D-05, and D-06. All pass green; BackgroundTasks run synchronously under TestClient with no sleep.

## What Was Built

### Tasks 1-3: tests/test_auto_merge_trigger.py (commit b07d210)

One new test file with 7 acceptance tests covering all 6 CONTEXT `<specifics>` plus the D-04 revoked-sensor exclusion proof.

**File-backed SQLite isolation pattern:** The key design decision was using a file-backed SQLite pointed at `QUIRK_DB_PATH` for both the FastAPI `get_db` override and `run_auto_merge`'s own `get_session(db_path)`. In-memory SQLite (used by `test_sensor_ingest.py`) would have left the background task unable to find data written by the test client since they'd be operating on different in-memory DBs.

**Test inventory:**

| Test | Req | Assertion |
|------|-----|-----------|
| `test_all_sensors_in_triggers_merge` | AUTOMERGE-01 | After sensor-a push → 0 MergeRun; after sensor-b push → exactly 1 MergeRun |
| `test_auto_merge_disabled` | AUTOMERGE-02a | `enabled=false` in config → 0 MergeRun after both sensors push |
| `test_revoked_sensor_excluded` | D-04 | Revoked sensor-b excluded; sensor-a alone triggers → 1 MergeRun |
| `test_merge_failure_isolated` | AUTOMERGE-02b | merge_scan patched to raise → push=accepted, 0 MergeRun, 1 auto_merge/failed IntegrationDelivery with non-empty error_summary, no raw Traceback in audit row |
| `test_double_fire_harmless` | D-05/D-06 | Second push with no newer data → MergeRun count <= prior+1 (idempotent re-check) |
| `test_cadence_window_triggers` | AUTOMERGE-02c | `cadence_window_minutes=0` + prior MergeRun in past → new MergeRun; `coverage_warning` lists sensor-b |
| `test_manual_merge_regression` | AUTOMERGE-03 | `merge_scan()` Option-A union: endpoint_count≥2, sensor_count=2, no coverage_warning (both current), scanned_at not rewritten for either sensor |

## Verification Results

- `python -m pytest tests/test_auto_merge_trigger.py -q` — 7 passed, 0 failures
- `python -m pytest tests/ -k "sensor_ingest or sensor_merge or sensor_push" -q` — 16 passed, 0 failures
- `python -m compileall tests/test_auto_merge_trigger.py` — clean

## Deviations from Plan

**[Auto-fix - Minor] 7 tests instead of 6**

The plan specified 6 acceptance tests matching the 6 CONTEXT `<specifics>`. The `test_revoked_sensor_excluded` (D-04) was added as a separate test from `test_all_sensors_in_triggers_merge` for clarity: it validates that a sensor with a revoked token does not block the all-in trigger. This aligns with the plan's Task 1 `<behavior>` which listed the revoked-sensor case as a required behavior alongside the main acceptance tests.

**[Auto-fix - Bug] CryptoEndpoint title field does not exist**

The initial draft passed `title="TLS"` to `CryptoEndpoint(...)` in `test_manual_merge_regression`. This field does not exist in the model — removed after the first test run failure.

## Known Stubs

None.

## Threat Flags

No new threat surface introduced. Test-only file with no production code changes.

## Self-Check: PASSED

- tests/test_auto_merge_trigger.py: created, committed at b07d210
- All 7 acceptance tests green (verified via pytest output above)
- 16 pre-existing sensor tests remain green (no regressions)
