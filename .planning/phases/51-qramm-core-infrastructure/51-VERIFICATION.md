---
phase: 51-qramm-core-infrastructure
verified: 2026-05-05T00:00:00Z
status: passed
score: 13/13 must-haves verified
overrides_applied: 0
gaps: []
deferred: []
human_verification: []
---

# Phase 51: QRAMM Core Infrastructure Verification Report

**Phase Goal:** Establish QRAMM (Quantum Readiness Assessment & Maturity Model) core infrastructure — database models, question catalog, scoring engine, FastAPI CRUD router, and test coverage — enabling phases 53–56 to build the full assessment workflow.
**Verified:** 2026-05-05T00:00:00Z
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|---------|
| 1 | Running `init_db()` against a fresh database creates `qramm_sessions`, `qramm_answers`, and `qramm_profiles` tables idempotently via `_ensure_qramm_tables()` | ✓ VERIFIED | `python -c "...init_db(p)..."` confirmed idempotent table creation on both fresh and existing DBs; `_ensure_qramm_tables` present in `quirk/db.py` line 193 |
| 2 | All 5 CRUD endpoint families respond with correct HTTP status codes and Pydantic-validated payloads | ✓ VERIFIED | Router exports 5 routes: `/api/qramm/sessions`, `/api/qramm/sessions/{session_id}`, `.../answers`, `.../score`, DELETE; all verified live via `create_app()` path inspection |
| 3 | `QRAMM_QUESTIONS` is a list of exactly 120 entries with correct schema (question_number, dimension, practice_area, text, maturity_labels) | ✓ VERIFIED | `len(QRAMM_QUESTIONS)==120` asserted programmatically; 30/dim, 10/practice_area confirmed; Q1 and Q120 verbatim text spot-checked |
| 4 | Dimension score equals `min()` of its 3 practice scores (weakest-link), not average; CSNP reference calculation `min([2.5, 3.4, 1.5]) == 1.5` passes | ✓ VERIFIED | `compute_dimension_score([2.5, 3.4, 1.5]) == 1.5` verified; `compute_practice_score([3,2,3,4,2,2,3,2,3,1]) == 2.5`; overall `(2.8, 3.1, 2.5, 2.9) -> 2.825 "Established"` |
| 5 | Zero `DeprecationWarning: datetime.utcnow()` in test suite; `datetime.now(timezone.utc)` used throughout affected modules | ✓ VERIFIED | `grep -c "utcnow"` returns `0` for both `test_saml_scanner.py` and `test_broker_scanner_redis.py`; production `quirk/` code also clean |
| 6 | QRAMMSession, QRAMMAnswer, QRAMMProfile ORM classes registered on Base.metadata | ✓ VERIFIED | Import check: `{'qramm_sessions','qramm_answers','qramm_profiles'}.issubset(Base.metadata.tables)` passes; all columns match QRAMM-01 spec including score_json, suggested_answer, confirmed_at, evidence_source |
| 7 | scoring.py isolates from risk_engine, scanner, db, models (D-09) | ✓ VERIFIED | `grep -qE "from quirk\.(risk_engine|scanner|db|models)" scoring.py` exits 1; only `__future__` and `typing` imported |
| 8 | QRAMM_MODEL constant has qramm_version, last_verified, source_url, github_url, license; STALENESS_THRESHOLD_DAYS=90 | ✓ VERIFIED | `model_meta.py` contains all 5 required keys; `STALENESS_THRESHOLD_DAYS: int = 90` confirmed |
| 9 | Pydantic Field validators reject answer_value outside 1..4 and question_number outside 1..120 | ✓ VERIFIED | `AnswerItem.answer_value = Field(ge=1, le=4)`, `AnswerItem.question_number = Field(ge=1, le=120)`; test_qramm_router confirms 422 on value=5 and question_number=121 |
| 10 | Router registered in app.py before SPA catch-all | ✓ VERIFIED | `app.py` line 44: `application.include_router(qramm.router, prefix="/api")` appears at line 44, SPA catch-all at line 70 (`/{full_path:path}`) |
| 11 | 35 QRAMM tests pass covering catalog, scoring, and router endpoint families | ✓ VERIFIED | `pytest tests/test_qramm_questions.py tests/test_qramm_scoring.py tests/test_qramm_router.py -x`: 35 passed in 0.37s |
| 12 | test_qramm_router.py verifies QRAMM-01 table existence after init_db() and cascade delete of answers | ✓ VERIFIED | `test_qramm_tables_exist_after_init_db` and `test_qramm_init_db_idempotent` pass; `test_delete_session_cascades_answers` verifies QRAMMAnswer rows removed via direct session query |
| 13 | score endpoint persists computed score to score_json, sets status="scored", GET returns populated score | ✓ VERIFIED | `session.score_json = json.dumps(response, default=str)` in router line 266; `test_score_session_persistence_round_trip` passes |

