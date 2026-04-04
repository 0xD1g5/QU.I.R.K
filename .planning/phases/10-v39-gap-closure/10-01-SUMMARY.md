---
phase: 10-v39-gap-closure
plan: "01"
subsystem: dashboard-api
tags: [bug-fix, tdd, quantum-safety, dashboard]
dependency_graph:
  requires: []
  provides: [MISMATCH-01-fixed]
  affects: [quirk/dashboard/api/routes/scan.py]
tech_stack:
  added: []
  patterns: [two-step classify_algorithm -> quantum_safety_label, module-level display map]
key_files:
  created:
    - tests/test_gap_closure.py
  modified:
    - quirk/dashboard/api/routes/scan.py
decisions:
  - "_QS_DISPLAY promoted to module level so _derive_findings, _derive_cbom, and _cert_quantum_safety all share one source of truth for display label mapping"
  - "Two-step classify_algorithm(alg) -> quantum_safety_label(nist_level) pattern enforced at all three call sites — no direct string-to-label shortcut allowed"
metrics:
  duration: 89s
  completed: "2026-04-04"
  tasks: 2
  files: 2
---

# Phase 10 Plan 01: MISMATCH-01 Quantum Safety Label Fix Summary

Fixed type-confusion bug in the dashboard API where `quantum_safety_label()` received a raw algorithm string instead of an integer NIST level, causing DSA/ECDSA/RSA certificates to silently display "quantum-safe" instead of "Vulnerable" in all three dashboard views.

## What Was Built

### Task 1: Regression Tests (TDD RED)

Created `tests/test_gap_closure.py` with 4 tests that confirmed the bug was testable:

- `test_findings_quantum_label_dsa` — `_derive_findings` with DSA cert must produce `quantum_risk="Vulnerable"`
- `test_findings_quantum_label_ecdsa` — same for ECDSA cert
- `test_cert_quantum_safety_display_label` — `_cert_quantum_safety("RSA")` must return `"Vulnerable"` not raw enum
- `test_cert_quantum_safety_pqc_safe` — `_cert_quantum_safety("ML-KEM-768")` must return `"Safe"`

All 4 failed against the broken code (RED state confirmed bug is testable).

### Task 2: Fix MISMATCH-01 (TDD GREEN)

Three changes to `quirk/dashboard/api/routes/scan.py`:

1. **Module-level `_QS_DISPLAY`** added after router declaration (line 31). Removed duplicate definition from inside `_derive_cbom()`.

2. **`_derive_findings()` fixed** — replaced `quantum_safety_label(ep.cert_pubkey_alg)` (string arg) with two-step:
   ```python
   _, nist_level, _ = classify_algorithm(ep.cert_pubkey_alg)
   qs = _QS_DISPLAY.get(quantum_safety_label(nist_level), "Unknown")
   ```

3. **`_cert_quantum_safety()` fixed** — replaced `quantum_safety_label(algorithm)` (string arg, raw enum return) with two-step pattern returning display labels.

## Verification Results

- `python -m pytest tests/test_gap_closure.py -q` — 4 passed
- `python -m pytest tests/test_dashboard_api.py -q` — 7 passed (no regressions)
- `python -m compileall quirk/dashboard/api/routes/scan.py` — clean
- `grep "^_QS_DISPLAY" scan.py` — matches exactly once at module level
- Bug patterns `quantum_safety_label(ep.cert_pubkey_alg)` and `quantum_safety_label(algorithm)` — no matches

## Commits

| Task | Commit | Message |
|------|--------|---------|
| 1 (TDD RED) | e49497f | test(10-01): add failing regression tests for MISMATCH-01 |
| 2 (Fix) | 05ae299 | fix(10-01): fix MISMATCH-01 quantum safety label type confusion in scan.py |

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all data paths are fully wired.

## Self-Check: PASSED
