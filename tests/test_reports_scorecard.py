from dataclasses import dataclass
from datetime import datetime
from types import SimpleNamespace
import unittest

from quirk.reports.scorecard import build_scorecard_markdown


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
    tls_supported_versions: str | None = None


class ScorecardReportTests(unittest.TestCase):
    def test_scorecard_includes_required_sections(self) -> None:
        cfg = SimpleNamespace(assessment=SimpleNamespace(name="Test Assessment"))
        endpoints = [
            _Ep(host="a", port=8000, protocol="HTTP"),
            _Ep(host="b", port=5555, protocol="UNKNOWN"),
            _Ep(
                host="c",
                port=443,
                protocol="TLS",
                scanned_at=datetime(2026, 2, 19, 12, 0, 0),
                cert_pubkey_alg="RSA",
                cert_not_after=datetime(2026, 12, 31, 0, 0, 0),
                cert_subject="CN=c",
                cert_issuer="CN=ca",
                tls_supported_versions="TLSv1.2,TLSv1.3",
            ),
        ]
        findings = [
            {
                "severity": "HIGH",
                "host": "a",
                "port": 8000,
                "title": "Plaintext HTTP service detected",
                "recommendation": "Use TLS.",
            },
            {
                "severity": "MEDIUM",
                "host": "b",
                "port": 5555,
                "title": "Unknown open service",
                "recommendation": "Investigate.",
            },
        ]

        md = build_scorecard_markdown(cfg, endpoints, findings)
        self.assertIn("# Scorecard — Test Assessment", md)
        self.assertIn("## Snapshot", md)
        self.assertIn("## Interpretation", md)
        self.assertIn("## Top Drivers (5)", md)
        self.assertIn("## NOW Actions (Top 3)", md)
        self.assertIn("| Driver | Impact |", md)
        self.assertIn("Plaintext HTTP exposure", md)
        self.assertIn("1. **Remove plaintext HTTP exposure**", md)


if __name__ == "__main__":
    unittest.main()
