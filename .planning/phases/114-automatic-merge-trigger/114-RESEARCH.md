# Phase 114: Automatic Merge Trigger - Research

**Researched:** 2026-05-26
**Domain:** FastAPI BackgroundTasks, SQLAlchemy session lifecycle, push-trigger merge orchestration
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Auto-merge fires via a FastAPI `BackgroundTask` scheduled from `sensor_push()` after its own `db.commit()` succeeds (~`sensor.py:377`). Push returns `{"status": "accepted", ...}` immediately.
- **D-02:** The background task must open its own DB session via `get_session(db_path)` and resolve its own `output_dir`. Cannot reuse the request-scoped `Depends(get_db)` session. Mirror `_cmd_merge`'s db_path/output_dir resolution.
- **D-03:** Trigger evaluation happens on every successful push (both trigger modes push-evaluated). No standalone timer, poller, or scheduler thread.
- **D-04:** "all-sensors-in" fires when every non-revoked enrolled Sensor has a non-null `last_push_at` AND at least one push is newer than the latest `MergeRun.merged_at`. Excludes sensors with `revoked_at` set (Phase 113).
- **D-05:** Concurrency guard is an idempotent re-check inside the background task (no lock, no new schema). Task re-evaluates "is there a push newer than the latest MergeRun?" before merging. A covering MergeRun found → no-op.
- **D-06:** Residual TOCTOU window (two tasks both seeing newer push before either writes MergeRun) is accepted for v5.5. A duplicate MergeRun row is harmless (idempotent merge artifact).
- **D-07:** Auto-merge is ON by default. Operators disable via config. Toggle read at trigger-eval time per push; never affects in-flight pushes.
- **D-08:** Config exposes (a) enable/disable boolean and (b) `trigger_condition` selector with two values: `all-sensors-in` and `cadence-window`. Lives in existing `config.yaml` (exact key path is discretion). Follow existing `security.*` / console-config conventions.
- **D-09:** `cadence-window` is push-evaluated. A push triggers a merge when elapsed time since latest `MergeRun.merged_at` exceeds the configured window (default: per-sensor `expected_cadence_minutes`, 1440). Merges whatever has arrived; emits `coverage_warning` for missing sensors.
- **D-10:** Auto-merge failure writes `IntegrationDelivery` row (`destination="auto_merge"`, `status="failed"`, `error_summary=safe_str(exc)`) plus `logger.warning`. Successful auto-merge SHOULD also write an `ok` row.
- **D-11:** Merge runs entirely inside the background task's own try/except. No failure path can touch the push transaction (structural guarantee).
- **D-12:** `merge_scan()` is reused unchanged. `_cmd_merge` is not modified beyond what's needed. Existing v5.4 merge behavior preserved by construction.

### Claude's Discretion

- Exact config key path/names for enable flag and `trigger_condition` selector.
- Exact background-task DB session + `output_dir` wiring (mirror `_cmd_merge`).
- Whether successful auto-merge writes an `ok` IntegrationDelivery row and exact strings.
- Whether to add lightweight "last auto-merge result" surfacing to the registry response.
- Whether/how to expose the resolved cadence-window minutes (reuse `expected_cadence_minutes` vs a dedicated config key).

### Deferred Ideas (OUT OF SCOPE)

- Standalone scheduler/poller for true time-based cadence merging.
- Dashboard banner / React indicator for "last auto-merge failed".
- DB merge-lock row / advisory lock for hard double-merge guarantee.
- External cron + `quirk sensor merge` for cadence.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| AUTOMERGE-01 | Console automatically merges pushed results into one CBOM + quantum-readiness score once all enrolled sensors have checked in, without requiring `quirk sensor merge` | FastAPI BackgroundTasks in `sensor_push()` after commit; `merge_scan()` callable confirmed at `quirk/merge/scan.py:141` |
| AUTOMERGE-02 | Auto-merge configurable (enable/disable + trigger_condition); merge failure never blocks/fails/rolls back an in-flight sensor push | Config loaded via `QUIRK_CONFIG_PATH` / `yaml.safe_load` pattern; try/except in background task provides structural isolation |
| AUTOMERGE-03 | Manual `quirk sensor merge` still works, coexists with auto-merge, no regression to v5.4 behavior | `_cmd_merge` unchanged; `merge_scan()` unchanged; same function called by both paths |
</phase_requirements>

---

## Summary

Phase 114 is a pure backend integration — no new libraries, no schema changes, no UI work. The entire implementation is a new function `run_auto_merge()` wired into `sensor_push()` as a `BackgroundTask`, plus a config sub-block read at trigger-eval time. All the hard merge logic already exists in `merge_scan()` (Phase 110); this phase is plumbing, trigger logic, and config wiring.

The push handler (`sensor.py`) already has the exact insertion point: the final `db.commit()` on line 375, immediately before `return {"status": "accepted", ...}` on line 382. FastAPI `BackgroundTasks` is the right mechanism — it is already a Starlette primitive (no new dependency), and under `TestClient` it runs synchronously after the response is sent (verified empirically: Starlette 0.49.3 / FastAPI 0.128.8). This means acceptance tests can assert `MergeRun` existence immediately after the push response without any async coordination.

