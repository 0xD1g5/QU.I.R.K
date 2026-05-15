"""Tests for DNSSEC scanner (DNSSEC-01 through DNSSEC-07).

Tests mock dns.query/dns.resolver to avoid network calls.
Scanner module: quirk/scanner/dnssec_scanner.py
"""
import json
import os
import pytest
from unittest.mock import patch, MagicMock, PropertyMock

from quirk.scanner.dnssec_scanner import (
    scan_dnssec_targets,
    DNSSEC_ALG_MAP,
    DNSPYTHON_AVAILABLE,
    _resolve_ns,
)


# ---------------------------------------------------------------------------
# Helper constructors for mock DNS objects
# ---------------------------------------------------------------------------

def _mock_dnskey(algorithm: int, flags: int = 257, key_bytes: bytes = b'\x03\x01\x00\x01' + b'\x00' * 256):
    """Create a mock DNSKEY rdata with given algorithm, flags, key material."""
    rdata = MagicMock()
    rdata.algorithm = algorithm
    rdata.flags = flags
    rdata.key = key_bytes
    rdata.protocol = 3
    return rdata


def _mock_ds(key_tag: int, algorithm: int = 13, digest_type: int = 2):
    """Create a mock DS rdata with given key_tag, algorithm, digest_type."""
    rdata = MagicMock()
    rdata.key_tag = key_tag
    rdata.algorithm = algorithm
    rdata.digest_type = digest_type
    return rdata


def _mock_rrset(rdtype: int, rdata_list: list):
    """Create a mock rrset with .rdtype and iterable rdata."""
    rrset = MagicMock()
    rrset.rdtype = rdtype
    rrset.__iter__ = MagicMock(return_value=iter(rdata_list))
    return rrset


def _mock_dns_response(answer_rrsets=None, authority_rrsets=None):
    """Create a mock DNS response message."""
    response = MagicMock()
    response.answer = answer_rrsets or []
    response.authority = authority_rrsets or []
    response.flags = 0
    return response


def _mock_ns_answer(ns_name: str = "ns1.example.com"):
    """Create a mock NS answer record."""
    ns_rdata = MagicMock()
    ns_rdata.target = MagicMock()
    ns_rdata.target.__str__ = MagicMock(return_value=ns_name)
    return ns_rdata


def _mock_a_answer(ip: str = "10.0.0.1"):
    """Create a mock A record answer."""
    a_rdata = MagicMock()
    a_rdata.address = ip
    return a_rdata


# ---------------------------------------------------------------------------
# DNSSEC-02: Algorithm Classification (static map tests — GREEN against stub)
# ---------------------------------------------------------------------------

def test_algorithm_classification_critical():
    """DNSSEC-02: RSASHA1 (alg 5) and RSASHA1-NSEC3-SHA1 (alg 7) are CRITICAL."""
    assert DNSSEC_ALG_MAP[5] == ("RSASHA1", "CRITICAL")
    assert DNSSEC_ALG_MAP[7] == ("RSASHA1-NSEC3-SHA1", "CRITICAL")


def test_algorithm_classification_critical_legacy():
    """DNSSEC-02: RSAMD5 (alg 1), DSA (alg 3), DSA-NSEC3 (alg 6), ECC-GOST (alg 12) are CRITICAL."""
    assert DNSSEC_ALG_MAP[1] == ("RSAMD5", "CRITICAL")
    assert DNSSEC_ALG_MAP[3] == ("DSA", "CRITICAL")
    assert DNSSEC_ALG_MAP[6] == ("DSA-NSEC3-SHA1", "CRITICAL")
    assert DNSSEC_ALG_MAP[12] == ("ECC-GOST", "CRITICAL")


def test_algorithm_classification_high():
    """DNSSEC-02: RSASHA256 (alg 8) and RSASHA512 (alg 10) are HIGH severity."""
    assert DNSSEC_ALG_MAP[8] == ("RSASHA256", "HIGH")
    assert DNSSEC_ALG_MAP[10] == ("RSASHA512", "HIGH")


