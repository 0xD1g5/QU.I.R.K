"""INFRA-03 Nyquist coverage — 6 scanner entry points × 3 scenarios = 18 tests.

See REQUIREMENTS.md INFRA-03 and 37-CONTEXT.md D-03. This is the single auditable
artifact for INFRA-03; existing scenario tests in test_email_scanner.py and
test_broker_scanner_*.py cover finer-grained slices and are intentionally not
duplicated here.

STRUCT-01 lock: every test passes session_start=SESSION_START (a fixed UTC datetime)
so per-scanner datetime drift cannot regress.

Mocking strategy:
- happy:           patch the per-host helper (scan_one_*) to return a CryptoEndpoint
                   with tls_version set, simulating a successful TLS handshake.
- refused:         patch socket.create_connection to raise ConnectionRefusedError AND
                   patch SSLYZE_AVAILABLE to False, exercising the real graceful-
                   degradation paths through _detect_*_plaintext / _scan_one_sslyze_*.
- plaintext-only:  patch the per-host helper to return only the plaintext-port
                   CryptoEndpoint (protocol="*-PLAIN" / "AMQP-PLAIN", no tls_version)
                   and None on TLS ports.

Azure Service Bus (RABBIT-04) and AWS SQS (RABBIT-05) are dispatched as parameters
to scan_rabbitmq_targets (azure_namespaces=, sqs_regions=); they do not have
separate public functions.
"""
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from quirk.models import CryptoEndpoint
from quirk.scanner.email_scanner import scan_email_targets
from quirk.scanner.broker_scanner import (
    scan_kafka_targets,
    scan_rabbitmq_targets,
    scan_redis_targets,
)


