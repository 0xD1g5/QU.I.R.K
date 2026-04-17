# Phase 23: DNSSEC CBOM Skip List Fix — Pattern Map

**Mapped:** 2026-04-16
**Files analyzed:** 2
**Analogs found:** 2 / 2

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `quirk/cbom/builder.py` | service | transform | `quirk/cbom/builder.py` (Pass 3 skip tuple at line 468) | exact — same tuple pattern in same function |
| `tests/test_cbom_builder.py` | test | batch | `tests/test_cbom_builder.py` lines 421–478 (SAML + KERBEROS three-test block) | exact — same TDD three-test pattern, same fixture factory pattern |

---

## Pattern Assignments

### `quirk/cbom/builder.py` (service, transform)

**Change:** One-line addition — add `"DNSSEC"` to the Pass 2 certificate skip tuple at line 389.

**Analog:** Pass 3 skip tuple in the same file (line 468), which already lists `"DNSSEC"`.

**Existing Pass 3 skip tuple — confirmed correct template** (line 468):
```python
elif ep.protocol in ("JWT", "CONTAINER", "SOURCE", "AWS", "AZURE", "DNSSEC", "SAML", "KERBEROS"):
    # These are not TLS/SSH network protocols — no ProtocolProperties component.
    # Their cryptographic assets are captured in Pass 1 (algorithms) and Pass 2 (certificates).
    continue
```

**Current (buggy) Pass 2 skip tuple** (`quirk/cbom/builder.py` line 389):
```python
for ep in endpoints:
    if ep.protocol in ("SSH", "CONTAINER", "SOURCE", "KERBEROS", "SAML"):
        continue
    if not ep.cert_pubkey_alg:
        continue  # no cert info available
```

**Fixed Pass 2 skip tuple** (add `"DNSSEC"` — the entire change):
```python
for ep in endpoints:
    if ep.protocol in ("SSH", "CONTAINER", "SOURCE", "KERBEROS", "SAML", "DNSSEC"):
        continue
    if not ep.cert_pubkey_alg:
        continue  # no cert info available
```

**Why this pattern:** Non-TLS protocols that store algorithm names in `cert_pubkey_alg` as a
convention (not because a real X.509 certificate was observed) must be excluded from Pass 2.
DNSSEC stores algorithm names like `"RSASHA256"`, `"ECDSAP256SHA256"` in `cert_pubkey_alg` — the
`if not ep.cert_pubkey_alg` guard does NOT protect against this because the field IS set for all
real algorithm records.

**Pass 1 DNSSEC branch (already correct — do not touch)** (lines 351–355):
```python
elif ep.protocol == "DNSSEC":
    # DNSSEC: cert_pubkey_alg holds the DNSKEY algorithm name
    # Exclude synthetic finding types — they are not real cryptographic algorithms
    if ep.cert_pubkey_alg and ep.cert_pubkey_alg not in ("NONE", "NSEC", "DS-MISMATCH", "SHA1-DS"):
        _register_algorithm(ep.cert_pubkey_alg, algo_registry, key_size=ep.cert_pubkey_size)
```

---

### `tests/test_cbom_builder.py` (test, batch)

**Change:** Add `_dnssec_endpoint()` fixture factory + 3 DNSSEC test cases after the KERBEROS block (currently ending at line 478).

**Analog:** SAML three-test block (lines 421–442) and KERBEROS three-test block (lines 449–478) — exact structural template.

**Imports pattern** (`tests/test_cbom_builder.py` lines 1–18):
```python
from __future__ import annotations

import json
import pytest

from quirk.models import CryptoEndpoint
from quirk.cbom.builder import build_cbom

from cyclonedx.model.bom import Bom
from cyclonedx.model.component import Component, ComponentType
from cyclonedx.model.crypto import CryptoAssetType, ProtocolPropertiesType
```

**Fixture factory pattern** — copy from `_saml_endpoint` (lines 72–83) / `_kerberos_endpoint` (lines 86–97):
```python
def _saml_endpoint(**overrides):
    """Create a SAML CryptoEndpoint with sensible defaults."""
    defaults = dict(
        host="idp.example.com", port=443, protocol="SAML",
        tls_version=None, cipher_suite=None,
        cert_pubkey_alg="RSA", cert_pubkey_size=2048,
        cert_sig_alg=None, cert_subject=None, cert_issuer=None,
        cert_not_before=None, cert_not_after=None,
        tls_capabilities_json=None, ssh_audit_json=None,
    )
    defaults.update(overrides)
    return CryptoEndpoint(**defaults)
```

