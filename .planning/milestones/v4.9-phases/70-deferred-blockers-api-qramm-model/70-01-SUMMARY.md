---
phase: 70
plan: 01
subsystem: qramm-model
tags: [block-07, qramm, foreign-key, sqlite, migration, audit-closure]
requires:
  - "PRAGMA foreign_keys must be set per-connection on SQLite for FK enforcement"
  - "SQLite supports the 12-step rebuild for retrofitting FKs (no ALTER TABLE ADD CONSTRAINT)"
  - "SQLAlchemy 2.x autobegins a transaction on first execute via Engine.connect()"
provides:
  - "DB-level FK on qramm_profiles.session_id REFERENCES qramm_sessions(id) ON DELETE SET NULL"
  - "Module-level connect event listener enabling PRAGMA foreign_keys=ON for every Engine"
  - "_ensure_qramm_profiles_fk(engine) idempotent migration for pre-existing FK-less DBs"
  - "FK-safe delete_session ordering (null reverse pointer + flush + delete profile/answer rows + delete session)"
affects:
  - quirk/db.py
  - quirk/models.py
  - quirk/dashboard/api/routes/qramm.py
  - tests/test_qramm_models.py
  - tests/test_qramm_delete_session_fk.py
tech-stack:
  added: []
  patterns:
    - "SQLAlchemy `event.listens_for(Engine, 'connect')` module-level hook for SQLite PRAGMA"
    - "Raw DBAPI cursor for PRAGMA + DDL when SQLA 2.x autobegin would interfere"
    - "PRAGMA foreign_key_list short-circuit for FK-retrofit idempotency"
key-files:
  created:
    - tests/test_qramm_delete_session_fk.py
  modified:
    - quirk/db.py
    - quirk/models.py
    - quirk/dashboard/api/routes/qramm.py
    - tests/test_qramm_models.py
decisions:
  - "D-01 (locked): _ensure_qramm_profiles_fk uses the SQLite 12-step rebuild with raw DBAPI cursor for PRAGMA hygiene"
  - "D-02 (locked): module-level @event.listens_for(Engine, 'connect') hook in quirk/db.py"
  - "D-03 (locked): QRAMMProfile.session_id declares ForeignKey(..., ondelete='SET NULL')"
  - "D-04 (locked): delete_session order = null profile_id -> flush -> delete profile rows -> delete answer rows -> delete session -> commit"
  - "Implementation discretion: idempotency check uses a separate engine.connect() block (read-only) so the rebuild path can drop to raw DBAPI for PRAGMA-outside-transaction hygiene without an autobegin conflict"
metrics:
  duration: "~25min"
  completed: "2026-05-15"
---

# Phase 70 Plan 01: Deferred BLOCKERs — API + QRAMM Model (FK + delete_session) Summary

QRAMM `qramm_profiles.session_id` now carries a real DB-level foreign key
referencing `qramm_sessions(id) ON DELETE SET NULL`, every SQLAlchemy connection
has `PRAGMA foreign_keys=ON`, and `delete_session` orders its cleanup so neither
the FK constraint nor the application leaves orphan rows. Closes audit BLOCKERs
`api-cli-core/CR-04` and `CR-05`.

## What Shipped

### D-01 — `_ensure_qramm_profiles_fk(engine)` migration
- Location: `quirk/db.py` (new function, called from `init_db()` immediately after
  `_ensure_phase54_qramm_columns(engine)`).
- Behavior: short-circuits when `PRAGMA foreign_key_list('qramm_profiles')`
  already lists a row referencing `qramm_sessions`; otherwise performs the
  canonical SQLite 12-step rebuild (CREATE `qramm_profiles_new` with the FK
  clause → explicit-column `INSERT … SELECT` → DROP → RENAME).
- **SQLite Pitfall 3 verified:** `PRAGMA foreign_keys=OFF` and `=ON` are both
  issued via the raw DBAPI cursor (outside any transaction). The `BEGIN`/
  `COMMIT`/`ROLLBACK` are explicit cursor statements. This was the source of
  the only deviation found during execution (see below).

### D-02 — per-connection FK PRAGMA
- Module-level `@event.listens_for(Engine, "connect")` hook
  `_sqlite_fk_pragma` in `quirk/db.py`. Fires for every Engine in the
  process, including UUID-named in-memory test engines built via
  `create_engine(...)` directly (verified by
  `tests/test_qramm_delete_session_fk.py` running against
  `_make_qramm_client`-style fixtures).

