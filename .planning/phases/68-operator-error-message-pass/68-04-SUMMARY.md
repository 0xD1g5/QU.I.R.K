---
phase: 68
plan: "04"
subsystem: errors-dashboard
tags: [error-migration, dashboard, middleware, routes, tdd, operator-ux]
dependency_graph:
  requires: [quirk/errors.py, quirk/dashboard/api/middleware, quirk/dashboard/api/routes]
  provides: [migrated middleware/routes with QRK codes, DASHBOARD-001..012, SCHED-002..004, INSTALL-002/004]
  affects: [test_api_auth, test_jobs_api, test_qramm_router, test_schedules_api, test_qramm_multiplier]
tech_stack:
  added: []
  patterns: [format_error-call-site-migration, json-dumps-response-body, try-except-oserror]
key_files:
  created: []
  modified:
    - quirk/dashboard/api/middleware/auth.py
    - quirk/dashboard/api/middleware/csrf.py
    - quirk/dashboard/api/middleware/rate_limit.py
    - quirk/dashboard/server.py
    - quirk/dashboard/api/routes/scan.py
    - quirk/dashboard/api/routes/jobs.py
    - quirk/dashboard/api/routes/qramm.py
    - quirk/dashboard/api/routes/schedules.py
    - quirk/dashboard/api/routes/pdf.py
    - tests/test_api_auth.py
    - tests/test_jobs_api.py
    - tests/test_qramm_router.py
    - tests/test_schedules_api.py
    - tests/conftest.py
    - tests/test_qramm_multiplier.py
decisions:
  - "Rate-limit Response body uses json.dumps({detail: format_error(DASHBOARD-003)}).encode() — same json.dumps pattern as pdf.py"
  - "server.py catches OSError for port conflict before re-raising; only 'address already in use' gets INSTALL-004"
  - "QRAMM dict-detail eliminated: HTTPException detail is now a plain string from format_error(DASHBOARD-010)"
  - "conftest.py dashboard_client fixture fixed to include X-Quirk-Request: 1 header (pre-existing bug)"
  - "test_qramm_router.py _make_qramm_client() fixed to include X-Quirk-Request: 1 header (Rule 1 fix)"
metrics:
  duration: "~25 minutes"
  completed: "2026-05-14"
  tasks: 3
  files: 15
---

# Phase 68 Plan 04: Dashboard Error Migration Summary

**One-liner:** All dashboard middleware, route handlers, and server.py error surfaces migrated to `format_error()` QRK codes — 18 raise/return sites updated, QRAMM dict-detail eliminated, 5 test files updated and green.

## What Was Built

### Task 1: Middleware (auth, csrf, rate_limit) + server.py

Migrated four files to import and call `format_error()`.

**auth.py (DASHBOARD-001):**
- Both `raise HTTPException(401, "Authentication required")` calls replaced with `detail=format_error("DASHBOARD-001")`
- Import added: `from quirk.errors import format_error`

**csrf.py (DASHBOARD-002):**
- `raise HTTPException(403, f"Missing CSRF header: {CSRF_HEADER}")` replaced with `detail=format_error("DASHBOARD-002")`
- Docstring updated to remove legacy detail string reference
- Import added: `from quirk.errors import format_error`

**rate_limit.py (DASHBOARD-003):**
- `'{"detail":"Rate limit exceeded"}'` hardcoded string replaced with `json.dumps({"detail": format_error("DASHBOARD-003")}).encode()`
- `import json` added; `from quirk.errors import format_error` added
- Response structure (status_code=429, media_type, Retry-After header) preserved exactly

**server.py (INSTALL-002 + INSTALL-004):**
- `"ERROR: uvicorn not installed..."` replaced with `print(format_error("INSTALL-002"), file=sys.stderr)`
- `uvicorn.run(...)` wrapped in `try/except OSError` — emits `format_error("INSTALL-004")` when "address already in use" detected
- `from quirk.errors import format_error` added as top-level import

### Task 2: Route handlers (scan, jobs, qramm, schedules, pdf)

