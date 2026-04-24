"""Tests for SAML/OIDC scanner (SAML-01 through SAML-06).

Tests mock httpx and lxml to avoid network calls and lxml dependency.
Scanner module: quirk/scanner/saml_scanner.py
"""

import base64
import datetime
import json
import os
import pytest
from unittest.mock import patch, MagicMock

from quirk.scanner.saml_scanner import (
    scan_saml_targets,
    SAML_NS,
    LXML_AVAILABLE,
    SHA1_INDICATORS,
    OIDC_ALG_SEVERITY,
    _is_sha1_uri,
    _classify_key_severity,
)


# ---------------------------------------------------------------------------
# Module-level test certificate generation
# ---------------------------------------------------------------------------

def _generate_test_cert(key_size: int = 1024) -> str:
    """Generate a self-signed RSA certificate and return base64-encoded DER."""
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography import x509
    from cryptography.x509.oid import NameOID

    key = rsa.generate_private_key(public_exponent=65537, key_size=key_size)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, f"test-{key_size}")])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.utcnow())
        .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=365))
        .sign(key, hashes.SHA256())
    )
    return base64.b64encode(cert.public_bytes(serialization.Encoding.DER)).decode()


# Generate test certs at module level — deterministic per test run
RSA_1024_CERT_B64 = _generate_test_cert(1024)
RSA_2048_CERT_B64 = _generate_test_cert(2048)


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------

SAMPLE_SAML_METADATA_XML = f"""<?xml version="1.0" encoding="UTF-8"?>
<md:EntityDescriptor
    xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata"
    xmlns:ds="http://www.w3.org/2000/09/xmldsig#"
    xmlns:alg="urn:oasis:names:tc:SAML:metadata:algsupport"
    xmlns:mdui="urn:oasis:names:tc:SAML:metadata:ui"
    entityID="https://idp.chaos.local/">
  <ds:Signature>
    <ds:SignedInfo>
      <ds:SignatureMethod Algorithm="http://www.w3.org/2000/09/xmldsig#rsa-sha1"/>
    </ds:SignedInfo>
  </ds:Signature>
  <md:Extensions>
    <alg:SigningMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"/>
  </md:Extensions>
  <md:IDPSSODescriptor WantAuthnRequestsSigned="false"
      protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">
    <md:KeyDescriptor use="signing">
      <ds:KeyInfo>
        <ds:X509Data>
          <ds:X509Certificate>{RSA_1024_CERT_B64}</ds:X509Certificate>
        </ds:X509Data>
      </ds:KeyInfo>
    </md:KeyDescriptor>
    <md:KeyDescriptor use="encryption">
      <ds:KeyInfo>
        <ds:X509Data>
          <ds:X509Certificate>{RSA_2048_CERT_B64}</ds:X509Certificate>
        </ds:X509Data>
      </ds:KeyInfo>
    </md:KeyDescriptor>
  </md:IDPSSODescriptor>
</md:EntityDescriptor>
""".encode()

SAMPLE_OIDC_DISCOVERY_JSON = json.dumps({
    "issuer": "https://auth.chaos.local",
    "id_token_signing_alg_values_supported": ["RS256", "ES256"],
    "request_object_signing_alg_values_supported": ["RS256"],
}).encode()

SAMPLE_OIDC_MINIMAL_JSON = json.dumps({
    "issuer": "https://auth.chaos.local",
    "id_token_signing_alg_values_supported": ["RS256"],
}).encode()


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------

