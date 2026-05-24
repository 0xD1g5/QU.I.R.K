---
phase: 98-executive-narrative-score-transparency
plan: "02"
subsystem: reports
tags: [exec-narrative, score-transparency, html-renderer, cli-markdown, jinja2-template, congruence-guard]
requires: [98-01]
provides: [writer-exec-content-seam, build_exec_markdown-exec_content-kwarg, render_html_report-exec_content-kwarg, narrative-block-html, risks-list-html, rollup-formula-html, priority-label-html, test_exec_narrative_ordering]
affects:
  - quirk/reports/writer.py
  - quirk/reports/executive.py
  - quirk/reports/html_renderer.py
  - quirk/reports/templates/report.html.j2
  - tests/test_congruence_guard.py
  - tests/test_exec_narrative_ordering.py
tech-stack:
  added: []
  patterns: [exec-content-kwarg-backward-compat, jinja2-safe-for-static-prose, jinja2-attribute-or-item-lookup, conditional-backward-compat-path]
key-files:
  created:
    - tests/test_exec_narrative_ordering.py
  modified:
    - quirk/reports/writer.py
    - quirk/reports/executive.py
    - quirk/reports/html_renderer.py
    - quirk/reports/templates/report.html.j2
    - tests/test_congruence_guard.py
decisions:
  - "writer.py seam: exec_md build moved after score_raw/roadmap_raw; build_exec_content() called with canonical score_raw BEFORE compat wrapper (Pitfall 1 avoidance)"
  - "narrative_lead uses | safe in template — static prose from _NARRATIVE_LEADS, not scanner input; autoescape was escaping apostrophes"
  - "narrative_drivers use | sanitize in template — come from score_raw['drivers'], scanner-derived"
  - "RoadmapItem dataclass accessed via item.title in template (Jinja2 attribute-or-item-lookup works for both dataclass and dict backward-compat)"
  - "Backward-compat None path in both build_exec_markdown() and render_html_report() for callers not yet using exec_content kwarg"
  - "exec_content.top_risks risk_label/impact_sentence are from ALGO_IMPACT_MAP — static strings, no sanitize in template"
metrics:
  duration_minutes: 22
  completed: "2026-05-24"
  tasks_completed: 2
  tasks_total: 2
  files_created: 1
  files_modified: 5
---

# Phase 98 Plan 02: Writer Seam, HTML Renderer, Template, and Ordering Tests Summary

**One-liner:** Wire ExecContent into writer.py/executive.py/html_renderer.py seam and report.html.j2 template, adding narrative-block, risks-list, rollup-formula, and priority-label across CLI and HTML surfaces with full ordering/presence test coverage.

## What Was Built

### Task 1: Writer seam + congruence guard integration + CLI narrative/risks/roadmap

Modified `quirk/reports/writer.py`:
- Added `from quirk.reports.content_model import build_exec_content, ReportCongruenceError` import (D-03/D-06)
- Moved `tech_md` build before intelligence outputs (no score dependency)
- Reordered: intelligence outputs computed first (`score_raw`, `roadmap_raw`), then `build_exec_content()` called with canonical `score_raw` BEFORE the compat wrapper — avoids Pitfall 1 key-shape mismatch
- `exec_md` (build_exec_markdown) now built after exec_content, with `exec_content=exec_content` kwarg
- `render_html_report` call gets `exec_content=exec_content` kwarg

Modified `quirk/reports/executive.py`:
- Added `from __future__ import annotations` and `Optional` typing import
- Added `from quirk.reports.content_model import ExecContent` (D-03)
- Added `exec_content: "ExecContent | None" = None` keyword to `build_exec_markdown()` (backward-compat default None)
- Inserted `## Readiness Assessment` narrative prose block immediately after `## Executive Summary` and BEFORE `## Quantum Readiness Score` (EXEC-01 compliance; Pitfall 4 avoidance)
- Added `## Priority Business Risks` bullet section from `exec_content.top_risks` after Score Decomposition (EXEC-02); md_cell-wrapped per HARDEN-01
- Roadmap rendering updated: when `exec_content` provided, uses `exec_content.roadmap_items` (RoadmapItem dataclasses with effort/impact attributes); appends `[EFFORT · IMPACT]` labels to each bullet (EXEC-03)
- Removed `## Interpretation` section entirely (Pitfall 6; content subsumed into narrative block)
- Backward-compat path maintained when `exec_content=None`

Appended to `tests/test_congruence_guard.py`:
- `test_guard_blocks_report_generation`: integration test asserting `write_reports()` raises `ReportCongruenceError` before writing any executive summary file; mocks intelligence layer; verifies no `executive-summary-*` file created in output dir

Commit: `c9ecd54`

### Task 2: HTML renderer + template narrative/risks/rollup/priority + ordering tests

Modified `quirk/reports/html_renderer.py`:
- Added `from quirk.reports.content_model import ExecContent` import (D-03)
- Added `exec_content: "ExecContent | None" = None` keyword to `render_html_report()` (backward-compat default None)
- When `exec_content` provided: `subscores_ctx` sourced from `exec_content.subscores` (D-07); `roadmap_now/next/later` split from `exec_content.roadmap_items` (RoadmapItem dataclasses); `narrative_lead`, `narrative_drivers`, `top_risks` passed to template
- Backward-compat fallback when `exec_content=None`: raw dicts from `score`/`roadmap_section()`

