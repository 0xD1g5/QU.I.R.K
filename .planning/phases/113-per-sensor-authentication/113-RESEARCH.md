# Phase 113: Per-Sensor Authentication - Research

**Researched:** 2026-05-26
**Domain:** FastAPI auth dependencies, SQLite additive migration, Python argparse subcommand dispatch
**Confidence:** HIGH (all findings verified directly from codebase source)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Add `require_sensor_auth` dependency for `POST /api/sensor/push`. Reads Bearer token, SHA-256-hashes it, looks up in `sensor_tokens`, resolves owning sensor (attach to `request.state`). Replaces shared `require_auth` on push route only.
- **D-02:** Operator-facing routes (`GET /api/sensor/registry`, merge routes, dashboard) stay on existing `require_auth`. Keep M2M sensor auth and operator auth cleanly separated.
- **D-03:** Reuse timing-safe comparison discipline from `middleware/auth.py` (hmac.compare_digest semantics); never log raw tokens (mirror T-102-09).
- **D-04:** Token is authoritative for sensor identity. `sensor_id` resolved from `sensor_tokens` row is source of truth — closes the v5.4 "trust the body's sensor_id" impersonation gap.
- **D-05:** If `envelope.sensor_id` disagrees with token-resolved sensor_id → reject with 403 + `IntegrationDelivery` audit row.
- **D-06:** Soft revoke via additive nullable `revoked_at` column on `sensor_tokens`. `quirk console revoke-sensor <id>` stamps `revoked_at`. `require_sensor_auth` rejects any token whose row has `revoked_at` set. Sensor row + push history retained.
- **D-07:** Revocation affects only the target sensor — every other enrolled sensor keeps pushing unchanged. One active token per sensor in v5.5.
- **D-08:** No token-reissue path in v5.5. To bring a revoked segment back online: re-enroll as a fresh sensor. (`reissue-sensor` deferred.)
- **D-09:** Unknown token → 401. Revoked token → 401. Body/token sensor_id mismatch → 403. Every branch writes an `IntegrationDelivery` audit row using fixed strings / `safe_str()`.
- **D-10:** Clean documented cutover — no dual-accept code path. Operators re-point each sensor's `console_api_token` in `sensor.yaml` to its per-sensor enrollment token.
- **D-11:** Sensor-side credential field semantics change: value the sensor presents is now its own per-sensor token, not the shared console token. Document migration in `docs/operators-guide.md`.

### Claude's Discretion

- Exact name/signature of `require_sensor_auth` dependency and where the resolved sensor is attached (`request.state` vs return value).
- Whether `revoke-sensor` also accepts a `--reason` or prints the revoked sensor's segment for operator confirmation.
- Whether to add a lightweight `quirk console list-sensors` convenience CLI.

### Deferred Ideas (OUT OF SCOPE)

- `quirk console reissue-sensor <id>` — deferred.
- Dual-accept grace window — explicitly rejected.
- HMAC payload signing (`X-Sensor-Signature` crypto verification) — `hmac_key` column still absent; separate concern.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| AUTH-01 | Each sensor authenticates with its own per-sensor token; console identifies which sensor a push came from based on the presented token. | `require_sensor_auth` dependency: SHA-256 hash of Bearer token → lookup in `sensor_tokens` → resolved sensor_id. Existing table already populated at enrollment. |
| AUTH-02 | Operator can revoke an individual sensor's token with no effect on other enrolled sensors. | `revoked_at` nullable column on `sensor_tokens` + `quirk console revoke-sensor <id>` subcommand in `console_cmd.py`. |
| AUTH-03 | Enrollment issues a per-sensor token bound to sensor UUID; raw token never persisted (SHA-256 hash only), reusing existing `sensor_tokens` table. | Token minting and hashing already implemented in `_cmd_enroll`; table already populated — this phase just activates the auth use. |
| AUTH-04 | Revoked or unknown per-sensor token → 401 at `POST /api/sensor/push` (gating test); migration off v5.4 shared-token model is backward-compatible and documented. | Test mirrors `test_sensor_ingest.py` pattern; docs update in `operators-guide.md`. |
</phase_requirements>

---

## Summary

Phase 113 activates an already-built but dormant per-sensor token table. The `sensor_tokens` table exists (Phase 107), is populated at enrollment (`_cmd_enroll`, `console_cmd.py:L163-164`), and stores a SHA-256 hash of the raw token — but `POST /api/sensor/push` currently authenticates via the shared operator `require_auth` dependency, ignoring `sensor_tokens` entirely. The enrollment printout explicitly says "NOT the push credential" (L217-224 in `console_cmd.py`).

This phase makes four surgical changes: (1) adds a `require_sensor_auth` FastAPI dependency that hash-looks-up the Bearer token in `sensor_tokens` and resolves the owning sensor, (2) swaps the push route from `require_auth` to `require_sensor_auth` while leaving all other routes on `require_auth`, (3) adds a nullable `revoked_at` column to `sensor_tokens` via the existing `_ensure_columns` / `_ADDITIVE_MIGRATIONS` infrastructure, and (4) adds a `revoke-sensor` subcommand to `console_cmd.py`'s `run_console` dispatcher. Migration documentation goes in `docs/operators-guide.md` §8.1.1.

