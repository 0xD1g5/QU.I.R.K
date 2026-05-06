---
phase: 51-qramm-core-infrastructure
plan: 04
subsystem: qramm
tags: [tests, pytest, fastapi, testclient, qramm, scoring, questions]
requires: [51-01, 51-02, 51-03]
provides: [test_qramm_questions, test_qramm_scoring, test_qramm_router]
affects: []
tech-stack:
  added: []
  patterns: [UUID-named in-memory SQLite, dependency_overrides, TestClient smoke tests]
key-files:
  created:
    - tests/test_qramm_questions.py
    - tests/test_qramm_scoring.py
    - tests/test_qramm_router.py
  modified: []
decisions:
  - "Router tests use two _make_qramm_client() call variants: one accepting (TestClient, TestingSession) tuple for cascade-delete verification, one discarding session factory — same UUID-DB pattern as test_dashboard_trends.py"
  - "Pre-existing test failures in test_cli_correctness, test_doctor_cmd, test_v41_gap_closure, test_cbom_schema_validation are out-of-scope pre-existing issues; documented as deferred"
metrics:
  duration: "2m 55s"
  completed: "2026-05-06"
  tasks_completed: 2
  tasks_total: 2
  files_created: 3
  files_modified: 0
---

# Phase 51 Plan 04: QRAMM Test Suite Summary

QRAMM test suite with 35 tests across three files covering catalog schema/count/distribution (QRAMM-03), weakest-link scoring reference calculations (QRAMM-04), and full HTTP endpoint smoke tests with score persistence and cascade-delete verification (QRAMM-01/02).

## Tasks Completed

### Task 1: tests/test_qramm_questions.py + tests/test_qramm_scoring.py (commit 2021368)

**Questions catalog tests (7 tests):**
- `test_question_count` — asserts exactly 120 entries (QRAMM-03)
- `test_question_schema` — all required keys + 4 maturity labels per question
- `test_question_dimensions` — all dimensions in {CVI, SGRM, DPE, ITR}
- `test_question_distribution` — 30/dim, 10/practice-area, sequential numbering 1..120
- `test_q1_verbatim_csnp_text` — verbatim CSNP source match (D-01 traceability)
- `test_q120_verbatim_csnp_text` — verbatim CSNP source match (D-01 traceability)
- `test_get_question_out_of_range` — IndexError for 0 and 121

**Scoring unit tests (9 tests):**
- `test_practice_score_reference` — CSNP reference: [3,2,3,4,2,2,3,2,3,1] -> 2.5
- `test_practice_score_empty` — empty list returns 0.0
- `test_weakest_link_rule` — D-06: min([2.5, 3.4, 1.5]) == 1.5
- `test_weakest_link_empty` — empty returns 0.0
- `test_profile_multiplier` — 1.5 * 1.2 == 1.8 across all dims
- `test_overall_score_csnp_example` — (2.8, 3.1, 2.5, 2.9) -> 2.825 "Established"
- `test_overall_score_default_multiplier` — default mult=1.0
- `test_maturity_label_thresholds` — 9 boundary cases (Basic/Developing/Established/Advanced/Optimizing)
- `test_d09_isolation_no_forbidden_imports` — static source inspection confirms no risk_engine/scanner/db/models imports

### Task 2: tests/test_qramm_router.py (commit ae233d2)

**19 TestClient tests:**
- `test_qramm_tables_exist_after_init_db` — QRAMM-01: init_db() creates qramm_sessions, qramm_answers, qramm_profiles
- `test_qramm_init_db_idempotent` — second init_db() call does not error
- `test_create_session` — POST /api/qramm/sessions returns 201 + session_id + status=draft
- `test_create_session_empty_body` — empty JSON body accepted (org_name optional)
- `test_read_session_round_trip` — GET returns matching org_name, answers_count=0, score=null
- `test_read_session_not_found` — GET 9999 returns 404 with "Session not found"
- `test_save_answers_basic` — 200, saved_count=2, total_answered=2
- `test_save_answers_upsert_overwrites` — duplicate question_number upserts, not duplicates
- `test_save_answers_validation_rejects_out_of_range` — answer_value=5 -> 422
- `test_save_answers_validation_rejects_question_out_of_range` — question_number=121 -> 422
- `test_save_answers_session_not_found` — 9999 returns 404
- `test_score_session_full_120_answers` — 120 answers at value=2 -> overall=2.0, maturity="Developing"
- `test_score_session_persistence_round_trip` — D-10: score persisted, GET returns status=scored + matching score
- `test_score_session_with_multiplier` — profile_multiplier=1.2 applied: CVI.weighted=2.4
- `test_score_session_not_found` — 9999 -> 404
- `test_delete_session` — 204, then GET returns 404
- `test_delete_session_cascades_answers` — QRAMMAnswer rows removed pre/post verified via TestingSession direct query
- `test_delete_session_not_found` — 9999 -> 404
- `test_no_utcnow_in_qramm_module` — DEBT-01: zero utcnow() in qramm/*.py

## Deviations from Plan

### Out-of-scope pre-existing test failures

The following test failures exist on the base branch (prior to plan 51-04) and are unrelated to QRAMM:

- `tests/test_cli_correctness.py::test_no_quirk_scan_references` — docs/operators-guide.md contains "quirk scan" phrase
- `tests/test_doctor_cmd.py::test_doctor_exits_0_all_pass` — `quirk.cli.doctor_cmd` module not found
- `tests/test_v41_gap_closure.py::TestV41GapClosure::test_package_manifest_version_is_4_1_0` — version mismatch
- `tests/test_cbom_schema_validation.py` — excluded per plan instructions

These are logged to deferred-items and will not be addressed in this plan.

No deviations to QRAMM-related work. Plan executed exactly as written.

## Known Stubs

None. All test assertions use concrete values from QRAMM-verified sources.

## Threat Flags

None. Test files create no new network endpoints, auth paths, or trust boundaries.

## Self-Check: PASSED

- tests/test_qramm_questions.py: FOUND
- tests/test_qramm_scoring.py: FOUND
- tests/test_qramm_router.py: FOUND
- commit 2021368: FOUND
- commit ae233d2: FOUND
- 35 tests pass: VERIFIED
