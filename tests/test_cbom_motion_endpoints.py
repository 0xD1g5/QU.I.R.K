"""Synthesized-endpoint CBOM tests for email + broker motion-class endpoints
(Phase 35, Plan 01 — RED phase).

This file locks the contract for Plan 02. Today the test split is:
- 13 PASSED  : 6 email TLS labels (CBOM-01) + 4 broker TLS labels (CBOM-02)
                + 3 cipher-suite quantum-safety verifications (CBOM-04).
- 6  FAILED  : KAFKA-PLAIN / AMQP-PLAIN / REDIS-PLAIN x (cert-pass + protocol-pass).
                These RED-state failures will turn GREEN when Plan 02 adds the three
                plaintext labels to the Pass 2 + Pass 3 skip tuples in
                quirk/cbom/builder.py.

No production code is modified by this plan. Mirrors Phase 34's synthesized-
endpoint pattern: no DB, no Docker, no network — pure unit tests against
build_cbom() and classify_algorithm().
"""
from __future__ import annotations

import pytest

from quirk.models import CryptoEndpoint
from quirk.cbom.builder import build_cbom, _decompose_cipher_suite
from quirk.cbom.classifier import classify_algorithm, quantum_safety_label

from cyclonedx.model.bom import Bom


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _tls_endpoint(**overrides) -> CryptoEndpoint:
    """Synthesize a TLS CryptoEndpoint with CBOM-friendly defaults.

    Mirrors the helper in tests/test_cbom_builder.py verbatim. Override any
    field via kwargs.
    """
    defaults = dict(
        host="example.com", port=443, protocol=None,
        tls_version="TLSv1.2",
        cipher_suite="TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384",
        cert_pubkey_alg="RSA", cert_pubkey_size=2048,
        cert_sig_alg="sha256WithRSAEncryption",
        cert_subject="CN=example.com", cert_issuer="CN=Example CA",
        cert_not_before=None, cert_not_after=None,
        tls_capabilities_json=None, ssh_audit_json=None,
    )
    defaults.update(overrides)
    return CryptoEndpoint(**defaults)


def _plaintext_broker_endpoint(label: str, port: int) -> CryptoEndpoint:
    """Synthesize a plaintext broker CryptoEndpoint.

    Plaintext brokers have no TLS metadata: no cipher suite, no cert, no
    TLS version. Mirrors the real shape produced by broker_scanner for
    KAFKA-PLAIN / AMQP-PLAIN / REDIS-PLAIN labels.
    """
    return CryptoEndpoint(
        host="broker.example.com", port=port, protocol=label,
        tls_version=None, cipher_suite=None,
        cert_pubkey_alg=None, cert_pubkey_size=None,
        cert_sig_alg=None, cert_subject=None, cert_issuer=None,
        cert_not_before=None, cert_not_after=None,
        tls_capabilities_json=None, ssh_audit_json=None,
    )


def _bom_refs(bom: Bom) -> set[str]:
    """Return the set of all bom_ref values for components in the Bom."""
    refs: set[str] = set()
    for c in bom.components:
        ref = getattr(c, "bom_ref", None)
        if ref is None:
            continue
        value = getattr(ref, "value", None)
        if value:
            refs.add(value)
    return refs


# ---------------------------------------------------------------------------
# CBOM-01 — Email TLS labels (six labels, default-TLS branch in build_cbom)
# ---------------------------------------------------------------------------

EMAIL_TLS_CASES = [
    pytest.param("SMTP-STARTTLS", 587, id="smtp-starttls"),
    pytest.param("SMTPS",         465, id="smtps"),
    pytest.param("IMAP-STARTTLS", 143, id="imap-starttls"),
    pytest.param("IMAPS",         993, id="imaps"),
    pytest.param("POP3-STARTTLS", 110, id="pop3-starttls"),
    pytest.param("POP3S",         995, id="pop3s"),
]


@pytest.mark.parametrize("label,port", EMAIL_TLS_CASES)
def test_email_tls_endpoint_emits_protocol_and_cert_components(label, port):
    """All 6 email TLS labels flow through default-TLS branch of build_cbom().

    Asserts both a TLS protocol component and a certificate component are
    emitted with the canonical bom_ref shape.
    """
    ep = _tls_endpoint(protocol=label, port=port)
    bom = build_cbom([ep])
    refs = _bom_refs(bom)

    expected_proto = f"crypto/protocol/tls/{ep.host}:{port}"
    expected_cert = f"crypto/certificate/{ep.host}:{port}"

    assert expected_proto in refs, (
        f"Expected protocol component {expected_proto!r} for label {label!r}; "
        f"got refs={sorted(refs)}"
    )
    assert expected_cert in refs, (
        f"Expected certificate component {expected_cert!r} for label {label!r}; "
        f"got refs={sorted(refs)}"
    )


# ---------------------------------------------------------------------------
# CBOM-02 — Broker TLS labels (four labels including AMQPS/Azure-ServiceBus)
# ---------------------------------------------------------------------------

