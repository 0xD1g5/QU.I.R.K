# Phase 109: Console Ingestion API — Research

**Researched:** 2026-05-25
**Domain:** FastAPI route engineering, SQLAlchemy ORM, sensor payload dedup & auth
**Confidence:** HIGH

---

## Summary

Phase 109 replaces the `_ingest_envelope` stub in `quirk/cli/console_cmd.py` with the
real dedup + persist logic, and adds a new `quirk/dashboard/api/routes/sensor.py` router
that exposes `POST /api/sensor/push` on the existing `quirk serve` FastAPI app. Every
locked decision from `docs/architecture-distributed.md` §6 is fully implementable using
existing primitives — `require_auth`, `get_db`, `IntegrationDelivery`, `safe_str`, and
the `SensorPush` / `Sensor` / `CryptoEndpoint` ORM models that Phase 107 landed.

The most important finding is the **provisioning seam**: `quirk sensor enroll` is
completely console-agnostic — it mints `sensor_id` / `hmac_key` locally and writes
`sensor.yaml` without any network call. There is therefore NO mechanism in Phases 107 or
108 that writes a `sensors` row to the console DB. This must be resolved in this phase.
The recommended approach is (a): a `quirk console enroll` sub-command that writes the
`sensors` + `sensor_tokens` rows and echoes the bearer token the sensor should configure
as `console_api_token`. This is the minimal, architecturally-clean approach, consistent
with the locked "unknown sensor_id → 4xx" rule.

**Primary recommendation:** Add `quirk console enroll` (console-side provisioning) and
`POST /api/sensor/push` (with router-level `require_auth`, body-size cap, replay-window
check, payload_id dedup, and `IntegrationDelivery` audit) as two tightly-scoped plans in
this phase.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Pre-locked from Phase 106 architecture §6 (do NOT re-litigate)
- **(D-07):** Duplicate `payload_id` → HTTP 409.
- **(D-08):** Replay window ±15 min (`pushed_at` vs `received_at`); outside → reject with
  `console_utc` in the response for clock-skew diagnosis.
- **(D-09):** Body-size limit 10 MB → HTTP 413 (FastAPI has no default limit).
- **(D-10):** Accepted `payload_id`s retained indefinitely — no TTL/cleanup in v5.4.
- **(D-11):** Pydantic ingest model uses `extra='ignore'`; `schema_version`/`sensor_version`
  mismatch is warn-only, never blocks ingest (forward/backward compatible).
- **Auth anti-bypass:** ingest route inherits auth at the router level —
  `APIRouter(dependencies=[Depends(require_auth)])`.
- **(D-15 transport carve-out):** ±15-min replay window applies to HTTPS push only;
  air-gap `import-results` skips the window but keeps `payload_id` dedup. Shared
  `_ingest_envelope` honors a `skip_replay_window` flag (already threaded by Phase 108).

#### Auth & HMAC Verification Boundary (v5.4)
- **Primary boundary:** router-level `Depends(require_auth)` bearer token. Unauthenticated
  `POST /api/sensor/push` returns 401 (gating test required — CONSOLE-02).
- **HMAC `X-Sensor-Signature`:** recorded + structurally validated, but full per-sensor-key
  cryptographic verification deferred to v5.5. The `sensors` table has no `hmac_key` column.
- **Unknown sensor_id → 4xx** (audited). Route placement: `quirk/dashboard/api/routes/sensor.py`
  mounted at `/api/sensor`, path `POST /api/sensor/push`.

#### Failure-Mode Ordering & Status Codes
- auth (401) → body-size (413) → parse/version-skew (graceful) → replay-window (422) →
  payload_id dedup (409) → success (200).
- Replay-window violation: HTTP 422 with `console_utc` echoed.
- Body-size: 10 MB cap → 413 (Content-Length guard + streamed read).
- Unknown `sensor_id`: 4xx, audited. Duplicate `payload_id`: 409 (not idempotent-200).

#### Audit Trail (CONSOLE-04)
- Reuse `IntegrationDelivery`, `destination="sensor_push"`, `status` ∈ {ok, failed},
  `error_summary = safe_str(exc)`.
- Write a row on EVERY attempt (success AND every failure mode).
- Extend the `safe_str` AST gate (`test_phase57_invariants.py`-style) to cover the new
  ingestion module.

#### Schema & Version-Skew (CONSOLE-05)
- Pydantic ingest model: `extra='ignore'`; warn-only version-skew (non-blocking).
- On success persist: `sensor_pushes` + update `sensors.last_push_at` + write
  `CryptoEndpoint` rows tagged with `sensor_id` and `segment`.
- Reuse Phase 108's `_ingest_envelope` seam: replace stub with real logic so HTTPS push
  and air-gap import share ONE ingest path.

### Claude's Discretion
- Exact Pydantic model field layout and the `console_utc` timestamp format in error bodies.
- Whether body-size is enforced via middleware, a dependency, or in-handler Content-Length.
- Index/query specifics for the `payload_id` dedup lookup (unique constraint already exists).

