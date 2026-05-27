---
phase: 113-per-sensor-authentication
plan: "02"
subsystem: sensor-auth
tags: [auth, middleware, router-split, tdd, wave-2, AUTH-01, AUTH-02, AUTH-04]
dependency_graph:
  requires:
    - SensorToken.revoked_at column (113-01)
    - tests/test_sensor_auth_per_sensor.py gating test scaffold (113-01)
  provides:
    - require_sensor_auth FastAPI dependency
    - sensor_push_router (per-sensor auth router)
    - POST /api/sensor/push on per-sensor token path
    - quirk console revoke-sensor subcommand
    - D-01/D-02 operator/sensor router split
  affects:
    - quirk/dashboard/api/middleware/sensor_auth.py (created)
    - quirk/dashboard/api/routes/sensor.py (sensor_push_router split)
    - quirk/dashboard/api/app.py (dual router registration)
    - quirk/cli/console_cmd.py (revoke-sensor subcommand)
    - tests/test_api_auth.py (D-06 gate updated for require_sensor_auth)
    - tests/test_route_coverage.py (AUTH-02 gate updated for require_sensor_auth)
tech_stack:
  added: []
  patterns:
    - Two-router split (operator/sensor) mirroring jobs.py read_router/write_router
    - hmac.compare_digest timing-safe token comparison on SHA-256 hex
    - request.state.sensor_id for token-authoritative identity propagation
    - IntegrationDelivery audit rows on all auth failure branches
key_files:
  created:
    - quirk/dashboard/api/middleware/sensor_auth.py
  modified:
    - quirk/dashboard/api/routes/sensor.py
    - quirk/dashboard/api/app.py
    - quirk/cli/console_cmd.py
    - tests/test_api_auth.py
    - tests/test_route_coverage.py
decisions:
  - require_sensor_auth injects db via Depends(get_db) so audit rows can be written on 401 (D-09; RESEARCH Pitfall 2)
  - sensor_push_router split mirrors jobs.py read_router/write_router two-router pattern (D-01/D-02)
  - D-04: sensor lookup keyed off request.state.sensor_id (token-resolved), not envelope.sensor_id
  - D-05: envelope.sensor_id mismatch after token resolution -> 403 + audit (not 401)
  - test_api_auth.py and test_route_coverage.py gates updated to accept require_sensor_auth as a valid auth dep (D-01/D-02 split is by design)
  - test_sensor_ingest.py failures are expected and scheduled for Plan 03 (old shared-token tests; per VALIDATION Wave 0)
metrics:
  duration: "18m"
  completed: "2026-05-27"
  tasks: 3
  files: 6
---

# Phase 113 Plan 02: Per-Sensor Auth Cutover Summary

**One-liner:** SHA-256 per-sensor token auth on POST /api/sensor/push via require_sensor_auth middleware + revoke-sensor CLI — all 8 AUTH gating tests GREEN

## What Was Built

### Task 1: require_sensor_auth middleware

Created `quirk/dashboard/api/middleware/sensor_auth.py` with `require_sensor_auth(request, credentials, db) -> None`:

- Module-level `_bearer = HTTPBearer(auto_error=False)` mirrors auth.py L31
- DB injected via `Depends(get_db)` so audit rows can be written before raising (D-09; RESEARCH Pitfall 2)
- Inner `_audit_and_raise(status_code, error_summary, detail)` writes an `IntegrationDelivery` row with `destination="sensor_push"` and commits (guarding commit failures with `logger.warning(..., safe_str(exc))`), then raises `HTTPException`
- Three 401 branches: `missing_sensor_token` (no credentials), `unknown_sensor_token` (SHA-256 lookup miss), `revoked_sensor_token` (revoked_at not None)
- `hmac.compare_digest(hashed, token_row.token_hash)` defense-in-depth on matched row (D-03/T-113-06)
- `request.state.sensor_id = token_row.sensor_id` on success (D-04)
- Raw token `credentials.credentials` never logged (T-102-09/T-113-05)

**Verification:** compileall clean; signature check `{'request','credentials','db'} <= params` passed.

**Commit:** `8a5c5e1`

### Task 2: sensor_push_router split + token-authoritative identity (D-01/D-04/D-05)

Modified `quirk/dashboard/api/routes/sensor.py`:

- Added `from quirk.dashboard.api.middleware.sensor_auth import require_sensor_auth`
- Added `sensor_push_router = APIRouter(dependencies=[Depends(require_sensor_auth)])` (mirrors jobs.py read_router/write_router pattern)
- Moved `@router.post("/sensor/push")` to `@sensor_push_router.post("/sensor/push")` — operator `router` retains `require_auth`; `GET /api/sensor/registry` stays on `router` (D-02)
- Sensor lookup now uses `token_sensor_id = request.state.sensor_id` (D-04): `db.query(Sensor).filter(Sensor.sensor_id == token_sensor_id).first()`
- D-05 mismatch check: `if envelope.sensor_id != token_sensor_id:` -> `_audit(db, scan_id, "failed", "sensor_id_mismatch")` then `HTTPException(403, detail="sensor_id mismatch: token does not match envelope")`

Modified `quirk/dashboard/api/app.py`:
- Added `application.include_router(sensor.sensor_push_router, prefix="/api")` immediately after `sensor.router` include

**Verification:** All 8 `tests/test_sensor_auth_per_sensor.py` tests GREEN (8/8 passed).

