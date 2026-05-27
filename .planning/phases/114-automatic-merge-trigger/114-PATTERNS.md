# Phase 114: Automatic Merge Trigger - Pattern Map

**Mapped:** 2026-05-26
**Files analyzed:** 4 new/modified files (sensor.py modified, config.yaml modified, operators-guide.md modified, tests/test_auto_merge_trigger.py new)
**Analogs found:** 4 / 4

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `quirk/dashboard/api/routes/sensor.py` | route handler + background task | request-response + event-driven | self (existing sensor_push + _audit patterns) | exact — modify in place |
| `config.yaml` | config | transform | `quirk/notify/config.py` load pattern + existing `config.yaml` structure | role-match |
| `docs/operators-guide.md` | documentation | — | existing operators-guide sections | docs update |
| `tests/test_auto_merge_trigger.py` | test | request-response + event-driven | `tests/test_sensor_ingest.py` | exact — same push test harness |

---

## Pattern Assignments

### `quirk/dashboard/api/routes/sensor.py` — `sensor_push()` modification (route handler)

**Analog:** `quirk/dashboard/api/routes/sensor.py` (self) — existing handler, `_audit()` helper, `IntegrationDelivery` usage
**Also mirrors:** `quirk/cli/sensor_cmd.py` `_cmd_merge` L770–797 for db_path/output_dir resolution inside `run_auto_merge`

**Insertion point** (lines 203–204, current signature):
```python
@sensor_push_router.post("/sensor/push")
async def sensor_push(request: Request, db: Session = Depends(get_db)) -> dict:
```
Becomes (add `BackgroundTasks` param — FastAPI DI resolves automatically):
```python
@sensor_push_router.post("/sensor/push")
async def sensor_push(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> dict:
```
Add to imports block (lines 39–49):
```python
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
import os
from sqlalchemy import func
```

**Trigger scheduling — insertion point** (line 382, after final db.commit() succeeds, before return):
```python
    # D-01/D-03: evaluate trigger AFTER commit, BEFORE return.
    # Uses request-scoped db (still open; last_push_at just committed).
    db_path = _default_db_path()
    config_path = os.environ.get("QUIRK_CONFIG_PATH", "./config.yaml")
    if _eval_trigger_condition(db, config_path):
        background_tasks.add_task(run_auto_merge, db_path, config_path)

    return {"status": "accepted", "sensor_id": envelope.sensor_id, "payload_id": envelope.payload_id}
```
Add to imports:
```python
from quirk.dashboard.api.deps import _default_db_path
from quirk.models import IntegrationDelivery, MergeRun, Sensor, SensorToken
```

