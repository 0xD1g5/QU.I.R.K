---
phase: 68-operator-error-message-pass
reviewed: 2026-05-14T00:00:00Z
depth: standard
files_reviewed: 20
files_reviewed_list:
  - quirk/errors.py
  - quirk/cli/errors_cmd.py
  - quirk/cli/doctor_cmd.py
  - quirk/cli/schedule_cmd.py
  - quirk/util/optional_extra.py
  - quirk/dashboard/server.py
  - quirk/dashboard/api/middleware/auth.py
  - quirk/dashboard/api/middleware/csrf.py
  - quirk/dashboard/api/middleware/rate_limit.py
  - quirk/dashboard/api/routes/scan.py
  - quirk/dashboard/api/routes/jobs.py
  - quirk/dashboard/api/routes/qramm.py
  - quirk/dashboard/api/routes/schedules.py
  - quirk/dashboard/api/routes/pdf.py
  - run_scan.py
  - tests/test_errors.py
  - tests/test_errors_cmd.py
  - tests/test_install_errors.py
  - tests/test_error_codes_freshness.py
  - tests/conftest.py
findings:
  critical: 3
  warning: 5
  info: 3
  total: 11
status: issues_found
---

# Phase 68: Code Review Report

**Reviewed:** 2026-05-14
**Depth:** Standard
**Files Reviewed:** 20
**Status:** issues_found

## Summary

Phase 68 delivers a well-structured canonical error registry (`quirk/errors.py`) with a frozen dataclass, a `format_error()` helper, and a `CATEGORY_TO_CODE` dispatch map. Wire format is consistent across all call sites. The test suite is substantive — 29 tests covering the registry, CLI command, install scenarios, and freshness gate.

Three blockers require attention before this code ships: the INSTALL-004 error message hard-codes `:8512` even when `quirk serve --port <N>` is invoked with a different port (the message will lie to the operator); the dashboard job dispatcher hard-codes `allow_internal_targets: True` in every scan config it writes (a security regression unrelated to phase scope but introduced here); and the pdf.py fallback error message when Playwright fails for a non-chromium reason leaks the raw exception string rather than a structured QRK code.

---

## Critical Issues

### CR-01: INSTALL-004 fix hint hard-codes port 8512 regardless of actual port

**File:** `quirk/errors.py:40`, `quirk/dashboard/server.py:47-48`

**Issue:** The `INSTALL-004` `fix` string hard-codes `lsof -i :8512`, but `server.serve()` accepts an arbitrary `port` parameter and emits this error regardless of what port was actually in conflict. When an operator runs `quirk serve --port 9000` and port 9000 is occupied, the error message instructs them to run `lsof -i :8512` — the wrong port. This directly misleads the operator about the conflict source.

The registry design intentionally has no runtime parameters (codes are static strings), but the server-side call site does not compensate. The fix is to emit the port-specific message from `server.py` rather than delegating to the static registry entry when the port is non-default, or to add the port to the error string at the call site.

**Fix:**
```python
# quirk/dashboard/server.py — replace the static format_error call with a
# port-aware message:
except OSError as exc:
    if "address already in use" in str(exc).lower():
        port_hint = f"lsof -i :{port}" if port != 8512 else "lsof -i :8512"
        msg = (
            f"[QRK-INSTALL-004] Port {port} is already in use. "
            f"Fix: Run `{port_hint}` to find the conflicting process, "
            f"or use `quirk serve --port <other>`."
        )
        print(msg, file=sys.stderr)
        sys.exit(1)
    raise
```

Alternatively, keep `format_error("INSTALL-004")` and update the `fix` field to say `lsof -i :<port>` with a generic placeholder. Either way the current behaviour silently lies on non-default ports.

---

### CR-02: `jobs.py` hard-codes `allow_internal_targets: True` in every dispatched scan config

**File:** `quirk/dashboard/api/routes/jobs.py:95`

**Issue:** `_write_job_config()` unconditionally writes `"security": {"allow_internal_targets": True}` into every YAML config generated for a dashboard-dispatched scan. This means every scan launched from the web UI bypasses the internal-target SSRF guard that Phase 57 deliberately made opt-in. An operator who has not set `allow_internal_targets: True` in their own config.yaml gets a more permissive posture when scans run from the dashboard, with no indication.

This is not gated on the `ScanSubmitRequest` payload — there is no field for it — so there is no way for the caller to opt out, and no advisory is emitted.

**Fix:**
```python
# Remove the allow_internal_targets override entirely, or pass it through
# from the ScanSubmitRequest payload (defaulting False):
"security": {
    "allow_internal_targets": payload.allow_internal_targets,  # default False
},
```
If the field should never be surfaced in the dashboard, remove the `security` block from the generated config so the default (False) applies.

---

### CR-03: `pdf.py` exception handler emits raw exception string instead of structured QRK message

