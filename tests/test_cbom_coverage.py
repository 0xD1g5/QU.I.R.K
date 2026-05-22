"""Per-protocol-family CBOM Pass-1 algorithm coverage assertion.

Phase 61 / CBOM-COVER-01: for each of the 14 protocol families that scanner
phases produce, build_cbom must emit at least one ALGORITHM component. If any
family regresses to zero, this test fails by ID (e.g., id="vault") so the
regression points to the specific family.

No production code is modified — this is a pure regression guard.
"""
from __future__ import annotations

import pytest
from cyclonedx.model.component import ComponentType
from cyclonedx.model.crypto import CryptoAssetType

from quirk.cbom.builder import build_cbom
from quirk.models import CryptoEndpoint


def _algorithm_components(bom):
    return [
        c for c in bom.components
        if c.type == ComponentType.CRYPTOGRAPHIC_ASSET
        and c.crypto_properties is not None
        and c.crypto_properties.asset_type == CryptoAssetType.ALGORITHM
    ]


def _make_endpoint(**overrides):
    """Factory: returns a CryptoEndpoint with all required fields defaulted to None,
    then applies overrides. Avoids 14-line constructors per family."""
    base = dict(
        host="h", port=1, protocol="TLS",
        tls_version=None, cipher_suite=None,
        cert_pubkey_alg=None, cert_pubkey_size=None,
        cert_sig_alg=None, cert_subject=None, cert_issuer=None,
        cert_not_before=None, cert_not_after=None,
        tls_capabilities_json=None, ssh_audit_json=None,
        service_detail=None,
    )
    base.update(overrides)
    return CryptoEndpoint(**base)


FAMILIES = [
    pytest.param(
        _make_endpoint(protocol="MYSQL", service_detail="MySQL/AES256-SHA-ok"),
        id="database-mysql",
    ),
    pytest.param(
        _make_endpoint(protocol="POSTGRESQL", cert_pubkey_alg="RSA", cert_pubkey_size=2048),
        id="database-postgres",
    ),
    pytest.param(
        _make_endpoint(protocol="RDS", cert_pubkey_alg="RSA", cert_pubkey_size=2048),
        id="database-rds",
    ),
    pytest.param(
        _make_endpoint(protocol="CONTAINER", cipher_suite="openssl"),
        id="container",
    ),
    pytest.param(
        _make_endpoint(protocol="SOURCE", cipher_suite="my.unknown.rule.id"),
        id="source",
    ),
    pytest.param(
        _make_endpoint(protocol="SSH", cert_pubkey_alg="ssh-rsa", cert_pubkey_size=2048),
        id="ssh-weak",
    ),
    pytest.param(
        _make_endpoint(protocol="S3", service_detail="S3/sse-kms-aws"),
        id="storage-s3",
    ),
    pytest.param(
        _make_endpoint(protocol="AZURE_BLOB", service_detail="AzureBlob/sse-cmek"),
        id="storage-azure",
    ),
    pytest.param(
        _make_endpoint(
            protocol="KAFKA-TLS",
            cipher_suite="TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384",
            tls_version="TLSv1.2",
        ),
        id="kafka-tls",
    ),
    pytest.param(
        _make_endpoint(
            protocol="SMTP-STARTTLS",
            cipher_suite="TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384",
            tls_version="TLSv1.2",
        ),
        id="email-starttls",
    ),
    pytest.param(
        _make_endpoint(protocol="VAULT", cert_pubkey_alg="rsa-2048", cert_pubkey_size=2048),
        id="vault",
    ),
    pytest.param(
        _make_endpoint(protocol="DNSSEC", cert_pubkey_alg="ECDSAP256SHA256", cert_pubkey_size=256),
        id="dnssec",
    ),
    pytest.param(
        _make_endpoint(protocol="SAML", cert_pubkey_alg="RSA", cert_pubkey_size=2048),
        id="saml",
    ),
    pytest.param(
        _make_endpoint(protocol="KERBEROS", cert_pubkey_alg="aes256-cts-hmac-sha1-96"),
        id="kerberos",
    ),
]


def _coverage_notes(bom) -> list[str]:
    """Return quirk:coverage-note values from Bom root component (D-06 markers)."""
    if bom.metadata and bom.metadata.component:
        return [
            p.value
            for p in (bom.metadata.component.properties or [])
            if p.name == "quirk:coverage-note"
        ]
    return []


# Protocol families that emit D-06 affirmative coverage notes instead of
# algorithm components when no cryptographic algorithm is directly observed
# (Phase 88 D-05/D-06 / SCORE-CBOM-01). These families are excluded from the
# algo-component gate and asserted to emit a coverage note instead.
_COVERAGE_NOTE_FAMILIES = frozenset({"CONTAINER", "SOURCE"})


@pytest.mark.parametrize("ep", FAMILIES)
def test_protocol_family_emits_algo_component(ep):
    bom = build_cbom([ep])
    algos = _algorithm_components(bom)
    if ep.protocol in _COVERAGE_NOTE_FAMILIES:
        # D-06: these families emit affirmative coverage notes, not algo components
        notes = _coverage_notes(bom)
        assert notes, (
            f"Protocol family {ep.protocol!r} emitted zero algorithm components and "
            f"no quirk:coverage-note — Pass-1 D-06 branch missing or broken. "
            f"Components: {[c.name for c in bom.components]}"
        )
    else:
        assert len(algos) >= 1, (
            f"Protocol family {ep.protocol!r} emitted zero algorithm components — "
            f"Pass-1 branch missing or broken. Components: {[c.name for c in bom.components]}"
        )
