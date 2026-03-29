---
phase: 02-cbom-pipeline
verified: 2026-03-29T21:35:13Z
status: passed
score: 13/13 must-haves verified
re_verification: false
---

# Phase 02: CBOM Pipeline Verification Report

**Phase Goal:** Build the CBOM (Cryptography Bill of Materials) generation pipeline — algorithm classification, CBOM construction, and file output (JSON + XML) — integrated into the existing report writer.
**Verified:** 2026-03-29T21:35:13Z
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Every algorithm string from any scanner maps to a CycloneDX CryptoPrimitive enum value | VERIFIED | `_ALGORITHM_TABLE` in classifier.py has 50+ entries; all 28 classifier tests pass |
| 2 | Every algorithm carries a nistQuantumSecurityLevel integer (0 for quantum-vulnerable, 1-5 for PQC/symmetric) | VERIFIED | 3-tuple `(primitive, nist_level, classical_level)` returned; SHA-256=0, AES-256-GCM=1, ML-KEM-768=3 confirmed in tests |
| 3 | Unknown algorithm strings return `(UNKNOWN, None, None)` without crashing | VERIFIED | `_FALLBACK` constant returned for unrecognized strings; `test_unknown_algorithm_returns_unknown` passes |
| 4 | SSH vendor suffixes (@openssh.com, @libssh.org) stripped before lookup | VERIFIED | `name.split("@")[0]` at line 158 of classifier.py; `test_ssh_kex_vendor_suffix_stripped` passes |
| 5 | build_cbom() accepts a list of CryptoEndpoint objects and returns a Bom instance | VERIFIED | builder.py line 250; `test_build_cbom_returns_bom` passes |
| 6 | TLS cipher suite strings are decomposed into constituent algorithm components | VERIFIED | `_decompose_cipher_suite()` in builder.py; `TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384` produces X25519, RSA, AES-256-GCM, SHA-384 |
| 7 | SSH algorithms from ssh_audit_json (kex, key, enc, mac) each become CBOM components | VERIFIED | `_extract_ssh_algorithms()` + Pass 1 SSH branch in builder.py; 4 SSH test cases pass |
| 8 | Duplicate algorithms across endpoints produce a single shared component | VERIFIED | `algo_registry` dict in builder.py; `test_algorithm_deduplication` passes |
| 9 | Protocol components created for both TLS and SSH endpoints | VERIFIED | Pass 3 in builder.py; `test_tls_protocol_component_created` and `test_ssh_protocol_component_created` pass |
| 10 | write_cbom_files() serializes Bom to JSON and XML files on disk | VERIFIED | writer.py uses JsonV1Dot6/XmlV1Dot6; 9 writer unit tests pass |
| 11 | JSON output has bomFormat=CycloneDX, specVersion=1.6, cryptoProperties fields | VERIFIED | Spot-check confirmed: `bomFormat=CycloneDX, specVersion=1.6`, 8 components with cryptoProperties |
| 12 | XML output contains CycloneDX namespace | VERIFIED | Spot-check confirmed: `cyclonedx.org` present in XML output |
| 13 | write_reports() calls build_cbom + write_cbom_files and includes CBOM paths in console output | VERIFIED | quirk/reports/writer.py lines 15, 216-217, 230: import, step 5, path list extended |

