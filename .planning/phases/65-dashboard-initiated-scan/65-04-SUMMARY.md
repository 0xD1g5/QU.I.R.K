---
phase: 65
plan: 04
subsystem: dashboard-initiated-scan
tags: [fastapi, lifespan, sqlalchemy, test, stale-jobs]
dependency_graph:
  requires:
    - quirk.models.ScanJob
    - quirk.dashboard.api.deps._default_db_path
    - quirk.dashboard.api.routes.jobs (read_router, write_router)
  provides:
    - quirk.dashboard.api.app.lifespan
    - quirk.dashboard.api.app._recover_stale_jobs
    - quirk.dashboard.api.app.create_app(db_path=None)
    - tests/test_jobs_api.py (11/11 passing, 0 stubs)
  affects:
    - quirk/dashboard/api/app.py
    - tests/test_jobs_api.py
tech_stack:
  added: []
  patterns:
    - "asynccontextmanager lifespan for FastAPI startup sweep"
    - "app.state.db_path set before include_router (Pitfall 4 ordering)"
    - "Best-effort try/except wrapping of startup DB work"
    - "create_app(db_path=None) backward-compatible optional parameter"
key_files:
  created: []
  modified:
    - quirk/dashboard/api/app.py
    - tests/test_jobs_api.py
decisions:
  - "lifespan calls _recover_stale_jobs synchronously in startup block (simple, correct for single-process API)"
  - "application.state.db_path set immediately after FastAPI() construction, before any include_router (ensures lifespan sees it)"
  - "_recover_stale_jobs uses lazy imports inside the function body (minimal import-time side effects)"
  - "test_stale_job_recovery calls _recover_stale_jobs directly rather than via TestClient lifespan (simpler, more direct, avoids lifespan complexity in tests)"
metrics:
  duration: "~10 minutes"
  completed: "2026-05-13"
  tasks_completed: 2
  files_changed: 2
---

# Phase 65 Plan 04: Dashboard-Initiated Scan — Lifespan + Stale Job Recovery Summary

One-liner: FastAPI asynccontextmanager lifespan that sweeps orphaned running scan_jobs rows to failed on startup, backward-compatible create_app(db_path=None) signature, and 11/11 test_jobs_api.py tests green.

## What Was Built

### Task 1: Add lifespan, modify create_app, mount jobs routers

Modified `quirk/dashboard/api/app.py` with three additions:

**Imports added:**
- `from contextlib import asynccontextmanager`
- `from datetime import datetime, timezone`
- `from quirk.dashboard.api.deps import _default_db_path`

**`_recover_stale_jobs(db_path: str) -> None`** (private module helper, above `create_app`):

Opens a SQLAlchemy session at `db_path`, queries all `ScanJob` rows with `status == "running"`, sets each to `status="failed"`, `error_message="API restarted — job lost"`, `completed_at=utcnow_naive()`, commits. Wrapped entirely in `try/except Exception: pass` so a missing `scan_jobs` table on first-ever boot (before `init_db` has run) does not crash API startup (T-65-04-01 mitigation).

**`lifespan(application: FastAPI)` asynccontextmanager:**

Reads `application.state.db_path`, calls `_recover_stale_jobs(db_path)`, then yields. No teardown logic needed.

**`create_app` signature change:**

```python
def create_app(db_path: str | None = None) -> FastAPI:
    if db_path is None:
        db_path = _default_db_path()
    application = FastAPI(..., lifespan=lifespan)
    application.state.db_path = db_path  # Must precede include_router
    ...
```

The `db_path: str | None = None` default preserves full backward compatibility — all existing callers (`tests/conftest.py`, `tests/test_schedules_api.py`, `tests/test_qramm_evidence_bridge.py`) continue to call `create_app()` with no arguments.

The jobs routers (`jobs.read_router`, `jobs.write_router`) were already registered in app.py as part of Plan 03's Rule 2 deviation — no duplication needed.

**Verification passed:**
- `python -c "from quirk.dashboard.api.app import create_app, lifespan, _recover_stale_jobs; a = create_app(); print('ok')"` exits 0
- `/api/jobs` and `/api/jobs/{job_id}` confirmed in app routes
- `tests/test_jobs_api.py`: 10 passed, 1 skipped (stale_job_recovery still a stub)

### Task 2: Fill in test_stale_job_recovery

Replaced the `pytest.skip("Implemented in Plan 04...")` stub in `tests/test_jobs_api.py` with a real body that:

1. Creates a fresh SQLite DB at `tmp_path/test.db` using `Base.metadata.create_all`
2. Seeds two rows: `stale-1` (status=running) and `done-1` (status=completed)
3. Calls `_recover_stale_jobs(db_file)` directly (not via lifespan/TestClient)
4. Asserts: `stale-1.status == "failed"`, `stale-1.error_message == "API restarted — job lost"`, `stale-1.completed_at is not None`
5. Asserts: `done-1.status == "completed"` (untouched), `done-1.error_message is None` (untouched)

**All 11 tests pass — zero pytest.skip stubs remaining.**

Route auth introspection (`test_api_auth.py::test_all_mutating_routes_have_auth_dependency`) also passes — the dynamic route enumeration correctly picks up POST and DELETE /api/jobs as protected.

## Deviations from Plan

### Note: Jobs Routers Already Registered

Plan 04 Task 1 included instructions to add `jobs_routes.read_router` and `jobs_routes.write_router` to `app.py`. These were already added in Plan 03 (as Rule 2 — Missing Critical deviation) because the test suite required them. No duplication was added. The acceptance criteria check for `jobs_routes.read_router` uses the alias `jobs_routes` but the actual import uses `from ... import jobs` (registered as `jobs.read_router`). Functionally equivalent; both routers are mounted.

### Note: Worktree Required Merge from main

This worktree was created from Phase 57 commit and did not have Plans 01–03 changes. A `git merge main --no-edit` was performed before Task 1 to bring in 227 files from Phases 57–65 Plan 03 (same approach as Plan 03 used). This is standard worktree initialization, not a deviation.

### Pre-existing Test Failures (Out of Scope)

The following failures existed in main before Plan 04 and are unrelated:
- `tests/test_broker_scanner_rabbitmq.py::test_enrich_rabbitmq_mgmt_success` — KeyError on `rabbitmq_version` key
- `tests/test_schedules_api.py` CSRF-missing failures (conftest.py missing X-Quirk-Request header)
- `tests/test_skip_registry.py::test_no_unregistered_skips` — two unregistered skipif markers from other phases
- `tests/test_scoring_correctness.py` and `tests/test_v41_gap_closure.py` version-related failures

All logged to deferred-items per scope boundary rule.

## Threat Surface Scan

No new network endpoints introduced. `_recover_stale_jobs` runs at startup, writes only fixed constant strings (T-65-04-02 mitigation: no user input flows in). `app.state.db_path` is in-memory only (T-65-04-03: accepted).

## Self-Check: PASSED

- `quirk/dashboard/api/app.py`: `def lifespan` ✓, `@asynccontextmanager` ✓, `def _recover_stale_jobs` ✓, `def create_app(db_path` ✓, `lifespan=lifespan` ✓, `application.state.db_path` ✓
- `tests/test_jobs_api.py`: `grep -c 'pytest.skip'` = 0 ✓, 11 passed ✓
- `tests/test_api_auth.py`: 16 passed ✓
- Commits: e178be2, 173ad07 present in git log ✓
