---
type: todo
created: 2026-10-27
source: Phase 234 (D-21; decision record §10)
priority: medium
area: quirk/qramm/assessment_state.py (row_coverage_status, overall_state), quirk/dashboard/api/routes/qramm.py (score_session), src/dashboard/src/lib/qramm-assessment.ts
status: pending
resolves_phase: null
owner: "999.139"
---

# QRAMM stale detection compares answered counts, not answer values

**Owner:** 999.139

SCORE-10 (Phase 234, D-15) marks a saved QRAMM score stale when a dimension's live answered count differs from
the count saved with the score (`answered_by_dimension` in `score_json`;
`quirk/qramm/assessment_state.py:101`, `scored_answered != answered`, and the overall check at `:204`; the TS
twin in `src/dashboard/src/lib/qramm-assessment.ts`). Re-answering an already-answered question with a different
value keeps the count the same, so the saved score is shown as current ("Self-assessed" and a maturity level)
although it no longer reflects the answers.

## Proposed fix shape

Persist a digest of the answers with the score (for example a SHA-256 over the sorted `(question_id, value)`
pairs, per dimension or for the session) and compare it with the live digest; keep the count comparison as the
fallback for scores saved before the digest existed. Extend the shared contract
`src/dashboard/src/lib/__fixtures__/qramm-assessment-contract.json` with a "same count, changed value" case so
the pytest and vitest halves both cover it.

## Feasibility & Effort

**CONFIRMED** by reading the comparison above. Effort **S**: one key in `score_json`, the two twins and one
contract case.