The config pattern is already established by `quirk/notify/config.py`: read a specific sub-block from `config.yaml` via `QUIRK_CONFIG_PATH` env var (falling back to `./config.yaml`), use `yaml.safe_load`, return a default-safe dataclass when the key is absent. The new `console.auto_merge.*` sub-block follows this exact pattern. No new config machinery is needed.

**Primary recommendation:** Wire `BackgroundTasks background_tasks` parameter into `sensor_push()`, schedule `run_auto_merge(db_path, config_path)` after the final commit, implement trigger-condition logic and idempotent re-check inside `run_auto_merge`, extend `IntegrationDelivery` with `destination="auto_merge"` rows. No schema changes. No new dependencies.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Trigger evaluation (all-sensors-in / cadence-window) | API / Backend | — | Push handler owns the trigger point; condition reads DB state |
| Merge execution (union CBOM + score) | API / Backend | — | `merge_scan()` is a standalone callable; runs in background task with own session |
| Failure surfacing | API / Backend | — | `IntegrationDelivery` audit rows already read by existing registry/dashboard |
| Config toggle + trigger-condition selector | API / Backend | — | `config.yaml` is server-side; read per-push at trigger-eval time |
| Manual merge regression | CLI | — | `_cmd_merge` calls same `merge_scan()` unchanged |
| Lab e2e script update | Lab / Shell | — | `distributed-e2e.sh` Step 3 currently runs `quirk sensor merge`; with auto-merge ON by default the step becomes optional, but the script must remain correct |

---

## Standard Stack

### Core (all already in project — no new pip deps)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `fastapi` `BackgroundTasks` | 0.128.8 (installed) | Schedule `run_auto_merge` after push commit | Built-in Starlette primitive; zero new dependency; runs synchronously under TestClient |
| `sqlalchemy` `sessionmaker` / `get_session` | already installed | Background task owns its own DB session | Request-scoped `Depends(get_db)` closes before background task runs |
| `yaml` (PyYAML) | already installed | Read `config.yaml` for auto-merge toggle | Same library used by `quirk/notify/config.py` and `quirk/config.py` |
| `quirk.merge.scan.merge_scan` | Phase 110 | The merge pipeline | Complete Option-A callable; `_cmd_merge` docstring explicitly designates it as the "v5.5 auto-trigger seam" |
| `quirk.models.IntegrationDelivery` | Phase 101 | Audit rows for auto-merge outcomes | Already used on `destination="sensor_push"` path; extend with `"auto_merge"` |
| `quirk.util.safe_exc.safe_str` | existing | Scrub exception strings before persisting | Mandatory per T-109-07; never stringify raw exception into audit row |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `quirk.dashboard.api.deps._default_db_path` | existing | Resolve DB path inside background task | Background task mirrors `_cmd_merge`'s db_path resolution |
| `quirk.db.get_session` | existing | Context-manager session for background task | Provides commit-on-exit / rollback-on-exception lifecycle matching `_cmd_merge` |
| `quirk.db.init_db` | existing | Ensure schema before opening background session | `_cmd_merge` calls `init_db(db_path)` before `get_session`; background task must do the same |

**Installation:** none required — all dependencies already installed.

---

## Package Legitimacy Audit

No new packages are installed in this phase. All dependencies are already present in the project.

| Package | Registry | Status | Disposition |
|---------|----------|--------|-------------|
| `fastapi` | pip | Already installed (0.128.8) | Approved — existing dep |
| `sqlalchemy` | pip | Already installed | Approved — existing dep |
| `PyYAML` | pip | Already installed | Approved — existing dep |

**Packages removed due to slopcheck:** none (no new packages introduced).

---

## Architecture Patterns

### System Architecture Diagram

```
POST /api/sensor/push
        |
        v
[require_sensor_auth] → request.state.sensor_id
        |
        v
[sensor_push() handler]
  ├── body_size_guard
  ├── decompress + parse PushEnvelope
  ├── replay_window check
  ├── sensor lookup (Sensor row)
  ├── _ingest_envelope() — flush only, no commit
  ├── add ok IntegrationDelivery row (destination="sensor_push")
  ├── db.commit()  ← D-01 insertion point
  ├── [D-01/D-03] evaluate trigger condition
  │       ├── read auto_merge config (enabled? trigger_condition?)
  │       ├── all-sensors-in: every non-revoked Sensor.last_push_at non-null
  │       │   AND max(last_push_at) > latest MergeRun.merged_at
  │       └── cadence-window: (now - latest MergeRun.merged_at) > window_minutes
  │
  ├── background_tasks.add_task(run_auto_merge, db_path, config_path)  ← if condition met
  │
  └── return {"status": "accepted", ...}
        |
        v  (after response sent — D-11 structural isolation)
[run_auto_merge(db_path, config_path)]
  ├── init_db(db_path)
  ├── with get_session(db_path) as db:
  │       ├── idempotent re-check (D-05)
  │       │   "is there a push newer than latest MergeRun.merged_at?"
  │       │   no → no-op (return)
  │       ├── merge_scan(db, output_dir=output_dir)  ← D-12 reuse unchanged
  │       │   → writes MergeRun row (flush), returns result dict
  │       │   [get_session commit-on-exit persists MergeRun]
  │       ├── on success: add IntegrationDelivery(destination="auto_merge", status="ok")
  │       └── on failure: add IntegrationDelivery(destination="auto_merge", status="failed",
  │                           error_summary=safe_str(exc)) + logger.warning
  └── (exceptions caught and surfaced via audit row — never propagate to push transaction)
```

