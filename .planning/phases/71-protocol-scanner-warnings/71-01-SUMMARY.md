---
phase: 71-protocol-scanner-warnings
plan: 01
subsystem: discovery/coverage
tags: [audit, WR-01, WR-02, PROTO-01]
requires: []
provides: [PROTO-01]
affects: [quirk/discovery/coverage.py]
tech-stack:
  added: []
  patterns: [clamp-return-value, uppercase-severity-normalization]
key-files:
  created:
    - tests/test_coverage_bounds.py
  modified:
    - quirk/discovery/coverage.py
    - .planning/audit-2026-05-08/AUDIT-TASKS.md
decisions: [D-06, D-07, D-15]
metrics:
  duration: ~5min
  completed: 2026-05-15
---

# Phase 71 Plan 01: Coverage Clamp + Severity Normalization Summary

**One-liner:** Clamped `calculate_coverage` return to `[0.0, 1.0]` and normalized
`quantum_readiness_score` severity comparison to `.upper()`, closing audit WR-01/WR-02.

## What Changed

### `quirk/discovery/coverage.py`

- `calculate_coverage`: Final return wrapped as `max(0.0, min(1.0, round(coverage, 2)))`
  with inline comment citing WR-01 (per D-06). Numerator / denominator math left
  untouched per D-15 — the formula correctness debate belongs to a future Phase 73
  INTEL-03 plan. Zero-denominator path now returns `0.0` (was `0`, an int).
- `quantum_readiness_score`: Severity comparison now reads
  `severity = str(f["severity"]).upper()` once per finding, then matches against
  uppercase literals `"CRITICAL"`, `"HIGH"`, `"MEDIUM"` per D-07. `.upper()` was
  chosen over `.casefold()` to align with the project-wide uppercase severity
  precedent (audit ledger, Phase 60, Phase 64.1).

### `tests/test_coverage_bounds.py` (new)

14 tests across two concerns:

- **Clamp (4 tests + zero-denominator):** above-range → 1.0, negative target → 0.0,
  zero target → 0.0, normal mid-range stays in `[0.0, 1.0]`.
- **Severity normalization (9 parametrized + 1 monotonicity):** `critical/Critical/CRITICAL`,
  `high/High/HIGH`, `medium/Medium/MEDIUM` each compared against their canonical
  uppercase form; plus a relative-monotonicity test proving lowercase `"high"`
  still applies the penalty (not silently ignored).

### `.planning/audit-2026-05-08/AUDIT-TASKS.md`

- Row `scanners-protocol/WR-01` → `Phase 71 | [x] closed` with evidence pointer.
- Row `scanners-protocol/WR-02` → `Phase 71 | [x] closed` with evidence pointer.
- No other rows modified — surgical 2-line diff.

## Commits

| Commit  | Type     | Subject                                                                       |
| ------- | -------- | ----------------------------------------------------------------------------- |
| 9175042 | test     | add failing tests for coverage clamp and severity normalization (RED)         |
| 0db2f8e | feat     | clamp calculate_coverage and normalize severity to upper-case (GREEN)         |
| d35a36c | docs     | flip audit rows WR-01 and WR-02 to closed under Phase 71                      |

## Verification Evidence

- `python -m compileall quirk/discovery/coverage.py` — clean
- `pytest tests/test_coverage_bounds.py -x` — 14/14 passed
- `grep -c "scanners-protocol/WR-01.*Phase 71.*\[x\] closed"` — 1
- `grep -c "scanners-protocol/WR-02.*Phase 71.*\[x\] closed"` — 1
- One-liner acceptance checks (clamp at 1.0, clamp at 0.0, mid-range bounded) — all PASS

## Decisions Honored

- **D-06 (locked):** Wrap return only; do not change formula math. ✓
- **D-07 (locked):** Use `.upper()`, not `.casefold()`. ✓
- **D-15 (locked):** Coverage numerator/denominator out of scope; deferred to Phase 73 INTEL-03. ✓

## Deviations from Plan

None — plan executed exactly as written.

## Deferred / Out-of-Scope Observations

Unrelated pre-existing test failures observed during regression sweep (NOT caused by this plan):

- `tests/test_cbom_classifier_coverage.py::test_no_unknown_classifications_across_lab_profiles` —
  `ssh-dss` classified as UNKNOWN; needs row in `_ALGORITHM_TABLE`.
- `tests/test_motion_scoring.py::test_motion_subscore_lowers_with_findings`,
  `tests/test_scoring_correctness.py::ScoringCorrectnessTests::test_strict_scores_lower_than_lenient_on_penalized_evidence`,
  `tests/test_identity_surface.py::IdentityScoringTests::test_all_three_weak_lowers_score`,
  `tests/test_identity_surface.py::IdentityScoringTests::test_weak_kerberos_lowers_score`,
  `tests/test_qramm_evidence_bridge.py::test_unconfirmed_excluded_from_score` —
  these touch `quirk.intelligence.scoring.compute_readiness_score`, a different module
  from `quirk.discovery.coverage.quantum_readiness_score` modified here. Pre-existing
  per pre-edit `git stash` check.

These belong to follow-up scoring/classifier phases (likely Phase 73 INTEL-03 and the
ongoing CBOM classifier work) — not WR-01/WR-02 scope.

## Self-Check: PASSED

- FOUND: tests/test_coverage_bounds.py
- FOUND: quirk/discovery/coverage.py (modified)
- FOUND commit 9175042 (test RED)
- FOUND commit 0db2f8e (feat GREEN)
- FOUND commit d35a36c (docs audit flip)
