---
phase: 108-sensor-push-cli-windows-ci
reviewed: 2026-05-25T00:00:00Z
depth: standard
files_reviewed: 2
files_reviewed_list:
  - quirk/cli/sensor_cmd.py
  - quirk/cli/console_cmd.py
findings:
  critical: 0
  warning: 0
  info: 1
  total: 1
status: clean
iteration: 3
---

# Phase 108: Code Review Report (Iteration 3 — Final Re-Review)

**Reviewed:** 2026-05-25T00:00:00Z
**Depth:** standard
**Files Reviewed:** 2
**Status:** clean (no Critical or Warning findings remain)

## Summary

Final re-review of `sensor_cmd.py` and `console_cmd.py` after the iteration-3 fix round,
with `tests/test_console_cmd.py` read as supporting evidence for the WR-03a test-coverage
finding.

All three targeted findings are fully resolved:

**WR-01a — single-stat in `_evict_if_full`:** The generator expression that called
`.stat()` twice per file has been replaced with an explicit `for` loop. Each file gets
exactly one `p.stat()` call; the result is stored in `st`; both `st.st_size` and
`st.st_mtime` are extracted from the same `stat` object. The `try/except FileNotFoundError`
wraps the entire `stat()` + `append()` operation so a file removed between glob and stat
is silently skipped. The sort runs on the already-complete list, after the loop. The fix
matches the recommended pattern exactly.

**WR-03a — HMAC-framed .qpush tests:** The test file now contains eight new test
functions covering the full framing code path:
- `test_import_results_framed_happy_path` — valid framed file, sig forwarded to `_ingest_envelope`
- `test_import_results_framing_no_newline` — `newline_pos == -1` branch
- `test_import_results_framing_invalid_json_header` — JSON parse failure in header line
- `test_import_results_framing_missing_hmac_key` — `hmac-sha256` key absent from header object
- `test_import_results_framing_invalid_sig_format` — value without `hmac-sha256=` prefix
- `test_import_results_framing_sig_not_a_string` — non-string value (integer)
- `test_import_results_framing_body_contains_newline_byte` — the highest-risk case: compressed
  body containing 0x0A bytes round-trips correctly because the parser splits only on the
  first newline via `raw_file.find(b"\n")`, then slices the remainder as opaque bytes.

**IN-01 — file handle context manager:** `open(file_path, "rb").read()` has been replaced
with `with open(file_path, "rb") as fh: raw_file = fh.read()` inside a `try/except OSError`
block. File handle is closed deterministically on all code paths.

No new Critical or Warning issues were introduced by these fixes. One pre-existing Info
item in the test suite is noted below; it does not affect correctness.

---

## Info

### IN-01: `test_import_results_finding_count_nonzero` runs the function twice with a dead first call

**File:** `tests/test_console_cmd.py:124-143`
**Issue:** The test calls `_cmd_import_results(Args())` twice. The first call at line 124
is inside a `pytest.raises` block whose captured output is discarded — `capsys.readouterr()`
is called twice in sequence at line 127 (second call always returns empty strings since
the buffer was already drained), so the `output` variable at line 127 is always an empty
string and the comment on line 128 ("just check 2 is present somewhere") is never checked.
The actual assertion at line 143 relies on a second manual invocation using redirected
`sys.stdout`/`sys.stderr`. This means the test makes two real calls to the function under
test. The assertion `"2" in out` is also very loose — any output containing the digit `"2"`
anywhere (including a timestamp or UUID) would satisfy it.

The test is not wrong, but the dead first call wastes a function invocation and the
capsys/manual-redirect double-capture pattern is confusing enough that a future maintainer
may not realise the first block contributes nothing to the assertion.

**Fix:** Remove the dead first `pytest.raises` block and the capsys drain. Keep only the
manual-redirect invocation, and tighten the assertion to check for the string `"findings:       2"`
(matching the exact format printed by `_ingest_envelope`) rather than the single digit `"2"`:

```python
def test_import_results_finding_count_nonzero(tmp_path):
    sid = str(uuid.uuid4())
    findings = [
        {"host": "10.0.0.1", "port": 443, "protocol": "tls"},
        {"host": "10.0.0.2", "port": 22, "protocol": "ssh"},
    ]
    envelope = {
        "payload_id": str(uuid.uuid4()),
        "pushed_at": "2026-05-25T12:00:00Z",
        "schema_version": "1.0.0",
        "sensor_version": "5.4.0",
        "sensor_id": sid,
        "segment": "dmz",
        "findings": findings,
    }
    raw = json.dumps(envelope).encode()
    qpush = tmp_path / "findings-count.qpush"
    qpush.write_bytes(zstandard.ZstdCompressor(level=3).compress(raw))

    import io, sys
    from quirk.cli.console_cmd import _cmd_import_results

    class Args:
        file = str(qpush)
        config = "config.yaml"

    old_stdout, old_stderr = sys.stdout, sys.stderr
    sys.stdout = io.StringIO()
    sys.stderr = io.StringIO()
    try:
        with pytest.raises(SystemExit):
            _cmd_import_results(Args())
        out = sys.stdout.getvalue() + sys.stderr.getvalue()
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr

    assert "findings:       2" in out, f"Expected 'findings:       2' in output: {out!r}"
```

---

_Reviewed: 2026-05-25T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
_Iteration: 3_
