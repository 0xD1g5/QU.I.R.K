---
phase: 08-legacy-debt-cleanup
plan: "03"
subsystem: core
tags: [dead-code, cleanup, bugfix, datetime, try-finally]
dependency_graph:
  requires: []
  provides: [D-09, D-10, D-11, D-12, D-13, D-15, D-17, D-19, D-20, D-21]
  affects: [quirk/assessment/migration_advisor.py, quirk/reports/writer.py, run_scan.py, quirk/logging_util.py, quirk/discovery/nmap_provider.py]
tech_stack:
  added: []
  patterns: [try/finally config restore, timezone-aware datetime]
key_files:
  created: []
  modified:
    - quirk/assessment/migration_advisor.py
    - run_scan.py
    - quirk/logging_util.py
    - quirk/discovery/nmap_provider.py
    - quirk/reports/writer.py
  deleted:
    - quirk/connectors/__init__.py
    - quirk/connectors/aws_stub.py
    - quirk/connectors/azure_stub.py
    - quirk/connectors/windows_adcs_stub.py
    - quirk/engine/rules.py
    - quirk/intelligence/driver_text.py
    - quirk/intelligence/calibration.py
    - data/_archive/qcscan-legacy.sqlite
decisions:
  - "D-09/10/11/12/19: Deleted all dead code artifacts; none were tracked by git (untracked files on disk)"
  - "D-15: migration_advisor 'deprecated tls' -> 'legacy tls' to match actual risk_engine finding title; removed dead 'public key' quantum pattern"
  - "D-17: TLS and SSH cfg.scan mutations wrapped in try/finally ensuring config always restored on exception"
  - "D-20: datetime.utcnow() replaced with datetime.now(timezone.utc) in logging_util.py and nmap_provider.py"
  - "D-21: tqdm=None assignment and dead if-tqdm/bar branch fully removed from run_scan.py"
  - "D-13: 4 dead writer.py functions removed (_count_findings, _extract_cert_dates, _is_self_signed, _mtls_present); _extract_cert_key_type preserved"
metrics:
  duration_minutes: 3
  completed_date: "2026-04-03"
  tasks_completed: 2
  files_changed: 8
---

# Phase 08 Plan 03: Dead Code Deletion and Code Quality Fixes Summary

**One-liner:** Deleted 8 dead code artifacts and fixed 5 code quality issues: wrong migration pattern strings, unguarded config mutations, deprecated datetime calls, dead tqdm branch, and 4 unused writer functions.

## What Was Built

### Task 1: Delete dead files and directories (D-09, D-10, D-11, D-12, D-19)

Removed all dead code artifacts that were never called, imported, or used:

- `quirk/connectors/` directory (4 files: `__init__.py`, `aws_stub.py`, `azure_stub.py`, `windows_adcs_stub.py`) — cloud connector stubs that were superseded by the real connectors in Phase 3; zero imports found in codebase
- `quirk/engine/rules.py` — reserved placeholder file with a comment, never imported
- `quirk/intelligence/driver_text.py` — `polish_drivers()` function never called; evidence key names mismatched
- `quirk/intelligence/calibration.py` — `get_calibration()` never called; references wrong config field name
- `data/_archive/qcscan-legacy.sqlite` — artifact from pre-rename package; untracked by git

All files were untracked by git. `quirk.engine` and `quirk.intelligence` imports verified clean after deletion.

### Task 2: Code quality fixes (D-13, D-15, D-17, D-20, D-21)

**D-15 — migration_advisor.py pattern fix (silent match failure):**
- `"deprecated tls"` changed to `"legacy tls"` — the actual finding title from `risk_engine.py` is `"Legacy TLS versions allowed (TLS 1.0/1.1)"` (lowercased to `"legacy tls"`); the old pattern never matched anything
- Removed dead `"public key"` pattern from quantum check — no finding title contains this string

**D-17 — cfg.scan mutation guarded with try/finally:**
- TLS scan phase: wrapped scan block in `try/finally` so `cfg.scan.timeout_seconds` and `cfg.scan.concurrency` are always restored even if `scan_tls_targets()` raises
- SSH scan phase: same pattern applied, ensuring both phases restore baseline config on exception

**D-20 — datetime.utcnow() modernization:**
- `quirk/logging_util.py`: `datetime.utcnow()` → `datetime.now(timezone.utc)`; added `timezone` to import
- `quirk/discovery/nmap_provider.py`: same replacement; added `timezone` to import
- Eliminates Python 3.12+ `DeprecationWarning: datetime.utcnow() is deprecated`

**D-21 — tqdm dead branch removal:**
- Removed `tqdm = None` assignment and its comment from `run_scan.py`
- Removed the entire `if tqdm: bar = tqdm(...)` / `else: bar = None` block and the `if bar: bar.update(1)` / `if bar: bar.close()` references in the fingerprinting phase
- `tqdm` was always `None` since the assignment; the branch was never executed

**D-13 — dead writer.py functions removed:**
- Removed `_count_findings()` — never called after intelligence layer replaced assessment scoring
- Removed `_extract_cert_dates()` — never called; cert date logic lives in report builders directly
- Removed `_is_self_signed()` — never called anywhere in codebase
- Removed `_mtls_present()` — never called anywhere in codebase
- Removed unused `Tuple` from typing import (was only used by `_extract_cert_dates`)
- **Kept** `_extract_cert_key_type()` — actively called in tech report builder for cert inventory table

## Deviations from Plan

### Parallel Agent Pre-Applied Changes

**Situation:** The 08-01 summary agent (running in parallel wave) included all Task 2 source file changes in its `docs(08-01)` commit (`d534bf2`) along with its own SUMMARY and STATE updates. When this agent went to commit Task 2 changes, git showed them already in HEAD.

**Impact:** All source code changes were verified correct against plan requirements. No code corrections needed. The functional outcome is identical.

**Task 1 note:** The dead code files (`quirk/connectors/`, `quirk/engine/rules.py`, etc.) were untracked by git — deletion succeeded on disk, but there were no git-tracked deletions to commit.

## Verification Results

All plan verification checks passed:

```
T1: All dead files/dirs removed
T1: Import verification PASSED
T2 D-15: migration_advisor patterns OK
T2 D-17, D-21: run_scan.py try/finally and tqdm cleanup OK
T2 D-20: logging_util datetime OK
T2 D-20: nmap_provider datetime OK
T2 D-13: writer.py dead functions removed OK
ALL CHECKS PASSED
```

- `python3 -m compileall` succeeded for all modified files
- `quirk.engine` and `quirk.intelligence` import cleanly after deletions

## Known Stubs

None — all changes are functional implementations or clean deletions.

## Self-Check: PASSED

- All dead files confirmed absent from disk
- `"legacy tls"` present in migration_advisor.py
- 2 `finally:` blocks present in run_scan.py
- No `utcnow` in source files
- No `tqdm = None` in run_scan.py
- `_extract_cert_key_type` present, 4 dead functions absent from writer.py
- Changes committed in `d534bf2` (pre-applied by parallel agent)
