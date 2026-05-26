"""Tests for quirk.cbom.builder — CBOM builder converting CryptoEndpoint scan
results into a CycloneDX Bom object.

RED phase: all tests import from quirk.cbom.builder which does not exist yet.
"""
from __future__ import annotations

import json
import pytest

from quirk.models import CryptoEndpoint

# This import will fail until builder.py is created (RED phase)
from quirk.cbom.builder import build_cbom

from cyclonedx.model.bom import Bom
from cyclonedx.model.component import Component, ComponentType
from cyclonedx.model.crypto import CryptoAssetType, ProtocolPropertiesType


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _tls_endpoint(**overrides):
    """Create a TLS CryptoEndpoint with sensible defaults."""
    defaults = dict(
        host="example.com", port=443, protocol=None,
        tls_version="TLSv1.2",
        cipher_suite="TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384",
        cert_pubkey_alg="RSA", cert_pubkey_size=2048,
        cert_sig_alg="sha256WithRSAEncryption",
        cert_subject="CN=example.com", cert_issuer="CN=Example CA",
        cert_not_before=None, cert_not_after=None,
        tls_capabilities_json=None, ssh_audit_json=None,
    )
    defaults.update(overrides)
    return CryptoEndpoint(**defaults)


def _ssh_endpoint(**overrides):
    """Create an SSH CryptoEndpoint with ssh_audit_json."""
    ssh_json = {
        "target": "10.0.0.1:22",
        "banner": {"raw": "SSH-2.0-OpenSSH_8.9p1", "protocol": "2.0"},
        "kex": [
            {"algorithm": "curve25519-sha256", "keysize": None},
            {"algorithm": "diffie-hellman-group14-sha256", "keysize": 2048},
        ],
        "key": [
            {"algorithm": "ssh-rsa", "keysize": 3072},
            {"algorithm": "ecdsa-sha2-nistp256", "keysize": 256},
        ],
        "enc": [
            {"algorithm": "aes128-ctr"},
            {"algorithm": "chacha20-poly1305@openssh.com"},
        ],
        "mac": [{"algorithm": "hmac-sha2-256"}],
    }
    defaults = dict(
        host="10.0.0.1", port=22, protocol="SSH",
        cipher_suite="SSH", tls_version=None,
        cert_pubkey_alg=None, cert_pubkey_size=None,
        cert_sig_alg=None, cert_subject=None, cert_issuer=None,
        ssh_audit_json=json.dumps(ssh_json),
        tls_capabilities_json=None,
    )
    defaults.update(overrides)
    return CryptoEndpoint(**defaults)


def _saml_endpoint(**overrides):
    """Create a SAML CryptoEndpoint with sensible defaults."""
    defaults = dict(
        host="idp.example.com", port=443, protocol="SAML",
        tls_version=None, cipher_suite=None,
        cert_pubkey_alg="RSA", cert_pubkey_size=2048,
        cert_sig_alg=None, cert_subject=None, cert_issuer=None,
        cert_not_before=None, cert_not_after=None,
        tls_capabilities_json=None, ssh_audit_json=None,
    )
    defaults.update(overrides)
    return CryptoEndpoint(**defaults)


def _kerberos_endpoint(**overrides):
    """Create a Kerberos CryptoEndpoint with sensible defaults."""
    defaults = dict(
        host="dc.example.com", port=88, protocol="KERBEROS",
        tls_version=None, cipher_suite=None,
        cert_pubkey_alg="rc4-hmac", cert_pubkey_size=None,
        cert_sig_alg=None, cert_subject=None, cert_issuer=None,
        cert_not_before=None, cert_not_after=None,
        tls_capabilities_json=None, ssh_audit_json=None,
    )
    defaults.update(overrides)
    return CryptoEndpoint(**defaults)


def _component_names(bom: Bom) -> list[str]:
    """Return sorted list of component names from a Bom."""
    return sorted(c.name for c in bom.components)


