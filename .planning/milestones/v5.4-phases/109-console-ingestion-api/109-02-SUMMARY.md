---
phase: 109-console-ingestion-api
plan: "02"
subsystem: api
tags: [sensor, ingestion, push-endpoint, dedup, audit, fastapi, pydantic, cryptoendpoint]
dependency_graph:
  requires: [109-01, 108-03]
  provides: [CONSOLE-01, CONSOLE-02, CONSOLE-03, CONSOLE-04, CONSOLE-05]
  affects:
    - quirk/cli/console_cmd.py
    - quirk/dashboard/api/routes/sensor.py
    - quirk/dashboard/api/app.py
tech_stack:
  added: []
  patterns:
    - "APIRouter(dependencies=[Depends(require_auth)]) — M2M router-level auth, no require_csrf"
    - "PushEnvelope Pydantic model ConfigDict(extra='ignore') — version-skew warn-only"
    - "_audit() helper: IntegrationDelivery commit outside ingest try (WR-01 base.py L149)"
    - "DuplicatePayloadError sentinel: IntegrityError → rollback → typed raise → 409 fixed string"
    - "_ingest_envelope db=None extension: own-session (CLI) vs injected-session (HTTPS) paths"
    - "_parse_dt: fromisoformat + Z→+00:00 + replace(tzinfo=None); malformed → None"
    - "safe_str(exc) on all error_summary paths; fixed strings for 409/unknown-sensor (LEAK-02)"
key_files:
  created:
    - quirk/dashboard/api/routes/sensor.py
  modified:
    - quirk/cli/console_cmd.py
    - quirk/dashboard/api/app.py
decisions:
  - "109-02-D-01: _audit() commits in its own try/except so audit-write failure cannot mask original error (WR-01)"
  - "109-02-D-02: Injected db session uses flush-only inside _ingest_envelope; route owns final db.commit() after ingest"
  - "109-02-D-03: scan_id for audit rows uses pushed_at once parsed (received_at ISO string as fallback before parse)"
metrics:
  duration: "~25 min"
  completed: "2026-05-25"
  tasks_completed: 3
  files_modified: 3
---

# Phase 109 Plan 02: Sensor Push Endpoint + Shared Ingest Path Summary

**One-liner:** POST /api/sensor/push with router-level auth, full §6 failure ladder (401/413/400/422/404/409/200), IntegrationDelivery audit on every branch, and a shared `_ingest_envelope` path (sensor_pushes dedup + sensors.last_push_at + CryptoEndpoint persist) used by both HTTPS push and air-gap import.

## What Was Built

### Task 1: Replace `_ingest_envelope` stub with real dedup + persist logic (`quirk/cli/console_cmd.py`)

Replaced the Phase 108 print-summary stub with real DB logic:

- **`DuplicatePayloadError`** sentinel exception defined at module level (typed raise for 409 seam).
- **`_parse_dt()` helper** — `fromisoformat` with `Z→+00:00` + `replace(tzinfo=None)`; malformed → None.
- **Signature extended** with trailing `db=None` param — air-gap caller at line 305 unchanged.
- **Own-session path** (CLI / `db=None`): `init_db(_default_db_path())` + sessionmaker; `finally: db.close()`.
- **Injected-session path** (HTTPS / `db!=None`): flush-only, caller owns commit boundary.
- **Dedup**: `SensorPush(payload_id, sensor_id, received_at=now)` → `db.flush()` → `IntegrityError` → `db.rollback()` → `raise DuplicatePayloadError`.
- **`sensors.last_push_at`** updated to `now` on accepted push.
- **`CryptoEndpoint` rows**: one per finding dict; envelope top-level `sensor_id`/`segment` override per-finding values (forward-compat).
- No `str(exc)` / `repr(exc)` anywhere; `safe_str()` for all logging.

**Commit:** `b3cb598`

### Task 2: Create `quirk/dashboard/api/routes/sensor.py` — PushEnvelope model + failure-mode ladder + audit

New file implementing the full §6 security contract:

