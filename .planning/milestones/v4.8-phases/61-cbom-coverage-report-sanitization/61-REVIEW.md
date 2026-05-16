---
phase: 61-cbom-coverage-report-sanitization
reviewed: 2026-05-10T00:00:00Z
depth: standard
files_reviewed: 6
files_reviewed_list:
  - quirk/cbom/builder.py
  - quirk/reports/_md_escape.py
  - quirk/reports/technical.py
  - tests/test_cbom_coverage.py
  - tests/test_cbom_vault_consistency.py
  - tests/test_report_sanitization.py
findings:
  critical: 0
  warning: 3
  info: 3
  total: 6
status: issues_found
---

# Phase 61: Code Review Report

**Reviewed:** 2026-05-10T00:00:00Z
**Depth:** standard
**Files Reviewed:** 6
**Status:** issues_found

## Summary

Phase 61 added 9 Pass-1 dispatch branches in `builder.py` covering previously zero-algo CBOM families, a GFM table-cell escape utility (`_md_escape.py`), and three new test files. The core escaping logic and most builder branches are sound. Three issues require attention before this code ships: one blocker in the sanitization test suite (a tautological assertion that cannot detect unescaped pipes per-cell), one correctness bug in the S3/AZURE_BLOB branch (false-positive AES-256 when encryption posture is unknown), and one spec-vs-implementation mismatch in the SSH D-07 fallback (registered unconditionally rather than as a true fallback).

---

## Critical Issues

None.

---

## Warnings

### WR-01: S3/AZURE_BLOB Branch Registers AES-256 for Unknown/Empty Encryption Posture

**File:** `quirk/cbom/builder.py:472-476`

**Issue:** When `ep.service_detail` is `None` or an empty string, `detail.lower()` is `""`, and `"unencrypted" not in ""` evaluates to `True`. The branch therefore registers `AES-256` as if the bucket is encrypted. This is a false positive: a missing or unpopulated `service_detail` field means the scan could not determine the encryption state, but the CBOM will report the asset as using AES-256 encryption. In a compliance or audit context this silently hides an "unknown posture" finding behind a passing algorithm entry.

```python
# Current code (line 472-476)
detail = ep.service_detail or ""
if "unencrypted" not in detail.lower():
    _register_algorithm("AES-256", algo_registry)

# Fix: require a non-empty known-encrypted sentinel before registering
ENCRYPTED_POSTURES = frozenset({
    "sse-s3", "sse-kms-aws", "sse-kms-cmk",          # S3
    "sse-cmek", "sse-microsoft-storage",               # Azure Blob
})
detail_lower = detail.lower()
# Only register when we have a positive confirmation of encryption
if any(posture in detail_lower for posture in ENCRYPTED_POSTURES):
    _register_algorithm("AES-256", algo_registry)
```

There is also no test covering the `None` or `""` `service_detail` case for this branch. A test should be added.

---

### WR-02: SSH D-07 Adds cert_pubkey_alg Unconditionally, Not as a Fallback

**File:** `quirk/cbom/builder.py:387-389`

**Issue:** Decision note D-07 states the `cert_pubkey_alg` registration is an "ssh-weak fallback when `ssh_audit_json` is empty", but the implementation runs unconditionally for every SSH endpoint regardless of whether `ssh_audit_json` was populated. When `ssh_audit_json` contains a `key` section with the host key algorithm (e.g., `ssh-rsa`), `cert_pubkey_alg` is typically the same key in a different name form (e.g., `"RSA"`). Because `_normalize_bom_ref_key("ssh-rsa")` produces `"ssh-rsa"` while `_normalize_bom_ref_key("RSA")` produces `"rsa"`, two distinct algorithm component entries are created for the same key material. This inflates the CBOM and could confuse downstream consumers comparing algorithm inventories.

```python
# Current code (lines 380-389)
ssh_data = _extract_ssh_algorithms(ep.ssh_audit_json)
for section in ("kex", "key", "enc", "mac"):
    for entry in ssh_data.get(section, []):
        alg = entry.get("algorithm")
        if alg:
            keysize = entry.get("keysize")
            _register_algorithm(alg, algo_registry, key_size=keysize)
# D-07: also register host key alg if present (ssh-weak fallback when ssh_audit_json is empty)
if ep.cert_pubkey_alg:
    _register_algorithm(ep.cert_pubkey_alg, algo_registry, key_size=ep.cert_pubkey_size)

# Fix: guard with the fallback condition that D-07 documents
if ep.cert_pubkey_alg and not ssh_data:
    _register_algorithm(ep.cert_pubkey_alg, algo_registry, key_size=ep.cert_pubkey_size)
```

