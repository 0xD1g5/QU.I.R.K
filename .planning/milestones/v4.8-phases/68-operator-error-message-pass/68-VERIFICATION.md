---
phase: 68-operator-error-message-pass
verified: 2026-05-14T19:30:00Z
status: passed
score: 6/6
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 5/6
  gaps_closed:
    - "All CLI error exits emit [QRK-*] format via format_error() from quirk/errors.py — server.py import restored and INSTALL-004 inline string replaced with format_error() call"
  gaps_remaining: []
  regressions: []
---

# Phase 68: Operator Error-Message Pass — Verification Report

**Phase Goal:** Every operator-facing error in QU.I.R.K. emits a stable `QRK-<DOMAIN>-NNN` error
code, a one-line cause, and a one-line remediation hint. A central `quirk/errors.py` registry is
the single source of truth. A `quirk errors` CLI command exists for operator reference.
`docs/error-codes.md` is auto-generated and CI-gated.

**Verified:** 2026-05-14T19:30:00Z
**Status:** passed
**Re-verification:** Yes — after gap closure (previous status: gaps_found, 5/6)

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `quirk errors` prints a Rich table of all QRK codes | VERIFIED | `run_errors()` in `quirk/cli/errors_cmd.py` renders a Rich table; `--domain` filter confirmed working |
| 2 | `quirk errors --dump-md` generates `docs/error-codes.md` | VERIFIED | `_dump_markdown()` produces Markdown; `diff <(python run_scan.py errors --dump-md) docs/error-codes.md` is clean |
| 3 | All CLI error exits emit `[QRK-*]` format via `format_error()` | VERIFIED | `quirk/dashboard/server.py` now imports `from quirk.errors import format_error` at line 8; INSTALL-002 path uses `format_error("INSTALL-002")` at line 22; INSTALL-004 OSError path uses `format_error("INSTALL-004").replace("<port>", str(port))` at line 48 |
| 4 | All dashboard 4xx/5xx use `format_error` in detail string | VERIFIED | `auth.py` 401, `csrf.py` 403, `rate_limit.py` 429, `scan.py` DASHBOARD-004..007, `jobs.py` DASHBOARD-008, `qramm.py` DASHBOARD-009..011, `schedules.py` SCHED-002..004, `pdf.py` DASHBOARD-012/013 — all confirmed |
| 5 | `tests/test_install_errors.py` exists with install-day smoke tests | VERIFIED | File exists; 4 non-slow unit tests cover INSTALL-003, INSTALL-006, INSTALL-007, regex shape; 2 slow subprocess tests cover INSTALL-004 and INSTALL-002 |
| 6 | CI gate prevents `docs/error-codes.md` drift | VERIFIED | `tests/test_error_codes_freshness.py` included in `.github/workflows/python-staleness.yml` at line 32 |

**Score:** 6/6 truths verified

---

## Gap Closure Evidence (Re-verification Focus)

The single BLOCKER from the initial verification was confined to `quirk/dashboard/server.py`. Both
defects are now fixed:

**Fix 1 — Missing import restored**

- `quirk/dashboard/server.py` line 8: `from quirk.errors import format_error`
- Previously absent; caused a `NameError` at runtime when uvicorn was not installed (INSTALL-002 path)

**Fix 2 — INSTALL-004 inline string replaced**

- `quirk/dashboard/server.py` line 48: `print(format_error("INSTALL-004").replace("<port>", str(port)), file=sys.stderr)`
- Previously an f-string: `f"[QRK-INSTALL-004] Port {port} is already in use. Fix: ..."`
- Registry cause text is canonical ("Dashboard port is already in use."); the fix text `lsof -i :<port>` is correctly parameterized by the `.replace()` call

**Fix 3 — DASHBOARD-013 added to registry**

- `quirk/errors.py` lines 134-138: `DASHBOARD-013` — "PDF export failed due to an unexpected error."
- `quirk/dashboard/api/routes/pdf.py` line 115 uses `format_error("DASHBOARD-013")` in the generic `except Exception` handler

**Output verification:**

