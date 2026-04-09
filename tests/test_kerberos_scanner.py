"""Tests for Kerberos scanner (KERB-01 through KERB-05).

Tests mock impacket sendReceive and ldap3 to avoid network calls.
Scanner module: quirk/scanner/kerberos_scanner.py
"""

import json
import os
import pytest
from unittest.mock import patch, MagicMock, PropertyMock

from quirk.scanner.kerberos_scanner import (
    scan_kerberos_targets,
    KERBEROS_ETYPE_MAP,
    IMPACKET_AVAILABLE,
    ALL_ETYPES,
    _derive_realm,
)


# ---------------------------------------------------------------------------
# Section 1: Static KERBEROS_ETYPE_MAP tests (PASS against stub)
# ---------------------------------------------------------------------------

def test_etype_map_des_critical():
    """KERB-02: DES etypes (1, 2, 3) must map to CRITICAL severity."""
    assert KERBEROS_ETYPE_MAP[1][1] == "CRITICAL", f"etype 1 severity: {KERBEROS_ETYPE_MAP[1][1]}"
    assert KERBEROS_ETYPE_MAP[2][1] == "CRITICAL", f"etype 2 severity: {KERBEROS_ETYPE_MAP[2][1]}"
    assert KERBEROS_ETYPE_MAP[3][1] == "CRITICAL", f"etype 3 severity: {KERBEROS_ETYPE_MAP[3][1]}"


def test_etype_map_rc4_high():
    """KERB-02: RC4-HMAC (etype 23) must map to ('rc4-hmac', 'HIGH')."""
    assert KERBEROS_ETYPE_MAP[23] == ("rc4-hmac", "HIGH")


def test_etype_map_aes256_safe():
    """KERB-02: AES-256 etypes (18 and 20) must have SAFE severity."""
    assert KERBEROS_ETYPE_MAP[18][1] == "SAFE", f"etype 18 severity: {KERBEROS_ETYPE_MAP[18][1]}"
    assert KERBEROS_ETYPE_MAP[20][1] == "SAFE", f"etype 20 severity: {KERBEROS_ETYPE_MAP[20][1]}"


def test_etype_map_aes128_high():
    """KERB-02 / D-11: AES-128 (etype 17) maps to HIGH -- Grover reduces to ~64-bit."""
    assert KERBEROS_ETYPE_MAP[17] == ("aes128-cts-hmac-sha1-96", "HIGH")


def test_etype_map_completeness():
    """KERB-02: KERBEROS_ETYPE_MAP must have exactly 7 entries covering known etypes."""
    assert len(KERBEROS_ETYPE_MAP) == 7
    expected_keys = {1, 2, 3, 17, 18, 20, 23}
    assert set(KERBEROS_ETYPE_MAP.keys()) == expected_keys


def test_etype_map_unknown_default():
    """KERB-02 / D-12: Unknown etypes (e.g., 99) are not in KERBEROS_ETYPE_MAP; handled at runtime."""
    assert KERBEROS_ETYPE_MAP.get(99) is None


# ---------------------------------------------------------------------------
# Section 2: _derive_realm tests (PASS against stub -- pure logic implemented)
# ---------------------------------------------------------------------------

def test_derive_realm_fqdn():
    """D-06: FQDN with multiple labels returns domain portion uppercased."""
    assert _derive_realm("dc01.corp.local") == "CORP.LOCAL"


def test_derive_realm_two_labels():
    """D-06: Two-label hostname returns both labels uppercased."""
    assert _derive_realm("corp.local") == "CORP.LOCAL"


def test_derive_realm_ip_address():
    """D-06: IPv4 address has no domain portion -- return uppercased as-is."""
    assert _derive_realm("10.0.0.1") == "10.0.0.1"


def test_derive_realm_single_label():
    """D-06: Single-label hostname returns uppercased hostname."""
    assert _derive_realm("localhost") == "LOCALHOST"


# ---------------------------------------------------------------------------
# Section 3: Mock helper constructors (for functional tests)
# ---------------------------------------------------------------------------

def _mock_etype_info2_padata(etypes: list):
    """Create a mock METHOD_DATA containing PA-ETYPE-INFO2 with given etype list.

    Returns bytes that decoder.decode can parse, or a MagicMock that
    simulates the decoded structure.
    """
    # Build mock padata entry
    padata = MagicMock()
    padata.__getitem__ = MagicMock(side_effect=lambda k: {
        'padata-type': 19,  # PA_ETYPE_INFO2
        'padata-value': b'mock',
    }[k])
    return padata


