---
phase: 73-cbom-intel-reports-warnings
plan: 01
subsystem: reports
tags: [pdf, playwright, hardening, intel-01, wr-01, wr-02, wr-14]
requires: [quirk.util.safe_exc.safe_str, playwright.sync_api]
provides: [hardened render_pdf_report, stderr PDF advisory contract]
affects: [quirk/reports/html_renderer.py, tests/test_pdf_render_hardening.py, tests/test_reports_writer.py, .planning/audit-2026-05-08/AUDIT-TASKS.md]
tech_stack_added: []
patterns: [narrowed-except, try/finally cleanup, safe_str advisory, callee-emit advisory]
key_files_created:
  - tests/test_pdf_render_hardening.py
key_files_modified:
  - quirk/reports/html_renderer.py
  - tests/test_reports_writer.py
  - .planning/audit-2026-05-08/AUDIT-TASKS.md
decisions:
  - D-01 sync-API translation (drop asyncio.TimeoutError, use playwright.sync_api.TimeoutError; no explicit context object — RESEARCH C-2)
  - D-01a satisfied by existing [dashboard]-gated ImportError (RESEARCH C-7); no pyproject.toml change
  - WR-14 advisory emitted from callee (html_renderer.py), not writer.py — both `e` and `html_path` in scope (RESEARCH C-3)
metrics:
  duration_minutes: 6
  tasks_completed: 3
  tests_added: 8
  audit_rows_closed: 3
completed: 2026-05-15
---

# Phase 73 Plan 01: INTEL-01 PDF Render Hardening Summary

Hardens `quirk/reports/html_renderer.py::render_pdf_report` against blanket-except masking,
Playwright chromium subprocess leaks, and silent PDF-failure UX — closes WR-01, WR-02, WR-14.

## What Was Built

### Task 1 — Narrowed except + try/finally + stderr advisory (commit e06febf)

`quirk/reports/html_renderer.py:105-138` — `render_pdf_report` restructured:

- Added second import line under the existing `try: from playwright.sync_api import sync_playwright` ImportError guard:
  `from playwright.sync_api import Error as PlaywrightError, TimeoutError as PlaywrightTimeoutError`
- `browser = None` initialized before the inner `try` so the `finally` can probe safely
- Inner `try` body unchanged except `browser.close()` removed from the success path (now lives only in `finally`)
- Inner `except Exception: return False` replaced with `except (PlaywrightError, PlaywrightTimeoutError, OSError, RuntimeError) as e:` — programmer bugs (e.g. KeyError) now propagate
- The narrowed except emits the WR-14 advisory verbatim per D-01:
  `print(f"PDF generation failed: {safe_str(e)}; scan complete, HTML report at {html_path}", file=sys.stderr)`
- New `finally:` block calls `if browser is not None: try: browser.close() except Exception: pass` — defensive cleanup that never masks the original failure

Module-top imports also added: `import sys` and `from quirk.util.safe_exc import safe_str`.

D-01a (ImportError fallback) preserved verbatim — the existing `[dashboard]`-gated guard satisfies the discretion point (RESEARCH C-7; the `[reports]` extra in CONTEXT D-01a does not exist).

### Task 2 — RED-then-GREEN coverage (commit 98c2e29)

`tests/test_pdf_render_hardening.py` (new, 7 tests):

1. `test_render_pdf_returns_false_on_playwright_error` — PlaywrightError caught, advisory in stderr
2. `test_render_pdf_returns_false_on_runtime_error` — RuntimeError in narrowed tuple
3. `test_render_pdf_returns_false_on_os_error` — OSError in narrowed tuple
4. `test_render_pdf_propagates_unexpected_exception` — **WR-01 RED-then-GREEN negative case**: KeyError propagates, proving blanket-except is gone
5. `test_render_pdf_closes_browser_in_finally` — WR-02 GREEN: `browser.close()` invoked on inner-raise
6. `test_render_pdf_close_failure_does_not_mask` — defensive close-time `try/except Exception: pass` validated
7. `test_render_pdf_import_error_returns_false` — D-01a preserved: ImportError → False, no stderr advisory

`tests/test_reports_writer.py` extended with `test_pdf_failure_advisory_propagates_via_writer` — verifies writer remains stable on `pdf_ok=False` and the callee-emitted advisory observable in stderr from the writer flow.

Mock idiom: installs a fake `playwright.sync_api` module in `sys.modules` exposing
`sync_playwright`, `Error`, `TimeoutError` so the in-function `from playwright.sync_api import …`
resolves to controllable mocks/real Exception subclasses (mirrors `tests/test_pdf_export.py`).

### Task 3 — Audit rows flipped (commit 9a19ada)

`.planning/audit-2026-05-08/AUDIT-TASKS.md` lines 149, 150, 162 flipped to `Phase 73 | [x] closed`
with per-row evidence (D-01 cite, RESEARCH C-2/C-3 rationale, test references).

## Decisions Made

| ID | Decision | Source |
|----|----------|--------|
| D-01 (translated) | Sync-API exception tuple `(PlaywrightError, PlaywrightTimeoutError, OSError, RuntimeError)` — `asyncio.TimeoutError` unreachable in sync path | CONTEXT D-01 + RESEARCH C-2 |
| Callee-emit advisory | Print from `html_renderer.py` not `writer.py` — both `e` and `html_path` already in scope | RESEARCH C-3 |
| D-01a no-op | Existing `[dashboard]`-gated ImportError already satisfies the pattern; the `[reports]` extra cited in CONTEXT does not exist | RESEARCH C-7 |
| Defensive close in finally | Inner `try/except Exception: pass` around `browser.close()` so close-time errors never mask original failure | CONTEXT D-01 |

## Deviations from Plan

None — plan executed exactly as written. RESEARCH C-2, C-3, C-7 adjudications applied as
prescribed; no decision changes.

## Verification

- `python -m compileall quirk/reports/html_renderer.py` — clean
- `pytest tests/test_pdf_render_hardening.py tests/test_reports_writer.py -x` — 11 passed (7 new + 4 existing writer tests)
- `pytest tests/test_safe_exc.py -x` — 8 passed (safe_str unit tests; project has no `tests/test_safe_exc_gate.py` despite plan reference)
- Audit acceptance: `grep -cE "cbom-intel-reports/WR-(01|02|14).*Phase 73.*\[x\] closed"` = 3
- Other WR rows untouched: `grep -cE "cbom-intel-reports/WR-(03|04|06|07|08|09|10|11|12|13).*\[ \] open"` = 10

## Commits

| Hash    | Type | Description |
|---------|------|-------------|
| e06febf | fix  | Narrow PDF render except + finally cleanup + stderr advisory |
| 98c2e29 | test | PDF render hardening coverage (7 new tests + 1 writer test) |
| 9a19ada | docs | Flip WR-01, WR-02, WR-14 audit rows to Phase 73 closed |

## Self-Check: PASSED

- FOUND: quirk/reports/html_renderer.py (modified, all acceptance greps pass)
- FOUND: tests/test_pdf_render_hardening.py (7 test functions)
- FOUND: tests/test_reports_writer.py::test_pdf_failure_advisory_propagates_via_writer
- FOUND: e06febf, 98c2e29, 9a19ada in git log
- FOUND: 3 audit rows flipped with per-row evidence