**Score:** 13/13 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `quirk/cbom/classifier.py` | classify_algorithm() mapping algorithm string to (CryptoPrimitive, nist_level, classical_level) | VERIFIED | 181 lines, full lookup table, vendor stripping, case normalization, fuzzy fallback |
| `quirk/cbom/__init__.py` | Package init re-exporting public API | VERIFIED | Exports: build_cbom, classify_algorithm, quantum_safety_label, QuantumSafety, write_cbom_files |
| `quirk/cbom/builder.py` | build_cbom(endpoints) -> Bom | VERIFIED | 446 lines, three-pass build, deduplication registry, cipher suite decomposition |
| `quirk/cbom/writer.py` | write_cbom_files(bom, outdir, stamp) -> tuple[str, str] | VERIFIED | 36 lines, JsonV1Dot6 + XmlV1Dot6, allow_overwrite=True |
| `quirk/reports/writer.py` | Modified write_reports() with CBOM as step 5 | VERIFIED | Lines 15, 215-217, 230 — import, step 5, and path list all present |
| `tests/test_cbom_classifier.py` | Unit tests for all algorithm families | VERIFIED | 28 tests covering all algorithm families, edge cases, vendor suffixes |
| `tests/test_cbom_builder.py` | Unit tests for builder logic | VERIFIED | 15 tests covering BOM construction, cipher decomposition, SSH mapping, dedup |
| `tests/test_cbom_writer.py` | Unit tests for JSON/XML serialization | VERIFIED | 9 tests covering file creation, naming, format, cryptoProperties, NIST level |
| `tests/test_cbom_integration.py` | Integration tests for write_reports() CBOM step | VERIFIED | 3 tests covering file creation, console paths, algorithm component presence |
| `pyproject.toml` | cyclonedx-python-lib dependency declaration | VERIFIED | Dependency registered; cyclonedx-python-lib 11.7.0 installed and importable |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `quirk/cbom/classifier.py` | `cyclonedx.model.crypto.CryptoPrimitive` | enum import and return value | WIRED | Line 18: `from cyclonedx.model.crypto import CryptoPrimitive`; all table entries use `CryptoPrimitive.*` |
| `quirk/cbom/builder.py` | `quirk/cbom/classifier.py` | classify_algorithm() calls | WIRED | Line 34 import + line 191 call in `_make_algorithm_component()` |
| `quirk/cbom/builder.py` | `cyclonedx.model.component.Component` | `ComponentType.CRYPTOGRAPHIC_ASSET` | WIRED | Line 21 import; line 200 `type=ComponentType.CRYPTOGRAPHIC_ASSET` |
| `quirk/cbom/builder.py` | `quirk/models.py` | reads CryptoEndpoint fields | WIRED | Lines 274-301 read `ep.protocol`, `ep.cipher_suite`, `ep.cert_pubkey_alg`, `ep.ssh_audit_json` etc. |
| `quirk/cbom/writer.py` | `cyclonedx.output.json.JsonV1Dot6` | JSON serialization | WIRED | Line 7 import; line 28 `JsonV1Dot6(bom)` |
| `quirk/cbom/writer.py` | `cyclonedx.output.xml.XmlV1Dot6` | XML serialization | WIRED | Line 8 import; line 32 `XmlV1Dot6(bom)` |
| `quirk/reports/writer.py` | `quirk/cbom/__init__.py` | `from quirk.cbom import build_cbom, write_cbom_files` | WIRED | Line 15 import; lines 216-217 call both functions in step 5 |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `quirk/cbom/builder.py` | `algo_registry` | CryptoEndpoint fields from scan results | Yes — reads cipher_suite, cert_pubkey_alg, ssh_audit_json from real ORM objects | FLOWING |
| `quirk/cbom/writer.py` | `bom` parameter | Passed from build_cbom(endpoints) which is called with real endpoints | Yes — Bom object contains components built from scan data | FLOWING |
| `quirk/reports/writer.py` | `cbom` / `cbom_json_path` / `cbom_xml_path` | `build_cbom(endpoints)` at line 216, endpoints from scan run | Yes — endpoints are real scan results passed from calling code | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| classify_algorithm("RSA") returns (PKE, 0, 112) | Python assertion | (CryptoPrimitive.PKE, 0, 112) confirmed | PASS |
| SSH vendor suffix stripped (curve25519-sha256@libssh.org = curve25519-sha256) | Python assertion | Both calls return identical tuples | PASS |
| Unknown algorithm returns (UNKNOWN, None, None) | Python assertion | Returns fallback correctly | PASS |
| build_cbom produces Bom with 8 components from TLS endpoint | Python assertion | 8 components confirmed | PASS |
| JSON output has bomFormat=CycloneDX, specVersion=1.6 | Python assertion + file parse | Confirmed | PASS |
| XML output contains cyclonedx.org namespace | Python assertion + file read | Confirmed | PASS |
| nistQuantumSecurityLevel=0 present in JSON for RSA component | Python assertion | At least one level-0 component confirmed | PASS |
| Full test suite: 111 tests, 0 failures | pytest | 111 passed, 13 warnings (deprecations in non-CBOM code) | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| CBOM-01 | 02-02, 02-03 | cyclonedx-python-lib integration — map all scan results to CycloneDX CBOM components | SATISFIED | build_cbom() returns valid Bom with CRYPTOGRAPHIC_ASSET components; write_reports() calls it as step 5 |
| CBOM-02 | 02-01, 02-02 | Algorithm -> CBOM component mapping layer (all scanner outputs -> CycloneDX schema) | SATISFIED | _ALGORITHM_TABLE covers SSH KEX/key/enc/mac, TLS cipher suite decomposition, cert algorithms, PQC algorithms |
| CBOM-03 | 02-01 | NIST PQC quantum-safety classification enrichment per algorithm | SATISFIED | Every table entry carries nist_quantum_security_level; quantum_safety_label() translates to human-readable string |
| CBOM-04 | 02-03 | CBOM JSON + XML output artifact per scan run | SATISFIED | write_cbom_files() produces cbom-{stamp}.cdx.json and cbom-{stamp}.cdx.xml; paths in console output |

No orphaned requirements. All four CBOM requirements are claimed by plans and verified in the codebase.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `quirk/cbom/classifier.py` | 170 | `import re` inside function body | Info | Minor style issue; no runtime impact (re is stdlib, cached after first import) |

No stubs, no hardcoded empty returns, no TODO/FIXME/placeholder comments found in any CBOM module.

---

### Human Verification Required

None. All truths are verifiable programmatically and all checks passed.

---

### Gaps Summary

No gaps. All 13 observable truths are verified, all artifacts pass levels 1-4 (exist, substantive, wired, data flowing), all key links are confirmed wired, all four requirements are satisfied, and 111 tests pass with zero failures.

The full CBOM pipeline is operational:
- `classify_algorithm()` — 50+ algorithm entries, SSH vendor stripping, case normalization, fuzzy fallback
- `build_cbom()` — three-pass construction (algorithms, certificates, protocols), bom_ref deduplication registry, TLS cipher suite decomposition, SSH kex/key/enc/mac parsing
- `write_cbom_files()` — CycloneDX 1.6 JSON and XML via cyclonedx-python-lib, files named `cbom-{stamp}.cdx.{json,xml}`
- `write_reports()` — CBOM as step 5, paths included in console output

---

_Verified: 2026-03-29T21:35:13Z_
_Verifier: Claude (gsd-verifier)_
