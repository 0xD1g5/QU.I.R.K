# Phase 70: Deferred BLOCKERs — API + QRAMM Model — Pattern Map

**Mapped:** 2026-05-15
**Files analyzed:** 9 (4 modify, 1 model edit, 4 test new/extend) + 1 ledger flip
**Analogs found:** 9 / 9 (every change has an in-repo precedent ≤ 250 lines away)

## File Classification

| New / Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---------------------|------|-----------|----------------|---------------|
| `quirk/db.py` (MODIFY — add `_SAFE_COL_TYPE_RE`, `_ensure_qramm_profiles_fk`, `connect` event listener) | DB / migration / engine wiring | DDL transform + event-driven | `quirk/db.py` itself (`_SAFE_COL_RE` L13; `_ensure_phase46_columns` L176-190; `_ensure_qramm_tables` L214-225; `get_engine` L30-39) | exact (self-precedent) |
| `quirk/models.py` (MODIFY — `QRAMMProfile.session_id` gets `ForeignKey(...)`) | ORM model | declarative-schema | `quirk/models.py` L137-155 (`QRAMMProfile` itself) — no existing `ForeignKey()` usage in file; SQLAlchemy idiom (research-sourced) | role-match |
| `quirk/dashboard/api/routes/qramm.py` (MODIFY — `delete_session` body reorder L414-421) | FastAPI route handler | request-response / CRUD-delete | Same file, same function (current body) + `qramm.py` L17-19, 49 logger idiom | exact (self-precedent) |
| `quirk/dashboard/api/routes/scan.py` (MODIFY — narrow `_qs_for_alg` except, add module logger L632-642) | FastAPI route handler / helper | transform with error handling | `quirk/dashboard/api/routes/qramm.py` L17-19, 49 (`logger = logging.getLogger(__name__)`); same-file `_qs_for_alg` (existing body) | role-match |
| `tests/test_qramm_delete_session_fk.py` (NEW — FK + delete_session integration) | pytest integration test | request-response via TestClient + ORM assert | `tests/test_qramm_router.py::test_delete_session_cascades_answers` L223-248; `_make_qramm_client` L20-43 | exact |
| `tests/test_db_migrations.py` (NEW or extend — `_SAFE_COL_TYPE_RE` matrix) | pytest unit test | DDL safety / parametrized regex | `tests/test_init_db_idempotent.py::test_all_ensure_functions_idempotent` L40-58 | role-match |
| `tests/test_cbom_scan_route.py` (EXTEND/NEW — `_qs_for_alg` tests) | pytest unit test | function-level monkeypatch | `tests/test_qramm_router.py` fixture style + standard `monkeypatch.setattr` (RESEARCH Wave 0 §) | role-match |
| `tests/test_qramm_models.py` (EXTEND — `PRAGMA foreign_key_list` assertion) | pytest unit test | schema-shape assertion | `tests/test_qramm_models.py::TestQRAMMProfileColumns` L132 (existing); `tests/test_init_db_idempotent.py` L30-37 (init_db + inspect pattern) | exact |
| `.planning/audit-2026-05-08/AUDIT-TASKS.md` (MODIFY — row flips CR-04/05/06/07) | docs / ledger | row replacement | Same file L84-87 (Phase 59/69 closure rows, evidence-column appended) | exact |

## Pattern Assignments

---

### `quirk/db.py` (DB / migration / engine wiring)

**Analog:** `quirk/db.py` itself — every new addition mirrors an existing helper within ≤ 200 lines.

**Imports pattern** (current L1-10 — extend with `event` + `Engine` already imported at L7):
```python
import os
import re
from contextlib import contextmanager
from typing import Iterator, Optional

from sqlalchemy import create_engine, inspect as sa_inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from quirk.models import Base
```
For Phase 70: add `from sqlalchemy import event` to the existing `sqlalchemy` import line (or a new line under it). `Engine` is already imported from `sqlalchemy.engine`.

