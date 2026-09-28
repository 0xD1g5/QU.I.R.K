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
    service_detail: str | None = None


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


def test_ecdsa_ed25519_credits_ecdsa_bucket():
    """SCOREFIX-03 / WR-05: EdDSA (Ed25519) folds into ECDSA agility bucket."""
    assert _ecdsa_count("ED25519") == 1


def _saml_count(alg: str) -> int:
    summary = build_evidence_summary([_Ep(host="h", port=443, protocol="SAML",
                                          cert_pubkey_alg=alg)])
    return summary.get("saml_weak_signing_count", 0)


def test_saml_sha1_mixed_case():
    """WR-10 / D-02: SAML alg in {SHA-1, sha1, #rsa-sha1} all increment counter."""
    for alg in ("SHA-1", "sha1", "#rsa-sha1"):
        assert _saml_count(alg) == 1, f"missed: {alg!r}"


def _saml_weak_ep(host: str, port: int, service_detail: str | None) -> _Ep:
    """A weak-key SAML endpoint row (RSA-1024, matches the `< 2048` branch)."""
    return _Ep(host=host, port=port, protocol="SAML", cert_pubkey_alg="RSA",
               cert_pubkey_size=1024, service_detail=service_detail)


class SamlWeakSigningDedupeTests(unittest.TestCase):
    """XSURF-01 / D-03: saml_weak_signing_count dedupes on (host, port, cert serial),
    the same key plan 210-02 applied to finding emission. This counter iterates raw
    CryptoEndpoint rows independently of finding_list (see the structural grep in
    210-03-SUMMARY.md) and does NOT self-heal from that finding-side dedupe."""

    def test_same_serial_dual_use_pair_counts_one(self) -> None:
        endpoints = [
            _saml_weak_ep("10.80.0.41", 8080, "urn:x|use=signing|serial=0a1b"),
            _saml_weak_ep("10.80.0.41", 8080, "urn:x|use=encryption|serial=0a1b"),
        ]
        summary = build_evidence_summary(endpoints)
        assert summary["saml_weak_signing_count"] == 1, summary["saml_weak_signing_count"]

    def test_distinct_serials_count_two(self) -> None:
        endpoints = [
            _saml_weak_ep("10.80.0.41", 8080, "urn:x|use=signing|serial=0a1b"),
            _saml_weak_ep("10.80.0.41", 8080, "urn:x|use=encryption|serial=0a1c"),
        ]
        summary = build_evidence_summary(endpoints)
        assert summary["saml_weak_signing_count"] == 2, summary["saml_weak_signing_count"]

    def test_same_serial_different_host_counts_two(self) -> None:
        endpoints = [
            _saml_weak_ep("10.80.0.41", 8080, "urn:x|use=signing|serial=0a1b"),
            _saml_weak_ep("10.80.0.42", 8080, "urn:x|use=encryption|serial=0a1b"),
        ]
        summary = build_evidence_summary(endpoints)
        assert summary["saml_weak_signing_count"] == 2, summary["saml_weak_signing_count"]

    def test_same_serial_different_port_counts_two(self) -> None:
        endpoints = [
            _saml_weak_ep("10.80.0.41", 8080, "urn:x|use=signing|serial=0a1b"),
            _saml_weak_ep("10.80.0.41", 8443, "urn:x|use=encryption|serial=0a1b"),
        ]
        summary = build_evidence_summary(endpoints)
        assert summary["saml_weak_signing_count"] == 2, summary["saml_weak_signing_count"]

    def test_missing_serial_token_never_deduped(self) -> None:
        """Fail-open convention from plan 210-02's test of the same name: a row with
        no serial= token must never be deduped against another serial-less row."""
        endpoints = [
            _saml_weak_ep("10.80.0.41", 8080, "urn:x|use=signing"),
            _saml_weak_ep("10.80.0.41", 8080, "urn:x|use=encryption"),
        ]
        summary = build_evidence_summary(endpoints)
        assert summary["saml_weak_signing_count"] == 2, summary["saml_weak_signing_count"]

    def test_ratio_matches_deduped_count(self) -> None:
        endpoints = [
            _saml_weak_ep("10.80.0.41", 8080, "urn:x|use=signing|serial=0a1b"),
            _saml_weak_ep("10.80.0.41", 8080, "urn:x|use=encryption|serial=0a1b"),
        ]
        summary = build_evidence_summary(endpoints)
        expected = round(summary["saml_weak_signing_count"] / len(endpoints), 4)
        assert summary["identity_saml_weak_signing_ratio"] == expected


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
