---
phase: 25-identity-findings-accuracy
plan: "02"
subsystem: dashboard-api
tags: [identity, saml, oidc, kerberos, tls-bleed, bug-fix, green-gate]

# Dependency graph
requires: ["25-01"]
provides:
  - "RS256/RS384/RS512 OIDC endpoints produce IdentityFinding(source='saml', severity='HIGH') from _derive_identity_findings()"
  - "SAML/KERBEROS/DNSSEC endpoints produce zero FindingItem entries from _derive_findings()"
  - "pyproject.toml [identity] extras contains ldap3>=2.9.1 alongside impacket"
  - "All 4 Phase 25 RED tests pass GREEN"
affects: [25-03]

# Tech tracking
tech-stack:
  added:
    - "ldap3>=2.9.1 in [identity] extras (pyproject.toml)"
  patterns:
    - "OIDC_ALG_SEVERITY dict imported from saml_scanner into routes/scan.py for single-source RS-family detection"
    - "Broad identity protocol guard (D-03) as first statement in _derive_findings() loop body"
    - "RS-family OIDC check runs before SHA-1/weak-key fallthrough in SAML branch of _derive_identity_findings()"

key-files:
  created: []
  modified:
    - quirk/dashboard/api/routes/scan.py
    - pyproject.toml

key-decisions:
  - "D-01/D-02: OIDC_ALG_SEVERITY imported at module level into scan.py; RS-family check inserted as FIRST check in SAML branch (before SHA-1 and weak-key fallthrough)"
  - "D-03: Broad protocol guard uses inline proto variable (not module-level constant) per CONTEXT.md Claude's Discretion — sufficient for this guard"
  - "D-04: ldap3>=2.9.1 with no upper-bound pin per D-04 spec (no known conflict risk with impacket)"

requirements-completed: [SAML-04, IDENT-02, IDENT-03, KERB-03, INFRA-03]

# Metrics
duration: 6min
completed: 2026-04-24
---

# Phase 25 Plan 02: Identity Findings Accuracy — GREEN Implementation Summary

**Three surgical edits to scan.py and one line in pyproject.toml turn all 4 Phase 25 RED tests GREEN: RS-family OIDC routing via OIDC_ALG_SEVERITY, TLS-bleed guard, and ldap3 dependency**

## Performance

- **Duration:** ~6 min
- **Started:** 2026-04-24T22:48:00Z
- **Completed:** 2026-04-24T22:54:05Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Added `from quirk.scanner.saml_scanner import OIDC_ALG_SEVERITY` as module-level import in scan.py (D-01)
- Inserted RS-family OIDC check as the first check in the SAML branch of `_derive_identity_findings()` — uses `OIDC_ALG_SEVERITY.get(alg)` to detect RS256/RS384/RS512 and emits `IdentityFinding(source="saml", severity="HIGH")` (D-02)
- Added broad protocol guard at top of `for ep in endpoints:` loop in `_derive_findings()` — skips KERBEROS/SAML/DNSSEC endpoints entirely, preventing TLS-bleed (D-03)
- Added `"ldap3>=2.9.1"` to `[project.optional-dependencies].identity` in pyproject.toml alongside impacket (D-04)
- All 4 Phase 25 tests PASS GREEN: test_rs256_oidc, test_rs384_oidc, test_saml_tls_bleed, test_pyproject_ldap3
- Zero regressions: 363 passed, 3 pre-existing failures unchanged, 3 skipped

## Task Commits

Each task was committed atomically:

1. **Task 1: RS-family OIDC check + TLS-bleed guard in scan.py** — `5afb834` (feat)
2. **Task 2: ldap3>=2.9.1 in pyproject.toml** — `ec91d4b` (feat)

## Files Created/Modified

- `quirk/dashboard/api/routes/scan.py` — 3 surgical edits: module import (line 29), TLS-bleed guard (lines 50-55), RS-family OIDC check (lines 228-244)
- `pyproject.toml` — 1 line addition: `"ldap3>=2.9.1"` in [identity] extras

## Verification Results

All 6 acceptance checks pass:

1. GREEN gate: `python -m pytest tests/test_identity_findings_accuracy.py -v` → 4 PASSED
2. Regression gate: `python -m pytest tests/` → 363 passed, 3 pre-existing failed, 3 skipped, 0 new failures
3. Import check: `grep "from quirk.scanner.saml_scanner import OIDC_ALG_SEVERITY" scan.py` → line 29
4. Guard check: `grep 'proto in {"KERBEROS", "SAML", "DNSSEC"}' scan.py` → line 55
5. Dependency check: `grep '"ldap3>=2.9.1"' pyproject.toml` → match found
6. Compile check: `python -m compileall quirk/` → 0 errors

## Decisions Made

- RS-family OIDC check positioned as the FIRST check in the SAML branch (before SHA-1 and weak-key-size checks) for highest specificity — SHA-1 is not in OIDC_ALG_SEVERITY so it naturally falls through to the existing elif handler
- Protocol guard uses a locally-scoped `proto` variable (inline, not module-level constant) per CONTEXT.md "Claude's Discretion" ruling
- ES256/ES384/ES512/EdDSA/HS-family entries in OIDC_ALG_SEVERITY return None — these produce no finding (quantum-safe or symmetric, correct behavior)

## Deviations from Plan

None — plan executed exactly as written. All three edits matched the interface spec in the plan's `<interfaces>` section.

## Known Stubs

None. Both modified functions derive real findings from real endpoint data. No placeholder values or hardcoded empty results.

## Threat Flags

None. No new API routes, no new endpoints, no new external-facing attack surface. The TLS-bleed guard (T-25-03 mitigation) is implemented as specified.

---
*Phase: 25-identity-findings-accuracy*
*Completed: 2026-04-24*

## Self-Check: PASSED

- FOUND: quirk/dashboard/api/routes/scan.py (modified with 3 edits)
- FOUND: pyproject.toml (modified, contains ldap3>=2.9.1)
- FOUND: commit 5afb834 (Task 1 — scan.py)
- FOUND: commit ec91d4b (Task 2 — pyproject.toml)
- FOUND: 4/4 Phase 25 tests GREEN
- FOUND: 363 passed, 0 new regressions
