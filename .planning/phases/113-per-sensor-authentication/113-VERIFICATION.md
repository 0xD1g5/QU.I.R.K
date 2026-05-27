---
phase: 113-per-sensor-authentication
verified: 2026-05-26T00:00:00Z
status: passed
score: 4/4 must-haves verified
overrides_applied: 0
---

# Phase 113: Per-Sensor Authentication Verification Report

**Phase Goal:** Operators can issue, manage, and revoke individual sensor tokens so each sensor is independently authenticated at ingestion and a compromised sensor can be cut off without affecting others.
**Verified:** 2026-05-26
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `quirk console enroll-sensor` issues a per-sensor opaque token bound to the sensor UUID; raw token shown once, SHA-256 hash only in `sensor_tokens` | VERIFIED | `_cmd_enroll` hashes with `hashlib.sha256`; enrollment printout states "Bearer token (copy now — shown once, never recoverable)"; `test_console_enroll.py` asserts `token_row.revoked_at is None`; raw never written to DB |
| 2 | `quirk console revoke-sensor <sensor-id>` succeeds and immediately causes that sensor's next `POST /api/sensor/push` to return 401, while other enrolled sensors continue to push | VERIFIED | `_cmd_revoke_sensor` stamps `revoked_at=now` filtered by `revoked_at.is_(None)` for the target sensor only (D-07 isolation); `require_sensor_auth` rejects any row with `revoked_at is not None`; `test_revoke_isolates_to_one_sensor` confirms sensor-b stays 200; all 8 gating tests GREEN |
| 3 | `POST /api/sensor/push` with unknown/revoked token returns 401 and logs the rejection; valid per-sensor token accepted, push attributed to correct sensor UUID | VERIFIED | `require_sensor_auth` covers all four branches (missing_sensor_token, unknown_sensor_token, revoked_sensor_token, valid); `sensor_push_router = APIRouter(dependencies=[Depends(require_sensor_auth)])`; push handler uses `request.state.sensor_id` (D-04); `test_all_branches_write_audit_rows` confirms `IntegrationDelivery` rows with correct `error_summary` values |
| 4 | Operators running the v5.4 shared-token model can migrate to per-sensor tokens following the updated operators guide without re-enrolling from scratch | VERIFIED | `docs/operators-guide.md` §8.1.1 fully replaced with v5.5 per-sensor migration (12 "per-sensor" occurrences); references `revoke-sensor`; covers four D-10/D-11 points; `expected_results_distributed.md` oracle updated; enrollment printout corrected (D-11) |

