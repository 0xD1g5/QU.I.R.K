"""Tests for broker_scanner.py Redis functions (REDIS-01..03 + STRUCT-01 + BROKER-ARCH).

Phase 33 Plan 05: covers _detect_redis_plaintext, _probe_redis_tls, _enrich_redis_config,
scan_one_redis, scan_redis_targets.

All network calls are mocked — no live network required.
"""
import ssl
import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock, call

pytest.importorskip("quirk.scanner.broker_scanner", reason="Phase 33 Plan 05")

from quirk.scanner.broker_scanner import (
    _detect_redis_plaintext,
    _probe_redis_tls,
    _enrich_redis_config,
    scan_one_redis,
    scan_redis_targets,
)


# ---------------------------------------------------------------------------
# REDIS-02: plaintext PING detection — _detect_redis_plaintext
# ---------------------------------------------------------------------------

def test_detect_redis_plaintext_pong():
    """REDIS-02 +PONG: mock socket recv -> b'+PONG\\r\\n'; _detect_redis_plaintext returns True."""
    mock_sock = MagicMock()
    mock_sock.recv.return_value = b"+PONG\r\n"
    mock_sock.__enter__ = MagicMock(return_value=mock_sock)
    mock_sock.__exit__ = MagicMock(return_value=False)

    with patch("socket.create_connection", return_value=mock_sock):
        result = _detect_redis_plaintext("r.example.com", 6379)

    assert result is True, f"Expected True for +PONG response, got {result!r}"


def test_detect_redis_plaintext_noauth():
    """REDIS-02 -NOAUTH: mock recv -> b'-NOAUTH Authentication required\\r\\n'; True."""
    mock_sock = MagicMock()
    mock_sock.recv.return_value = b"-NOAUTH Authentication required\r\n"
    mock_sock.__enter__ = MagicMock(return_value=mock_sock)
    mock_sock.__exit__ = MagicMock(return_value=False)

    with patch("socket.create_connection", return_value=mock_sock):
        result = _detect_redis_plaintext("r.example.com", 6379)

    assert result is True, f"Expected True for -NOAUTH response, got {result!r}"


def test_detect_redis_plaintext_array_prefix():
    """REDIS-02 *array: mock recv -> b'*1\\r\\n$4\\r\\nPING\\r\\n'; True."""
    mock_sock = MagicMock()
    mock_sock.recv.return_value = b"*1\r\n$4\r\nPING\r\n"
    mock_sock.__enter__ = MagicMock(return_value=mock_sock)
    mock_sock.__exit__ = MagicMock(return_value=False)

    with patch("socket.create_connection", return_value=mock_sock):
        result = _detect_redis_plaintext("r.example.com", 6379)

    assert result is True, f"Expected True for *array RESP response, got {result!r}"


def test_detect_redis_plaintext_garbage_data():
    """REDIS-02 garbage: mock recv -> b'\\x00garbage'; _detect_redis_plaintext returns False."""
    mock_sock = MagicMock()
    mock_sock.recv.return_value = b"\x00garbage"
    mock_sock.__enter__ = MagicMock(return_value=mock_sock)
    mock_sock.__exit__ = MagicMock(return_value=False)

    with patch("socket.create_connection", return_value=mock_sock):
        result = _detect_redis_plaintext("r.example.com", 6379)

    assert result is False, f"Expected False for garbage response, got {result!r}"


def test_detect_redis_plaintext_connection_refused():
    """REDIS-02 ConnectionRefused: create_connection raises; _detect_redis_plaintext returns False."""
    with patch("socket.create_connection", side_effect=ConnectionRefusedError()):
        result = _detect_redis_plaintext("r.example.com", 6379)

    assert result is False, f"Expected False on ConnectionRefusedError, got {result!r}"


def test_scan_one_redis_6379_emits_redis_plain():
    """REDIS-02 emission: scan_one_redis(host, 6379) with detection True -> ep.protocol == 'REDIS-PLAIN'."""
    with patch("quirk.scanner.broker_scanner._detect_redis_plaintext", return_value=True):
        ep = scan_one_redis("r.example.com", 6379, timeout=5)

    assert ep is not None, "scan_one_redis must return endpoint when plaintext detected"
    assert ep.protocol == "REDIS-PLAIN", f"Expected 'REDIS-PLAIN', got {ep.protocol!r}"
    assert ep.port == 6379