def _algorithm_components(bom: Bom) -> list[Component]:
    """Return components that are CRYPTOGRAPHIC_ASSET with ALGORITHM asset type."""
    result = []
    for c in bom.components:
        if (
            c.type == ComponentType.CRYPTOGRAPHIC_ASSET
            and c.crypto_properties is not None
            and c.crypto_properties.asset_type == CryptoAssetType.ALGORITHM
        ):
            result.append(c)
    return result


def _protocol_components(bom: Bom) -> list[Component]:
    """Return PROTOCOL asset components from a Bom."""
    result = []
    for c in bom.components:
        if (
            c.type == ComponentType.CRYPTOGRAPHIC_ASSET
            and c.crypto_properties is not None
            and c.crypto_properties.asset_type == CryptoAssetType.PROTOCOL
        ):
            result.append(c)
    return result


def _certificate_components(bom: Bom) -> list[Component]:
    """Return CERTIFICATE asset components from a Bom."""
    result = []
    for c in bom.components:
        if (
            c.type == ComponentType.CRYPTOGRAPHIC_ASSET
            and c.crypto_properties is not None
            and c.crypto_properties.asset_type == CryptoAssetType.CERTIFICATE
        ):
            result.append(c)
    return result


# ---------------------------------------------------------------------------
# CBOM-01 — Basic BOM construction
# ---------------------------------------------------------------------------

def test_build_cbom_returns_bom():
    """build_cbom returns a Bom instance."""
    bom = build_cbom([_tls_endpoint()])
    assert isinstance(bom, Bom)


def test_bom_has_metadata():
    """Returned Bom has metadata with timestamp and a tool component."""
    bom = build_cbom([_tls_endpoint()])
    assert bom.metadata is not None
    assert bom.metadata.timestamp is not None
    assert bom.metadata.component is not None
    assert bom.metadata.component.name == "QU.I.R.K."


def test_components_are_crypto_assets():
    """All components in the Bom are CRYPTOGRAPHIC_ASSET type."""
    bom = build_cbom([_tls_endpoint()])
    assert len(bom.components) > 0
    for c in bom.components:
        assert c.type == ComponentType.CRYPTOGRAPHIC_ASSET, (
            f"Component '{c.name}' has type {c.type!r}, expected CRYPTOGRAPHIC_ASSET"
        )


def test_empty_endpoints_returns_empty_bom():
    """build_cbom([]) returns a Bom with 0 components."""
    bom = build_cbom([])
    assert isinstance(bom, Bom)
    assert len(list(bom.components)) == 0


# ---------------------------------------------------------------------------
# CBOM-02 — TLS cipher suite decomposition
# ---------------------------------------------------------------------------

def test_cipher_suite_decomposed():
    """TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384 decomposes into at least 4 algorithm components."""
    bom = build_cbom([_tls_endpoint(
        cipher_suite="TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384",
    )])
    algo_comps = _algorithm_components(bom)
    assert len(algo_comps) >= 4, (
        f"Expected at least 4 algorithm components, got {len(algo_comps)}: "
        f"{[c.name for c in algo_comps]}"
    )
    names = [c.name for c in algo_comps]
    # Should find names related to key exchange, auth, encryption, MAC
    name_str = " ".join(names).upper()
    # At least one should relate to key exchange (X25519 / ECDHE)
    has_kex = any("X25519" in n.upper() or "ECDHE" in n.upper() or "ECDH" in n.upper() for n in names)
    # At least one should relate to RSA
    has_rsa = any("RSA" in n.upper() for n in names)
    # At least one should relate to AES-256-GCM
    has_aes = any("AES" in n.upper() and "256" in n for n in names)
    # At least one should relate to SHA-384
    has_sha = any("SHA" in n.upper() and "384" in n for n in names)
    assert has_kex, f"No key-exchange component in: {names}"
    assert has_rsa, f"No RSA component in: {names}"
    assert has_aes, f"No AES-256 component in: {names}"
    assert has_sha, f"No SHA-384 component in: {names}"


