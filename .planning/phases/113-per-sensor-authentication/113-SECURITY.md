---
phase: 113-per-sensor-authentication
audit_date: 2026-05-27
auditor: gsd-security-auditor
asvs_level: 1
block_on: high
threats_open: 0
threats_closed: 10
threats_accepted: 3
---

# Phase 113 Security Audit — Per-Sensor Authentication

## Summary

**All declared mitigations verified in shipped code. No open threats.**

| Metric | Value |
|--------|-------|
| Threats in register | 13 (10 mitigate + 3 accept) |
| Threats closed | 10 |
| Threats accepted (documented) | 3 |
| Threats open (blockers) | 0 |
| Unregistered flags | 0 |

---

## Threat Verification

### Plan 113-01 Threats

| Threat ID | Category | Disposition | Status | Evidence |
|-----------|----------|-------------|--------|----------|
| T-113-01 | Tampering | mitigate | CLOSED | `quirk/db.py:131–134` — `_V55_SENSOR_TOKEN_COLUMNS = (("revoked_at", "DATETIME"),)` registered at `db.py:193` as `("sensor_tokens", _V55_SENSOR_TOKEN_COLUMNS)` in `_ADDITIVE_MIGRATIONS`; `_ensure_columns` (db.py:138–168) skips existing columns via inspector (idempotent); no destructive DDL. |
| T-113-02 | Information disclosure | mitigate | CLOSED | `tests/test_sensor_auth_per_sensor.py` — `_seed_token` helper mints `secrets.token_urlsafe(32)`, stores only `sha256(raw).hexdigest()` in `SensorToken.token_hash`; raw token held in local variable only. Mirrors enroll path (console_cmd.py:199–200). |
| T-113-SC (01) | Tampering | accept | CLOSED | No new packages introduced in Plan 01. Accepted per plan. |

### Plan 113-02 Threats

| Threat ID | Category | Disposition | Status | Evidence |
|-----------|----------|-------------|--------|----------|
| T-113-03 | Spoofing | mitigate | CLOSED | `quirk/dashboard/api/routes/sensor.py:485–494` — `token_sensor_id = request.state.sensor_id` (D-04, token authoritative); `if envelope.sensor_id != token_sensor_id:` → `_audit(..., "sensor_id_mismatch")` + `HTTPException(403)` (D-05). WR-01 (use token-resolved id in success/ingest path) is satisfied: the sensor lookup at line 486 and the mismatch check at line 492 both key off `token_sensor_id`, not `envelope.sensor_id`. |
| T-113-04 | Elevation of privilege | mitigate | CLOSED | `quirk/dashboard/api/middleware/sensor_auth.py:93–94` — `if token_row.revoked_at is not None: _audit_and_raise(401, "revoked_sensor_token", ...)`. Revocation CLI at `console_cmd.py:297–316` filters `SensorToken.revoked_at.is_(None)` (active rows only), stamps `now` on each, commits — isolation is per-sensor_id filter. WR-04 (idempotent revoke-sensor) noted as non-blocking follow-up; the revoke path correctly exits 1 when no active token exists (console_cmd.py:306–311), which is the safe-fail behavior. The revoked_at check in require_sensor_auth is the enforcement gate for T-113-04 and remains closed regardless of WR-04's non-blocking status. |
| T-113-05 | Information disclosure | mitigate | CLOSED | `quirk/dashboard/api/middleware/sensor_auth.py:79` — sole use of `credentials.credentials` is `hashlib.sha256(credentials.credentials.encode()).hexdigest()`. No `logger.*` call in the file references `credentials.credentials`. Module docstring explicitly notes "Raw token value NEVER logged (T-113-05 / T-102-09)". |
| T-113-06 | Spoofing | mitigate | CLOSED | `quirk/dashboard/api/middleware/sensor_auth.py:87` — `if not hmac.compare_digest(hashed, token_row.token_hash):` — constant-time compare on two SHA-256 hex strings (equal length, 64 chars). |
| T-113-07 | Elevation of privilege | mitigate | CLOSED | `quirk/dashboard/api/routes/sensor.py:62–63` — `router = APIRouter(dependencies=[Depends(require_auth)])` (operator routes); `sensor_push_router = APIRouter(dependencies=[Depends(require_sensor_auth)])` (push only). `GET /sensor/registry` at line 282 is decorated `@router.get(...)` (operator auth). `quirk/dashboard/api/app.py:117–118` registers both routers — `sensor.router` then `sensor.sensor_push_router`. |
| T-113-08 | Spoofing | mitigate | CLOSED | `quirk/dashboard/api/routes/sensor.py:367` — `@sensor_push_router.post("/sensor/push")` — push route is exclusively under `require_sensor_auth`; no parallel `@router.post("/sensor/push")` exists. No dual-accept. |
| T-113-SC (02) | Tampering | accept | CLOSED | No new packages introduced in Plan 02. Accepted per plan. |

