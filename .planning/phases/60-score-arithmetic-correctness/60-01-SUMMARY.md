---
phase: 60
plan: "01"
subsystem: intelligence/scoring
tags: [scoring, confidence, qramm, arithmetic, correctness, audit-hardening]
dependency_graph:
  requires: []
  provides: [score-clamp-SCORE-01, zero-tls-fallback-SCORE-03, multiplier-400-guard-SCORE-02]
  affects: [quirk/intelligence/scoring.py, quirk/intelligence/confidence.py, quirk/dashboard/api/routes/qramm.py]
tech_stack:
  added: []
  patterns: [explicit-HTTP-400-guard, _clamp()-reuse, zero-fallback-arithmetic]
key_files:
  created: []
  modified:
    - quirk/intelligence/scoring.py
    - quirk/intelligence/confidence.py
    - quirk/dashboard/api/routes/qramm.py
    - tests/test_intelligence_scoring.py
    - tests/test_intelligence_confidence.py
decisions:
  - "Clamp applied at compute_readiness_score() total only; no second clamp in writer/scan/qramm (D-01/D-02)"
  - "Zero-TLS fallback changed from 1.0 to 0.0 so no phantom 20-point bonus without data (D-07)"
  - "Pydantic ge/le constraints removed; HTTP 400 guard inserted before DB query (D-04/D-05/D-06)"
  - "Test fixtures updated to use degraded evidence (pre-clamp sum < 100) so clamped comparisons remain meaningful"
metrics:
  duration_minutes: 25
  completed_date: "2026-05-10"
  tasks_completed: 3
  files_modified: 5
---

# Phase 60 Plan 01: Score Arithmetic Correctness Summary

**One-liner:** Three audit-blocking arithmetic fixes — score clamp to [0,100], zero-TLS confidence fallback corrected from 1.0 to 0.0, and QRAMM multiplier validation replaced with explicit HTTP 400 guard.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 01-01 | Clamp total_score to [0,100] in compute_readiness_score() | 28ffdd2 | quirk/intelligence/scoring.py |
| 01-02 | Fix zero-TLS confidence fallback (1.0 → 0.0) | 3f8bc10 | quirk/intelligence/confidence.py |
| 01-03 | Replace Pydantic multiplier constraint with explicit 400 guard | 9284bf3 | quirk/dashboard/api/routes/qramm.py, tests/ |

## What Was Built

### Task 01-01: Score Clamp (SCORE-01 / BL-01)

At line 219 of `quirk/intelligence/scoring.py`, replaced the unclamped `int()` cast with:
```python
total_score = int(_clamp(
    hygiene_score + modern_tls_score + identity_trust_score +
    agility_score + dar_score + motion_score,
    0, 100,
))
```
Reuses the existing `_clamp()` helper at line 65. The six subscores each max at 25 (total max 150), so without the clamp a perfect-evidence scan would return 150. The clamp is applied only here per plan decisions D-01/D-02.

### Task 01-02: Zero-TLS Confidence Fallback (SCORE-03 / BL-02)

At line 83 of `quirk/intelligence/confidence.py`, changed:
```python
# Before:
tls_enum_coverage_ratio = 1.0 if tls_count == 0 else 0.0
# After:
tls_enum_coverage_ratio = 0.0  # no TLS data → no coverage bonus
```
The previous logic awarded a full 1.0 ratio (20-point phantom bonus) when no TLS data existed. The correct behavior is 0.0 — no coverage bonus without actual TLS endpoints.

### Task 01-03: Explicit 400 Guard (SCORE-02 / CR-04)

Two changes in `quirk/dashboard/api/routes/qramm.py`:

**Change A:** Removed `ge=0.8, le=1.5` Pydantic field constraints from `ScoreRequest.profile_multiplier`. These caused a 422 response before the route handler could produce the business-specific 400.

**Change B:** Inserted explicit guard in `score_session()` immediately after multiplier extraction:
```python
if payload is not None and payload.profile_multiplier is not None:
    if not (0.8 <= multiplier <= 1.5):
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "QRAMM_MULTIPLIER_OUT_OF_RANGE",
                "message": "profile_multiplier must be in [0.8, 1.5]",
                "valid_range": [0.8, 1.5],
            },
        )
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test fixtures produced pre-clamp sums > 100, masking assertions post-clamp**

- **Found during:** Task 01-03 test suite run
- **Issue:** After applying `_clamp(total, 0, 100)`, existing test fixtures in `tests/test_intelligence_scoring.py` and `tests/test_intelligence_confidence.py` both produced readiness scores of 100 for cases that should differ (e.g., safe vs. risky, default vs. override). The pre-existing `_base_evidence()` produced a pre-clamp total of ~141, so all variants clamped to 100.
- **Root cause:** The subscore design allows 6 subscores × 25 max = 150 total; most "typical" evidence sets (even penalized ones) still sum over 100. Tests relied on unclamped arithmetic being able to express differences above 100.
- **Fix:** Updated `_base_evidence()` in `test_intelligence_scoring.py` to use heavily penalized evidence (pre-clamp sum = 94) so profile/override/risky comparisons remain meaningfully differentiated post-clamp. Updated `test_confidence_and_readiness_are_independent_outputs` in `test_intelligence_confidence.py` with its own evidence dict producing pre-clamp sums of 94 and 87.
- **Files modified:** `tests/test_intelligence_scoring.py`, `tests/test_intelligence_confidence.py`
- **Commit:** 9284bf3

## Verification Results

```
python -m compileall quirk/intelligence/scoring.py quirk/intelligence/confidence.py quirk/dashboard/api/routes/qramm.py
# Exit 0

SCORE-01 clamp OK: 100
SCORE-03 zero-TLS OK: 0.0

pytest tests/test_intelligence_scoring.py tests/test_intelligence_confidence.py -x -q
# 11 passed in 0.02s
```

## Success Criteria — All Met

1. `compute_readiness_score()` never returns score outside `[0, 100]` — PASS (clamp applied)
2. `POST /api/qramm/sessions/{id}/score` with `profile_multiplier=2.0` returns HTTP 400 with `error_code: QRAMM_MULTIPLIER_OUT_OF_RANGE` — PASS (guard logic verified)
3. `compute_confidence()` with zero TLS and no explicit key yields `points == 0.0` — PASS
4. `python -m compileall` exits 0 on all three modified files — PASS
5. Pre-existing tests in scoring and confidence test suites continue to pass — PASS (11/11 after fixture updates)

## Known Stubs

None.

## Threat Flags

No new security surface introduced. All three changes close existing audit threats (T-60-01, T-60-02, T-60-03 from plan threat register).
