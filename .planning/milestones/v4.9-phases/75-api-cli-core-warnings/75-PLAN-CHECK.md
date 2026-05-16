# Phase 75 Plan Check — API + CLI + Core WARNINGs

**Date:** 2026-05-15
**Plans verified:** 75-01, 75-02, 75-03, 75-04
**Verdict:** PASSED WITH WARNINGS — execution can proceed

---

## Dimension Summary

| Dimension | Status |
|-----------|--------|
| context_compliance (D-01..D-18) | PASS (with explicit C-2 override surfaced) |
| success_criteria_coverage (SC 1–4) | PASS |
| audit_row_coverage (WR-01..WR-17, 17 rows) | PASS |
| research_concern_handling (C-1..C-5) | PASS — C-2 multiplier range preserved at `[0.8, 1.5]` |
| commit_atomicity | PASS (test commit → impl commit → audit commit per plan, 3 commits each) |

---

## Dimension 1: Context Compliance (D-01..D-18)

| Decision | Plan | Implementation Reference | Status |
|----------|------|--------------------------|--------|
| D-01 typed dict doctor checks | 75-01 Task 2 | `_check_dashboard` / `_check_network` rewritten with HTTP HEAD + DNS probes + remediation field | PASS |
| D-02 `_check_db` honors QUIRK_DB_PATH | 75-01 Task 2 | env-first resolution with readability validation | PASS |
| D-03 fail-loud `_default_db_path` | 75-01 Task 2 | canonical `./quirk-output/quirk.db` + `ValueError` on multi-DB | PASS (RESEARCH A1 honored) |
| D-04 microsecond scan_id window | 75-02 Task 2 | `datetime.fromisoformat` inclusive `[start, end]` | PASS |
| D-05 list_scans parsed-datetime grouping | 75-02 Task 2 | `.replace(microsecond=0)` keys, descending sort | PASS |
| D-06 multiplier server-validated pre-DB | 75-02 Task 2 | **DEVIATION ACKNOWLEDGED:** range stays `[0.8, 1.5]` per RESEARCH C-2 + explicit user override, NOT widened to `[0.0, 4.0]` | PASS-with-deviation |
| D-07 clamp-before-round | 75-02 Task 2 | `round(max(0.8, min(1.5, value)), 2)` | PASS |
| D-08 read_session 422 | 75-03 Task 2 | corrected catch tuple per C-3 + 422 raise with `safe_str` | PASS |
| D-09 `_derive_dar_findings` logged | 75-03 Task 2 | narrow tuple + `logger.warning` + AST-gate sentence dropped per C-4 | PASS |
| D-10 list_questions schema-drift | 75-03 Task 2 | real `QuestionItem` field names per C-5 | PASS |
| D-11 `_prompt_int` EOF-safe | 75-04 Task 2 | function-entry default check + bounded loop + EOFError catch returns default | PASS (RESEARCH A3 honored) |
| D-12 exposure 3-retry reprompt | 75-04 Task 2 | literal invalid-choice message + budget exhaustion ValueError | PASS |
| D-13 declared `enable_nmap` field | 75-04 Task 2 | dataclass field added + single setattr removed at `interactive.py:273` | PASS |
| D-14 validate.py artifact list | 75-04 Task 2 | `intelligence-{stamp}.json` added | PASS |
| D-15 qramm_cmd try/except | 75-04 Task 2 | wrapped `fromisoformat` + warning + fallback | PASS |
| D-16 QUIRK_OUTPUT_DIR guard | 75-04 Task 2 | mirrors `init_cmd.py:21-40` per user directive | PASS |
| D-17 RFC-1123 hostname validation | 75-04 Task 2 | `_HOSTNAME_RE` + `ipaddress` fallback ladder | PASS |
| D-18 do-not-touch list | all plans | exit-code semantics preserved; schema untouched; QRAMM taxonomy untouched; React deferred to 76 | PASS |

**Deferred Ideas excluded:** ✓ no underscore-tolerant hostnames, no JSON doctor output, no audit logging for multiplier rejections, no DB-disambiguation prompt.

---

## Dimension 2: Success Criteria Coverage (4 SCs)

