# Phase 23: DNSSEC CBOM Skip List Fix — Research

**Researched:** 2026-04-16
**Domain:** CycloneDX CBOM builder — Pass 2 certificate component skip list
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DNSSEC-04 | Results stored in `dnssec_scan_json` with `protocol="DNSSEC"` CryptoEndpoints; `DNSSEC_ALG_MAP` added to classifier; `build_cbom()` gains DNSSEC `elif` branches; DNSSEC added to Pass 2 cert skip list | Audit confirmed: Pass 1 DNSSEC `elif` branch exists and is correct. Classifier has all DNSSEC entries. Only Pass 2 skip list omits "DNSSEC". One-line fix + regression test. |
</phase_requirements>

---

## Summary

Phase 23 is a surgical gap closure. The entire fix is a **one-line change** to `quirk/cbom/builder.py`
line 389: add `"DNSSEC"` to the Pass 2 certificate component skip list tuple. The rest of DNSSEC-04
(Pass 1 algorithm branches, `DNSSEC_ALG_MAP` in classifier, `dnssec_scan_json` storage) was
implemented in Phases 18 and 22. The v4.2 milestone audit (2026-04-16) identified the single
remaining gap: the Pass 2 loop generates hollow `CertificateProperties(subject_name=None, ...)` 
X.509 components for every DNSSEC endpoint whose `cert_pubkey_alg` is non-null (i.e., all real
algorithm records — RSASHA256, ECDSAP256SHA256, etc.).

The fix is small but the testing story matters: the existing `tests/test_cbom_builder.py` has no
DNSSEC-specific test cases at all. SAML and KERBEROS both have coverage patterns (three tests each:
algorithm registered, no TLS protocol, no certificate). DNSSEC needs the same three-test pattern.
Writing tests first (RED), then the one-line fix (GREEN) follows the project's established TDD
practice perfectly.

The pre-existing test suite failure (`test_dashboard_wiring.py::test_deps_default_db_path`) is
unrelated to this phase and must not be fixed here — treat it as a known pre-existing failure.

**Primary recommendation:** Single-plan phase. TDD: write three failing DNSSEC tests in
`test_cbom_builder.py`, then add `"DNSSEC"` to the skip list tuple. No other files need changes.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| CBOM certificate component filtering | API / Backend | — | `build_cbom()` in `quirk/cbom/builder.py` is pure Python server-side logic; no frontend involvement |
| CycloneDX schema compliance | API / Backend | — | CycloneDX library validates structure; hollow cert components violate CertificateProperties semantics |
| DNSSEC algorithm registration (Pass 1) | API / Backend | — | Already correct — DNSSEC `elif` branch in Pass 1 is implemented and tested |
| Test coverage | API / Backend | — | `tests/test_cbom_builder.py` pytest unit tests |

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| cyclonedx-python-lib | (installed) | CycloneDX BOM construction | Project standard — all CBOM output goes through this library |
| pytest | 9.0.2 | Test runner | Project standard — `pyproject.toml` configures pytest |

### No new dependencies
This phase requires zero new library installations. The fix is a string literal addition to an
existing tuple inside an existing function.

---

## Architecture Patterns

### System Architecture Diagram

```
DNSSEC CryptoEndpoint (protocol="DNSSEC", cert_pubkey_alg="RSASHA256")
    |
    v
build_cbom() Pass 1
    ├── DNSSEC elif branch (EXISTS — alg registered correctly)
    |       cert_pubkey_alg="RSASHA256" --> algo_registry["rsasha256"]
    v
build_cbom() Pass 2  <-- BUG IS HERE
    ├── Skip list: ("SSH", "CONTAINER", "SOURCE", "KERBEROS", "SAML")
    |       "DNSSEC" NOT in list --> does NOT continue
    |       cert_pubkey_alg is non-null --> generates CertificateProperties(subject_name=None, ...)
    |       Result: hollow X.509 cert component in CBOM  [WRONG]
    v
build_cbom() Pass 3
    ├── DNSSEC is in the skip tuple at line 468 (EXISTS -- no protocol component generated)
    |
    v
CycloneDX Bom output
    ├── Correct: algorithm components for DNSKEY records
    ├── WRONG:   certificate components for DNSKEY records (spurious)
    └── Correct: no TLS protocol components for DNSSEC
```

**After fix:**
```
build_cbom() Pass 2
    ├── Skip list: ("SSH", "CONTAINER", "SOURCE", "KERBEROS", "SAML", "DNSSEC")
    |       "DNSSEC" IS in list --> continue (skip)
    |       Result: no certificate component generated  [CORRECT]
```

