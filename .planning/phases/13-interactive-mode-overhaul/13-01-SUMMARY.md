---
phase: 13-interactive-mode-overhaul
plan: 01
subsystem: testing
tags: [tdd, interactive-mode, pytest, unittest-mock, expectedFailure]

requires:
  - phase: 12-cli-correctness
    provides: "Correctness baseline (205 passing tests, 4.1.0 versions unified) required before overhaul"

provides:
  - "RED TDD scaffold for INTER-01 through INTER-10 in tests/test_interactive_mode.py"
  - "MINIMAL_INPUTS constant defining the new targets-first prompt sequence for Plan 02"
  - "10 @unittest.expectedFailure tests covering all interactive mode requirements"

affects:
  - 13-interactive-mode-overhaul (Plan 02 — implementation must pass all 10 tests)

tech-stack:
  added: []
  patterns:
    - "TDD RED scaffold with @unittest.expectedFailure — same Nyquist pattern as Phase 12"
    - "MINIMAL_INPUTS module-level constant for reusable mock side_effect lists"
    - "unittest.mock.patch('builtins.input', side_effect=[...]) for prompt simulation"
    - "unittest.mock.patch('builtins.print', side_effect=capture) for output capture"

key-files:
  created:
    - tests/test_interactive_mode.py
  modified: []

key-decisions:
  - "MINIMAL_INPUTS sequence encodes the NEW D-15 prompt order (targets first); tests fail against current metadata-first order"
  - "All 10 tests use @unittest.expectedFailure — suite stays green while tests are individually RED"
  - "Tests verify tuple return type (cfg, profile) = interactive_config() — fails current AppConfig-only return"
  - "test_prompt_order captures input() call arguments in order to verify targets precede metadata"
  - "test_connector_labels_no_stub patches builtins.print to inspect all printed output for stub labels and credential warnings"

patterns-established:
  - "Pattern: module-level MINIMAL_INPUTS constant; each test does list(MINIMAL_INPUTS) to avoid shared mutable state"
  - "Pattern: insert extra inputs into copy of MINIMAL_INPUTS for tests requiring scanner/connector follow-up prompts"

requirements-completed:
  - INTER-01
  - INTER-02
  - INTER-03
  - INTER-04
  - INTER-05
  - INTER-06
  - INTER-07
  - INTER-08
  - INTER-09
  - INTER-10

duration: 8min
completed: 2026-04-06
---

# Phase 13 Plan 01: Interactive Mode Overhaul TDD Scaffold Summary

**10 RED expectedFailure tests in tests/test_interactive_mode.py defining the complete Plan 02 implementation contract for interactive_config() overhaul**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-04-06T00:03:19Z
- **Completed:** 2026-04-06T00:11:36Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Created `tests/test_interactive_mode.py` with 10 test functions covering INTER-01 through INTER-10
- All 10 tests decorated with `@unittest.expectedFailure` — they are RED against current `interactive.py` and confirm the implementation contract
- Defined `MINIMAL_INPUTS` constant encoding the new targets-first prompt sequence (D-15) for reuse across all tests
- Full test suite remains green: 205 passed + 10 xfailed
- Tests verify: tuple return type, timezone auto-detection, no SNI prompt, no ADCS prompt/field, no stub labels, credential warnings for AWS/Azure, all 17 consulting-grade ports, targets-before-metadata order, profile selection, unified data classification mapping

## Task Commits

1. **Task 1: Create RED test scaffold for interactive mode requirements** - `f7c29e9` (test)

## Files Created/Modified

- `tests/test_interactive_mode.py` — 10 @unittest.expectedFailure tests for INTER-01 through INTER-10, MINIMAL_INPUTS constant, detailed assertions per requirement

## Decisions Made

- `MINIMAL_INPUTS` is defined as a module-level list constant; every test copies it with `list(MINIMAL_INPUTS)` to prevent shared mutable state across tests
- Scanner-enabling tests (INTER-05) insert follow-up target inputs at the correct positions in the copied list rather than using a different approach
- `test_prompt_order` uses a `try/except Exception` block inside the mock context so partial execution is captured even if the current implementation fails mid-run
- `test_data_classification_unified` tests all three explicitly mapped tiers from D-11 in a single test function (regulated, public, confidential)

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Plan 01 complete: all 10 INTER requirement tests exist in RED state
- Plan 02 (implementation) can begin: `interactive_config()` needs full rewrite per D-01 through D-16
- Plan 02 must make all 10 tests GREEN while keeping the full suite at 215 passed
- Key implementation targets: tuple return type, timezone auto-detect, hardcoded SNI/ports, profile selection menu, unified data classification menu, targets-first prompt order, credential warnings

## Known Stubs

None — this plan creates test scaffolding only; no production code changes.

---
*Phase: 13-interactive-mode-overhaul*
*Completed: 2026-04-06*
