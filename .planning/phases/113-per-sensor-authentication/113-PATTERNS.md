# Phase 113: Per-Sensor Authentication - Pattern Map

**Mapped:** 2026-05-26
**Files analyzed:** 10 (8 new/modified + 2 existing tests updated)
**Analogs found:** 10 / 10

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `quirk/dashboard/api/middleware/sensor_auth.py` | middleware | request-response | `quirk/dashboard/api/middleware/auth.py` | exact |
| `quirk/dashboard/api/routes/sensor.py` | route | request-response | `quirk/dashboard/api/routes/jobs.py` (two-router pattern) | exact |
| `quirk/dashboard/api/app.py` | config | request-response | existing `app.py` L117 sensor include | exact |
| `quirk/db.py` | migration | CRUD | existing `_V54_SENSOR_COLUMNS` + `_ADDITIVE_MIGRATIONS` | exact |
| `quirk/models.py` | model | CRUD | existing `SensorToken` class (L291-313) | exact |
| `quirk/cli/console_cmd.py` | service/CLI | CRUD | existing `_cmd_enroll` + `run_console` dispatch | exact |
| `quirk/cli/sensor_cmd.py` | service/CLI | request-response | same file L574-601 (credential field + Bearer header) | exact |
| `docs/operators-guide.md` | documentation | — | existing §8.1.1 text (replace in place) | exact |
| `tests/test_sensor_auth_per_sensor.py` | test | request-response | `tests/test_sensor_ingest.py` (full file) | exact |
| `tests/test_sensor_ingest.py` | test (update) | request-response | same file — add `_seed_token()` helper + update auth headers | exact |

---

## Pattern Assignments

### `quirk/dashboard/api/middleware/sensor_auth.py` (middleware, NEW)

**Analog:** `quirk/dashboard/api/middleware/auth.py`

**Imports pattern** (auth.py lines 1-11):
```python
from __future__ import annotations

import hmac
import os
from typing import Optional

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from quirk.errors import format_error
```
New file's imports extend this with `hashlib`, `logging`, `datetime/timezone`,
`Session`/`get_db`, `SensorToken`, `IntegrationDelivery`, and `safe_str`.

**`_bearer` singleton pattern** (auth.py line 31):
```python
_bearer = HTTPBearer(auto_error=False)
```
Copy verbatim — new file instantiates its own `_bearer` the same way.

**Core dependency signature** (auth.py lines 34-37):
```python
def require_auth(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> None:
```
`require_sensor_auth` mirrors this signature exactly, adding `db: Session = Depends(get_db)` as a third parameter so it can write `IntegrationDelivery` audit rows for the 401 branches (D-09 / RESEARCH Pitfall 2).

**Timing-safe comparison discipline** (auth.py lines 54, 61):
```python
if hmac.compare_digest(x_api_key, configured):   # timing-safe (T-102-05)
    ...
if not hmac.compare_digest(credentials.credentials, configured):  # D-03
```
Use `hmac.compare_digest(hashed, token_row.token_hash)` in the new dependency — same discipline on equal-length 64-char hex strings.

**Never-log-raw-token contract** (auth.py docstring line 44):
```
Token never logged (T-102-09).
```
Copy this docstring annotation verbatim into `require_sensor_auth`.

**`_audit_and_raise` inner helper** — no exact analog in `auth.py` (which just raises directly). Model the inner helper pattern on `_audit()` in `sensor.py` lines 168-193 (see that section below), but inline it as a nested function inside `require_sensor_auth` since it needs `db` + `scan_id` from the closure.

---

### `quirk/dashboard/api/routes/sensor.py` (route, MODIFIED — router split)

**Analog:** `quirk/dashboard/api/routes/jobs.py` lines 38-39

**Two-router pattern** (jobs.py lines 38-39):
```python
read_router = APIRouter(dependencies=[Depends(require_auth)])
write_router = APIRouter(dependencies=[Depends(require_auth), Depends(require_csrf)])
```
Apply the same pattern to sensor.py:
```python
# Operator auth — GET /sensor/registry (D-02)
router = APIRouter(dependencies=[Depends(require_auth)])

# Sensor M2M auth — POST /sensor/push only (D-01)
sensor_push_router = APIRouter(dependencies=[Depends(require_sensor_auth)])
```
Name `router` and `sensor_push_router` so `app.py` can import both; the existing import `from quirk.dashboard.api.routes import ... sensor` does not need to change if `sensor_push_router` is added as a second export.

**Current single-router declaration** (sensor.py line 55):
```python
router = APIRouter(dependencies=[Depends(require_auth)])
```
This line stays for the operator router. The `@router.post("/sensor/push")` decorator at line 199 moves to `@sensor_push_router.post("/sensor/push")`.