**Allowlist constant pattern** (existing, L12-13 — template for `_SAFE_COL_TYPE_RE`):
```python
# Allowlist pattern for migration column names — prevents SQL injection via column interpolation.
_SAFE_COL_RE = re.compile(r"^[a-z][a-z0-9_]*$")
```
For Phase 70 (D-06) — add directly below:
```python
_SAFE_COL_TYPE_RE = re.compile(r"^(TEXT|INTEGER|REAL|BOOLEAN|DATETIME|VARCHAR\(\d{1,4}\))$")
```

**Migration helper "guard then DDL" pattern** (L93-106 `_ensure_v43_columns` — exact template for the D-06 guard insertion):
```python
def _ensure_v43_columns(engine) -> None:
    existing = {c["name"] for c in sa_inspect(engine).get_columns("crypto_endpoints")}
    with engine.connect() as conn:
        for col, col_type in _V43_COLUMN_DDLS.items():
            if not _SAFE_COL_RE.match(col):
                raise ValueError(f"Unsafe column name in migration: {col!r}")
            # PHASE 70 INSERT POINT (D-06):
            # if not _SAFE_COL_TYPE_RE.match(col_type):
            #     raise ValueError(f"Unsafe column type in migration: {col_type!r}")
            if col not in existing:
                conn.execute(text(f"ALTER TABLE crypto_endpoints ADD COLUMN {col} {col_type}"))
        conn.commit()
```
Replicate the inserted check verbatim inside `_ensure_phase41_columns` (L153-168), `_ensure_phase46_columns` (L176-190), and `_ensure_phase54_qramm_columns` (L198-211). Do **not** alter the four single-literal helpers per D-07 (`_ensure_identity_columns`, `_ensure_gcp_columns`, `_ensure_email_columns`, `_ensure_broker_columns`).

**Idempotent migration via PRAGMA introspection** (new — closest analog is the `sa_inspect(engine).get_columns(...)` early-return shape at L99 / L161 / L184 / L204):
```python
def _ensure_qramm_profiles_fk(engine) -> None:
    """Phase 70 BLOCK-07/D-01: retrofit FK on qramm_profiles.session_id."""
    with engine.connect() as conn:
        fk_rows = conn.execute(text("PRAGMA foreign_key_list('qramm_profiles')")).fetchall()
        if any(row[2] == "qramm_sessions" for row in fk_rows):
            return  # idempotent — FK already present
        # ... 12-step rebuild per RESEARCH Pattern 2 ...
```
The early-return shape mirrors `existing = {...}; if col not in existing` from every `_ensure_*` helper — same idempotency philosophy, different introspection mechanism (PRAGMA instead of `sa_inspect`).

**`connect` event listener** (NEW pattern — no existing in-repo precedent; canonical SQLAlchemy idiom per RESEARCH §"Code Examples"). Place **module-level** immediately after the `sqlalchemy` imports (L6-8 region):
```python
@event.listens_for(Engine, "connect")
def _sqlite_fk_pragma(dbapi_connection, connection_record):
    """Phase 70 BLOCK-07/D-02: enable per-connection FK enforcement."""
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys=ON")
    finally:
        cursor.close()
```

**init_db ordering pattern** (L256-285 — call site for the new migration):
```python
def init_db(db_path: str) -> Engine:
    engine = get_engine(db_path)
    with engine.connect() as conn:
        conn.commit()
    Base.metadata.create_all(engine, checkfirst=True)
    _ensure_identity_columns(engine)
    # ... existing chain ...
    _ensure_qramm_tables(engine)
    _ensure_phase54_qramm_columns(engine)
    # PHASE 70 INSERT POINT (D-01):
    # _ensure_qramm_profiles_fk(engine)
    _ensure_scheduled_tables(engine)
    # ...
    return engine
```

---

### `quirk/models.py` (ORM model)

**Analog:** Same file L137-155. No existing `ForeignKey()` usage in file — Phase 70 introduces it (per D-03).

**Current shape** (L137-155, target of edit at L148):
```python
class QRAMMProfile(Base):
    __tablename__ = "qramm_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, nullable=True)        # <-- REPLACE THIS LINE
    industry = Column(String(64), nullable=True)
    # ...
```

