---
phase: 18-dnssec-scanner
plan: "01"
subsystem: scanner
tags: [dnssec, tdd, red-scaffold, dns, cryptography]
dependency_graph:
  requires: [phase-17-identity-infrastructure]
  provides: [DNSSEC-01-test-contract, DNSSEC-02-test-contract, DNSSEC-03-test-contract, DNSSEC-04-test-contract, DNSSEC-05-test-contract, DNSSEC-06-test-contract, DNSSEC-07-test-contract]
  affects: [quirk/scanner/dnssec_scanner.py, tests/test_dnssec_scanner.py]
tech_stack:
  added: [dnspython-import-guard, DNSSEC_ALG_MAP-constant]
  patterns: [tdd-red-scaffold, import-guard-DNSPYTHON_AVAILABLE, mock-based-dns-testing]
key_files:
  created:
    - quirk/scanner/dnssec_scanner.py
    - tests/test_dnssec_scanner.py
  modified: []
decisions:
  - "DNSSEC_ALG_MAP placed in dnssec_scanner.py (not classifier.py) for scanner self-containment — mirrors jwt_scanner HTTPX_AVAILABLE pattern"
  - "RFC 8624/9905 3-tier classification: CRITICAL (SHA-1/MD5/DSA/GOST), HIGH (RSA-only), SAFE (ECDSA/EdDSA) per D-04"
  - "patch target quirk.scanner.dnssec_scanner.dns.* — standard unittest.mock deep attribute patching for optional deps"
metrics:
  duration: 160
  completed_date: "2026-04-09"
  tasks_completed: 2
  files_changed: 2
---

# Phase 18 Plan 01: DNSSEC TDD RED Scaffold Summary

**One-liner:** TDD RED scaffold for DNSSEC scanner — 16 tests covering 7 requirements plus stub module with DNSPYTHON_AVAILABLE guard and DNSSEC_ALG_MAP constant (RFC 8624/9905).

## What Was Built

### Task 1: Stub Module (`quirk/scanner/dnssec_scanner.py`)

Created the DNSSEC scanner stub with:
- Module docstring per RFC 8624/9905 classification scope
- `DNSPYTHON_AVAILABLE` import guard (mirrors jwt_scanner.py `HTTPX_AVAILABLE` pattern)
- `DNSSEC_ALG_MAP` constant — 12 entries covering alg numbers 1, 3, 5, 6, 7, 8, 10, 12, 13, 14, 15, 16
- `scan_dnssec_targets()` entry point — returns `[]` if `DNSPYTHON_AVAILABLE = False`, raises `NotImplementedError` otherwise
- 7 internal helper stubs: `_resolve_ns`, `_query_rrset`, `_parse_dnskeys`, `_parse_ds_records`, `_check_chain`, `_detect_nsec_type`, `_scan_domain` — all raise `NotImplementedError("Plan 02 implements")`
- `from quirk.models import CryptoEndpoint` import (unconditional — models always available)

The stub is importable with `DNSPYTHON_AVAILABLE = False` (dnspython not yet installed). All function signatures match the contract specified in D-15 and the CONTEXT.md.

### Task 2: RED Test Scaffold (`tests/test_dnssec_scanner.py`)

Created 16 tests covering DNSSEC-01 through DNSSEC-07:

| Requirement | Tests | Status |
|-------------|-------|--------|
| DNSSEC-01 | `test_authoritative_ns_resolution`, `test_dnskey_query_do_bit` | FAIL (NotImplementedError/AttributeError) |
| DNSSEC-02 | `test_algorithm_classification_critical`, `test_algorithm_classification_critical_legacy`, `test_algorithm_classification_high`, `test_algorithm_classification_safe`, `test_algorithm_map_has_all_twelve_entries`, `test_rsasha1_produces_critical_finding` | 5 PASS (static map), 1 FAIL (functional) |
| DNSSEC-03 | `test_unsigned_zone` | FAIL |
| DNSSEC-04 | `test_cryptoendpoint_protocol_dnssec`, `test_dnssec_scan_json_populated` | FAIL |
| DNSSEC-05 | `test_nsec_detection_exposure`, `test_nsec3_no_exposure` | FAIL |
| DNSSEC-06 | `test_ds_chain_broken`, `test_ds_chain_valid` | FAIL |
| DNSSEC-07 | `test_chaos_lab_integration` | SKIPPED (no QUIRK_INTEGRATION_TESTS) |

**Final state: 10 FAILED, 5 PASSED, 1 SKIPPED — correct RED state.**

Mock helpers built:
- `_mock_dnskey(algorithm, flags, key_bytes)` — mock DNSKEY rdata
- `_mock_ds(key_tag, algorithm, digest_type)` — mock DS rdata
- `_mock_rrset(rdtype, rdata_list)` — mock RRset with rdtype and iterable rdata
- `_mock_dns_response(answer_rrsets, authority_rrsets)` — mock DNS response message

## Verification Results

```
python3 -c "from quirk.scanner.dnssec_scanner import scan_dnssec_targets, DNSPYTHON_AVAILABLE, DNSSEC_ALG_MAP; print('OK')"
# -> OK

pytest tests/test_dnssec_scanner.py --co -q
# -> 16 tests collected

pytest tests/test_dnssec_scanner.py -k "algorithm_classification" -q
# -> 4 passed

pytest tests/test_dnssec_scanner.py -q
# -> 10 failed, 5 passed, 1 skipped (RED state confirmed)

pytest tests/ -q --ignore=tests/test_dnssec_scanner.py
# -> 1 pre-existing failure (test_package_manifest_version_is_4_1_0), 238 passed — no new regressions
```

## Deviations from Plan

None — plan executed exactly as written.

Note: The pre-existing `test_v41_gap_closure.py::test_package_manifest_version_is_4_1_0` failure (version string 4.0.0 vs expected 4.1.0) was confirmed present before this plan's changes. Out of scope for this plan.

## Known Stubs

`quirk/scanner/dnssec_scanner.py` is intentionally a stub module — all functional methods raise `NotImplementedError`. Plan 02 implements the full scanner. This is the expected state for a TDD RED plan.

## Self-Check: PASSED
