---
phase: 31-trend-analysis
plan: "02"
subsystem: intelligence, api
tags: [intelligence, fastapi, sqlalchemy, pydantic, trends, dar, tdd]

requires:
  - phase: 31-01
    provides: "Wave 0 RED scaffold — stub trends.py + 12 failing tests"
  - phase: 30
    provides: "compute_readiness_score() returning int score via int(...) cast"

provides:
  - "compute_trend_report() pure function returning TrendReport dataclass"
  - "TrendReportResponse + SampleFinding Pydantic models in schemas.py"
  - "GET /api/trends FastAPI endpoint (0/1/2+ session handling)"
  - "All 12 Wave 0 RED tests now GREEN"

affects: [31-03, 31-04]

tech-stack:
  added: []
  patterns:
    - "D-04 compound exclusion: hosts with scan_error in current session excluded from previous_keys to prevent phantom resolved entries"
    - "D-12 pure function pattern: caller supplies both timestamps, no datetime.now() inside"
    - "strftime second-truncated session grouping reused verbatim from scan.py:457"
    - "±1 second window endpoint fetch reused verbatim from scan.py:497-507"

key-files:
  created:
    - quirk/intelligence/trends.py
    - quirk/dashboard/api/routes/trends.py
  modified:
    - quirk/dashboard/api/schemas.py
    - quirk/dashboard/api/app.py

key-decisions:
  - "D-04 compound exclusion: if (host, port, protocol) has a scan_error in the current session, remove matching previous_keys entries so phantom resolved findings are not generated for temporarily unreachable hosts"
  - "Severity bucket INFO intentionally excluded from _SEVERITY_BUCKET so INFO keys are never added to new_keys/resolved_keys or sample arrays (D-05)"
  - "score_delta computed as Optional[int] — None when either session has no endpoints (score_for_session returns None); int when both sessions have endpoints"

patterns-established:
  - "TDD GREEN pattern: stub→RED in Plan 01, full implementation→GREEN in Plan 02 (two-plan TDD wave)"
  - "_to_response() converter pattern: separates dataclass business logic from Pydantic serialization concerns"

requirements-completed: [TREND-01, TREND-02, TREND-03, TREND-04]

duration: 4min
completed: 2026-04-26
---

# Phase 31 Plan 02: Trend Analysis GREEN Implementation Summary

**compute_trend_report() pure function + GET /api/trends FastAPI route turning all 12 Wave 0 RED tests GREEN — severity-bucketed finding delta, scan-error isolation, and D-06 null-delta single-session path**

## Performance

- **Duration:** 4 min 7s
- **Started:** 2026-04-26T22:50:11Z
- **Completed:** 2026-04-26T22:54:18Z
- **Tasks:** 2
- **Files modified:** 4 (2 created, 2 modified)

## Accomplishments

- Implemented `compute_trend_report()` pure function (281 lines) covering all 10 unit test cases including D-04 scan_error exclusion, D-06 single-session null-delta, D-13 NULL scanned_at filter, and D-08 5-sample cap
- Appended `SampleFinding` + `TrendReportResponse` (15 fields) Pydantic models to `schemas.py` following existing style
- Created `routes/trends.py` handling 0/1/2+ session cases with the verbatim strftime grouping pattern from scan.py:457
- Registered trends router in `app.py` — import on line 19, `include_router` after scan router
- All 12 Wave 0 tests pass GREEN: 10 unit tests (`test_intelligence_trends.py`) + 2 integration tests (`test_dashboard_trends.py`)

## Test Results

| Test File | Count | Status |
|-----------|-------|--------|
| tests/test_intelligence_trends.py | 10 | ALL PASS GREEN |
| tests/test_dashboard_trends.py | 2 | ALL PASS GREEN |
| **Wave 0 Total** | **12** | **ALL PASS GREEN** |
| Full pytest suite (excl. 3 pre-existing failures) | 490 | PASS |

Pre-existing failures (unrelated to this plan):
- `test_cli_correctness.py::test_version_consistency` — expects `4.2.0`, codebase has `4.3.0`
- `test_v41_gap_closure.py::TestV41GapClosure::test_package_manifest_version_is_4_1_0`
- `test_v41_gap_closure.py::TestV41GapClosure::test_pyproject_version_field_is_4_1_0`
- `test_identity_surface.py::Issue3ScanWindowRegressionTest::test_issue3_scan_window_returns_all_identity_protocols`