**`_audit()` helper** (sensor.py lines 168-193) — unchanged; called from the push handler for the 403 branch (D-05) and all existing branches. Also called by `require_sensor_auth` via the inner helper for 401 branches.

**Sensor identity check insertion point** (sensor.py lines 312-315):
```python
# Current (v5.4 — trust body):
sensor_row = db.query(Sensor).filter(Sensor.sensor_id == envelope.sensor_id).first()
if sensor_row is None:
    _audit(db, scan_id, "failed", "unknown_sensor_id")
    raise HTTPException(status_code=404, detail="Unknown sensor_id")
```
After the router split, add the D-04/D-05 identity check immediately after the sensor row lookup, using `request.state.sensor_id` (resolved by `require_sensor_auth`):
```python
# New: token-resolved identity is authoritative (D-04)
token_sensor_id = request.state.sensor_id
sensor_row = db.query(Sensor).filter(Sensor.sensor_id == token_sensor_id).first()
if sensor_row is None:
    _audit(db, scan_id, "failed", "unknown_sensor_id")
    raise HTTPException(status_code=404, detail="Unknown sensor_id")
# D-05: body/token mismatch → 403 + audit
if envelope.sensor_id != token_sensor_id:
    _audit(db, scan_id, "failed", "sensor_id_mismatch")
    raise HTTPException(status_code=403, detail="sensor_id mismatch: token does not match envelope")
```

---

### `quirk/dashboard/api/app.py` (config, MODIFIED — register second router)

**Analog:** app.py line 117

**Current sensor router registration** (app.py line 117):
```python
application.include_router(sensor.router, prefix="/api")
```
Add one line immediately after:
```python
application.include_router(sensor.router, prefix="/api")
application.include_router(sensor.sensor_push_router, prefix="/api")
```

**Multi-router precedent** (app.py lines 114-115 — jobs already does this):
```python
application.include_router(jobs.read_router, prefix="/api")
application.include_router(jobs.write_router, prefix="/api")
```
Same registration pattern — no new technique required.

---

### `quirk/db.py` (migration, MODIFIED — additive column)

**Analog:** `quirk/db.py` lines 125-130 (`_V54_SENSOR_COLUMNS`) + lines 178-188 (`_ADDITIVE_MIGRATIONS`)

**Existing column-list definition pattern** (db.py lines 125-130):
```python
_V54_SENSOR_COLUMNS: tuple[tuple[str, str], ...] = (
    # Phase 107 MODEL-01: nullable sensor tracking columns on crypto_endpoints.
    # NULL sensor_id = implicit local sensor (backward-compatible with pre-v5.4 rows).
    ("sensor_id", "TEXT"),
    ("segment",   "TEXT"),
)
```
New entry follows exactly this shape — append after `_V54_SENSOR_COLUMNS`:
```python
_V55_SENSOR_TOKEN_COLUMNS: tuple[tuple[str, str], ...] = (
    # Phase 113 AUTH-02: soft revocation timestamp. NULL = active token; set = revoked.
    ("revoked_at", "DATETIME"),
)
```
`DATETIME` is in `_SAFE_COL_TYPE_RE` allowlist (db.py line 52: `r"^(TEXT|INTEGER|REAL|BOOLEAN|DATETIME|VARCHAR\(\d{1,4}\))$"`).

**`_ADDITIVE_MIGRATIONS` registration** (db.py lines 178-188):
```python
_ADDITIVE_MIGRATIONS: tuple[tuple[str, tuple[tuple[str, str], ...]], ...] = (
    ("crypto_endpoints", _IDENTITY_COLUMNS),
    ...
    ("crypto_endpoints", _V54_SENSOR_COLUMNS),  # Phase 107 MODEL-01  <- last entry
)
```
Append one line:
```python
    ("sensor_tokens",    _V55_SENSOR_TOKEN_COLUMNS),  # Phase 113 AUTH-02
```

**`_ensure_columns` idempotency guarantee** (db.py lines 154-162):
```python
existing = {c["name"] for c in sa_inspect(engine).get_columns(table)}
with engine.connect() as conn:
    for col, col_type in expected:
        ...
        if col not in existing:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}"))
    conn.commit()
```
No custom logic needed — `_ensure_columns` handles existing-column skip automatically. The new column is NULL for all existing rows on first `init_db` after upgrade, satisfying the additive-only constraint (D-06).

---

### `quirk/models.py` (model, MODIFIED — add `revoked_at` column)

**Analog:** `quirk/models.py` lines 291-313 (`SensorToken` class)

