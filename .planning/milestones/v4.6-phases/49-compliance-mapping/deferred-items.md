# Phase 49 Deferred Items

## Pre-existing failures (out-of-scope for plan 49-02)

### tests/test_cbom_schema_validation.py — 19 failures

Pre-existing baseline: confirmed by `git stash && pytest` before plan 49-02 changes.
These tests require Docker chaos-lab fixtures that are not present in CI environment.
Not caused by plan 49-02 changes — out-of-scope per executor scope-boundary rule.

### Expected RED tests (per plan 49-02 instructions)

- tests/test_compliance_cli.py::test_status_text_smoke
- tests/test_compliance_cli.py::test_status_json_smoke
- tests/test_compliance_report_section.py::test_html_contains_compliance_summary

These remain RED until plans 49-03 (report-render) and 49-04 (CLI) execute.
