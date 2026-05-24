---
phase: 100-professional-editable-report-delivery
reviewed: 2026-05-24T00:00:00Z
depth: standard
files_reviewed: 6
files_reviewed_list:
  - quirk/config.py
  - quirk/reports/html_renderer.py
  - quirk/reports/templates/report.html.j2
  - quirk/reports/docx_renderer.py
  - quirk/reports/writer.py
  - pyproject.toml
findings:
  critical: 2
  warning: 2
  info: 3
  total: 7
status: issues_found
fixed:
  - CR-01
  - CR-02
  - WR-01
  - WR-02
fixed_at: 2026-05-24T00:00:00Z
fix_commits:
  - 34ffbd5  # CR-01: size guard + widen except in _load_logo_b64
  - 583df60  # CR-02/WR-02: guard doc.save, belt-and-suspenders in writer, stderr success log
  - 9ae4495  # fix test monkeypatch target
---

# Phase 100: Code Review Report

**Reviewed:** 2026-05-24
**Depth:** standard
**Files Reviewed:** 6
**Status:** issues_found

## Summary

Phase 100 adds a branded PDF cover page with base64-embedded logo, print-pagination CSS, and a
new DOCX editable report export. The optional-extra import pattern for python-docx is correctly
implemented (lazy import inside function body; writer.py module-level import of the module
itself is safe because no top-level `from docx import` exists in docx_renderer.py). The
Jinja2 autoescaping + sanitize filter chain is correctly ordered. Two correctness/security
issues require fixes before ship: an unbounded file read in `_load_logo_b64` that will exhaust
memory on a misconfigured or adversarial `logo_path`, and an unguarded `doc.save` call in
`render_docx_report` that allows a DOCX write failure to abort CBOM generation and run-stats
flush by propagating out of `write_reports`.

---

## Critical Issues

### CR-01: Unbounded file read in `_load_logo_b64` — memory exhaustion on large or adversarial logo_path

**File:** `quirk/reports/html_renderer.py:156`
**Issue:** `f.read()` reads the entire file at `logo_path` into memory with no size limit.
`logo_path` is operator-supplied via `config.yaml` (a file path string). A misconfiguration
pointing at a multi-GB file (e.g., a disk image, a VM snapshot, a database dump) will load the
entire file into RAM, then base64-encode it (+33% overhead), then embed it in the rendered HTML
string, then pass that HTML to Chromium for PDF rendering. On a resource-constrained scan host
this causes an OOM crash of the scan process. Additionally, neither `MemoryError` (raised by
`f.read()` or `base64.b64encode()` when allocation fails) nor any exception other than
`OSError`/`IOError` is caught — so a `MemoryError` escapes the try/except, propagates through
`render_html_report`, and aborts `write_reports` (killing CBOM and run-stats flush along
with it).

The D-03 guarantee ("failure degrades to graceful-omit, no exception escapes") is broken for
the MemoryError path and for any other non-OS exception that `f.read()` or
`base64.b64encode()` can raise.

**Fix:** Add a file-size guard before reading and widen the except to catch `Exception`:

```python
_MAX_LOGO_BYTES = 5 * 1024 * 1024  # 5 MB — generous for any real logo file

def _load_logo_b64(logo_path):
    """Return (b64_string, mime_subtype) or (None, 'png') when logo absent/unreadable.

    Phase 100 / D-01 / D-03: base64-embed for offline HTML; None means omit logo region.
    T-100-LOGO: guards against missing/invalid/permission/large-file errors (graceful omit).
    """
    if not logo_path:
        return None, "png"
    try:
        size = os.path.getsize(logo_path)
        if size > _MAX_LOGO_BYTES:
            print(
                f"Logo at {logo_path!r} exceeds size limit ({size} bytes > {_MAX_LOGO_BYTES}); "
                "logo omitted from report.",
                file=sys.stderr,
            )
            return None, "png"
        with open(logo_path, "rb") as f:
            data = f.read()
        b64 = base64.b64encode(data).decode("ascii")
        ext = os.path.splitext(logo_path)[1].lower().lstrip(".")
        mime = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png",
                "gif": "gif", "svg": "svg+xml"}.get(ext, "png")
        return b64, mime
    except Exception:
        return None, "png"
```

Note: `os.path.getsize` can itself raise `OSError` for permission-denied paths — covered by the
widened `except Exception`.

---

### CR-02: Unguarded `doc.save(path)` in `render_docx_report` — DOCX write failure propagates through `write_reports` aborting CBOM and run-stats

**File:** `quirk/reports/docx_renderer.py:282` and `quirk/reports/writer.py:243-250`
**Issue:** `doc.save(path)` at line 282 of `docx_renderer.py` is not wrapped in a try/except.
If the save fails — due to a full filesystem, a permissions error on the output directory, or
any internal python-docx exception — the exception propagates out of `render_docx_report`
into `write_reports` at line 243. Because `write_reports` also has no try/except around the
DOCX call, the exception terminates the function entirely, skipping:
- `run_stats["timings_sec"]["reporting"]` flush (line 253)
- `run_stats.setdefault("partial_failures", [])` (line 256)
- CBOM generation via `build_cbom` / `write_cbom_files` (lines 265-268)
- The Rich scan summary table printout (lines 271-314)

