---
phase: 57-scanner-security-hardening
plan: "04"
subsystem: scanner
tags: [saml, oidc, ssrf, security, url-allowlist, advisory, cryptoendpoint]

# Dependency graph
requires:
  - phase: 57-01
    provides: "quirk.util.url_allowlist.validate_external_url + ValidationResult"
  - phase: 57-02
    provides: "SecurityCfg.allow_internal_targets knob in quirk/config.py"
provides:
  - "SSRF-guarded SAML metadata fetcher rejecting RFC1918/loopback/link-local/file:///metadata IPs"
  - "ADVISORY_SAML_INTERNAL_TARGET constant for HIGH advisory CryptoEndpoint on opt-in internal fetches"
  - "scan_saml_targets allow_internal_targets kwarg propagated through call chain"
  - "run_scan.py wired to pass cfg.security.allow_internal_targets into scan_saml_targets"
  - "11 tests covering every forbidden category, opt-in, metadata-blocked-on-opt-in, advisory emission"
affects: [58-dashboard-api-hardening, 63-scheduled-continuous-scanning]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Module-level httpx import enables patch('quirk.scanner.saml_scanner.httpx') in tests"
    - "validate_external_url called BEFORE httpx.get — blocked URLs produce zero outbound requests"
    - "Advisory CryptoEndpoint shape: protocol=ADVISORY, service_detail=ADVISORY_SAML_INTERNAL_TARGET, severity=HIGH"
    - "Strict re-evaluation pattern: re-run validate_external_url with allow_internal=False to detect opt-in targets"

key-files:
  created:
    - tests/scanner/test_saml_hardening.py
  modified:
    - quirk/scanner/saml_scanner.py
    - run_scan.py

key-decisions:
  - "Move httpx import to module level (was lazy inside _fetch_metadata) to support test patching via patch('quirk.scanner.saml_scanner.httpx')"
  - "Advisory emission uses strict re-validation: call validate_external_url(url, allow_internal=False) after successful fetch to detect RFC1918/loopback/link-local opt-in targets"
  - "Metadata-service IPs (169.254.169.254, fd00:ec2::254) blocked unconditionally even when allow_internal_targets=True — this is enforced in validate_external_url itself"

patterns-established:
  - "SSRF guard pattern: call validate_external_url BEFORE any httpx.get; check result.ok; return None on block"
  - "Opt-in advisory pattern: strict re-validation to detect internal-IP fetches that succeeded only due to allow_internal=True"

requirements-completed: [HARDEN-SCAN-02]

# Metrics
duration: 15min
completed: 2026-05-09
---

# Phase 57 Plan 04: SAML Scanner SSRF Hardening Summary

**SAML metadata fetcher routes all outbound URLs through validate_external_url before httpx.get, blocking RFC1918/loopback/link-local/file:///metadata IPs by default and emitting a HIGH advisory CryptoEndpoint per internal target when operator opts in via allow_internal_targets**

## Performance

- **Duration:** 15 min
- **Started:** 2026-05-09T00:00:00Z
- **Completed:** 2026-05-09T00:15:00Z
- **Tasks:** 1 (TDD: RED + GREEN commits)
- **Files modified:** 3

## Accomplishments

- SAML metadata fetcher hardened against SSRF: every URL is validated by `validate_external_url` before any `httpx.get` call; blocked categories produce zero outbound HTTP requests
- Metadata-service IPs (169.254.169.254, fd00:ec2::254) blocked unconditionally even with `allow_internal_targets=True`, closing the cloud-credential exfiltration SSRF chain (T-57-11)
- Operator opt-in advisory: when `allow_internal_targets=True` and a target resolves to RFC1918/loopback/link-local, a HIGH advisory `CryptoEndpoint` with `service_detail="SAML/internal-target-fetched"` is emitted so the consulting deliverable surfaces every probed internal host
- `run_scan.py` wired to pass `cfg.security.allow_internal_targets` into `scan_saml_targets`
- 11 new TDD tests covering all forbidden categories, opt-in permission, metadata-blocked-on-opt-in, and advisory emission semantics; zero regression in 26 pre-existing SAML scanner tests

## Task Commits

1. **RED — failing tests** - `8b55fca` (test)
2. **GREEN — SSRF guard + advisory implementation** - `fbf3eaa` (feat)

## Files Created/Modified

- `quirk/scanner/saml_scanner.py` — Added module-level `httpx` import + `validate_external_url` import; added `ADVISORY_SAML_INTERNAL_TARGET` constant; hardened `_fetch_metadata` with SSRF guard; updated `scan_saml_targets` with `allow_internal_targets` kwarg and advisory emission
- `run_scan.py` — Added `allow_internal_targets=cfg.security.allow_internal_targets` to `scan_saml_targets` call
- `tests/scanner/test_saml_hardening.py` — New: 11 TDD tests for SSRF allowlist behaviors

## Decisions Made

- **Module-level httpx import:** The original code did `import httpx` lazily inside `_fetch_metadata`. Moved to module level (with `try/except ImportError`) to support `patch("quirk.scanner.saml_scanner.httpx")` in tests — this is the standard patching pattern for the project (mirrors JWT scanner hardening in plan 57-03)
- **Strict re-validation for advisory detection:** After `_fetch_metadata` returns content for an allow_internal_targets call, `scan_saml_targets` re-calls `validate_external_url(target_url, allow_internal=False)` to detect whether the successful fetch was to an internal IP. This avoids needing to thread internal-IP state through the return path of `_fetch_metadata`
- **Advisory emitted once per opt-in target:** The advisory `CryptoEndpoint` is added at the top of the target loop body before the parse phase, ensuring exactly one advisory per internal target regardless of how many SAML certificates or OIDC algorithms the document contains

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Moved httpx import to module level for test patchability**
- **Found during:** Task 1 GREEN phase (test run failure after implementation)
- **Issue:** Tests patching `quirk.scanner.saml_scanner.httpx` failed with `AttributeError: module does not have the attribute 'httpx'` because `httpx` was imported lazily inside `_fetch_metadata` (not a module-level attribute)
- **Fix:** Added `try: import httpx / except ImportError: httpx = None` at module level; removed lazy `import httpx` from inside `_fetch_metadata`
- **Files modified:** `quirk/scanner/saml_scanner.py`
- **Verification:** All 11 tests pass; `python -m compileall quirk/scanner/saml_scanner.py` exits 0
- **Committed in:** `fbf3eaa` (implementation commit, GREEN phase)

---

**Total deviations:** 1 auto-fixed (Rule 1 — bug fix)
**Impact on plan:** Essential for test correctness; no scope creep. Module-level import is strictly better than lazy import for patchability.

## Issues Encountered

None beyond the httpx lazy-import patching issue documented above.

## Known Stubs

None — all behaviors are fully implemented and tested.

## Threat Flags

No new threat surface introduced. This plan closes T-57-10 and T-57-11 from the plan's threat register. Residual risks documented in plan frontmatter (DNS rebinding, redirect-chasing) remain out of scope for v4.8.

## Next Phase Readiness

- HARDEN-SCAN-02 closed
- `ADVISORY_SAML_INTERNAL_TARGET` pattern established for future advisory-emitting scanners
- Wave 2 plans (57-05, 57-06) may proceed independently

---
*Phase: 57-scanner-security-hardening*
*Completed: 2026-05-09*
