---
phase: 58-dashboard-api-hardening
plan: "04"
subsystem: api-security
tags: [fastapi, auth, csrf, rate-limit, cors, tdd, middleware, security]

requires:
  - phase: 58-dashboard-api-hardening-plan-01
    provides: require_auth + require_csrf Depends() in middleware package
  - phase: 58-dashboard-api-hardening-plan-02
    provides: RateLimitMiddleware + CORSMiddleware in app factory
  - phase: 58-dashboard-api-hardening-plan-03
    provides: port-clamp guard in pdf.py (D-11 / HARDEN-API-05)

provides:
  - tests/test_api_auth.py: full 16-test suite for auth/CSRF/rate-limit/CORS/GET-auth/introspection/pdf-port-clamp
  - quirk/dashboard/api/routes/pdf.py: router with Depends(require_auth) + Depends(require_csrf)
  - quirk/dashboard/api/routes/qramm.py: router with Depends(require_auth) + Depends(require_csrf)
  - quirk/dashboard/api/routes/scan.py: router with Depends(require_auth)
  - quirk/dashboard/api/routes/trends.py: router with Depends(require_auth)

affects:
  - 65-dashboard-initiated-scan (all scan-initiating routes now require auth)

tech-stack:
  added: []
  patterns:
    - "TDD RED/GREEN: failing tests committed before implementation, then wired to pass"
    - "Router-level Depends() injection: APIRouter(dependencies=[...]) applies to all routes in the router"
    - "D-06 introspection gate: meta-test iterates app.routes to catch future auth omissions in CI"
    - "monkeypatch.setattr() used to bypass playwright's 503-not-installed guard for port-clamp functional coverage"

key-files:
  created:
    - tests/test_api_auth.py
  modified:
    - quirk/dashboard/api/routes/pdf.py
    - quirk/dashboard/api/routes/qramm.py
    - quirk/dashboard/api/routes/scan.py
    - quirk/dashboard/api/routes/trends.py

key-decisions:
  - "Router-level dependencies preferred over per-endpoint Depends() — single declaration covers all routes in router, future routes added to same router inherit auth automatically"
  - "scan.py and trends.py get require_auth only (read-only routers — D-05: no CSRF needed for GET)"
  - "pdf.py and qramm.py get both require_auth + require_csrf (mutating routers)"
  - "pdf port-clamp test uses monkeypatch.setattr to set sync_playwright to a non-None sentinel, allowing the port check to fire before Playwright's 503-not-installed guard"
  - "introspection gate (D-06) checks route.dependencies not endpoint-level deps — router-level injection appears here correctly"

requirements-completed:
  - HARDEN-API-01
  - HARDEN-API-02
  - HARDEN-API-03
  - HARDEN-API-05

duration: 5min
completed: 2026-05-09
---

# Phase 58 Plan 04: Dashboard API Hardening — Auth Wiring + Test Suite Summary

**Full 16-test auth/CSRF/rate-limit/CORS/GET-auth/introspection/pdf-port-clamp suite; require_auth + require_csrf wired at router level on pdf, qramm, scan, and trends routers via TDD RED/GREEN cycle**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-05-09T22:30:11Z
- **Completed:** 2026-05-09T22:32:37Z
- **Tasks:** 2 (RED commit + GREEN commit)
- **Files modified:** 5 (1 created, 4 modified)

## Accomplishments

- Created `tests/test_api_auth.py` — 16 tests covering all HARDEN-API-01/02/03/05 requirements
- Wired `require_auth` + `require_csrf` to `pdf.py` and `qramm.py` as router-level dependencies
- Wired `require_auth` to `scan.py` and `trends.py` as router-level dependencies (read-only routes — D-05)
- Route-introspection regression gate `test_all_mutating_routes_have_auth_dependency` passes — will catch any future mutating route added without auth
- `test_get_routes_require_auth` confirms GET /api/scans and GET /api/trends return 401 without token (D-05 read routes not exempt from auth)
- `test_pdf_port_clamp_rejects_privileged_port` provides functional pytest coverage for D-11/HARDEN-API-05 guard implemented in Plan 03

