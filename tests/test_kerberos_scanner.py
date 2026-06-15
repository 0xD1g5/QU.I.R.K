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
# Section 3: Mock helper utilities (for functional tests)
# ---------------------------------------------------------------------------

def _make_mock_padata_entry(ptype, pvalue_bytes=b'mock'):
    """Create a mock padata entry with given type and value bytes."""
    entry = MagicMock()
    entry.__getitem__ = MagicMock(side_effect=lambda k: {
        'padata-type': ptype,
        'padata-value': pvalue_bytes,
    }[k])
    return entry


def _make_mock_etype_info2_entry(etype_int):
    """Create a mock ETYPE_INFO2 entry with a single etype."""
    entry = MagicMock()
    entry.__getitem__ = MagicMock(side_effect=lambda k: etype_int if k == 'etype' else None)
    return entry


def _patch_probe_kdc(kmod, etypes):
    """Return a context manager that patches _probe_kdc to return given etypes."""
    return patch.object(kmod, '_probe_kdc', return_value=etypes)


def _patch_probe_kdc_raises(kmod, exc):
    """Return a context manager that patches _probe_kdc to raise given exception."""
    return patch.object(kmod, '_probe_kdc', side_effect=exc)


def _patch_probe_kdc_udp(kmod, etypes):
    """Return a context manager that patches _probe_kdc_udp to return given etypes."""
    return patch.object(kmod, '_probe_kdc_udp', return_value=etypes)


def _patch_probe_ldap(kmod, result):
    """Return a context manager that patches _probe_ldap_anon to return given dict."""
    return patch.object(kmod, '_probe_ldap_anon', return_value=result)


# ---------------------------------------------------------------------------
# Section 4: KERB-01 AS-REQ Probe tests (GREEN -- real behavior)
# ---------------------------------------------------------------------------

def test_as_req_probe_returns_etypes():
    """KERB-01: AS-REQ probe returns etypes from PA-ETYPE-INFO2.

    Mocks _probe_kdc to return [18, 23]; verifies scan_kerberos_targets produces
    CryptoEndpoints with protocol=KERBEROS and correct cert_pubkey_alg values.
    """
    import quirk.scanner.kerberos_scanner as kmod
    ldap_ok = {"ldap_status": "ok", "msDS-SupportedEncryptionTypes": None}
    with patch.object(kmod, "IMPACKET_AVAILABLE", True), \
         _patch_probe_kdc(kmod, [18, 23]), \
         _patch_probe_ldap(kmod, ldap_ok):
        results = scan_kerberos_targets(["localhost"], timeout=5)
    assert len(results) == 2
    alg_names = {ep.cert_pubkey_alg for ep in results}
    assert "aes256-cts-hmac-sha1-96" in alg_names
    assert "rc4-hmac" in alg_names
    for ep in results:
        assert ep.protocol == "KERBEROS"
        assert ep.port == 88


def test_as_req_tcp_primary():
    """KERB-01: TCP (_probe_kdc) is used as primary transport before UDP fallback.

    Verifies _probe_kdc is called and its result is used when no exception occurs.
    """
    import quirk.scanner.kerberos_scanner as kmod
    ldap_ok = {"ldap_status": "skipped"}
    with patch.object(kmod, "IMPACKET_AVAILABLE", True), \
         _patch_probe_kdc(kmod, [23]) as mock_tcp, \
         _patch_probe_kdc_udp(kmod, []) as mock_udp, \
         _patch_probe_ldap(kmod, ldap_ok):
        results = scan_kerberos_targets(["dc01.corp.local"], timeout=5)
    mock_tcp.assert_called_once()
    mock_udp.assert_not_called()
    assert any(ep.cert_pubkey_alg == "rc4-hmac" for ep in results)


def test_as_req_udp_fallback():
    """KERB-01: When TCP fails (socket.error), UDP fallback is attempted.

    _probe_kdc raises socket.error; _probe_kdc_udp is then called and its
    etypes are used.
    """
    import quirk.scanner.kerberos_scanner as kmod
    ldap_ok = {"ldap_status": "skipped"}
    with patch.object(kmod, "IMPACKET_AVAILABLE", True), \
         _patch_probe_kdc_raises(kmod, OSError("Connection refused")) as mock_tcp, \
         _patch_probe_kdc_udp(kmod, [23]) as mock_udp, \
         _patch_probe_ldap(kmod, ldap_ok):
        results = scan_kerberos_targets(["10.0.0.1"], timeout=5)
    mock_tcp.assert_called_once()
    mock_udp.assert_called_once()
    assert any(ep.cert_pubkey_alg == "rc4-hmac" for ep in results)


