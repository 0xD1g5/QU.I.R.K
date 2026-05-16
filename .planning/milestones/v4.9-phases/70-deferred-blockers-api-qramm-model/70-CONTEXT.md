# Phase 70: Deferred BLOCKERs — API + QRAMM Model - Context

**Gathered:** 2026-05-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Close two API/QRAMM-subsystem BLOCKERs deferred from the 2026-05-08 audit:

- **BLOCK-07** — `QRAMMProfile.session_id` becomes a real DB-level FK (`REFERENCES qramm_sessions(id) ON DELETE SET NULL`); `delete_session` clears the reverse `qramm_sessions.profile_id` pointer and removes the linked profile so deletion completes without FK violation or dangling rows. Closes `api-cli-core/CR-04, CR-05`.
- **BLOCK-08** — The bare `except Exception` in `quirk/dashboard/api/routes/scan.py::_qs_for_alg` is narrowed to specific classifier exception types with a logged warning; `col_type` strings in `quirk/db.py` `_ensure_*_columns` migrations are validated against a regex allowlist before any DDL interpolation. Closes `api-cli-core/CR-06, CR-07`.

In scope: schema migration for `qramm_profiles`, PRAGMA wiring, `delete_session` ordering, `_qs_for_alg` exception narrowing, `_SAFE_COL_TYPE_RE` guard in every existing migration helper, tests for each criterion, AUDIT-TASKS.md row flips for CR-04/05/06/07.

Out of scope: any QRAMM-WARN cluster (those land in Phase 74), other API/CLI WARNINGs (Phase 75), classifier-internal refactor, broader DDL framework changes.

</domain>

<decisions>
## Implementation Decisions

### FK Enforcement (BLOCK-07)
- **D-01:** Implement a `_ensure_qramm_profiles_fk()` migration in `quirk/db.py` that performs the SQLite 12-step table rebuild — create `qramm_profiles_new` with `session_id INTEGER REFERENCES qramm_sessions(id) ON DELETE SET NULL`, copy rows, drop old, rename. Wrap in a transaction with `PRAGMA foreign_keys=OFF` around the swap and re-enable on exit. Idempotent: skip when `PRAGMA foreign_key_list('qramm_profiles')` already lists the constraint. Called from `init_db()` after `_ensure_qramm_tables()` / `_ensure_phase54_qramm_columns()`.
- **D-02:** Enable `PRAGMA foreign_keys=ON` per connection via a SQLAlchemy `connect` event listener (single hook in `quirk/db.py`). Without this PRAGMA the FK is documentation-only. Existing tests must keep passing with FKs enforced; any test that depended on dangling FK behavior is itself a finding.
- **D-03:** Update `QRAMMProfile.session_id` in `quirk/models.py` from `Column(Integer, nullable=True)` to `Column(Integer, ForeignKey("qramm_sessions.id", ondelete="SET NULL"), nullable=True)` so `create_all` on fresh DBs produces the same constraint without depending on the rebuild migration.

### delete_session Ordering (BLOCK-07)
- **D-04:** New `delete_session` body order (in `quirk/dashboard/api/routes/qramm.py`): (1) `session.profile_id = None`; (2) `db.flush()`; (3) delete the `QRAMMProfile` row(s) where `session_id == session_id`; (4) delete `QRAMMAnswer` rows where `session_id == session_id`; (5) `db.delete(session)`; (6) `db.commit()`. This avoids any FK violation regardless of whether SQLite FKs are ON, and leaves no orphan profile rows.

### Classifier except Narrowing (BLOCK-08)
- **D-05:** Replace the bare `except Exception` at `quirk/dashboard/api/routes/scan.py:640` (`_qs_for_alg`) with `except (KeyError, TypeError, AttributeError) as e:` — log via `logger.warning("classifier failed for alg=%r: %s", alg, e)` then return `"unknown"`. Other exception types propagate to the route handler so real bugs aren't silently relabeled. Use the existing module logger.

### col_type DDL Allowlist (BLOCK-08)
- **D-06:** Introduce `_SAFE_COL_TYPE_RE = re.compile(r"^(TEXT|INTEGER|REAL|BOOLEAN|DATETIME|VARCHAR\(\d{1,4}\))$")` at the top of `quirk/db.py` alongside `_SAFE_COL_RE`. In every `_ensure_*_columns` helper that interpolates a `col_type` (currently `_ensure_v43_columns`, `_ensure_phase41_columns`, `_ensure_phase46_columns`, `_ensure_phase54_qramm_columns`, and any other matching helper), add `if not _SAFE_COL_TYPE_RE.match(col_type): raise ValueError(f"Unsafe column type in migration: {col_type!r}")` immediately after the existing `_SAFE_COL_RE.match(col)` guard. Validate BEFORE the transaction opens so a bad value fails fast without partial migration.
- **D-07:** Helpers that interpolate a literal `TEXT` (e.g. `_ensure_email_columns`, `_ensure_broker_columns`) do not currently bind `col_type` from a variable — leave them as-is to keep the diff minimal. Defense-in-depth applies only where `col_type` is read from a dict.

