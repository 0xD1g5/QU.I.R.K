---
phase: 12-cli-correctness
plan: 01
subsystem: testing
tags: [pytest, tdd, cli, version-consistency, config-template]

requires:
  - phase: 08-legacy-debt-cleanup
    provides: config_template.yaml aligned to ConnectorsCfg fields; enable_windows_adcs removed
  - phase: 07-polish-and-packaging
    provides: quirk init subcommand and docs/getting-started.md

provides:
  - tests/test_cli_correctness.py with 6 contract tests covering CLI-01 through CLI-04
  - RED contract for version consistency (4.0.0 vs 4.1.0 target)
  - RED contract for config_from_dict fallback version
  - RED contract for [owner] placeholder in docs/getting-started.md
  - GREEN regression guards for template field alignment and no quirk scan references

affects:
  - 12-02 (implements fixes to make all 6 tests GREEN)
  - 13-interactive-mode (CLI contract must stay GREEN)
  - 14-scoring-correctness (version consistency affects score output headers)

tech-stack:
  added: []
  patterns:
    - "TDD RED scaffold: write failing tests first to define the contract before any fix (Nyquist validation strategy)"
    - "pathlib.Path source inspection: read config.py source text to assert fallback string values"
    - "dataclasses.fields() introspection: verify YAML template keys against real dataclass field names"

key-files:
  created:
    - tests/test_cli_correctness.py
  modified: []

key-decisions:
  - "test_config_default_version uses pathlib source inspection (not import) to assert the fallback string — this catches the exact value even before any module reload"
  - "test_no_quirk_scan_references excludes docs/superpowers/ (historical spec docs) per D-09/Pitfall 5"
  - "Template field alignment test asserts enable_windows_adcs absent to prevent regression of Phase 8 cleanup"

patterns-established:
  - "Phase 12 contract pattern: 3 RED tests define what Plan 02 must fix; 3 GREEN tests guard existing correctness"

requirements-completed:
  - CLI-01
  - CLI-02
  - CLI-03
  - CLI-04

duration: 2min
completed: 2026-04-06
---

# Phase 12 Plan 01: CLI Correctness Summary

**TDD RED scaffold establishing the Phase 12 contract: 3 failing tests prove version inconsistency (4.0.0 vs 4.1.0), stale config fallback, and [owner] placeholder; 3 passing tests guard already-clean areas (config template, no quirk scan refs, load_config integrity)**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-06T12:24:09Z
- **Completed:** 2026-04-06T12:26:09Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Created `tests/test_cli_correctness.py` with exactly 6 test functions covering all four CLI correctness requirements (CLI-01 through CLI-04)
- Confirmed RED state: `test_version_consistency` fails (quirk.__version__ = "4.0.0", PLATFORM_VERSION = "4.0", target = "4.1.0"), `test_config_default_version` fails (fallback "4.0.0"), `test_no_owner_placeholder` fails ([owner] on lines 22 and 28 of docs/getting-started.md)
- Confirmed GREEN state: `test_init_config_loads_without_error`, `test_template_field_alignment`, `test_no_quirk_scan_references` all pass
- Full test suite continues to pass: 199 existing tests + 3 GREEN new tests = 202 passing (3 intentional RED)

## Task Commits

1. **Task 1: Create RED test scaffold for all CLI correctness requirements** - `a29d6fa` (test)

## Files Created/Modified

- `tests/test_cli_correctness.py` - 6-test Phase 12 correctness contract scaffold (3 RED, 3 GREEN)

## Decisions Made

- `test_config_default_version` uses pathlib source text inspection rather than import to detect the exact fallback string in `config_from_dict` — this ensures the test catches the value even before any module cache invalidation is needed in Plan 02
- The `test_no_quirk_scan_references` exclusion of `docs/superpowers/` follows D-09 / Pitfall 5 from RESEARCH.md to avoid false positives on historical spec documents
- `test_template_field_alignment` checks both `connectors:` and `scan:` blocks and explicitly asserts `enable_windows_adcs` absent — guards against regression of the Phase 8 dead-field cleanup

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## Known Stubs

None — this plan creates only test code. No data sources or UI components involved.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 02 (12-02) can proceed immediately: the contract tests are in place and provide an unambiguous target — all 6 tests must be GREEN after Plan 02
- Plan 02 must update: `quirk/__init__.py` (__version__), `quirk/reports/writer.py` (PLATFORM_VERSION = "4.1.0", INTELLIGENCE_VERSION = "4.1.0"), `quirk/cbom/builder.py` (PLATFORM_VERSION = "4.1.0"), `quirk/config.py` (IntelligenceCfg default + config_from_dict fallback), `docs/getting-started.md` ([owner] → real org handle)

---
*Phase: 12-cli-correctness*
*Completed: 2026-04-06*
