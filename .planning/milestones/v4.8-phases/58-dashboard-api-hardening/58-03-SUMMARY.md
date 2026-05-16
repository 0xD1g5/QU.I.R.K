---
phase: 58-dashboard-api-hardening
plan: "03"
subsystem: cli-util-security
tags:
  - security
  - path-traversal
  - ssrf
  - dos
  - cr-01
  - cr-02
  - cr-09
dependency_graph:
  requires: []
  provides:
    - "quirk/cli/init_cmd.py::CWD-anchored output path guard"
    - "quirk/dashboard/api/routes/pdf.py::port-range clamp + Playwright redirect guard"
    - "quirk/util/targets.py::TargetFileError + @file path/size/line guards"
  affects:
    - "quirk/cli/run_scan.py (TargetFileError propagated via ValueError)"
tech_stack:
  added: []
  patterns:
    - "os.path.realpath() CWD-anchor pattern (mirrors subprocess_input.py RC_* pattern)"
    - "Playwright page.route() intercept-and-abort for SSRF mitigation"
    - "TargetFileError(ValueError) with Final[str] reason-code constants"
key_files:
  created: []
  modified:
    - quirk/cli/init_cmd.py
    - quirk/dashboard/api/routes/pdf.py
    - quirk/util/targets.py
decisions:
  - "TargetFileError extends ValueError for backward compat with existing callers (D-14)"
  - "Port clamp placed before print_url construction — URL never built for out-of-range ports (D-11)"
  - "Playwright _abort_non_loopback defined inline as closure to avoid module-level state (D-12)"
  - "Line cap uses stream-counting (sum(1 for _ in fh)) to avoid loading large files into memory"
metrics:
  duration: "~12 minutes"
  completed: "2026-05-09"
  tasks_completed: 3
  tasks_total: 3
  files_modified: 3
---

# Phase 58 Plan 03: CLI/PDF/@file Security Guards Summary

**One-liner:** Three stdlib-only security guards closing CR-01 (init path traversal), CR-02 (PDF SSRF via port + Playwright redirect), and CR-09 (@file reflective DoS + path escape).

## What Was Built

### Task 1 — CWD-anchored path-traversal guard in `quirk init` (CR-01 / HARDEN-API-04)

Modified `quirk/cli/init_cmd.py` to insert a two-layer path guard after `os.path.abspath()`:

1. **Realpath CWD-anchor check:** `os.path.realpath(output_path)` must descend from `os.path.realpath(os.getcwd())`. Rejects symlink escapes and absolute paths outside CWD.
2. **Defense-in-depth dotdot check:** `os.path.normpath(output_path).split(os.sep)` must not contain `..`. Catches literal traversal segments before resolution.

Both rejections use the existing `_warn()` helper for consistent output style, then `return` to halt processing before any `os.makedirs` or `shutil.copy2` call.

Commit: `ed667f3`

### Task 2 — Port-range clamp and Playwright redirect guard in pdf.py (CR-02 / HARDEN-API-05)

Modified `quirk/dashboard/api/routes/pdf.py` with two guards:

**Guard 1 — Port range clamp (D-11):** After the existing `ValueError` check for `QUIRK_SERVE_PORT` int conversion, added a range assertion: `not (1024 <= port <= 65535)` returns HTTP 500 with a JSON detail message before `print_url` is ever constructed.

**Guard 2 — Playwright redirect abort (D-12):** After `page = context.new_page()`, registered `page.route("**/*", _abort_non_loopback)`. The handler extracts the hostname via `urllib.parse.urlparse`, checks it against `_LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost"}`, and calls `route.abort()` for any non-loopback destination. All loopback navigations call `route.continue_()`.

Commit: `1c748f2`

### Task 3 — TargetFileError and @file guards in `parse_target_tokens` (CR-09 / HARDEN-API-06)

Modified `quirk/util/targets.py` with two additions:

**New class and constants at module level:**
- `RC_PATH_TRAVERSAL`, `RC_PATH_NOT_ALLOWED_PREFIX`, `RC_TARGET_FILE_TOO_LARGE`, `RC_TARGET_FILE_TOO_MANY_LINES` — `Final[str]` reason-code constants mirroring `subprocess_input.py` pattern.
- `_BLOCKED_PREFIXES: tuple[str, ...]` = `("/etc", "/proc", "/sys", "/dev")`.
- `_MAX_FILE_SIZE = 1_048_576` (1 MB), `_MAX_LINE_COUNT = 10_000`.
- `class TargetFileError(ValueError)` with `path` and `reason` attributes.

**Guard inside `parse_target_tokens()`**, inserted before `load_targets_file()` in the `@`-token branch:
1. **CWD-anchor check:** `os.path.realpath(file_path)` must descend from `os.path.realpath(os.getcwd())` — raises `TargetFileError(file_path, RC_PATH_TRAVERSAL)`.
2. **Blocked prefix check:** any `_BLOCKED_PREFIXES` match raises `TargetFileError(file_path, RC_PATH_NOT_ALLOWED_PREFIX)`.
3. **Size cap:** `os.path.getsize(file_path) > 1_048_576` raises `TargetFileError(file_path, RC_TARGET_FILE_TOO_LARGE)`.
4. **Line cap:** stream-count `sum(1 for _ in fh) > 10_000` raises `TargetFileError(file_path, RC_TARGET_FILE_TOO_MANY_LINES)`. Uses streaming to avoid loading large files into memory.

`OSError` (e.g., file not found) is silenced at checks 3 and 4 — `load_targets_file` surfaces the `FileNotFoundError` naturally.

Commit: `75b7df8`

## Deviations from Plan

None — plan executed exactly as written.

## Threat Coverage

| Threat ID | Category | Mitigation Status |
|-----------|----------|------------------|
| T-58-03-T (init path traversal) | Tampering | Closed — realpath CWD-anchor + dotdot defense-in-depth |
| T-58-03-T (port out-of-range) | Tampering | Closed — port clamp 1024-65535, HTTP 500 before URL construction |
| T-58-03-S (Playwright non-loopback) | Spoofing | Closed — page.route intercepts before DNS resolution |
| T-58-03-I (@file to /etc/passwd) | Info Disclosure | Closed — CWD-anchor + blocked-prefix before file open |
| T-58-03-D (@file DoS via large file) | DoS | Closed — 1 MB + 10k line caps with stream-counting |

## Known Stubs

None.

## Threat Flags

None — all security surfaces introduced in this plan are covered by the plan's threat model.

## Self-Check: PASSED

- `quirk/cli/init_cmd.py` — exists, contains `os.path.realpath`, `resolves outside the current working`, `path-traversal segments`
- `quirk/dashboard/api/routes/pdf.py` — exists, contains `1024 <= port <= 65535`, `_LOOPBACK_HOSTS`, `page.route("**/*", _abort_non_loopback)`
- `quirk/util/targets.py` — exists, contains `class TargetFileError(ValueError):`, all 4 RC_* constants, `_MAX_FILE_SIZE`, `_MAX_LINE_COUNT`, `_BLOCKED_PREFIXES`
- All three files compile cleanly (`python -m compileall` exits 0)
- All imports verified (`from quirk.cli.init_cmd import run_init`, `from quirk.util.targets import TargetFileError, ...`)
- Commits: `ed667f3`, `1c748f2`, `75b7df8`
