"""Phase 238 DETECT-06: mTLS-required endpoints are detected after the TLS handshake.

Under TLS 1.3 a server that requires a client certificate completes the handshake
from the client's point of view and rejects the client afterwards, either with a
``certificate required`` alert on the first read or (nginx ``ssl_verify_client on``)
with an HTTP 400 "No required SSL certificate was sent" page. No QUIRK path read
after the handshake, so such an endpoint read as plain TLS (D-12).

These tests drive the real ``tls_scanner.scan_one`` (sslyze leg) and
``_scan_one_fallback`` against loopback TLS servers bound to 127.0.0.1, using a CA
and a leaf certificate generated at test time. They prove each D-13 signal, each
false-positive guard, the D-32 ``supported_curves=None`` guard (TLS 1.2 strict
mTLS through sslyze) and the D-14 rule that the scanner never sets ``scan_error``
for a post-handshake rejection.
"""
from __future__ import annotations

import datetime
import socket
import ssl
import threading
from unittest.mock import patch

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from quirk.scanner import tls_scanner

_HOST = "127.0.0.1"
_NGINX_BODY = "<html>400 No required SSL certificate was sent</html>"


def _name(cn: str) -> x509.Name:
    return x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cn)])


def _pem_key(key) -> bytes:
    return key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    )


@pytest.fixture(scope="module")
def pki(tmp_path_factory):
    """CA ("CN=238-test-ca") and a leaf ("CN=238-mtls-leaf") issued by it."""
    d = tmp_path_factory.mktemp("pki238")
    now = datetime.datetime.now(datetime.timezone.utc)
    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    ca = (
        x509.CertificateBuilder()
        .subject_name(_name("238-test-ca"))
        .issuer_name(_name("238-test-ca"))
        .public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=30))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(ca_key, hashes.SHA256())
    )
    leaf_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    leaf = (
        x509.CertificateBuilder()
        .subject_name(_name("238-mtls-leaf"))
        .issuer_name(ca.subject)
        .public_key(leaf_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=30))
        .sign(ca_key, hashes.SHA256())
    )
    ca_pem = d / "ca.pem"
    leaf_pem = d / "leaf.pem"
    leaf_key_pem = d / "leaf-key.pem"
    ca_pem.write_bytes(ca.public_bytes(serialization.Encoding.PEM))
    leaf_pem.write_bytes(leaf.public_bytes(serialization.Encoding.PEM))
    leaf_key_pem.write_bytes(_pem_key(leaf_key))
    return {"ca": str(ca_pem), "cert": str(leaf_pem), "key": str(leaf_key_pem), "leaf": leaf}


@pytest.fixture
def server(pki):
    """Factory: ``_server(mode, max_version, http_status, body) -> port``.

    mode "required" = CERT_REQUIRED, "optional" = CERT_OPTIONAL, "none" = CERT_NONE.
    After the handshake the server reads once and answers one HTTP response, one
    thread per connection, every server-side exception swallowed.
    """
    listeners = []

    def _server(mode: str, max_version: str, http_status: int, body: str) -> int:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(pki["cert"], pki["key"])
        version = (
            ssl.TLSVersion.TLSv1_3 if max_version == "TLSv1.3" else ssl.TLSVersion.TLSv1_2
        )
        ctx.minimum_version = version
        ctx.maximum_version = version
        if mode == "required":
            ctx.verify_mode = ssl.CERT_REQUIRED
            ctx.load_verify_locations(pki["ca"])
        elif mode == "optional":
            ctx.verify_mode = ssl.CERT_OPTIONAL
            ctx.load_verify_locations(pki["ca"])
        else:
            ctx.verify_mode = ssl.CERT_NONE
        payload = body.encode("ascii")
        response = (
            f"HTTP/1.1 {http_status} X\r\nContent-Length: {len(payload)}\r\n"
            "Connection: close\r\n\r\n"
        ).encode("ascii") + payload

        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((_HOST, 0))
        srv.listen(64)
        srv.settimeout(1)
        listeners.append(srv)

        def handle(conn):
            try:
                conn.settimeout(5)
                s = ctx.wrap_socket(conn, server_side=True)
                try:
                    s.recv(65536)
                    s.sendall(response)
                finally:
                    s.close()
            except Exception:
                try:
                    conn.close()
                except Exception:
                    pass

        def serve():
            while True:
                try:
                    conn, _ = srv.accept()
                except socket.timeout:
                    continue
                except Exception:
                    return
                threading.Thread(target=handle, args=(conn,), daemon=True).start()

        threading.Thread(target=serve, daemon=True).start()
        return srv.getsockname()[1]

    yield _server
    for srv in listeners:
        try:
            srv.close()
        except Exception:
            pass


