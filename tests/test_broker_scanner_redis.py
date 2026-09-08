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
        .not_valid_before(datetime.now(timezone.utc).replace(tzinfo=None))
        .not_valid_after((datetime.now(timezone.utc) + dt.timedelta(days=365)).replace(tzinfo=None))
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
# Phase 190 / TRIAGE-06: probe_mode decouples plaintext-vs-TLS from port number
# ---------------------------------------------------------------------------

def test_scan_one_redis_probe_mode_plaintext_on_nondefault_port():
    """probe_mode='plaintext' on port 26379 (non-default) takes the plaintext path."""
    with patch("quirk.scanner.broker_scanner._detect_redis_plaintext", return_value=True) as mock_detect:
        ep = scan_one_redis("r.example.com", 26379, timeout=5, probe_mode="plaintext")

    mock_detect.assert_called_once_with("r.example.com", 26379)
    assert ep is not None
    assert ep.protocol == "REDIS-PLAIN"
    assert ep.port == 26379
    assert ep.service_detail == "REDIS-PLAIN:26379"


def test_scan_one_redis_probe_mode_tls_on_nondefault_port():
    """probe_mode='tls' takes the raw ssl probe path, never consulting the port
    number for routing."""
    with patch(
        "quirk.scanner.broker_scanner._probe_redis_tls", return_value=None,
    ) as mock_tls, \
         patch("quirk.scanner.broker_scanner._detect_redis_plaintext") as mock_detect:
        ep = scan_one_redis("r.example.com", 26379, timeout=5, probe_mode="tls")

    mock_tls.assert_called_once()
    mock_detect.assert_not_called()
    assert ep is None


def test_scan_one_redis_probe_mode_none_matches_legacy_dispatch():
    """probe_mode omitted (None) reproduces the legacy port==6379/6380 dispatch
    byte-for-byte."""
    with patch("quirk.scanner.broker_scanner._detect_redis_plaintext", return_value=True):
        ep_6379 = scan_one_redis("r.example.com", 6379, timeout=5)
    assert ep_6379.protocol == "REDIS-PLAIN"

    with patch("quirk.scanner.broker_scanner._probe_redis_tls", return_value=None) as mock_tls:
        ep_6380 = scan_one_redis("r.example.com", 6380, timeout=5)
    mock_tls.assert_called_once()
    assert ep_6380 is None


def test_scan_one_redis_unrecognized_probe_mode_raises():
    """An unrecognized probe_mode value raises rather than silently falling through."""
    with pytest.raises(ValueError):
        scan_one_redis("r.example.com", 6379, timeout=5, probe_mode="bogus")


# ---------------------------------------------------------------------------
# Phase 190 / TRIAGE-06: additive per-host port overrides in scan_redis_targets
# ---------------------------------------------------------------------------

def test_scan_redis_targets_port_overrides_additive():
    """port_overrides adds the override port to the 6379/6380 defaults (RQ-1),
    probed in both modes."""
    probed = []

    def fake_scan_one(host, port, timeout, logger=None, session_start=None, *, allow_cleartext=False, probe_mode=None):
        probed.append((host, port, probe_mode))
        return None

    with patch("quirk.scanner.broker_scanner.scan_one_redis", side_effect=fake_scan_one):
        scan_redis_targets(hosts=["h"], port_overrides={"h": [26380]})

    ports_probed = {p for _, p, _ in probed}
    assert {6379, 6380, 26380}.issubset(ports_probed), f"Expected defaults + override, got {ports_probed}"
    modes_for_override = {m for _, p, m in probed if p == 26380}
    assert modes_for_override == {"plaintext", "tls"}


def test_scan_redis_targets_port_overrides_none_matches_today():
    """port_overrides=None reproduces today's exact task list."""
    probed_default = []
    probed_none = []

    def fake_default(host, port, timeout, logger=None, session_start=None, *, allow_cleartext=False, probe_mode=None):
        probed_default.append((host, port, probe_mode))
        return None

    with patch("quirk.scanner.broker_scanner.scan_one_redis", side_effect=fake_default):
        scan_redis_targets(hosts=["h"])

    def fake_none(host, port, timeout, logger=None, session_start=None, *, allow_cleartext=False, probe_mode=None):
        probed_none.append((host, port, probe_mode))
        return None

    with patch("quirk.scanner.broker_scanner.scan_one_redis", side_effect=fake_none):
        scan_redis_targets(hosts=["h"], port_overrides=None)

    assert sorted(probed_default) == sorted(probed_none)
    assert all(mode is None for _, _, mode in probed_default)