**scan.py (DASHBOARD-004..007) — 7 sites:**
- `f"Invalid scan_id format: {scan_id!r}"` (×2) → `DASHBOARD-004`
- `f"No scan found with scan_id={scan_id!r}"` → `DASHBOARD-005`
- `"No scan results found. ..."` → `DASHBOARD-006`
- `"No endpoints found for latest scan."` → `DASHBOARD-006`
- `"Cannot compare a scan to itself."` → `DASHBOARD-007`
- `"Invalid scan_id format."` → `DASHBOARD-004`
- `f"No scan found: {a!r}"` and `f"No scan found: {b!r}"` (×2) → `DASHBOARD-005`

**jobs.py (DASHBOARD-008) — 1 site:**
- `"Job not found"` → `format_error("DASHBOARD-008")`

**qramm.py (DASHBOARD-009..011) — 3 sites:**
- `"Session not found"` → `format_error("DASHBOARD-009")`
- Dict detail `{"error_code": "QRAMM_MULTIPLIER_OUT_OF_RANGE", "message": ..., "valid_range": [0.8, 1.5]}` → `format_error("DASHBOARD-010")` (plain string)
- `"Cannot score a session with no answered questions"` → `format_error("DASHBOARD-011")`
- Pydantic Field docstring updated: `QRAMM_MULTIPLIER_OUT_OF_RANGE` → `QRK-DASHBOARD-010`

**schedules.py (SCHED-002..004) — 3 sites:**
- `"Schedule not found"` → `format_error("SCHED-004")`
- `f"Invalid cron expression: {payload.cron_expr!r}"` → `format_error("SCHED-002")`
- `f"Schedule '{payload.name}' already exists"` → `format_error("SCHED-003")`

**pdf.py (DASHBOARD-012) — 1 site:**
- `"Playwright not installed. Run: pip install playwright && playwright install chromium"` → `format_error("DASHBOARD-012")` (within existing `json.dumps` Response shape)

### Task 3: API test updates

Updated 5 test files to assert QRK codes instead of legacy detail strings:

| File | Old assertion | New assertion |
|------|--------------|---------------|
| test_api_auth.py:136 | `== "Authentication required"` | `"QRK-DASHBOARD-001" in detail` |
| test_api_auth.py:197 | `== "Missing CSRF header: X-Quirk-Request"` | `"QRK-DASHBOARD-002" in detail` |
| test_jobs_api.py:198 | `"Job not found" in detail` | `"QRK-DASHBOARD-008" in detail` |
| test_qramm_router.py:105 | `== "Session not found"` | `"QRK-DASHBOARD-009" in detail` |
| test_schedules_api.py:113 | `"dup-test" in detail` | `"QRK-SCHED-003" in detail` |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] test_qramm_router.py: all QRAMM POST tests failing with 403**
- **Found during:** Task 3 verification
- **Issue:** `_make_qramm_client()` returned `TestClient(app)` without `X-Quirk-Request: 1` header. CSRF middleware (added in Phase 58) rejects all POST/PUT/DELETE/PATCH requests without that header. 25/30 tests were failing pre-wave-3.
- **Fix:** Changed to `TestClient(app, headers={"X-Quirk-Request": "1"})` in `_make_qramm_client()`
- **Files modified:** `tests/test_qramm_router.py`
- **Commit:** 9501181

**2. [Rule 1 - Bug] conftest.py: dashboard_client fixture missing CSRF header**
- **Found during:** Task 3 verification (test_schedules_api failures)
- **Issue:** `conftest.py` `dashboard_client` fixture returns `TestClient(app)` without the `X-Quirk-Request: 1` header despite the docstring claiming it does. Tests relying on this fixture for POST operations were failing.
- **Fix:** Changed to `TestClient(app, headers={"X-Quirk-Request": "1"})` in the fixture
- **Files modified:** `tests/conftest.py`
- **Commit:** 9501181

