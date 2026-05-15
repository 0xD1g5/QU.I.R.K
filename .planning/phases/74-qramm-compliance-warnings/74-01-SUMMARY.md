---
phase: 74-qramm-compliance-warnings
plan: 01
subsystem: qramm-scoring
tags: [qramm, scoring, evidence-bridge, audit-2026-05-08, warnings, qwarn-01]
requires: []
provides:
  - fail-loud-practice-score-validation
  - discovery-factor-endpoint-count-curve
  - indeterminate-maturity-label
  - reachable-optimizing-top-band
affects:
  - quirk/qramm/scoring.py
  - quirk/qramm/evidence_bridge.py
tech-stack:
  added: []
  patterns:
    - "ValueError fail-loud at function entry (mirrors Phase 70 _SAFE_COL_TYPE_RE)"
    - "log10 curve clamp via min(1.0, max(0.25, ...))"
    - "None-sentinel + sibling label (NOT a numeric tier)"
key-files:
  created:
    - tests/test_qramm_practice_scoring.py
  modified:
    - quirk/qramm/scoring.py
    - quirk/qramm/evidence_bridge.py
    - .planning/audit-2026-05-08/AUDIT-TASKS.md
decisions:
  - "D-02 endpoint source: local total_endpoints (line 59), NOT evidence_summary.endpoint_count — preserves D-09 isolation invariant"
  - "D-04 path (a): threshold-only fix (4.0 → 3.95); 4.0 already reachable at multiplier=1.0 per RESEARCH Pitfall 2 VERIFIED"
  - "score_1_2 = None propagates via QRAMMAnswer.suggested_answer nullable Integer column — no schema change needed"
  - "'Indeterminate' added as sibling label in _maturity_label, NOT a numeric tier (D-14 protects 5-band scale)"
metrics:
  duration: "~10m"
  completed: "2026-05-15"
  tasks: 3
  tests_added: 17
  audit_rows_closed: 4
---

# Phase 74 Plan 01: QRAMM Practice Scoring Correctness Summary

Closed QWARN-01 (audit rows WR-02, WR-04, WR-05, WR-06) with four surgical fixes in `scoring.py` and `evidence_bridge.py`: fail-loud out-of-range validation, Practice 1.1 endpoint-count discovery_factor, vuln_pct=None sentinel with 'Indeterminate' maturity label, and >= 3.95 top-band threshold.

## What Changed

### `quirk/qramm/scoring.py`

- **D-01 / WR-02** — `compute_practice_score(answers, practice_id="")` now validates each answer ∈ {0,1,2,3,4} BEFORE summation and raises `ValueError(f"Practice score answer {answer!r} for {practice_id} out of range [0, 4]")`. Empty-list path preserved (returns 0.0).
- **D-03 / WR-05** — `_maturity_label` signature widened to `score: float | None`. Leading arm `if score is None: return "Indeterminate"` added.
- **D-04 / WR-06** — Top-band threshold lowered from `>= 4.0` to `>= 3.95` (path (a) per RESEARCH C-2, one-line diff). Per user input override, 4.0 was already reachable at multiplier=1.0 (RESEARCH Pitfall 2 VERIFIED); the threshold change only absorbs FP-noise at sub-1.0 multipliers.

### `quirk/qramm/evidence_bridge.py`

- **D-02 / WR-04** — Added `import math` and module-private `_discovery_factor(endpoint_count: int) -> float` helper computing `min(1.0, max(0.25, math.log10(max(endpoint_count, 1)) / 3.0))`. Curve: 0/1 → 0.25 floor, 10 → ~0.333, 100 → ~0.667, 1000+ → 1.0 ceiling. Practice 1.1 block now multiplies `score_1_1` by the factor and rounds to 4 decimals. Endpoint source is the **local `total_endpoints` variable at line 59** (NOT `evidence_summary.endpoint_count` — that field does not exist in scope, and importing would violate D-09 isolation invariant per RESEARCH C-1).
- **D-03 / WR-05** — When `total_algos == 0` (or `total_endpoints == 0` — already-existing zero-endpoint short-circuit kept consistent), `vuln_pct = None` and `score_1_2 = None`. Sentinel propagates to the UPDATE on the nullable `QRAMMAnswer.suggested_answer` Integer column (verified `nullable=True` at `quirk/models.py:131`). Downstream `_maturity_label(None)` returns `"Indeterminate"`.

### Tests — `tests/test_qramm_practice_scoring.py` (new, 17 functions across 11 test names)

