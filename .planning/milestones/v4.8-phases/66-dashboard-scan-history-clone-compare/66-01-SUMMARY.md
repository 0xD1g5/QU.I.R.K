---
phase: 66
plan: 01
subsystem: dashboard-api-tests
tags: [tdd, wave-0, scan-history, compare, pytest]
dependency_graph:
  requires: []
  provides: [tests/test_dashboard_scan_history.py]
  affects: []
tech_stack:
  added: []
  patterns: [shared-cache-sqlite-fixture, named-uuid-db-per-test]
key_files:
  created:
    - tests/test_dashboard_scan_history.py
  modified: []
decisions:
  - "Used scanned_at-based grouping (not scan_run_id column) in _seed_session helper — CryptoEndpoint has no scan_run_id column; sessions are identified by scanned_at timestamp; ScanJob join uses ScanJob.scan_run_id = scanned_at.isoformat()"
metrics:
  duration: "5 minutes"
  completed: "2026-05-14"
  tasks_completed: 1
  files_changed: 1
---

# Phase 66 Plan 01: Wave 0 Test Scaffold Summary

**One-liner:** 9 RED pytest tests for `/api/scans` enriched schema and `/api/compare` endpoint using named shared-cache SQLite fixtures.

## What Was Built

### Task 1: Create failing test scaffold tests/test_dashboard_scan_history.py

Created `tests/test_dashboard_scan_history.py` with 9 RED integration tests covering all VALIDATION.md §Per-Task Verification Map rows for UI-HIST-01 and UI-HIST-02:

**UI-HIST-01 tests (scan list + clone):**
- `test_list_scans_schema` — asserts `/api/scans` returns `score, profile, calibration, target, finding_counts` keys (fails: Plan 02 adds these)
- `test_list_scans_no_limit` — seeds 12 sessions, asserts `len == 12` (fails: LIMIT 10 still active)
- `test_clone_data_recovery` — seeds matching ScanJob, asserts target/profile/calibration recovered (fails: ScanJob join not yet in list_scans)
- `test_clone_reconstruction` — no ScanJob seeded, asserts host reconstruction into target (fails: reconstruction not yet in list_scans)

**UI-HIST-02 tests (compare endpoint):**
- `test_compare_schema` — asserts `/api/compare` returns 200 with 9-key schema + 6 subscore pillars (fails: endpoint not yet registered)
- `test_compare_self` — asserts `a == b` returns 400 + "Cannot compare a scan to itself." (fails: route doesn't exist, returns HTML catch-all 200)
- `test_compare_score_delta` — asserts `score_delta > 0` for good vs weak TLS (fails: endpoint missing)
- `test_compare_finding_diff` — asserts added_findings/removed_findings non-empty (fails: endpoint missing)
- `test_compare_endpoint_diff` — asserts endpoints_only_in_a, endpoints_only_in_b, changed_endpoints (fails: endpoint missing)

**Fixture pattern:** `_make_client_and_session()` uses named shared-cache UUID SQLite URI (`sqlite:///file:{uuid}?mode=memory&cache=shared&uri=true`) with `app.dependency_overrides[get_db]`. Same pattern as `tests/test_dashboard_trends.py`.

**Seeding helper:** `_seed_session(TestingSession, scanned_at, endpoints)` creates `CryptoEndpoint` rows with the given timestamp. ScanJob seeding is done inline in tests that need it, using `ScanJob.scan_run_id = scanned_at.isoformat()` to enable the `startswith(ts_str[:19])` join.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed invalid `scan_run_id` kwarg from `_seed_session` helper**
- **Found during:** Task 1 verification run
- **Issue:** Plan specification included `scan_run_id = scanned_at.isoformat()` in the `_seed_session` helper's `CryptoEndpoint()` constructor call, but `CryptoEndpoint` has no `scan_run_id` column (sessions are grouped by `scanned_at` timestamp; the `scan_run_id` lives on `ScanJob`, not `CryptoEndpoint`)
- **Fix:** Removed `scan_run_id` kwarg from `CryptoEndpoint()` constructor in `_seed_session`; added doc comment explaining the join mechanism
- **Files modified:** `tests/test_dashboard_scan_history.py`
- **Commit:** fcc9018

## Known Stubs

None — this is a test-only file. No production stubs introduced.

## Threat Flags

None — test file only; all DB access is in-process in-memory SQLite with UUID-namespaced DB names. No new network surfaces.

## Verification Results

- `python -m pytest tests/test_dashboard_scan_history.py --collect-only -q`: 9 tests collected, exit 0
- `python -m compileall tests/test_dashboard_scan_history.py`: exits 0
- `python -m pytest tests/test_dashboard_scan_history.py -q`: 9 failed (RED) — all failures are assertion errors or JSONDecodeError (HTML catch-all response for missing endpoint), not import/syntax/collection errors

## Self-Check: PASSED

- [x] `tests/test_dashboard_scan_history.py` exists
- [x] Commit fcc9018 exists
- [x] 9 tests collect cleanly
- [x] All 9 tests fail RED for the correct reason
