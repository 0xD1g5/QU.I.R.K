# 999.120 — P2b: observing more healthy endpoints still raises the readiness score

**Filed:** 2026-10-02 (v5.26 milestone re-audit)
**Priority:** P1 (inherited from the todo; the client's grade improves without their security improving)
**Horizon entry:** `HORIZON.md` Open-Item Ledger, row `999.120`.

## Why this exists

Phase 212 (v5.25, "Score Dilution — Decision Only") measured three candidate fixes and recommended
NONE (`.planning/decisions/212-score-dilution-denominator-decision.md`). Its section 8 handed
implementation to "a post-v5.25 phase in the next milestone, OPERATOR-RESERVED, confirmed at milestone
close". That confirmation never happened at the v5.25 or v5.26 close, so the todo
`p2b-healthy-endpoints-dilute-the-readiness-score.md` kept `resolves_phase: 212`, a closed phase. The
v5.26 re-audit found it through the new todo -> live-owner gate
(`tests/test_backlog_reconciliation_gate.py::test_no_pending_todo_points_at_a_closed_owner`).

## Feasibility & Effort

| Item | Feasibility | Size | Unknowns | Spike? |
|---|---|---|---|---|
| Close P2b | **CONFIRMED open** — `tests/test_score_properties.py:573` is still `xfail(strict=True)`; `assessable_endpoint_count` (`quirk/intelligence/evidence.py:154`, `:250`) grows with scan depth and is the endpoint denominator at `quirk/intelligence/scoring.py:412` | L | Which fix shape: none of 212's three candidates cleared both axes | YES — 212 says a third measurement instrument (reading the EMITTED score) is needed before a ceiling-shaped candidate can be evaluated |

### Costs not visible in the site count

- A denominator change rescales every ladder rung together; all five rungs must be re-measured (212 §3, §8).
- Not a release-phase item: re-scoring inside a tag freezes an unmeasured number (212 §8).
- Operator-reserved: the owner phase and its milestone are the operator's call, not a planner's.
