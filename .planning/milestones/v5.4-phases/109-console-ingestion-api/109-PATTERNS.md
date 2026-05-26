# Phase 109: Console Ingestion API - Pattern Map

**Mapped:** 2026-05-25
**Files analyzed:** 7
**Analogs found:** 7 / 7

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `quirk/dashboard/api/routes/sensor.py` | route | request-response | `quirk/dashboard/api/routes/scan.py` | exact (router-level auth, get_db, same M2M constraint) |
| `quirk/dashboard/api/app.py` | config | request-response | `quirk/dashboard/api/app.py` itself (modify) | exact |
| `quirk/cli/console_cmd.py` (_ingest_envelope + enroll) | service + CLI | CRUD | `quirk/cli/token_cmd.py` (token mint + atomic write) + `quirk/ticketing/base.py` (IntegrationDelivery) | role-match |
| `quirk/dashboard/api/schemas.py` (new PushEnvelope model) | model | transform | `quirk/dashboard/api/schemas.py` (ScanSubmitRequest inline Pydantic) | exact |
| IntegrationDelivery audit rows (sensor_push path) | service | CRUD | `quirk/ticketing/base.py` L104–151 | exact |
| `tests/test_sensor_ingest.py` | test | request-response | `tests/test_api_auth.py` | exact |
| `tests/scanner/test_phase57_invariants.py` (extend) | test | transform | itself (extend) | exact |

---

## Pattern Assignments

### `quirk/dashboard/api/routes/sensor.py` (NEW — route, request-response)

**Analog:** `quirk/dashboard/api/routes/scan.py` (M2M, no CSRF) + `quirk/dashboard/api/routes/schedules.py` (IntegrityError dedup)

**Imports pattern** (`scan.py` lines 1–48, `schedules.py` lines 15–34):
```python
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
```

**Router-level auth (M2M — no CSRF)** (`scan.py` line 81):
```python
# scan.py uses ONLY require_auth — no require_csrf (machine-to-machine)
router = APIRouter(dependencies=[Depends(require_auth)])

# schedules.py uses BOTH — browser-facing only, DO NOT copy for sensor.py
# router = APIRouter(dependencies=[Depends(require_auth), Depends(require_csrf)])
```

**get_db dependency injection pattern** (`schedules.py` lines 124, 131–134):
```python
@router.get("/schedules", response_model=ScheduleListResponse)
def list_schedules(db: Session = Depends(get_db)) -> ScheduleListResponse:
    ...

@router.post("/schedules", status_code=201, response_model=ScheduleResponse)
def create_schedule(
    payload: ScheduleCreateRequest,
    db: Session = Depends(get_db),
) -> ScheduleResponse:
    ...
```

**IntegrityError → fixed 409 (never stringify)** (`schedules.py` lines 151–162, comment T-63-16 / LEAK-02):
```python
db.add(row)
try:
    db.flush()
    db.commit()
    db.refresh(row)
except IntegrityError:
    db.rollback()
    # T-63-16 / LEAK-02: fixed message, never stringify the exception
    raise HTTPException(
        status_code=409,
        detail=format_error("SCHED-003"),
    )
```

**DateTime tz-naive convention** (`schedules.py` lines 69–71):
```python
def _utcnow_naive() -> datetime:
    """Return current UTC datetime as tz-naive (Pitfall 1 — matches Plan 02 convention)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
```

**async handler pattern for body read** (from RESEARCH.md Pattern 4 — no existing sync analog):
```python
@router.post("/sensor/push")
async def sensor_push(request: Request, db: Session = Depends(get_db)) -> dict:
    received_at = datetime.now(timezone.utc).replace(tzinfo=None)
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > 10 * 1024 * 1024:
        # Write audit row before raising
        raise HTTPException(status_code=413, detail="Payload too large (10 MB limit)")
    body = await request.body()
    if len(body) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Payload too large (10 MB limit)")
    ...
```

