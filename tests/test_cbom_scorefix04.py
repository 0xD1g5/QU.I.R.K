"""Phase 124 — SCOREFIX-04 RED scaffold.

Pins the post-fix behavior for cbom/builder.py::_decompose_cipher_suite:
  - TLS_AES_128_CCM_8_SHA256 → must contain "AES-128-CCM-8", NOT bare "AES-128-CCM".
  - TLS_AES_256_CCM_8_SHA256 → must contain "AES-256-CCM-8", NOT bare "AES-256-CCM".
  - Regression guard: bare-CCM suites still decompose as "AES-128-CCM" / "AES-256-CCM".

Current _ENC_MAP has "AES_128_CCM" → "AES-128-CCM" before any CCM_8 entry.
Because the loop matches via substring (`if key in remaining`), "AES_128_CCM" matches
inside "AES_128_CCM_8" BEFORE any CCM_8 entry → wrong canonical name "AES-128-CCM".
Wave 1 inserts CCM_8 entries before the bare CCM entries (D-05).
"""
from __future__ import annotations

from quirk.cbom.builder import _decompose_cipher_suite


# SF04a — TLS 1.3 CCM_8 suite decomposes to truncated-tag variant name.
def test_tls13_aes_128_ccm_8_decomposes_correctly():
    """TLS_AES_128_CCM_8_SHA256 must decompose to 'AES-128-CCM-8', not 'AES-128-CCM'.

    RED: current _ENC_MAP has AES_128_CCM before AES_128_CCM_8 (which doesn't exist).
    Substring match fires on AES_128_CCM → wrong canonical name returned.
    """
    result = _decompose_cipher_suite("TLS_AES_128_CCM_8_SHA256")

    assert "AES-128-CCM-8" in result, (
        f"Expected 'AES-128-CCM-8' in decomposition of TLS_AES_128_CCM_8_SHA256, "
        f"got: {result}"
    )
    assert "AES-128-CCM" not in result or all(
        s != "AES-128-CCM" for s in result
    ), (
        f"Bare 'AES-128-CCM' must not appear when the suite has CCM_8 suffix, "
        f"got: {result}"
    )


# SF04b — AES-256-CCM-8 variant also decomposes correctly.
def test_tls13_aes_256_ccm_8_decomposes_correctly():
    """TLS_AES_256_CCM_8_SHA256 must decompose to 'AES-256-CCM-8', not 'AES-256-CCM'.

    RED: same ordering bug — AES_256_CCM substring matches before CCM_8 entry.
    """
    result = _decompose_cipher_suite("TLS_AES_256_CCM_8_SHA256")

    assert "AES-256-CCM-8" in result, (
        f"Expected 'AES-256-CCM-8' in decomposition of TLS_AES_256_CCM_8_SHA256, "
        f"got: {result}"
    )
    assert "AES-256-CCM" not in result or all(
        s != "AES-256-CCM" for s in result
    ), (
        f"Bare 'AES-256-CCM' must not appear when the suite has CCM_8 suffix, "
        f"got: {result}"
    )


# SF04b regression guard — bare CCM suites still decompose to bare CCM names.
def test_bare_ccm_suite_regression_guard():
    """Existing bare-CCM suites must continue to decompose as 'AES-128-CCM'/'AES-256-CCM'.

    This regression guard verifies the CCM_8 fix does not accidentally break
    plain CCM decomposition. Must PASS before AND after the fix.
    """
    # Legacy TLS 1.2 bare CCM suite (no _8 suffix)
    result_128 = _decompose_cipher_suite("TLS_RSA_WITH_AES_128_CCM")
    assert "AES-128-CCM" in result_128, (
        f"Bare AES_128_CCM suite should still decompose to 'AES-128-CCM', got: {result_128}"
    )
    # Ensure CCM-8 does NOT appear for a bare-CCM suite
    assert "AES-128-CCM-8" not in result_128, (
        f"Bare CCM suite must not produce CCM-8 canonical name, got: {result_128}"
    )

    result_256 = _decompose_cipher_suite("TLS_RSA_WITH_AES_256_CCM")
    assert "AES-256-CCM" in result_256, (
        f"Bare AES_256_CCM suite should still decompose to 'AES-256-CCM', got: {result_256}"
    )
    assert "AES-256-CCM-8" not in result_256, (
        f"Bare CCM suite must not produce CCM-8 canonical name, got: {result_256}"
    )
