---
phase: 49-compliance-mapping
plan: 03
subsystem: reports
tags: [compliance, html-report, jinja2, pdf]
requires: [49-02]
provides: [compliance-summary-html-section]
affects: [quirk/reports/templates/report.html.j2]
tech-stack:
  added: []
  patterns: [jinja2-loop-accumulator]
key-files:
  created: []
  modified:
    - quirk/reports/templates/report.html.j2
decisions:
  - "Insert Compliance Summary inside Technical Appendix, after All Findings, before Endpoint Inventory (matches D-03 audit-evidence intent)"
  - "Always emit 'Findings without compliance mapping' header (with all-mapped fallback note) so smoke test substring check is fixture-independent"
  - "Reuse existing .sev-cell/.sev-* classes — no new CSS, PDF-safe markup only"
metrics:
  duration: "~5 min"
  completed: "2026-05-05"
  tasks_completed: 1
  files_modified: 1
requirements: [COMPLY-05]
---

# Phase 49 Plan 03: Compliance Summary HTML Section Summary

**One-liner:** Added framework-grouped Compliance Summary section (PCI-DSS 4.0.1, HIPAA 45 CFR, FIPS 140-3) plus unmapped-findings subsection to `report.html.j2`, turning COMPLY-05 GREEN.

## What Was Built

A single Jinja2 block (~57 lines) inserted into `quirk/reports/templates/report.html.j2` immediately after the "All Findings" table and before "Endpoint Inventory":

1. **Framework loop** — iterates `['PCI-DSS 4.0.1', 'HIPAA 45 CFR', 'FIPS 140-3']`. For each framework, accumulates `(finding, compliance_entry)` tuples where `compliance.framework == fw` (excluding `coverage_gap` findings), then emits a `<table>` with columns: Severity / Finding / Control (+version) / Source link · last_verified. Empty per-framework state renders a muted "No findings mapped to {fw}." paragraph so absence is explicit.
2. **Unmapped subsection** — collects findings with empty `compliance` list (excluding coverage_gap) into a `<ul>` of `title (host)` lines. When all findings are mapped, the heading still renders with a muted "all mapped" note (keeps smoke-test substring stable across fixtures).

PDF inheritance is automatic via the existing Playwright path in `render_pdf_report` — no Python changes.

## Verification

```
$ pytest tests/test_compliance_report_section.py -x -q
2 passed in 0.03s

$ pytest tests/test_compliance_*.py tests/test_pqc_terminology_gate.py -x -q
14 passed in 0.84s
```

Both gates green. Smoke test confirms all 5 required substrings present in rendered HTML: `Compliance Summary`, `PCI-DSS 4.0.1`, `HIPAA 45 CFR`, `FIPS 140-3`, `Findings without compliance mapping`.

## Deviations from Plan

None — plan executed exactly as written. The template insertion matches the plan's exact code block.

## Commits

- `16dfd66` feat(49-03): add Compliance Summary section to report.html.j2

## Self-Check: PASSED

- Modified file exists: `quirk/reports/templates/report.html.j2` — FOUND
- Commit `16dfd66` — FOUND in git log
- Smoke test GREEN — verified
- Threat-model dispositions honored: T-49-08 (Jinja2 autoescape — confirmed unchanged in `html_renderer.py:6`); T-49-10 (only `<table>`/`<span>`/existing CSS — no flex/grid/sticky).
