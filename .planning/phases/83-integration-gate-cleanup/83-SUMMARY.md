---
phase: 83
plan: 83
subsystem: integration-gate / cleanup
type: cleanup
requirements: [CLEAN-01]
tags: [integration-gate, score-weights, dead-code]
status: complete
updated: 2026-05-16
key-files:
  modified:
    - quirk/reports/writer.py
    - tests/test_score_weights_invariant.py
  removed:
    - quirk/engine/migration_planner.py
decisions:
  - "Inlined categorize_waves verbatim into writer.py (placed before SCHEMA_VERSION constant)"
  - "Test mocks at quirk.reports.writer.categorize_waves unchanged — namespace-of-use resolution"
  - "Honored actual path (quirk/engine/) over REQUIREMENTS' stated path (quirk/intelligence/)"
metrics:
  duration_min: 5
  completed: 2026-05-16
---

# Phase 83 Plan 83: Integration Gate + Cleanup Summary

**One-liner:** Wave A integration gate — bumped SCORE_WEIGHTS invariant from 261.0/29 → 275.0/36 absorbing Phase 79 SMIME + Phase 80 ADCS deltas, inlined `categorize_waves` into `quirk/reports/writer.py`, and removed the dead `quirk/engine/migration_planner.py` module.

## What Was Built

### 1. SCORE_WEIGHTS Invariant Bump (CLEAN-01 core)

`tests/test_score_weights_invariant.py`:
- `test_score_weights_sum_invariant`: assertion bumped `261.0` → `275.0` (+14.0)
- `test_score_weights_count_invariant`: assertion bumped `29` → `36` (+7)
- Docstrings cite Phase 83 rebalance with explicit per-source deltas:
  - Phase 79 SMIME: +3 entries / +6.0 sum
  - Phase 80 ADCS:  +4 entries / +8.0 sum
- Both tests flipped RED → GREEN.

Runtime verification:
```
$ python -c "from quirk.intelligence.scoring import SCORE_WEIGHTS; print(sum(SCORE_WEIGHTS.values()), len(SCORE_WEIGHTS))"
275.0 36
```

### 2. `categorize_waves` Inlined into `quirk/reports/writer.py`

- Function body copied verbatim from former `quirk/engine/migration_planner.py` (17 lines).
- Placement: module scope, before `SCHEMA_VERSION = 2` constant; well before the call site at `writer.py:225`.
- Docstring added crediting Phase 83 / CLEAN-01 origin.
- Import at former `writer.py:14` (`from quirk.engine.migration_planner import categorize_waves`) removed.

### 3. Dead Module Removed

- `git rm quirk/engine/migration_planner.py` ✓
- `find quirk/ -name "migration_planner*"` → empty (confirmed)
- `quirk/engine/` directory retained — it still holds `cache.py`, `findings_evaluator.py`, `profiles.py`, `rate_limiter.py`, `risk_engine.py`, plus `__init__.py`. Only the orphaned `migration_planner.py` was removed.

### 4. Mock-Path Verification (no test edits required)

`grep -rn "categorize_waves" tests/` confirmed all 9 mock sites target `quirk.reports.writer.categorize_waves`:

| File                                   | Sites |
| -------------------------------------- | ----- |
| tests/test_reports_writer.py           | 4     |
| tests/test_cbom_integration.py         | 3     |
| tests/test_cmvp_report_column.py       | 1     |
| tests/test_report_injection_hardening.py | 1   |

All mocks resolve at the *namespace-of-use* (`writer` module attribute lookup), so the inlined `def categorize_waves` continues to satisfy them — no patch path edits needed.

## Verification

| Check                                                                | Result                              |
| -------------------------------------------------------------------- | ----------------------------------- |
| `python -m compileall quirk/`                                        | Clean                               |
| `pytest tests/test_score_weights_invariant.py -v`                    | 2 PASSED (was RED)                  |
| `find quirk/ -name "migration_planner*"`                             | Empty                               |
| `grep -n "from quirk.engine.migration_planner" quirk/reports/writer.py` | No match                         |
| Sum invariant runtime                                                | 275.0 ✓                             |
| Count invariant runtime                                              | 36 ✓                                |

## Deviations from Plan

None for the in-scope work — plan executed exactly as written.

## Deferred / Pre-existing Issues (out of scope)

These failures **predate Phase 83** and were confirmed via `git stash`-baseline comparison. They are environment / fixture issues unrelated to Wave A integration:

1. **`module 'quirk.reports' has no attribute 'writer'`** — affects 16 tests across `test_reports_writer.py`, `test_cbom_integration.py`, `test_cmvp_report_column.py`, `test_report_injection_hardening.py`. Pre-existing import-graph issue; reproduces with our changes stashed. NOT introduced by inlining.
2. **`ValueError: Multiple QU.I.R.K. DBs found`** — 16 collection-time errors caused by 10 stray `*.db` files scattered across the repo (`./quirk.db`, `./output/quirk.db`, `./data/quirk.db`, worktree leftovers, etc.). Stale test-fixture pollution.

Recommended follow-up (separate housekeeping plan, NOT Phase 83): clean stray DBs and investigate the `quirk.reports.writer` import-resolution failure.

## Commit

- `52c91e9` — fix(83): integration gate — invariant bump + migration_planner inlined + dead module removed (CLEAN-01)

## Vault Note

`/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-83-Integration-Gate-Cleanup.md`

## Self-Check: PASSED

- `quirk/reports/writer.py` — modified, exists
- `tests/test_score_weights_invariant.py` — modified, exists
- `quirk/engine/migration_planner.py` — removed (confirmed via `find`)
- `52c91e9` — commit present in `git log`
