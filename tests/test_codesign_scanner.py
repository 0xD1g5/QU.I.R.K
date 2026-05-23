"""Phase 95 Plan 01 — Unit tests for quirk/scanner/codesign_scanner.py.

Mocks the LDAP bind+paged-search layer by patching
``quirk.scanner.codesign_scanner._bind_and_search_codesign`` to return a
synthetic iterable of searchResEntry dicts carrying pre-built DER fixtures.

Also covers the TLS-EKU in-process path via
``scan_codesign_from_tls_endpoints``.

For the TLS-EKU check, the implementation reads EKU OIDs from
``tls_capabilities_json["eku_oids"]`` (the existing TLS capabilities field).
This avoids needing a new model field while allowing run_scan.py (Plan 95-03)
to populate the EKU OID list when it captures TLS cert data.

Asserts the contract from Phase 95 Plan 95-01:

  - codesign_rsa1024_sha1.der  (RSA-1024 SHA-1 + CodeSigning EKU)
      → HIGH, reasons include "weak-signing-alg" AND "weak-rsa-key"
  - codesign_ec192.der         (EC-192 + CodeSigning EKU)
      → HIGH, reasons include "weak-ec-key"
  - codesign_rsa2048_sha256.der (RSA-2048 SHA-256 + CodeSigning EKU)
      → SAFE, zero endpoints emitted
  - codesign_rsa2048_sha256_noncoding.der (RSA-2048 SHA-256, NO EKU)
      → filtered out, zero endpoints

Every emitted CryptoEndpoint must carry ``protocol="CODE_SIGNING"`` and a
populated ``smime_scan_json`` (reuses the existing column per 95-01 plan).
"""
from __future__ import annotations

import json
import pathlib
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from quirk.scanner import codesign_scanner
from quirk.scanner.codesign_scanner import (
    scan_codesign_from_ldap,
    scan_codesign_from_tls_endpoints,
    CODE_SIGNING,
)
from quirk.models import CryptoEndpoint


FIXTURE_DIR = pathlib.Path(__file__).parent / "fixtures" / "codesign"


def _load(name: str) -> bytes:
    return (FIXTURE_DIR / name).read_bytes()


def _entry(uid: str, der: bytes, attr: str = "userCertificate") -> dict:
    """Build a fake ldap3 searchResEntry dict matching what
    ``paged_search(... generator=True)`` yields."""
    return {
        "type": "searchResEntry",
        "dn": f"uid={uid},ou=people,dc=quirk,dc=lab",
        "raw_attributes": {
            attr: [der],
            "cn": [uid.encode()],
            "uid": [uid.encode()],
        },
    }


def _target() -> SimpleNamespace:
    return SimpleNamespace(host="codesign-openldap", port=636, realm="QUIRK.LAB")


def _run_with_entries(entries: list[dict]) -> list:
    """Call scan_codesign_from_ldap with _bind_and_search_codesign patched to
    yield the supplied entries. Also forces LDAP3_AVAILABLE=True so the test
    suite runs in environments where the optional ``ldap3`` dep isn't installed.
    """
    with patch.object(codesign_scanner, "LDAP3_AVAILABLE", True), \
         patch.object(codesign_scanner, "_bind_and_search_codesign",
                      return_value=iter(entries)):
        return scan_codesign_from_ldap([_target()], timeout=5)


# ---------------------------------------------------------------------------
# Per-fixture contract assertions
# ---------------------------------------------------------------------------

def test_rsa1024_sha1_emits_high():
    """RSA-1024 SHA-1 + CodeSigning EKU → 1 endpoint, protocol == "CODE_SIGNING",
    severity == "HIGH", reasons include "weak-signing-alg" and "weak-rsa-key".
    """
    eps = _run_with_entries([_entry("signer1", _load("codesign_rsa1024_sha1.der"))])
    assert len(eps) == 1, f"expected 1 endpoint, got {len(eps)}"
    ep = eps[0]
    assert ep.protocol == "CODE_SIGNING"
    assert ep.severity == "HIGH"
    assert ep.cert_pubkey_alg == "RSA"
    assert ep.cert_pubkey_size == 1024
    assert ep.smime_scan_json, "smime_scan_json must be populated"
    blob = json.loads(ep.smime_scan_json)
    assert "weak-signing-alg" in blob["reasons"]
    assert "weak-rsa-key" in blob["reasons"]


def test_ec192_emits_high():
    """EC-192 + CodeSigning EKU → HIGH, reasons include "weak-ec-key"."""
    eps = _run_with_entries([_entry("signer2", _load("codesign_ec192.der"))])
    assert len(eps) == 1, f"expected 1 endpoint, got {len(eps)}"
    ep = eps[0]
    assert ep.protocol == "CODE_SIGNING"
    assert ep.severity == "HIGH"
    assert ep.cert_pubkey_alg == "ECDSA"
    assert ep.smime_scan_json, "smime_scan_json must be populated"
    blob = json.loads(ep.smime_scan_json)
    assert "weak-ec-key" in blob["reasons"]