### Recommended Project Structure

No new directories or modules. Changes are confined to:
```
quirk/cbom/
└── builder.py          # Line 389: add "DNSSEC" to skip tuple

tests/
└── test_cbom_builder.py  # Add 3 DNSSEC test cases (mirroring SAML/KERBEROS pattern)
```

### Pattern 1: Pass 2 Certificate Skip List

**What:** Pass 2 of `build_cbom()` iterates all endpoints and generates `CertificateProperties`
components for endpoints that have X.509 cert metadata (`cert_pubkey_alg`, `cert_subject`, etc.).
Non-TLS protocols that store algorithm names in `cert_pubkey_alg` for convenience (not because
they represent actual X.509 certificates) must be excluded from this pass via the skip list.

**Current state (buggy):**
```python
# quirk/cbom/builder.py line 389
# Source: [VERIFIED: codebase grep]
for ep in endpoints:
    if ep.protocol in ("SSH", "CONTAINER", "SOURCE", "KERBEROS", "SAML"):
        continue
    if not ep.cert_pubkey_alg:
        continue  # no cert info available
```

**Fixed state:**
```python
for ep in endpoints:
    if ep.protocol in ("SSH", "CONTAINER", "SOURCE", "KERBEROS", "SAML", "DNSSEC"):
        continue
    if not ep.cert_pubkey_alg:
        continue  # no cert info available
```

**Why `cert_pubkey_alg` is non-null for DNSSEC endpoints:** The DNSSEC scanner stores the
algorithm name in `cert_pubkey_alg` as a convention for carrying algorithm data through the
`CryptoEndpoint` model's existing fields — not because a real X.509 certificate was observed.
Values like `"RSASHA256"`, `"ECDSAP256SHA256"`, `"NONE"`, `"NSEC"`, `"DS-MISMATCH"` are all
stored here. The `if not ep.cert_pubkey_alg: continue` guard on the next line does NOT protect
against this because `cert_pubkey_alg` IS set for all real algorithm records.

### Pattern 2: TDD Three-Test Pattern for Identity Protocols

SAML and KERBEROS each have three builder tests that form the verification template for any
identity protocol added to the skip list. DNSSEC must follow the same pattern.

**Existing SAML pattern (lines 421–442, test_cbom_builder.py):**
```python
def test_saml_endpoint_algorithm_registered():
    """SAML endpoint registers algorithm component from cert_pubkey_alg."""
    # Verifies Pass 1 still fires correctly

def test_saml_endpoint_no_tls_protocol():
    """SAML endpoint must NOT produce a TLS protocol component."""
    # Verifies Pass 3 skip is working

def test_saml_endpoint_no_certificate():
    """SAML SHA1 finding must NOT produce a certificate component (no cert metadata)."""
    # Verifies Pass 2 skip is working
```

**Required DNSSEC tests (to write in RED phase):**
```python
def test_dnssec_endpoint_algorithm_registered():
    """DNSSEC endpoint registers algorithm component from cert_pubkey_alg."""

def test_dnssec_endpoint_no_tls_protocol():
    """DNSSEC endpoint must NOT produce a TLS protocol component."""

def test_dnssec_endpoint_no_certificate():
    """DNSSEC endpoint must NOT produce a certificate component."""
```

The third test (`no_certificate`) will FAIL (RED) before the fix — this is the targeted regression
test that verifies the skip list omission. The first two will pass immediately because Pass 1 and
Pass 3 are already correct.

**Note on synthetic DNSSEC findings:** The scanner produces endpoints with `cert_pubkey_alg` values
of `"NONE"`, `"NSEC"`, `"DS-MISMATCH"`, and `"SHA1-DS"` for synthetic findings. Pass 1 already
excludes these (explicit exclusion filter at line 354). The `no_certificate` test should use a
real algorithm name like `"ECDSAP256SHA256"` to exercise the hollow-cert scenario being fixed.

### Anti-Patterns to Avoid

- **Testing only the synthetic finding types:** `cert_pubkey_alg="NONE"` passes the existing
  `if not ep.cert_pubkey_alg` guard in Pass 2, so it would never generate a hollow cert. Tests
  must use a real algorithm name (e.g. `"ECDSAP256SHA256"`, `"RSASHA256"`) to reproduce the bug.
- **Touching Pass 1 or Pass 3:** Both passes handle DNSSEC correctly already. The fix is Pass 2 only.
- **Fixing the pre-existing `test_dashboard_wiring` failure:** Out of scope. Do not touch it.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Protocol skip filtering | Custom filtering logic | `ep.protocol in (...)` tuple membership | Already established pattern in codebase for all other protocols |
| CycloneDX component construction | Custom serialization | `cyclonedx-python-lib` Component/CryptoProperties | Already used throughout builder.py |

