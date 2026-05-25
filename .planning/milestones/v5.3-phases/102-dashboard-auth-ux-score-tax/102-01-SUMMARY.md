---
phase: 102-dashboard-auth-ux-score-tax
plan: "01"
subsystem: cli/auth
tags: [auth, token, cli, yaml, tdd]
dependency_graph:
  requires: []
  provides: [quirk.cli.token_cmd, AUTH-01]
  affects: [run_scan.py, quirk/dashboard/api/middleware/auth.py]
tech_stack:
  added: []
  patterns: [argparse-subparsers, yaml-round-trip-write-back, secrets.token_urlsafe, run_scan-interception-block]
key_files:
  created:
    - quirk/cli/token_cmd.py
    - tests/test_token_cmd.py
  modified:
    - run_scan.py
decisions:
  - "show reads YAML directly (not _get_configured_token) so operator sees persisted value, not env-var"
  - "generate and rotate share the same implementation path — both overwrite security.api_token with a fresh token"
  - "YAML write-back uses full yaml.safe_load -> update single key -> yaml.dump to prevent clobbering other config blocks"
  - "All imports (argparse, os, secrets, sys, yaml) at module scope to avoid local-import shadow trap"
metrics:
  duration: "~5 minutes"
  completed: "2026-05-25"
  tasks_completed: 2
  files_created: 2
  files_modified: 1
---

# Phase 102 Plan 01: AUTH-01 Token CLI Summary

**One-liner:** `quirk token` CLI (generate/rotate/show) using CSPRNG `secrets.token_urlsafe(32)` with full YAML round-trip write-back to `security.api_token`

## What Was Built

### Task 1: Failing AUTH-01 tests (RED)

Created `tests/test_token_cmd.py` with four test functions covering the complete AUTH-01 contract:

- `test_token_generate_writes_config` — generate writes a non-empty token to YAML
- `test_token_rotate_overwrites` — two generate calls produce different tokens
- `test_token_show` — show prints the persisted YAML token to stdout (not env-var)
- `test_token_generate_preserves_other_keys` — YAML round-trip preserves `assessment` and `targets` keys

Suite failed at import (RED) — `quirk.cli.token_cmd` did not yet exist.

**Commit:** `7445856` — `test(102-01): add failing AUTH-01 tests for token CLI (RED)`

### Task 2: Implementation (GREEN)

Created `quirk/cli/token_cmd.py` with:

- Module-scope imports only (`argparse`, `os`, `secrets`, `sys`, `yaml`) — local-import shadow trap prevention
- `run_token(argv: list[str]) -> None` — argparse entrypoint with three subcommands: generate, rotate, show
- `_write_token_to_config(config_path, token)` — YAML safe round-trip: load full file → update only `raw["security"]["api_token"]` → dump full dict
- generate/rotate: mint `secrets.token_urlsafe(32)`, call `_write_token_to_config`, print token + precedence note if `QUIRK_API_TOKEN` is set, `sys.exit(0)`
- show: read YAML directly, print full token (or "(no token configured)"), print precedence note when env-var is set, `sys.exit(0)` or `sys.exit(1)` on FileNotFoundError

Added interception block in `run_scan.py` after the `analyze-token` block (line 491):
```python
if len(_sys.argv) > 1 and _sys.argv[1] == "token":
    from quirk.cli.token_cmd import run_token
    run_token(_sys.argv[2:])
    return
```

All four tests pass (GREEN).

**Commit:** `7a96590` — `feat(102-01): implement quirk token CLI (AUTH-01) + run_scan.py interception`

## Deviations from Plan

None — plan executed exactly as written.

## TDD Gate Compliance

- RED gate: commit `7445856` (`test(102-01)`) — four tests fail at import
- GREEN gate: commit `7a96590` (`feat(102-01)`) — all four tests pass

## Threat Surface Scan

No new network endpoints, auth paths, or file access patterns beyond what the plan's threat model covers. `_write_token_to_config` writes only to an operator-supplied local path (T-102-02 mitigated by full round-trip). No external threat flags.

## Known Stubs

None.

## Self-Check

- [x] `quirk/cli/token_cmd.py` exists and compiles clean
- [x] `tests/test_token_cmd.py` exists with four named test functions
- [x] `run_scan.py` contains `_sys.argv[1] == "token"` interception block
- [x] Commits `7445856` (RED) and `7a96590` (GREEN) exist in git log
- [x] `python -m pytest tests/test_token_cmd.py -q` — 4 passed

## Self-Check: PASSED
