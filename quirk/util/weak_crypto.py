"""Centralized weak-crypto predicates — Phase 73 / INTEL-02.

Decision enforcement:
  - D-02: Single source of truth for weak-cipher token detection across the
    intelligence/evidence subsystem (email/broker/SAML predicates route here).
  - D-02a: Token set is module-private (_WEAK_CIPHER_TOKENS); helpers are
    public — discourages bypass.
  - D-10: Legacy-TLS-version detection (is_legacy_tls_version) co-locates
    here; deferred standalone tls_versions.py module per CONTEXT Deferred
    Ideas.
  - RESEARCH C-8: _WEAK_CIPHER_TOKENS includes "CBC3" for parity with
    quirk/scanner/tls_capabilities.py:103 weak_markers tuple.

Public surface:
  is_weak_cipher(cipher_or_label: str | None) -> bool
  is_legacy_tls_version(tls_version: str | None) -> bool
"""
from __future__ import annotations

from typing import Final

# D-02 base token set + CBC3 (RESEARCH C-8 parity with tls_capabilities.py:103).
_WEAK_CIPHER_TOKENS: Final[frozenset[str]] = frozenset({
    "DES", "3DES", "CBC3", "RC4", "MD5", "NULL", "EXPORT", "ANON",
    "DES-CBC", "IDEA",
    # SAML SHA-1 family (D-02)
    "SHA1", "SHA-1",
})

# D-10 legacy TLS versions (sourced from evidence.py motion_broker inline set).
_LEGACY_TLS_VERSIONS: Final[frozenset[str]] = frozenset({
    "TLSV1", "TLSV1.0", "TLSV1.1", "SSLV3",
})


def is_weak_cipher(cipher_or_label: str | None) -> bool:
    """Return True if any weak-crypto token is present (D-02).

    Uppercases the input once, then checks substring membership of every
    token in _WEAK_CIPHER_TOKENS. Returns False on None/empty.
    """
    if not cipher_or_label:
        return False
    upper = cipher_or_label.upper()
    return any(token in upper for token in _WEAK_CIPHER_TOKENS)


def is_legacy_tls_version(tls_version: str | None) -> bool:
    """Return True if *tls_version* names a legacy TLS/SSL version (D-10).

    Uppercases the input once, then checks exact membership against
    _LEGACY_TLS_VERSIONS. Returns False on None/empty.
    """
    if not tls_version:
        return False
    return tls_version.upper() in _LEGACY_TLS_VERSIONS
