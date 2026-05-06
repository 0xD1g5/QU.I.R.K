"""Tests for broker_scanner.py Kafka functions (KAFKA-01..04 + STRUCT-01).

Phase 33 Plan 03: covers scan_kafka_targets, scan_one_kafka, _detect_kafka_plaintext,
_enrich_kafka_admin, _scan_one_sslyze_kafka.

All network calls are mocked — no live network required.
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

pytest.importorskip("quirk.scanner.broker_scanner", reason="Phase 33 Plan 03")

from quirk.scanner.broker_scanner import (
    scan_kafka_targets,
    scan_one_kafka,
    _detect_kafka_plaintext,
    _enrich_kafka_admin,
    _scan_one_sslyze_kafka,
)

# ---------------------------------------------------------------------------
# sslyze enums — imported softly so test collection works when sslyze absent
# ---------------------------------------------------------------------------
try:
    from sslyze import ServerScanStatusEnum, ScanCommandAttemptStatusEnum
    _SSLYZE_ENUMS_AVAILABLE = True
except ImportError:
    _SSLYZE_ENUMS_AVAILABLE = False

    class ServerScanStatusEnum:  # noqa: N801
        COMPLETED = "COMPLETED"
        ERROR_NO_CONNECTIVITY = "ERROR_NO_CONNECTIVITY"

    class ScanCommandAttemptStatusEnum:  # noqa: N801
        COMPLETED = "COMPLETED"
        ERROR = "ERROR"


# ---------------------------------------------------------------------------
# Mock helper constructors
# ---------------------------------------------------------------------------

def _make_mock_sslyze_result(
    tls_version: str = "TLSv1.2",
    cipher: str = "AES256-SHA",
    completed: bool = True,
) -> MagicMock:
    """Build a mock sslyze ServerScanResult for broker scanner tests.

    Mirrors _make_mock_sslyze_result from test_email_scanner.py.
    """
    result = MagicMock()
    if completed:
        result.scan_status = ServerScanStatusEnum.COMPLETED
    else:
        result.scan_status = ServerScanStatusEnum.ERROR_NO_CONNECTIVITY

    # Cipher suite mock — TLS 1.2 path
    suite = MagicMock()
    suite.cipher_suite.name = cipher

    attempt = MagicMock()
    attempt.status = ScanCommandAttemptStatusEnum.COMPLETED
    attempt.result.accepted_cipher_suites = [suite]
    result.scan_result.tls_1_2_cipher_suites = attempt

    # TLS 1.3 cipher suites (empty for defaults)
    attempt_13 = MagicMock()
    attempt_13.status = ScanCommandAttemptStatusEnum.COMPLETED
    attempt_13.result.accepted_cipher_suites = []
    result.scan_result.tls_1_3_cipher_suites = attempt_13

    # Certificate info mock
    cert = MagicMock()
    cert.subject.rfc4514_string.return_value = "CN=kafka.example.com"
    cert.issuer.rfc4514_string.return_value = "CN=TestCA"
    cert.public_key.return_value.key_size = 2048
    cert.signature_hash_algorithm.name = "sha256"

    san_ext = MagicMock()
    san_ext.value.get_values_for_type.return_value = ["kafka.example.com"]
    cert.extensions.get_extension_for_class.return_value = san_ext

    deployment = MagicMock()
    deployment.received_certificate_chain = [cert]

    cert_attempt = MagicMock()
    cert_attempt.status = ScanCommandAttemptStatusEnum.COMPLETED
    cert_attempt.result.certificate_deployments = [deployment]
    result.scan_result.certificate_info = cert_attempt

    return result


def _make_mock_sslyze_scanner(result: MagicMock) -> MagicMock:
    """Return a MagicMock SslyzeScanner whose get_results() yields [result]."""
    scanner = MagicMock()
    scanner.queue_scans.return_value = None
    scanner.get_results.return_value = iter([result])
    return scanner


# ---------------------------------------------------------------------------
# KAFKA-01: sslyze probe returns KAFKA-TLS endpoint
# ---------------------------------------------------------------------------

def test_sslyze_probe_returns_kafka_tls_endpoint():
    """KAFKA-01: _scan_one_sslyze_kafka with mocked SslyzeScanner returns ep.protocol == 'KAFKA-TLS'."""
    mock_result = _make_mock_sslyze_result(tls_version="TLSv1.2", cipher="AES256-SHA")
    mock_scanner_cls = MagicMock()
    mock_scanner = _make_mock_sslyze_scanner(mock_result)
    mock_scanner_cls.return_value = mock_scanner

    with patch("quirk.scanner.broker_scanner.SSLYZE_AVAILABLE", True), \
         patch("quirk.scanner.broker_scanner.SslyzeScanner", mock_scanner_cls), \
         patch("quirk.scanner.broker_scanner.ServerNetworkConfiguration", MagicMock()), \
         patch("quirk.scanner.broker_scanner.ServerNetworkLocation", MagicMock()), \
         patch("quirk.scanner.broker_scanner.ServerScanRequest", MagicMock()), \
         patch("quirk.scanner.broker_scanner.ScanCommand", MagicMock()):
        ep = _scan_one_sslyze_kafka("kafka.example.com", 9093, timeout=5)

    assert ep is not None, "_scan_one_sslyze_kafka must return a CryptoEndpoint on success"
    assert ep.protocol == "KAFKA-TLS", f"Expected protocol='KAFKA-TLS', got {ep.protocol!r}"
    assert ep.host == "kafka.example.com"
    assert ep.port == 9093


# ---------------------------------------------------------------------------
# KAFKA-02: plaintext detection
# ---------------------------------------------------------------------------

def test_detect_kafka_plaintext_true_on_connect():
    """KAFKA-02: _detect_kafka_plaintext returns True when socket.create_connection succeeds."""
    mock_sock = MagicMock()
    mock_ctx = MagicMock()
    mock_ctx.__enter__ = MagicMock(return_value=mock_sock)
    mock_ctx.__exit__ = MagicMock(return_value=False)

    with patch("socket.create_connection", return_value=mock_ctx):
        result = _detect_kafka_plaintext("127.0.0.1", 9092)

    assert result is True


def test_detect_kafka_plaintext_false_on_refused():
    """KAFKA-02: _detect_kafka_plaintext returns False on ConnectionRefusedError."""
    with patch("socket.create_connection", side_effect=ConnectionRefusedError()):
        result = _detect_kafka_plaintext("127.0.0.1", 9092)

    assert result is False


# ---------------------------------------------------------------------------
# KAFKA-02: scan_one_kafka on port 9092
# ---------------------------------------------------------------------------

def test_scan_one_kafka_9092_returns_plain_endpoint():
    """KAFKA-02: scan_one_kafka on port 9092 returns ep.protocol == 'KAFKA-PLAIN' when listener detected."""
    with patch("quirk.scanner.broker_scanner._detect_kafka_plaintext", return_value=True):
        ep = scan_one_kafka("kafka.example.com", 9092, timeout=5)

    assert ep is not None, "scan_one_kafka must return endpoint when plaintext detected"
    assert ep.protocol == "KAFKA-PLAIN", f"Expected 'KAFKA-PLAIN', got {ep.protocol!r}"
    assert ep.service_detail == "KAFKA-PLAIN:9092", (
        f"Expected service_detail='KAFKA-PLAIN:9092', got {ep.service_detail!r}"
    )


def test_scan_one_kafka_9092_returns_none_when_no_listener():
    """KAFKA-02: scan_one_kafka on port 9092 returns None when no plaintext listener."""
    with patch("quirk.scanner.broker_scanner._detect_kafka_plaintext", return_value=False):
        ep = scan_one_kafka("kafka.example.com", 9092, timeout=5)

    assert ep is None, "scan_one_kafka must return None when plaintext detection fails"


# ---------------------------------------------------------------------------
# KAFKA-03: scan_kafka_targets profile gating
# ---------------------------------------------------------------------------

def test_scan_kafka_targets_standard_profile_includes_9094():
    """KAFKA-03: scan_kafka_targets(profile='standard') schedules probes on ports 9092, 9093, 9094."""
    probed_ports = []

    def fake_scan_one_kafka(host, port, timeout, logger=None, session_start=None):
        probed_ports.append(port)
        return None

    with patch("quirk.scanner.broker_scanner.scan_one_kafka", side_effect=fake_scan_one_kafka):
        scan_kafka_targets(["kafka.example.com"], timeout=5, profile="standard")

    assert 9094 in probed_ports, f"Port 9094 not probed in standard profile; probed: {probed_ports}"
    assert {9092, 9093, 9094}.issubset(set(probed_ports)), (
        f"Expected 9092, 9093, 9094 all probed; got {set(probed_ports)}"
    )


def test_scan_kafka_targets_quick_profile_excludes_9094():
    """KAFKA-03: scan_kafka_targets(profile='quick') does NOT probe port 9094."""
    probed_ports = []

    def fake_scan_one_kafka(host, port, timeout, logger=None, session_start=None):
        probed_ports.append(port)
        return None

    with patch("quirk.scanner.broker_scanner.scan_one_kafka", side_effect=fake_scan_one_kafka):
        scan_kafka_targets(["kafka.example.com"], timeout=5, profile="quick")

    assert 9094 not in probed_ports, f"Port 9094 should NOT be probed in quick profile; probed: {probed_ports}"
    assert set(probed_ports) == {9092, 9093}, (
        f"Expected only 9092 and 9093 for quick profile; got {set(probed_ports)}"
    )


# ---------------------------------------------------------------------------
# KAFKA-04: enrichment absent (library not available)
# ---------------------------------------------------------------------------

def test_enrich_kafka_admin_returns_empty_when_unavailable():
    """KAFKA-04 absent: _enrich_kafka_admin returns {} when KAFKA_AVAILABLE is False."""
    with patch("quirk.scanner.broker_scanner.KAFKA_AVAILABLE", False):
        result = _enrich_kafka_admin("kafka.example.com", 9093)

    assert result == {}, f"Expected empty dict, got {result!r}"


# ---------------------------------------------------------------------------
# KAFKA-04: enrichment present (library available + mocked)
# ---------------------------------------------------------------------------

def test_enrich_kafka_admin_returns_dict_when_available():
    """KAFKA-04 present: _enrich_kafka_admin returns enrichment dict from describe_configs."""
    # Build mock entry with ssl.enabled.protocols
    mock_entry = MagicMock()
    mock_entry.name = "ssl.enabled.protocols"
    mock_entry.value = "TLSv1.2,TLSv1.3"

    mock_resource = MagicMock()
    describe_result = {mock_resource: [mock_entry]}

    mock_admin = MagicMock()
    mock_admin.describe_configs.return_value = describe_result
    mock_admin_cls = MagicMock(return_value=mock_admin)

    mock_config_resource = MagicMock()
    mock_config_resource_type = MagicMock()
    mock_config_resource_type.BROKER = "BROKER"

    with patch("quirk.scanner.broker_scanner.KAFKA_AVAILABLE", True), \
         patch("quirk.scanner.broker_scanner.KafkaAdminClient", mock_admin_cls), \
         patch("quirk.scanner.broker_scanner.ConfigResource", mock_config_resource), \
         patch("quirk.scanner.broker_scanner.ConfigResourceType", mock_config_resource_type):
        result = _enrich_kafka_admin("kafka.example.com", 9093)

    assert "ssl.enabled.protocols" in result, (
        f"Expected ssl.enabled.protocols in enrichment; got {result!r}"
    )
    assert result["ssl.enabled.protocols"] == "TLSv1.2,TLSv1.3"


# ---------------------------------------------------------------------------
# D-08: enrichment swallows exceptions
# ---------------------------------------------------------------------------

def test_enrich_kafka_admin_swallows_exceptions():
    """D-08: KafkaAdminClient.describe_configs raises RuntimeError => _enrich_kafka_admin returns {}."""
    mock_admin = MagicMock()
    mock_admin.describe_configs.side_effect = RuntimeError("connection refused")
    mock_admin_cls = MagicMock(return_value=mock_admin)

    with patch("quirk.scanner.broker_scanner.KAFKA_AVAILABLE", True), \
         patch("quirk.scanner.broker_scanner.KafkaAdminClient", mock_admin_cls), \
         patch("quirk.scanner.broker_scanner.ConfigResource", MagicMock()), \
         patch("quirk.scanner.broker_scanner.ConfigResourceType", MagicMock()):
        result = _enrich_kafka_admin("kafka.example.com", 9093)

    assert result == {}, f"Expected empty dict on exception, got {result!r}"


# ---------------------------------------------------------------------------
# STRUCT-01: session_start propagation
# ---------------------------------------------------------------------------

def test_session_start_propagation():
    """STRUCT-01: scan_one_kafka(host, 9092, session_start=fixed_time) sets ep.scanned_at == fixed_time (naive)."""
    fixed_time = datetime(2026, 1, 1, 12, 0, 0)

    with patch("quirk.scanner.broker_scanner._detect_kafka_plaintext", return_value=True):
        ep = scan_one_kafka("kafka.example.com", 9092, timeout=5, session_start=fixed_time)

    assert ep is not None
    assert ep.scanned_at == fixed_time.replace(tzinfo=None), (
        f"Expected scanned_at={fixed_time.replace(tzinfo=None)!r}, got {ep.scanned_at!r}"
    )


# ---------------------------------------------------------------------------
# STRUCT-01: no naked datetime.now() in broker_scanner source
# ---------------------------------------------------------------------------

def test_no_naked_datetime_now_in_broker_scanner():
    """STRUCT-01: every datetime.now() call in broker_scanner.py must be guarded by 'session_start or'."""
    import inspect
    import quirk.scanner.broker_scanner as mod

    src = inspect.getsource(mod)
    code_lines = [ln for ln in src.splitlines() if not ln.lstrip().startswith("#")]
    bad = [ln for ln in code_lines if "datetime.now(" in ln and "session_start or" not in ln]
    assert not bad, f"Naked datetime.now() found in broker_scanner.py: {bad}"