BROKER_TLS_CASES = [
    pytest.param("AMQPS",                   5671, id="amqps"),
    pytest.param("AMQPS/Azure-ServiceBus",  5671, id="amqps-azure-servicebus"),
    pytest.param("KAFKA-TLS",               9093, id="kafka-tls"),
    pytest.param("REDIS-TLS",               6380, id="redis-tls"),
]


@pytest.mark.parametrize("label,port", BROKER_TLS_CASES)
def test_broker_tls_endpoint_emits_protocol_component(label, port):
    """Per D-03: AMQPS/Azure-ServiceBus passes through unchanged.

    The slash sits in the protocol label, never escapes into bom_ref values
    (bom_refs are 'crypto/protocol/tls/{host}:{port}'). Asserts no crash and
    canonical bom_ref shape for all four broker TLS labels.
    """
    ep = _tls_endpoint(host="broker.example.com", protocol=label, port=port)
    bom = build_cbom([ep])
    refs = _bom_refs(bom)

    expected_proto = f"crypto/protocol/tls/{ep.host}:{port}"
    expected_cert = f"crypto/certificate/{ep.host}:{port}"

    assert expected_proto in refs, (
        f"Expected protocol component {expected_proto!r} for label {label!r}; "
        f"got refs={sorted(refs)}"
    )
    assert expected_cert in refs, (
        f"Expected cert component {expected_cert!r} for label {label!r}; "
        f"got refs={sorted(refs)}"
    )
    # Defensive: slash from "AMQPS/Azure-ServiceBus" must never end up in a
    # bom_ref VALUE. The path-prefix slash in 'crypto/protocol/...' is fine,
    # but no ref should contain "Azure-ServiceBus" as a literal.
    assert not any("Azure-ServiceBus" in r for r in refs), (
        f"Slash-bearing label leaked into bom_ref value: {sorted(refs)}"
    )


# ---------------------------------------------------------------------------
# CBOM-03 — Plaintext broker labels skipped from cert + protocol passes
#
# These six tests are the RED-state. Today builder.py does NOT include
# KAFKA-PLAIN / AMQP-PLAIN / REDIS-PLAIN in its Pass 2 / Pass 3 skip tuples,
# so build_cbom() emits hollow cert + protocol components for plaintext
# endpoints. Plan 02 will add the three labels to both tuples and turn
# these six tests GREEN.
# ---------------------------------------------------------------------------

PLAINTEXT_BROKER_CASES = [
    pytest.param("KAFKA-PLAIN", 9092, id="kafka-plain"),
    pytest.param("AMQP-PLAIN",  5672, id="amqp-plain"),
    pytest.param("REDIS-PLAIN", 6379, id="redis-plain"),
]


@pytest.mark.parametrize("label,port", PLAINTEXT_BROKER_CASES)
def test_plaintext_broker_skipped_from_cert_pass(label, port):
    """Pass 2 (certificate components) MUST skip plaintext broker labels.

    RED today: cert components leak through. GREEN after Plan 02 skip-list.
    """
    ep = _plaintext_broker_endpoint(label, port)
    bom = build_cbom([ep])
    refs = _bom_refs(bom)

    cert_prefix = f"crypto/certificate/{ep.host}:{port}"
    leaked = [r for r in refs if r.startswith(cert_prefix)]

    assert leaked == [], (
        f"Plaintext broker {label!r} leaked into cert pass: "
        f"crypto/certificate/{ep.host}:{port} bom_refs found = {leaked}. "
        "Pass 2 skip-list must include this label (Plan 02)."
    )


@pytest.mark.parametrize("label,port", PLAINTEXT_BROKER_CASES)
def test_plaintext_broker_skipped_from_protocol_pass(label, port):
    """Pass 3 (protocol components) MUST skip plaintext broker labels.

    RED today: protocol:tls components leak through. GREEN after Plan 02.
    """
    ep = _plaintext_broker_endpoint(label, port)
    bom = build_cbom([ep])
    refs = _bom_refs(bom)

    proto_prefix = f"crypto/protocol/tls/{ep.host}:{port}"
    leaked = [r for r in refs if r.startswith(proto_prefix)]

    assert leaked == [], (
        f"Plaintext broker {label!r} leaked into protocol pass: "
        f"crypto/protocol/tls/{ep.host}:{port} bom_refs found = {leaked}. "
        "Pass 3 skip-list must include this label (Plan 02)."
    )


# ---------------------------------------------------------------------------
# CBOM-04 — Quantum-safety classification verification (verify, don't redefine)
# ---------------------------------------------------------------------------


def test_classify_tls_rsa_aes_128_cbc_sha_components_quantum_vulnerable():
    """TLS_RSA_WITH_AES_128_CBC_SHA decomposes to algorithms that include at
    least one nist_level==0 (quantum-vulnerable) component — namely the RSA
    key-transport, labeled 'RSA-kex' by builder _KEX_MAP (Phase 73 D-08/WR-12).

    Verify, don't redefine: classifier maps 'rsa-kex' -> level 0.
    """
    decomposed = _decompose_cipher_suite("TLS_RSA_WITH_AES_128_CBC_SHA")
    assert decomposed, "Cipher decomposition returned empty list"

    levels = {algo: classify_algorithm(algo)[1] for algo in decomposed}

    # RSA key-transport must be present and classified quantum-vulnerable.
    rsa_levels = [lvl for algo, lvl in levels.items() if algo.lower() == "rsa-kex"]
    assert rsa_levels, f"RSA-kex missing from decomposition: {decomposed}"
    assert rsa_levels[0] == 0, (
        f"RSA-kex expected nist_level=0 (quantum-vulnerable); got {rsa_levels[0]} "
        f"with full decomposition {levels}"
    )
    assert quantum_safety_label(rsa_levels[0]) == "quantum-vulnerable"