def _mock_kerberos_error(error_code: int, etypes: list):
    """Create a mock KerberosError with given error code and etype list in e-data.

    Used by tests to simulate KDC_ERR_PREAUTH_REQUIRED response.
    """
    error = MagicMock()
    error.getErrorCode.return_value = error_code
    error_pkt = MagicMock()
    error.getErrorPacket.return_value = error_pkt
    return error


# ---------------------------------------------------------------------------
# Section 4: KERB-01 AS-REQ Probe tests (FAIL -- NotImplementedError expected)
# ---------------------------------------------------------------------------

def test_as_req_probe_returns_etypes():
    """KERB-01: AS-REQ probe returns etypes from PA-ETYPE-INFO2.

    RED test -- scan_kerberos_targets raises NotImplementedError until Plan 02.
    Patches IMPACKET_AVAILABLE=True to exercise the stub code path.
    """
    import quirk.scanner.kerberos_scanner as kmod
    with patch.object(kmod, "IMPACKET_AVAILABLE", True):
        with pytest.raises(NotImplementedError, match="stub"):
            scan_kerberos_targets(["localhost"], timeout=5)


def test_as_req_tcp_primary():
    """KERB-01: TCP is used as primary transport (sendReceive/socket called over port 88).

    RED test -- scan_kerberos_targets raises NotImplementedError until Plan 02.
    """
    import quirk.scanner.kerberos_scanner as kmod
    with patch.object(kmod, "IMPACKET_AVAILABLE", True):
        with pytest.raises(NotImplementedError, match="stub"):
            scan_kerberos_targets(["dc01.corp.local"], timeout=5)


def test_as_req_udp_fallback():
    """KERB-01: When TCP fails (socket.error), UDP fallback is attempted.

    RED test -- scanner must attempt UDP when TCP sendReceive raises socket.error.
    Currently raises NotImplementedError until Plan 02.
    """
    import quirk.scanner.kerberos_scanner as kmod
    with patch.object(kmod, "IMPACKET_AVAILABLE", True):
        with pytest.raises(NotImplementedError, match="stub"):
            scan_kerberos_targets(["10.0.0.1"], timeout=5)


def test_as_req_both_fail_graceful():
    """KERB-01: When both TCP and UDP fail, returns CryptoEndpoint with service_detail='kerberos-unreachable'.

    RED test -- raises NotImplementedError until Plan 02 implements graceful failure.
    """
    import quirk.scanner.kerberos_scanner as kmod
    with patch.object(kmod, "IMPACKET_AVAILABLE", True):
        with pytest.raises(NotImplementedError, match="stub"):
            scan_kerberos_targets(["unreachable.host"], timeout=1)


def test_as_req_no_preauth_response():
    """KERB-01: If KDC returns AS-REP (no preauth required -- unexpected), returns empty list for target.

    RED test -- raises NotImplementedError until Plan 02.
    """
    import quirk.scanner.kerberos_scanner as kmod
    with patch.object(kmod, "IMPACKET_AVAILABLE", True):
        with pytest.raises(NotImplementedError, match="stub"):
            scan_kerberos_targets(["no-preauth.corp.local"], timeout=5)


# ---------------------------------------------------------------------------
# Section 5: KERB-02 Etype Classification tests (FAIL -- NotImplementedError expected)
# ---------------------------------------------------------------------------

def test_etype_classifier_produces_endpoints():
    """KERB-02: For each etype returned by probe, a CryptoEndpoint is produced with cert_pubkey_alg set.

    RED test -- raises NotImplementedError until Plan 02.
    """
    import quirk.scanner.kerberos_scanner as kmod
    with patch.object(kmod, "IMPACKET_AVAILABLE", True):
        with pytest.raises(NotImplementedError, match="stub"):
            scan_kerberos_targets(["dc01.corp.local"], timeout=5)


def test_etype_unknown_gets_medium():
    """KERB-02 / D-12: An etype not in KERBEROS_ETYPE_MAP (e.g., 99) produces severity='MEDIUM'.

    RED test -- raises NotImplementedError until Plan 02 implements classification logic.
    """
    import quirk.scanner.kerberos_scanner as kmod
    with patch.object(kmod, "IMPACKET_AVAILABLE", True):
        with pytest.raises(NotImplementedError, match="stub"):
            scan_kerberos_targets(["dc01.corp.local"], timeout=5)


# ---------------------------------------------------------------------------
# Section 6: KERB-03 LDAP Probe tests (FAIL -- NotImplementedError expected)
# ---------------------------------------------------------------------------