### D-03 — declarative ForeignKey on the model
- `quirk/models.py`: `QRAMMProfile.session_id` now reads
  `Column(Integer, ForeignKey("qramm_sessions.id", ondelete="SET NULL"), nullable=True)`.
- `ForeignKey` added to the existing sqlalchemy import line.
- Effect: `Base.metadata.create_all(engine)` produces the FK clause on fresh
  DBs without depending on the retrofit migration.

### D-04 — re-ordered `delete_session`
- `quirk/dashboard/api/routes/qramm.py`: body replaced with the six-step
  sequence — `session.profile_id = None` → `db.flush()` → delete
  `QRAMMProfile` rows → delete `QRAMMAnswer` rows → `db.delete(session)` →
  `db.commit()`. The flush guarantees the UPDATE precedes the DELETE under
  the unit-of-work batching, which matters now that `PRAGMA foreign_keys=ON`
  enforces the constraint.

## Files Modified

| File | Change |
|------|--------|
| `quirk/db.py` | +1 import (`event`); new module-level `_sqlite_fk_pragma` listener; new `_ensure_qramm_profiles_fk(engine)` function (~60 lines using raw DBAPI cursor); one-line call in `init_db()` after `_ensure_phase54_qramm_columns(engine)` |
| `quirk/models.py` | `ForeignKey` added to sqlalchemy import; `QRAMMProfile.session_id` rewritten with the `ForeignKey("qramm_sessions.id", ondelete="SET NULL")` clause |
| `quirk/dashboard/api/routes/qramm.py` | `delete_session` body replaced per D-04 (six-step ordered cleanup) |
| `tests/test_qramm_models.py` | +3 top-level tests (`test_qramm_profiles_has_db_level_fk`, `test_connect_event_enables_fk_pragma`, `test_qramm_profiles_fk_retrofit_idempotent`) |
| `tests/test_qramm_delete_session_fk.py` | NEW — two integration tests (`test_delete_session_with_profile_clears_fk`, `test_delete_session_with_profile_and_answers`) |

## Tests Added (5 new)

- `tests/test_qramm_models.py::test_qramm_profiles_has_db_level_fk` — asserts
  `PRAGMA foreign_key_list('qramm_profiles')` returns a row referencing
  `qramm_sessions` with `on_delete == 'SET NULL'`.
- `tests/test_qramm_models.py::test_connect_event_enables_fk_pragma` — asserts
  `PRAGMA foreign_keys` reads `1` on a fresh `init_db` engine connection.
- `tests/test_qramm_models.py::test_qramm_profiles_fk_retrofit_idempotent` —
  inserts a row between two `init_db` calls and asserts it survives (rebuild
  must short-circuit on the second call).
- `tests/test_qramm_delete_session_fk.py::test_delete_session_with_profile_clears_fk` —
  end-to-end DELETE through the FastAPI route with a linked `QRAMMProfile`;
  asserts 204 + zero `qramm_profiles` rows post-delete.
- `tests/test_qramm_delete_session_fk.py::test_delete_session_with_profile_and_answers` —
  same as above plus pre-existing `QRAMMAnswer` rows; asserts profile, answer,
  and session rows are all gone after delete.

All five RED on baseline `main` (4 of them as outright failures; the
idempotency test passes vacuously because the migration was never running).
All five GREEN after the implementation commit.

## Verification

- `python -m compileall quirk tests` — clean.
- Targeted suite (`pytest tests/test_qramm_delete_session_fk.py
  tests/test_qramm_models.py tests/test_qramm_router.py
  tests/test_init_db_idempotent.py`) — 74 passed, 0 failed.
- Broader QRAMM regression (`pytest tests/test_qramm_*.py
  tests/test_init_db_idempotent.py`) — 142 passed, 1 failed
  (`test_qramm_evidence_bridge.py::test_unconfirmed_excluded_from_score`,
  pre-existing failure on baseline `main`, unrelated to BLOCK-07).
- Full project suite — 1308 passed, 33 failed. Baseline was 1304 passed,
  37 failed. Net change: 4 tests flipped from RED → GREEN (the Wave 0 tests),
  zero new regressions.