## Task Commits

1. **Task 1 (RED): Create test_api_auth.py** — `9fc469d` (test)
2. **Task 2 (GREEN): Wire require_auth + require_csrf to all routers** — `31ff8ef` (feat)

## Files Created/Modified

- `tests/test_api_auth.py` — 16-test suite, TestClient(create_app()) pattern with in-memory SQLite
- `quirk/dashboard/api/routes/pdf.py` — `APIRouter(dependencies=[Depends(require_auth), Depends(require_csrf)])`
- `quirk/dashboard/api/routes/qramm.py` — `APIRouter(dependencies=[Depends(require_auth), Depends(require_csrf)])`
- `quirk/dashboard/api/routes/scan.py` — `APIRouter(dependencies=[Depends(require_auth)])`
- `quirk/dashboard/api/routes/trends.py` — `APIRouter(dependencies=[Depends(require_auth)])`

## TDD Gate Compliance

- RED commit (`9fc469d`): `test(58-04):` — 6 tests failing (auth/CSRF/introspection/GET-route-auth)
- GREEN commit (`31ff8ef`): `feat(58-04):` — all 16 tests pass after router wiring
- Gate sequence: RED → GREEN is correct and complete

## Decisions Made

- Router-level injection (`APIRouter(dependencies=[...])`) chosen over per-endpoint `Depends()` so that every future route added to the same router inherits auth automatically without a per-route annotation requirement. This is how the introspection gate's `route.dependencies` list surfaces the dependency.
- The introspection gate uses `route.dependencies` (the router-level list) to verify — FastAPI merges router-level and endpoint-level dependencies at route registration, but the introspection test specifically checks the router-level list which is where the router-wide Depends appear.
- `monkeypatch.setattr(pdf_module, "sync_playwright", object())` in the port-clamp test bypasses the Playwright-not-installed 503 guard that would otherwise prevent reaching the port-range clamp at lines 54-62 of pdf.py.

## Deviations from Plan

### Test adjustment — pdf port-clamp mock

The initial test wrote `QUIRK_SERVE_PORT=80` without mocking playwright, causing a 503 (playwright not installed) rather than 500 (port out of range). The port check at lines 54-62 only runs after the `sync_playwright is None` check at line 35. Fixed by adding `monkeypatch.setattr(pdf_module, "sync_playwright", object())` to patch the module-level attribute to a non-None sentinel so the port check fires. This is consistent with the plan's intent and is a test implementation detail, not a behavior change.

## Issues Encountered

None beyond the minor test adjustment documented above.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes introduced. The plan's threat model (T-58-04-E, T-58-04-S, T-58-04-I) mitigations are all implemented:
- T-58-04-E (Elevation of Privilege): D-06 introspection gate now in CI — `test_all_mutating_routes_have_auth_dependency` fails if any future mutating route omits `require_auth`
- T-58-04-S (test token leakage): Tests use `monkeypatch.setenv("QUIRK_API_TOKEN", "test-token")` — isolated to test process, never touches real config
- T-58-04-I (401 vs 403 distinction): Accepted per plan — the distinction is intentional

## Known Stubs

None — all security middleware is fully wired and tested.

## Self-Check: PASSED

- `tests/test_api_auth.py` — FOUND
- `quirk/dashboard/api/routes/pdf.py` contains `require_auth` — FOUND
- `quirk/dashboard/api/routes/qramm.py` contains `require_auth` — FOUND
- `quirk/dashboard/api/routes/scan.py` contains `require_auth` — FOUND
- `quirk/dashboard/api/routes/trends.py` contains `require_auth` — FOUND
- Commit 9fc469d (RED) — FOUND
- Commit 31ff8ef (GREEN) — FOUND
- `python -m pytest tests/test_api_auth.py -v` exits 0 — VERIFIED (16 passed)
- `python -m compileall` for all four route files exits 0 — VERIFIED

---
*Phase: 58-dashboard-api-hardening*
*Completed: 2026-05-09*
