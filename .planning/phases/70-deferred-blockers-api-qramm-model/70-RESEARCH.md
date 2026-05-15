# Phase 70: Deferred BLOCKERs — API + QRAMM Model - Research

**Researched:** 2026-05-15
**Domain:** SQLite schema migration (FK retrofit), SQLAlchemy event hooks, defensive DDL interpolation, FastAPI delete-route ordering
**Confidence:** HIGH

## Summary

Phase 70 closes four audit-deferred BLOCKERs (`api-cli-core/CR-04, CR-05, CR-06, CR-07`) by (1) retrofitting a real DB-level foreign key on `qramm_profiles.session_id` with per-connection PRAGMA enforcement, (2) re-ordering `delete_session` so the reverse `qramm_sessions.profile_id` pointer and any linked profile rows are cleared before the session is deleted, (3) narrowing a bare `except Exception` in `_qs_for_alg` to specific classifier exception types, and (4) adding a `_SAFE_COL_TYPE_RE` allowlist alongside the existing `_SAFE_COL_RE` guard in `quirk/db.py`. All implementation decisions are locked in CONTEXT.md (D-01 through D-07) — research focuses on validation architecture, gotchas, dependency surface, and the AUDIT-TASKS row-flip pattern.

**Primary recommendation:** Adopt the 3-plan split proposed in CONTEXT.md (70-01 FK + delete_session, 70-02 classifier except, 70-03 col_type allowlist) — the dependency analysis below confirms zero cross-plan coupling, matches Phase 69's one-row-family-per-plan precedent, and lets each plan ship a tight test bundle against its own success criterion.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| FK constraint on `qramm_profiles` | Database / Storage | — | Schema integrity is a DB-tier concern; SQLAlchemy model declares it, SQLite enforces it via PRAGMA |
| Per-connection `PRAGMA foreign_keys=ON` | Database / Storage (engine wiring) | — | Engine-level event listener; one source of truth in `quirk/db.py` |
| `delete_session` ordering | API / Backend | Database / Storage | Application-tier orchestration of FK-safe deletion; FK is safety-net, not cleanup driver |
| Classifier `except` narrowing | API / Backend | — | Route handler exception hygiene (`_qs_for_alg` in `scan.py`) |
| DDL `col_type` allowlist | Database / Storage (migration helpers) | — | Defense-in-depth in `quirk/db.py` migration framework |
| AUDIT-TASKS row flip | Process / Ledger | — | Phase closeout artifact, not runtime |

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**FK Enforcement (BLOCK-07)**
- **D-01:** Implement `_ensure_qramm_profiles_fk()` in `quirk/db.py` performing the SQLite 12-step table rebuild — create `qramm_profiles_new` with `session_id INTEGER REFERENCES qramm_sessions(id) ON DELETE SET NULL`, copy rows, drop old, rename. Wrap in a transaction with `PRAGMA foreign_keys=OFF` around the swap, re-enable on exit. Idempotent: skip when `PRAGMA foreign_key_list('qramm_profiles')` already lists the constraint. Called from `init_db()` after `_ensure_qramm_tables()` / `_ensure_phase54_qramm_columns()`.
- **D-02:** Enable `PRAGMA foreign_keys=ON` per connection via a SQLAlchemy `connect` event listener (single hook in `quirk/db.py`).
- **D-03:** Update `QRAMMProfile.session_id` in `quirk/models.py` from `Column(Integer, nullable=True)` to `Column(Integer, ForeignKey("qramm_sessions.id", ondelete="SET NULL"), nullable=True)` so `create_all` on fresh DBs produces the same constraint.

**delete_session Ordering (BLOCK-07)**
- **D-04:** New `delete_session` body order in `quirk/dashboard/api/routes/qramm.py`: (1) `session.profile_id = None`; (2) `db.flush()`; (3) delete `QRAMMProfile` rows where `session_id == session_id`; (4) delete `QRAMMAnswer` rows where `session_id == session_id`; (5) `db.delete(session)`; (6) `db.commit()`.

**Classifier except Narrowing (BLOCK-08)**
- **D-05:** Replace bare `except Exception` at `quirk/dashboard/api/routes/scan.py:640` (`_qs_for_alg`) with `except (KeyError, TypeError, AttributeError) as e:` — log via `logger.warning("classifier failed for alg=%r: %s", alg, e)` then return `"unknown"`. Other exception types propagate.

**col_type DDL Allowlist (BLOCK-08)**
- **D-06:** Introduce `_SAFE_COL_TYPE_RE = re.compile(r"^(TEXT|INTEGER|REAL|BOOLEAN|DATETIME|VARCHAR\(\d{1,4}\))$")` at the top of `quirk/db.py` alongside `_SAFE_COL_RE`. In every `_ensure_*_columns` helper that interpolates a `col_type` (currently `_ensure_v43_columns`, `_ensure_phase41_columns`, `_ensure_phase46_columns`, `_ensure_phase54_qramm_columns`), add `if not _SAFE_COL_TYPE_RE.match(col_type): raise ValueError(...)` immediately after the existing `_SAFE_COL_RE.match(col)` guard. Validate BEFORE the transaction opens.
- **D-07:** Helpers interpolating a literal `TEXT` (`_ensure_identity_columns`, `_ensure_gcp_columns`, `_ensure_email_columns`, `_ensure_broker_columns`) do NOT currently bind `col_type` from a variable — leave them as-is.

### Claude's Discretion
- Placement of the SQLAlchemy `connect` event listener (module-level vs inside `get_engine`/`init_db`).
- Whether the new migration uses `text()` strings or SQLAlchemy DDL constructs.
- Logger name in `_qs_for_alg` — reuse module logger if present; otherwise add `logger = logging.getLogger(__name__)`.

