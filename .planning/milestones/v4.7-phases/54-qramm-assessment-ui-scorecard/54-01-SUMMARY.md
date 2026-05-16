---
phase: 54-qramm-assessment-ui-scorecard
plan: "01"
subsystem: qramm-backend
tags: [qramm, fastapi, sqlite-migration, dashboard-api, tdd]
completed: 2026-05-07
duration_seconds: 219

dependency_graph:
  requires: []
  provides:
    - evidence_note column on qramm_answers
    - GET /api/qramm/sessions endpoint
    - POST /api/qramm/profiles endpoint
    - POST /api/qramm/assessment/draft endpoint
    - GET /api/qramm/sessions/{id}/answers endpoint
  affects:
    - plans 03 and 04 (React UI that consumes these endpoints)

tech_stack:
  added:
    - _compute_multiplier lookup table (industry + sensitivity delta formula)
  patterns:
    - idempotent ALTER TABLE migration via sa_inspect + _SAFE_COL_RE guard
    - TDD RED/GREEN per task (failing tests committed before implementation)

key_files:
  created:
    - tests/test_qramm_answer.py (82 lines — 3 migration behavior tests)
  modified:
    - quirk/models.py (155 lines — added evidence_note column to QRAMMAnswer)
    - quirk/db.py (284 lines — added _PHASE54_QRAMM_ANSWER_DDLS + _ensure_phase54_qramm_columns + init_db() call)
    - quirk/dashboard/api/routes/qramm.py (496 lines — added 4 endpoints, 6 Pydantic models, multiplier helper)
    - tests/test_qramm_router.py (516 lines — added 10 new tests for new endpoints)

decisions:
  - "Used static lookup table for multiplier computation (RESEARCH.md A4) rather than formula — deterministic, testable, matches spec"
  - "Tests 7 and 9 use SGRM question numbers (31, 32) instead of CVI to avoid collision with pre-seeded CVI rows from create_session Phase 53"
  - "Pre-existing test_cbom_schema_validation failures (18) confirmed unrelated to this plan via git stash verification"

metrics:
  tasks_completed: 2
  tasks_total: 2
  tests_added: 13
  files_created: 1
  files_modified: 4
  duration: "219s"
---

# Phase 54 Plan 01: QRAMM Backend Foundation Summary

**One-liner:** Added `evidence_note` column + idempotent migration to `qramm_answers`, and 4 new FastAPI endpoints (session list, profile create with multiplier, single-answer draft, answer read) with 13 pytest tests proving round-trip correctness.

## What Was Built

### Task 1: evidence_note column + idempotent migration

- Added `evidence_note = Column(Text, nullable=True)` to `QRAMMAnswer` ORM (quirk/models.py)
- Added `_PHASE54_QRAMM_ANSWER_DDLS` dict and `_ensure_phase54_qramm_columns(engine)` migration function to quirk/db.py, following the `_ensure_phase46_columns` shape exactly
- Wired `_ensure_phase54_qramm_columns(engine)` into `init_db()` after `_ensure_qramm_tables(engine)`
- Created `tests/test_qramm_answer.py` with 3 behavior tests (column existence, idempotency, round-trip)

### Task 2: 4 new QRAMM endpoints with multiplier computation

**Multiplier formula (static lookup table):**

| Industry | Base |
|----------|------|
| financial_services / government | 1.20 |
| healthcare | 1.15 |
| energy | 1.10 |
| technology | 1.05 |
| other | 1.00 |
| retail | 0.95 |

| Data Sensitivity | Delta |
|-----------------|-------|
| restricted_secret / restricted | +0.20 |
| confidential | +0.10 |
| internal | 0.00 |
| public | -0.10 |

Clamped to [0.8, 1.5] with `round(value, 2)`.

**New endpoints registered:**

| Path | Method | Status | Description |
|------|--------|--------|-------------|
| `/api/qramm/sessions` | GET | 200 | List all sessions, most-recent first, with answers_count |
| `/api/qramm/profiles` | POST | 201 | Create org profile, compute multiplier, link to session.profile_id |
| `/api/qramm/assessment/draft` | POST | 200 | Upsert single answer; sets confirmed_at if suggested_answer exists (D-04/D-05) |
| `/api/qramm/sessions/{session_id}/answers` | GET | 200/404 | Return all answer rows with suggested/confirmed state |

**Pydantic models added:** `SessionSummary`, `CreateProfileRequest`, `CreateProfileResponse`, `DraftAnswerRequest`, `AnswerRead`

**10 new tests added to test_qramm_router.py:**
- test_list_sessions, test_list_sessions_orders_desc
- test_create_profile, test_create_profile_multiplier_varies
- test_draft_answer_creates_row, test_draft_answer_updates_row, test_draft_answer_confirms_when_suggested, test_draft_answer_validation
- test_read_answers_includes_suggested, test_read_answers_404

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Tests 7 and 9 had duplicate-row collision with Phase 53 pre-seeded CVI rows**
- **Found during:** Task 2 GREEN phase (MultipleResultsFound exception)
- **Issue:** `create_session` pre-seeds 30 CVI answer rows (Q1-Q30). Tests pre-inserting rows for Q10 and Q2 (CVI) triggered `MultipleResultsFound` in `one_or_none()`
- **Fix:** Changed test rows to use Q31 and Q32 (SGRM dimension), which are not pre-seeded
- **Files modified:** tests/test_qramm_router.py
- **Commit:** 73d4cbf

## Threat Coverage

All 7 STRIDE threats from the threat model are mitigated as implemented:
- T-54-01/T-54-02: Pydantic `Field(ge=1, le=120)` and `Field(ge=1, le=4)` — tested in test_draft_answer_validation
- T-54-03: `max_length=2000` on evidence_note — validated by Pydantic
- T-54-04: `json.dumps(list)` for regulatory_obligations — no eval/exec
- T-54-06: `confirmed_at` server-set via `_now_iso()` — never from client
- T-54-07: `_SAFE_COL_RE.match(col)` guard on migration column names

## Self-Check

Files exist check:
- quirk/models.py: FOUND
- quirk/db.py: FOUND
- quirk/dashboard/api/routes/qramm.py: FOUND
- tests/test_qramm_answer.py: FOUND
- tests/test_qramm_router.py: FOUND

Commits check:
- 0f5c85e (RED Task 1): FOUND
- 72bd5c6 (GREEN Task 1): FOUND
- c6641ff (RED Task 2): FOUND
- 73d4cbf (GREEN Task 2): FOUND

## Self-Check: PASSED