def test_cert_pubkey_becomes_component():
    """cert_pubkey_alg=RSA, cert_pubkey_size=2048 creates RSA-2048 component."""
    bom = build_cbom([_tls_endpoint(cert_pubkey_alg="RSA", cert_pubkey_size=2048)])
    algo_comps = _algorithm_components(bom)
    names = [c.name for c in algo_comps]
    assert any("RSA-2048" in n or ("RSA" in n and "2048" in n) for n in names), (
        f"Expected RSA-2048 component in: {names}"
    )


# ---------------------------------------------------------------------------
# CBOM-02 — SSH algorithm mapping
# ---------------------------------------------------------------------------

def test_ssh_kex_algorithms_become_components():
    """SSH kex algorithms become ALGORITHM components."""
    bom = build_cbom([_ssh_endpoint()])
    algo_comps = _algorithm_components(bom)
    names = [c.name for c in algo_comps]
    # curve25519-sha256 -> X25519 (or curve25519-sha256)
    has_curve = any(
        "X25519" in n.upper() or "CURVE25519" in n.upper() or "CURVE25519-SHA256" in n.lower()
        for n in names
    )
    # diffie-hellman-group14-sha256 -> DH-2048 (or similar)
    has_dh = any(
        "DH-2048" in n.upper() or "DIFFIE" in n.upper() or "GROUP14" in n.upper()
        or "DH" in n.upper()
        for n in names
    )
    assert has_curve, f"No curve25519 / X25519 component in: {names}"
    assert has_dh, f"No DH / group14 component in: {names}"


def test_ssh_hostkey_algorithms_become_components():
    """SSH key (hostkey) algorithms become ALGORITHM components."""
    bom = build_cbom([_ssh_endpoint()])
    algo_comps = _algorithm_components(bom)
    names = [c.name for c in algo_comps]
    has_rsa = any("RSA" in n.upper() for n in names)
    has_ecdsa = any("ECDSA" in n.upper() or "NISTP256" in n.upper() for n in names)
    assert has_rsa, f"No RSA (ssh-rsa) component in: {names}"
    assert has_ecdsa, f"No ECDSA component in: {names}"


def test_ssh_enc_algorithms_become_components():
    """SSH enc (symmetric cipher) algorithms become ALGORITHM components."""
    bom = build_cbom([_ssh_endpoint()])
    algo_comps = _algorithm_components(bom)
    names = [c.name for c in algo_comps]
    has_aes128 = any("AES" in n.upper() and "128" in n for n in names)
    has_chacha = any("CHACHA20" in n.upper() or "CHACHA" in n.upper() for n in names)
    assert has_aes128, f"No AES-128 component in: {names}"
    assert has_chacha, f"No ChaCha20 component in: {names}"


def test_ssh_mac_algorithms_become_components():
    """SSH mac algorithms become ALGORITHM components."""
    bom = build_cbom([_ssh_endpoint()])
    algo_comps = _algorithm_components(bom)
    names = [c.name for c in algo_comps]
    has_hmac_sha256 = any("HMAC" in n.upper() and "SHA" in n.upper() for n in names)
    assert has_hmac_sha256, f"No HMAC-SHA component in: {names}"


# ---------------------------------------------------------------------------
# CBOM-02 — Deduplication
# ---------------------------------------------------------------------------

def test_algorithm_deduplication():
    """Two endpoints with same cipher suite produce only one AES-256-GCM component."""
    ep1 = _tls_endpoint(host="host1.com", port=443)
    ep2 = _tls_endpoint(host="host2.com", port=443)
    bom = build_cbom([ep1, ep2])
    algo_comps = _algorithm_components(bom)
    names = [c.name for c in algo_comps]
    aes_count = sum(1 for n in names if "AES" in n.upper() and "256" in n)
    assert aes_count == 1, (
        f"Expected exactly 1 AES-256 component, got {aes_count}: "
        f"{[n for n in names if 'AES' in n.upper()]}"
    )