def _closed_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((_HOST, 0))
    port = s.getsockname()[1]
    s.close()
    return port


def test_tls13_certificate_required_alert_is_mtls_required(server, pki):
    port = server("required", "TLSv1.3", 200, "ok")
    ep = tls_scanner.scan_one(_HOST, port, 5, False)
    assert ep.tls_version == "TLSv1.3"
    assert ep.tls_blocker_reason == "MTLS_REQUIRED"
    assert ep.scan_error is None
    assert ep.cert_subject == pki["leaf"].subject.rfc4514_string()


@pytest.mark.parametrize("version", ["TLSv1.3", "TLSv1.2"], ids=["TLSv1_3", "TLSv1_2"])
def test_nginx_style_400_phrase_is_mtls_required(server, version):
    port = server("optional", version, 400, _NGINX_BODY)
    ep = tls_scanner.scan_one(_HOST, port, 5, False)
    assert ep.tls_version == version
    assert ep.tls_blocker_reason == "MTLS_REQUIRED"
    assert ep.scan_error is None


def test_plain_400_is_not_mtls(server):
    port = server("optional", "TLSv1.3", 400, "Bad Request")
    ep = tls_scanner.scan_one(_HOST, port, 5, False)
    assert ep.tls_version == "TLSv1.3"
    assert ep.tls_blocker_reason is None
    assert ep.scan_error is None


def test_sslyze_optional_alone_is_not_mtls(server):
    port = server("optional", "TLSv1.3", 200, "ok")
    ep = tls_scanner.scan_one(_HOST, port, 5, False)
    assert ep.tls_version == "TLSv1.3"
    assert ep.tls_blocker_reason is None
    assert ep.scan_error is None


def test_tls12_certificate_required_is_mtls_required_via_sslyze(server):
    port = server("required", "TLSv1.2", 200, "ok")
    ep = tls_scanner.scan_one(_HOST, port, 5, False)
    assert ep.tls_version == "TLSv1.2"
    assert ep.tls_blocker_reason == "MTLS_REQUIRED"
    assert ep.scan_error is None
    assert ep.tls_enum_mode == "sslyze"


def test_fallback_probes_after_handshake(server):
    port = server("required", "TLSv1.3", 200, "ok")
    ep = tls_scanner._scan_one_fallback(_HOST, port, 5, False)
    assert ep.tls_version == "TLSv1.3"
    assert ep.tls_blocker_reason == "MTLS_REQUIRED"
    assert ep.scan_error is None


def test_disabled_client_auth_never_probes(server):
    port = server("none", "TLSv1.3", 200, "ok")
    with patch.object(tls_scanner, "_post_handshake_mtls_probe") as probe:
        ep = tls_scanner.scan_one(_HOST, port, 5, False)
    assert ep.tls_enum_mode == "sslyze"
    assert ep.tls_blocker_reason is None
    probe.assert_not_called()


def test_probe_failure_leaves_row_unchanged(server):
    assert tls_scanner._post_handshake_mtls_probe(_HOST, _closed_port(), 2, False) is None
    port = server("none", "TLSv1.3", 200, "ok")
    with patch.object(
        tls_scanner, "_post_handshake_mtls_probe", side_effect=RuntimeError("probe boom")
    ):
        ep = tls_scanner._scan_one_fallback(_HOST, port, 5, False)
    assert ep.tls_version == "TLSv1.3"
    assert ep.tls_blocker_reason is None
    assert ep.scan_error is None


