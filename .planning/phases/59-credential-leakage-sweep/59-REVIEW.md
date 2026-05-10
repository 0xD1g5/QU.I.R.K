---
phase: 59-credential-leakage-sweep
reviewed: 2026-05-09T21:00:00Z
depth: standard
files_reviewed: 13
files_reviewed_list:
  - quirk/cbom/writer.py
  - quirk/discovery/tls_scanner.py
  - quirk/scanner/broker_scanner.py
  - quirk/scanner/db_connector.py
  - quirk/scanner/email_scanner.py
  - quirk/scanner/gcp_connector.py
  - quirk/scanner/ssh_scanner.py
  - quirk/scanner/tls_scanner.py
  - quirk/scanner/vault_connector.py
  - quirk/util/safe_exc.py
  - tests/test_credential_leakage.py
  - tests/test_safe_exc.py
  - tests/test_scan_error_gate.py
findings:
  critical: 0
  warning: 3
  info: 1
  total: 4
status: issues_found
---

# Phase 59: Code Review Report

**Reviewed:** 2026-05-09T21:00:00Z
**Depth:** standard
**Files Reviewed:** 13
**Status:** issues_found

## Summary

Phase 59 adds the `safe_str` credential-scrubbing chokepoint (`quirk/util/safe_exc.py`), applies it to all `scan_error` writes across 9 scanner/connector files, and gates it with three test suites: a unit corpus (`test_safe_exc.py`), a behavior and import-presence regression suite (`test_credential_leakage.py`), and an AST static gate (`test_scan_error_gate.py`).

The core `safe_str` implementation is sound: class-name-only return on any pattern match, six compiled patterns covering the major credential shapes (Vault tokens, DSN passwords, GCP ADC paths, Authorization headers, long base64 tokens), and safe fallback when `str(exc)` itself raises. The AST gate logic is correct for the defined safe shapes.

Three issues warrant attention before this ships to production.

---

## Warnings

### WR-01: `db_connector.py` Missing from Import-Presence Gate

**File:** `tests/test_credential_leakage.py:18-27`

**Issue:** The commit modifies 9 files (confirmed by commit `14bd4c0` message: "All 9 files import from `quirk.util.safe_exc` import `safe_str`"), but `MODIFIED_FILES` in `test_credential_leakage.py` only lists 8 — `quirk/scanner/db_connector.py` is absent. The parametrized test `test_all_callsites_import_safe_str` therefore never checks that `db_connector.py` still imports `safe_str`. If a future edit removes that import, the gate silently misses it. The AST gate (`test_scan_error_gate.py`) does cover `db_connector.py` via `SCANNER_DIRS`, so `scan_error` write shapes are gated, but the import check is not.

**Fix:**
```python
MODIFIED_FILES = [
    "quirk/scanner/vault_connector.py",
    "quirk/scanner/gcp_connector.py",
    "quirk/scanner/tls_scanner.py",
    "quirk/scanner/email_scanner.py",
    "quirk/scanner/broker_scanner.py",
    "quirk/scanner/ssh_scanner.py",
    "quirk/scanner/db_connector.py",        # add this line
    "quirk/discovery/tls_scanner.py",
    "quirk/cbom/writer.py",
]
```

---

### WR-02: Base64 Pattern Causes False Positives on Diagnostic Data — Silently Drops Operator Context

**File:** `quirk/util/safe_exc.py:32`

**Issue:** Pattern 5 — `re.compile(r"\b[A-Za-z0-9+/]{40,}={0,2}\b")` — fires on any 40-or-more-character sequence of base64-legal characters. In practice this matches:

- SHA-256 fingerprints (64 hex chars, which are a subset of `[A-Za-z0-9]`)
- Certificate serial numbers
- GCP resource path components where a segment is 40+ alphanumeric characters (e.g., `longkeyringsthathasmorethanfortycharsinthename12345`)

When these appear in real connectivity error messages (e.g., an `HttpError` from the GCP API that includes a resource name), `safe_str` reduces the exception to the bare class name, stripping all diagnostic context the operator needs to debug the failure. Verified in a live test:

```python
>>> safe_str(Exception("Resource projects/myproject/locations/us-east1/keyRings/mykeyring/cryptoKeys/myencryptionkey-for-database-backups-prod not found"))
# => 'Exception'  when 'myencryptionkey...' path component crosses 40 chars
```

