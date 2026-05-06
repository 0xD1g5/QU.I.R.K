"""Phase 14 — Scoring & Intelligence Correctness RED scaffold.

Tests assert the correct end-state for SCORE-01 through SCORE-04.
SCORE-01 and SCORE-03 may pass immediately (regression guards per D-02).
SCORE-02 and SCORE-04 must FAIL before Plan 02 fixes land.
"""
import inspect
import unittest
from unittest import mock

from quirk.intelligence.scoring import compute_readiness_score
from quirk.validate import validate_run
from quirk.assessment.migration_advisor import recommend_migration_paths


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _penalized_evidence() -> dict:
    """Evidence with significant identity and agility issues.

    Research probe confirms: strict=59, lenient=76.
    """
    return {
        "totals": {"endpoints": 10, "findings": 5},
        "cert_key_type_counts": {"RSA": 8, "ECDSA": 0},
        "certificate_observations": {
            "expired_count": 3,
            "expiring_count": 2,
            "self_signed_count": 2,
        },
        "finding_severity_counts": {
            "CRITICAL": 1,
            "HIGH": 2,
            "MEDIUM": 1,
            "LOW": 1,
            "INFO": 0,
        },
    }


# ---------------------------------------------------------------------------
# SCORE-01 — Profile multipliers actually change the score
# ---------------------------------------------------------------------------

class ScoringCorrectnessTests(unittest.TestCase):
    """SCORE-01: strict profile must score LOWER than lenient on penalised evidence.

    This is a regression guard — research probe confirms strict=59, lenient=76
    (profiles are already wired in scoring.py).  This test will PASS immediately
    and stays green permanently.
    """

    def test_strict_scores_lower_than_lenient_on_penalized_evidence(self) -> None:
        evidence = _penalized_evidence()
        strict_score = compute_readiness_score(evidence, profile="strict")
        lenient_score = compute_readiness_score(evidence, profile="lenient")
        self.assertLess(
            strict_score["score"],
            lenient_score["score"],
            "strict should score LOWER than lenient when evidence has identity/agility issues",
        )


# ---------------------------------------------------------------------------
# SCORE-02 — validate_run must NOT accept require_delta_if_baseline parameter
# ---------------------------------------------------------------------------

class ValidateCorrectnessTests(unittest.TestCase):
    """SCORE-02: validate_run's dead require_delta_if_baseline parameter must be removed.

    Both tests in this class MUST FAIL before Plan 02 removes the parameter.
    """

    def test_validate_run_no_delta_param(self) -> None:
        """require_delta_if_baseline should not appear in validate_run's signature."""
        params = inspect.signature(validate_run).parameters
        self.assertNotIn(
            "require_delta_if_baseline",
            params,
            "validate_run still has dead require_delta_if_baseline parameter — SCORE-02 not fixed",
        )

    def test_validate_main_no_delta_arg(self) -> None:
        """main() should not expose --no-require-delta argparse argument."""
        from quirk.validate import main
        source = inspect.getsource(main)
        self.assertNotIn(
            "no-require-delta",
            source,
            "validate.main still registers --no-require-delta argument — SCORE-02 not fixed",
        )
        self.assertNotIn(
            "no_require_delta",
            source,
            "validate.main still references no_require_delta — SCORE-02 not fixed",
        )


# ---------------------------------------------------------------------------
# SCORE-03 — migration_advisor pattern matching
# ---------------------------------------------------------------------------

class MigrationAdvisorTests(unittest.TestCase):
    """SCORE-03: recommend_migration_paths produces correct recommendations.

    Research confirms matching is already correct after Phase 08 fix.
    These tests are regression guards — they pass immediately.
    """

    def test_legacy_tls_finding_produces_migration_rec(self) -> None:
        findings = [
            {
                "title": "Legacy TLS versions allowed (TLS 1.0/1.1)",
                "severity": "LOW",
                "host": "10.0.0.1",
                "port": 443,
                "recommendation": "Disable TLS 1.0/1.1",
            }
        ]
        recs = recommend_migration_paths(findings)
        self.assertEqual(len(recs), 1)
        self.assertIn(
            recs[0]["path"],
            ("Hygiene → Modernization", "Hygiene", "Modernization"),
            "Expected a Hygiene or Modernization migration path for legacy TLS finding",
        )

    def test_plaintext_http_finding_produces_migration_rec(self) -> None:
        findings = [
            {
                "title": "Plaintext HTTP service detected",
                "severity": "HIGH",
                "host": "10.0.0.1",
                "port": 80,
                "recommendation": "Enable TLS",
            }
        ]
        recs = recommend_migration_paths(findings)
        self.assertEqual(len(recs), 1)

    def test_info_findings_filtered_out(self) -> None:
        """INFO-severity findings must be excluded from migration recs."""
        findings = [
            {
                "title": "SSH quantum planning advisory",
                "severity": "INFO",
                "host": "10.0.0.1",
                "port": 22,
                "recommendation": "Plan",
            }
        ]
        recs = recommend_migration_paths(findings)
        self.assertEqual(
            len(recs),
            0,
            "INFO findings should be filtered out by migration_advisor",
        )


# ---------------------------------------------------------------------------
# SCORE-04 — dashboard route must pass profile kwarg to compute_readiness_score
# ---------------------------------------------------------------------------

class DashboardProfileTests(unittest.TestCase):
    """SCORE-04: dashboard get_latest_scan must pass profile= kwarg.

    Both tests in this class MUST FAIL before Plan 02 wires the profile kwarg.
    Per Research Pitfall 2, the correct field is calibration.profile, NOT
    assessment.profile.
    """

    def _get_scan_source(self) -> str:
        from quirk.dashboard.api.routes.scan import get_latest_scan
        return inspect.getsource(get_latest_scan)

    def test_dashboard_score_call_uses_profile_kwarg(self) -> None:
        """compute_readiness_score call in get_latest_scan must include profile=."""
        source = self._get_scan_source()
        self.assertIn(
            "profile=",
            source,
            "get_latest_scan does not pass profile= to compute_readiness_score — SCORE-04 not fixed",
        )

    def test_dashboard_reads_calibration_profile_not_assessment(self) -> None:
        """get_latest_scan must read profile from calibration, not assessment."""
        source = self._get_scan_source()
        self.assertIn(
            "calibration",
            source,
            "get_latest_scan does not reference calibration field — SCORE-04 not fixed",
        )


if __name__ == "__main__":
    unittest.main()
