---
phase: 102-dashboard-auth-ux-score-tax
reviewed: 2026-05-24T00:00:00Z
depth: standard
files_reviewed: 8
files_reviewed_list:
  - quirk/cli/token_cmd.py
  - quirk/dashboard/api/middleware/auth.py
  - quirk/reports/executive.py
  - src/dashboard/src/lib/api.ts
  - src/dashboard/src/context/AuthProvider.tsx
  - src/dashboard/src/pages/login.tsx
  - src/dashboard/src/App.tsx
  - src/dashboard/src/components/sidebar.tsx
findings:
  critical: 0
  warning: 4
  info: 3
  total: 7
status: issues_found
---

# Phase 102: Code Review Report

**Reviewed:** 2026-05-24T00:00:00Z
**Depth:** standard
**Files Reviewed:** 8
**Status:** issues_found

## Summary

Phase 102 delivers dashboard API token auth (bearer + X-API-Key), a login UX gate, and
TRANS-04 score sourcing alignment. The core security properties hold up well under
adversarial scrutiny: `hmac.compare_digest` is used on both header paths, the empty-string
guard is correct (falsy check on `x_api_key` before compare), the auth-disabled passthrough
requires a truly empty configured token, and the mid-session 401→logout handler is guarded
so it only fires when a token was actually sent (`token &&` check in `api.ts`). The
YAML round-trip in `token_cmd.py` loads the full file before writing, preventing key
clobbering. The frontend token is not logged to console or sent to a third party.

Four warnings and three info items were found. There are no critical security blockers.
The most significant concern is the non-atomic config file write in `_write_token_to_config`,
which can corrupt `config.yaml` on a mid-write crash. Two misleading code comments
(one factually wrong about useEffect ordering) are also flagged.

---

## Warnings

### WR-01: Non-atomic config write — `config.yaml` truncated on crash

**File:** `quirk/cli/token_cmd.py:26-27`

**Issue:** `_write_token_to_config` opens `config.yaml` with `open(config_path, "w", ...)` and
then calls `yaml.dump()` into that file handle. `open(..., "w")` truncates the file to zero
bytes immediately. If the process is killed or the disk fills between the `open` and the
completion of `yaml.dump`, `config.yaml` is left empty or partially written. On next
startup `yaml.safe_load(f) or {}` returns `{}`, silently discarding all prior configuration
(assessment name, targets, scan options, etc.). This is especially dangerous because
`generate` and `rotate` are the only way to create the token — they are likely run
interactively on a live deployment.

**Fix:** Write to a sibling temp file then atomically rename:
```python
import tempfile, os

def _write_token_to_config(config_path: str, token: str) -> None:
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
    except FileNotFoundError:
        raw = {}
    if not isinstance(raw.get("security"), dict):
        raw["security"] = {}
    raw["security"]["api_token"] = token
    dir_ = os.path.dirname(os.path.abspath(config_path))
    fd, tmp = tempfile.mkstemp(dir=dir_, prefix=".quirk_config_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            yaml.dump(raw, f, default_flow_style=False, allow_unicode=True)
        os.replace(tmp, config_path)  # atomic on POSIX; best-effort on Windows
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
```

---

### WR-02: YAML round-trip strips comments from `config.yaml`

**File:** `quirk/cli/token_cmd.py:19-27`

**Issue:** `yaml.safe_load` followed by `yaml.dump` is a lossy round-trip: YAML comments,
blank lines used for readability, and key ordering are all destroyed. A user who has
annotated their `config.yaml` with comments (e.g., `# production targets`) will lose
all annotations silently on the first `quirk token generate` or `rotate` call. This
is a data-loss risk for the configuration file even though the semantic values are
preserved.

**Fix:** Use `ruamel.yaml` (round-trip loader) if comment preservation is required, or
add a prominent warning to the `generate`/`rotate` output:
```
Warning: config.yaml comments and key ordering will be overwritten by this operation.
```
If `ruamel.yaml` is not acceptable as a new dependency, add the warning to both the
`generate` and `rotate` stdout output so operators are aware before running the command
on an annotated config.

---

### WR-03: Misleading / factually wrong comment in `AuthProvider.tsx` about useEffect ordering

**File:** `src/dashboard/src/context/AuthProvider.tsx:17-18`

**Issue:** The file-level comment states:

> "we use the raw fetch() for the probe so the 401 handler registration in useEffect
> fires AFTER the probe resolves."