def test_scan_redis_targets_port_overrides_no_duplicate_on_default_port():
    """An override port duplicating a default is not re-probed."""
    probed = []

    def fake_scan_one(host, port, timeout, logger=None, session_start=None, *, allow_cleartext=False, probe_mode=None):
        probed.append((host, port, probe_mode))
        return None

    with patch("quirk.scanner.broker_scanner.scan_one_redis", side_effect=fake_scan_one):
        scan_redis_targets(hosts=["h"], port_overrides={"h": [6379]})

    port_6379_hits = [p for p in probed if p[1] == 6379]
    assert len(port_6379_hits) == 1, f"Expected exactly one probe of duplicated default port, got {port_6379_hits}"
    assert port_6379_hits[0][2] is None


def test_scan_redis_targets_foreign_family_port_no_crash():
    """A foreign-family port (e.g. RabbitMQ's 25671) passed into scan_redis_targets
    harmlessly probes and finds nothing — no exception, no false endpoint."""
    with patch("quirk.scanner.broker_scanner._detect_redis_plaintext", return_value=False), \
         patch("quirk.scanner.broker_scanner._probe_redis_tls", return_value=None):
        results = scan_redis_targets(hosts=["h"], port_overrides={"h": [25671]})

    assert results == [], f"Expected no endpoints for foreign-family port, got {results}"


def _error_only_redis_tls_ep(host, port, msg="handshake failure"):
    """The exact shape the real _probe_redis_tls produces on a non-refused
    failure (ssl.SSLError / timeout / RST): protocol=REDIS-TLS, scan_error set,
    no tls_version/cipher evidence."""
    from quirk.models import CryptoEndpoint
    ep = CryptoEndpoint(host=host, port=port, protocol="REDIS-TLS")
    ep.scan_error = msg
    return ep


def test_scan_one_redis_override_tls_discards_error_only_endpoint():
    """Phase 190 CR-01: a speculative override-port TLS probe (probe_mode="tls")
    whose _probe_redis_tls fails non-refused must find NOTHING — no persisted
    REDIS-TLS error row, no redis-py enrichment attempt."""
    with patch(
        "quirk.scanner.broker_scanner._probe_redis_tls",
        side_effect=lambda h, p, t: _error_only_redis_tls_ep(h, p),
    ), patch("quirk.scanner.broker_scanner._enrich_redis_config") as enrich:
        result = scan_one_redis("h", 29092, timeout=5, probe_mode="tls")

    assert result is None, f"Expected None for errored override probe, got {result}"
    enrich.assert_not_called()


def test_scan_one_redis_default_port_tls_error_endpoint_preserved():
    """Phase 190 CR-01 non-regression: the legacy default-port path
    (probe_mode=None, port 6380) still reports real Redis TLS probe errors."""
    with patch(
        "quirk.scanner.broker_scanner._probe_redis_tls",
        side_effect=lambda h, p, t: _error_only_redis_tls_ep(h, p, "ssl handshake alert"),
    ), patch("quirk.scanner.broker_scanner._enrich_redis_config", return_value={}):
        result = scan_one_redis("h", 6380, timeout=5, probe_mode=None)

    assert result is not None, "Default-port REDIS-TLS error reporting must be preserved"
    assert result.protocol == "REDIS-TLS"
    assert result.scan_error == "ssl handshake alert"


def test_scan_redis_targets_kafka_plaintext_override_port_no_spurious_redis_tls_row():
    """Phase 190 CR-01 flagship TRIAGE-06 scenario: declaring the chaos lab's
    Kafka plaintext port (host:29092) must NOT persist a spurious REDIS-TLS
    error endpoint from the Redis driver's cross-family TLS handshake failure."""
    with patch("quirk.scanner.broker_scanner._detect_redis_plaintext", return_value=False), \
         patch(
             "quirk.scanner.broker_scanner._probe_redis_tls",
             side_effect=lambda h, p, t: (
                 None if p in (6379, 6380)
                 else _error_only_redis_tls_ep(h, p, "wrong version number")
             ),
         ):
        results = scan_redis_targets(hosts=["h"], port_overrides={"h": [29092]})

    assert results == [], (
        f"Expected no endpoints — cross-family override probe must find nothing, got {results}"
    )


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