# ---------------------------------------------------------------------------
# D-39 (code review WR-01/WR-02): read first, send GET only to HTTP-shaped
# services, and send a well-formed Host header.
# ---------------------------------------------------------------------------


@pytest.fixture
def raw_server(pki):
    """Factory: a TLS 1.3 CERT_NONE server that, after the handshake, sends
    *greeting* (may be empty) and then holds the connection open for up to
    3 s, recording every byte the client sends in ``received``."""
    listeners = []
    received: list[bytes] = []

    def _server(greeting: bytes) -> int:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(pki["cert"], pki["key"])
        ctx.minimum_version = ssl.TLSVersion.TLSv1_3
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((_HOST, 0))
        srv.listen(8)
        srv.settimeout(1)
        listeners.append(srv)

        def handle(conn):
            try:
                conn.settimeout(3)
                s = ctx.wrap_socket(conn, server_side=True)
                try:
                    if greeting:
                        s.sendall(greeting)
                    while True:
                        chunk = s.recv(65536)
                        if not chunk:
                            break
                        received.append(chunk)
                finally:
                    s.close()
            except Exception:
                try:
                    conn.close()
                except Exception:
                    pass

        def serve():
            while True:
                try:
                    conn, _ = srv.accept()
                except socket.timeout:
                    continue
                except Exception:
                    return
                threading.Thread(target=handle, args=(conn,), daemon=True).start()

        threading.Thread(target=serve, daemon=True).start()
        return srv.getsockname()[1]

    _server.received = received
    yield _server
    for srv in listeners:
        try:
            srv.close()
        except Exception:
            pass


def test_banner_first_server_ends_the_probe_without_a_request(raw_server):
    import time

    port = raw_server(b"* OK IMAP4rev1 ready\r\n")
    started = time.monotonic()
    result = tls_scanner._post_handshake_mtls_probe(_HOST, port, 5, False)
    elapsed = time.monotonic() - started
    assert result is None
    assert elapsed < 1.0
    time.sleep(0.2)
    assert raw_server.received == []


def test_well_known_non_http_port_gets_no_request(raw_server):
    import time

    port = raw_server(b"")
    with patch.object(tls_scanner, "_NON_HTTP_TLS_PORTS", frozenset({port})):
        started = time.monotonic()
        result = tls_scanner._post_handshake_mtls_probe(_HOST, port, 5, False)
        elapsed = time.monotonic() - started
    assert result is None
    assert elapsed < 1.0
    time.sleep(0.2)
    assert raw_server.received == []


def test_silent_http_port_gets_one_get_request(raw_server):
    import time

    port = raw_server(b"")
    assert tls_scanner._post_handshake_mtls_probe(_HOST, port, 1, False) is None
    time.sleep(0.2)
    sent = b"".join(raw_server.received)
    assert sent.startswith(b"GET / HTTP/1.1\r\n")
    assert f"\r\nHost: {_HOST}:{port}\r\n".encode() in sent


def test_well_known_non_http_ports_include_mail_and_directory_ports():
    for port in (465, 563, 636, 853, 989, 990, 992, 993, 994, 995, 3269, 5061, 5223, 6697, 8883):
        assert port in tls_scanner._NON_HTTP_TLS_PORTS
    for port in (443, 8443, 11443):
        assert port not in tls_scanner._NON_HTTP_TLS_PORTS


@pytest.mark.parametrize(
    "host, port, expected",
    [
        ("::1", 443, b"[::1]"),
        ("2001:db8::1", 8443, b"[2001:db8::1]:8443"),
        ("10.0.0.1", 443, b"10.0.0.1"),
        ("10.0.0.1", 11443, b"10.0.0.1:11443"),
        ("idp.example.com", 443, b"idp.example.com"),
        ("idp.example.com", 8443, b"idp.example.com:8443"),
        ("bücher.example", 443, b"xn--bcher-kva.example"),
    ],
)
def test_probe_host_header_formatting(host, port, expected):
    assert tls_scanner._probe_host_header(host, port) == expected
