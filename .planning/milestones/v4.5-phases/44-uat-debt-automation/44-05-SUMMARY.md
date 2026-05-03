---
phase: 44-uat-debt-automation
plan: "05"
subsystem: dashboard-pdf-accessibility
tags: [bug-fix, pdf-export, accessibility, python, tsx]
dependency_graph:
  requires: [44-CONTEXT.md, phase-43-continue-here]
  provides: [CR-02-fix, WR-01-fix, WR-03-fix, WR-04-fix]
  affects: [quirk/dashboard/api/routes/pdf.py, src/dashboard/src/pages/print.tsx, src/dashboard/src/pages/data-at-rest.tsx, src/dashboard/src/pages/motion.tsx]
tech_stack:
  added: []
  patterns: [try/except ValueError with structured 500 JSON, playwright finally-block cleanup, WCAG scope="col" accessibility attribute]
key_files:
  modified:
    - quirk/dashboard/api/routes/pdf.py
    - src/dashboard/src/pages/print.tsx
    - src/dashboard/src/pages/data-at-rest.tsx
    - src/dashboard/src/pages/motion.tsx
decisions:
  - "CR-02: surfaces QUIRK_SERVE_PORT misconfiguration via 500 JSON (no silent fallback) per D-09"
  - "WR-01: browser.close() in finally guarantees Playwright browser release on any exception path"
  - "WR-04 verification: grep -c '<TableHead' counts include <TableHeader lines (4 extra in DAR, 2 extra in motion); actual TableHead-specific counts are 35/35 and 13/13 — plan verification script has pre-existing off-by-N but all actual fixes are correct"
metrics:
  duration: "~10 minutes"
  completed: "2026-05-03"
  tasks: 3
  files: 4
---

# Phase 44 Plan 05: CR-02 + WR-01 + WR-03 + WR-04 Bug Fix Summary

**One-liner:** Four Phase 43 code-review findings resolved: structured ValueError response on bad QUIRK_SERVE_PORT, guaranteed Playwright browser cleanup via finally, data_in_motion 6th subscore in PDF executive summary, and WCAG scope="col" on all 48 TableHead elements across two pages.

## What Was Built

### Task 1: pdf.py CR-02 + WR-01 (commit 4c8a488)

**CR-02 — ValueError on bad QUIRK_SERVE_PORT:**
- Wrapped `int(os.environ.get("QUIRK_SERVE_PORT", "8512"))` in a `try/except ValueError` block
- Returns `HTTP 500` with JSON body `{"detail": "QUIRK_SERVE_PORT is not a valid integer."}` on bad value
- No silent fallback to default — misconfiguration is surfaced clearly (per D-09)
- `json` and `Response` were already imported; no new imports needed

**WR-01 — browser.close() in finally:**
- Restructured playwright block: `browser.close()` moved from inline (after `page.pdf()`) to a `finally:` block wrapping context/page operations
- Guarantees browser release even if `page.goto`, `page.wait_for_selector`, or `page.pdf` raises
- Outer `try/except Exception` wrapper for playwright install errors preserved unchanged
- Sentinel selector `body[data-ready="true"]` preserved unchanged from Phase 43

**Verification:**
- `python -m py_compile`: passes
- `grep -c 'except ValueError:' pdf.py`: 1
- `grep -q 'QUIRK_SERVE_PORT is not a valid integer.'`: match
- `grep -c 'finally:'`: 1
- `awk '/finally:/{flag=1; next} flag && /browser.close\(\)/{print "OK"; exit}'`: OK
- `python -m pytest tests/test_pdf_export.py -q`: 2 passed

### Task 2: print.tsx WR-03 (commit c56a41c)

**WR-03 — data_in_motion 6th subscore in PDF executive summary:**
- Inserted `data_in_motion` score-item block after the `data_at_rest` block in the `score-row` div
- Exact JSX shape mirrors existing blocks: `score-item > score-number + score-label`
- Label text: `"Data in Motion"`
- Source order: data_at_rest at line 221, data_in_motion immediately after

