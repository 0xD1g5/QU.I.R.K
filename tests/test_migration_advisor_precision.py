"""Phase 74-03 (D-08, D-09, WR-09, WR-10): migration advisor precision tests.

Word-boundary regex + CANONICAL_ALG_SYNONYMS map eliminate substring false
positives like `'DES' in 'DESede'` and `'DES' in 'libdes3.so'`.

D-09 integration: `_walk_json_for_alg_strings` extends to scan non-`_ALG_KEYS`
string values via the same `_matches` helper.
"""
from __future__ import annotations

import pytest

from quirk.assessment.migration_advisor import (
    CANONICAL_ALG_SYNONYMS,
    _matches,
)
from quirk.qramm.evidence_bridge import _walk_json_for_alg_strings


# D-08: word-boundary matching cases
@pytest.mark.parametrize(
    "canonical,text,expected",
    [
        # Canonical false-positive guards
        ("DES", "DESede", False),
        ("DES", "libdes3.so", False),
        ("DES", "AES-128", False),
        # Variant matches
        ("DES", "DES-CBC", True),
        ("DES", "DES-EDE", True),
        ("3DES", "TripleDES_v2", True),  # `_` is word-char; "TripleDES" lies behind `_v2` boundary IS NOT — see note
        ("SHA1", "SHA-1", True),
        ("SHA1", "SHA1", True),
        ("MD5", "MD5withRSA", False),  # not word-boundary isolated from `withRSA`
        ("RC4", "ARCFOUR", True),
        ("RC4", "RC4-MD5", True),
    ],
)
def test_matches_word_boundary(canonical: str, text: str, expected: bool) -> None:
    """Word-boundary regex correctly classifies canonical-vs-text pairs."""
    # NOTE on `TripleDES_v2`: Python regex `\b` treats `_` as a word character,
    # so `\bTripleDES\b` does NOT match `TripleDES_v2`. However the
    # `\b3DES\b` alternative will not match either (3DES is not present).
    # Adjust expectation if researcher confirms `_` does not act as a boundary.
    # Per plan: `True if \b accepts the _v2 boundary, False if not`.
    # Python: `_` is word char → boundary NOT created → expected False.
    # But the test parametrize uses True per plan's "Default expectation".
    # We document chosen expectation by trusting Python regex semantics: \b
    # between `S` and `_` is NOT a boundary. So overriding to False here:
    if canonical == "3DES" and text == "TripleDES_v2":
        expected = False
    assert _matches(canonical, text) is expected


def test_canonical_alg_synonyms_has_baseline() -> None:
    """The synonym map contains DES, 3DES, RC4, MD5, SHA1 minimum."""
    required = {"DES", "3DES", "RC4", "MD5", "SHA1"}
    assert required.issubset(CANONICAL_ALG_SYNONYMS.keys())


def test_canonical_alg_synonyms_des_variants() -> None:
    """DES synonyms include DES-EDE and DES-CBC."""
    assert "DES-EDE" in CANONICAL_ALG_SYNONYMS["DES"]
    assert "DES-CBC" in CANONICAL_ALG_SYNONYMS["DES"]


# D-09: _walk_json_for_alg_strings integration
def test_walk_json_extracts_non_keyed_alg_string() -> None:
    """Non-`_ALG_KEYS` keys whose string values contain canonical algorithm
    tokens are scanned via `_matches` and yielded."""
    result = _walk_json_for_alg_strings({
        "foo": "RC4-MD5",
        "cipher_list": ["AES-128-GCM", "RC4"],
    })
    # `foo` is not in _ALG_KEYS but the value matches RC4/MD5 — D-09 scan
    assert "RC4-MD5" in result
    # cipher_list bare strings — existing list-arm behavior preserved
    assert "RC4" in result


def test_walk_json_skips_non_matching_non_keyed_string() -> None:
    """Non-keyed strings with no canonical algorithm tokens are skipped."""
    result = _walk_json_for_alg_strings({"foo": "hello world"})
    assert result == []
