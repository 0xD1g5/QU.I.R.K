---
phase: 95-code-signing-certificate-inventory
plan: "01"
subsystem: scanner
tags: [codesign, ldap, eku, weak-crypto, csign-01, csign-02]
dependency_graph:
  requires: []
  provides:
    - quirk.scanner.codesign_scanner (CODE_SIGNING protocol, scan_codesign_from_ldap, scan_codesign_from_tls_endpoints)
    - ConnectorsCfg.enable_codesign / codesign_targets / codesign_search_base / codesign_timeout
  affects:
    - quirk/config.py (ConnectorsCfg extended)
    - tests/test_codesign_scanner.py (new unit suite)
tech_stack:
  added: []
  patterns:
    - LDAP anonymous bind + paged search (mirrors smime_scanner.py)
    - DER-then-PEM dual-parse (mirrors smime_scanner.py)
    - EKU OID check via cryptography.x509.ExtendedKeyUsageOID.CODE_SIGNING
    - SHA-256 fingerprint via cert.fingerprint(hashes.SHA256()).hex()
    - EC<256 inline key-size check (not via is_weak_cipher — avoids AES-256 substring collision)
key_files:
  created:
    - quirk/scanner/codesign_scanner.py
    - tests/test_codesign_scanner.py
    - tests/fixtures/codesign/regen.sh
    - tests/fixtures/codesign/codesign_rsa1024_sha1.der
    - tests/fixtures/codesign/codesign_ec192.der
    - tests/fixtures/codesign/codesign_rsa2048_sha256.der
    - tests/fixtures/codesign/codesign_rsa2048_sha256_noncoding.der
  modified:
    - quirk/config.py
decisions:
  - "TLS-EKU path reads eku_oids from tls_capabilities_json (existing field) rather than a new model field; uses surrogate compound key (cert_subject+key_alg+not_after) in service_detail per RESEARCH OQ1 resolution"
  - "EC<256 handled inline in _classify_codesign_severity (not via is_weak_cipher) to avoid AES-256 substring collision with ECDSA-256 token"
  - "scan_codesign_from_tls_endpoints emits CODE_SIGNING endpoint for TLS certs with CodeSigning EKU but no severity filter — weak status embedded via 'weak' token in service_detail only when severity is HIGH"
metrics:
  duration: "~12 minutes"
  completed: "2026-05-23"
  tasks_completed: 2
  files_changed: 9
---

# Phase 95 Plan 01: Code-Signing Scanner Module Summary

**One-liner:** LDAP `userCertificate` + TLS in-process EKU scanner with RSA<2048/EC<256/SHA-1 HIGH classification and SHA-256 fingerprint embedding.

## What Was Built

### Task 1: DER Fixtures + Failing Test Suite (RED)

Four deterministic DER cert fixtures generated via `regen.sh` (mirrors `smime/certs/regen.sh`):
- `codesign_rsa1024_sha1.der` — RSA-1024/SHA-1 + CodeSigning EKU → HIGH (2 reasons)
- `codesign_ec192.der` — EC prime192v1/SHA-256 + CodeSigning EKU → HIGH (weak-ec-key)
- `codesign_rsa2048_sha256.der` — RSA-2048/SHA-256 + CodeSigning EKU → SAFE
- `codesign_rsa2048_sha256_noncoding.der` — RSA-2048/SHA-256, no EKU → filtered

Test suite (`tests/test_codesign_scanner.py`) with 7 tests covering CSIGN-01/02:
- `test_rsa1024_sha1_emits_high` — protocol, severity, reasons
- `test_ec192_emits_high` — EC<256 detection
- `test_strong_rsa2048_sha256_safe` — SAFE cert → zero endpoints
- `test_non_codesign_eku_filtered` — no CodeSigning EKU → zero endpoints
- `test_fingerprint_in_service_detail` — 64-char SHA-256 hex in service_detail
- `test_protocol_constant_uppercase` — CODE_SIGNING == "CODE_SIGNING"
- `test_tls_eku_check` — TLS in-process EKU check (no network I/O)

RED confirmed: tests failed with `ImportError: cannot import name 'codesign_scanner'`.