```
format_error("INSTALL-002") ->
  [QRK-INSTALL-002] Dashboard extras not installed. Fix: Run `pip install quirk[dashboard]` then retry `quirk serve`.

format_error("INSTALL-004").replace("<port>", "8512") ->
  [QRK-INSTALL-004] Dashboard port is already in use. Fix: Run `lsof -i :8512` to find the conflicting process, or use `quirk serve --port <other>`.

format_error("DASHBOARD-013") ->
  [QRK-DASHBOARD-013] PDF export failed due to an unexpected error. Fix: Check server logs for the full traceback and file an issue if reproducible.
```

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `quirk/errors.py` | Central registry; `format_error()`; 38+ codes | VERIFIED | 38 codes across 9 domains (DASHBOARD-013 added); `format_error()` returns `[QRK-<code>] <cause> Fix: <fix>`; frozen dataclass |
| `quirk/cli/errors_cmd.py` | `run_errors()` with table/filter/lookup/dump-md | VERIFIED | All four modes implemented and substantive |
| `run_scan.py` | `errors` subcommand wired; INSTALL-001/003 via format_error | VERIFIED | Lines 457-460 intercept `errors` subcommand; INSTALL-001/003 wired |
| `quirk/cli/doctor_cmd.py` | Failure returns use `format_error()` via `_BINARY_TO_CODE` | VERIFIED | INSTALL-005..009 all via `format_error()` |
| `quirk/cli/schedule_cmd.py` | SCHED-001..004 on validation failures | VERIFIED | All four codes via `format_error()` |
| `quirk/util/optional_extra.py` | Missing-extra advisory uses `format_error("INSTALL-001")` | VERIFIED | Line 225 confirmed |
| `quirk/scanner/kerberos_scanner.py` | Impacket-missing uses `format_error("INSTALL-001")` | VERIFIED | Line 250 confirmed |
| `quirk/dashboard/server.py` | Port-conflict shows `[QRK-INSTALL-004]`; uvicorn-missing shows `[QRK-INSTALL-002]` | VERIFIED | Import at line 8; INSTALL-002 at line 22; INSTALL-004 at line 48 with port substitution |
| `quirk/dashboard/api/middleware/auth.py` | 401 uses `format_error` | VERIFIED | `format_error("DASHBOARD-001")` confirmed |
| `quirk/dashboard/api/middleware/csrf.py` | 403 uses `format_error` | VERIFIED | `format_error("DASHBOARD-002")` confirmed |
| `quirk/dashboard/api/middleware/rate_limit.py` | 429 uses `format_error` | VERIFIED | `format_error("DASHBOARD-003")` confirmed |
| `quirk/dashboard/api/routes/scan.py` | HTTPException details are format_error | VERIFIED | DASHBOARD-004..007 confirmed |
| `quirk/dashboard/api/routes/jobs.py` | HTTPException details are format_error | VERIFIED | DASHBOARD-008 confirmed |
| `quirk/dashboard/api/routes/qramm.py` | HTTPException details are format_error | VERIFIED | DASHBOARD-009..011 confirmed |
| `quirk/dashboard/api/routes/schedules.py` | HTTPException details are format_error | VERIFIED | SCHED-002..004 confirmed |
| `quirk/dashboard/api/routes/pdf.py` | HTTPException details are format_error for both 503 and 500 paths | VERIFIED | DASHBOARD-012 at lines 42 and 110; DASHBOARD-013 at line 115 |
| `docs/error-codes.md` | Exists and matches generator output | VERIFIED | `diff <(python run_scan.py errors --dump-md) docs/error-codes.md` — clean |
| `tests/test_errors.py` | Exists and covers registry contract | VERIFIED | 9 non-slow tests; all pass |
| `tests/test_install_errors.py` | Exists with install-day smoke tests | VERIFIED | 4 non-slow unit tests + 2 slow subprocess tests |
| `tests/test_error_codes_freshness.py` | Exists and gated in CI | VERIFIED | 3 tests; included in `python-staleness.yml` |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `run_scan.py` | `quirk/cli/errors_cmd.py` | `argv[1] == "errors"` intercept | WIRED | Lines 457-460 import and call `run_errors()` |
| `quirk/dashboard/server.py` | `quirk/errors.py` | `format_error()` call | WIRED | `from quirk.errors import format_error` at line 8; called at lines 22 and 48 |
| `quirk/util/optional_extra.py` | `quirk/errors.py` | `format_error("INSTALL-001")` | WIRED | Line 45 import; line 225 call |
| `quirk/cli/doctor_cmd.py` | `quirk/errors.py` | `_BINARY_TO_CODE` dispatch | WIRED | Line 20 import; multiple call sites |
| `quirk/cli/schedule_cmd.py` | `quirk/errors.py` | validation failure exits | WIRED | Line 16 import; lines 41/46/68/102/139/160 calls |
| Dashboard routes | `quirk/errors.py` | `HTTPException(detail=format_error(...))` | WIRED | auth, csrf, rate_limit, scan, jobs, qramm, schedules, pdf all confirmed |
| `tests/test_error_codes_freshness.py` | CI (`python-staleness.yml`) | listed in test run command | WIRED | Line 32 of workflow file |

