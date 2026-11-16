"""Phase 236 (XSURF-13, D-07): one CryptoEndpoint row set per finding family.

``FAMILY_ROWS`` maps a family name to a zero-arg builder returning the rows
that family contributes. The behaviour gate in
``tests/test_severity_divergence_behaviour.py`` runs the report deriver and the
dashboard deriver over each family on its own, so a residual severity
divergence is attributable to exactly one family.

Rules:
  * every family uses its own host and its own ids, and contains only its own
    rows (no shared healthy rows);
  * a family may hold more than one row when the finding only arises from a
    cross-endpoint pass (``_postprocess_findings`` rewrites findings using
    sibling rows on the same host:port);
  * naive datetimes only, no Python 3.12+ APIs (CI runs 3.11).
"""
from __future__ import annotations

import datetime
import itertools
from typing import Callable, Dict, List

from quirk.models import CryptoEndpoint

_PAST = datetime.datetime(2020, 1, 1)
_FUTURE = datetime.datetime(2035, 1, 1)
_NOW = datetime.datetime(2026, 10, 15, 12, 0, 0)

_ids = itertools.count(1000)
_hosts = itertools.count(1)


def _ep(host: str, **kw) -> CryptoEndpoint:
    base = dict(id=next(_ids), host=host, port=443, protocol="TLS",
                scanned_at=_NOW)
    base.update(kw)
    return CryptoEndpoint(**base)


def _tls(host: str, **kw) -> CryptoEndpoint:
    """A TLS row healthy in every respect except what ``kw`` overrides."""
    base = dict(
        cert_subject="CN=ok.example", cert_issuer="CN=Real CA",
        cert_pubkey_alg="ECDSA", cert_pubkey_size=256,
        cert_not_before=_PAST, cert_not_after=_FUTURE,
        tls_version="TLSv1.3", tls_supported_versions="TLSv1.3",
        chain_verified=True,
    )
    base.update(kw)
    return _ep(host, **base)


def _fam_host(n: int) -> str:
    return "10.236.%d.1" % n


def _legacy_max_tls10():
    return [_tls(_fam_host(1), tls_version="TLSv1",
                 tls_supported_versions="TLSv1")]


def _legacy_max_sslv3():
    return [_tls(_fam_host(2), tls_version="SSLv3",
                 tls_supported_versions="SSLv3", tls_weak_ciphers_present=True)]


def _legacy_offered_with_tls12():
    return [_tls(_fam_host(3), tls_version="TLSv1.2",
                 tls_supported_versions="TLSv1.2,TLSv1.1")]


def _weak_cipher():
    return [_tls(_fam_host(4), tls_weak_ciphers_present=True)]


def _ecdsa_192():
    return [_tls(_fam_host(5), cert_pubkey_alg="ECDSA", cert_pubkey_size=192)]


def _rsa_1024():
    return [_tls(_fam_host(6), cert_pubkey_alg="RSA", cert_pubkey_size=1024)]


def _cert_expired():
    return [_tls(_fam_host(7), cert_not_after=_PAST)]


def _cert_near_expiry():
    return [_tls(_fam_host(8), cert_not_after=datetime.datetime.now()
                 + datetime.timedelta(days=10))]


def _tls_untrusted_ca():
    return [_tls(_fam_host(9), chain_verified=False)]


def _tls_self_signed():
    return [_tls(_fam_host(10), cert_subject="CN=self", cert_issuer="CN=self")]


def _container(host: str, pkg: str, version: str, **kw):
    return [_ep(host, port=0, protocol="CONTAINER", cipher_suite=pkg,
                tls_version=version, **kw)]


def _container_openssl_111():
    return _container(_fam_host(11), "openssl", "1.1.1w")


def _container_openssl_102():
    return _container(_fam_host(12), "openssl", "1.0.2u")


def _container_pycrypto_old():
    return _container(_fam_host(13), "cryptography", "2.9.2")


def _container_scan_error():
    return _container(_fam_host(14), "", "", scan_error="syft failed")