---

## Common Pitfalls

### Pitfall 1: Testing with NONE/NSEC/DS-MISMATCH instead of a real algorithm

**What goes wrong:** A test using `cert_pubkey_alg="NONE"` will appear to pass even without
the fix because `"NONE"` gets excluded by Pass 1's synthetic filter — `cert_pubkey_alg` is still
technically set, but the hollow cert is never generated for these values in the current code.
Actually, they WOULD generate hollow certs since Pass 1's filter is only for algorithm registration,
not Pass 2. But using a real algorithm name like `"ECDSAP256SHA256"` more precisely models the
production scenario (real DNSKEY records always have real algorithm names).

**Why it happens:** Confusion between Pass 1 exclusion (synthetic values excluded from algorithm
registry) and Pass 2 behavior (any non-null `cert_pubkey_alg` triggers cert component).

**How to avoid:** Use `cert_pubkey_alg="ECDSAP256SHA256"` or `"RSASHA256"` in the no-certificate
test.

### Pitfall 2: Assuming Pass 2 is the only place DNSSEC needs adding

**What goes wrong:** Over-engineering the fix by also modifying Pass 1 or Pass 3.

**Why it happens:** Unfamiliarity with which passes already handle DNSSEC.

**How to avoid:** Review the audit evidence. Pass 1 has an explicit `elif ep.protocol == "DNSSEC":`
branch at line 351. Pass 3 lists `"DNSSEC"` in its skip tuple at line 468. Only Pass 2 (line 389)
is missing it.

### Pitfall 3: Misreading the existing test count

**What goes wrong:** Running `test_cbom_builder.py` shows 27 passing tests — confusing the
planner into thinking no new tests are needed.

**Why it happens:** The existing 27 tests have no DNSSEC coverage at all.

**How to avoid:** Phase 23 adds 3 tests, bringing total to 30. The 3 new tests must be written
first (two GREEN immediately, one RED until the fix is applied).

---

## Code Examples

### Exact fix location

```python
# quirk/cbom/builder.py  — Pass 2 loop, line 389
# Source: [VERIFIED: codebase read]

# CURRENT (buggy):
    if ep.protocol in ("SSH", "CONTAINER", "SOURCE", "KERBEROS", "SAML"):
        continue

# FIXED:
    if ep.protocol in ("SSH", "CONTAINER", "SOURCE", "KERBEROS", "SAML", "DNSSEC"):
        continue
```

### Test fixture for DNSSEC endpoint

```python
# Source: [VERIFIED: mirrors existing _saml_endpoint / _kerberos_endpoint patterns]

def _dnssec_endpoint(**overrides):
    """Create a DNSSEC CryptoEndpoint with sensible defaults."""
    defaults = dict(
        host="example.com", port=53, protocol="DNSSEC",
        tls_version=None, cipher_suite=None,
        cert_pubkey_alg="ECDSAP256SHA256", cert_pubkey_size=256,
        cert_sig_alg=None, cert_subject=None, cert_issuer=None,
        cert_not_before=None, cert_not_after=None,
        tls_capabilities_json=None, ssh_audit_json=None,
    )
    defaults.update(overrides)
    return CryptoEndpoint(**defaults)
```

### Three new tests