**Current `SensorToken` definition** (models.py lines 291-313):
```python
class SensorToken(Base):
    __tablename__ = "sensor_tokens"

    id         = Column(Integer,     primary_key=True, autoincrement=True)
    sensor_id  = Column(
        String(36),
        ForeignKey("sensors.sensor_id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash = Column(String(64),  nullable=False, unique=True)
    created_at = Column(DateTime,    nullable=False)
```
Add one column after `created_at`:
```python
    revoked_at = Column(DateTime, nullable=True)  # None = active; set = revoked (Phase 113 AUTH-02)
```
`DateTime` is already imported at the models.py module level (same import used by `created_at`). `nullable=True` is mandatory for additive-only constraint and backward-compatibility (D-06).

---

### `quirk/cli/console_cmd.py` (service/CLI, MODIFIED — `revoke-sensor` subcommand)

**Analog:** `run_console` dispatch (console_cmd.py lines 69-120) + `_cmd_enroll` (lines 123-228)

**`run_console` subparser pattern** (console_cmd.py lines 80-114):
```python
import_p = sub.add_parser(
    "import-results",
    help="Import a .qpush air-gap file into the console",
)
import_p.add_argument("file", ...)
import_p.add_argument("--config", ...)

enroll_p = sub.add_parser(
    "enroll",
    help="Provision a new sensor ...",
)
enroll_p.add_argument("--sensor-id", ...)
enroll_p.add_argument("--segment", required=True, ...)
enroll_p.add_argument("--engagement", ...)
enroll_p.add_argument("--config", ...)
```
Add `revoke-sensor` subparser in the same block:
```python
revoke_p = sub.add_parser(
    "revoke-sensor",
    help="Revoke a sensor's push token (sensor is immediately rejected on next push)",
)
revoke_p.add_argument("sensor_id", help="Sensor UUID to revoke")
revoke_p.add_argument("--config", default="config.yaml", help="Console config.yaml path")
```

**`run_console` dispatch block** (console_cmd.py lines 116-120):
```python
args = parser.parse_args(argv)
if args.action == "import-results":
    _cmd_import_results(args)
elif args.action == "enroll":
    _cmd_enroll(args)
```
Extend:
```python
elif args.action == "revoke-sensor":
    _cmd_revoke_sensor(args)
```

**`_cmd_enroll` DB session pattern** (console_cmd.py lines 143-176) — copy this pattern for `_cmd_revoke_sensor`:
```python
# Lazy imports inside function (matches _cmd_enroll's pattern)
from sqlalchemy.orm import sessionmaker
from quirk.dashboard.api.deps import _default_db_path
from quirk.db import init_db
from quirk.models import SensorToken

db_path = _default_db_path()
engine = init_db(db_path)
Session = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)

with Session() as db:
    ...
    db.commit()
```

**`_cmd_enroll` error+exit pattern** (console_cmd.py lines 198-201):
```python
except IntegrityError:
    db.rollback()
    print("ERROR: sensor_id already enrolled", file=sys.stderr)
    sys.exit(1)
```
`_cmd_revoke_sensor` mirrors this for the "no active token" case:
```python
if not rows:
    print(f"ERROR: no active token found for sensor_id {sensor_id!r}", file=sys.stderr)
    sys.exit(1)
```

**WR-04 return-normally convention** (console_cmd.py lines 226-228):
```python
# WR-04: return normally — run_console returns after dispatch; sys.exit(0) is
# unnecessary and prevents atexit handlers + unit test without SystemExit monkeypatching.
```
`_cmd_revoke_sensor` returns normally on success (no `sys.exit(0)`).

**Enrollment printout that must be updated** (console_cmd.py lines 217-224):
```python
print(f"Enrollment token (one-time, for provisioning audit only — shown once):\n{raw_token}")
print(
    "\nNOTE: This enrollment token is NOT the push credential.\n"
    "      Sensor push authentication uses the CONSOLE'S shared API token\n"
    ...
    file=sys.stderr,
)
```
This text must be replaced to say the enrollment token IS the push credential (per RESEARCH §State of the Art — "Deprecated after this phase").

---

### `quirk/cli/sensor_cmd.py` (service/CLI, MODIFIED — credential semantics note)

**Analog:** same file lines 574-601