### Deferred Ideas (OUT OF SCOPE)
- Promoting `classify_algorithm()` to total function (Option C from discuss-phase).
- Centralizing all `_ensure_*_columns` helpers behind one migration framework.
- Sweeping `scan.py` for other broad `except Exception` clauses.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| BLOCK-07 | `QRAMMProfile.session_id` has DB-level FK; `delete_session` nulls reverse pointer | D-01/D-02/D-03 FK retrofit + PRAGMA; D-04 delete ordering; tests at `tests/test_qramm_router.py::test_delete_session*` and new `PRAGMA foreign_key_list` assertion |
| BLOCK-08 | Bare except in classifier replaced with specific logged exception; `col_type` validated before DDL interpolation | D-05 narrows to `(KeyError, TypeError, AttributeError)` + module logger in `scan.py`; D-06 adds `_SAFE_COL_TYPE_RE` to four `_ensure_*` helpers |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **PEP 8** for all Python.
- **Minimal diffs** — avoid unnecessary refactors. D-07 explicitly preserves this constraint.
- After changes: `python -m compileall` and run relevant tests.
- **Mandatory phase completion:** Obsidian phase note at `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-70-Deferred-BLOCKERs-API-QRAMM-Model.md`; update `docs/UAT-SERIES.md`; sync UAT-SERIES.md to Obsidian; commit `docs/UAT-SERIES.md`.
- **AUDIT-TASKS row flip:** rows `api-cli-core/CR-04`, `CR-05`, `CR-06`, `CR-07` must flip from `[ ] deferred-v4.9` to `[x] closed` with evidence in the same phase.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy | 2.0.48 (installed `[VERIFIED: python3 -c]`) | ORM + engine + event hooks | Already the project's data layer; `event.listens_for(Engine, "connect")` is canonical |
| SQLite (stdlib `sqlite3`) | bundled with Python 3.14.5 | Storage; FK enforcement via per-connection PRAGMA | Project DB engine — `connect_args={"check_same_thread": False}` already in use |
| pytest | already pinned | Test runner | All existing test files use pytest fixtures + `tmp_path` |
| re (stdlib) | — | Allowlist regex | `_SAFE_COL_RE` already uses stdlib `re`; same pattern extends to `_SAFE_COL_TYPE_RE` |
| logging (stdlib) | — | Structured warning for `_qs_for_alg` | `qramm.py` already does `logger = logging.getLogger(__name__)` at L49 — copy that pattern into `scan.py` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| FastAPI `TestClient` | already used | HTTP-level assertions in `tests/test_qramm_router.py` | Use for `delete_session` integration test |
| SQLAlchemy `inspect` / raw `text("PRAGMA foreign_key_list(...)")` | already used | Idempotency check + test assertion | Both the migration's idempotency check and the FK-constraint test query this |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Manual 12-step rebuild | Alembic | Project has zero Alembic adoption — introducing it for one migration violates D-07 minimal-diff philosophy |
| `text()` raw DDL | SQLAlchemy DDL constructs | Existing `_ensure_*` helpers all use `text(f"ALTER TABLE ...")` — match the convention (CONTEXT.md Discretion #2) |

**Version verification:** `python3 -c "import sqlalchemy; print(sqlalchemy.__version__)"` → `2.0.48`; SQLAlchemy 2.x `event.listens_for(Engine, "connect")` API has been stable since 1.4 `[VERIFIED: local Python env, 2026-05-15]`.

## Architecture Patterns

### System Architecture Diagram

```
                       ┌─────────────────────────────────┐
                       │      init_db(db_path) [L256]    │
                       └────────────────┬────────────────┘
                                        │
              ┌─────────────────────────┴────────────────────────┐
              │                                                  │
              ▼                                                  ▼
   ┌──────────────────┐                            ┌────────────────────────┐
   │ get_engine(path) │◄── @event.listens_for ─────┤ event hook (new, D-02) │
   │ create_engine    │   (engine, "connect")      │ PRAGMA foreign_keys=ON │
   └────────┬─────────┘                            └────────────────────────┘
            │
            ▼
   ┌────────────────────────────────────────────────────────────────┐
   │ Base.metadata.create_all(engine, checkfirst=True)              │
   │   – fresh DB: QRAMMProfile.session_id ForeignKey(...) (D-03)   │
   │     => qramm_profiles already has FK clause                    │
   └────────────────────────────┬───────────────────────────────────┘
                                │
                                ▼
   ┌──────────────────────────────────────────────────────────────┐
   │ _ensure_identity/gcp/v43/email/broker/phase41/phase46_columns│
   │ _ensure_qramm_tables                                         │
   │ _ensure_phase54_qramm_columns                                │
   │ _ensure_qramm_profiles_fk(engine)   ◄── NEW (D-01)           │
   │   1. PRAGMA foreign_key_list('qramm_profiles')               │
   │      → if FK row exists, return (idempotent)                 │
   │   2. PRAGMA foreign_keys=OFF                                 │
   │   3. BEGIN TRANSACTION                                       │
   │   4. CREATE TABLE qramm_profiles_new (... FK clause ...)     │
   │   5. INSERT INTO qramm_profiles_new SELECT * FROM old        │
   │   6. DROP TABLE qramm_profiles                               │
   │   7. ALTER TABLE qramm_profiles_new RENAME TO qramm_profiles │
   │   8. COMMIT                                                  │
   │   9. PRAGMA foreign_keys=ON                                  │
   └──────────────────────────────────────────────────────────────┘

         ┌───────────────────────────────────┐
HTTP ───►│ DELETE /api/qramm/sessions/{id}   │
         │ delete_session  (qramm.py L414)   │
         └────────────────┬──────────────────┘
                          │  (D-04 ordering)
                          ▼
       1. session.profile_id = None
       2. db.flush()                          ← so UPDATE precedes any DELETE
       3. db.query(QRAMMProfile).filter(session_id==sid).delete()
       4. db.query(QRAMMAnswer).filter(session_id==sid).delete()
       5. db.delete(session)
       6. db.commit()
```

### Component Responsibilities

| Component | File | Responsibility |
|-----------|------|----------------|
| `_ensure_qramm_profiles_fk` (new) | `quirk/db.py` | Idempotent 12-step rebuild adding FK to existing `qramm_profiles` |
| `connect` event listener (new) | `quirk/db.py` | Per-connection `PRAGMA foreign_keys=ON` |
| `QRAMMProfile.session_id` (edit) | `quirk/models.py` L148 | Declares `ForeignKey("qramm_sessions.id", ondelete="SET NULL")` for fresh-DB path |
| `delete_session` (edit) | `quirk/dashboard/api/routes/qramm.py` L414–421 | Re-ordered cleanup per D-04 |
| `_qs_for_alg` (edit) | `quirk/dashboard/api/routes/scan.py` L636–642 | Narrowed exception + log warning |
| `_SAFE_COL_TYPE_RE` (new) | `quirk/db.py` near L13 | Regex allowlist for DDL type fragment |
| Type guard in `_ensure_v43/_phase41/_phase46/_phase54_qramm_columns` | `quirk/db.py` L93–211 | `ValueError` raise on bad `col_type` |

### Pattern 1: Per-connection PRAGMA via SQLAlchemy event hook

**What:** Attach a `connect` event listener to the Engine (or `Engine` class) that issues `PRAGMA foreign_keys=ON` on each new DBAPI connection.
**When to use:** Always, when using SQLite where FK enforcement matters.
**Example:**
```python
# Source: SQLAlchemy 2.x docs — sqlite dialect "Foreign Key Support"
# https://docs.sqlalchemy.org/en/20/dialects/sqlite.html#foreign-key-support
from sqlalchemy import event
from sqlalchemy.engine import Engine

@event.listens_for(Engine, "connect")
def _sqlite_fk_pragma(dbapi_connection, connection_record):
    # Skip for non-sqlite (defensive — codebase is sqlite-only today)
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys=ON")
    finally:
        cursor.close()
```
**Placement decision (Discretion #1):** Attach at **module level** in `quirk/db.py` immediately after the `from sqlalchemy` imports. This makes the hook attach exactly once per process — attaching inside `get_engine` would re-register on every call, producing duplicate listeners. SQLAlchemy deduplicates by callable identity, so the practical effect is harmless, but module-level placement is the canonical idiom in the SQLAlchemy docs `[CITED: docs.sqlalchemy.org/en/20/dialects/sqlite.html#foreign-key-support]`.

### Pattern 2: SQLite 12-step table rebuild (FK retrofit)

**What:** SQLite does not support `ALTER TABLE ... ADD CONSTRAINT`. The canonical workaround is the "table rebuild" sequence.
**When to use:** Adding a FK or other column-level constraint to an existing table with data.
**Example:**
```python
# Source: https://sqlite.org/lang_altertable.html §7
# Mirrors the existing _ensure_*_columns shape (text() + connect/commit).
def _ensure_qramm_profiles_fk(engine) -> None:
    """Phase 70 BLOCK-07: retrofit FK on qramm_profiles.session_id.

    Idempotent: PRAGMA foreign_key_list returns rows for each FK on the table.
    If any row references qramm_sessions, the rebuild has already run.
    """
    with engine.connect() as conn:
        fk_rows = conn.execute(text("PRAGMA foreign_key_list('qramm_profiles')")).fetchall()
        if any(row[2] == "qramm_sessions" for row in fk_rows):  # row[2] = referenced table
            return

        # Per SQLite §7, disable FK enforcement during the swap so dependent
        # rows are not validated mid-rebuild.
        conn.execute(text("PRAGMA foreign_keys=OFF"))
        trans = conn.begin()
        try:
            conn.execute(text("""
                CREATE TABLE qramm_profiles_new (
                    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER REFERENCES qramm_sessions(id) ON DELETE SET NULL,
                    industry VARCHAR(64),
                    org_size VARCHAR(32),
                    data_sensitivity VARCHAR(32),
                    regulatory_obligations TEXT,
                    geographic_scope VARCHAR(32),
                    multiplier FLOAT,
                    created_at DATETIME
                )
            """))
            conn.execute(text(
                "INSERT INTO qramm_profiles_new "
                "(id, session_id, industry, org_size, data_sensitivity, "
                "regulatory_obligations, geographic_scope, multiplier, created_at) "
                "SELECT id, session_id, industry, org_size, data_sensitivity, "
                "regulatory_obligations, geographic_scope, multiplier, created_at "
                "FROM qramm_profiles"
            ))
            conn.execute(text("DROP TABLE qramm_profiles"))
            conn.execute(text("ALTER TABLE qramm_profiles_new RENAME TO qramm_profiles"))
            trans.commit()
        except Exception:
            trans.rollback()
            raise
        finally:
            conn.execute(text("PRAGMA foreign_keys=ON"))
        conn.commit()
```

### Pattern 3: Idempotent migration via PRAGMA introspection

Existing `_ensure_*` helpers use `sa_inspect(engine).get_columns(...)` for idempotency. For FK retrofit, `sa_inspect` does not surface FK rows reliably on SQLite — use `PRAGMA foreign_key_list('qramm_profiles')` directly. Row format: `(id, seq, table, from, to, on_update, on_delete, match)`. Index `[2]` is the referenced table; matching `"qramm_sessions"` confirms the constraint is present.

### Anti-Patterns to Avoid
- **Hand-rolling FK enforcement at the ORM layer:** Do not add SQLAlchemy `Session` event listeners or pre-delete validators. The DB-level FK + `delete_session` ordering is sufficient.
- **Catching the wrong exception narrowness:** Do not include `Exception` or `BaseException` in the tuple — that defeats D-05 entirely.
- **Re-registering the `connect` listener inside `get_engine`:** While SQLAlchemy deduplicates, the canonical idiom is module-level once.
- **Skipping idempotency check on the rebuild:** A second `init_db()` call must not recreate the table; the test suite calls `init_db` repeatedly across tests via `tmp_path` and explicit re-init (see `test_qramm_init_db_idempotent`).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| FK enforcement on SQLite | Custom Session event handler that simulates FK checks | Per-connection `PRAGMA foreign_keys=ON` via `event.listens_for(Engine, "connect")` | SQLite's native enforcement is the authoritative implementation; PRAGMA is one line |
| FK retrofit | Custom DDL builder | Raw `text()` strings matching existing `_ensure_*` convention (CONTEXT.md Discretion #2) | Project has zero precedent for DDL constructs; preserve minimal-diff |
| Type-fragment validation | Per-helper inline if/else | Single shared `_SAFE_COL_TYPE_RE` constant + `ValueError` raise | Matches `_SAFE_COL_RE` precedent at L13 (fail-fast, single source of truth) |
| Classifier error wrapping | Try/except inside `classify_algorithm` | Narrow `except` at the call site (`_qs_for_alg`) | D-05 explicitly keeps the classifier untouched (deferred ideas list — Option C is out of scope) |

**Key insight:** Every change in this phase has an established codebase pattern within ≤200 lines of the edit site. Reuse, do not invent.

## Runtime State Inventory

This phase touches the live `qramm_profiles` table schema; runtime state must be reasoned about.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `qramm_profiles` rows in any existing `data/quirk.db` SQLite file — these survive the migration via the `INSERT INTO ... SELECT *` copy step | Migration data copy preserves existing rows; no out-of-band data migration needed |
| Live service config | None — no n8n / external orchestration touches QRAMM tables | None — verified by `grep -rn "qramm_profiles" .` showing only Python source + tests |
| OS-registered state | None — QRAMM is purely in-process FastAPI; no schedulers or service registrations | None — verified by absence of any `pm2`/`systemd`/`launchd` artifact in repo |
| Secrets/env vars | None — FK retrofit and classifier hardening do not touch credentials | None |
| Build artifacts / installed packages | None — pure source edits to `quirk/db.py`, `quirk/models.py`, two route files; no `pyproject.toml` change | None |

**Canonical question answered:** After every file in the repo is updated, the only runtime system that still has the old (FK-less) schema is an existing on-disk `data/quirk.db`. The new `_ensure_qramm_profiles_fk` migration in `init_db()` handles that case — every code path that opens the DB goes through `init_db()`, so the rebuild runs on first open after upgrade.

## Common Pitfalls

### Pitfall 1: Existing `qramm_profiles` data lost during rebuild
**What goes wrong:** A naive `CREATE TABLE ... new; DROP TABLE; RENAME` drops data if the `INSERT INTO _new SELECT *` is omitted or column-mismatched.
**Why it happens:** Hand-typed column lists drift from the model.
**How to avoid:** Use the explicit column-name `INSERT INTO ... SELECT col1, col2, ...` form (see Pattern 2 example). Match column order exactly to the current `QRAMMProfile` model declaration in `quirk/models.py` L147–155.
**Warning signs:** Test that creates a profile, re-runs `init_db()`, then asserts profile still readable — should be one of the new tests.

### Pitfall 2: `PRAGMA foreign_keys=ON` flips existing test expectations
**What goes wrong:** Tests that previously inserted orphan rows (relying on FK-OFF behavior) start failing after D-02 lands.
**Why it happens:** SQLite FKs were never enforced; the codebase developed against an FK-OFF world.
**How to avoid:** Run the full QRAMM test suite (`pytest tests/test_qramm_*.py -x`) before and after the PRAGMA hook lands. Any failure is itself a finding — per CONTEXT.md D-02, any test that depended on dangling FK behavior is a bug to fix, not a reason to roll back.
**Warning signs:** Test failures with `sqlite3.IntegrityError: FOREIGN KEY constraint failed` after the hook lands. Audit of `tests/test_qramm_*.py` shows no obvious dangling-FK tests, but verification phase must confirm full suite green.

### Pitfall 3: `PRAGMA foreign_keys` is a no-op inside a transaction
**What goes wrong:** SQLite ignores `PRAGMA foreign_keys=OFF` if issued inside an open transaction.
**Why it happens:** Documented SQLite behavior `[CITED: sqlite.org/pragma.html#pragma_foreign_keys]` — the PRAGMA only takes effect outside a transaction.
**How to avoid:** Issue `PRAGMA foreign_keys=OFF` **before** `conn.begin()`, and `PRAGMA foreign_keys=ON` **after** the transaction commits/rolls back. The example code in Pattern 2 follows this ordering.
**Warning signs:** Migration runs but FK rows in dependent tables fail validation mid-rebuild.

### Pitfall 4: `delete_session` ordering fails if `flush()` is omitted
**What goes wrong:** Steps 1+3 in D-04 (null `profile_id`, then delete profile) — if the `flush()` between them is skipped, SQLAlchemy may reorder the UPDATE and DELETE statements, and the DELETE could fire while the FK still points at the about-to-be-deleted profile, raising `IntegrityError`.
**Why it happens:** SQLAlchemy unit-of-work batches statements; the explicit `flush()` is what guarantees the UPDATE precedes the DELETE.
**How to avoid:** Keep `db.flush()` as step 2 verbatim per D-04. Test fixture must exercise the path with FKs enforced.
**Warning signs:** Test passes locally without flush() (because session is sqlite-FK-naive) but fails after D-02 lands.

### Pitfall 5: `_qs_for_alg` exception list too narrow / too broad
**What goes wrong:** Including `ValueError` swallows real bugs; excluding `AttributeError` lets real None-dereferences crash the route.
**Why it happens:** Classifier returns `_FALLBACK` for unknown input rather than raising — so the most likely real failure modes are non-string input (`TypeError`), missing dict keys in `quantum_safety_label` (`KeyError`), or None attribute access (`AttributeError`).
**How to avoid:** Use exactly `(KeyError, TypeError, AttributeError)` per D-05. The classifier source at `quirk/cbom/classifier.py:204` shows `classify_algorithm` is total over `str | None`, so any actual exception originates downstream in `quantum_safety_label`.
**Warning signs:** Test injects each of the three exception types via monkeypatched `classify_algorithm` and verifies (a) warning logged, (b) return value `"unknown"`, (c) other exceptions (e.g., `RuntimeError`) propagate.

### Pitfall 6: `_SAFE_COL_TYPE_RE` regex over- or under-matches
**What goes wrong:** Pattern too permissive (matches `TEXT; DROP TABLE`) or too strict (rejects existing `VARCHAR(16)`).
**Why it happens:** Anchored regex without proper grouping.
**How to avoid:** The CONTEXT.md D-06 regex `r"^(TEXT|INTEGER|REAL|BOOLEAN|DATETIME|VARCHAR\(\d{1,4}\))$"` covers all current literal values in `quirk/db.py`:
  - `_V43_COLUMN_DDLS`: `TEXT`, `VARCHAR(16)` — both match
  - `_PHASE41_COLUMN_DDLS`: `VARCHAR(32)` — matches
  - `_PHASE46_COLUMN_DDLS`: `BOOLEAN` — matches
  - `_PHASE54_QRAMM_ANSWER_DDLS`: `TEXT` — matches
  Verified manually `[VERIFIED: grep of dict literals in quirk/db.py L87-211]`.
**Warning signs:** First post-change `init_db()` raises `ValueError("Unsafe column type ...")` on a known-good value.

## Code Examples

### Module-level `connect` listener (D-02)
```python
# quirk/db.py — near top of file, after imports
from sqlalchemy import event
from sqlalchemy.engine import Engine

@event.listens_for(Engine, "connect")
def _sqlite_fk_pragma(dbapi_connection, connection_record):
    """Phase 70 BLOCK-07/D-02: enable FK enforcement per connection.

    SQLite FK constraints are declared at table-create time but only enforced
    when this PRAGMA is set. Without it, ON DELETE SET NULL is documentation.
    """
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys=ON")
    finally:
        cursor.close()
```

### Model edit (D-03)
```python
# quirk/models.py L148 — replace
session_id = Column(Integer, nullable=True)
# with
session_id = Column(
    Integer,
    ForeignKey("qramm_sessions.id", ondelete="SET NULL"),
    nullable=True,
)
```
Requires adding `ForeignKey` to the import line at top of `quirk/models.py`.

### `delete_session` body (D-04)
```python
# quirk/dashboard/api/routes/qramm.py L414-421 — replace body
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

### `_qs_for_alg` narrowing (D-05)
```python
# quirk/dashboard/api/routes/scan.py — add module logger near top of file
import logging
logger = logging.getLogger(__name__)

# Then L632-642 — replace body
def _qs_for_alg(alg: str) -> str:
    try:
        _, nist_level, _ = classify_algorithm(alg)
        raw = quantum_safety_label(nist_level)
    except (KeyError, TypeError, AttributeError) as e:
        logger.warning("classifier failed for alg=%r: %s", alg, e)
        raw = "unknown"
    return _QS_DISPLAY.get(raw, "Unknown")
```

### `_SAFE_COL_TYPE_RE` guard (D-06)
```python
# quirk/db.py — near L13
_SAFE_COL_RE = re.compile(r"^[a-z][a-z0-9_]*$")
_SAFE_COL_TYPE_RE = re.compile(r"^(TEXT|INTEGER|REAL|BOOLEAN|DATETIME|VARCHAR\(\d{1,4}\))$")

# Then in each of _ensure_v43_columns / _ensure_phase41_columns /
# _ensure_phase46_columns / _ensure_phase54_qramm_columns, immediately
# after the existing _SAFE_COL_RE.match(col) check:
for col, col_type in _V43_COLUMN_DDLS.items():
    if not _SAFE_COL_RE.match(col):
        raise ValueError(f"Unsafe column name in migration: {col!r}")
    if not _SAFE_COL_TYPE_RE.match(col_type):
        raise ValueError(f"Unsafe column type in migration: {col_type!r}")
    if col not in existing:
        conn.execute(text(f"ALTER TABLE crypto_endpoints ADD COLUMN {col} {col_type}"))
```

## Dependency Analysis

### `col_type`-interpolating helpers (D-06 scope)
Verified by reading `quirk/db.py` L87–211:

| Helper | DDL dict | Values |
|--------|----------|--------|
| `_ensure_v43_columns` | `_V43_COLUMN_DDLS` | `TEXT`, `VARCHAR(16)` |
| `_ensure_phase41_columns` | `_PHASE41_COLUMN_DDLS` | `VARCHAR(32)` |
| `_ensure_phase46_columns` | `_PHASE46_COLUMN_DDLS` | `BOOLEAN` |
| `_ensure_phase54_qramm_columns` | `_PHASE54_QRAMM_ANSWER_DDLS` | `TEXT` |

**Helpers explicitly OUT of scope** (D-07 — literal `TEXT` in f-string, no `col_type` variable):
- `_ensure_identity_columns` (L49)
- `_ensure_gcp_columns` (L71)
- `_ensure_email_columns` (L112)
- `_ensure_broker_columns` (L132)

### Tests that touch `qramm_profiles` / `delete_session` (regression surface)
- `tests/test_qramm_router.py::test_qramm_tables_exist_after_init_db` (L48) — asserts table presence; unaffected
- `tests/test_qramm_router.py::test_qramm_init_db_idempotent` (L58) — re-runs `init_db`; **must remain green after rebuild migration is idempotent**
- `tests/test_qramm_router.py::test_delete_session` (L214)
- `tests/test_qramm_router.py::test_delete_session_cascades_answers` (L223)
- `tests/test_qramm_router.py::test_delete_session_not_found` (L251)
- `tests/test_qramm_router.py::test_create_profile` (L292) — exercises `session.profile_id = profile.id` (qramm.py L520); after D-03 the FK is real, so the profile row must already exist before this UPDATE — verify ordering in the route
- `tests/test_qramm_models.py::TestQRAMMProfileColumns` (L132) — schema-shape assertions; add `PRAGMA foreign_key_list` check here per CONTEXT.md

### Tests that may break under FK-ON (Pitfall 2)
A grep of `tests/test_qramm_*.py` for direct `INSERT`/orphan-creation patterns shows **no test** explicitly creates a `QRAMMProfile` row without a corresponding session, or vice versa. Confidence: MEDIUM — confirm by running the full QRAMM suite before/after D-02 lands.

### Logger surface in `scan.py` (D-05 Discretion #3)
Verified by `grep -n "logger\|logging\|getLogger" quirk/dashboard/api/routes/scan.py` → **no existing module logger**. Must add `import logging` + `logger = logging.getLogger(__name__)` at module top. Mirror the pattern in `quirk/dashboard/api/routes/qramm.py:18-19, 49`.

## Plan-Split Recommendation

CONTEXT.md proposes a 3-plan split. Dependency analysis confirms this is sound:

| Plan | Scope | Files Touched | Audit Rows | Independence |
|------|-------|---------------|------------|--------------|
| 70-01 | FK retrofit + delete_session ordering | `quirk/db.py` (+`_ensure_qramm_profiles_fk`, event listener), `quirk/models.py` (FK on session_id), `quirk/dashboard/api/routes/qramm.py` (delete_session body), `tests/test_qramm_router.py` (+1 test), `tests/test_qramm_models.py` (+PRAGMA assertion) | CR-04, CR-05 | Self-contained — touches FK enforcement end-to-end |
| 70-02 | Classifier `except` narrowing | `quirk/dashboard/api/routes/scan.py` (+logger, narrow except), `tests/test_scan_qs_for_alg.py` (new file, Wave 0) | CR-06 | Zero overlap with 70-01 (different file/function) |
| 70-03 | `col_type` DDL allowlist | `quirk/db.py` (+`_SAFE_COL_TYPE_RE`, 4 helper edits), `tests/test_db_migration_safety.py` (new file, Wave 0) | CR-07 | Touches `quirk/db.py` (shared with 70-01) — see merge note below |

**Merge note for 70-01 ↔ 70-03:** Both touch `quirk/db.py`, but in different regions (70-01 adds a new function + event hook near top; 70-03 adds a constant near L13 and edits 4 existing helpers L93–211). The diffs do not overlap. Recommended execution order: ship 70-01 first (touches more files, higher risk), then 70-02 in parallel, then 70-03 last (smallest, defense-in-depth only).

**Alternative considered:** Merge 70-02 and 70-03 into a single "BLOCK-08" plan since they share the same requirement ID. Rejected — they touch entirely disjoint files (`scan.py` vs `db.py`) with no logical coupling, and a single plan would have two unrelated test bundles. Phase 69 precedent ships one row family per plan; preserve that.

## AUDIT-TASKS Row-Flip Pattern (from Phase 64.1 / Phase 69 precedent)

Per `.planning/audit-2026-05-08/AUDIT-TASKS.md` L180–183, the four target rows currently read:

```
| api-cli-core/CR-04 | BLOCKER | QRAMMProfile.session_id is nullable and has no DB-level FK | — | [ ] deferred-v4.9 |
| api-cli-core/CR-05 | BLOCKER | delete_session does not clear qramm_sessions.profile_id link | — | [ ] deferred-v4.9 |
| api-cli-core/CR-06 | BLOCKER | Bare except: pass in classifier call drops findings silently | — | [ ] deferred-v4.9 |
| api-cli-core/CR-07 | BLOCKER | SQL injection guard on column names lacks col_type DDL fragment | — | [ ] deferred-v4.9 |
```

**Flip pattern** (mirrors Phase 69's precedent — final column transitions, evidence column populated):

```
| api-cli-core/CR-04 | BLOCKER | QRAMMProfile.session_id is nullable and has no DB-level FK | Phase 70 | [x] closed |
| api-cli-core/CR-05 | BLOCKER | delete_session does not clear qramm_sessions.profile_id link | Phase 70 | [x] closed |
| api-cli-core/CR-06 | BLOCKER | Bare except: pass in classifier call drops findings silently | Phase 70 | [x] closed |
| api-cli-core/CR-07 | BLOCKER | SQL injection guard on column names lacks col_type DDL fragment | Phase 70 | [x] closed |
```

Each row's per-row detail block (L396–432 of AUDIT-TASKS.md) gets a closing paragraph appended (Phase 69 style):

```
> **closed by Phase 70** — <plan-NN>
> - Resolution: <one-line summary>
> - Evidence: <test names / file:line refs>
> - Commit: <SHA after phase merges>
```

This is owned by the final plan in the phase (70-03) or a dedicated `70-04` closeout — planner's call. Phase 69's pattern was to fold AUDIT-TASKS flips into the last plan's `SUMMARY.md` workflow.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (configured via `pyproject.toml` `[tool.pytest.ini_options]` testpaths=["tests"]) |
| Config file | `pyproject.toml` (no `pytest.ini`) |
| Quick run command | `pytest tests/test_qramm_router.py tests/test_qramm_models.py tests/test_init_db_idempotent.py -x` |
| Full suite command | `pytest tests/ -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BLOCK-07 (CR-04) | `PRAGMA foreign_key_list('qramm_profiles')` returns a row referencing `qramm_sessions` after `init_db()` on fresh DB | unit | `pytest tests/test_qramm_models.py::test_qramm_profiles_has_db_level_fk -x` | ❌ Wave 0 (new test in existing file) |
| BLOCK-07 (CR-04) | `PRAGMA foreign_key_list` returns the FK row after `init_db()` on a pre-existing FK-less DB (migration path) | unit | `pytest tests/test_qramm_models.py::test_qramm_profiles_fk_retrofit_idempotent -x` | ❌ Wave 0 |
| BLOCK-07 (CR-05) | `delete_session` on a session with linked profile completes without `IntegrityError` and leaves zero `qramm_profiles` rows for that session | integration | `pytest tests/test_qramm_router.py::test_delete_session_with_profile_clears_fk -x` | ❌ Wave 0 (new test in existing file) |
| BLOCK-07 (D-02) | Newly opened SQLAlchemy connection has `PRAGMA foreign_keys` reading `1` | unit | `pytest tests/test_qramm_models.py::test_connect_event_enables_fk_pragma -x` | ❌ Wave 0 |
| BLOCK-07 | Existing tests still green (no FK-OFF dependency surfaces) | regression | `pytest tests/test_qramm_router.py tests/test_qramm_models.py tests/test_qramm_scoring.py tests/test_qramm_answer.py -x` | ✅ (existing) |
| BLOCK-08 (CR-06) | `_qs_for_alg` returns `"Unknown"` and emits `WARNING` log when `classify_algorithm` raises `KeyError`/`TypeError`/`AttributeError` | unit | `pytest tests/test_scan_qs_for_alg.py -x` | ❌ Wave 0 (new file) |
| BLOCK-08 (CR-06) | `_qs_for_alg` propagates `RuntimeError` (and other unrelated types) — no silent swallow | unit | `pytest tests/test_scan_qs_for_alg.py::test_qs_for_alg_propagates_unrelated_exc -x` | ❌ Wave 0 |
| BLOCK-08 (CR-07) | `_ensure_v43_columns` (and the other 3 D-06 helpers) raise `ValueError` when a poisoned `col_type` ("TEXT; DROP TABLE x") is injected via monkeypatched DDL dict | unit | `pytest tests/test_db_migration_safety.py -x` | ❌ Wave 0 (new file) |
| BLOCK-08 (CR-07) | All four D-06 helpers accept their current real `col_type` values (regression) | unit | `pytest tests/test_db_migration_safety.py::test_real_col_types_pass_allowlist -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_qramm_router.py tests/test_qramm_models.py tests/test_scan_qs_for_alg.py tests/test_db_migration_safety.py -x`
- **Per wave merge:** `pytest tests/test_qramm_*.py tests/test_init_db_idempotent.py tests/test_db_*.py tests/test_scan_qs_for_alg.py -x`
- **Phase gate:** `pytest tests/ -x` green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_scan_qs_for_alg.py` — new file; covers BLOCK-08 CR-06; pattern: build a fake classifier via `monkeypatch.setattr("quirk.cbom.classifier.classify_algorithm", _raises_keyerror)`, call `_qs_for_alg` via importing `_derive_cbom`'s closure (or refactor minimally to export `_qs_for_alg`).
- [ ] `tests/test_db_migration_safety.py` — new file; covers BLOCK-08 CR-07; pattern: monkeypatch the `_V43_COLUMN_DDLS` (and equivalents) module-level dict to inject a poisoned value, assert `_ensure_v43_columns(engine)` raises `ValueError`. Use `tmp_path` for engine.
- [ ] Test fixture: minor extension of `_make_qramm_client` (in `tests/test_qramm_router.py`) so that the new test can verify `PRAGMA foreign_keys` is ON in the test engine. NOTE: in-memory SQLite test engines bypass `init_db()` and use raw `create_engine` — the event listener (D-02) attaches to the global `Engine` class, so it WILL fire for the test engine too. Verify explicitly.
- [ ] No framework install needed — pytest already configured.

**Test-engine subtlety:** `_make_qramm_client` at `tests/test_qramm_router.py:20` builds its own `create_engine(...)` and `Base.metadata.create_all(engine)` — it does NOT call `init_db()`. This means:
- D-03 (ForeignKey on the model) makes the FK appear in the test engine via `create_all` — good, the test sees the constraint.
- D-02 (`event.listens_for(Engine, "connect")`) attaches at module level — fires for the test engine too — good.
- D-01 (the rebuild migration) does NOT run for the test engine (no `init_db()`) — that's fine; the test engine is built fresh with the FK already present via D-03.

This means the **delete-session FK-safe test** can use the existing `_make_qramm_client` fixture as-is once D-02/D-03 land.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Application-only cascade (Phase 51 D-09) | DB-level FK + ordered cascade | Phase 70 | Defense in depth; no app-level behavior change |
| Bare `except Exception` in `_qs_for_alg` | Narrow `(KeyError, TypeError, AttributeError)` + logged warning | Phase 70 | Real bugs propagate; silent finding loss eliminated |
| `_SAFE_COL_RE` for column names only | Plus `_SAFE_COL_TYPE_RE` for DDL type fragments | Phase 70 | Closes the "future contributor adds dynamic col_type" defense gap |
| No per-connection PRAGMA | `PRAGMA foreign_keys=ON` via `connect` event | Phase 70 | SQLite FK constraints now enforced project-wide |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | No existing test depends on FK-OFF behavior (no orphan-row creation in test fixtures) | Pitfall 2, Regression surface | If wrong: test breakage after D-02; resolution is to fix the test (not roll back D-02) per CONTEXT.md D-02 instruction |
| A2 | The `connect` event listener fires for `_make_qramm_client`'s test engine (because it attaches to the `Engine` class, not an instance) | Validation Architecture, Test-engine subtlety | LOW — SQLAlchemy 2.0 docs confirm `event.listens_for(Engine, "connect")` fires for all engines `[CITED: docs.sqlalchemy.org/en/20/core/event.html]`; verify in first test run |
| A3 | `quantum_safety_label` and `classify_algorithm` together raise only `KeyError`/`TypeError`/`AttributeError` under malformed input | Pitfall 5, D-05 | MEDIUM — if a real call path raises `ValueError` or similar, that exception will now propagate (CONTEXT.md D-05 explicitly accepts this trade); add a test case if a runtime surprise occurs |
| A4 | The current `_V43_COLUMN_DDLS` / `_PHASE41_COLUMN_DDLS` / `_PHASE46_COLUMN_DDLS` / `_PHASE54_QRAMM_ANSWER_DDLS` literal values all match `_SAFE_COL_TYPE_RE` | Pitfall 6, D-06 | LOW — manually verified by grep; verify by running `_ensure_*_columns` once after the guard lands |

## Open Questions

1. **Does the AUDIT-TASKS row-flip belong in the last plan (70-03) or a dedicated 70-04?**
   - What we know: Phase 69 folded the flip into its final plan's SUMMARY.
   - What's unclear: Whether the planner prefers a dedicated closeout plan to keep diffs separated.
   - Recommendation: Fold into 70-03 per Phase 69 precedent unless the planner has reason to split.

2. **Should `_qs_for_alg` be lifted to a module-level function for direct testability?**
   - What we know: It is currently a closure inside `_derive_cbom`.
   - What's unclear: Whether the planner accepts the minor refactor (lifting it to module scope) or prefers to test through `_derive_cbom`'s public surface.
   - Recommendation: Lift to module scope — minimal-diff cost (one indent change + the function moves up), pays back in direct unit-testability. CLAUDE.md "minimal diffs" applies but does not forbid this kind of testability lift.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | All | ✓ | 3.14.5 (≥3.11 required) | — |
| SQLAlchemy | DB layer, event hook | ✓ | 2.0.48 | — |
| pytest | Test execution | ✓ | bundled in project venv | — |
| SQLite (stdlib `sqlite3`) | DB | ✓ | Python 3.14 bundled | — |

**Missing dependencies with no fallback:** None.
**Missing dependencies with fallback:** None.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | unchanged |
| V3 Session Management | no | unchanged |
| V4 Access Control | no | unchanged |
| V5 Input Validation | **yes** | `_SAFE_COL_TYPE_RE` regex allowlist on DDL fragments; `(KeyError, TypeError, AttributeError)` exception narrowing prevents silent data loss |
| V6 Cryptography | no | unchanged (classifier hardening is exception-handling, not crypto) |
| V13 API and Web Service | tangential | FastAPI route exception hygiene (`_qs_for_alg`) |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SQL injection via DDL string interpolation | Tampering | Allowlist regex (`_SAFE_COL_RE`, new `_SAFE_COL_TYPE_RE`) — fail fast with `ValueError` |
| Silent finding loss via bare `except` | Information Disclosure (negative) / Repudiation | Narrow exception tuple + `WARNING` log |
| FK constraint bypass via missing PRAGMA | Tampering (data integrity) | Per-connection `PRAGMA foreign_keys=ON` via SQLAlchemy event hook |
| Orphan row creation via incorrect cascade | Tampering (data integrity) | DB-level FK + explicit ordered cascade in `delete_session` |

## Sources

### Primary (HIGH confidence)
- `quirk/db.py` (entire file, L1–290) `[VERIFIED: local read 2026-05-15]` — migration helper conventions, `_SAFE_COL_RE` template, `init_db()` ordering
- `quirk/models.py` L95–155 `[VERIFIED: local read 2026-05-15]` — `QRAMMSession.profile_id` (L109) and `QRAMMProfile.session_id` (L148)
- `quirk/dashboard/api/routes/qramm.py` L414–421 `[VERIFIED: local read 2026-05-15]` — current `delete_session` body
- `quirk/dashboard/api/routes/scan.py` L632–642 `[VERIFIED: local read 2026-05-15]` — current `_qs_for_alg` body
- `quirk/cbom/classifier.py` L204–249 `[VERIFIED: local read 2026-05-15]` — `classify_algorithm` is total over `str | None`, never raises directly
- `tests/test_qramm_router.py` and `tests/test_qramm_models.py` `[VERIFIED: local read 2026-05-15]` — fixture pattern, existing delete_session coverage
- `.planning/audit-2026-05-08/AUDIT-TASKS.md` L180–183 + L396–432 `[VERIFIED]` — target row format
- SQLite docs §7 "Making Other Kinds Of Table Schema Changes" `[CITED: https://sqlite.org/lang_altertable.html]`
- SQLite docs `PRAGMA foreign_keys` `[CITED: https://sqlite.org/pragma.html#pragma_foreign_keys]`
- SQLAlchemy 2.0 docs — sqlite dialect "Foreign Key Support" `[CITED: https://docs.sqlalchemy.org/en/20/dialects/sqlite.html#foreign-key-support]`

### Secondary (MEDIUM confidence)
- `.planning/phases/69-deferred-blockers-scanner-cloud/69-RESEARCH.md` `[VERIFIED: local grep]` — Validation Architecture section shape adopted here
- CONTEXT.md L73–101 — code context insights (`safe_str`, idempotency pattern, integration points)

### Tertiary (LOW confidence)
- None — all critical claims are verified by direct file reads or official docs.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries are already in use, versions verified
- Architecture: HIGH — all patterns have ≤200-line-distant precedent in the same file or sibling modules
- Pitfalls: HIGH — SQLite PRAGMA-in-transaction quirk and SQLAlchemy unit-of-work ordering are documented + well-known; A1/A2/A3 explicitly flagged in Assumptions Log

**Research date:** 2026-05-15
**Valid until:** 2026-06-14 (30 days — stable subsystem, no fast-moving dependencies)