```python
# Source: [VERIFIED: mirrors SAML/KERBEROS pattern at lines 421-478 of test_cbom_builder.py]

def test_dnssec_endpoint_algorithm_registered():
    """DNSSEC endpoint registers algorithm component from cert_pubkey_alg."""
    ep = _dnssec_endpoint(cert_pubkey_alg="ECDSAP256SHA256", cert_pubkey_size=256)
    bom = build_cbom([ep])
    algo_refs = [c.bom_ref for c in bom.components if "crypto/algorithm/" in str(c.bom_ref)]
    assert any("ecdsap256sha256" in str(ref) for ref in algo_refs), \
        f"ECDSAP256SHA256 algorithm not found in {algo_refs}"


def test_dnssec_endpoint_no_tls_protocol():
    """DNSSEC endpoint must NOT produce a TLS protocol component."""
    ep = _dnssec_endpoint()
    bom = build_cbom([ep])
    tls_protos = [c for c in bom.components
                  if str(c.bom_ref).startswith("crypto/protocol/tls/")]
    assert tls_protos == [], \
        f"Spurious TLS protocol components for DNSSEC: {[str(c.bom_ref) for c in tls_protos]}"


def test_dnssec_endpoint_no_certificate():
    """DNSSEC endpoint must NOT produce a certificate component (DNSKEY is not an X.509 cert)."""
    ep = _dnssec_endpoint(cert_pubkey_alg="ECDSAP256SHA256", cert_pubkey_size=256)
    bom = build_cbom([ep])
    cert_comps = [c for c in bom.components
                  if str(c.bom_ref).startswith("crypto/certificate/")]
    assert cert_comps == [], \
        f"Spurious certificate components for DNSSEC: {[str(c.bom_ref) for c in cert_comps]}"
    # NOTE: This test is RED before the fix (add "DNSSEC" to Pass 2 skip list in builder.py line 389)
```

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | `pyproject.toml` |
| Quick run command | `python -m pytest tests/test_cbom_builder.py -x -q` |
| Full suite command | `python -m pytest tests/ -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| DNSSEC-04 | DNSSEC endpoint registers algorithm component | unit | `python -m pytest tests/test_cbom_builder.py::test_dnssec_endpoint_algorithm_registered -x` | Wave 0 |
| DNSSEC-04 | DNSSEC endpoint generates no TLS protocol component | unit | `python -m pytest tests/test_cbom_builder.py::test_dnssec_endpoint_no_tls_protocol -x` | Wave 0 |
| DNSSEC-04 | DNSSEC endpoint generates no certificate component | unit | `python -m pytest tests/test_cbom_builder.py::test_dnssec_endpoint_no_certificate -x` | Wave 0 (RED test) |

### Sampling Rate

- **Per task commit:** `python -m pytest tests/test_cbom_builder.py -x -q`
- **Per wave merge:** `python -m pytest tests/ -x -q --ignore=tests/test_dashboard_wiring.py`
- **Phase gate:** Full suite (minus pre-existing failure) green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_cbom_builder.py` — add `_dnssec_endpoint()` fixture + 3 DNSSEC test cases
  (2 immediately GREEN for Pass 1/Pass 3 correctness, 1 RED for Pass 2 skip list gap)

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | no | CBOM generation is internal transform; no external input |
| V6 Cryptography | no | This phase generates CBOM documentation — no crypto operations performed |

No security surface is introduced or modified by this phase.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| DNSSEC absent from Pass 2 skip list | Add "DNSSEC" to tuple | Phase 23 | Hollow X.509 cert components no longer generated |

**Deprecated/outdated:** N/A — this phase is a defect fix, not an API evolution.

---

## Open Questions

None. The fix is fully understood from the audit report and code inspection.

---

## Environment Availability

Step 2.6: SKIPPED (no external dependencies — pure Python code and test change).

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| — | — | — | — |

**All claims in this research were verified directly from codebase inspection.** No assumed claims.

---

## Sources

### Primary (HIGH confidence)

- `quirk/cbom/builder.py` lines 386–426 — Pass 2 loop, current skip tuple, cert component generation logic [VERIFIED: codebase read]
- `quirk/cbom/builder.py` lines 349–355 — Pass 1 DNSSEC elif branch [VERIFIED: codebase read]
- `quirk/cbom/builder.py` lines 468–471 — Pass 3 skip tuple (DNSSEC present) [VERIFIED: codebase read]
- `tests/test_cbom_builder.py` lines 421–478 — SAML and KERBEROS test patterns to mirror [VERIFIED: codebase read]
- `.planning/v4.2-MILESTONE-AUDIT.md` — Audit report identifying exact line, fix, and impact [VERIFIED: codebase read]
- `quirk/cbom/classifier.py` lines 148–159 — DNSSEC algorithm entries present in classifier [VERIFIED: codebase read]
- `quirk/scanner/dnssec_scanner.py` lines 249–260 — cert_pubkey_alg is always set for real DNSKEY records [VERIFIED: codebase read]

### Test Baseline (HIGH confidence)

- 27 tests pass in `test_cbom_builder.py` (0 DNSSEC tests exist) [VERIFIED: pytest run]
- 350 pass / 3 skip in full suite; 1 pre-existing failure in `test_dashboard_wiring.py` unrelated to this phase [VERIFIED: pytest run]

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new libraries; uses existing cyclonedx-python-lib and pytest
- Architecture: HIGH — exact file, exact line, exact fix verified from source and audit
- Pitfalls: HIGH — derived from direct code inspection, not heuristic reasoning

**Research date:** 2026-04-16
**Valid until:** Stable — builder.py structure is stable; this research is valid until the builder is restructured
