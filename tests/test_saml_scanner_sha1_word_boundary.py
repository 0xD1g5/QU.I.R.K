"""Phase 77 D-03 / scanners-protocol/IN-03: SHA1 detection is word-boundary.

The previous substring scan matched ``SHA1024`` as a positive hit. The fix
delegates to the Phase 74 ``quirk/assessment/migration_advisor.py::_matches``
word-boundary helper (Researcher Discretion D-03).
"""
from __future__ import annotations

from quirk.scanner.saml_scanner import _is_sha1_uri


def test_bare_sha1_token_is_detected() -> None:
    assert _is_sha1_uri("http://www.w3.org/2000/09/xmldsig#sha1") is True


def test_dashed_sha_1_token_is_detected() -> None:
    assert _is_sha1_uri("urn:example:alg/SHA-1") is True


def test_sha1024_is_not_a_false_positive() -> None:
    """The crux of D-03: SHA1024 must NOT match the SHA1 indicator."""
    assert _is_sha1_uri("urn:example:alg/sha1024") is False


def test_sha256_is_not_detected() -> None:
    assert _is_sha1_uri("http://www.w3.org/2001/04/xmlenc#sha256") is False
