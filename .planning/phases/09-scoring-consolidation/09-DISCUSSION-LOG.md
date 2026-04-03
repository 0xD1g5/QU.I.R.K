# Phase 9: Scoring Consolidation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the discussion.

**Date:** 2026-04-03
**Phase:** 09-scoring-consolidation
**Mode:** discuss
**Areas analyzed:** Migration strategy, Profile weight tables, Roadmap format, Narrative interpretation

## Gray Areas Presented

| Area | Options Presented | User Choice |
|------|------------------|-------------|
| Migration strategy | Delete assessment/ compute modules / Deprecated aliases / Leave operator_context only | **Delete assessment/ compute modules** |
| Roadmap format | NOW/NEXT/LATER (unified) / Keep Wave 1/2/3 in exec summary | **NOW/NEXT/LATER** |
| Narrative interpretation | Port rich logic to evidence dict / Simplify to scorecard bullets | **Port the rich logic** |
| Profile weight tables | Agility-focused multipliers / Uniform scaling / Claude decides | **Agility-focused** |

## Codebase Findings

### Dual scoring (CONCERNS.md §4.1–4.3)
- `executive.py` imports all four compute functions from `assessment/` (readiness_score, confidence, transition_planner, interpretation_engine)
- `writer.py` imports equivalent functions from `intelligence/` (scoring, confidence, roadmap)
- Both run on every scan — two different scores in two different artifacts

### calibration_overrides (§12.1)
- `cfg.intelligence.calibration_overrides` loaded by config.py but never passed to `compute_readiness_score()` as `weights`
- `compute_readiness_score()` already has a `weights` param — just needs wiring

### operator_context.py survival
- `run_scan.py` imports `prompt_for_context` and `attach_context` from `assessment/operator_context`
- Must not be deleted — out of scope for Phase 9 compute cleanup

### migration_advisor.py survival
- Only used by `executive.py` for `recommend_migration_paths(findings)`
- No intelligence layer equivalent; keep in place

## Corrections Made

No corrections — all decisions were confirmed from presented options.