### Recommended Project Structure (additive — no new top-level module)

```
quirk/dashboard/api/routes/
├── sensor.py                # [MODIFIED] sensor_push() gains BackgroundTasks param
                             # + _eval_trigger_condition() helper
                             # + run_auto_merge() background task function
quirk/notify/                # [REFERENCE PATTERN] config loading pattern reused
config.yaml                  # [MODIFIED] new console.auto_merge.* sub-block (optional)
docs/operators-guide.md      # [MODIFIED] auto-merge toggle, trigger conditions, audit rows
```

No new module needed. `run_auto_merge` lives in `sensor.py` (collocated with trigger logic, mirrors the Phase 109 pattern of keeping push-path logic together).

### Pattern 1: BackgroundTask injection in an async route

**What:** Add `background_tasks: BackgroundTasks` as a FastAPI-injected parameter alongside the existing `request: Request` and `db: Session`. FastAPI's DI resolves `BackgroundTasks` automatically.
**When to use:** After the final `db.commit()` succeeds and the trigger condition is met.
**Example:**
```python
# Source: FastAPI docs + Starlette 0.49.3 source (ASSUMED — training data, not Context7)
from fastapi import APIRouter, BackgroundTasks, Depends, Request
from sqlalchemy.orm import Session

@sensor_push_router.post("/sensor/push")
async def sensor_push(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> dict:
    # ... existing failure ladder unchanged ...
    
    # Final db.commit() — D-01 insertion point
    try:
        db.commit()
    except Exception as exc:
        # existing error handling
        ...

    # D-01/D-03: evaluate trigger AFTER commit, BEFORE return
    db_path = _default_db_path()
    config_path = os.environ.get("QUIRK_CONFIG_PATH", "./config.yaml")
    if _eval_trigger_condition(db, config_path):
        background_tasks.add_task(run_auto_merge, db_path, config_path)

    return {"status": "accepted", "sensor_id": ..., "payload_id": ...}
```

### Pattern 2: Background task with own session (D-02)

**What:** Mirror `_cmd_merge`'s exact db_path/output_dir resolution and session lifecycle. The request-scoped `get_db` session is closed before the background task runs.
**Example:**
```python
# Source: quirk/cli/sensor_cmd.py _cmd_merge (~L770) — VERIFIED in codebase
def run_auto_merge(db_path: str, config_path: str) -> None:
    """Auto-merge background task — own session, own output_dir (D-02)."""
    from quirk.merge.scan import merge_scan
    from quirk.db import get_session, init_db

    # Mirror _cmd_merge exactly
    init_db(db_path)
    output_dir = os.path.dirname(os.path.abspath(db_path))

    try:
        with get_session(db_path) as db:
            # D-05: idempotent re-check
            latest_merge = db.query(MergeRun).order_by(MergeRun.merged_at.desc()).first()
            latest_push = db.query(func.max(Sensor.last_push_at)).scalar()
            if latest_merge and latest_push and latest_push <= latest_merge.merged_at:
                return  # already covered — no-op

            result = merge_scan(db, output_dir=output_dir)
            # get_session commit-on-exit persists MergeRun written by merge_scan (flush)

            # D-10: success audit row (discretion — write it for symmetry)
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            db.add(IntegrationDelivery(
                scan_id=result["scan_id"],
                finding_hash=None,
                destination="auto_merge",
                status="ok",
                attempted_at=now,
                error_summary=None,
            ))
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
                    error_summary=safe_str(exc),
                ))
        except Exception as audit_exc:
            logger.warning("Auto-merge audit row failed: %s", safe_str(audit_exc))
```

**Critical detail:** `merge_scan()` calls `db.flush()` (not `db.commit()`). The `MergeRun` row is persisted by `get_session`'s commit-on-exit. This means the success audit row (added after `merge_scan()` returns inside the `with` block) is committed in the same transaction. [VERIFIED: quirk/merge/scan.py:245]

### Pattern 3: Trigger condition evaluation (all-sensors-in, D-04)