**3. [Rule 1 - Bug] test_qramm_multiplier.py: dict-detail assertions broken by Task 2**
- **Found during:** Full regression run after Task 3 commit
- **Issue:** Task 2 converted the QRAMM multiplier error from a dict-detail to a plain `format_error("DASHBOARD-010")` string. `tests/test_qramm_multiplier.py` was asserting `detail.get("error_code") == "QRAMM_MULTIPLIER_OUT_OF_RANGE"` — a dict access on the now-string detail.
- **Fix:** Updated assertion to `assert "QRK-DASHBOARD-010" in detail` (string substring check)
- **Files modified:** `tests/test_qramm_multiplier.py`
- **Commit:** dfd8d1e

## QRK Codes Emitted Per File

| File | Codes |
|------|-------|
| middleware/auth.py | DASHBOARD-001 |
| middleware/csrf.py | DASHBOARD-002 |
| middleware/rate_limit.py | DASHBOARD-003 |
| server.py | INSTALL-002, INSTALL-004 |
| routes/scan.py | DASHBOARD-004, DASHBOARD-005, DASHBOARD-006, DASHBOARD-007 |
| routes/jobs.py | DASHBOARD-008 |
| routes/qramm.py | DASHBOARD-009, DASHBOARD-010, DASHBOARD-011 |
| routes/schedules.py | SCHED-002, SCHED-003, SCHED-004 |
| routes/pdf.py | DASHBOARD-012 |

## QRAMM Dict-Detail Elimination Confirmation

The dict `{"error_code": "QRAMM_MULTIPLIER_OUT_OF_RANGE", "message": "...", "valid_range": [0.8, 1.5]}` has been fully replaced with `format_error("DASHBOARD-010")` which returns the plain string `[QRK-DASHBOARD-010] QRAMM profile_multiplier is out of range. Fix: profile_multiplier must be in [0.8, 1.5].`

Verification: `grep -v '^#' quirk/dashboard/api/routes/qramm.py | grep -c 'QRAMM_MULTIPLIER_OUT_OF_RANGE'` returns 0.

## Commits

| Task | Hash | Message |
|------|------|---------|
| Task 1 (middleware + server.py) | 82d4998 | feat(68-04): migrate middleware and server.py to format_error QRK codes |
| Task 2 (routes) | 86d3a55 | feat(68-04): migrate route handlers to format_error QRK codes |
| Task 3 (tests) | 9501181 | feat(68-04): update API tests to assert QRK error codes |
| Rule 1 fix (multiplier test) | dfd8d1e | fix(68-04): update test_qramm_multiplier for DASHBOARD-010 plain string detail |

## Known Stubs

None — all error migration sites are fully wired to format_error().

## Self-Check: PASSED

- [x] `grep -c 'from quirk.errors import format_error' quirk/dashboard/api/middleware/auth.py` → 1
- [x] `grep -c 'from quirk.errors import format_error' quirk/dashboard/api/middleware/csrf.py` → 1
- [x] `grep -c 'from quirk.errors import format_error' quirk/dashboard/api/middleware/rate_limit.py` → 1
- [x] `grep -c 'from quirk.errors import format_error' quirk/dashboard/server.py` → 1
- [x] `grep -c 'INSTALL-004' quirk/dashboard/server.py` → 1
- [x] `grep -c 'address already in use' quirk/dashboard/server.py` → 1
- [x] `grep -c 'DASHBOARD-010' quirk/dashboard/api/routes/qramm.py` → at least 1
- [x] `grep -v '^#' quirk/dashboard/api/routes/qramm.py | grep -c 'QRAMM_MULTIPLIER_OUT_OF_RANGE'` → 0
- [x] `python -m compileall quirk/dashboard` → success
- [x] `python -m pytest tests/test_api_auth.py tests/test_jobs_api.py tests/test_qramm_router.py tests/test_schedules_api.py -x -q` → 68 passed
- [x] `python -m pytest tests/test_qramm_multiplier.py -q` → 12 passed
- [x] Commits 82d4998, 86d3a55, 9501181, dfd8d1e confirmed in git log