# ---------------------------------------------------------------------------
# REDIS-01: raw ssl.SSLContext TLS probe — _probe_redis_tls
# ---------------------------------------------------------------------------

def _make_mock_ssock(tls_version="TLSv1.2", cipher_name="AES256-SHA", bits=256):
    """Build a mock SSL socket for _probe_redis_tls tests."""
    # Build a self-signed DER cert for the mock
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID
    import datetime as dt

    # Generate a minimal RSA key for the fake cert
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "redis.example.com"),
    ])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(dt.datetime.utcnow())
        .not_valid_after(dt.datetime.utcnow() + dt.timedelta(days=365))
        .sign(key, hashes.SHA256())
    )
    der_bytes = cert.public_bytes(serialization.Encoding.DER)

    ssock = MagicMock()
    ssock.version.return_value = tls_version
    ssock.cipher.return_value = (cipher_name, "TLSv1.2", bits)
    ssock.getpeercert.return_value = der_bytes
    ssock.__enter__ = MagicMock(return_value=ssock)
    ssock.__exit__ = MagicMock(return_value=False)
    return ssock


def test_probe_redis_tls_success():
    """REDIS-01 success: mocked ssl handshake; ep.protocol == 'REDIS-TLS', ep.tls_version == 'TLSv1.2'."""
    ssock = _make_mock_ssock(tls_version="TLSv1.2", cipher_name="AES256-SHA")

    # Mock the raw socket
    mock_sock = MagicMock()
    mock_sock.__enter__ = MagicMock(return_value=mock_sock)
    mock_sock.__exit__ = MagicMock(return_value=False)

    mock_ssl_ctx = MagicMock()
    mock_ssl_ctx.wrap_socket.return_value = ssock

    with patch("socket.create_connection", return_value=mock_sock), \
         patch("ssl.create_default_context", return_value=mock_ssl_ctx):
        ep = _probe_redis_tls("redis.example.com", 6380, timeout=5)

    assert ep is not None, "_probe_redis_tls must return CryptoEndpoint on success"
    assert ep.protocol == "REDIS-TLS", f"Expected 'REDIS-TLS', got {ep.protocol!r}"
    assert ep.tls_version == "TLSv1.2", f"Expected 'TLSv1.2', got {ep.tls_version!r}"
    assert ep.host == "redis.example.com"
    assert ep.port == 6380


def test_probe_redis_tls_connection_refused():
    """REDIS-01 ConnectionRefused: _probe_redis_tls returns None."""
    with patch("socket.create_connection", side_effect=ConnectionRefusedError()):
        ep = _probe_redis_tls("redis.example.com", 6380, timeout=5)

    assert ep is None, f"Expected None on ConnectionRefusedError, got {ep!r}"


def test_probe_redis_tls_handshake_error():
    """REDIS-01 handshake error: wrap_socket raises ssl.SSLError; ep returned with scan_error populated."""
    mock_sock = MagicMock()
    mock_sock.__enter__ = MagicMock(return_value=mock_sock)
    mock_sock.__exit__ = MagicMock(return_value=False)

    mock_ssl_ctx = MagicMock()
    mock_ssl_ctx.wrap_socket.side_effect = ssl.SSLError("HANDSHAKE FAILURE")

    with patch("socket.create_connection", return_value=mock_sock), \
         patch("ssl.create_default_context", return_value=mock_ssl_ctx):
        ep = _probe_redis_tls("redis.example.com", 6380, timeout=5)

    assert ep is not None, "_probe_redis_tls must return ep with scan_error on ssl.SSLError"
    assert ep.scan_error is not None, "scan_error must be populated on handshake failure"
    assert "HANDSHAKE FAILURE" in ep.scan_error or len(ep.scan_error) > 0


# ---------------------------------------------------------------------------
# REDIS-03: redis-py CONFIG GET enrichment — _enrich_redis_config
# ---------------------------------------------------------------------------

def test_enrich_redis_config_absent_library():
    """REDIS-03 absent: patch REDIS_AVAILABLE=False; _enrich_redis_config returns {}."""
    with patch("quirk.scanner.broker_scanner.REDIS_AVAILABLE", False):
        result = _enrich_redis_config("r.example.com", 6380)

    assert result == {}, f"Expected empty dict when redis-py absent, got {result!r}"


