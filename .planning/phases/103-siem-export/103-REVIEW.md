---
phase: 103-siem-export
reviewed: 2026-05-24T00:00:00Z
depth: standard
files_reviewed: 5
files_reviewed_list:
  - quirk/siem/formatter.py
  - quirk/siem/transport.py
  - quirk/siem/config.py
  - quirk/siem/dispatcher.py
  - quirk/cli/export_cmd.py
findings:
  critical: 2
  warning: 4
  info: 3
  total: 9
status: issues_found
---

# Phase 103: Code Review Report

**Reviewed:** 2026-05-24T00:00:00Z
**Depth:** standard
**Files Reviewed:** 5
**Status:** issues_found

## Summary

The SIEM export implementation is structurally sound: the ISEC-03 whitelist is correctly
enforced via explicit `.get()` extractions, `yaml.safe_load` is used, `safe_str` guards
exception strings in the audit path, and the scheduler hook is properly isolated so that
SIEM failure cannot corrupt a committed scan record. The config loader correctly reads
from `QUIRK_CONFIG_PATH`, never from the scheduler's SQLite `--config` path.

Two critical defects were found. The most serious is a **log-injection / CEF event forgery**
vulnerability: `_cef_escape_header()` does not strip or encode newline characters (`\n`,
`\r`), so a finding whose `title` or `category` field contains a newline injects a
second, fully-formed CEF line into the syslog stream, allowing an attacker who controls
finding metadata to forge arbitrary SIEM events. The second critical defect is **missing
TCP framing**: the transport sends raw bytes over TCP with no newline terminator and no
octet-count prefix, which violates RFC 6587 and will cause most TCP syslog receivers to
either discard messages or concatenate all events into one unparseable blob.

Four warnings cover: silent protocol fallthrough for unrecognised protocol strings,
missing list-type validation in the after-scan hook before calling `export_findings`, a
type mismatch where `safe_str(BaseException)` is called with a plain `str` argument, and
partial-success being indistinguishable from total failure via the CLI exit code.

---

## Critical Issues

### CR-01: Newline injection in CEF header fields allows event forgery (log injection)

**File:** `quirk/siem/formatter.py:40-49`

**Issue:** `_cef_escape_header()` escapes backslash and pipe but does **not** strip or
encode newline characters (`\n`, `\r\n`, `\r`). The CEF header fields `name` (from
`finding["title"]`) and `signature` (from `finding["category"]`) are passed through this
function. If a finding's `title` contains a newline, the assembled CEF line is split into
two physical lines at the syslog layer, and everything after the newline is interpreted by
the SIEM as a new, independent log event.

Concrete attack: a scanner finding whose `title` is
`Weak TLS\nCEF:0|EVIL|forged|9.9|EVIL-001|Injected|10|dhost=attacker`
produces two CEF lines from a single call to `build_cef_event`. The injected second line
carries arbitrary header and extension content chosen by whoever controls finding metadata
(e.g. a hostile target that influences scan results via a crafted TLS certificate CN).

The same defect exists in `_cef_escape_extension()` for the `\r` case — `\r\n` and bare
`\r` are handled, but a bare `\n` without a preceding `\r` is also handled correctly
there. The extension escaping is therefore correct; **only the header function is
missing newline handling**.

Verified with:
```
_cef_escape_header("Legit Finding\nCEF:0|EVIL|...")
# -> 'Legit Finding\nCEF:0\\|EVIL\\|...'   <- newline is NOT removed
```

**Fix:** Add newline stripping (or encoding) to `_cef_escape_header()`. Stripping is
safest because newlines carry no meaningful information in a CEF header field name:

```python
def _cef_escape_header(value: str) -> str:
    """Escape a CEF header field value.

    CEF header rules (ArcSight CEF Implementation Standard):
      - Backslash (\\) -> \\\\   MUST be escaped FIRST
      - Pipe (|)       -> \\|
      - Newlines       -> stripped (no valid CEF header value contains a newline)
    """
    return (
        value
        .replace("\\", "\\\\")
        .replace("|", "\\|")
        .replace("\r\n", "")
        .replace("\r", "")
        .replace("\n", "")
    )
```

If encoding is preferred over stripping (to preserve evidence content for review):

```python
        .replace("\r\n", "\\n")
        .replace("\r", "\\n")
        .replace("\n", "\\n")
```

---

