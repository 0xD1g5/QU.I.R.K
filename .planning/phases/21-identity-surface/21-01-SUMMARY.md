---
phase: 21-identity-surface
plan: "01"
subsystem: testing
tags: [identity, kerberos, saml, dnssec, tdd, pydantic, typescript, schemas]

# Dependency graph
requires:
  - phase: 20-kerberos-scanner
    provides: Kerberos AS-REQ scanner with etype service_detail format
  - phase: 19-saml-oidc-scanner
    provides: SAML scanner with cert_pubkey_alg/cert_pubkey_size/service_detail fields
  - phase: 18-dnssec-scanner
    provides: DNSSEC scanner with cert_pubkey_alg RSASHA1/ECDSAP256SHA256/etc values
provides:
  - tests/test_identity_surface.py — 17-test RED scaffold for IDENT-01 through IDENT-04
  - IdentityFinding Pydantic model in quirk/dashboard/api/schemas.py
  - ScanLatestResponse.identity_findings field (backward compatible, default=[])
  - IdentityFinding TypeScript interface in src/dashboard/src/types/api.ts
  - ScanLatestResponse.identity_findings field in TypeScript
affects:
  - 21-identity-surface plan 02 (must implement evidence counters, scoring weights, _derive_identity_findings to make RED tests GREEN)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - TDD RED scaffold with conditional skipUnless for unimplemented functions (_HAS_DERIVE pattern)
    - Dataclass _Ep extended with service_detail field to mirror Kerberos/SAML/DNSSEC scanner output
    - IdentityFinding extends FindingItem contract with required algorithm: str field

key-files:
  created:
    - tests/test_identity_surface.py
  modified:
    - quirk/dashboard/api/schemas.py
    - src/dashboard/src/types/api.ts

key-decisions:
  - "IdentityFinding.algorithm is non-Optional str — every identity finding must name the weak algorithm"
  - "ScanLatestResponse.identity_findings defaults to [] for backward compatibility with existing API responses"
  - "Derivation tests use @skipUnless(_HAS_DERIVE) pattern to SKIP gracefully until Plan 02 implements _derive_identity_findings"
  - "pre-existing test_saml_scanner.py::test_signing_cert_rsa_1024_extraction failure (defused_ET bug) deferred — out of scope"

patterns-established:
  - "RED/SKIP separation: evidence/scoring tests are RED (KeyError), derivation tests SKIP (import guard) — different fail modes for different implementation phases"
  - "_Ep dataclass extended with service_detail to match scanner endpoint format for Kerberos/SAML/DNSSEC"
  - "_base_evidence_with_identity() helper provides baseline evidence dict with all three identity counters zeroed"

requirements-completed: [IDENT-01, IDENT-02, IDENT-03, IDENT-04]

# Metrics
duration: 3min
completed: 2026-04-10
---

# Phase 21 Plan 01: Identity Surface RED Scaffold Summary

**TDD RED scaffold for Kerberos/SAML/DNSSEC identity findings with IdentityFinding Pydantic model and TypeScript interface establishing the data contract for Plan 02 implementation**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-04-10T11:33:32Z
- **Completed:** 2026-04-10T11:36:14Z
- **Tasks:** 2
- **Files modified:** 3 (created 1)

## Accomplishments

- Created 17-test RED scaffold in `tests/test_identity_surface.py` covering IDENT-01 through IDENT-04 across 4 test classes
- Added `IdentityFinding` Pydantic model to `quirk/dashboard/api/schemas.py` with required `algorithm: str` field
- Extended `ScanLatestResponse` with backward-compatible `identity_findings: List[IdentityFinding] = []`
- Mirrored both additions as TypeScript interfaces in `src/dashboard/src/types/api.ts`
- Confirmed correct RED/GREEN/SKIP distribution: 9 FAILED, 3 PASSED, 5 SKIPPED

## Task Commits

Each task was committed atomically:

1. **Task 1: RED test scaffold for IDENT-01 through IDENT-04** - `974268d` (test)
2. **Task 2: IdentityFinding Pydantic model + TypeScript interface contract** - `d674769` (feat)

**Plan metadata:** committed separately in final docs commit

## Files Created/Modified

- `tests/test_identity_surface.py` — 17-test RED scaffold (IdentityEvidenceCounterTests x6, IdentityScoringTests x3, IdentityFindingModelTests x3, IdentityDerivationTests x5)
- `quirk/dashboard/api/schemas.py` — Added IdentityFinding model + identity_findings field on ScanLatestResponse
- `src/dashboard/src/types/api.ts` — Added IdentityFinding interface + identity_findings field on ScanLatestResponse

## Decisions Made

- `IdentityFinding.algorithm` is `str` (not `Optional`) — every identity finding must name the weak algorithm for the consultant report
- `ScanLatestResponse.identity_findings` defaults to `[]` — backward compatible so existing API consumers don't break
- Derivation tests use `@unittest.skipUnless(_HAS_DERIVE, ...)` pattern — tests skip cleanly when `_derive_identity_findings` doesn't exist in scan.py rather than erroring

## Deviations from Plan

None - plan executed exactly as written.

The pre-existing `test_saml_scanner.py::test_signing_cert_rsa_1024_extraction` failure (`defused_ET is not defined` — SAML scanner bug) was observed during regression check but is out of scope for this plan. Logged to deferred items.

## Issues Encountered

- Pre-existing: `test_saml_scanner.py::test_signing_cert_rsa_1024_extraction` fails with `NameError: name 'defused_ET' is not defined` in the SAML scanner. This was pre-existing before this plan's changes. Deferred.

## Known Stubs

None. All three test classes have correct import targets. The derivation tests are intentionally SKIP (not stubs) — they use `@skipUnless` to cleanly defer until Plan 02 adds `_derive_identity_findings`.

## Next Phase Readiness

- Plan 02 (evidence + scoring + derivation) can now implement against concrete failing tests
- Evidence counter tests RED: `build_evidence_summary` must return `identity_weak_etype_count`, `saml_weak_signing_count`, `dnssec_weak_algo_count`
- Scoring weight tests RED: `SCORE_WEIGHTS` must include `identity_kerberos_weak_etype_ratio`, `identity_saml_weak_signing_ratio`, `identity_dnssec_weak_algo_ratio`
- Derivation tests SKIP: `_derive_identity_findings` in `quirk/dashboard/api/routes/scan.py` needed to turn SKIP into GREEN
- No blockers for Plan 02 execution

---
*Phase: 21-identity-surface*
*Completed: 2026-04-10*
