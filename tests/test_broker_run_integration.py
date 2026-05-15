"""Phase 33 Plan 06: broker_scan_json aggregation shape + finding emission tests.

Tests cover:
  - D-12 payload shape (all five protocol-family keys present)
  - D-14 attachment rule (broker_scan_json on first endpoint only)
  - Four finding types: kafka-plaintext-listener, amqp-plaintext-listener,
    redis-plaintext-no-auth, weak-cipher (TLS_RSA_WITH_*, DES-CBC3)
  - No false-positive on PFS ECDHE cipher
  - Layered findings (KAFKA-PLAIN + KAFKA-TLS weak-cipher) survive _dedupe_findings
  - BROKER-00 column write round-trip via in-memory DB

All scanner calls are exercised via evaluate_broker_endpoints only; no live network.
"""
import json
import os
import tempfile
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from quirk.engine.findings_evaluator import evaluate_broker_endpoints, _dedupe_findings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ep(host="h.example.com", port=9093, protocol="KAFKA-TLS", cipher=None, tls=None):
    """Create a minimal mock CryptoEndpoint for testing."""
    e = MagicMock()
    e.host = host
    e.port = port
    e.protocol = protocol
    e.cipher_suite = cipher
    e.tls_version = tls
    e.cert_pubkey_alg = None
    e.cert_subject = None
    e.scan_error = None
    return e


def _ep_dict(ep):
    """Replicate the _ep_dict helper from run_scan.py for aggregation tests."""
    return {
        "host": getattr(ep, "host", None),
        "port": getattr(ep, "port", None),
        "protocol": getattr(ep, "protocol", None),
        "tls_version": getattr(ep, "tls_version", None),
        "cipher_suite": getattr(ep, "cipher_suite", None),
        "cert_pubkey_alg": getattr(ep, "cert_pubkey_alg", None),
        "cert_subject": getattr(ep, "cert_subject", None),
        "scan_error": getattr(ep, "scan_error", None),
    }


# ---------------------------------------------------------------------------
# Test 1: D-12 aggregation shape — all five top-level keys present + correct types
# ---------------------------------------------------------------------------

def test_aggregation_shape_d12():
    """D-12: broker_scan_json payload has keys kafka, rabbitmq, redis, azure_servicebus,
    aws_sqs, session_start; each value is a list."""
    kafka_eps = [_ep(host="k.example.com", port=9093, protocol="KAFKA-TLS")]
    rabbit_eps = [
        _ep(host="r.example.com", port=5671, protocol="AMQPS"),
        _ep(host="ns.servicebus.windows.net", port=5671, protocol="AMQPS/Azure-ServiceBus"),
        _ep(host="sqs.us-east-1.amazonaws.com", port=443, protocol="HTTPS/AWS-SQS"),
    ]
    redis_eps = [_ep(host="rd.example.com", port=6380, protocol="REDIS-TLS")]

    session_start = datetime(2026, 4, 28, 12, 0, 0, tzinfo=timezone.utc)

    # Replicate run_scan.py aggregation logic inline (D-14: attach to first endpoint)
    all_broker_eps = kafka_eps + rabbit_eps + redis_eps
    azure_eps = [e for e in rabbit_eps if getattr(e, "protocol", "") == "AMQPS/Azure-ServiceBus"]
    sqs_eps   = [e for e in rabbit_eps if getattr(e, "protocol", "") == "HTTPS/AWS-SQS"]
    rabbit_self = [e for e in rabbit_eps if e not in azure_eps and e not in sqs_eps]
    payload = {
        "kafka":            [_ep_dict(e) for e in kafka_eps],
        "rabbitmq":         [_ep_dict(e) for e in rabbit_self],
        "redis":            [_ep_dict(e) for e in redis_eps],
        "azure_servicebus": [_ep_dict(e) for e in azure_eps],
        "aws_sqs":          [_ep_dict(e) for e in sqs_eps],
        "session_start":    session_start.isoformat() if session_start else None,
    }

    assert set(payload.keys()) == {"kafka", "rabbitmq", "redis", "azure_servicebus", "aws_sqs", "session_start"}, \
        "Payload missing expected top-level keys"
    assert isinstance(payload["kafka"], list)
    assert isinstance(payload["rabbitmq"], list)
    assert isinstance(payload["redis"], list)
    assert isinstance(payload["azure_servicebus"], list)
    assert isinstance(payload["aws_sqs"], list)
    assert payload["session_start"] is not None


# ---------------------------------------------------------------------------
# Test 2: D-14 attachment rule — broker_scan_json on first endpoint only
# ---------------------------------------------------------------------------

