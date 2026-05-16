---
phase: 65
plan: 03
subsystem: dashboard-initiated-scan
tags: [fastapi, pydantic, subprocess, test, api]
dependency_graph:
  requires:
    - quirk.models.ScanJob
    - quirk.dashboard.api.middleware.auth (require_auth)
    - quirk.dashboard.api.middleware.csrf (require_csrf)
    - quirk.dashboard.api.deps (get_db, _default_db_path)
  provides:
    - quirk.dashboard.api.schemas.ScanSubmitRequest
    - quirk.dashboard.api.schemas.JobStatusResponse
    - quirk.dashboard.api.routes.jobs.read_router
    - quirk.dashboard.api.routes.jobs.write_router
    - quirk.dashboard.api.routes.jobs._stage_index
    - tests/test_jobs_api.py (10 real bodies, 1 skip stub)
  affects:
    - quirk/dashboard/api/schemas.py
    - quirk/dashboard/api/routes/jobs.py
    - quirk/dashboard/api/app.py
    - tests/test_jobs_api.py
tech_stack:
  added: []
  patterns:
    - "Split read/write APIRouter with router-level auth+csrf Depends (Phase 63 pattern)"
    - "subprocess.Popen non-blocking dispatch (no communicate/wait)"
    - "Pydantic field_validator with @classmethod for @file rejection"
    - "Backend-computed stage_index (0..7) from current_stage string"
    - "SIGTERM cancellation with ProcessLookupError race handling (optimistic cancel)"
key_files:
  created:
    - quirk/dashboard/api/routes/jobs.py
  modified:
    - quirk/dashboard/api/schemas.py
    - quirk/dashboard/api/app.py
    - tests/test_jobs_api.py
decisions:
  - "Split read_router/write_router: GET uses read_router (auth only); POST/DELETE use write_router (auth+csrf)"
  - "stage_index computed backend-side in _stage_index() — single source of truth for progress bar"
  - "Popen with stdout/stderr=DEVNULL; never communicate or wait (non-blocking requirement)"
  - "Optimistic cancel: os.kill raises ProcessLookupError if process gone; caught silently"
  - "output_dir=output/jobs/{uuid}/ — server-generated UUID, never user-supplied (T-65-03-05 mitigation)"
  - "Rule 2: registered jobs.read_router + jobs.write_router in app.py immediately (Plan 04 adds lifespan)"
metrics:
  duration: "~5 minutes"
  completed: "2026-05-13"
  tasks_completed: 3
  files_changed: 4
---

# Phase 65 Plan 03: Dashboard-Initiated Scan — HTTP Surface Summary

One-liner: `/api/jobs` HTTP surface with Pydantic schemas, split read/write routers, non-blocking Popen dispatch, SIGTERM cancellation, and 10 real test bodies (1 stub deferred to Plan 04).

## What Was Built

### Task 1: ScanSubmitRequest + JobStatusResponse schemas

Added to `quirk/dashboard/api/schemas.py` (verbatim from CONTEXT.md D-05):

- **`ScanSubmitRequest`**: targets (min_length=1/max_length=1024), profile/calibration Literals, enable_nmap bool. `no_file_paths` validator rejects empty strings and @-prefixed targets (422).
- **`JobStatusResponse`**: job_id, status, current_stage, started_at, completed_at, scan_run_id, error_message, stage_index (0..7, backend-computed), stage_total=7.
- Imports extended: `Literal` from typing, `Field` and `field_validator` from pydantic.

### Task 2: /api/jobs router (quirk/dashboard/api/routes/jobs.py)

Created `jobs.py` with split router pattern (Phase 63 precedent):

| Router | Auth | Endpoints |
|--------|------|-----------|
| `read_router` | require_auth only | GET /api/jobs/{job_id} |
| `write_router` | require_auth + require_csrf | POST /api/jobs, DELETE /api/jobs/{job_id} |

**POST /api/jobs**: generates job_id UUID, inserts ScanJob row, creates output/jobs/{uuid}/ dir, spawns `run_scan.py` via `subprocess.Popen` (non-blocking), writes pid to row, returns 201 `{"job_id": ..., "status": "running"}`.

**GET /api/jobs/{job_id}**: looks up row; returns `JobStatusResponse` with computed stage_index; 404 for unknown ids.

**DELETE /api/jobs/{job_id}**: os.kill(pid, SIGTERM), ProcessLookupError caught silently (race), flips status to "cancelled", sets completed_at; returns 204.

**`_stage_index(current_stage, status)` mapping:**
- None + queued → 0
- discovery → 1, tls → 2, ssh → 3, api → 4, identity → 5, data_at_rest → 6, reports → 7
- status="completed" → 7 (regardless of stage)
- unknown stage → 0