---

### `quirk/dashboard/api/app.py` (MODIFY — config, request-response)

**Analog:** `quirk/dashboard/api/app.py` itself

**Router import and include pattern** (lines 25–26, 108–115):
```python
# Line 25: extend the import tuple
from quirk.dashboard.api.routes import health, jobs, pdf, qramm, scan, schedules, trends

# Add sensor to import, then include_router inside create_app():
application.include_router(sensor.router, prefix="/api")
```

The new `include_router` line must be added alongside the existing ones at lines 108–115, before the static file mounts. The sensor router mounts at `/api` (same prefix as all other route modules), so `POST /api/sensor/push` resolves correctly.

---

### `quirk/cli/console_cmd.py` (MODIFY — service + CLI, CRUD)

Two modifications in this file: (1) add `quirk console enroll` sub-command, (2) replace `_ingest_envelope` stub body.

**Sub-command token mint pattern** (`quirk/cli/token_cmd.py` lines 53–110):
```python
# token_cmd.py: argparse sub-parser with --config flag
parser = argparse.ArgumentParser(prog="quirk token", ...)
subparsers = parser.add_subparsers(dest="action", required=True)
gen_parser = subparsers.add_parser("generate", ...)
gen_parser.add_argument("--config", default="config.yaml", ...)
```

**Atomic config write pattern** (`token_cmd.py` lines 13–50):
```python
dir_ = os.path.dirname(os.path.abspath(config_path))
fd, tmp = tempfile.mkstemp(dir=dir_, prefix=".quirk_config_")
try:
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        yaml.dump(raw, f, ...)
    os.replace(tmp, config_path)  # atomic on POSIX
except Exception:
    try:
        os.unlink(tmp)
    except OSError:
        pass
    raise
```

**Token generation (secrets.token_urlsafe)** (`token_cmd.py` line 100):
```python
token = secrets.token_urlsafe(32)
```

**DB session creation for CLI (no FastAPI context)** (`quirk/dashboard/api/deps.py` lines 38–58):
```python
# get_db() shows the session lifecycle; for CLI enroll, create without FastAPI:
from sqlalchemy.orm import sessionmaker
from quirk.db import init_db
from quirk.dashboard.api.deps import _default_db_path

engine = init_db(_default_db_path())
Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
with Session() as db:
    db.add(...)
    db.commit()
```

**`_ingest_envelope` stub to replace** (`console_cmd.py` lines 183–188 — current signature, must NOT change):
```python
def _ingest_envelope(
    envelope: dict,
    config_path: str,
    skip_replay_window: bool = False,
    qpush_sig: str | None = None,
) -> None:
```

Extend with optional `db=None` parameter per RESEARCH.md Pattern 7. The CLI air-gap path calls this function without a FastAPI session; the HTTPS route injects its `get_db` session to avoid a second connection per request.

---

### Pydantic `PushEnvelope` model in `quirk/dashboard/api/routes/sensor.py` (NEW — model, transform)

**Analog:** `quirk/dashboard/api/schemas.py` `ScanSubmitRequest` (lines 336–353) — inline Pydantic model in a route module

**`extra='ignore'` / ConfigDict pattern** (RESEARCH.md confirmed — `ScanSubmitRequest` does not use ConfigDict but Pydantic v2 `model_config` is the project standard):
```python
from pydantic import BaseModel, ConfigDict

class PushEnvelope(BaseModel):
    model_config = ConfigDict(extra="ignore")   # D-11: unknown fields silently dropped

    payload_id: str
    pushed_at: str
    schema_version: str
    sensor_version: str
    sensor_id: str
    segment: str
    findings: list = []
```

The `extra="ignore"` setting is the entire D-11 requirement. Unknown fields from newer sensor versions are dropped without error. `schema_version` / `sensor_version` mismatches are warn-only (log a warning, do not block ingest).

---

