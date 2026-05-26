# Phase 113: Per-Sensor Authentication - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-26
**Phase:** 113-per-sensor-authentication
**Areas discussed:** Push auth integration, Token↔body identity, Revocation semantics, Migration off shared token

---

## Push auth integration

| Option | Description | Selected |
|--------|-------------|----------|
| Dedicated require_sensor_auth | New dependency on POST /sensor/push: hash bearer token, look up in sensor_tokens, resolve sensor. Operator routes keep shared require_auth. | ✓ |
| Layer both (shared + per-sensor) | Sensor presents both shared console token and per-sensor token. | |
| Extend require_auth in place | Single dependency accepts shared OR per-sensor token across all routes. | |

**User's choice:** Dedicated require_sensor_auth
**Notes:** Cleanest separation of M2M sensor auth vs operator auth; GET /sensor/registry + merge stay on operator/shared require_auth.

---

## Token ↔ body identity

| Option | Description | Selected |
|--------|-------------|----------|
| Token authoritative; reject mismatch | Token's resolved sensor_id is source of truth; body mismatch → reject + audit. | ✓ |
| Token authoritative; silently override body | Overwrite body sensor_id, no rejection. | |
| Keep trusting body sensor_id | Token only gates access; body still names sensor. | |

**User's choice:** Token authoritative; reject mismatch
**Notes:** Closes the v5.4 "trust the body" impersonation gap. Mismatch returns 403 (see status-code follow-up).

---

## Revocation semantics

| Option | Description | Selected |
|--------|-------------|----------|
| Additive revoked_at column, soft revoke | Nullable revoked_at on sensor_tokens; revoke-sensor stamps it; auth rejects revoked. | ✓ |
| Hard-delete the sensor_tokens row | revoke-sensor deletes the token row. | |

**User's choice:** Additive revoked_at column, soft revoke
**Notes:** Preserves audit history, fits additive-only constraint, leaves other sensors untouched (AUTH-02).

---

## Migration off shared token

| Option | Description | Selected |
|--------|-------------|----------|
| Clean documented cutover | Per-sensor token required; operators re-point each sensor's credential to its per-sensor token; documented in operators-guide. No dual-accept code. | ✓ |
| Dual-accept grace window | Accept shared OR per-sensor token during transition; remove in v5.6. | |

**User's choice:** Clean documented cutover
**Notes:** Avoids keeping the weak shared path alive. Already-enrolled sensors have a token hash on file; re-enroll only if raw was lost.

---

## Follow-up: mismatch status code

| Option | Description | Selected |
|--------|-------------|----------|
| 403 for mismatch, 401 for unknown/revoked | 401 = no/invalid/revoked credential (matches AUTH-04 gating wording); 403 = valid token acting as a different sensor. | ✓ |
| 401 for everything | Uniform non-disclosure. | |

**User's choice:** 403 for mismatch, 401 for unknown/revoked

---

## Follow-up: re-enrollment after revoke

| Option | Description | Selected |
|--------|-------------|----------|
| Re-enroll as a fresh sensor | revoke soft-revokes token; resume via quirk console enroll → new sensor_id + token. | ✓ |
| Add a reissue-token path | reissue-sensor keeps same sensor_id, mints new token. | |

**User's choice:** Re-enroll as a fresh sensor
**Notes:** Matches existing enroll PK/IntegrityError behavior; reissue path deferred.

---

## Claude's Discretion

- Name/signature of `require_sensor_auth` and where the resolved sensor is attached (request.state vs return).
- Whether `revoke-sensor` accepts `--reason` / prints segment for confirmation.
- Optional `quirk console list-sensors` CLI sugar (registry endpoint already lists sensors).

## Deferred Ideas

- `quirk console reissue-sensor <id>` — same-UUID token reissue (beyond AUTH-02).
- Dual-accept grace window — rejected in favor of clean cutover; note for v5.6 launch only.
- HMAC payload signing (`X-Sensor-Signature` crypto verify) — `hmac_key` column still absent (T-109-11); separate concern.