### Deferred Ideas (OUT OF SCOPE)
- Full per-sensor-key HMAC cryptographic verification → v5.5.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CONSOLE-01 | Console exposes `POST /api/sensor/push` on the existing FastAPI app | New `sensor.py` router mounted via `app.include_router` in `app.py` |
| CONSOLE-02 | Endpoint requires router-level `Depends(require_auth)`; unauthenticated → 401 | `require_auth` pattern confirmed; test pattern confirmed via `test_api_auth.py` |
| CONSOLE-03 | 413 body-size limit, 409 dedup, ±15-min replay window with `console_utc` | All enforced in `_ingest_envelope` + handler; `SensorPush.payload_id` unique constraint is the 409 seam |
| CONSOLE-04 | Every push attempt writes an `IntegrationDelivery` row via `safe_str()`; AST gate extended | `IntegrationDelivery` + `safe_str` + AST-gate extension pattern all confirmed from Phase 103/104 |
| CONSOLE-05 | Pydantic model uses `extra='ignore'`; version-skew is warn-only | Pydantic v2 `model_config = ConfigDict(extra='ignore')` or class-level `class Config: extra = 'ignore'` |
</phase_requirements>

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Sensor provisioning (write `sensors` + `sensor_tokens`) | Console CLI (`quirk console enroll`) | — | Must happen on the console where the DB lives; sensor side only knows its sensor_id after enrollment |
| Ingest HTTP gate (auth, body-size, replay, dedup) | FastAPI route (`POST /api/sensor/push`) | — | Request-time validation belongs in the route handler |
| Ingest persistence (`sensor_pushes`, `CryptoEndpoint`, `sensors.last_push_at`) | Shared `_ingest_envelope` in `console_cmd.py` | Called from both HTTPS route and air-gap CLI | Single ingest path enforces the D-15 air-gap carve-out cleanly |
| Audit trail | `_ingest_envelope` + route handler (failure modes before ingest call) | — | Audit row needed for pre-ingest failures (413, replay) AND ingest outcomes |
| Body decompression | Route handler (HTTPS) / `console_cmd._cmd_import_results` (air-gap) | — | Decompression already done before `_ingest_envelope` is called in both paths |

---

## CRITICAL FINDING: Console-Side Provisioning Seam

### Problem statement

`quirk sensor enroll` (`sensor_cmd.py` `_cmd_enroll`, L167–220) is **100% local**.
It performs no HTTP call to the console. It:

1. Generates `sensor_id = str(uuid.uuid4())` locally.
2. Generates `hmac_key = secrets.token_bytes(32).hex()` locally.
3. Mints `raw_token = secrets.token_urlsafe(32)` locally.
4. Computes `_token_hash = hashlib.sha256(raw_token.encode()).hexdigest()` locally (but
   comments say: "console-side storage is Phase 109").
5. Writes only `sensor.yaml` on the local machine.
6. Prints the raw token once.

There is no call to the console. Therefore: **after Phase 108, there is no `sensors` row
in the console DB for any sensor**. The Phase 107 schema exists but is unpopulated.

### Implication

If Phase 109 ships `POST /api/sensor/push` with the locked "unknown `sensor_id` → 4xx"
rule but without a provisioning mechanism, **no push can ever succeed** — every push
would fail with 4xx. Phases 110 (merge) and 112 (chaos-lab E2E) would be entirely
blocked.

### Recommendation: Option (a) — `quirk console enroll` CLI command [VERIFIED from codebase analysis]

Add a `quirk console enroll` sub-command to `console_cmd.py`. This is the minimal
approach and is consistent with the architecture:

- The operator runs `quirk console enroll --sensor-id <uuid> --segment <label>
  [--engagement <tag>]` on the console machine (where the DB lives).
- This writes one `sensors` row and one `sensor_tokens` row (SHA-256 hash of the
  enrollment token) to the console DB.
- It prints the generated bearer token (raw, one-time display) for the operator to
  configure as `console_api_token` in the sensor's `sensor.yaml`.

**Why this is better than Option (b) — trust-on-first-push auto-registration:**

Option (b) conflicts directly with the locked decision "unknown sensor_id → 4xx".
Reconciling them would require changing the locked decision, which the CONTEXT.md
forbids. Option (a) requires zero changes to any locked decision and is simpler to
reason about: the console operator explicitly approves each sensor before it can push.

**Minimal implementation for `quirk console enroll`:**

```python
# In console_cmd.py, add "enroll" to the sub-parsers:

def _cmd_enroll(args: argparse.Namespace) -> None:
    """Write sensors + sensor_tokens rows; print bearer token once."""
    from datetime import datetime, timezone
    import hashlib, secrets
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from quirk.models import Sensor, SensorToken
    from quirk.db import init_db

    # sensor_id may be operator-provided (matches sensor.yaml) or generated
    sensor_id = args.sensor_id or str(uuid.uuid4())
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    engine = init_db(args.db or _default_console_db())
    with Session(engine) as db:
        sensor = Sensor(
            sensor_id=sensor_id,
            segment=args.segment,
            engagement=args.engagement,
            enrolled_at=now,
            last_push_at=None,
            expected_cadence_minutes=1440,
            sensor_version=None,
        )
        db.add(sensor)
        db.flush()
        db.add(SensorToken(sensor_id=sensor_id, token_hash=token_hash, created_at=now))
        db.commit()

    print(f"Bearer token (shown once — set as console_api_token in sensor.yaml):\n{raw_token}")
    print(f"sensor_id: {sensor_id}", file=sys.stderr)
```

**Key implementation notes:**
- The `--sensor-id` flag should be required (or auto-generate and print); the operator
  must ensure it matches the `sensor_id` in `sensor.yaml`.
- The raw token becomes the sensor's `Authorization: Bearer <token>` credential, which
  `require_auth` checks via `hmac.compare_digest` against `QUIRK_API_TOKEN`.