### IntegrationDelivery audit rows (sensor_push path)

**Analog:** `quirk/ticketing/base.py` lines 104–151 (`dispatch_finding` / `TicketingChannel`)

**Full write pattern** (`ticketing/base.py` lines 118–151):
```python
status = "ok"
error_summary: Optional[str] = None

try:
    _do_ingest(...)
except Exception as exc:
    status = "failed"
    error_summary = safe_str(exc)   # NEVER str(exc) or repr(exc) — ISEC-02
    logger.warning("Ingest failed: %s", error_summary)

row = IntegrationDelivery(
    scan_id=scan_id,          # pushed_at or received_at as fallback
    finding_hash=None,        # not used for sensor_push rows
    destination="sensor_push",
    status=status,
    attempted_at=datetime.now(timezone.utc).replace(tzinfo=None),
    error_summary=error_summary,
)
db.add(row)
try:
    db.commit()               # commit outside try — WR-01 pattern (base.py L149)
except Exception as exc:
    logger.warning("Audit row commit failed: %s", safe_str(exc))
```

**CRITICAL — write audit row BEFORE raising pre-ingest HTTPExceptions:** CONSOLE-04 requires a row on EVERY attempt including 413, 422, 409 (before `_ingest_envelope` is called). The ticketing base pattern writes after the try/except; for pre-ingest failures the route handler must write the audit row in its own except block before re-raising.

**Model fields** (`quirk/models.py` lines 251–266):
```python
# IntegrationDelivery columns:
id            = Column(Integer, primary_key=True, autoincrement=True)
scan_id       = Column(String(64), nullable=False, index=True)
finding_hash  = Column(String(64), nullable=True)
destination   = Column(String(64), nullable=False)   # "sensor_push"
status        = Column(String(16), nullable=False)   # "ok" | "failed"
attempted_at  = Column(DateTime,   nullable=False)
error_summary = Column(Text,       nullable=True)    # safe_str(exc) — never raw exc
```

---

### `tests/test_sensor_ingest.py` (NEW — test, request-response)

**Analog:** `tests/test_api_auth.py` lines 1–51

**In-memory DB + TestClient factory** (`test_api_auth.py` lines 28–51):
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from quirk.dashboard.api.app import create_app
from quirk.dashboard.api.deps import get_db
from quirk.models import Base

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
    return app, TestClient(app, raise_server_exceptions=False)
```

**Auth fixture pattern** (`test_api_auth.py` lines 58–72):
```python
@pytest.fixture
def authed_client(monkeypatch):
    """TestClient with QUIRK_API_TOKEN=test-token — auth enabled."""
    monkeypatch.setenv("QUIRK_API_TOKEN", "test-token")
    _app, tc = _app_with_db()
    return _app, tc
```

**401 gating test** (`test_api_auth.py` lines 303–338 gate pattern applied to new route):
```python
def test_push_requires_auth(monkeypatch):
    """CONSOLE-02: POST /api/sensor/push without auth returns 401."""
    monkeypatch.setenv("QUIRK_API_TOKEN", "test-token")
    _, client = _app_with_db()   # client has no auth headers by default
    resp = client.post("/api/sensor/push", content=b"data")
    assert resp.status_code == 401
```

**Route-introspection gate** (`test_api_auth.py` lines 303–338) — this existing test AUTOMATICALLY covers the new route once `sensor.router` is mounted. The new route must have `require_auth` at the `APIRouter(dependencies=[...])` level (not per-handler) or this gate fails CI.

---

### `tests/scanner/test_phase57_invariants.py` (EXTEND — test, transform)

**Analog:** itself (`tests/scanner/test_phase57_invariants.py` lines 1–80)

**`_strip_comments` tokenize helper** (lines 21–42 — reuse as-is, do not copy):
```python
# Already defined in the file. All new parametrize tests call the same helper.
def _strip_comments(src: str) -> str:
    """Strip Python comments accurately using the tokenize module."""
    ...