The codebase has a mature, well-tested pattern for each of these elements — the work is integration, not invention. The main risk is the router-level dependency swap (the push route shares a router with `GET /api/sensor/registry` which must remain on operator `require_auth`), which requires splitting `POST /api/sensor/push` off onto its own `APIRouter` instance.

**Primary recommendation:** Split `POST /api/sensor/push` onto a dedicated sensor-auth router; leave `GET /api/sensor/registry` on the existing operator-auth router. All other changes flow from existing patterns in the codebase.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Per-sensor token authentication | API / Backend (`middleware/auth.py` + new `require_sensor_auth`) | — | M2M auth belongs in the API layer; never browser-side |
| `sensor_tokens` hash lookup + revocation check | API / Backend (`routes/sensor.py` dependency) | Database / Storage (`sensor_tokens` table) | Auth dependency reads DB to resolve identity |
| Revocation stamp (`revoked_at`) | Database / Storage (`sensor_tokens` table) | API / Backend (CLI command writes it) | Schema change; CLI mutates the record |
| `revoke-sensor` CLI subcommand | API / Backend (CLI = `console_cmd.py`) | — | Console-side management; writes to DB directly |
| `sensor.yaml` credential field update | No new tier — docs only | — | Wire contract unchanged; operator reconfigures value |
| Migration documentation | Documentation (`docs/operators-guide.md`) | — | AUTH-04 requirement |

---

## Standard Stack

This phase installs **no new packages**. All required libraries are already present in the codebase.

### Core (all already installed)

| Library | Purpose | Already Used In |
|---------|---------|-----------------|
| `fastapi` | `Depends()`, `HTTPException`, `Request` | `quirk/dashboard/api/middleware/auth.py`, `routes/sensor.py` |
| `sqlalchemy` | Session, Column, DateTime, `sa_inspect` | `quirk/models.py`, `quirk/db.py` |
| `hashlib` | `sha256(...).hexdigest()` for token hash | `quirk/cli/console_cmd.py:L164` |
| `hmac` | `compare_digest` timing-safe compare | `quirk/dashboard/api/middleware/auth.py:L54,61` |
| `secrets` | `token_urlsafe(32)` | `quirk/cli/console_cmd.py:L163`, `token_cmd.py` |
| `argparse` | Subcommand dispatch | `quirk/cli/console_cmd.py:run_console` |

### Package Legitimacy Audit

No new packages are introduced in this phase. All dependencies are pre-existing. Audit: N/A.

---

## Architecture Patterns

### System Architecture Diagram

```
POST /api/sensor/push
        |
        v
[Sensor Auth Router] — router = APIRouter(dependencies=[Depends(require_sensor_auth)])
        |
        v
require_sensor_auth(request, credentials=Depends(_bearer))
    |
    +-- extract Bearer token from credentials
    |
    +-- SHA-256 hash it: hashlib.sha256(token.encode()).hexdigest()
    |
    +-- db.query(SensorToken).filter(SensorToken.token_hash == hashed).first()
    |        |
    |        +-- None → HTTPException(401)
    |        +-- revoked_at is not None → HTTPException(401)
    |        +-- found, not revoked → sensor resolved
    |
    +-- attach resolved sensor_id to request.state.sensor_id
    |
    v
sensor_push handler (request, db)
    |
    +-- body size check → 413
    +-- decompress → 400
    +-- parse PushEnvelope → 400
    +-- replay window → 422
    |
    +-- TOKEN IDENTITY CHECK (D-04/D-05, NEW):
    |       envelope.sensor_id != request.state.sensor_id
    |       → _audit(db, ..., "failed", "sensor_id_mismatch") → 403
    |
    +-- _ingest_envelope(...)
    |       → DuplicatePayloadError → 409
    |       → UnknownSensorError → 404
    |       → Exception → 500
    |
    +-- _audit(db, ..., "ok") → 200

GET /api/sensor/registry
        |
        v
[Operator Auth Router] — router = APIRouter(dependencies=[Depends(require_auth)])
        |
        v
(unchanged — D-02)
```

### Recommended Project Structure (changes only)

```
quirk/
├── dashboard/api/
│   ├── middleware/
│   │   ├── auth.py            # unchanged — require_auth stays as-is
│   │   └── sensor_auth.py     # NEW — require_sensor_auth dependency
│   └── routes/
│       └── sensor.py          # MODIFIED — split push route to sensor-auth router
├── cli/
│   └── console_cmd.py         # MODIFIED — add revoke-sensor subcommand + run_console dispatch
├── models.py                  # MODIFIED — add revoked_at column to SensorToken
└── db.py                      # MODIFIED — add _V55_SENSOR_TOKEN_COLUMNS to _ADDITIVE_MIGRATIONS
tests/
└── test_sensor_auth_per_sensor.py  # NEW — AUTH-04 gating test (all 4 cases)
docs/
└── operators-guide.md         # MODIFIED — replace §8.1.1 with v5.5 per-sensor model
```

### Pattern 1: Router-Level Dependency Split (CRITICAL)

**What:** The current `sensor.py` uses a single `APIRouter` with `dependencies=[Depends(require_auth)]` at L55. Both `POST /sensor/push` and `GET /sensor/registry` are registered on this router. To swap auth on push-only without touching registry, the push route must move to a second `APIRouter` with `dependencies=[Depends(require_sensor_auth)]`.

