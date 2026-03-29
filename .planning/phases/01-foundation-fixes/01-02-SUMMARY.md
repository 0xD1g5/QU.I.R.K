---
phase: 01-foundation-fixes
plan: 02
subsystem: scanner
tags: [ssh, ssh-audit, threading, concurrency, cbom, crypto-inventory]

# Dependency graph
requires:
  - phase: 01-foundation-fixes/01
    provides: No hard dependency — Plan 02 is wave-1, can run standalone

provides:
  - Threaded SSH scanner using ThreadPoolExecutor matching TLS scanner pattern
  - ssh-audit subprocess integration with full KEX/hostkey/MAC/encryption JSON output
  - CryptoEndpoint.ssh_audit_json TEXT column for storing full audit JSON
  - Graceful fallback to socket banner grab when ssh-audit is not installed
  - D-06 compliance: tls_version no longer misused for SSH data; cipher_suite="SSH" marker

affects:
  - 01-foundation-fixes/03 (sslyze integration — same scanner pattern)
  - 01-foundation-fixes/04 (package rename — will need to update imports)
  - Phase 02 (CBOM pipeline — ssh_audit_json feeds into algorithm enumeration for CBOM)

# Tech tracking
tech-stack:
  added:
    - concurrent.futures.ThreadPoolExecutor (SSH concurrency)
    - subprocess (ssh-audit -j JSON invocation)
    - shutil.which (ssh-audit availability detection)
    - pytest (added to .venv2 for test execution)
  patterns:
    - TDD Red-Green: tests written first (failing), then implementation to pass
    - ThreadPoolExecutor pattern mirroring tls_scanner.py exactly
    - Additive-only schema change (ssh_audit_json column, no migration)
    - Graceful subprocess fallback (ssh-audit absent → banner grab)

key-files:
  created:
    - tests/test_ssh_scanner.py
    - .gitignore
  modified:
    - qcscan/scanner/ssh_scanner.py
    - qcscan/models.py

key-decisions:
  - "D-04: ssh-audit invoked as subprocess with -j flag, not imported as library"
  - "D-05: Full ssh-audit JSON stored in single new TEXT column ssh_audit_json"
  - "D-06: tls_version NOT used for SSH data; cipher_suite='SSH' is the identifier"
  - "D-07: ThreadPoolExecutor replaces sequential loop in scan_ssh_targets"
  - "Banner stored in service_detail (not tls_version) in both ssh-audit and fallback paths"

patterns-established:
  - "SSH scanner pattern: ThreadPoolExecutor with cfg.scan.concurrency workers (matches TLS scanner)"
  - "ssh-audit subprocess: shutil.which check -> subprocess.run with -j -> json.loads"
  - "Scanner fallback: try advanced scanner first, catch all exceptions, fall back to basic"
  - "Additive schema: new v4.0 fields added after existing v3.6 fields with comment header"

requirements-completed: [CORE-04, SCAN-02]

# Metrics
duration: 3min
completed: 2026-03-29
---

# Phase 01 Plan 02: SSH Scanner Summary

**Threaded SSH scanner with ssh-audit subprocess integration storing full KEX/hostkey/MAC JSON in new ssh_audit_json column, replacing sequential banner-only scan**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-03-29T19:01:00Z
- **Completed:** 2026-03-29T19:04:27Z
- **Tasks:** 2 (Task 1: model, Task 2: TDD scanner rewrite)
- **Files modified:** 4 (models.py, ssh_scanner.py, test_ssh_scanner.py, .gitignore)

## Accomplishments