The parametrized coverage test (`id="ssh-weak"`) exercises the correct fallback path (`ssh_audit_json=None`), so the test does not catch this issue for the populated-json case.

---

### WR-03: test_no_unescaped_pipe_in_data_cells Has a Tautological Per-Cell Assertion

**File:** `tests/test_report_sanitization.py:90-93`

**Issue:** The assertion inside the loop is logically incapable of detecting an unescaped pipe. The loop splits each row's interior on unescaped `|` characters using `re.split(r"(?<!\\)\|", interior)`. After this split, by definition no resulting cell element can contain a bare (unescaped) pipe — the split already consumed all of them. The subsequent `assert "|" not in cell.replace("\\|", "")` therefore always evaluates to `True` regardless of whether `md_cell()` escaped anything.

The overall test suite does not become blind to pipe injection (test 2, `test_consistent_column_count_per_section`, would catch a column-count mismatch caused by unescaped pipes), but `test_no_unescaped_pipe_in_data_cells` does not deliver on its stated contract of detecting unescaped pipes per-cell. A reader of this test will believe it provides stronger per-cell coverage than it actually does, which is a reliability and maintainability problem.

```python
# Current (tautological) assertion
cells = re.split(r"(?<!\\)\|", interior)
for cell in cells:
    assert "|" not in cell.replace("\\|", ""), ...   # always True after re.split

# Fix: count unescaped pipes in the ORIGINAL interior before splitting,
# and assert that all interior pipes are escaped
import re
unescaped_count = len(re.findall(r"(?<!\\)\|", interior))
expected_pipes = len(re.split(r"(?<!\\)\|", interior)) - 1  # pipes from column delimiters only
# All interior pipes should equal expected_pipes (the structural column delimiters)
# OR alternatively: verify the column count matches the header
# Simplest fix: assert there are no unescaped pipes inside any cell content by
# checking the stripped cells for bare pipes AFTER accounting for structural delimiters
```

A concrete minimal fix:

```python
# Replace the inner loop with a check on the row's internal pipe count
# that is NOT based on splitting on what you're trying to detect
stripped = interior.strip()
# All pipes in a valid data row interior should be escaped with backslash
bare_pipes = re.findall(r"(?<!\\)\|", stripped)
assert len(bare_pipes) == 0, (
    f"Unescaped pipe(s) found in row interior {stripped!r}"
)
```

---

## Info

### IN-01: md_cell Does Not Strip DEL (0x7F) or C1 Control Characters (0x80-0x9F)

**File:** `quirk/reports/_md_escape.py:33`

**Issue:** The filter condition `c == " " or c >= "\x20"` passes all Unicode code points >= 0x20, including DEL (0x7F) and the C1 control character block (0x80-0x9F). DEL and C1 controls are not GFM table-break vectors, but DEL in particular is the conventional "erase" char and can appear in terminal-sourced scan output. The docstring claims to strip "ASCII control chars (< 0x20)", which is accurate as written but leaves the DEL gap undocumented. The risk is that these characters will appear literally in rendered Markdown output.

**Fix:** Extend the filter to also strip 0x7F (DEL):

```python
text = "".join(c for c in text if c >= "\x20" and c != "\x7f")
```

---

### IN-02: Redundant `c == " "` Guard in md_cell Control-Char Filter

**File:** `quirk/reports/_md_escape.py:33`

**Issue:** The expression `c == " " or c >= "\x20"` has a dead left operand. Space is `chr(0x20)`, so `c >= "\x20"` already covers space. The `c == " "` clause is unreachable dead code.

**Fix:** Remove the redundant clause:

```python
text = "".join(c for c in text if c >= "\x20")
# Combined with IN-01 fix:
text = "".join(c for c in text if "\x20" <= c < "\x7f" or c > "\x7f")
```

---

### IN-03: _md_escape.py Has No `__all__` Declaration

**File:** `quirk/reports/_md_escape.py:1`

**Issue:** The module is intentionally private (underscore prefix) and exports a single public function `md_cell`. Without `__all__`, a `from quirk.reports._md_escape import *` would export everything in the module namespace. Adding `__all__` is the idiomatic way to document the module's public API and prevent accidental wildcard imports.

**Fix:**

```python
__all__ = ["md_cell"]
```

---

_Reviewed: 2026-05-10T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