**What:** Read from the request-scoped `db` session before returning (DB still open, last_push_at just updated by `_ingest_envelope`).
**Example:**
```python
# Source: quirk/dashboard/api/routes/sensor.py _sensor_status + merge/scan.py _build_coverage_warning
def _eval_trigger_condition(db: Session, config_path: str) -> bool:
    """Return True if auto-merge should be scheduled for this push.
    
    Reads config first (fast exit when disabled). Then evaluates the
    condition against current DB state using the just-committed push.
    """
    cfg = _load_auto_merge_config(config_path)
    if not cfg.get("enabled", True):
        return False

    condition = cfg.get("trigger_condition", "all-sensors-in")

    if condition == "all-sensors-in":
        # All non-revoked enrolled sensors must have last_push_at set
        # AND at least one push is newer than the latest MergeRun.merged_at
        active_sensors = (
            db.query(Sensor)
            .outerjoin(SensorToken, Sensor.sensor_id == SensorToken.sensor_id)
            .filter(
                (SensorToken.revoked_at.is_(None)) | (SensorToken.sensor_id.is_(None))
            )
            .all()
        )
        # Simpler: query sensors with no active (non-revoked) token → consider them active
        # but CONTEXT says: honor revoked_at — exclude sensors whose token is revoked
        # See note in Pitfall 2 for the correct revocation query approach
        if not active_sensors:
            return False
        if any(s.last_push_at is None for s in active_sensors):
            return False
        # Check watermark: any push newer than latest MergeRun
        latest_merge = db.query(MergeRun).order_by(MergeRun.merged_at.desc()).first()
        if latest_merge is None:
            return True  # no prior merge — always trigger when all in
        latest_push = max(s.last_push_at for s in active_sensors)
        return latest_push > latest_merge.merged_at

    elif condition == "cadence-window":
        latest_merge = db.query(MergeRun).order_by(MergeRun.merged_at.desc()).first()
        if latest_merge is None:
            return True  # no prior merge — trigger immediately
        # Use configurable window_minutes or fall back to first sensor's cadence
        window_minutes = cfg.get("cadence_window_minutes")
        if window_minutes is None:
            # Fall back to per-sensor expected_cadence_minutes (first non-null found)
            first_sensor = db.query(Sensor).first()
            window_minutes = (first_sensor.expected_cadence_minutes or 1440) if first_sensor else 1440
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        elapsed = (now - latest_merge.merged_at).total_seconds() / 60
        return elapsed >= window_minutes

    return False  # unknown condition → safe default off
```

**Note on revoked-sensor exclusion:** `Sensor` has no `revoked_at` column — revocation lives in `SensorToken.revoked_at`. A sensor whose only token is revoked should be excluded from "all enrolled". The cleanest approach: query `Sensor` rows that have at least one active (non-revoked) `SensorToken` OR query all `Sensor` rows and cross-reference against revoked tokens. The planner should determine the exact query. See Pitfall 2.

### Pattern 4: Auto-merge config loading

**What:** Follow `quirk/notify/config.py` — read a sub-block from `config.yaml` via `QUIRK_CONFIG_PATH`, return a default-safe dict/dataclass when absent.
**Example:**
```python
# Source: quirk/notify/config.py _load_notify_config pattern — VERIFIED in codebase
def _load_auto_merge_config(config_path: str | None = None) -> dict:
    """Load console.auto_merge block from config.yaml.
    
    Returns defaults when the block is absent (auto_merge ON, all-sensors-in).
    Never raises — a missing/malformed config file is treated as defaults.
    """
    effective_path = config_path or os.environ.get("QUIRK_CONFIG_PATH", "./config.yaml")
    defaults = {"enabled": True, "trigger_condition": "all-sensors-in"}
    if not effective_path or not os.path.isfile(effective_path):
        return defaults
    try:
        import yaml
        with open(effective_path, encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        auto_merge_raw = (raw.get("console") or {}).get("auto_merge")
        if not auto_merge_raw:
            return defaults
        return {**defaults, **auto_merge_raw}
    except Exception:
        return defaults
```

**Proposed config.yaml addition:**
```yaml
# Console behavior settings (Phase 114)
console:
  auto_merge:
    enabled: true                        # default: ON (D-07)
    trigger_condition: all-sensors-in    # "all-sensors-in" | "cadence-window" (D-08)
    # cadence_window_minutes: 1440       # only used when trigger_condition: cadence-window
    #                                    # defaults to per-sensor expected_cadence_minutes
```

### Anti-Patterns to Avoid

