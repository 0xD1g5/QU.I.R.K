---
phase: 88-scoring-residuals
plan: "02"
subsystem: cbom
tags: [cbom, classifier, builder, d-05, d-06, score-cbom-01, phase42-obs1]
dependency_graph:
  requires: []
  provides: [SCORE-CBOM-01]
  affects: [quirk/cbom/classifier.py, quirk/cbom/builder.py, tests/test_cbom_zero_algo_profiles.py]
tech_stack:
  added: []
  patterns: [quirk:coverage-note Property on Bom root component, coverage_notes accumulator pattern]
key_files:
  created:
    - tests/test_cbom_zero_algo_profiles.py
  modified:
    - quirk/cbom/classifier.py
    - quirk/cbom/builder.py
    - tests/test_cbom_motion_endpoints.py
    - tests/test_cbom_coverage.py
decisions:
  - "D-05: ssh-weak fixture updated with realistic ssh_audit_json; SSH builder branch now registers actual weak algorithms (diffie-hellman-group1-sha1, ssh-dss, hmac-md5)"
  - "D-06: CONTAINER/SOURCE/POSTGRESQL/MYSQL/S3 branches emit hardcoded quirk:coverage-note Property on Bom root when no algorithm material is observed — never scanner-derived values (T-88-03)"
  - "Rule 2 deviation: added md5, md4, rc4, des, blowfish, aes to classifier _ALGORITHM_TABLE for source-scanner output correctness"
  - "Rule 1 deviation: updated test_cbom_coverage.py CONTAINER/SOURCE cases to assert coverage note (not algo component) per new D-06 contract"
metrics:
  duration: "~25 minutes"
  completed: "2026-05-22"
  tasks: 2
  files: 5
---

# Phase 88 Plan 02: Zero-Algo CBOM Profile Coverage Summary

**One-liner:** CBOM builder emits real SSH weak-algorithm components (D-05) and affirmative hardcoded no-crypto markers (D-06) for the five formerly-zero-algo profiles, closing Phase 42 OBS-1.

---

## What Was Built

### Task 1: Weak SSH Algorithm Classifier Entries

Added five new entries to `quirk/cbom/classifier.py` `_ALGORITHM_TABLE`:

| Algorithm | Primitive | NIST Level | Classical Bits |
|-----------|-----------|------------|----------------|
| diffie-hellman-group1-sha1 | KEY_AGREE | 0 | 80 |
| ssh-dss | SIGNATURE | 0 | 80 |
| hmac-md5 | HASH | 0 | 64 |
| hmac-md5-96 | HASH | 0 | 64 |
| hmac-sha1-96 | HASH | 0 | 80 |

All five now return non-UNKNOWN primitives from `classify_algorithm()`. Unblocks the SSH builder path and classifier coverage gate for ssh-weak profile.

**Commit:** `3f0ec45`

### Task 2: Builder Pass-1 D-06 Markers + Realistic Fixtures + Coverage Gate

**`quirk/cbom/builder.py` changes:**
- Added `_emit_coverage_note(bom_component, note)` helper — attaches `Property(name="quirk:coverage-note", value=note)` to the Bom root component. Note values are HARDCODED string literals (T-88-03 / D-06).
- Initialized `coverage_notes: list[str] = []` at top of `build_cbom` Pass-1.
- CONTAINER branch: emit coverage note `"crypto library/pattern observed; algorithm-level detail not captured by container scanner"` instead of registering library name (which produces UNKNOWN).
- SOURCE branch: emit coverage note `"crypto library/pattern observed; algorithm-level detail not captured by source scanner"` for rule IDs with no extractable algorithm hint (raw rule ID was previously registered — UNKNOWN).
- MYSQL branch: emit plaintext note `"plaintext endpoint — MySQL connection uses no TLS; no cryptographic material observed"` when `cipher_name == SSL-OFF`.
- POSTGRESQL/RDS branch: emit plaintext note `"plaintext endpoint — PostgreSQL/RDS connection uses no TLS; no cryptographic material observed"` when no `cert_pubkey_alg` (ssl-off).
- S3/AZURE_BLOB branch: emit unencrypted note `"unencrypted S3/Blob endpoint — no server-side encryption observed; no algorithm material to catalog"` when detail is unencrypted or no encrypted posture matched.
- All coverage notes attached to `root_component` after Pass-1 via `_emit_coverage_note()`.

