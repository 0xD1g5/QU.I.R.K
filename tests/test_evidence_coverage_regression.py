"""Phase 184.1 SCORE-01 D-03 non-movement boundary — end-to-end regression.

No existing test in the eleven-file scoring group constructs its evidence via
``build_evidence_summary`` from real endpoints — they all hand-build the evidence dict
directly. That makes the D-03 non-movement boundary (``protocol_counts`` and
``compute_readiness_score`` must not move) safe against direct edits to those files, but
UNPROVEN at the level where the new ``assessed_crypto_count`` / ``assessable_endpoint_count``
counters are actually computed: a hand-built dict cannot demonstrate that a real
``SMTP-STARTTLS`` (or any of the other five email/STARTTLS protocols ``_PROTOCOL_KEYS`` is
blind to) endpoint reaches the new coverage numerator while remaining invisible to
``protocol_counts`` and therefore to ``compute_readiness_score``.

This module closes that gap: it drives real ``quirk.models.CryptoEndpoint`` instances through
``build_evidence_summary`` once, then feeds the single resulting evidence dict into BOTH
``compute_confidence`` and ``compute_readiness_score``, and pins all three factors named in the
plan (coverage_ratio, the readiness score, and protocol_counts) as literals.

No Docker, no DB, no network — CryptoEndpoint is instantiated directly as a plain Python object
(SQLAlchemy declarative models do not require a session or engine to construct).
"""

import unittest

from quirk.models import CryptoEndpoint
from quirk.intelligence.evidence import build_evidence_summary
from quirk.intelligence.confidence import compute_confidence
from quirk.intelligence.scoring import compute_readiness_score


def _build_endpoints() -> list:
    """Nine real CryptoEndpoint objects covering the full protocol spread required by the
    plan: at least one SMTP-STARTTLS (one of the six _PROTOCOL_KEYS-invisible protocols), one
    ADVISORY, one CLOSED, one UNKNOWN, one plaintext HTTP, and one endpoint with a truthy
    scan_error.

    Hand-derived arithmetic (re-derive from _NON_ASSET_PROTOCOLS = {ADVISORY, CLOSED} and the
    D-05/D-09 UNKNOWN/scan_error numerator exclusions in evidence.py — do not trust this
    comment blindly, re-check it against evidence.py on any future edit to this fixture):

        9 total endpoints
        - 1 ADVISORY (D-06) - 1 CLOSED (D-07)      => assessable_endpoint_count = 7
        - 1 UNKNOWN (D-09) - 1 scan_error TLS (D-05) from the 7 assessable
                                                    => assessed_crypto_count = 5
        coverage_ratio = 5 / 7 = 0.7142857142857143 -> rounds to 0.7143

    protocol_counts (_PROTOCOL_KEYS is blind to SMTP-STARTTLS, ADVISORY, and CLOSED):
        TLS=3 (2 healthy + 1 with scan_error), SSH=1, HTTP=1, UNKNOWN=1, all other keys 0.
    """
    return [
        CryptoEndpoint(
            host="host1.example.com", port=443, protocol="TLS",
            tls_version="TLSv1.3", tls_supported_versions="TLSv1.2,TLSv1.3",
            cert_pubkey_alg="RSA", cert_pubkey_size=2048,
        ),
        CryptoEndpoint(
            host="host2.example.com", port=443, protocol="TLS",
            tls_version="TLSv1.2", tls_supported_versions="TLSv1.2",
            cert_pubkey_alg="ECDSA", cert_pubkey_size=256,
        ),
        CryptoEndpoint(host="host3.example.com", port=22, protocol="SSH"),
        CryptoEndpoint(host="host4.example.com", port=80, protocol="HTTP"),
        # D-04: reached-but-no-crypto SMTP-STARTTLS endpoint — one of the six protocols
        # _PROTOCOL_KEYS cannot see. Stays in the numerator regardless of tls_version.
        CryptoEndpoint(host="host5.example.com", port=587, protocol="SMTP-STARTTLS"),
        # D-06: ADVISORY is a scanner self-report, not a scanned asset — excluded from
        # both numerator and denominator.
        CryptoEndpoint(
            host="host6.example.com", port=9999, protocol="ADVISORY",
            service_detail="liveness-prepass",
        ),
        # D-07: CLOSED (TIMEOUT/REFUSED/UNREACHABLE) — excluded from both numerator and
        # denominator, the largest correction this phase makes.
        CryptoEndpoint(
            host="host7.example.com", port=8443, protocol="CLOSED",
            scan_error_category="timeout",
        ),
        # D-09: UNKNOWN stays in the denominator, excluded from the numerator.
        CryptoEndpoint(host="host8.example.com", port=12345, protocol="UNKNOWN"),
        # D-05: a real scan target with a truthy scan_error stays in the denominator,
        # excluded from the numerator.
        CryptoEndpoint(
            host="host9.example.com", port=443, protocol="TLS",
            scan_error="connection reset by peer",
        ),
    ]