**Current state (L55):**
```python
# Source: quirk/dashboard/api/routes/sensor.py:55
router = APIRouter(dependencies=[Depends(require_auth)])
```

**Required split:**
```python
# Source: verified pattern from quirk/dashboard/api/routes/sensor.py
# Operator-auth router — GET /sensor/registry stays here (D-02)
router = APIRouter(dependencies=[Depends(require_auth)])

# Sensor-auth router — POST /sensor/push moves here (D-01)
sensor_push_router = APIRouter(dependencies=[Depends(require_sensor_auth)])
```

Both routers must be registered in the app factory (`create_app()`). Check `quirk/dashboard/api/app.py` for how `include_router` is called.

**Why this matters:** FastAPI router-level `Depends` cannot be overridden per-handler. If both routes share a router, ALL handlers inherit the same dependency. The only clean split is two routers. Per-route `dependencies=` on the `@router.post(...)` decorator is an alternative — it ADDS to router-level dependencies rather than replacing them, so that approach requires removing the router-level dep and adding it back per-handler on each route. Two-router approach is cleaner.

### Pattern 2: `require_sensor_auth` Dependency Shape

Mirror `require_auth` from `middleware/auth.py` exactly, adapted for hash lookup:

```python
# Source: verified from quirk/dashboard/api/middleware/auth.py structure
import hashlib
import hmac
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from quirk.dashboard.api.deps import get_db
from quirk.models import SensorToken

_bearer = HTTPBearer(auto_error=False)

def require_sensor_auth(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: Session = Depends(get_db),
) -> None:
    """Sensor M2M auth — Bearer token hashed to SHA-256 and looked up in sensor_tokens.
    Never reaches business logic on 401 (T-109-04 guarantee preserved).
    Token never logged (T-102-09).
    """
    if credentials is None:
        raise HTTPException(status_code=401, detail="Sensor authentication required")
    
    raw_token = credentials.credentials
    hashed = hashlib.sha256(raw_token.encode()).hexdigest()
    
    token_row = db.query(SensorToken).filter(SensorToken.token_hash == hashed).first()
    if token_row is None:
        raise HTTPException(status_code=401, detail="Unknown sensor token")
    if token_row.revoked_at is not None:
        raise HTTPException(status_code=401, detail="Sensor token revoked")
    
    # Attach resolved sensor_id for the handler (D-04)
    request.state.sensor_id = token_row.sensor_id
```

**Timing-safe note (D-03):** A hash-table lookup is not timing-equivalent to `hmac.compare_digest`, but the hash itself (SHA-256) is a fixed-time operation on the input — the comparison is integer equality on a 64-char hex string. Using `hmac.compare_digest(hashed, token_row.token_hash)` instead of `==` is a direct drop-in improvement that mirrors the `middleware/auth.py` discipline and should be used for the database comparison.

### Pattern 3: Additive Schema Migration (VERIFIED)

**What:** The `_ensure_columns` / `_ADDITIVE_MIGRATIONS` infrastructure in `quirk/db.py` is the established pattern for adding nullable columns to existing tables. [VERIFIED: quirk/db.py]

**Exact pattern to follow for `revoked_at`:**

Step 1 — Define the column tuple (add to `quirk/db.py`):
```python
# Source: quirk/db.py — mirrors _V54_SENSOR_COLUMNS pattern (L125-130)
_V55_SENSOR_TOKEN_COLUMNS: tuple[tuple[str, str], ...] = (
    # Phase 113 AUTH-02: soft revocation — NULL = active, set = revoked.
    ("revoked_at", "DATETIME"),
)
```

Step 2 — Register in `_ADDITIVE_MIGRATIONS` tuple (append to the tuple in `quirk/db.py:L178`):
```python
("sensor_tokens", _V55_SENSOR_TOKEN_COLUMNS),  # Phase 113 AUTH-02
```

Step 3 — `init_db` picks it up automatically because it iterates `_ADDITIVE_MIGRATIONS` at L410.

Step 4 — Update `SensorToken` model in `quirk/models.py`:
```python
# Source: quirk/models.py:L303-312 — add after created_at
revoked_at = Column(DateTime, nullable=True)   # None = active; set = revoked (Phase 113)
```

**Idempotency guarantee:** `_ensure_columns` checks existing columns via `sa_inspect(engine).get_columns(table)` and skips any column already present (L154-162). Existing single-host and v5.4 distributed DBs migrate cleanly on first `init_db` call after upgrade.

**`_SAFE_COL_TYPE_RE` allows DATETIME** — confirmed at `db.py:L52`: `r"^(TEXT|INTEGER|REAL|BOOLEAN|DATETIME|VARCHAR\(\d{1,4}\))$"`.

### Pattern 4: `run_console` Subcommand Dispatch

**What:** `console_cmd.py:run_console()` uses argparse subparsers dispatched via `args.action`. The `revoke-sensor` subcommand slots in at L116-120.

**Current dispatch (L116-120):**
```python
# Source: quirk/cli/console_cmd.py:116-120
args = parser.parse_args(argv)
if args.action == "import-results":
    _cmd_import_results(args)
elif args.action == "enroll":
    _cmd_enroll(args)
```

