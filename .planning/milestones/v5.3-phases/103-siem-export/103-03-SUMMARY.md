---
phase: 103-siem-export
plan: "03"
subsystem: siem
tags: [siem, dispatcher, cef, export-cmd, run-scan, scheduler, tdd, siem-01, siem-02]
dependency_graph:
  requires: [103-01, 103-02]
  provides:
    - quirk.siem.dispatcher (export_findings, export_after_scan_hook)
    - quirk.cli.export_cmd (run_export, _find_latest_findings)
  affects:
    - run_scan.py (export interception block)
    - quirk/cli/scheduler_cmd.py (after-scan SIEM hook)
tech_stack:
  added: []
  patterns:
    - "Per-finding CEF event loop with per-send try/except (ISEC-03 whitelist applied inside build_cef_event)"
    - "Single-batch IntegrationDelivery audit row (destination='siem', finding_hash=None)"
    - "Deferred import + outer try/except in scheduler hook (isolation: SIEM failure never corrupts scan record)"
    - "QUIRK_CONFIG_PATH discipline — load_siem_config() called with no args from hook"
    - "run_scan.py subcommand interception block (argv[1]=='export')"
    - "_send_raw indirection for monkeypatching in tests"
key_files:
  created:
    - quirk/siem/dispatcher.py
    - quirk/cli/export_cmd.py
    - tests/test_siem_dispatcher.py
    - tests/test_siem_export_cmd.py
  modified:
    - run_scan.py
    - quirk/cli/scheduler_cmd.py
decisions:
  - "export_findings writes ONE IntegrationDelivery row per batch (not per finding) — finding_hash=None per plan spec (phases 104/105 add per-finding dedup)"
  - "_send_raw module-level indirection allows monkeypatching without patching the transport module's attribute directly"
  - "scan_id in export_after_scan_hook falls back to os.path.basename(output_path) when run.scan_id is None"
  - "export_findings returns success count (0 when all fail) — caller can detect partial failures"
metrics:
  duration_minutes: 4
  completed_date: "2026-05-25"
  tasks_completed: 3
  files_created: 4
  files_modified: 2
---

# Phase 103 Plan 03: SIEM Dispatcher + CLI Wiring Summary

**One-liner:** SIEM export dispatcher (per-finding CEF loop, single audit row, full failure isolation) wired to `quirk export --siem` CLI and scheduler after-scan hook, with run_scan.py interception completing the SIEM-01/02 integration seam.

## What Was Built

### Task 1: Failing tests — dispatcher + CLI wiring (RED)

Created `tests/test_siem_dispatcher.py` (6 tests) and `tests/test_siem_export_cmd.py` (6 tests). All 12 failed with `ImportError`/`ModuleNotFoundError` as expected — the dispatcher and export_cmd modules did not yet exist.

**test_siem_dispatcher.py tests:**
- `test_export_one_event_per_finding` — 3 findings → 3 `_send_raw` calls
- `test_audit_row_written` — one `IntegrationDelivery` row with `destination="siem"`, `finding_hash=None`, `status="ok"`
- `test_unreachable_endpoint` — OSError from `_send_raw` → `count=0`, `status="failed"` row, no exception raised
- `test_after_scan_hook_fires` — `export_after_scan=True` + findings-*.json present → `_send_raw` called
- `test_after_scan_hook_noop` — `export_after_scan=False` → `_send_raw` never called, no row written
- `test_hook_never_raises_on_bad_config` — `load_siem_config()=None` → clean no-op

**test_siem_export_cmd.py tests:**
- `test_no_flag_exits_1` — `run_export([])` → `SystemExit(1)` after print_help
- `test_no_flag_exits_1_unknown_flag` — unknown flags → non-zero exit
- `test_input_path_used` — `--siem --input PATH` is parsed without crash
- `test_find_latest_findings` — two findings files → newer chosen by `st_mtime`
- `test_run_scan_intercepts_export` — `argv[1]=="export"` routes to `run_export`
- `test_missing_findings_clear_error` — no findings file → non-zero exit, no traceback

### Task 2: Implement dispatcher.py and export_cmd.py (GREEN)

