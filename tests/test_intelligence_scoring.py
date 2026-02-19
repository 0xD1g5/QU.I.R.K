import unittest

from qcscan.intelligence.scoring import compute_readiness_score


def _base_evidence() -> dict:
    return {
        "totals": {"endpoints": 10, "findings": 4},
        "protocol_counts": {"TLS": 6, "HTTP": 2, "SSH": 1, "UNKNOWN": 1},
        "plaintext_http_count": 1,
        "http_on_tls_port_count": 1,
        "mtls_present_count": 1,
        "cert_key_type_counts": {"RSA": 6, "ECDSA": 2},
        "certificate_observations": {
            "certs_observed": 8,
            "expired_count": 0,
            "expiring_count": 1,
            "self_signed_count": 0,
        },
        "scan_error": {"count": 1, "rate": 0.1},
        "finding_severity_counts": {"CRITICAL": 0, "HIGH": 2, "MEDIUM": 1, "LOW": 0, "INFO": 1},
    }


class ReadinessScoringTests(unittest.TestCase):
    def test_compute_readiness_score_shape(self) -> None:
        result = compute_readiness_score(_base_evidence())
        self.assertIn("score", result)
        self.assertIn("rating", result)
        self.assertIn("subscores", result)
        self.assertIn("drivers", result)
        self.assertEqual(set(result["subscores"].keys()), {"hygiene", "modern_tls", "identity_trust", "agility_signals"})
        self.assertGreaterEqual(result["score"], 0)
        self.assertLessEqual(result["score"], 100)
        self.assertLessEqual(len(result["drivers"]), 5)

    def test_risky_evidence_scores_lower(self) -> None:
        safe = _base_evidence()
        risky = _base_evidence()
        risky["plaintext_http_count"] = 4
        risky["http_on_tls_port_count"] = 3
        risky["scan_error"] = {"count": 5, "rate": 0.5}
        risky["certificate_observations"]["expired_count"] = 3
        risky["certificate_observations"]["self_signed_count"] = 2
        risky["cert_key_type_counts"] = {"RSA": 8, "ECDSA": 0}
        risky["finding_severity_counts"]["HIGH"] = 4

        safe_score = compute_readiness_score(safe)["score"]
        risky_score = compute_readiness_score(risky)["score"]
        self.assertLess(risky_score, safe_score)

    def test_output_is_deterministic(self) -> None:
        evidence = _base_evidence()
        a = compute_readiness_score(evidence)
        b = compute_readiness_score(evidence)
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