- **IMPORTANT:** `require_auth` validates against a SINGLE configured token
  (`QUIRK_API_TOKEN` or `security.api_token`). For v5.4 single-tenant architecture this
  works: one console, one operator-configured token shared across all enrolled sensors.
  This is NOT a per-sensor token check — that would require v5.5 per-sensor key lookup.
- The `sensor_tokens` table stores the SHA-256 hash for audit/provenance; actual auth
  is still the shared `require_auth` mechanism (v5.4 scope).

**Scope call:** The provisioning command is minimal (< 50 lines). It belongs in Plan 01
of this phase, shipped as a prerequisite to the push endpoint. It is small enough not to
be its own phase. The planner should make it Plan 01 (`quirk console enroll`) and Plan 02
(`POST /api/sensor/push` + `_ingest_envelope` replacement).

---

## Standard Stack

### Core (all already in the project — no new dependencies)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `fastapi` | installed | HTTP route, request body, dependencies | Already serves the dashboard |
| `pydantic` | installed | Request body parsing, `extra='ignore'` | Already used in all routes |
| `sqlalchemy` | installed | ORM session, `SensorPush`, `Sensor`, `CryptoEndpoint` | All models in `quirk/models.py` |
| `quirk.util.safe_exc.safe_str` | internal | Exception scrubbing in audit rows | LEAK-01 compliant |
| `quirk.dashboard.api.middleware.auth.require_auth` | internal | Router-level bearer auth | Anti-bypass pattern |
| `quirk.dashboard.api.deps.get_db` | internal | DB session dependency injection | Standard pattern for all routes |
| `quirk.models.IntegrationDelivery` | internal | Audit trail for every push attempt | Phase 103/104/105 pattern |
| `quirk.models.Sensor`, `SensorPush`, `SensorToken` | internal | Phase 107 tables | Schema landed |

**No new pip dependencies required for Phase 109.** [VERIFIED: codebase grep]

### Package Legitimacy Audit

No new packages. This section is N/A — Phase 109 installs no external packages.

---

## Architecture Patterns

### System Architecture Diagram

```
quirk sensor push         quirk console import-results
     │                              │
     │ POST /api/sensor/push        │ _cmd_import_results
     │ zstd body + Bearer + X-Sig   │ reads .qpush file
     ▼                              │ skip_replay_window=True
 require_auth (router level)        │
     │ 401 if unauth                │
     ▼                              ▼
 body-size check (10 MB)     [decompressed envelope dict]
     │ 413 if over                  │
     ▼                              │
 PushEnvelope Pydantic parse ←──────┘
 extra='ignore', version-skew warn
     │
     ├─ replay-window check (HTTPS only; skip if air-gap)
     │    422 + console_utc if outside ±15 min
     │
     ├─ sensor_id lookup (sensors table)
     │    4xx if unknown
     │
     ├─ payload_id dedup (sensor_pushes table UNIQUE constraint)
     │    409 if duplicate
     │
     ▼
 _ingest_envelope (shared path)
     ├─ INSERT sensor_pushes (payload_id, sensor_id, received_at)
     ├─ UPDATE sensors.last_push_at
     ├─ INSERT/UPDATE CryptoEndpoint rows (sensor_id + segment tagged)
     └─ INSERT IntegrationDelivery (destination="sensor_push", status="ok"|"failed")
          └─ safe_str(exc) → error_summary (never raw exception)
     │
     ▼
 200 OK  (or 4xx on any failure — audit row written either way)
```

### Recommended File Changes

```
quirk/
├── cli/
│   └── console_cmd.py          ← Add "enroll" sub-command; replace _ingest_envelope stub
├── dashboard/
│   └── api/
│       ├── app.py              ← include_router(sensor.router, prefix="/api")
│       └── routes/
│           └── sensor.py       ← NEW: APIRouter + POST /sensor/push
tests/
├── test_sensor_ingest.py       ← NEW: 401, 413, 409, 422, 200, audit-row tests
└── scanner/
    └── test_phase57_invariants.py  ← Extend SCANNER_FILES / ingest module list
```

### Pattern 1: Router with router-level auth (no CSRF for sensor push)
**What:** Machine-to-machine endpoint; no browser session, no CSRF needed.
**When to use:** Non-browser callers (sensors) that already carry bearer token.

```python
# Source: quirk/dashboard/api/routes/scan.py L81 (VERIFIED: codebase read)
# and quirk/dashboard/api/routes/schedules.py L33 (VERIFIED: codebase read)

# scan.py uses ONLY require_auth (no require_csrf):
router = APIRouter(dependencies=[Depends(require_auth)])

# schedules.py uses BOTH (browser-facing):
router = APIRouter(dependencies=[Depends(require_auth), Depends(require_csrf)])

# For sensor.py — machine-to-machine; no CSRF:
from quirk.dashboard.api.middleware.auth import require_auth
router = APIRouter(dependencies=[Depends(require_auth)])
```

**Key insight:** `require_csrf` checks for `X-Quirk-Request: 1`. Sensors never send
this header — they are not browser-based. Only include `require_auth` on the sensor
router. The existing `test_all_mutating_routes_have_auth_dependency` gate in
`test_api_auth.py` L303 will verify `require_auth` is present.

### Pattern 2: DB session dependency injection
**What:** `get_db()` generator yields a `Session` per request, closes on exit.
**Source:** `quirk/dashboard/api/deps.py` (VERIFIED: codebase read)

```python
# Source: quirk/dashboard/api/routes/schedules.py L124 (VERIFIED: codebase read)
@router.post("/sensor/push")
def sensor_push(
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    ...
```