---

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `quirk errors` prints Rich table | `python run_scan.py errors --domain INSTALL` | Rich table with QRK-INSTALL-001..010 rendered | PASS |
| `quirk errors --dump-md` generates Markdown | `python run_scan.py errors --dump-md` | Full Markdown with all domains | PASS |
| `docs/error-codes.md` matches generator | `diff <(python run_scan.py errors --dump-md) docs/error-codes.md` | No diff | PASS |
| `format_error()` wire format correct | `python3 -c "from quirk.errors import format_error; print(format_error('INSTALL-001'))"` | `[QRK-INSTALL-001] Optional scanner package not installed. Fix: ...` | PASS |
| `server.py` INSTALL-002 import | `python3 -c "import quirk.dashboard.server"` | No error — module loads cleanly | PASS |
| `server.py` INSTALL-004 port substitution | `python3 -c "from quirk.errors import format_error; print(format_error('INSTALL-004').replace('<port>', '8512'))"` | `[QRK-INSTALL-004] Dashboard port is already in use. Fix: Run \`lsof -i :8512\`...` | PASS |
| DASHBOARD-013 format | `python3 -c "from quirk.errors import format_error; print(format_error('DASHBOARD-013'))"` | `[QRK-DASHBOARD-013] PDF export failed due to an unexpected error. Fix: Check server logs...` | PASS |

---

## Test Run Results

Command: `python -m pytest tests/test_errors.py tests/test_errors_cmd.py tests/test_install_errors.py tests/test_error_codes_freshness.py tests/test_api_auth.py tests/test_jobs_api.py tests/test_qramm_router.py tests/test_schedules_api.py tests/test_qramm_multiplier.py tests/test_scan_robustness.py tests/test_pdf_export.py -q -m "not slow"`

Result: **114 passed, 6 deselected in 2.37s**

The 6 deselected tests are `@pytest.mark.slow` subprocess tests. Two of those slow tests
(`test_port_conflict_format`, `test_dashboard_missing_uvicorn_format`) directly exercise the
`server.py` paths that were broken in the initial verification and are now fixed.

---

## Requirements Coverage

| Requirement | Description | Status | Evidence |
|-------------|-------------|--------|----------|
| UX-01 | All operator-facing error paths use `format_error()`; wire format `[QRK-<code>] <cause> Fix: <fix>` | SATISFIED | All paths including `quirk/dashboard/server.py` now use `format_error()`. Import confirmed at line 8; INSTALL-002 at line 22; INSTALL-004 at line 48. |
| UX-02 | Install-day failure scenarios (missing extra, missing binary, port conflict, unreadable db) emit structured `QRK-INSTALL-NNN` codes | SATISFIED | INSTALL-001 (missing-extra), INSTALL-002 (missing-uvicorn), INSTALL-003 (unreadable db), INSTALL-004 (port conflict), INSTALL-006/007/008 (missing binaries) — all via `format_error()`. |

---

## Anti-Patterns Found

None. The two BLOCKER/WARNING patterns identified in the initial verification have been resolved:

- `quirk/dashboard/server.py` line 8: import is present
- `quirk/dashboard/server.py` line 48: INSTALL-004 uses `format_error()` with port substitution

---

## Human Verification Required

None. All must-haves are programmatically verified.

---

## Summary

The single BLOCKER from the initial verification (`quirk/dashboard/server.py` missing the
`format_error` import and constructing INSTALL-004 inline) has been fully resolved. The fix is
correct at both levels:

1. The import is present (`from quirk.errors import format_error` at module level, before `serve()`).
2. The INSTALL-004 OSError handler delegates to `format_error("INSTALL-004").replace("<port>", str(port))`, producing a canonical cause text and an actionable, port-parameterized fix hint.

DASHBOARD-013 was also added to the registry and is used by `pdf.py`'s generic exception handler,
closing the coverage gap for unexpected PDF export failures.

All 6 success criteria are satisfied. The phase goal is achieved.

---

_Verified: 2026-05-14T19:30:00Z_
_Verifier: Claude (gsd-verifier)_