**quirk/siem/dispatcher.py:**
- `_send_raw()`: thin indirection over `send_syslog_raw` for monkeypatching in tests
- `_find_latest_findings_in(output_path)`: glob-based newest findings-*.json locator
- `export_findings(findings, cfg, db, scan_id)`: per-finding loop calling `build_cef_event` → `_send_raw`; collects errors per-finding; builds ONE `IntegrationDelivery` row after the loop (`status="ok"` if no errors, `"failed"` otherwise, `error_summary=safe_str("; ".join(errors))`); commits in its own `try/except`; returns success count; never raises
- `export_after_scan_hook(run, schedule, db)`: calls `load_siem_config()` (no args); guards on `cfg.export_after_scan`; locates findings JSON from `run.scan_output_path`; calls `export_findings`; entire body guarded by outer try/except (T-103-07)

**quirk/cli/export_cmd.py:**
- `_find_latest_findings(output_dir)`: `Path.glob("findings-*.json")` + `max(..., key=st_mtime)`
- `run_export(argv)`: argparse `prog="quirk export"` with `--siem` (store_true), `--input`, `--output-dir`; no-siem → `print_help() + sys.exit(1)`; missing file → `sys.exit(2)` with clear message; loads findings JSON; calls `load_siem_config()`; acquires DB session via `get_session`; calls `export_findings`; prints success count

All 12 tests pass; compileall clean.

### Task 3: Wire run_scan.py interception + scheduler after-scan hook

**run_scan.py** — added 4-line block after the `token` interception block (line ~494):
```python
# --- export subcommand: intercept before scan argparse (Phase 103 SIEM-01/02) ---
if len(_sys.argv) > 1 and _sys.argv[1] == "export":
    from quirk.cli.export_cmd import run_export
    run_export(_sys.argv[2:])
    return
```

**quirk/cli/scheduler_cmd.py** — added SIEM hook block after the Phase 101 notification hook (before `return run`), mirroring the exact try/except structure:
```python
# Phase 103 SIEM-01: after-scan SIEM export (when export_after_scan: true in [siem] config).
try:
    from quirk.siem.dispatcher import export_after_scan_hook
    export_after_scan_hook(run=run, schedule=schedule, db=db)
except Exception as exc:  # noqa: BLE001
    ...
    _logging.getLogger(__name__).warning("SIEM export error (scan record unaffected): %s", _safe_str(exc))
```

Full verification: 90/90 SIEM tests pass; compileall clean across all modified files.

## Deviations from Plan

None — plan executed exactly as written.

## TDD Gate Compliance

| Gate | Commit | Status |
|------|--------|--------|
| RED (test) | 3f20cea | 12 tests failing with ModuleNotFoundError |
| GREEN (feat) | 7b24ae2 | 12/12 tests pass, compileall clean |
| Task 3 (wire) | 7ec209b | 90/90 siem tests pass, compileall clean |

## Known Stubs

None. All functions are fully implemented and wired end-to-end.

## Threat Flags

No new threat surface beyond the plan's `<threat_model>`:
- T-103-07 (DoS isolation): mitigated — deferred import + try/except in scheduler + hook body; tested by `test_unreachable_endpoint` and `test_hook_never_raises_on_bad_config`
- T-103-08 (information disclosure): mitigated — all exception outputs routed through `safe_str`; no raw exc in logs or CLI output
- T-103-09 (repudiation): mitigated — one per-batch `IntegrationDelivery` row with `attempted_at` and `status`; tested by `test_audit_row_written`

## Self-Check: PASSED

Files exist:
- quirk/siem/dispatcher.py: FOUND
- quirk/cli/export_cmd.py: FOUND
- tests/test_siem_dispatcher.py: FOUND
- tests/test_siem_export_cmd.py: FOUND
- run_scan.py (export interception block): FOUND (grep run_export confirmed)
- quirk/cli/scheduler_cmd.py (SIEM hook): FOUND (grep export_after_scan_hook confirmed)

Commits exist:
- 3f20cea: FOUND (RED phase)
- 7b24ae2: FOUND (GREEN phase — dispatcher + export_cmd)
- 7ec209b: FOUND (wiring — run_scan.py + scheduler_cmd.py)