**Security mitigations applied (threat_model):**
- T-65-03-01: `subprocess.Popen` called with list argv (no `shell=True`) — shell metacharacters in targets not interpreted
- T-65-03-02: `no_file_paths` validator rejects @-prefix (422 before subprocess dispatch)
- T-65-03-03/04: router-level `Depends(require_csrf)` and `Depends(require_auth)` on write_router
- T-65-03-05: output_dir derived from server-generated UUID only

### Task 3: Replace test stubs in test_jobs_api.py

Replaced 10 of 11 pytest.skip stubs with real test bodies. `test_stale_job_recovery` stays stubbed for Plan 04 (lifespan).

| Test | What It Verifies |
|------|-----------------|
| test_post_job_creates_row | 201 + DB row created + status=running |
| test_post_job_rejects_file_path | 422 for @/tmp/x.txt target |
| test_post_job_empty_targets | 422 for empty targets string |
| test_post_job_requires_auth | 401 when QUIRK_API_TOKEN set, no auth header |
| test_post_job_requires_csrf | 403 when X-Quirk-Request header absent |
| test_get_job_status | 200 with stage_index=2 for current_stage="tls" |
| test_get_job_not_found | 404 with "Job not found" for unknown id |
| test_get_job_requires_auth | 401 without auth; 404 (not 403) with auth but no CSRF |
| test_stage_index_computation | Direct unit test of all 7 stage mappings |
| test_cancel_job | 204 + status=cancelled + os.kill called |

Subprocess.Popen mocked via `monkeypatch.setattr("...jobs.subprocess.Popen", _fake_popen)`. os.kill mocked in cancel test to avoid real signals.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Worktree branch was 14 commits behind main**
- **Found during:** Pre-execution setup (prerequisites check)
- **Issue:** The worktree branch was created from Phase 57 commit (65e0463) and was missing Phase 65 Plan 01 (ScanJob model, test stubs), Phase 58 (auth/CSRF middleware), Phase 63 (schedules router), and all related code. Without these, jobs.py imports would fail.
- **Fix:** Merged `main` into the worktree branch (fast-forward, no conflicts). All 227 files from main (Phases 57-65 Plan 01) merged cleanly.
- **Commit:** merged upstream in fast-forward

**2. [Rule 2 - Missing Critical] Registered jobs routers in app.py**
- **Found during:** Task 3 (test file implementation)
- **Issue:** `tests/test_jobs_api.py` tests POST/GET/DELETE `/api/jobs` via `create_app()`. Without jobs.read_router + jobs.write_router registered in app.py, all 10 route tests would return 404 or be routed to the SPA catch-all.
- **Fix:** Added `from quirk.dashboard.api.routes import jobs` import and two `include_router` calls to `app.py`. Plan 04 is responsible for the more complex lifespan addition; the router registration is immediate correctness.
- **Files modified:** quirk/dashboard/api/app.py
- **Commit:** cf74742

### Pre-existing Issues (Out of Scope)

The `tests/test_schedules_api.py` tests that use `dashboard_client` for POST/DELETE fail because the `conftest.py` fixture creates a `TestClient` without the `X-Quirk-Request: 1` header required by `require_csrf`. These failures were present before this plan ran (confirmed by reverting changes and re-running). They are logged as deferred items — fixing would require modifying conftest.py which is outside Plan 03's scope.

## Known Stubs

| File | Stub | Reason |
|------|------|--------|
| tests/test_jobs_api.py | test_stale_job_recovery | Intentional; Plan 04 implements lifespan + _recover_stale_jobs |

## Threat Surface Scan

New network endpoints introduced:

| Flag | File | Description |
|------|------|-------------|
| threat_flag: new_mutating_endpoint | quirk/dashboard/api/routes/jobs.py | POST /api/jobs — guarded by require_auth + require_csrf + Pydantic validation |
| threat_flag: new_mutating_endpoint | quirk/dashboard/api/routes/jobs.py | DELETE /api/jobs/{job_id} — guarded by require_auth + require_csrf |
| threat_flag: subprocess_dispatch | quirk/dashboard/api/routes/jobs.py | Popen with list argv (no shell=True); db_path is server-resolved |

All three surfaces have mitigations applied per the plan's threat_model register (T-65-03-01 through T-65-03-07).

## Self-Check: PASSED

- quirk/dashboard/api/schemas.py: ScanSubmitRequest class ✓, JobStatusResponse class ✓, no_file_paths validator ✓
- quirk/dashboard/api/routes/jobs.py: file exists ✓, read_router + write_router ✓, Popen non-blocking ✓, SIGTERM + ProcessLookupError ✓
- quirk/dashboard/api/app.py: jobs.read_router + jobs.write_router registered ✓
- tests/test_jobs_api.py: 10 passed, 1 skipped (stale_job_recovery) ✓
- test_api_auth.py: 16 passed, 0 failed ✓
- test_dashboard_api.py: passes ✓
- Commits: 218fd28, 56a3d2f, cf74742 all present in git log ✓