### Pattern 3: IntegrationDelivery audit row
**What:** Write one row per push attempt, success or failure. `safe_str(exc)` always.
**Source:** `quirk/ticketing/base.py` L139–151 (VERIFIED: codebase read)

```python
# Canonical pattern (mirrors Phase 103/104/105):
from datetime import datetime, timezone
from quirk.models import IntegrationDelivery
from quirk.util.safe_exc import safe_str

status = "ok"
error_summary = None
try:
    _do_ingest(...)
except Exception as exc:
    status = "failed"
    error_summary = safe_str(exc)   # NEVER str(exc) or repr(exc) — ISEC-02

row = IntegrationDelivery(
    scan_id=scan_id,          # pushed_at or received_at as fallback
    finding_hash=None,        # not used for sensor_push rows
    destination="sensor_push",
    status=status,
    attempted_at=datetime.now(timezone.utc).replace(tzinfo=None),
    error_summary=error_summary,
)
db.add(row)
db.commit()
```

**For pre-ingest failure modes** (413, replay, unknown sensor_id): write the audit row
before raising `HTTPException`. Use a try/except around the commit so an audit-row
failure doesn't mask the original error.

### Pattern 4: Body-size enforcement options
**What:** FastAPI has no default body size limit. Three options for 10 MB cap.

**Option A — Content-Length header check (recommended for Phase 109):**

```python
@router.post("/sensor/push")
async def sensor_push(request: Request, db: Session = Depends(get_db)):
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > 10 * 1024 * 1024:
        # Write audit row for 413
        raise HTTPException(status_code=413, detail="Payload too large (10 MB limit)")
    body = await request.body()
    if len(body) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Payload too large (10 MB limit)")
    ...
```

**Why Content-Length + body read:** The CONTEXT.md says "Content-Length guard + streamed
read; not proxy-only." This means both: (1) fast reject when Content-Length header is
present and over limit, and (2) actual byte count after reading to catch chunked
transfers without a Content-Length header.

**Note:** This endpoint must be `async def` to call `await request.body()`. The route
handler reads the raw bytes (already zstd-compressed), decompresses, then passes the
dict to `_ingest_envelope`. Decompression is NOT done in the route — it is already done
in `_cmd_import_results` for air-gap and should be done in the route for HTTPS push
before calling `_ingest_envelope`.

**Option B — Middleware (not recommended):** Would apply the limit to all routes.
CONTEXT.md says "not proxy-only", implying route-level enforcement is desired. Middleware
is heavier and harder to test in isolation.

### Pattern 5: Replay-window check
**What:** `pushed_at` (from envelope) vs `received_at` (console clock) within ±15 min.
**Source:** `docs/architecture-distributed.md` §6 (VERIFIED: codebase read)

```python
from datetime import datetime, timezone, timedelta

_REPLAY_WINDOW = timedelta(minutes=15)

def _check_replay_window(pushed_at_str: str, received_at: datetime) -> bool:
    """Return True if pushed_at is within ±15 min of received_at."""
    try:
        pushed_at = datetime.fromisoformat(pushed_at_str.replace("Z", "+00:00"))
        pushed_at_naive = pushed_at.replace(tzinfo=None)
        delta = abs(received_at - pushed_at_naive)
        return delta <= _REPLAY_WINDOW
    except (ValueError, TypeError):
        return False  # malformed pushed_at → reject
```

**Rejection response (HTTP 422):**

```python
console_utc = received_at.strftime("%Y-%m-%dT%H:%M:%SZ")
raise HTTPException(
    status_code=422,
    detail={"error": "replay_window_exceeded", "console_utc": console_utc},
)
```

The `console_utc` format matches `pushed_at` format from `sensor_cmd._build_envelope`:
`"%Y-%m-%dT%H:%M:%SZ"`. [VERIFIED: sensor_cmd.py L281]

### Pattern 6: payload_id dedup via unique constraint
**What:** `SensorPush.payload_id` has a `unique=True` SQLAlchemy column constraint
(Phase 107). INSERT a duplicate → `IntegrityError`.
**Source:** `quirk/models.py` SensorPush L329 (VERIFIED: codebase read)

```python
from sqlalchemy.exc import IntegrityError

try:
    db.add(SensorPush(
        payload_id=envelope["payload_id"],
        sensor_id=envelope["sensor_id"],
        received_at=received_at,
    ))
    db.flush()
except IntegrityError:
    db.rollback()
    # Write audit row for 409 before raising
    raise HTTPException(status_code=409, detail="Duplicate payload_id")
```

**Never stringify the IntegrityError** in a response — fixed message only (mirrors
schedules.py L157–161 T-63-16 / LEAK-02 pattern). [VERIFIED: schedules.py L155–161]

### Pattern 7: `_ingest_envelope` replacement
**What:** Replace the Phase 108 stub body with real DB logic. The signature is already
correct and must NOT change.

**Current stub signature** (VERIFIED: `console_cmd.py` L183–186):
```python
def _ingest_envelope(
    envelope: dict,
    config_path: str,
    skip_replay_window: bool = False,
    qpush_sig: str | None = None,
) -> None:
```

**The HTTPS push path does NOT use `config_path`** — it gets a DB session from the
FastAPI `get_db` dependency. The `_ingest_envelope` function is also called from the CLI
(`_cmd_import_results`), which does not have a FastAPI context. This means
`_ingest_envelope` must get a DB session by resolving the DB path itself (using
`_default_db_path()` from `quirk/dashboard/api/deps.py`), OR the function signature
must be extended to accept an optional `db: Session = None` parameter (and create its
own session when not provided).