def test_cross_scanner_deduplication():
    """TLS endpoint with RSA-2048 cert + SSH endpoint with ssh-rsa — no bom_ref collision."""
    tls_ep = _tls_endpoint(cert_pubkey_alg="RSA", cert_pubkey_size=2048)
    ssh_ep = _ssh_endpoint()
    # Should not raise; distinct algorithm names get distinct bom_refs
    bom = build_cbom([tls_ep, ssh_ep])
    # Collect bom_refs — must all be unique (no collision)
    refs = [str(c.bom_ref) for c in bom.components]
    assert len(refs) == len(set(refs)), (
        f"Duplicate bom_refs detected: {refs}"
    )
    # RSA appears from both TLS cert (RSA-2048) and SSH (ssh-rsa -> RSA); no crash
    assert len(bom.components) > 0


# ---------------------------------------------------------------------------
# CBOM-01 — Protocol components
# ---------------------------------------------------------------------------

def test_tls_protocol_component_created():
    """A TLS endpoint produces a PROTOCOL component with ProtocolPropertiesType.TLS."""
    bom = build_cbom([_tls_endpoint()])
    proto_comps = _protocol_components(bom)
    assert len(proto_comps) >= 1, f"No protocol components found; all: {_component_names(bom)}"
    proto_types = [
        c.crypto_properties.protocol_properties.type
        for c in proto_comps
        if c.crypto_properties.protocol_properties is not None
    ]
    assert ProtocolPropertiesType.TLS in proto_types, (
        f"No TLS protocol component; found: {proto_types}"
    )


def test_ssh_protocol_component_created():
    """An SSH endpoint produces a PROTOCOL component with ProtocolPropertiesType.SSH."""
    bom = build_cbom([_ssh_endpoint()])
    proto_comps = _protocol_components(bom)
    assert len(proto_comps) >= 1, f"No protocol components found; all: {_component_names(bom)}"
    proto_types = [
        c.crypto_properties.protocol_properties.type
        for c in proto_comps
        if c.crypto_properties.protocol_properties is not None
    ]
    assert ProtocolPropertiesType.SSH in proto_types, (
        f"No SSH protocol component; found: {proto_types}"
    )


# ---------------------------------------------------------------------------
# CBOM-01 — Certificate components
# ---------------------------------------------------------------------------

def test_certificate_component_created():
    """A TLS endpoint with cert fields produces a CERTIFICATE component."""
    ep = _tls_endpoint(
        cert_subject="CN=example.com",
        cert_issuer="CN=Example CA",
        cert_pubkey_alg="RSA",
        cert_pubkey_size=2048,
    )
    bom = build_cbom([ep])
    cert_comps = _certificate_components(bom)
    assert len(cert_comps) >= 1, (
        f"No certificate components found; all: {_component_names(bom)}"
    )


# ---------------------------------------------------------------------------
# New protocol surfaces (Plan 03-04)
# ---------------------------------------------------------------------------

def test_jwt_endpoint_creates_algorithm_component():
    """JWT endpoint must register its alg as an algorithm component."""
    ep = CryptoEndpoint(host="api.example.com", port=443, protocol="JWT",
                        cert_pubkey_alg="RS256", cert_pubkey_size=2048,
                        jwt_scan_json='{"kty":"RSA","alg":"RS256"}')
    bom = build_cbom([ep])
    algo_names = {c.name for c in bom.components if "algorithm" in str(c.bom_ref)}
    assert "RS256" in algo_names


def test_container_endpoint_no_tls_fallthrough():
    """CONTAINER endpoint must NOT create a TLS protocol component (pitfall 6)."""
    ep = CryptoEndpoint(host="python:3.12", port=0, protocol="CONTAINER",
                        cipher_suite="openssl", tls_version="3.0.2",
                        container_scan_json='{"name":"openssl"}')
    bom = build_cbom([ep])
    proto_names = [c.name for c in bom.components if "protocol" in str(c.bom_ref)]
    # No protocol component should be created for CONTAINER
    assert len(proto_names) == 0


def test_source_endpoint_extracts_algo_hint():
    """SOURCE endpoint should extract algorithm from rule_id when possible."""
    ep = CryptoEndpoint(host="/repo", port=0, protocol="SOURCE",
                        cipher_suite="python.cryptography.security.insecure-hash-algorithms-md5",
                        source_scan_json='{}')
    bom = build_cbom([ep])
    algo_names = {c.name.lower() for c in bom.components if "algorithm" in str(c.bom_ref)}
    assert "md5" in algo_names


