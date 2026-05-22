---
phase: 86-scoring-correctness-hotfix
plan: "01"
subsystem: intelligence/scoring
tags: [scoring, normalization, bug-fix, tdd, backend]
dependency_graph:
  requires: []
  provides: [normalized-readiness-aggregator, scoring-docstring-rewrite, boundary-tests]
  affects: [quirk/intelligence/scoring.py, tests/test_scoring_normalization.py]
tech_stack:
  added: []
  patterns: [int(round(sum/1.5)) normalization]
key_files:
  created:
    - tests/test_scoring_normalization.py
  modified:
    - quirk/intelligence/scoring.py
decisions:
  - "D-01: Replace _clamp(sum,0,100) with int(round(sum/1.5)) — 0-150 subscore range maps correctly to 0-100"
  - "D-11: Docstring rewritten to name 0-25 subscore scale and normalize formula; Phase 60 SCORE-04 clamp-is-intentional language removed"
  - "D-08: SCORE_WEIGHTS sum=275.0 / count=36 invariant confirmed independent of aggregation formula — no edits needed"
metrics:
  duration: "< 5 minutes"
  completed: "2026-05-22"
  tasks_completed: 3
  files_changed: 2
  tests_added: 3
---

# Phase 86 Plan 01: Scoring Normalization Backend Fix Summary

**One-liner:** Replace broken `_clamp(sum,0,100)` aggregator with `int(round(sum/1.5))` normalization, fixing the `100/EXCELLENT` display bug when canonical subscores sum to 120.

## What Was Built

### Task 1 — RED: Boundary + Canonical Normalization Tests

Created `tests/test_scoring_normalization.py` with three tests per D-09:

| Test | Premise | Expected (fixed) | Actual (broken) |
|------|---------|-----------------|-----------------|
| `test_overall_score_max_when_all_subscores_at_25` | Empty evidence → all subscores=25 | score=100, EXCELLENT | 100 (passes trivially pre-fix) |
| `test_overall_score_zero_when_all_subscores_zero` | Max-penalty evidence → all subscores=0 | score=0, POOR | 0 (passes trivially pre-fix) |
| `test_overall_score_canonical_example_120_to_80` | Monkeypatched subscores 25+25+23+3+25+19=120 | score=80, GOOD | **100** (FAILED — broken clamp) |

The canonical test confirmed the RED gate: `AssertionError: got 100. If this returns 100, the broken clamp is still in effect.`

Commit: `96f5ebd` — `test(86-01): add scoring normalization boundary tests (RED)`

### Task 2 — GREEN: Formula Change + Docstring Rewrite

**Lines 253-257 change** (`quirk/intelligence/scoring.py`):

Before:
```python
total_score = int(_clamp(
    hygiene_score + modern_tls_score + identity_trust_score +
    agility_score + dar_score + motion_score,
    0, 100,
))
```

After:
```python
total_score = int(round(
    (hygiene_score + modern_tls_score + identity_trust_score +
     agility_score + dar_score + motion_score) / 1.5
))
```

**Docstring rewrite** (lines 5-17): Removed `"clamp [0, 100]"`, `"Phase 60 SCORE-04 / CR-06 closure"`, and wrong `"261.0 BY DESIGN"` references. Replaced with:
- Six categories scored on 0-25 scale via `_apply_weighted_impacts(score_cap=25.0)`
- Overall = `int(round((sum of six 0-25 subscores) / 1.5))`
- Corrected sum reference to 275.0 (Phase 83 rebalance)
- Contributor guard line preserved

**Invariant audit:** `tests/test_score_weights_invariant.py` confirmed independent of aggregation formula — both assertions (sum=275.0, count=36) target `SCORE_WEIGHTS` dict only. No edits needed.

Commit: `7d0f71e` — `fix(86-01): normalize overall readiness (sum/1.5) + rewrite scoring docstring (GREEN)`

### Task 3 — Regression Sweep

Ran 79 scoring-related tests across:
- `test_scoring_normalization.py` (3 new — all PASS)
- `test_score_weights_invariant.py` (2 — PASS)
- `test_intelligence_scoring.py` (9 — PASS)
- `test_scoring_correctness.py` (7 — PASS)
- `test_score_clamp_property.py` (1 — PASS; `0 <= score <= 100` still holds since `int(round(150/1.5))=100`)
- `test_scoring_consolidation.py` (14 — PASS)
- `test_dar_k8s_scoring.py` (12 — PASS)
- `test_qramm_scoring.py` (15 — PASS)
- `test_executive_score_guard.py` (5 — PASS)

Zero failures. No incidental assertion drift discovered. No additional commit required.

## Sample Demonstration

```python
from quirk.intelligence.scoring import compute_readiness_score

# Canonical live-dashboard example (2026-05-22 bug report)
# Subscores injected via monkeypatch: 25+25+23+3+25+19 = 120
# Before fix:  int(min(120, 100)) = 100  → EXCELLENT  (WRONG)
# After fix:   int(round(120/1.5)) = 80  → GOOD       (CORRECT)
```

## Deviations from Plan

None — plan executed exactly as written.

## TDD Gate Compliance

- RED gate: commit `96f5ebd` (`test(86-01): ...`) — `test_overall_score_canonical_example_120_to_80` confirmed FAILED against unmodified scoring.py
- GREEN gate: commit `7d0f71e` (`fix(86-01): ...`) — all 3 normalization tests PASS
- REFACTOR gate: not needed (formula + docstring edit is minimal; no structural cleanup required)

## Threat Flags

None. This change reduces the attack surface of incorrect score representation; no new network endpoints, auth paths, or schema changes introduced.

## Self-Check: PASSED

- `tests/test_scoring_normalization.py` exists: FOUND
- `quirk/intelligence/scoring.py` contains `int(round(`: FOUND (line 255)
- `quirk/intelligence/scoring.py` does NOT contain `Phase 60 SCORE-04`: CONFIRMED
- Commit `96f5ebd` exists: FOUND
- Commit `7d0f71e` exists: FOUND
- 79 scoring-related tests pass: CONFIRMED
