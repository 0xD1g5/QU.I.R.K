---
phase: 102-dashboard-auth-ux-score-tax
plan: "03"
subsystem: reports
tags: [trans-04, score-parity, exec-content, tdd]
dependency_graph:
  requires: []
  provides: [TRANS-04]
  affects: [quirk/reports/executive.py, tests/test_score_parity.py]
tech_stack:
  added: []
  patterns:
    - "exec_content-gated score section in build_exec_markdown (mirrors narrative branch pattern)"
key_files:
  created:
    - tests/test_score_parity.py
  modified:
    - quirk/reports/executive.py
decisions:
  - "Restructured score section as exec_content is not None / else rather than patching three individual lines — produces a cleaner, self-contained dual-path structure matching the existing narrative section pattern"
  - "Score Drivers still reads score_raw.get('drivers') in both branches — drivers are not on ExecContent and this is out of scope for TRANS-04 (pure sourcing refactor for total/band/subscores/rollup)"
  - "Backward-compat else-branch retained verbatim for external callers; writer.py always passes exec_content so this path is never exercised in production"
metrics:
  duration: "8 minutes"
  completed: "2026-05-25"
  tasks: 2
  files: 2
---

# Phase 102 Plan 03: TRANS-04 CLI Score Source Refactor Summary

**One-liner:** CLI executive markdown score total/band/subscores/rollup now sourced from shared exec_content model (not score_raw re-derivation), closing v5.2 score-tax tech debt with cross-surface parity test.

## What Was Built

### Task 1: TRANS-04 Score Parity Test (TDD RED)

Created `tests/test_score_parity.py` with `test_score_parity_across_surfaces`. Test builds one `ExecContent` instance and asserts that `build_exec_markdown` CLI output contains `exec_content.score_total`, `exec_content.score_band`, and every subscore value from `exec_content.subscores`. The test failed RED because the CLI was rendering `score_raw['rating']` ("EXCELLENT" from re-computed score of 91) instead of `exec_content.score_band` ("FAIR" — the canonical shared-model value). This confirmed the sourcing divergence.

Commit: `c8a9857` — `test(102-03): add failing TRANS-04 score parity test (RED)`

### Task 2: Executive Score Section Sourced from exec_content (TDD GREEN)

Modified `quirk/reports/executive.py::build_exec_markdown` score section (~lines 213-256). Restructured from a mixed-source flat block into a dual-path `if exec_content is not None / else` structure:

- **Active path (exec_content is not None):** `score_raw['score']` → `exec_content.score_total` (Score line + Rollup line); `score_raw['rating']` → `exec_content.score_band`; `score_raw.get("subscores") or {}` → `exec_content.subscores`; `exec_content.raw_sum` kept (was already partially sourced from exec_content)
- **Backward-compat else-path:** original score_raw reads retained for external callers (writer.py always passes exec_content, so this path is never hit in production)

Verification: `python -m compileall` clean; `tests/test_score_parity.py + tests/test_cross_surface_parity.py` all 4 tests GREEN; `grep -c 'exec_content\.score_total' quirk/reports/executive.py` = 2 (Score line + Rollup line).

Commit: `9a29e04` — `feat(102-03): source CLI executive score section from exec_content (TRANS-04)`

## Deviations from Plan

None - plan executed exactly as written. The restructuring into a dual-path if/else (rather than patching three individual lines) produced a cleaner result that mirrors the existing narrative branch structure; this is a presentation choice within the plan's direction, not a deviation.

## Threat Flags

None — pure internal sourcing refactor; no new network endpoints, auth paths, file access patterns, or schema changes introduced.

## Self-Check: PASSED

- [x] `tests/test_score_parity.py` exists and contains `test_score_parity_across_surfaces`
- [x] `quirk/reports/executive.py` contains `exec_content.score_total` (count = 2)
- [x] Commits `c8a9857` and `9a29e04` exist in git log
- [x] `python -m compileall quirk/reports/executive.py` clean
- [x] `python -m pytest tests/test_score_parity.py tests/test_cross_surface_parity.py -q` — 4 passed