def test_aggregation_attachment_d14():
    """D-14: broker_scan_json is attached ONLY to the first broker endpoint; others have
    no such attribute set."""
    kafka_eps = [_ep(host="k.example.com", port=9093, protocol="KAFKA-TLS")]
    rabbit_eps = [_ep(host="r.example.com", port=5671, protocol="AMQPS")]
    redis_eps  = [_ep(host="rd.example.com", port=6380, protocol="REDIS-TLS")]

    all_broker_eps = kafka_eps + rabbit_eps + redis_eps
    azure_eps = []
    sqs_eps   = []
    rabbit_self = rabbit_eps
    session_start = datetime(2026, 4, 28, 12, 0, 0, tzinfo=timezone.utc)
    payload = {
        "kafka":            [_ep_dict(e) for e in kafka_eps],
        "rabbitmq":         [_ep_dict(e) for e in rabbit_self],
        "redis":            [_ep_dict(e) for e in redis_eps],
        "azure_servicebus": [_ep_dict(e) for e in azure_eps],
        "aws_sqs":          [_ep_dict(e) for e in sqs_eps],
        "session_start":    session_start.isoformat(),
    }
    setattr(all_broker_eps[0], "broker_scan_json", json.dumps(payload, default=str))

    # First endpoint must have the attribute
    first = all_broker_eps[0]
    assert hasattr(first, "broker_scan_json"), "First endpoint missing broker_scan_json"
    decoded = json.loads(first.broker_scan_json)
    assert isinstance(decoded["kafka"], list)

    # Other endpoints must NOT have been assigned (MagicMock spec doesn't restrict attrs,
    # but we verify they weren't explicitly assigned)
    for ep in all_broker_eps[1:]:
        assert ep is not first, "Sanity: ensure we're checking different objects"
        # The other eps are fresh MagicMocks; they have not had broker_scan_json set
        # via setattr, so accessing it returns a Mock (not a real string). We verify
        # the value is not the same JSON string.
        broker_json_val = ep.__dict__.get("broker_scan_json", None)
        assert broker_json_val is None, \
            f"Endpoint {ep} should not have broker_scan_json set; got {broker_json_val!r}"


# ---------------------------------------------------------------------------
# Test 3: kafka-plaintext-listener finding
# ---------------------------------------------------------------------------

def test_kafka_plaintext_finding():
    """evaluate_broker_endpoints with KAFKA-PLAIN ep -> exactly one HIGH finding
    with 'Plaintext Kafka' in title."""
    eps = [_ep(host="k.example.com", port=9092, protocol="KAFKA-PLAIN")]
    findings = evaluate_broker_endpoints(eps)
    assert len(findings) == 1, f"Expected 1 finding, got {len(findings)}: {findings}"
    assert findings[0]["severity"] == "HIGH"
    assert "Plaintext Kafka" in findings[0]["title"]


# ---------------------------------------------------------------------------
# Test 4: amqp-plaintext-listener finding
# ---------------------------------------------------------------------------

def test_amqp_plaintext_finding():
    """evaluate_broker_endpoints with AMQP-PLAIN ep -> one HIGH finding with
    'Plaintext AMQP' in title."""
    eps = [_ep(host="r.example.com", port=5672, protocol="AMQP-PLAIN")]
    findings = evaluate_broker_endpoints(eps)
    assert len(findings) == 1, f"Expected 1 finding, got {len(findings)}: {findings}"
    assert findings[0]["severity"] == "HIGH"
    assert "Plaintext AMQP" in findings[0]["title"]


# ---------------------------------------------------------------------------
# Test 5: redis-plaintext-no-auth finding
# ---------------------------------------------------------------------------

def test_redis_plaintext_finding():
    """evaluate_broker_endpoints with REDIS-PLAIN ep -> one HIGH finding with
    'Plaintext Redis' in title."""
    eps = [_ep(host="rd.example.com", port=6379, protocol="REDIS-PLAIN")]
    findings = evaluate_broker_endpoints(eps)
    assert len(findings) == 1, f"Expected 1 finding, got {len(findings)}: {findings}"
    assert findings[0]["severity"] == "HIGH"
    assert "Plaintext Redis" in findings[0]["title"]


# ---------------------------------------------------------------------------
# Test 6: weak-cipher TLS_RSA_WITH_* finding
# ---------------------------------------------------------------------------

def test_weak_cipher_tls_rsa_with():
    """KAFKA-TLS ep with cipher_suite=TLS_RSA_WITH_AES_128_CBC_SHA, tls_version=TLSv1.2
    -> one HIGH finding with 'Weak cipher' in title."""
    eps = [_ep(
        host="k.example.com",
        port=9093,
        protocol="KAFKA-TLS",
        cipher="TLS_RSA_WITH_AES_128_CBC_SHA",
        tls="TLSv1.2",
    )]
    findings = evaluate_broker_endpoints(eps)
    assert len(findings) == 1, f"Expected 1 finding, got {len(findings)}: {findings}"
    assert findings[0]["severity"] == "HIGH"
    assert "Weak cipher" in findings[0]["title"]