**Commit:** `6757df1`

### Task 3: quirk console revoke-sensor subcommand (AUTH-02/D-06/D-07/D-08)

Modified `quirk/cli/console_cmd.py`:

- Added `revoke-sensor` subparser alongside `enroll` and `import-results`: positional `sensor_id` + `--config` args
- Extended dispatch block: `elif args.action == "revoke-sensor": _cmd_revoke_sensor(args)`
- Implemented `_cmd_revoke_sensor(args)` using `_cmd_enroll`'s lazy-import + session pattern:
  - Queries `SensorToken` filtered by `sensor_id == args.sensor_id` AND `revoked_at.is_(None)` (only active rows)
  - No active rows: `print(f"ERROR: no active token found for sensor_id {sensor_id!r}", file=sys.stderr); sys.exit(1)`
  - Sets `row.revoked_at = datetime.now(timezone.utc).replace(tzinfo=None)` for each active row, commits
  - `print(f"Revoked token(s) for sensor_id: {sensor_id}")` and returns normally (WR-04)
  - D-07 isolation: filter targets only the named sensor's rows; other sensors untouched
  - D-08: revoke-only path; no reissue logic added

Modified `tests/test_api_auth.py` (Rule 1 auto-fix):
- Updated D-06 mutating-route gate to accept `require_sensor_auth` alongside `require_auth`

Modified `tests/test_route_coverage.py` (Rule 1 auto-fix):
- Updated AUTH-02 coverage gate to accept `require_sensor_auth` alongside `require_auth`

**Verification:** `pytest tests/test_sensor_auth_per_sensor.py` — 8/8 passed; `pytest tests/test_api_auth.py tests/test_route_coverage.py` — 17/17 passed.

**Commits:** `ebb6665`, `f6e6c0d`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] test_api_auth.py D-06 gate rejected require_sensor_auth**

- **Found during:** Task 3
- **Issue:** `test_all_mutating_routes_have_auth_dependency` only checked for `require_auth`; after the router split, POST /api/sensor/push (now on `sensor_push_router`) triggered a D-06 violation
- **Fix:** Updated the gate to accept `auth_deps = {require_auth, require_sensor_auth}`; documented the D-01/D-02 split rationale in the docstring
- **Files modified:** `tests/test_api_auth.py`
- **Commit:** `ebb6665`

**2. [Rule 1 - Bug] test_route_coverage.py AUTH-02 gate rejected require_sensor_auth**

- **Found during:** Post-task regression run
- **Issue:** Same as above — `test_all_data_routes_have_auth_dependency` only checked for `require_auth`; POST /api/sensor/push triggered an AUTH-02 violation
- **Fix:** Updated the gate to accept `auth_deps = {require_auth, require_sensor_auth}`; documented the D-01/D-02 split rationale
- **Files modified:** `tests/test_route_coverage.py`
- **Commit:** `f6e6c0d`

### Expected RED (not attributable to this plan)

`tests/test_sensor_ingest.py` push tests (6 failures) are RED after this plan because the old shared-token tests pass `Authorization: Bearer test-token` (the v5.4 operator token) which is now correctly rejected with 401 on the per-sensor route. Per the plan's verification note and VALIDATION.md Wave 0: these tests are scheduled for update in Plan 03.

Other pre-existing failures in the broader suite (test_packaging, test_openapi_scanner, test_qramm_*, etc.) are pre-existing and not attributable to this plan.

## Known Stubs

None. All auth paths are fully wired.

## Threat Flags

None. All STRIDE threat register items from the plan's `<threat_model>` are mitigated:

| Threat ID | Mitigation Implemented |
|-----------|------------------------|
| T-113-03 | D-04: token_sensor_id authoritative; D-05: 403 + audit on mismatch |
| T-113-04 | revoked_at check in require_sensor_auth; revoke-sensor CLI; D-07 isolation |
| T-113-05 | credentials.credentials never logged; only SHA-256 hash compared |
| T-113-06 | hmac.compare_digest(hashed, token_row.token_hash) on equal-length hex |
| T-113-07 | sensor_push_router (require_sensor_auth) vs operator router (require_auth); registry on operator router |
| T-113-08 | Push route fully on require_sensor_auth; no dual-accept; D-10 clean cutover |
| T-113-SC | No new npm/pip installs |

## Self-Check

### Files exist:

- quirk/dashboard/api/middleware/sensor_auth.py — FOUND (require_sensor_auth implemented)
- quirk/dashboard/api/routes/sensor.py — FOUND (sensor_push_router + D-04/D-05 identity check)
- quirk/dashboard/api/app.py — FOUND (sensor.sensor_push_router registered)
- quirk/cli/console_cmd.py — FOUND (_cmd_revoke_sensor + revoke-sensor subparser)
- tests/test_api_auth.py — FOUND (D-06 gate updated)
- tests/test_route_coverage.py — FOUND (AUTH-02 gate updated)

### Commits exist:

- 8a5c5e1 — feat(113-02): add require_sensor_auth middleware
- 6757df1 — feat(113-02): split push route onto sensor-auth router + enforce token identity
- ebb6665 — feat(113-02): add revoke-sensor subcommand + update D-06 auth gate
- f6e6c0d — fix(113-02): update route-coverage auth gate for require_sensor_auth

### Gating tests: 8/8 PASSED

## Self-Check: PASSED
