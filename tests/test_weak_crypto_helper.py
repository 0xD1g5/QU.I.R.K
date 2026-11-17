"""Tests for quirk.util.weak_crypto (Phase 73 / INTEL-02).

Covers D-02 weak-cipher token detection (incl. CBC3 per RESEARCH C-8) and
D-10 legacy-TLS-version detection. Parametrized table per CONTEXT
<test_strategy>.
"""
from __future__ import annotations

import pytest

from quirk.util.weak_crypto import is_weak_cipher, is_legacy_tls_version


@pytest.mark.parametrize(
    "cipher,expected",
    [
        # None / empty
        (None, False),
        ("", False),
        # Weak — D-02 token set
        ("DES-CBC-SHA", True),                  # DES + DES-CBC
        ("RC4-MD5", True),                      # RC4 + MD5
        ("NULL-SHA", True),                     # NULL + SHA1
        ("EXPORT40-RC2-CBC-MD5", True),         # EXPORT + MD5
        ("AECDH-NULL-SHA", True),               # NULL token
        ("DES-CBC3-SHA", True),                 # CBC3 (RESEARCH C-8) + DES
        ("IDEA-CBC-SHA", True),                 # IDEA
        ("SHA1", True),                         # SAML-flavored
        ("sha-1", True),                        # lowercase normalized to SHA-1
        ("RC4-SHA", True),                      # RC4
        ("ANON-DH-AES256-SHA", True),           # ANON literal token
        ("TLS_ECDH_anon_WITH_AES_128_CBC_SHA", True),  # uppercases to anon -> ANON
        # Strong — no weak token
        ("AES128-GCM-SHA256", False),
        ("ECDHE-RSA-AES256-GCM-SHA384", False),
        ("CHACHA20-POLY1305-SHA256", False),
        ("TLS_AES_256_GCM_SHA384", False),
    ],
)
def test_is_weak_cipher(cipher, expected):
    assert is_weak_cipher(cipher) is expected


@pytest.mark.parametrize(
    "version,expected",
    [
        (None, False),
        ("", False),
        ("TLSV1", True),
        ("TLSv1.0", True),
        ("tlsv1.1", True),
        ("SSLV3", True),
        ("TLSV1.2", False),
        ("TLSv1.3", False),
    ],
)
def test_is_legacy_tls_version(version, expected):
    assert is_legacy_tls_version(version) is expected


def test_helper_symmetry_repeated_calls():
    """is_weak_cipher is pure — repeated calls return the same value (parity prep for Task 2)."""
    for cipher in ("DES-CBC-SHA", "RC4-MD5", "AES128-GCM-SHA256", None, ""):
        assert is_weak_cipher(cipher) is is_weak_cipher(cipher)


import pytest as _pytest_236


@_pytest_236.mark.parametrize(
    "ver,supported,expected",
    [
        ("TLSv1", "TLSv1", True),
        ("TLSv1.1", "TLSv1.1,TLSv1", True),
        ("SSLv3", "SSLv3", True),
        ("SSLv2", "SSLv2", True),
        ("TLSv1.2", "TLSv1.2,TLSv1.1", False),
        ("TLSv1.3", "TLSv1.3", False),
        (None, None, False),
        ("", "", False),
        ("TLSv1", "TLSv1.2,TLSv1", False),
    ],
)
def test_is_max_legacy_tls(ver, supported, expected):
    from quirk.util.weak_crypto import is_max_legacy_tls

    assert is_max_legacy_tls(ver, supported) is expected


# Phase 238 D-17: weak certificate signature hash (exact membership).
@_pytest_236.mark.parametrize(
    "name,expected",
    [
        ("sha1", True),
        ("SHA1", True),
        (" md5 ", True),
        ("md4", True),
        ("md2", True),
        (None, False),
        ("", False),
        ("unknown", False),
        ("sha256", False),
        ("sha1WithRSAEncryption", False),
    ],
)
def test_is_weak_signature_hash(name, expected):
    from quirk.util.weak_crypto import is_weak_signature_hash

    assert is_weak_signature_hash(name) is expected


# Phase 238 D-20: one undersized-RSA predicate for both finding pipelines.
@_pytest_236.mark.parametrize(
    "alg,size,expected",
    [
        ("RSA", 1024, True),
        ("rsa-pss", 1024, True),
        ("RSA", 2047, True),
        ("RSA", 0, False),
        ("RSA", None, False),
        ("RSA", 2048, False),
        ("RSA", True, False),
        ("RSASSA-PSS", 1024, False),
        ("ECDSA", 1024, False),
        (None, 1024, False),
    ],
)
def test_is_undersized_rsa(alg, size, expected):
    from quirk.util.weak_crypto import is_undersized_rsa

    assert is_undersized_rsa(alg, size) is expected