**_eval_trigger_condition helper** (new function, add near _sensor_status):
```python
def _load_auto_merge_config(config_path: str) -> dict:
    """Load console.auto_merge block from config.yaml.

    Priority: explicit path > QUIRK_CONFIG_PATH env var > ./config.yaml.
    Returns defaults when file absent, missing key, or malformed — never raises.
    Source: quirk/notify/config.py load_notifications_config L172-L184 pattern.
    """
    defaults: dict = {"enabled": True, "trigger_condition": "all-sensors-in"}
    effective_path = config_path or os.environ.get("QUIRK_CONFIG_PATH", "./config.yaml")
    if not effective_path or not os.path.isfile(effective_path):
        return defaults
    try:
        import yaml
        with open(effective_path, encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        block = (raw.get("console") or {}).get("auto_merge") or {}
        return {**defaults, **block}
    except Exception:
        return defaults


def _eval_trigger_condition(db: Session, config_path: str) -> bool:
    """Return True if auto-merge should be scheduled for this push (D-03/D-04/D-09).

    Reads config first (fast exit when disabled). Evaluates against current DB
    state using the just-committed push (last_push_at is fresh).
    Source: _sensor_status (L84) + merge/scan._build_coverage_warning (L34) patterns.
    """
    cfg = _load_auto_merge_config(config_path)
    if not cfg.get("enabled", True):
        return False

    condition = cfg.get("trigger_condition", "all-sensors-in")

    if condition == "all-sensors-in":
        # Active sensors: have at least one non-revoked SensorToken (D-04 + Pitfall 2)
        revoked_sub = (
            db.query(SensorToken.sensor_id)
            .filter(SensorToken.revoked_at.isnot(None))
            .subquery()
        )
        active_sensors = (
            db.query(Sensor)
            .filter(~Sensor.sensor_id.in_(
                db.query(SensorToken.sensor_id)
                .filter(SensorToken.revoked_at.isnot(None))
            ))
            .all()
        )
        if not active_sensors:
            return False
        if any(s.last_push_at is None for s in active_sensors):
            return False
        latest_merge = db.query(MergeRun).order_by(MergeRun.merged_at.desc()).first()
        if latest_merge is None:
            return True  # no prior merge — always trigger when all in
        latest_push = max(s.last_push_at for s in active_sensors)
        return latest_push > latest_merge.merged_at

    elif condition == "cadence-window":
        latest_merge = db.query(MergeRun).order_by(MergeRun.merged_at.desc()).first()
        if latest_merge is None:
            return True
        window_minutes = cfg.get("cadence_window_minutes")
        if window_minutes is None:
            first_sensor = db.query(Sensor).first()
            window_minutes = (first_sensor.expected_cadence_minutes or 1440) if first_sensor else 1440
        now = datetime.now(timezone.utc).replace(tzinfo=None)  # Pitfall 3: always naive UTC
        elapsed = (now - latest_merge.merged_at).total_seconds() / 60
        return elapsed >= window_minutes

    return False  # unknown condition → safe default off
```

**run_auto_merge background task** (new function, add after _eval_trigger_condition):
```python
def run_auto_merge(db_path: str, config_path: str) -> None:
    """Auto-merge background task — own session, own output_dir (D-02/D-11).

    Mirrors _cmd_merge's db_path/output_dir resolution exactly.
    Source: quirk/cli/sensor_cmd.py _cmd_merge L770-L797.
    All exceptions caught and surfaced via IntegrationDelivery audit row (D-10).
    Never propagates to the push transaction (D-11 structural isolation).
    """
    from quirk.merge.scan import merge_scan
    from quirk.db import get_session, init_db

    # Mirror _cmd_merge exactly (D-02)
    init_db(db_path)
    output_dir = os.path.dirname(os.path.abspath(db_path))

    try:
        with get_session(db_path) as db:
            # D-05: idempotent re-check — no-op if a MergeRun already covers latest pushes
            latest_merge = db.query(MergeRun).order_by(MergeRun.merged_at.desc()).first()
            if latest_merge is not None:
                latest_push = db.query(func.max(Sensor.last_push_at)).scalar()
                if latest_push is not None and latest_push <= latest_merge.merged_at:
                    return  # already covered — no-op (D-05)

            # D-12: reuse merge_scan() unchanged
            result = merge_scan(db, output_dir=output_dir)
            # get_session commit-on-exit persists MergeRun (merge_scan used flush)

            # D-10: success audit row (same session — Pitfall 6)
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            db.add(IntegrationDelivery(
                scan_id=result["scan_id"],
                finding_hash=None,
                destination="auto_merge",
                status="ok",
                attempted_at=now,
                error_summary=None,
            ))
            # get_session commit-on-exit persists both MergeRun + audit row atomically

    except Exception as exc:
        # D-10/D-11: failure surfaced via audit row; never touches push transaction
        logger.warning("Auto-merge failed: %s", safe_str(exc))
        try:
            init_db(db_path)
            with get_session(db_path) as audit_db:
                now = datetime.now(timezone.utc).replace(tzinfo=None)
                audit_db.add(IntegrationDelivery(
                    scan_id=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    finding_hash=None,
                    destination="auto_merge",
                    status="failed",
                    attempted_at=now,
                    error_summary=safe_str(exc),  # T-109-07: never str(exc)
                ))
        except Exception as audit_exc:
            logger.warning("Auto-merge audit row failed: %s", safe_str(audit_exc))
```

