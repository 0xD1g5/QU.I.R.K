---
phase: 24-scan-session-timestamp
reviewed: 2026-04-24T00:00:00Z
depth: standard
files_reviewed: 8
files_reviewed_list:
  - quirk/scanner/dnssec_scanner.py
  - quirk/scanner/kerberos_scanner.py
  - quirk/scanner/saml_scanner.py
  - run_scan.py
  - tests/test_dnssec_scanner.py
  - tests/test_identity_surface.py
  - tests/test_kerberos_scanner.py
  - tests/test_saml_scanner.py
findings:
  critical: 0
  warning: 4
  info: 3
  total: 7
status: issues_found
---

# Phase 24: Code Review Report

**Reviewed:** 2026-04-24T00:00:00Z
**Depth:** standard
**Files Reviewed:** 8
**Status:** issues_found

## Summary

Phase 24 threaded a shared `session_start` parameter through three identity scanner entry points
(`scan_dnssec_targets`, `scan_saml_targets`, `scan_kerberos_targets`) and wired the shared
timestamp in `run_scan.py`. The core correctness of the timestamp threading is sound: the
`(session_start or datetime.now(timezone.utc)).replace(tzinfo=None)` pattern is applied
consistently at entry-point level in all three scanners, and `run_scan.py` passes an aware UTC
datetime to all three callers.

Four warnings are raised. The most significant is a **timezone stripping inconsistency** in the
SAML scanner's inner parse functions: `_parse_saml_metadata` and `_parse_oidc_discovery` each
contain their own `datetime.now(timezone.utc).replace(tzinfo=None)` fallback that is reached when
`now=None` — but this path is now dead code for session-start callers, creating a latent correctness
risk if those inner functions are ever called directly. The DNSSEC scanner has a symmetric design
flaw: `now` is computed in `_scan_domain` (the inner function) rather than at the entry point,
meaning that in multi-domain scans the inner datetime fallback can fire independently per domain
even when `session_start` is `None`, producing non-uniform timestamps across domains within the same
call. Two test-quality warnings round out the findings.

No security vulnerabilities or data-loss bugs were found.

---

## Warnings

### WR-01: DNSSEC `now` computed inside inner function, not at entry point

**File:** `quirk/scanner/dnssec_scanner.py:188`

**Issue:** `now` is computed inside `_scan_domain` rather than at the `scan_dnssec_targets` entry
point. The `session_start` parameter is forwarded correctly, but the pattern `(session_start or
datetime.now(timezone.utc)).replace(tzinfo=None)` executes once **per domain** inside the loop.
When `session_start` is `None` (e.g., in tests that do not pass `session_start`), each domain
call independently calls `datetime.now()`, which can yield different naive datetimes for
long-running multi-domain scans. By contrast, Kerberos and SAML compute `now` once at entry-point
level before the loop. The inconsistency is not triggered by the Phase 24 fix (since
`run_scan.py` always passes a non-`None` `session_start`), but it is a latent regression for
callers that omit `session_start`.

**Fix:** Move `now` computation to `scan_dnssec_targets`, before the domain loop, then pass it
into `_scan_domain`:

```python
# scan_dnssec_targets (entry point)
def scan_dnssec_targets(targets: list, timeout: int = 10, logger=None, session_start=None) -> list:
    ...
    now = (session_start or datetime.now(timezone.utc)).replace(tzinfo=None)
    results = []
    for domain in targets:
        try:
            results.extend(_scan_domain(domain, timeout, logger, now=now))
        ...

# _scan_domain — accept pre-computed now; remove local computation
def _scan_domain(domain: str, timeout: int, logger, now) -> list:
    ...
    # Remove: now = (session_start or datetime.now(timezone.utc)).replace(tzinfo=None)
```

---

### WR-02: SAML inner parse functions have dead `now=None` fallback after session_start threading

**File:** `quirk/scanner/saml_scanner.py:184-185` and `quirk/scanner/saml_scanner.py:326-327`

**Issue:** `_parse_saml_metadata` and `_parse_oidc_discovery` both accept a `now` parameter and
include a local fallback:

