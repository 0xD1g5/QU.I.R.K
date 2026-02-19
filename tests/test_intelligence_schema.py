import json
import unittest

from qcscan.intelligence.schema import (
    SCHEMA_VERSION,
    ConfidenceResult,
    IntelligenceReport,
    RoadmapItem,
    ScoreInputs,
    ScoreResult,
)


class IntelligenceSchemaTests(unittest.TestCase):
    def test_report_to_dict_shape(self) -> None:
        report = IntelligenceReport(
            generated_utc="2026-02-19T20:00:00Z",
            score_inputs=ScoreInputs(
                total_endpoints=10,
                tls_success=6,
                ssh_success=1,
                http_plain=2,
                unknown_open=1,
                high_impact=2,
            ),
            score_result=ScoreResult(
                score=73,
                rating="GOOD",
                drivers=(("High severity items present", 4),),
            ),
            confidence_result=ConfidenceResult(
                confidence_score=78,
                confidence_rating="MEDIUM",
                coverage_pct=70.0,
                tls_enum_coverage_pct=100.0,
                blockers_top=(("TIMEOUT", 1),),
            ),
            roadmap=(
                RoadmapItem(
                    wave="Wave 1",
                    title="Eliminate plaintext HTTP",
                    rationale="Reduce baseline risk",
                    deliverable="HTTP to HTTPS migration list",
                    owner_hint="Infra + Platform",
                    effort="M",
                ),
            ),
        )

        payload = report.to_dict()
        self.assertEqual(payload["schema_version"], SCHEMA_VERSION)
        self.assertEqual(payload["score_inputs"]["total_endpoints"], 10)
        self.assertEqual(payload["score_result"]["drivers"][0]["points"], 4)
        self.assertEqual(payload["confidence_result"]["blockers_top"][0]["category"], "TIMEOUT")
        self.assertEqual(payload["roadmap"][0]["effort"], "M")

    def test_report_to_json_is_deterministic(self) -> None:
        report = IntelligenceReport(
            generated_utc="2026-02-19T20:00:00Z",
            score_inputs=ScoreInputs(1, 1, 0, 0, 0, 0),
            score_result=ScoreResult(100, "EXCELLENT", ()),
            confidence_result=ConfidenceResult(100, "HIGH", 100.0, 100.0, ()),
            roadmap=(),
        )

        first = report.to_json()
        second = report.to_json()
        self.assertEqual(first, second)
        self.assertEqual(json.loads(first)["schema_version"], SCHEMA_VERSION)


if __name__ == "__main__":
    unittest.main()
