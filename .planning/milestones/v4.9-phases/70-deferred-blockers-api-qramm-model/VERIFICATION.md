---
phase: 70-deferred-blockers-api-qramm-model
verified: 2026-05-15T00:00:00Z
status: passed
score: 11/11 must-haves verified
overrides_applied: 0
---

# Phase 70: Deferred BLOCKERs — API + QRAMM Model Verification Report

**Phase Goal:** Resolve the two deferred BLOCKERs in the API/QRAMM subsystem — `QRAMMProfile` table has a real DB-level FK constraint with safe session deletion, and the classifier no longer uses a bare `except` or interpolates unvalidated strings into DDL. Closes audit findings api-cli-core/CR-04, CR-05, CR-06, CR-07.

**Verified:** 2026-05-15
**Status:** PASSED
**Re-verification:** No — initial verification
**Score:** 11/11 must-haves verified across 3 plans

## Goal Achievement

### Roadmap Success Criteria

| # | Success Criterion | Status | Evidence |
|---|-------------------|--------|----------|
| 1 | `qramm_profiles` has FK `(session_id) REFERENCES qramm_sessions(id)`; `delete_session` nulls `profile_id` before deletion | VERIFIED | `quirk/models.py:149-153` declares `ForeignKey("qramm_sessions.id", ondelete="SET NULL")`; `quirk/dashboard/api/routes/qramm.py:418` sets `session.profile_id = None`; `_ensure_qramm_profiles_fk` retrofit at `quirk/db.py:243`; PRAGMA foreign_keys=ON enforced via `_sqlite_fk_pragma` at `quirk/db.py:13-24` |
| 2 | Classifier `except` is specific (not bare) and logs structured message; `col_type` validated against allowlist before DDL interpolation | VERIFIED | `quirk/dashboard/api/routes/scan.py:652` uses `except (KeyError, TypeError, AttributeError) as e:` with `logger.warning(...)` at L653; `_SAFE_COL_TYPE_RE` defined at `quirk/db.py:34` and applied in 4 helpers (lines 125, 189, 213, 236) with `raise ValueError(f"Unsafe column type in migration: ...")` |
| 3 | Pytest fixture deleting QRAMM session with active profile completes cleanly (no FK error, no dangling row) | VERIFIED | `tests/test_qramm_delete_session_fk.py` defines 2 integration tests; `tests/test_qramm_models.py::test_qramm_profiles_has_db_level_fk` and `::test_connect_event_enables_fk_pragma` confirm DB-level guarantees; `pytest` of all phase 70 test files: 32 passed, 0 failed |

### Plan-Level Truths (BLOCK-07 + BLOCK-08)

| # | Truth | Plan | Status | Evidence |
|---|-------|------|--------|----------|
| 1 | qramm_profiles table has FK from session_id REFERENCES qramm_sessions(id) ON DELETE SET NULL on fresh + pre-existing DBs | 70-01 | VERIFIED | model declarative FK + `_ensure_qramm_profiles_fk(engine)` 12-step rebuild at `quirk/db.py:243`, called from `init_db()` L390 |
| 2 | PRAGMA foreign_keys reads 1 on every newly opened SQLAlchemy connection | 70-01 | VERIFIED | `@event.listens_for(Engine, "connect")` at `quirk/db.py:13-24` issues `PRAGMA foreign_keys=ON` via raw DBAPI cursor |
| 3 | DELETE /api/qramm/sessions/{id} on session with linked QRAMMProfile returns 204, no IntegrityError, zero leftover profile rows | 70-01 | VERIFIED | `delete_session` body at `quirk/dashboard/api/routes/qramm.py:415-424`: null profile_id → flush → delete profiles → delete answers → delete session → commit |
| 4 | init_db() is idempotent — running twice does not raise or duplicate qramm_profiles | 70-01 | VERIFIED | `_ensure_qramm_profiles_fk` short-circuits via `PRAGMA foreign_key_list`; tested by `test_qramm_profiles_fk_retrofit_idempotent` |
| 5 | _qs_for_alg returns "Unknown" + WARNING log on KeyError/TypeError/AttributeError | 70-02 | VERIFIED | `scan.py:652-653`: narrowed except + `logger.warning("classifier failed for alg=%r: %s", alg, e)` |
| 6 | _qs_for_alg propagates other exception types (RuntimeError, ValueError) | 70-02 | VERIFIED | tests `test_qs_for_alg_propagates_unrelated_exc[RuntimeError]/[ValueError]` PASS |
| 7 | scan.py defines module-level logger | 70-02 | VERIFIED | `scan.py:5` `import logging`; `scan.py:46` `logger = logging.getLogger(__name__)` |
| 8 | quirk/db.py defines module-level _SAFE_COL_TYPE_RE allowlist | 70-03 | VERIFIED | `quirk/db.py:34` — `_SAFE_COL_TYPE_RE = re.compile(r"^(TEXT\|INTEGER\|REAL\|BOOLEAN\|DATETIME\|VARCHAR\(\d{1,4}\))$")` |
| 9 | Each of 4 _ensure_* helpers raises ValueError when col_type fails allowlist | 70-03 | VERIFIED | grep finds 4 occurrences of `_SAFE_COL_TYPE_RE.match(col_type)` (lines 125, 189, 213, 236) and 4 `raise ValueError(f"Unsafe column type in migration: ...")` |
| 10 | All 4 helpers continue to succeed with real col_type values | 70-03 | VERIFIED | `pytest tests/test_db_migrations.py` 16 passed; init_db idempotent tests pass |
| 11 | AUDIT-TASKS rows CR-04/05/06/07 flipped to `[x] closed` with Phase 70 evidence | 70-03 | VERIFIED | `.planning/audit-2026-05-08/AUDIT-TASKS.md:180-183` — all 4 rows show `Phase 70 \| [x] closed` with per-row test references |

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `quirk/db.py` | _sqlite_fk_pragma listener + _ensure_qramm_profiles_fk + _SAFE_COL_TYPE_RE + 4 guards | VERIFIED | All 4 patterns present at expected locations (L13, L34, L243, plus 4 guard sites) |
| `quirk/models.py` | QRAMMProfile.session_id with ForeignKey(ondelete="SET NULL") | VERIFIED | L149-153 |
| `quirk/dashboard/api/routes/qramm.py` | delete_session FK-safe ordering | VERIFIED | L415-424, comment "Phase 70 BLOCK-07/D-04" |
| `quirk/dashboard/api/routes/scan.py` | module logger + lifted _qs_for_alg + narrow except + warning log | VERIFIED | L5, L46, L635, L652-653 |
| `tests/test_qramm_delete_session_fk.py` | 2 integration tests, ≥40 lines | VERIFIED | 4734 bytes, 2 test functions |
| `tests/test_qramm_models.py` | +3 new tests with PRAGMA assertions | VERIFIED | L247, L267, L281 |
| `tests/test_cbom_scan_route.py` | parametrized swallow/propagation/happy tests, ≥30 lines | VERIFIED | 3156 bytes, 3 test functions w/ parametrize → 6 cases |
| `tests/test_db_migrations.py` | regex matrix + 4 poisoned-dict tests, ≥50 lines | VERIFIED | 4734 bytes, 7 functions with parametrization |
| `.planning/audit-2026-05-08/AUDIT-TASKS.md` | 4 rows flipped to `[x] closed` with Phase 70 + test refs | VERIFIED | Lines 180-183 confirmed |