```

**`SCANNER_FILES` list pattern** (lines 12–18 — extend by adding new files):
```python
SCANNER_FILES = [
    REPO_ROOT / "quirk" / "scanner" / "jwt_scanner.py",
    # ... existing entries ...
]

# ADD alongside SCANNER_FILES (or extend it):
INGEST_FILES = [
    REPO_ROOT / "quirk" / "cli" / "console_cmd.py",
    REPO_ROOT / "quirk" / "dashboard" / "api" / "routes" / "sensor.py",
]
```

**AST gate parametrize test pattern** (lines 45–54 — mirror this structure):
```python
@pytest.mark.parametrize("ingest_file", INGEST_FILES, ids=lambda p: p.name)
def test_ingest_no_raw_exception_stringification(ingest_file):
    """CONSOLE-04: no str(exc) or repr(exc) in ingest path outside comments."""
    src = _strip_comments(ingest_file.read_text())
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

## Shared Patterns

### Authentication (router-level, anti-bypass)
**Source:** `quirk/dashboard/api/middleware/auth.py` lines 34–62
**Apply to:** `quirk/dashboard/api/routes/sensor.py` router declaration
```python
# require_auth implementation: timing-safe hmac.compare_digest, X-API-Key priority over Bearer
# D-02: passthrough when QUIRK_API_TOKEN is empty (auth disabled)
# D-04: raises 401 HTTPException when token is wrong or missing (never passes through)
def require_auth(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> None:
    configured = _get_configured_token()
    if not configured:
        return  # D-02: auth disabled
    x_api_key = request.headers.get("X-API-Key", "")
    if x_api_key:
        if hmac.compare_digest(x_api_key, configured):
            return
        raise HTTPException(status_code=401, detail=format_error("DASHBOARD-001"))
    if credentials is None:
        raise HTTPException(status_code=401, detail=format_error("DASHBOARD-001"))
    if not hmac.compare_digest(credentials.credentials, configured):
        raise HTTPException(status_code=401, detail=format_error("DASHBOARD-001"))
```

### DB Session (FastAPI dependency)
**Source:** `quirk/dashboard/api/deps.py` lines 38–58
**Apply to:** All handler functions in `sensor.py`
```python
def get_db() -> Generator[Session, None, None]:
    db_path = _default_db_path()
    engine = init_db(db_path)
    SessionLocal = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, expire_on_commit=False,
    )
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### Exception Scrubbing
**Source:** `quirk/util/safe_exc.py` (referenced throughout)
**Apply to:** `sensor.py`, `console_cmd.py` — every `except Exception as exc` block
```python
from quirk.util.safe_exc import safe_str

# In every except block that touches a response, log, or audit row:
error_summary = safe_str(exc)   # NEVER str(exc) or repr(exc)
```

### IntegrityError — Fixed Response String
**Source:** `quirk/dashboard/api/routes/schedules.py` lines 155–161 (T-63-16 / LEAK-02)
**Apply to:** `sensor.py` payload_id dedup 409 path
```python
except IntegrityError:
    db.rollback()
    # Fixed message only — never stringify the IntegrityError (LEAK-02)
    raise HTTPException(status_code=409, detail="Duplicate payload_id")
```

---

## No Analog Found

No files in Phase 109 are without an analog. All patterns have verified codebase counterparts.

---

## Metadata

**Analog search scope:**
- `quirk/dashboard/api/routes/` (scan.py, schedules.py, app.py, deps.py, middleware/auth.py)
- `quirk/cli/` (token_cmd.py, console_cmd.py)
- `quirk/ticketing/base.py`
- `quirk/models.py`
- `quirk/dashboard/api/schemas.py`
- `tests/test_api_auth.py`
- `tests/scanner/test_phase57_invariants.py`

**Files scanned:** 11
**Pattern extraction date:** 2026-05-25
