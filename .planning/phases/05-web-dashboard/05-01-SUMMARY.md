---
phase: 05-web-dashboard
plan: 01
subsystem: dashboard
tags: [tdd, test-scaffolds, dependencies, wave-0]
dependency_graph:
  requires: []
  provides: [dashboard-test-fixtures, dashboard-deps]
  affects: [05-02, 05-04, 05-06]
tech_stack:
  added: [fastapi>=0.128.8, uvicorn[standard]>=0.39.0, python-multipart>=0.0.20, playwright>=1.58.0]
  patterns: [pytest-skip-stubs, deferred-import-fixture]
key_files:
  created:
    - tests/conftest.py
    - tests/test_dashboard_api.py
    - tests/test_pdf_export.py
  modified:
    - pyproject.toml
decisions:
  - httpx omitted from dashboard optional group (already in main dependencies)
  - conftest.py uses try/except ImportError so tests skip cleanly before quirk.dashboard exists
  - dashboard group in [project.optional-dependencies] keeps deps separable from core scanner
metrics:
  duration: 93s
  completed: "2026-03-31T02:45:47Z"
  tasks_completed: 2
  files_changed: 4
---

# Phase 5 Plan 01: Wave 0 Dashboard Test Scaffolds Summary

**One-liner:** Wave 0 RED-state test stubs and dashboard optional-dependencies added to pyproject.toml — 9 tests collect and skip cleanly establishing the automated verify contract for 05-02 through 05-06.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Install backend Python dependencies | 4084e6a | pyproject.toml |
| 2 | Create Wave 0 test scaffolds — dashboard API and PDF export | 43dc722 | tests/conftest.py, tests/test_dashboard_api.py, tests/test_pdf_export.py |

## Verification Results

1. `python -c "import fastapi, uvicorn, httpx, playwright; print('OK')"` — prints OK
2. `pytest tests/test_dashboard_api.py tests/test_pdf_export.py -q` — 9 skipped, exit 0
3. `pyproject.toml` contains `[project.optional-dependencies]` with `dashboard` group
4. `grep -c "pytest.skip" tests/test_dashboard_api.py` — returns 7

## Decisions Made

- **httpx excluded from dashboard group**: httpx is already in `[project]` dependencies; adding it to the optional group would create a version conflict risk with no benefit.
- **deferred import in conftest.py**: The `dashboard_client` fixture wraps the import in try/except ImportError and calls `pytest.skip()` so all fixture-dependent tests collect and skip cleanly before `quirk/dashboard/api/app.py` exists (created in 05-02).
- **Optional group over main deps**: FastAPI/uvicorn/playwright are dashboard-only — keeping them in an optional group prevents them from being pulled into environments that only use the CLI scanner.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

The following test stubs are intentional Wave 0 placeholders:

| File | Tests | Reason |
|------|-------|--------|
| tests/test_dashboard_api.py | test_serve_command, test_dashboard_loads, test_health_endpoint | Implemented in 05-02 |
| tests/test_dashboard_api.py | test_score_endpoint, test_findings_endpoint, test_certificates_endpoint, test_cbom_endpoint | Implemented in 05-04 |
| tests/test_pdf_export.py | test_pdf_export_endpoint, test_pdf_export_graceful_degradation | Implemented in 05-06 |

These stubs are intentional — the Wave 0 goal is to establish the test contract. Subsequent plans wire real implementations.
