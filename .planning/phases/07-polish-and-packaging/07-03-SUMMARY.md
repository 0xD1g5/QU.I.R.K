---
phase: 07-polish-and-packaging
plan: "03"
subsystem: reports
tags: [html-report, jinja2, pdf, playwright, branding, BRAND-03]
dependency_graph:
  requires: [07-01, 07-02]
  provides: [html-report-renderer, pdf-report-renderer]
  affects: [quirk/reports/writer.py, quirk/reports/html_renderer.py, quirk/reports/templates/report.html.j2]
tech_stack:
  added: [jinja2-FileSystemLoader, playwright-pdf-graceful-degradation]
  patterns: [self-contained-html, embedded-css, graceful-degradation]
key_files:
  created:
    - quirk/reports/html_renderer.py
    - quirk/reports/templates/report.html.j2
  modified:
    - quirk/reports/writer.py
decisions:
  - "FileSystemLoader with os.path.dirname(__file__) used instead of PackageLoader — avoids pip reinstall requirement during development"
  - "render_pdf_report() returns bool — False means Playwright unavailable, HTML still written (graceful degradation)"
  - "pdf_path set to None in write_reports() when PDF fails — excluded from output files list automatically via [p for p in [...] if p]"
  - "pyproject.toml package-data entry quirk = ['reports/templates/*.j2'] was already present from prior plan work"
metrics:
  duration_seconds: 128
  completed_date: "2026-04-01"
  tasks_completed: 2
  files_created: 2
  files_modified: 1
---

# Phase 7 Plan 3: HTML Report Renderer and PDF Wiring Summary

Self-contained Jinja2 HTML report renderer with QU.I.R.K. branding and Playwright PDF generation wired into write_reports().

## Objective

Build standalone HTML report renderer (Jinja2) and wire PDF generation into write_reports(). A scan run now produces a professional single-file HTML report and optional PDF — the primary consulting deliverable (D-08 through D-12). Satisfies BRAND-03.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create html_renderer.py and report.html.j2 | f747dff | quirk/reports/html_renderer.py, quirk/reports/templates/report.html.j2 |
| 2 | Wire HTML and PDF generation into write_reports() | 28bbc7b | quirk/reports/writer.py |

## What Was Built

**quirk/reports/html_renderer.py**
- `render_html_report(path, cfg, endpoints, findings, score, conf, roadmap_items)` — renders self-contained HTML via Jinja2 FileSystemLoader
- `render_pdf_report(html_path, pdf_path)` — Playwright headless Chromium PDF; returns False if Playwright unavailable
- `_score_band()`, `_score_color()`, `_severity_color()` helper functions
- Score band thresholds match scoring.py: EXCELLENT>=85, GOOD>=70, MODERATE>=55, FAIR>=35, POOR<35

**quirk/reports/templates/report.html.j2**
- All CSS embedded in `<style>` block — no CDN links, no external font references, fully offline-capable
- CSS variables: `--bg: #0a0a0f`, `--surface: #12121a`, `--accent: #3b9dff`
- QU.I.R.K. wordmark in electric-blue (#3b9dff) with `.wordmark` class
- `<section id="executive-summary">` with score card, findings breakdown, score drivers, top findings, transition roadmap
- `<section id="technical-appendix">` with full findings table and endpoint inventory
- Page title: `QU.I.R.K. — {{ org_name }} Quantum Readiness Report`

**quirk/reports/writer.py**
- Import added: `from quirk.reports.html_renderer import render_html_report, render_pdf_report`
- Step 3b inserted after roadmap write: generates `report-{stamp}.html` then `report-{stamp}.pdf`
- pdf_path set to None when Playwright unavailable (graceful degradation)
- html_path and pdf_path added to rich output files list

## Decisions Made

1. **FileSystemLoader over PackageLoader** — Reads templates from `os.path.dirname(__file__)/templates/` at runtime; no pip reinstall needed during development. PackageLoader requires package data to be built into the distribution which is only available post-install.

2. **render_pdf_report() returns bool** — False signals Playwright unavailable without raising. The caller (write_reports) handles this gracefully by setting pdf_path = None.

3. **pdf_path = None in output list** — The `[p for p in [...] if p]` filter in write_reports() already handles None values, so pdf_path=None is excluded from the printed list automatically.

4. **pyproject.toml package-data already present** — The `[tool.setuptools.package-data]` entry for `quirk = ["reports/templates/*.j2", "config_template.yaml"]` was added in a prior plan; no change needed.

## Verification Results

```
.venv/bin/python -m pytest tests/test_html_report.py tests/test_packaging.py::test_package_data_templates -q
5 passed in 0.13s

.venv/bin/python -m pytest tests/ -q
165 passed, 13 warnings in 5.19s
```

## Deviations from Plan

None — plan executed exactly as written. The pyproject.toml package-data entry was already present from earlier plan work (no action needed for that step).

## Known Stubs

None — render_html_report() produces a complete, wired HTML report. All data flows from actual scan results through write_reports().

## Self-Check: PASSED

- quirk/reports/html_renderer.py exists: FOUND
- quirk/reports/templates/report.html.j2 exists: FOUND
- Commit f747dff exists: FOUND
- Commit 28bbc7b exists: FOUND
- 165 tests pass, no regressions