**Current `console_api_token` usage** (sensor_cmd.py lines 574, 596-601):
```python
api_token: str = sensor_cfg.get("console_api_token", "")
...
def _make_headers(b: bytes) -> dict:
    return {
        "Content-Type": "application/octet-stream",
        "X-Sensor-Signature": _sign(b, bytes.fromhex(hmac_key_hex)),
        "Authorization": f"Bearer {api_token}",
    }
```
The wire mechanism is unchanged — `console_api_token` is still read from `sensor.yaml` and sent as `Authorization: Bearer`. Only the **value** the operator places in that field changes: it is now the per-sensor enrollment token (D-10/D-11), not the shared `QUIRK_API_TOKEN`. No code change is required to the header construction. The required changes are:
1. Update any inline comment on `console_api_token` referencing the shared API token.
2. Ensure any enrollment-step docs in the file describe the per-sensor token.

---

### `docs/operators-guide.md` (documentation, MODIFIED)

**Analog:** existing §8.1.1 in the same file (v5.4 shared-token model description — the replacement target per RESEARCH §Sources / §State of the Art)

Replace the v5.4 shared-token model section entirely. The new section must cover (D-11):
1. What changed — per-sensor tokens replace the shared console token at `POST /api/sensor/push`.
2. What the operator must do on each sensor host — change `console_api_token` in `sensor.yaml` from the shared `QUIRK_API_TOKEN` value to the sensor's enrollment token (printed by `quirk console enroll`).
3. What to do if the raw enrollment token was lost — run `quirk console revoke-sensor <sensor_id>` then re-enroll (`quirk console enroll`) to mint a new token and sensor_id.
4. How the shared `QUIRK_API_TOKEN` (operator/dashboard auth) is unaffected.

---

### `tests/test_sensor_auth_per_sensor.py` (test, NEW — AUTH-04 gating test)

**Analog:** `tests/test_sensor_ingest.py` (entire file)

**`_app_with_db()` factory** (test_sensor_ingest.py lines 38-61) — copy verbatim:
```python
def _make_test_engine():
    engine = create_engine(
        "sqlite:///file::memory:?cache=shared&uri=true",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    return engine


def _app_with_db():
    engine = _make_test_engine()
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    return app, TestClient(app, raise_server_exceptions=False), engine, TestingSession
```
`Base.metadata.create_all(engine)` on a fresh in-memory DB creates `sensor_tokens` with the updated `SensorToken` model (including `revoked_at`), so the column is present from test start (RESEARCH Pitfall 4 avoided).

**`_seed_sensor()` helper** (test_sensor_ingest.py lines 103-123) — copy verbatim and add a companion `_seed_token()` helper:
```python
import hashlib, secrets

def _seed_token(TestingSession, sensor_id, raw_token=None, revoked=False):
    """Write a SensorToken row and return the raw token string."""
    if raw_token is None:
        raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    db = TestingSession()
    try:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        db.add(SensorToken(
            sensor_id=sensor_id,
            token_hash=token_hash,
            created_at=now,
            revoked_at=now if revoked else None,
        ))
        db.commit()
    finally:
        db.close()
    return raw_token
```

**Envelope builder + compress helpers** (test_sensor_ingest.py lines 68-100) — copy `_build_envelope()` and `_compress()` verbatim.

**Auth header pattern** (test_sensor_ingest.py lines 195-197):
```python
headers={"Authorization": "Bearer test-token"},
```
In the new test file the token value is the raw enrollment token, not `"test-token"`:
```python
raw_token = _seed_token(TestingSession, sensor_id="sensor-a")
headers={"Authorization": f"Bearer {raw_token}"},
```
The `QUIRK_API_TOKEN` env var is NOT set (or set to a distinct value) for tests in this file — the push route no longer uses it.

**Audit row assertion pattern** (test_sensor_ingest.py lines 336-348):
```python
ok_rows = (
    db.query(IntegrationDelivery)
    .filter(
        IntegrationDelivery.destination == "sensor_push",
        IntegrationDelivery.status == "ok",
    )
    .all()
)
assert len(ok_rows) >= 1, ...
```
Mirror this pattern for each AUTH-04 branch — filter on `error_summary` for the distinct cases:
- `error_summary == "unknown_sensor_token"` for 401 unknown
- `error_summary == "revoked_sensor_token"` for 401 revoked
- `error_summary == "sensor_id_mismatch"` for 403 mismatch
- `status == "ok"` + `error_summary is None` for 200 success

---

### `tests/test_sensor_ingest.py` (test, MODIFIED — update existing push tests)

**Change scope:** Every test that calls `client.post("/api/sensor/push", ...)` with `Authorization: Bearer test-token` will break after the router split because the push route no longer uses `require_auth` (which accepts `test-token` via `QUIRK_API_TOKEN`).

**Tests requiring `_seed_token` + header update** (from test_sensor_ingest.py):

