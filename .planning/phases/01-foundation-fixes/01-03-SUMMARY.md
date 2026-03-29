---
phase: 01-foundation-fixes
plan: 03
subsystem: scanner/tls
tags: [sslyze, tls, scanner, fallback, cbom]
dependency_graph:
  requires: [01-02]
  provides: [sslyze-primary-tls-scan, tls_capabilities_json]
  affects: [qcscan/scanner/tls_scanner.py, qcscan/models.py]
tech_stack:
  added: [sslyze (optional), json]
  patterns: [conditional-import, primary-fallback, tdd-red-green]
key_files:
  created: [tests/test_sslyze_integration.py]
  modified: [qcscan/scanner/tls_scanner.py, qcscan/models.py]
decisions:
  - "sslyze is primary TLS scanner; existing ssl+cryptography is fallback (D-01, D-02)"
  - "tls_capabilities_json stores deep sslyze data: accepted_by_version, chain_depth, elliptic_curves (D-03)"
  - "SSLYZE_AVAILABLE flag set at module level via try/except ImportError — graceful fallback when not installed"
  - "scan_one renamed to _scan_one_fallback; new scan_one() orchestrates primary/fallback"
metrics:
  duration_seconds: 262
  completed_date: "2026-03-29"
  tasks_completed: 2
  files_changed: 3
requirements_satisfied: [SCAN-01]
---

# Phase 01 Plan 03: sslyze TLS Scanner Integration Summary

**One-liner:** sslyze primary TLS scanner with ssl+cryptography fallback, storing full cipher/chain/curve inventory in tls_capabilities_json.

## What Was Built

### Task 1 — Add tls_capabilities_json column to CryptoEndpoint
Added `tls_capabilities_json = Column(Text, nullable=True)` to `CryptoEndpoint` after `tls_enum_notes`. This is an additive schema change — nullable, no migration required. Stores sslyze deep scan results as a JSON blob.

**Commit:** `b5e208d` — `feat(01-03): add tls_capabilities_json column to CryptoEndpoint`

### Task 2 — Integrate sslyze as primary TLS scanner (TDD)

**RED phase:** Wrote 12 failing tests in `tests/test_sslyze_integration.py` covering:
- sslyze happy path (mocked Scanner returning COMPLETED result)
- `SSLYZE_AVAILABLE=False` when sslyze not installed
- `scan_one()` routing to `_scan_one_fallback` when sslyze unavailable
- `ERROR_NO_CONNECTIVITY` scan status triggers fallback
- Certificate field mapping from sslyze cryptography x509 objects
- `tls_capabilities_json` structure (accepted_by_version, chain_depth, elliptic_curves)
- Presence of `SSLYZE_AVAILABLE`, `_scan_one_sslyze`, `_scan_one_fallback` symbols

**Commit (RED):** `8afa8c5` — `test(01-03): add failing tests for sslyze integration`

**GREEN phase:** Rewrote `qcscan/scanner/tls_scanner.py` with:
- Module-level conditional import of sslyze (try/except ImportError → `SSLYZE_AVAILABLE` bool)
- `_scan_one_sslyze(host, port, timeout, include_sni, logger)` — returns `Optional[CryptoEndpoint]`, `None` means "use fallback"
  - Builds `ServerScanRequest` with all 8 ScanCommands (CERTIFICATE_INFO, SSL2–TLS1.3 cipher suites, ELLIPTIC_CURVES)
  - Maps cert fields using existing `_pubkey_info()` and `_extract_sans()` helpers
  - Determines highest TLS version from accepted cipher suites
  - Populates all existing v3.6 capability fields (`tls_supported_versions`, `tls_weak_ciphers_present`, etc.)
  - Builds `tls_capabilities_json` with source, version, accepted_by_version dict, chain_depth, chain_verified, elliptic_curves
  - Returns `None` on any exception or `ERROR_NO_CONNECTIVITY` status
- `_scan_one_fallback()` — original `scan_one()` renamed (D-02: existing code preserved verbatim)
- New `scan_one()` — tries sslyze first, falls back to `_scan_one_fallback()` if sslyze unavailable or returns None
- `scan_tls_targets()` — unchanged (already calls `scan_one()` via ThreadPoolExecutor)

**Deviation fixed (Rule 1 — Bug):** Test `Scanner` mock was initialized as `MagicMock` class instead of `MagicMock()` instance in `_make_sslyze_mock_modules()`. `sslyze_mod.Scanner.return_value = scanner_instance` was setting a class-level attribute on `MagicMock` rather than on a mock instance, so `SslyzeScanner(...)` inside `_scan_one_sslyze` was returning a new unconfigured mock. Fixed by changing `sslyze_mod.Scanner = MagicMock` to `sslyze_mod.Scanner = MagicMock()`.

**Commit (GREEN):** `2bc80c6` — `feat(01-03): integrate sslyze as primary TLS scanner with fallback`

## Test Results

All 12 new tests pass. Full suite: 56/56 passing. No regressions.

## Acceptance Criteria

| Criterion | Status |
|-----------|--------|
| `from sslyze import` inside try block | PASS |
| `SSLYZE_AVAILABLE` flag defined | PASS |
| `_scan_one_sslyze` function defined | PASS |
| `_scan_one_fallback` function defined (old scan_one) | PASS |
| `tls_capabilities_json` populated in scanner | PASS |
| `python -m pytest tests/test_sslyze_integration.py -x -v` | PASS (12/12) |
| `python -m pytest tests/ -x -q` (no regressions) | PASS (56/56) |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test mock: Scanner must be MagicMock instance, not class**
- **Found during:** Task 2 GREEN phase
- **Issue:** `_make_sslyze_mock_modules()` set `sslyze_mod.Scanner = MagicMock` (the class itself). Tests then tried `sslyze_mod.Scanner.return_value = scanner_instance` which sets a class attribute — but when `_scan_one_sslyze` called `SslyzeScanner(per_server_concurrent_connections_limit=2)`, it invoked the MagicMock class constructor, returning a new unconfigured instance, not `scanner_instance`.
- **Fix:** Changed `sslyze_mod.Scanner = MagicMock` to `sslyze_mod.Scanner = MagicMock()` in the factory function so `return_value` is configured on a mock instance.
- **Files modified:** `tests/test_sslyze_integration.py`
- **Commit:** `2bc80c6`

## Known Stubs

None — sslyze implementation is fully wired. When sslyze is not installed at runtime, `SSLYZE_AVAILABLE=False` and the fallback scanner runs. No placeholder data flows to UI.

## Self-Check: PASSED
