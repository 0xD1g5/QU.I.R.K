---
phase: 195-quantum-exposure-map
plan: 04
subsystem: api
tags: [fastapi, pydantic, sqlalchemy, exposure-map, auth]

# Dependency graph
requires:
  - phase: 195-quantum-exposure-map
    provides: "plan 02's derive_exposure_map orchestrator (nodes/edges dict shape, honest-absence D-08); plan 03's score-firewall guard (D-10)"
provides:
  - "ExposureNode/ExposureEdge/ExposureMapResponse Pydantic schemas (schemas.py) with closed edge_type vocabulary + required non-empty evidence + no severity/score field"
  - "GET /api/exposure-map auth-gated route, registered in app.py, serializing derive_exposure_map's dict output"
  - "Route tests: auth gating (401/200), empty-DB honest-absence, seeded key-reuse cluster evidence assertions"
affects: [195-05, 195-06, 195-07, dashboard-frontend-exposure-map-tab]

# Tech tracking
tech-stack:
  added: []
  patterns: [router-level-auth-dependency, honest-absence-response-envelope, closed-vocabulary-field-validator, orchestrator-serialization-only-route]

key-files:
  created:
    - quirk/dashboard/api/routes/exposure_map.py
    - tests/test_exposure_map_route.py
  modified:
    - quirk/dashboard/api/schemas.py
    - quirk/dashboard/api/app.py

key-decisions:
  - "EDGE_TYPES stays Tier-A-only (key_reuse, hardware_bridge) — 195-SPIKE-DECISION.md recorded DECISION: DEFERRED, not GO, so declared_reachability was NOT added"
  - "Derivation errors in the route handler degrade to an advisory-empty ExposureMapResponse rather than a 500, mirroring hardware_drift/scan.py bridge error handling, to avoid leaking internals (T-195-06)"
  - "Route tests use QUIRK_DB_PATH env var override (not a route-specific monkeypatch of _default_db_path) since get_db() resolves the path itself via deps.py, matching the get_db()/_default_db_path() call shape exactly"

patterns-established:
  - "Pattern: route handler is pure serialization — calls the importable orchestrator, maps its dict output into typed Pydantic models, never reimplements derivation logic route-side"

requirements-completed: [MAP-02]

# Metrics
duration: 25min
completed: 2026-09-09
---

# Phase 195 Plan 04: Exposure Map Schemas + Auth-Gated Route Summary

**Auth-gated GET /api/exposure-map wired to the plan-02 derivation via typed Pydantic schemas that structurally forbid severity/score fields and require per-edge evidence.**

## Performance

- **Duration:** ~25 min
- **Tasks:** 2 completed
- **Files modified:** 4 (2 created, 2 modified)

## Accomplishments
- `ExposureNode`/`ExposureEdge`/`ExposureMapResponse` Pydantic models added to `schemas.py`, mirroring the `HardwareDriftEventItem`/`HardwareDriftResponse` pattern: closed `edge_type` vocabulary via `field_validator`, required non-empty `evidence` via `field_validator`, no `severity`/`score` field anywhere, and always-present typed lists defaulting to `[]`.
- `quirk/dashboard/api/routes/exposure_map.py` created: `router = APIRouter(dependencies=[Depends(require_auth)])` at router level only (identical to `hardware_drift.router`), handler calls `derive_exposure_map(db)` directly (no route-private logic), returns `ExposureMapResponse(nodes=[], edges=[])` on zero edges, degrades to advisory-empty on any derivation exception.
- Registered in `app.py`: import added to the routes tuple, `include_router(exposure_map.router, prefix="/api")` added adjacent to `hardware_drift.router`.
- `tests/test_exposure_map_route.py` created with 3 tests: empty-DB honest-absence (`nodes == []`, `edges == []`), seeded key-reuse cluster (two `CryptoEndpoint` rows sharing a `cert_spki_fingerprint`) asserting every returned edge has non-empty `evidence` and a vocabulary-valid `edge_type`, and auth gating (401 without token, 200 with `X-API-Key`).

## Task Commits

Each task was committed atomically:

1. **Task 1: Add ExposureNode/ExposureEdge/ExposureMapResponse to schemas.py** - `ae92ca83` (feat)
2. **Task 2: Create routes/exposure_map.py, register in app.py, add route tests** - `4ea93cf5` (feat)

**Plan metadata:** commit pending (docs: complete plan)

## Files Created/Modified
- `quirk/dashboard/api/schemas.py` - Added `EDGE_TYPES`, `ExposureNode`, `ExposureEdge`, `ExposureMapResponse`
- `quirk/dashboard/api/routes/exposure_map.py` - New auth-gated route module
- `quirk/dashboard/api/app.py` - Registered `exposure_map.router`
- `tests/test_exposure_map_route.py` - Auth gating, empty-DB, seeded-edge-evidence tests

## Decisions Made
- Kept `EDGE_TYPES` Tier-A-only per the spike's `DECISION: DEFERRED` — did not add `declared_reachability`.
- Wrapped `derive_exposure_map(db)` in try/except degrading to an advisory-empty response, matching the plan's explicit instruction and the codebase's established error-handling shape (T-195-06 mitigation).
- Used `QUIRK_DB_PATH` env var for route-test DB isolation since `get_db()` resolves its own path via `deps._default_db_path()` at call time — matches the actual dependency wiring rather than assuming a per-route override point existed.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `GET /api/exposure-map` is live, auth-gated, and returns the stable JSON contract (`nodes`/`edges` always present) the frontend map tab (plan 195-06/07) needs.
- No scoring import present in the route module (D-10 firewall intact — `tests/test_exposure_map_score_guard.py` from plan 195-03 still green against the now-larger module surface).
- No blockers for the frontend Cytoscape wiring.

---
*Phase: 195-quantum-exposure-map*
*Completed: 2026-09-09*

## Self-Check: PASSED

All created/modified files found on disk; both task commits (`ae92ca83`, `4ea93cf5`) present in `git log`.