```python
if now is None:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
```

`scan_saml_targets` now always passes `now=now` (the pre-computed `session_start`-derived value),
so the `now is None` branch is dead code for the production call path. The risk is: if either
inner function is called directly in a future test or utility without `now=`, it silently uses a
fresh `datetime.now()` instead of raising, masking the missing argument. The test
`test_saml_session_start_stamps_all_endpoints` does not exercise the inner functions directly, so
the dead fallback is not caught.

Additionally, `_parse_saml_metadata` re-serializes `scan_dict` to JSON for each endpoint as it is
added (lines 224, 252, 270, 288), then overwrites with a `final_json` pass at line 293-295. This
means intermediate endpoints carry stale JSON that excludes later-added certs/URIs. The final pass
fixes this, but the approach is fragile. This is a pre-existing pattern, not introduced in Phase 24,
but worth noting.

**Fix for the `now=None` fallback:** Make `now` a required positional argument in both inner
functions so callers cannot accidentally omit it:

```python
def _parse_saml_metadata(xml_bytes: bytes, target_url: str, now) -> "tuple[list, dict]":
    # Remove the `if now is None:` guard entirely

def _parse_oidc_discovery(json_bytes: bytes, target_url: str, now) -> "tuple[list, dict]":
    # Remove the `if now is None:` guard entirely
```

Update the docstrings to reflect that `now` is required. The call sites in `scan_saml_targets`
already pass `now=now`, so no call-site changes are needed.

---

### WR-03: `test_dnssec_session_start_stamps_all_endpoints` docstring claims RED but test was written GREEN

**File:** `tests/test_dnssec_scanner.py:522-523`

**Issue:** The docstring reads:

```
RED: scan_dnssec_targets does not accept session_start yet — TypeError expected.
```

But the test body calls `scan_dnssec_targets(["weak.example.com"], session_start=fixed_dt)` and
asserts `ep.scanned_at == expected_naive`. This is a GREEN assertion — if `session_start` were
missing, the test would raise `TypeError` before reaching the assertion, not produce a meaningful
failure. The docstring is stale from the Wave 1 RED scaffold and was not updated when Wave 2
implemented the GREEN fix. The same stale docstring pattern appears in the parallel tests for
Kerberos (`tests/test_kerberos_scanner.py:403-404`) and SAML (`tests/test_saml_scanner.py:401-402`).

This misleads future contributors about the test's current intent and state.

**Fix:** Update all three docstrings to reflect the GREEN state:

```python
# test_dnssec_scanner.py:522
"""ISSUE-3 GREEN: scan_dnssec_targets(session_start=<fixed_dt>) stamps all endpoints
with the fixed naive datetime, verifying session_start is correctly threaded."""

# test_kerberos_scanner.py:403
"""ISSUE-3 GREEN: scan_kerberos_targets(session_start=<fixed_dt>) stamps all endpoints
with the fixed naive datetime."""

# test_saml_scanner.py:401
"""ISSUE-3 GREEN: scan_saml_targets(session_start=<fixed_dt>) stamps all endpoints
with the fixed naive datetime."""
```

---

### WR-04: `test_as_req_both_fail_graceful` has a redundant inner `patch` that shadows the outer one

**File:** `tests/test_kerberos_scanner.py:194-197`

**Issue:** The test opens two overlapping patches for `_probe_kdc_udp`:

```python
with patch.object(kmod, "IMPACKET_AVAILABLE", True), \
     _patch_probe_kdc_raises(kmod, OSError("TCP timeout")), \
     _patch_probe_kdc_udp(kmod, None) as mock_udp_fail, \   # outer — returns None
     _patch_probe_ldap(kmod, ldap_skip):
    with patch.object(kmod, '_probe_kdc_udp', side_effect=OSError("UDP timeout")):  # inner — raises
        results = scan_kerberos_targets(["unreachable.host"], timeout=1)
```