Commit: `2c2f50e`

### Task 2: codesign_scanner.py Implementation + ConnectorsCfg (GREEN)

`quirk/scanner/codesign_scanner.py` implemented with:
- `CODE_SIGNING = "CODE_SIGNING"` module constant (UPPERCASE — downstream key on exact match)
- `EKU_CODE_SIGNING = ExtendedKeyUsageOID.CODE_SIGNING` (OID 1.3.6.1.5.5.7.3.3)
- `_CODESIGN_ATTRS = ("userCertificate",)` — standard RFC 4523 attribute only
- `_has_codesigning_eku(cert_obj)` — EKU filter via cryptography `ExtendedKeyUsage` extension
- `_parse_codesign_cert(cert_bytes)` — DER-then-PEM dual parse, RSA/ECDSA key extraction, SHA-256 fingerprint
- `_classify_codesign_severity(parsed)` — SHA-1 via `is_weak_cipher()`, RSA<2048 inline, EC<256 inline (not via `is_weak_cipher` — avoids AES-256 substring collision)
- `_bind_and_search_codesign()` — hardcoded `(userCertificate=*)` filter, paged_size=500
- `scan_codesign_from_ldap()` — LDAP discovery, EKU filter, weak-algo classification, fingerprint in service_detail
- `scan_codesign_from_tls_endpoints()` — in-process TLS EKU check via `tls_capabilities_json["eku_oids"]`

`quirk/config.py` ConnectorsCfg additions (mirror SMIME block):
- `enable_codesign: bool = False`
- `codesign_targets: list = field(default_factory=list)`
- `codesign_search_base: Optional[str] = None`
- `codesign_timeout: int = 10`

All 7 tests GREEN. Compile clean.

Commit: `2735d4d`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Deviation] Test updated to use tls_capabilities_json instead of tls_scan_json**
- **Found during:** Task 1 test writing
- **Issue:** Plan said "read EKU from tls_scan_json if present" but `tls_scan_json` is not a field on the `CryptoEndpoint` model. The existing field `tls_capabilities_json` is available.
- **Fix:** Tests and implementation use `tls_capabilities_json["eku_oids"]` for TLS-EKU check. This is consistent with the RESEARCH OQ1 resolution (surrogate compound key for TLS path).
- **Files modified:** `tests/test_codesign_scanner.py`, `quirk/scanner/codesign_scanner.py`

**2. [Rule 1 - Bug] Fixed regen.sh empty-array unbound variable on macOS**
- **Found during:** Task 1 fixture generation
- **Issue:** `set -euo pipefail` combined with empty bash arrays (`addext_arg=()`) fails on macOS with `unbound variable` when array expansion `"${addext_arg[@]}"` is empty.
- **Fix:** Replaced array-based approach with explicit if/else branches for codesign vs. no-EKU cert generation.
- **Files modified:** `tests/fixtures/codesign/regen.sh`

## Known Stubs

None — all generated fixtures are real DER certs with verified EKU presence/absence; test mocks use patch.object on `_bind_and_search_codesign` which is the correct LDAP isolation pattern.

## Threat Surface Scan

No new network endpoints, auth paths, or trust boundaries introduced beyond what the plan's threat model covers. The `search_filter = "(userCertificate=*)"` hardcoded literal (T-95-01) and `safe_str()` on all LDAP-derived logging (T-95-03) are implemented as specified. DER parse wrapped in try/except (T-95-02) is implemented.

## Self-Check: PASSED

Files present:
- quirk/scanner/codesign_scanner.py: YES
- quirk/config.py (modified): YES
- tests/test_codesign_scanner.py: YES
- tests/fixtures/codesign/codesign_rsa1024_sha1.der: YES
- tests/fixtures/codesign/codesign_ec192.der: YES
- tests/fixtures/codesign/codesign_rsa2048_sha256.der: YES
- tests/fixtures/codesign/codesign_rsa2048_sha256_noncoding.der: YES
- tests/fixtures/codesign/regen.sh: YES

Commits present:
- 2c2f50e (test RED): YES
- 2735d4d (feat GREEN): YES

Tests: 7/7 passed
