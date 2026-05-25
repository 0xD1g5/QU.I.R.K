---
phase: 103-siem-export
fixed_at: 2026-05-24T00:00:00Z
review_path: .planning/phases/103-siem-export/103-REVIEW.md
iteration: 1
findings_in_scope: 6
fixed: 6
skipped: 0
status: all_fixed
---

# Phase 103: Code Review Fix Report

**Fixed at:** 2026-05-24
**Source review:** `.planning/phases/103-siem-export/103-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 6 (2 Critical + 4 Warning; Info findings excluded per scope)
- Fixed: 6
- Skipped: 0

---

## Fixed Issues

### CR-01: Newline injection in CEF header fields allows event forgery (log injection)

**Files modified:** `quirk/siem/formatter.py`, `tests/test_siem_cef.py`
**Commit:** `0105953`
**Applied fix:** Added `.replace("\r\n", "").replace("\r", "").replace("\n", "")` to
`_cef_escape_header()` after the existing backslash-then-pipe replacements. A bare `\n`
in a CEF header field (e.g. a finding title containing an embedded newline) previously
split the syslog line into two physical records, allowing log injection / event forgery
(CWE-117). Also updated the function docstring to document the newline-stripping rule
and added an explicit `NOTE:` comment confirming `=` is intentionally not escaped per
the CEF spec.

Five regression tests added to `tests/test_siem_cef.py`:
- `test_header_newline_stripped_lf`
- `test_header_newline_stripped_cr`
- `test_header_newline_stripped_crlf`
- `test_build_cef_event_newline_in_title_is_single_line` (end-to-end: full `build_cef_event` call with injected title must produce a single physical line)

---

### CR-02: TCP transport sends raw bytes with no RFC 6587 message framing

**Files modified:** `quirk/siem/transport.py`, `tests/test_siem_transport.py`
**Commit:** `33bd786`
**Applied fix:** Changed `sock.sendall(payload)` to `sock.sendall(payload + b"\n")` in
the `SOCK_STREAM` branch of `send_syslog_raw()`. The trailing LF implements RFC 6587
section 3.4.2 non-transparent framing so TCP syslog receivers (rsyslog, syslog-ng,
Splunk, ArcSight) can determine message boundaries. The UDP `sendto` path is unchanged.

Regression test added: `test_send_cef_tcp_ends_with_lf`.

---

### WR-01: Unrecognised `protocol` values silently fall through to UDP

**Files modified:** `quirk/siem/transport.py`, `tests/test_siem_transport.py`
**Commit:** `eb7c362`
**Applied fix:** Added a `_VALID_PROTOCOLS = {"udp", "tcp"}` guard before the
`socktype` assignment. Any protocol value not in that set now raises `ValueError`
immediately. Previously `"tls"`, `"sctp"`, or any other unsupported string silently
produced an unencrypted UDP socket.

Regression tests added: `test_rejects_unknown_protocol` ("tls"), `test_rejects_invalid_protocol_string` ("sctp").

---

### WR-02: `export_after_scan_hook` does not validate that `findings` is a list

**Files modified:** `quirk/siem/dispatcher.py`, `tests/test_siem_dispatcher.py`
**Commit:** `c0e0884`
**Applied fix:** Added `if not isinstance(findings, list): logger.warning(...); return`
immediately after `json.load(f)` in `export_after_scan_hook()`. This matches the guard
that `export_cmd.py` already applies. Without it, a JSON object root caused
`AttributeError` per iteration (string keys passed as findings to `build_cef_event`),
silently swallowed by the per-finding `except Exception` with no operator-visible root
cause.

Regression test added: `test_hook_skips_non_list_findings` — asserts no CEF events sent
and no `IntegrationDelivery` rows written when findings JSON root is a dict.

---

### WR-03: `safe_str` called with a plain `str` argument, violating its type contract

**Files modified:** `quirk/siem/dispatcher.py`
**Commit:** `d2d6508`
**Applied fix:** Removed the `safe_str(...)` wrapper from the `error_summary` assignment.
The individual error strings in `errors` were already sanitised via `safe_str(exc)` when
collected per-finding. The join result is a plain `str`; passing it to `safe_str` (which
expects `BaseException`) is a type violation and a no-op. The line now reads:
`error_summary = "; ".join(errors) if errors else None`.

No new tests needed — existing dispatcher tests exercise the error path and confirm
`error_summary` is populated correctly.

---

### WR-04: Partial SIEM export success is indistinguishable from total failure via CLI exit code

**Files modified:** `quirk/cli/export_cmd.py`
**Commit:** `7e8dd38`
**Applied fix:** Replaced the single `if count < len(findings): sys.exit(2)` with:

```python
if count == 0:
    sys.exit(2)    # total failure — no findings sent
elif count < len(findings):
    sys.exit(3)    # partial failure — some findings not sent
```

Updated both the module-level docstring and the `run_export()` function docstring to
document all four exit codes (0, 1, 2, 3). Exit code semantics:
- `0` — all findings exported successfully
- `1` — usage error (no destination flag)
- `2` — total failure (zero sent, bad config, missing file)
- `3` — partial failure (some sent, at least one failed)

---

## Skipped Issues

None — all six in-scope findings were successfully fixed.

---

_Fixed: 2026-05-24_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