**File:** `quirk/dashboard/api/routes/pdf.py:106-118`

**Issue:** The generic exception branch at lines 106-118 returns `f"PDF export failed: {msg}"` or `f"PDF export failed. Ensure Playwright is installed: ... Error: {msg}"` — raw Python exception strings with no `QRK-` prefix. The `format_error("DASHBOARD-012")` import is only used for the "sync_playwright is None" path (line 42). When Playwright is installed but chromium fails to launch for any reason (permission denied, corrupted install, wrong architecture), the response detail does not conform to the `[QRK-DOMAIN-NNN]` wire format that is the sole deliverable of this phase.

Additionally, the raw exception string is returned directly in the HTTP response body, which can expose internal paths or system state.

**Fix:**
```python
# Replace the chromium-detection branch with the canonical code and suppress
# the raw exception string in the response:
except Exception as exc:
    msg = str(exc)
    if (
        "chromium" in msg.lower()
        or "executable" in msg.lower()
        or "no such file" in msg.lower()
    ):
        return Response(
            content=json.dumps({"detail": format_error("DASHBOARD-012")}).encode(),
            status_code=503,
            media_type="application/json",
        )
    # Generic internal error — do not expose msg
    return Response(
        content=json.dumps({"detail": "[QRK-DASHBOARD-012] PDF export failed."}).encode(),
        status_code=500,
        media_type="application/json",
    )
```

---

## Warnings

### WR-01: SCHED-001 documented max length (64 chars) contradicts code validation (255 chars)

**File:** `quirk/errors.py:139`, `quirk/cli/schedule_cmd.py:20`, `quirk/dashboard/api/routes/schedules.py:40`

**Issue:** The `SCHED-001` fix string tells operators "Schedule names must match [A-Za-z0-9_-]+ and be 1-64 chars." However:
- `quirk/cli/schedule_cmd.py` uses `_NAME_RE = re.compile(r"^[A-Za-z0-9_\-\.]{1,255}$")` — up to 255 chars, and also allows `.` (dot) which the error message does not mention.
- `quirk/dashboard/api/routes/schedules.py` uses `max_length=255, pattern=r"^[A-Za-z0-9_\-\.]+$"` — same discrepancy.

So the error code documents the wrong constraint in two ways: the length bound is 255 not 64, and the character set includes `.`. An operator who reads the error and tries a 65-character name will be confused to find it succeeds.

**Fix:** Update `SCHED-001` fix text to accurately document the actual constraint:
```python
fix="Schedule names must match [A-Za-z0-9_\\-\\.]{1,255}.",
```
Or enforce 64-char limit in both the CLI regex and the API Pydantic field to match the documented constraint.

---

### WR-02: `probe_missing_extras` emits INSTALL-001 ("optional scanner package not installed") for the `dashboard` and `cbom` extras, which are not scanner packages

**File:** `quirk/util/optional_extra.py:225`

**Issue:** `probe_missing_extras()` calls `format_error("INSTALL-001")` for every missing extra regardless of which extra it is. `INSTALL-001` reads: "Optional scanner package not installed. Fix: Run `pip install quirk[<extra>]` to enable this scanner." The `dashboard` and `cbom` entries have `enabled_attrs=()` (always-probe) and are not scanners. When fastapi/uvicorn/playwright are missing, the error message says "enable this **scanner**" — a misleading hint for a user who is trying to set up the web UI, not a scanner.

The `dashboard` entry has its own dedicated code `INSTALL-002`. The `probe_missing_extras` loop should use `INSTALL-002` when emitting for the `dashboard` extra.

**Fix:**
```python
# In probe_missing_extras, choose the error code based on the entry:
error_code = "INSTALL-002" if entry.extra == "dashboard" else "INSTALL-001"
print(format_error(error_code), file=sys.stderr)
```

---

### WR-03: `server.py` port-conflict detection relies on a case-insensitive substring match that may not fire on all platforms

**File:** `quirk/dashboard/server.py:47`

**Issue:** The check `"address already in use" in str(exc).lower()` catches the POSIX EADDRINUSE message. On Windows the OSError message is "Only one usage of each socket address (protocol/network address/port) is normally permitted" — "address already in use" is absent. This means on Windows, the `raise` at line 50 propagates an unformatted OSError instead of the operator-friendly `format_error("INSTALL-004")` message.

This is secondary to CR-01 but compounds it: on a Windows deployment the user sees a raw traceback instead of the QRK message.

**Fix:** Add an errno check alongside the string match:
```python
import errno as _errno
except OSError as exc:
    if (
        "address already in use" in str(exc).lower()
        or getattr(exc, "errno", None) == _errno.EADDRINUSE
    ):
        print(format_error("INSTALL-004"), file=sys.stderr)
        sys.exit(1)
    raise
```

---

### WR-04: `_check_binary` in `doctor_cmd.py` falls back to `INSTALL-006` for unknown binary names

