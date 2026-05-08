---
phase: 55-qramm-compliance-mapping-view
plan: "01"
subsystem: qramm
tags: [qramm, compliance, api, fastapi, pydantic, tdd]
dependency_graph:
  requires: []
  provides:
    - GET /api/qramm/sessions/{id}/compliance-map endpoint
    - quirk.qramm.compliance_map module (QRAMM_COMPLIANCE_WEIGHTS, SCANNER_COVERAGE, FRAMEWORK_KEYS)
  affects:
    - quirk/dashboard/api/routes/qramm.py
tech_stack:
  added: []
  patterns:
    - Pure-data module (no engine/scanner imports, per Phase 51 D-09)
    - Inline Pydantic model (per Phase 51 D-11)
    - Direct function call tests with monkeypatched _get_session_or_404
key_files:
  created:
    - quirk/qramm/compliance_map.py
    - tests/test_qramm_compliance_map.py
  modified:
    - quirk/dashboard/api/routes/qramm.py
decisions:
  - "Import-scan test checks only 'import'/'from' lines, not docstrings, to avoid false positives from documentation prose"
  - "dim_score read from score_data['dimensions'][dim]['score'] (not 'weighted') per RESEARCH Pitfall 2"
  - "Docstring shortened to avoid literal 'risk_engine' string which confused the grep acceptance check"
metrics:
  duration_minutes: 3
  completed_date: "2026-05-08"
  tasks_completed: 3
  files_created: 2
  files_modified: 1
---

# Phase 55 Plan 01: Compliance Map Server Data Layer Summary

**One-liner:** QRAMM compliance mapping endpoint serving 96 rows (12 practice areas x 8 frameworks) with scanner-coverage-capped relevance scores via a pure-data `compliance_map.py` module.

## What Was Built

### Task 1: quirk/qramm/compliance_map.py

New pure-data module with six named constants:

- `FRAMEWORK_KEYS` — 8-tuple of framework identifiers (NIST_PQC, NSM10, CNSA2, ISO27001, ETSI_QS, PCI_DSS, CC, BSI_TR)
- `FRAMEWORK_DISPLAY_NAMES` — human-readable labels for each framework key
- `SCANNER_COVERAGE` — CVI=1.0, SGRM/DPE/ITR=0.0 (v4.7 ceiling; expanded in QRAMM-F01)
- `PRACTICE_AREA_TO_DIMENSION` — maps 12 practice areas to their dimensions
- `PRACTICE_AREA_NAMES` — human-readable labels for each practice area
- `QRAMM_COMPLIANCE_WEIGHTS` — 12x8 float dict; all values in [0.0, 1.0]

Zero engine or scanner imports per Phase 51 D-09.

### Task 2: GET /qramm/sessions/{session_id}/compliance-map

New endpoint added to `quirk/dashboard/api/routes/qramm.py`:

- Returns 96 `ComplianceMapRow` objects (12 practice areas x 8 frameworks), sorted by practice area
- Unscored sessions: every `relevance_score` is `null` (HTTP 200, never 404/409 per D-03)
- Scored sessions: CVI rows = `static_weight * (dim_score / 4.0)` capped at `SCANNER_COVERAGE['CVI'] * static_weight`; SGRM/DPE/ITR rows = 0.0 (ceiling=0.0)
- Malformed `score_json` falls back to null relevance_score (T-55-02 mitigation)
- Session-not-found reuses `_get_session_or_404` for 404 (T-55-01 mitigation)
- `ComplianceMapRow` Pydantic model inline per Phase 51 D-11

### Task 3: tests/test_qramm_compliance_map.py

14 tests covering both the data module and the endpoint:

Structural (7): weights keys match questions, all weights in [0.0,1.0], scanner_coverage shape, framework display names match, practice-dimension map, practice area names complete, no engine/scanner imports.

Behavioral (7): 96 rows unscored, null relevance unscored, CVI nonzero when scored (max 4.0 dim_score), SGRM/DPE/ITR zero when scored, row shape (7 keys), scanner_informed flag matches SCANNER_COVERAGE, 404 on missing session.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test import-scan matched docstring prose, not actual imports**
- **Found during:** Task 3 GREEN phase (test `test_no_engine_imports_in_compliance_map`)
- **Issue:** The plan's test body stripped `#` comment lines but not docstring lines. The compliance_map.py docstring mentioned "risk_engine" as a prohibition note. The grep matched the docstring text and the test failed even though no import existed.
- **Fix:** Rewrote test to filter only lines starting with `import ` or `from ` (actual Python import statements) before scanning. Also shortened the compliance_map.py docstring to remove the literal "risk_engine" string.
- **Files modified:** `tests/test_qramm_compliance_map.py`, `quirk/qramm/compliance_map.py`
- **Commit:** 25bc82b

## TDD Gate Compliance

| Gate | Commit | Status |
|------|--------|--------|
| RED (test) | 650d8ed | Passed — tests collected but failed at import |
| GREEN (feat) | 25bc82b | Passed — all 14 tests pass |
| REFACTOR | N/A | No refactor needed |

## Threat Surface Scan

No new network endpoints beyond the planned compliance-map route. All threat mitigations from the plan's STRIDE register were applied:

| Threat | Mitigation | Location |
|--------|-----------|----------|
| T-55-01 session enumeration | Reuses `_get_session_or_404` | `get_compliance_map` |
| T-55-02 malformed score_json | `try/except (TypeError, ValueError)` | `get_compliance_map` |
| T-55-04 wrong-type dim score | `try/except (KeyError, TypeError, ValueError)` | `get_compliance_map` |

## Self-Check

| Item | Status |
|------|--------|
| `quirk/qramm/compliance_map.py` exists | FOUND |
| `tests/test_qramm_compliance_map.py` exists | FOUND |
| `quirk/dashboard/api/routes/qramm.py` modified | FOUND |
| RED commit 650d8ed | FOUND |
| GREEN commit 25bc82b | FOUND |
| 14 tests pass | PASS |

## Self-Check: PASSED
