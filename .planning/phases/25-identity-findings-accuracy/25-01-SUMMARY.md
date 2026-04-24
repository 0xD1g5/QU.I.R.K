---
phase: 25-identity-findings-accuracy
plan: "01"
subsystem: testing
tags: [tdd, pytest, identity, saml, oidc, kerberos, red-scaffold]

# Dependency graph
requires: []
provides:
  - "RED test scaffold with 4 failing tests defining acceptance contract for Phase 25 identity fixes"
  - "Confirmed TLS-bleed bug: RS256 OIDC endpoint emits source='tls' FindingItem from _derive_findings"
  - "Confirmed RS-family gap: _derive_identity_findings emits nothing for RS256/RS384 OIDC endpoints"
  - "Confirmed pyproject.toml [identity] group missing ldap3>=2.9.1"
affects: [25-02, 25-03]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "_Ep dataclass fixture pattern extended with tls_version and tls_weak_ciphers_present fields"
    - "RED gate verification: all 4 tests FAIL before GREEN implementation in Plan 02"

key-files:
  created:
    - tests/test_identity_findings_accuracy.py
  modified: []

key-decisions:
  - "Include tls_version and tls_weak_ciphers_present in _Ep fixture so _derive_findings does not raise AttributeError on iteration"
  - "Test pyproject.toml with exact string match '\"ldap3>=2.9.1\"' to pin the required version format"
  - "Use pathlib.Path('pyproject.toml').read_text() (CWD-relative) matching Plan 02 implementation contract"

patterns-established:
  - "Phase 25 RED scaffold: 4-test class testing identity findings accuracy contract"

requirements-completed: [SAML-04, IDENT-02, IDENT-03, KERB-03]

# Metrics
duration: 8min
completed: 2026-04-24
---

# Phase 25 Plan 01: Identity Findings Accuracy — RED Scaffold Summary

**RED test scaffold establishing 4-test acceptance contract for RS-family OIDC routing, TLS-bleed guard, and ldap3 dependency fixes**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-04-24T22:40:00Z
- **Completed:** 2026-04-24T22:48:42Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Created `tests/test_identity_findings_accuracy.py` with 4 failing tests (RED gate)
- Confirmed TLS-bleed bug is live: RS256 OIDC endpoint produces `source='tls'` FindingItem from `_derive_findings`
- Confirmed RS-family gap is live: `_derive_identity_findings` returns empty list for RS256/RS384 OIDC endpoints
- Confirmed `pyproject.toml` [identity] group is missing `ldap3>=2.9.1`
- Zero regressions in existing 359-test suite (3 pre-existing failures, unchanged)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create RED test file with 4 failing tests** - `efd08fa` (test)

## Files Created/Modified

- `tests/test_identity_findings_accuracy.py` — 4-test RED scaffold covering SAML-04, IDENT-02, IDENT-03, KERB-03

## Decisions Made

- Extended `_Ep` fixture with `tls_version: Optional[str] = None` and `tls_weak_ciphers_present: bool = False` — required so `_derive_findings` iterates the fixture without AttributeError. The existing `test_identity_surface.py` dataclass lacks these fields, which would have caused ERROR (not FAIL) in the TLS-bleed test.
- Used exact string match `'"ldap3>=2.9.1"'` (with embedded double-quotes) to pin the expected format in pyproject.toml for the KERB-03 test.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. RED gate confirmed with all 4 tests failing for the correct reasons:
- `test_rs256_oidc_produces_identity_finding`: `AssertionError: 0 != 1` (RS256 falls through SAML branch)
- `test_rs384_oidc_produces_identity_finding`: `AssertionError: 0 != 1` (RS384 falls through SAML branch)
- `test_saml_endpoint_absent_from_tls_findings`: `AssertionError: 1 != 0` (TLS-bleed confirmed — RS256 emits source='tls' finding)
- `test_pyproject_ldap3_in_identity_extras`: `AssertionError: '"ldap3>=2.9.1"' not found` (only impacket in [identity])

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- RED gate established; Plan 02 can implement the three production fixes (RS-family OIDC routing, TLS-bleed guard, ldap3 dependency)
- Plan 02 GREEN gate: all 4 tests must PASS after implementation
- No blockers

---
*Phase: 25-identity-findings-accuracy*
*Completed: 2026-04-24*

## Self-Check: PASSED

- FOUND: tests/test_identity_findings_accuracy.py
- FOUND: .planning/phases/25-identity-findings-accuracy/25-01-SUMMARY.md
- FOUND: commit efd08fa (test task)
- FOUND: commit de35dd1 (metadata)
