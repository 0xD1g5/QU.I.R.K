---
phase: 60-score-arithmetic-correctness
reviewed: 2026-05-10T00:00:00Z
depth: standard
files_reviewed: 8
files_reviewed_list:
  - quirk/intelligence/scoring.py
  - quirk/intelligence/confidence.py
  - quirk/dashboard/api/routes/qramm.py
  - tests/test_intelligence_scoring.py
  - tests/test_intelligence_confidence.py
  - tests/test_score_clamp_property.py
  - tests/test_qramm_multiplier.py
  - tests/test_qramm_scoring.py
findings:
  critical: 1
  warning: 3
  info: 2
  total: 6
status: issues_found
---

# Phase 60: Code Review Report

**Reviewed:** 2026-05-10T00:00:00Z
**Depth:** standard
**Files Reviewed:** 8
**Status:** issues_found

## Summary

Phase 60 applied three arithmetic correctness fixes: clamping `total_score` to [0, 100] in
`compute_readiness_score()`, zeroing the TLS confidence bonus when no TLS enumeration data is
present, and replacing a Pydantic field constraint with an explicit 400 HTTPException guard that
fires before DB access. New property tests (1,000 random iterations), unit tests, and a
maturity-band parametrized sweep were also added.

The clamp logic in `scoring.py` is correct. Boundary conditions at exactly 0 and 100 are
inclusive and cannot produce off-by-one errors. The 400 guard in `qramm.py` fires before the DB
lookup and correctly rejects NaN and Inf (both fail the `0.8 <= x <= 1.5` check in Python).

However, one correctness bug is present: `compute_overall_score()` in `quirk/qramm/scoring.py`
does not clamp its `overall` output to the CSNP 0–4 scale. With `profile_multiplier=1.5` and all
dimension scores at 4.0, the returned `overall` is 6.0. The 400 guard permits multiplier 1.5
and answer values of 4 are valid, making this reachable in production. This is not new to Phase
60 (the Pydantic constraint also allowed 1.5), but Phase 60 added test coverage specifically for
this area and missed it — and the bug is directly exposed by the guard's explicit allowance of
the full [0.8, 1.5] range.

Three test-quality issues weaken the regression protection Phase 60 intended to establish.

---

## Critical Issues

### CR-01: `compute_overall_score` returns `overall` > 4.0 with valid inputs

**File:** `quirk/qramm/scoring.py:56-57`

**Issue:** The `overall` score is computed as the mean of weighted dimension scores where each
dimension score is multiplied by the profile multiplier. When all four dimensions are 4.0 (the
maximum answer value) and `multiplier=1.5` (the maximum the 400 guard allows), `overall` equals
6.0 — outside the CSNP 0–4 scale. This value is persisted to `score_json` and returned to API
consumers without any clamping. The `_maturity_label` function handles scores above 4.0
gracefully (maps to "Optimizing"), but the numeric `overall` field itself is wrong. Any
downstream consumer parsing `overall` and expecting 0–4 will receive out-of-range data.

This is reachable via: all 120 answers set to 4, `POST /api/qramm/sessions/{id}/score` with
`{"profile_multiplier": 1.5}`.

```python
# current — no clamp on overall
weighted = {d: round(dimension_scores.get(d, 0.0) * multiplier, 4) for d in dims}
overall = round(sum(weighted.values()) / len(dims), 4)

# fix — clamp overall to CSNP spec range
weighted = {d: round(dimension_scores.get(d, 0.0) * multiplier, 4) for d in dims}
overall = round(min(4.0, sum(weighted.values()) / len(dims)), 4)
```

The `test_qramm_scoring.py` maturity-band sweep (lines 106–122) only covers scores up to 4.0
(step 0.5 from 0 to 4), so it cannot catch this regression.

---

## Warnings

### WR-01: Unit test upper-bound assertion does not enforce Phase 60's clamp contract

**File:** `tests/test_intelligence_scoring.py:37-40`

**Issue:** `test_compute_readiness_score_shape` asserts
`result["score"] <= MAX_SUBSCORE * NUM_SUBSCORES` (i.e., `<= 150`). Phase 60's primary
deliverable is clamping `total_score` to 100. The assertion allows any value up to 150, meaning a
regression that removes the `_clamp(total, 0, 100)` call would still pass this test. The property
test in `test_score_clamp_property.py` catches this regression, but only when the full test suite
is run. The unit test itself makes a false claim.

```python
# current — too weak; allows up to 150
self.assertLessEqual(result["score"], MAX_SUBSCORE * NUM_SUBSCORES)

# fix — enforce the actual SCORE-01 contract
self.assertLessEqual(result["score"], 100)
self.assertGreaterEqual(result["score"], 0)
```