### Claude's Discretion
- Exact placement of the SQLAlchemy `connect` event listener (module-level vs inside `init_db`) — pick the spot consistent with existing engine setup in `quirk/db.py`.
- Whether the new migration uses `text()` strings directly or builds the rebuild via SQLAlchemy DDL constructs — pick whichever matches the existing `_ensure_*` style.
- Logger name in `_qs_for_alg` — reuse the module-level logger if one exists; otherwise add the standard `logger = logging.getLogger(__name__)` pattern.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Audit + Requirements
- `.planning/audit-2026-05-08/AUDIT-TASKS.md` rows `api-cli-core/CR-04`, `CR-05`, `CR-06`, `CR-07` — original BLOCKER descriptions; flip to `[x] closed` when this phase ships.
- `.planning/REQUIREMENTS.md` `BLOCK-07`, `BLOCK-08` — locked requirement language.
- `.planning/ROADMAP.md` Phase 70 success criteria (1, 2, 3) — verification targets.

### Code Under Change
- `quirk/db.py` — migration helpers; `_SAFE_COL_RE` at L102 is the template for the new `_SAFE_COL_TYPE_RE` guard. `_ensure_*_columns` family (L93–211) is where the allowlist check is inserted.
- `quirk/models.py` L137–158 — `QRAMMProfile` model; L109 — `QRAMMSession.profile_id` reverse pointer.
- `quirk/dashboard/api/routes/qramm.py` L414–421 — `delete_session` body.
- `quirk/dashboard/api/routes/scan.py` L632–642 — `_qs_for_alg` bare except.
- `quirk/cbom/classifier.py` — `classify_algorithm()` (called from `_qs_for_alg`); informs which exception types are legitimate.

### Precedent
- Phase 64.1 (`.planning/phases/64.1-audit-residual-blockers/`) — transactional `init_db` migrations (CR-08) and the AUDIT-TASKS row-flip pattern.
- Phase 69 (`.planning/phases/69-deferred-blockers-scanner-cloud/`) — same audit-closing structure (Wave-A/B BLOCKER batches, per-row evidence in AUDIT-TASKS).
- SQLite docs §7 "Making Other Kinds Of Table Schema Changes" (https://sqlite.org/lang_altertable.html) — the 12-step rebuild template for adding the FK.

### Tests (authoritative for success criteria)
- `tests/test_qramm_router.py` — existing `delete_session` coverage; new test (criterion 3) lives here or in a new `tests/test_qramm_delete_session_fk.py`.
- `tests/test_qramm_models.py` — schema-shape assertions; add `PRAGMA foreign_key_list('qramm_profiles')` check.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_SAFE_COL_RE` (`quirk/db.py:102` pattern) — exact shape to mirror for `_SAFE_COL_TYPE_RE`, including the `ValueError` raise.
- `sa_inspect(engine).get_columns(...)` idempotency pattern used in every `_ensure_*` helper — applicable to the new FK migration's idempotency check (replace with `PRAGMA foreign_key_list`).
- `safe_str` helper at `quirk/util/safe_exc.py` — used by Phase 59 for safe exception text in logs; reuse for the `_qs_for_alg` warning if the exception text could contain user-supplied algorithm strings.

### Established Patterns
- All migration helpers raise `ValueError` on unsafe input rather than logging-and-continuing — preserves fail-fast semantics. The new `col_type` guard follows the same pattern.
- SQLite FK enforcement requires per-connection PRAGMA — codebase has no existing PRAGMA hook, so this is a net-new addition. Place it next to engine creation to keep one source of truth.
- Wave-A BLOCKER fixes ship one per plan (Phase 69 style): one plan per audit row family. Suggests Phase 70 plans split as `70-01` (FK + delete_session, BLOCK-07/CR-04+05), `70-02` (classifier except, BLOCK-08/CR-06), `70-03` (col_type allowlist, BLOCK-08/CR-07). Planner has final say.

### Integration Points
- `init_db()` in `quirk/db.py` — call site for the new `_ensure_qramm_profiles_fk()` migration. Existing helper ordering convention applies.
- SQLAlchemy engine creation in `quirk/db.py` — the PRAGMA `connect` event listener attaches here.
- `quirk/dashboard/api/routes/qramm.py` imports — `QRAMMProfile` is already importable; no new imports needed beyond the existing `QRAMMAnswer` pattern.

</code_context>

<specifics>
## Specific Ideas

- Migration is idempotent via `PRAGMA foreign_key_list('qramm_profiles')` — if the row already exists pointing at `qramm_sessions`, skip the rebuild entirely.
- `ON DELETE SET NULL` (not `CASCADE`) on the FK — the application-level delete handles profile removal explicitly so the FK behavior is only a safety net, not the cleanup mechanism.
- Regex allowlist accepts `VARCHAR(\d{1,4})` to cover existing `VARCHAR(16)` and `VARCHAR(32)` while bounding length to prevent absurd values.
- Test for criterion 3 should explicitly assert: `PRAGMA foreign_key_list('qramm_profiles')` returns a row referencing `qramm_sessions`, then `delete_session` on a session with active `QRAMMProfile` completes without raising and leaves zero rows in `qramm_profiles` for that `session_id`.

</specifics>

<deferred>
## Deferred Ideas

- Promoting `classify_algorithm()` to a total function that never raises (Option C in the discussion) — would simplify call sites across the codebase, but expands the BLOCK-08 surface area into the classifier internals. Track as a candidate for a Phase 74 (`QRAMM + Compliance WARNINGs`) follow-up or a standalone refactor phase.
- Centralizing all `_ensure_*_columns` helpers behind a single migration framework with declarative typing — improves long-term maintainability but is out of scope for an audit-closing phase. Capture for post-v4.9 backlog.
- Sweeping `quirk/dashboard/api/routes/scan.py` for other broad `except Exception` clauses — those are listed individually in audit WARNING rows and belong in Phase 75.

</deferred>

---

*Phase: 70-Deferred-BLOCKERs-API-QRAMM-Model*
*Context gathered: 2026-05-15*