## Severity Bucket Map (Confirmed)

| Input | Bucket | Notes |
|-------|--------|-------|
| CRITICAL | high | Maps to high bucket |
| HIGH | high | Maps to high bucket |
| MEDIUM | medium | Maps to medium bucket |
| LOW | low | Maps to low bucket |
| INFO | EXCLUDED | Intentionally absent from `_SEVERITY_BUCKET` — not counted, not sampled |

## Score Type Confirmation

`compute_readiness_score()` returns `{"score": total_score, ...}` where `total_score = int(...)` — confirmed `Optional[int]` in `TrendReport.score_delta` is correct. `_score_for_session()` returns `score_dict["score"]` directly.

## Task Commits

1. **Task 1: Implement compute_trend_report()** - `51aecfe` (feat)
2. **Task 2: Schemas + route + app registration** - `5c24f17` (feat)

## Files Created/Modified

- `quirk/intelligence/trends.py` — Full implementation replacing stub (281 lines): `compute_trend_report()` pure function, `TrendReport` + `SampleFindingItem` dataclasses, `_SEVERITY_BUCKET` + `_SEVERITY_RANK` constants, private helpers `_fetch_session_endpoints`, `_bucket_for_severity`, `_count_by_bucket`, `_sample_findings`, `_score_for_session`
- `quirk/dashboard/api/routes/trends.py` — New file (117 lines): `GET /api/trends` with `_list_session_timestamps` helper, `_to_response` converter, handles 0/1/2+ session paths
- `quirk/dashboard/api/schemas.py` — Appended `SampleFinding` + `TrendReportResponse` (28 lines added) after existing `ScanSession`
- `quirk/dashboard/api/app.py` — Added `trends` to import on line 19, added `include_router(trends.router)` after scan router

## Decisions Made

- **D-04 compound exclusion** (deviation from plan): The plan description said to exclude `scan_error` rows from finding-key sets. However, this alone caused phantom "resolved" entries when a host had a clean finding in the previous session but a scan_error in the current session. Fix: also exclude from `previous_keys` any endpoint whose `(host, port, protocol)` matches a scan_error in `current_eps`. This correctly models "we cannot determine if this finding is resolved because we couldn't reach the host."
- **Score Optional handling**: `current_score` is `None` when a session has 0 endpoints (guard: `if current_eps`). `score_delta` is `None` when either score is `None`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] D-04 scan_error exclusion required compound previous_keys filter**

- **Found during:** Task 1 (first test run — `test_scan_error_excluded_from_delta` FAIL)
- **Issue:** Excluding scan_error rows from `current_keys` alone caused PREV's clean endpoint to appear in `resolved_keys` when the corresponding current-session entry was a scan_error. Test asserted `resolved_high == 0` but got 1.
- **Fix:** Added `current_error_hosts = {(ep.host, ep.port, ep.protocol) for ep in current_eps if ep.scan_error is not None}` and filtered `previous_keys` to exclude any endpoints whose (host, port, protocol) appears in `current_error_hosts`.
- **Files modified:** `quirk/intelligence/trends.py`
- **Verification:** `test_scan_error_excluded_from_delta` passes; all other 9 unit tests still pass
- **Committed in:** `51aecfe` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 bug)
**Impact on plan:** Required for D-04 correctness — phantom resolved entries would be misleading in the dashboard. Fix adds 5 lines. No scope creep.

## Issues Encountered

None beyond the D-04 fix above.

## Known Stubs

None. All fields in `TrendReportResponse` are wired to `compute_trend_report()` output. No placeholder values.

## Threat Surface Scan

All mitigations from the plan's threat model are inherent to the implementation:

- T-31-02-01 (SQL injection): All queries use SQLAlchemy ORM parameter binding; no string interpolation
- T-31-02-03 (DoS unbounded query): `LIMIT 10` in session list query; ±1 second window for per-session endpoint fetch; sample arrays capped at 5
- T-31-02-04 (scan_error stack traces): `scan_error` rows excluded from samples (D-04); only counts exposed in response

No new threat surface introduced beyond what is documented in the plan.

## Next Phase Readiness

Wave 1 complete. `GET /api/trends` returns a working JSON response matching the documented schema for all session-count scenarios (0/1/2+). Wave 2 (Plan 03) can now fetch from this endpoint to build the React Trends tab component.

---
*Phase: 31-trend-analysis*
*Completed: 2026-04-26*