**Verification:**
- `grep -q '{score.subscores.data_in_motion}'`: match
- `grep -q 'Data in Motion'`: match
- awk ordering check (data_in_motion appears after data_at_rest): OK
- `tsc --noEmit`: Exit 0 (clean)

### Task 3: data-at-rest.tsx + motion.tsx WR-04 (commit a7fbe33)

**WR-04 — scope="col" on every TableHead:**
- `data-at-rest.tsx`: 35/35 `<TableHead>` elements now carry `scope="col"`
  - 4 TableHeader blocks: DB engines (9), Object Storage (10), Kubernetes (8), Vault (8)
  - No `<TableHead className=` (without scope) remains
- `motion.tsx`: 13/13 `<TableHead>` elements now carry `scope="col"`
  - 2 TableHeader blocks: TLS endpoints (7), Broker grouped (6)
  - No `<TableHead className=` (without scope) remains

**Note on verification counts:** The plan's automated grep uses `grep -c "<TableHead"` which also matches `<TableHeader>` lines, resulting in totals of 39/35 for data-at-rest and 15/13 for motion. The correct count using `grep -c "<TableHead[^e]"` confirms 35/35 and 13/13. All actual `<TableHead` (not `<TableHeader>`) elements have `scope="col"`. This is a pre-existing issue in the plan's verification script.

**Verification:**
- `grep -c "<TableHead[^e]" data-at-rest.tsx`: 35; `grep -c '<TableHead scope="col"' data-at-rest.tsx`: 35 — match
- `grep -c "<TableHead[^e]" motion.tsx`: 13; `grep -c '<TableHead scope="col"' motion.tsx`: 13 — match
- `grep '<TableHead className=' data-at-rest.tsx | wc -l`: 0
- `grep '<TableHead className=' motion.tsx | wc -l`: 0
- `tsc --noEmit`: Exit 0 (clean)

## Deferred Items

**WR-05 and WR-06 remain explicitly deferred per D-10.** These were out of scope for this plan and have not been touched.

## Test Results

```
python -m pytest tests/test_pdf_export.py -q
2 passed in 0.19s

python -m pytest tests/ -m 'not slow' -q
19 failed (pre-existing), 699 passed, 16 deselected, 70 warnings
```

The 19 failures are pre-existing in `test_cbom_schema_validation.py` (CBOM profile validation issues, tracked as Phase 42 OBS-1 in MEMORY.md) and `test_cli_correctness.py::test_no_quirk_scan_references`. None are caused by the changes in this plan.

## TSC Verification Status

`tsc --noEmit` ran successfully from `src/dashboard` using the project's local `./node_modules/.bin/tsc`. Exit code 0 — no TypeScript errors. Verified after both Task 2 (print.tsx) and Task 3 (data-at-rest.tsx + motion.tsx).

## Threat Model Compliance

| Threat ID | Mitigation Applied |
|-----------|-------------------|
| T-44-05-01 | CR-02: ValueError caught, returns structured 500 JSON — no stack trace leakage |
| T-44-05-02 | WR-01: browser.close() in finally — no playwright browser leak on exception |
| T-44-05-03 | WR-04: scope="col" on all 48 TableHead elements (35 + 13) — WCAG compliance |
| T-44-05-04 | Sentinel `body[data-ready="true"]` preserved — confirmed via grep |

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | 4c8a488 | fix(44-05): CR-02 + WR-01 — ValueError on bad port, browser.close in finally |
| 2 | c56a41c | fix(44-05): WR-03 — add data_in_motion 6th subscore to PDF executive summary |
| 3 | a7fbe33 | fix(44-05): WR-04 — scope="col" on every TableHead for accessibility |

## Self-Check

- [x] quirk/dashboard/api/routes/pdf.py — modified, committed 4c8a488
- [x] src/dashboard/src/pages/print.tsx — modified, committed c56a41c
- [x] src/dashboard/src/pages/data-at-rest.tsx — modified, committed a7fbe33
- [x] src/dashboard/src/pages/motion.tsx — modified, committed a7fbe33

## Self-Check: PASSED
