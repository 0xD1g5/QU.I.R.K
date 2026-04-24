---
phase: 23-dnssec-cbom-skip-fix
fixed_at: 2026-04-24T12:15:00Z
review_path: .planning/phases/23-dnssec-cbom-skip-fix/23-REVIEW.md
iteration: 1
findings_in_scope: 3
fixed: 3
skipped: 0
status: all_fixed
---

# Phase 23: Code Review Fix Report

**Fixed at:** 2026-04-24T12:15:00Z
**Source review:** .planning/phases/23-dnssec-cbom-skip-fix/23-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 3
- Fixed: 3
- Skipped: 0

## Fixed Issues

### WR-01: Unhandled json.JSONDecodeError on cloud_scan_json

**Files modified:** `quirk/cbom/builder.py`
**Commit:** 988e7b1
**Applied fix:** Wrapped the `json.loads(ep.cloud_scan_json or "{}")` call at line 340 in a try/except catching `json.JSONDecodeError`, `TypeError`, and `ValueError`, falling back to an empty dict. This makes the cloud JSON parsing consistent with the SSH path (`_extract_ssh_algorithms`) which already has the same guard.

### WR-02: AES-CCM cipher suites misclassified as AES-GCM

**Files modified:** `quirk/cbom/builder.py`, `quirk/cbom/classifier.py`
**Commit:** fbb5433
**Applied fix:** Corrected `_ENC_MAP` entries for `AES_256_CCM` and `AES_128_CCM` to map to `"AES-256-CCM"` and `"AES-128-CCM"` respectively (was incorrectly mapping to GCM variants). Added corresponding `"aes-256-ccm"` and `"aes-128-ccm"` entries to `_ALGORITHM_TABLE` in `classifier.py` with `CryptoPrimitive.AE` classification so the new canonical names are recognized by the classifier.

### WR-03: Substring match in _extract_algo_from_rule_id produces false positives for "dsa"

**Files modified:** `quirk/cbom/builder.py`
**Commit:** e712696
**Applied fix:** Replaced the unordered `dict` in `_extract_algo_from_rule_id` with an ordered list of `(fragment, canonical)` tuples. Longer/more-specific patterns are checked first: `"ecdsa"` before `"dsa"`, `"3des"` before `"des"`. Also added `"ecdsa" -> "ECDSA"` mapping which was previously missing entirely. This prevents ECDSA-related semgrep rules from being misclassified as plain DSA.

---

_Fixed: 2026-04-24T12:15:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