- D-01: rejects 5, rejects -1, accepts {0..4} returning 2.0, empty list → 0.0
- D-02: parametrized discovery_factor curve (0,1,10,100,1000,10000) + applied-to-score_1_1 sanity
- D-03: `_maturity_label(None) == "Indeterminate"`; non-None inputs return a real band
- D-04: parametrized `_maturity_label({3.95, 3.99, 4.0}) == "Optimizing"`; 3.94 stays in "Advanced"

### `.planning/audit-2026-05-08/AUDIT-TASKS.md`

Four `qramm-compliance` rows flipped from `— | [ ] open |` to `Phase 74 | [x] closed |`: WR-02, WR-04, WR-05, WR-06.

## Verification Evidence

| Check | Result |
|-------|--------|
| `python -m compileall quirk/qramm/scoring.py quirk/qramm/evidence_bridge.py` | exit 0 |
| `pytest tests/test_qramm_practice_scoring.py -x` | 17 passed |
| `pytest tests/test_qramm_staleness.py tests/test_compliance_freshness.py` | 7 passed (no regression) |
| `grep -cE "qramm-compliance/WR-(02\|04\|05\|06).*Phase 74.*\[x\] closed" AUDIT-TASKS.md` | 4 |
| `grep -cE "qramm-compliance/WR-(01\|03\|07\|08\|09\|10\|11\|12\|13).*\[ \] open" AUDIT-TASKS.md` | 9 (remain open for 74-02/74-03) |

## Audit Rows Closed

| Row | Disposition | Evidence |
|-----|-------------|----------|
| qramm-compliance/WR-02 | Phase 74 / [x] closed | `compute_practice_score` raises `ValueError` on out-of-range answers BEFORE summation (scoring.py L20-35) |
| qramm-compliance/WR-04 | Phase 74 / [x] closed | Practice 1.1 score scaled by `_discovery_factor(total_endpoints)` log10 curve (evidence_bridge.py L37-43, L100-102) |
| qramm-compliance/WR-05 | Phase 74 / [x] closed | `vuln_pct = None` when `total_algos == 0`; `_maturity_label(None) == "Indeterminate"` (evidence_bridge.py L104-121, scoring.py L66-73) |
| qramm-compliance/WR-06 | Phase 74 / [x] closed | Top-band threshold `>= 3.95` (scoring.py L76); parametrized test asserts 3.95/3.99/4.0 all land in "Optimizing" |

## Deviations from Plan

None of Rules 1-4 fired. Plan executed exactly as written.

## Decisions Made

- **D-02 endpoint source (locked at planning):** Used local `total_endpoints` per RESEARCH C-1 + user input override. `evidence_summary.endpoint_count` does not exist in this module's scope, and importing the evidence summary path would violate the D-09 isolation invariant.
- **D-04 path (a) — threshold-only fix:** Lowered `>= 4.0` to `>= 3.95` in `_maturity_label`. Did NOT touch the `min(4.0, …)` clamp in `compute_overall_score` (line 56). One-line surgical diff; preserves the 5-band scale per D-14.
- **None-propagation for score_1_2:** `QRAMMAnswer.suggested_answer` is a nullable Integer column (verified at `quirk/models.py:131`), so no schema migration was required to allow the None sentinel through the UPDATE.

## Deferred Issues

- **`tests/test_qramm_evidence_bridge.py::test_unconfirmed_excluded_from_score` fails (422 vs 200).** Verified via `git stash` that this failure pre-dates Plan 74-01 — not caused by my changes. It is a route-level behavior question (when there are zero confirmed answers, the `/score` endpoint returns 422 by design). The test itself asserts 200, suggesting either the test is outdated or the route contract changed in a prior phase. Out of scope for QWARN-01. Recommend filing a follow-up audit row or addressing in a future qramm phase.
- **Three test collection errors** in `tests/test_compliance_coverage_status.py`, `tests/test_migration_advisor_precision.py`, `tests/test_qramm_model_stale.py` — these are pre-existing RED-state stubs from `c336535` (Plan 74-03 RED commit). Out of scope for 74-01; 74-02/74-03 GREEN commits will resolve.

## Self-Check

- `tests/test_qramm_practice_scoring.py` exists: FOUND
- `quirk/qramm/scoring.py` modified (out-of-range, Indeterminate, 3.95): FOUND
- `quirk/qramm/evidence_bridge.py` modified (`_discovery_factor`, `vuln_pct = None`): FOUND
- 4 audit rows flipped: FOUND (`grep` count == 4)
- Commit 25e7a66 (RED): FOUND
- Commit 528b699 (GREEN): FOUND
- Commit 26da5a5 (audit flip): FOUND

## Self-Check: PASSED
