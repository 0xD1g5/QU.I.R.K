---
type: todo
created: 2026-10-25
source: Phase 231 review round R1 (WR-01), 231-REVIEW-R1.md; R1 reported BLOCKERS 0
priority: high
area: quirk/dashboard/api/routes/qramm.py (score_session, build_compliance_rows), src/dashboard/src/components/qramm/ScorecardTab.tsx, src/dashboard/src/lib/qramm-assessment.ts, src/dashboard/src/hooks/useQRAMMPrintData.ts
status: pending
resolves_phase: null
owner: "SCORE-10"
---

# QRAMM: a stale saved score is shown under a "Self-assessed" label

The assessed state comes from the session's **live** answers. The score comes from the **saved**
`score_json`. Saving answers never invalidates that score.

- [ ] **WR-01** (reproduced by R1 through TestClient):
  1. Answer Q1, then Calculate Score.
  2. Answer all 30 ITR questions at level 4, without rescoring.
  3. The ITR rows come back `self-assessed` with a score of `0.0`, on all three surfaces.

  So the 0.0 placeholder that Phase 231 D-07/D-21a meant to hide reappears under a label that says it is real.
  The surfaces still agree (D-09 holds), so they are consistently wrong.
- **Fix shape (R1):**
  - `score_session` saves each dimension's answered count inside `score_json`.
  - Once a session is scored, the state is derived from that saved count.
  - Alternatively, show the score as stale (or pending) whenever answers changed after the last score.
  - Either way, update the shared contract fixture `qramm-assessment-contract.json` so pytest and vitest parity both cover it.
  - A `score_json` without the new key keeps today's behaviour.

## Feasibility & Effort

- **CONFIRMED** by R1's TestClient reproduction, and re-read by the orchestrator at `routes/qramm.py:719-780`.
- Effort: **S-M**. One key added to `score_json`, the row builder, the scorecard and print state derivation, and the contract fixture plus both parity halves.
- It is owned by **SCORE-10** (Phase 234) because that phase already reopens how the QRAMM overall treats unassessed dimensions, and both are the same truth question.
