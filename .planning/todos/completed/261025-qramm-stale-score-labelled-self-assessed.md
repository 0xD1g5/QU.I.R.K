---
type: todo
created: 2026-10-25
source: Phase 231 review round R1 (WR-01), 231-REVIEW-R1.md; R1 reported BLOCKERS 0
priority: high
area: quirk/dashboard/api/routes/qramm.py (score_session, build_compliance_rows), src/dashboard/src/components/qramm/ScorecardTab.tsx, src/dashboard/src/lib/qramm-assessment.ts, src/dashboard/src/hooks/useQRAMMPrintData.ts
status: completed
resolved: 2026-10-27
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

## Resolution

Resolved 2026-10-27 by Phase 234 (SCORE-10), decisions D-14, D-15 and D-25, with the review fixes D-27 and D-31 (IN-04).

- **D-15 (the fix shape R1 proposed first).** `score_session` saves each dimension's answered count in `score_json` (`answered_by_dimension`). A dimension whose live answered count differs from the saved count reads **"Stale — recalculate"**, never "Self-assessed", on the API, the scorecard, the compliance map and print. Commits: 234-02 `d56af77f` (red, contract cases) and `f56ae61f` (Python); 234-04 `486e0052` (red, vitest), `9dda7bfd` (dashboard), `279c1088` (scorecard Not-assessed fix found by mutation M6-TS), bundles `dd79fa28` and `3fc322f7`.
- **D-27 (code review CR-01).** The overall of a stale current-format score also reads "Stale — recalculate" instead of a maturity level; the API's `score_overall_state` gains `"stale"`, and print consumes it. Commits `b92535d9` (red), `831d76a3`, bundle `747e3ec5`.
- **D-31 IN-04.** Non-integer persisted counts read stale in Python, as in the TS twin (`c3c3e77d`).
- **Contract cases** in `qramm-assessment-contract.json`, each asserted by both the pytest and vitest halves: `stale_case` (WR-01's reproduction: answer after scoring; the ITR rows and the overall read stale), `legacy_score_json` (D-25) and `non_integer_counts_case`.
- **D-25, a deliberate change to this todo's last bullet.** The todo asked that a `score_json` without the new key keep today's behaviour. Phase 234 decided otherwise (D-25 revision 2): without saved counts, newer answers cannot be ruled out, so a pre-upgrade score reads **"Recalculate to apply the updated overall"** for the overall and Stale for every answered dimension until the session is re-scored. Pinned by the `legacy_score_json` case.
- **Known limitation, D-21.** Staleness compares answered **counts**, not values, so re-answering an already-answered question with a different value is not flagged. Follow-up: `.planning/todos/pending/261027-qramm-stale-detection-compares-counts-not-values.md` (owner HORIZON 999.139, filed in the SCORE-09 closure commit).
- UAT: UAT-234-10 and UAT-234-11 (`b0f5451e`). Record: `.planning/decisions/234-p2b-fix-and-ladder-remeasurement.md` §9, §10 and §13.