def test_classify_tls_ecdhe_rsa_aes_256_gcm_sha384_has_vulnerable_components():
    """TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384 layering:
    - X25519 (KEX)  -> nist_level 0  (quantum-vulnerable, classical KEX)
    - RSA   (AUTH) -> nist_level 0  (quantum-vulnerable signature)
    - AES-256-GCM  -> nist_level 1  (quantum-safe at the cipher level)
    - SHA-384      -> nist_level 2  (quantum-safe hash)

    The suite as a whole is quantum-vulnerable due to RSA auth + classical KEX,
    even though AES-256-GCM by itself is quantum-safe. Asserts the layering.
    """
    decomposed = _decompose_cipher_suite("TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384")
    levels = {algo: classify_algorithm(algo)[1] for algo in decomposed}

    # RSA component is quantum-vulnerable (level 0).
    rsa_levels = [lvl for algo, lvl in levels.items() if algo.lower() == "rsa"]
    assert rsa_levels and rsa_levels[0] == 0, (
        f"RSA must be present and level=0; decomposition={levels}"
    )

    # AES-256-GCM is quantum-safe at AES level (level 1) — Grover halves bits
    # but 128-bit post-Grover security is acceptable.
    aes_levels = [lvl for algo, lvl in levels.items() if algo.lower() == "aes-256-gcm"]
    assert aes_levels and aes_levels[0] == 1, (
        f"AES-256-GCM must be present and level=1; decomposition={levels}"
    )

    # Suite-level conclusion: at least one component is quantum-vulnerable.
    vulnerable = [algo for algo, lvl in levels.items() if lvl == 0]
    assert vulnerable, (
        f"Suite expected to contain at least one quantum-vulnerable component; "
        f"decomposition={levels}"
    )


def test_classify_tls_aes_256_gcm_sha384_aead_only():
    """TLSv1.3 TLS_AES_256_GCM_SHA384 is AEAD-only — no KEX/auth in suite name.

    Decomposition contains AES-256-GCM (level 1) and SHA-384 (level 2). No RSA
    and no X25519 token because TLSv1.3 negotiates KEX outside the suite.
    """
    decomposed = _decompose_cipher_suite("TLS_AES_256_GCM_SHA384")
    levels = {algo: classify_algorithm(algo)[1] for algo in decomposed}

    aes_levels = [lvl for algo, lvl in levels.items() if algo.lower() == "aes-256-gcm"]
    assert aes_levels and aes_levels[0] == 1, (
        f"AES-256-GCM must be present and level=1; decomposition={levels}"
    )

    sha_levels = [lvl for algo, lvl in levels.items() if algo.lower() == "sha-384"]
    assert sha_levels and sha_levels[0] == 2, (
        f"SHA-384 must be present and level=2; decomposition={levels}"
    )

    # No RSA / no X25519 — TLSv1.3 strips KEX/auth from suite name.
    assert not any(algo.lower() == "rsa" for algo in decomposed), (
        f"TLSv1.3 suite should not decompose to RSA; got {decomposed}"
    )
    assert not any(algo.lower() == "x25519" for algo in decomposed), (
        f"TLSv1.3 suite should not decompose to X25519 (negotiated outside suite); "
        f"got {decomposed}"
    )


# ---------------------------------------------------------------------------
# Phase 42 / Plan 03 — Per-profile endpoint synthesizers
#
# Three shape-golden synthesizers (rich, used by snapshot tests in
# tests/test_cbom_motion_golden.py) plus thirteen lightweight synthesizers
# (one per remaining shipped chaos lab profile). Together they cover ALL 18
# profiles in quantum-chaos-enterprise-lab/docker-compose.yml.
#
# All ports/algorithm names sourced from
# quantum-chaos-enterprise-lab/expected_results_v3.md (2026-04-30).
# Algorithm names default to RSA/2048 where possible to minimize Plan 04
# gap-fill burden; profiles whose REAL scanner observable is a known-weak
# algo (RSASHA1, ssh-dss, RC4-HMAC, MD5) use that name intentionally so the
# Plan 04 classifier-coverage gate flags it for resolution.
# ---------------------------------------------------------------------------


# --- Shape-golden synthesizers (Phase 42 / Plan 03 — used by snapshot tests) ---

def _build_pki_lab_endpoints() -> list[CryptoEndpoint]:
    """PKI lab — TLS-with-cert shape (mTLS step-CA gateway, port 17443).

    Sourced from quantum-chaos-enterprise-lab/docker-compose.yml line ~499
    (mtls-stepca-gateway). Cipher suite chosen so all decomposed parts already
    exist in the classifier's _ALGORITHM_TABLE.
    """
    subj = "CN=mtls.chaos.local"
    return [
        CryptoEndpoint(
            host="localhost", port=17443, protocol="HTTPS",
            tls_version="TLSv1.2",
            cipher_suite="TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384",
            cert_pubkey_alg="RSA", cert_pubkey_size=2048,
            cert_sig_alg="sha256WithRSAEncryption",
            cert_subject=subj, cert_issuer=subj,
            cert_not_before=None, cert_not_after=None,
            tls_capabilities_json=None, ssh_audit_json=None,
        ),
    ]