**Score:** 13/13 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|---------|--------|---------|
| `quirk/models.py` | QRAMMSession, QRAMMAnswer, QRAMMProfile ORM classes | ✓ VERIFIED | 3 classes appended after CryptoEndpoint; Float import added; all columns match spec including Phase 53 pre-provisioned columns |
| `quirk/db.py` | `_ensure_qramm_tables()` called from `init_db()` | ✓ VERIFIED | Function at line 193; call in `init_db()` at line 231 after `_ensure_phase46_columns` |
| `quirk/qramm/__init__.py` | Package init | ✓ VERIFIED | Module docstring present |
| `quirk/qramm/questions.py` | QRAMM_QUESTIONS constant — 120 entries | ✓ VERIFIED | 120 entries, correct schema, Q1/Q120 verbatim text verified, `get_question()` helper present |
| `quirk/qramm/scoring.py` | compute_practice_score, compute_dimension_score, compute_overall_score | ✓ VERIFIED | All 3 functions + `_maturity_label()`; min() rule confirmed; D-09 isolation confirmed |
| `quirk/qramm/model_meta.py` | QRAMM_MODEL staleness constant | ✓ VERIFIED | All 5 keys; STALENESS_THRESHOLD_DAYS=90 |
| `quirk/dashboard/api/routes/qramm.py` | FastAPI router with 5 endpoint families and inline Pydantic models | ✓ VERIFIED | 280 lines; 5 routes registered; inline Pydantic with Field validators; explicit cascade delete |
| `quirk/dashboard/api/app.py` | Updated to include qramm router | ✓ VERIFIED | `qramm` in routes import; `include_router(qramm.router, prefix="/api")` at line 44 |
| `tests/test_qramm_questions.py` | Schema and count tests for QRAMM_QUESTIONS | ✓ VERIFIED | 7 tests; all pass |
| `tests/test_qramm_scoring.py` | Reference-calc + weakest-link + multiplier + overall + maturity + D-09 tests | ✓ VERIFIED | 9 tests; all pass |
| `tests/test_qramm_router.py` | TestClient smoke tests for 5 endpoint families + table existence | ✓ VERIFIED | 19 tests; all pass including cascade delete verification |
| `tests/test_saml_scanner.py` | Fixed datetime.now(timezone.utc) (DEBT-01) | ✓ VERIFIED | 0 utcnow occurrences; 41 tests pass |
| `tests/test_broker_scanner_redis.py` | Fixed datetime.now(timezone.utc) (DEBT-01) | ✓ VERIFIED | 0 utcnow occurrences; tests pass |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `quirk/db.py:init_db()` | `quirk/models.py:Base.metadata` | `Base.metadata.create_all(engine, checkfirst=True)` | ✓ WIRED | `_ensure_qramm_tables` calls `Base.metadata.create_all`; models registered via top-of-file `from quirk.models import Base` |
| `quirk/dashboard/api/routes/qramm.py` | `quirk/qramm/scoring.py` | `from quirk.qramm.scoring import compute_practice_score, compute_dimension_score, compute_overall_score` | ✓ WIRED | Import at line 29; all 3 functions called in `score_session()` |
| `quirk/dashboard/api/routes/qramm.py` | `quirk/models.py:QRAMMSession,QRAMMAnswer` | ORM via `Depends(get_db)` Session | ✓ WIRED | `db.get(QRAMMSession, session_id)` at line 101; `db.query(QRAMMAnswer)` at multiple sites |
| `quirk/dashboard/api/app.py` | `quirk/dashboard/api/routes/qramm.py` | `include_router(qramm.router, prefix='/api')` | ✓ WIRED | Line 44; confirmed by live route check: `/api/qramm/sessions` present |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|-------------------|--------|
| `qramm.py:score_session` | `rows` (QRAMMAnswer list) | `db.query(QRAMMAnswer).filter(...).all()` | Yes — live DB query | ✓ FLOWING |
| `qramm.py:read_session` | `score` | `json.loads(session.score_json)` | Yes — reads persisted JSON blob | ✓ FLOWING |
| `qramm.py:save_answers` | `meta` | `get_question(item.question_number)` | Yes — reads from QRAMM_QUESTIONS catalog | ✓ FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| ORM models on Base.metadata | `python -c "...assert {'qramm_sessions'...}.issubset(Base.metadata.tables)"` | ORM models OK | ✓ PASS |
| init_db() idempotent | `python -c "...init_db(p); init_db(p)..."` | OK idempotent | ✓ PASS |
| Scoring reference calc | `python -c "...compute_dimension_score([2.5,3.4,1.5])==1.5; overall=2.825 Established"` | Scoring OK | ✓ PASS |
| Router registered in live app | `python -c "...paths=[r.path for r in app.routes]..."` | 5 qramm paths present | ✓ PASS |
| 35 QRAMM tests | `pytest tests/test_qramm_*.py -x` | 35 passed in 0.37s | ✓ PASS |
| DEBT-01 utcnow eliminated | `grep -c "utcnow" test_saml_scanner.py test_broker_scanner_redis.py` | 0/0 | ✓ PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|---------|
| QRAMM-01 | 51-01 | SQLite QRAMM tables via `_ensure_qramm_tables()` | ✓ SATISFIED | 3 tables created idempotently; `test_qramm_tables_exist_after_init_db` passes |
| QRAMM-02 | 51-03 | FastAPI router at `/api/qramm/` with 5 CRUD endpoints | ✓ SATISFIED | All 5 routes wired; 19 router tests pass including validation, persistence, cascade |
| QRAMM-03 | 51-02 | 120-question CSNP catalog in `questions.py` | ✓ SATISFIED | `len(QRAMM_QUESTIONS)==120`; schema verified; dimension/practice distribution correct |
| QRAMM-04 | 51-02 | Weakest-link scoring engine with reference-verified values | ✓ SATISFIED | `min()` rule confirmed; CSNP reference `2.5 / 1.5 / 2.825 Established` all pass |
| DEBT-01 | 51-05 | Zero `datetime.utcnow()` calls in affected test files | ✓ SATISFIED | 0 utcnow in `test_saml_scanner.py` and `test_broker_scanner_redis.py`; production `quirk/` clean |

