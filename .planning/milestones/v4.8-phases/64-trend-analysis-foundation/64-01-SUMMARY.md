---
phase: 64
plan: "01"
subsystem: dashboard-api
tags: [backend, trends, timeline, pydantic, fastapi, tdd]
dependency_graph:
  requires: []
  provides: [GET /api/trends/timeline, TrendTimelineResponse schema]
  affects: [quirk/dashboard/api/routes/trends.py, quirk/dashboard/api/schemas.py]
tech_stack:
  added: []
  patterns: [per-session scoring loop, parameterized LIMIT variant, router-level auth inheritance]
key_files:
  created: []
  modified:
    - tests/test_dashboard_trends.py
    - quirk/dashboard/api/schemas.py
    - quirk/dashboard/api/routes/trends.py
decisions:
  - "Reuse SubScores model from schemas.py (no duplication) per D-06"
  - "Named shared-cache UUID isolation pattern for seeded-DB tests (mirrors UAT-31)"
  - "_list_session_timestamps() left completely untouched; new _list_session_timestamps_n() is a separate parameterized variant"
  - "Auth inherited from router-level dependency — no per-route annotation (RESEARCH.md Pitfall 5)"
  - "Do not call compute_trend_report() in loop — only build_evidence_summary + compute_readiness_score per RESEARCH.md anti-pattern guidance"
metrics:
  duration: "~8 minutes"
  completed: "2026-05-10"
  tasks: 3
  files: 3
---

# Phase 64 Plan 01: Timeline Backend Endpoint Summary

**One-liner:** New `GET /api/trends/timeline?n=30` FastAPI route returning up to N sessions (newest-first) each with overall score, all 6 subscores, and severity-bucketed finding counts via per-session `build_evidence_summary` + `compute_readiness_score` loop.

---

## What Was Built

### Task 1: Wave 0 failing tests

Added a `# ---- Wave 0: GET /api/trends/timeline (TREND-01) ----` section to `tests/test_dashboard_trends.py` with 5 new test functions:

- `test_trends_timeline_endpoint` — 200 with sessions array on empty DB
- `test_trends_timeline_schema` — full schema shape assertion (session_ts, score, subscores 6 keys, finding_counts 3 keys; INFO excluded)
- `test_trends_timeline_n_param` — ?n=5 returns at most 5 sessions
- `test_trends_timeline_n_validation` — ?n=1 and ?n=201 return 422
- `test_trends_timeline_empty` — empty DB returns `{"sessions": []}`

Helper `_make_trend64_client_and_session()` uses the named shared-cache UUID isolation pattern. All 5 tests were RED before Task 3.

### Task 2: Pydantic schemas

Appended to `quirk/dashboard/api/schemas.py` after `TrendReportResponse`:

- `FindingCounts` — high/medium/low int counts mirroring `_count_by_bucket` output
- `TrendSessionPoint` — session_ts (ISO str), score (int), subscores (SubScores reused), finding_counts (FindingCounts)
- `TrendTimelineResponse` — sessions: List[TrendSessionPoint] = []

`SubScores` is reused (not duplicated). No new imports needed.

### Task 3: Route implementation

Modified `quirk/dashboard/api/routes/trends.py`:

- Extended `from fastapi import` to include `Query`
- Extended schemas import to include `FindingCounts`, `TrendSessionPoint`, `TrendTimelineResponse`
- Added imports for `build_evidence_summary`, `compute_readiness_score`, `_fetch_session_endpoints`, `_count_by_bucket`
- Added `_list_session_timestamps_n(db, n)` — parameterized-LIMIT variant; original `_list_session_timestamps()` (LIMIT 10) unchanged
- Added `get_trends_timeline` route: `@router.get("/trends/timeline", response_model=TrendTimelineResponse)` with `n: int = Query(default=30, ge=2, le=200)`

All 5 Wave 0 tests transitioned RED→GREEN.

---

## Verification Results

```
python -m pytest tests/test_dashboard_trends.py -x -q   →  8 passed
python -m pytest tests/test_api_auth.py -x -q           → 16 passed
python -m compileall quirk/dashboard/api/ -q            → exit 0
```

---

## Deviations from Plan

None - plan executed exactly as written.

---

## Commits

| Task | Commit | Message |
|------|--------|---------|
| 1 | 287d34d | test(64-01): add Wave 0 failing tests for /api/trends/timeline (TREND-01) |
| 2 | 3fc6b48 | feat(64-01): add timeline schemas (FindingCounts, TrendSessionPoint, TrendTimelineResponse) |
| 3 | aa36937 | feat(64-01): add GET /api/trends/timeline (TREND-01) |

---

## Threat Surface Scan

No new network endpoints beyond `/api/trends/timeline` (already in the plan threat model).
T-64-01 (DoS via n param): mitigated by `Query(ge=2, le=200)` — verified by `test_trends_timeline_n_validation`.
T-64-02 (auth bypass): mitigated — route on `router = APIRouter(dependencies=[Depends(require_auth)])`.

## Known Stubs

None.

## Self-Check: PASSED

- tests/test_dashboard_trends.py: FOUND
- quirk/dashboard/api/schemas.py: FOUND (class TrendTimelineResponse present)
- quirk/dashboard/api/routes/trends.py: FOUND (@router.get("/trends/timeline") present)
- Commits 287d34d, 3fc6b48, aa36937: FOUND in git log
