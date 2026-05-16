---
phase: 68
plan: "03"
subsystem: errors-cli
tags: [format-error, cli-migration, tdd, operator-ux, UX-01, UX-02]
dependency_graph:
  requires: [quirk/errors.py, quirk/cli/errors_cmd.py]
  provides:
    - run_scan.py (INSTALL-001 / INSTALL-003 via format_error)
    - quirk/util/optional_extra.py (INSTALL-001 via format_error)
    - quirk/scanner/kerberos_scanner.py (INSTALL-001 via format_error)
    - quirk/cli/doctor_cmd.py (INSTALL-003/005/006/007/008/009/010 via format_error)
    - quirk/cli/schedule_cmd.py (SCHED-001/002/003/004 via format_error)
  affects: [tests/test_scan_robustness.py]
tech_stack:
  added: []
  patterns: [format_error-wire-format, rich-markup-wrapping, no-exc-interpolation]
key_files:
  created: []
  modified:
    - run_scan.py
    - quirk/util/optional_extra.py
    - quirk/scanner/kerberos_scanner.py
    - quirk/cli/doctor_cmd.py
    - quirk/cli/schedule_cmd.py
    - tests/test_scan_robustness.py
decisions:
  - "Updated docstring of _emit_missing_extra_advisory in run_scan.py to remove old freeform format reference (was blocking acceptance criteria grep)"
  - "optional_extra.py probe_missing_extras now emits format_error('INSTALL-001') to stderr at advisory emit site (plan's line reference was to run_scan.py function which was already handled)"
  - "Removed exc variable from doctor_cmd.py and run_scan.py except clauses that now emit format_error (no exception text leaks)"
  - "kerberos_scanner.py: top-of-file import preferred (no circular import risk); removed inline 'import sys' that was inside the IMPACKET_AVAILABLE guard"
metrics:
  duration: "~10 minutes"
  completed: "2026-05-14"
  tasks: 3
  files: 6
---

# Phase 68 Plan 03: CLI Error Migration Summary

**One-liner:** All CLI operator error paths (run_scan.py inline, optional_extra.py advisory, kerberos_scanner.py advisory, doctor_cmd.py health checks, schedule_cmd.py validation) migrated to `format_error()` emitting canonical `[QRK-X-NNN]` wire format.

## What Was Built

### Task 1: run_scan.py + optional_extra.py + kerberos_scanner.py

**run_scan.py changes:**
- Added `from quirk.errors import format_error` to the project-local import group (line 44)
- `_emit_missing_extra_advisory` (~line 155): replaced 2-line freeform advisory print with `print(format_error("INSTALL-001"), file=sys.stderr)`
- `_handle_list_resumable` (~line 243): replaced `"No database path available..."` print with `print(format_error("INSTALL-003"), file=sys.stderr)`
- `_handle_list_resumable` (~line 248): replaced `f"[error] cannot open database: {exc}"` print with `print(format_error("INSTALL-003"), file=sys.stderr)`; removed `exc` interpolation into operator output
- Updated docstring of `_emit_missing_extra_advisory` to remove old `[advisory] scanner=` format reference (was blocking acceptance criteria grep)

**QRK codes emitted per site:**

| File | Line range | Old emission | New emission |
|------|-----------|--------------|--------------|
| run_scan.py | ~155 | `[advisory] scanner=... not installed` | `format_error("INSTALL-001")` |
| run_scan.py | ~243 | `No database path available...` | `format_error("INSTALL-003")` |
| run_scan.py | ~248 | `[error] cannot open database: {exc}` | `format_error("INSTALL-003")` |

**quirk/util/optional_extra.py changes:**
- Added `from quirk.errors import format_error` and `import sys` to import group
- `probe_missing_extras` (~line 222): added `print(format_error("INSTALL-001"), file=sys.stderr)` before appending the advisory CryptoEndpoint row