**Imports pattern** (current L4 — extend):
```python
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Float
# Phase 70 D-03: add ForeignKey
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Float, ForeignKey
```

**New session_id declaration** (per D-03, no in-repo precedent — SQLAlchemy canonical form):
```python
session_id = Column(
    Integer,
    ForeignKey("qramm_sessions.id", ondelete="SET NULL"),
    nullable=True,
)
```

---

### `quirk/dashboard/api/routes/qramm.py` (FastAPI route handler — `delete_session` reorder)

**Analog:** Same file, same function (current body L414-421).

**Current body** (L414-421 — to be replaced per D-04):
```python
@router.delete("/qramm/sessions/{session_id}", status_code=204)
def delete_session(session_id: int, db: Session = Depends(get_db)) -> None:
    session = _get_session_or_404(db, session_id)
    # Explicit cascade — SQLite FK enforcement is per-connection PRAGMA only.
    db.query(QRAMMAnswer).filter(QRAMMAnswer.session_id == session_id).delete()
    db.delete(session)
    db.commit()
    return None
```

**Imports already in place** (L32): `from quirk.models import QRAMMAnswer, QRAMMProfile, QRAMMSession` — `QRAMMProfile` already imported, no new imports needed.

**New body per D-04**:
```python
@router.delete("/qramm/sessions/{session_id}", status_code=204)
def delete_session(session_id: int, db: Session = Depends(get_db)) -> None:
    session = _get_session_or_404(db, session_id)
    # Phase 70 BLOCK-07/D-04: FK-safe ordering.
    session.profile_id = None
    db.flush()
    db.query(QRAMMProfile).filter(QRAMMProfile.session_id == session_id).delete()
    db.query(QRAMMAnswer).filter(QRAMMAnswer.session_id == session_id).delete()
    db.delete(session)
    db.commit()
    return None
```

---

### `quirk/dashboard/api/routes/scan.py` (FastAPI route handler — `_qs_for_alg` narrowing)

**Analog:** `quirk/dashboard/api/routes/qramm.py` L17-19, 49 — the module-logger pattern to copy.

**Logger pattern to mirror** (`qramm.py` L17-19, 49):
```python
import json
import logging
from datetime import datetime, timezone
# ...
router = APIRouter(dependencies=[Depends(require_auth), Depends(require_csrf)])
logger = logging.getLogger(__name__)
```

**Add to `scan.py`** (verified by RESEARCH §"Dependency Analysis" — no existing module logger). Insert `import logging` near L4 and `logger = logging.getLogger(__name__)` at module scope (after imports, before first function).

**Current `_qs_for_alg` body** (L632-642 — to be narrowed per D-05):
```python
def _derive_cbom(endpoints: list[CryptoEndpoint]) -> list[CbomComponent]:
    from quirk.cbom.classifier import classify_algorithm, quantum_safety_label

    def _qs_for_alg(alg: str) -> str:
        try:
            _, nist_level, _ = classify_algorithm(alg)
            raw = quantum_safety_label(nist_level)
        except Exception:                              # <-- REPLACE
            raw = "unknown"
        return _QS_DISPLAY.get(raw, "Unknown")
```

**Narrowed body per D-05**:
```python
        try:
            _, nist_level, _ = classify_algorithm(alg)
            raw = quantum_safety_label(nist_level)
        except (KeyError, TypeError, AttributeError) as e:
            logger.warning("classifier failed for alg=%r: %s", alg, e)
            raw = "unknown"
```

**Discretion (RESEARCH Open Question 2):** Consider lifting `_qs_for_alg` to module scope for direct unit-testability — recommended by RESEARCH, planner's call.

---

### `tests/test_qramm_delete_session_fk.py` (NEW — FK + delete_session integration)

**Analog:** `tests/test_qramm_router.py::test_delete_session_cascades_answers` L223-248 + `_make_qramm_client` L20-43.

