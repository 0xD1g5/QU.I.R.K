"""D-08 / WR-12: TLS 1.2 non-PFS RSA suites emit 'RSA-kex' label (Phase 73)."""
import pytest

from quirk.cbom.builder import _decompose_cipher_suite


# 8 non-PFS RSA TLS 1.2 cipher suites per CONTEXT <test_strategy>.
# Some are commonly seen with TLS_RSA_WITH_ prefix; others as bare OpenSSL aliases.
NON_PFS_RSA_TLS12_SUITES = [
    "TLS_RSA_WITH_AES_128_CBC_SHA",
    "TLS_RSA_WITH_AES_256_CBC_SHA",
    "TLS_RSA_WITH_AES_128_CBC_SHA256",
    "TLS_RSA_WITH_AES_256_CBC_SHA256",
    "TLS_RSA_WITH_AES_128_GCM_SHA256",
    "TLS_RSA_WITH_AES_256_GCM_SHA384",
    "TLS_RSA_WITH_NULL_SHA",
    "TLS_RSA_WITH_NULL_MD5",
]


@pytest.mark.parametrize("suite", NON_PFS_RSA_TLS12_SUITES)
def test_non_pfs_rsa_tls12_suite_emits_rsa_kex_label(suite):
    """Each non-PFS RSA TLS 1.2 suite decomposes with 'RSA-kex' (not bare 'RSA')."""
    parts = _decompose_cipher_suite(suite)
    assert "RSA-kex" in parts, (
        f"Suite {suite!r} parts {parts!r} missing 'RSA-kex' KEX token"
    )
    # The bare 'RSA' label must NOT appear as a KEX token. The cert-signature
    # role on these suites is also RSA but _AUTH_MAP emits 'RSA' there; the
    # current auth-loop skips the already-consumed KEX token, so on these
    # suites no bare 'RSA' should appear in parts at all.
    assert "RSA" not in parts, (
        f"Suite {suite!r} parts {parts!r} still contains bare 'RSA' token"
    )


def test_ecdhe_rsa_does_not_get_rsa_kex_label():
    """ECDHE-RSA suites must use the ECDHE KEX mapping (X25519), not RSA-kex."""
    parts = _decompose_cipher_suite("TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384")
    assert "RSA-kex" not in parts
    assert "X25519" in parts  # ECDHE → X25519 per _KEX_MAP


def test_tls13_path_unaffected():
    """TLS 1.3 suites skip _KEX_MAP entirely — no RSA / RSA-kex token in parts."""
    parts = _decompose_cipher_suite("TLS_AES_256_GCM_SHA384")
    assert "RSA" not in parts
    assert "RSA-kex" not in parts