def test_aws_endpoint_registers_algorithm():
    """AWS endpoint with KeySpec in cloud_scan_json must register algorithm."""
    ep = CryptoEndpoint(host="arn:aws:kms:us-east-1:123:key/abc", port=0, protocol="AWS",
                        cert_pubkey_alg="RSA_2048",
                        cloud_scan_json='{"KeySpec":"RSA_2048","Arn":"arn:aws:kms:us-east-1:123:key/abc"}')
    bom = build_cbom([ep])
    algo_names = {c.name.lower() for c in bom.components if "algorithm" in str(c.bom_ref)}
    assert "rsa" in algo_names or "rsa_2048" in algo_names


def test_azure_endpoint_no_tls_protocol():
    """AZURE endpoint must NOT fall through to TLS protocol component."""
    ep = CryptoEndpoint(host="https://vault.azure.net/keys/k1", port=0, protocol="AZURE",
                        cert_pubkey_alg="RSA",
                        cloud_scan_json='{"key_type":"RSA","key_size":2048}')
    bom = build_cbom([ep])
    proto_names = [c.name for c in bom.components if "protocol:tls" in str(c.bom_ref)]
    assert len(proto_names) == 0


# ---------------------------------------------------------------------------
# SAML protocol tests (Phase 22 gap closure — SAML-05)
# ---------------------------------------------------------------------------

def test_saml_endpoint_algorithm_registered():
    """SAML endpoint registers algorithm component from cert_pubkey_alg."""
    ep = _saml_endpoint(cert_pubkey_alg="RSA", cert_pubkey_size=2048)
    bom = build_cbom([ep])
    algo_refs = [c.bom_ref for c in bom.components if "crypto/algorithm/" in str(c.bom_ref)]
    assert any("rsa" in str(ref) for ref in algo_refs), f"RSA algorithm not found in {algo_refs}"


def test_saml_endpoint_no_tls_protocol():
    """SAML endpoint must NOT produce a TLS protocol component."""
    ep = _saml_endpoint()
    bom = build_cbom([ep])
    tls_protos = [c for c in bom.components if str(c.bom_ref).startswith("crypto/protocol/tls/")]
    assert tls_protos == [], f"Spurious TLS protocol components for SAML: {[str(c.bom_ref) for c in tls_protos]}"


def test_saml_endpoint_no_certificate():
    """SAML SHA1 finding must NOT produce a certificate component (no cert metadata)."""
    ep = _saml_endpoint(cert_pubkey_alg="SHA1", cert_pubkey_size=None)
    bom = build_cbom([ep])
    cert_comps = [c for c in bom.components if str(c.bom_ref).startswith("crypto/certificate/")]
    assert cert_comps == [], f"Spurious certificate components for SAML: {[str(c.bom_ref) for c in cert_comps]}"


# ---------------------------------------------------------------------------
# Kerberos protocol tests (Phase 22 gap closure — KERB-04)
# ---------------------------------------------------------------------------

def test_kerberos_endpoint_algorithm_registered():
    """Kerberos endpoint registers algorithm component from etype name."""
    ep = _kerberos_endpoint(cert_pubkey_alg="rc4-hmac")
    bom = build_cbom([ep])
    algo_refs = [str(c.bom_ref) for c in bom.components if "crypto/algorithm/" in str(c.bom_ref)]
    assert any("rc4-hmac" in ref for ref in algo_refs), f"rc4-hmac algorithm not found in {algo_refs}"


def test_kerberos_endpoint_no_tls_protocol():
    """Kerberos endpoint must NOT produce a TLS protocol component."""
    ep = _kerberos_endpoint()
    bom = build_cbom([ep])
    tls_protos = [c for c in bom.components if str(c.bom_ref).startswith("crypto/protocol/tls/")]
    assert tls_protos == [], f"Spurious TLS protocol components for Kerberos: {[str(c.bom_ref) for c in tls_protos]}"