**`tests/test_cbom_motion_endpoints.py` fixture updates (Phase 42 OBS-1 fix):**
- `_build_ssh_weak_lab_endpoints`: replaced `ssh_audit_json=None` with realistic JSON containing kex=diffie-hellman-group1-sha1, key=ssh-dss, enc=aes128-ctr, mac=hmac-md5 (D-05 — reflects real ssh-audit output).
- `_build_database_lab_endpoints`: fixed `cert_pubkey_alg=None` (was synthetically RSA) to reflect real ssl-off postgresql behavior.
- `_build_storage_s3_lab_endpoints`: fixed to use `service_detail="S3/unencrypted"` with no cert_pubkey_alg (was synthetically AES-256).
- `_build_registry_lab_endpoints`: fixed to use `cipher_suite="openssl"` with no cert_pubkey_alg (was synthetically RSA).
- `_build_source_lab_endpoints`: fixed to use `cipher_suite="python.cryptography.security.insecure-hash-algorithms-md5"` (real rule ID pattern).

**`tests/test_cbom_zero_algo_profiles.py` (new):**
- Parametrized over all five profiles: database, registry, source, ssh-weak, storage-s3.
- Asserts `algo_names or coverage_notes` — never both absent (D-05/D-06 contract).
- Additional `test_ssh_weak_emits_real_weak_algorithm_components` gate asserting diffie-hellman-group1-sha1, ssh-dss, hmac-md5 specifically present.

**`tests/test_cbom_coverage.py` update:**
- CONTAINER and SOURCE protocol families now assert `coverage_notes` (not algo components) per new D-06 contract.

**Commit:** `eb304fc`

---

## Verification Results

| Check | Result |
|-------|--------|
| `test_cbom_zero_algo_profiles.py` (6 tests) | PASS |
| `test_cbom_classifier_coverage.py` (coverage gate) | Pre-existing RSA-kex failure only |
| `test_cbom_motion_endpoints.py` | Pre-existing RSA-kex/decomposition failures only |
| `test_cbom_coverage.py` (14 tests) | PASS |
| Full test suite | 40 failures = baseline (no new regressions) |
| `python -m compileall quirk/cbom/builder.py` | PASS |
| `python -m compileall quirk/cbom/classifier.py` | PASS |
| Security check: no scanner-derived coverage note values | PASS (AST gate verified) |

---

## Profile Outcomes (Phase 42 OBS-1)

| Profile | Before | After | Mechanism |
|---------|--------|-------|-----------|
| database | 0 algo components, no marker | 0 algo + 1 coverage note | D-06 PostgreSQL ssl-off marker |
| registry | 0 algo components (after fixture fix) | 0 algo + 1 coverage note | D-06 CONTAINER library-name marker |
| source | 0 algo components (after fixture fix) | 1 algo (MD5) | D-05 rule ID extraction correct |
| ssh-weak | 1 algo (ssh-dss cert_pubkey_alg fallback) | 4 algos from ssh_audit_json | D-05 realistic fixture |
| storage-s3 | 0 algo (after fixture fix) | 0 algo + 1 coverage note | D-06 unencrypted S3 marker |

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical Functionality] Added md5, md4, rc4, des, blowfish, aes to classifier**
- **Found during:** Task 2 — the source fixture's `cipher_suite="python.cryptography.security.insecure-hash-algorithms-md5"` caused `_extract_algo_from_rule_id` to return "MD5" which was UNKNOWN in the classifier.
- **Issue:** `_extract_algo_from_rule_id` can return MD5, MD4, RC4, DES, Blowfish, AES — none were in `_ALGORITHM_TABLE`.
- **Fix:** Added all six missing entries alongside existing entries in the CycloneDX canonical names section.
- **Files modified:** `quirk/cbom/classifier.py`
- **Commit:** `eb304fc`

**2. [Rule 1 - Bug] Updated test_cbom_coverage.py CONTAINER/SOURCE assertions**
- **Found during:** Task 2 — existing Phase 61 gate `test_protocol_family_emits_algo_component` required algo components for CONTAINER and SOURCE. My D-06 changes correctly changed those protocols to emit coverage notes instead.
- **Issue:** The Phase 61 gate tested the old (architecturally incorrect) behavior of registering library names as algorithm names.
- **Fix:** Updated test to assert coverage notes for CONTAINER/SOURCE, algo components for all other protocol families.
- **Files modified:** `tests/test_cbom_coverage.py`
- **Commit:** `eb304fc`

---

## Known Stubs

None. All five profiles now satisfy the D-05/D-06 contract. The coverage-note values are affirmative findings ("we looked, this endpoint is plaintext"), not stubs.

---

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: hardcoded-string-enforcement | quirk/cbom/builder.py | All 5 coverage_notes.append() calls use hardcoded string literals; AST gate verified no f-strings or scanner-derived interpolation (T-88-03 satisfied) |

## Self-Check: PASSED

- classifier.py: FOUND
- builder.py: FOUND
- test_cbom_zero_algo_profiles.py: FOUND
- SUMMARY.md: FOUND
- commit 3f0ec45 (Task 1): FOUND
- commit eb304fc (Task 2): FOUND
