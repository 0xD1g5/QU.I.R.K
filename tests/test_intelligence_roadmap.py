import unittest

from quirk.intelligence.roadmap import build_phased_roadmap


def _evidence() -> dict:
    return {
        "totals": {"endpoints": 10, "findings": 7},
        "protocol_counts": {"TLS": 6, "HTTP": 2, "SSH": 1, "UNKNOWN": 1},
        "plaintext_http_count": 1,
        "http_on_tls_port_count": 1,
        "mtls_present_count": 1,
        "certificate_observations": {
            "expired_count": 1,
            "expiring_count": 2,
            "self_signed_count": 1,
        },
        "cert_key_type_counts": {"RSA": 6, "ECDSA": 0},
        "scan_error": {"rate": 0.3},
        "finding_severity_counts": {
            "CRITICAL": 0,
            "HIGH": 2,
            "MEDIUM": 1,
            "LOW": 1,
            "INFO": 1,
        },
        "tls_enum_coverage_ratio": 0.7,
    }


def _scoring() -> dict:
    return {
        "drivers": [
            {"reason": "Plaintext HTTP exposure", "points": -5},
            {"reason": "Assessment visibility blockers", "points": -3},
            {"reason": "Expired certificates", "points": -2},
        ]
    }


class IntelligenceRoadmapTests(unittest.TestCase):
    def test_build_phased_roadmap_shape_and_limits(self) -> None:
        result = build_phased_roadmap(_evidence(), _scoring())
        self.assertIn("roadmap_version", result)
        self.assertIn("item_count", result)
        self.assertIn("phase_counts", result)
        self.assertIn("items", result)
        self.assertEqual(result["item_count"], len(result["items"]))
        self.assertGreaterEqual(result["item_count"], 6)
        self.assertLessEqual(result["item_count"], 12)

        for item in result["items"]:
            self.assertEqual(
                set(item.keys()),
                {"phase", "title", "why", "owner_placeholder", "dependencies", "timeframe"},
            )
            self.assertIn(item["phase"], {"NOW", "NEXT", "LATER"})
            self.assertIsInstance(item["dependencies"], list)

    def test_output_is_deterministic(self) -> None:
        first = build_phased_roadmap(_evidence(), _scoring())
        second = build_phased_roadmap(_evidence(), _scoring())
        self.assertEqual(first, second)

    def test_rules_create_expected_items(self) -> None:
        result = build_phased_roadmap(_evidence(), _scoring())
        titles = {item["title"]: item for item in result["items"]}

        self.assertIn("Remove plaintext HTTP exposure", titles)
        self.assertIn("Classify unknown open services", titles)
        self.assertIn("Standardize mTLS lifecycle operations", titles)
        self.assertIn("Plan ECDSA adoption", titles)
        self.assertIn("Driver:", titles["Remove plaintext HTTP exposure"]["why"])

    def test_zero_endpoints_generates_minimum_roadmap(self) -> None:
        result = build_phased_roadmap({"totals": {"endpoints": 0}}, {"drivers": []})
        self.assertEqual(result["item_count"], 6)
        phases = [item["phase"] for item in result["items"]]
        self.assertIn("NOW", phases)
        self.assertIn("NEXT", phases)
        self.assertIn("LATER", phases)


if __name__ == "__main__":
    unittest.main()
