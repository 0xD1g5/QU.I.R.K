"""Phase 71 / PROTO-04 hardening tests (WR-07, WR-08, WR-09, WR-10).

Covers:
- DNSSEC _parse_dnskeys bounds key_bytes by per-algorithm minimum and skips truncated records
- Kerberos _probe_kdc_udp narrows decode except + logs WARNING on transport/decode failure
- Kerberos _build_as_req nonce sourced from secrets, never from random
- SAML _classify_target enforces 1 MiB JSON cap and falls through to the parse-failure path
"""

from __future__ import annotations

import json
import logging
import socket
import struct
from unittest.mock import MagicMock, patch

import pytest


# ────────────────────────────────────────────────────────────
# DNSSEC (WR-07)
# ────────────────────────────────────────────────────────────

def _mock_dnskey(algorithm: int, key_bytes: bytes, flags: int = 257):
    rdata = MagicMock()
    rdata.algorithm = algorithm
    rdata.flags = flags
    rdata.key = key_bytes
    rdata.protocol = 3
    return rdata


def _mock_rrset(rdata_list):
    rrset = MagicMock()
    rrset.__iter__ = MagicMock(return_value=iter(rdata_list))
    return rrset


def test_parse_dnskeys_truncated_ed25519_skipped(caplog):
    """Ed25519 (alg 15) requires >= 32 bytes; a 10-byte key must be skipped + warned."""
    from quirk.scanner.dnssec_scanner import _parse_dnskeys

    rrset = _mock_rrset([_mock_dnskey(algorithm=15, key_bytes=b"\x00" * 10)])
    with caplog.at_level(logging.WARNING, logger="quirk.scanner.dnssec_scanner"):
        keys = _parse_dnskeys(rrset)
    assert keys == [], "truncated Ed25519 record should be skipped"
    assert any("too short" in rec.message for rec in caplog.records)


def test_parse_dnskeys_truncated_ecdsa_skipped(caplog):
    """ECDSA P-256 (alg 13) requires >= 64 bytes; a 10-byte key must be skipped + warned."""
    from quirk.scanner.dnssec_scanner import _parse_dnskeys

    rrset = _mock_rrset([_mock_dnskey(algorithm=13, key_bytes=b"\x00" * 10)])
    with caplog.at_level(logging.WARNING, logger="quirk.scanner.dnssec_scanner"):
        keys = _parse_dnskeys(rrset)
    assert keys == []
    assert any("alg 13" in rec.message or "too short" in rec.message for rec in caplog.records)


def test_parse_dnskeys_valid_ed25519_succeeds():
    """A correctly-sized Ed25519 key must still appear in the output (regression guard)."""
    from quirk.scanner.dnssec_scanner import _parse_dnskeys

    with patch("quirk.scanner.dnssec_scanner.dns.dnssec.key_id", return_value=12345):
        rrset = _mock_rrset([_mock_dnskey(algorithm=15, key_bytes=b"\x00" * 32)])
        keys = _parse_dnskeys(rrset)
    assert len(keys) == 1
    assert keys[0]["alg"] == 15
    assert keys[0]["tag"] == 12345


# ────────────────────────────────────────────────────────────
# Kerberos (WR-08, WR-09)
# ────────────────────────────────────────────────────────────

@pytest.fixture
def _kerb_mod():
    pytest.importorskip("impacket")
    from quirk.scanner import kerberos_scanner
    return kerberos_scanner


def test_kdc_udp_decode_failure_logs(_kerb_mod, caplog):
    """A decode error inside _probe_kdc_udp must log WARNING and return []
    rather than propagating or being silently swallowed."""
    kmod = _kerb_mod

    fake_sock = MagicMock()
    fake_sock.recvfrom.return_value = (b"\x00\x01\x02garbage", ("127.0.0.1", 88))

    def _fail_decode(*_a, **_kw):
        raise struct.error("truncated KRB_ERROR")

    with patch.object(kmod.socket, "socket", return_value=fake_sock), \
         patch.object(kmod.decoder, "decode", side_effect=_fail_decode), \
         caplog.at_level(logging.WARNING, logger="quirk.scanner.kerberos_scanner"):
        result = kmod._probe_kdc_udp("127.0.0.1", "EXAMPLE.COM", timeout=1)
    assert result == []
    assert any("decode failed" in rec.message for rec in caplog.records)


def test_build_as_req_nonce_uses_secrets(_kerb_mod):
    """_build_as_req must source its nonce from secrets, not random.
    We monkeypatch secrets.randbits to a sentinel and assert it appears in the AS-REQ;
    we also assert random.randint / random.getrandbits are not called."""
    kmod = _kerb_mod
    from impacket.krb5 import constants
    from impacket.krb5.types import Principal

    sentinel = 0x0DEADBEE  # 28-bit value — well within the 31-bit field
    client_name = Principal("nobody", type=constants.PrincipalNameType.NT_PRINCIPAL.value)
    server_name = Principal("krbtgt/EXAMPLE.COM", type=constants.PrincipalNameType.NT_SRV_INST.value)

    import random as _random
    called = {"random": False}

    def _fail_random(*_a, **_kw):
        called["random"] = True
        return 0

    with patch.object(kmod.secrets, "randbits", return_value=sentinel) as mock_secrets, \
         patch.object(_random, "getrandbits", side_effect=_fail_random), \
         patch.object(_random, "randint", side_effect=_fail_random):
        as_req = kmod._build_as_req(client_name, server_name, "EXAMPLE.COM")

    assert int(as_req['req-body']['nonce']) == sentinel
    mock_secrets.assert_called_once_with(31)
    assert called["random"] is False, "random.* must not be called for nonce"


# ────────────────────────────────────────────────────────────
# SAML (WR-10)
# ────────────────────────────────────────────────────────────

def test_classify_target_oversized_json_capped(caplog):
    """A payload > MAX_SAML_JSON_BYTES must log WARNING and bypass json.loads,
    falling through to the XML-sniff path (here -> 'unknown' because payload is binary)."""
    from quirk.scanner import saml_scanner

    oversized = b"\x00" * (saml_scanner.MAX_SAML_JSON_BYTES + 1)

    json_loads_called = {"v": False}

    def _fail_loads(*_a, **_kw):
        json_loads_called["v"] = True
        raise AssertionError("json.loads must NOT be called for oversized payload")

    with patch.object(saml_scanner.json, "loads", side_effect=_fail_loads), \
         caplog.at_level(logging.WARNING, logger="quirk.scanner.saml_scanner"):
        result = saml_scanner._classify_target("https://idp.example/metadata", oversized)

    assert result == "unknown"
    assert json_loads_called["v"] is False
    assert any("MAX_SAML_JSON_BYTES" in rec.message or "exceeds" in rec.message for rec in caplog.records)


def test_classify_target_normal_size_proceeds():
    """A small valid JSON OIDC payload classifies as 'oidc' (regression guard)."""
    from quirk.scanner.saml_scanner import _classify_target

    payload = json.dumps({"issuer": "https://idp.example"}).encode("utf-8")
    assert _classify_target("https://idp.example/.well-known/openid-configuration", payload) == "oidc"
    # Also verify non-well-known JSON still classifies as oidc by content sniff
    assert _classify_target("https://idp.example/other", payload) == "oidc"