def test_kerberos_endpoint_no_certificate():
    """Kerberos etype endpoint must NOT produce a certificate component."""
    ep = _kerberos_endpoint(cert_pubkey_alg="rc4-hmac")
    bom = build_cbom([ep])
    cert_comps = [c for c in bom.components if str(c.bom_ref).startswith("crypto/certificate/")]
    assert cert_comps == [], f"Spurious certificate components for Kerberos: {[str(c.bom_ref) for c in cert_comps]}"


def test_kerberos_unreachable_excluded():
    """Kerberos 'kerberos-unreachable' synthetic finding must NOT register an algorithm."""
    ep = _kerberos_endpoint(cert_pubkey_alg="kerberos-unreachable")
    bom = build_cbom([ep])
    algo_refs = [str(c.bom_ref) for c in bom.components if "crypto/algorithm/" in str(c.bom_ref)]
    assert algo_refs == [], f"kerberos-unreachable should not register algorithm: {algo_refs}"


# ---------------------------------------------------------------------------
# DNSSEC protocol tests (Phase 23 gap closure — DNSSEC-04)
# ---------------------------------------------------------------------------

def _dnssec_endpoint(**overrides):
    """Create a DNSSEC CryptoEndpoint with sensible defaults."""
    defaults = dict(
        host="example.com", port=53, protocol="DNSSEC",
        tls_version=None, cipher_suite=None,
        cert_pubkey_alg="ECDSAP256SHA256", cert_pubkey_size=256,
        cert_sig_alg=None, cert_subject=None, cert_issuer=None,
        cert_not_before=None, cert_not_after=None,
        tls_capabilities_json=None, ssh_audit_json=None,
    )
    defaults.update(overrides)
    return CryptoEndpoint(**defaults)


def test_dnssec_endpoint_algorithm_registered():
    """DNSSEC endpoint registers algorithm component from cert_pubkey_alg."""
    ep = _dnssec_endpoint(cert_pubkey_alg="ECDSAP256SHA256", cert_pubkey_size=256)
    bom = build_cbom([ep])
    algo_refs = [c.bom_ref for c in bom.components if "crypto/algorithm/" in str(c.bom_ref)]
    assert any("ecdsap256sha256" in str(ref) for ref in algo_refs), \
        f"ECDSAP256SHA256 algorithm not found in {algo_refs}"


def test_dnssec_endpoint_no_tls_protocol():
    """DNSSEC endpoint must NOT produce a TLS protocol component."""
    ep = _dnssec_endpoint()
    bom = build_cbom([ep])
    tls_protos = [c for c in bom.components
                  if str(c.bom_ref).startswith("crypto/protocol/tls/")]
    assert tls_protos == [], \
        f"Spurious TLS protocol components for DNSSEC: {[str(c.bom_ref) for c in tls_protos]}"


def test_dnssec_endpoint_no_certificate():
    """DNSSEC endpoint must NOT produce a certificate component (DNSKEY is not an X.509 cert)."""
    ep = _dnssec_endpoint(cert_pubkey_alg="ECDSAP256SHA256", cert_pubkey_size=256)
    bom = build_cbom([ep])
    cert_comps = [c for c in bom.components
                  if str(c.bom_ref).startswith("crypto/certificate/")]
    assert cert_comps == [], \
        f"Spurious certificate components for DNSSEC: {[str(c.bom_ref) for c in cert_comps]}"


# ---------------------------------------------------------------------------
# Phase 52 COMPLY-10 — FIPS 140-3 annotation stubs (RED — fail until Plan 02)
# ---------------------------------------------------------------------------

def test_fips_status_helper():
    """COMPLY-10 (D-04): _fips_status() maps nist_level correctly."""
    from quirk.cbom.builder import _fips_status
    assert _fips_status(1) == "approved"
    assert _fips_status(3) == "approved"
    assert _fips_status(0) == "non-approved"
    assert _fips_status(None) == "non-approved"


