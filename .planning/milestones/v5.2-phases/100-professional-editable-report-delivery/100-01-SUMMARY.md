---
phase: 100-professional-editable-report-delivery
plan: "01"
subsystem: reports
tags: [fmt, cover-page, print-css, logo-embed, pdf, html]
dependency_graph:
  requires: []
  provides: [FMT-01, FMT-02]
  affects: [quirk/reports/html_renderer.py, quirk/reports/templates/report.html.j2, quirk/config.py]
tech_stack:
  added: [base64 (stdlib)]
  patterns: [optional-field-default, base64-data-uri-embed, jinja2-conditional-guard, css-media-print]
key_files:
  created: [tests/test_config.py]
  modified:
    - quirk/config.py
    - quirk/config_template.yaml
    - quirk/reports/html_renderer.py
    - quirk/reports/templates/report.html.j2
    - tests/test_html_report.py
decisions:
  - "logo_path added as last field of AssessmentCfg with None default — backward-compat with existing configs using **raw[assessment] expansion (D-01)"
  - ".cover-meta-block CSS uses only padding:16px 24px + margin-top:auto — dead padding-top:48px dropped per UI-SPEC executor note"
  - "test_logo_absent_graceful checks for <div class=cover-logo-region> element absence not CSS class name string, since CSS always contains the selector"
  - "test_findings_table_class renders with one finding — class is inside {% if findings %} branch"
metrics:
  duration: "~12 minutes"
  completed: "2026-05-24"
  tasks_completed: 2
  files_changed: 5
---

# Phase 100 Plan 01: PDF Cover Page + Print CSS + Logo Embed Summary

**One-liner:** Branded PDF cover page with base64 logo embed, graceful omit guard, and fixed-layout print CSS for the 7-column findings table.

## What Was Built

### Task 1: AssessmentCfg.logo_path + backward-compat tests

Added `logo_path: str | None = None` as the last field of `AssessmentCfg` in `quirk/config.py`, preserving backward compatibility with all existing configs that use `AssessmentCfg(**raw["assessment"])` (no new required key, defaulted optional). Added a commented-out `# logo_path:` example line in `quirk/config_template.yaml` (never uncommented — would cause TypeError if yaml key has no matching field until the field ships). Created `tests/test_config.py` with `test_assessment_cfg_logo_path` and `test_backward_compat_config`.

**Commit:** b6b43cf

### Task 2: Logo embed + cover-page markup + print CSS

- **`quirk/reports/html_renderer.py`**: Added `import base64`, `_load_logo_b64(logo_path)` helper with `try/except (OSError, IOError)` graceful omit (T-100-LOGO / D-03). Added double-getattr logo_path extraction before `template.render`, passes `logo_b64` and `logo_mime` as new kwargs.

- **`quirk/reports/templates/report.html.j2`**: Inserted verbatim CSS additions (cover-page, cover-logo-region, cover-title, cover-org-name, cover-meta-block, cover-classification-banner, findings-table fixed-layout with 8/22/12/5/23/18/12% column widths) before `</style>`. Added `@media print` block (A4, break-after/break-inside guards, thead repeat, screen-only element suppression). Inserted verbatim cover-page Jinja2 block as first child of `<div class="report-body">`, with `{% if logo_b64 %}` guard. Added `class="findings-table"` to the All Findings `<table>` element.

- **`tests/test_html_report.py`**: Added 6 new Phase 100 tests: `test_cover_page_in_html`, `test_logo_absent_graceful`, `test_logo_embedded`, `test_print_media_block`, `test_findings_table_class`, `test_fixed_table_layout_css`.

**Commit:** 792f295

## Verification

```
python -m pytest tests/test_config.py tests/test_html_report.py -q
12 passed in 0.30s

python -m compileall quirk/config.py quirk/reports/html_renderer.py
(no errors)
```

Rendered HTML contains:
- `cover-page` block (FMT-01)
- Locked title string `QU.I.R.K. Cryptographic Readiness Report`
- `{% if logo_b64 %}` guard (D-03)
- `@media print` block (FMT-02)
- `table-layout: fixed` (FMT-02 / D-06)
- `class="findings-table"` on All Findings table (FMT-02)
- `.cover-meta-block` has `padding: 16px 24px` + `margin-top: auto` only (no `padding-top: 48px`)

## Deviations from Plan

### Minor test adjustments (Rule 1 — correctness)

**1. [Rule 1 - Bug] test_logo_absent_graceful assertion scope**
- **Found during:** Task 2 GREEN
- **Issue:** Test asserted `"cover-logo-region" not in content` but the CSS `<style>` block always contains `.cover-logo-region` as a selector string, causing false failure.
- **Fix:** Changed to `'<div class="cover-logo-region">' not in content` to check for the HTML *element* not the CSS class name.
- **Files modified:** tests/test_html_report.py

**2. [Rule 1 - Bug] test_findings_table_class rendered with empty findings**
- **Found during:** Task 2 GREEN
- **Issue:** The All Findings `<table class="findings-table">` is inside `{% if findings %}` in the template, so rendering with empty findings never outputs the element.
- **Fix:** Changed helper to render with one synthetic finding so the `{% if findings %}` branch is reached.
- **Files modified:** tests/test_html_report.py

## Known Stubs

None — all cover-page fields wire through to live template context variables (`org_name`, `report_owner`, `data_classification`, `generated_at`, `logo_b64`/`logo_mime`).

## Threat Flags

No new threat surface beyond what was declared in the plan's threat model (T-100-LOGO, T-100-XSS, T-100-IMG — all mitigated as implemented).

## Self-Check: PASSED

- quirk/config.py has `logo_path: str | None = None`: FOUND
- quirk/reports/html_renderer.py has `def _load_logo_b64` and `import base64`: FOUND
- quirk/reports/templates/report.html.j2 has `cover-page`, `QU.I.R.K. Cryptographic Readiness Report`, `{% if logo_b64 %}`, `@media print`, `table-layout: fixed`, `class="findings-table"`: FOUND
- tests/test_config.py exists: FOUND
- tests/test_html_report.py has Phase 100 tests: FOUND
- Commits b6b43cf and 792f295 exist: FOUND