def _kerberos_rc4():
    return [_ep(_fam_host(15), port=88, protocol="KERBEROS",
                service_detail="etype:23:rc4-hmac:HIGH")]


def _dnssec_none():
    return [_ep(_fam_host(16), port=53, protocol="DNSSEC",
                cert_pubkey_alg="NONE", service_detail="no DNSKEY")]


def _dnssec_nsec():
    return [_ep(_fam_host(17), port=53, protocol="DNSSEC",
                cert_pubkey_alg="NSEC", service_detail="nsec")]


def _email_weak():
    return [_ep(_fam_host(18), port=465, protocol="SMTPS",
                tls_version="TLSv1.2",
                cipher_suite="TLS_RSA_WITH_AES_128_CBC_SHA")]


def _broker():
    return [_ep(_fam_host(19), port=9092, protocol="KAFKA-PLAIN")]


def _broker_tls_weak():
    return [_ep(_fam_host(20), port=9093, protocol="KAFKA-TLS",
                tls_version="TLSv1.2",
                cipher_suite="TLS_RSA_WITH_AES_128_CBC_SHA")]


def _plaintext_amqp():
    return [_ep(_fam_host(21), port=5672, protocol="AMQP-PLAIN")]


def _plaintext_redis():
    return [_ep(_fam_host(22), port=6379, protocol="REDIS-PLAIN")]


def _codesign():
    return [_ep(_fam_host(23), port=0, protocol="CODE_SIGNING",
                cert_subject="CN=Signer", cert_issuer="CN=Real CA",
                cert_pubkey_alg="RSA", cert_pubkey_size=4096,
                cert_not_before=_PAST, cert_not_after=_PAST,
                codesign_scan_json='{"reasons": ["expired"]}')]


def _codesign_weak_alg():
    return [_ep(_fam_host(24), port=0, protocol="CODE_SIGNING",
                cert_subject="CN=Signer2", cert_issuer="CN=Real CA",
                cert_pubkey_alg="RSA", cert_pubkey_size=1024,
                cert_not_before=_PAST, cert_not_after=_FUTURE,
                codesign_scan_json='{"reasons": ["weak-rsa-key"]}')]


def _saml():
    return [_ep(_fam_host(25), port=8080, protocol="SAML",
                cert_pubkey_alg="RSA", cert_pubkey_size=1024,
                service_detail="urn:mh-saml-idp|use=signing|serial=0a1b")]


def _saml_weak_encryption():
    return [_ep(_fam_host(26), port=8080, protocol="SAML",
                cert_pubkey_alg="RSA", cert_pubkey_size=1024,
                service_detail="urn:mh-saml-idp|use=encryption|serial=0c2d")]


def _saml_sha1():
    return [_ep(_fam_host(27), port=8080, protocol="SAML",
                cert_pubkey_alg="SHA1", service_detail="urn:mh-saml-idp")]


def _saml_oidc_rs256():
    return [_ep(_fam_host(28), port=8080, protocol="SAML",
                cert_pubkey_alg="RS256", service_detail="oidc-jwks")]


def _plaintext_http():
    return [_ep(_fam_host(29), port=80, protocol="HTTP")]


def _http_on_tls_port():
    return [_ep(_fam_host(30), port=443, protocol="HTTP")]


def _http_on_tls_port_with_mtls_pair():
    host = _fam_host(31)
    return [
        _ep(host, port=443, protocol="HTTP"),
        _ep(host, port=443, protocol="TLS", tls_blocker_reason="MTLS_REQUIRED"),
    ]


def _jwks_verify_disabled():
    return [_ep(_fam_host(32), port=443, protocol="ADVISORY",
                service_detail="JWKS/verify-disabled")]


def _bearer_unsigned():
    return [_ep(_fam_host(33), port=0, protocol="BEARER_TOKEN",
                cert_pubkey_alg="none", service_detail="bearer")]