**File:** `quirk/cli/doctor_cmd.py:42`

**Issue:**
```python
code = _BINARY_TO_CODE.get(name, "INSTALL-006")
```
`INSTALL-006` is the nmap-specific code ("nmap binary not found in PATH"). If `_check_binary` is ever called with a binary name not in `_BINARY_TO_CODE` (e.g., a future binary added to the loop at line 143), the wrong, nmap-specific remediation hint will be emitted. There is no guard or assertion to prevent this.

Currently the only callers pass `"nmap"`, `"syft"`, `"semgrep"` — all in `_BINARY_TO_CODE` — so this does not fire today, but it is a latent correctness bug: the dict lookup silently swallows unknown keys rather than failing loudly.

**Fix:**
```python
code = _BINARY_TO_CODE[name]  # KeyError is a legitimate signal; add entry if needed
```
Or at minimum add an assertion:
```python
code = _BINARY_TO_CODE.get(name)
assert code is not None, f"No error code mapped for binary {name!r}; update _BINARY_TO_CODE"
```

---

### WR-05: Rate-limit response body is double-JSON-encoded on the wire

**File:** `quirk/dashboard/api/middleware/rate_limit.py:61-65`

**Issue:**
```python
content=json.dumps({"detail": format_error("DASHBOARD-003")}).encode(),
```
`format_error()` returns a plain string such as `"[QRK-DASHBOARD-003] Rate limit exceeded. Fix: ..."`. The dict `{"detail": format_error(...)}` is correct — that matches the FastAPI HTTPException JSON shape. However, the `content` passed to `Response()` is already the encoded bytes, and `media_type="application/json"` is set, so Starlette/FastAPI will **not** double-encode this. This is actually correct behavior.

However, this differs subtly from what FastAPI produces for `HTTPException` responses: FastAPI wraps the detail in `{"detail": ...}` automatically, but here the explicit `json.dumps` means the `detail` value is already a plain string inside the JSON object — consistent with the auth and CSRF middleware that raise `HTTPException(detail=format_error(...))`. The shape is consistent.

**Reclassifying:** This is a WARNING for maintainability, not a runtime bug. The comment in the source ("Rate-limit middleware cannot raise HTTPException") is accurate and the approach is correct. The concern is that future maintainers who copy this pattern for a different code may forget `.encode()` or omit `media_type`, producing invalid responses. Add an inline comment explaining why `Response(content=...)` is used instead of `HTTPException`.

---

## Info

### IN-01: `errors.py` reserved/dormant codes (TLS-002, SSH-002) are present in the registry and appear in `--dump-md` output

**File:** `quirk/errors.py:204-215`, `quirk/cli/errors_cmd.py:71-92`

**Issue:** The registry contains codes marked "dormant; not actively written today" (`TLS-002`, `SSH-002`). They appear in `quirk errors` table output and `docs/error-codes.md`, which may cause operator confusion ("why does TLS-002 show in the reference but never appears in scan output?").

**Fix:** Either remove dormant codes from the registry until they are actively emitted, or add an `active: bool` field to `ErrorEntry` and suppress dormant codes in `--dump-md` and table output. The current approach also means the freshness test in `test_error_codes_freshness.py` will verify these codes are in the generated docs even though no code path emits them.

---

### IN-02: `_normalize_code` in `errors_cmd.py` strips only the four-character prefix `"QRK-"` by position, not by semantic matching

**File:** `quirk/cli/errors_cmd.py:16`

**Issue:**
```python
return raw[4:] if raw.startswith("QRK-") else raw
```
If a user types `QRK-INSTALL-001` this correctly returns `INSTALL-001`. If a user types `qrk-install-001` (lowercase), `startswith("QRK-")` is False so the whole string is passed to the registry lookup — which will miss because registry keys are uppercase. The `--domain` filter already normalizes case via `.upper()`, but single-code lookup does not.

**Fix:**
```python
def _normalize_code(raw: str) -> str:
    stripped = raw.upper()
    return stripped[4:] if stripped.startswith("QRK-") else stripped
```

---

### IN-03: `test_install_errors.py` subprocess test `test_port_conflict_format` has a TOCTOU window between `_free_port()` and `holder.bind()`

**File:** `tests/test_install_errors.py:74-99`

**Issue:** `_free_port()` binds a socket to get a free port, releases it, then the test re-binds the port via `holder`. Between `_free_port()` releasing and `holder.bind()` re-acquiring, another process could claim that port, causing a spurious test failure on busy CI environments. This is a test reliability issue rather than a correctness issue in production code.

**Fix:**
```python
# Hold the socket across the bind — do not close after getting the port number:
def _free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
    s.bind(("127.0.0.1", 0))
    s.listen(1)
    port = s.getsockname()[1]
    return port, s  # return socket too; caller must close after subprocess completes
```

---

_Reviewed: 2026-05-14_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
