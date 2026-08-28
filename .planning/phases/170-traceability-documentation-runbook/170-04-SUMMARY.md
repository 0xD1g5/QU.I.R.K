---
phase: 170-traceability-documentation-runbook
plan: 04
subsystem: testing
tags: [traceability, requirements, docstrings, pytest, vitest]

# Dependency graph
requires:
  - phase: 170-03
    provides: "DEBT-02 and QRAMM-08 real tests (the other half of TRACE-03)"
provides:
  - "Requirement-ID annotations linking GAP-01, GAP-02, QRAMM-09, AUTH-05, DEBT-04, QRAMM-11, TAIL-04, and GAUGE-01/02/03 to their existing, already-passing tests"
affects: [170-05, 170-07]

# Tech tracking
tech-stack:
  added: []
  patterns: ["Requirement-ID annotation convention: parenthetical ID reference inserted into existing docstring/comment, matching qramm.py's established pattern"]

key-files:
  created: []
  modified:
    - tests/test_identity_surface.py
    - tests/test_qramm_router.py
    - tests/test_credential_leakage.py
    - tests/test_adcs_ast_gate.py
    - tests/test_smime_ast_gate.py
    - tests/test_saml_scanner.py
    - tests/test_identity_findings_accuracy.py
    - tests/test_run_scan_codesign_wiring.py
    - src/dashboard/src/components/qramm/__tests__/scorecard-maturity.test.tsx
    - src/dashboard/src/components/gauges/__tests__/ScoreGauge.test.tsx

key-decisions:
  - "No new tests written — 170-03 already wrote the only two genuinely missing tests (DEBT-02, QRAMM-08); this plan is annotation-only"
  - "GAP-02 and QRAMM-09 confirmed to already have real passing coverage the original review missed; annotated in place rather than duplicating with new tests"

patterns-established:
  - "Requirement-ID annotation: append/prepend the ID in parentheses or as a labeled sentence inside the existing docstring/comment, closest to the specific test function/class, preserving all existing prose"

requirements-completed: [TRACE-03, TRACE-04]

# Metrics
duration: 15min
completed: 2026-08-28
---

# Phase 170 Plan 04: Requirement-ID annotations on 11 already-passing tests Summary

**Added discoverable requirement-ID annotations to 10 test files (8 Python, 2 TypeScript), closing TRACE-03 and TRACE-04 with zero new tests and zero behavior change — every annotated test was re-run and confirmed passing before the link was recorded.**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-08-28T14:40:00Z (approx)
- **Completed:** 2026-08-28
- **Tasks:** 2/2 completed
- **Files modified:** 10

## Accomplishments

- Annotated `tests/test_identity_surface.py::Issue3ScanWindowRegressionTest` (class docstring: GAP-01 + GAP-02) and its `test_saml_visible_with_earlier_dnssec` method (GAP-02 bracket-edge-case detail)
- Annotated `tests/test_qramm_router.py::test_create_profile` and `::test_create_profile_multiplier_varies` with QRAMM-09
- Annotated `tests/test_credential_leakage.py`, `tests/test_adcs_ast_gate.py`, `tests/test_smime_ast_gate.py` module docstrings with AUTH-05
- Annotated `tests/test_saml_scanner.py` module docstring with DEBT-04
- Annotated `tests/test_identity_findings_accuracy.py` module docstring with GAP-01 (precision unit-level companion to the test_identity_surface.py annotation)
- Annotated `tests/test_run_scan_codesign_wiring.py` module docstring with TAIL-04
- Annotated `scorecard-maturity.test.tsx` top-of-file comment block with QRAMM-11
- Annotated `ScoreGauge.test.tsx` directly above the `describe` block with GAUGE-01/02/03
- All 119 Python tests (8 files) re-ran and passed (1 skipped for missing impacket, 1 deselected — both unrelated, pre-existing)
- All 13 frontend tests (2 files) re-ran and passed; `npm run lint` clean
- Marked TRACE-03 and TRACE-04 complete in REQUIREMENTS.md via `requirements.mark-complete` (verified underlying condition first, per plan constraints — the verb has no per-phase granularity and has previously over-flipped requirements)
- Updated ROADMAP.md: 170-04-PLAN.md checked off, phase progress row 3/7 -> 4/7

## Verification Evidence

Full grep sweep after both tasks confirms all 10 target files carry a discoverable annotation:

```
tests/test_identity_findings_accuracy.py
tests/test_run_scan_codesign_wiring.py
tests/test_credential_leakage.py
tests/test_saml_scanner.py
tests/test_adcs_ast_gate.py
tests/test_identity_surface.py
tests/test_smime_ast_gate.py
tests/test_qramm_router.py
src/dashboard/src/components/qramm/__tests__/scorecard-maturity.test.tsx
src/dashboard/src/components/gauges/__tests__/ScoreGauge.test.tsx
```

Test run results:
- `pytest tests/test_identity_surface.py tests/test_qramm_router.py tests/test_credential_leakage.py tests/test_adcs_ast_gate.py tests/test_smime_ast_gate.py tests/test_saml_scanner.py tests/test_identity_findings_accuracy.py tests/test_run_scan_codesign_wiring.py -q` -> 119 passed, 1 skipped, 1 deselected
- `npx vitest run src/components/qramm/__tests__/scorecard-maturity.test.tsx src/components/gauges/__tests__/ScoreGauge.test.tsx` -> 2 files passed, 13 tests passed
- `npm run lint` (src/dashboard) -> clean

## Requirement Mapping Confidence

Every mapping below was verified by reading the test body (not just the filename) before annotating, per the plan's critical constraint:

| Req ID | Test | Verified behavior |
|---|---|---|
| GAP-01 | `test_identity_surface.py::Issue3ScanWindowRegressionTest` + `test_identity_findings_accuracy.py` | SAML/OIDC restored in `identity_findings[]`; RS-family OIDC routed to `_derive_identity_findings` |
| GAP-02 | `test_identity_surface.py::Issue3ScanWindowRegressionTest::test_saml_visible_with_earlier_dnssec` | SAML visible in scan-window bracket alongside earlier DNSSEC endpoint |
| QRAMM-09 | `test_qramm_router.py::test_create_profile`, `::test_create_profile_multiplier_varies` | POSTs to `/api/qramm/profiles`, asserts multiplier in 0.8-1.5 range and varies by industry/data_sensitivity |
| AUTH-05 | `test_credential_leakage.py`, `test_adcs_ast_gate.py`, `test_smime_ast_gate.py` | safe_str()/AST-gate credential-scrubbing mechanism, extended to API-key/token field shapes |
| DEBT-04 | `test_saml_scanner.py` | Exercises the lxml-migrated SAML/OIDC parsing path |
| QRAMM-11 | `scorecard-maturity.test.tsx` | Dimension Scorecard maturity-band rendering (bar width, fill class, badge tokens, indeterminate state) |
| TAIL-04 | `test_run_scan_codesign_wiring.py` | TAIL-02/TAIL-03 code-signing wiring (flag on/off, scanner invocation, DAR protocol tuple) |
| GAUGE-01/02/03 | `ScoreGauge.test.tsx` | Per-subscore color thresholds, overall-score amber/green boundary, integer value display |

No mapping failed to hold up — all 8 requirement targets have genuine, passing coverage.

## Deviations from Plan

None — plan executed exactly as written. All 10 files modified per the interfaces table, annotation text matched or closely followed the specified wording, no test logic touched, no new tests written.

## Self-Check: PASSED

- FOUND: tests/test_identity_surface.py (GAP-01/GAP-02 annotations present)
- FOUND: tests/test_qramm_router.py (QRAMM-09 annotations present)
- FOUND: tests/test_credential_leakage.py, tests/test_adcs_ast_gate.py, tests/test_smime_ast_gate.py (AUTH-05 present)
- FOUND: tests/test_saml_scanner.py (DEBT-04 present)
- FOUND: tests/test_identity_findings_accuracy.py (GAP-01 present)
- FOUND: tests/test_run_scan_codesign_wiring.py (TAIL-04 present)
- FOUND: src/dashboard/src/components/qramm/__tests__/scorecard-maturity.test.tsx (QRAMM-11 present)
- FOUND: src/dashboard/src/components/gauges/__tests__/ScoreGauge.test.tsx (GAUGE-0 present)
- FOUND: commit 14647e1 (8 Python file annotations)
- FOUND: commit 2b9f7b8 (2 frontend file annotations)
- FOUND: TRACE-03 and TRACE-04 marked `[x]` in .planning/REQUIREMENTS.md
