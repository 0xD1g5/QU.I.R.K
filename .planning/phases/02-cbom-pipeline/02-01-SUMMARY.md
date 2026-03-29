---
phase: 02-cbom-pipeline
plan: "01"
subsystem: cbom
tags: [cyclonedx, pqc, cryptography, classification, nist, tdd]

# Dependency graph
requires:
  - phase: 01-foundation-fixes
    provides: quirk package with models.py CryptoEndpoint fields, ssh_audit_json column, tls_capabilities_json
provides:
  - classify_algorithm() function mapping any algorithm string to (CryptoPrimitive, nist_level, classical_level)
  - quantum_safety_label() helper translating NIST levels to human-readable strings
  - QuantumSafety enum for structured safety classification
  - quirk.cbom package with full public API
  - cyclonedx-python-lib dependency registered in pyproject.toml
affects: [02-cbom-builder, 02-cbom-output, 03-scoring, 05-dashboard]

# Tech tracking
tech-stack:
  added:
    - cyclonedx-python-lib==11.7.0
  patterns:
    - TDD (RED then GREEN) for lookup table with comprehensive parametric tests
    - Vendor suffix stripping for SSH @openssh.com / @libssh.org algorithm names
    - Normalized lowercase key lookup with fuzzy hyphen-insertion fallback

key-files:
  created:
    - quirk/cbom/__init__.py
    - quirk/cbom/classifier.py
    - tests/test_cbom_classifier.py
  modified:
    - pyproject.toml

key-decisions:
  - "classify_algorithm returns 3-tuple (CryptoPrimitive, nist_level, classical_level) to carry both quantum and classical security bit-strength in one call"
  - "SHA-256 and SHA-384 nist_level differ (0 vs 2) reflecting Grover's algorithm halving effect on hash output length — SHA-256 has only 128-bit post-quantum security"
  - "AES-256-CBC gets nist_level=3 (quantum-safe) while AES-128-CBC gets nist_level=1 — threshold is 192-bit effective classical security for full quantum safety"
  - "SSH algorithm names are normalized through the same lookup table as TLS/cert names — single source of truth"
  - "Fuzzy hyphen-insertion fallback handles compact SSH enc names like aes128-ctr arriving without hyphens"

patterns-established:
  - "Pattern 1: All algorithm classification routes through classify_algorithm() — never hardcode primitive checks elsewhere"
  - "Pattern 2: Vendor suffixes always stripped with name.split('@')[0] before any lookup"
  - "Pattern 3: Case-insensitive lookup via .lower() on input"

requirements-completed: [CBOM-02, CBOM-03]

# Metrics
duration: 2min
completed: 2026-03-29
---

# Phase 02 Plan 01: Algorithm Classifier Summary

**classify_algorithm() lookup table mapping 50+ algorithm strings from TLS/SSH/cert scanners to CycloneDX CryptoPrimitive enum values and NIST PQC quantum security levels via cyclonedx-python-lib 11.7.0**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-29T21:14:21Z
- **Completed:** 2026-03-29T21:16:30Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Installed cyclonedx-python-lib 11.7.0 and registered it as a project dependency in pyproject.toml
- Built `quirk/cbom/classifier.py` with a 50-entry `_ALGORITHM_TABLE` covering SSH KEX, SSH host key, SSH enc/mac, TLS cipher primitives, cert key algorithms, symmetric ciphers, hashes, and all NIST PQC FIPS 203/204/205 standards
- 28/28 classifier tests pass covering all algorithm families plus edge cases (unknown algorithms, case-insensitivity, vendor suffix stripping, compact SSH name normalization)

## Task Commits

Each task was committed atomically:

1. **Task 1: Install cyclonedx-python-lib and write failing classifier tests** - `63dffd5` (test)
2. **Task 2: Implement classifier.py to make all tests pass** - `9650ff2` (feat)

**Plan metadata:** (created below)

_Note: TDD tasks have two commits (test RED then feat GREEN)_

## Files Created/Modified

- `quirk/cbom/__init__.py` - Package init re-exporting classify_algorithm, quantum_safety_label, QuantumSafety
- `quirk/cbom/classifier.py` - Core classifier: _ALGORITHM_TABLE, classify_algorithm(), quantum_safety_label(), QuantumSafety enum
- `tests/test_cbom_classifier.py` - 28 unit tests covering all algorithm families and edge cases
- `pyproject.toml` - Added `cyclonedx-python-lib>=11.7.0,<12` to project dependencies

## Decisions Made

- `classify_algorithm` returns a 3-tuple `(CryptoPrimitive, nist_level, classical_level)` to carry both quantum and classical security bit-strength in a single call — callers can derive labels without additional lookups
- SHA-256 assigned `nist_level=0` (quantum-vulnerable) because Grover's algorithm halves output security, giving only 128-bit post-quantum security — SHA-384 earns `nist_level=2` with effective 192-bit post-quantum security
- AES-256-CBC earns `nist_level=3` (quantum-safe) because AES-256 retains 128-bit post-quantum security after Grover; AES-128-CBC earns `nist_level=1` (marginally quantum-safe at 64-bit effective)
- Fuzzy fallback using regex hyphen-insertion handles compact SSH enc names arriving without standard hyphens (e.g., `aes128ctr`)
- `quirk/cbom/__init__.py` exports the full public API so callers use `from quirk.cbom import classify_algorithm` without knowing internal module structure

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Recreated .venv with current Python after stale interpreter path**
- **Found during:** Task 1 (pip install cyclonedx-python-lib)
- **Issue:** `.venv/bin/pip` referenced Python 3.14 at old Homebrew Cellar path that no longer existed after a version bump; interpreter bad-path error prevented pip execution
- **Fix:** Ran `python3 -m venv .venv --clear` to rebuild venv with the current system Python 3.14.3, then reinstalled requirements.txt and cyclonedx-python-lib
- **Files modified:** .venv/ (runtime, not tracked in git)
- **Verification:** `pip install cyclonedx-python-lib==11.7.0` succeeded; all 28 tests pass
- **Committed in:** N/A (runtime environment fix, no source file change needed)

---

**Total deviations:** 1 auto-fixed (Rule 3 - blocking environment issue)
**Impact on plan:** Required fix to unblock execution. No scope creep, no source file changes.

## Issues Encountered

- Python venv stale interpreter path blocked pip — resolved by recreating venv (see Deviations above)

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `classify_algorithm()` is ready for use by 02-02-cbom-builder which will consume algorithm strings from CryptoEndpoint records
- All CryptoPrimitive values used by 02-02 (PKE, SIGNATURE, KEY_AGREE, KEM, AE, BLOCK_CIPHER, HASH, UNKNOWN) are confirmed present in cyclonedx-python-lib 11.7.0
- quirk.cbom package path is established — 02-02 should add `builder.py` in same package

---
*Phase: 02-cbom-pipeline*
*Completed: 2026-03-29*

## Self-Check: PASSED

- quirk/cbom/__init__.py: FOUND
- quirk/cbom/classifier.py: FOUND
- tests/test_cbom_classifier.py: FOUND
- .planning/phases/02-cbom-pipeline/02-01-SUMMARY.md: FOUND
- Commit 63dffd5 (RED phase): FOUND
- Commit 9650ff2 (GREEN phase): FOUND
- 28/28 tests pass: VERIFIED