**Fixture pattern to reuse** (L20-43):
```python
def _make_qramm_client() -> Tuple[TestClient, object]:
    from quirk.dashboard.api.app import create_app
    from quirk.dashboard.api.deps import get_db
    from quirk.models import Base

    db_name = f"test_qramm_{uuid.uuid4().hex}"
    engine = create_engine(
        f"sqlite:///file:{db_name}?mode=memory&cache=shared&uri=true",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def _override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[get_db] = _override_get_db
    return TestClient(app, headers={"X-Quirk-Request": "1"}), TestingSession
```

**Cascade-assertion pattern to mirror** (L223-248):
```python
def test_delete_session_cascades_answers():
    from quirk.models import QRAMMAnswer

    client, TestingSession = _make_qramm_client()
    sid = client.post("/api/qramm/sessions", json={}).json()["session_id"]
    client.post(f"/api/qramm/sessions/{sid}/answers", json={"answers": [...]})

    # pre-count
    db = TestingSession()
    try:
        pre_count = db.query(QRAMMAnswer).filter(QRAMMAnswer.session_id == sid).count()
    finally:
        db.close()
    assert pre_count >= 1

    assert client.delete(f"/api/qramm/sessions/{sid}").status_code == 204

    db = TestingSession()
    try:
        post_count = db.query(QRAMMAnswer).filter(QRAMMAnswer.session_id == sid).count()
    finally:
        db.close()
    assert post_count == 0
```

**Apply to Phase 70**: same shape with `QRAMMProfile` instead of/in addition to `QRAMMAnswer`. Plus a `PRAGMA foreign_keys` introspection check — see `tests/test_qramm_models.py` analog below.

---

### `tests/test_db_migrations.py` (NEW — `_SAFE_COL_TYPE_RE` matrix)

**Analog:** `tests/test_init_db_idempotent.py` L40-58 — same "iterate the `_ensure_*` family, exercise it, assert behavior" shape.

**Iterate-and-call pattern** (L40-58):
```python
def test_all_ensure_functions_idempotent(tmp_path: Path) -> None:
    db = tmp_path / "ensure.db"
    engine = init_db(str(db))
    ensure_funcs = [
        getattr(quirk_db_module, name)
        for name in dir(quirk_db_module)
        if name.startswith("_ensure_") and callable(getattr(quirk_db_module, name))
        and name != "_ensure_parent_dir"
    ]
    for fn in ensure_funcs:
        fn(engine)
        fn(engine)
```

**Apply to Phase 70** — monkeypatch a poisoned `col_type` into each DDL dict and assert `ValueError`:
```python
def test_v43_columns_rejects_poisoned_col_type(tmp_path, monkeypatch):
    from quirk.db import init_db, _ensure_v43_columns
    import quirk.db as quirk_db_module

    db = tmp_path / "poison.db"
    engine = init_db(str(db))
    monkeypatch.setitem(quirk_db_module._V43_COLUMN_DDLS, "evil_col", "TEXT; DROP TABLE x")
    with pytest.raises(ValueError, match="Unsafe column type"):
        _ensure_v43_columns(engine)
```
Repeat for `_PHASE41_COLUMN_DDLS`, `_PHASE46_COLUMN_DDLS`, `_PHASE54_QRAMM_ANSWER_DDLS`. Also a positive regression test that the real values still pass.

---

### `tests/test_cbom_scan_route.py` (EXTEND/NEW — `_qs_for_alg`)

**Analog:** standard `monkeypatch.setattr` + `pytest.raises` (no exact in-repo analog for testing a closure — RESEARCH Open Question 2 recommends lifting `_qs_for_alg` to module scope to enable direct import).

**If lifted** (recommended):
```python
import pytest
from quirk.dashboard.api.routes.scan import _qs_for_alg

def test_qs_for_alg_returns_unknown_on_keyerror(monkeypatch, caplog):
    def _raises(*_, **__): raise KeyError("missing")
    monkeypatch.setattr("quirk.cbom.classifier.classify_algorithm", _raises)
    with caplog.at_level("WARNING"):
        result = _qs_for_alg("RSA-2048")
    assert result == "Unknown"
    assert "classifier failed" in caplog.text

def test_qs_for_alg_propagates_runtime_error(monkeypatch):
    def _raises(*_, **__): raise RuntimeError("real bug")
    monkeypatch.setattr("quirk.cbom.classifier.classify_algorithm", _raises)
    with pytest.raises(RuntimeError):
        _qs_for_alg("RSA-2048")
```

