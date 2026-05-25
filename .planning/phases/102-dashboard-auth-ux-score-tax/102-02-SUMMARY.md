---
phase: 102-dashboard-auth-ux-score-tax
plan: "02"
subsystem: dashboard-auth
tags: [auth, x-api-key, bearer, ci-gate, middleware, tdd]
dependency_graph:
  requires: []
  provides: [AUTH-02, route-coverage-ci-gate]
  affects: [quirk.dashboard.api.middleware.auth, tests/test_dashboard_auth_apikey, tests/test_route_coverage]
tech_stack:
  added: []
  patterns: [hmac.compare_digest timing-safe comparison, FastAPI route introspection, TDD RED-GREEN]
key_files:
  created:
    - tests/test_dashboard_auth_apikey.py
    - tests/test_route_coverage.py
  modified:
    - quirk/dashboard/api/middleware/auth.py
decisions:
  - "Static file routes (/favicon.*, /{full_path:path}) exempted from route-coverage gate — gate scoped to /api/* prefix only (all data API routes)"
  - "X-API-Key precedence over bearer: if present, it is fully authoritative (valid=pass, invalid=401); bearer never consulted when X-API-Key header is non-empty"
metrics:
  duration_seconds: 115
  completed_date: "2026-05-25"
  tasks_completed: 2
  files_modified: 3
requirements: [AUTH-02]
---

# Phase 102 Plan 02: AUTH-02 X-API-Key Header + Route-Coverage CI Gate Summary

**One-liner:** X-API-Key header support added to require_auth with hmac.compare_digest precedence over bearer, plus a /api/* route-coverage CI gate that fails the build if any data route ships without auth.

## What Was Built

### Task 1: Failing AUTH-02 tests + route-coverage gate (TDD RED)

Created `tests/test_dashboard_auth_apikey.py` with five functional tests using the `authed_client` pattern from `test_api_auth.py`:

- `test_x_api_key_accepted` — GET /api/scans with X-API-Key=test-token returns non-401
- `test_x_api_key_precedence_over_bearer` — X-API-Key=test-token + wrong bearer → non-401 (X-API-Key wins)
- `test_invalid_x_api_key_returns_401` — wrong X-API-Key returns 401
- `test_bearer_still_works` — no X-API-Key, valid bearer → non-401 (fallback preserved)
- `test_auth_disabled_passthrough` — no QUIRK_API_TOKEN → GET /api/scans returns non-401 with no auth header

Created `tests/test_route_coverage.py` with `test_all_data_routes_have_auth_dependency` — introspects `app.routes`, filters to `/api/` prefix (excluding `/api/health` and static/SPA routes), asserts every route has `require_auth` in its dependency callables. This is a regression guard: all 7 data routers already use `router-level Depends(require_auth)`, so it passed GREEN immediately.

RED state confirmed: `test_x_api_key_accepted` and `test_x_api_key_precedence_over_bearer` failed (auth.py not yet extended).

### Task 2: Extend require_auth to accept X-API-Key (TDD GREEN)

Extended `quirk/dashboard/api/middleware/auth.py::require_auth` to insert the X-API-Key path before the existing bearer check:

```python
x_api_key = request.headers.get("X-API-Key", "")
if x_api_key:
    if hmac.compare_digest(x_api_key, configured):
        return  # valid X-API-Key
    raise HTTPException(status_code=401, detail=format_error("DASHBOARD-001"))
# Fallback: bearer path — preserved unchanged
```

Key properties:
- `if x_api_key:` guard prevents `hmac.compare_digest` on empty string (T-102-06)
- Both operands to `hmac.compare_digest` are `str` — no `.encode()` (per Pitfall 1 / T-102-05)
- X-API-Key present → authoritative; bearer never consulted (T-102-07)
- Auth-disabled passthrough (`not configured: return`) preserved (D-02)
- Token never logged (T-102-09)
- No new imports — `Request` already in signature, `hmac` already imported

All 22 tests pass: 5 new AUTH-02 functional, 1 route-coverage gate, 16 pre-existing.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Route-coverage gate scoped to /api/ prefix only**
- **Found during:** Task 1 (TDD RED verification)
- **Issue:** Initial gate checked all `APIRoute` instances; `app.routes` includes static file routes (`/favicon.ico`, `/favicon.svg`, `/favicon.png`) and the SPA catch-all (`/{full_path:path}`) — none of which have or need `require_auth`. These caused spurious gate failures.
- **Fix:** Added `if not route.path.startswith("/api/"): continue` filter — all data-returning API routes live under `/api/`, static/SPA routes do not. This is semantically correct: the plan's intent is to gate API data routes.
- **Files modified:** `tests/test_route_coverage.py`
- **Commit:** 4e00c4f

## Known Stubs

None — no placeholder values or hardcoded stubs introduced.

## Threat Flags

No new security surface beyond what the plan's threat model covers. The X-API-Key path reuses existing DASHBOARD-001 error code, no new endpoints, no query-param token path.

## TDD Gate Compliance

- RED gate commit: `4e00c4f` (test(102-02): add failing AUTH-02 tests + route-coverage gate)
- GREEN gate commit: `419c7c5` (feat(102-02): extend require_auth to accept X-API-Key header)

## Self-Check

### Files exist:

- quirk/dashboard/api/middleware/auth.py: FOUND
- tests/test_dashboard_auth_apikey.py: FOUND
- tests/test_route_coverage.py: FOUND

### Commits exist:

- 4e00c4f: FOUND
- 419c7c5: FOUND

## Self-Check: PASSED