**Extension pattern:**
```python
# Add sub.add_parser("revoke-sensor", ...) alongside enroll_p and import_p
revoke_p = sub.add_parser(
    "revoke-sensor",
    help="Revoke a sensor's push token (sensor is immediately rejected on next push)",
)
revoke_p.add_argument("sensor_id", help="Sensor UUID to revoke")
revoke_p.add_argument("--config", default="config.yaml", help="Console config.yaml path")

# In dispatch block:
elif args.action == "revoke-sensor":
    _cmd_revoke_sensor(args)
```

`_cmd_revoke_sensor` stamps `revoked_at = datetime.now(timezone.utc).replace(tzinfo=None)` on the `SensorToken` row(s) for the given `sensor_id`. No `sys.exit(0)` — return normally (WR-04 pattern from enroll).

### Pattern 5: Body/Token Identity Check (D-04/D-05)

After `require_sensor_auth` resolves `request.state.sensor_id`, the push handler adds this check immediately after the existing sensor-lookup step:

```python
# After: sensor_row = db.query(Sensor).filter(...).first() — existing L312
# Add:
token_sensor_id = request.state.sensor_id
if envelope.sensor_id != token_sensor_id:
    _audit(db, scan_id, "failed", "sensor_id_mismatch")
    raise HTTPException(status_code=403, detail="sensor_id mismatch: token does not match envelope")
```

This replaces the existing body-trust model (D-04): `sensor_row` lookup now uses `token_sensor_id` instead of `envelope.sensor_id`.

### Pattern 6: `_audit()` for New Branches

Every new failure branch must write an `IntegrationDelivery` audit row before raising `HTTPException` (D-09). The `_audit()` helper at `sensor.py:L168` takes `(db, scan_id, status, error_summary)`. New branches:

| HTTP Status | Trigger | `error_summary` fixed string |
|------------|---------|------------------------------|
| 401 | Unknown token (no matching hash) | `"unknown_sensor_token"` |
| 401 | Revoked token (`revoked_at` set) | `"revoked_sensor_token"` |
| 403 | Body `sensor_id` != token-resolved `sensor_id` | `"sensor_id_mismatch"` |
| 200 | Valid push | `None` (status="ok") |

The 401 branches from `require_sensor_auth` fire *before* the route handler, so `_audit()` cannot be called there (no `db` session in the dependency without injecting it — see Pattern 2 above for injecting `db` into `require_sensor_auth`). If `db` is injected into `require_sensor_auth`, audit rows can be written there. Alternatively, catch the 401 at middleware level. **Recommended:** Inject `db: Session = Depends(get_db)` into `require_sensor_auth` so it can write audit rows for the 401 cases — this is consistent with the handler's `_audit()` pattern and injectable via FastAPI's DI.

**Audit `scan_id` for pre-parse 401 branches:** Use `datetime.now(timezone.utc).replace(tzinfo=None).strftime("%Y-%m-%dT%H:%M:%SZ")` as surrogate scan_id (same fallback the handler uses at L207).

### Anti-Patterns to Avoid