Parametrize over `(KeyError, TypeError, AttributeError)` for the three narrowed types.

---

### `tests/test_qramm_models.py` (EXTEND — `PRAGMA foreign_key_list` assertion)

**Analog:** Same file — `TestQRAMMProfileColumns` L132 region; combined with `tests/test_init_db_idempotent.py::test_init_db_twice_on_fresh_db` L30-37 for the `init_db` + introspection shape.

**Init-db + introspect pattern** (`test_init_db_idempotent.py` L30-37):
```python
def test_init_db_twice_on_fresh_db(tmp_path: Path) -> None:
    db = tmp_path / "fresh.db"
    engine1 = init_db(str(db))
    snap1 = _column_snapshot(engine1)
    engine2 = init_db(str(db))
    snap2 = _column_snapshot(engine2)
    assert snap1 == snap2
```

**Apply to Phase 70** — PRAGMA-row assertion via raw `text()`:
```python
def test_qramm_profiles_has_db_level_fk(tmp_path):
    from quirk.db import init_db
    from sqlalchemy import text

    engine = init_db(str(tmp_path / "fk.db"))
    with engine.connect() as conn:
        rows = conn.execute(text("PRAGMA foreign_key_list('qramm_profiles')")).fetchall()
    # row[2] == referenced table
    assert any(row[2] == "qramm_sessions" for row in rows), rows


def test_connect_event_enables_fk_pragma(tmp_path):
    from quirk.db import init_db
    from sqlalchemy import text

    engine = init_db(str(tmp_path / "pragma.db"))
    with engine.connect() as conn:
        val = conn.execute(text("PRAGMA foreign_keys")).scalar()
    assert val == 1
```

---

### `.planning/audit-2026-05-08/AUDIT-TASKS.md` (row flip)

**Analog:** Same file L84-87 (Phase 59 / Phase 69 closure rows — evidence column populated inline).

**Current rows** (L180-183):
```
| api-cli-core/CR-04 | BLOCKER | QRAMMProfile.session_id is nullable and has no DB-level FK | — | [ ] deferred-v4.9 |
| api-cli-core/CR-05 | BLOCKER | delete_session does not clear qramm_sessions.profile_id link | — | [ ] deferred-v4.9 |
| api-cli-core/CR-06 | BLOCKER | Bare except: pass in classifier call drops findings silently | — | [ ] deferred-v4.9 |
| api-cli-core/CR-07 | BLOCKER | SQL injection guard on column names lacks col_type DDL fragment | — | [ ] deferred-v4.9 |
```

**Phase 69-style closure shape** (existing pattern at L86-87 — evidence appended after `closed`):
```
| scanners-cloud/CR-06 | BLOCKER | ... | Phase 69 (BLOCK-05) | [x] closed — closed by Phase 69 (BLOCK-05): <one-line resolution>. <Test ref>. |
```

**Apply to Phase 70** — flip the four rows and append per-row detail block (RESEARCH §"AUDIT-TASKS Row-Flip Pattern"):
```
| api-cli-core/CR-04 | BLOCKER | QRAMMProfile.session_id is nullable and has no DB-level FK | Phase 70 | [x] closed — closed by Phase 70 (BLOCK-07): ForeignKey(...,ondelete=SET NULL) on QRAMMProfile.session_id; _ensure_qramm_profiles_fk 12-step rebuild for existing DBs; per-connection PRAGMA foreign_keys=ON via connect event. Tests: tests/test_qramm_models.py::test_qramm_profiles_has_db_level_fk, ::test_connect_event_enables_fk_pragma |
```
(Repeat for CR-05/06/07 with matching one-line resolutions + test refs.)