**Recommended approach:** Extend signature to accept `db: Session | None = None`:

```python
def _ingest_envelope(
    envelope: dict,
    config_path: str,
    skip_replay_window: bool = False,
    qpush_sig: str | None = None,
    db=None,  # Session | None — injected by HTTPS route; created internally for CLI path
) -> None:
    ...
    _own_session = db is None
    if _own_session:
        from quirk.db import init_db
        from quirk.dashboard.api.deps import _default_db_path
        from sqlalchemy.orm import sessionmaker
        engine = init_db(_default_db_path())
        db = sessionmaker(bind=engine)()
    try:
        # ... real logic ...
    finally:
        if _own_session:
            db.close()
```

This keeps backward compatibility with the CLI air-gap path while letting the HTTPS
route inject its own session (avoiding a second connection per request).

### Pattern 8: CryptoEndpoint row persistence from findings
**What:** Each finding dict in `envelope["findings"]` maps to a `CryptoEndpoint` row.
Tag every row with `sensor_id` and `segment` from the envelope.
**Source:** `_endpoint_to_dict` fields in `sensor_cmd.py` L252–269 (VERIFIED: codebase read)

Fields present in the finding dict (from `_endpoint_to_dict`): `host`, `port`,
`protocol`, `scanned_at`, `tls_version`, `cipher_suite`, `cert_subject`, `cert_issuer`,
`cert_sans`, `cert_sig_alg`, `cert_pubkey_alg`, `cert_pubkey_size`, `cert_not_before`,
`cert_not_after`, `sensor_id` (from endpoint, may be None), `segment`.

The Pydantic ingest model uses `extra='ignore'` so unknown fields are dropped. When
persisting `CryptoEndpoint` rows, use the `sensor_id` and `segment` from the **envelope
top level** (authoritative), not from the individual finding dict (which may be None for
older sensor versions — forward-compat).

**DateTime parsing:** `scanned_at`, `cert_not_before`, `cert_not_after` are ISO-8601
strings. Parse with `datetime.fromisoformat(v.replace("Z", "+00:00")).replace(tzinfo=None)`
to get tz-naive UTC datetimes (project convention — Pitfall 1 from schedules RESEARCH).

### Anti-Patterns to Avoid

- **`str(exc)` or `repr(exc)` in responses or audit rows:** Always `safe_str(exc)`.
  The new AST gate will catch violations. [VERIFIED: test_phase57_invariants.py]
- **`require_csrf` on the sensor router:** Sensors are machine-to-machine, never browser.
  Adding CSRF would break all sensor pushes.
- **Per-handler `Depends(require_auth)` instead of router-level:** The anti-bypass rule
  requires router-level auth — future handlers auto-inherit it.
- **Verifying HMAC cryptographically in this phase:** `hmac_key` is not stored in the
  `sensors` table (Phase 107 schema confirmed). Record `qpush_sig`, do not verify.
- **Averaging pre-scored segments:** Not applicable to this phase but record for Phase 110.
- **`db.refresh()` after `db.add()` without `db.flush()`:** Always `db.flush()` before
  `db.refresh()` to materialize the row.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Exception text scrubbing | Custom regex in route handler | `safe_str()` from `quirk.util.safe_exc` | Existing LEAK-01 compliant implementation with AST gate |
| Auth timing-safe compare | `==` token comparison | `require_auth` router dependency | Already implements `hmac.compare_digest` empty-string guard |
| DB session lifecycle | Manual engine/session per request | `Depends(get_db)` | Existing FastAPI dependency; handles close on exit |
| Audit row writing | Inline `db.add(IntegrationDelivery(...))` from scratch | Mirror Phase 103/104 ticketing base pattern | Established pattern ensures every path (success + failure) writes a row |
| Dedup lookup | Manual SELECT + INSERT | `db.add(SensorPush(...))` + catch `IntegrityError` | UNIQUE constraint in schema does the work |
| Body-size middleware | Custom ASGI middleware | Content-Length check + `await request.body()` length | Simpler, testable, route-scoped |

---

## Common Pitfalls

### Pitfall 1: CSRF dependency on machine-to-machine endpoint
**What goes wrong:** Adding `Depends(require_csrf)` to the sensor router causes every
push to return 403 (sensors never send `X-Quirk-Request: 1`).
**Why it happens:** Developers copy the schedules.py pattern which uses BOTH
`require_auth` + `require_csrf`.
**How to avoid:** Sensor push is M2M, not browser. Only `require_auth` at router level.
**Warning signs:** `test_all_mutating_routes_have_auth_dependency` passes, but manual
push returns 403.

### Pitfall 2: Audit row not written for pre-ingest failure modes
**What goes wrong:** CONSOLE-04 requires a row on EVERY attempt, including 413, 422, 409.
If the audit write only happens inside `_ingest_envelope`, failures before that call
(body-size, replay) produce no audit trail.
**Why it happens:** The natural code structure puts the audit in the happy path.
**How to avoid:** The route handler must write an audit row in the `except` block before
re-raising `HTTPException` for each failure mode. Use a helper function.

### Pitfall 3: DateTime tz-naive convention
**What goes wrong:** `datetime.utcnow()` is deprecated; mixing tz-aware and tz-naive
datetimes causes comparison errors.
**How to avoid:** Use `datetime.now(timezone.utc).replace(tzinfo=None)` throughout
(project-wide convention — confirmed in schedules.py `_utcnow_naive()`).

