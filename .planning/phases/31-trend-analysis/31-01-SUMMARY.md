---
phase: 31-trend-analysis
plan: "01"
subsystem: intelligence-tests
tags: [tdd, red-scaffold, trend-analysis, testing]
dependency_graph:
  requires: []
  provides:
    - tests/test_intelligence_trends.py
    - tests/test_dashboard_trends.py
    - quirk/intelligence/trends.py (stub)
  affects:
    - quirk/intelligence/trends.py (Wave 1 implementation target)
    - quirk/dashboard/api/routes/trends.py (Wave 1 integration target)
tech_stack:
  added: []
  patterns:
    - pytest fixtures with in-memory SQLite (module-local db fixture)
    - dashboard_client fixture from conftest.py for integration tests
    - CryptoEndpoint direct construction with scanned_at timestamps
key_files:
  created:
    - tests/test_intelligence_trends.py (228 lines)
    - tests/test_dashboard_trends.py (51 lines)
    - quirk/intelligence/trends.py (59 lines — stub only)
  modified: []
decisions:
  - "Stub module required for test collection: quirk/intelligence/trends.py raises NotImplementedError so tests collect (RED) but fail when run (as designed)"
  - "Stub module exports SampleFindingItem and TrendReport dataclasses so Wave 1 can import and implement without modifying test files"
metrics:
  duration: "~8 min"
  completed: "2026-04-26"
  tasks_completed: 2
  files_created: 3
---

# Phase 31 Plan 01: Wave 0 RED Test Scaffold Summary

RED test scaffold for compute_trend_report() and GET /api/trends — 12 failing tests locking in TREND-01/02/03/04 and D-03/D-04/D-05/D-13 contract before Wave 1 implementation.

## Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `tests/test_intelligence_trends.py` | 228 | 10 unit tests for `compute_trend_report()` covering TREND-01/02/03, D-03/D-04/D-05/D-13 |
| `tests/test_dashboard_trends.py` | 51 | 2 integration tests for `GET /api/trends` using `dashboard_client` fixture |
| `quirk/intelligence/trends.py` | 59 | Stub module with `NotImplementedError` so tests can be collected |

## Test Collection

```
pytest tests/test_intelligence_trends.py tests/test_dashboard_trends.py --collect-only
12 tests collected in 0.08s
```

All 12 tests: 10 unit tests + 2 integration tests collected successfully.

## RED State Confirmation

All 12 new tests fail as expected:

- **Unit tests** (`test_intelligence_trends.py`): Fail with `NotImplementedError: compute_trend_report() is not yet implemented` — stub module allows collection while preventing implementation leakage.
- **Integration tests** (`test_dashboard_trends.py`): Fail because `/api/trends` is not registered in the FastAPI app — returns SPA HTML (200 with HTML body, not JSON), causing test assertions to fail.

## No Existing Test Regressions

```
pytest tests/ --ignore=test_intelligence_trends.py --ignore=test_dashboard_trends.py
482 passed, 5 skipped, 4 pre-existing failures (version string checks from prior phases)
```

The 4 pre-existing failures (`test_version_consistency`, `test_no_quirk_scan_references`, `test_issue3_scan_window_returns_all_identity_protocols`, `test_pyproject_version_field_is_4_1_0`) exist on the base commit b6348bf and are not caused by Plan 01 changes.

## Decisions Made

1. **Stub module created (Rule 3 — blocking issue):** The plan specified test files only, but pytest cannot collect tests when the imported module does not exist. Creating `quirk/intelligence/trends.py` as a stub (raising `NotImplementedError`) allows collection while preserving the RED contract. The stub exports `SampleFindingItem`, `TrendReport`, and `compute_trend_report` so Wave 1 (Plan 02) has the correct signature to implement against.

2. **Stub exports full dataclass types:** `TrendReport` and `SampleFindingItem` are declared in the stub with all fields from PATTERNS.md — Wave 1 replaces the stub body without changing the type signatures.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Created quirk/intelligence/trends.py stub to enable test collection**
- **Found during:** Task 01
- **Issue:** `python -m pytest tests/test_intelligence_trends.py --collect-only` raised `ModuleNotFoundError: No module named 'quirk.intelligence.trends'` — tests could not be collected because the module didn't exist
- **Fix:** Created `quirk/intelligence/trends.py` stub with `NotImplementedError` in `compute_trend_report()`. The RESEARCH.md Wave 0 Gaps section also listed this stub as a Wave 0 deliverable, confirming the intent.
- **Files modified:** `quirk/intelligence/trends.py` (new file, 59 lines)
- **Commit:** d6a9788

## Commits

| Task | Commit | Files |
|------|--------|-------|
| Task 01: 10 RED unit tests + stub | d6a9788 | `tests/test_intelligence_trends.py`, `quirk/intelligence/trends.py` |
| Task 02: 2 RED integration tests | 46b4b25 | `tests/test_dashboard_trends.py` |

## Self-Check

- [x] `tests/test_intelligence_trends.py` exists (228 lines, 10 test functions)
- [x] `tests/test_dashboard_trends.py` exists (51 lines, 2 test functions)
- [x] `quirk/intelligence/trends.py` exists (59 lines, stub)
- [x] 12 tests collected
- [x] All 12 tests fail (RED state confirmed)
- [x] No new regressions in existing test suite
- [x] Commits d6a9788 and 46b4b25 exist

## Self-Check: PASSED
