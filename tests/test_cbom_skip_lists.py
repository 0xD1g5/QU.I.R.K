"""CBOM-04: Pass-2 (cert) and Pass-3 (protocol) skip-list unit tests.

Drives parametrize directly off `MOTION_PLAINTEXT_PROTOCOLS` and
`DAR_SKIP_PROTOCOLS` (extracted in Plan 01 / D-10 / D-11). For each label,
constructs a synthetic CryptoEndpoint with FULL TLS+cert metadata and
asserts the resulting CBOM contains no certificate component and no TLS
protocol component for that endpoint.

This is a direct unit-level guard against silent skip-list regressions
(T-42-03): if a refactor accidentally drops a protocol from either skip
tuple in `quirk/cbom/builder.py`, this test fails loudly and names the
offending protocol.
"""
from __future__ import annotations

import pytest

from quirk.cbom.builder import (
    DAR_SKIP_PROTOCOLS,
    HARDWARE_PROTOCOLS,   # Phase 129 HWCOMPAT-05
    MOTION_PLAINTEXT_PROTOCOLS,
    build_cbom,
)
from quirk.models import CryptoEndpoint


def _full_tls_endpoint(protocol: str, host: str = "h", port: int = 1) -> CryptoEndpoint:
    """Construct an endpoint with FULL TLS+cert metadata so the skip
    cannot be attributed to missing fields."""
    return CryptoEndpoint(
        host=host, port=port, protocol=protocol,
        tls_version="TLSv1.2",
        cipher_suite="TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384",
        cert_pubkey_alg="RSA", cert_pubkey_size=2048,
        cert_sig_alg="sha256WithRSAEncryption",
        cert_subject="CN=example.com", cert_issuer="CN=Example CA",
        cert_not_before=None, cert_not_after=None,
        tls_capabilities_json=None, ssh_audit_json=None,
    )


def _bom_refs(bom) -> set[str]:
    return {str(c.bom_ref.value) for c in bom.components}


def test_skip_list_constants_are_nonempty():
    """Sanity guard: an empty skip-list constant would silently shrink
    the parametrize set to zero cases and degrade this gate to a no-op."""
    assert len(MOTION_PLAINTEXT_PROTOCOLS) > 0, (
        "MOTION_PLAINTEXT_PROTOCOLS is empty — Pass 2/3 skip coverage is now zero."
    )
    assert len(DAR_SKIP_PROTOCOLS) > 0, (
        "DAR_SKIP_PROTOCOLS is empty — Pass 2/3 skip coverage is now zero."
    )
    assert len(HARDWARE_PROTOCOLS) > 0, (
        "HARDWARE_PROTOCOLS is empty — HWCOMPAT-05 Pass 2/3 hardware skip coverage is zero."
    )


@pytest.mark.parametrize(
    "protocol",
    sorted(MOTION_PLAINTEXT_PROTOCOLS | DAR_SKIP_PROTOCOLS | HARDWARE_PROTOCOLS),
)
def test_skip_protocol_emits_no_cert_or_proto_component(protocol):
    """Pass 2 (cert) AND Pass 3 (protocol) must both skip the listed
    protocols even when the endpoint has full TLS+cert metadata.
    Pass 1 algorithm components MAY appear — only certs and TLS
    protocol entries are forbidden."""
    ep = _full_tls_endpoint(protocol)
    bom = build_cbom([ep])
    refs = _bom_refs(bom)

    cert_prefix = f"crypto/certificate/{ep.host}:{ep.port}"
    proto_prefix = f"crypto/protocol/tls/{ep.host}:{ep.port}"

    cert_leaked = sorted(r for r in refs if r.startswith(cert_prefix))
    proto_leaked = sorted(r for r in refs if r.startswith(proto_prefix))

    assert cert_leaked == [], (
        f"Skip-list protocol {protocol!r} leaked into Pass 2 (cert) — "
        f"got cert refs {cert_leaked}. Check the Pass 2 skip tuple in "
        f"quirk/cbom/builder.py around line 436."
    )
    assert proto_leaked == [], (
        f"Skip-list protocol {protocol!r} leaked into Pass 3 (protocol) — "
        f"got protocol refs {proto_leaked}. Check the Pass 3 skip tuple in "
        f"quirk/cbom/builder.py around line 519."
    )