### Plan 113-03 Threats

| Threat ID | Category | Disposition | Status | Evidence |
|-----------|----------|-------------|--------|----------|
| T-113-09 | Information disclosure | mitigate | CLOSED | `quirk/cli/console_cmd.py:252–258` — printout reads "Bearer token (copy now — shown once, never recoverable)" followed by the raw token; NOTE block states token IS the per-sensor push credential, lost → revoke + re-enroll (D-08). `SensorToken` stores only `token_hash` (SHA-256 hex); raw token not written to DB. `console_cmd.py:226–233` writes `SensorToken(token_hash=token_hash, ...)` with no `revoked_at` field (defaults to NULL, column nullable). |
| T-113-10 | Denial of service | mitigate | CLOSED | `docs/operators-guide.md:471–508` — §8.1.1 "v5.5 per-sensor authentication model (migration from v5.4)" documents: (1) what changed, (2) per-sensor migration steps (set `console_api_token` to enrollment token), (3) lost token recovery via `revoke-sensor` + re-enroll, (4) QUIRK_API_TOKEN unaffected. References `revoke-sensor` explicitly. States "no dual-accept period (D-10)". |
| T-113-SC (03) | Tampering | accept | CLOSED | No new packages introduced in Plan 03. Accepted per plan. |

---

## WR-01..04 Follow-up Impact Assessment

The code review for Phase 113 left four non-blocking follow-ups (WR-01 through WR-04). Their impact on threat closure status is assessed below.

| WR Tag | Description | Affected Threat | Impact on Closure |
|--------|-------------|-----------------|-------------------|
| WR-01 | Fail-closed fallback on `request.state.sensor_id` if attribute missing | T-113-03 | None — `require_sensor_auth` always sets `request.state.sensor_id` on the success path (sensor_auth.py:97); a missing attribute would indicate middleware was bypassed entirely, not a mismatch. T-113-03 CLOSED. |
| WR-02 | Use token-resolved id in success response and ingest | T-113-03 | None — the 200 response at sensor.py:564 returns `envelope.sensor_id` (the body field), but the sensor lookup and mismatch check (lines 486/492) are already keyed off `token_sensor_id`. An envelope that passes the mismatch check has `envelope.sensor_id == token_sensor_id` by invariant, so echoing the envelope value is semantically equivalent. T-113-03 CLOSED. |
| WR-03 | `db.rollback()` before audit on `_audit_and_raise` commit failure | T-113-04, T-113-05 | Non-blocking audit plumbing; does not weaken revocation enforcement or token-logging avoidance. Both threats CLOSED. |
| WR-04 | Idempotent `revoke-sensor` (currently exits 1 when no active token) | T-113-04 | The current behavior (exit 1 on no-op revoke) is a usability gap, not a security regression. The enforcement gate — `revoked_at is not None` check in `require_sensor_auth` — is unaffected. T-113-04 CLOSED. |

---

## Unregistered Flags

None. All `## Threat Flags` sections in the three SUMMARY files explicitly state "None."

---

## Accepted Risks Log

| ID | Plan | Category | Rationale |
|----|------|----------|-----------|
| T-113-SC (01) | 113-01 | Supply chain / Tampering | No new npm or pip packages introduced. No dependency surface change. |
| T-113-SC (02) | 113-02 | Supply chain / Tampering | No new npm or pip packages introduced. No dependency surface change. |
| T-113-SC (03) | 113-03 | Supply chain / Tampering | No new npm or pip packages introduced. No dependency surface change. |