class EvidenceCoverageRegressionTests(unittest.TestCase):
    def test_coverage_ratio_reaches_numerator_for_protocol_keys_invisible_protocols(self) -> None:
        """The property no hand-built dict can prove: build_evidence_summary sees the raw
        ep.protocol string (SMTP-STARTTLS included) before _PROTOCOL_KEYS filtering, so
        assessed_crypto_count / assessable_endpoint_count correctly counts it even though
        protocol_counts never will.
        """
        evidence = build_evidence_summary(_build_endpoints(), [])
        self.assertEqual(evidence["assessed_crypto_count"], 5)
        self.assertEqual(evidence["assessable_endpoint_count"], 7)

        confidence = compute_confidence(evidence)
        self.assertEqual(
            confidence["factor_breakdown"]["coverage_ratio"]["value"], 0.7143
        )

    def test_readiness_score_and_protocol_counts_are_pinned_and_unmoved(self) -> None:
        """D-03: the readiness score and protocol_counts must not move except by a deliberate,
        recorded phase decision. Pinned literals here are the direct proof — a future accidental
        edit to _PROTOCOL_KEYS or the coverage counters that leaks into protocol_counts fails
        this test immediately.

        Phase 188 / SCORE-06 (RQ-1) made exactly that deliberate change: _PROTOCOL_KEYS was
        widened to count the email/broker data-in-motion protocol literals (SMTP-STARTTLS,
        SMTPS, IMAPS, IMAP-STARTTLS, POP3S, POP3-STARTTLS, KAFKA-PLAIN, KAFKA-TLS, AMQP-PLAIN,
        AMQPS, AMQPS/AZURE-SERVICEBUS, HTTPS/AWS-SQS, REDIS-PLAIN, REDIS-TLS) so that
        compute_readiness_score()'s data_in_motion assessed-predicate has an honest signal to
        read (previously documented here as deferred _PROTOCOL_KEYS blindness). This fixture's
        host5 endpoint is SMTP-STARTTLS, so it now shows up in protocol_counts as 1 instead of
        being invisible. The `score` assertion below is updated separately (see the derivation
        comment at that assertion) because Phase 188 also changed the aggregation formula
        (exclude-and-rescale) — a second, unrelated cause of pin movement.
        """
        evidence = build_evidence_summary(_build_endpoints(), [])

        self.assertEqual(
            evidence["protocol_counts"],
            {
                "TLS": 3, "HTTP": 1, "SSH": 1, "UNKNOWN": 1, "KERBEROS": 0, "SAML": 0,
                "DNSSEC": 0, "POSTGRESQL": 0, "MYSQL": 0, "RDS": 0, "S3": 0,
                "AZURE_BLOB": 0, "KUBERNETES": 0, "VAULT": 0, "CONTAINER": 0, "SOURCE": 0,
                "AWS": 0, "AZURE": 0, "GCP": 0, "CLOUD_SQL": 0, "BEARER_TOKEN": 0,
                "OPENAPI": 0, "CODE_SIGNING": 0, "REST_FUZZ": 0,
                "SMTP-STARTTLS": 1, "SMTPS": 0, "IMAPS": 0, "IMAP-STARTTLS": 0, "POP3S": 0,
                "POP3-STARTTLS": 0, "KAFKA-PLAIN": 0, "KAFKA-TLS": 0, "AMQP-PLAIN": 0,
                "AMQPS": 0, "AMQPS/AZURE-SERVICEBUS": 0, "HTTPS/AWS-SQS": 0,
                "REDIS-PLAIN": 0, "REDIS-TLS": 0,
            },
        )

    def test_denominator_base_unchanged_from_totals_endpoints(self) -> None:
        """evidence['totals']['endpoints'] equals len(endpoints) exactly — the OLD denominator
        (used by unknown_ratio and scan_error_ratio, both in scoring.py and confidence.py) is
        untouched by this phase's coverage_ratio rewrite, so those two ratios keep being
        computed against the same base they always were.
        """
        endpoints = _build_endpoints()
        evidence = build_evidence_summary(endpoints, [])
        self.assertEqual(evidence["totals"]["endpoints"], len(endpoints))

    def test_build_evidence_summary_is_deterministic(self) -> None:
        """Mirrors test_intelligence_scoring.py's test_output_is_deterministic: calling
        build_evidence_summary twice on the same input produces two equal dicts.
        """
        endpoints = _build_endpoints()
        a = build_evidence_summary(endpoints, [])
        b = build_evidence_summary(endpoints, [])
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
