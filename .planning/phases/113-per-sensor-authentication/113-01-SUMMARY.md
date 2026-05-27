---
phase: 113-per-sensor-authentication
plan: "01"
subsystem: sensor-auth
tags: [auth, schema, migration, tdd, wave-0]
dependency_graph:
  requires: []
  provides:
    - SensorToken.revoked_at nullable column
    - _V55_SENSOR_TOKEN_COLUMNS additive migration
    - tests/test_sensor_auth_per_sensor.py AUTH-01..04 gating test scaffold
  affects:
    - quirk/models.py
    - quirk/db.py
    - tests/test_sensor_auth_per_sensor.py
tech_stack:
  added: []
  patterns:
    - additive nullable column via _ensure_columns (idempotent ALTER TABLE)
    - Wave 0 RED gating test scaffold (tests fail until Plan 02 wires auth)
key_files:
  created:
    - tests/test_sensor_auth_per_sensor.py
  modified:
    - quirk/models.py
    - quirk/db.py
decisions:
  - SensorToken.revoked_at is nullable (None=active, set=revoked) per D-06 additive-only constraint
  - Raw token stored only in-memory during tests; only SHA-256 hash written to sensor_tokens (T-113-02)
  - Wave 0 RED tests: 2 pass (success path works via existing auth), 6 fail (per-sensor behaviors RED until Plan 02)
metrics:
  duration: "12m"
  completed: "2026-05-27"
  tasks: 2
  files: 3
---

# Phase 113 Plan 01: Schema Foundation + AUTH-01..04 Gating Test Summary

**One-liner:** Additive `revoked_at` column on `sensor_tokens` with idempotent migration + 8-function AUTH gating test scaffold (Wave 0 RED)

## What Was Built

### Task 1: SensorToken.revoked_at column + _V55_SENSOR_TOKEN_COLUMNS migration

Added `revoked_at = Column(DateTime, nullable=True)` to `SensorToken` in `quirk/models.py` immediately after `created_at`. Existing `DateTime` import used — no new import needed.

In `quirk/db.py`, defined `_V55_SENSOR_TOKEN_COLUMNS` tuple containing `("revoked_at", "DATETIME")` and appended `("sensor_tokens", _V55_SENSOR_TOKEN_COLUMNS)` as the last entry in `_ADDITIVE_MIGRATIONS`. The existing `_ensure_columns` helper handles idempotency (skips the column if already present) and the `DATETIME` type is already in `_SAFE_COL_TYPE_RE`. No changes to `_ensure_columns` or `init_db` were needed.

**Verification:** `python -m compileall` exits 0; `SensorToken.__table__.columns['revoked_at'].nullable is True`; migration registered in `_ADDITIVE_MIGRATIONS`.

**Commits:** `48c3bcd`

### Task 2: AUTH-01..04 Gating Test File (Wave 0, RED)

Created `tests/test_sensor_auth_per_sensor.py` with:

- `_make_test_engine`, `_app_with_db`, `_seed_sensor`, `_build_envelope`, `_compress` — copied verbatim from `test_sensor_ingest.py` per PATTERNS.md
- `_seed_token(TestingSession, sensor_id, raw_token=None, revoked=False)` — mints `secrets.token_urlsafe(32)` when no raw token given; stores only SHA-256 hex digest; supports `revoked=True` for immediate revocation (T-113-02)
- 8 test functions:
  1. `test_valid_sensor_token_accepted` — valid push → 200 (AUTH-01)
  2. `test_token_identity_is_authoritative` — token identity is canonical (AUTH-01 / D-04)
  3. `test_revoked_token_returns_401` — revoked token → 401 (AUTH-02 / AUTH-04)
  4. `test_revoke_isolates_to_one_sensor` — sensor-a revoked; sensor-b active → a=401, b=200 (AUTH-02)
  5. `test_unknown_token_returns_401` — never-seeded token → 401 (AUTH-04)
  6. `test_sensor_id_mismatch_returns_403` — valid token for a, envelope claims b → 403 (AUTH-04 / D-05)
  7. `test_all_branches_write_audit_rows` — all 4 branches write IntegrationDelivery rows with distinct error_summary values (AUTH-04 / D-09)
  8. `test_missing_token_returns_401` — no Authorization header → 401

**Wave 0 RED state:** 2 tests pass (success path goes through existing auth path), 6 tests fail (per-sensor auth behaviors not yet wired). This is expected per VALIDATION.md Wave 0 — auth wiring lands in Plan 02.

**Verification:** `python -m compileall` exits 0; 8 tests collected cleanly; RED state confirmed.

**Commits:** `4d5dba0`

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. This plan adds a schema column and a test scaffold. No UI, no data rendering.

## Threat Flags

None. All threat register items from the plan's `<threat_model>` were satisfied:
- T-113-01 (additive migration): mitigated by `_ensure_columns` idempotency
- T-113-02 (raw token in tests): mitigated by `_seed_token` using SHA-256 hash only (raw token in-memory only)
- T-113-SC (no new packages): confirmed — no new `npm install` or `pip install`

## Self-Check

### Files exist:
- quirk/models.py — FOUND (SensorToken.revoked_at added)
- quirk/db.py — FOUND (_V55_SENSOR_TOKEN_COLUMNS + migration entry added)
- tests/test_sensor_auth_per_sensor.py — FOUND (8 tests, _seed_token)

### Commits exist:
- 48c3bcd — feat(113-01): add revoked_at column to SensorToken and _V55_SENSOR_TOKEN_COLUMNS migration
- 4d5dba0 — test(113-01): add AUTH-01..04 gating test scaffold (Wave 0, RED)

## Self-Check: PASSED