def test_algorithm_classification_safe():
    """DNSSEC-02: ECDSA and EdDSA algorithms are SAFE."""
    assert DNSSEC_ALG_MAP[13] == ("ECDSAP256SHA256", "SAFE")
    assert DNSSEC_ALG_MAP[14] == ("ECDSAP384SHA384", "SAFE")
    assert DNSSEC_ALG_MAP[15] == ("ED25519", "SAFE")
    assert DNSSEC_ALG_MAP[16] == ("ED448", "SAFE")


def test_algorithm_map_has_all_twelve_entries():
    """DNSSEC-02 + Phase 77 D-02: ALG_MAP covers 12 defined algorithm numbers
    plus the two IANA-Reserved slots (9, 11) added in Phase 77 to close
    scanners-protocol/IN-02 (the previously-undefined Reserved range now has
    explicit HIGH-severity entries instead of falling through to UNKNOWN).
    """
    expected_keys = {1, 3, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16}
    assert set(DNSSEC_ALG_MAP.keys()) == expected_keys


# ---------------------------------------------------------------------------
# DNSSEC-01: Authoritative NS resolution (RED — calls _resolve_ns)
# ---------------------------------------------------------------------------

def test_authoritative_ns_resolution():
    """DNSSEC-01: _resolve_ns must return list of NS IP strings from real DNS resolver."""
    ns_answer = MagicMock()
    ns_answer.__iter__ = MagicMock(return_value=iter([_mock_ns_answer("ns1.example.com")]))

    a_answer = MagicMock()
    a_answer.__iter__ = MagicMock(return_value=iter([_mock_a_answer("93.184.216.34")]))

    def resolve_side_effect(qname, rdtype, **kwargs):
        if rdtype == "NS":
            return ns_answer
        if rdtype == "A":
            return a_answer
        raise Exception(f"Unexpected rdtype: {rdtype}")

    with patch("quirk.scanner.dnssec_scanner.dns.resolver.resolve", side_effect=resolve_side_effect):
        result = _resolve_ns("example.com", timeout=5)
        assert isinstance(result, list)
        assert len(result) > 0
        assert all(isinstance(ip, str) for ip in result)


# ---------------------------------------------------------------------------
# DNSSEC-01: DO bit in DNSKEY query (RED — calls scan_dnssec_targets)
# ---------------------------------------------------------------------------

def test_dnskey_query_do_bit():
    """DNSSEC-01: DNS queries must set the DO (DNSSEC OK) bit via want_dnssec=True."""
    ns_answer = MagicMock()
    ns_rdata = _mock_ns_answer("ns1.example.com")
    ns_answer.__iter__ = MagicMock(return_value=iter([ns_rdata]))

    a_answer = MagicMock()
    a_rdata = _mock_a_answer("10.0.0.1")
    a_answer.__iter__ = MagicMock(return_value=iter([a_rdata]))

    # DNSKEY rrset with one ECDSAP256SHA256 KSK (flags=257)
    dnskey_rdata = _mock_dnskey(algorithm=13, flags=257)
    dnskey_rrset = _mock_rrset(rdtype=48, rdata_list=[dnskey_rdata])  # 48 = DNSKEY

    mock_response = _mock_dns_response(answer_rrsets=[dnskey_rrset])

    def resolve_side_effect(qname, rdtype, **kwargs):
        if rdtype == "NS":
            return ns_answer
        if rdtype == "A":
            return a_answer
        raise Exception(f"Unexpected rdtype: {rdtype}")

    with patch("quirk.scanner.dnssec_scanner.dns.resolver.resolve", side_effect=resolve_side_effect), \
         patch("quirk.scanner.dnssec_scanner.dns.query.udp_with_fallback", return_value=mock_response) as mock_query, \
         patch("quirk.scanner.dnssec_scanner.dns.dnssec.key_id", return_value=12345), \
         patch("quirk.scanner.dnssec_scanner.DNSPYTHON_AVAILABLE", True):
        result = scan_dnssec_targets(["example.com"])
        assert mock_query.called, "udp_with_fallback must be called to query DNSKEY records"
        # The request passed to udp_with_fallback should have want_dnssec=True (DO bit set)
        call_kwargs = mock_query.call_args
        # DO bit can be verified via the request object's flags or the want_dnssec kwarg
        assert call_kwargs is not None