**_audit pattern** (lines 172–197, existing — extend destination set; no code change needed):
```python
# Source: sensor.py L172-L197
def _audit(db, scan_id, status, error_summary=None):
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    row = IntegrationDelivery(
        scan_id=scan_id,
        finding_hash=None,
        destination="sensor_push",   # run_auto_merge uses "auto_merge" as destination
        status=status,
        attempted_at=now,
        error_summary=error_summary,
    )
    db.add(row)
    try:
        db.commit()
    except Exception as exc:
        logger.warning("Audit row commit failed: %s", safe_str(exc))
```

**get_session commit-on-exit contract** (quirk/db.py L442–469):
```python
# Source: quirk/db.py L442-L469
@contextmanager
def get_session(db_path: str) -> Iterator:
    session = Session()
    try:
        yield session
        session.commit()   # <-- commit-on-exit: persists merge_scan's flush + audit row
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
```

**_cmd_merge db_path/output_dir resolution** (quirk/cli/sensor_cmd.py L770–797 — mirror exactly):
```python
# Source: quirk/cli/sensor_cmd.py L770-L797
def _cmd_merge(args):
    from quirk.merge.scan import merge_scan
    from quirk.dashboard.api.deps import _default_db_path
    from quirk.db import get_session, init_db

    db_path = args.db or _default_db_path()
    init_db(db_path)
    output_dir = os.path.dirname(os.path.abspath(db_path))
    with get_session(db_path) as db:
        result = merge_scan(db, stale_days=args.stale_days, output_dir=output_dir)
```

---

### `config.yaml` — new `console.auto_merge` sub-block (config)

**Analog:** `quirk/notify/config.py` config loading conventions; existing `config.yaml` top-level structure (assessment, scan, connectors, output, intelligence blocks)

**Existing config.yaml structure** (lines 1–57 — current top-level keys):
```yaml
assessment:   # top-level block
scan:
targets:
connectors:
output:
intelligence:
```

**New block to append** (follow existing flat-block conventions, no nesting beyond `console.auto_merge`):
```yaml
# Console behavior settings (Phase 114 AUTOMERGE-02)
console:
  auto_merge:
    enabled: true                        # default: ON (D-07)
    trigger_condition: all-sensors-in    # "all-sensors-in" | "cadence-window" (D-08)
    # cadence_window_minutes: 1440       # used only when trigger_condition: cadence-window
    #                                    # defaults to per-sensor expected_cadence_minutes
```

**Config loader pattern** (quirk/notify/config.py L159–184 — the exact pattern to follow):
```python
# Source: quirk/notify/config.py L159-L184
def load_notifications_config(path=None):
    effective_path = path or os.environ.get("QUIRK_CONFIG_PATH")
    if not effective_path or not os.path.isfile(effective_path):
        return None  # auto_merge version returns defaults dict instead of None
    try:
        with open(effective_path, encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        notify_raw = (raw or {}).get("notifications")
        if not notify_raw:
            return None
        return _parse_notify_cfg(notify_raw)
    except Exception:
        return None  # binary / malformed → silent fallback
```

Key differences for `_load_auto_merge_config` vs `load_notifications_config`:
- Returns a `dict` with defaults (not `None`) so callers get safe defaults without None checks.
- Sub-block key path: `(raw.get("console") or {}).get("auto_merge") or {}`.
- Env var fallback includes `./config.yaml` (not just `QUIRK_CONFIG_PATH`) to match the `sensor_push` call site.

---

### `tests/test_auto_merge_trigger.py` (new test file)

**Analog:** `tests/test_sensor_ingest.py` — same `_app_with_db()`, `_seed_sensor()`, `_seed_token()`, `_build_envelope()`, `_compress()` helper set; same `TestClient` push pattern; same `monkeypatch.delenv("QUIRK_API_TOKEN")` auth setup.

