"""Tests for broker_scanner.py RabbitMQ functions (RABBIT-01..05 + D-09 + STRUCT-01).

Phase 33 Plan 04: covers scan_rabbitmq_targets, scan_one_rabbitmq, _detect_amqp_plaintext,
_enrich_rabbitmq_mgmt, and cloud probe hostname construction.

All network calls are mocked — no live network required.
"""
import json
import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock, call

pytest.importorskip("quirk.scanner.broker_scanner", reason="Phase 33 Plan 04")

from quirk.scanner.broker_scanner import (
    scan_rabbitmq_targets,
    scan_one_rabbitmq,
    _detect_amqp_plaintext,
    _enrich_rabbitmq_mgmt,
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
# Mock helper constructors (mirrors test_broker_scanner_kafka.py)
# ---------------------------------------------------------------------------

def _make_mock_sslyze_result(
    tls_version: str = "TLSv1.2",
    cipher: str = "AES256-SHA",
    completed: bool = True,
) -> MagicMock:
    """Build a mock sslyze ServerScanResult for RabbitMQ broker scanner tests."""
    result = MagicMock()
    if completed:
        result.scan_status = ServerScanStatusEnum.COMPLETED
    else:
        result.scan_status = ServerScanStatusEnum.ERROR_NO_CONNECTIVITY

    suite = MagicMock()
    suite.cipher_suite.name = cipher

    attempt = MagicMock()
    attempt.status = ScanCommandAttemptStatusEnum.COMPLETED
    attempt.result.accepted_cipher_suites = [suite]
    result.scan_result.tls_1_2_cipher_suites = attempt

    attempt_13 = MagicMock()
    attempt_13.status = ScanCommandAttemptStatusEnum.COMPLETED
    attempt_13.result.accepted_cipher_suites = []
    result.scan_result.tls_1_3_cipher_suites = attempt_13

    cert = MagicMock()
    cert.subject.rfc4514_string.return_value = "CN=rabbitmq.example.com"
    cert.issuer.rfc4514_string.return_value = "CN=TestCA"
    cert.public_key.return_value.key_size = 2048
    cert.signature_hash_algorithm.name = "sha256"

    san_ext = MagicMock()
    san_ext.value.get_values_for_type.return_value = ["rabbitmq.example.com"]
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
# Test 1 — RABBIT-01: sslyze probe on 5671 returns ep.protocol == "AMQPS"
# ---------------------------------------------------------------------------

def test_scan_one_rabbitmq_5671_returns_amqps_endpoint():
    """RABBIT-01: scan_one_rabbitmq(host, 5671) returns ep.protocol == 'AMQPS'."""
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
        ep = scan_one_rabbitmq("rabbitmq.example.com", 5671, timeout=5)

    assert ep is not None, "scan_one_rabbitmq must return a CryptoEndpoint on success"
    assert ep.protocol == "AMQPS", f"Expected protocol='AMQPS', got {ep.protocol!r}"
    assert ep.host == "rabbitmq.example.com"
    assert ep.port == 5671


# ---------------------------------------------------------------------------
# Test 2 — RABBIT-02 positive: recv returns binary METHOD frame -> True
# ---------------------------------------------------------------------------

def test_detect_amqp_plaintext_true_on_binary_response():
    """RABBIT-02 positive: recv returns binary METHOD frame (non-empty) -> True.

    Proves len(data) > 0 logic — the response is a binary frame, not b'AMQP'-prefixed.
    """
    binary_method_frame = b"\x01\x00\x00\x00\x00\x00\xbe\x00\x0a\x00\x00"

    mock_sock = MagicMock()
    mock_sock.recv.return_value = binary_method_frame
    mock_ctx = MagicMock()
    mock_ctx.__enter__.return_value = mock_sock
    mock_ctx.__exit__.return_value = False

    with patch("socket.create_connection", return_value=mock_ctx):
        result = _detect_amqp_plaintext("rabbitmq.example.com", 5672)

    assert result is True, "Binary METHOD frame response should return True (len(data)>0)"


# ---------------------------------------------------------------------------
# Test 3 — RABBIT-02 empty bytes negative: recv returns b"" -> False
# ---------------------------------------------------------------------------

def test_detect_amqp_plaintext_false_on_empty_response():
    """RABBIT-02 empty bytes: recv returns b'' -> False.

    Proves len(data)>0 logic: empty response is not a positive detection, even though
    the old b'AMQP' prefix approach would have also returned False here.
    """
    mock_sock = MagicMock()
    mock_sock.recv.return_value = b""
    mock_ctx = MagicMock()
    mock_ctx.__enter__.return_value = mock_sock
    mock_ctx.__exit__.return_value = False

    with patch("socket.create_connection", return_value=mock_ctx):
        result = _detect_amqp_plaintext("rabbitmq.example.com", 5672)

    assert result is False, "Empty response should return False"


# ---------------------------------------------------------------------------
# Test 4 — RABBIT-02 ConnectionRefused negative: -> False
# ---------------------------------------------------------------------------

def test_detect_amqp_plaintext_false_on_connection_refused():
    """RABBIT-02 negative: ConnectionRefusedError -> False."""
    with patch("socket.create_connection", side_effect=ConnectionRefusedError()):
        result = _detect_amqp_plaintext("rabbitmq.example.com", 5672)

    assert result is False, "ConnectionRefusedError should return False"


# ---------------------------------------------------------------------------
# Test 5 — RABBIT-02 plaintext endpoint emission via scan_one_rabbitmq
# ---------------------------------------------------------------------------

def test_scan_one_rabbitmq_5672_returns_amqp_plain_endpoint():
    """RABBIT-02: scan_one_rabbitmq(host, 5672) with detection True -> ep.protocol == 'AMQP-PLAIN'."""
    with patch("quirk.scanner.broker_scanner._detect_amqp_plaintext", return_value=True):
        ep = scan_one_rabbitmq("rabbitmq.example.com", 5672, timeout=5)

    assert ep is not None, "scan_one_rabbitmq must return endpoint when AMQP detected"
    assert ep.protocol == "AMQP-PLAIN", f"Expected 'AMQP-PLAIN', got {ep.protocol!r}"
    assert ep.service_detail == "AMQP-PLAIN:5672", (
        f"Expected service_detail='AMQP-PLAIN:5672', got {ep.service_detail!r}"
    )


# ---------------------------------------------------------------------------
# Test 6 — RABBIT-03 success: _enrich_rabbitmq_mgmt returns version + listeners
# ---------------------------------------------------------------------------

def test_enrich_rabbitmq_mgmt_success():
    """RABBIT-03: urllib.request.urlopen returning JSON -> dict with rabbitmq_version."""
    payload = json.dumps({
        "rabbitmq_version": "3.12.0",
        "erlang_version": "25.0",
        "listeners": [{"protocol": "amqp", "port": 5672}],
        "node": "rabbit@node1",
    }).encode()

    mock_resp = MagicMock()
    mock_resp.read.return_value = payload
    mock_urlopen = MagicMock()
    mock_urlopen.return_value.__enter__.return_value = mock_resp

    with patch("quirk.scanner.broker_scanner.urllib.request.urlopen", mock_urlopen):
        result = _enrich_rabbitmq_mgmt("rabbitmq.example.com", 15672)

    assert result["rabbitmq_version"] == "3.12.0", (
        f"Expected rabbitmq_version='3.12.0', got {result.get('rabbitmq_version')!r}"
    )
    assert "erlang_version" in result
    assert "listeners" in result
    assert "node" in result


# ---------------------------------------------------------------------------
# Test 7 — RABBIT-03 401: urlopen raises HTTPError(401) -> {"mgmt_auth": "rejected_401"}
# ---------------------------------------------------------------------------

def test_enrich_rabbitmq_mgmt_401():
    """RABBIT-03 401: HTTPError code=401 -> returns {"mgmt_auth": "rejected_401"} (not an error)."""
    import urllib.error
    side_effect = urllib.error.HTTPError(
        url="http://rabbitmq.example.com:15672/api/overview",
        code=401,
        msg="Unauthorized",
        hdrs=None,
        fp=None,
    )

    with patch("quirk.scanner.broker_scanner.urllib.request.urlopen", side_effect=side_effect):
        result = _enrich_rabbitmq_mgmt("rabbitmq.example.com")

    assert result == {"mgmt_auth": "rejected_401"}, (
        f"Expected {{'mgmt_auth': 'rejected_401'}}, got {result!r}"
    )


# ---------------------------------------------------------------------------
# Test 8 — RABBIT-03 connection refused: urlopen raises URLError -> {}
# ---------------------------------------------------------------------------

def test_enrich_rabbitmq_mgmt_connection_refused():
    """RABBIT-03 connection failure: URLError -> returns {} (silent)."""
    import urllib.error
    side_effect = urllib.error.URLError(reason="Connection refused")

    with patch("quirk.scanner.broker_scanner.urllib.request.urlopen", side_effect=side_effect):
        result = _enrich_rabbitmq_mgmt("rabbitmq.example.com")

    assert result == {}, f"Expected empty dict on connection failure, got {result!r}"


# ---------------------------------------------------------------------------
# Test 9 — D-09: broker_scanner.py does NOT import the `requests` package
# ---------------------------------------------------------------------------

def test_no_requests_dependency():
    """D-09: broker_scanner.py must NOT import the requests package."""
    import inspect
    import quirk.scanner.broker_scanner as mod

    src = inspect.getsource(mod)
    for line in src.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("#"):
            continue
        assert not stripped.startswith("import requests"), (
            f"D-09: requests dep prohibited — found: {stripped!r}"
        )
        assert not stripped.startswith("from requests"), (
            f"D-09: requests dep prohibited — found: {stripped!r}"
        )


# ---------------------------------------------------------------------------
# Test 10 — RABBIT-04: Azure Service Bus hostname construction
# ---------------------------------------------------------------------------

def test_azure_servicebus_hostname_construction():
    """RABBIT-04: scan_rabbitmq_targets(azure_namespaces=['my-ns']) calls scan_one_rabbitmq
    with host='my-ns.servicebus.windows.net', port=5671, protocol_label='AMQPS/Azure-ServiceBus'.
    """
    with patch("quirk.scanner.broker_scanner.scan_one_rabbitmq") as mock_scan_one:
        mock_scan_one.return_value = None
        scan_rabbitmq_targets(hosts=[], azure_namespaces=["my-ns"], sqs_regions=[])

    azure_calls = [
        c for c in mock_scan_one.call_args_list
        if c.kwargs.get("protocol_label") == "AMQPS/Azure-ServiceBus"
    ]
    assert len(azure_calls) == 1, (
        f"Expected 1 Azure SB call, got {len(azure_calls)}: {mock_scan_one.call_args_list}"
    )
    assert azure_calls[0].args[0] == "my-ns.servicebus.windows.net", (
        f"Expected host='my-ns.servicebus.windows.net', got {azure_calls[0].args[0]!r}"
    )
    assert azure_calls[0].args[1] == 5671, (
        f"Expected port=5671, got {azure_calls[0].args[1]!r}"
    )


# ---------------------------------------------------------------------------
# Test 11 — RABBIT-05: AWS SQS hostname construction
# ---------------------------------------------------------------------------

def test_aws_sqs_hostname_construction():
    """RABBIT-05: scan_rabbitmq_targets(sqs_regions=['us-east-1']) calls scan_one_rabbitmq
    with host='sqs.us-east-1.amazonaws.com', port=443, protocol_label='HTTPS/AWS-SQS'.
    """
    with patch("quirk.scanner.broker_scanner.scan_one_rabbitmq") as mock_scan_one:
        mock_scan_one.return_value = None
        scan_rabbitmq_targets(hosts=[], azure_namespaces=[], sqs_regions=["us-east-1"])

    sqs_calls = [
        c for c in mock_scan_one.call_args_list
        if c.kwargs.get("protocol_label") == "HTTPS/AWS-SQS"
    ]
    assert len(sqs_calls) == 1, (
        f"Expected 1 SQS call, got {len(sqs_calls)}: {mock_scan_one.call_args_list}"
    )
    assert sqs_calls[0].args[0] == "sqs.us-east-1.amazonaws.com", (
        f"Expected host='sqs.us-east-1.amazonaws.com', got {sqs_calls[0].args[0]!r}"
    )
    assert sqs_calls[0].args[1] == 443, (
        f"Expected port=443, got {sqs_calls[0].args[1]!r}"
    )


# ---------------------------------------------------------------------------
# Test 12 — RABBIT-04: empty azure_namespaces yields zero cloud probes
# ---------------------------------------------------------------------------

def test_empty_azure_namespaces_yields_no_cloud_probes():
    """RABBIT-04 boundary: azure_namespaces=[] -> no Azure-tagged endpoints."""
    with patch("quirk.scanner.broker_scanner.scan_one_rabbitmq") as mock_scan_one:
        mock_scan_one.return_value = None
        scan_rabbitmq_targets(hosts=[], azure_namespaces=[], sqs_regions=[])

    azure_calls = [
        c for c in mock_scan_one.call_args_list
        if c.kwargs.get("protocol_label") == "AMQPS/Azure-ServiceBus"
    ]
    assert len(azure_calls) == 0, (
        f"Expected 0 Azure SB calls with empty list, got {len(azure_calls)}"
    )


# ---------------------------------------------------------------------------
# Test 13 — RABBIT-03 mgmt enrichment attachment
# ---------------------------------------------------------------------------

def test_mgmt_enrichment_attached_to_amqps_endpoint():
    """RABBIT-03: scan_rabbitmq_targets attaches _rabbit_mgmt_enrichment to the AMQPS endpoint."""
    from quirk.models import CryptoEndpoint

    # Create a stub AMQPS endpoint that scan_one_rabbitmq will return
    stub_ep = CryptoEndpoint(host="rabbitmq.example.com", port=5671, protocol="AMQPS")

    def fake_scan_one(host, port, timeout, *, protocol_label="AMQPS", logger=None, session_start=None):
        if port == 5671 and protocol_label == "AMQPS":
            return stub_ep
        return None

    enrichment_data = {"rabbitmq_version": "3.12.0"}

    with patch("quirk.scanner.broker_scanner.scan_one_rabbitmq", side_effect=fake_scan_one), \
         patch("quirk.scanner.broker_scanner._enrich_rabbitmq_mgmt", return_value=enrichment_data):
        results = scan_rabbitmq_targets(hosts=["rabbitmq.example.com"])

    amqps_eps = [ep for ep in results if ep.protocol == "AMQPS"]
    assert len(amqps_eps) == 1, f"Expected 1 AMQPS endpoint, got {len(amqps_eps)}"
    enriched_ep = amqps_eps[0]
    assert hasattr(enriched_ep, "_rabbit_mgmt_enrichment"), (
        "_rabbit_mgmt_enrichment attribute must be set on AMQPS endpoint"
    )
    assert enriched_ep._rabbit_mgmt_enrichment == enrichment_data, (
        f"Expected enrichment_data={enrichment_data!r}, got {enriched_ep._rabbit_mgmt_enrichment!r}"
    )


# ---------------------------------------------------------------------------
# Test 14 — STRUCT-01: session_start propagation
# ---------------------------------------------------------------------------

def test_session_start_propagation():
    """STRUCT-01: scan_one_rabbitmq(host, 5672, session_start=fixed_time) sets ep.scanned_at == fixed_time."""
    fixed_time = datetime(2026, 1, 1, 12, 0, 0)

    with patch("quirk.scanner.broker_scanner._detect_amqp_plaintext", return_value=True):
        ep = scan_one_rabbitmq("rabbitmq.example.com", 5672, timeout=5, session_start=fixed_time)

    assert ep is not None, "scan_one_rabbitmq must return endpoint when AMQP detected"
    assert ep.scanned_at == fixed_time.replace(tzinfo=None), (
        f"Expected scanned_at={fixed_time.replace(tzinfo=None)!r}, got {ep.scanned_at!r}"
    )