The credential classes this pattern is designed to catch (AWS secret keys, long API tokens) are genuinely long base64-like strings, so the intent is correct. The false positive risk is intrinsic to an overly broad character class.

**Fix:** Narrow the pattern to require base64 padding or a higher minimum length (e.g., 60+) to reduce false positives on hex digests, or add a hex-only exclusion. Alternatively, accept the current behaviour and document it as an explicit trade-off. At minimum, add a comment acknowledging the false-positive cost:

```python
# NOTE: [A-Za-z0-9+/]{40,} will also suppress SHA-256 hex digests and long
# GCP resource path segments when they appear in exception messages. This is an
# accepted trade-off: false positives lose operator debug context but never leak
# credentials; false negatives silently leak credentials. Tuning the threshold
# (currently 40) upward reduces false positives at the cost of missing shorter tokens.
re.compile(r"\b[A-Za-z0-9+/]{40,}={0,2}\b"),
```

---

### WR-03: AST Gate Does Not Cover `tls_blocker_reason` Writes — Future Leakage Vector Ungated

**File:** `tests/test_scan_error_gate.py:147-170`

**Issue:** `test_scan_error_writes_use_safe_str` walks every `.py` under `quirk/scanner/`, `quirk/discovery/`, and `quirk/cbom/` and checks all `scan_error` keyword arguments and `ep.scan_error` attribute assignments. It does not check `ep.tls_blocker_reason` writes. `tls_blocker_reason` is a persisted column on `CryptoEndpoint` (surfaced in `email_scan_json` at `email_scanner.py:595` and logged to the DB). Today it only stores string constants (`"CONNECTION_REFUSED"`, `"TIMEOUT"`, etc.) — but the gate provides no enforcement. A future developer adding `ep.tls_blocker_reason = str(exc)` would bypass all three test suites.

Currently safe because all existing writes are string literals:
- `tls_scanner.py:454` — `ep.tls_blocker_reason = cat` (where `cat` is output of `_categorize_tls_error()` which returns a string constant)
- `email_scanner.py:451, 458, 464` — all string literals

**Fix:** Extend `test_scan_error_writes_use_safe_str` to also flag raw exception data written to `tls_blocker_reason`:

```python
# In the ast.Assign check block, alongside the existing scan_error check:
if isinstance(target, ast.Attribute) and target.attr in ("scan_error", "tls_blocker_reason"):
    if not _classify_rhs(node.value, tree):
        violations.append((str(py_file.relative_to(PROJECT_ROOT)), node.lineno))
```

Also add `tls_blocker_reason` to the keyword-argument check in the `ast.Call` block.

---

## Info

### IN-01: `cbom/writer.py` Double-Wrap Pattern `safe_str(Exception(str(err)))` Is Fragile

**File:** `quirk/cbom/writer.py:79`

**Issue:** The validation error `err` returned by `validator.validate_str()` is a `JsonValidationError` (not a `BaseException` subclass), so `safe_str(err)` cannot be called directly — it requires wrapping. The current code uses `Exception(str(err))` to bridge the type gap:

```python
scan_error=f"CBOM JSON failed schema validation: {safe_str(Exception(str(err)))}",
```

`str(err)` is called _outside_ the `safe_str` try/except. If `str(err)` raises (which `safe_str` is designed to handle gracefully for `BaseException` subclasses), the exception propagates and the surrounding `try/except Exception` block at line 86 catches it — producing a second, generic CBOM advisory endpoint with a different message. The CBOM validation path then emits two advisory endpoints instead of one.

This is low probability (jsonschema `ValidationError.__str__` is well-behaved), but the intent — "never crash in the writer" — is violated by the ordering.

**Fix:** Wrap the string conversion inside a helper to ensure the raise case is handled gracefully:

```python
try:
    err_msg = str(err)
except Exception:
    err_msg = type(err).__name__
scan_error=f"CBOM JSON failed schema validation: {err_msg}",
```

Or, if `err` is confirmed to always support `str()`, add a comment explaining why the outer `str(err)` call is safe and why `Exception(str(err))` bridging is necessary:

```python
# err is JsonValidationError (not BaseException); wrap so safe_str() can scrub it.
# str(err) is safe here — jsonschema ValidationError.__str__ never raises.
scan_error=f"CBOM JSON failed schema validation: {safe_str(Exception(str(err)))}",
```

---

_Reviewed: 2026-05-09T21:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
