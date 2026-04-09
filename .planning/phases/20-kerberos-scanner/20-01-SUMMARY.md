---
phase: 20-kerberos-scanner
plan: "01"
subsystem: scanner
tags: [kerberos, impacket, kdc, as-req, etype, tdd, red-scaffold]

# Dependency graph
requires:
  - phase: 17-identity-infrastructure
    provides: kerberos_scan_json column in CryptoEndpoint, enable_kerberos config flag
  - phase: 18-dnssec-scanner
    provides: import guard pattern, severity map pattern, scanner function signature
  - phase: 19-saml-oidc-scanner
    provides: LXML_AVAILABLE guard pattern, test scaffold structure with pytest.raises RED pattern
provides:
  - kerberos_scanner.py stub -- importable with IMPACKET_AVAILABLE guard, 7-entry KERBEROS_ETYPE_MAP
  - test_kerberos_scanner.py RED scaffold -- 24 tests defining full contract for Plan 02 implementation
affects: [20-02-kerberos-scanner-implementation, 21-identity-surface-dashboard]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - IMPACKET_AVAILABLE import guard mirrors DNSPYTHON_AVAILABLE/LXML_AVAILABLE pattern
    - KERBEROS_ETYPE_MAP dict maps int -> (name, severity) per D-08 through D-12
    - Functional RED tests patch IMPACKET_AVAILABLE=True to exercise stub NotImplementedError path
    - _derive_realm handles FQDN, two-label, IPv4, and single-label hostnames

key-files:
  created:
    - quirk/scanner/kerberos_scanner.py
    - tests/test_kerberos_scanner.py
  modified: []

key-decisions:
  - "Functional RED tests patch IMPACKET_AVAILABLE=True -- impacket not installed in dev env, stub must be reachable"
  - "_derive_realm IPv4 detection added: 4-part all-numeric splits return full address, not last 2 octets"

patterns-established:
  - "RED functional tests using pytest.raises(NotImplementedError, match='stub') with IMPACKET_AVAILABLE=True patch"
  - "KERBEROS_ETYPE_MAP etype int -> (name, severity) structure for Plan 02 classification use"

requirements-completed: [KERB-01, KERB-02, KERB-03, KERB-04, KERB-05]

# Metrics
duration: 3min
completed: 2026-04-09
---

# Phase 20 Plan 01: Kerberos Scanner RED Scaffold Summary

**TDD RED scaffold: importable kerberos_scanner.py stub with 7-entry KERBEROS_ETYPE_MAP and 24 RED tests defining AS-REQ probe, etype classification, LDAP degradation, and CBOM contract for Plan 02**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-09T12:39:58Z
- **Completed:** 2026-04-09T12:43:02Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Created `quirk/scanner/kerberos_scanner.py` -- importable stub with `IMPACKET_AVAILABLE` guard, 7-entry `KERBEROS_ETYPE_MAP` (DES=CRITICAL, RC4=HIGH, AES-128=HIGH, AES-256=SAFE), `ALL_ETYPES` constant, `_derive_realm()` fully implemented, all other functions stubbed with `NotImplementedError("stub")`
- Created `tests/test_kerberos_scanner.py` -- 24 tests covering KERB-01 through KERB-05: 23 pass, 1 skipped (integration); static map and `_derive_realm` tests pass directly; functional tests verify NotImplementedError via patched `IMPACKET_AVAILABLE=True`
- Established RED test contract for Plan 02: AS-REQ probe, UDP fallback, LDAP graceful degrade, CBOM endpoint structure, import guard behavior

## Task Commits

Each task was committed atomically:

1. **Task 1: Create kerberos_scanner.py stub** - `9470e6f` (feat)
2. **Task 2: Create test_kerberos_scanner.py RED scaffold** - `9397495` (test)

## Files Created/Modified

- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/quirk/scanner/kerberos_scanner.py` -- Kerberos scanner stub: import guard, KERBEROS_ETYPE_MAP, ALL_ETYPES, _derive_realm, stubbed functions
- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/tests/test_kerberos_scanner.py` -- 24 RED tests covering KERB-01 through KERB-05

## Decisions Made

- **Functional RED tests patch `IMPACKET_AVAILABLE=True`**: impacket is not installed in the dev environment (`IMPACKET_AVAILABLE=False`), so `scan_kerberos_targets()` would return `[]` without reaching the stub. All functional tests use `patch.object(kmod, "IMPACKET_AVAILABLE", True)` to exercise the `NotImplementedError` code path. Plan 02 tests will patch to specific behaviors.
- **`_derive_realm` IPv4 detection**: The plan's stub code `if len(parts) >= 2: return ".".join(parts[-2:]).upper()` would produce `"0.1"` for `"10.0.0.1"`. Added IP detection (4-part all-numeric) to return the full address uppercased, matching the acceptance criteria.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed `_derive_realm` IPv4 address handling**
- **Found during:** Task 1 verification
- **Issue:** Plan's stub code `".".join(parts[-2:]).upper()` returns `"0.1"` for `"10.0.0.1"` since an IPv4 has 4 parts and `>= 2` is true; joining last 2 gives last 2 octets, not the full address
- **Fix:** Added IPv4 detection check: if 4 parts and all are numeric, return full address uppercase; otherwise use domain-label logic
- **Files modified:** `quirk/scanner/kerberos_scanner.py`
- **Verification:** `_derive_realm("10.0.0.1") == "10.0.0.1"` confirmed in Task 1 verification
- **Committed in:** `9470e6f` (Task 1 commit)

**2. [Rule 1 - Bug] Patched `IMPACKET_AVAILABLE=True` in functional RED tests**
- **Found during:** Task 2 first test run
- **Issue:** All functional tests using `pytest.raises(NotImplementedError)` reported "DID NOT RAISE" because `IMPACKET_AVAILABLE=False` causes `scan_kerberos_targets()` to return `[]` before reaching the stub
- **Fix:** Added `with patch.object(kmod, "IMPACKET_AVAILABLE", True)` to all 12 functional RED tests
- **Files modified:** `tests/test_kerberos_scanner.py`
- **Verification:** All 23 tests pass, 1 skipped (integration), confirmed RED state
- **Committed in:** `9397495` (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (2 Rule 1 bugs)
**Impact on plan:** Both fixes required for correctness. The `_derive_realm` fix aligns with the acceptance criteria. The import guard patch is essential for RED tests to actually test the stub code path in a dev environment without impacket installed.

## Issues Encountered

None beyond the two auto-fixed issues above.

## Known Stubs

The following stubs exist by design (RED scaffold for Plan 02):

| File | Function | Reason |
|------|----------|--------|
| `quirk/scanner/kerberos_scanner.py` | `_build_as_req` | Plan 02 implements |
| `quirk/scanner/kerberos_scanner.py` | `_probe_kdc` | Plan 02 implements |
| `quirk/scanner/kerberos_scanner.py` | `_probe_kdc_udp` | Plan 02 implements |
| `quirk/scanner/kerberos_scanner.py` | `_probe_ldap_anon` | Plan 02 implements |
| `quirk/scanner/kerberos_scanner.py` | `scan_kerberos_targets` | Plan 02 implements |

These stubs are intentional -- this is the TDD RED scaffold plan. Plan 02 will turn RED to GREEN.

## Next Phase Readiness

- Plan 02 (`20-02`) can begin immediately -- test contract is fully established
- Plan 02 will implement `_build_as_req`, `_probe_kdc`, `_probe_kdc_udp`, `_probe_ldap_anon`, and `scan_kerberos_targets` against this test scaffold
- No new columns or config flags needed -- Phase 17 pre-wired `kerberos_scan_json` and `enable_kerberos`

---
*Phase: 20-kerberos-scanner*
*Completed: 2026-04-09*