def test_ldap_graceful_degrade():
    """KERB-03: When LDAP port 389 is unreachable, scanner logs warning and continues without crashing.

    RED test -- raises NotImplementedError until Plan 02 implements LDAP probing.
    """
    import quirk.scanner.kerberos_scanner as kmod
    with patch.object(kmod, "IMPACKET_AVAILABLE", True):
        with pytest.raises(NotImplementedError, match="stub"):
            scan_kerberos_targets(["no-ldap.corp.local"], timeout=1)


def test_ldap_anonymous_bind_rejected():
    """KERB-03: When LDAP returns auth error (anonymous bind rejected), scanner logs and continues.

    RED test -- raises NotImplementedError until Plan 02.
    """
    import quirk.scanner.kerberos_scanner as kmod
    with patch.object(kmod, "IMPACKET_AVAILABLE", True):
        with pytest.raises(NotImplementedError, match="stub"):
            scan_kerberos_targets(["auth-reject.corp.local"], timeout=5)


def test_ldap_success_reads_enc_types():
    """KERB-03: When anonymous LDAP bind succeeds and msDS-SupportedEncryptionTypes is readable,
    value is included in kerberos_scan_json.

    RED test -- raises NotImplementedError until Plan 02.
    """
    import quirk.scanner.kerberos_scanner as kmod
    with patch.object(kmod, "IMPACKET_AVAILABLE", True):
        with pytest.raises(NotImplementedError, match="stub"):
            scan_kerberos_targets(["ldap-ok.corp.local"], timeout=5)


# ---------------------------------------------------------------------------
# Section 7: KERB-04 Database/CBOM Integration tests (FAIL -- NotImplementedError expected)
# ---------------------------------------------------------------------------

def test_kerberos_db_row():
    """KERB-04: Each returned CryptoEndpoint has protocol='KERBEROS', port=88, and kerberos_scan_json populated.

    RED test -- raises NotImplementedError until Plan 02.
    """
    import quirk.scanner.kerberos_scanner as kmod
    with patch.object(kmod, "IMPACKET_AVAILABLE", True):
        with pytest.raises(NotImplementedError, match="stub"):
            scan_kerberos_targets(["dc01.corp.local"], timeout=5)


def test_kerberos_scan_json_structure():
    """KERB-04: kerberos_scan_json field is valid JSON containing at minimum: realm, etypes, ldap_status.

    RED test -- raises NotImplementedError until Plan 02.
    """
    import quirk.scanner.kerberos_scanner as kmod
    with patch.object(kmod, "IMPACKET_AVAILABLE", True):
        with pytest.raises(NotImplementedError, match="stub"):
            scan_kerberos_targets(["dc01.corp.local"], timeout=5)


# ---------------------------------------------------------------------------
# Section 8: KERB-05 Integration / Chaos Lab test (SKIPPED unless env var set)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    not os.environ.get("QUIRK_KERBEROS_INTEGRATION"),
    reason="Set QUIRK_KERBEROS_INTEGRATION=1 to run against local Samba DC chaos lab",
)
def test_samba_dc_integration():
    """KERB-05: Against a running Samba DC, scan returns RC4 etype 23 in results.

    Requires: QUIRK_KERBEROS_INTEGRATION=1 env var and running chaos lab (kerberos profile).
    """
    results = scan_kerberos_targets(["127.0.0.1"], timeout=10)
    assert isinstance(results, list), "scan_kerberos_targets must return a list"
    assert len(results) > 0, "Expected at least one CryptoEndpoint from Samba DC"
    etype_names = [ep.cert_pubkey_alg for ep in results]
    assert "rc4-hmac" in etype_names, f"Expected rc4-hmac in results, got {etype_names}"
    for ep in results:
        assert ep.protocol == "KERBEROS", f"Expected KERBEROS protocol, got {ep.protocol}"
        assert ep.port == 88, f"Expected port 88, got {ep.port}"
        scan_data = json.loads(ep.kerberos_scan_json)
        assert "realm" in scan_data, "kerberos_scan_json must contain 'realm' key"
        assert "etypes" in scan_data, "kerberos_scan_json must contain 'etypes' key"
        assert "ldap_status" in scan_data, "kerberos_scan_json must contain 'ldap_status' key"


# ---------------------------------------------------------------------------
# Section 9: Import guard test (PASS)
# ---------------------------------------------------------------------------

def test_import_guard_returns_empty_when_unavailable():
    """D-04: When IMPACKET_AVAILABLE is False, scan_kerberos_targets returns empty list."""
    import quirk.scanner.kerberos_scanner as kmod
    with patch.object(kmod, "IMPACKET_AVAILABLE", False):
        result = scan_kerberos_targets(["localhost"])
        assert result == [], f"Expected [] when impacket unavailable, got {result}"
