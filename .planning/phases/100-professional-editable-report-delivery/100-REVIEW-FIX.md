---
phase: 100-professional-editable-report-delivery
fixed_at: 2026-05-24T00:00:00Z
review_path: .planning/phases/100-professional-editable-report-delivery/100-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 100: Code Review Fix Report

**Fixed at:** 2026-05-24
**Source review:** `.planning/phases/100-professional-editable-report-delivery/100-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 4 (CR-01, CR-02, WR-01, WR-02)
- Fixed: 4
- Skipped: 0

---

## Fixed Issues

### CR-01: Unbounded file read in `_load_logo_b64` — memory exhaustion on large or adversarial logo_path

**Files modified:** `quirk/reports/html_renderer.py`, `tests/test_html_report.py`
**Commit:** 34ffbd5
**Applied fix:**
- Added `_MAX_LOGO_BYTES = 5 * 1024 * 1024` module-level constant (5 MB limit).
- Added `os.path.getsize(logo_path)` pre-read check: if size exceeds the limit, print a stderr advisory and return `(None, "png")` immediately — no file read happens.
- Widened the except clause from `except (OSError, IOError)` to `except Exception` so `MemoryError`, `ValueError`, and any other non-OS failure path cannot escape the function and propagate into `render_html_report`. Honors the D-03 graceful-omit contract completely.
- Added three new tests to `tests/test_html_report.py`:
  - `test_logo_missing_path_returns_none` — nonexistent path returns `(None, 'png')`.
  - `test_logo_none_path_returns_none` — `None` logo_path returns `(None, 'png')`.
  - `test_logo_oversized_returns_none` — oversized file returns `(None, 'png')` with stderr advisory (limit monkeypatched to 10 bytes).

### CR-02: Unguarded `doc.save(path)` in `render_docx_report` — DOCX write failure propagates through `write_reports`

**Files modified:** `quirk/reports/docx_renderer.py`, `quirk/reports/writer.py`, `tests/test_docx_report.py`
**Commits:** 583df60 (main fix), 9ae4495 (corrected test monkeypatch target)
**Applied fix:**
- `docx_renderer.py`: Wrapped `doc.save(path)` in `try/except Exception as e`. On failure, prints stderr advisory (`"DOCX export failed while writing {path}: {e}"`) and returns `False`. Honors D-11 contract: any DOCX failure returns `False`, never aborts `write_reports`.
- `writer.py`: Added belt-and-suspenders outer `try/except Exception` around the `render_docx_report(...)` call site. Any exception that escapes the renderer before `doc.save` cannot abort CBOM generation or run-stats flush. The `import sys` inside the except clause uses a local alias (`_sys`) to avoid shadowing the existing module-level imports.
- `tests/test_docx_report.py`: Added `test_docx_save_failure_returns_false`. Monkeypatches `docx.document.Document.save` (the real class, not the `docx.Document` factory function) to raise `OSError("No space left on device")`; asserts `render_docx_report` returns `False` and that `"DOCX export failed"` appears in stderr.

### WR-01: `_load_logo_b64` catches redundant `(OSError, IOError)` — narrow exception set

**Files modified:** `quirk/reports/html_renderer.py` (same edit as CR-01)
**Commit:** 34ffbd5
**Applied fix:** Subsumed by CR-01. The widening of the except clause to `except Exception` resolves both the redundancy and the narrow-catch intent. No separate change required.

### WR-02: `render_docx_report` success log writes to stdout instead of stderr

**Files modified:** `quirk/reports/docx_renderer.py` (same edit as CR-02)
**Commit:** 583df60
**Applied fix:** Changed `print(f"DOCX report written to {path}")` to `print(f"DOCX report written to {path}", file=sys.stderr)`. This mirrors the PDF failure advisory convention in `html_renderer.py` (line 354) and is consistent with the DOCX failure advisory at line 78 that already targeted stderr.

---

## Skipped Issues

None — all four in-scope findings were fixed.

---

## Test Results

All 30 tests in the four required files pass after fixes:

```
tests/test_html_report.py        13 passed
tests/test_docx_report.py         8 passed  (7 pre-existing + 1 new)
tests/test_reports_writer.py      6 passed
tests/test_cross_surface_parity.py 3 passed
TOTAL: 30 passed
```

`python -m compileall` passes for all three modified source files.

---

_Fixed: 2026-05-24_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
