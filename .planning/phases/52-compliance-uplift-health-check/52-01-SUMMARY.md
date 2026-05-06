---
phase: 52-compliance-uplift-health-check
plan: "01"
subsystem: test-scaffolding
tags: [tdd, red-phase, compliance, cbom, doctor, wave-0]
dependency_graph:
  requires: []
  provides:
    - test_fips_status_helper
    - test_algorithm_component_has_fips_property
    - test_soc2_entries_present
    - test_iso_entries_present
    - test_iso_rejects_legacy_control_ids
    - test_iso_version_string_exact
    - test_doctor_exits_0_all_pass
    - test_doctor_exits_1_missing_binary
    - test_informational_checks_never_exit_1
    - test_run_stats_ports_and_hosts_scanned
  affects:
    - tests/test_cbom_builder.py
    - tests/test_compliance_schema.py
    - tests/test_doctor_cmd.py
    - tests/test_writer.py
tech_stack:
  added: []
  patterns:
    - TDD red-phase stub pattern (append + new file)
    - SimpleNamespace cfg adapter for write_reports testing
    - monkeypatch + unittest.mock isolation for doctor_cmd tests
key_files:
  created:
    - tests/test_doctor_cmd.py
    - tests/test_writer.py
  modified:
    - tests/test_cbom_builder.py
    - tests/test_compliance_schema.py
decisions:
  - Adapted test_run_stats_ports_and_hosts_scanned to use SimpleNamespace cfg (matching actual write_reports signature) instead of plain dict — writer test passes immediately as fields already exist under counts; serves as regression guard rather than RED stub
  - test_iso_rejects_legacy_control_ids and test_iso_version_string_exact pass vacuously when no ISO entries exist yet — this is correct behavior; they will catch regressions if wrong-format ISO entries are added
metrics:
  duration_seconds: 187
  completed_date: "2026-05-06"
  tasks_completed: 2
  files_modified: 4
---

# Phase 52 Plan 01: Wave 0 Test Scaffolding Summary

Wave 0 test stubs for Phase 52 compliance uplift. Seven new test functions installed across four test files. All FIPS, SOC2, ISO, and doctor stubs fail RED (ImportError or AssertionError) as required; the writer stub serves as a passing regression guard for an already-implemented feature.

## What Was Built

### Task 1: FIPS annotation stubs in tests/test_cbom_builder.py

Two new test functions appended after existing DNSSEC tests:

- `test_fips_status_helper` — asserts `_fips_status(1,3)=="approved"` and `_fips_status(0,None)=="non-approved"`. Fails RED with `ImportError: cannot import name '_fips_status' from 'quirk.cbom.builder'`. Plan 02 turns GREEN by adding the helper.
- `test_algorithm_component_has_fips_property` — asserts every algorithm component in a CBOM built from a TLS endpoint has a Property named `quirk:fips140-3-status` with value in `{"approved","non-approved"}`. Fails RED for the same reason. Plan 02 turns GREEN by adding the property in `_make_algorithm_component`.

Pre-existing 30 tests still collect and pass.

**Commit:** a257f6a

### Task 2: SOC2/ISO schema stubs + test_doctor_cmd.py + test_writer.py

Four stubs appended to `tests/test_compliance_schema.py`:

- `test_soc2_entries_present` — requires `>= 3` SOC2 CC6.x entries in COMPLIANCE_MAP. Fails RED (0 entries found).
- `test_iso_entries_present` — requires `>= 3` ISO 27001:2022 entries. Fails RED (0 entries found).
- `test_iso_rejects_legacy_control_ids` — asserts zero ISO entries with A.x.x control IDs. Passes vacuously now (no ISO entries exist); will catch regressions when wrong-format ISO entries are added.
- `test_iso_version_string_exact` — asserts all ISO entries have `version == "ISO 27001:2022"`. Passes vacuously now; will catch regressions.

New file `tests/test_doctor_cmd.py` with 3 functions:

- `test_doctor_exits_0_all_pass` — monkeypatches `shutil.which` to return valid path; expects `SystemExit(0)`. Fails RED with `ModuleNotFoundError: No module named 'quirk.cli.doctor_cmd'`.
- `test_doctor_exits_1_missing_binary` — monkeypatches `shutil.which` to return None; expects `SystemExit(1)`. Fails RED same way.
- `test_informational_checks_never_exit_1` — network probe patched to raise OSError; expects `SystemExit(0)`. Fails RED same way.

New file `tests/test_writer.py` with 1 function:

- `test_run_stats_ports_and_hosts_scanned` — creates a minimal run_stats dict with `counts.hosts_scanned` and `counts.ports_scanned`, calls `write_reports`, and confirms the fields appear in the `run-stats-*.json` output. Uses `SimpleNamespace` cfg adapter to match the actual `write_reports` signature. Passes immediately (fields already exist under `counts`); serves as DEBT-03 regression guard.

**Commit:** c049147

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Adaptation] Adapted write_reports test cfg to SimpleNamespace**
- **Found during:** Task 2
- **Issue:** Plan stub used `cfg = {"output_dir": str(tmp_path), "report_formats": ["json"]}` (dict), but `write_reports` accesses `cfg.output.directory`, `cfg.assessment.name`, `cfg.intelligence.profile`, etc. via attribute access.
- **Fix:** Used `SimpleNamespace` pattern from `tests/test_html_report.py` (same project pattern) to build a complete minimal cfg that matches the actual signature.
- **Files modified:** tests/test_writer.py
- **Impact:** Test passes immediately because `hosts_scanned` and `ports_scanned` already exist under `counts`. Still serves as the DEBT-03 regression guard.

## Known Stubs

None in production code — this plan only adds test stubs.

## Threat Flags

None — this plan only adds test files, no new network endpoints or auth paths.

## Self-Check: PASSED

- [x] tests/test_cbom_builder.py exists with 2 new functions (lines 527–561)
- [x] tests/test_compliance_schema.py exists with 4 new functions
- [x] tests/test_doctor_cmd.py created with 3 functions
- [x] tests/test_writer.py created with 1 function
- [x] Commit a257f6a exists (Task 1)
- [x] Commit c049147 exists (Task 2)
- [x] 7 RED failures confirmed; 37 pre-existing tests pass