SESSION_START = datetime(2026, 1, 1, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _tls_endpoint(host: str, port: int, protocol: str) -> CryptoEndpoint:
    """Build a CryptoEndpoint that looks like a successful TLS handshake."""
    ep = CryptoEndpoint(host=host, port=port, protocol=protocol)
    ep.tls_version = "TLSv1.3"
    ep.cipher_suite = "TLS_AES_256_GCM_SHA384"
    ep.service_detail = f"{protocol}:{port}"
    return ep


def _plain_endpoint(host: str, port: int, protocol: str) -> CryptoEndpoint:
    """Build a CryptoEndpoint that looks like a plaintext-only finding (no TLS)."""
    ep = CryptoEndpoint(host=host, port=port, protocol=protocol)
    ep.service_detail = f"{protocol}:{port}"
    return ep


# ---------------------------------------------------------------------------
# Email — scan_email_targets (3 tests)
# ---------------------------------------------------------------------------

def test_scan_email_targets_happy():
    # INFRA-03 / EMAIL-01 — happy path: SMTPS / IMAPS / POP3S handshakes succeed.
    def fake_scan_one_email(host, port, label, starttls, timeout, logger=None, session_start=None):
        return _tls_endpoint(host, port, label)

    with patch("quirk.scanner.email_scanner.scan_one_email", side_effect=fake_scan_one_email):
        eps = scan_email_targets(
            ["mail.example.com"], timeout=5, session_start=SESSION_START,
        )

    assert len(eps) >= 1
    assert any(getattr(ep, "tls_version", None) == "TLSv1.3" for ep in eps)


def test_scan_email_targets_refused():
    # INFRA-03 / EMAIL-08 — refused: every probe ConnectionRefusedError; no TLS-bearing endpoints.
    with patch("quirk.scanner.email_scanner.SSLYZE_AVAILABLE", False), \
         patch("socket.create_connection", side_effect=ConnectionRefusedError()):
        eps = scan_email_targets(
            ["unreachable.example.com"], timeout=2, session_start=SESSION_START,
        )

    # Email scanner returns endpoints even on refusal (with tls_blocker_reason set);
    # assert no endpoint carries a successful TLS version.
    tls_bearing = [ep for ep in eps if getattr(ep, "tls_version", None)]
    assert tls_bearing == [], f"Expected zero TLS-bearing endpoints on refusal, got {tls_bearing}"


def test_scan_email_targets_plaintext_only():
    # INFRA-03 / EMAIL-08 — plaintext-only: port 25 SMTP responds without STARTTLS.
    def fake_scan_one_email(host, port, label, starttls, timeout, logger=None, session_start=None):
        # Return a plaintext-only finding for port 25 (SMTP-STARTTLS where STARTTLS is absent).
        if port == 25:
            ep = _plain_endpoint(host, port, label)
            ep.tls_blocker_reason = "STARTTLS_UNSUPPORTED"
            return ep
        # All TLS-bearing ports refused.
        ep = CryptoEndpoint(host=host, port=port, protocol=label)
        ep.tls_blocker_reason = "CONNECTION_REFUSED"
        return ep

    with patch("quirk.scanner.email_scanner.scan_one_email", side_effect=fake_scan_one_email):
        eps = scan_email_targets(
            ["legacy-mta.example.com"], timeout=5, session_start=SESSION_START,
        )

    plaintext_25 = [ep for ep in eps if getattr(ep, "port", None) == 25]
    assert plaintext_25, "Expected at least one plaintext SMTP-25 finding"
    assert all(getattr(ep, "tls_version", None) is None for ep in plaintext_25)


# ---------------------------------------------------------------------------
# Kafka — scan_kafka_targets (3 tests)
# ---------------------------------------------------------------------------

def test_scan_kafka_targets_happy():
    # INFRA-03 / KAFKA-01 — happy: TLS handshake on 9093/9094 succeeds.
    def fake_scan_one_kafka(host, port, timeout, logger=None, session_start=None):
        if port in (9093, 9094):
            return _tls_endpoint(host, port, "KAFKA-TLS")
        return None

    with patch("quirk.scanner.broker_scanner.scan_one_kafka", side_effect=fake_scan_one_kafka):
        eps = scan_kafka_targets(
            ["kafka.example.com"], timeout=5, profile="standard", session_start=SESSION_START,
        )

    tls_eps = [ep for ep in eps if getattr(ep, "tls_version", None)]
    assert len(tls_eps) >= 1, f"Expected ≥1 TLS endpoint on happy path, got {eps}"


def test_scan_kafka_targets_refused():
    # INFRA-03 / KAFKA-02 — refused: socket.create_connection raises; scanner returns [].
    with patch("quirk.scanner.broker_scanner.SSLYZE_AVAILABLE", False), \
         patch("socket.create_connection", side_effect=ConnectionRefusedError()):
        eps = scan_kafka_targets(
            ["unreachable.example.com"], timeout=2, session_start=SESSION_START,
        )

    assert eps == [], f"Expected empty list on refusal, got {eps}"


def test_scan_kafka_targets_plaintext_only():
    # INFRA-03 / KAFKA-02 — plaintext-only: 9092 PLAIN listener, 9093/9094 refused.
    def fake_scan_one_kafka(host, port, timeout, logger=None, session_start=None):
        if port == 9092:
            return _plain_endpoint(host, port, "KAFKA-PLAIN")
        return None

    with patch("quirk.scanner.broker_scanner.scan_one_kafka", side_effect=fake_scan_one_kafka):
        eps = scan_kafka_targets(
            ["plaintext-kafka.example.com"], timeout=5, session_start=SESSION_START,
        )

    plaintext_9092 = [ep for ep in eps if ep.protocol == "KAFKA-PLAIN" and ep.port == 9092]
    assert plaintext_9092, f"Expected KAFKA-PLAIN finding on 9092, got {eps}"
    assert all(getattr(ep, "tls_version", None) is None for ep in plaintext_9092)


# ---------------------------------------------------------------------------
# RabbitMQ — scan_rabbitmq_targets (3 tests, self-hosted)
# ---------------------------------------------------------------------------

def test_scan_rabbitmq_targets_happy():
    # INFRA-03 / RABBIT-01 — happy: AMQPS handshake on 5671 succeeds.
    def fake_scan_one_rabbitmq(host, port, timeout, *, protocol_label="AMQPS", logger=None, session_start=None):
        if port == 5671:
            return _tls_endpoint(host, port, protocol_label)
        return None

    with patch("quirk.scanner.broker_scanner.scan_one_rabbitmq", side_effect=fake_scan_one_rabbitmq), \
         patch("quirk.scanner.broker_scanner._enrich_rabbitmq_mgmt", return_value={}):
        eps = scan_rabbitmq_targets(
            ["rabbit.example.com"], timeout=5, session_start=SESSION_START,
        )

    tls_eps = [ep for ep in eps if getattr(ep, "tls_version", None)]
    assert len(tls_eps) >= 1


def test_scan_rabbitmq_targets_refused():
    # INFRA-03 / RABBIT-02 — refused: socket.create_connection raises; scanner returns [].
    with patch("quirk.scanner.broker_scanner.SSLYZE_AVAILABLE", False), \
         patch("quirk.scanner.broker_scanner._enrich_rabbitmq_mgmt", return_value={}), \
         patch("socket.create_connection", side_effect=ConnectionRefusedError()):
        eps = scan_rabbitmq_targets(
            ["unreachable.example.com"], timeout=2, session_start=SESSION_START,
        )

    assert eps == [], f"Expected empty list on refusal, got {eps}"


def test_scan_rabbitmq_targets_plaintext_only():
    # INFRA-03 / RABBIT-02 — plaintext-only: 5672 AMQP listener, 5671 refused.
    def fake_scan_one_rabbitmq(host, port, timeout, *, protocol_label="AMQPS", logger=None, session_start=None):
        if port == 5672:
            return _plain_endpoint(host, port, "AMQP-PLAIN")
        return None

    with patch("quirk.scanner.broker_scanner.scan_one_rabbitmq", side_effect=fake_scan_one_rabbitmq), \
         patch("quirk.scanner.broker_scanner._enrich_rabbitmq_mgmt", return_value={}):
        eps = scan_rabbitmq_targets(
            ["plaintext-rabbit.example.com"], timeout=5, session_start=SESSION_START,
        )

    plaintext = [ep for ep in eps if ep.protocol == "AMQP-PLAIN"]
    assert plaintext, f"Expected AMQP-PLAIN finding, got {eps}"
    assert all(getattr(ep, "tls_version", None) is None for ep in plaintext)


# ---------------------------------------------------------------------------
# Redis — scan_redis_targets (3 tests)
# ---------------------------------------------------------------------------

def test_scan_redis_targets_happy():
    # INFRA-03 / REDIS-01 — happy: TLS on 6380 succeeds.
    def fake_scan_one_redis(host, port, timeout, logger=None, session_start=None):
        if port == 6380:
            return _tls_endpoint(host, port, "REDIS-TLS")
        return None

    with patch("quirk.scanner.broker_scanner.scan_one_redis", side_effect=fake_scan_one_redis):
        eps = scan_redis_targets(
            ["redis.example.com"], timeout=5, session_start=SESSION_START,
        )

    tls_eps = [ep for ep in eps if getattr(ep, "tls_version", None)]
    assert len(tls_eps) >= 1


def test_scan_redis_targets_refused():
    # INFRA-03 / REDIS-02 — refused: socket.create_connection raises; scanner returns [].
    with patch("quirk.scanner.broker_scanner.SSLYZE_AVAILABLE", False), \
         patch("socket.create_connection", side_effect=ConnectionRefusedError()):
        eps = scan_redis_targets(
            ["unreachable.example.com"], timeout=2, session_start=SESSION_START,
        )

    assert eps == [], f"Expected empty list on refusal, got {eps}"


def test_scan_redis_targets_plaintext_only():
    # INFRA-03 / REDIS-02 — plaintext-only: 6379 PING/PONG without auth.
    def fake_scan_one_redis(host, port, timeout, logger=None, session_start=None):
        if port == 6379:
            return _plain_endpoint(host, port, "REDIS-PLAIN")
        return None

    with patch("quirk.scanner.broker_scanner.scan_one_redis", side_effect=fake_scan_one_redis):
        eps = scan_redis_targets(
            ["plaintext-redis.example.com"], timeout=5, session_start=SESSION_START,
        )

    plaintext = [ep for ep in eps if ep.protocol == "REDIS-PLAIN"]
    assert plaintext, f"Expected REDIS-PLAIN finding, got {eps}"
    assert all(getattr(ep, "tls_version", None) is None for ep in plaintext)


# ---------------------------------------------------------------------------
# Azure Service Bus — scan_rabbitmq_targets(azure_namespaces=...) (3 tests)
# Probe path: {namespace}.servicebus.windows.net:5671 with protocol_label="AMQPS/Azure-ServiceBus"
# ---------------------------------------------------------------------------

def test_azure_servicebus_probe_happy():
    # INFRA-03 / RABBIT-04 — happy: Azure SB AMQPS handshake succeeds on :5671.
    def fake_scan_one_rabbitmq(host, port, timeout, *, protocol_label="AMQPS", logger=None, session_start=None):
        if port == 5671 and "servicebus.windows.net" in host:
            return _tls_endpoint(host, port, protocol_label)
        return None

    with patch("quirk.scanner.broker_scanner.scan_one_rabbitmq", side_effect=fake_scan_one_rabbitmq), \
         patch("quirk.scanner.broker_scanner._enrich_rabbitmq_mgmt", return_value={}):
        eps = scan_rabbitmq_targets(
            hosts=[],
            azure_namespaces=["myns"],
            sqs_regions=[],
            timeout=5,
            session_start=SESSION_START,
        )

    azure_eps = [ep for ep in eps if "servicebus.windows.net" in (ep.host or "")]
    assert azure_eps, f"Expected Azure SB endpoint, got {eps}"
    assert any(ep.protocol == "AMQPS/Azure-ServiceBus" for ep in azure_eps)


def test_azure_servicebus_probe_refused():
    # INFRA-03 / RABBIT-04 — refused: Azure SB endpoint refuses the handshake; scanner returns [].
    with patch("quirk.scanner.broker_scanner.SSLYZE_AVAILABLE", False), \
         patch("quirk.scanner.broker_scanner._enrich_rabbitmq_mgmt", return_value={}), \
         patch("socket.create_connection", side_effect=ConnectionRefusedError()):
        eps = scan_rabbitmq_targets(
            hosts=[],
            azure_namespaces=["unreachable-ns"],
            sqs_regions=[],
            timeout=2,
            session_start=SESSION_START,
        )

    assert eps == [], f"Expected empty list on refusal, got {eps}"


def test_azure_servicebus_probe_plaintext_only():
    # INFRA-03 / RABBIT-04 — degenerate plaintext-only scenario: Azure Service Bus only
    # exposes AMQPS on :5671; there is NO plaintext analog (port 5672 is not part of the
    # Azure SB probe set). Per D-03, the test asserts the documented absence: probing a
    # nonexistent / TLS-refused Azure SB host yields zero findings without raising.
    def fake_scan_one_rabbitmq(host, port, timeout, *, protocol_label="AMQPS", logger=None, session_start=None):
        return None  # neither TLS handshake nor plaintext listener ever responds

    with patch("quirk.scanner.broker_scanner.scan_one_rabbitmq", side_effect=fake_scan_one_rabbitmq), \
         patch("quirk.scanner.broker_scanner._enrich_rabbitmq_mgmt", return_value={}):
        eps = scan_rabbitmq_targets(
            hosts=[],
            azure_namespaces=["empty-ns"],
            sqs_regions=[],
            timeout=5,
            session_start=SESSION_START,
        )

    assert eps == [], (
        f"Azure SB has no plaintext analog at 5671; expected empty result, got {eps}"
    )


# ---------------------------------------------------------------------------
# AWS SQS — scan_rabbitmq_targets(sqs_regions=...) (3 tests)
# Probe path: sqs.{region}.amazonaws.com:443 with protocol_label="HTTPS/AWS-SQS"
# ---------------------------------------------------------------------------

def test_aws_sqs_probe_happy():
    # INFRA-03 / RABBIT-05 — happy: AWS SQS HTTPS handshake succeeds on :443.
    def fake_scan_one_rabbitmq(host, port, timeout, *, protocol_label="AMQPS", logger=None, session_start=None):
        if port == 443 and host.startswith("sqs."):
            return _tls_endpoint(host, port, protocol_label)
        return None

    with patch("quirk.scanner.broker_scanner.scan_one_rabbitmq", side_effect=fake_scan_one_rabbitmq), \
         patch("quirk.scanner.broker_scanner._enrich_rabbitmq_mgmt", return_value={}):
        eps = scan_rabbitmq_targets(
            hosts=[],
            azure_namespaces=[],
            sqs_regions=["us-east-1"],
            timeout=5,
            session_start=SESSION_START,
        )

    sqs_eps = [ep for ep in eps if (ep.host or "").startswith("sqs.")]
    assert sqs_eps, f"Expected AWS SQS endpoint, got {eps}"
    assert any(ep.protocol == "HTTPS/AWS-SQS" for ep in sqs_eps)


def test_aws_sqs_probe_refused():
    # INFRA-03 / RABBIT-05 — refused: SQS regional endpoint refuses; scanner returns [].
    with patch("quirk.scanner.broker_scanner.SSLYZE_AVAILABLE", False), \
         patch("quirk.scanner.broker_scanner._enrich_rabbitmq_mgmt", return_value={}), \
         patch("socket.create_connection", side_effect=ConnectionRefusedError()):
        eps = scan_rabbitmq_targets(
            hosts=[],
            azure_namespaces=[],
            sqs_regions=["nope-region-1"],
            timeout=2,
            session_start=SESSION_START,
        )

    assert eps == [], f"Expected empty list on refusal, got {eps}"


def test_aws_sqs_probe_plaintext_only():
    # INFRA-03 / RABBIT-05 — degenerate plaintext-only scenario: AWS SQS is HTTPS-only on
    # :443. There is no plaintext analog in the SQS probe path. Per D-03, the test asserts
    # the documented absence: when TLS is refused, the scanner emits no false-positive
    # plaintext finding (since port 80 is NOT part of the SQS probe set).
    def fake_scan_one_rabbitmq(host, port, timeout, *, protocol_label="AMQPS", logger=None, session_start=None):
        return None

    with patch("quirk.scanner.broker_scanner.scan_one_rabbitmq", side_effect=fake_scan_one_rabbitmq), \
         patch("quirk.scanner.broker_scanner._enrich_rabbitmq_mgmt", return_value={}):
        eps = scan_rabbitmq_targets(
            hosts=[],
            azure_namespaces=[],
            sqs_regions=["plaintext-region"],
            timeout=5,
            session_start=SESSION_START,
        )

    assert eps == [], (
        f"AWS SQS is HTTPS-only on :443 with no plaintext analog; expected empty result, got {eps}"
    )
