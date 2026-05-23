---
phase: 93-credential-infrastructure
plan: "01"
subsystem: auth
tags: [credentials, authentication, bytearray, ephemeral, security]
dependency_graph:
  requires: []
  provides: [quirk.auth.credentials.CredentialContext, quirk.config.ConnectorsCfg.enable_authenticated_mode]
  affects: [quirk/config.py]
tech_stack:
  added: []
  patterns: [bytearray-secret-zeroization, reference-not-secret-cli, env-var-deletion, path-traversal-guard-reuse]
key_files:
  created:
    - quirk/auth/__init__.py
    - quirk/auth/credentials.py
    - tests/test_credential_context.py
  modified:
    - quirk/config.py
decisions:
  - "CredentialContext stores secret as bytearray (D-04) with close() zeroization; best-effort caveat documented (D-05)"
  - "from_cli() accepts references only (@file/env-var-name/bare-prompt), never inline secrets; error text scrubbed via safe_str"
  - "_BLOCKED_PREFIXES guard imported from quirk.util.targets and applied before load_targets_file call (D-13/CR-09 reuse)"
  - "query_param() returns (name, secret) tuple for api_key_query scheme; as_headers() returns {} for that scheme (D-03)"
  - "enable_authenticated_mode bool=False added to ConnectorsCfg before _user_set_fields (AUTH-01)"
metrics:
  duration: "178 seconds"
  completed: "2026-05-23"
  tasks_completed: 3
  files_changed: 4
---

# Phase 93 Plan 01: Credential Infrastructure Core Summary

Ephemeral credential subsystem core: `CredentialContext` bytearray-backed value object with `as_headers()` / `query_param()` materialization at the httpx boundary, `close()` zeroization, and `from_cli()` reference-resolution builder with env-var deletion and `@file` path-guard reuse.

## What Was Built

### Task 1 + 2: CredentialContext dataclass and from_cli() (TDD)

**quirk/auth/__init__.py** — empty package init with `from __future__ import annotations` only.

**quirk/auth/credentials.py** — `CredentialContext` dataclass (199 lines):
- `scheme` field: `"bearer" | "api_key_header" | "api_key_query" | "basic"`
- `_secret_buf: bytearray` with `repr=False, compare=False` — secret never surfaces in repr/logs
- `as_headers()`: materializes str secret only at injection boundary; returns `{}` for `api_key_query`
- `query_param()`: returns `(param_name, secret)` tuple for `api_key_query`; `None` for all other schemes
- `close()`: zeroes buffer in-place via `self._secret_buf[:] = b"\x00" * n`
- `__enter__` / `__exit__`: context manager calling `close()` on exit
- `from_cli()`: classmethod resolving references with precedence prompt > env > @file/flag; inline secrets rejected with ValueError guidance; consumed env vars deleted; error text scrubbed via `safe_str`

Security invariants enforced:
- D-14: zero `quirk.scanner.*` imports (prevents circular deps when captured into `run_scan.py` closures)
- LEAK-03: `safe_str` imported and used for ValueError message scrubbing
- D-13/CR-09: `_BLOCKED_PREFIXES` + CWD-descent check applied before `load_targets_file` call (reuses v4.8 guard)
- D-04: bytearray storage, single str materialization only inside `as_headers()`/`query_param()`
- PITFALLS Pitfall 1: `del os.environ[ref]` after consumption prevents subprocess inheritance

**tests/test_credential_context.py** — 22 unit tests covering all scheme/method combinations, zeroization after close(), context manager, repr sentinel absence, from_cli @file/env/None/ValueError paths.

### Task 3: enable_authenticated_mode opt-in flag

**quirk/config.py** — appended `enable_authenticated_mode: bool = False` to `ConnectorsCfg` before `_user_set_fields`, with comment referencing AUTH-01 and D-11 / QRK-SCHED-AUTH-001 scheduler-rejection invariant.

## Verification Results

- `python -m pytest tests/test_credential_context.py -q` — 22 passed
- `python -m compileall quirk/auth quirk/config.py` — exit 0
- `grep -n "^from quirk.scanner|^import quirk.scanner" quirk/auth/credentials.py` — empty (D-14 clean)
- `grep -q "from quirk.util.safe_exc import safe_str" quirk/auth/credentials.py` — present (LEAK-03)
- `ConnectorsCfg().enable_authenticated_mode is False` — confirmed
- No new pip dependencies

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Path-traversal guard not triggered by load_targets_file alone**
- **Found during:** Task 2 TDD GREEN (test_at_file_blocked_prefix failing)
- **Issue:** `load_targets_file()` itself doesn't apply the path-traversal + blocked-prefix guard — that logic lives in `parse_target_tokens()`. The plan described "reuse load_targets_file + path-traversal guard" but the guard needed to be called explicitly before delegating to `load_targets_file`.
- **Fix:** Imported `_BLOCKED_PREFIXES`, `RC_PATH_TRAVERSAL`, `RC_PATH_NOT_ALLOWED_PREFIX` from `quirk.util.targets` and applied the same CWD-descent + blocked-prefix checks in `_resolve_reference()` before calling `load_targets_file()`.
- **Files modified:** `quirk/auth/credentials.py`
- **Commit:** 7e74541

**2. [Rule 2 - Missing functionality] Task 1 and Task 2 merged into single TDD cycle**
- **Found during:** Plan read — Task 1 (dataclass shape) and Task 2 (from_cli) share the same file and their tests are inseparable at the RED phase.
- **Fix:** Wrote all tests (Task 1 + Task 2 coverage) in the RED commit, then implemented both the dataclass and `from_cli()` in the GREEN commit. Task 2 has no separate artifact commit since it was co-developed with Task 1.
- **Impact:** Single feat commit covers both tasks; TDD RED→GREEN sequence still respected.

## Known Stubs

None — all public methods wired to real implementations; no placeholders or TODOs that block plan's goal.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes beyond what is declared in the plan's threat model. The `_BLOCKED_PREFIXES` guard + `TargetFileError` propagation directly address T-93-04. T-93-01 through T-93-05 mitigations are present in the implementation.

## Self-Check: PASSED

- quirk/auth/__init__.py: FOUND
- quirk/auth/credentials.py: FOUND (199 lines, > 80 min)
- tests/test_credential_context.py: FOUND
- quirk/config.py contains enable_authenticated_mode: FOUND
- Commit 69679ed (TDD RED): FOUND
- Commit 7e74541 (feat CredentialContext): FOUND
- Commit 804c84d (feat enable_authenticated_mode): FOUND