**DNSSEC fixture to write** (mirrors `_saml_endpoint` / `_kerberos_endpoint` exactly):
```python
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

**Three-test pattern to copy** — full KERBEROS block (lines 449–478) as the structural template:
```python
def test_kerberos_endpoint_algorithm_registered():
    """Kerberos endpoint registers algorithm component from etype name."""
    ep = _kerberos_endpoint(cert_pubkey_alg="rc4-hmac")
    bom = build_cbom([ep])
    algo_refs = [str(c.bom_ref) for c in bom.components if "crypto/algorithm/" in str(c.bom_ref)]
    assert any("rc4-hmac" in ref for ref in algo_refs), f"rc4-hmac algorithm not found in {algo_refs}"


def test_kerberos_endpoint_no_tls_protocol():
    """Kerberos endpoint must NOT produce a TLS protocol component."""
    ep = _kerberos_endpoint()
    bom = build_cbom([ep])
    tls_protos = [c for c in bom.components if str(c.bom_ref).startswith("crypto/protocol/tls/")]
    assert tls_protos == [], f"Spurious TLS protocol components for Kerberos: {[str(c.bom_ref) for c in tls_protos]}"


def test_kerberos_endpoint_no_certificate():
    """Kerberos etype endpoint must NOT produce a certificate component."""
    ep = _kerberos_endpoint(cert_pubkey_alg="rc4-hmac")
    bom = build_cbom([ep])
    cert_comps = [c for c in bom.components if str(c.bom_ref).startswith("crypto/certificate/")]
    assert cert_comps == [], f"Spurious certificate components for Kerberos: {[str(c.bom_ref) for c in cert_comps]}"
```

**Three DNSSEC tests to write** (direct translation of the kerberos block):
```python
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

**TDD execution order:**
1. Write `_dnssec_endpoint()` fixture + all 3 tests (RED phase).
2. Run `python -m pytest tests/test_cbom_builder.py -x -q` — expect `test_dnssec_endpoint_no_certificate` to FAIL, first two to PASS.
3. Add `"DNSSEC"` to the Pass 2 skip tuple in `builder.py` line 389 (GREEN phase).
4. Re-run — all 3 tests PASS, total count goes from 27 to 30.

---

## Shared Patterns

### Protocol Skip Tuple Pattern
**Source:** `quirk/cbom/builder.py` lines 389 (Pass 2) and 468 (Pass 3)
**Apply to:** `builder.py` Pass 2 skip tuple (the fix target)

The established convention is a bare `ep.protocol in (...)` tuple membership test followed
immediately by `continue`. New protocols are appended to the end of the tuple. Pass 3 at line 468
is the authoritative reference for the full set of non-TLS/non-SSH protocols that belong in the
skip list.

### Fixture Factory Pattern
**Source:** `tests/test_cbom_builder.py` lines 72–97 (`_saml_endpoint`, `_kerberos_endpoint`)
**Apply to:** `_dnssec_endpoint()` fixture

All protocol-specific endpoint factories follow the same shape: `**overrides` keyword argument,
`defaults` dict with all `CryptoEndpoint` fields set explicitly (no implicit defaults), then
`defaults.update(overrides)` followed by `return CryptoEndpoint(**defaults)`. This ensures test
isolation and makes field overrides explicit.

### Three-Test Coverage Requirement
**Source:** `tests/test_cbom_builder.py` lines 421–442 (SAML), 449–478 (KERBEROS)
**Apply to:** Any protocol added to a pass-specific skip list

Each protocol in the skip list gets exactly three tests:
1. `_algorithm_registered` — verifies Pass 1 fires correctly (algorithm component created).
2. `_no_tls_protocol` — verifies Pass 3 skip is working (no TLS protocol component).
3. `_no_certificate` — verifies Pass 2 skip is working (no certificate component).

The `_no_certificate` test must use a real algorithm name (e.g., `"ECDSAP256SHA256"`, `"RSASHA256"`)
not a synthetic value like `"NONE"` — synthetic values would pass even without the fix due to
unrelated filters.

---

## No Analog Found

None. Both files have direct structural analogs within the same files being modified.

---

## Metadata

**Analog search scope:** `quirk/cbom/builder.py`, `tests/test_cbom_builder.py`
**Files scanned:** 2
**Pattern extraction date:** 2026-04-16