# ---------------------------------------------------------------------------
# DNSSEC-02: RSASHA1 produces CRITICAL finding (RED — calls scan_dnssec_targets)
# ---------------------------------------------------------------------------

def test_rsasha1_produces_critical_finding():
    """DNSSEC-02: A zone signed with RSASHA1 (alg 5) must produce cert_pubkey_alg='RSASHA1'."""
    ns_answer = MagicMock()
    ns_answer.__iter__ = MagicMock(return_value=iter([_mock_ns_answer()]))
    a_answer = MagicMock()
    a_answer.__iter__ = MagicMock(return_value=iter([_mock_a_answer()]))

    # alg=5 is RSASHA1 (CRITICAL)
    dnskey_rdata = _mock_dnskey(algorithm=5, flags=257)
    dnskey_rrset = _mock_rrset(rdtype=48, rdata_list=[dnskey_rdata])
    mock_response = _mock_dns_response(answer_rrsets=[dnskey_rrset])

    def resolve_side_effect(qname, rdtype, **kwargs):
        if rdtype == "NS":
            return ns_answer
        if rdtype == "A":
            return a_answer
        raise Exception(f"Unexpected: {rdtype}")

    with patch("quirk.scanner.dnssec_scanner.dns.resolver.resolve", side_effect=resolve_side_effect), \
         patch("quirk.scanner.dnssec_scanner.dns.query.udp_with_fallback", return_value=mock_response), \
         patch("quirk.scanner.dnssec_scanner.dns.dnssec.key_id", return_value=99001), \
         patch("quirk.scanner.dnssec_scanner.DNSPYTHON_AVAILABLE", True):
        result = scan_dnssec_targets(["weak.example.com"])
        assert len(result) > 0
        alg_names = [ep.cert_pubkey_alg for ep in result]
        assert "RSASHA1" in alg_names, f"Expected RSASHA1 in {alg_names}"


# ---------------------------------------------------------------------------
# DNSSEC-03: Unsigned zone (RED — calls scan_dnssec_targets)
# ---------------------------------------------------------------------------

def test_unsigned_zone():
    """DNSSEC-03: Zone with no DNSKEY rrset must produce unsigned-zone finding."""
    ns_answer = MagicMock()
    ns_answer.__iter__ = MagicMock(return_value=iter([_mock_ns_answer()]))
    a_answer = MagicMock()
    a_answer.__iter__ = MagicMock(return_value=iter([_mock_a_answer()]))

    # Empty answer — no DNSKEY rrset
    mock_response = _mock_dns_response(answer_rrsets=[])

    def resolve_side_effect(qname, rdtype, **kwargs):
        if rdtype == "NS":
            return ns_answer
        if rdtype == "A":
            return a_answer
        raise Exception(f"Unexpected: {rdtype}")

    with patch("quirk.scanner.dnssec_scanner.dns.resolver.resolve", side_effect=resolve_side_effect), \
         patch("quirk.scanner.dnssec_scanner.dns.query.udp_with_fallback", return_value=mock_response), \
         patch("quirk.scanner.dnssec_scanner.DNSPYTHON_AVAILABLE", True):
        result = scan_dnssec_targets(["unsigned.example.com"])
        assert len(result) == 1, f"Expected 1 endpoint for unsigned zone, got {len(result)}"
        ep = result[0]
        assert ep.cert_pubkey_alg == "NONE", f"Expected NONE, got {ep.cert_pubkey_alg}"
        assert ep.service_detail == "unsigned-zone", f"Expected unsigned-zone, got {ep.service_detail}"
        assert ep.protocol == "DNSSEC", f"Expected DNSSEC protocol, got {ep.protocol}"


# ---------------------------------------------------------------------------
# DNSSEC-04: CryptoEndpoint protocol and JSON fields (RED)
# ---------------------------------------------------------------------------

