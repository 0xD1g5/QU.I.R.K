---
phase: 53-qramm-evidence-bridge
plan: "03"
subsystem: qramm
tags: [qramm, router, evidence-bridge, wiring]
dependency_graph:
  requires: ["53-02"]
  provides: []
  affects:
    - quirk/dashboard/api/routes/qramm.py
    - tests/test_qramm_router.py
tech_stack:
  added: []
  patterns: [synchronous bridge call inside request handler, flush-before-bulk-insert, confirmed_at auto-set]
key_files:
  created: []
  modified:
    - quirk/dashboard/api/routes/qramm.py
    - tests/test_qramm_router.py
decisions:
  - "db.flush() used before pre-creating CVI rows so session.id is available within the same transaction"
  - "30 CVI rows pre-created before db.commit() so the bridge bulk-updates within the same logical request window"
  - "confirmed_at auto-set is guarded by both suggested_answer IS NOT NULL and item.answer_value IS NOT NULL — manual-only answers cannot accidentally trigger confirmation timestamps (T-53-03-01)"
  - "score_session NOT modified (D-10) — existing answer_value IS NOT NULL filter already correctly excludes unconfirmed suggestions"
  - "Rule 1 auto-fix: test_delete_session_cascades_answers pre_count updated from ==1 to >=1 to account for 30 pre-seeded CVI rows introduced by create_session"
metrics:
  duration: "~10 minutes"
  completed: "2026-05-07"
  tasks_completed: 1
  tasks_total: 1
---

# Phase 53 Plan 03: QRAMM Evidence Bridge — Router Wiring Summary

**One-liner:** Three surgical edits to qramm.py wire populate_cvi_suggestions into create_session (with 30 CVI row pre-seeding) and add confirmed_at auto-set in save_answers, turning all 8 Phase 53 tests GREEN.

## Edits Applied

### Edit 1 — New imports (lines 27-28 area)

Added two imports to the existing import block:

```python
from quirk.qramm.evidence_bridge import populate_cvi_suggestions
from quirk.qramm.questions import QRAMM_QUESTIONS, get_question
```

`QRAMM_QUESTIONS` appended to the existing `get_question` import line. `populate_cvi_suggestions` added as a new import line.

### Edit 2 — create_session modification (~lines 109-155)

Changed `db.commit()` to `db.flush()` immediately after `db.add(session)`, then inserted a pre-creation loop for 30 blank CVI `QRAMMAnswer` rows, then called `db.commit()` + `db.refresh(session)`, then called `populate_cvi_suggestions(session.id, db)` synchronously.

Key pattern:
```python
db.add(session)
db.flush()  # get session.id without committing yet

for q in QRAMM_QUESTIONS:
    if q["dimension"] != "CVI":
        continue
    db.add(QRAMMAnswer(
        session_id=session.id,
        question_number=q["question_number"],
        dimension=q["dimension"],
        practice_area=q["practice_area"],
        answer_value=None,
        suggested_answer=None,
    ))
db.commit()
db.refresh(session)

populate_cvi_suggestions(session.id, db)
```

### Edit 3 — save_answers confirmed_at auto-set (~lines 204-208)

Appended two lines to the existing `else` branch (update path) in `save_answers`:

```python
if existing.suggested_answer is not None and item.answer_value is not None:
    existing.confirmed_at = _now_iso()
```

This satisfies D-09 (QRAMM-13/14): only fires for bridge-populated rows where the human is writing an answer_value. Manual-only rows (suggested_answer IS NULL) are unaffected.

## score_session Confirmation (D-10)

`score_session` was NOT modified. The existing filter at lines 218-222:
```python
QRAMMAnswer.answer_value.isnot(None)
```
correctly excludes unconfirmed suggestions (suggested_answer set but answer_value NULL) — no change needed.

## Test Results

```
============================= test session starts ==============================
collected 36 items

tests/test_qramm_evidence_bridge.py::test_bridge_populates_on_session_create PASSED
tests/test_qramm_evidence_bridge.py::test_bridge_skips_when_no_scan_data PASSED
tests/test_qramm_evidence_bridge.py::test_no_risk_engine_import PASSED
tests/test_qramm_evidence_bridge.py::test_rc4_scan_lower_score_than_aes256 PASSED
tests/test_qramm_evidence_bridge.py::test_unconfirmed_excluded_from_score PASSED
tests/test_qramm_evidence_bridge.py::test_confirmed_included_in_score PASSED
tests/test_qramm_evidence_bridge.py::test_confirmed_at_auto_set PASSED
tests/test_qramm_evidence_bridge.py::test_badge_signal_data_model PASSED
tests/test_qramm_router.py (19/19 PASSED — including utcnow gate, cascade test)
tests/test_qramm_scoring.py (9/9 PASSED)

============================== 36 passed in 0.47s ==============================
```

**Phase 53 total: 8/8 GREEN. Phase 51 router: 19/19 GREEN. Phase 51 scoring: 9/9 GREEN.**

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test_delete_session_cascades_answers pre-count assertion**
- **Found during:** Task 1 verification
- **Issue:** `pre_count == 1` failed because `create_session` now pre-creates 30 CVI rows, making the total 31 (30 CVI + 1 saved answer) — not 1.
- **Fix:** Changed `assert pre_count == 1` to `assert pre_count >= 1` with a comment explaining the new behavior. The test's actual intent (cascade-delete removes ALL rows) is unchanged — the `post_count == 0` assertion was already correct.
- **Files modified:** `tests/test_qramm_router.py` (line 239)
- **Commit:** 65e45fe

## Known Stubs

None. All CVI derivation logic is fully implemented via the bridge (Plan 02). Router wiring is complete.

## Threat Flags

None. No new network endpoints or auth paths introduced. The `confirmed_at` write is server-side-only via `_now_iso()` (`datetime.now(timezone.utc)`) and is guarded by the `suggested_answer IS NOT NULL` check, mitigating T-53-03-01. All DB writes are parameterized via SQLAlchemy ORM.

## Self-Check: PASSED

- [x] `quirk/dashboard/api/routes/qramm.py` modified — 3 edits applied
- [x] `tests/test_qramm_router.py` modified — Rule 1 fix for cascade test
- [x] Commit 65e45fe exists
- [x] `python -m py_compile quirk/dashboard/api/routes/qramm.py` exits 0
- [x] Bridge import present
- [x] QRAMM_QUESTIONS import present
- [x] Bridge call site `populate_cvi_suggestions(session.id, db)` present
- [x] `db.flush()` pattern adopted
- [x] CVI filter loop present
- [x] `existing.confirmed_at = _now_iso()` present
- [x] `if existing.suggested_answer is not None` guard present
- [x] `QRAMMAnswer.answer_value.isnot(None)` count >= 1 (score_session unchanged)
- [x] utcnow count = 0 in non-comment lines
- [x] All 8 Phase 53 tests GREEN
- [x] All Phase 51 router tests GREEN (19/19)
- [x] All Phase 51 scoring tests GREEN (9/9)
- [x] 36/36 total GREEN
- [x] No unexpected file deletions in commit
- [x] STATE.md not modified
- [x] ROADMAP.md not modified