This is factually incorrect. React fires all `useEffect` callbacks synchronously in
declaration order after the first render, before any async resolution. The second
`useEffect` (line 122, handler registration) fires immediately after the first `useEffect`
sets off the `fetch()` call — it does NOT wait for the network response. The logout
handler is therefore registered before the probe 401 response arrives.

The behavior happens to be correct only because the probe uses raw `fetch()` rather than
`fetchApi()`, so the registered `_onUnauthorized` callback is never triggered by the probe
regardless of ordering. But the stated reason ("fires AFTER") is wrong and will mislead
future maintainers into believing the ordering gives safety that it does not actually
provide.

**Fix:** Replace the comment with an accurate explanation:
```
// The probe uses raw fetch() — NOT fetchApi() — to avoid triggering the
// _onUnauthorized callback that is registered in the second useEffect.
// Because the probe bypasses fetchApi, the handler registration order
// relative to the probe completing does not matter for correctness.
```

---

### WR-04: Network errors on login show a misleading "Invalid token" message

**File:** `src/dashboard/src/pages/login.tsx:63-69`

**Issue:** The `catch` block on lines 63-69 sets the error state to
`"Invalid token. Check your token and try again."` for any network failure
(DNS error, server down, CORS rejection, etc.). A user who enters a correct token
while the server is briefly unreachable will be told their token is invalid, clear
their input, and may believe they have the wrong token. This could cause an operator
to regenerate a valid token unnecessarily.

**Fix:** Distinguish network errors from auth rejections:
```typescript
} catch (err) {
  setError("Cannot reach the server. Check your network connection and try again.")
  if (inputRef.current) {
    inputRef.current.focus()  // do NOT clear — token may be valid
  }
}
```
Also preserve the token value in the input on network errors (don't clear) so the
user can retry without re-typing.

---

## Info

### IN-01: `run_token()` always calls `sys.exit()` — the `return` in `run_scan.py` is dead code

**File:** `run_scan.py:494`

**Issue:** `run_token(_sys.argv[2:])` always terminates via `sys.exit(0)` (for
`generate`/`rotate`/`show`) or `sys.exit(2)` (argparse error). The `return` on line 494
is never reached. This is harmless but represents dead code that could confuse future
maintainers who add new branches to `run_token()` and expect the caller to continue.

**Fix:** Add a comment documenting the invariant:
```python
run_token(_sys.argv[2:])
return  # unreachable: run_token always calls sys.exit()
```

---

### IN-02: X-API-Key takes full precedence over Authorization: Bearer — no fallback when X-API-Key is wrong

**File:** `quirk/dashboard/api/middleware/auth.py:52-56`

**Issue:** When a client sends both `X-API-Key` (wrong value) and
`Authorization: Bearer` (correct value), the middleware raises 401 after checking
X-API-Key and never evaluates the bearer token. This is the documented behavior
(`X-API-Key has precedence`) but it creates an invisible footgun: if a CLI script
sends an X-API-Key header with a stale token while also sending a valid bearer token,
authentication silently fails with no indication that the other header was ignored.

This is an accepted design trade-off (documented in T-102-07), but a clearer 401
detail would help operators diagnose the issue. No code change is mandatory.

**Fix (optional):** Change the 401 detail when X-API-Key is present but wrong to
distinguish it from a missing-credentials 401:
```python
raise HTTPException(
    status_code=401,
    detail=format_error("DASHBOARD-001") + " (X-API-Key header rejected; Authorization: Bearer not evaluated)"
)
```
Or, if leaking header names is a concern, document the precedence order in
the `format_error("DASHBOARD-001")` message itself.

---

### IN-03: `quirk token show` prints the full token value to stdout with no TTY check

**File:** `quirk/cli/token_cmd.py:103`

**Issue:** `quirk token show` unconditionally prints the raw token to stdout. In CI
pipelines or scripts that capture stdout for logging (`quirk token show >> build.log`),
the token is inadvertently persisted in plaintext log files. There is no TTY check, no
masking, and no warning about log capture risk.

**Fix:** Add a TTY check and warning:
```python
import sys
if not sys.stdout.isatty():
    print(
        "Warning: stdout is not a TTY — token will appear in captured output.",
        file=sys.stderr,
    )
print(token if token else "(no token configured)")
```

---

_Reviewed: 2026-05-24T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
