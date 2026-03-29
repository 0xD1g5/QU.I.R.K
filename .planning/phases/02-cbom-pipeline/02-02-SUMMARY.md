---
phase: 02-cbom-pipeline
plan: "02"
subsystem: cbom
tags: [cyclonedx, cbom, tls, ssh, algorithm-mapping, cryptography]

requires:
  - phase: 02-cbom-pipeline/02-01
    provides: classify_algorithm() returning (CryptoPrimitive, nist_level, classical_level)

provides:
  - build_cbom(endpoints) -> Bom with deduplicated CRYPTOGRAPHIC_ASSET components
  - TLS cipher suite decomposition into constituent algorithm components
  - SSH kex/key/enc/mac algorithm processing from ssh_audit_json
  - Certificate components (X.509) for TLS endpoints
  - Protocol components for both TLS and SSH endpoints
  - bom_ref registry-based deduplication across endpoints

affects:
  - 02-cbom-pipeline/02-03 (writer serializes this Bom to JSON/XML)
  - reports (CBOM attached to scan output)
  - dashboard (CBOM viewer uses Bom data structure)

tech-stack:
  added: []
  patterns:
    - "CBOM builder: algo_registry dict keyed by normalized bom_ref fragment prevents duplicates"
    - "Three-pass build: algorithms first -> certs second -> protocols third (algorithms must exist before certs/protocols reference them)"
    - "_decompose_cipher_suite: token-based parser splitting on _WITH_ boundary; TLS1.3 vs 1.2 detection"
    - "bom_ref format: crypto/algorithm/{name}, crypto/certificate/{host}:{port}, crypto/protocol/{tls|ssh}/{host}:{port}"

key-files:
  created:
    - quirk/cbom/builder.py
    - tests/test_cbom_builder.py
  modified:
    - quirk/cbom/__init__.py

key-decisions:
  - "Three-pass build order (algo -> cert -> protocol) ensures BomRef cross-references are valid when protocol/cert components are created"
  - "bom_ref registry keyed by _normalize_bom_ref_key(name) — same algorithm from two endpoints shares one component, collision-free"
  - "TLSv1.3 suite detection via regex ^TLS_(AES|CHACHA20) suppresses key-exchange component (it is implicit in TLSv1.3 handshake)"
  - "PLATFORM_VERSION duplicated in builder.py to avoid circular import with quirk.reports.writer"

patterns-established:
  - "Pattern 1: algo_registry dict[str, Component] for per-build deduplication — reuse across all future CBOM callers"
  - "Pattern 2: _normalize_bom_ref_key strips non-alphanumeric -> consistent bom_ref keys"
  - "Pattern 3: _extract_ssh_algorithms() gracefully returns empty dict on None/invalid JSON — null-safe SSH parsing"

requirements-completed: [CBOM-01, CBOM-02]

duration: 8min
completed: 2026-03-29
---

# Phase 02 Plan 02: CBOM Builder Summary

**CycloneDX Bom builder with TLS cipher suite decomposition, SSH kex/key/enc/mac parsing, certificate components, and bom_ref deduplication via in-memory registry**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-03-29T21:18:31Z
- **Completed:** 2026-03-29T21:26:00Z
- **Tasks:** 2 (RED + GREEN)
- **Files modified:** 3

## Accomplishments

- `build_cbom(endpoints) -> Bom` converts raw CryptoEndpoint scan results into standards-compliant CycloneDX BOM
- Cipher suite string `TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384` decomposes into 4 algorithm components (X25519, RSA, AES-256-GCM, SHA-384)
- SSH endpoints: all four sections (kex/key/enc/mac) from `ssh_audit_json` become ALGORITHM components; vendor suffixes stripped
- Algorithm deduplication: two endpoints sharing AES-256-GCM produce exactly one component (registry keyed by normalized name)
- Certificate component per TLS endpoint with BomRef cross-links to signature and public-key algorithm components
- Protocol components for both TLS (with version, cipher suite refs) and SSH (with KEX algorithm refs)
- BOM metadata: tool name "QU.I.R.K." + timestamp on every Bom instance
- All 15 builder tests pass; 43 total (classifier + builder) pass together

## Task Commits

1. **Task 1: Write failing builder tests** - `f3b5dd2` (test)
2. **Task 2: Implement builder.py to make all tests pass** - `7ce23b7` (feat)

## Files Created/Modified

- `quirk/cbom/builder.py` - Core build_cbom() function with decomposition helpers, registry, three-pass build
- `tests/test_cbom_builder.py` - 15 tests: BOM construction, cipher decomposition, SSH mapping, dedup, protocol/cert components
- `quirk/cbom/__init__.py` - Added build_cbom to public exports

## Decisions Made

- **Three-pass build order** (algorithms first, certificates second, protocols third): ensures BomRef cross-references in certificate and protocol components point to already-registered algorithm components.
- **bom_ref registry keyed by normalized name**: `_normalize_bom_ref_key()` strips non-alphanumeric characters and lowercases, producing stable keys. Same algorithm string from two endpoints shares one component.
- **TLSv1.3 suite detection**: Regex `^TLS_(AES|CHACHA20|CAMELLIA)` distinguishes TLSv1.3 suites (no explicit KEX in suite name) from TLSv1.2 and earlier.
- **PLATFORM_VERSION duplicated** in `builder.py` rather than importing from `quirk.reports.writer` to avoid circular imports.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## Known Stubs

None — `build_cbom()` produces real CycloneDX Bom objects from real scan data; no hardcoded empty values flow to output.

## Next Phase Readiness

- `build_cbom()` is fully implemented and tested; Plan 03 (writer) can import it directly
- `quirk.cbom.build_cbom` is exported from the package `__init__.py`
- The writer will serialize the returned `Bom` to JSON/XML via `cyclonedx-python-lib` serializers

---
*Phase: 02-cbom-pipeline*
*Completed: 2026-03-29*
