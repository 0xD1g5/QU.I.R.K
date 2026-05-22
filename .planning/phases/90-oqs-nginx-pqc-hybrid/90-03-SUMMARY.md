---
phase: 90-oqs-nginx-pqc-hybrid
plan: "03"
subsystem: intelligence/scoring
tags: [pqc, scoring, agility, tdd, invariant]
dependency_graph:
  requires: [90-02]
  provides: [agility_pqc_hybrid_bonus, test_pqc_agility_bonus]
  affects: [quirk/intelligence/scoring.py, tests/test_score_weights_invariant.py]
tech_stack:
  added: []
  patterns: [presence-bonus, score-cap-clamp, tdd-red-green]
key_files:
  created:
    - tests/test_pqc_agility_bonus.py
  modified:
    - quirk/intelligence/scoring.py
    - tests/test_score_weights_invariant.py
decisions:
  - "D-03: agility_pqc_hybrid_bonus=8.0 (exceeds 4.0 ECDSA / 6.0 mTLS — PQC is the top signal)"
  - "Presence bonus: full +8.0 when pqc_hybrid_endpoint_count > 0 (simple, deterministic)"
  - "Clamp: existing _apply_weighted_impacts(score_cap=25.0) relied upon; no second clamp added"
  - "Invariant updated atomically: sum 275.0->283.0, count 36->37 in same commit"
metrics:
  duration_seconds: 420
  completed_date: "2026-05-22"
  tasks_completed: 1
  files_changed: 3
---

# Phase 90 Plan 03: Agility PQC-Hybrid Bonus Scoring Summary

**One-liner:** agility_pqc_hybrid_bonus=8.0 added to SCORE_WEIGHTS (PQC-03) makes X25519MLKEM768 hybrid TLS the clear top agility signal, clamped at /25 via existing score_cap, with the invariant test updated atomically (37 weights, sum 283.0).

## What Was Built

### Task 1: Add agility PQC-hybrid bonus + update invariant test atomically (TDD)

**RED commit:** `00e24f5` — 10 failing tests in `tests/test_pqc_agility_bonus.py` covering:
- Uplift: PQC-hybrid agility strictly > classical agility
- Clamp: agility never exceeds 25 (plain, ECDSA+PQC, strict profile)
- Orthogonality: five non-agility subscores identical between count=0 and count=1
- Presence: zero/missing/negative/garbage values → no bonus, no crash

**GREEN commit:** `41e172d`

- `quirk/intelligence/scoring.py`:
  - Added `"agility_pqc_hybrid_bonus": 8.0` to `SCORE_WEIGHTS` (37th key, per D-03)
  - Reads `pqc_hybrid_count = max(0, _as_int(evidence.get("pqc_hybrid_endpoint_count", 0)))` before `agility_impacts`
  - Appends `("PQC-hybrid key exchange (X25519MLKEM768)", w["agility_pqc_hybrid_bonus"])` to `agility_impacts` when `pqc_hybrid_count > 0`
  - Does NOT add a second clamp; relies on existing `_apply_weighted_impacts(score_cap=25.0)`
  - Does NOT touch any other impact block (orthogonality preserved)

- `tests/test_score_weights_invariant.py`:
  - `test_score_weights_sum_invariant`: assertion updated 275.0 → 283.0
  - `test_score_weights_count_invariant`: assertion updated 36 → 37
  - Both docstrings updated to record Phase 90 PQC-03 delta (+1 entry / +8.0)

- `tests/test_pqc_agility_bonus.py` (new, 140 lines): 12 tests across 4 classes, all passing

## Verification Results

- `QUIRK_DB_PATH=:memory: python -m pytest tests/test_score_weights_invariant.py tests/test_pqc_agility_bonus.py -v` — **12 passed**
- `python -m compileall quirk` — **clean**

Agility subscore with 2/4 HIGH findings:
- Classical (pqc_hybrid_endpoint_count=0): 18
- PQC-hybrid (pqc_hybrid_endpoint_count=1): 25 (clamped, bonus pushes it to cap)
- Delta: +7 visible uplift

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] RED test base evidence adjusted for visible uplift headroom**

- **Found during:** RED phase test run
- **Issue:** The initial `_base_evidence` had no penalties — agility started at 25 (maximum), so any PQC bonus was invisible (still 25 after clamping). The uplift test was "failing for the wrong reason" (both sides were 25, but the bonus had no room to show).
- **Fix:** Changed `_base_evidence` to include `finding_severity_counts: {HIGH: 2}` with `endpoints: 4, findings: 4` — a 50% HIGH finding ratio applies a -7 penalty giving 18 baseline agility, leaving room for the +8 bonus to push to 25 (demonstrating real uplift before clamping).
- **Files modified:** `tests/test_pqc_agility_bonus.py`
- **Impact:** Tests now fail RED for the correct reason (bonus not wired yet), pass GREEN correctly.

## Known Stubs

None — the scoring weight is wired to the evidence key from Plan 02. No placeholders.

## Threat Surface Scan

No new network endpoints, auth paths, file access, or schema changes. Pure scoring-math addition.

- T-90-06 mitigated: `max(0, _as_int(evidence.get("pqc_hybrid_endpoint_count", 0)))` — non-int/negative/missing coerce to 0.
- T-90-07 mitigated: single agility_impacts entry under existing score_cap=25; invariant test forward-locks the weight set at 37/283.0.

## TDD Gate Compliance

- RED gate: `test(90-03)` commit `00e24f5` — PRESENT
- GREEN gate: `feat(90-03)` commit `41e172d` — PRESENT

## Self-Check: PASSED

- `quirk/intelligence/scoring.py` contains `agility_pqc_hybrid_bonus` — FOUND
- `tests/test_pqc_agility_bonus.py` — FOUND
- `tests/test_score_weights_invariant.py` asserts 37 and 283.0 — FOUND
- `00e24f5` (RED commit) — FOUND in git log
- `41e172d` (GREEN commit) — FOUND in git log