- **`router = APIRouter(dependencies=[Depends(require_auth)])`** — M2M, NO `require_csrf`.
- **`PushEnvelope`** Pydantic model with `ConfigDict(extra="ignore")` — unknown fields silently dropped (D-11).
- **`_audit(db, scan_id, status, error_summary)`** — writes `IntegrationDelivery(destination="sensor_push")` on every attempt; commit OUTSIDE the ingest try-block.
- **Failure ladder** (in order):
  - `413` Content-Length > 10 MB or actual body > 10 MB → `_audit` + raise.
  - `400` zstd decompress failure → `_audit` + raise (not 500).
  - `413` decompressed size > 20 MB → `_audit` + raise.
  - `400` JSON/Pydantic parse failure → `_audit` + raise.
  - `422` `pushed_at` outside ±15 min of `received_at` → `_audit` + raise with `{"error":"replay_window_exceeded","console_utc":"..."}`.
  - `404` unknown `sensor_id` → `_audit` + raise with fixed "Unknown sensor_id".
  - `409` `DuplicatePayloadError` → `_audit` + raise with fixed "Duplicate payload_id".
  - `200` success → `db.commit()` + `_audit(status="ok")` + `{"status":"accepted",...}`.
- **X-Sensor-Signature**: read + structural validate (`hmac-sha256=<hex>` prefix); carried as `qpush_sig` into `_ingest_envelope`; no crypto verify (T-109-11 / v5.5 deferred).
- **schema_version / sensor_version** mismatch: logged at DEBUG only, never 422/500.

**Commit:** `75561b4`

### Task 3: Mount `sensor.router` in `app.py`

- Added `sensor` to the `from quirk.dashboard.api.routes import ...` tuple.
- Added `application.include_router(sensor.router, prefix="/api")` alongside existing include_router calls.
- `POST /api/sensor/push` now resolves on the FastAPI app.

**Commit:** `6577e09`

## Verification Results

```
python -m compileall quirk run_scan.py  → Exit code 0 (CLEAN)
pytest tests/test_api_auth.py -k "auth_dependency" -q  → 1 passed
pytest tests/ -k "sensor_push or ingest" -q  → 8 passed
QUIRK_DB_PATH=/tmp/test.db python -c "assert any(r.path=='/api/sensor/push' ...)"  → PASS
grep "require_csrf" sensor.py (non-comment usage)  → NONE (PASS)
grep "str(exc)\|repr(exc)" sensor.py  → NONE (PASS)
```

## Deviations from Plan

None — plan executed exactly as written. All acceptance criteria met across all three tasks.

## Threat Surface Scan

New network endpoint introduced: `POST /api/sensor/push` — documented in plan threat model (T-109-04 through T-109-11). All mitigations applied:

| Flag | File | Description |
|------|------|-------------|
| threat: new_endpoint | quirk/dashboard/api/routes/sensor.py | POST /api/sensor/push — compressed M2M push from remote sensors; gated by router-level auth + full failure ladder |

All threats in the plan's STRIDE register are mitigated (T-109-04..T-109-10) or accepted with documented rationale (T-109-11: HMAC verify deferred v5.5).

## Known Stubs

None — all persistence paths are wired. `_ingest_envelope` writes real SensorPush + CryptoEndpoint rows.

## Self-Check: PASSED

- `quirk/dashboard/api/routes/sensor.py` created: FOUND
- `quirk/cli/console_cmd.py` modified: FOUND
- `quirk/dashboard/api/app.py` modified: FOUND
- Commit `b3cb598` (Task 1 _ingest_envelope): FOUND
- Commit `75561b4` (Task 2 sensor.py): FOUND
- Commit `6577e09` (Task 3 app.py mount): FOUND
- `python -m compileall quirk run_scan.py`: CLEAN
- Route `/api/sensor/push` present in app routes: PASS
- No `require_csrf` usage in sensor.py: PASS
- No `str(exc)`/`repr(exc)` in sensor.py: PASS
- Auth dependency test: 1 passed
- Ingest/sensor_push tests: 8 passed
