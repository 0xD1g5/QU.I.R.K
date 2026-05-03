---
phase: 38-identity-api-regression-fix
plan: "03"
subsystem: test-hygiene
tags: [tdd, regression-fix, hygiene, nyquist]
dependency_graph:
  requires: [38-01]
  provides: [full-suite-green]
  affects: [tests/test_hygiene.py]
tech_stack:
  added: []
  patterns: [skip-on-missing]
key_files:
  created: []
  modified:
    - tests/test_hygiene.py
decisions:
  - "D-02: Skip-on-missing chosen over backfilling 14 historical stub VALIDATION.md files (minimal diff, audit trail preserved)"
metrics:
  duration: "< 5 minutes"
  completed: "2026-04-29"
---

# Phase 38 Plan 03: HYGN-04 Skip-on-Missing Fix Summary

**One-liner:** Scoped `test_all_completed_phase_validations_nyquist_compliant` to skip phases with no on-disk VALIDATION.md, turning a hard-fail into a skip-on-missing pattern per D-02.

## What Was Built

### Task 1: Tighten HYGN-04 to skip-on-missing

Two targeted edits to `tests/test_hygiene.py` (lines ~197-243), no other file touched.

**Edit 1 — comment block replacement (lines 197-204):**

Before:
```python
    # ------------------------------------------------------------------
    # HYGN-04: All completed phase VALIDATION.md files must be nyquist_compliant: true
    # Expected: RED (11 files have false, 2 are missing)
    # ------------------------------------------------------------------
```

After:
```python
    # ------------------------------------------------------------------
    # HYGN-04: Phases with a VALIDATION.md on disk MUST declare
    # nyquist_compliant: true. Phases whose VALIDATION.md is absent
    # (e.g., the v4.4 cleanup in commit a991a69 removed phases 01-14)
    # are skipped — Phase 38 D-02 picked skip-on-missing as the minimal
    # resolution rather than backfilling 14 historical stub files.
    # Expected: GREEN
    # ------------------------------------------------------------------
```

**Edit 2 — missing-file branch replacement (lines 238-243):**

Before:
```python
            if not validation_path.exists():
                failures.append((phase_slug, "file missing"))
                continue
```

After:
```python
            if not validation_path.exists():
                # Phase 38 (D-02): skip-on-missing — the v4.4 cleanup commit
                # a991a69 deleted the historical VALIDATION.md files for
                # phases 01-14. The hygiene rule still has teeth for any
                # phase that DOES have a VALIDATION.md on disk.
                continue
```

**Unchanged:** `COMPLETED_PHASES` list, YAML regex, `nyquist_compliant` regex, final `self.assertEqual` assertion.

## Full-Suite Pytest Result

```
665 passed, 7 skipped, 9 warnings in 7.93s
```

Zero failures. Phase 38 success criterion 4 ("Full test suite passes with no regressions, 0 failures") satisfied.

## Grep Gate Results

| Gate | Expected | Actual |
|------|----------|--------|
| `grep -c '"file missing"' tests/test_hygiene.py` | 0 | 0 |
| `grep -c "Phase 38 (D-02)" tests/test_hygiene.py` | >= 1 | 1 |
| `grep -c "COMPLETED_PHASES = \[" tests/test_hygiene.py` | 1 | 1 |

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- `tests/test_hygiene.py` modified and committed at `ab5bb15`
- Full pytest suite: 665 passed, 0 failed
- No other test modified