The outer `_patch_probe_kdc_udp(kmod, None)` is immediately shadowed by the inner
`patch.object(kmod, '_probe_kdc_udp', side_effect=OSError(...))`. The `mock_udp_fail` reference is
never asserted and the outer patch serves no functional purpose. The test works correctly because
the inner patch wins, but the redundant outer patch adds confusion about test intent. If the inner
patch were removed, `_probe_kdc_udp` would return `None` — and since the production code checks
`if etypes is None:` to detect dual failure, this would still work. The redundant patch should be
removed.

**Fix:**

```python
def test_as_req_both_fail_graceful():
    import quirk.scanner.kerberos_scanner as kmod
    ldap_skip = {"ldap_status": "skipped"}
    with patch.object(kmod, "IMPACKET_AVAILABLE", True), \
         _patch_probe_kdc_raises(kmod, OSError("TCP timeout")), \
         patch.object(kmod, '_probe_kdc_udp', side_effect=OSError("UDP timeout")), \
         _patch_probe_ldap(kmod, ldap_skip):
        results = scan_kerberos_targets(["unreachable.host"], timeout=1)
    assert len(results) == 1
    assert results[0].service_detail == "kerberos-unreachable"
```

---

## Info

### IN-01: `run_scan.py` computes `session_start` after cloud connector phases, not before all scanners

**File:** `run_scan.py:463`

**Issue:** `session_start = datetime.now(timezone.utc)` is placed at line 463, after the AWS and
Azure cloud connector phases complete (lines 441-461). If those connector phases are slow (e.g.,
large AWS account with many KMS keys), the `session_start` timestamp will be later than the actual
start of the identity scan pipeline. This is not a bug — the intent is that DNSSEC, SAML, and
Kerberos share one timestamp — but the variable name `session_start` suggests it captures the
scan session start, while it actually captures a mid-scan timestamp. A clearer name (e.g.,
`identity_scan_start`) would reduce confusion for future maintainers.

**Suggestion:** Either rename the variable to `identity_scan_start` and update all three call
sites, or move it to immediately before the first identity scanner call (line 467) and add a
comment clarifying scope:

```python
# Shared timestamp for all three identity scanners — ensures DNSSEC, SAML, and
# Kerberos endpoints from this run share one scanned_at value (ISSUE-3 fix).
identity_scan_start = datetime.now(timezone.utc)
```

---

### IN-02: `_fetch_metadata` disables SSL verification globally with `verify=False`

**File:** `quirk/scanner/saml_scanner.py:61`

**Issue:** `httpx.get(..., verify=False)` suppresses SSL certificate validation for all SAML/OIDC
metadata fetches. The comment says "Disables SSL verification for enterprise CAs (D-13, D-14)",
which is intentional. This is a pre-existing design decision, not introduced in Phase 24. However,
it warrants a note: if this scanner is ever used against untrusted networks, there is no protection
against MITM attacks on the metadata fetch itself, which could inject a malicious signing
certificate into the CBOM. Callers relying on this scanner for compliance evidence should be aware
of this limitation.

**Suggestion:** Add a log-level warning when `verify=False` is active, so operators know
certificate validation is bypassed:

```python
logging.getLogger(__name__).debug(
    "SAML fetch: SSL verification disabled for %s (enterprise CA mode)", url
)
```

---

### IN-03: `test_identity_surface.py` `Issue3ScanWindowRegressionTest` uses a shared-memory SQLite URI that can leak state between test runs

**File:** `tests/test_identity_surface.py:492`

**Issue:** The test creates an in-memory SQLite engine with `cache=shared`:

```python
engine = create_engine(
    "sqlite:///file::memory:?cache=shared&uri=true",
    ...
)
```

The `cache=shared` URI means all connections within the process that use the same URI string share
the same in-memory database. If another test (or a parallel test worker) also creates a
`cache=shared` connection to `file::memory:`, they will see each other's data. In a `pytest -n`
parallel run or in a test session that exercises the API app multiple times, this can cause
non-deterministic failures (stale rows from prior tests). The conftest pattern (referenced in the
comment) typically uses a per-test `StaticPool` instead.

**Suggestion:** Use a `StaticPool` or a unique per-test memory URI to avoid cross-test state:

```python
from sqlalchemy.pool import StaticPool
engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
```

---

_Reviewed: 2026-04-24T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