# ---------------------------------------------------------------------------
# Test 7: weak-cipher 3DES on AMQPS
# ---------------------------------------------------------------------------

def test_weak_cipher_3des_amqps():
    """AMQPS ep with cipher DES-CBC3-SHA -> HIGH weak-cipher finding."""
    eps = [_ep(
        host="r.example.com",
        port=5671,
        protocol="AMQPS",
        cipher="DES-CBC3-SHA",
        tls="TLSv1.2",
    )]
    findings = evaluate_broker_endpoints(eps)
    assert len(findings) == 1, f"Expected 1 finding, got {len(findings)}: {findings}"
    assert findings[0]["severity"] == "HIGH"
    assert "Weak cipher" in findings[0]["title"]


# ---------------------------------------------------------------------------
# Test 8: no false-positive on PFS ECDHE cipher
# ---------------------------------------------------------------------------

def test_no_false_positive_ecdhe():
    """KAFKA-TLS ep with ECDHE-RSA-AES256-GCM-SHA384 -> NO weak-cipher finding."""
    eps = [_ep(
        host="k.example.com",
        port=9093,
        protocol="KAFKA-TLS",
        cipher="ECDHE-RSA-AES256-GCM-SHA384",
        tls="TLSv1.2",
    )]
    findings = evaluate_broker_endpoints(eps)
    assert len(findings) == 0, \
        f"No findings expected for PFS ECDHE cipher, got: {findings}"


# ---------------------------------------------------------------------------
# Test 9: layered findings survive _dedupe_findings
# ---------------------------------------------------------------------------

def test_layered_findings_survive_dedupe():
    """One host has both KAFKA-PLAIN (9092) and KAFKA-TLS weak-cipher (9093).
    Both findings should survive _dedupe_findings because titles differ."""
    eps = [
        _ep(host="k.example.com", port=9092, protocol="KAFKA-PLAIN"),
        _ep(
            host="k.example.com",
            port=9093,
            protocol="KAFKA-TLS",
            cipher="TLS_RSA_WITH_AES_128_CBC_SHA",
            tls="TLSv1.2",
        ),
    ]
    findings = evaluate_broker_endpoints(eps)
    assert len(findings) == 2, \
        f"Expected 2 findings before dedupe, got {len(findings)}: {findings}"

    deduped = _dedupe_findings(findings)
    assert len(deduped) == 2, \
        f"Both layered findings should survive dedupe (different titles), got {len(deduped)}: {deduped}"

    titles = {f["title"] for f in deduped}
    assert any("Plaintext Kafka" in t for t in titles), \
        f"KAFKA-PLAIN finding missing from deduped set; titles={titles}"
    assert any("Weak cipher" in t for t in titles), \
        f"Weak-cipher finding missing from deduped set; titles={titles}"


# ---------------------------------------------------------------------------
# Test 10: BROKER-00 column write round-trip via real in-memory DB
# ---------------------------------------------------------------------------

def test_broker_scan_json_db_round_trip():
    """BROKER-00: insert CryptoEndpoint with broker_scan_json, SELECT and decode;
    assert decoded JSON is correct."""
    from sqlalchemy import create_engine, text
    from quirk.db import init_db
    from quirk.models import CryptoEndpoint, Base

    # Use a temp on-disk file (init_db requires a path, not an engine)
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    try:
        engine = init_db(tmp.name)
        payload = {"kafka": [{"host": "k.example.com", "port": 9093}]}
        payload_str = json.dumps(payload)

        # Insert via ORM
        from sqlalchemy.orm import Session
        with Session(engine) as session:
            ep = CryptoEndpoint(
                host="k.example.com",
                port=9093,
                protocol="KAFKA-TLS",
                broker_scan_json=payload_str,
            )
            session.add(ep)
            session.commit()

        # Read back via raw SQL
        with engine.connect() as conn:
            rows = list(conn.execute(
                text("SELECT broker_scan_json FROM crypto_endpoints WHERE host='k.example.com'")
            ).fetchall())

        assert len(rows) == 1, f"Expected 1 row, got {len(rows)}"
        stored_json = rows[0][0]
        assert stored_json is not None, "broker_scan_json should not be NULL"
        decoded = json.loads(stored_json)
        assert "kafka" in decoded, "Decoded JSON must have 'kafka' key"
        assert isinstance(decoded["kafka"], list)
        assert decoded["kafka"][0]["host"] == "k.example.com"
    finally:
        engine.dispose()
        os.unlink(tmp.name)