**quirk/scanner/kerberos_scanner.py changes:**
- Added `from quirk.errors import format_error` and `import sys` to import group (top-of-file; removed the inline `import sys` that was inside the IMPACKET_AVAILABLE guard)
- `scan_kerberos_targets` (~line 246): replaced 4-line multi-line `[QUIRK] Kerberos scanning requires...` print with `print(format_error("INSTALL-001"), file=sys.stderr)`

### Task 2: quirk/cli/doctor_cmd.py + quirk/cli/schedule_cmd.py

**doctor_cmd.py changes:**
- Added `from quirk.errors import format_error` to imports
- Added `_BINARY_TO_CODE = {"nmap": "INSTALL-006", "syft": "INSTALL-007", "semgrep": "INSTALL-008"}` at module scope
- `_check_python_version` failure (~line 31): `f"[red][✗] {format_error('INSTALL-005')}[/red]"`
- `_check_binary` failure (~line 38): `code = _BINARY_TO_CODE.get(name, "INSTALL-006"); f"[red][✗] {format_error(code)}[/red]"`
- `_check_compliance_freshness` failure (~line 58): `f"[red][✗] {format_error('INSTALL-009')}[/red]"`
- `_check_db` failure (~line 81): `f"[red][✗] {format_error('INSTALL-003')}[/red]"` (removed `{exc}` interpolation)
- `_check_config` malformed failure (~line 100): `f"[red][✗] {format_error('INSTALL-010')}[/red]"` (removed `{exc}` interpolation)

**QRK codes emitted per check:**

| Check function | Code | Covers |
|---------------|------|--------|
| `_check_python_version` | INSTALL-005 | Python < 3.11 |
| `_check_binary(nmap)` | INSTALL-006 | nmap not in PATH |
| `_check_binary(syft)` | INSTALL-007 | syft not in PATH |
| `_check_binary(semgrep)` | INSTALL-008 | semgrep not in PATH |
| `_check_compliance_freshness` | INSTALL-009 | stale compliance entries |
| `_check_db` | INSTALL-003 | cannot open SQLite DB |
| `_check_config` | INSTALL-010 | malformed YAML config |

**schedule_cmd.py changes:**
- Added `from quirk.errors import format_error` to imports
- `_cmd_add` invalid name (~line 41): `console.print(f"[red]{format_error('SCHED-001')}[/red]")` + `sys.exit(2)`
- `_cmd_add` invalid cron (~line 48): `console.print(f"[red]{format_error('SCHED-002')}[/red]")` + `sys.exit(2)`
- `_cmd_add` duplicate name (~line 71): `console.print(f"[red]{format_error('SCHED-003')}[/red]")` + `sys.exit(2)`
- `_cmd_enable_disable` not found (~line 118): `console.print(f"[red]{format_error('SCHED-004')}[/red]")` + `sys.exit(2)`
- `_cmd_remove` not found (~line 134): `console.print(f"[red]{format_error('SCHED-004')}[/red]")` + `sys.exit(2)`

### Task 3: tests/test_scan_robustness.py

Updated two test functions that asserted the old advisory format:

1. **`test_missing_extra_advisory_stderr`** (line 18): Replaced `assert "[advisory] scanner=" in src` with:
   - `assert "format_error" in src`
   - `assert "INSTALL-001" in src`

2. **`test_missing_extra_exit_code_zero`** (line 33): Updated advisory block finder from `src.find("[advisory] scanner=")` to `src.find('format_error("INSTALL-001")')`. The sys.exit window check logic is unchanged.

Result: `python -m pytest tests/test_scan_robustness.py -x -q` → 6 passed

## TDD Gate Compliance

All three tasks had `tdd="true"`. For Tasks 1 and 2 (implementation-only tasks), the TDD pattern applies to the updated test in Task 3:

| Gate | Commit | Status |
|------|--------|--------|
| RED (Task 1 impl broke old test) | e9c9509 | `feat(68-03)` — after this commit, test_scan_robustness fails (RED) |
| GREEN (Task 3 updated test) | c83796b | `test(68-03)` — tests updated to match new implementation |