### CR-02: TCP transport sends raw bytes with no RFC 6587 message framing

**File:** `quirk/siem/transport.py:72-74`

**Issue:** When `protocol="tcp"`, the transport calls `sock.sendall(payload)` where
`payload` is the raw UTF-8 encoded CEF string with a `<PRI>` prefix. No message
delimiter is appended and no octet-count prefix is prepended.

RFC 6587 ("Transmission of Syslog Messages over TCP") defines two framing methods:
- **Octet Counting (section 3.4.1):** prepend `len(msg)` as ASCII decimal followed by
  a space: `"123 <12>CEF:0|..."`.
- **Non-Transparent Framing (section 3.4.2):** append a trailing `LF` (byte `0x0a`).

Without either framing method the TCP receiver has no way to determine message
boundaries. Most production syslog receivers (rsyslog, syslog-ng, Splunk HEC TCP,
ArcSight SmartConnector) default to non-transparent framing and expect a trailing
newline. Without it, the receiver either:
- Buffers indefinitely waiting for the frame boundary, then times out and discards, or
- Concatenates multiple sequential QUIRK sends into one unparseable super-event.

UDP (`sock.sendto`) is unaffected — each datagram is a self-delimiting message.

**Fix:** Apply Non-Transparent Framing (trailing `\n`) for TCP, which is the most
broadly compatible default. Octet-counting can be added later if needed for strict
RFC 5425 TLS syslog:

```python
if socktype == socket.SOCK_STREAM:
    sock.connect((host, port))
    # RFC 6587 section 3.4.2: Non-Transparent-Framing — append LF
    sock.sendall(payload + b"\n")
else:
    sock.sendto(payload, (host, port))
```

---

## Warnings

### WR-01: Unrecognised `protocol` values silently fall through to UDP

**File:** `quirk/siem/transport.py:68`

**Issue:** The protocol selection expression is:
```python
socktype = socket.SOCK_STREAM if protocol == "tcp" else socket.SOCK_DGRAM
```
Any value that is not exactly `"tcp"` (e.g. `"TCP"`, `"tls"`, `"invalid"`) silently
produces a UDP socket. The config loader lowercases the protocol string at parse time
(`str(raw.get("protocol", "udp")).lower()`), which makes typos like `"TCP"` safe in
practice, but `"tls"` or any other non-`"tcp"` string would silently degrade to
unencrypted UDP with no error or log message. This is especially confusing if a future
operator configures `protocol: tls` expecting encrypted transport.

**Fix:** Raise `ValueError` for unrecognised protocols instead of falling through:

```python
_VALID_PROTOCOLS = {"udp", "tcp"}
if protocol not in _VALID_PROTOCOLS:
    raise ValueError(f"protocol must be 'udp' or 'tcp', got: {protocol!r}")
socktype = socket.SOCK_STREAM if protocol == "tcp" else socket.SOCK_DGRAM
```

---

### WR-02: `export_after_scan_hook` does not validate that `findings` is a list before calling `export_findings`

**File:** `quirk/siem/dispatcher.py:146-155`

**Issue:** `export_after_scan_hook` loads findings from the JSON file and passes the
result directly to `export_findings` without checking `isinstance(findings, list)`:

```python
findings = json.load(f)
# ... no type check ...
export_findings(findings, cfg, db, scan_id=str(scan_id))
```

`export_cmd.py` does perform this check (line 118). The after-scan hook does not.

If `findings-*.json` contains a JSON object (`{}`) rather than an array, iterating
over it yields the object's keys as plain strings. Each string is then passed to
`build_cef_event(str_key, version)`, which calls `to_cef_finding(str)`, which calls
`str.get(...)` — `AttributeError`. Each iteration raises, the per-finding `except
Exception` clause catches it and appends an error string, `success_count` stays 0,
and the batch is written to the audit table as `status="failed"` with no indication of
the root cause (malformed file vs. network error vs. type mismatch). The failure is
entirely silent from the operator's perspective.

**Fix:** Add the same guard that `export_cmd.py` already has, immediately after loading:

```python
findings = json.load(f)
if not isinstance(findings, list):
    logger.warning(
        "SIEM after-scan hook: findings file %s does not contain a list — skipping",
        findings_path,
    )
    return
```

---

### WR-03: `safe_str` called with a plain `str` argument, violating its type contract

**File:** `quirk/siem/dispatcher.py:93`