- **Reusing the request-scoped session in the background task:** The `Depends(get_db)` session is a generator that closes in the `finally` block when the route function returns. By the time the background task runs, the session is closed and any ORM objects loaded from it are detached. Always open a new session in the background task via `get_session(db_path)`.
- **Calling `merge_scan()` without `init_db()` first:** `_cmd_merge` calls `init_db(db_path)` before `get_session`. Background task must do the same — `init_db` is idempotent and ensures `merge_runs` table exists.
- **Committing inside `run_auto_merge` before `merge_scan` returns:** `merge_scan` uses `db.flush()` not `db.commit()`. Committing early would leave the session in an inconsistent state. Let `get_session`'s commit-on-exit handle it.
- **Evaluating trigger condition inside the background task only:** The trigger condition should be evaluated in `sensor_push()` (in the request session, while last_push_at is fresh) to decide whether to schedule the task. The idempotent re-check inside `run_auto_merge` is a safety net for the TOCTOU window (D-05), not the primary gate.
- **Using `str(exc)` in audit rows:** Always `safe_str(exc)` — this is the T-109-07 pattern. `safe_str` truncates and scrubs sensitive fragments.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Union CBOM + score + MergeRun persistence | Custom merge function | `merge_scan()` at `quirk/merge/scan.py:141` | Complete implementation already exists; Phase 110 hardened it; D-12 mandates reuse |
| Post-response background execution | Thread + Event | `fastapi.BackgroundTasks` | Already the Starlette primitive; no new dependency; runs synchronously under TestClient |
| Session lifecycle in background | Manual SQLAlchemy connection | `quirk.db.get_session(db_path)` context manager | Handles commit-on-exit + rollback-on-exception; mirrors `_cmd_merge` exactly |
| Per-sensor push recency logic | Custom "all in" checker | `_build_coverage_warning` / `_sensor_status` patterns in `merge/scan.py` and `routes/sensor.py` | Already implemented; background task can use the same logic |
| Audit rows | Custom log table | `IntegrationDelivery` with `destination="auto_merge"` | Phase 101 table already exists; dashboard reads it; operator sees it with no new storage |

**Key insight:** This phase is almost entirely wiring. The merge pipeline, session factory, config loader pattern, and audit framework are all built. The new code is a trigger evaluator, a background task function, a config sub-block, and one test file.

---

## Common Pitfalls

### Pitfall 1: Session Closed Before Background Task Runs
**What goes wrong:** Background task tries to access ORM objects loaded in the request session (e.g. `sensor_row`, `db`) and gets `DetachedInstanceError` or silent stale data.
**Why it happens:** `Depends(get_db)` is a generator; its `finally: db.close()` runs when the route coroutine finishes (before the background task). The session is closed.
**How to avoid:** Pass only scalar values (`db_path: str`, `config_path: str`) to the background task. Never pass ORM objects or the request-scoped session.
**Warning signs:** `DetachedInstanceError` in background task logs; `SQLAlchemy session is already closed` warnings.

### Pitfall 2: Revoked-Sensor Exclusion Query
**What goes wrong:** "all-sensors-in" counts a sensor as "enrolled and not yet pushed" when its only token has `revoked_at` set. This blocks auto-merge permanently for decommissioned sensors.
**Why it happens:** `Sensor` has no `revoked_at` column. Revocation lives in `SensorToken.revoked_at`. A naive `db.query(Sensor).all()` includes revoked sensors.
**How to avoid:** The trigger condition must join or subquery `SensorToken` to exclude sensors whose token(s) are all revoked. One approach: a sensor is "active" if it has at least one `SensorToken` row with `revoked_at IS NULL`. This matches the `require_sensor_auth` middleware behavior (Phase 113).
**Warning signs:** Auto-merge never fires after a sensor is revoked; test AT-4 (near-simultaneous pushes) finds extra MergeRun rows when revoked sensors are present.

### Pitfall 3: MergeRun Watermark Comparison with Naive Datetimes
**What goes wrong:** Comparing `Sensor.last_push_at` (naive UTC stored by Phase 109) with `MergeRun.merged_at` (also naive UTC stored by Phase 110) works — but if any code path accidentally stores a timezone-aware datetime, `TypeError: can't compare offset-naive and offset-aware datetimes` is raised inside the trigger.
**Why it happens:** Both models use `DateTime` (no timezone column type in SQLite). Existing code consistently uses `.replace(tzinfo=None)` after `datetime.now(timezone.utc)`. The trigger condition must follow the same convention.
**How to avoid:** Always `.replace(tzinfo=None)` before storing or comparing. See `sensor.py:209` (`received_at = datetime.now(timezone.utc).replace(tzinfo=None)`) as the established pattern.
**Warning signs:** `TypeError` in trigger condition or background task on first real push.

### Pitfall 4: Config Load on Every Push (Performance)
**What goes wrong:** `_load_auto_merge_config` opens and parses `config.yaml` on every single push request. In a high-frequency environment this adds unnecessary I/O.
**Why it happens:** The config is read at trigger-eval time per push (D-07: "toggle is read at trigger-eval time, per push").
**How to avoid:** For v5.5 single-tenant single-console this is acceptable. The `yaml.safe_load` of a small file is sub-millisecond. Do NOT add caching without a clear need — it introduces staleness and complexity that are explicitly not required.
**Warning signs:** N/A for v5.5 scale.

