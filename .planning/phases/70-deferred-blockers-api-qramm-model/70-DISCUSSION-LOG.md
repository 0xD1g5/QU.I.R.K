# Phase 70: Deferred BLOCKERs — API + QRAMM Model - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-15
**Phase:** 70-Deferred-BLOCKERs-API-QRAMM-Model
**Areas discussed:** FK enforcement strategy, delete_session reverse-link handling, Classifier except specificity, col_type DDL allowlist shape

---

## FK Enforcement Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Full table rebuild | _ensure_qramm_profiles_fk() SQLite 12-step rebuild + PRAGMA foreign_keys=ON; gives real DB-level FK on every install, fresh and existing. | ✓ |
| Declarative FK + create_all only | ForeignKey() on the model; only fresh DBs get the FK, existing DBs keep the app-level guard. | |
| App-level guard + PRAGMA only | No schema change; rely on explicit cascade in delete_session. Does not actually close CR-04. | |

**User's choice:** Full table rebuild
**Notes:** Closes both fresh-install and upgrade paths so `PRAGMA foreign_key_list('qramm_profiles')` reports the constraint everywhere. PRAGMA wired via SQLAlchemy connect event so the FK actually fires.

---

## delete_session Reverse-Link Handling

| Option | Description | Selected |
|--------|-------------|----------|
| Delete profile too, null pointer first | Null session.profile_id, flush, delete linked QRAMMProfile, delete answers, delete session. No orphans, no dangling reverse pointer. | ✓ |
| Keep profile, rely on SET NULL | FK's ON DELETE SET NULL leaves an orphan QRAMMProfile with session_id=NULL. | |
| Cascade on FK + explicit null | FK with ON DELETE CASCADE plus null of reverse pointer; implicit cleanup inside SQLite. | |

**User's choice:** Delete profile too, null pointer first
**Notes:** Explicit ordering keeps the cleanup mechanism in application code; FK acts as a safety net rather than the primary path. Matches success criterion 3 verbatim.

---

## Classifier except Specificity

| Option | Description | Selected |
|--------|-------------|----------|
| Narrow types + per-call warning log | except (KeyError, TypeError, AttributeError) with logger.warning; real bugs propagate. | ✓ |
| Catch-all + structured error log | except Exception with exc_info=True; keeps broad catch but adds traceback. | |
| No catch — fix classifier to never raise | Make classify_algorithm() total; remove try/except entirely. | |

**User's choice:** Narrow types + per-call warning log
**Notes:** Each silent miss now leaves a log trail ops can grep without expanding scope into classifier internals. Option C captured as deferred refactor.

---

## col_type DDL Allowlist Shape

| Option | Description | Selected |
|--------|-------------|----------|
| Regex pattern | _SAFE_COL_TYPE_RE = ^(TEXT\|INTEGER\|REAL\|BOOLEAN\|DATETIME\|VARCHAR\(\d{1,4}\))$ alongside _SAFE_COL_RE. | ✓ |
| Literal allowlist set | frozenset of exact strings; strictest, every new type requires code edit. | |
| Both — regex + normalize helper | Regex plus normalize_col_type() that uppercases/strips. | |

**User's choice:** Regex pattern
**Notes:** Mirrors _SAFE_COL_RE shape and ValueError-raise semantics; bounds VARCHAR length to 4 digits to reject absurd values.

---

## Claude's Discretion

- Placement of the SQLAlchemy `connect` event listener within `quirk/db.py` (module-level vs inside `init_db`).
- Whether the rebuild migration uses raw `text()` strings or SQLAlchemy DDL constructs — match existing `_ensure_*` style.
- Logger acquisition pattern in `_qs_for_alg` (reuse existing module logger or add `logger = logging.getLogger(__name__)`).

## Deferred Ideas

- Promote `classify_algorithm()` to a total function that never raises — would simplify call sites but expands BLOCK-08 surface area. Candidate for Phase 74 follow-up or standalone refactor.
- Centralize all `_ensure_*_columns` helpers behind a declarative migration framework — out of scope for an audit-closing phase; post-v4.9 backlog.
- Sweep `routes/scan.py` for other broad `except Exception` clauses — addressed individually in WARNING rows under Phase 75.