def test_as_req_both_fail_graceful():
    """KERB-01: When both TCP and UDP fail, returns CryptoEndpoint with
    service_detail='kerberos-unreachable' instead of raising an exception.
    """
    import quirk.scanner.kerberos_scanner as kmod
    ldap_skip = {"ldap_status": "skipped"}
    with patch.object(kmod, "IMPACKET_AVAILABLE", True), \
         _patch_probe_kdc_raises(kmod, OSError("TCP timeout")), \
         _patch_probe_kdc_udp(kmod, None) as mock_udp_fail, \
         _patch_probe_ldap(kmod, ldap_skip):
        # UDP returning None simulates both failing -- override to raise too
        with patch.object(kmod, '_probe_kdc_udp', side_effect=OSError("UDP timeout")):
            results = scan_kerberos_targets(["unreachable.host"], timeout=1)
    assert len(results) == 1
    assert results[0].service_detail == "kerberos-unreachable"
    assert results[0].cert_pubkey_alg == "kerberos-unreachable"
    assert results[0].protocol == "KERBEROS"
    assert results[0].port == 88


def test_as_req_both_fail_surfaces_tcp_error():
    """IN-01 (Phase 130): when both TCP and UDP fail, the unreachable endpoint
    must surface the TCP failure detail in scan_error for operator diagnostics,
    rather than capturing it as dead state. Mirrors the codesign scanner's
    error-endpoint pattern (sanitized via safe_str).
    """
    import quirk.scanner.kerberos_scanner as kmod
    ldap_skip = {"ldap_status": "skipped"}
    with patch.object(kmod, "IMPACKET_AVAILABLE", True), \
         _patch_probe_kdc_raises(kmod, OSError("TCP connection refused")), \
         _patch_probe_ldap(kmod, ldap_skip):
        with patch.object(kmod, '_probe_kdc_udp', side_effect=OSError("UDP timeout")):
            results = scan_kerberos_targets(["unreachable.host"], timeout=1)
    assert len(results) == 1
    ep = results[0]
    assert ep.service_detail == "kerberos-unreachable"
    assert ep.scan_error and "TCP connection refused" in ep.scan_error, (
        f"unreachable endpoint must carry the TCP failure detail in scan_error; "
        f"got {ep.scan_error!r}"
    )
    assert ep.scan_error_category == "exception"


def test_as_req_no_preauth_response():
    """KERB-01: If KDC returns AS-REP (no preauth required -- unexpected),
    scan_kerberos_targets returns a placeholder endpoint with no etype endpoints.
    """
    import quirk.scanner.kerberos_scanner as kmod
    ldap_skip = {"ldap_status": "skipped"}
    with patch.object(kmod, "IMPACKET_AVAILABLE", True), \
         _patch_probe_kdc(kmod, []), \
         _patch_probe_ldap(kmod, ldap_skip):
        results = scan_kerberos_targets(["no-preauth.corp.local"], timeout=5)
    # Expect one placeholder endpoint (no preauth)
    assert len(results) == 1
    assert results[0].service_detail == "kerberos-no-preauth"


# ---------------------------------------------------------------------------
# Section 5: KERB-02 Etype Classification tests (GREEN -- real behavior)
# ---------------------------------------------------------------------------

def test_etype_classifier_produces_endpoints():
    """KERB-02: For each etype returned by probe, a CryptoEndpoint is produced
    with cert_pubkey_alg set to the etype name.
    """
    import quirk.scanner.kerberos_scanner as kmod
    ldap_skip = {"ldap_status": "skipped"}
    with patch.object(kmod, "IMPACKET_AVAILABLE", True), \
         _patch_probe_kdc(kmod, [18, 23, 1]), \
         _patch_probe_ldap(kmod, ldap_skip):
        results = scan_kerberos_targets(["dc01.corp.local"], timeout=5)
    assert len(results) == 3
    alg_names = {ep.cert_pubkey_alg for ep in results}
    assert "aes256-cts-hmac-sha1-96" in alg_names
    assert "rc4-hmac" in alg_names
    assert "des-cbc-crc" in alg_names