### WR-02: Test comment claims subscores can exceed 25; they cannot

**File:** `tests/test_intelligence_scoring.py:137-138`

**Issue:** The function `test_subscores_unaffected_by_clamp` (line 134) contains the comment
"Subscores are allowed to exceed 25 in edge cases (per `_apply_weighted_impacts`)." This is
factually wrong. `_apply_weighted_impacts` calls `_clamp(total, 0.0, score_cap)` where
`score_cap=25.0`, so subscores are always in [0, 25]. The test itself only checks
`isinstance(val, int)` and never asserts the upper bound, meaning if a future refactor breaks the
per-subscore clamp, no assertion in this test catches it.

```python
# fix — replace incorrect comment and add the missing bound assertion
def test_subscores_unaffected_by_clamp():
    """SCORE-01: subscores are individually clamped to [0, 25]; total clamped to [0, 100]."""
    result = compute_readiness_score({})
    assert "subscores" in result
    for key, val in result["subscores"].items():
        assert isinstance(val, int), f"subscore {key} is not int: {val}"
        assert 0 <= val <= 25, f"subscore {key}={val} is outside [0, 25]"
    assert 0 <= result["score"] <= 100
```

### WR-03: `list_sessions` accepts unbounded `limit` parameter

**File:** `quirk/dashboard/api/routes/qramm.py:445`

**Issue:** `limit: int = 50` has no upper-bound validation. A caller can pass `?limit=10000000`,
causing SQLAlchemy to issue `.limit(10000000)` against the sessions table and return an
arbitrarily large result set in a single response. There is no authentication-level protection
that prevents this — auth is passthrough when `QUIRK_API_TOKEN` is unset (the default dev
configuration). FastAPI query parameters with plain `int` type accept any integer including
negative values; SQLite silently ignores a negative LIMIT and returns all rows.

```python
# current
def list_sessions(db: Session = Depends(get_db), limit: int = 50) -> List[SessionSummary]:

# fix — add Query constraint
from fastapi import Query
def list_sessions(
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=200),
) -> List[SessionSummary]:
```

---

## Info

### IN-01: Dead `"LOW"` key in `protocol_counts` of property test fixture

**File:** `tests/test_score_clamp_property.py:44`

**Issue:** `_random_evidence` populates `protocol_counts` with a `"LOW"` key
(`"LOW": rng.randint(0, findings)`). `scoring.py` never reads `protocol_counts["LOW"]`; it reads
`finding_severity_counts.get("LOW", 0)` for `legacy_tls_count`. The stray key is harmless but
suggests a copy-paste error from the `finding_severity_counts` dict (line 48) and could confuse
future maintainers who look for where `"LOW"` severity is fed into the scoring function.

```python
# fix — remove the dead key
protocol_counts = {
    "TLS": rng.randint(0, endpoints),
    "SSH": rng.randint(0, max(0, endpoints - 10)),
    "UNKNOWN": rng.randint(0, 50),
    # "LOW" removed — not a protocol, was never read by scoring.py
}
```

### IN-02: SCORE-03 test does not cover the case where `tls_count == 0` but the ratio key is present

**File:** `tests/test_intelligence_confidence.py:74-88`

**Issue:** `test_zero_tls_produces_no_enum_coverage_bonus` omits both `tls_enum_coverage_ratio`
and `tls_enum_coverage_pct` from the evidence dict. The Phase 60 fix zeroes the bonus when both
keys are absent (sentinel → 0.0 path, lines 77–83 of `confidence.py`). However, if a caller
provides `tls_enum_coverage_ratio: 0.8` in evidence while `protocol_counts["TLS"] == 0`, the fix
does not zero the bonus — the ratio key is present and is used as-is. The test name says "zero
TLS" but actually tests "absent keys," which is a narrower condition. This is a documentation
mismatch; whether the wider case is intentional behavior is not specified in the CONTEXT.

```python
# add a second regression guard to document the boundary explicitly
def test_explicit_zero_tls_ratio_when_no_tls_endpoints():
    """When TLS count is 0 but ratio key is present, the ratio is still honored (by design)."""
    evidence = {
        "totals": {"endpoints": 10},
        "protocol_counts": {"TLS": 0, "SSH": 3},
        "tls_enum_coverage_ratio": 0.8,  # key present but TLS count is 0
    }
    result = compute_confidence(evidence)
    factor = result["factor_breakdown"]["tls_enum_coverage_ratio"]
    # Document: 0.8 is used; zeroing does NOT happen when key is explicit
    assert factor["value"] == 0.8
```

---

_Reviewed: 2026-05-10T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
