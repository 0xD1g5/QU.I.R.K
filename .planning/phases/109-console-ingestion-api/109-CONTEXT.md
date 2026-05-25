# Phase 109: Console Ingestion API - Context

**Gathered:** 2026-05-25
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase adds the **console-side ingestion endpoint** that securely accepts pushed sensor
payloads: `POST /api/sensor/push` on the existing `quirk serve` FastAPI app. It enforces the
locked security contract from `docs/architecture-distributed.md` §6 — router-level
authentication (no bypass), payload_id replay dedup (409), a ±15-minute clock-skew window, a
body-size cap (413), graceful version-skew handling, and a full `IntegrationDelivery` audit
trail with `safe_str()`-scrubbed exception text. On a valid push it persists the dedup record,
updates `sensors.last_push_at`, and writes `CryptoEndpoint` rows tagged with `sensor_id`/`segment`
— reusing the single ingest path that Phase 108's `_ingest_envelope` stub left as a seam.

**Out of scope (downstream):** cross-sensor merge & unified scoring (Phase 110), dashboard
sensor awareness (Phase 111). Console-side sensor *provisioning* (writing `sensors` /
`sensor_tokens` rows) is out of the push endpoint's scope — see the flagged research item below.

</domain>

<decisions>
## Implementation Decisions

### Pre-locked from Phase 106 architecture §6 (carried forward — do NOT re-litigate)
- **(D-07):** Duplicate `payload_id` → **HTTP 409**.
- **(D-08):** Replay window **±15 min** (`pushed_at` vs `received_at`); outside → reject with
  `console_utc` in the response for clock-skew diagnosis.
- **(D-09):** Body-size limit **10 MB** → **HTTP 413** (FastAPI has no default limit).
- **(D-10):** Accepted `payload_id`s retained **indefinitely** — no TTL/cleanup in v5.4.
- **(D-11):** Pydantic ingest model uses **`extra='ignore'`**; `schema_version`/`sensor_version`
  mismatch is **warn-only**, never blocks ingest (forward/backward compatible).
- **Auth anti-bypass:** ingest route inherits auth at the **router** level —
  `APIRouter(dependencies=[Depends(require_auth)])` (reuses `quirk/dashboard/api/middleware/auth.py`,
  `require_auth` @ ~L34, timing-safe `hmac.compare_digest`).
- **(D-15 transport carve-out):** the ±15-min replay window applies to **HTTPS push only**;
  air-gap `import-results` skips the window but keeps `payload_id` dedup. The shared
  `_ingest_envelope` honors a `skip_replay_window` flag (already threaded by Phase 108).

### Auth & HMAC Verification Boundary (v5.4)
- **Primary boundary:** router-level `Depends(require_auth)` bearer token. An unauthenticated
  `POST /api/sensor/push` returns **401** (gating test is part of phase verification — CONSOLE-02).
- **HMAC `X-Sensor-Signature`:** **recorded + structurally validated** (header present, well-formed
  `hmac-sha256=<hex>`), but **full per-sensor-key cryptographic verification is deferred to v5.5.**
  Rationale: the `sensors` table (closed Phase 107) has **no `hmac_key` column**, and adding one is
  out of this phase's push scope. The signature value is carried into the audit/verification seam
  (the `qpush_sig` parameter Phase 108 already forwards) for v5.5 to verify.
- **Console-side provisioning out of scope:** the push endpoint assumes the `sensor_id` row already
  exists. A push with an **unknown `sensor_id` → 4xx** (audited). See flagged research item.
- **Route placement:** new `quirk/dashboard/api/routes/sensor.py` with its own
  `APIRouter(dependencies=[Depends(require_auth)])`, mounted at `/api/sensor`
  (path `POST /api/sensor/push`).

### Failure-Mode Ordering & Status Codes
- **Check order:** auth (401) → body-size (413) → parse / version-skew (graceful) →
  replay-window (422) → `payload_id` dedup (409) → success (200).
- **Replay-window violation:** **HTTP 422** with `console_utc` echoed in the body.
- **Body-size:** 10 MB cap → **413** (Content-Length guard + streamed read; not proxy-only).
- **Unknown `sensor_id`:** 4xx, audited. Duplicate `payload_id`: **409** (not idempotent-200).

### Audit Trail (CONSOLE-04)
- **Reuse `IntegrationDelivery`** (`quirk/models.py` ~L251): `destination="sensor_push"`,
  `status` ∈ {ok, failed}, `error_summary = safe_str(exc)` (never raw exception).
