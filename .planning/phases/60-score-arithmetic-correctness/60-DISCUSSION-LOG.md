# Phase 60: Score Arithmetic Correctness - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-09
**Phase:** 60-score-arithmetic-correctness
**Areas discussed:** Clamp strategy, Property test approach, Multiplier 400 path, SCORE-04 scope

---

## Clamp Strategy (SCORE-01)

| Option | Description | Selected |
|--------|-------------|----------|
| Minimal clamp | Add `_clamp(total_score, 0, 100)` inside `compute_readiness_score()` — subscore caps unchanged | ✓ |
| Weight renormalization | Adjust all SCORE_WEIGHTS so they sum to 100 — avoids needing a clamp at all | |

**User's choice:** Recommended — minimal clamp
**Notes:** Renormalization would change all weight values and break existing test fixtures.
The WR-06 warning (weights sum to 261) is deferred to v5.x tech-debt sweep.

---

## Property Test Approach (SCORE-01 test)

| Option | Description | Selected |
|--------|-------------|----------|
| Seeded random loop | `random.Random(42)` loop, 1,000 synthesized evidence dicts — zero new deps | ✓ |
| Hypothesis | `@given` property testing — stronger shrinking, but adds new dev dependency | |

**User's choice:** Recommended — seeded random loop
**Notes:** Hypothesis not in pyproject.toml; adding it would be a new dependency.
The seeded loop is deterministic and achieves the same invariant coverage.

---

## Multiplier 400 Path (SCORE-02)

| Option | Description | Selected |
|--------|-------------|----------|
| Route-level guard | Remove Pydantic `ge/le`, add explicit `HTTPException(400)` in `score_session()` | ✓ |
| Pydantic validator | Keep `ge=0.8, le=1.5` — but produces 422, not 400 | |
| FastAPI exception handler | Override `RequestValidationError` globally to produce 400 — too broad | |

**User's choice:** Recommended — route-level guard
**Notes:** Pydantic bounds produce 422 (wrong input shape) not 400 (semantically invalid).
The field description is updated to include `[0.8, 1.5]` for OpenAPI schema documentation.
Error code `QRAMM_MULTIPLIER_OUT_OF_RANGE` follows the pattern from Phase 57.

---

## SCORE-04 Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Test-coverage only | Add parametrized sweep — maturity band logic already contiguous | ✓ |
| Logic fix + test | Fix gap in `_maturity_label()` AND add sweep test | |

**User's choice:** Recommended — test-coverage only
**Notes:** Live probe of `_maturity_label()` at all 0.05-step increments from 0.0–4.0
showed all labels present, no gaps. Audit BL-02 appears to flag missing test coverage
rather than an active logic bug. The parametrized sweep test at 0.5-step increments
provides the regression guard.

---

## Claude's Discretion

All four areas were decided by Claude's recommended approach; user confirmed
"take all recommended suggestions."

## Deferred Ideas

- SCORE_WEIGHTS normalization (WR-06): deferred to v5.x tech-debt sweep.
- `score_cap=25.0` magic constant extraction (WR-05): cleanup deferred.