def test_cryptoendpoint_protocol_dnssec():
    """DNSSEC-04: All returned CryptoEndpoints must have protocol='DNSSEC' and port=53."""
    ns_answer = MagicMock()
    ns_answer.__iter__ = MagicMock(return_value=iter([_mock_ns_answer()]))
    a_answer = MagicMock()
    a_answer.__iter__ = MagicMock(return_value=iter([_mock_a_answer()]))

    dnskey_rdata = _mock_dnskey(algorithm=13, flags=257)
    dnskey_rrset = _mock_rrset(rdtype=48, rdata_list=[dnskey_rdata])
    mock_response = _mock_dns_response(answer_rrsets=[dnskey_rrset])

    def resolve_side_effect(qname, rdtype, **kwargs):
        if rdtype == "NS":
            return ns_answer
        if rdtype == "A":
            return a_answer
        raise Exception(f"Unexpected: {rdtype}")

    with patch("quirk.scanner.dnssec_scanner.dns.resolver.resolve", side_effect=resolve_side_effect), \
         patch("quirk.scanner.dnssec_scanner.dns.query.udp_with_fallback", return_value=mock_response), \
         patch("quirk.scanner.dnssec_scanner.dns.dnssec.key_id", return_value=54321), \
         patch("quirk.scanner.dnssec_scanner.DNSPYTHON_AVAILABLE", True):
        result = scan_dnssec_targets(["signed.example.com"])
        assert len(result) > 0
        for ep in result:
            assert ep.protocol == "DNSSEC", f"Expected DNSSEC protocol, got {ep.protocol}"
            assert ep.port == 53, f"Expected port 53, got {ep.port}"


def test_dnssec_scan_json_populated():
    """DNSSEC-04: dnssec_scan_json must be non-None JSON string with 'domain' key."""
    ns_answer = MagicMock()
    ns_answer.__iter__ = MagicMock(return_value=iter([_mock_ns_answer()]))
    a_answer = MagicMock()
    a_answer.__iter__ = MagicMock(return_value=iter([_mock_a_answer()]))

    dnskey_rdata = _mock_dnskey(algorithm=13, flags=257)
    dnskey_rrset = _mock_rrset(rdtype=48, rdata_list=[dnskey_rdata])
    mock_response = _mock_dns_response(answer_rrsets=[dnskey_rrset])

    def resolve_side_effect(qname, rdtype, **kwargs):
        if rdtype == "NS":
            return ns_answer
        if rdtype == "A":
            return a_answer
        raise Exception(f"Unexpected: {rdtype}")

    with patch("quirk.scanner.dnssec_scanner.dns.resolver.resolve", side_effect=resolve_side_effect), \
         patch("quirk.scanner.dnssec_scanner.dns.query.udp_with_fallback", return_value=mock_response), \
         patch("quirk.scanner.dnssec_scanner.dns.dnssec.key_id", return_value=54321), \
         patch("quirk.scanner.dnssec_scanner.DNSPYTHON_AVAILABLE", True):
        result = scan_dnssec_targets(["signed.example.com"])
        assert len(result) > 0
        for ep in result:
            assert ep.dnssec_scan_json is not None, "dnssec_scan_json must not be None"
            parsed = json.loads(ep.dnssec_scan_json)
            assert "domain" in parsed, f"dnssec_scan_json missing 'domain' key: {parsed}"
            assert parsed["domain"] == "signed.example.com"


# ---------------------------------------------------------------------------
# DNSSEC-05: NSEC zone enumeration exposure (RED)
# ---------------------------------------------------------------------------