def test_algorithm_component_has_fips_property():
    """COMPLY-10 (D-03): Every algo component built by build_cbom carries quirk:fips140-3-status."""
    ep = _tls_endpoint()
    bom = build_cbom([ep])
    algo_components = [
        c for c in bom.components
        if hasattr(c, "crypto_properties")
        and c.crypto_properties is not None
        and c.crypto_properties.asset_type is not None
        and c.crypto_properties.asset_type.value == "algorithm"
    ]
    assert algo_components, "Expected at least one algorithm component in CBOM"
    for comp in algo_components:
        prop_names = {p.name for p in (comp.properties or [])}
        assert "quirk:fips140-3-status" in prop_names, (
            f"Algorithm component '{comp.name}' missing quirk:fips140-3-status property"
        )
        fips_val = next(p.value for p in comp.properties if p.name == "quirk:fips140-3-status")
        assert fips_val in ("approved", "non-approved"), (
            f"quirk:fips140-3-status must be 'approved' or 'non-approved', got '{fips_val}'"
        )


# ---------------------------------------------------------------------------
# Phase 110 MERGE-03 — sensor-aware bom_ref identity (RED until Task 2)
# ---------------------------------------------------------------------------

def test_two_sensors_same_ip_two_components():
    """MERGE-03: two sensors reporting same RFC1918 host:port in different segments must
    produce two distinct CBOM certificate components (not collapsed into one).
    RED: fails until _sensor_prefix is threaded through builder.py bom_ref sites.
    """
    ep_a = _tls_endpoint(host="10.0.0.5", port=443, sensor_id="sensor-a", segment="prod-east")
    ep_b = _tls_endpoint(host="10.0.0.5", port=443, sensor_id="sensor-b", segment="prod-west")
    bom = build_cbom([ep_a, ep_b])

    cert_refs = [
        getattr(c.bom_ref, "value", None)
        for c in bom.components
        if c.crypto_properties and c.crypto_properties.asset_type == CryptoAssetType.CERTIFICATE
    ]
    assert "crypto/certificate/sensor-a:10.0.0.5:443" in cert_refs, (
        f"Missing sensor-a cert ref; got: {cert_refs}"
    )
    assert "crypto/certificate/sensor-b:10.0.0.5:443" in cert_refs, (
        f"Missing sensor-b cert ref; got: {cert_refs}"
    )
    assert len(cert_refs) == 2, (
        f"Expected exactly 2 certificate components (one per sensor), got {len(cert_refs)}: {cert_refs}"
    )

    # TLS protocol components must also be sensor-separated
    tls_proto_refs = [
        getattr(c.bom_ref, "value", None)
        for c in bom.components
        if c.crypto_properties and c.crypto_properties.asset_type == CryptoAssetType.PROTOCOL
    ]
    assert "crypto/protocol/tls/sensor-a:10.0.0.5:443" in tls_proto_refs, (
        f"Missing sensor-a TLS proto ref; got: {tls_proto_refs}"
    )
    assert "crypto/protocol/tls/sensor-b:10.0.0.5:443" in tls_proto_refs, (
        f"Missing sensor-b TLS proto ref; got: {tls_proto_refs}"
    )


def test_null_sensor_id_backward_compat():
    """MERGE-03: NULL sensor_id must produce byte-identical bom_refs to the pre-110 format.
    GREEN: passes even before Task 2 is implemented (NULL prefix = empty string).
    After Task 2: still passes with _sensor_prefix returning '' for None.
    """
    ep_local = _tls_endpoint(host="10.0.0.5", port=443, sensor_id=None)
    bom_local = build_cbom([ep_local])

    cert_refs = [
        getattr(c.bom_ref, "value", None)
        for c in bom_local.components
        if c.crypto_properties and c.crypto_properties.asset_type == CryptoAssetType.CERTIFICATE
    ]
    assert cert_refs == ["crypto/certificate/10.0.0.5:443"], (
        f"NULL sensor_id must produce pre-110 byte-identical bom_ref; got: {cert_refs}"
    )

    tls_proto_refs = [
        getattr(c.bom_ref, "value", None)
        for c in bom_local.components
        if c.crypto_properties and c.crypto_properties.asset_type == CryptoAssetType.PROTOCOL
    ]
    assert "crypto/protocol/tls/10.0.0.5:443" in tls_proto_refs, (
        f"NULL sensor_id TLS proto ref must be pre-110 format; got: {tls_proto_refs}"
    )