---

## Shared Patterns

### Allowlist regex + fail-fast `ValueError`
**Source:** `quirk/db.py:13` (`_SAFE_COL_RE`) and every `_ensure_*_columns` helper (L60, L81, L102, L122, L141, L164, L186, L207).
**Apply to:** New `_SAFE_COL_TYPE_RE` and its four insertion points (`_ensure_v43_columns`, `_ensure_phase41_columns`, `_ensure_phase46_columns`, `_ensure_phase54_qramm_columns`).
```python
if not _SAFE_COL_RE.match(col):
    raise ValueError(f"Unsafe column name in migration: {col!r}")
```

### Module-level logger via stdlib `logging`
**Source:** `quirk/dashboard/api/routes/qramm.py:17-19, 49`.
**Apply to:** `quirk/dashboard/api/routes/scan.py` (`_qs_for_alg` warning) and any other new module needing `logger.warning(...)`.
```python
import logging
# ...
logger = logging.getLogger(__name__)
```

### UUID-named shared-cache in-memory SQLite test fixture
**Source:** `tests/test_qramm_router.py::_make_qramm_client` L20-43.
**Apply to:** Every new HTTP-level QRAMM test in this phase. The fixture's `Base.metadata.create_all(engine)` already picks up the D-03 ForeignKey, and the module-level `connect` event listener fires on this engine too (RESEARCH §"Test-engine subtlety" + Assumption A2).

### `tmp_path` + `init_db` + `inspect` for migration tests
**Source:** `tests/test_init_db_idempotent.py` L20-37.
**Apply to:** New `tests/test_db_migrations.py` and the `PRAGMA foreign_key_list` assertion in `tests/test_qramm_models.py`.

### Per-row evidence-column flip in AUDIT-TASKS
**Source:** `.planning/audit-2026-05-08/AUDIT-TASKS.md` L86-87 (Phase 69 BLOCK-05/06 closure rows).
**Apply to:** All four Phase 70 row flips (CR-04 / CR-05 / CR-06 / CR-07). Pattern: column 4 = `Phase 70`, column 5 = `[x] closed — closed by Phase 70 (BLOCK-NN): <resolution>. <test refs>`.

---

## No Analog Found

| File | Role | Data Flow | Reason / Compensating Source |
|------|------|-----------|-----------------------------|
| `quirk/db.py` `connect` event listener | engine wiring | event-driven | No existing SQLAlchemy `event.listens_for(Engine, ...)` hook anywhere in repo. Use SQLAlchemy 2.0 docs canonical idiom verbatim from RESEARCH §"Code Examples" (Pattern 1). |
| `quirk/db.py` `_ensure_qramm_profiles_fk` (12-step rebuild) | migration | DDL transform | No existing FK-retrofit precedent. Use SQLite §7 / RESEARCH Pattern 2 verbatim. Shape (function signature, `with engine.connect()`, `text(...)`, `conn.commit()`) still mirrors every `_ensure_*` helper in the same file. |
| `quirk/models.py` `ForeignKey` usage | ORM model | declarative-schema | No existing `ForeignKey()` call anywhere in `quirk/models.py` (verified by Read of L1-160). Use SQLAlchemy canonical form per D-03 / RESEARCH §"Code Examples". |

---

## Metadata

**Analog search scope:** `quirk/db.py`, `quirk/models.py`, `quirk/dashboard/api/routes/`, `tests/` (specifically `test_qramm_*.py`, `test_init_db_idempotent.py`, `test_db_*.py`, `test_cbom_*.py`).
**Files scanned (read):** 7 (`quirk/db.py`, `quirk/models.py` L1-160, `quirk/dashboard/api/routes/qramm.py` L1-60 + L400-460, `quirk/dashboard/api/routes/scan.py` L1-40 + L620-660, `tests/test_qramm_router.py` L1-80 + L200-280, `tests/test_qramm_models.py` L1-60, `tests/test_init_db_idempotent.py` full).
**Pattern extraction date:** 2026-05-15