HTML and PDF artifacts are already written at this point (lines 225-239), but the CBOM — a
primary deliverable — is silently lost when DOCX save fails. The docx "graceful skip" contract
(D-11) requires returning `False` + advisory on failure, not propagating exceptions.

**Fix — two changes required:**

`quirk/reports/docx_renderer.py` — wrap the save:
```python
    # ---------------------------------------------------------------------------
    # Save document
    # ---------------------------------------------------------------------------
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
    try:
        doc.save(path)
    except Exception as e:
        print(
            f"DOCX export failed while writing {path}: {e}",
            file=sys.stderr,
        )
        return False
    print(f"DOCX report written to {path}")
    return True
```

`quirk/reports/writer.py` — belt-and-suspenders outer guard (handles any future exception
that escapes render_docx_report before the save):
```python
    try:
        docx_ok = render_docx_report(
            path=docx_path,
            cfg=cfg,
            findings=findings,
            exec_content=exec_content,
        )
    except Exception as e:
        print(f"DOCX export failed unexpectedly: {e}", file=sys.stderr)
        docx_ok = False
    if not docx_ok:
        docx_path = None
```

---

## Warnings

### WR-01: `_load_logo_b64` catches redundant `(OSError, IOError)` — masking exception set is narrower than declared

**File:** `quirk/reports/html_renderer.py:163`
**Issue:** In Python 3, `IOError` is a type alias for `OSError`. The tuple `(OSError, IOError)`
is redundant and signals that the author was uncertain about the exception hierarchy. More
importantly, as documented in CR-01, the narrow `OSError`-family catch leaves `MemoryError`,
`ValueError`, and any internal `base64` or `os.path` exception uncaught. This finding is
subsumed by CR-01 but called out separately because the redundancy signals the intent was to
catch broadly — yet the implementation does not.

**Fix:** After applying the CR-01 fix (widening to `except Exception`), this redundancy is
automatically resolved. If the broader fix is rejected, at minimum remove the redundant
`IOError`:
```python
    except OSError:
        return None, "png"
```

---

### WR-02: `render_docx_report` success log writes to stdout instead of stderr — inconsistent with all other report-path log lines

**File:** `quirk/reports/docx_renderer.py:283`
**Issue:** `print(f"DOCX report written to {path}")` writes to stdout. All equivalent report
artifact log lines in `html_renderer.py` write to `sys.stderr` (e.g., the PDF failure message
at line 355, and the PDF metadata injection is silent). The `write_reports` Rich console output
goes to stdout, but single-artifact "written to" advisory messages conventionally go to stderr
in CLI tools so they can be redirected or suppressed independently of scan data.

Additionally, the DOCX advisory `"DOCX export skipped: ..."` at line 78 correctly goes to
`sys.stderr`, making the success path inconsistent with the failure path.

**Fix:**
```python
    print(f"DOCX report written to {path}", file=sys.stderr)
```

---

## Info

### IN-01: `except (OSError, IOError)` — Python 3 redundancy

**File:** `quirk/reports/html_renderer.py:163`
**Issue:** `IOError` is an alias for `OSError` in Python 3.3+. The two-element tuple catches
the same exception class twice. This is dead code in the exception specification.
**Fix:** Use `except OSError:` only. (Subsumed by WR-01 / CR-01 fix.)

---

### IN-02: `_SUBSCORE_LABELS` duplicated in `docx_renderer.py` and `writer.py`

**File:** `quirk/reports/docx_renderer.py:25-32` and `quirk/reports/writer.py:84-91`
**Issue:** The same six-element `_SUBSCORE_LABELS` list is defined identically in both modules.
This is a two-location maintenance hazard: if a seventh subscore is added, only one module may
be updated. `html_renderer.py` accesses subscores directly via `subscores.get(key)` in the
Jinja2 template, not through this list.
**Fix:** Extract to `quirk/reports/content_model.py` (or a new `quirk/reports/_subscore_labels.py`
constants module) and import from both call sites. Tag with a note about the subscore budget
(currently all `/25`).

---

### IN-03: `print(f"DOCX report written to {path}")` — missing `safe_str` wrapper on user-influenced path

**File:** `quirk/reports/docx_renderer.py:283`
**Issue:** The path value is constructed from `cfg.output.directory` (operator config) and a
timestamp, so it is not direct user input. However, the rest of the codebase consistently uses
`safe_str(e)` when printing exception messages and operator-supplied strings to stderr (see
`html_renderer.py:355`). The inconsistency is minor — no injection risk in a terminal print
context — but worth flagging for pattern compliance.
**Fix:** Not critical. If WR-02 is fixed (stdout → stderr), also consider wrapping:
```python
    from quirk.util.safe_exc import safe_str
    print(f"DOCX report written to {safe_str(path)}", file=sys.stderr)
```

---

_Reviewed: 2026-05-24_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