# ---------------------------------------------------------------------------
# CR-02 — surrogate key is sensor-scoped; same wildcard cert from two sensors
#          must annotate the correct per-sensor TLS component
# ---------------------------------------------------------------------------

def test_codesign_surrogate_attaches_to_correct_sensor_cert():
    """CR-02: two sensors present the same wildcard cert; CODE_SIGNING annotation
    must attach to the correct per-sensor TLS cert component, not collide.

    Setup:
      - sensor-a TLS endpoint: *.internal.example.com, RSA-2048, same not_after
      - sensor-b TLS endpoint: same cert metadata
      - One CODE_SIGNING endpoint for sensor-a with the same surrogate metadata

    Expected:
      - The quirk:code-signing-eku property is on sensor-a's cert component only.
      - sensor-b's cert component has no such property.
    """
    not_after = "2027-01-01"

    ep_tls_a = _tls_endpoint(
        host="10.0.1.5", port=443,
        sensor_id="sensor-a",
        cert_subject="CN=*.internal.example.com",
        cert_pubkey_alg="RSA",
        cert_pubkey_size=2048,
        cert_sig_alg="sha256WithRSAEncryption",
        cert_issuer="CN=Internal CA",
        cert_not_after=not_after,
    )
    ep_tls_b = _tls_endpoint(
        host="10.0.2.5", port=443,
        sensor_id="sensor-b",
        cert_subject="CN=*.internal.example.com",
        cert_pubkey_alg="RSA",
        cert_pubkey_size=2048,
        cert_sig_alg="sha256WithRSAEncryption",
        cert_issuer="CN=Internal CA",
        cert_not_after=not_after,
    )
    # CODE_SIGNING endpoint from sensor-a matching the same surrogate key
    ep_cs_a = CryptoEndpoint(
        host="10.0.1.5", port=0,
        protocol="CODE_SIGNING",
        cert_subject="CN=*.internal.example.com",
        cert_pubkey_alg="RSA",
        cert_pubkey_size=2048,
        cert_sig_alg="sha256WithRSAEncryption",
        cert_issuer="CN=Internal CA",
        cert_not_after=not_after,
        sensor_id="sensor-a",
        segment="prod-east",
        tls_version=None,
        cipher_suite=None,
        cert_not_before=None,
        tls_capabilities_json=None,
        ssh_audit_json=None,
    )

    bom = build_cbom([ep_tls_a, ep_tls_b, ep_cs_a])

    cert_components = [
        c for c in bom.components
        if c.crypto_properties and c.crypto_properties.asset_type == CryptoAssetType.CERTIFICATE
    ]

    # Find sensor-a and sensor-b cert components by bom_ref
    cert_a = next(
        (c for c in cert_components
         if getattr(c.bom_ref, "value", "") == "crypto/certificate/sensor-a:10.0.1.5:443"),
        None
    )
    cert_b = next(
        (c for c in cert_components
         if getattr(c.bom_ref, "value", "") == "crypto/certificate/sensor-b:10.0.2.5:443"),
        None
    )

    assert cert_a is not None, "sensor-a cert component must be present"
    assert cert_b is not None, "sensor-b cert component must be present"

    # sensor-a cert should carry the code-signing annotation
    prop_names_a = {p.name for p in (cert_a.properties or [])}
    assert "quirk:code-signing-eku" in prop_names_a, (
        f"sensor-a cert should have quirk:code-signing-eku; props={prop_names_a}"
    )

    # sensor-b cert must NOT carry the annotation (different sensor, no CODE_SIGNING ep)
    prop_names_b = {p.name for p in (cert_b.properties or [])}
    assert "quirk:code-signing-eku" not in prop_names_b, (
        f"sensor-b cert must NOT have quirk:code-signing-eku (CR-02 collision); props={prop_names_b}"
    )