Note: QRAMM-05 (QRAMM_MODEL constant with staleness metadata) is partially delivered — `model_meta.py` provides the constant. The CI staleness gate (QRAMM-06) and CLI subcommand (QRAMM-07) are explicitly scoped to Phase 55 per REQUIREMENTS.md traceability table. These are not required for Phase 51.

---

### Deferred Items

Items not yet met but explicitly addressed in later milestone phases.

| # | Item | Addressed In | Evidence |
|---|------|-------------|---------|
| 1 | CI pytest gate fails when QRAMM_MODEL.last_verified is > 90 days old (QRAMM-06) | Phase 55 | Phase 55 requirements: QRAMM-05, QRAMM-06, QRAMM-07 (REQUIREMENTS.md traceability line 124-126) |
| 2 | `quirk qramm status` CLI subcommand (QRAMM-07) | Phase 55 | Phase 55 goal: "staleness CLI and CI gate" |

---

### Anti-Patterns Found

No anti-patterns found. All QRAMM source files scanned:
- Zero TODO/FIXME/PLACEHOLDER comments in any QRAMM file
- Zero `return null` / stub return patterns in router or scoring
- Zero `datetime.utcnow()` in production `quirk/` code
- D-09 isolation enforced: `scoring.py` imports only `__future__` and `typing`

---

### Human Verification Required

None — all must-haves are programmatically verifiable and confirmed passing.

---

## Gaps Summary

No gaps. All 13 must-haves are VERIFIED. Phase goal achieved.

---

_Verified: 2026-05-05T00:00:00Z_
_Verifier: Claude (gsd-verifier)_
