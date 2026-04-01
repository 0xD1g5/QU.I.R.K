---
phase: 07-polish-and-packaging
plan: "01"
subsystem: testing/packaging
tags: [tdd, test-scaffold, branding, jinja2, rich, packaging]
dependency_graph:
  requires: []
  provides: [RED-test-scaffold, jinja2-installed, rich-declared]
  affects: [07-02, 07-03, 07-04, 07-05]
tech_stack:
  added: [jinja2>=3.1.0, rich>=13.0.0]
  patterns: [TDD-RED-scaffold, wave-0-test-first]
key_files:
  created:
    - tests/test_html_report.py
    - tests/test_dashboard_theme.py
    - tests/test_cli_version.py
    - tests/test_rich_output.py
    - tests/test_cli_init.py
    - tests/test_packaging.py
  modified:
    - pyproject.toml
decisions:
  - "jinja2>=3.1.0 and rich>=13.0.0 added as core dependencies (not optional) — required for CLI + report outputs"
  - "test_dashboard_theme.py immediately GREEN — CSS tokens and sidebar wordmark already in place from Phase 5"
  - "test_packaging.py::test_run_scan_importable immediately GREEN — package importable from Phase 1"
  - "test_packaging.py::test_pyproject_has_jinja2/rich immediately GREEN — added in this plan"
  - "10 RED stubs define the full Phase 7 implementation contract"
metrics:
  duration_seconds: 109
  completed_date: "2026-04-01T00:38:01Z"
  tasks_completed: 2
  tasks_total: 2
  files_created: 6
  files_modified: 1
---

# Phase 07 Plan 01: Test Scaffold (Wave 0) Summary

**One-liner:** Six Phase 7 test stubs with Jinja2/rich declared as core deps — 10 behaviors RED, 7 already GREEN.

## What Was Built

Wave 0 TDD scaffold for all Phase 7 branding and polish behaviors. Six test files created covering HTML report rendering, dashboard CSS tokens, CLI `--version` flag, rich terminal output, `quirk init` subcommand, and package data/version validation.

Jinja2 3.1.6 installed into `.venv` and declared alongside `rich>=13.0.0` as core `pyproject.toml` dependencies.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Install Jinja2, write HTML/dashboard stubs | 0a3b303 | pyproject.toml, tests/test_html_report.py, tests/test_dashboard_theme.py |
| 2 | Write CLI and packaging test stubs | 3a9afd4 | tests/test_cli_version.py, tests/test_rich_output.py, tests/test_cli_init.py, tests/test_packaging.py |

## Test State After This Plan

**RED (10) — awaiting Phase 7 implementation:**
- `test_html_report.py`: test_report_contains_wordmark, test_html_is_self_contained, test_html_report_sections (html_renderer module missing)
- `test_cli_version.py`: test_version_flag (--version not added to argparse)
- `test_rich_output.py`: test_scan_summary_uses_rich, test_no_bare_summary_prints (writer.py still uses bare print())
- `test_cli_init.py`: test_init_creates_config, test_init_no_overwrite (init subcommand missing)
- `test_packaging.py`: test_version_is_4_0_0 (still 3.9.0), test_package_data_templates (templates dir missing)

**GREEN (7) — already satisfied:**
- `test_dashboard_theme.py`: test_primary_color_token, test_accent_color_token, test_sidebar_wordmark_present
- `test_html_report.py`: test_pdf_graceful_degradation (writer module reloads without error)
- `test_packaging.py`: test_run_scan_importable, test_pyproject_has_jinja2, test_pyproject_has_rich

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None that affect this plan's goal. Test stubs are intentionally RED — they define the contract for subsequent implementation plans.

## Self-Check: PASSED

Files created:
- tests/test_html_report.py: FOUND
- tests/test_dashboard_theme.py: FOUND
- tests/test_cli_version.py: FOUND
- tests/test_rich_output.py: FOUND
- tests/test_cli_init.py: FOUND
- tests/test_packaging.py: FOUND

Commits:
- 0a3b303: FOUND (test(07-01): install Jinja2, add HTML report and dashboard theme test stubs)
- 3a9afd4: FOUND (test(07-01): add CLI, rich output, init, and packaging test stubs)

pyproject.toml contains jinja2>=3.1.0: VERIFIED
pyproject.toml contains rich>=13.0.0: VERIFIED
.venv jinja2 installed: Version 3.1.6