| Test | Line | Seeded sensor_id | Required fix |
|---|---|---|---|
| `test_push_413_body_too_large` | 160 | none | Add any token seed; update header |
| `test_push_409_duplicate_payload` | 183 | `"sensor-dedup-01"` | `_seed_token(TestingSession, "sensor-dedup-01")` + update header |
| `test_push_200_accepted` | 247 | `"sensor-ok-01"` | `raw_token = _seed_token(TestingSession, "sensor-ok-01")` + update header |
| `test_audit_row_written` | 316 | `"sensor-audit-01"` | token seed + header update |
| `test_extra_fields_ignored` | 388 | `"sensor-extra-01"` | token seed + header update |
| `test_version_skew_graceful` | 414 | skew sensor | token seed + header update |
| `test_unknown_sensor_id_4xx` | 441 | none (intentional) | After auth swap this returns 401 (no token row); assertion `400 <= status < 500` still holds — update comment only |
| `test_push_422_replay_window` | 216 | `"nonexistent-sensor"` | Seed a real sensor + token; set `pushed_at` to stale; assertion remains 422 |

**`test_push_requires_auth`** (line 145) — sends no `Authorization` header; `require_sensor_auth` still returns 401 for a missing token. No change to assertion.

**`test_push_endpoint_exists`** (line 130) — no push call. No change needed.

**`_seed_token` helper location:** Add to `test_sensor_ingest.py` directly (alongside the existing `_seed_sensor`), or extract both to `tests/conftest.py` if the planner wants a shared fixture — either approach works with the existing `conftest.py` autouse isolation.

---

## Shared Patterns

### Bearer Token Extraction
**Source:** `quirk/dashboard/api/middleware/auth.py` line 31
**Apply to:** `sensor_auth.py`
```python
_bearer = HTTPBearer(auto_error=False)
```
Module-level singleton — prevents re-instantiation per request.

### Timing-Safe Comparison
**Source:** `quirk/dashboard/api/middleware/auth.py` lines 54, 61
**Apply to:** `sensor_auth.py` hash comparison
```python
hmac.compare_digest(x_api_key, configured)
```
Use `hmac.compare_digest(hashed, token_row.token_hash)` — both sides are 64-char hex strings.

### `IntegrationDelivery` Audit Row
**Source:** `quirk/dashboard/api/routes/sensor.py` lines 168-193
**Apply to:** `sensor_auth.py` (401 branches), `sensor.py` push handler (403 branch)
```python
def _audit(db, scan_id, status, error_summary=None):
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    row = IntegrationDelivery(
        scan_id=scan_id, finding_hash=None,
        destination="sensor_push", status=status,
        attempted_at=now, error_summary=error_summary,
    )
    db.add(row)
    try:
        db.commit()
    except Exception as exc:
        logger.warning("Audit row commit failed: %s", safe_str(exc))
```

### Lazy Imports Inside CLI Handler
**Source:** `quirk/cli/console_cmd.py` lines 143-152 (`_cmd_enroll`)
**Apply to:** `_cmd_revoke_sensor`
```python
import hashlib
import secrets
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from quirk.dashboard.api.deps import _default_db_path
from quirk.db import init_db
from quirk.models import Sensor, SensorToken
```
All imports inside the function body — matches the project's CLI lazy-import convention.

### `get_db` Dependency Injection
**Source:** `quirk/dashboard/api/deps.py` lines 38-58
**Apply to:** `sensor_auth.py` (inject `db` session)
```python
def get_db() -> Generator[Session, None, None]:
    ...
    yield db
```
`db: Session = Depends(get_db)` in `require_sensor_auth`'s signature provides a session FastAPI manages — same scope as the route handler's session (RESEARCH Pitfall 2 fix).

### Additive Migration Registration
**Source:** `quirk/db.py` lines 178-188
**Apply to:** `db.py` (new `_V55_SENSOR_TOKEN_COLUMNS` entry)
Append after `("crypto_endpoints", _V54_SENSOR_COLUMNS)`:
```python
("sensor_tokens", _V55_SENSOR_TOKEN_COLUMNS),  # Phase 113 AUTH-02
```

### Two-Router App Registration
**Source:** `quirk/dashboard/api/app.py` lines 114-115
**Apply to:** `app.py` (register `sensor_push_router`)
```python
application.include_router(jobs.read_router, prefix="/api")
application.include_router(jobs.write_router, prefix="/api")
```

---

## No Analog Found

All 10 files have close or exact analogs in the codebase. No files require falling back to RESEARCH.md patterns.

---

## Metadata

**Analog search scope:** `quirk/dashboard/api/`, `quirk/cli/`, `quirk/`, `tests/`
**Files scanned:** 10 source + 2 test files read directly
**Pattern extraction date:** 2026-05-26