def _build_vault_lab_endpoints() -> list[CryptoEndpoint]:
    """Vault lab — Data-at-rest shape (HashiCorp Vault, port 28200).

    VAULT is in DAR_SKIP_PROTOCOLS — Pass 2 and Pass 3 skip this endpoint.
    Pass 1 still emits an algorithm component for cert_pubkey_alg, so this
    fixture captures the "algorithm-only" output shape characteristic of
    DAR-skipped protocols.
    """
    return [
        CryptoEndpoint(
            host="localhost", port=28200, protocol="VAULT",
            tls_version=None, cipher_suite=None,
            cert_pubkey_alg="RSA", cert_pubkey_size=2048,
            cert_sig_alg=None, cert_subject=None, cert_issuer=None,
            cert_not_before=None, cert_not_after=None,
            tls_capabilities_json=None, ssh_audit_json=None,
        ),
    ]


def _build_saml_lab_endpoints() -> list[CryptoEndpoint]:
    """SAML lab — Identity shape (simplesamlphp IdP, port 8080).

    SAML signing certs do not carry TLS metadata in the scanner output —
    tls_version=None, cipher_suite=None. The cert_pubkey_alg / cert_pubkey_size
    are the IdP signing-key observables.
    """
    return [
        CryptoEndpoint(
            host="localhost", port=8080, protocol="SAML",
            tls_version=None, cipher_suite=None,
            cert_pubkey_alg="RSA", cert_pubkey_size=2048,
            cert_sig_alg=None, cert_subject=None, cert_issuer=None,
            cert_not_before=None, cert_not_after=None,
            tls_capabilities_json=None, ssh_audit_json=None,
        ),
    ]


# --- Lightweight synthesizers (Phase 42 / Plan 03 — no goldens) -----------
# Minimum viable representative coverage: 1-3 endpoints each, ensuring the
# schema validator (Plan 02) inspects a non-trivial Bom for every profile.


def _build_cloud_lab_endpoints() -> list[CryptoEndpoint]:
    """Cloud profile — TLS shape (localstack-tls + azurite-blob-tls).

    Sourced from expected_results_v3.md Phase B — Cloud Simulators.
    """
    rows = [(24566, "HTTPS"), (21000, "HTTPS")]
    subj = "CN=cloud.chaos.local"
    return [
        CryptoEndpoint(
            host="localhost", port=port, protocol=label,
            tls_version="TLSv1.2",
            cipher_suite="TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384",
            cert_pubkey_alg="RSA", cert_pubkey_size=2048,
            cert_sig_alg="sha256WithRSAEncryption",
            cert_subject=subj, cert_issuer=subj,
            cert_not_before=None, cert_not_after=None,
            tls_capabilities_json=None, ssh_audit_json=None,
        )
        for (port, label) in rows
    ]


def _build_database_lab_endpoints() -> list[CryptoEndpoint]:
    """Database profile — DAR shape (POSTGRESQL ssl-off, port 25432).

    POSTGRESQL/MYSQL are in DAR_SKIP_PROTOCOLS — Pass 2/3 skip. Real ssl-off
    behaviour: db_connector does NOT set cert_pubkey_alg (no TLS negotiation).
    Phase 88 D-06 / SCORE-CBOM-01: builder emits an affirmative quirk:coverage-note
    instead of an algorithm component, closing Phase 42 OBS-1 for this profile.
    Sourced from expected_results_v3.md Phase 27.
    """
    return [
        CryptoEndpoint(
            host="localhost", port=25432, protocol="POSTGRESQL",
            tls_version=None, cipher_suite=None,
            cert_pubkey_alg=None, cert_pubkey_size=None,
            cert_sig_alg=None, cert_subject=None, cert_issuer=None,
            cert_not_before=None, cert_not_after=None,
            tls_capabilities_json=None, ssh_audit_json=None,
        ),
    ]


def _build_dnssec_lab_endpoints() -> list[CryptoEndpoint]:
    """DNSSEC profile — port 15353, RSASHA1 weak signing alg.

    Sourced from expected_results_v3.md "weak.example.com / RSASHA1".
    NOTE: RSASHA1 likely surfaces an UNKNOWN classification — Plan 04 closes.
    """
    return [
        CryptoEndpoint(
            host="localhost", port=15353, protocol="DNSSEC",
            tls_version=None, cipher_suite=None,
            cert_pubkey_alg="RSASHA1", cert_pubkey_size=None,
            cert_sig_alg=None, cert_subject=None, cert_issuer=None,
            cert_not_before=None, cert_not_after=None,
            tls_capabilities_json=None, ssh_audit_json=None,
        ),
    ]


