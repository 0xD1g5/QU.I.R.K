---
phase: 51-qramm-core-infrastructure
plan: "01"
subsystem: database
tags: [sqlalchemy, orm, sqlite, migration, qramm, tdd]
requirements: [QRAMM-01]

dependency_graph:
  requires: []
  provides:
    - QRAMMSession ORM class on Base.metadata (qramm_sessions table)
    - QRAMMAnswer ORM class on Base.metadata (qramm_answers table)
    - QRAMMProfile ORM class on Base.metadata (qramm_profiles table)
    - _ensure_qramm_tables() in quirk/db.py
    - init_db() now creates all QRAMM tables idempotently
  affects:
    - quirk/models.py
    - quirk/db.py

tech_stack:
  added: []
  patterns:
    - SQLAlchemy declarative ORM models on shared Base
    - Base.metadata.create_all(checkfirst=True) for idempotent table creation

key_files:
  created:
    - tests/test_qramm_models.py
  modified:
    - quirk/models.py
    - quirk/db.py

decisions:
  - "Float imported alongside existing sqlalchemy column types to support QRAMMProfile.multiplier"
  - "Phase 53 columns (suggested_answer, confirmed_at, evidence_source) pre-provisioned in QRAMMAnswer per Open Question 2 to avoid ALTER TABLE in Phase 53"
  - "_ensure_qramm_tables uses create_all(checkfirst=True) rather than ALTER TABLE pattern since these are entirely new tables, not new columns on crypto_endpoints"

metrics:
  duration: "166s"
  completed: "2026-05-06"
  tasks_completed: 2
  files_modified: 2
  files_created: 1
---

# Phase 51 Plan 01: QRAMM Core Infrastructure — Database Foundation Summary

**One-liner:** Three SQLAlchemy ORM declarative models (QRAMMSession, QRAMMAnswer, QRAMMProfile) registered on Base.metadata with idempotent `_ensure_qramm_tables()` called from `init_db()`.

## What Was Built

### Task 1: QRAMM ORM Models (quirk/models.py)

Added three declarative model classes at the bottom of `quirk/models.py`, after the existing `CryptoEndpoint` class:

- **QRAMMSession** (`qramm_sessions`): id, org_name, created_at, updated_at, model_version, profile_id, status, score_json (Text — persisted weakest-link score blob)
- **QRAMMAnswer** (`qramm_answers`): id, session_id, question_number, dimension, practice_area, answer_value, plus Phase 53 pre-provisioned columns: suggested_answer, confirmed_at, evidence_source
- **QRAMMProfile** (`qramm_profiles`): id, session_id, industry, org_size, data_sensitivity, regulatory_obligations, geographic_scope, multiplier (Float, 0.8-1.5), created_at

Also updated the sqlalchemy import line to include `Float`.

### Task 2: _ensure_qramm_tables() in quirk/db.py

Added `_ensure_qramm_tables(engine)` immediately before `init_db()`. The function calls `Base.metadata.create_all(engine, checkfirst=True)` — the correct pattern for entirely new tables (not ALTER TABLE). Added a call to `_ensure_qramm_tables(engine)` in `init_db()` after `_ensure_phase46_columns(engine)`.

## TDD Process

- **RED commit:** `e9e22a4` — 36 failing tests covering import, column presence, and idempotency
- **GREEN commits:** `5363597` (models.py) and `ac1af2e` (db.py) — all 36 tests pass

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — these are schema-only tables. No stub data or placeholder values.

## Threat Surface Scan

No new network endpoints, auth paths, or untrusted input paths introduced. All changes are local SQLite DDL operations (checkfirst=True prevents recreation). T-51-01 mitigation confirmed via idempotency test in Task 2.

## Self-Check: PASSED

| Item | Status |
|------|--------|
| quirk/models.py | FOUND |
| quirk/db.py | FOUND |
| tests/test_qramm_models.py | FOUND |
| 51-01-SUMMARY.md | FOUND |
| e9e22a4 (RED tests commit) | FOUND |
| 5363597 (models GREEN commit) | FOUND |
| ac1af2e (db GREEN commit) | FOUND |

## TDD Gate Compliance

- RED gate commit: `e9e22a4` — `test(51-01): add failing tests for QRAMM ORM models and db init`
- GREEN gate commit (models): `5363597` — `feat(51-01): add QRAMMSession, QRAMMAnswer, QRAMMProfile ORM models`
- GREEN gate commit (db): `ac1af2e` — `feat(51-01): add _ensure_qramm_tables() to db.py and call from init_db()`
- All 36 tests pass in GREEN state.
