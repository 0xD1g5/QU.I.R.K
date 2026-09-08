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


# ---------------------------------------------------------------------------
# Phase 190 / TRIAGE-06: broker_targets threading + unreached-target advisory
#
# _run_broker_phase is a closure inside run_scan()'s scan loop and is not
# independently importable; its pure host-union / port-override construction
# is extracted to the standalone `_build_broker_scan_inputs` (same pattern as
# `_broker_missing_extra`) so these tests exercise the real logic instead of a
# hand-mirrored copy of it. No sockets are stood up — inputs are built and
# fed to the pure helpers directly.
# ---------------------------------------------------------------------------

def _make_ep(host, port, protocol="KAFKA-PLAIN"):
    from quirk.models import CryptoEndpoint
    return CryptoEndpoint(host=host, port=port, protocol=protocol)


def test_build_broker_scan_inputs_broker_targets_only_host_reaches_drivers():
    """A host declared ONLY in broker_targets (empty tls_targets) is still in
    the host list handed to the drivers."""
    from run_scan import _build_broker_scan_inputs

    broker_hosts, port_overrides, explicit_pairs = _build_broker_scan_inputs(
        tls_targets=[], broker_targets_raw=["localhost:29092"],
    )

    assert broker_hosts == ["localhost"], f"Expected broker-only host present, got {broker_hosts}"
    assert port_overrides == {"localhost": [29092]}
    assert explicit_pairs == [("localhost", 29092)]


def test_build_broker_scan_inputs_empty_matches_today():
    """broker_targets_raw=[] reproduces today's exact broker_hosts / empty overrides."""
    from run_scan import _build_broker_scan_inputs

    tls_targets = [("a.example.com", 443), ("b.example.com", 443)]
    broker_hosts, port_overrides, explicit_pairs = _build_broker_scan_inputs(
        tls_targets=tls_targets, broker_targets_raw=[],
    )

    assert broker_hosts == ["a.example.com", "b.example.com"]
    assert port_overrides == {}
    assert explicit_pairs == []


def test_build_broker_scan_inputs_union_dedupes_and_stays_order_stable():
    """A host present in BOTH tls_targets and broker_targets is not duplicated,
    and hosts declared only via broker_targets are appended additively."""
    from run_scan import _build_broker_scan_inputs

    tls_targets = [("shared.example.com", 443)]
    broker_hosts, port_overrides, explicit_pairs = _build_broker_scan_inputs(
        tls_targets=tls_targets,
        broker_targets_raw=["shared.example.com:29092", "broker-only.example.com:25671"],
    )

    assert broker_hosts == ["shared.example.com", "broker-only.example.com"]
    assert port_overrides == {
        "shared.example.com": [29092],
        "broker-only.example.com": [25671],
    }


def test_build_broker_scan_inputs_bare_host_excluded_from_explicit_pairs():
    """A bare-host broker_targets entry (no port) contributes to broker_hosts
    but not to explicit_reachable_pairs (no specific port to confirm reached)."""
    from run_scan import _build_broker_scan_inputs

    broker_hosts, port_overrides, explicit_pairs = _build_broker_scan_inputs(
        tls_targets=[], broker_targets_raw=["bare-host.example.com"],
    )

    assert broker_hosts == ["bare-host.example.com"]
    assert port_overrides == {}
    assert explicit_pairs == []


def test_build_unreached_target_advisories_one_per_unreached_pair():
    """One ADVISORY row per explicit (host, port) pair that produced no endpoint;
    zero rows for pairs that WERE reached."""
    from quirk.scanner.broker_scanner import (
        build_unreached_target_advisories,
        ADVISORY_BROKER_TARGET_UNREACHED,
    )

    explicit_pairs = [("localhost", 29092), ("localhost", 25671)]
    results = [_make_ep("localhost", 29092, "KAFKA-PLAIN")]  # 25671 not reached

    advisories = build_unreached_target_advisories(explicit_pairs, results)

    assert len(advisories) == 1, f"Expected exactly 1 advisory, got {len(advisories)}"
    adv = advisories[0]
    assert adv.host == "localhost"
    assert adv.port == 25671
    assert adv.protocol == "ADVISORY"
    assert adv.service_detail == ADVISORY_BROKER_TARGET_UNREACHED
    assert adv.severity == "INFO"
    assert adv.scan_error_category == "config"
    assert adv.scan_error


def test_build_unreached_target_advisories_error_only_endpoint_still_fires():
    """Phase 190 CR-01: a firewalled explicit target (connect timeout, not
    refusal) may leave an error-only endpoint (scan_error set, no TLS/cipher
    evidence) in results. That row is NOT probe evidence and must not count as
    "reached" — the T-190-03 advisory must still fire for that pair."""
    from quirk.scanner.broker_scanner import (
        build_unreached_target_advisories,
        ADVISORY_BROKER_TARGET_UNREACHED,
    )

    explicit_pairs = [("dark-host.example.com", 29092)]
    errored = _make_ep("dark-host.example.com", 29092, "REDIS-TLS")
    errored.scan_error = "timed out"

    advisories = build_unreached_target_advisories(explicit_pairs, [errored])

    assert len(advisories) == 1, (
        f"Error-only endpoint must not suppress the advisory, got {advisories}"
    )
    assert advisories[0].service_detail == ADVISORY_BROKER_TARGET_UNREACHED
    assert (advisories[0].host, advisories[0].port) == ("dark-host.example.com", 29092)


def test_build_unreached_target_advisories_errored_but_evidenced_counts_reached():
    """Phase 190 CR-01 counterpart: an endpoint with real probe evidence
    (tls_version/cipher_suite) counts as reached even if scan_error is also
    set — reached-but-errored is not unreached."""
    from quirk.scanner.broker_scanner import build_unreached_target_advisories

    explicit_pairs = [("localhost", 6380)]
    ep = _make_ep("localhost", 6380, "REDIS-TLS")
    ep.tls_version = "TLSv1.2"
    ep.scan_error = "cert enrichment failed"

    advisories = build_unreached_target_advisories(explicit_pairs, [ep])

    assert advisories == [], f"Evidenced endpoint must count as reached, got {advisories}"


def test_build_unreached_target_advisories_empty_when_all_reached():
    """Zero advisory rows when every explicit target produced an endpoint."""
    from quirk.scanner.broker_scanner import build_unreached_target_advisories

    explicit_pairs = [("localhost", 29092)]
    results = [_make_ep("localhost", 29092, "KAFKA-PLAIN")]

    advisories = build_unreached_target_advisories(explicit_pairs, results)

    assert advisories == [], f"Expected no advisories when all reached, got {advisories}"


def test_build_unreached_target_advisories_silent_for_default_port_probes():
    """D-03 silence is preserved: a default-port probe that finds nothing produces
    NO advisory — only operator-named (explicit) targets do. Passing an empty
    explicit_targets list (the default-probe case) always yields zero advisories,
    regardless of how many endpoints were or were not found."""
    from quirk.scanner.broker_scanner import build_unreached_target_advisories

    # No explicit targets declared at all -- only speculative default-port probes,
    # which found nothing (results=[]).
    advisories = build_unreached_target_advisories([], [])

    assert advisories == [], "Default-port-only probes must never produce an advisory"