- **Write a row on EVERY attempt** — success AND every failure mode (401 / 413 / 409 / replay /
  parse error).
- **`scan_id`** = the pushed payload's scan/session timestamp; fall back to `received_at` if absent.
- **Extend the existing `safe_str` AST gate** (the `test_phase57_invariants`-style tokenize test)
  to cover the new ingestion module — no raw exception text may reach a response or audit row.

### Schema & Version-Skew (CONSOLE-05)
- Pydantic ingest model: **`extra='ignore'`**; **warn-only** version-skew (non-blocking).
- **On success persist:** `sensor_pushes` (payload_id dedup row) + update `sensors.last_push_at`
  + write `CryptoEndpoint` rows tagged with `sensor_id` and `segment`.
- **Reuse Phase 108's `_ingest_envelope` seam:** replace the stub body with the real dedup +
  persist logic so HTTPS push and air-gap `console import-results` share **one** ingest path.

### Claude's Discretion
- Exact Pydantic model field layout and the `console_utc` timestamp format in error bodies.
- Whether body-size is enforced via FastAPI middleware, a dependency, or in-handler Content-Length.
- Index/query specifics for the `payload_id` dedup lookup (the unique constraint already exists).

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `quirk/dashboard/api/middleware/auth.py::require_auth` (~L34) — router-level dependency,
  timing-safe `hmac.compare_digest`. The anti-bypass pattern: declare on `APIRouter(dependencies=[...])`.
- `quirk/util/safe_exc.py::safe_str` — scrubs exception text before it reaches responses/audit.
- `quirk/models.py::IntegrationDelivery` (~L251) — shared delivery audit log (Phases 101/103/104/105).
- `quirk/models.py::Sensor / SensorToken / SensorPush` (Phase 107) — `sensor_pushes.payload_id`
  is `unique` (the 409 seam); `sensors.last_push_at` nullable until first push.
- `quirk/cli/console_cmd.py::_ingest_envelope(envelope, config_path, skip_replay_window=...)` —
  Phase 108 stub to replace with the real ingest logic (shared push + air-gap path).
- Existing route modules under `quirk/dashboard/api/routes/` (scan.py, schedules.py, etc.) —
  the `APIRouter` registration + app-mount pattern to mirror (`quirk/dashboard/api/app.py`).

### Established Patterns
- AST/tokenize invariant gates live in `tests/scanner/test_phase57_invariants.py` (the safe_str /
  verify=False style). Extend, don't reinvent.
- Routers are registered/mounted in `quirk/dashboard/api/app.py`.

### Integration Points
- New route mounted on the same FastAPI app served by `quirk serve` (`quirk/dashboard/server.py`).
- The ingest path is shared with `quirk console import-results` (Phase 108) via `_ingest_envelope`.

</code_context>

<specifics>
## Specific Ideas

- The unauthenticated-401 gating test (CONSOLE-02) is a phase-verification must — it proves the
  router-level auth cannot be bypassed by a newly added handler.
- Push and air-gap import MUST flow through one `_ingest_envelope` — no parallel ingest logic.

</specifics>

<deferred>
## Deferred Ideas

- **Full per-sensor-key HMAC cryptographic verification → v5.5** (requires an `hmac_key` storage
  column on `sensors`, which Phase 107 did not add).

## FLAGGED FOR RESEARCH/PLANNING (resolve before or during planning)

- **Console-side `sensors`-row provisioning seam.** This phase accepts that provisioning is out of
  the push endpoint's scope AND that an unknown `sensor_id` returns 4xx. But Phase 108 `quirk sensor
  enroll` is sensor-side and generates `sensor_id`/`hmac_key` locally — so **how does a `sensors`
  row come to exist console-side?** The researcher/planner MUST determine the actual provisioning
  path in v5.4 and either:
  (a) document an operator/console enrollment step (e.g. a `quirk console enroll` seam) that writes
      the `sensors` + `sensor_tokens` rows and emits the token the sensor consumes, OR
  (b) adopt trust-on-first-authenticated-push auto-registration (bearer auth already gates it), OR
  (c) surface this as a genuine milestone gap to the user.
  Phase 110 (merge) and Phase 112 (chaos-lab E2E) cannot work end-to-end until this is resolved.
  Do not silently assume rows exist — pick and document the mechanism.

</deferred>