**Issue:**
```python
error_summary = safe_str("; ".join(errors)) if errors else None
```
`safe_str` is typed and documented as `safe_str(exc: BaseException) -> str`. It is
called here with a plain `str` — the joined error messages. This works at runtime
because `type(str_val).__name__` returns `"str"` and `str(str_val)` returns the
string itself, so the function effectively becomes a no-op passthrough. However:

1. It is a type violation that will produce a `mypy` error if type-checking is ever
   enabled on this module.
2. The double-wrapping is unnecessary and misleading — `errors` is already a
   `list[str]` where each element was already `safe_str(exc)` at line 87.

**Fix:** Remove the redundant `safe_str` wrapper since each individual error string was
already sanitised when it was appended:

```python
error_summary = "; ".join(errors) if errors else None
```

---

### WR-04: Partial SIEM export success is indistinguishable from total failure via CLI exit code

**File:** `quirk/cli/export_cmd.py:151-153`

**Issue:**
```python
print(f"SIEM export complete: {count}/{len(findings)} findings sent.")
if count < len(findings):
    sys.exit(2)
```
Exit code `2` is used for both "zero findings sent" (total failure) and "99 of 100
findings sent" (partial success). Operators using the exit code in automation pipelines
(cron, CI, monitoring) cannot distinguish between a total endpoint failure and a single
transient delivery error that dropped one event.

**Fix:** Either document that exit code `2` means "at least one finding was not
delivered" (and make this explicit in the epilog and docstring), or introduce an
exit code `3` for partial success:

```python
if count == 0:
    sys.exit(2)    # total failure — no findings sent
elif count < len(findings):
    sys.exit(3)    # partial failure — some findings not sent
# else: sys.exit(0) implicit — all findings sent
```

Update the exit-code table in the module docstring to match.

---

## Info

### IN-01: `os` imported twice inside a conditional block in `export_cmd.py`; `_version` imported but never used

**File:** `quirk/cli/export_cmd.py:136-145`

**Issue:** Inside the `if args.siem:` block, `os` is imported twice under different
aliases (`import os` at line 136, `import os as _os` at line 145), and `__version__`
is imported as `_version` at line 139 but never referenced again. All three should be
module-level imports; `_version` should be removed entirely since `build_cef_event`
receives the version from inside `dispatcher.export_findings` (via `from quirk import
__version__` at its own deferred import).

**Fix:**
```python
import os  # move to top of file; remove 'import os as _os' and the duplicate
# Remove: from quirk import __version__ as _version  (dead import)
```

---

### IN-02: `__import__('os')` inline pattern in `dispatcher.py` instead of a module-level import

**File:** `quirk/siem/dispatcher.py:53, 153`

**Issue:** Two locations use the `__import__('os')` pattern inline rather than a
module-level `import os`:
- Line 53: `__import__("os").path.getmtime(p)` inside `_find_latest_findings_in`
- Line 153: `__import__("os").path.basename(output_path)` inside `export_after_scan_hook`

`os` is already implicitly available (it is a stdlib module and the import cache is
shared), but the inline `__import__` pattern is unconventional, harder to read, and
will confuse linters.

**Fix:** Add `import os` at the top of `dispatcher.py` alongside the other stdlib
imports and replace both inline patterns with `os.path.getmtime(p)` and
`os.path.basename(output_path)`.

---

### IN-03: `_cef_escape_header` does not escape `=` — confirm this is intentional

**File:** `quirk/siem/formatter.py:40-49`

**Issue:** The function's docstring correctly states that `=` is not escaped in header
fields per the CEF specification ("Equals (=) is NOT escaped in header fields — only in
extension values"). This is correct per the ArcSight CEF Implementation Standard.
However, the code comment says only "Backslash MUST be replaced first"; the rationale
for omitting `=` escaping is only in the docstring, not inline. A future maintainer
editing the escaping logic could add `=` escaping to the header function erroneously
(it would produce double-escaping for extension fields that also pass through
`_cef_escape_header`).

**Fix:** Add a brief inline comment in `_cef_escape_header` to make the omission
explicit and intentional:

```python
# NOTE: '=' is intentionally NOT escaped in header fields per CEF spec
# (section 5, ArcSight CEF Implementation Standard). Only extension values escape '='.
return value.replace("\\", "\\\\").replace("|", "\\|")
```

---

_Reviewed: 2026-05-24T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
