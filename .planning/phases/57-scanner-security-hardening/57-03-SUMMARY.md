---
phase: 57-scanner-security-hardening
plan: "03"
subsystem: jwt-scanner
tags: [security-hardening, tls-verify, jwks, advisory, cr-01, harden-scan-01]
dependency_graph:
  requires: [57-01, 57-02]
  provides: [jwt-tls-verify-hardening, jwks-advisory-emission]
  affects: [quirk/scanner/jwt_scanner.py, run_scan.py]
tech_stack:
  added: []
  patterns:
    - "verify_tls keyword parameter pattern for httpx.get TLS control"
    - "Advisory CryptoEndpoint emission per unsafe JWKS URL fetch"
    - "Operator opt-out gated behind SecurityCfg.allow_insecure_jwks"
key_files:
  created:
    - tests/scanner/__init__.py
    - tests/scanner/test_jwt_hardening.py
  modified:
    - quirk/scanner/jwt_scanner.py
    - run_scan.py
    - .planning/ROADMAP.md
    - .planning/REQUIREMENTS.md
decisions:
  - "Refactored _fetch_jwks to return fetched_urls list so caller can emit one advisory per URL without duplicating URL-construction logic"
  - "Advisories emitted even when no JWKS keys are found (fetch was attempted with verify_tls=False)"
  - "Comment text reworded to avoid verify=False literal (keeps grep-based acceptance check clean)"
metrics:
  duration: "~12 minutes"
  completed: "2026-05-09"
  tasks_completed: 1
  files_changed: 6
---

# Phase 57 Plan 03: JWT Scanner TLS Verify Hardening Summary

**One-liner:** JWKS fetches in jwt_scanner.py now use `verify=True` by default; operator opt-out via `SecurityCfg.allow_insecure_jwks` is gated and emits one HIGH advisory `CryptoEndpoint` per affected JWKS URL (CR-01 / HARDEN-SCAN-01).

## What Was Built

### Task 1: JWT JWKS TLS Verify Hardening + Advisory Emission + D-11 ROADMAP Correction

**jwt_scanner.py signature changes:**

- `ADVISORY_JWKS_VERIFY_DISABLED = "JWKS/verify-disabled"` module-level constant added (D-09).
- `_fetch_jwks(base_url, timeout, *, verify_tls: bool = True)` — added `verify_tls` keyword param; both `httpx.get` calls now use `verify=verify_tls` (not `verify=False`); return tuple extended to `(keys, path, fetched_urls)` so callers receive the list of URLs actually fetched.
- `scan_jwt_endpoint(..., *, allow_insecure_jwks: bool = False)` — computes `verify_tls = not allow_insecure_jwks`; propagates into `_fetch_jwks`; appends one `CryptoEndpoint(protocol="ADVISORY", service_detail=ADVISORY_JWKS_VERIFY_DISABLED, severity="HIGH", scan_error_category="config")` per URL in `fetched_urls` when `allow_insecure_jwks=True`.
- `scan_jwt_targets(..., *, allow_insecure_jwks: bool = False)` — propagates flag to each `scan_jwt_endpoint` call.

**run_scan.py wiring:**

The existing `scan_jwt_targets` call at line 657 now passes `allow_insecure_jwks=cfg.security.allow_insecure_jwks` as a keyword argument.

**ROADMAP.md D-11 correction:**

Phase 57 success criterion #1 previously referenced `quirk/scanner/api_scanner.py` (incorrect — JWKS fetch lives in `jwt_scanner.py`). Corrected to `quirk/scanner/jwt_scanner.py`.

**REQUIREMENTS.md D-11 correction:**

HARDEN-SCAN-01 row previously referenced `quirk/scanner/api_scanner.py`. Corrected to `quirk/scanner/jwt_scanner.py`.

**TDD gate compliance:**

- RED commit `7bae51c`: `test(57-03): add failing tests for JWT JWKS TLS verify hardening (CR-01)` — ImportError on `ADVISORY_JWKS_VERIFY_DISABLED` confirmed failure.
- GREEN commit `81179bc`: `feat(57-03): harden JWT scanner JWKS TLS verify + advisory emission (CR-01/HARDEN-SCAN-01)` — 9/9 tests pass.

## Acceptance Criteria Verification

| Check | Expected | Result |
|-------|----------|--------|
| `verify=False` literals in jwt_scanner.py (non-comment) | 0 | 0 |
| `verify=verify_tls` occurrences | >= 2 | 2 |
| `ADVISORY_JWKS_VERIFY_DISABLED` occurrences | >= 2 | 3 |
| `allow_insecure_jwks` occurrences | >= 3 | 9 |
| `JWKS/verify-disabled` literal | >= 1 | 1 |
| `verify_tls: bool = True` in signature | >= 1 | 1 |
| `allow_insecure_jwks=cfg.security.allow_insecure_jwks` in run_scan.py | >= 1 | 1 |
| `api_scanner.py` in ROADMAP.md Phase 57 section | 0 | 0 |
| `jwt_scanner.py` in ROADMAP.md | >= 1 | 1 |
| `api_scanner.py` in REQUIREMENTS.md | 0 | 0 |
| `HARDEN-SCAN-01.*jwt_scanner.py` in REQUIREMENTS.md | 1 | 1 |
| `tests/scanner/test_jwt_hardening.py` pytest | 0 (exit) | PASS |
| `tests/test_jwt_scanner.py` pytest | 0 (exit) | PASS |
| `python -m compileall jwt_scanner.py run_scan.py` | 0 (exit) | PASS |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Comment text contained `verify=False` literal causing grep acceptance check to fail**

- **Found during:** Task 1 GREEN phase
- **Issue:** Three inline code comments used `verify=False` as explanatory text, causing `grep -E "verify=False" | grep -v '^#' | grep -c .` to return 3 instead of 0 (the `grep -v '^#'` only strips lines starting with `#`, not indented comments).
- **Fix:** Reworded comments to use `verify_tls=False` or equivalent phrasing without the `verify=False` literal.
- **Files modified:** `quirk/scanner/jwt_scanner.py`
- **Commit:** 81179bc (included in GREEN commit)

**2. [Rule 2 - Enhancement] _fetch_jwks refactored to return fetched_urls**

- **Found during:** Task 1 implementation
- **Decision:** Rather than duplicating URL-construction logic in `scan_jwt_endpoint` to track which URLs were fetched, `_fetch_jwks` was extended to return `fetched_urls: list[str]` as a third tuple element. This keeps URL construction in one place (plan's "Preferred approach").
- **Files modified:** `quirk/scanner/jwt_scanner.py`

## Known Stubs

None. All wiring is complete: `SecurityCfg.allow_insecure_jwks` flows from config -> `run_scan.py` -> `scan_jwt_targets` -> `scan_jwt_endpoint` -> `_fetch_jwks`.

## Threat Flags

No new network endpoints, auth paths, or file access patterns introduced beyond the plan's `<threat_model>` scope.

## Self-Check: PASSED

- `quirk/scanner/jwt_scanner.py` — FOUND
- `tests/scanner/test_jwt_hardening.py` — FOUND
- `tests/scanner/__init__.py` — FOUND
- RED commit `7bae51c` — FOUND
- GREEN commit `81179bc` — FOUND
- ROADMAP.md D-11 correction — FOUND (`jwt_scanner.py` at line 1205)
- REQUIREMENTS.md D-11 correction — FOUND (`jwt_scanner.py` at line 21)
- `run_scan.py` wiring — FOUND (`allow_insecure_jwks=cfg.security.allow_insecure_jwks`)
