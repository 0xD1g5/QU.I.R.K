---
phase: 22-v42-gap-closure
plan: 01
subsystem: cbom
tags: [cbom, kerberos, saml, dnssec, identity, builder, run_scan]

requires:
  - phase: 20-kerberos-scanner
    provides: Kerberos scanner producing KERBEROS protocol endpoints with etype names in cert_pubkey_alg
  - phase: 19-saml-oidc-scanner
    provides: SAML scanner producing SAML protocol endpoints with key_alg or SHA1 in cert_pubkey_alg
  - phase: 18-dnssec-scanner
    provides: DNSSEC scanner producing DNSSEC protocol endpoints

provides:
  - Identity scanner blocks in run_scan.py use correct logger variable (no NameError on invocation)
  - CBOM builder Pass 2 skips SAML and KERBEROS endpoints (no spurious X.509 certificate components)
  - CBOM builder Pass 3 skips SAML and KERBEROS endpoints (no spurious crypto/protocol/tls/ components)
  - 7 new CBOM builder tests covering SAML and Kerberos algorithm registration and protocol/cert isolation

affects:
  - cbom
  - identity-surface
  - dashboard

tech-stack:
  added: []
  patterns:
    - "Identity protocol (SAML, KERBEROS) endpoints are skipped in Pass 2 (cert) and Pass 3 (protocol) — algorithm registration in Pass 1 is their only CBOM contribution"
    - "Synthetic identity findings (kerberos-unreachable) excluded from algorithm registration via explicit string check"

key-files:
  created:
    - tests/test_cbom_builder.py (7 new test functions added)
  modified:
    - run_scan.py
    - quirk/cbom/builder.py
    - tests/test_cbom_builder.py

key-decisions:
  - "SAML and KERBEROS added to Pass 2 skip list — neither protocol sets cert_subject/cert_issuer/cert_sig_alg/cert_not_before/cert_not_after; cert_pubkey_alg for these protocols holds etype names or SHA1 URI findings, not X.509 cert algorithms"
  - "SAML and KERBEROS added to Pass 3 skip list — identity protocols are not TLS/SSH network protocols; their cryptographic posture is captured in Pass 1 algorithm components only"

patterns-established:
  - "New identity protocols added to builder.py must be explicitly excluded from Pass 2 (cert) and Pass 3 (protocol) skip lists to prevent CBOM misclassification"

requirements-completed:
  - DNSSEC-04
  - SAML-05
  - KERB-04

duration: 8min
completed: 2026-04-15
---

# Phase 22 Plan 01: v4.2 Identity Crypto Gap Closure Summary

**Fixed 3 runtime bugs blocking identity scans: main_logger NameError in run_scan.py, spurious TLS protocol components for SAML/Kerberos in CBOM builder Pass 3, and spurious X.509 certificate components for SAML/Kerberos in Pass 2; confirmed by 7 new targeted CBOM builder tests.**

## Performance

- **Duration:** 8 min
- **Started:** 2026-04-15T17:22:00Z
- **Completed:** 2026-04-15T17:30:45Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Replaced all 6 occurrences of undefined `main_logger` with `logger` in run_scan.py identity scanner blocks (DNSSEC, SAML, Kerberos) — closes DNSSEC-04 NameError crash
- Added `KERBEROS` and `SAML` to Pass 2 certificate skip list in builder.py — prevents hollow X.509 `crypto/certificate/` components for protocols that carry etype names or SHA-1 URI findings rather than cert metadata
- Added `SAML` and `KERBEROS` to Pass 3 protocol skip list in builder.py — prevents spurious `crypto/protocol/tls/` components for identity protocols that are not TLS
- 7 new CBOM builder tests covering both protocols (algorithm registration, no-TLS-protocol, no-certificate, unreachable-exclusion) all pass GREEN

## Task Commits

1. **Task 1: Fix main_logger NameError and add SAML/KERBEROS to builder.py skip lists** - `ed6b925` (fix)
2. **Task 2: Add CBOM builder tests for SAML and Kerberos identity protocol endpoints** - `f62d2d2` (test)

## Files Created/Modified

- `run_scan.py` — Fixed 6 occurrences of `main_logger` → `logger` in DNSSEC, SAML, and Kerberos scanner blocks
- `quirk/cbom/builder.py` — Added `KERBEROS` and `SAML` to Pass 2 skip list (line 389); added `SAML` and `KERBEROS` to Pass 3 skip list (line 468)
- `tests/test_cbom_builder.py` — Added `_saml_endpoint()` and `_kerberos_endpoint()` helper factories; added 7 new test functions

## Decisions Made

- Pass 1 (algorithm registration) for SAML and KERBEROS was already correct in builder.py from prior phases — only Pass 2 and Pass 3 needed the skip list additions
- The `kerberos-unreachable` synthetic finding exclusion already existed in Pass 1 (from Phase 20); confirmed by `test_kerberos_unreachable_excluded` test passing GREEN

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. The pre-edit hook triggered repeatedly because it tracks per-file read state; the reads were completed in session before edits. All edits succeeded on first application.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All three v4.2 milestone gaps (DNSSEC-04, SAML-05, KERB-04) are closed
- Identity scans (DNSSEC, SAML, Kerberos) can now be invoked end-to-end without NameError crashes
- CBOM output for identity protocols contains only algorithm components — no spurious protocol/cert components
- Full test suite: 354 passed, 1 pre-existing failure (test_dashboard_wiring — unrelated), 0 new failures
- 27 CBOM builder tests pass (20 pre-existing + 7 new)

## Self-Check

**Files exist:**
- `run_scan.py` — FOUND (modified)
- `quirk/cbom/builder.py` — FOUND (modified)
- `tests/test_cbom_builder.py` — FOUND (modified)

**Commits exist:**
- `ed6b925` — FOUND (fix(22-01): replace main_logger with logger...)
- `f62d2d2` — FOUND (test(22-01): add 7 CBOM builder tests...)

## Self-Check: PASSED

---
*Phase: 22-v42-gap-closure*
*Completed: 2026-04-15*