def _build_identity_lab_endpoints() -> list[CryptoEndpoint]:
    """Identity profile — TLS shape (keycloak-tls + mtls-gateway).

    Sourced from expected_results_v3.md identity profile section.
    """
    rows = [(15449, "HTTPS"), (16443, "HTTPS")]
    subj = "CN=identity.chaos.local"
    return [
        CryptoEndpoint(
            host="localhost", port=port, protocol=label,
            tls_version="TLSv1.2",
            cipher_suite="TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384",
            cert_pubkey_alg="RSA", cert_pubkey_size=2048,
            cert_sig_alg="sha256WithRSAEncryption",
            cert_subject=subj, cert_issuer=subj,
            cert_not_before=None, cert_not_after=None,
            tls_capabilities_json=None, ssh_audit_json=None,
        )
        for (port, label) in rows
    ]


def _build_jwt_lab_endpoints() -> list[CryptoEndpoint]:
    """JWT profile — port 20001, RS256 signing (RSA-based, quantum-vulnerable).

    Sourced from expected_results_v3.md Phase 4 — JWT Profile.
    """
    return [
        CryptoEndpoint(
            host="localhost", port=20001, protocol="JWT",
            tls_version=None, cipher_suite=None,
            cert_pubkey_alg="RSA", cert_pubkey_size=2048,
            cert_sig_alg=None, cert_subject=None, cert_issuer=None,
            cert_not_before=None, cert_not_after=None,
            tls_capabilities_json=None, ssh_audit_json=None,
        ),
    ]


def _build_kerberos_lab_endpoints() -> list[CryptoEndpoint]:
    """Kerberos profile — port 88, RC4-HMAC weak enctype.

    Sourced from expected_results_v3.md "rc4-hmac" finding.
    NOTE: RC4-HMAC likely surfaces an UNKNOWN classification — Plan 04 closes.
    """
    return [
        CryptoEndpoint(
            host="localhost", port=88, protocol="KERBEROS",
            tls_version=None, cipher_suite=None,
            cert_pubkey_alg="RC4-HMAC", cert_pubkey_size=None,
            cert_sig_alg=None, cert_subject=None, cert_issuer=None,
            cert_not_before=None, cert_not_after=None,
            tls_capabilities_json=None, ssh_audit_json=None,
        ),
    ]


def _build_ldaps_lab_endpoints() -> list[CryptoEndpoint]:
    """LDAPS profile — TLS shape (port 636).

    Sourced from expected_results_v3.md ldaps profile section.
    """
    subj = "CN=ldap.chaos.local"
    return [
        CryptoEndpoint(
            host="localhost", port=636, protocol="LDAPS",
            tls_version="TLSv1.2",
            cipher_suite="TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384",
            cert_pubkey_alg="RSA", cert_pubkey_size=2048,
            cert_sig_alg="sha256WithRSAEncryption",
            cert_subject=subj, cert_issuer=subj,
            cert_not_before=None, cert_not_after=None,
            tls_capabilities_json=None, ssh_audit_json=None,
        ),
    ]


def _build_phaseA_lab_endpoints() -> list[CryptoEndpoint]:
    """phaseA profile — TLS shape (tls-missing-intermediate, tls-rsa1024, tls-sha1).

    Sourced from expected_results_v3.md phaseA section. Includes an RSA-1024
    weak-key endpoint and a sha1WithRSAEncryption weak-sig endpoint.
    """
    subj = "CN=phaseA.chaos.local"
    return [
        CryptoEndpoint(
            host="localhost", port=13443, protocol="HTTPS",
            tls_version="TLSv1.2",
            cipher_suite="TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384",
            cert_pubkey_alg="RSA", cert_pubkey_size=2048,
            cert_sig_alg="sha256WithRSAEncryption",
            cert_subject=subj, cert_issuer=subj,
            cert_not_before=None, cert_not_after=None,
            tls_capabilities_json=None, ssh_audit_json=None,
        ),
        CryptoEndpoint(
            host="localhost", port=14443, protocol="HTTPS",
            tls_version="TLSv1.2",
            cipher_suite="TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384",
            cert_pubkey_alg="RSA", cert_pubkey_size=1024,
            cert_sig_alg="sha256WithRSAEncryption",
            cert_subject=subj, cert_issuer=subj,
            cert_not_before=None, cert_not_after=None,
            tls_capabilities_json=None, ssh_audit_json=None,
        ),
        CryptoEndpoint(
            host="localhost", port=15443, protocol="HTTPS",
            tls_version="TLSv1.2",
            cipher_suite="TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384",
            cert_pubkey_alg="RSA", cert_pubkey_size=2048,
            cert_sig_alg="sha1WithRSAEncryption",
            cert_subject=subj, cert_issuer=subj,
            cert_not_before=None, cert_not_after=None,
            tls_capabilities_json=None, ssh_audit_json=None,
        ),
    ]