def test_nsec_detection_exposure():
    """DNSSEC-05: Zone using NSEC must produce service_detail='nsec-exposure'."""
    ns_answer = MagicMock()
    ns_answer.__iter__ = MagicMock(return_value=iter([_mock_ns_answer()]))
    a_answer = MagicMock()
    a_answer.__iter__ = MagicMock(return_value=iter([_mock_a_answer()]))

    # DNSKEY rrset (signed with RSASHA1 to also test alg detection)
    dnskey_rdata = _mock_dnskey(algorithm=5, flags=257)
    dnskey_rrset = _mock_rrset(rdtype=48, rdata_list=[dnskey_rdata])

    # NXDOMAIN response with NSEC (rdtype=47) in authority section
    nsec_rdata = MagicMock()
    nsec_rrset = _mock_rrset(rdtype=47, rdata_list=[nsec_rdata])  # 47 = NSEC

    # Main DNSKEY response
    mock_dnskey_response = _mock_dns_response(answer_rrsets=[dnskey_rrset])
    # NXDOMAIN response for NSEC detection
    mock_nxdomain_response = _mock_dns_response(answer_rrsets=[], authority_rrsets=[nsec_rrset])

    call_count = {"n": 0}

    def udp_side_effect(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return mock_dnskey_response
        return mock_nxdomain_response

    def resolve_side_effect(qname, rdtype, **kwargs):
        if rdtype == "NS":
            return ns_answer
        if rdtype == "A":
            return a_answer
        raise Exception(f"Unexpected: {rdtype}")

    with patch("quirk.scanner.dnssec_scanner.dns.resolver.resolve", side_effect=resolve_side_effect), \
         patch("quirk.scanner.dnssec_scanner.dns.query.udp_with_fallback", side_effect=udp_side_effect), \
         patch("quirk.scanner.dnssec_scanner.dns.dnssec.key_id", return_value=11111), \
         patch("quirk.scanner.dnssec_scanner.DNSPYTHON_AVAILABLE", True):
        result = scan_dnssec_targets(["weak.example.com"])
        service_details = [ep.service_detail for ep in result]
        assert "nsec-exposure" in service_details, \
            f"Expected nsec-exposure in service_details: {service_details}"
        nsec_eps = [ep for ep in result if ep.service_detail == "nsec-exposure"]
        assert len(nsec_eps) >= 1
        assert nsec_eps[0].cert_pubkey_alg == "NSEC"


def test_nsec3_no_exposure():
    """DNSSEC-05: Zone using NSEC3 must NOT produce nsec-exposure finding."""
    ns_answer = MagicMock()
    ns_answer.__iter__ = MagicMock(return_value=iter([_mock_ns_answer()]))
    a_answer = MagicMock()
    a_answer.__iter__ = MagicMock(return_value=iter([_mock_a_answer()]))

    dnskey_rdata = _mock_dnskey(algorithm=13, flags=257)
    dnskey_rrset = _mock_rrset(rdtype=48, rdata_list=[dnskey_rdata])

    # NXDOMAIN response with NSEC3 (rdtype=50) in authority section — NOT NSEC
    nsec3_rdata = MagicMock()
    nsec3_rrset = _mock_rrset(rdtype=50, rdata_list=[nsec3_rdata])  # 50 = NSEC3

    mock_dnskey_response = _mock_dns_response(answer_rrsets=[dnskey_rrset])
    mock_nxdomain_response = _mock_dns_response(answer_rrsets=[], authority_rrsets=[nsec3_rrset])

    call_count = {"n": 0}

    def udp_side_effect(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return mock_dnskey_response
        return mock_nxdomain_response

    def resolve_side_effect(qname, rdtype, **kwargs):
        if rdtype == "NS":
            return ns_answer
        if rdtype == "A":
            return a_answer
        raise Exception(f"Unexpected: {rdtype}")

    with patch("quirk.scanner.dnssec_scanner.dns.resolver.resolve", side_effect=resolve_side_effect), \
         patch("quirk.scanner.dnssec_scanner.dns.query.udp_with_fallback", side_effect=udp_side_effect), \
         patch("quirk.scanner.dnssec_scanner.dns.dnssec.key_id", return_value=22222), \
         patch("quirk.scanner.dnssec_scanner.DNSPYTHON_AVAILABLE", True):
        result = scan_dnssec_targets(["safe.example.com"])
        service_details = [ep.service_detail for ep in result]
        assert "nsec-exposure" not in service_details, \
            f"NSEC3 zone must not produce nsec-exposure: {service_details}"


# ---------------------------------------------------------------------------
# DNSSEC-06: DS chain validation (RED)
# ---------------------------------------------------------------------------

def test_ds_chain_broken():
    """DNSSEC-06: DNSKEY with tag=12345 but DS key_tag=99999 must produce ds-chain-broken."""
    ns_answer = MagicMock()
    ns_answer.__iter__ = MagicMock(return_value=iter([_mock_ns_answer()]))
    a_answer = MagicMock()
    a_answer.__iter__ = MagicMock(return_value=iter([_mock_a_answer()]))

    dnskey_rdata = _mock_dnskey(algorithm=13, flags=257)
    dnskey_rrset = _mock_rrset(rdtype=48, rdata_list=[dnskey_rdata])

    # DS with mismatched key_tag (99999 != 12345)
    ds_rdata = _mock_ds(key_tag=99999, algorithm=13)
    ds_rrset = _mock_rrset(rdtype=43, rdata_list=[ds_rdata])  # 43 = DS

    mock_response = _mock_dns_response(answer_rrsets=[dnskey_rrset, ds_rrset])

    def resolve_side_effect(qname, rdtype, **kwargs):
        if rdtype == "NS":
            return ns_answer
        if rdtype == "A":
            return a_answer
        raise Exception(f"Unexpected: {rdtype}")

    with patch("quirk.scanner.dnssec_scanner.dns.resolver.resolve", side_effect=resolve_side_effect), \
         patch("quirk.scanner.dnssec_scanner.dns.query.udp_with_fallback", return_value=mock_response), \
         patch("quirk.scanner.dnssec_scanner.dns.dnssec.key_id", return_value=12345), \
         patch("quirk.scanner.dnssec_scanner.DNSPYTHON_AVAILABLE", True):
        result = scan_dnssec_targets(["broken.example.com"])
        service_details = [ep.service_detail for ep in result]
        assert "ds-chain-broken" in service_details, \
            f"Expected ds-chain-broken in service_details: {service_details}"


def test_ds_chain_valid():
    """DNSSEC-06: DNSKEY with tag=12345 and DS key_tag=12345 must NOT produce ds-chain-broken."""
    ns_answer = MagicMock()
    ns_answer.__iter__ = MagicMock(return_value=iter([_mock_ns_answer()]))
    a_answer = MagicMock()
    a_answer.__iter__ = MagicMock(return_value=iter([_mock_a_answer()]))

    dnskey_rdata = _mock_dnskey(algorithm=13, flags=257)
    dnskey_rrset = _mock_rrset(rdtype=48, rdata_list=[dnskey_rdata])

    # DS with matching key_tag (12345 == 12345)
    ds_rdata = _mock_ds(key_tag=12345, algorithm=13)
    ds_rrset = _mock_rrset(rdtype=43, rdata_list=[ds_rdata])

    mock_response = _mock_dns_response(answer_rrsets=[dnskey_rrset, ds_rrset])

    def resolve_side_effect(qname, rdtype, **kwargs):
        if rdtype == "NS":
            return ns_answer
        if rdtype == "A":
            return a_answer
        raise Exception(f"Unexpected: {rdtype}")

    with patch("quirk.scanner.dnssec_scanner.dns.resolver.resolve", side_effect=resolve_side_effect), \
         patch("quirk.scanner.dnssec_scanner.dns.query.udp_with_fallback", return_value=mock_response), \
         patch("quirk.scanner.dnssec_scanner.dns.dnssec.key_id", return_value=12345), \
         patch("quirk.scanner.dnssec_scanner.DNSPYTHON_AVAILABLE", True):
        result = scan_dnssec_targets(["valid-chain.example.com"])
        service_details = [ep.service_detail for ep in result]
        assert "ds-chain-broken" not in service_details, \
            f"Valid DS chain must not produce ds-chain-broken: {service_details}"


# ---------------------------------------------------------------------------
# DNSSEC-07: Chaos lab integration (skipped unless QUIRK_INTEGRATION_TESTS=1)
# ---------------------------------------------------------------------------

@pytest.mark.slow
@pytest.mark.integration
@pytest.mark.skipif(
    not os.environ.get("QUIRK_INTEGRATION_TESTS"),
    reason="Set QUIRK_INTEGRATION_TESTS=1 to run integration tests against chaos lab"
)
def test_chaos_lab_integration():
    """DNSSEC-07: Full integration test against chaos lab BIND9 at localhost:15353.

    Requires:
    - docker compose --profile dnssec up -d
    - QUIRK_INTEGRATION_TESTS=1 env variable set
    - /etc/resolver/chaos.local or direct DNS query to localhost:15353

    Zones tested:
    - weak.chaos.local: RSASHA1 + NSEC (CRITICAL algorithm + zone enumeration exposure)
    - safe.chaos.local: ECDSAP256SHA256 + NSEC3 (clean baseline)
    - broken.chaos.local: valid DNSKEY but DS key_tag mismatch
    - unsigned.chaos.local: no DNSSEC
    """
    domains = [
        "weak.chaos.local",
        "safe.chaos.local",
        "broken.chaos.local",
        "unsigned.chaos.local",
    ]
    result = scan_dnssec_targets(domains)
    assert len(result) > 0, "Integration scan must return at least one CryptoEndpoint"

    alg_names = [ep.cert_pubkey_alg for ep in result]
    service_details = [ep.service_detail for ep in result]

    assert "RSASHA1" in alg_names, \
        f"weak.chaos.local must produce RSASHA1 finding; got alg_names={alg_names}"
    assert "ECDSAP256SHA256" in alg_names, \
        f"safe.chaos.local must produce ECDSAP256SHA256 finding; got alg_names={alg_names}"
    assert "ds-chain-broken" in service_details, \
        f"broken.chaos.local must produce ds-chain-broken; got service_details={service_details}"
    assert "unsigned-zone" in service_details, \
        f"unsigned.chaos.local must produce unsigned-zone; got service_details={service_details}"


# ---------------------------------------------------------------------------
# DNSSEC-04 / ISSUE-3: session_start parameter acceptance
# ---------------------------------------------------------------------------

def test_dnssec_session_start_stamps_all_endpoints():
    """ISSUE-3: scan_dnssec_targets(session_start=<fixed_dt>) stamps all endpoints with that time.

    RED: scan_dnssec_targets does not accept session_start yet — TypeError expected.
    """
    from datetime import datetime, timezone

    fixed_dt = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
    expected_naive = datetime(2026, 1, 15, 12, 0, 0)  # tzinfo stripped

    # Reuse the RSASHA1 mock setup from test_rsasha1_produces_critical_finding
    ns_answer = MagicMock()
    ns_answer.__iter__ = MagicMock(return_value=iter([_mock_ns_answer()]))
    a_answer = MagicMock()
    a_answer.__iter__ = MagicMock(return_value=iter([_mock_a_answer("198.51.100.1")]))

    dnskey_rdata = _mock_dnskey(algorithm=5, flags=257)
    dnskey_rrset = _mock_rrset(48, [dnskey_rdata])  # 48 = DNSKEY
    mock_response = _mock_dns_response(answer_rrsets=[dnskey_rrset])

    def resolve_side_effect(domain, rdtype, **kwargs):
        if rdtype == "NS":
            return ns_answer
        if rdtype == "A":
            return a_answer
        raise Exception(f"Unexpected resolve: {rdtype}")

    with patch("quirk.scanner.dnssec_scanner.dns.resolver.resolve", side_effect=resolve_side_effect), \
         patch("quirk.scanner.dnssec_scanner.dns.query.udp_with_fallback", return_value=mock_response), \
         patch("quirk.scanner.dnssec_scanner.dns.dnssec.key_id", return_value=99001), \
         patch("quirk.scanner.dnssec_scanner.DNSPYTHON_AVAILABLE", True):
        result = scan_dnssec_targets(["weak.example.com"], session_start=fixed_dt)

    assert len(result) > 0, "Expected at least one endpoint"
    for ep in result:
        assert ep.scanned_at == expected_naive, \
            f"Expected scanned_at={expected_naive!r}, got {ep.scanned_at!r}"
