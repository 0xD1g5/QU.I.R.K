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

Phase 230 (2026-10-23): + `261023-detect-kerberos-placeholder-rows-count-as-assessed` (resolve before or in Phase 233).

## Closure (2026-10-27)

**CLOSED by Phase 234 (SCORE-09).** Phase 233 built the third measurement instrument this item asked for
(`.planning/decisions/233-p2b-third-instrument-measurement.md`); Phase 234 implemented the two-part shape it pointed
to: scoring 4.0, commit `23ef422875071113ca33e81c9eb63ce35d2db4de` (absolute-count penalties at N_REF = 40, the
classical-key rule, the PQC certificate bucket, Kerberos placeholder rows not assessed). The P2b property passes
without xfail and the instrument shows 0 rising series over 5 rungs x 5 readings x 4 points. Re-measurement record:
`.planning/decisions/234-p2b-fix-and-ladder-remeasurement.md` (`cfde8c90`; code-review fixes D-27..D-31 in §13,
`5023507a`). The member todo `261023-detect-kerberos-placeholder-rows-count-as-assessed` closed in `23ef4228` and
the owning todo `p2b-healthy-endpoints-dilute-the-readiness-score` closed with this row.

**Successor:** HORIZON 999.139 (`.planning/backlog/999.139-score-truth-residuals-after-234/IDEA.md`) owns the
residuals the record discloses.