def _build_registry_lab_endpoints() -> list[CryptoEndpoint]:
    """Registry profile — port 20005, OUTDATED_CRYPTO_LIB observable.

    Sourced from expected_results_v3.md registry section. Real scanner behaviour:
    container_scanner sets cipher_suite=library_name (e.g. "openssl"). Library names
    are not algorithm names and would produce UNKNOWN classification.
    Phase 88 D-06 / SCORE-CBOM-01: builder emits affirmative quirk:coverage-note
    instead of registering the library string as an algorithm component.
    """
    return [
        CryptoEndpoint(
            host="localhost", port=20005, protocol="CONTAINER",
            tls_version=None, cipher_suite="openssl",
            cert_pubkey_alg=None, cert_pubkey_size=None,
            cert_sig_alg=None, cert_subject=None, cert_issuer=None,
            cert_not_before=None, cert_not_after=None,
            tls_capabilities_json=None, ssh_audit_json=None,
        ),
    ]


def _build_source_lab_endpoints() -> list[CryptoEndpoint]:
    """Source profile — port 20006, weak-algorithm anti-pattern (MD5 semgrep rule).

    Sourced from expected_results_v3.md source-code scanner findings.
    Phase 88 D-05 / SCORE-CBOM-01: source scanner sets cipher_suite=rule_id;
    _extract_algo_from_rule_id extracts "MD5" from the -md5 fragment.
    """
    return [
        CryptoEndpoint(
            host="localhost", port=20006, protocol="SOURCE",
            tls_version=None,
            cipher_suite="python.cryptography.security.insecure-hash-algorithms-md5",
            cert_pubkey_alg=None, cert_pubkey_size=None,
            cert_sig_alg=None, cert_subject=None, cert_issuer=None,
            cert_not_before=None, cert_not_after=None,
            tls_capabilities_json=None, ssh_audit_json=None,
        ),
    ]


def _build_ssh_weak_lab_endpoints() -> list[CryptoEndpoint]:
    """ssh-weak profile — port 20022, weak SSH algorithms (CRITICAL findings).

    Sourced from expected_results_v3.md ssh-weak hostkey ssh-dss CRITICAL.
    Phase 88 D-05 / SCORE-CBOM-01: realistic ssh_audit_json so the SSH builder
    branch registers the actual weak algorithms observed by ssh-audit rather than
    falling back to the cert_pubkey_alg sentinel. All algorithm names must exist
    in classifier._ALGORITHM_TABLE (added in Phase 88 Plan 02 Task 1).
    """
    import json as _json
    _SSH_AUDIT_JSON = _json.dumps({
        "kex": [{"algorithm": "diffie-hellman-group1-sha1"}],
        "key": [{"algorithm": "ssh-dss"}],
        "enc": [{"algorithm": "aes128-ctr"}],
        "mac": [{"algorithm": "hmac-md5"}],
    })
    return [
        CryptoEndpoint(
            host="localhost", port=20022, protocol="SSH",
            tls_version=None, cipher_suite=None,
            cert_pubkey_alg="ssh-dss", cert_pubkey_size=None,
            cert_sig_alg=None, cert_subject=None, cert_issuer=None,
            cert_not_before=None, cert_not_after=None,
            tls_capabilities_json=None, ssh_audit_json=_SSH_AUDIT_JSON,
        ),
    ]


def _build_storage_lab_endpoints() -> list[CryptoEndpoint]:
    """Storage profile — VAULT (port 20009) + S3 (port 20007).

    Sourced from expected_results_v3.md Phase 4 — Storage Profile. Both
    protocols are in DAR_SKIP_PROTOCOLS — Pass 2/3 skip; Pass 1 emits algos.
    """
    return [
        CryptoEndpoint(
            host="localhost", port=20009, protocol="VAULT",
            tls_version=None, cipher_suite=None,
            cert_pubkey_alg="AES-256", cert_pubkey_size=None,
            cert_sig_alg=None, cert_subject=None, cert_issuer=None,
            cert_not_before=None, cert_not_after=None,
            tls_capabilities_json=None, ssh_audit_json=None,
        ),
        CryptoEndpoint(
            host="localhost", port=20007, protocol="S3",
            tls_version=None, cipher_suite=None,
            cert_pubkey_alg="RSA", cert_pubkey_size=2048,
            cert_sig_alg=None, cert_subject=None, cert_issuer=None,
            cert_not_before=None, cert_not_after=None,
            tls_capabilities_json=None, ssh_audit_json=None,
        ),
    ]


def _build_storage_s3_lab_endpoints() -> list[CryptoEndpoint]:
    """storage-s3 profile — MinIO S3 (port 29000), unencrypted bucket.

    Sourced from expected_results_v3.md storage-s3 section. S3 is in
    DAR_SKIP_PROTOCOLS — Pass 2/3 skip. Real unencrypted-bucket observation:
    aws_connector sets service_detail="S3/unencrypted" with no cert_pubkey_alg.
    Phase 88 D-06 / SCORE-CBOM-01: builder emits an affirmative quirk:coverage-note
    instead of an algorithm component, closing Phase 42 OBS-1 for this profile.
    """
    return [
        CryptoEndpoint(
            host="localhost", port=29000, protocol="S3",
            tls_version=None, cipher_suite=None,
            cert_pubkey_alg=None, cert_pubkey_size=None,
            cert_sig_alg=None, cert_subject=None, cert_issuer=None,
            cert_not_before=None, cert_not_after=None,
            tls_capabilities_json=None, ssh_audit_json=None,
            service_detail="S3/unencrypted",
        ),
    ]


