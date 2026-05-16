---
phase: 51-qramm-core-infrastructure
plan: "03"
subsystem: qramm-api
tags: [fastapi, router, pydantic, qramm, crud, sqlite]
dependency_graph:
  requires: [51-01, 51-02]
  provides: [qramm-rest-api]
  affects: [quirk/dashboard/api/app.py, quirk/dashboard/api/routes/qramm.py]
tech_stack:
  added: []
  patterns: [inline-pydantic-models, explicit-cascade-delete, get-session-or-404-helper]
key_files:
  created:
    - quirk/dashboard/api/routes/qramm.py
  modified:
    - quirk/dashboard/api/app.py
decisions:
  - "Explicit QRAMMAnswer delete before session delete (Pitfall 2 — SQLite FK not enforced)"
  - "QRAMM router registered between trends.router and SPA catch-all (Pitfall 5 prevention)"
  - "json.dumps(default=str) on score_json persistence prevents non-serializable type leaks (T-51-12)"
  - "SaveAnswersRequest answers list capped at max_length=120 to limit DoS surface (T-51-10)"
metrics:
  duration: "~8 minutes"
  completed: "2026-05-05"
  tasks_completed: 2
  tasks_total: 2
  files_created: 1
  files_modified: 1
requirements: [QRAMM-02]
---

# Phase 51 Plan 03: QRAMM CRUD Router Summary

**One-liner:** FastAPI CRUD router for QRAMM with 5 endpoint families, inline Pydantic validators, weakest-link score persistence to SQLite, and explicit cascade delete.

## What Was Built

### Task 1 — quirk/dashboard/api/routes/qramm.py (280 lines)

New `qramm.py` router with 5 endpoint families and all inline Pydantic models:

| Endpoint | Method | Status | Description |
|----------|--------|--------|-------------|
| `/api/qramm/sessions` | POST | 201 | Create session; sets status="draft", model_version from QRAMM_MODEL |
| `/api/qramm/sessions/{id}` | GET | 200/404 | Read session; parses score_json; returns answers_count |
| `/api/qramm/sessions/{id}/answers` | POST | 200/404 | Bulk upsert QRAMMAnswer rows; dimension/practice_area from get_question() |
| `/api/qramm/sessions/{id}/score` | POST | 200/404 | Compute weakest-link score via scoring.py; persist to score_json; set status="scored" |
| `/api/qramm/sessions/{id}` | DELETE | 204/404 | Explicit QRAMMAnswer cascade, then session delete |

Inline Pydantic models include Field validators:
- `AnswerItem.answer_value`: `Field(ge=1, le=4)` — rejects out-of-range values with 422 (T-51-08)
- `AnswerItem.question_number`: `Field(ge=1, le=120)` — rejects out-of-range question numbers (T-51-09)
- `SaveAnswersRequest.answers`: `Field(max_length=120)` — caps batch size at 120 (T-51-10)

### Task 2 — quirk/dashboard/api/app.py (+2 lines)

Minimal diff:
1. Added `qramm` to the routes import alongside `health, pdf, scan, trends`
2. Added `application.include_router(qramm.router, prefix="/api")` after the trends router registration, before the SPA catch-all (Pitfall 5 mitigation)

## Verification Results

- `python -m compileall quirk/dashboard/api/routes/qramm.py quirk/dashboard/api/app.py` — passed
- Router exports 5 routes — passed
- All 4 path families present in live FastAPI app — passed (5 routes matched `/api/qramm/sessions*`)
- End-to-end smoke: POST session (201) → GET session (200) → DELETE session (204) — passed

## Deviations from Plan

None — plan executed exactly as written.

## Threat Coverage

All STRIDE mitigations from the plan's threat register are implemented:

| Threat | Mitigation | Implemented |
|--------|-----------|-------------|
| T-51-08 | AnswerItem Field(ge=1, le=4) | Yes |
| T-51-09 | AnswerItem Field(ge=1, le=120) | Yes |
| T-51-10 | SaveAnswersRequest max_length=120 | Yes |
| T-51-11 | _get_session_or_404 raises HTTPException(404) | Yes |
| T-51-12 | json.dumps(default=str) | Yes |
| T-51-13 | Explicit QRAMMAnswer.delete() before session.delete() | Yes |
| T-51-14 | Auth accept (localhost-only) | Accepted per plan |
| T-51-15 | Score race accept (per-request session) | Accepted per plan |

## Known Stubs

None — all endpoints are fully wired. Score computation calls the real scoring module. Answers upsert calls the real questions catalog.

## Threat Flags

None — no new network surfaces beyond the documented /api/qramm/* routes.

## Commits

| Task | Commit | Files |
|------|--------|-------|
| 1 — qramm.py router | dc6586e | quirk/dashboard/api/routes/qramm.py (created, 280 lines) |
| 2 — app.py registration | fa939a2 | quirk/dashboard/api/app.py (+2 lines) |

## Self-Check: PASSED

| Check | Result |
|-------|--------|
| quirk/dashboard/api/routes/qramm.py exists | FOUND |
| quirk/dashboard/api/app.py exists | FOUND |
| .planning/phases/51-qramm-core-infrastructure/51-03-SUMMARY.md exists | FOUND |
| Commit dc6586e exists | FOUND |
| Commit fa939a2 exists | FOUND |