def test_etype_unknown_gets_medium():
    """KERB-02 / D-12: An etype not in KERBEROS_ETYPE_MAP (e.g., 99) produces
    a CryptoEndpoint with service_detail containing 'MEDIUM'.
    """
    import quirk.scanner.kerberos_scanner as kmod
    ldap_skip = {"ldap_status": "skipped"}
    with patch.object(kmod, "IMPACKET_AVAILABLE", True), \
         _patch_probe_kdc(kmod, [99]), \
         _patch_probe_ldap(kmod, ldap_skip):
        results = scan_kerberos_targets(["dc01.corp.local"], timeout=5)
    assert len(results) == 1
    assert "MEDIUM" in results[0].service_detail
    assert results[0].cert_pubkey_alg == "unknown-etype-99"


# ---------------------------------------------------------------------------
# Section 6: KERB-03 LDAP Probe tests (GREEN -- real behavior)
# ---------------------------------------------------------------------------

def test_ldap_graceful_degrade():
    """KERB-03: When LDAP port 389 is unreachable, scanner logs warning and
    continues without crashing -- etype results are still returned.
    """
    import quirk.scanner.kerberos_scanner as kmod
    with patch.object(kmod, "IMPACKET_AVAILABLE", True), \
         _patch_probe_kdc(kmod, [23]):
        # Patch the actual _probe_ldap_anon to simulate connection failure
        with patch.object(kmod, '_probe_ldap_anon',
                          return_value={"ldap_status": "skipped", "ldap_error": "Connection refused"}):
            results = scan_kerberos_targets(["no-ldap.corp.local"], timeout=1)
    assert len(results) >= 1
    assert any(ep.cert_pubkey_alg == "rc4-hmac" for ep in results)
    # Verify kerberos_scan_json captures LDAP skip
    scan_data = json.loads(results[0].kerberos_scan_json)
    assert scan_data["ldap_status"] == "skipped"


def test_ldap_anonymous_bind_rejected():
    """KERB-03: When LDAP returns auth error (anonymous bind rejected), scanner
    logs and continues -- kerberos_scan_json captures the rejection.
    """
    import quirk.scanner.kerberos_scanner as kmod
    rejected = {"ldap_status": "anonymous-bind-rejected", "ldap_error": "ANONYMOUS_AUTH_REJECTED"}
    with patch.object(kmod, "IMPACKET_AVAILABLE", True), \
         _patch_probe_kdc(kmod, [23]), \
         _patch_probe_ldap(kmod, rejected):
        results = scan_kerberos_targets(["auth-reject.corp.local"], timeout=5)
    assert len(results) >= 1
    scan_data = json.loads(results[0].kerberos_scan_json)
    assert scan_data["ldap"]["ldap_status"] == "anonymous-bind-rejected"


def test_ldap_success_reads_enc_types():
    """KERB-03: When anonymous LDAP bind succeeds and msDS-SupportedEncryptionTypes
    is readable, value is included in kerberos_scan_json.
    """
    import quirk.scanner.kerberos_scanner as kmod
    ldap_ok = {
        "ldap_status": "ok",
        "msDS-SupportedEncryptionTypes": 28,
    }
    with patch.object(kmod, "IMPACKET_AVAILABLE", True), \
         _patch_probe_kdc(kmod, [18, 23]), \
         _patch_probe_ldap(kmod, ldap_ok):
        results = scan_kerberos_targets(["ldap-ok.corp.local"], timeout=5)
    assert len(results) >= 1
    scan_data = json.loads(results[0].kerberos_scan_json)
    assert scan_data["ldap"]["ldap_status"] == "ok"
    assert scan_data["ldap"]["msDS-SupportedEncryptionTypes"] == 28


# ---------------------------------------------------------------------------
# Section 7: KERB-04 Database/CBOM Integration tests (GREEN -- real behavior)
# ---------------------------------------------------------------------------

