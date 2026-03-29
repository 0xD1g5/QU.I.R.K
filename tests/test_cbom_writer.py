"""Tests for quirk.cbom.writer — CBOM file serialization to JSON and XML.

RED phase: tests import from quirk.cbom.writer which does not exist yet.
"""
from __future__ import annotations

import json
import os

import pytest

from quirk.cbom.writer import write_cbom_files


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _tls_endpoint(**overrides):
    """Create a TLS CryptoEndpoint with sensible defaults."""
    from quirk.models import CryptoEndpoint
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


def _build_test_bom():
    """Build a Bom from a TLS endpoint for use in tests."""
    from quirk.cbom.builder import build_cbom
    ep = _tls_endpoint()
    return build_cbom([ep])


# ---------------------------------------------------------------------------
# Test: file creation
# ---------------------------------------------------------------------------

def test_write_cbom_files_creates_two_files(tmp_path):
    from cyclonedx.model.bom import Bom
    bom = Bom()
    json_path, xml_path = write_cbom_files(bom, str(tmp_path), "20260329-120000")
    assert os.path.exists(json_path)
    assert os.path.exists(xml_path)


def test_write_cbom_files_returns_paths(tmp_path):
    from cyclonedx.model.bom import Bom
    bom = Bom()
    result = write_cbom_files(bom, str(tmp_path), "20260329-120000")
    assert isinstance(result, tuple)
    assert len(result) == 2
    json_path, xml_path = result
    assert isinstance(json_path, str)
    assert isinstance(xml_path, str)
    assert os.path.exists(json_path)
    assert os.path.exists(xml_path)


def test_write_cbom_files_naming_pattern(tmp_path):
    from cyclonedx.model.bom import Bom
    bom = Bom()
    stamp = "20260329-120000"
    json_path, xml_path = write_cbom_files(bom, str(tmp_path), stamp)
    assert json_path.endswith(f"cbom-{stamp}.cdx.json")
    assert xml_path.endswith(f"cbom-{stamp}.cdx.xml")


# ---------------------------------------------------------------------------
# Test: JSON format validation
# ---------------------------------------------------------------------------

def test_json_output_is_valid_cdx(tmp_path):
    from cyclonedx.model.bom import Bom
    bom = Bom()
    json_path, _ = write_cbom_files(bom, str(tmp_path), "20260329-120000")
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    assert data["bomFormat"] == "CycloneDX"
    assert data["specVersion"].startswith("1.6")


def test_xml_output_is_valid_cdx(tmp_path):
    from cyclonedx.model.bom import Bom
    bom = Bom()
    _, xml_path = write_cbom_files(bom, str(tmp_path), "20260329-120000")
    with open(xml_path, encoding="utf-8") as f:
        xml_content = f.read()
    assert 'cyclonedx.org' in xml_content


# ---------------------------------------------------------------------------
# Test: crypto properties in JSON/XML
# ---------------------------------------------------------------------------

def test_json_contains_crypto_properties(tmp_path):
    bom = _build_test_bom()
    json_path, _ = write_cbom_files(bom, str(tmp_path), "20260329-120000")
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    components = data.get("components", [])
    assert len(components) > 0
    # At least one component must have cryptoProperties
    assert any("cryptoProperties" in c for c in components), (
        f"No component has cryptoProperties; components: {[c.get('name') for c in components]}"
    )


def test_xml_contains_crypto_properties(tmp_path):
    bom = _build_test_bom()
    _, xml_path = write_cbom_files(bom, str(tmp_path), "20260329-120000")
    with open(xml_path, encoding="utf-8") as f:
        xml_content = f.read()
    # CycloneDX XML uses either 'cryptoProperties' or 'crypto-properties'
    assert ("cryptoProperties" in xml_content or "crypto-properties" in xml_content), (
        "XML does not contain crypto properties element"
    )


# ---------------------------------------------------------------------------
# Test: NIST quantum security level in JSON
# ---------------------------------------------------------------------------

def test_json_algorithm_has_nist_level(tmp_path):
    """RSA-2048 should have nistQuantumSecurityLevel=0 (quantum-vulnerable)."""
    bom = _build_test_bom()
    json_path, _ = write_cbom_files(bom, str(tmp_path), "20260329-120000")
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    components = data.get("components", [])
    # Find RSA component (pubkey component from cert)
    rsa_components = [
        c for c in components
        if "rsa" in c.get("name", "").lower()
        and "cryptoProperties" in c
        and c["cryptoProperties"].get("assetType") == "algorithm"
    ]
    assert len(rsa_components) > 0, "No RSA algorithm component found in CBOM"
    rsa = rsa_components[0]
    algo_props = rsa["cryptoProperties"].get("algorithmProperties", {})
    assert algo_props.get("nistQuantumSecurityLevel") == 0, (
        f"Expected nistQuantumSecurityLevel=0 for RSA, got: {algo_props.get('nistQuantumSecurityLevel')}"
    )


# ---------------------------------------------------------------------------
# Test: overwrite existing files
# ---------------------------------------------------------------------------

def test_overwrite_existing_files(tmp_path):
    """Writing twice to the same stamp should not raise an error."""
    bom = _build_test_bom()
    stamp = "20260329-120000"
    # First write
    write_cbom_files(bom, str(tmp_path), stamp)
    # Second write — should not raise
    json_path, xml_path = write_cbom_files(bom, str(tmp_path), stamp)
    assert os.path.exists(json_path)
    assert os.path.exists(xml_path)