### Pitfall 5: distributed-e2e.sh Step 3 Behavior
**What goes wrong:** With auto-merge ON by default, the `distributed-e2e.sh` "Step 3: merge" still runs `quirk sensor merge` manually. This produces a second `MergeRun` row (duplicate). The e2e test oracle checks for a merged CBOM — a duplicate row is harmless (D-06), but the script comment is now misleading.
**Why it happens:** The e2e script was written before auto-merge existed. Step 3 is no longer required for correctness but is also not wrong.
**How to avoid:** The CONTEXT.md requires keeping `lab.sh distributed e2e` green. The script must not *break* — and it won't, because `quirk sensor merge` is idempotent (produces a second MergeRun which is harmless). However: the operators-guide.md and possibly the e2e script comment should note that manual merge is no longer required with default config. The expected_results_distributed.md oracle should be updated to note that auto-merge fires after sensor-b push (before the explicit manual merge step). No functional change needed to make e2e pass.
**Warning signs:** e2e fails if a coverage_warning is expected but the background task already merged (producing the expected result before Step 3). In practice this means the assertions in the e2e pass regardless.

### Pitfall 6: `merge_scan()` Flush vs Commit — audit row order
**What goes wrong:** The success audit row is added to the session after `merge_scan()` returns. `merge_scan()` only calls `db.flush()`, not `db.commit()`. If `get_session`'s commit-on-exit fails, both the `MergeRun` row AND the audit row are rolled back together — this is correct behavior. But if the planner opens a second session for the audit row while the first session is still in the `with` block, a SQLite write-lock conflict may occur.
**How to avoid:** Add the success audit row to the same session as the `merge_scan()` call (inside the same `with get_session(db_path) as db:` block). The `get_session` commit-on-exit persists both the `MergeRun` (flushed by `merge_scan`) and the audit row atomically.

---

## Code Examples

Verified patterns from existing codebase:

### BackgroundTasks parameter injection (D-01)
```python
# Source: FastAPI docs pattern; tested empirically with fastapi==0.128.8 + starlette==0.49.3
# BackgroundTasks under TestClient runs SYNCHRONOUSLY after response is sent.
# Confirmed: task ran synchronously: ['ran'] — see research verification.
from fastapi import BackgroundTasks

@sensor_push_router.post("/sensor/push")
async def sensor_push(
    request: Request,
    background_tasks: BackgroundTasks,      # <-- add this param
    db: Session = Depends(get_db),
) -> dict:
    ...
    db.commit()
    # evaluate trigger here (uses request-scoped db — still open)
    if _eval_trigger_condition(db, config_path):
        background_tasks.add_task(run_auto_merge, db_path, config_path)
    return {"status": "accepted", ...}
```

### Background task session (D-02) — mirror _cmd_merge exactly
```python
# Source: quirk/cli/sensor_cmd.py _cmd_merge L770-L784 — VERIFIED
# Pattern: init_db first; get_session context manager; output_dir = dirname(abspath(db_path))
from quirk.dashboard.api.deps import _default_db_path
from quirk.db import get_session, init_db
from quirk.merge.scan import merge_scan

db_path = _default_db_path()
init_db(db_path)
output_dir = os.path.dirname(os.path.abspath(db_path))
with get_session(db_path) as db:
    result = merge_scan(db, stale_days=30, output_dir=output_dir)
    # get_session commit-on-exit persists MergeRun (merge_scan used flush)
```

### IntegrationDelivery audit row for auto_merge (D-10)
```python
# Source: quirk/dashboard/api/routes/sensor.py _audit() L172-L197 — VERIFIED
# Pattern: destination="auto_merge"; safe_str(exc) for error_summary
from quirk.models import IntegrationDelivery
from quirk.util.safe_exc import safe_str

now = datetime.now(timezone.utc).replace(tzinfo=None)
db.add(IntegrationDelivery(
    scan_id=scan_id_or_timestamp,
    finding_hash=None,
    destination="auto_merge",   # new destination value
    status="failed",            # or "ok"
    attempted_at=now,
    error_summary=safe_str(exc),  # never str(exc) or repr(exc)
))
```

### MergeRun watermark query (D-04/D-05)
```python
# Source: quirk/models.py MergeRun L339-L358 — VERIFIED column names
# MergeRun columns: id, scan_id, merged_at, endpoint_count, sensor_count, score, coverage_warning_json
latest_merge = db.query(MergeRun).order_by(MergeRun.merged_at.desc()).first()
# latest_merge is None if no prior merge has ever run
latest_merge_at = latest_merge.merged_at if latest_merge else None
```