- Added `ssh_audit_json TEXT` column to `CryptoEndpoint` — additive-only schema change, no migration needed
- Rewrote `scan_ssh_targets()` to use `ThreadPoolExecutor(max_workers=cfg.scan.concurrency)` — matches TLS scanner pattern exactly
- Integrated ssh-audit subprocess (`-j` flag) via `_run_ssh_audit()` with full JSON output capture
- Implemented graceful fallback to socket banner grab when ssh-audit is not installed, with clear install instruction in log
- Eliminated `tls_version` misuse for SSH data (D-06) — banner now stored in `service_detail`
- 17 tests covering all required behaviors — all pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Add ssh_audit_json column to CryptoEndpoint** - `887bcf9` (feat)
2. **Task 2: TDD RED — failing tests for threaded SSH scanner** - `416558e` (test)
3. **Task 2: TDD GREEN — rewrite ssh_scanner.py** - `652ad36` (feat)
4. **Deviation: Add .gitignore** - `ec01cb3` (chore)

**Plan metadata:** (final commit below)

_Note: TDD task produced two commits: RED (test) then GREEN (feat)_

## Files Created/Modified

- `qcscan/models.py` - Added ssh_audit_json TEXT column after tls_enum_notes (v4.0 SSH audit fields section)
- `qcscan/scanner/ssh_scanner.py` - Full rewrite: ThreadPoolExecutor, _run_ssh_audit() subprocess, json storage, fallback
- `tests/test_ssh_scanner.py` - 17 tests covering ssh-audit success, fallback, timeout, thread pool, D-06 compliance
- `.gitignore` - New file: Python project .gitignore (Rule 2 deviation — missing critical project config)

## Decisions Made

- D-04: ssh-audit invoked as subprocess with `-j` for JSON, not imported as library (per locked decision)
- D-05: Full JSON stored in single `ssh_audit_json TEXT` column, no typed sub-columns (per locked decision)
- D-06: `tls_version` field NOT set for SSH endpoints; `cipher_suite="SSH"` is the identifier marker
- D-07: `ThreadPoolExecutor` replaces the sequential `for host, port in targets` loop

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added .gitignore**
- **Found during:** Task 2 (after verifying untracked files with `git status --short | grep '^??'`)
- **Issue:** Project had no .gitignore — generated files (.pyc, .venv2/, .claude/) were untracked
- **Fix:** Created comprehensive .gitignore for Python project covering __pycache__, venvs, Claude tooling, output dirs
- **Files modified:** .gitignore (new file)
- **Verification:** `git status --short | grep '^??'` shows only .gitignore remaining after creation
- **Committed in:** ec01cb3 (separate chore commit)

---

**Total deviations:** 1 auto-fixed (missing critical project config)
**Impact on plan:** .gitignore is essential for repository hygiene. No scope creep.

## Issues Encountered

- **Broken venv symlinks:** The project's `.venv/` was created on a different machine (path `/Users/digs/Repos/QuRisk/`) and had broken Python 3.14 symlinks. Created `.venv2/` with local Python 3.14 for test execution. The main venv issue pre-existed this plan.
- **grep -c acceptance criterion:** Plan specified `grep -cn "tls_version" qcscan/scanner/ssh_scanner.py returns 0`. Initial implementation had two comment lines containing "tls_version" for D-06 documentation. Rewrote comments to use "protocol version field" phrasing instead, achieving count=0 while retaining intent.

## Known Stubs

None — `ssh_audit_json` is populated from real ssh-audit subprocess output. The fallback path stores the actual banner string in `service_detail`. No placeholder values or hardcoded empty data.

## User Setup Required

None — no external service configuration required. ssh-audit absence is handled gracefully with fallback.

**Note for operators:** `ssh-audit` must be installed for full algorithm enumeration (`pip install ssh-audit` or OS package). Without it, the scanner falls back to banner-only with a log warning.

## Next Phase Readiness

- SSH scanner foundation ready for CBOM pipeline (Phase 02) — `ssh_audit_json` provides KEX, host-key, MAC, encryption algorithm data needed for CBOM component generation
- `CryptoEndpoint.ssh_audit_json` populated and queryable from DB
- Thread pool pattern established — Plan 03 (sslyze) follows identical concurrency model
- No blockers for Plans 03 or 04

---
*Phase: 01-foundation-fixes*
*Completed: 2026-03-29*