Modified `quirk/reports/templates/report.html.j2`:
- Added 4 CSS rule blocks inside existing `<style>` block (no new colors/sizes/weights per UI-SPEC): `.narrative-block`, `.risks-list`/`.risk-label`/`.risk-impact`, `.rollup-formula`, `.priority-label`
- Inserted `<div class="narrative-block">` (heading "Readiness Assessment") before `<h2>Quantum Readiness Score</h2>` (EXEC-01); `narrative_lead | safe` for static prose; `narrative_drivers | join | sanitize` for scanner-derived text
- Added `<div class="rollup-formula">` block after Score Decomposition table with UI-SPEC exact copy: "How this score was computed" / "Six pillar subscores..." (TRANS-02)
- Added `Priority Business Risks` `<ul class="risks-list">` after rollup-formula and before Findings Breakdown; each `<li>` with `.risk-label` + `.risk-impact` spans from `top_risks` (EXEC-02)
- Added `<span class="priority-label">` inside each `.roadmap-item` showing effort/impact bands from `item.effort`/`item.impact` (EXEC-03); conditional on `item.effort is defined`

Created `tests/test_exec_narrative_ordering.py`:
- All 5 VALIDATION.md node IDs implemented and green:
  - `test_narrative_before_findings_cli`: asserts `## Readiness Assessment` position < `## Findings Overview` in CLI output; also checks narrative_lead string present (EXEC-01/EXEC-04)
  - `test_narrative_before_table_html`: asserts `narrative-block` position < first `<table` in HTML; checks narrative_lead string present
  - `test_risks_list_in_html`: asserts `risks-list`, `risk-label`, `Priority Business Risks` present; checks ordering before Findings Breakdown (EXEC-02)
  - `test_priority_labels_in_html_roadmap`: asserts `priority-label`, `EFFORT`, `IMPACT` strings present (EXEC-03)
  - `test_rollup_formula_in_html`: asserts `rollup-formula`, "How this score was computed", "Six pillar subscores" present; checks ordering before Findings Breakdown (TRANS-02)

Commit: `f6703d1`

## Decisions Made

1. **writer.py seam ordering** — `exec_md` (build_exec_markdown) was previously called at step 2 BEFORE intelligence outputs were computed (step 3). Restructured so intelligence outputs (score_raw, roadmap_raw) are computed first, then `build_exec_content()` called with canonical `score_raw` BEFORE the compat wrapper. This is the only correct insertion point per Pitfall 1 and D-06 (guard fires before file I/O).

2. **`narrative_lead | safe` in Jinja2 template** — Jinja2's autoescape was escaping the apostrophe in "organization's" to `&#39;`, causing the test assertion `exec_content.narrative_lead in content` to fail. Since `narrative_lead` is a static string from `_NARRATIVE_LEADS` (fully controlled code, not scanner input), `| safe` is correct. `narrative_drivers` remain `| sanitize` (scanner-derived).

3. **Jinja2 attribute-or-item-lookup for RoadmapItem** — Template uses `item.title`, `item.why`, `item.effort`, `item.impact` which Jinja2 resolves via `getattr` first then item lookup. This works for both `RoadmapItem` dataclass objects (attribute access) and backward-compat raw dict items (item lookup). The `{% if item.effort is defined and item.effort %}` guard prevents priority-label rendering on raw dicts that lack the attribute.

4. **top_risks static-string template rendering** — `risk.risk_label` and `risk.impact_sentence` from ALGO_IMPACT_MAP are fully static strings from our code (not scanner input). No `| sanitize` applied in template — consistent with the "static prose unsanitized" rule from RESEARCH Pitfall 5.

5. **Backward-compat None path in both renderers** — Both `build_exec_markdown(exec_content=None)` and `render_html_report(exec_content=None)` work correctly for callers that don't yet pass exec_content; they fall back to their pre-98-02 behavior.

## Deviations from Plan

None. Plan executed exactly as written. One refinement applied: `narrative_lead | safe` in the template (Rule 1 auto-fix — autoescape was producing incorrect output for static prose with apostrophes). This is not a bug in scanner-controlled content but in the handling of trusted static strings; `| safe` is the correct Jinja2 idiom.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes introduced.

Trust boundary adherence:
- `narrative_drivers` (score_raw["drivers"] — scanner-derived) piped through `| sanitize` in template
- `top_risks` items (from ALGO_IMPACT_MAP — static strings) rendered without sanitize (not scanner input)
- `narrative_lead` (from `_NARRATIVE_LEADS` — static strings) rendered with `| safe` (not scanner input)
- md_cell applied to all roadmap/risk finding-derived text in executive.py new sections (HARDEN-01)
- T-98-03 (markdown cell injection): risk_label/impact_sentence are static map values, not raw finding text; md_cell applied per HARDEN-01 for belt-and-suspenders
- T-98-04 (HTML injection): narrative_drivers sanitized; static prose uses safe/no-filter
- T-98-05 (contradictory report): guard fires in writer.py before exec_md is written; integration test confirms

## Self-Check

Files created:
- `tests/test_exec_narrative_ordering.py`: FOUND
- `.planning/phases/98-executive-narrative-score-transparency/98-02-SUMMARY.md`: FOUND

Files modified:
- `quirk/reports/writer.py`: FOUND
- `quirk/reports/executive.py`: FOUND
- `quirk/reports/html_renderer.py`: FOUND
- `quirk/reports/templates/report.html.j2`: FOUND
- `tests/test_congruence_guard.py`: FOUND

Commits:
- `c9ecd54` feat(98-02): writer seam + congruence guard integration + CLI narrative/risks/roadmap: FOUND
- `f6703d1` feat(98-02): HTML renderer + template narrative/risks/rollup/priority + ordering tests: FOUND

## Self-Check: PASSED
