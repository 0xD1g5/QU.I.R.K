---
phase: 100-professional-editable-report-delivery
plan: "02"
subsystem: reports
tags: [fmt, docx, word, editable-report, optional-extra, cross-surface-parity]
dependency_graph:
  requires: [100-01]
  provides: [FMT-03]
  affects:
    - quirk/reports/docx_renderer.py
    - quirk/reports/writer.py
    - pyproject.toml
    - tests/test_docx_report.py
    - tests/test_reports_writer.py
    - tests/test_cross_surface_parity.py
    - docs/UAT-SERIES.md
tech_stack:
  added: [python-docx>=1.1.0 (optional extra [docx])]
  patterns:
    - optional-extra-lazy-import
    - graceful-skip-return-bool
    - double-getattr-cfg-access
    - single-content-pipeline (D-10)
    - tdd-red-green
key_files:
  created:
    - quirk/reports/docx_renderer.py
    - tests/test_docx_report.py
  modified:
    - quirk/reports/writer.py
    - pyproject.toml
    - tests/test_reports_writer.py
    - tests/test_cross_surface_parity.py
    - docs/UAT-SERIES.md
decisions:
  - "python-docx lazy-imported inside render_docx_report body only (optional-extra import trap prevention)"
  - "Table Grid style assigned defensively — KeyError/exception falls back to default (research A3)"
  - "DOCX derives from same exec_content pipeline as HTML/CLI — no parallel doc construction (D-10)"
  - "docx_path added to output_files list with existing None-filter pattern (no new code needed)"
  - "python-docx added to [all] extra since DOCX auto-emits every run (D-11, no dep conflict)"
metrics:
  duration: "~30 minutes"
  completed: "2026-05-24"
  tasks_completed: 3
  files_changed: 7
---

# Phase 100 Plan 02: DOCX Editable Report Export Summary

**One-liner:** DOCX auto-emit every report run via render_docx_report — structural Word document (cover/exec/findings/roadmap/score, Heading 1/2, native tables, logo placeholder) derived from the shared exec_content pipeline, gated behind [docx] optional extra with graceful skip.

## What Was Built

### Task 1: docx_renderer.py — structural DOCX from shared content model + graceful skip

Created `quirk/reports/docx_renderer.py` as the analog to `html_renderer.py`. The module:

- Exports `render_docx_report(path, cfg, findings, exec_content=None) -> bool`
- Lazy-imports `from docx import Document` inside the function body — never module-level (optional-extra import trap prevention, T-100-DEP)
- On `ImportError`: prints verbatim advisory `"DOCX export skipped: python-docx is not installed. Install with: pip install quirk-scanner[docx]"` to `sys.stderr`, returns `False`
- Routes content through `exec_content` when present (D-10 single pipeline — narrative_lead, narrative_drivers, top_risks, roadmap NOW/NEXT/LATER, subscores); falls back to empty when `None`
- Builds document in the exact layout order from 100-UI-SPEC.md: logo placeholder paragraph (verbatim `"[ Insert organization logo here ]"`), Heading 1/2 title/org, metadata Normal line, Executive Summary (narrative + Score Decomp + Priority Risks + Top Findings sub-tables), Findings 7-col table, Remediation Roadmap NOW/NEXT/LATER with 4-col tables, Score Breakdown section
- `_set_table_style()` helper: assigns `'Table Grid'` defensively — any `KeyError` or style error falls back silently (research A3)
- `os.makedirs` before `doc.save`, prints `"DOCX report written to {path}"`, returns `True`

TDD RED commit: `910b6cd` — 7 failing tests
TDD GREEN commit: `4895c97` — 7 passing tests + implementation

### Task 2: Wire DOCX into write_reports + [docx] extra + parity/writer tests

**`quirk/reports/writer.py`:**
- Added `from quirk.reports.docx_renderer import render_docx_report` import (line 22)
- DOCX auto-emit block after `render_pdf_report` (D-11): `docx_path = os.path.join(outdir, f"report-{stamp}.docx")`, `docx_ok = render_docx_report(...)`, `if not docx_ok: docx_path = None`
- `docx_path` added to `output_files` list; existing `if p` filter handles `None` when skipped

**`pyproject.toml`:**
- Added `docx = ["python-docx>=1.1.0"]` under `[project.optional-dependencies]`
- Added `"quirk-scanner[docx]"` to `[all]` (D-11 auto-emit justifies bundling with full installs; no dep conflict)

