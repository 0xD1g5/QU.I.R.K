"""Phase 96 FUZZ-01: Assert REST_FUZZ endpoints produce zero crypto/protocol/tls/* CBOM components.

REST_FUZZ findings carry no TLS metadata (they are active crypto-posture probe
results, not passive TLS handshake observations). Adding "REST_FUZZ" to both
the Pass-2 and Pass-3 skip tuples in quirk/cbom/builder.py prevents them from
falling through to the TLS else-clause and emitting phantom
`crypto/protocol/tls/{host}:{port}` components.

This test verifies the skip is in place for CRITICAL, HIGH, and INFO severity
REST_FUZZ findings — none should produce a TLS protocol CBOM component.
"""
from __future__ import annotations

import pytest

from quirk.cbom.builder import build_cbom
from quirk.models import CryptoEndpoint


def _rest_fuzz_endpoint(severity: str, service_detail: str = "") -> CryptoEndpoint:
    """Return a minimal REST_FUZZ CryptoEndpoint with the given severity."""
    return CryptoEndpoint(
        host="api.x",
        port=443,
        protocol="REST_FUZZ",
        severity=severity,
        service_detail=service_detail,
    )


def _tls_bom_refs(bom) -> list[str]:
    """Collect bom_ref values for all crypto/protocol/tls/* components."""
    refs = []
    for component in bom.components:
        ref = getattr(getattr(component, "bom_ref", None), "value", None) or ""
        if ref.startswith("crypto/protocol/tls/"):
            refs.append(ref)
    return refs


def test_rest_fuzz_critical_no_tls_component():
    """A REST_FUZZ CRITICAL endpoint must not produce any crypto/protocol/tls/* component."""
    ep = _rest_fuzz_endpoint("CRITICAL", "alg_confusion")
    bom = build_cbom([ep])
    tls_refs = _tls_bom_refs(bom)
    assert tls_refs == [], (
        f"REST_FUZZ CRITICAL endpoint produced unexpected TLS component(s): {tls_refs}"
    )


def test_rest_fuzz_high_no_tls_component():
    """A REST_FUZZ HIGH endpoint must not produce any crypto/protocol/tls/* component."""
    ep = _rest_fuzz_endpoint("HIGH")
    bom = build_cbom([ep])
    tls_refs = _tls_bom_refs(bom)
    assert tls_refs == [], (
        f"REST_FUZZ HIGH endpoint produced unexpected TLS component(s): {tls_refs}"
    )


def test_rest_fuzz_info_no_tls_component():
    """A REST_FUZZ INFO endpoint (probe_skipped) must not produce any crypto/protocol/tls/* component."""
    ep = _rest_fuzz_endpoint("INFO", "probe_skipped")
    bom = build_cbom([ep])
    tls_refs = _tls_bom_refs(bom)
    assert tls_refs == [], (
        f"REST_FUZZ INFO endpoint produced unexpected TLS component(s): {tls_refs}"
    )


def test_rest_fuzz_mixed_with_tls_no_phantom_components():
    """A REST_FUZZ endpoint alongside a TLS endpoint must not produce extra TLS components.

    The real TLS endpoint (api.real:443) produces exactly one crypto/protocol/tls component.
    The REST_FUZZ endpoint (api.x:443) must not add a second one.
    """
    tls_ep = CryptoEndpoint(
        host="api.real",
        port=443,
        protocol="TLS",
        tls_version="TLSv1.3",
        cipher_suite="TLS_AES_256_GCM_SHA384",
        cert_pubkey_alg="RSA",
        cert_pubkey_size=2048,
        cert_sig_alg="SHA256withRSA",
        cert_subject="CN=api.real",
        cert_issuer="CN=Test CA",
    )
    fuzz_ep = _rest_fuzz_endpoint("HIGH")
    bom = build_cbom([tls_ep, fuzz_ep])
    tls_refs = _tls_bom_refs(bom)
    # Only the real TLS endpoint should produce a TLS protocol component
    assert "crypto/protocol/tls/api.real:443" in tls_refs, (
        "Expected TLS component for api.real:443 to be present"
    )
    assert "crypto/protocol/tls/api.x:443" not in tls_refs, (
        "REST_FUZZ endpoint api.x:443 must not produce a phantom TLS component"
    )