### Key Link Verification

| From | To | Via | Status |
|------|----|----|--------|
| `delete_session` | `QRAMMProfile.session_id ForeignKey` | `session.profile_id = None + db.flush()` before profile delete | WIRED |
| `init_db` | `_ensure_qramm_profiles_fk` | function call after `_ensure_phase54_qramm_columns` | WIRED (L390) |
| `quirk/db.py` module | SQLAlchemy `Engine` connect event | `@event.listens_for(Engine, "connect")` | WIRED (L13) |
| `_qs_for_alg` | `classifier.classify_algorithm` | narrow `except (KeyError, TypeError, AttributeError) as e` | WIRED (L652) |
| `_qs_for_alg` | logger | `logger.warning("classifier failed for alg=%r: %s", alg, e)` | WIRED (L653) |
| 4 _ensure_*_columns helpers | `_SAFE_COL_TYPE_RE` | `if not _SAFE_COL_TYPE_RE.match(col_type): raise ValueError(...)` | WIRED (4 sites) |
| AUDIT-TASKS rows CR-04/05/06/07 | Phase 70 evidence | row column 5 references test files | WIRED |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All phase 70 test modules pass | `pytest tests/test_qramm_delete_session_fk.py tests/test_cbom_scan_route.py tests/test_db_migrations.py tests/test_qramm_models.py::test_qramm_profiles_has_db_level_fk ...` | 32 passed | PASS |
| Modified modules compile | `python -m compileall quirk/db.py quirk/models.py quirk/dashboard/api/routes/qramm.py quirk/dashboard/api/routes/scan.py -q` | exit 0 | PASS |

### Requirements Coverage

| Requirement | Source Plan | Status | Evidence |
|-------------|-------------|--------|----------|
| BLOCK-07 (FK retrofit + PRAGMA + FK-safe delete_session) | 70-01 | SATISFIED | model FK + retrofit migration + connect-event PRAGMA + reordered delete_session, all backed by 5 new tests |
| BLOCK-08 (narrow bare except + DDL allowlist; covers CR-06 + CR-07) | 70-02 + 70-03 | SATISFIED | _qs_for_alg narrowed + module logger (CR-06); _SAFE_COL_TYPE_RE + 4 guards (CR-07); all 13 new tests pass |

### Anti-Patterns Found

None. No `TBD/FIXME/XXX` debt markers introduced; no stub returns; no `except Exception:` introduced (the existing `_qs_for_alg` bare except was REMOVED, which is the goal). The plan explicitly defers the other broad `except Exception:` clauses in scan.py to Phase 75 — this is intentional scope discipline, not a gap.

### Human Verification Required

None. All goals are programmatically verifiable: schema-level FK presence (PRAGMA), exception narrowing (grep + tests), allowlist regex (grep + tests), audit row flips (grep). All test surfaces are deterministic.

### Gaps Summary

No gaps. Phase 70 achieves its stated goal end-to-end:

1. **BLOCK-07 (CR-04/CR-05)** — DB-level FK on `qramm_profiles.session_id` declared in the model, retrofitted into existing DBs by `_ensure_qramm_profiles_fk`, enforced per-connection by the `_sqlite_fk_pragma` event listener, and respected by the reordered `delete_session` (null profile_id → flush → delete dependents → delete session).
2. **BLOCK-08 (CR-06)** — Bare `except Exception:` in `_qs_for_alg` replaced with `except (KeyError, TypeError, AttributeError) as e:`, logged as a `logger.warning`, lifted to module scope for direct testability; unrelated exception types correctly propagate.
3. **BLOCK-08 (CR-07)** — `_SAFE_COL_TYPE_RE` allowlist guards 4 migration helpers with fail-fast `ValueError`; 4 do-not-touch helpers respected per D-07.
4. **Audit ledger closure** — All four AUDIT-TASKS rows flipped to `[x] closed` with per-row test-file evidence pointing at the plans that closed them.

All 32 dedicated phase 70 tests pass; the four modified production modules compile cleanly.

---

_Verified: 2026-05-15_
_Verifier: Claude (gsd-verifier)_
