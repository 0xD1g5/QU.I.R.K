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
    cert_not_after: datetime | None = None
    cert_subject: str | None = None
    cert_issuer: str | None = None


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


if __name__ == "__main__":
    unittest.main()