| SC | Mapped Plan | Verification |
|----|-------------|--------------|
| SC-1 doctor + DB path determinism | 75-01 (APCL-01) | 6+ tests in `test_doctor_actionable.py` |
| SC-2 scan window + grouping + multiplier server-validate | 75-02 (APCL-02) | 8+ tests in `test_api_scan_window.py` |
| SC-3 QRAMM/DAR structured errors + schema drift | 75-03 (APCL-03) | 6+ tests in `test_api_qramm_hardening.py` |
| SC-4 interactive/validate/routes hardening (7 fixes) | 75-04 (APCL-04) | 14+ tests in `test_interactive_validate_routes.py` |

All 4 SCs mapped 1:1 to a plan. No SC fragments missing.

---

## Dimension 3: Audit Row Coverage (17 rows)

| Plan | WR rows closed | Lines flipped |
|------|----------------|---------------|
| 75-01 | WR-01, WR-02, WR-03 (3) | 186, 187, 188 |
| 75-02 | WR-04, WR-05, WR-06, WR-09 (4) | 189, 190, 191, 194 |
| 75-03 | WR-07, WR-08, WR-17 (3) | 192, 193, 202 |
| 75-04 | WR-10..WR-16 (7) | 195–201 |

Total = 3 + 4 + 3 + 7 = **17 rows**. Cross-check verified: plan 75-04 Task 3 acceptance includes `== 17` aggregated assertion across all four plans.

---

## Dimension 4: Research Concern Handling (C-1..C-5)

| Concern | Disposition in Plans | Status |
|---------|----------------------|--------|
| C-1 `doctor.py` → `doctor_cmd.py` | 75-01 objective explicitly notes shorthand, lands edits in `doctor_cmd.py` | PASS |
| C-2 multiplier range `[0.8, 1.5]` vs `[0.0, 4.0]` | 75-02 objective surfaces adjudication; **range preserved at `[0.8, 1.5]`** per user override + Phase 54 Pydantic constraint; error string uses `[0.8, 1.5]`; all must_haves + acceptance assert preserved range | **PASS — explicit override documented** |
| C-3 D-08 catch tuple | 75-03 uses `(json.JSONDecodeError, TypeError, ValueError)` | PASS |
| C-4 AST-gate file | 75-03 + 75-04 explicitly drop AST-gate sentence; no scope creep | PASS |
| C-5 list_questions field names | 75-03 uses real `QuestionItem` fields (`question_number`, `dimension`, `practice_area`, `text`, `maturity_labels`) | PASS |

**C-2 explicit verification:** every reference to the multiplier band in 75-02 reads `[0.8, 1.5]`. The CONTEXT D-06 `[0.0, 4.0]` text is acknowledged in the plan as superseded by RESEARCH C-2 + user prompt directive. No silent scope reduction — this is a deliberate adjudication recorded in the objective, error string, must_haves, acceptance criteria, and SUMMARY directive.

---

## Dimension 5: Commit Atomicity

Each plan structures three atomic commits:
1. `test(75-NN): ...` — RED tests committed
2. `feat(75-NN): ...` — GREEN implementation
3. `docs(75-NN): close ...` — audit ledger flip

This matches Phase 71/74 cadence. No multi-concern commits; AUDIT-TASKS.md flips are isolated as docs commits.

---

## Issues

### Warnings

**W-1 (dimension: scope_sanity / context_compliance):**
- Plan: 75-02
- Description: CONTEXT D-06 verbatim states multiplier range `[0.0, 4.0]`; the plan deliberately deviates to `[0.8, 1.5]` honoring RESEARCH C-2 + user override.
- Severity: WARNING (NOT blocker — the deviation is explicit, traceable to user prompt directive "DO NOT widen to [0.0, 4.0]", surfaced in plan objective, and aligns with Phase 54 Pydantic invariant).
- Fix hint: Confirmed acceptable per `feedback_planner_context_precedence.md`-style adjudication that the user has already issued in the prompt itself. No action required.

**W-2 (dimension: scope_sanity):**
- Plan: 75-04
- Description: 8 files modified, 3 tasks. Sits at the upper edge of the scope envelope but each fix (D-11..D-17) is independent and surgically bounded. Test module has >=14 functions — large but parametrized.
- Severity: WARNING.
- Fix hint: Acceptable given the audit-row clustering rationale; splitting would fragment audit-row ledger updates.

### Blockers

**None.**

---

## Verdict

`PASSED WITH WARNINGS` — plans are coherent, every D-NN has a covering task, every SC and WR row is addressed, C-2 multiplier range preservation is explicit and locked across must_haves + error strings + acceptance criteria, no Deferred Ideas have leaked into scope, and commit cadence is atomic. Execute Phase 75.