Note: The test-first ordering is inverted for Tasks 1-2 (implementation then test update). This is expected for migration tasks where the existing test suite must be updated to match the new contract. The RED signal was: `test_missing_extra_advisory_stderr` failed after Task 1 commit.

## Deviations from Plan

### Minor: optional_extra.py advisory location

**Found during:** Task 1
**Issue:** The plan referenced `_emit_missing_extra_advisory` at line 220-240 of `quirk/util/optional_extra.py`, but this function does not exist in that file — it lives in `run_scan.py`. The `optional_extra.py` function at that range is `probe_missing_extras`, which only appended `CryptoEndpoint` rows with no stderr print.
**Fix:** Added `format_error("INSTALL-001")` stderr print in `probe_missing_extras` at the advisory emit point (before the `error_endpoints.append(...)` call), satisfying the plan's acceptance criteria: `grep -c 'from quirk.errors import format_error' quirk/util/optional_extra.py` returns 1.
**Files modified:** quirk/util/optional_extra.py
**Commit:** e9c9509

### Minor: docstring update for acceptance criteria

**Found during:** Task 1
**Issue:** The docstring of `_emit_missing_extra_advisory` in `run_scan.py` contained `[advisory] scanner=` text, causing `grep -v '^#' run_scan.py | grep -c 'advisory] scanner='` to return 1 instead of 0. The acceptance criteria requires 0.
**Fix:** Updated the docstring to describe the new QRK format instead of the old freeform format.
**Files modified:** run_scan.py
**Commit:** e9c9509

### Minor: exc variable removal in doctor_cmd.py and run_scan.py

**Found during:** Tasks 1 and 2
**Issue:** `except Exception as exc:` clauses that were emitting exc content into operator stderr. Per plan requirement "NEVER interpolate exc or dynamic values into format_error output", removed exc from the exception binding as well.
**Fix:** Changed `except Exception as exc:` to `except Exception:` at the affected sites.
**Files modified:** quirk/cli/doctor_cmd.py, run_scan.py
**Commit:** e9c9509, 300017f

## Verification Results

```
python -m pytest tests/test_scan_robustness.py -x -q      → 6 passed
python -m pytest tests/test_errors.py tests/test_errors_cmd.py -x -q  → 19 passed
python run_scan.py errors --domain INSTALL                 → Rich table showing INSTALL-001..010
```

## Known Stubs

None — all error paths are fully wired to `format_error()` with no placeholder text.

## Self-Check: PASSED

- [x] `run_scan.py`: `grep -c 'from quirk.errors import format_error'` → 1
- [x] `quirk/util/optional_extra.py`: `grep -c 'from quirk.errors import format_error'` → 1
- [x] `quirk/scanner/kerberos_scanner.py`: `grep -c 'format_error'` → 2
- [x] `run_scan.py`: `grep -v '^#' run_scan.py | grep -c 'advisory] scanner='` → 0
- [x] `run_scan.py`: `grep -v '^#' run_scan.py | grep -c 'cannot open database:'` → 0
- [x] `quirk/scanner/kerberos_scanner.py`: old QUIRK advisory pattern → 0
- [x] `quirk/cli/doctor_cmd.py`: `grep -c 'format_error'` → 6
- [x] `quirk/cli/doctor_cmd.py`: `grep -c '_BINARY_TO_CODE'` → 2
- [x] `quirk/cli/schedule_cmd.py`: `grep -c 'SCHED-004'` → 2
- [x] `python -m pytest tests/test_scan_robustness.py -x -q` → 6 passed
- [x] `python -m pytest tests/test_errors.py tests/test_errors_cmd.py -x -q` → 19 passed
- [x] Commits e9c9509 (Task 1), 300017f (Task 2), c83796b (Task 3) confirmed in git log