**Test harness setup** (test_sensor_ingest.py L40–63 — copy verbatim):
```python
# Source: tests/test_sensor_ingest.py L40-L63
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

**Sensor + token seed helpers** (test_sensor_ingest.py L105–154 — copy verbatim):
```python
# Source: tests/test_sensor_ingest.py L105-L125
def _seed_sensor(TestingSession, sensor_id="test-sensor-01", segment="dmz"):
    db = TestingSession()
    try:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        db.add(Sensor(
            sensor_id=sensor_id,
            segment=segment,
            engagement=None,
            enrolled_at=now,
            last_push_at=None,
            expected_cadence_minutes=1440,
            sensor_version=None,
        ))
        db.commit()
    finally:
        db.close()

# Source: tests/test_sensor_ingest.py L128-L154
def _seed_token(TestingSession, sensor_id, raw_token=None, revoked=False):
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

**Push call pattern** (test_sensor_ingest.py — the standard push sequence):
```python
# Source: tests/test_sensor_ingest.py — standard push via TestClient
envelope = _build_envelope(sensor_id=sensor_id, pushed_at=pushed_at)
body = _compress(envelope)
resp = client.post(
    "/api/sensor/push",
    content=body,
    headers={"Authorization": f"Bearer {raw_token}"},
)
assert resp.status_code == 200
data = resp.json()
assert data["status"] == "accepted"
```

**BackgroundTasks under TestClient — key behavior** (verified empirically, RESEARCH.md):
```python
# BackgroundTasks runs SYNCHRONOUSLY after response is sent under TestClient
# (starlette==0.49.3 / fastapi==0.128.8).
# Tests can assert MergeRun existence immediately after client.post() returns —
# no time.sleep, no async coordination needed.
db = TestingSession()
merge_runs = db.query(MergeRun).all()
assert len(merge_runs) == 1   # assert right after client.post() — synchronous
db.close()
```

**Config isolation pattern for auto_merge tests** (use tmp_path + monkeypatch):
```python
# Pattern: write a minimal config.yaml to tmp_path, set QUIRK_CONFIG_PATH
def _write_auto_merge_config(tmp_path, enabled=True, trigger_condition="all-sensors-in",
                              cadence_window_minutes=None):
    cfg = {
        "console": {
            "auto_merge": {
                "enabled": enabled,
                "trigger_condition": trigger_condition,
                **({"cadence_window_minutes": cadence_window_minutes}
                   if cadence_window_minutes else {}),
            }
        }
    }
    import yaml
    p = tmp_path / "config.yaml"
    p.write_text(yaml.dump(cfg))
    return str(p)

# In test:
def test_auto_merge_disabled(monkeypatch, tmp_path):
    config_path = _write_auto_merge_config(tmp_path, enabled=False)
    monkeypatch.setenv("QUIRK_CONFIG_PATH", config_path)
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)
    ...
```

**Six acceptance tests to implement** (CONTEXT.md Specifics + RESEARCH.md Validation Architecture):
```
test_all_sensors_in_triggers_merge     — AUTOMERGE-01: last enrolled sensor push → MergeRun exists
test_auto_merge_disabled               — AUTOMERGE-02a: OFF → no MergeRun after final push
test_merge_failure_isolated            — AUTOMERGE-02b: bad merge → push=accepted + failed IntegrationDelivery row
test_cadence_window_triggers           — AUTOMERGE-02c: push after window → MergeRun + coverage_warning
test_manual_merge_regression           — AUTOMERGE-03: _cmd_merge / merge_scan unchanged behavior
test_double_fire_harmless              — D-05: two simultaneous final pushes → at most harmless duplicate MergeRun
```

---

### `docs/operators-guide.md` (documentation update)

**Analog:** Existing `docs/operators-guide.md` section structure (no code patterns — documentation prose update only).

