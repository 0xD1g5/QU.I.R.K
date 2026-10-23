"""Phase 230 DETECT-01: --inventory-code-signing's TLS-EKU source fires in a real scan.

Before this phase nothing in a real scan wrote the leaf EKU anywhere, so
``scan_codesign_from_tls_endpoints`` never emitted a CODE_SIGNING endpoint (Phase 224
probe: ``real-scan CODE_SIGNING endpoints: 0``). Every earlier test injected the value
the real path never produced. These tests drive the REAL ``tls_scanner.scan_one``
(sslyze leg) and the stdlib fallback leg (both parse sites) against a real loopback
TLS socket, then a DB round-trip (the --resume-scan-id path). D-04 / D-22.
"""
from __future__ import annotations

import datetime
import json
import socket
import ssl
import threading

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

from quirk.db import get_session, init_db
from quirk.models import CryptoEndpoint
from quirk.scanner import tls_scanner
from quirk.scanner.codesign_scanner import scan_codesign_from_tls_endpoints

CS_OID = "1.3.6.1.5.5.7.3.3"
SA_OID = "1.3.6.1.5.5.7.3.1"

_EKU_BY_LEAF = {
    "eku_codesign": [ExtendedKeyUsageOID.SERVER_AUTH, ExtendedKeyUsageOID.CODE_SIGNING],
    "eku_serverauth_only": [ExtendedKeyUsageOID.SERVER_AUTH],
    "no_eku": None,
}


def _build_leaf(ekus):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    now = datetime.datetime.now(datetime.timezone.utc)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "codesign-live")])
    b = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=30))
    )
    if ekus is not None:
        b = b.add_extension(x509.ExtendedKeyUsage(ekus), critical=False)
    return key, b.sign(key, hashes.SHA256())


@pytest.fixture(params=sorted(_EKU_BY_LEAF))
def tls_server(request, tmp_path):
    """Loopback TLS server presenting a self-signed leaf; yields (leaf_kind, port, cert)."""
    kind = request.param
    key, cert = _build_leaf(_EKU_BY_LEAF[kind])
    cp, kp = tmp_path / "c.pem", tmp_path / "k.pem"
    cp.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    kp.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        )
    )
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(str(cp), str(kp))
    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen(50)
    srv.settimeout(5)
    port = srv.getsockname()[1]

    def serve():
        while True:
            try:
                c, _ = srv.accept()
            except socket.timeout:
                continue
            except Exception:
                return
            try:
                c.settimeout(5)
                s = ctx.wrap_socket(c, server_side=True)
                s.recv(1)
                s.close()
            except Exception:
                try:
                    c.close()
                except Exception:
                    pass

    threading.Thread(target=serve, daemon=True).start()
    yield kind, port, cert
    srv.close()


def _expected(kind: str) -> int:
    return 1 if kind == "eku_codesign" else 0


def _count(ep) -> list:
    return scan_codesign_from_tls_endpoints([ep])


def test_sslyze_leg_real_capture(tls_server):
    kind, port, _cert = tls_server
    assert tls_scanner.SSLYZE_AVAILABLE
    ep = tls_scanner.scan_one("127.0.0.1", port, 5, False)
    assert json.loads(ep.tls_capabilities_json)["source"] == "sslyze"
    assert not ep.scan_error
    out = _count(ep)
    assert len(out) == _expected(kind), (kind, ep.cert_eku_oids)
    if out:
        assert out[0].protocol == "CODE_SIGNING"
    if kind == "no_eku":
        assert ep.cert_eku_oids is None


def test_fallback_leg_via_scan_one(tls_server, monkeypatch):
    kind, port, _cert = tls_server
    monkeypatch.setattr(tls_scanner, "SSLYZE_AVAILABLE", False)
    ep = tls_scanner.scan_one("127.0.0.1", port, 5, False)
    assert not ep.scan_error
    out = _count(ep)
    assert len(out) == _expected(kind)
    if out:
        assert out[0].protocol == "CODE_SIGNING"
    if kind == "no_eku":
        assert ep.cert_eku_oids is None


def test_fallback_leg_direct(tls_server):
    kind, port, _cert = tls_server
    ep = tls_scanner._scan_one_fallback("127.0.0.1", port, 5, False, None, "fast")
    assert len(_count(ep)) == _expected(kind)


def test_eku_never_written_into_caps_blob(tls_server):
    _kind, port, _cert = tls_server
    ep = tls_scanner._scan_one_fallback("127.0.0.1", port, 5, False, None, "fast")
    assert not ep.tls_capabilities_json  # D-02: no deep-TLS liveness evidence on fallback


def test_eku_oids_helper_values_and_never_raise():
    from quirk.scanner.tls_scanner import _eku_oids

    _k, with_eku = _build_leaf(_EKU_BY_LEAF["eku_codesign"])
    _k, without = _build_leaf(None)
    assert _eku_oids(with_eku) == f"{SA_OID},{CS_OID}"
    assert _eku_oids(without) is None

    class _Raises:
        class extensions:  # noqa: N801
            @staticmethod
            def get_extension_for_class(_cls):
                raise ValueError("malformed EKU")

    assert _eku_oids(_Raises()) is None


def test_resume_round_trip_persists_cert_eku_oids(tmp_path):
    _k, cert = _build_leaf(_EKU_BY_LEAF["eku_codesign"])
    value = tls_scanner._eku_oids(cert)
    db = str(tmp_path / "p230.db")
    init_db(db)
    with get_session(db) as s:
        s.add(CryptoEndpoint(host="127.0.0.1", port=443, protocol="TLS", cert_eku_oids=value))
    with get_session(db) as s:
        rows = s.query(CryptoEndpoint).filter(CryptoEndpoint.protocol == "TLS").all()
        assert len(rows) == 1
        assert rows[0].cert_eku_oids == value
        assert len(scan_codesign_from_tls_endpoints(rows)) == 1