- **Single router for both routes:** If `POST /sensor/push` and `GET /sensor/registry` share one router, changing the dependency changes both. Two separate routers is required.
- **String comparison on raw token:** Never compare raw Bearer token directly against anything stored (nothing is stored raw). Always hash first.
- **`sys.exit()` in `_cmd_revoke_sensor`:** Follow WR-04 — return normally. `sys.exit(1)` only on error (mirrors `_cmd_enroll`'s `IntegrityError` path).
- **Audit rows in `require_sensor_auth` without `db` injection:** A dependency that receives `db=Depends(get_db)` can write audit rows for the 401 cases. Without it, 401 cases produce no audit trail — violates D-09.
- **`hmac.compare_digest` on full raw token vs stored hash:** Only the hash is stored. Compare `hashed == token_row.token_hash` (or use `hmac.compare_digest(hashed, token_row.token_hash)` for timing-safe guarantee even on equal-length hex strings).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Idempotent `ALTER TABLE ADD COLUMN` | Custom migration script | `_ensure_columns` + `_ADDITIVE_MIGRATIONS` in `quirk/db.py` | Already handles existing-column skip, allowlist guards, both `init_db` and `run_additive_migration` paths |
| Token bearer extraction from HTTP request | Manual header parsing | `HTTPBearer(auto_error=False)` (already instantiated as `_bearer` in `auth.py`) | FastAPI security scheme; handles missing/malformed headers cleanly |
| Database session injection | Manual session factory | `Depends(get_db)` from `quirk.dashboard.api.deps` | Existing DI pattern; manages commit/rollback scope |
| Audit row writing | Per-branch `db.add(IntegrationDelivery(...))` inline | Reuse `_audit(db, scan_id, status, error_summary)` helper at `sensor.py:L168` | Centralizes commit, error handling, timestamp discipline |
| SHA-256 token hashing | Any other digest | `hashlib.sha256(raw_token.encode()).hexdigest()` | Matches what `_cmd_enroll` writes — must produce identical 64-char hex |

---

## Runtime State Inventory

> This phase replaces the push auth model. Runtime state that uses the old shared-token model must be noted.

| Category | Items Found | Action Required |
|----------|-------------|-----------------|
| Stored data | `sensor_tokens` table: existing rows have `token_hash` set; no `revoked_at` column yet | Schema migration (additive column, nullable) — handled by `_ensure_columns` automatically on first `init_db` after upgrade |
| Live service config | `sensor.yaml` on each sensor host: `console_api_token` currently holds the shared `QUIRK_API_TOKEN` value | Code rename only (field name unchanged); operator must re-point value to per-sensor enrollment token (D-11) |
| OS-registered state | None — no Task Scheduler / pm2 / systemd involvement in push auth | None |
| Secrets/env vars | `QUIRK_API_TOKEN` / `security.api_token` on console: still used for operator/dashboard auth; unchanged. `console_api_token` in `sensor.yaml` on sensor: value changes semantics but key name stays | Operator reconfigures value; code change in `docs/operators-guide.md` documents what the new value must be |
| Build artifacts | None — no compiled artifacts affected by this auth change | None |

**Key operator migration note (D-10/D-11):** After upgrade, the operator must change `console_api_token` in `sensor.yaml` on each sensor host from the shared `QUIRK_API_TOKEN` value to the sensor's **enrollment token** (printed by `quirk console enroll` at provisioning time). If the raw token was lost, the operator must run `quirk console revoke-sensor <id>` + re-enroll. This is a manual step that must be documented clearly in §8.1.1 of `operators-guide.md`.

---

## Common Pitfalls

### Pitfall 1: Router-Level Auth Applies to ALL Routes on the Router

**What goes wrong:** Developer modifies `router = APIRouter(dependencies=[Depends(require_auth)])` at `sensor.py:L55` to use `require_sensor_auth` instead, assuming only `POST /sensor/push` is affected. `GET /sensor/registry` (also on this router) silently gets the wrong auth dependency — sensor tokens would be accepted for the operator registry endpoint.

**Why it happens:** Router-level `dependencies=` applies to every route registered on that router instance. There is no "except this one route" carve-out.

**How to avoid:** Two-router split: `router` (operator auth) keeps `GET /sensor/registry`; `sensor_push_router` (sensor auth) gets `POST /sensor/push`. Both registered in `create_app()`.

**Warning signs:** Any test for `GET /sensor/registry` with a sensor Bearer token that returns 200 instead of 401.

### Pitfall 2: 401 Branches in Dependency Have No `db` Session by Default

**What goes wrong:** `require_sensor_auth` raises `HTTPException(401)` before the route handler runs. No `IntegrationDelivery` audit row is written for the unknown/revoked token cases — violates D-09.

**Why it happens:** FastAPI dependencies execute before handlers. If `db` is not injected into the dependency itself, there is no session to write the audit row.

**How to avoid:** Add `db: Session = Depends(get_db)` to `require_sensor_auth`'s signature (Pattern 2 above). This is standard FastAPI DI — dependencies can depend on other dependencies.

**Warning signs:** `test_sensor_auth_per_sensor.py` asserting `IntegrationDelivery` rows exist for the 401 cases fails even though the 401 HTTP status is correct.

### Pitfall 3: Comparison Must Use the Hash, Not the Raw Token

**What goes wrong:** Developer stores `credentials.credentials` (the raw Bearer token from the request) directly into a variable and queries `SensorToken.token_hash == raw_token`. Returns zero rows for a valid token.

**Why it happens:** `sensor_tokens.token_hash` stores `SHA-256(raw_token).hexdigest()` — 64 hex chars. The raw token from `secrets.token_urlsafe(32)` is ~43 base64url chars. They will never match.

**How to avoid:** Always hash before lookup: `hashlib.sha256(credentials.credentials.encode()).hexdigest()`.

**Warning signs:** `require_sensor_auth` always returns 401 even for a freshly enrolled sensor.

### Pitfall 4: `sensor_tokens` Table Has No `revoked_at` Column Until `init_db` Runs

**What goes wrong:** Developer updates `SensorToken` model and `_ADDITIVE_MIGRATIONS` but tests fail with `OperationalError: table sensor_tokens has no column named revoked_at`.

**Why it happens:** In-memory test engines call `Base.metadata.create_all(engine)` directly, which uses the ORM model definition. If the model is updated correctly, `create_all` on a fresh in-memory DB will include the column. However, if any test fixture pre-creates the table from an older schema snapshot (or if `create_all` is called before the model module is imported), the column is missing.

**How to avoid:** Ensure test helpers call `Base.metadata.create_all(engine)` AFTER importing `quirk.models` (which registers `SensorToken` with the updated schema). The `conftest.py` autouse fixture already handles this for the standard test suite.

**Warning signs:** `OperationalError` on `revoked_at` in tests despite the model being updated.

### Pitfall 5: `console_api_token` Semantics Change Is Not Backward-Compatible Without Documentation

**What goes wrong:** Operator upgrades QUIRK on the console, which activates per-sensor auth. All sensors immediately start getting 401 because `console_api_token` in their `sensor.yaml` still holds the shared `QUIRK_API_TOKEN` value, which is not a valid per-sensor enrollment token.

**Why it happens:** D-10 specifies clean cutover with no dual-accept. Operators must re-point the credential value.

**How to avoid:** Clear, prominent migration section in `docs/operators-guide.md` §8.1.1 explaining: (a) what changed, (b) what the operator must do on each sensor host, (c) what to do if the raw enrollment token was lost (`revoke-sensor` + re-enroll). The planner should include documentation as a Wave 0 or pre-implementation task so it ships alongside the code.

---

## Code Examples

### `require_sensor_auth` — Full Dependency

```python
# Source: verified pattern from quirk/dashboard/api/middleware/auth.py (L1-63)
# and quirk/models.py (L291-312)
# File: quirk/dashboard/api/middleware/sensor_auth.py (new)
from __future__ import annotations

import hashlib
import hmac
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from quirk.dashboard.api.deps import get_db
from quirk.models import IntegrationDelivery, SensorToken
from quirk.util.safe_exc import safe_str

logger = logging.getLogger(__name__)
_bearer = HTTPBearer(auto_error=False)


def require_sensor_auth(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: Session = Depends(get_db),
) -> None:
    """FastAPI Depends() — per-sensor Bearer token auth for POST /api/sensor/push.

    1. Extract Bearer token from Authorization header.
    2. SHA-256-hash it.
    3. Look up hash in sensor_tokens — unknown hash → 401.
    4. Check revoked_at — revoked → 401.
    5. Attach resolved sensor_id to request.state.
    All 401 branches write an IntegrationDelivery audit row (D-09).
    Token never logged (T-102-09).
    """
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    scan_id = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    def _audit_and_raise(status_code: int, error_summary: str, detail: str) -> None:
        row = IntegrationDelivery(
            scan_id=scan_id,
            finding_hash=None,
            destination="sensor_push",
            status="failed",
            attempted_at=now,
            error_summary=error_summary,
        )
        db.add(row)
        try:
            db.commit()
        except Exception as exc:
            logger.warning("Sensor auth audit row commit failed: %s", safe_str(exc))
        raise HTTPException(status_code=status_code, detail=detail)

    if credentials is None:
        _audit_and_raise(401, "missing_sensor_token", "Sensor authentication required")

    hashed = hashlib.sha256(credentials.credentials.encode()).hexdigest()
    token_row = db.query(SensorToken).filter(SensorToken.token_hash == hashed).first()

    if token_row is None:
        _audit_and_raise(401, "unknown_sensor_token", "Unknown sensor token")

    # Timing-safe comparison (defense in depth — hashed == stored is already constant-time
    # on equal-length hex strings, but compare_digest mirrors middleware/auth.py discipline)
    if not hmac.compare_digest(hashed, token_row.token_hash):
        _audit_and_raise(401, "unknown_sensor_token", "Unknown sensor token")

    if token_row.revoked_at is not None:
        _audit_and_raise(401, "revoked_sensor_token", "Sensor token revoked")

    request.state.sensor_id = token_row.sensor_id
```

### `_cmd_revoke_sensor` — Revocation CLI Handler

```python
# Source: verified dispatch pattern from quirk/cli/console_cmd.py:116-120
# and _cmd_enroll DB session pattern (L167-201)
def _cmd_revoke_sensor(args: argparse.Namespace) -> None:
    """Stamp revoked_at on the sensor_tokens row(s) for the given sensor_id.

    Sensor row and push history are retained (D-06).
    Returns normally on success (WR-04 — no sys.exit(0)).
    Exits 1 with fixed message if sensor_id has no active token rows.
    """
    import hashlib  # noqa — lazy import pattern from _cmd_enroll
    from datetime import datetime, timezone
    from sqlalchemy.orm import sessionmaker
    from quirk.dashboard.api.deps import _default_db_path
    from quirk.db import init_db
    from quirk.models import SensorToken

    sensor_id: str = args.sensor_id
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    db_path = _default_db_path()
    engine = init_db(db_path)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

    with Session() as db:
        rows = db.query(SensorToken).filter(
            SensorToken.sensor_id == sensor_id,
            SensorToken.revoked_at.is_(None),
        ).all()
        if not rows:
            print(f"ERROR: no active token found for sensor_id {sensor_id!r}", file=sys.stderr)
            sys.exit(1)
        for row in rows:
            row.revoked_at = now
        db.commit()
    print(f"Revoked token(s) for sensor_id: {sensor_id}")
```

### DB Migration — `_V55_SENSOR_TOKEN_COLUMNS`

```python
# Source: verified pattern from quirk/db.py:L125-130 (_V54_SENSOR_COLUMNS)
# Add to quirk/db.py after _V54_SENSOR_COLUMNS:
_V55_SENSOR_TOKEN_COLUMNS: tuple[tuple[str, str], ...] = (
    # Phase 113 AUTH-02: soft revocation timestamp. NULL = active token; set = revoked.
    ("revoked_at", "DATETIME"),
)

# Append to _ADDITIVE_MIGRATIONS tuple (after the last existing entry):
("sensor_tokens", _V55_SENSOR_TOKEN_COLUMNS),  # Phase 113 AUTH-02
```

### SensorToken Model Update

```python
# Source: verified from quirk/models.py:L303-312
# Add revoked_at after created_at in SensorToken class:
revoked_at = Column(DateTime, nullable=True)  # None = active; set = revoked (Phase 113 AUTH-02)
```

### `sensor.py` Router Split

```python
# Source: verified from quirk/dashboard/api/routes/sensor.py:L55
# Replace single router with two:

# Operator auth — GET /sensor/registry (D-02: operator surfaces stay on require_auth)
router = APIRouter(dependencies=[Depends(require_auth)])

# Sensor auth — POST /sensor/push only (D-01)
sensor_push_router = APIRouter(dependencies=[Depends(require_sensor_auth)])
# Import at top: from quirk.dashboard.api.middleware.sensor_auth import require_sensor_auth

# Move @router.post("/sensor/push") decorator to @sensor_push_router.post("/sensor/push")
```

In `create_app()`, register both routers with the same prefix:
```python
app.include_router(sensor_router, prefix="/api")
app.include_router(sensor_push_router, prefix="/api")
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Shared `QUIRK_API_TOKEN` for all sensor pushes (v5.4 TD-1) | Per-sensor opaque token, SHA-256 hashed, looked up in `sensor_tokens` | Phase 113 (this phase) | Individual sensor revocation without affecting other sensors |
| `enroll` token was audit-only, NOT the push credential | Enroll token IS the push credential (raw value printed at enrollment) | Phase 113 (this phase) | Operators must reconfigure `console_api_token` in `sensor.yaml` |

**Deprecated/outdated after this phase:**
- v5.4 shared-token model description in `docs/operators-guide.md §8.1.1`: replace entirely with v5.5 per-sensor model.
- Enrollment stdout message "This enrollment token is NOT the push credential" (`console_cmd.py:L217-224`): update to say the token IS the push credential.
- `sensor_cmd.py` enrollment docs referencing `--api-token <console-QUIRK_API_TOKEN>`: update to show per-sensor token usage.

---

## Assumptions Log

> All claims in this research were verified directly from the codebase source. No training-data-only assumptions.

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `create_app()` in `quirk/dashboard/api/app.py` uses `include_router` for sensor routes — exact call signature not verified | Architecture Patterns (router split) | If routes are registered differently, the two-router pattern needs adjustment |

**All other claims are verified from source files read during this session.**

---

## Open Questions (RESOLVED)

1. **`create_app()` include_router signature** — RESOLVED in planning.
   - What we know: `routes/sensor.py` exports `router`; `create_app()` imports and includes it.
   - Resolution: `quirk/dashboard/api/app.py:117` includes `sensor.router` with `prefix="/api"`; the `jobs.read_router` + `jobs.write_router` dual-include at L114-115 is the confirmed precedent for registering `sensor_push_router` alongside `router` at the same prefix. Captured in Plan 113-02 Task 2 interfaces block.

2. **Existing push tests use shared token — need update** — RESOLVED in planning.
   - What we know: `test_sensor_ingest.py` sets `QUIRK_API_TOKEN="test-token"` and sends `Authorization: Bearer test-token` directly. After this phase, those requests will hit `require_sensor_auth` which will not find a `sensor_tokens` row for the shared token's hash.
   - Resolution: Plan 113-01 Task 2 creates `test_sensor_auth_per_sensor.py` using seeded enrollment tokens (Wave 0); Plan 113-03 Task 1 updates the existing `test_sensor_ingest.py` push tests to seed a `SensorToken` row and use the enrollment token as the Bearer header, after the auth swap lands in 113-02.

---

## Environment Availability

Phase is purely code/config changes — no external tools or services beyond the existing Python/pytest stack required.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11+ | Runtime | Confirmed (project requirement) | — | — |
| pytest | Test suite | Confirmed (`pyproject.toml:L130`) | — | — |
| SQLite (via sqlalchemy) | DB migration | Confirmed (in-memory used in tests) | — | — |

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/test_sensor_auth_per_sensor.py -x -q` |
| Full suite command | `pytest tests/ -x -q -m 'not slow'` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AUTH-01 | Valid enrolled sensor token → 200 accepted; `request.state.sensor_id` matches enrolled sensor | unit (API) | `pytest tests/test_sensor_auth_per_sensor.py::test_valid_sensor_token_accepted -x` | Wave 0 |
| AUTH-01 | Token-resolved `sensor_id` is used (not envelope body's sensor_id) | unit (API) | `pytest tests/test_sensor_auth_per_sensor.py::test_token_identity_is_authoritative -x` | Wave 0 |
| AUTH-02 | `quirk console revoke-sensor <id>` stamps `revoked_at`; subsequent push returns 401 | unit (CLI + API) | `pytest tests/test_sensor_auth_per_sensor.py::test_revoked_token_returns_401 -x` | Wave 0 |
| AUTH-02 | Revoking sensor A has no effect on sensor B's push | unit (API) | `pytest tests/test_sensor_auth_per_sensor.py::test_revoke_isolates_to_one_sensor -x` | Wave 0 |
| AUTH-03 | `console enroll` still writes correct SHA-256 hash to `sensor_tokens`; `revoked_at` is NULL on new enrollment | unit (CLI) | `pytest tests/test_console_enroll.py -x` (update existing) | Yes (update) |
| AUTH-04 | Unknown token (no matching hash) → 401 + IntegrationDelivery audit row | unit (API) | `pytest tests/test_sensor_auth_per_sensor.py::test_unknown_token_returns_401 -x` | Wave 0 |
| AUTH-04 | Revoked token → 401 + IntegrationDelivery audit row | unit (API) | `pytest tests/test_sensor_auth_per_sensor.py::test_revoked_token_returns_401 -x` | Wave 0 |
| AUTH-04 | Body sensor_id != token sensor_id → 403 + IntegrationDelivery audit row | unit (API) | `pytest tests/test_sensor_auth_per_sensor.py::test_sensor_id_mismatch_returns_403 -x` | Wave 0 |
| AUTH-04 | All 4 cases write IntegrationDelivery rows | unit (API) | `pytest tests/test_sensor_auth_per_sensor.py::test_all_branches_write_audit_rows -x` | Wave 0 |

### Observable Signals Proving AUTH-01..04 Hold

- **AUTH-01:** `GET /api/sensor/registry` still returns 200 with operator Bearer token; `POST /api/sensor/push` with operator Bearer token returns 401 (wrong auth type); `POST /api/sensor/push` with valid per-sensor enrollment token returns 200 with `sensor_id` in response matching the enrolled sensor.
- **AUTH-02:** `sensor_tokens` table has `revoked_at IS NOT NULL` after `quirk console revoke-sensor <id>` is called; next push from that sensor returns 401; pushes from other sensors continue returning 200.
- **AUTH-03:** `sensor_tokens` row after new enrollment: `revoked_at IS NULL`; `token_hash == SHA-256(raw_enrollment_token).hexdigest()`.
- **AUTH-04:** HTTP 401 for unknown token; HTTP 401 for revoked token; HTTP 403 for mismatched sensor_id; HTTP 200 for valid matching token; `IntegrationDelivery` rows with `destination='sensor_push'`, `status='failed'`, distinct `error_summary` values for each case.

### Sampling Rate

- **Per task commit:** `pytest tests/test_sensor_auth_per_sensor.py -x -q`
- **Per wave merge:** `pytest tests/ -x -q -m 'not slow'`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_sensor_auth_per_sensor.py` — new file covering all AUTH-01..04 assertions (8 test functions listed above)
- [ ] Update `tests/test_sensor_ingest.py` — existing push tests must seed a `SensorToken` row + use enrollment token as Bearer token after the auth swap; otherwise ALL existing push tests fail post-Phase 113

*(Existing test infrastructure covers the rest — conftest.py QUIRK_DB_PATH isolation, in-memory SQLite pattern, `_app_with_db()` factory all reusable as-is)*

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | Yes | SHA-256 token hash lookup + `hmac.compare_digest` timing-safe compare |
| V3 Session Management | No | M2M token-per-request; no session state |
| V4 Access Control | Yes | Sensor auth vs. operator auth segregated via separate dependency + separate router |
| V5 Input Validation | Yes | Bearer token extracted via `HTTPBearer`; never logged or reflected |
| V6 Cryptography | Partial | SHA-256 hash storage (no key material stored raw); HMAC payload signing deferred |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Sensor impersonation via body `sensor_id` spoofing | Spoofing | D-04: token is authoritative; `envelope.sensor_id` != `request.state.sensor_id` → 403 |
| Compromised sensor affecting others | Elevation of privilege | D-07: revocation affects only the target sensor's token row |
| Raw token leakage in logs | Information disclosure | D-03/T-102-09: never log `credentials.credentials`; only hash is compared |
| Timing oracle on token comparison | Spoofing | `hmac.compare_digest(hashed, token_row.token_hash)` — constant-time on equal-length hex strings |
| Shared token compromise (v5.4 model) | Spoofing | Phase 113 goal: eliminate shared token from push route entirely (D-10) |

---

## Sources

### Primary (HIGH confidence — all verified from codebase source)

- `quirk/dashboard/api/middleware/auth.py` — `require_auth`, `_bearer`, `hmac.compare_digest`, `_get_configured_token` patterns
- `quirk/dashboard/api/routes/sensor.py` — router-level `Depends(require_auth)` at L55; full failure ladder; `_audit()` helper; `PushEnvelope`; both route handlers
- `quirk/cli/console_cmd.py` — `run_console` dispatch (L69-120), `_cmd_enroll` SHA-256 hashing (L163-164), `SensorToken` insert (L191-195), enrollment printout (L217-224)
- `quirk/models.py` — `SensorToken` (L291-312), `Sensor` (L269-288), `IntegrationDelivery` (L258-266)
- `quirk/db.py` — `_ensure_columns` (L133-163), `_ADDITIVE_MIGRATIONS` (L178-188), `init_db` (L386-433), `_SAFE_COL_TYPE_RE` (L52)
- `tests/test_sensor_ingest.py` — `_app_with_db()` factory, `_seed_sensor()`, `_build_envelope()`, `_compress()` helpers; auth header pattern; audit row assertion pattern
- `tests/test_console_enroll.py` — `_make_db()`, QUIRK_DB_PATH monkeypatch pattern
- `tests/conftest.py` — autouse QUIRK_DB_PATH isolation fixture

### Secondary (MEDIUM confidence)

- `docs/operators-guide.md §8.1.1` — v5.4 shared-token model description (confirmed existing text that needs replacing)
- `quirk/cli/sensor_cmd.py L574-611` — `console_api_token` in `sensor.yaml` + Bearer header construction

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries verified in codebase
- Architecture: HIGH — all patterns verified from source files
- Migration pattern: HIGH — `_ensure_columns` / `_ADDITIVE_MIGRATIONS` fully read and understood
- Test infrastructure: HIGH — `test_sensor_ingest.py` fully read; Wave 0 gaps identified precisely
- Pitfalls: HIGH — derived from actual code structure (router-level deps, lazy-import pattern, audit row timing)

**Research date:** 2026-05-26
**Valid until:** 2026-06-25 (stable internal codebase; no external dependencies)