def test_enrich_redis_config_success():
    """REDIS-03 success: patch redis_lib.Redis().config_get -> {'tls-port': '6380'}; returns that dict."""
    with patch("quirk.scanner.broker_scanner.REDIS_AVAILABLE", True), \
         patch("quirk.scanner.broker_scanner.redis_lib") as mock_redis_lib:
        mock_client = MagicMock()
        mock_client.config_get.return_value = {"tls-port": "6380", "tls-protocols": "TLSv1.2"}
        mock_redis_lib.Redis.return_value = mock_client

        result = _enrich_redis_config("r.example.com", 6380)

    assert result == {"tls-port": "6380", "tls-protocols": "TLSv1.2"}, (
        f"Expected tls config dict, got {result!r}"
    )


def test_enrich_redis_config_noauth():
    """REDIS-03 NOAUTH/D-08: AuthenticationError raised; _enrich_redis_config returns {}."""
    with patch("quirk.scanner.broker_scanner.REDIS_AVAILABLE", True), \
         patch("quirk.scanner.broker_scanner.redis_lib") as mock_redis_lib:
        class FakeAuthErr(Exception):
            pass
        class FakeNoPerm(Exception):
            pass
        mock_redis_lib.exceptions.AuthenticationError = FakeAuthErr
        mock_redis_lib.exceptions.NoPermissionError = FakeNoPerm
        mock_client = MagicMock()
        mock_client.config_get.side_effect = FakeAuthErr("NOAUTH")
        mock_redis_lib.Redis.return_value = mock_client

        result = _enrich_redis_config("r.example.com", 6380)

    assert result == {}, f"Expected empty dict on NOAUTH, got {result!r}"


def test_enrich_redis_config_noperm():
    """REDIS-03 NOPERM/D-08: NoPermissionError raised; _enrich_redis_config returns {}."""
    with patch("quirk.scanner.broker_scanner.REDIS_AVAILABLE", True), \
         patch("quirk.scanner.broker_scanner.redis_lib") as mock_redis_lib:
        class FakeAuthErr(Exception):
            pass
        class FakeNoPerm(Exception):
            pass
        mock_redis_lib.exceptions.AuthenticationError = FakeAuthErr
        mock_redis_lib.exceptions.NoPermissionError = FakeNoPerm
        mock_client = MagicMock()
        mock_client.config_get.side_effect = FakeNoPerm("NOPERM")
        mock_redis_lib.Redis.return_value = mock_client

        result = _enrich_redis_config("r.example.com", 6380)

    assert result == {}, f"Expected empty dict on NOPERM, got {result!r}"


# ---------------------------------------------------------------------------
# BROKER-ARCH: all three drivers importable
# ---------------------------------------------------------------------------

def test_broker_arch_all_drivers_importable():
    """BROKER-ARCH: all three scanner drivers importable from broker_scanner."""
    from quirk.scanner.broker_scanner import (
        scan_kafka_targets,
        scan_rabbitmq_targets,
        scan_redis_targets,
    )
    assert callable(scan_kafka_targets), "scan_kafka_targets must be callable"
    assert callable(scan_rabbitmq_targets), "scan_rabbitmq_targets must be callable"
    assert callable(scan_redis_targets), "scan_redis_targets must be callable"


# ---------------------------------------------------------------------------
# STRUCT-01: session_start propagation to ep.scanned_at
# ---------------------------------------------------------------------------

def test_struct01_session_start_propagated():
    """STRUCT-01: scan_one_redis(host, 6379, session_start=fixed_time) sets ep.scanned_at == fixed_time (naive)."""
    fixed_time = datetime(2026, 1, 1, 12, 0, 0)

    with patch("quirk.scanner.broker_scanner._detect_redis_plaintext", return_value=True):
        ep = scan_one_redis("r.example.com", 6379, timeout=5, session_start=fixed_time)

    assert ep is not None
    assert ep.scanned_at == fixed_time.replace(tzinfo=None), (
        f"Expected scanned_at={fixed_time.replace(tzinfo=None)!r}, got {ep.scanned_at!r}"
    )