# --- Phase 46/79/80/89/90/96/127 profile synthesizers (chaos-lab drift sync) --
# Added to close the PROFILE_ENDPOINTS ↔ docker-compose.yml drift (CLAUDE.md
# Chaos Lab Maintenance). Each profile below was added to docker-compose.yml
# after the Phase 42 synthesizer map was written. Ports/shapes sourced from the
# compose service definitions cited in each docstring.


def _build_smime_lab_endpoints() -> list[CryptoEndpoint]:
    """smime profile — S/MIME LDAP cert discovery (port 38900, Phase 79).

    smime-openldap seeds userSMIMECertificate values exercising weak-key /
    weak-signing paths. Cert-only shape (no TLS) — the signing key is the
    observable. RSA-1024 captures the deliberately weak SMIME key.
    """
    return [
        CryptoEndpoint(
            host="localhost", port=38900, protocol="SMIME",
            tls_version=None, cipher_suite=None,
            cert_pubkey_alg="RSA", cert_pubkey_size=1024,
            cert_sig_alg="sha256WithRSAEncryption",
            cert_subject="CN=smime-user,dc=quirk,dc=lab",
            cert_issuer="CN=smime-ca,dc=quirk,dc=lab",
            cert_not_before=None, cert_not_after=None,
            tls_capabilities_json=None, ssh_audit_json=None,
        ),
    ]


def _build_adcs_lab_endpoints() -> list[CryptoEndpoint]:
    """adcs profile — Windows AD CS LDAP discovery (port 38910, Phase 80).

    adcs-openldap seeds a misconfigured AD CS partition with an RSA-1024 SHA-1
    CA signing cert (adcs/certs/ca-weak.der). Modeled as the code-signing CA
    cert observable (CODE_SIGNING Pass-1 registers cert_pubkey_alg).
    """
    return [
        CryptoEndpoint(
            host="localhost", port=38910, protocol="CODE_SIGNING",
            tls_version=None, cipher_suite=None,
            cert_pubkey_alg="RSA", cert_pubkey_size=1024,
            cert_sig_alg="sha256WithRSAEncryption",
            cert_subject="CN=adcs-ca,dc=quirk,dc=lab",
            cert_issuer="CN=adcs-ca,dc=quirk,dc=lab",
            cert_not_before=None, cert_not_after=None,
            tls_capabilities_json=None, ssh_audit_json=None,
            service_detail="fingerprint=" + ("ad" * 32) + "|weak",
        ),
    ]


def _build_tls_cert_defects_lab_endpoints() -> list[CryptoEndpoint]:
    """tls-cert-defects profile — nginx cert-defect targets (ports 13444-13447,
    Phase 46). Representative subset: expired (13444, RSA-2048) and the
    deliberately weak rsa1024 target (13447, RSA-1024).
    """
    subj = "CN=cert-defects.chaos.local"
    rows = [(13444, 2048), (13447, 1024)]
    return [
        CryptoEndpoint(
            host="localhost", port=port, protocol="HTTPS",
            tls_version="TLSv1.2",
            cipher_suite="TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384",
            cert_pubkey_alg="RSA", cert_pubkey_size=size,
            cert_sig_alg="sha256WithRSAEncryption",
            cert_subject=subj, cert_issuer=subj,
            cert_not_before=None, cert_not_after=None,
            tls_capabilities_json=None, ssh_audit_json=None,
        )
        for (port, size) in rows
    ]


def _build_postgres_tls_lab_endpoints() -> list[CryptoEndpoint]:
    """postgres-tls profile — weak-TLS PostgreSQL (port 39432, Phase 89 LAB-01).

    RSA key-exchange ciphers, no PFS. The weak suite decomposes to the
    quantum-vulnerable RSA-kex + AES-128-CBC + SHA-1 components.
    """
    subj = "CN=postgres-tls.chaos.local"
    return [
        CryptoEndpoint(
            host="localhost", port=39432, protocol="POSTGRES-TLS",
            tls_version="TLSv1.2", cipher_suite="TLS_RSA_WITH_AES_128_CBC_SHA",
            cert_pubkey_alg="RSA", cert_pubkey_size=2048,
            cert_sig_alg="sha256WithRSAEncryption",
            cert_subject=subj, cert_issuer=subj,
            cert_not_before=None, cert_not_after=None,
            tls_capabilities_json=None, ssh_audit_json=None,
        ),
    ]


def _build_redis_tls_lab_endpoints() -> list[CryptoEndpoint]:
    """redis-tls profile — weak-TLS Redis (port 39380, Phase 89 LAB-02).

    3DES + RSA ciphers. DES-CBC3-SHA decomposes to the weak 3DES + RSA-kex
    + SHA-1 components (mirrors the broker AMQPS/REDIS-TLS rows).
    """
    subj = "CN=redis-tls.chaos.local"
    return [
        CryptoEndpoint(
            host="localhost", port=39380, protocol="REDIS-TLS",
            tls_version="TLSv1.2", cipher_suite="DES-CBC3-SHA",
            cert_pubkey_alg="RSA", cert_pubkey_size=2048,
            cert_sig_alg="sha256WithRSAEncryption",
            cert_subject=subj, cert_issuer=subj,
            cert_not_before=None, cert_not_after=None,
            tls_capabilities_json=None, ssh_audit_json=None,
        ),
    ]