- Acceptance grep checks all pass:
  - `_ensure_qramm_profiles_fk` defined in `quirk/db.py` and called from
    `init_db()` (2 matches).
  - `@event.listens_for(Engine, "connect")` present exactly once.
  - `ForeignKey("qramm_sessions.id", ondelete="SET NULL")` present exactly
    once in `quirk/models.py`.
  - `session.profile_id = None` present exactly once in `delete_session`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Bug] Migration crashed under SQLAlchemy 2.x autobegin**

- **Found during:** Task 2 GREEN verification (broader suite — `tests/test_qramm_multiplier.py` started returning HTTP 500 when the live `app` ran `init_db` through `get_db`).
- **Issue:** The plan's Pattern 2 (research §"Code Examples") used `conn.begin()` after `conn.execute(text("PRAGMA foreign_keys=OFF"))`. In SQLAlchemy 2.x, `engine.connect()` autobegins a transaction on the first `execute()` call, so `conn.begin()` raised `InvalidRequestError: This connection has already initialized a SQLAlchemy Transaction()`. This also meant the `PRAGMA foreign_keys=OFF` was issued *inside* the autobegun transaction — the very Pitfall 3 the plan warned about.
- **Fix:** Split the function into two phases — a read-only ORM `engine.connect()` block for the `PRAGMA foreign_key_list` idempotency check (auto-managed transaction is harmless for a read PRAGMA), and a raw DBAPI `engine.raw_connection()` cursor block for the rebuild. The raw cursor lets us issue `PRAGMA foreign_keys=OFF`, explicit `BEGIN`, the DDL/DML statements, `COMMIT`/`ROLLBACK`, and `PRAGMA foreign_keys=ON` directly via the DBAPI driver — no SQLAlchemy unit-of-work boundary to fight, and the PRAGMAs are guaranteed to fire outside any transaction.
- **Files modified:** `quirk/db.py` (`_ensure_qramm_profiles_fk` body only — the function signature, call site, and behavior are unchanged).
- **Commit:** `7557763`.
- **Documented in research:** Pitfall 3 is explicitly called out in `70-RESEARCH.md`. The fix preserves the exact same behavior and ordering the research prescribes — the deviation is purely a SQLAlchemy 2.x API mechanics adjustment, not a behavioral change. The tests written in Task 1 remained authoritative and caught the issue.

## SQLite Pitfall 3 — Ordering Verified

The migration issues `PRAGMA foreign_keys=OFF` **before** any `BEGIN` and
re-enables `PRAGMA foreign_keys=ON` in a `finally` clause **after** `COMMIT`
(or `ROLLBACK`). Both PRAGMAs run on a raw DBAPI cursor that is not
participating in an open transaction, so SQLite honors them rather than
silently ignoring them. Verified by reading the new function body and by
the live behavior of `tests/test_qramm_multiplier.py` (which exercises
`get_db → init_db → _ensure_qramm_profiles_fk`) returning a clean 400
once the raw-DBAPI fix landed.

## Threat Surface Coverage

The plan's `<threat_model>` named two `mitigate` entries (T-70-01, T-70-02);
both are implemented end-to-end:

- **T-70-01** (referential integrity tampering on `qramm_profiles`):
  D-01 + D-02 + D-03 — model-declared FK, retrofit migration for existing
  DBs, per-connection PRAGMA enforcement.
- **T-70-02** (orphan-row tampering via `delete_session`): D-04 — explicit
  ordered cleanup with `flush()` between the UPDATE and the DELETE so the
  FK is a safety net, not the cleanup driver.

No new threat surface introduced.

## Per-Task Commits

| Task | Description | Commit |
|------|-------------|--------|
| 1 | Wave 0 RED — failing tests for FK presence, PRAGMA, FK-safe delete | `2f1d584` |
| 2 | GREEN — FK retrofit migration, connect event, FK on model, delete_session reorder | `7557763` |

## Self-Check: PASSED

- `quirk/db.py` — FOUND (definition + call), `event.listens_for(Engine, 'connect')` FOUND.
- `quirk/models.py` — `ForeignKey("qramm_sessions.id", ondelete="SET NULL")` FOUND.
- `quirk/dashboard/api/routes/qramm.py` — `session.profile_id = None` FOUND.
- `tests/test_qramm_delete_session_fk.py` — FOUND, 2 test functions.
- `tests/test_qramm_models.py` — 3 new top-level functions FOUND.
- Commits `2f1d584`, `7557763` — FOUND in `git log`.