def _mock_httpx_response(
    content: bytes,
    status_code: int = 200,
    content_type: str = "application/xml",
) -> MagicMock:
    """Return a mock httpx.Response object."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.content = content
    resp.headers = {"content-type": content_type}
    resp.text = content.decode("utf-8", errors="replace")
    return resp


# ---------------------------------------------------------------------------
# SAML-04 (static severity tests) — GREEN against stub
# ---------------------------------------------------------------------------

def test_severity_rsa_1024_critical():
    """SAML-04: RSA-1024 key must be classified CRITICAL (D-07)."""
    assert _classify_key_severity("RSA", 1024) == "CRITICAL"


def test_severity_rsa_2048_high():
    """SAML-04: RSA-2048 key must be classified HIGH (D-07)."""
    assert _classify_key_severity("RSA", 2048) == "HIGH"


def test_severity_rsa_4096_high():
    """SAML-04: RSA-4096 still quantum-vulnerable — must be classified HIGH (D-07)."""
    assert _classify_key_severity("RSA", 4096) == "HIGH"


def test_severity_ecdsa_safe():
    """SAML-04: ECDSA key must produce no severity finding (D-07)."""
    assert _classify_key_severity("ECDSA", 256) is None


def test_severity_ecdsa_p384_safe():
    """SAML-04: ECDSA P-384 must produce no severity finding (D-07)."""
    assert _classify_key_severity("ECDSA", 384) is None


def test_sha1_uri_detected():
    """SAML-04: Standard SHA-1 xmldsig URI must be detected (D-05)."""
    assert _is_sha1_uri("http://www.w3.org/2000/09/xmldsig#rsa-sha1") is True


def test_sha1_variant_uri_detected():
    """SAML-04: Variant SHA-1 URI must be detected case-insensitively (D-05)."""
    assert _is_sha1_uri("http://www.w3.org/2001/04/xmldsig-more#rsa-sha1") is True


def test_sha256_uri_not_flagged():
    """SAML-04: SHA-256 URI must NOT be flagged as SHA-1 (D-05)."""
    assert _is_sha1_uri("http://www.w3.org/2001/04/xmldsig-more#rsa-sha256") is False


def test_sha1_uppercase_detected():
    """SAML-04: SHA1 in upper case must be detected (D-05 case-insensitive)."""
    assert _is_sha1_uri("http://example.com/URI#RSA-SHA1") is True


# ---------------------------------------------------------------------------
# SAML-01 (static namespace test) — GREEN against stub
# ---------------------------------------------------------------------------

def test_saml_ns_has_all_namespaces():
    """SAML-01: SAML_NS must contain all 4 required prefix keys (D-06)."""
    assert set(SAML_NS.keys()) == {"md", "ds", "alg", "mdui"}


def test_saml_ns_md_value():
    """SAML-01: SAML_NS['md'] must be the SAML 2.0 metadata namespace URI."""
    assert SAML_NS["md"] == "urn:oasis:names:tc:SAML:2.0:metadata"


def test_saml_ns_ds_value():
    """SAML-01: SAML_NS['ds'] must be the XMLDSig namespace URI."""
    assert SAML_NS["ds"] == "http://www.w3.org/2000/09/xmldsig#"


def test_saml_ns_alg_value():
    """SAML-01: SAML_NS['alg'] must be the SAML algorithm support namespace URI."""
    assert SAML_NS["alg"] == "urn:oasis:names:tc:SAML:metadata:algsupport"


# ---------------------------------------------------------------------------
# SAML-01: Signing cert extraction (RED — calls scan_saml_targets)
# ---------------------------------------------------------------------------

def test_signing_cert_rsa_1024_extraction():
    """SAML-01: RSA-1024 signing cert must produce CryptoEndpoint with cert_pubkey_alg='RSA', cert_pubkey_size=1024."""
    with patch("quirk.scanner.saml_scanner.LXML_AVAILABLE", True), \
         patch("quirk.scanner.saml_scanner._fetch_metadata", return_value=SAMPLE_SAML_METADATA_XML):
        result = scan_saml_targets(["https://idp.chaos.local/metadata"])
    signing_eps = [ep for ep in result if ep.service_detail and "use=signing" in ep.service_detail]
    assert len(signing_eps) >= 1, "Expected at least one signing cert endpoint"
    ep = signing_eps[0]
    assert ep.cert_pubkey_alg == "RSA", f"Expected RSA, got {ep.cert_pubkey_alg}"
    assert ep.cert_pubkey_size == 1024, f"Expected 1024, got {ep.cert_pubkey_size}"
    assert ep.protocol == "SAML", f"Expected SAML protocol, got {ep.protocol}"


def test_signing_cert_entity_id_in_service_detail():
    """SAML-01: Entity ID from metadata must appear in service_detail (D-02)."""
    with patch("quirk.scanner.saml_scanner.LXML_AVAILABLE", True), \
         patch("quirk.scanner.saml_scanner._fetch_metadata", return_value=SAMPLE_SAML_METADATA_XML):
        result = scan_saml_targets(["https://idp.chaos.local/metadata"])
    signing_eps = [ep for ep in result if ep.service_detail and "use=signing" in ep.service_detail]
    assert len(signing_eps) >= 1
    ep = signing_eps[0]
    assert "idp.chaos.local" in ep.service_detail, \
        f"Entity ID missing from service_detail: {ep.service_detail}"
    assert "use=signing" in ep.service_detail


# ---------------------------------------------------------------------------
# SAML-02: Encryption cert separation (RED — calls scan_saml_targets)
# ---------------------------------------------------------------------------

def test_encryption_cert_separate_from_signing():
    """SAML-02: Metadata with both signing and encryption certs must produce separate CryptoEndpoints."""
    with patch("quirk.scanner.saml_scanner.LXML_AVAILABLE", True), \
         patch("quirk.scanner.saml_scanner._fetch_metadata", return_value=SAMPLE_SAML_METADATA_XML):
        result = scan_saml_targets(["https://idp.chaos.local/metadata"])
    service_details = [ep.service_detail for ep in result if ep.service_detail]
    has_signing = any("use=signing" in sd for sd in service_details)
    has_encryption = any("use=encryption" in sd for sd in service_details)
    assert has_signing, f"Missing signing endpoint in service_details: {service_details}"
    assert has_encryption, f"Missing encryption endpoint in service_details: {service_details}"


def test_encryption_cert_key_size():
    """SAML-02: Encryption cert (RSA-2048) must report cert_pubkey_size=2048 independently."""
    with patch("quirk.scanner.saml_scanner.LXML_AVAILABLE", True), \
         patch("quirk.scanner.saml_scanner._fetch_metadata", return_value=SAMPLE_SAML_METADATA_XML):
        result = scan_saml_targets(["https://idp.chaos.local/metadata"])
    enc_eps = [ep for ep in result if ep.service_detail and "use=encryption" in ep.service_detail]
    assert len(enc_eps) >= 1, "Expected at least one encryption cert endpoint"
    ep = enc_eps[0]
    assert ep.cert_pubkey_size == 2048, f"Expected 2048, got {ep.cert_pubkey_size}"


# ---------------------------------------------------------------------------
# SAML-03: OIDC discovery enumeration (RED — calls scan_saml_targets)
# ---------------------------------------------------------------------------

def test_oidc_discovery_alg_enumeration():
    """SAML-03: OIDC discovery with RS256+ES256 must produce HIGH finding for RS256."""
    with patch("quirk.scanner.saml_scanner.LXML_AVAILABLE", True), \
         patch("quirk.scanner.saml_scanner._fetch_metadata", return_value=SAMPLE_OIDC_DISCOVERY_JSON):
        result = scan_saml_targets(["https://auth.chaos.local/.well-known/openid-configuration"])
    rs256_eps = [ep for ep in result if ep.cert_pubkey_alg == "RS256"]
    assert len(rs256_eps) >= 1, "Expected at least one RS256 finding"
    ep = rs256_eps[0]
    # RS256 is HIGH severity per OIDC_ALG_SEVERITY
    assert OIDC_ALG_SEVERITY["RS256"] == "HIGH"


def test_oidc_missing_request_object_field():
    """SAML-03: Missing request_object_signing_alg_values_supported must not raise (D-03 graceful degradation)."""
    with patch("quirk.scanner.saml_scanner.LXML_AVAILABLE", True), \
         patch("quirk.scanner.saml_scanner._fetch_metadata", return_value=SAMPLE_OIDC_MINIMAL_JSON):
        # Must not raise; RS256 must still be found
        result = scan_saml_targets(["https://auth.chaos.local/.well-known/openid-configuration"])
    rs256_eps = [ep for ep in result if ep.cert_pubkey_alg == "RS256"]
    assert len(rs256_eps) >= 1, "Expected RS256 finding even without request_object field"


def test_wellknown_url_classified_as_oidc():
    """SAML-03: URL containing '.well-known' must be classified as OIDC target (D-01)."""
    from quirk.scanner.saml_scanner import _classify_target
    url = "https://auth.chaos.local/.well-known/openid-configuration"
    result = _classify_target(url, SAMPLE_OIDC_DISCOVERY_JSON)
    assert result == "oidc", f"Expected 'oidc', got {result!r}"


# ---------------------------------------------------------------------------
# SAML-04: SHA-1 URI in metadata produces finding (RED — calls scan_saml_targets)
# ---------------------------------------------------------------------------

def test_sha1_uri_in_metadata_produces_finding():
    """SAML-04: SHA-1 SignatureMethod URI in metadata must produce a SHA1 CryptoEndpoint (D-04, D-08)."""
    with patch("quirk.scanner.saml_scanner.LXML_AVAILABLE", True), \
         patch("quirk.scanner.saml_scanner._fetch_metadata", return_value=SAMPLE_SAML_METADATA_XML):
        result = scan_saml_targets(["https://idp.chaos.local/metadata"])
    sha1_eps = [ep for ep in result if ep.cert_pubkey_alg == "SHA1"]
    assert len(sha1_eps) >= 1, \
        f"Expected SHA1 finding from SignatureMethod URI; got algs={[ep.cert_pubkey_alg for ep in result]}"
    ep = sha1_eps[0]
    assert ep.service_detail and "source=SignatureMethod" in ep.service_detail, \
        f"Expected 'source=SignatureMethod' in service_detail: {ep.service_detail}"


# ---------------------------------------------------------------------------
# SAML-05: CBOM integration — CryptoEndpoint fields (RED — calls scan_saml_targets)
# ---------------------------------------------------------------------------

def test_cryptoendpoint_protocol_saml():
    """SAML-05: All endpoints from a SAML scan must have protocol='SAML'."""
    with patch("quirk.scanner.saml_scanner.LXML_AVAILABLE", True), \
         patch("quirk.scanner.saml_scanner._fetch_metadata", return_value=SAMPLE_SAML_METADATA_XML):
        result = scan_saml_targets(["https://idp.chaos.local/metadata"])
    assert len(result) > 0, "Expected at least one endpoint"
    for ep in result:
        assert ep.protocol == "SAML", f"Expected SAML protocol, got {ep.protocol}"


def test_saml_scan_json_populated():
    """SAML-05: saml_scan_json must be non-None and valid JSON (D-17)."""
    with patch("quirk.scanner.saml_scanner.LXML_AVAILABLE", True), \
         patch("quirk.scanner.saml_scanner._fetch_metadata", return_value=SAMPLE_SAML_METADATA_XML):
        result = scan_saml_targets(["https://idp.chaos.local/metadata"])
    assert len(result) > 0
    for ep in result:
        assert ep.saml_scan_json is not None, "saml_scan_json must not be None"
        parsed = json.loads(ep.saml_scan_json)
        assert isinstance(parsed, (dict, list)), "saml_scan_json must parse to dict or list"


def test_saml_scan_json_structure():
    """SAML-05: saml_scan_json must contain required keys per D-17."""
    with patch("quirk.scanner.saml_scanner.LXML_AVAILABLE", True), \
         patch("quirk.scanner.saml_scanner._fetch_metadata", return_value=SAMPLE_SAML_METADATA_XML):
        result = scan_saml_targets(["https://idp.chaos.local/metadata"])
    assert len(result) > 0
    # Get the scan_json from the first endpoint (all share same scan dict for same target)
    ep = result[0]
    scan_data = json.loads(ep.saml_scan_json)
    # D-17: must contain url, type, entity_id (SAML) or issuer (OIDC), errors
    assert "url" in scan_data, f"saml_scan_json missing 'url' key: {scan_data}"
    assert "type" in scan_data, f"saml_scan_json missing 'type' key: {scan_data}"
    assert "errors" in scan_data, f"saml_scan_json missing 'errors' key: {scan_data}"
    # SAML target: entity_id required
    assert "entity_id" in scan_data, f"saml_scan_json missing 'entity_id' key: {scan_data}"


def test_saml_scan_json_oidc_structure():
    """SAML-05: OIDC saml_scan_json must contain 'issuer' key instead of 'entity_id'."""
    with patch("quirk.scanner.saml_scanner.LXML_AVAILABLE", True), \
         patch("quirk.scanner.saml_scanner._fetch_metadata", return_value=SAMPLE_OIDC_DISCOVERY_JSON):
        result = scan_saml_targets(["https://auth.chaos.local/.well-known/openid-configuration"])
    assert len(result) > 0
    ep = result[0]
    scan_data = json.loads(ep.saml_scan_json)
    assert "issuer" in scan_data, f"OIDC saml_scan_json missing 'issuer' key: {scan_data}"
    assert scan_data.get("type") == "oidc", f"OIDC scan_data type must be 'oidc': {scan_data}"


# ---------------------------------------------------------------------------
# SAML-06: Chaos lab integration (SKIPPED unless QUIRK_INTEGRATION_TESTS=1)
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.skipif(
    not os.environ.get("QUIRK_INTEGRATION_TESTS"),
    reason="Set QUIRK_INTEGRATION_TESTS=1 to run integration tests against chaos lab"
)
def test_chaos_lab_integration():
    """SAML-06: Full integration test against SimpleSAMLphp chaos lab at localhost:8080.

    Requires:
    - docker compose --profile saml up -d
    - QUIRK_INTEGRATION_TESTS=1 env variable set
    - RSA-1024 signing cert pre-baked in SimpleSAMLphp container

    Assertions:
    - At least one CryptoEndpoint returned
    - At least one endpoint with cert_pubkey_size=1024 (RSA-1024 weak cert)
    - severity CRITICAL implied by key size (D-07)
    """
    result = scan_saml_targets(
        ["http://localhost:8080/simplesaml/saml2/idp/metadata.php"],
        timeout=10,
    )
    assert len(result) > 0, "Integration scan must return at least one CryptoEndpoint"
    key_sizes = [ep.cert_pubkey_size for ep in result]
    assert 1024 in key_sizes, \
        f"Expected RSA-1024 cert in chaos lab results; got cert_pubkey_sizes={key_sizes}"


# ---------------------------------------------------------------------------
# SAML-05 / ISSUE-3: session_start parameter acceptance
# ---------------------------------------------------------------------------

def test_saml_session_start_stamps_all_endpoints():
    """ISSUE-3: scan_saml_targets(session_start=<fixed_dt>) stamps all endpoints with that time.

    RED: scan_saml_targets does not accept session_start yet — TypeError expected.
    """
    from datetime import datetime, timezone

    fixed_dt = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
    expected_naive = datetime(2026, 1, 15, 12, 0, 0)  # tzinfo stripped

    with patch("quirk.scanner.saml_scanner.LXML_AVAILABLE", True), \
         patch("quirk.scanner.saml_scanner._fetch_metadata", return_value=SAMPLE_SAML_METADATA_XML):
        result = scan_saml_targets(["https://idp.chaos.local/metadata"], session_start=fixed_dt)

    assert len(result) > 0, "Expected at least one endpoint"
    for ep in result:
        assert ep.scanned_at == expected_naive, \
            f"Expected scanned_at={expected_naive!r}, got {ep.scanned_at!r}"
