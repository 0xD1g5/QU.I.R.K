---
phase: 97-v5-1-tech-debt-cleanup
plan: "03"
subsystem: jwt-scanner, scheduler
tags: [security, fail-closed, tdd, credential-handling]
dependency_graph:
  requires: []
  provides: [jwt-scanner-param-guard, scheduler-parse-fail-closed]
  affects: [quirk/scanner/jwt_scanner.py, quirk/cli/schedule_cmd.py]
tech_stack:
  added: []
  patterns: [ValueError-rejection, fail-closed-control, TDD-RED-GREEN]
key_files:
  created:
    - tests/test_schedule_auth_reject.py
  modified:
    - quirk/scanner/jwt_scanner.py
    - quirk/cli/schedule_cmd.py
    - tests/test_jwt_scanner.py
decisions:
  - "D-03: _append_query_param raises ValueError (not Optional[str] return) so existing try/except in _fetch_jwks handles it cleanly without any new caller changes"
  - "D-05: os.path.exists guard added before parse attempt; non-dict YAML result returns True (fail closed) rather than False"
  - "Added module-level logging.getLogger(__name__) to jwt_scanner.py for structured warning on param conflict"
metrics:
  duration: "~25 minutes"
  completed: "2026-05-23"
  tasks_completed: 2
  files_changed: 4
---

# Phase 97 Plan 03: Fail-Closed Credential Fixes (D-03 / D-05) Summary

**One-liner:** Pre-existing query-param guard in jwt_scanner raises ValueError with scrubbed log; scheduler auth-reject parses any existing file and returns True on unclassifiable configs (fail-closed, D-11).

## What Was Built

### Task 1: Pre-existing-param guard in _append_query_param (D-03 / WR-04)

Added a guard to `quirk/scanner/jwt_scanner.py:_append_query_param` that detects any pre-existing key-param name (case-insensitively matched against `_KEY_PARAM_NAMES`) in the target URL before appending the operator secret. When a conflict is found:

- Emits a `logger.warning(...)` with `safe_str(url)` — the pre-existing value is scrubbed by `safe_str`'s `_SENSITIVE_PATTERNS` regex (the `[?&]api_key=...` pattern matches 8+ char values).
- Raises `ValueError` with a message referencing the conflicting key name and the scrubbed URL.
- The existing `except Exception: continue` at line 195 of `_fetch_jwks` catches it, so the conflicting target yields no endpoints and the next target proceeds normally.

Also added `import logging` and `logger = logging.getLogger(__name__)` at module level (jwt_scanner.py had no module-level logger previously).

Four new tests in `tests/test_jwt_scanner.py`:
- Test 1: `pytest.raises(ValueError)` on conflicting URL
- Test 2: `safe_str(exc)` of the ValueError does not contain the PROBED value
- Test 3: `scan_jwt_targets([conflicting_url, clean_url])` returns endpoints from clean_url only
- Test 4: Non-conflicting URL still gets param appended (happy path unchanged)

**Commits:** `736e4f6` (RED), `40557eb` (GREEN)

### Task 2: Parse-based fail-closed scheduler auth-reject (D-05 / WR-06)

Rewrote `quirk/cli/schedule_cmd.py:_config_has_authenticated_mode` to:

1. **Remove** the `.endswith((".yml", ".yaml"))` extension gate (line 33 in original).
2. **Add** `os.path.exists(config_path)` guard — returns `False` only for `None` or non-existent paths (not non-`.yml` paths).
3. **Attempt YAML parse** for any existing file regardless of extension.
4. **Fail closed** (return `True`) when the file exists but cannot be definitively classified as non-authenticated: `isinstance(data, dict)` fails (non-dict result), or `except Exception` fires (parse error).
5. Updated docstring to state the parse-based, fail-closed contract explicitly.

Four new tests in `tests/test_schedule_auth_reject.py`:
- Test 1: Extensionless auth config file returns `True` (scheduler rejects)
- Test 2: Non-existent path and `None` return `False`
- Test 3: Existing non-authenticated YAML dict returns `False`
- Test 4: Binary/garbage file and non-dict YAML both return `True` (fail closed)

**Commits:** `d175cb1` (RED), `3722587` (GREEN)

## Verification

```
python -m pytest tests/test_jwt_scanner.py tests/test_schedule_auth_reject.py -q
# 19 passed in 0.30s

python -m compileall quirk/scanner/jwt_scanner.py quirk/cli/schedule_cmd.py
# exit 0
```

All source assertions confirmed:
- `_append_query_param` pre-existing-param branch exists referencing `_KEY_PARAM_NAMES`
- Reject path logs via `safe_str(`
- `.endswith((".yml",` extension gate is absent from schedule_cmd.py
- `os.path.exists` gates the parse, returning False only for None/non-existent paths
- Parse-failure branch returns `True` (fail closed), not `False`

## Deviations from Plan

### Auto-additions (Rule 2)

**1. [Rule 2 - Missing] Added module-level logger to jwt_scanner.py**
- **Found during:** Task 1 implementation
- **Issue:** jwt_scanner.py had no module-level logger; the plan specified `logger.warning(...)` in the reject path. The existing pattern passed `logger` as a function parameter, but `_append_query_param` has no logger parameter and adding one would change the call signature unnecessarily.
- **Fix:** Added `import logging` and `logger = logging.getLogger(__name__)` at module level — standard Python pattern, zero behavior change to callers, enables structured warning on param conflict.
- **Files modified:** quirk/scanner/jwt_scanner.py

## Known Stubs

None.

## Threat Flags

No new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries beyond what the plan's threat model documents. T-97-06 through T-97-10 mitigations are implemented as specified.

## TDD Gate Compliance

- RED gate: `test(97-03)` commits present for both tasks (736e4f6, d175cb1)
- GREEN gate: `feat(97-03)` commits present for both tasks (40557eb, 3722587)
- Gate sequence validated.

## Self-Check: PASSED

Files exist:
- quirk/scanner/jwt_scanner.py: FOUND
- quirk/cli/schedule_cmd.py: FOUND
- tests/test_jwt_scanner.py: FOUND
- tests/test_schedule_auth_reject.py: FOUND

Commits exist:
- 736e4f6: FOUND (test RED task 1)
- 40557eb: FOUND (feat GREEN task 1)
- d175cb1: FOUND (test RED task 2)
- 3722587: FOUND (feat GREEN task 2)