def test_kerberos_db_row():
    """KERB-04: Each returned CryptoEndpoint has protocol='KERBEROS', port=88,
    and the first endpoint for each target has kerberos_scan_json populated.
    """
    import quirk.scanner.kerberos_scanner as kmod
    ldap_ok = {"ldap_status": "ok", "msDS-SupportedEncryptionTypes": None}
    with patch.object(kmod, "IMPACKET_AVAILABLE", True), \
         _patch_probe_kdc(kmod, [23]), \
         _patch_probe_ldap(kmod, ldap_ok):
        results = scan_kerberos_targets(["dc01.corp.local"], timeout=5)
    assert len(results) == 1
    ep = results[0]
    assert ep.protocol == "KERBEROS"
    assert ep.port == 88
    assert ep.kerberos_scan_json is not None
    # Verify valid JSON
    scan_data = json.loads(ep.kerberos_scan_json)
    assert isinstance(scan_data, dict)


def test_kerberos_scan_json_structure():
    """KERB-04: kerberos_scan_json field is valid JSON containing at minimum:
    realm, etypes, ldap keys.
    """
    import quirk.scanner.kerberos_scanner as kmod
    ldap_ok = {"ldap_status": "ok", "msDS-SupportedEncryptionTypes": None}
    with patch.object(kmod, "IMPACKET_AVAILABLE", True), \
         _patch_probe_kdc(kmod, [23, 18]), \
         _patch_probe_ldap(kmod, ldap_ok):
        results = scan_kerberos_targets(["dc01.corp.local"], timeout=5)
    assert len(results) >= 1
    scan_data = json.loads(results[0].kerberos_scan_json)
    assert "realm" in scan_data, "kerberos_scan_json must contain 'realm' key"
    assert "etypes" in scan_data, "kerberos_scan_json must contain 'etypes' key"
    assert "ldap" in scan_data, "kerberos_scan_json must contain 'ldap' key"
    assert "ldap_status" in scan_data, "kerberos_scan_json must contain 'ldap_status' key"
    assert scan_data["realm"] == "CORP.LOCAL"
    assert 23 in scan_data["etypes"]


# ---------------------------------------------------------------------------
# Section 8: KERB-05 Integration / Chaos Lab test (SKIPPED unless env var set)
# ---------------------------------------------------------------------------

@pytest.mark.slow
@pytest.mark.skipif(
    not os.environ.get("QUIRK_KERBEROS_INTEGRATION"),
    reason="Set QUIRK_KERBEROS_INTEGRATION=1 to run against local Samba DC chaos lab",
)
def test_samba_dc_integration():
    """UAT-25 / KERB-05: Phase 25 HUMAN-UAT closure — against the running `kerberos`
    chaos lab profile (Samba DC), scan_kerberos_targets returns rc4-hmac (etype 23) in
    cert_pubkey_alg results. This test is the automated equivalent of the Phase 25
    HUMAN-UAT scenario and supersedes the manual run; closure recorded in
    .planning/STATE.md Deferred Items (plan 44-06).

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


# ---------------------------------------------------------------------------
# KERB-04 / ISSUE-3: session_start parameter acceptance
# ---------------------------------------------------------------------------

def test_kerberos_session_start_stamps_all_endpoints():
    """ISSUE-3: scan_kerberos_targets(session_start=<fixed_dt>) stamps all endpoints with that time.

    RED: scan_kerberos_targets does not accept session_start yet — TypeError expected.
    """
    from datetime import datetime, timezone

    fixed_dt = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
    expected_naive = datetime(2026, 1, 15, 12, 0, 0)  # tzinfo stripped

    import quirk.scanner.kerberos_scanner as kmod
    ldap_ok = {"ldap_status": "ok", "msDS-SupportedEncryptionTypes": None}
    with patch.object(kmod, "IMPACKET_AVAILABLE", True), \
         _patch_probe_kdc(kmod, [18, 23]), \
         _patch_probe_ldap(kmod, ldap_ok):
        results = scan_kerberos_targets(["localhost"], timeout=5, session_start=fixed_dt)

    assert len(results) == 2, f"Expected 2 endpoints, got {len(results)}"
    for ep in results:
        assert ep.scanned_at == expected_naive, \
            f"Expected scanned_at={expected_naive!r}, got {ep.scanned_at!r}"
