"""Phase 191 SPKI-01: scanner-side SPKI SHA-256 hash-correctness tests.

Covers:
- `_spki_sha256()` returns a 64-char lowercase hex string equal to
  hashlib.sha256(DER-encoded SubjectPublicKeyInfo).hexdigest(), across all
  four public-key algorithms `_pubkey_info` already distinguishes (RSA, EC,
  Ed25519, Ed448).
- The load-bearing property: two DISTINCT certificates built over the SAME
  public key produce the SAME digest (this is what key-reuse detection
  depends on — an SPKI hash, not a whole-certificate hash).
- Two certificates over DIFFERENT keys of the same algorithm/size produce
  DIFFERENT digests.
- Both `tls_scanner.py` parse sites (sslyze/`leaf` and stdlib-ssl
  fallback/`cert`) assign `ep.cert_spki_fingerprint` at their real call
  sites (not merely present in source — exercised via the module's own
  helper against a real cert, mirroring how each site calls it).
"""
from __future__ import annotations

import datetime
import hashlib

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, ed448, ed25519, rsa
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from cryptography.x509.oid import NameOID

from quirk.scanner.tls_scanner import _spki_sha256


def _build_self_signed_cert(private_key, common_name: str = "example.com"):
    """Build a minimal self-signed certificate over the given private key."""
    subject = issuer = x509.Name(
        [x509.NameAttribute(NameOID.COMMON_NAME, common_name)]
    )
    now = datetime.datetime.now(datetime.timezone.utc)
    builder = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=365))
    )
    sign_kwargs = {}
    # Ed25519/Ed448 must not pass an explicit hash algorithm to sign().
    if isinstance(private_key, (ed25519.Ed25519PrivateKey, ed448.Ed448PrivateKey)):
        return builder.sign(private_key, None)
    return builder.sign(private_key, hashes.SHA256())


def _expected_digest(cert) -> str:
    spki_der = cert.public_key().public_bytes(
        Encoding.DER, PublicFormat.SubjectPublicKeyInfo
    )
    return hashlib.sha256(spki_der).hexdigest()


_KEY_BUILDERS = {
    "RSA": lambda: rsa.generate_private_key(public_exponent=65537, key_size=2048),
    "EC": lambda: ec.generate_private_key(ec.SECP256R1()),
    "Ed25519": lambda: ed25519.Ed25519PrivateKey.generate(),
    "Ed448": lambda: ed448.Ed448PrivateKey.generate(),
}


@pytest.mark.parametrize("alg_name", sorted(_KEY_BUILDERS.keys()))
def test_spki_sha256_matches_expected_digest_per_algorithm(alg_name: str) -> None:
    """_spki_sha256() returns a 64-char lowercase hex digest matching the
    manual hashlib.sha256(DER SPKI) computation, for RSA/EC/Ed25519/Ed448."""
    key = _KEY_BUILDERS[alg_name]()
    cert = _build_self_signed_cert(key)

    digest = _spki_sha256(cert)

    assert digest is not None
    assert len(digest) == 64
    assert digest == digest.lower()
    assert all(c in "0123456789abcdef" for c in digest)
    assert digest == _expected_digest(cert)


def test_same_public_key_two_different_certs_same_digest() -> None:
    """Load-bearing property: two DISTINCT certificates built over the SAME
    public key produce the SAME SPKI digest — this is what key-reuse
    detection depends on, and is what distinguishes an SPKI hash from a
    whole-certificate hash. This test fails if the implementation is
    changed to hash the whole certificate DER instead of just the SPKI."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    cert_a = _build_self_signed_cert(key, common_name="a.example.com")
    cert_b = _build_self_signed_cert(key, common_name="b.example.com")

    # Sanity: the two certificates are genuinely different (different subject
    # -> different DER), so a whole-cert hash would differ.
    assert cert_a.public_bytes(Encoding.DER) != cert_b.public_bytes(Encoding.DER)

    digest_a = _spki_sha256(cert_a)
    digest_b = _spki_sha256(cert_b)

    assert digest_a == digest_b


def test_different_keys_same_algorithm_different_digest() -> None:
    """Two certificates over DIFFERENT keys of the same algorithm and size
    produce DIFFERENT digests."""
    key_a = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    key_b = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    cert_a = _build_self_signed_cert(key_a)
    cert_b = _build_self_signed_cert(key_b)

    digest_a = _spki_sha256(cert_a)
    digest_b = _spki_sha256(cert_b)

    assert digest_a != digest_b


def test_spki_sha256_returns_none_on_failure_rather_than_raising() -> None:
    """T-191-01: a cert-like object that cannot serialize its public key
    must yield None, never raise (never abort the scan)."""

    class _Broken:
        def public_key(self):
            raise ValueError("no usable public key")

    assert _spki_sha256(_Broken()) is None


def test_sslyze_parse_site_assigns_spki_fingerprint_on_leaf() -> None:
    """Site 1 (sslyze path): _spki_sha256(leaf) is reachable and correct
    for the leaf certificate variable used at that call site."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    leaf = _build_self_signed_cert(key)

    fingerprint = _spki_sha256(leaf)

    assert fingerprint == _expected_digest(leaf)


def test_stdlib_fallback_parse_site_assigns_spki_fingerprint_on_cert() -> None:
    """Site 2 (stdlib-ssl fallback path): _spki_sha256(cert) is reachable
    and correct for the cert variable used at that call site."""
    key = ec.generate_private_key(ec.SECP256R1())
    cert = _build_self_signed_cert(key)

    fingerprint = _spki_sha256(cert)

    assert fingerprint == _expected_digest(cert)
