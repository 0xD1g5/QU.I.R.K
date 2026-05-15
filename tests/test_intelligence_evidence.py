from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import unittest

from quirk.intelligence.evidence import build_evidence_summary


@dataclass
class _Ep:
    host: str
    port: int
    protocol: str
    scanned_at: datetime | None = None
    scan_error: str | None = None
    tls_blocker_reason: str | None = None
    cert_pubkey_alg: str | None = None
    cert_pubkey_size: int | None = None
    cert_not_after: datetime | None = None
    cert_subject: str | None = None
    cert_issuer: str | None = None
    tls_version: str | None = None
    cipher_suite: str | None = None


class EvidenceSummaryTests(unittest.TestCase):
    def test_build_evidence_summary_counts(self) -> None:
        endpoints = [
            _Ep(
                host="a",
                port=443,
                protocol="TLS",
                scanned_at=datetime(2026, 2, 19, 20, 0, 0),
                cert_pubkey_alg="RSA",
                cert_not_after=datetime(2026, 2, 25, 0, 0, 0),
                cert_subject="CN=a",
                cert_issuer="CN=a",
            ),
            _Ep(
                host="b",
                port=8443,
                protocol="TLS",
                scanned_at=datetime(2026, 2, 19, 20, 0, 1),
                cert_pubkey_alg="ECDSA",
                cert_not_after=datetime(2026, 2, 10, 0, 0, 0),
                scan_error="TIMEOUT: test",
            ),
            _Ep(host="c", port=8000, protocol="HTTP"),
            _Ep(host="d", port=2222, protocol="SSH"),
            _Ep(host="e", port=5555, protocol="UNKNOWN", tls_blocker_reason="MTLS_REQUIRED"),
        ]
        findings = [
            {"host": "c", "port": 8000, "title": "Plaintext HTTP service detected", "severity": "HIGH"},
            {"host": "c", "port": 8000, "title": "Plaintext HTTP service detected", "severity": "HIGH"},
            {"host": "c", "port": 8444, "title": "HTTP on TLS-designated port", "severity": "HIGH"},
            {"host": "e", "port": 5555, "title": "mTLS required", "severity": "INFO"},
        ]

        summary = build_evidence_summary(
            endpoints,
            findings,
            expiring_days=10,
            reference_utc=datetime(2026, 2, 19, 20, 0, 0),
        )

        self.assertEqual(summary["protocol_counts"]["TLS"], 2)
        self.assertEqual(summary["protocol_counts"]["HTTP"], 1)
        self.assertEqual(summary["protocol_counts"]["SSH"], 1)
        self.assertEqual(summary["protocol_counts"]["UNKNOWN"], 1)
        self.assertEqual(summary["plaintext_http_count"], 1)
        self.assertEqual(summary["http_on_tls_port_count"], 1)
        self.assertEqual(summary["mtls_present_count"], 1)
        self.assertEqual(summary["cert_key_type_counts"]["RSA"], 1)
        self.assertEqual(summary["cert_key_type_counts"]["ECDSA"], 1)
        self.assertEqual(summary["certificate_observations"]["expiring_count"], 1)
        self.assertEqual(summary["certificate_observations"]["expired_count"], 1)
        self.assertEqual(summary["certificate_observations"]["self_signed_count"], 1)
        self.assertEqual(summary["scan_error"]["count"], 1)
        self.assertEqual(summary["scan_error"]["rate"], 0.2)


def test_dar_db_counters():
    """dar_ counters must be present in build_evidence_summary output (Phase 27 DB-01/DB-02)."""
    # This test will fail until dar_ counters are added to evidence.py in Plan 02
    result = build_evidence_summary([])
    assert "dar_db_plaintext_count" in result, "dar_db_plaintext_count missing from evidence summary"
    assert "dar_db_weak_ssl_count" in result, "dar_db_weak_ssl_count missing from evidence summary"
    assert "dar_db_plaintext_ratio" in result, "dar_db_plaintext_ratio missing from evidence summary"
    assert "dar_db_weak_ssl_ratio" in result, "dar_db_weak_ssl_ratio missing from evidence summary"


# ---- Phase 73 / INTEL-02 / WR-03/04/10/11 tests -------------------------------

def _ecdsa_count(cert_alg: str) -> int:
    summary = build_evidence_summary([_Ep(host="h", port=443, protocol="TLS",
                                          cert_pubkey_alg=cert_alg)])
    return summary["cert_key_type_counts"].get("ECDSA", 0)


def test_ecdsa_alias_ec():
    """WR-04 / D-03: cert_pubkey_alg='EC' increments ECDSA counter."""
    assert _ecdsa_count("EC") == 1


def test_ecdsa_alias_ecdsa():
    """WR-04 / D-03: cert_pubkey_alg='ECDSA' increments ECDSA counter."""
    assert _ecdsa_count("ECDSA") == 1


def test_ecdsa_negative_ed25519():
    """WR-04 / D-03: ED25519 input does NOT increment ECDSA counter."""
    assert _ecdsa_count("ED25519") == 0


def _saml_count(alg: str) -> int:
    summary = build_evidence_summary([_Ep(host="h", port=443, protocol="SAML",
                                          cert_pubkey_alg=alg)])
    return summary.get("saml_weak_signing_count", 0)


def test_saml_sha1_mixed_case():
    """WR-10 / D-02: SAML alg in {SHA-1, sha1, #rsa-sha1} all increment counter."""
    for alg in ("SHA-1", "sha1", "#rsa-sha1"):
        assert _saml_count(alg) == 1, f"missed: {alg!r}"


def test_motion_broker_legacy_tls():
    """WR-03 / D-10: tls_version='TLSv1.1' increments motion_broker_weak_tls_count."""
    summary = build_evidence_summary([_Ep(host="h", port=9093, protocol="KAFKA-TLS",
                                          tls_version="TLSv1.1")])
    assert summary["motion_broker_weak_tls_count"] == 1


def test_motion_email_des_cbc_now_detected():
    """WR-11 / D-02: cipher 'DES-CBC-SHA' now increments motion_email_weak_cipher_count
    (pre-fix the email predicate only checked 3DES / RC4)."""
    summary = build_evidence_summary([_Ep(host="h", port=25, protocol="SMTP-STARTTLS",
                                          tls_version="TLSv1.2",
                                          cipher_suite="DES-CBC-SHA")])
    assert summary["motion_email_weak_cipher_count"] == 1


def test_email_broker_parity_token_set():
    """WR-11 / D-02: For token-driven weak ciphers, email and broker predicates
    produce identical truth values."""
    for cipher in ("DES-CBC-SHA", "RC4-MD5", "AES128-GCM-SHA256",
                   "ECDHE-RSA-AES256-GCM-SHA384"):
        email = build_evidence_summary([_Ep(host="h", port=25,
                                            protocol="SMTP-STARTTLS",
                                            tls_version="TLSv1.2",
                                            cipher_suite=cipher)])
        broker = build_evidence_summary([_Ep(host="h", port=9093,
                                             protocol="KAFKA-TLS",
                                             tls_version="TLSv1.2",
                                             cipher_suite=cipher)])
        # Structural-RSA and ECDHE-less-AES-SHA broker special-cases excluded
        # — only token-set parity tested.
        assert (email["motion_email_weak_cipher_count"]
                == broker["motion_broker_weak_cipher_count"]), (
            f"parity failure for cipher={cipher!r}: "
            f"email={email['motion_email_weak_cipher_count']} "
            f"broker={broker['motion_broker_weak_cipher_count']}"
        )


if __name__ == "__main__":
    unittest.main()