### Config QUIRK_CONFIG_PATH pattern (D-08)
```python
# Source: quirk/notify/config.py L172-L184 — VERIFIED
# Priority: explicit path arg > QUIRK_CONFIG_PATH env var > ./config.yaml fallback
effective_path = config_path or os.environ.get("QUIRK_CONFIG_PATH", "./config.yaml")
if not effective_path or not os.path.isfile(effective_path):
    return defaults  # never raises
try:
    with open(effective_path, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    auto_merge_raw = (raw.get("console") or {}).get("auto_merge") or {}
    return {**defaults, **auto_merge_raw}
except Exception:
    return defaults  # malformed / binary file → safe defaults
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual `quirk sensor merge` required after every push cycle | Auto-merge via BackgroundTask after last-sensor push | Phase 114 (v5.5) | Operators in common deployment case no longer need a manual step |
| Shared console API token for all sensors | Per-sensor tokens with `revoked_at` (Phase 113) | Phase 113 (v5.5) | Revoked tokens must be excluded from "all-sensors-in" set |
| `distributed-e2e.sh` Step 3 is required | Step 3 is optional when auto-merge ON | Phase 114 (v5.5) | Script must remain valid (not removed) but docs should note auto-merge fires first |

**Deprecated/outdated:**
- Nothing in the existing codebase is deprecated by this phase. `_cmd_merge` / `quirk sensor merge` coexist unchanged (AUTOMERGE-03).

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `console.auto_merge` is the right YAML key path (following `security.*` convention) | Config surface | Low — key path is Claude's Discretion; planner picks the exact path |
| A2 | The success `IntegrationDelivery` row should be added inside the same `get_session` block as `merge_scan()` (not a separate session) | Code Examples | Medium — if planner uses separate session, risk of SQLite write-lock under concurrent pushes; recommend same session |
| A3 | "Active sensor" = sensor with at least one non-revoked SensorToken (for the all-sensors-in check) | Pitfall 2 / Pattern 3 | Medium — if a sensor has no token at all (enrollment token was deleted?), the query may mis-classify it; planner should verify the exact join |

**If this table is empty, all claims would be verified — but A1/A2/A3 represent edge-case decisions left to the planner as discretion.**

---

## Open Questions (RESOLVED)

1. **Revoked-sensor exclusion: sensor with no tokens**
   - What we know: `SensorToken` rows exist for each enrolled sensor (Phase 113 enrollment mints exactly one token per enrollment). A sensor may have its token revoked via `revoke-sensor`.
   - What's unclear: Can a sensor exist with zero `SensorToken` rows? (e.g. token record deleted manually from DB) — would such a sensor block the "all-sensors-in" trigger?
   - Recommendation: Define "active sensor" as `Sensor` rows where `NOT EXISTS (SELECT 1 FROM sensor_tokens WHERE sensor_id=? AND revoked_at IS NOT NULL)` OR `NOT EXISTS (SELECT 1 FROM sensor_tokens WHERE sensor_id=?)`. The planner should pick one consistent definition.

2. **cadence-window: per-sensor vs global window**
   - What we know: Each `Sensor` has `expected_cadence_minutes` (default 1440). D-09 says "default to the per-sensor `expected_cadence_minutes`".
   - What's unclear: Which sensor's cadence to use when multiple sensors have different cadences (e.g. sensor A cadence=1440, sensor B cadence=60).
   - Recommendation: Use the minimum across all active sensors (conservative — fires as soon as any sensor's window is exceeded), or use a dedicated `cadence_window_minutes` config key. Planner's call per Discretion.

3. **e2e script update scope**
   - What we know: `distributed-e2e.sh` Step 3 runs `quirk sensor merge`. With auto-merge ON, a MergeRun is already written before Step 3 runs. The second merge produces a harmless duplicate.
   - What's unclear: Whether the expected_results_distributed.md oracle needs to be updated to note the auto-merge MergeRun, or whether the Step 3 manual merge comment is sufficient.
   - Recommendation: Update the oracle to state "after sensor-b push completes, one MergeRun row exists (auto-merge); Step 3 produces a second MergeRun (manual, harmless duplicate)". Update the script comment but leave `quirk sensor merge` in place so the step demonstrates manual merge still works (AUTOMERGE-03 regression proof).

---

## Environment Availability

Step 2.6: The phase is pure Python/FastAPI code + config. No external services, runtimes, or CLI utilities beyond the project's existing stack.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11+ | Project | ✓ | 3.13.x (darwin) | — |
| FastAPI | BackgroundTasks | ✓ | 0.128.8 | — |
| Starlette | BackgroundTask primitives | ✓ | 0.49.3 | — |
| SQLite | DB layer | ✓ | built-in | — |
| PyYAML | Config loading | ✓ | installed | — |
| pytest | Test suite | ✓ | installed | — |

**Missing dependencies with no fallback:** none.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (installed) |
| Config file | `pytest.ini` or `pyproject.toml` (project root) |
| Quick run command | `pytest tests/test_auto_merge_trigger.py -x` |
| Full suite command | `pytest tests/ -x --ignore=tests/scanner` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AUTOMERGE-01 | After last enrolled sensor pushes, MergeRun exists without manual merge call | integration | `pytest tests/test_auto_merge_trigger.py::test_all_sensors_in_triggers_merge -x` | ❌ Wave 0 |
| AUTOMERGE-02a | With auto-merge OFF: final push produces no MergeRun | integration | `pytest tests/test_auto_merge_trigger.py::test_auto_merge_disabled -x` | ❌ Wave 0 |
| AUTOMERGE-02b | Merge failure leaves push accepted + writes failed IntegrationDelivery row | integration | `pytest tests/test_auto_merge_trigger.py::test_merge_failure_isolated -x` | ❌ Wave 0 |
| AUTOMERGE-02c | cadence-window mode triggers after window, emits coverage_warning | integration | `pytest tests/test_auto_merge_trigger.py::test_cadence_window_triggers -x` | ❌ Wave 0 |
| AUTOMERGE-03 | Manual `quirk sensor merge` produces identical output to auto-merge | unit | `pytest tests/test_auto_merge_trigger.py::test_manual_merge_regression -x` | ❌ Wave 0 |
| D-05 | Two near-simultaneous final pushes → at most harmless duplicate MergeRun | integration | `pytest tests/test_auto_merge_trigger.py::test_double_fire_harmless -x` | ❌ Wave 0 |

**BackgroundTasks under TestClient:** VERIFIED synchronous execution — task runs before `client.post()` returns. Tests can assert `MergeRun` existence immediately after the push response without `time.sleep` or async coordination. [Verified empirically: starlette==0.49.3 / fastapi==0.128.8]

### Sampling Rate
- **Per task commit:** `pytest tests/test_auto_merge_trigger.py -x`
- **Per wave merge:** `pytest tests/ -x --ignore=tests/scanner`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_auto_merge_trigger.py` — covers all 6 acceptance tests (AUTOMERGE-01/02/03 + D-05 + cadence-window + merge-failure-isolated)
- [ ] Test DB setup: reuse `_app_with_db()` + `_seed_sensor()` + `_seed_token()` patterns from `tests/test_sensor_ingest.py`
- [ ] `conftest.py` already provides `_isolate_quirk_db` autouse fixture — new test file inherits it automatically

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | BackgroundTask has no inbound auth surface |
| V3 Session Management | no | Background task uses own session (no request session leak) |
| V4 Access Control | no | Background task triggered only from authenticated push success path |
| V5 Input Validation | yes | Config values (trigger_condition, cadence_window_minutes) must be validated before use; unknown trigger_condition → log + default off |
| V6 Cryptography | no | No new crypto operations |