**`tests/test_reports_writer.py`:**
- `test_docx_emitted_by_write_reports`: asserts `report-*.docx` exists after `write_reports`
- `test_docx_none_on_fail_not_in_output_files`: mocks `render_docx_report` returning `False`, asserts no `.docx` file created

**`tests/test_cross_surface_parity.py`:**
- `test_docx_narrative_parity`: builds one `ExecContent`, renders CLI/HTML/DOCX, asserts `narrative_lead` present in all three — D-10 single pipeline cross-surface gate

TDD RED commit: `00b5afd` — 2 failing writer tests + 1 already-passing parity test
TDD GREEN commit: `35d22b1` — all 9 tests passing

### Task 3: Update docs/UAT-SERIES.md + sync to Obsidian

Updated `docs/UAT-SERIES.md`:
- Bumped `**Version:**` to `5.2.0`
- Updated `**Last Updated:**` with Phase 100 completion summary
- Added `# Series 100` section with UAT-100-01..04:
  - UAT-100-01: PDF cover page automated + manual visual check (FMT-01)
  - UAT-100-02: PDF pagination — no overflow, no split rows, headers repeat (FMT-02)
  - UAT-100-03: DOCX auto-emits, opens in Word/Google Docs, editable (FMT-03 manual)
  - UAT-100-04: DOCX graceful skip + full automated gate suite (FMT-03 automated)

Synced to Obsidian vault: `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md` with frontmatter prepended.

Commit: `f3e5392`

## Verification

```
python -m pytest tests/test_docx_report.py tests/test_reports_writer.py tests/test_cross_surface_parity.py -q
16 passed in 1.89s

python -m compileall quirk/reports/docx_renderer.py quirk/reports/writer.py
(no errors)

python -m pytest tests/test_html_report.py tests/test_docx_report.py tests/test_reports_writer.py -q
23 passed in 1.93s

grep -v '^#' quirk/reports/docx_renderer.py | grep -c "from docx import Document"
1  (only inside function body — minimal-install safe)

grep -q "docx" docs/UAT-SERIES.md && echo OK
OK

ls "/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md"
/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md  (531596 bytes, 2026-05-24)
```

Acceptance criteria verified:
- `quirk/reports/docx_renderer.py` exports `render_docx_report(path, cfg, findings, exec_content=None) -> bool`
- `from docx import Document` appears exactly 1 time, only inside function body
- First DOCX paragraph is exactly `"[ Insert organization logo here ]"`
- DOCX has Heading-1 sections: Executive Summary / Findings / Remediation Roadmap / Score Breakdown
- First findings table has 7 columns with locked header order
- `test_docx_graceful_skip` asserts False + stderr advisory when docx absent
- `writer.py` imports `render_docx_report` and calls it after `render_pdf_report` with `exec_content`
- `docx_path` appended to output_files list
- `pyproject.toml` has `docx = ["python-docx>=1.1.0"]` and `"quirk-scanner[docx]"` in `[all]`
- `test_docx_narrative_parity` asserts `narrative_lead` present in DOCX
- docs/UAT-SERIES.md mentions DOCX export; Obsidian vault copy in sync

## Deviations from Plan

None — plan executed exactly as written. The graceful-skip tests required re-importing `quirk.reports.docx_renderer` after patching `sys.modules["docx"] = None`, which is standard monkeypatch pattern and handled in the test setup with module cache clearing.

## Known Stubs

None — all document content wires through live `exec_content` (when provided) or falls back to empty-state messages. The logo placeholder `"[ Insert organization logo here ]"` is intentional per D-12 (consultant inserts logo before client handoff).

## Threat Flags

No new threat surface beyond the plan's declared threat model (T-100-DEP, T-100-DOCX, T-100-SC — all addressed).

## Self-Check: PASSED

- quirk/reports/docx_renderer.py exists: FOUND
- quirk/reports/writer.py imports render_docx_report: FOUND
- pyproject.toml has `docx = ["python-docx>=1.1.0"]`: FOUND
- tests/test_docx_report.py exists: FOUND
- tests/test_cross_surface_parity.py has test_docx_narrative_parity: FOUND
- docs/UAT-SERIES.md mentions DOCX and UAT-100: FOUND
- /Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md exists: FOUND
- Commits 910b6cd, 4895c97, 00b5afd, 35d22b1, f3e5392: all in git log
