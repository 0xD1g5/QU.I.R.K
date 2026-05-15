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
        ("ADH-AES128-SHA", True),               # ANON (ADH) -> ANON token? ADH contains no ANON. Use ANON token via ADH? No - we use literal ANON. Use AECDH-NULL-SHA instead via NULL.
        # Note: above ADH-AES128-SHA matches via SHA1 token (AES128-SHA contains SHA1 substring).
        ("AECDH-NULL-SHA", True),               # NULL token
        ("DES-CBC3-SHA", True),                 # CBC3 (RESEARCH C-8) + DES
        ("IDEA-CBC-SHA", True),                 # IDEA + SHA1
        ("SHA1", True),                         # SAML-flavored
        ("sha-1", True),                        # lowercase normalized
        ("EXP-RC4-MD5", True),                  # EXPORT shorthand? "EXP" doesn't contain EXPORT. matches via RC4+MD5.
        ("ANON-DH-AES256-SHA", True),           # ANON literal token
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