### Known Threat Patterns for This Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Raw exception in audit row | Information Disclosure | `safe_str(exc)` — mandatory, same as T-109-07 |
| Config file YAML injection | Tampering | `yaml.safe_load` (not `yaml.load`) — already the project convention |
| Background task escalation via merge failure | Denial of Service | try/except in `run_auto_merge`; failure writes audit row, never raises to caller; push response already returned |
| Trigger fires on revoked sensor's push | Spoofing | `require_sensor_auth` rejects revoked tokens before `sensor_push()` runs; revoked sensor's push is rejected at auth layer — never reaches trigger eval |

---

## Sources

### Primary (HIGH confidence)
- `quirk/dashboard/api/routes/sensor.py` — `sensor_push()` handler (read in full, L1-L382), exact commit location L375, `_audit()` L172, `BackgroundTasks` not yet imported
- `quirk/merge/scan.py` — `merge_scan()` full implementation (read in full, L1-L259), `_build_coverage_warning()` L34, `MergeRun` flush L245
- `quirk/cli/sensor_cmd.py` — `_cmd_merge` L770-L797 (db_path/output_dir resolution pattern, v5.5 seam comment)
- `quirk/models.py` — `Sensor` L269 (last_push_at L286, expected_cadence_minutes L287), `SensorToken` L291 (revoked_at L313), `MergeRun` L339, `IntegrationDelivery` L251
- `quirk/db.py` — `get_session` L443 (commit-on-exit pattern), `init_db` L392
- `quirk/dashboard/api/deps.py` — `_default_db_path()` L12, `get_db()` L38
- `quirk/notify/config.py` — config loading pattern L160-L184 (QUIRK_CONFIG_PATH priority, safe fallback)
- `quirk/config.py` — `SecurityCfg` L316, `AppConfig` L344, `config_from_dict` L374, `load_config` L491
- `tests/test_sensor_ingest.py` — test fixture patterns (`_app_with_db`, `_seed_sensor`, `_seed_token`, `_build_envelope`, `_compress`)
- `quantum-chaos-enterprise-lab/scripts/distributed-e2e.sh` — Step 3 manual merge at L128-L131
- FastAPI 0.128.8 + Starlette 0.49.3 empirical verification — BackgroundTasks runs synchronously under TestClient (confirmed via Python subprocess)

### Secondary (MEDIUM confidence)
- `quantum-chaos-enterprise-lab/expected_results_distributed.md` L96 — merge step oracle: `quirk sensor merge` on console produces one merged CBOM
- `tests/conftest.py` — `_isolate_quirk_db` autouse fixture (QUIRK_DB_PATH isolation)

### Tertiary (LOW confidence)
- none

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in project; no new dependencies
- Architecture: HIGH — insertion point, session lifecycle, and merge callable all verified in source
- Pitfalls: HIGH — session lifecycle (verified), revoked-sensor query (verified from models), naive datetime (verified from sensor.py pattern)
- Test design: HIGH — BackgroundTasks TestClient behavior verified empirically

**Research date:** 2026-05-26
**Valid until:** 2026-06-25 (stable — no fast-moving dependencies)
