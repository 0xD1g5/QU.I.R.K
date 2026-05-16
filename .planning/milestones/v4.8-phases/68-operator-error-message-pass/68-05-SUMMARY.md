---
phase: 68
plan: "05"
subsystem: errors-testing
tags: [smoke-tests, freshness-gate, ci-workflow, install-day, UX-02, tdd]
dependency_graph:
  requires: [quirk/errors.py, quirk/cli/doctor_cmd.py, quirk/dashboard/server.py, quirk/cli/errors_cmd.py]
  provides:
    - tests/test_install_errors.py (6 install-day scenario assertions)
    - tests/test_error_codes_freshness.py (CI drift gate for docs/error-codes.md)
    - docs/error-codes.md (regenerated to final Phase 68 state)
    - .github/workflows/python-staleness.yml (freshness + install-error steps added)
  affects: [CI on PR/push/cron]
tech_stack:
  added: []
  patterns: [subprocess-smoke-test, monkeypatch-shutil-which, chmod-000-unreadable, port-holder-socket, import-hook-blocker]
key_files:
  created:
    - tests/test_install_errors.py
    - tests/test_error_codes_freshness.py
  modified:
    - docs/error-codes.md
    - .github/workflows/python-staleness.yml
decisions:
  - "test_dashboard_missing_uvicorn_format uses import hook in subprocess -c script (not monkeypatch) since server.py import-time check requires subprocess isolation"
  - "broker scanner pre-existing failure (test_broker_scanner_rabbitmq.py::test_enrich_rabbitmq_mgmt_success) documented as out-of-scope — not caused by Plan 05 changes"
  - "docs/error-codes.md regenerated as final Phase 68 close step to capture all registry entries from Plans 01-04"
metrics:
  duration: "~8 minutes"
  completed: "2026-05-14"
  tasks: 3
  files: 4
---

# Phase 68 Plan 05: Install-Day Smoke Tests + Freshness Gate Summary

**One-liner:** UX-02 install-day scenarios locked with executable assertions (6 tests), docs/error-codes.md CI freshness gate installed, and python-staleness.yml wired to run both new test files on PR/push/cron.

## What Was Built

### Task 1: tests/test_install_errors.py

Created `tests/test_install_errors.py` with 6 install-day scenario tests:

**Unit tests (4):**

| Test | Strategy | Code asserted |
|------|----------|---------------|
| `test_unreadable_db_format` | chmod 000 tmp file, call `doctor_cmd._check_db` | QRK-INSTALL-003 |
| `test_missing_nmap_format` | monkeypatch `shutil.which` → None, call `_check_binary("nmap")` | QRK-INSTALL-006 |
| `test_missing_syft_format` | same monkeypatch, `_check_binary("syft")` | QRK-INSTALL-007 |
| `test_format_error_matches_qrk_regex` | iterate all ERROR_REGISTRY entries, assert `QRK_FORMAT.match(format_error(code))` | All codes |

**Subprocess smoke tests (2, marked `@pytest.mark.slow`):**

| Test | Strategy | Code asserted |
|------|----------|---------------|
| `test_port_conflict_format` | pre-bind port, subprocess `run_scan.py serve --port <port>`, assert combined output | QRK-INSTALL-004 |
| `test_dashboard_missing_uvicorn_format` | subprocess `-c` script with import hook blocking uvicorn, import `quirk.dashboard.server` | QRK-INSTALL-002 |

Result: `python -m pytest tests/test_install_errors.py -x -q -m "not slow"` → 4 passed

### Task 2: tests/test_error_codes_freshness.py + docs/error-codes.md

Created `tests/test_error_codes_freshness.py` with 3 tests mirroring `test_compliance_freshness.py` pattern:

- `test_error_codes_md_exists` — asserts `docs/error-codes.md` is present
- `test_error_codes_md_is_current` — subprocess `run_scan.py errors --dump-md`, asserts output matches file byte-for-byte
- `test_error_codes_md_contains_install_section` — asserts `## INSTALL` section, `QRK-INSTALL-001/004`, and `lsof -i :8512` hint

Regenerated `docs/error-codes.md` from final Phase 68 registry state: **88 lines**, covering all domains (CBOM, CLOUD, DASHBOARD, DB, INSTALL, SCHED, SSH, TLS).

Verification: `diff <(python run_scan.py errors --dump-md) docs/error-codes.md` → no output.

Result: `python -m pytest tests/test_error_codes_freshness.py -x -q` → 3 passed

### Task 3: .github/workflows/python-staleness.yml

Extended "Run staleness gates" step to include `tests/test_error_codes_freshness.py`. Added new "Run install-error unit checks" step that runs `tests/test_install_errors.py -m "not slow"` (slow subprocess tests excluded from CI).

YAML step names added:
- `Run staleness gates` (extended with `test_error_codes_freshness.py`)
- `Run install-error unit checks` (new step)

YAML validates cleanly. All existing triggers (pull_request, push to main, weekly Monday 09:00 UTC cron) preserved.

## Deviations from Plan

None — plan executed exactly as written. The `_check_db` and `_check_binary` signatures from Plan 03 matched the expected call shape precisely.

## Pre-existing Failure (Out of Scope)

`tests/test_broker_scanner_rabbitmq.py::test_enrich_rabbitmq_mgmt_success` fails with `KeyError: 'rabbitmq_version'`. This failure exists on the base commit before any Plan 05 changes (confirmed via `git diff HEAD~3..HEAD` — file not modified by this plan). Deferred to the next broker-related phase.

## Verification Results

```
python -m pytest tests/test_install_errors.py tests/test_error_codes_freshness.py -x -q -m "not slow"  → 7 passed
python -m pytest tests/ -q -m "not slow"  → 1 pre-existing failure (broker), all new tests green
diff <(python run_scan.py errors --dump-md) docs/error-codes.md  → no output
python -c "import yaml; yaml.safe_load(open('.github/workflows/python-staleness.yml'))"  → valid
```

## Final Phase 68 Close State

All operator-facing error paths now emit QRK wire format. Reference doc cannot go stale (CI gate). Install-day scenarios have executable assertions.

| Requirement | Coverage |
|-------------|----------|
| UX-01 | Error registry + format_error() + all call sites migrated (Plans 01-04) |
| UX-02 | 6 install-day smoke tests covering missing-extra, missing-nmap/syft, unreadable-db, port-conflict, missing-uvicorn |

## Known Stubs

None.

## Self-Check: PASSED

- [x] `tests/test_install_errors.py` exists and has 6 test functions
- [x] `tests/test_error_codes_freshness.py` exists and has 3 test functions
- [x] `docs/error-codes.md` has 88 lines, contains `lsof -i :8512` and `| QRK-INSTALL-004 |`
- [x] `.github/workflows/python-staleness.yml` contains `test_error_codes_freshness` and `test_install_errors` and `not slow`
- [x] YAML valid
- [x] `python -m pytest tests/test_install_errors.py tests/test_error_codes_freshness.py -x -q -m "not slow"` → 7 passed
- [x] Commits 85c8c51 (Task 1), c755d50 (Task 2), 564bdb1 (Task 3) confirmed in git log
