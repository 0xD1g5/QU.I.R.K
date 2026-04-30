"""Lab-driven golden CBOM verification (Phase 35, Plan 03 — D-04).

This file produces and asserts against committed JSON fixtures captured from
hand-built ``CryptoEndpoint`` lists that mirror the chaos-lab port maps in
``labs/email/expected_results.md`` and ``labs/broker/expected_results.md``
exactly. The snapshot is **structural** (component bom_refs, asset types,
named cipher suites) — never byte-for-byte: timestamps, UUIDs, and
serial numbers are stripped before comparison.

Running ``REGEN_CBOM_FIXTURES=1 pytest tests/test_cbom_motion_golden.py \
        ::test_generate_fixtures -s`` regenerates both JSON files when the
scanner emits a new label or the builder layout changes intentionally.

No production code is modified — this is fixture + test only (Phase 35 / D-04).
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from quirk.cbom.builder import build_cbom
from quirk.cbom.classifier import classify_algorithm, quantum_safety_label
from quirk.models import CryptoEndpoint


FIXTURES_DIR = Path(__file__).parent / "fixtures" / "cbom"


# ---------------------------------------------------------------------------
# Endpoint generators — mirror the chaos-lab port maps verbatim
# ---------------------------------------------------------------------------

def _build_email_lab_endpoints() -> list[CryptoEndpoint]:
    """Return the 7 email-lab endpoints from labs/email/expected_results.md.

    Per D-02, all 6 distinct email TLS labels (SMTP-STARTTLS, SMTPS,
    IMAP-STARTTLS, IMAPS, POP3-STARTTLS, POP3S) flow through the default-TLS
    branch of build_cbom(). Two endpoints share the SMTP-STARTTLS label
    (ports 30025 + 30587) — both must produce distinct protocol bom_refs
    keyed by host:port.
    """
    postfix_subj = "CN=postfix.chaos.local"
    dovecot_subj = "CN=dovecot.chaos.local"
    aria = "TLS_RSA_WITH_ARIA_256_GCM_SHA384"
    chacha = "TLS_CHACHA20_POLY1305_SHA256"

    rows = [
        # (port, label, tls_version, cipher_suite, subject)
        (30025, "SMTP-STARTTLS", "TLSv1.2", aria,   postfix_subj),
        (30465, "SMTPS",         "TLSv1.2", aria,   postfix_subj),
        (30587, "SMTP-STARTTLS", "TLSv1.2", aria,   postfix_subj),
        (30143, "IMAP-STARTTLS", "TLSv1.3", chacha, dovecot_subj),
        (30993, "IMAPS",         "TLSv1.3", chacha, dovecot_subj),
        (30110, "POP3-STARTTLS", "TLSv1.3", chacha, dovecot_subj),
        (30995, "POP3S",         "TLSv1.3", chacha, dovecot_subj),
    ]
    return [
        CryptoEndpoint(
            host="localhost", port=port, protocol=label,
            tls_version=tls_ver, cipher_suite=cipher,
            cert_pubkey_alg="RSA", cert_pubkey_size=2048,
            cert_sig_alg="sha256WithRSAEncryption",
            cert_subject=subj, cert_issuer=subj,
            cert_not_before=None, cert_not_after=None,
            tls_capabilities_json=None, ssh_audit_json=None,
        )
        for (port, label, tls_ver, cipher, subj) in rows
    ]


def _build_broker_lab_endpoints() -> list[CryptoEndpoint]:
    """Return the 6 broker-lab endpoints from labs/broker/expected_results.md.

    Plaintext rows (KAFKA-PLAIN/AMQP-PLAIN/REDIS-PLAIN) carry no TLS metadata
    and no cert metadata — mirrors the real broker_scanner output. Per
    Phase 35 / CBOM-03 these labels are now in the Pass 2 + Pass 3 skip
    tuples, so they must NOT produce certificate or TLS protocol components.
    """
    self_signed_subj = "CN=broker.chaos.local"
    tls_rows = [
        # (port, label, cipher_suite)
        (29093, "KAFKA-TLS", "TLS_RSA_WITH_AES_128_CBC_SHA"),
        (25671, "AMQPS",     "DES-CBC3-SHA"),
        (26380, "REDIS-TLS", "DES-CBC3-SHA"),
    ]
    plain_rows = [
        (29092, "KAFKA-PLAIN"),
        (25672, "AMQP-PLAIN"),
        (26379, "REDIS-PLAIN"),
    ]

    tls_endpoints = [
        CryptoEndpoint(
            host="localhost", port=port, protocol=label,
            tls_version="TLSv1.2", cipher_suite=cipher,
            cert_pubkey_alg="RSA", cert_pubkey_size=2048,
            cert_sig_alg="sha256WithRSAEncryption",
            cert_subject=self_signed_subj, cert_issuer=self_signed_subj,
            cert_not_before=None, cert_not_after=None,
            tls_capabilities_json=None, ssh_audit_json=None,
        )
        for (port, label, cipher) in tls_rows
    ]

    plain_endpoints = [
        CryptoEndpoint(
            host="localhost", port=port, protocol=label,
            tls_version=None, cipher_suite=None,
            cert_pubkey_alg=None, cert_pubkey_size=None,
            cert_sig_alg=None, cert_subject=None, cert_issuer=None,
            cert_not_before=None, cert_not_after=None,
            tls_capabilities_json=None, ssh_audit_json=None,
        )
        for (port, label) in plain_rows
    ]
    return tls_endpoints + plain_endpoints


# ---------------------------------------------------------------------------
# Snapshot normalization — strip volatile fields, keep structural shape
# ---------------------------------------------------------------------------

def _normalize_bom_for_snapshot(bom) -> dict:
    """Return a stable dict shape with all volatile fields stripped.

    Per D-04: timestamps (metadata.timestamp, cert validity), UUIDs/serial
    numbers, and the metadata block itself are all excluded from the
    snapshot. Components are sorted by bom_ref so insertion order is
    irrelevant.
    """
    rows: list[dict] = []
    for c in bom.components:
        bom_ref_value = (
            getattr(getattr(c, "bom_ref", None), "value", None)
        )
        if bom_ref_value is None:
            continue

        crypto = getattr(c, "crypto_properties", None)
        proto_props = getattr(crypto, "protocol_properties", None) if crypto else None

        asset_type = None
        if crypto and getattr(crypto, "asset_type", None) is not None:
            asset_type = crypto.asset_type.value

        protocol_type = None
        protocol_version = None
        cipher_suite_names: list[str] = []
        if proto_props is not None:
            ptype = getattr(proto_props, "type", None)
            if ptype is not None:
                protocol_type = ptype.value
            protocol_version = getattr(proto_props, "version", None)
            suites = getattr(proto_props, "cipher_suites", None) or []
            cipher_suite_names = sorted(s.name for s in suites if s.name)

        type_value = c.type.value if getattr(c, "type", None) is not None else None

        rows.append({
            "bom_ref": str(bom_ref_value),
            "name": c.name,
            "type": type_value,
            "asset_type": asset_type,
            "protocol_type": protocol_type,
            "protocol_version": protocol_version,
            "cipher_suite_names": cipher_suite_names,
        })
    rows.sort(key=lambda r: r["bom_ref"])
    return {"components": rows}


def _write_snapshot(name: str, builder_fn) -> Path:
    """Materialize a snapshot JSON for the given lab profile."""
    bom = build_cbom(builder_fn())
    snap = _normalize_bom_for_snapshot(bom)
    path = FIXTURES_DIR / f"expected_{name}_cbom.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snap, indent=2, sort_keys=True) + "\n")
    return path


# ---------------------------------------------------------------------------
# One-shot fixture regeneration — gated by env var
# ---------------------------------------------------------------------------

@pytest.mark.slow
@pytest.mark.skipif(
    os.environ.get("REGEN_CBOM_FIXTURES") != "1",
    reason="set REGEN_CBOM_FIXTURES=1 to regenerate golden fixtures",
)
def test_generate_fixtures():
    """Regenerate both golden CBOM fixtures from the lab-shaped endpoints.

    Run once locally after an intentional builder change:
        REGEN_CBOM_FIXTURES=1 pytest tests/test_cbom_motion_golden.py \\
            ::test_generate_fixtures -s
    Then ``git diff tests/fixtures/cbom/`` to review and commit.
    """
    for name, builder_fn in (
        ("email", _build_email_lab_endpoints),
        ("broker", _build_broker_lab_endpoints),
    ):
        path = _write_snapshot(name, builder_fn)
        print(f"Wrote {path}")


# ---------------------------------------------------------------------------
# Snapshot assertions (always-on)
# ---------------------------------------------------------------------------

def _load_snapshot(name: str) -> dict:
    path = FIXTURES_DIR / f"expected_{name}_cbom.json"
    return json.loads(path.read_text())


def test_email_cbom_matches_snapshot():
    bom = build_cbom(_build_email_lab_endpoints())
    actual = _normalize_bom_for_snapshot(bom)
    expected = _load_snapshot("email")
    assert actual == expected, (
        "Email CBOM diverged from golden snapshot. If this change is "
        "intentional, run "
        "`REGEN_CBOM_FIXTURES=1 pytest tests/test_cbom_motion_golden.py"
        "::test_generate_fixtures -s` and commit the updated JSON."
    )


def test_broker_cbom_matches_snapshot():
    bom = build_cbom(_build_broker_lab_endpoints())
    actual = _normalize_bom_for_snapshot(bom)
    expected = _load_snapshot("broker")
    assert actual == expected, (
        "Broker CBOM diverged from golden snapshot. If this change is "
        "intentional, run "
        "`REGEN_CBOM_FIXTURES=1 pytest tests/test_cbom_motion_golden.py"
        "::test_generate_fixtures -s` and commit the updated JSON."
    )


# ---------------------------------------------------------------------------
# Structural invariants asserted directly against build_cbom() output
# (CBOM-01..CBOM-04 + D-03)
# ---------------------------------------------------------------------------

def test_email_snapshot_has_seven_protocol_components():
    """CBOM-01: each of the 7 email endpoints emits its own protocol bom_ref.

    Two endpoints share the SMTP-STARTTLS label (ports 30025 + 30587). Each
    must produce a distinct ``crypto/protocol/tls/localhost:{port}`` ref.
    """
    snap = _load_snapshot("email")
    proto_refs = [
        c["bom_ref"] for c in snap["components"]
        if c["bom_ref"].startswith("crypto/protocol/tls/")
    ]
    assert len(proto_refs) == 7, (
        f"Expected 7 TLS protocol components in email snapshot; got "
        f"{len(proto_refs)}: {proto_refs}"
    )
    # 6 distinct labels collapse to 7 ports — both 30025 + 30587 present.
    assert "crypto/protocol/tls/localhost:30025" in proto_refs
    assert "crypto/protocol/tls/localhost:30587" in proto_refs


def test_broker_snapshot_has_three_tls_protocol_components():
    """CBOM-02: only the 3 TLS broker ports emit protocol components."""
    snap = _load_snapshot("broker")
    proto_refs = [
        c["bom_ref"] for c in snap["components"]
        if c["bom_ref"].startswith("crypto/protocol/tls/")
    ]
    assert len(proto_refs) == 3, (
        f"Expected 3 TLS protocol components in broker snapshot; got "
        f"{len(proto_refs)}: {proto_refs}"
    )
    for plain_port in (29092, 25672, 26379):
        assert not any(f":{plain_port}" in r for r in proto_refs), (
            f"Plaintext port {plain_port} leaked into protocol pass: "
            f"{proto_refs}"
        )


def test_no_certificate_components_for_plaintext_brokers():
    """CBOM-03: plaintext broker endpoints emit ZERO cert components.

    Asserted both against the live build and against the committed snapshot
    so a future regression in either path is caught.
    """
    bom = build_cbom(_build_broker_lab_endpoints())
    cert_refs = [
        str(c.bom_ref.value) for c in bom.components
        if c.crypto_properties
        and c.crypto_properties.asset_type
        and c.crypto_properties.asset_type.value == "certificate"
    ]
    for plain_port in (29092, 25672, 26379):
        assert not any(f":{plain_port}" in r for r in cert_refs), (
            f"Hollow cert component leaked for plaintext port {plain_port}: "
            f"{cert_refs}"
        )

    # Snapshot mirror: bom_refs of asset_type=certificate must not contain
    # any plaintext port.
    snap = _load_snapshot("broker")
    snap_cert_refs = [
        c["bom_ref"] for c in snap["components"]
        if c.get("asset_type") == "certificate"
    ]
    for plain_port in (29092, 25672, 26379):
        assert not any(f":{plain_port}" in r for r in snap_cert_refs), (
            f"Snapshot regression: cert leaked for plaintext port "
            f"{plain_port}: {snap_cert_refs}"
        )


def test_no_tls_protocol_components_for_plaintext_brokers():
    """CBOM-03: plaintext broker endpoints emit ZERO TLS protocol components."""
    bom = build_cbom(_build_broker_lab_endpoints())
    tls_proto_refs = [
        str(c.bom_ref.value) for c in bom.components
        if c.crypto_properties
        and c.crypto_properties.asset_type
        and c.crypto_properties.asset_type.value == "protocol"
        and str(c.bom_ref.value).startswith("crypto/protocol/tls/")
    ]
    for plain_port in (29092, 25672, 26379):
        assert not any(f":{plain_port}" in r for r in tls_proto_refs), (
            f"Hollow TLS protocol leaked for plaintext port {plain_port}: "
            f"{tls_proto_refs}"
        )


def test_amqps_azure_servicebus_protocol_component_present():
    """D-03: the slash in 'AMQPS/Azure-ServiceBus' never escapes into
    bom_ref values. The label flows through the default-TLS branch and
    produces ``crypto/protocol/tls/{host}:5671`` — no normalization, no
    Azure-ServiceBus literal in any ref.
    """
    ep = CryptoEndpoint(
        host="azure-broker.example.com", port=5671,
        protocol="AMQPS/Azure-ServiceBus",
        tls_version="TLSv1.2",
        cipher_suite="TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384",
        cert_pubkey_alg="RSA", cert_pubkey_size=2048,
        cert_sig_alg="sha256WithRSAEncryption",
        cert_subject="CN=azure-broker.example.com",
        cert_issuer="CN=Azure CA",
        cert_not_before=None, cert_not_after=None,
        tls_capabilities_json=None, ssh_audit_json=None,
    )
    bom = build_cbom([ep])
    refs = {
        str(getattr(c.bom_ref, "value", "")) for c in bom.components
    }
    assert "crypto/protocol/tls/azure-broker.example.com:5671" in refs, (
        f"AMQPS/Azure-ServiceBus did not produce canonical TLS protocol "
        f"bom_ref; refs={sorted(refs)}"
    )
    assert not any("Azure-ServiceBus" in r for r in refs), (
        f"Slash-bearing label leaked into bom_ref value: {sorted(refs)}"
    )


def test_kafka_tls_rsa_cipher_decomposes_to_quantum_vulnerable():
    """CBOM-04: KAFKA-TLS uses TLS_RSA_WITH_AES_128_CBC_SHA, which decomposes
    to RSA + AES-128-CBC + SHA-1. The RSA component must be classified as
    quantum-vulnerable (nist_level=0).
    """
    bom = build_cbom(_build_broker_lab_endpoints())
    algo_refs = {
        str(c.bom_ref.value) for c in bom.components
        if c.crypto_properties
        and c.crypto_properties.asset_type
        and c.crypto_properties.asset_type.value == "algorithm"
    }
    assert "crypto/algorithm/rsa" in algo_refs, (
        f"RSA algorithm component missing; algo_refs={sorted(algo_refs)}"
    )
    _, nist_level, _ = classify_algorithm("rsa")
    assert nist_level == 0
    assert quantum_safety_label(nist_level) == "quantum-vulnerable"
