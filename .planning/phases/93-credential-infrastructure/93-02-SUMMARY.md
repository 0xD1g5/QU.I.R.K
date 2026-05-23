---
phase: 93-credential-infrastructure
plan: "02"
subsystem: security-guards
tags: [safe_str, scrubbing, error-registry, scheduler, ast-gate, schema-gate]
dependency_graph:
  requires: []
  provides: [safe_str-api-key-shapes, SCHED-AUTH-001, scheduler-auth-rejection, credential-ast-gate, schema-column-gate]
  affects: [quirk/util/safe_exc.py, quirk/errors.py, quirk/cli/schedule_cmd.py, tests/test_scan_error_gate.py, tests/test_safe_exc.py]
tech_stack:
  added: []
  patterns: [re.compile-extend, yaml.safe_load-no-load_config, AST-walk-kwarg-gate, frozenset-deny-list]
key_files:
  created: []
  modified:
    - quirk/util/safe_exc.py
    - tests/test_safe_exc.py
    - quirk/errors.py
    - quirk/cli/schedule_cmd.py
    - tests/test_scan_error_gate.py
decisions:
  - "yaml.safe_load used in _config_has_authenticated_mode to avoid importing load_config and pulling scanner deps"
  - "CREDENTIAL_FIELD_NAMES check scoped to keyword args and dict-key string literals in json.dumps/model_dump (not all AST nodes) to avoid false positives on non-serialization contexts"
  - "Schema gate asserts quoted column literals in all of db.py (not just CREATE TABLE blocks) to keep the check simple and conservative"
metrics:
  duration: "~12 minutes"
  completed: "2026-05-23"
  tasks_completed: 3
  files_modified: 5
---

# Phase 93 Plan 02: Scrubbing and Regression-Guard Layer Summary

**One-liner:** Extended safe_str credential scrubbing to API-key/Basic shapes, registered QRK-SCHED-AUTH-001 + scheduler hard-rejection, and added AST+schema CI gates preventing credential field name leakage into serialization or DB columns.

## What Was Built

### Task 1: Extend safe_str() _SENSITIVE_PATTERNS for API-key + Basic shapes (D-08)

Four new `re.compile` entries appended to `_SENSITIVE_PATTERNS` in `quirk/util/safe_exc.py`:
- `X-Api-Key\s*:\s*\S+` (IGNORECASE) — API-key header shape
- `X-Auth-Token\s*:\s*\S+` (IGNORECASE) — auth token header shape
- `[?&](api_key|token|key|auth_token)=[^&\s]{8,}` (IGNORECASE) — query-param API key (D-03 surface)
- `Authorization:\s*Basic\s+[A-Za-z0-9+/]{8,}={0,2}` (IGNORECASE) — HTTP Basic payload

Six new corpus tests added to `tests/test_safe_exc.py` with sentinel value `QUIRK_SENTINEL_CRED_d41d8cd9`, one per new shape plus a case-insensitive variant. All 14 safe_exc tests pass.

**Commit:** 10c841b

### Task 2: Register QRK-SCHED-AUTH-001 and reject authenticated-mode in schedule add (D-11)

- Added `SCHED-AUTH-001` ErrorEntry to `quirk/errors.py` after the SCHED-004 entry
- Added `_config_has_authenticated_mode(config_path) -> bool` private helper to `quirk/cli/schedule_cmd.py` using `yaml.safe_load` (no `load_config` import)
- Added rejection branch in `_cmd_add` after cron validation: if `_config_has_authenticated_mode(args.config)` → print `[QRK-SCHED-AUTH-001]` message and `sys.exit(2)`
- Added `test_sched_auth_001_format_error()` in `tests/test_scan_error_gate.py` asserting both `QRK-SCHED-AUTH-001` and `Fix:` are present in the output

**Commit:** 4d887ed

### Task 3: Extend AST deny-list gate + add schema column-name gate (D-09)

Added `quirk/auth` to `SCANNER_DIRS` in `tests/test_scan_error_gate.py`.

Defined `CREDENTIAL_FIELD_NAMES = frozenset({"bearer", "api_key", "authorization", "token", "password", "credential", "secret", "key"})`.

New test `test_credential_field_names_not_in_serialization_calls()` walks all files in SCANNER_DIRS and fails if any `json.dumps` or `model_dump` call has a keyword arg or dict-key string literal whose lowercased name is in `CREDENTIAL_FIELD_NAMES`.

Positive self-test `test_credential_serialization_gate_catches_synthetic_violation()` proves a synthetic `json.dumps(token=...)` is flagged.

Negative self-test `test_credential_serialization_gate_negative_self_test()` proves `json.dumps({"host": ..., "port": ...})` is not flagged.

New test `test_no_credential_column_in_schema()` reads `quirk/db.py` and asserts no quoted column literal matching any `CREDENTIAL_FIELD_NAMES` field appears in the source.

All 14 test_scan_error_gate tests pass.

**Commit:** 65fbc3c

## Verification

```
python -m pytest tests/test_safe_exc.py tests/test_scan_error_gate.py -q
# 28 passed

python -c "from quirk.errors import format_error; print(format_error('SCHED-AUTH-001'))"
# [QRK-SCHED-AUTH-001] Authenticated scan configs cannot be scheduled...

python -m compileall quirk/errors.py quirk/cli/schedule_cmd.py quirk/util/safe_exc.py
# All OK
```

## Deviations from Plan

None - plan executed exactly as written.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes introduced. The `_config_has_authenticated_mode` helper reads the filesystem (YAML config) but is a read-only check within existing CLI invocation context — no new trust boundary.

## Known Stubs

None.

## Self-Check: PASSED

- quirk/util/safe_exc.py: FOUND
- quirk/errors.py: FOUND (SCHED-AUTH-001 entry)
- quirk/cli/schedule_cmd.py: FOUND (_config_has_authenticated_mode + rejection)
- tests/test_safe_exc.py: FOUND (14 tests)
- tests/test_scan_error_gate.py: FOUND (14 tests, CREDENTIAL_FIELD_NAMES)
- Commit 10c841b: FOUND
- Commit 4d887ed: FOUND
- Commit 65fbc3c: FOUND
