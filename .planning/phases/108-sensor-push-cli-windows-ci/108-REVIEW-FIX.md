---
phase: 108-sensor-push-cli-windows-ci
fixed_at: 2026-05-25T00:00:00Z
review_path: .planning/phases/108-sensor-push-cli-windows-ci/108-REVIEW.md
iteration: 2
findings_in_scope: 3
fixed: 3
skipped: 0
status: all_fixed
---

# Phase 108: Code Review Fix Report (Iteration 2)

**Fixed at:** 2026-05-25T00:00:00Z
**Source review:** .planning/phases/108-sensor-push-cli-windows-ci/108-REVIEW.md
**Iteration:** 2

**Summary:**
- Findings in scope: 3
- Fixed: 3
- Skipped: 0

## Fixed Issues

### WR-01a: `_evict_if_full` generator calls `.stat()` twice per file — double-stat not eliminated

**Files modified:** `quirk/cli/sensor_cmd.py`
**Commit:** 9844b96
**Applied fix:** Replaced the `sorted(generator)` form that called `p.stat().st_size` and
`p.stat().st_mtime` as two separate syscalls with an explicit for-loop. Each file now calls
`p.stat()` exactly once into a named variable `st`, then appends `(p, st.st_size, st.st_mtime)`
to a list. The loop wraps each `p.stat()` call in `try/except FileNotFoundError` to skip files
removed between glob and stat. The list is sorted separately with `files.sort(key=lambda t: t[2])`.
No `.stat()` call is made more than once per file.

---

### IN-01: `open()` without context manager in `_cmd_import_results` leaks file handle

**Files modified:** `quirk/cli/console_cmd.py`
**Commit:** 351f82a
**Applied fix:** Changed `raw_file = open(file_path, "rb").read()` to a
`with open(file_path, "rb") as fh: raw_file = fh.read()` context manager. The existing
`OSError` handler is preserved unchanged. The file descriptor is now closed deterministically
on all exit paths including exception paths.

---

### WR-03a: New WR-03 framing path in `_cmd_import_results` has zero test coverage

**Files modified:** `tests/test_console_cmd.py`
**Commit:** 109d8aa
**Applied fix:** Added `import hashlib`, `import hmac as _hmac`, and `import os` to the test
module header, plus `_make_framed_qpush_file()` helper that builds a properly WR-03-framed
`.qpush` file (JSON header line + `\n` + compressed body) with a real HMAC-SHA256 embedded
signature. Added 7 new test functions covering every branch in the framing parser:

1. `test_import_results_framed_happy_path` — valid framed file parses correctly; sig forwarded to `_ingest_envelope` verbatim; exit 0
2. `test_import_results_framing_no_newline` — file starts with `{` but no `\n` → clean SystemExit non-zero, no traceback
3. `test_import_results_framing_invalid_json_header` — header line is not valid JSON → clean SystemExit non-zero, no traceback
4. `test_import_results_framing_missing_hmac_key` — valid JSON header but no `hmac-sha256` field → clean SystemExit non-zero
5. `test_import_results_framing_invalid_sig_format` — `hmac-sha256` value present but wrong prefix → clean SystemExit non-zero
6. `test_import_results_framing_sig_not_a_string` — `hmac-sha256` value is an integer → clean SystemExit non-zero
7. `test_import_results_framing_body_contains_newline_byte` — compressed body containing 0x0A bytes round-trips intact; confirms parser splits on first `\n` only

## Skipped Issues

None.

---

**Verification results:**
- `python -m compileall quirk run_scan.py`: passed (no output / no errors)
- `pytest tests/test_sensor_cmd.py tests/test_console_cmd.py tests/test_sensor_no_verify_false.py tests/test_sensor_windows_smoke.py -q`: **56 passed**, 26 deprecation warnings (pre-existing `datetime.utcnow()` usage in sensor_cmd.py, unrelated to these fixes), 0 failures

---

_Fixed: 2026-05-25T00:00:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 2_