def _tls_scan_error_with_fields():
    """The _scan_one_fallback shape: tls_version is set at the handshake and
    the catch-all sets scan_error afterwards (review WR-02, 236-VERIFICATION
    gap 1). The report sends every scan_error row to its scan-error branch."""
    return [_tls(_fam_host(34), tls_version="TLSv1",
                 tls_supported_versions=None,
                 cert_subject="CN=legacy-device", cert_issuer="CN=legacy-device",
                 scan_error="TLS_ERROR: certificate parse failed after handshake",
                 tls_blocker_reason="TLS_ERROR")]


def _http_scan_error():
    """Same guard asymmetry on the HTTP block; the report emits INFO."""
    return [_ep(_fam_host(35), port=80, protocol="HTTP",
                scan_error="TIMEOUT: read timed out")]


def _legacy_inconsistent_max():
    return [_tls(_fam_host(36), tls_version="TLSv1",
                 tls_supported_versions="TLSv1,TLSv1.2")]


def _legacy_supported_only():
    # Both surfaces give LOW today (review WR-07, filed not fixed).
    return [_tls(_fam_host(37), tls_version=None,
                 tls_supported_versions="TLSv1,TLSv1.1")]


def _ecdsa_256():
    return [_tls(_fam_host(38), cert_pubkey_alg="ECDSA", cert_pubkey_size=256)]


def _rsa_2048():
    # rsa_size_0 / rsa_pss_1024 are deliberately NOT families: they diverge
    # (WR-03), tracked by LEDGER 261116-rsa-undersized-key-predicate-differs-across-surfaces.
    return [_tls(_fam_host(39), cert_pubkey_alg="RSA", cert_pubkey_size=2048)]


FAMILY_ROWS: Dict[str, Callable[[], List[CryptoEndpoint]]] = {
    "legacy_max_tls10": _legacy_max_tls10,
    "legacy_max_sslv3": _legacy_max_sslv3,
    "legacy_offered_with_tls12": _legacy_offered_with_tls12,
    "weak_cipher": _weak_cipher,
    "ecdsa_192": _ecdsa_192,
    "rsa_1024": _rsa_1024,
    "cert_expired": _cert_expired,
    "cert_near_expiry": _cert_near_expiry,
    "tls_untrusted_ca": _tls_untrusted_ca,
    "tls_self_signed": _tls_self_signed,
    "container_openssl_111": _container_openssl_111,
    "container_openssl_102": _container_openssl_102,
    "container_pycrypto_old": _container_pycrypto_old,
    "container_scan_error": _container_scan_error,
    "kerberos_rc4": _kerberos_rc4,
    "dnssec_none": _dnssec_none,
    "dnssec_nsec": _dnssec_nsec,
    "email_weak": _email_weak,
    "broker": _broker,
    "broker_tls_weak": _broker_tls_weak,
    "plaintext_amqp": _plaintext_amqp,
    "plaintext_redis": _plaintext_redis,
    "codesign": _codesign,
    "codesign_weak_alg": _codesign_weak_alg,
    "saml": _saml,
    "saml_weak_encryption": _saml_weak_encryption,
    "saml_sha1": _saml_sha1,
    "saml_oidc_rs256": _saml_oidc_rs256,
    "plaintext_http": _plaintext_http,
    "http_on_tls_port": _http_on_tls_port,
    "http_on_tls_port_with_mtls_pair": _http_on_tls_port_with_mtls_pair,
    "jwks_verify_disabled": _jwks_verify_disabled,
    "bearer_unsigned": _bearer_unsigned,
    "tls_scan_error_with_fields": _tls_scan_error_with_fields,
    "http_scan_error": _http_scan_error,
    "legacy_inconsistent_max": _legacy_inconsistent_max,
    "legacy_supported_only": _legacy_supported_only,
    "ecdsa_256": _ecdsa_256,
    "rsa_2048": _rsa_2048,
}


def ALL_ROWS() -> List[CryptoEndpoint]:
    rows: List[CryptoEndpoint] = []
    for build in FAMILY_ROWS.values():
        rows.extend(build())
    return rows
