---
phase: 108-sensor-push-cli-windows-ci
plan: "01"
subsystem: util/notify/ticketing/scheduler/deps
tags: [stab-02, sensor-05, ssrf, posix, dependencies]
dependency_graph:
  requires: []
  provides:
    - quirk.util.no_redirect._NoRedirectHandler (STAB-02 single-source SSRF guard)
    - platformdirs>=4.3.0 core dep (SENSOR-05)
    - tenacity>=8.2.0 core dep (SENSOR-02)
    - zstandard>=0.22.0 core dep (SENSOR-02/03/04)
    - scheduler --scan-config arg + cfg.output.directory anchor (SENSOR-05)
    - scheduler SIGTERM platform guard (SENSOR-05)
  affects:
    - quirk/notify/channels/webhook.py (now imports _NoRedirectHandler)
    - quirk/ticketing/servicenow.py (now imports _NoRedirectHandler)
    - quirk/cli/scheduler_cmd.py (POSIX-ism fixes)
tech_stack:
  added: [platformdirs>=4.3.0, tenacity>=8.2.0, zstandard>=0.22.0]
  patterns:
    - Pure extraction refactor (no behavior change to _NoRedirectHandler)
    - Optional scan_config_path parameter threads through scheduler call chain
    - Platform guard (sys.platform != "win32") for SIGTERM registration
key_files:
  created:
    - quirk/util/no_redirect.py
    - tests/test_no_redirect_extraction.py
    - tests/test_scheduler_posix_fixes.py
  modified:
    - quirk/notify/channels/webhook.py
    - quirk/ticketing/servicenow.py
    - quirk/cli/scheduler_cmd.py
    - pyproject.toml
decisions:
  - "Added --scan-config arg to scheduler run subcommand to separate YAML config from DB path (research error: plan assumed config_path was YAML, it is SQLite DB path)"
  - "Used optional scan_config_path parameter with fallback to QUIRK_OUTPUT_DIR env var / 'output' for backward compat"
metrics:
  duration: "~25 minutes"
  completed: "2026-05-25"
  tasks_completed: 3
  files_changed: 7
---

# Phase 108 Plan 01: Cross-OS Prerequisites — _NoRedirectHandler Extraction + Deps + Scheduler Fixes Summary

**One-liner:** Single-source _NoRedirectHandler SSRF guard via STAB-02 extraction, three new core deps (platformdirs/tenacity/zstandard), and Windows-compatible scheduler (absolute output path + SIGTERM guard).

## What Was Built

### Task 1 — Extract _NoRedirectHandler to quirk/util/no_redirect.py (STAB-02)

Created `quirk/util/no_redirect.py` with the `_NoRedirectHandler(urllib.request.HTTPRedirectHandler)` class extracted verbatim from `webhook.py`. Both `webhook.py` and `servicenow.py` now import from this single module. The class behavior is byte-identical — `redirect_request()` still raises `urllib.error.HTTPError("Redirect blocked (SSRF guard)")` on any 3xx response.

- `quirk/util/no_redirect.py` — new single-source SSRF redirect guard
- `quirk/notify/channels/webhook.py` — removed local class definition; added `from quirk.util.no_redirect import _NoRedirectHandler`
- `quirk/ticketing/servicenow.py` — same replacement; updated T-105-04 docstring comment
- `tests/test_no_redirect_extraction.py` — two tests: import + subclass check; no-duplicate-definition check (reads source of both callers)

### Task 2 — Declare platformdirs, tenacity, zstandard in pyproject.toml core deps

Added three entries to `[project] dependencies` (NOT optional-dependencies):
- `platformdirs>=4.3.0` — SENSOR-05: cross-OS config/data dirs
- `tenacity>=8.2.0` — SENSOR-02: retry with exponential backoff
- `zstandard>=0.22.0` — SENSOR-02/03/04: zstd payload compression

All three verified absent before addition; all three `import` cleanly after `pip install -e .`.

### Task 3 — Fix scheduler_cmd.py POSIX-isms (SENSOR-05)

**Fix 1 (output path anchor):** Added `--scan-config` argument to `quirk scheduler run` subcommand. When provided, `load_config(scan_config_path)` yields `cfg.output.directory` as the absolute output base, replacing the CWD-relative `Path("output/scheduled")` construction. Fallback: `QUIRK_OUTPUT_DIR` env var or `"output"` when no scan config is supplied (preserves backward compat for existing tests and CLI usage).

The `scan_config_path` parameter is threaded from `run_scheduler` → `_check_and_dispatch_due` → `_dispatch_schedule` as an optional keyword argument with `None` default.

**Fix 2 (SIGTERM guard):** Wrapped `signal.signal(signal.SIGTERM, _handle_signal)` in `if sys.platform != "win32":`. SIGINT registration remains unconditional. `sys` was already imported.

Added `from quirk.config import load_config` to module imports (exactly once; was not previously imported).

Created `tests/test_scheduler_posix_fixes.py` with two comment-stripped static regression guards:
- `test_output_dir_anchored`: asserts `Path("output/scheduled")` absent and `cfg.output.directory` present
- `test_sigterm_guard`: asserts platform check and SIGTERM registration are adjacent in source

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Research error: config_path in _dispatch_schedule is the SQLite DB path, not YAML config**
- **Found during:** Task 3 implementation — calling `load_config(config_path)` on a `.db` file raised `UnicodeDecodeError` in existing tests
- **Issue:** The plan's context stated "config_path IS in scope; load_config(config_path) yields cfg" but the third parameter to `_dispatch_schedule` is `db_path` (the SQLite DB file), not the YAML scan config path
- **Fix:** Added `--scan-config` argument to the scheduler run subcommand; threaded `scan_config_path` through `_check_and_dispatch_due` and `_dispatch_schedule` as an optional parameter with `None` default for backward compatibility
- **Files modified:** `quirk/cli/scheduler_cmd.py`, `tests/test_scheduler_posix_fixes.py` (updated static assertion to match new code structure)
- **Commits:** e5622ef

## Known Stubs

None.

## Threat Flags

None — no new network endpoints, auth paths, or trust boundaries introduced. STAB-02 extraction is behavior-preserving; pyproject.toml dep additions are supply-chain-reviewed (all three packages >5 years old on PyPI, per plan's threat model accept disposition T-108-SC).

## Self-Check: PASSED
