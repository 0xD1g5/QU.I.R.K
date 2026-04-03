---
phase: 08-legacy-debt-cleanup
plan: 04
subsystem: validate
tags: [validation, artifact-checks, tdd, test-coverage]
dependency_graph:
  requires: [08-01, 08-02, 08-03]
  provides: [validate.py correctness, integration test coverage for validate_run]
  affects: [quirk/validate.py, tests/test_validate.py]
tech_stack:
  added: []
  patterns: [TDD red-green, mtime-based file sorting]
key_files:
  created: [tests/test_validate.py]
  modified: [quirk/validate.py]
decisions:
  - "validate.py expected_files now mirrors actual writer.py output: findings, executive-summary, technical-findings, scorecard, roadmap, run-stats, cbom .cdx.json, cbom .cdx.xml"
  - "_validate_calibration() and _validate_delta() removed — dead code for artifacts that writer.py never produces"
  - "_latest_intelligence() and _previous_intelligence() sort by st_mtime not filename to handle same-second-timestamp edge cases"
metrics:
  duration_seconds: 85
  completed_date: "2026-04-03"
  tasks_completed: 2
  files_changed: 2
requirements: [D-01, D-02]
---

# Phase 08 Plan 04: Validate.py Artifact Checks and Integration Test Summary

**One-liner:** Fixed validate.py to check real writer.py artifacts (run-stats, cbom) and sort intelligence files by mtime; added 4-test integration suite.

## What Was Built

### Task 1: Fix validate.py (D-01)
- Replaced incorrect `expected_files` list: removed `assessment-{stamp}.json` and `calibration-{stamp}.json` (never produced by writer.py), added `run-stats-{stamp}.json`, `cbom-{stamp}.cdx.json`, `cbom-{stamp}.cdx.xml`
- Removed `_validate_calibration()` function and its call site — dead code for a non-existent artifact
- Removed `_validate_delta()` function and its call site — delta artifact not produced by current writer
- Fixed `_latest_intelligence()` to use `max(files, key=lambda p: p.stat().st_mtime)` instead of `sorted(..., reverse=True)` on filename
- Fixed `_previous_intelligence()` with same mtime-based approach

### Task 2: Integration test for validate_run (D-02)
Created `tests/test_validate.py` with 4 tests:
- `test_validate_run_passes_on_complete_output` — full artifact set produces ok=True
- `test_validate_run_fails_on_missing_findings` — missing findings-*.json detected correctly
- `test_validate_run_fails_on_missing_intelligence` — empty dir returns ok=False with intelligence error
- `test_latest_intelligence_uses_mtime` — newer mtime wins regardless of filename sort order

## Verification Results

```
4 passed in 0.07s
python -m quirk.validate --help → OK
python -m compileall quirk/validate.py → OK
```

## Commits

| Hash | Task | Description |
|------|------|-------------|
| 3ae6453 | Task 1 (RED) | test(08-04): add failing tests for validate_run() and _latest_intelligence() |
| 2b47149 | Task 1 (GREEN) | feat(08-04): fix validate.py artifact checks and mtime sort (D-01) |

## Deviations from Plan

None — plan executed exactly as written. The TDD test file for Task 2 was created in the RED step of Task 1's TDD flow, which is the correct TDD sequence.

## Known Stubs

None — all checks are wired to real file existence tests against the actual artifact list.

## Self-Check: PASSED

- `quirk/validate.py` exists and compiles: FOUND
- `tests/test_validate.py` exists with all 4 test functions: FOUND
- Commit 3ae6453 exists: confirmed
- Commit 2b47149 exists: confirmed
- All 4 pytest tests pass: confirmed