def _build_kafka_tls_lab_endpoints() -> list[CryptoEndpoint]:
    """kafka-tls profile — weak-TLS Kafka (port 39093, Phase 89 LAB-04).

    RSA key-exchange ciphers. TLS_RSA_WITH_AES_128_CBC_SHA decomposes to the
    quantum-vulnerable RSA-kex + AES-128-CBC + SHA-1 components.
    """
    subj = "CN=kafka-tls.chaos.local"
    return [
        CryptoEndpoint(
            host="localhost", port=39093, protocol="KAFKA-TLS",
            tls_version="TLSv1.2", cipher_suite="TLS_RSA_WITH_AES_128_CBC_SHA",
            cert_pubkey_alg="RSA", cert_pubkey_size=2048,
            cert_sig_alg="sha256WithRSAEncryption",
            cert_subject=subj, cert_issuer=subj,
            cert_not_before=None, cert_not_after=None,
            tls_capabilities_json=None, ssh_audit_json=None,
        ),
    ]


def _build_grpc_tls_lab_endpoints() -> list[CryptoEndpoint]:
    """grpc-tls profile — Go gRPC server, self-signed RSA-2048 (port 39443,
    Phase 89 LAB-05). Quantum-vulnerable MEDIUM finding expected.
    """
    subj = "CN=grpc-tls.chaos.local"
    return [
        CryptoEndpoint(
            host="localhost", port=39443, protocol="GRPC-TLS",
            tls_version="TLSv1.3",
            cipher_suite="TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384",
            cert_pubkey_alg="RSA", cert_pubkey_size=2048,
            cert_sig_alg="sha256WithRSAEncryption",
            cert_subject=subj, cert_issuer=subj,
            cert_not_before=None, cert_not_after=None,
            tls_capabilities_json=None, ssh_audit_json=None,
        ),
    ]


def _build_oqs_nginx_lab_endpoints() -> list[CryptoEndpoint]:
    """oqs-nginx profile — PQC-hybrid nginx (port 39444, Phase 90 PQC-01).

    Negotiates the X25519MLKEM768 hybrid KEM (NamedGroup 4588) and serves an
    ML-DSA-65 (Dilithium) certificate. Both are quantum-safe (NIST level 3).
    The bare hybrid group name is observed by the raw openssl s_client probe
    (Phase 90 PQC-02) and maps through builder _KEX_MAP directly.
    """
    subj = "CN=oqs-nginx.chaos.local"
    return [
        CryptoEndpoint(
            host="localhost", port=39444, protocol="HTTPS",
            tls_version="TLSv1.3", cipher_suite="X25519MLKEM768",
            cert_pubkey_alg="ML-DSA-65", cert_pubkey_size=None,
            cert_sig_alg=None,
            cert_subject=subj, cert_issuer=subj,
            cert_not_before=None, cert_not_after=None,
            tls_capabilities_json=None, ssh_audit_json=None,
        ),
    ]


def _build_fuzz_target_lab_endpoints() -> list[CryptoEndpoint]:
    """fuzz-target profile — deliberately-weak REST service (port 20100,
    Phase 96 LAB-01). /probe accepts a forged JWT; the observed crypto is the
    RS256-signed JWT (RSA-based, quantum-vulnerable). Mirrors the jwt profile.
    """
    return [
        CryptoEndpoint(
            host="localhost", port=20100, protocol="JWT",
            tls_version=None, cipher_suite=None,
            cert_pubkey_alg="RSA", cert_pubkey_size=2048,
            cert_sig_alg=None, cert_subject=None, cert_issuer=None,
            cert_not_before=None, cert_not_after=None,
            tls_capabilities_json=None, ssh_audit_json=None,
        ),
    ]


def _build_hwcompat_lab_endpoints() -> list[CryptoEndpoint]:
    """hwcompat profile — hardware fingerprinting lab (Phase 127 HWCOMPAT-02).

    hwcompat-ssh (port 20221) is an OpenSSH server exercising the
    banner-fingerprinting path; the incidental SSH crypto (modern, standard
    algorithms) is the CBOM observable here. hwcompat-http (20222) emits HTTP
    management headers only — no cataloguable algorithm.
    """
    import json as _json
    _SSH_AUDIT_JSON = _json.dumps({
        "kex": [{"algorithm": "curve25519-sha256"}],
        "key": [{"algorithm": "ssh-ed25519"}],
        "enc": [{"algorithm": "aes256-gcm"}],
        "mac": [{"algorithm": "hmac-sha2-256"}],
    })
    return [
        CryptoEndpoint(
            host="localhost", port=20221, protocol="SSH",
            tls_version=None, cipher_suite=None,
            cert_pubkey_alg="ssh-ed25519", cert_pubkey_size=None,
            cert_sig_alg=None, cert_subject=None, cert_issuer=None,
            cert_not_before=None, cert_not_after=None,
            tls_capabilities_json=None, ssh_audit_json=_SSH_AUDIT_JSON,
        ),
    ]
