---
phase: 23-dnssec-cbom-skip-fix
reviewed: 2026-04-24T12:00:00Z
depth: standard
files_reviewed: 2
files_reviewed_list:
  - tests/test_cbom_builder.py
  - quirk/cbom/builder.py
findings:
  critical: 0
  warning: 3
  info: 2
  total: 5
status: issues_found
---

# Phase 23: Code Review Report

**Reviewed:** 2026-04-24T12:00:00Z
**Depth:** standard
**Files Reviewed:** 2
**Status:** issues_found

## Summary

Reviewed the CBOM builder (`quirk/cbom/builder.py`) and its test suite (`tests/test_cbom_builder.py`) in the context of Phase 23 (DNSSEC CBOM skip list fix). The DNSSEC-specific additions are well-structured: the skip list on line 354 correctly filters synthetic findings (`NONE`, `NSEC`, `DS-MISMATCH`, `SHA1-DS`), the certificate exclusion on line 389 prevents spurious X.509 components for DNSKEY records, and the protocol exclusion on line 468 avoids erroneous TLS protocol components. Test coverage for DNSSEC is solid with four targeted tests.

However, three pre-existing warnings were found during the standard review: an unhandled `json.loads` that can crash on malformed cloud data, a CCM-to-GCM misclassification in the cipher suite decomposition map, and a substring-matching false positive in semgrep rule-id extraction. These are not regressions from Phase 23 but are worth addressing.

## Warnings

### WR-01: Unhandled json.JSONDecodeError on cloud_scan_json

**File:** `quirk/cbom/builder.py:340`
**Issue:** `json.loads(ep.cloud_scan_json or "{}")` is called without a try/except. If `cloud_scan_json` contains malformed JSON, the entire `build_cbom` call crashes with a `JSONDecodeError`. This is inconsistent with the SSH path (`_extract_ssh_algorithms`, lines 256-259) which wraps `json.loads` in try/except. A single corrupted cloud endpoint would prevent CBOM generation for the entire scan run.
**Fix:**
```python
try:
    cloud_data = json.loads(ep.cloud_scan_json or "{}")
except (json.JSONDecodeError, TypeError, ValueError):
    cloud_data = {}
```

### WR-02: AES-CCM cipher suites misclassified as AES-GCM

**File:** `quirk/cbom/builder.py:96-97`
**Issue:** The `_ENC_MAP` maps `AES_256_CCM` to `"AES-256-GCM"` and `AES_128_CCM` to `"AES-128-GCM"`. CCM (Counter with CBC-MAC) is a distinct AEAD mode from GCM (Galois/Counter Mode). While both are AEAD, they have different security properties and this mapping will produce incorrect algorithm names in the CBOM output. Any TLS cipher suite using CCM (e.g., `TLS_RSA_WITH_AES_128_CCM`) will be incorrectly reported as using GCM.
**Fix:**
```python
"AES_256_CCM": "AES-256-CCM",
"AES_128_CCM": "AES-128-CCM",
```
Note: also add the new canonical names to `_ALGORITHM_TABLE` in `classifier.py`:
```python
"aes-256-ccm": (CryptoPrimitive.AE, 1, 256),
"aes-128-ccm": (CryptoPrimitive.AE, 1, 128),
```

### WR-03: Substring match in _extract_algo_from_rule_id produces false positives for "dsa"

**File:** `quirk/cbom/builder.py:53-58`
**Issue:** The `_extract_algo_from_rule_id` function uses `if fragment in rule_lower` for substring matching. The fragment `"dsa"` will also match any rule containing `"ecdsa"`, causing ECDSA-related semgrep rules to be misclassified as plain DSA. Similarly, `"des"` could match unrelated rule IDs containing that substring (e.g., `"deserialize"`). The iteration order is insertion-order in Python 3.7+, so `"des"` (line 53) is checked before `"dsa"` (line 55), and neither `"ecdsa"` nor `"ecdhe"` are in the map at all.
**Fix:** Use an ordered list and check longer/more specific patterns first:
```python
algo_hints = [
    ("ecdsa", "ECDSA"), ("sha-1", "SHA-1"), ("sha1", "SHA-1"),
    ("blowfish", "Blowfish"), ("3des", "3DES"),
    ("md5", "MD5"), ("md4", "MD4"), ("rc4", "RC4"),
    ("rsa", "RSA"), ("dsa", "DSA"), ("des", "3DES"),
    ("aes", "AES-256-GCM"),
]
for fragment, canonical in algo_hints:
    if fragment in rule_lower:
        return canonical
```

## Info

### IN-01: Stale RED-phase docstring in test file

**File:** `tests/test_cbom_builder.py:4`
**Issue:** The module docstring says "RED phase: all tests import from quirk.cbom.builder which does not exist yet." The builder module clearly exists and the tests are functional, so this comment is outdated.
**Fix:** Remove or update the "RED phase" comment to reflect the current state.

### IN-02: Generic "aes" fragment maps to specific "AES-256-GCM"

**File:** `quirk/cbom/builder.py:55`
**Issue:** In `_extract_algo_from_rule_id`, the fragment `"aes"` maps to `"AES-256-GCM"`. A semgrep rule mentioning AES could reference AES-128, AES-192, AES-CBC, etc. Mapping to a specific mode and key size is a best-guess that may not be accurate. Similarly, `"des"` maps to `"3DES"` when it could mean plain DES.
**Fix:** Consider mapping to a generic name (e.g., `"AES"` or `"DES"`) and letting the classifier handle the ambiguity, or add a code comment documenting this as a deliberate conservative mapping.

---

_Reviewed: 2026-04-24T12:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