### Pitfall 4: `_ingest_envelope` called from HTTPS route without a DB session
**What goes wrong:** The HTTPS route has a FastAPI `get_db` session; `_ingest_envelope`
as currently stubbed creates its own (Phase 108 stub doesn't open a DB at all). If
Phase 109 gives the function a separate session from the route's session, the
`sensors.last_push_at` update and `sensor_pushes` INSERT happen in a different
transaction than the route might expect.
**How to avoid:** Pass the route's `db` session into `_ingest_envelope` via the extended
`db=None` parameter (Pattern 7 above).

### Pitfall 5: Unknown sensor_id not audited
**What goes wrong:** The locked decision says "unknown sensor_id → 4xx, audited". If the
4xx is raised before the audit row is written, the audit is lost.
**How to avoid:** Write the `IntegrationDelivery` row with `status="failed"` and
`error_summary="unknown_sensor_id"` (via `safe_str`-equivalent fixed string) before
raising `HTTPException`.

### Pitfall 6: `test_all_mutating_routes_have_auth_dependency` gate fails
**What goes wrong:** After adding `sensor.py` to `app.py`, the existing route-introspection
gate (`test_api_auth.py` L303–338) checks all POST/PUT/DELETE/PATCH routes for
`require_auth`. It must find it on the new `POST /api/sensor/push` route.
**Why it happens:** If the route is added to `app.py` but `require_auth` is at handler
level rather than router level, the gate inspects `route.dependencies` (router-level),
not per-handler dependencies.
**How to avoid:** Ensure `require_auth` is in `APIRouter(dependencies=[Depends(require_auth)])`,
not in `@router.post(..., dependencies=[...])`.

### Pitfall 7: IntegrityError rollback not called before audit row
**What goes wrong:** After `IntegrityError` on duplicate `payload_id`, the session is in
an invalid state. `db.add(IntegrationDelivery(...))` and `db.commit()` fail with
"transaction aborted" or similar.
**How to avoid:** Always `db.rollback()` after catching `IntegrityError` before writing
the audit row.

---

## Code Examples

### Route file skeleton
```python
# Source: pattern from quirk/dashboard/api/routes/scan.py L81 and
#         quirk/dashboard/api/routes/schedules.py L33 (VERIFIED: codebase read)
# File: quirk/dashboard/api/routes/sensor.py

from __future__ import annotations
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from quirk.dashboard.api.deps import get_db
from quirk.dashboard.api.middleware.auth import require_auth
from quirk.models import IntegrationDelivery, Sensor, SensorPush
from quirk.util.safe_exc import safe_str

_BODY_LIMIT = 10 * 1024 * 1024   # 10 MB (D-09)
_REPLAY_WINDOW = timedelta(minutes=15)

router = APIRouter(dependencies=[Depends(require_auth)])   # anti-bypass

class PushEnvelope(BaseModel):
    model_config = ConfigDict(extra="ignore")   # D-11: unknown fields dropped

    payload_id: str
    pushed_at: str
    schema_version: str
    sensor_version: str
    sensor_id: str
    segment: str
    findings: list = []

@router.post("/sensor/push")
async def sensor_push(request: Request, db: Session = Depends(get_db)) -> dict:
    received_at = datetime.now(timezone.utc).replace(tzinfo=None)
    ...
```

### Mounting the new router in app.py
```python
# Source: quirk/dashboard/api/app.py L107–115 (VERIFIED: codebase read)
# In create_app(), add after existing router includes:
from quirk.dashboard.api.routes import ..., sensor   # add sensor to import

application.include_router(sensor.router, prefix="/api")
```

### TestClient pattern for 401 gating test
```python
# Source: tests/test_api_auth.py pattern (VERIFIED: codebase read)
# File: tests/test_sensor_ingest.py

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from quirk.dashboard.api.app import create_app
from quirk.dashboard.api.deps import get_db
from quirk.models import Base

def _make_authed_client(monkeypatch, token="test-token"):
    monkeypatch.setenv("QUIRK_API_TOKEN", token)
    engine = create_engine(
        "sqlite:///file::memory:?cache=shared&uri=true",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    return app, TestClient(app, raise_server_exceptions=False)

def test_push_requires_auth(monkeypatch):
    """CONSOLE-02 gating test: POST /api/sensor/push without auth → 401."""
    monkeypatch.setenv("QUIRK_API_TOKEN", "test-token")
    _, client = _make_authed_client(monkeypatch)
    # Note: TestClient sends no auth header by default
    resp = client.post("/api/sensor/push", content=b"data")
    assert resp.status_code == 401
```

### AST gate extension
```python
# Source: tests/scanner/test_phase57_invariants.py (VERIFIED: codebase read)
# Add to SCANNER_FILES list (or create a parallel INGEST_FILES list):

INGEST_FILES = [
    REPO_ROOT / "quirk" / "cli" / "console_cmd.py",
    REPO_ROOT / "quirk" / "dashboard" / "api" / "routes" / "sensor.py",
]

@pytest.mark.parametrize("ingest_file", INGEST_FILES, ids=lambda p: p.name)
def test_ingest_no_raw_exception_stringification(ingest_file):
    """CONSOLE-04: no str(exc) or repr(exc) in ingest path outside comments."""
    src = _strip_comments(ingest_file.read_text())
    # Allow safe_str(exc), but not str(exc) as a standalone call with exc variable
    raw_str_pattern = re.compile(r'\bstr\s*\(\s*exc\b')
    raw_repr_pattern = re.compile(r'\brepr\s*\(\s*exc\b')
    assert not raw_str_pattern.search(src), (
        f"{ingest_file.name}: raw str(exc) found — use safe_str(exc)"
    )
    assert not raw_repr_pattern.search(src), (
        f"{ingest_file.name}: raw repr(exc) found — use safe_str(exc)"
    )
```

---

## Provisioning Gap — Resolved Decision

**Flagged item from CONTEXT.md `<deferred>`:**

> Phase 108 `quirk sensor enroll` is sensor-side and generates `sensor_id`/`hmac_key`
> locally — so how does a `sensors` row come to exist console-side?

**Resolution: Option (a) — `quirk console enroll` CLI command.**

Evidence from codebase (`sensor_cmd.py` L167–220, `console_cmd.py` full file):

1. `quirk sensor enroll` makes NO network call. It writes only `sensor.yaml` locally.
2. `sensor_cmd.py` L196 comment: "token_hash is available for context/logging only —
   **console-side storage is Phase 109**."
3. No other mechanism in Phases 107 or 108 writes `sensors` / `sensor_tokens` rows.
4. Option (b) trust-on-first-push conflicts with the locked "unknown sensor_id → 4xx"
   decision — cannot be adopted without changing a locked decision.

**Recommended workflow for v5.4 enrollment:**

```
Step 1 — Console operator runs:
    quirk console enroll --sensor-id <uuid> --segment dmz [--engagement ClientA]
    → Prints: Bearer token: <raw-token>
    → Writes: sensors row + sensor_tokens row

Step 2 — Sensor operator runs (already done in Phase 108):
    quirk sensor enroll https://console.example.com --segment dmz --api-token <raw-token>
    → Writes: sensor.yaml (sensor_id, hmac_key, console_api_token)

Step 3 — Push (Phase 109):
    quirk sensor push
    → POST /api/sensor/push with Authorization: Bearer <raw-token>
    → Console validates token via require_auth → looks up sensor_id → accepts
```

**Auth linkage clarification:** `require_auth` checks against the single
`QUIRK_API_TOKEN` env var or `security.api_token` config. For v5.4, the console
operator sets `QUIRK_API_TOKEN` to the same value printed by `console enroll`. All
enrolled sensors use this shared bearer token. This is consistent with the single-tenant
architecture — one console, one operator, one engagement at a time.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing) |
| Config file | `pytest.ini` or `pyproject.toml` (existing) |
| Quick run command | `python -m pytest tests/test_sensor_ingest.py -x` |
| Full suite command | `python -m pytest tests/ -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CONSOLE-01 | `POST /api/sensor/push` route registered | smoke | `pytest tests/test_sensor_ingest.py::test_push_endpoint_exists -x` | Wave 0 |
| CONSOLE-02 | Unauthenticated → 401 | unit | `pytest tests/test_sensor_ingest.py::test_push_requires_auth -x` | Wave 0 |
| CONSOLE-03 | Body > 10 MB → 413 | unit | `pytest tests/test_sensor_ingest.py::test_push_413_body_too_large -x` | Wave 0 |
| CONSOLE-03 | Duplicate payload_id → 409 | unit | `pytest tests/test_sensor_ingest.py::test_push_409_duplicate_payload -x` | Wave 0 |
| CONSOLE-03 | Outside ±15 min → 422 + console_utc | unit | `pytest tests/test_sensor_ingest.py::test_push_422_replay_window -x` | Wave 0 |
| CONSOLE-03 | Valid push → 200, sensor_pushes row written | integration | `pytest tests/test_sensor_ingest.py::test_push_200_accepted -x` | Wave 0 |
| CONSOLE-04 | IntegrationDelivery row on every attempt | unit | `pytest tests/test_sensor_ingest.py::test_audit_row_written -x` | Wave 0 |
| CONSOLE-04 | AST gate: no raw `str(exc)` in ingest files | static | `pytest tests/scanner/test_phase57_invariants.py -x` | extend existing |
| CONSOLE-05 | Extra fields dropped (`extra='ignore'`) | unit | `pytest tests/test_sensor_ingest.py::test_extra_fields_ignored -x` | Wave 0 |

### Wave 0 Gaps
- [ ] `tests/test_sensor_ingest.py` — covers CONSOLE-01 through CONSOLE-05
- [ ] Extend `SCANNER_FILES` or add `INGEST_FILES` list in `tests/scanner/test_phase57_invariants.py`

*(Existing test infrastructure and conftest fixtures cover all other infrastructure needs.)*

---

## Environment Availability

Step 2.6: All dependencies are internal Python packages already installed. No external
services, CLIs, or databases beyond the existing SQLite + FastAPI stack.

| Dependency | Required By | Available | Fallback |
|------------|------------|-----------|----------|
| SQLite | DB persistence | ✓ | — |
| FastAPI + pydantic | HTTP route | ✓ | — |
| SQLAlchemy | ORM | ✓ | — |
| zstandard | Body decompression | ✓ (already in requirements) | — |
| `quirk.util.safe_exc` | Exception scrubbing | ✓ | — |

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | `require_auth` router-level `Depends` — timing-safe `hmac.compare_digest` |
| V3 Session Management | no | Stateless API; no session |
| V4 Access Control | yes | Router-level auth prevents any handler-level bypass |
| V5 Input Validation | yes | Pydantic `PushEnvelope` with `extra='ignore'`; body-size cap; UUID format check for sensor_id |
| V6 Cryptography | partial | HMAC-SHA256 signature recorded but not verified in v5.4; no hand-rolled crypto |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Replay attack (stale push) | Spoofing | ±15-min window on `pushed_at` vs `received_at`; `payload_id` dedup → 409 |
| Credential leak in error body | Information Disclosure | `safe_str(exc)` on all exception paths; AST gate |
| Unknown sensor push forged payload | Spoofing | sensor_id lookup → 4xx before any persistence |
| Decompression bomb | DoS | 10 MB body limit before decompression; `console_cmd` already uses `_MAX_DECOMPRESS_BYTES` |
| Auth bypass via new handler | Elevation of Privilege | Router-level `require_auth` (anti-bypass pattern) |
| IntegrityError raw message leak | Information Disclosure | Fixed string on 409 response (mirrors T-63-16 / LEAK-02) |

---

## State of the Art

| Old Approach | Current Approach | Notes |
|--------------|-----------------|-------|
| Per-handler `Depends(require_auth)` | Router-level `APIRouter(dependencies=[...])` | Anti-bypass pattern; Phase 58 HARDEN-API-01 |
| `str(exc)` in error bodies | `safe_str(exc)` | LEAK-01; AST-gated |
| Manual `INSERT` for dedup | `UNIQUE` constraint + `IntegrityError` catch | Cleaner; avoids TOCTOU race |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `require_auth` passes through when `QUIRK_API_TOKEN` is not set (auth disabled) — tests can run without setting a token | Validation Architecture | Tests always pass even when they should be testing auth; confirm `_get_configured_token()` returns `""` when env unset |
| A2 | `QUIRK_API_TOKEN` is the single bearer token for all sensors in v5.4 (single-tenant, one token per console) | Provisioning Seam | If per-sensor token validation is expected, the `require_auth` mechanism would need rework; but this is consistent with locked decisions |

**If this table is empty:** All claims in this research were verified or cited — no user
confirmation needed. Two minor assumptions above are LOW risk given codebase confirmation.

---

## Open Questions

1. **Does `quirk console enroll` need a `--db` path flag?**
   - What we know: `console_cmd.py` currently takes `--config config.yaml`. The DB path
     resolves via `QUIRK_DB_PATH` env var or `_default_db_path()`.
   - What's unclear: Should the enroll command take an explicit `--db` path, or rely on
     the env var / `_default_db_path()` convention?
   - Recommendation: Follow `token_cmd.py` pattern — use `_default_db_path()` with an
     optional `--config` override for the DB path (the same overloading already exists
     in the codebase).

2. **`_ingest_envelope` `config_path` parameter: now unused for real logic?**
   - What we know: The Phase 108 stub accepts `config_path` but the real logic needs a
     DB path, not a YAML config path.
   - What's unclear: Should `config_path` be repurposed as a DB path, or should the
     function add a `db_path` parameter?
   - Recommendation: Extend with optional `db=None` (Session) parameter as described
     in Pattern 7. Keep `config_path` for backward compat (it defaults to `"config.yaml"`
     which is unused in the real path).

---

## Sources

### Primary (HIGH confidence)
- `quirk/cli/sensor_cmd.py` — canonical wire envelope format, `_build_envelope`,
  `_cmd_enroll` confirmed as purely local (no console network call)
- `quirk/cli/console_cmd.py` — Phase 108 `_ingest_envelope` stub signature, full
  `_cmd_import_results` implementation
- `quirk/dashboard/api/app.py` — router mount pattern, `create_app` factory
- `quirk/dashboard/api/routes/scan.py` — `APIRouter(dependencies=[Depends(require_auth)])` pattern
- `quirk/dashboard/api/routes/schedules.py` — `get_db`, `IntegrityError`, CRUD patterns
- `quirk/dashboard/api/middleware/auth.py` — `require_auth` full implementation
- `quirk/dashboard/api/deps.py` — `get_db`, `_default_db_path`
- `quirk/models.py` — `Sensor`, `SensorToken`, `SensorPush`, `IntegrationDelivery`
  field sets confirmed
- `quirk/util/safe_exc.py` — `safe_str` full implementation
- `tests/conftest.py` — `dashboard_client` fixture, `_isolate_quirk_db` pattern
- `tests/test_api_auth.py` — auth test patterns, `test_all_mutating_routes_have_auth_dependency`
- `tests/scanner/test_phase57_invariants.py` — AST/tokenize gate structure
- `quirk/ticketing/base.py` — `IntegrationDelivery` write pattern with `safe_str`
- `docs/architecture-distributed.md` §3, §6 — wire contract field table, enrollment model
- `.planning/REQUIREMENTS.md` — CONSOLE-01..05

### Secondary (MEDIUM confidence)
- `tests/test_schedules_api.py` — schedule API test patterns (additional TestClient usage)
- `tests/test_dashboard_auth_apikey.py` — additional auth test patterns

---

## Metadata

**Confidence breakdown:**
- Provisioning seam resolution: HIGH — confirmed by code inspection; Option (a) is the
  only path consistent with all locked decisions
- Standard stack: HIGH — all libraries in use, no new dependencies
- Architecture patterns: HIGH — all patterns sourced from existing codebase files
- Pitfalls: HIGH — derived from existing code comments, test file patterns, and project
  memory notes
- Test patterns: HIGH — TestClient and fixture patterns confirmed from `test_api_auth.py`
  and `conftest.py`

**Research date:** 2026-05-25
**Valid until:** 2026-06-25 (stable codebase; patterns are internal)
