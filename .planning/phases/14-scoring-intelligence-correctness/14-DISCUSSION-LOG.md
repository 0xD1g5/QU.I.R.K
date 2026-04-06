# Phase 14: Scoring & Intelligence Correctness - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the discussion flow.

**Date:** 2026-04-06
**Phase:** 14-scoring-intelligence-correctness
**Mode:** discuss

## Gray Areas Presented

| Area | Description |
|------|-------------|
| Test plan structure | 2-plan TDD vs single plan |
| SCORE-04 profile source | Where dashboard gets profile from |
| SCORE-02 fix direction | Remove phantom delta checks vs change default |

## Decisions Made

### Test Plan Structure
- **User chose:** 2-plan TDD (Recommended)
- **Decision:** Plan 1 = RED scaffold proving all 4 bugs; Plan 2 = GREEN fixes

### SCORE-04 Profile Source
- **User chose:** Read from stored intelligence JSON (Recommended)
- **Decision:** Extract `assessment.profile` from `intelligence-*.json`, pass to `compute_readiness_score()`. Do not re-read config at dashboard request time.

### SCORE-02 Fix Direction
- **User chose:** Remove delta requirement (Recommended)
- **Decision:** Remove `require_delta_if_baseline` logic entirely — delta reports not implemented.

## Scope Note

User raised scoring transparency: *"It would be ideal to define in reporting how scoring is calculated, or what scoring levels equal 'high', 'medium'... transparency is key for me when it comes to defining risk and scoring levels."*

**Routing:** Deferred to backlog at medium priority. User will review Phase 14 output (score drivers already in executive summary) before deciding if additional methodology explanation is needed.

## Codebase Scout Findings

- `intelligence/scoring.py` has `PROFILE_MULTIPLIERS` + `profile` param — structure correct
- `writer.py` correctly passes `profile=cfg.intelligence.profile` (reference call)
- `dashboard/api/routes/scan.py` lines 329-330 confirmed missing `profile` kwarg — SCORE-04 bug visible in code
- `validate.py` `expected_files` + `require_delta_if_baseline` logic confirmed — SCORE-02 target
- `migration_advisor.py` uses `"legacy tls" in title.lower()` — risk_engine emits matching title; need test to confirm end-to-end
