# Phase 113: Per-Sensor Authentication - Context

**Gathered:** 2026-05-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace the v5.4 shared-token push model (TD-1) with per-sensor opaque tokens.
Today every sensor authenticates to `POST /api/sensor/push` with one **shared**
console token (`security.api_token` / `QUIRK_API_TOKEN`, enforced by router-level
`require_auth`), and the console trusts whatever `sensor_id` the request **body**
claims. The `sensor_tokens` table already exists (Phase 107) and is already
populated at enrollment (SHA-256 hash of a per-sensor token, raw printed once) —
but it is **dormant**: `quirk console enroll` literally prints "This enrollment
token is NOT the push credential." This phase wakes that table up.

**Delivers (AUTH-01–04):**
- The presented Bearer token, hashed to SHA-256, is looked up in `sensor_tokens`
  to **identify which sensor** a push came from.
- Operator revocation of an individual sensor's token (`quirk console
  revoke-sensor <id>`), with no effect on other enrolled sensors.
- Per-sensor token bound to the sensor UUID, raw never persisted (reuses the
  existing table + `token_cmd.py` / `console_cmd.py` SHA-256 hashing pattern).
- Revoked or unknown token → 401 at `POST /api/sensor/push` (gating test);
  backward-compatible, documented migration off the shared-token model.

**Locked constraints (milestone-level):** single-tenant only · additive schema
only (new columns nullable/independent) · no new heavy infra · reuse
`require_auth`, `sensor_tokens`, `IntegrationDelivery`, `safe_str()`, SSRF
allowlist · OS-agnostic sensor↔console wire contract unchanged.

</domain>

<decisions>
## Implementation Decisions

### Push auth integration
- **D-01:** Add a dedicated `require_sensor_auth` dependency for the
  `POST /api/sensor/push` route. It reads the presented Bearer token,
  SHA-256-hashes it, looks the hash up in `sensor_tokens`, and resolves the
  owning sensor (attach to `request.state` for the handler). This **replaces**
  the shared `require_auth` on the push route specifically.
- **D-02:** Operator-facing routes stay on the existing shared/operator
  `require_auth` — `GET /api/sensor/registry`, the merge routes, and all other
  dashboard routes are operator surfaces, not sensors. Do NOT route those
  through `require_sensor_auth`. Keep M2M sensor auth and operator auth as
  cleanly separated dependencies.
- **D-03:** Reuse the existing timing-safe comparison discipline from
  `middleware/auth.py` (hmac.compare_digest semantics); never log raw tokens
  (mirror T-102-09).

### Token ↔ body identity binding
- **D-04:** The token is **authoritative** for sensor identity. The
  `sensor_id` resolved from the token's `sensor_tokens` row is the source of
  truth — this closes the v5.4 "trust the body's `sensor_id`" impersonation gap.
- **D-05:** If `envelope.sensor_id` disagrees with the token-resolved
  sensor_id → reject with **403** + `IntegrationDelivery` audit row (a valid
  token trying to act as a different sensor). Distinct from the unknown/revoked
  case below.

### Revocation semantics
- **D-06:** Soft revoke via an **additive nullable `revoked_at` column** on
  `sensor_tokens` (fits additive-only constraint; preserves audit history).
  `quirk console revoke-sensor <id>` stamps `revoked_at` on the sensor's
  token row(s). `require_sensor_auth` rejects any token whose row has
  `revoked_at` set. The sensor row + its push history are retained (registry/audit).
- **D-07:** Revocation affects only the target sensor — every other enrolled
  sensor keeps pushing unchanged (AUTH-02). One active token per sensor in v5.5.
- **D-08:** No token-reissue path in v5.5. To bring a revoked segment back
  online, the operator **re-enrolls as a fresh sensor** (`quirk console enroll`
  → new sensor_id UUID + new token), matching the existing enroll PK /
  IntegrityError behavior. (`reissue-sensor` is explicitly out of scope —
  deferred.)

### Failure ladder (status codes)
- **D-09:** Unknown token (no matching hash) → **401**. Revoked token
  (`revoked_at` set) → **401**. These two match the AUTH-04 gating-test wording
  ("revoked or unknown per-sensor token returns 401"). Body/token sensor_id
  mismatch → **403** (D-05). Every branch writes an `IntegrationDelivery`
  audit row, consistent with the Phase 109 §6 failure ladder, using fixed
  strings / `safe_str()` (never stringify a raw token or exception into audit).

### Migration off the shared-token model
- **D-10:** **Clean documented cutover** — no dual-accept code path. The
  per-sensor token is required at `POST /api/sensor/push`. Operators re-point
  each sensor's `console_api_token` (in sensor config, sent as
  `Authorization: Bearer` at `sensor_cmd.py:600`) to its **per-sensor
  enrollment token** (already minted at enroll time). Sensors already enrolled
  have a token hash on file; they only re-enroll if the raw token was lost.
- **D-11:** The sensor-side credential field semantics change: the value the
  sensor presents is now its **own** per-sensor token, not the shared console
  token. Document the migration steps (re-point credential; revoke + re-enroll
  if raw lost) in `docs/operators-guide.md`. The wire contract /
  `Authorization: Bearer` mechanism is unchanged (OS-agnostic constraint held).

### Claude's Discretion
- Exact name/signature of the `require_sensor_auth` dependency and where the
  resolved sensor is attached (`request.state` vs return value) — planner's call.
- Whether `revoke-sensor` also accepts a `--reason` or prints the revoked
  sensor's segment for operator confirmation — nice-to-have, not required.
- Whether to add a lightweight `quirk console list-sensors` convenience CLI
  (the `GET /api/sensor/registry` endpoint already lists sensors; CLI is
  optional sugar, not required by AUTH-02).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Distributed architecture & wire contract
- `docs/architecture-distributed.md` — sensor/console split, the locked wire
  contract and forbidden-additions that the auth change must not violate.
- `quantum-chaos-enterprise-lab/expected_results_distributed.md` — distributed
  e2e oracle; per-sensor auth must keep `lab.sh distributed e2e` green.

### Operator-facing migration target
- `docs/operators-guide.md` — where the backward-compatible migration off the
  shared-token model (D-10/D-11) MUST be documented (AUTH-04).

### Existing auth/token code to reuse (not reinvent)
- `quirk/dashboard/api/middleware/auth.py` — `require_auth`, `_get_configured_token`,
  timing-safe compare; pattern for the new `require_sensor_auth`.
- `quirk/dashboard/api/routes/sensor.py` — `POST /api/sensor/push` (router-level
  `require_auth` at L55, §6 failure ladder with `IntegrationDelivery` audit) +
  `GET /api/sensor/registry`. The push route's auth dependency is the seam.
- `quirk/cli/console_cmd.py` — `_cmd_enroll` (SHA-256 hashing at ~L163-164,
  `sensor_tokens` insert), `_ingest_envelope`, `UnknownSensorError`. Add
  `revoke-sensor` subcommand here.
- `quirk/cli/token_cmd.py` — `secrets.token_urlsafe(32)` + SHA-256 hashing
  pattern to mirror.
- `quirk/models.py` — `Sensor` (L269), `SensorToken` (L291, `sensor_tokens`,
  add `revoked_at`), `SensorPush` (L315).
- `quirk/cli/sensor_cmd.py` — sensor-side push: `console_api_token` config +
  `Authorization: Bearer` header (L596-611). Migration target for D-11.

### Requirements
- `.planning/REQUIREMENTS.md` §"Per-Sensor Authentication (AUTH)" — AUTH-01–04.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `sensor_tokens` table + enroll-time SHA-256 hashing already exist (Phase 107);
  this phase activates them rather than building new storage.
- `IntegrationDelivery` audit table + the Phase 109 §6 failure-ladder pattern
  already wrap every push branch — extend it for the new 401/403 branches.
- `secrets.token_urlsafe(32)` + `hashlib.sha256(...).hexdigest()` pattern in
  `console_cmd._cmd_enroll` / `token_cmd.py`.
- `hmac.compare_digest` timing-safe compare discipline in `middleware/auth.py`.

### Established Patterns
- **Router-level `Depends(require_auth)`** (`sensor.py:55`) — no per-handler
  auth bypass; new sensor auth must hold the same "never reaches business logic
  on 401" guarantee.
- **Additive, nullable columns only** — `revoked_at` must be nullable so
  existing single-host and v5.4 distributed DBs migrate cleanly.
- **Fixed-string / `safe_str()` audit error summaries** — never leak a raw
  token or stringified exception into `IntegrationDelivery`.

### Integration Points
- Push route auth dependency swap: `require_auth` → `require_sensor_auth` on
  `POST /api/sensor/push` only.
- New `revoked_at` column on `SensorToken` model + DB migration path.
- New `quirk console revoke-sensor <id>` subcommand in `console_cmd.run_console`.
- Sensor-side credential semantics (`sensor_cmd.py` `console_api_token`) +
  `docs/operators-guide.md` migration section.

</code_context>

<specifics>
## Specific Ideas

- The AUTH-04 gating test should assert: a push presenting (a) an unknown token
  and (b) a revoked token both return **401** at `POST /api/sensor/push`; a
  valid token with a mismatched body `sensor_id` returns **403**; a valid
  non-revoked token for the matching sensor returns 200. All four write an
  `IntegrationDelivery` audit row.

</specifics>

<deferred>
## Deferred Ideas

- **`quirk console reissue-sensor <id>`** (mint a new token for the same
  sensor_id without re-enrolling) — operator convenience beyond AUTH-02's
  revoke ask. Revisit if re-enroll churn proves painful.
- **Dual-accept grace window** (accept shared OR per-sensor token during a
  transition) — explicitly rejected in favor of a clean cutover (D-10). Note
  for the v5.6 public-repo/launch conversation only if a live fleet needs it.
- **HMAC payload signing** (`X-Sensor-Signature` crypto verification) — the
  `hmac_key` column is still absent (T-109-11 deferred from v5.4); structural
  validation only. Separate concern from token auth; not in this phase.

</deferred>

---

*Phase: 113-per-sensor-authentication*
*Context gathered: 2026-05-26*
