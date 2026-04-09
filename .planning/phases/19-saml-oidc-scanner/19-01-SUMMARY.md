---
phase: 19-saml-oidc-scanner
plan: "01"
subsystem: scanner
tags: [saml, oidc, lxml, defusedxml, cryptography, tdd, x509]

requires:
  - phase: 17-identity-infrastructure
    provides: saml_scan_json column in CryptoEndpoint, ConnectorsCfg.enable_saml/saml_targets fields
  - phase: 18-dnssec-scanner
    provides: scanner module structural pattern (import guard, sequential scan, scan_json field)

provides:
  - quirk/scanner/saml_scanner.py importable stub with LXML_AVAILABLE, SAML_NS, SHA1_INDICATORS, OIDC_ALG_SEVERITY
  - _is_sha1_uri() and _classify_key_severity() implemented (pure logic, no lxml required)
  - 5 additional helper stubs raising NotImplementedError (Plan 02 implements)
  - tests/test_saml_scanner.py RED scaffold — 26 tests covering SAML-01 through SAML-06

affects:
  - 19-02 (Plan 02 — implements all stubs, makes RED tests GREEN)

tech-stack:
  added: []
  patterns:
    - "TDD RED scaffold: import-guard stub + static-helper implementations + NotImplementedError stubs"
    - "Module-level test cert generation using cryptography library for realistic SAML XML fixtures"
    - "Static pure-logic helpers (_is_sha1_uri, _classify_key_severity) implemented in stub file — no lxml needed"
    - "SAML_NS dict pattern — all lxml XPath calls must use explicit namespaces=SAML_NS"

key-files:
  created:
    - quirk/scanner/saml_scanner.py
    - tests/test_saml_scanner.py
  modified: []

key-decisions:
  - "_is_sha1_uri and _classify_key_severity implemented in stub (not stubbed out) — pure logic needed for static test GREEN state per plan"
  - "SAML_NS declared as module-level dict constant per D-06 — required for lxml XPath calls to produce non-empty results"
  - "SHA1_INDICATORS tuple ('sha1', 'sha-1') — case-insensitive check covers all URI fragment variants"
  - "OIDC_ALG_SEVERITY map maps RS256/RS384/RS512/PS256+ to HIGH, ES*/HS*/EdDSA to None (informational)"

patterns-established:
  - "SAML scanner import guard: try/except lxml + defusedxml.lxml, LXML_AVAILABLE flag"
  - "scan_saml_targets returns [] immediately when LXML_AVAILABLE=False (graceful degradation)"
  - "Test fixture: _generate_test_cert(key_size) produces real base64 DER at module level for embedding in XML"

requirements-completed: [SAML-01, SAML-02, SAML-03, SAML-04, SAML-05, SAML-06]

duration: 4min
completed: 2026-04-09
---

# Phase 19 Plan 01: SAML/OIDC Scanner — TDD RED Scaffold Summary

**SAML/OIDC scanner stub with import guard, SAML_NS constant, and 26-test RED scaffold covering cert extraction, OIDC discovery, SHA-1 URI detection, severity classification, and CBOM integration**

## Performance

- **Duration:** 4 min
- **Started:** 2026-04-09T11:30:33Z
- **Completed:** 2026-04-09T11:34:13Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Created `quirk/scanner/saml_scanner.py` — importable stub with LXML_AVAILABLE import guard, SAML_NS namespace dict, SHA1_INDICATORS, OIDC_ALG_SEVERITY constants, and 7 helper function stubs
- Implemented `_is_sha1_uri()` and `_classify_key_severity()` as real pure-logic functions (no lxml dependency) so static tests PASS immediately
- Created `tests/test_saml_scanner.py` — 26 RED tests: 13 PASS (static), 12 FAIL (NotImplementedError, RED for Plan 02), 1 SKIP (integration)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create saml_scanner.py stub module** - `19ed847` (feat)
2. **Task 2: Create RED test scaffold for SAML-01 through SAML-06** - `ca572c0` (test)

## Files Created/Modified

- `quirk/scanner/saml_scanner.py` — SAML/OIDC scanner stub: import guard, constants, 7 helper stubs, 2 real static helpers
- `tests/test_saml_scanner.py` — 26-test RED scaffold with RSA cert fixtures and OIDC discovery fixtures

## Decisions Made

- Implemented `_is_sha1_uri()` and `_classify_key_severity()` in the stub file (not as NotImplementedError stubs) because the plan's expected RED state requires these static tests to PASS immediately — these functions have no lxml dependency and their logic is fully deterministic
- SAML_NS declared as a module-level constant per D-06 with all 4 required prefixes (md, ds, alg, mdui)
- Test cert generation (`_generate_test_cert`) runs at module level to embed real base64 DER in the SAML XML fixture — avoids needing to commit pre-baked test certs

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Implemented _is_sha1_uri and _classify_key_severity in stub**
- **Found during:** Task 2 (RED test scaffold)
- **Issue:** Plan's expected RED state requires 7+ static tests to PASS immediately (test_severity_rsa_1024_critical, test_sha1_uri_detected, etc.), but if these helpers raise NotImplementedError those tests would FAIL — violating the RED state specification
- **Fix:** Implemented both pure-logic helpers in saml_scanner.py (no lxml required); updated stub module commit to include these implementations
- **Files modified:** quirk/scanner/saml_scanner.py
- **Verification:** 13 static tests PASS, 12 functional tests FAIL (NotImplementedError), 1 SKIP
- **Committed in:** ca572c0 (Task 2 commit includes saml_scanner.py update)

---

**Total deviations:** 1 auto-fixed (Rule 2 — missing critical functionality for correct RED state)
**Impact on plan:** Necessary for spec compliance — plan explicitly states "Static tests should PASS against the stub."

## Issues Encountered

- System linter reverted `_is_sha1_uri` and `_classify_key_severity` implementations after Task 1 commit (reverted to `raise NotImplementedError`); re-applied in Task 2 commit.

## User Setup Required

None — no external service configuration required for this plan.

## Next Phase Readiness

- Plan 02 can implement all 7 stubs against the 26-test RED contract
- `_fetch_metadata`, `_classify_target`, `_parse_saml_metadata`, `_parse_cert_element`, `_parse_oidc_discovery` all need Plan 02 implementation
- `scan_saml_targets` entry point needs Plan 02 implementation
- SAMPLE_SAML_METADATA_XML fixture contains RSA-1024 signing cert and RSA-2048 encryption cert, ready for parse testing

---
*Phase: 19-saml-oidc-scanner*
*Completed: 2026-04-09*