def test_strong_rsa2048_sha256_safe():
    """RSA-2048/SHA-256 + CodeSigning EKU → SAFE, zero endpoints emitted."""
    eps = _run_with_entries([_entry("signer3", _load("codesign_rsa2048_sha256.der"))])
    assert eps == [], f"expected zero endpoints for SAFE cert, got {len(eps)}"


def test_non_codesign_eku_filtered():
    """RSA-2048/SHA-256 WITHOUT CodeSigning EKU → zero endpoints (filtered)."""
    eps = _run_with_entries(
        [_entry("signer4", _load("codesign_rsa2048_sha256_noncoding.der"))]
    )
    assert eps == [], f"expected zero endpoints for non-CodeSigning cert, got {len(eps)}"


def test_fingerprint_in_service_detail():
    """A weak endpoint's service_detail contains "fingerprint=" with a
    64-char hex SHA-256 string."""
    eps = _run_with_entries([_entry("signer1", _load("codesign_rsa1024_sha1.der"))])
    assert len(eps) == 1
    ep = eps[0]
    assert ep.service_detail, "service_detail must be populated"
    # Extract fingerprint= token
    fp_token = None
    for part in ep.service_detail.split("|"):
        if part.startswith("fingerprint="):
            fp_token = part[len("fingerprint="):]
            break
    assert fp_token is not None, "service_detail must contain fingerprint= token"
    assert len(fp_token) == 64, f"SHA-256 hex must be 64 chars, got {len(fp_token)}"
    assert all(c in "0123456789abcdef" for c in fp_token), \
        "fingerprint must be lowercase hex"


def test_protocol_constant_uppercase():
    """codesign_scanner.CODE_SIGNING == 'CODE_SIGNING' (exact uppercase)."""
    assert CODE_SIGNING == "CODE_SIGNING"
    assert codesign_scanner.CODE_SIGNING == "CODE_SIGNING"


def test_tls_eku_check():
    """scan_codesign_from_tls_endpoints: a TLS CryptoEndpoint whose
    tls_capabilities_json includes the CodeSigning EKU OID (1.3.6.1.5.5.7.3.3)
    emits exactly one CODE_SIGNING endpoint; a TLS endpoint without that OID
    yields zero. Proves in-process TLS-EKU source of CSIGN-01 (no network I/O).
    """
    # Build a CryptoEndpoint that simulates a TLS scan which captured a cert
    # with CodeSigning EKU (1.3.6.1.5.5.7.3.3) stored in tls_capabilities_json.
    tls_ep_with_codesign = CryptoEndpoint(
        host="tls-server.example.com",
        port=443,
        protocol="TLS",
        cert_pubkey_alg="RSA",
        cert_pubkey_size=2048,
        cert_sig_alg="sha256",
        cert_subject="CN=tls-server.example.com",
        cert_not_after=None,
        tls_capabilities_json=json.dumps({
            "eku_oids": ["1.3.6.1.5.5.7.3.1", "1.3.6.1.5.5.7.3.3"],  # ServerAuth + CodeSigning
        }),
    )
    tls_ep_without_codesign = CryptoEndpoint(
        host="web-server.example.com",
        port=443,
        protocol="TLS",
        cert_pubkey_alg="RSA",
        cert_pubkey_size=2048,
        cert_sig_alg="sha256",
        cert_subject="CN=web-server.example.com",
        cert_not_after=None,
        tls_capabilities_json=json.dumps({
            "eku_oids": ["1.3.6.1.5.5.7.3.1"],  # ServerAuth only
        }),
    )

    # Only the server-auth-only endpoint
    eps = scan_codesign_from_tls_endpoints([tls_ep_without_codesign])
    assert eps == [], f"expected 0 endpoints for TLS cert without CodeSigning EKU, got {len(eps)}"

    # Only the codesigning endpoint
    eps = scan_codesign_from_tls_endpoints([tls_ep_with_codesign])
    assert len(eps) == 1, f"expected 1 endpoint for TLS cert with CodeSigning EKU, got {len(eps)}"
    assert eps[0].protocol == "CODE_SIGNING"

    # Both together: only one CODE_SIGNING endpoint
    eps = scan_codesign_from_tls_endpoints(
        [tls_ep_with_codesign, tls_ep_without_codesign]
    )
    assert len(eps) == 1
    assert eps[0].protocol == "CODE_SIGNING"
    assert eps[0].host == "tls-server.example.com"