**Score:** 4/4 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `quirk/dashboard/api/middleware/sensor_auth.py` | `require_sensor_auth` dependency | VERIFIED | File exists; `require_sensor_auth(request, credentials, db)` with `hashlib.sha256`, `hmac.compare_digest`, `revoked_at` check, `IntegrationDelivery` audit on all 401 branches; raw token never logged |
| `quirk/dashboard/api/routes/sensor.py` | `sensor_push_router` + D-04/D-05 identity check | VERIFIED | `sensor_push_router = APIRouter(dependencies=[Depends(require_sensor_auth)])` at L59; `@sensor_push_router.post("/sensor/push")` at L203; `token_sensor_id = request.state.sensor_id` at L317; D-05 mismatch check at L324 |
| `quirk/dashboard/api/app.py` | `include_router(sensor.sensor_push_router)` | VERIFIED | `application.include_router(sensor.sensor_push_router, prefix="/api")` at L118, immediately after `sensor.router` |
| `quirk/cli/console_cmd.py` | `_cmd_revoke_sensor` + `revoke-sensor` subparser | VERIFIED | Subparser added at L117; dispatch at L132-133; `_cmd_revoke_sensor` at L241 with `revoked_at.is_(None)` filter, timestamp stamp, `sys.exit(1)` on no-active, WR-04 return-normally |
| `quirk/models.py` | `SensorToken.revoked_at` nullable column | VERIFIED | `revoked_at = Column(DateTime, nullable=True)` at L313 |
| `quirk/db.py` | `_V55_SENSOR_TOKEN_COLUMNS` + migration entry | VERIFIED | Defined at L131-135; registered in `_ADDITIVE_MIGRATIONS` at L193 as `("sensor_tokens", _V55_SENSOR_TOKEN_COLUMNS)` |
| `tests/test_sensor_auth_per_sensor.py` | 8 gating tests + `_seed_token` | VERIFIED | 8 test functions confirmed by AST parse; `_seed_token` helper present; all 8 tests GREEN |
| `tests/test_sensor_ingest.py` | `_seed_token` + per-sensor Bearer headers | VERIFIED | `_seed_token` at L128; 7 push tests updated to seed tokens and use `Bearer {raw_token}` |
| `tests/test_console_enroll.py` | AUTH-03 `revoked_at IS NULL` assertion | VERIFIED | `assert token_row.revoked_at is None` at L87 with AUTH-03 comment |
| `docs/operators-guide.md` | §8.1.1 per-sensor migration section | VERIFIED | §8.1.1 replaced; 12 "per-sensor" mentions; `revoke-sensor` referenced; all four D-10/D-11 migration points present |
| `quantum-chaos-enterprise-lab/expected_results_distributed.md` | Per-sensor oracle update | VERIFIED | Authentication block updated to per-sensor model; step table reflects `quirk console enroll` per-sensor token path |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `quirk/dashboard/api/routes/sensor.py POST /sensor/push` | `require_sensor_auth` | `sensor_push_router = APIRouter(dependencies=[Depends(require_sensor_auth)])` | WIRED | L59 and L203 confirmed |
| `quirk/dashboard/api/app.py` | `sensor.sensor_push_router` | `include_router` | WIRED | L118 confirmed |
| `require_sensor_auth` | `sensor_tokens` table | SHA-256 hash lookup + `revoked_at` check | WIRED | `SensorToken.token_hash == hashed` + `token_row.revoked_at is not None` in `sensor_auth.py` |
| `_cmd_revoke_sensor` | `sensor_tokens` table | `SensorToken.revoked_at.is_(None)` filter + stamp | WIRED | L279-293 in `console_cmd.py` confirmed |
| `tests/test_sensor_ingest.py` push tests | `sensor_tokens` | `_seed_token` + `Bearer {raw_token}` headers | WIRED | All 7 updated push tests seed tokens and use per-sensor Bearer headers |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| 8 gating AUTH tests GREEN | `pytest tests/test_sensor_auth_per_sensor.py -q` | 8 passed, 0 failed | PASS |
| 20 combined push/enroll/auth tests GREEN | `pytest tests/test_sensor_auth_per_sensor.py tests/test_sensor_ingest.py tests/test_console_enroll.py -q` | 20 passed, 0 failed | PASS |
| Model + migration + middleware imports clean | `python -c "from quirk.models import SensorToken; from quirk.db import _ADDITIVE_MIGRATIONS; from quirk.dashboard.api.middleware.sensor_auth import require_sensor_auth"` | All imports succeed; assertions pass | PASS |
| Stale "NOT the push credential" wording removed | `grep -v '^[[:space:]]*#' quirk/cli/console_cmd.py \| grep -c "NOT the push credential"` | 0 | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| AUTH-01 | 113-02 | Per-sensor token identifies owning sensor; token-resolved id authoritative | SATISFIED | `require_sensor_auth` sets `request.state.sensor_id`; push handler uses `token_sensor_id`; `test_valid_sensor_token_accepted` and `test_token_identity_is_authoritative` GREEN |
| AUTH-02 | 113-02 | `revoke-sensor` cuts off one sensor without affecting others | SATISFIED | `_cmd_revoke_sensor` isolates by `sensor_id` + `revoked_at.is_(None)`; `test_revoke_isolates_to_one_sensor` confirms sensor-b unaffected |
| AUTH-03 | 113-01, 113-03 | Enrollment issues per-sensor token; SHA-256 hash only; raw never persisted | SATISFIED | `_cmd_enroll` hashes via SHA-256; `test_console_enroll.py` asserts `revoked_at is None` on new row; `_seed_token` stores only hex digest |
| AUTH-04 | 113-01, 113-02, 113-03 | Unknown/revoked token → 401; mismatch → 403; migration documented | SATISFIED | All four branches tested; `test_all_branches_write_audit_rows` confirms audit rows; `docs/operators-guide.md` §8.1.1 documents migration |

**Note:** REQUIREMENTS.md traceability rows still show `pending` for AUTH-01..04 (documentation artifact not updated by the executor). This is a planning-doc bookkeeping gap, not a code gap — all implementations are in the codebase and all tests pass.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None found | — | — | — | — |

No `TBD`, `FIXME`, `XXX`, placeholder text, empty returns, or stale wording found in any of the phase-modified files. The "NOT the push credential" stale message is confirmed absent from non-comment lines in `console_cmd.py`.

---

### Human Verification Required

None. All success criteria are fully automated and verified programmatically:
- Token auth enforced at the router level (grepped and confirmed)
- Revocation isolation confirmed by tests
- Migration documentation text confirmed by grep
- All 20 relevant tests GREEN

---

### Gaps Summary

No gaps. All four phase success criteria are met by live code in the codebase.

---

## Commits Verified

All 10 documented commits exist in git history:

| Commit | Description |
|--------|-------------|
| `48c3bcd` | feat(113-01): add revoked_at column to SensorToken and _V55_SENSOR_TOKEN_COLUMNS migration |
| `4d5dba0` | test(113-01): add AUTH-01..04 gating test scaffold (Wave 0, RED) |
| `8a5c5e1` | feat(113-02): add require_sensor_auth middleware |
| `6757df1` | feat(113-02): split push route onto sensor-auth router + enforce token identity |
| `ebb6665` | feat(113-02): add revoke-sensor subcommand + update D-06 auth gate |
| `f6e6c0d` | fix(113-02): update route-coverage auth gate for require_sensor_auth |
| `91f7e3b` | feat(113-03): update push tests for per-sensor auth; assert revoked_at NULL on enroll |
| `647801e` | feat(113-03): correct enrollment printout and sensor credential semantics (D-11) |
| `139ae89` | docs(113-03): operators-guide per-sensor migration section + distributed lab oracle |
| `039b774` | docs(phase-113): update UAT-SERIES.md |

---

_Verified: 2026-05-26_
_Verifier: Claude (gsd-verifier)_
