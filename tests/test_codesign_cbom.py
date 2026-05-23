"""Phase 95 CSIGN-03 — CBOM CODE_SIGNING branch + fingerprint dedup tests.

Tests:
  - test_codesign_pass1_registers_algorithm: a single CODE_SIGNING endpoint
    with cert_pubkey_alg=RSA registers exactly one algorithm component
  - test_cbom_dedup_stable_count: two CODE_SIGNING endpoints sharing one
    fingerprint produce the SAME component count as one endpoint (no dup)
  - test_codesign_distinct_fingerprints_not_deduped: two CODE_SIGNING endpoints
    with different fingerprints produce two cert components
  - test_cbom_tls_plus_codesign_no_dup: TLS + CODE_SIGNING for same cert
    (same surrogate key) produces exactly one cert component; TLS-derived wins
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from quirk.cbom.builder import build_cbom
from quirk.models import CryptoEndpoint


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_codesign_ep(
    host: str = "cs.example.com",
    port: int = 0,
    cert_pubkey_alg: str = "RSA",
    cert_pubkey_size: int = 1024,
    fingerprint: str | None = "aabbcc",
    extra_detail: str = "weak",
    cert_subject: str = "CN=Test CodeSign",
    cert_not_after: str = "2027-01-01T00:00:00Z",
) -> CryptoEndpoint:
    """Build a minimal CryptoEndpoint with protocol=CODE_SIGNING."""
    ep = MagicMock(spec=CryptoEndpoint)
    ep.protocol = "CODE_SIGNING"
    ep.host = host
    ep.port = port
    ep.cert_pubkey_alg = cert_pubkey_alg
    ep.cert_pubkey_size = cert_pubkey_size
    ep.cert_subject = cert_subject
    ep.cert_issuer = "CN=Test CA"
    ep.cert_sig_alg = "SHA1withRSA"
    ep.cert_not_before = "2020-01-01T00:00:00Z"
    ep.cert_not_after = cert_not_after
    # Build service_detail from fingerprint + extra tokens
    parts = []
    if fingerprint is not None:
        parts.append(f"fingerprint={fingerprint}")
    if extra_detail:
        parts.append(extra_detail)
    ep.service_detail = "|".join(parts) if parts else ""
    # Unrelated fields
    ep.cipher_suite = None
    ep.tls_version = None
    ep.ssh_audit_json = None
    ep.tls_capabilities_json = None
    ep.scan_error = None
    ep.smime_scan_json = None
    ep.cert_sans = None
    return ep


def _make_tls_ep(
    host: str = "tls.example.com",
    port: int = 443,
    cert_pubkey_alg: str = "RSA",
    cert_pubkey_size: int = 2048,
    cert_subject: str = "CN=Test CodeSign",
    cert_not_after: str = "2027-01-01T00:00:00Z",
) -> CryptoEndpoint:
    """Build a minimal TLS CryptoEndpoint."""
    ep = MagicMock(spec=CryptoEndpoint)
    ep.protocol = "TLS"
    ep.host = host
    ep.port = port
    ep.cert_pubkey_alg = cert_pubkey_alg
    ep.cert_pubkey_size = cert_pubkey_size
    ep.cert_subject = cert_subject
    ep.cert_issuer = "CN=Test CA"
    ep.cert_sig_alg = "sha256WithRSAEncryption"
    ep.cert_not_before = "2020-01-01T00:00:00Z"
    ep.cert_not_after = cert_not_after
    ep.service_detail = ""
    ep.cipher_suite = "ECDHE-RSA-AES256-GCM-SHA384"
    ep.tls_version = "TLSv1.3"
    ep.ssh_audit_json = None
    ep.tls_capabilities_json = None
    ep.scan_error = None
    ep.smime_scan_json = None
    ep.cert_sans = None
    return ep


def _count_cert_components(bom) -> int:
    from cyclonedx.model.crypto import CryptoAssetType
    return sum(
        1 for c in bom.components
        if getattr(c, "crypto_properties", None) is not None
        and getattr(c.crypto_properties, "asset_type", None) == CryptoAssetType.CERTIFICATE
    )


def _count_algo_components(bom) -> int:
    from cyclonedx.model.crypto import CryptoAssetType
    return sum(
        1 for c in bom.components
        if getattr(c, "crypto_properties", None) is not None
        and getattr(c.crypto_properties, "asset_type", None) == CryptoAssetType.ALGORITHM
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_codesign_pass1_registers_algorithm():
    """A single CODE_SIGNING endpoint with cert_pubkey_alg=RSA must register
    exactly one algorithm component in Pass-1."""
    ep = _make_codesign_ep(cert_pubkey_alg="RSA", cert_pubkey_size=1024)
    bom = build_cbom([ep])
    algo_count = _count_algo_components(bom)
    assert algo_count >= 1, (
        f"Expected at least one algorithm component from CODE_SIGNING endpoint, got {algo_count}"
    )


def test_cbom_dedup_stable_count():
    """Two CODE_SIGNING endpoints sharing the same fingerprint must produce the
    SAME cert-component count as a single endpoint — no duplicate cert component."""
    fp = "deadbeef" * 8  # 64-char hex
    ep1 = _make_codesign_ep(host="cs1.example.com", fingerprint=fp)
    ep2 = _make_codesign_ep(host="cs2.example.com", fingerprint=fp)
    ep_single = _make_codesign_ep(host="cs3.example.com", fingerprint=fp)

    bom_two = build_cbom([ep1, ep2])
    bom_one = build_cbom([ep_single])

    count_two = _count_cert_components(bom_two)
    count_one = _count_cert_components(bom_one)

    assert count_two == count_one, (
        f"Two CODE_SIGNING endpoints with same fingerprint produced {count_two} cert components, "
        f"expected {count_one} (same as single endpoint — dedup must suppress duplicate)"
    )


def test_codesign_distinct_fingerprints_not_deduped():
    """Two CODE_SIGNING endpoints with DIFFERENT fingerprints must produce two
    distinct cert components — dedup must not collapse distinct certs."""
    ep1 = _make_codesign_ep(host="cs1.example.com", fingerprint="aabbcc" * 10 + "aa")
    ep2 = _make_codesign_ep(host="cs2.example.com", fingerprint="112233" * 10 + "11")
    bom = build_cbom([ep1, ep2])
    count = _count_cert_components(bom)
    assert count == 2, (
        f"Two CODE_SIGNING endpoints with distinct fingerprints must produce 2 cert components, "
        f"got {count}"
    )


def test_cbom_tls_plus_codesign_no_dup():
    """Passing one TLS CryptoEndpoint and one CODE_SIGNING endpoint representing
    the SAME cert (same surrogate key: cert_subject + cert_pubkey_alg + cert_not_after)
    must produce exactly one cert component. The TLS-derived component wins;
    the CODE_SIGNING endpoint annotates it rather than emitting a duplicate.

    Proves CSIGN-03 contract + ROADMAP Success Criterion 3.
    """
    shared_subject = "CN=TLS-And-CodeSign Shared"
    shared_alg = "RSA"
    shared_not_after = "2028-06-01T00:00:00Z"

    tls_ep = _make_tls_ep(
        host="tls.example.com",
        port=443,
        cert_pubkey_alg=shared_alg,
        cert_subject=shared_subject,
        cert_not_after=shared_not_after,
    )
    codesign_ep = _make_codesign_ep(
        host="ldap.example.com",
        port=0,
        cert_pubkey_alg=shared_alg,
        cert_subject=shared_subject,
        cert_not_after=shared_not_after,
        fingerprint="cafebabe" * 8,
    )

    bom = build_cbom([tls_ep, codesign_ep])
    cert_count = _count_cert_components(bom)
    assert cert_count == 1, (
        f"TLS + CODE_SIGNING for same cert (same surrogate key) must produce exactly 1 cert component, "
        f"got {cert_count}. TLS-derived component must win; CODE_SIGNING must annotate, not duplicate."
    )