**Content to add:** Auto-merge toggle, two trigger conditions (`all-sensors-in` / `cadence-window`), default-ON behavior, how to disable, how to read `IntegrationDelivery` audit rows with `destination="auto_merge"`, note that `quirk sensor merge` remains available and unchanged.

---

## Shared Patterns

### IntegrationDelivery audit row
**Source:** `quirk/dashboard/api/routes/sensor.py` lines 172–197 (`_audit`) + lines 362–380 (inline ok row)
**Apply to:** `run_auto_merge` (both success and failure paths)
```python
# Source: sensor.py L184-L197
now = datetime.now(timezone.utc).replace(tzinfo=None)
row = IntegrationDelivery(
    scan_id=scan_id,
    finding_hash=None,
    destination="sensor_push",   # use "auto_merge" in run_auto_merge
    status=status,               # "ok" | "failed"
    attempted_at=now,
    error_summary=error_summary, # safe_str(exc) or None — NEVER str(exc)
)
db.add(row)
```

### safe_str exception scrubbing (T-109-07 — mandatory on all error paths)
**Source:** `quirk/util/safe_exc.py` (imported as `from quirk.util.safe_exc import safe_str`)
**Apply to:** Every `except Exception as exc:` block that writes to `IntegrationDelivery.error_summary` or calls `logger.warning`
```python
logger.warning("Auto-merge failed: %s", safe_str(exc))
# IntegrationDelivery error_summary:
error_summary=safe_str(exc)  # never: str(exc), repr(exc), f"{exc}"
```

### Naive UTC datetime convention (Pitfall 3)
**Source:** `quirk/dashboard/api/routes/sensor.py` line 209
**Apply to:** All datetime creation in `run_auto_merge`, `_eval_trigger_condition`, audit rows
```python
# Source: sensor.py L209
received_at = datetime.now(timezone.utc).replace(tzinfo=None)
# Pattern: always .replace(tzinfo=None) — SQLite DateTime columns are naive UTC throughout
```

### YAML config sub-block loading (never-raise contract)
**Source:** `quirk/notify/config.py` lines 172–184
**Apply to:** `_load_auto_merge_config` function
```python
# Source: quirk/notify/config.py L172-L184
effective_path = path or os.environ.get("QUIRK_CONFIG_PATH")
if not effective_path or not os.path.isfile(effective_path):
    return None  # (auto_merge version: return defaults dict)
try:
    with open(effective_path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    ...
except Exception:
    return None  # binary/malformed → silent fallback — never raises
```

### MergeRun watermark query
**Source:** `quirk/models.py` lines 339–358 (MergeRun columns), `quirk/merge/scan.py` L141–259 (merge_scan flush pattern)
**Apply to:** `_eval_trigger_condition` (all-sensors-in + cadence-window) and `run_auto_merge` (D-05 re-check)
```python
# Source: quirk/models.py L339-L358 — verified column names
latest_merge = db.query(MergeRun).order_by(MergeRun.merged_at.desc()).first()
# latest_merge is None if no prior merge has ever run — always trigger in that case
```

### init_db before get_session (mandatory)
**Source:** `quirk/cli/sensor_cmd.py` `_cmd_merge` L779–783
**Apply to:** `run_auto_merge` (both initial call and failure-path audit session)
```python
# Source: sensor_cmd.py L779-L783
db_path = args.db or _default_db_path()
init_db(db_path)             # always call init_db before get_session
output_dir = os.path.dirname(os.path.abspath(db_path))
with get_session(db_path) as db:
    result = merge_scan(db, stale_days=args.stale_days, output_dir=output_dir)
```

---

## No Analog Found

No files lack a close analog. All new/modified files have high-quality matches.

---

## Metadata

**Analog search scope:** `quirk/dashboard/api/routes/`, `quirk/cli/`, `quirk/merge/`, `quirk/notify/`, `quirk/models.py`, `quirk/db.py`, `quirk/dashboard/api/deps.py`, `tests/`, `config.yaml`
**Files read:** 9 source files
**Pattern extraction date:** 2026-05-26
