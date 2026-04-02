---
phase: 03-scanner-coverage
plan: 02
subsystem: scanner
tags: [jwt, jwks, syft, semgrep, container, source-code, cryptography]

requires:
  - phase: 03-scanner-coverage-01
    provides: test scaffolds for jwt_scanner, container_scanner, source_scanner; CryptoEndpoint Phase 3 columns; ConnectorsCfg Phase 3 fields

provides:
  - quirk/scanner/jwt_scanner.py — JWT/JWKS scanner with RSA+EC key size extraction
  - quirk/scanner/container_scanner.py — container image scanner via syft with CRYPTO_LIB_ALLOWLIST
  - quirk/scanner/source_scanner.py — source code scanner via semgrep p/cryptography

affects: [03-03, 03-04, phase-05-dashboard, cbom-pipeline]

tech-stack:
  added: [httpx (optional, guarded by HTTPX_AVAILABLE)]
  patterns:
    - ImportError guard for optional dependency (HTTPX_AVAILABLE pattern)
    - shutil.which guard for external CLI tools (syft, semgrep)
    - One CryptoEndpoint per scanned artifact (key/library/finding)
    - protocol= field as scanner type discriminator (JWT/CONTAINER/SOURCE)

key-files:
  created:
    - quirk/scanner/jwt_scanner.py
    - quirk/scanner/container_scanner.py
    - quirk/scanner/source_scanner.py
  modified: []

key-decisions:
  - "JWKS_PATHS probes three paths in order, stops at first non-empty keys array"
  - "RSA key size computed from base64url modulus n byte length * 8"
  - "EC key size from _EC_CRV_BITS lookup (P-256=256, P-384=384, P-521=521)"
  - "CRYPTO_LIB_ALLOWLIST uses frozenset for O(1) membership test"
  - "source_scanner cipher_suite = semgrep check_id, service_detail = file:line"

patterns-established:
  - "ImportError guard pattern: try/except ImportError sets TOOL_AVAILABLE flag"
  - "shutil.which guard pattern: returns empty list immediately if binary absent"
  - "scan_X_targets delegates to scan_X_one/scan_X_endpoint per entry"

requirements-completed: [SCAN-03, SCAN-04, SCAN-05]

duration: 2min
completed: 2026-03-29
---

# Phase 03 Plan 02: Scanner Coverage — JWT, Container, Source Summary

**Three new CryptoEndpoint-producing scanners (JWT/JWKS via httpx, container images via syft, source code via semgrep) expanding QU.I.R.K. from 2 to 5 scan surfaces with graceful degradation when tools are absent**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-03-29T23:36:24Z
- **Completed:** 2026-03-29T23:37:58Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- JWT/JWKS scanner extracts RSA key size from base64url modulus and EC size from curve name, creating one CryptoEndpoint per key per JWKS endpoint
- Container scanner filters syft artifact output through CRYPTO_LIB_ALLOWLIST (23 library names), creating one CryptoEndpoint per crypto library found in image
- Source scanner parses semgrep p/cryptography findings, setting cipher_suite=check_id and service_detail="file:line" per finding
- All 14 tests across three test files pass (5 JWT + 4 container + 5 source)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create JWT/JWKS scanner module** - `da55bad` (feat)
2. **Task 2: Create container and source code scanner modules** - `7a96f66` (feat)

**Plan metadata:** (to be added after docs commit)

## Files Created/Modified
- `quirk/scanner/jwt_scanner.py` — JWT/JWKS scanner: HTTPX_AVAILABLE guard, JWKS_PATHS, _rsa_key_bits_from_n, _EC_CRV_BITS, scan_jwt_endpoint, scan_jwt_targets
- `quirk/scanner/container_scanner.py` — Container scanner: CRYPTO_LIB_ALLOWLIST frozenset, scan_container_image (syft subprocess), scan_container_targets
- `quirk/scanner/source_scanner.py` — Source scanner: scan_source_repo (semgrep subprocess), scan_source_targets

## Decisions Made
- RSA key bits computed as `len(base64.b64decode(padded_n)) * 8` — direct byte count from modulus length
- JWKS path probing stops at first success to avoid unnecessary HTTP round-trips
- OIDC discovery path follows `jwks_uri` field in the discovery document
- All three scanners follow identical error handling: return `[]` on any exception or tool absence

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. Test files were already created by Plan 01. All tests passed on first implementation attempt.

## User Setup Required

None - no external service configuration required. httpx, syft, and semgrep are all optional; scanners degrade gracefully when absent.

## Next Phase Readiness
- Three scanner modules ready for Plan 03 (cloud scanner) and Plan 04 (engine integration)
- All scanner modules follow ssh_scanner.py pattern — consistent interface for engine integration
- No blockers

---
*Phase: 03-scanner-coverage*
*Completed: 2026-03-29*

## Self-Check: PASSED

- quirk/scanner/jwt_scanner.py — FOUND
- quirk/scanner/container_scanner.py — FOUND
- quirk/scanner/source_scanner.py — FOUND
- .planning/phases/03-scanner-coverage/03-02-SUMMARY.md — FOUND
- Commit da55bad (jwt_scanner) — FOUND
- Commit 7a96f66 (container + source scanners) — FOUND
- 14/14 tests pass across test_jwt_scanner.py, test_container_scanner.py, test_source_scanner.py
