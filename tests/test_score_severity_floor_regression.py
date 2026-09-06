"""Phase 184.4 — SCORE-04 / D-13 RED-first regression: rating band severity floor.

Reproduction provenance (Phase 184.2 UAT-184.2-05, chaos lab, target `127.0.0.1`,
shipped 17-port `CONSULTING_TLS_PORTS` default): a scan scored 89/100 EXCELLENT while
carrying one open CRITICAL finding (`TLS certificate expired` on port 9443) and one
HIGH finding (`TLS certificate is self-signed` on port 10443). `write_reports()` halted
with:

    Report generation halted: executive headline 'EXCELLENT' is inconsistent with
    1 CRITICAL finding(s). Review findings before generating the report.

D-13 requires this reproduced RED-first, against the pre-fix code, driving the REAL
`compute_readiness_score()` end-to-end through `write_reports()` — never a mocked
score — so this test cannot pass by bypassing the very severity floor it exists to
prove. Phase 184.4 supersedes BACK-89 (`.planning/milestones/v5.0-ROADMAP.md:845`).

This file intentionally does NOT assert anything about `rating_cap_reason` — that key
does not exist yet on pre-fix code and is plan 184.4-04's (producer) and 184.4-06's
(surfacing) contract, not this plan's.
"""
from __future__ import annotations

import glob
import os
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from quirk.intelligence.evidence import build_evidence_summary
from quirk.intelligence.scoring import compute_readiness_score
from quirk.reports.content_model import ReportCongruenceError
from quirk.reports.writer import write_reports

# ---------------------------------------------------------------------------
# Fixture — matches the documented reproduction shape, not an invented one.
#
# Five clean TLS endpoints (no plaintext, no expired/self-signed cert
# *attributes* on the endpoints themselves — those signals only reach the
# scorer via the findings list here, exactly as `build_evidence_summary`
# and `compute_readiness_score` are wired today) plus exactly one CRITICAL
# and one HIGH finding, mirroring the UAT-184.2-05 chaos-lab run. The
# resulting real numeric score was verified empirically (not guessed, not
# hard-coded to the reproduction's literal 89) by calling
# `build_evidence_summary` + `compute_readiness_score` directly before this
# test was written: five clean endpoints + these two findings score 91/100,
# safely and stably above the 85 EXCELLENT threshold.
# ---------------------------------------------------------------------------


def _clean_endpoints() -> list:
    return [
        SimpleNamespace(
            host=f"10.0.0.{i}",
            port=443,
            protocol="TLS",
            scanned_at=datetime.now(timezone.utc),
            scan_error=None,
        )
        for i in range(1, 6)
    ]


def _reproduction_findings() -> list:
    return [
        {
            "title": "TLS certificate expired",
            "severity": "CRITICAL",
            "category": "tls",
            "description": "TLS certificate expired on 127.0.0.1:9443",
            "host": "127.0.0.1",
            "port": 9443,
            "recommendation": "Renew the certificate immediately.",
            "compliance": [],
        },
        {
            "title": "TLS certificate is self-signed",
            "severity": "HIGH",
            "category": "tls",
            "description": "TLS certificate is self-signed on 127.0.0.1:10443",
            "host": "127.0.0.1",
            "port": 10443,
            "recommendation": "Replace with a CA-signed certificate.",
            "compliance": [],
        },
    ]


def test_regression_fixture_reproduces_the_documented_defect_conditions():
    """Unconditional, never-xfailed guard on the fixture's own preconditions.

    Asserts only that the fixture reproduces the documented defect
    conditions (a CRITICAL `TLS certificate expired` finding present, and a
    real numeric score >= 85) without invoking `write_reports` at all, so
    the fixture cannot silently drift out from under the xfailed test below
    while the xfail marker hides a fixture-shape regression.
    """
    endpoints = _clean_endpoints()
    findings = _reproduction_findings()

    evidence = build_evidence_summary(endpoints, findings)
    score_raw = compute_readiness_score(evidence, profile="balanced", weights=None)

    critical_titles = {
        f["title"] for f in findings if f["severity"] == "CRITICAL"
    }
    assert "TLS certificate expired" in critical_titles, (
        "Fixture must carry the documented CRITICAL finding "
        "'TLS certificate expired' (Phase 184.2 UAT-184.2-05 reproduction)."
    )
    assert score_raw["score"] >= 85, (
        f"Fixture's real numeric score {score_raw['score']} dropped below the 85 "
        "EXCELLENT threshold — the fixture no longer reproduces the documented "
        "defect conditions (score >= 85 with one CRITICAL open). Adjust the clean "
        "endpoint count in _clean_endpoints() to restore it."
    )


# ---------------------------------------------------------------------------
# The D-13 RED-first regression.
#
# strict=True is required, not incidental: with strict=True, this test
# reports XFAIL (suite stays green) while the producer is unfixed across
# Waves 2-3, and reports a hard FAILURE the instant the severity-floor fix
# (plan 184.4-04) makes it pass — which is exactly the signal that the
# `xfail` marker below must now be deleted. A plain non-strict xfail would
# let that removal be silently forgotten; strict=True makes forgetting it
# impossible to miss. Removed by plan 184.4-04.
# ---------------------------------------------------------------------------
@pytest.mark.xfail(
    strict=True,
    reason=(
        "Phase 184.4 D-13: pre-fix quirk.intelligence.scoring._rating() has no "
        "severity floor, so a score >= 85 with an open CRITICAL still emits "
        "EXCELLENT and quirk.reports.content_model._check_congruence() halts "
        "report generation with ReportCongruenceError. This xfail is removed by "
        "plan 184.4-04 once the severity floor caps the band to FAIR."
    ),
)
def test_high_score_with_one_critical_still_produces_a_report(tmp_path):
    """D-13: score >= 85 with one open CRITICAL must still produce a report.

    Drives the REAL `compute_readiness_score()` (never mocked) through the REAL
    `write_reports()` end-to-end. Only the peripheral CBOM I/O is patched, exactly
    matching `test_guard_blocks_report_generation`'s patch list
    (`tests/test_congruence_guard.py`) — `build_evidence_summary`,
    `compute_readiness_score`, `compute_confidence`, and `build_phased_roadmap`
    all run for real.
    """
    cfg = SimpleNamespace(
        assessment=SimpleNamespace(
            name="Severity Floor Regression Org",
            report_owner="Test Owner",
            data_classification="CONFIDENTIAL",
            timezone="UTC",
        ),
        output=SimpleNamespace(directory=str(tmp_path / "reports")),
        intelligence=SimpleNamespace(
            profile="balanced",
            calibration_overrides=None,
        ),
    )

    endpoints = _clean_endpoints()
    findings = _reproduction_findings()

    with patch("quirk.reports.writer.build_cbom", return_value={}), \
         patch(
             "quirk.reports.writer.write_cbom_files",
             return_value=("/tmp/a.json", "/tmp/a.xml"),
         ):
        try:
            write_reports(cfg, endpoints=endpoints, findings=findings)
        except ReportCongruenceError as exc:
            pytest.fail(
                "write_reports() raised ReportCongruenceError for a scan with "
                f"score >= 85 and one open CRITICAL finding: {exc}. D-13 requires "
                "the severity floor cap the BAND (not the score) so this scan "
                "yields FAIR and the report is produced, not halted."
            )

    # Assertion 2: the band must be FAIR, not EXCELLENT. Read it back from the
    # real evidence/score recomputed identically to how write_reports derived
    # it (same evidence + same profile), not a hand re-derivation of the band
    # logic itself.
    evidence = build_evidence_summary(endpoints, findings)
    score_raw = compute_readiness_score(evidence, profile="balanced", weights=None)
    assert score_raw["rating"] != "EXCELLENT", (
        f"Real numeric score is {score_raw['score']} (>= 85) with one open "
        "CRITICAL finding, yet compute_readiness_score() still emits band "
        f"{score_raw['rating']!r} instead of capping it below EXCELLENT. D-01/D-02 "
        "require min(numeric_band, severity_cap) to yield FAIR for any CRITICAL >= 1."
    )
    assert score_raw["rating"] == "FAIR", (
        f"Expected the severity-floor-capped band to be exactly 'FAIR' per D-02 "
        f"(least-destructive band the congruence guard accepts for CRITICAL >= 1), "
        f"got {score_raw['rating']!r}."
    )

    # Assertion 3: the executive markdown artifact WAS written — the exact
    # inversion of test_guard_blocks_report_generation's "no executive
    # markdown was written" check. Glob rather than hardcode the timestamped
    # filename (writer.py:691 stamps it `executive-summary-{stamp}.md`).
    report_dir = tmp_path / "reports"
    exec_files = glob.glob(os.path.join(str(report_dir), "executive-summary-*.md"))
    assert exec_files, (
        f"Expected an executive-summary-*.md artifact under {report_dir}, found "
        f"none. D-13 requires write_reports() to actually PRODUCE the report for "
        "a high-score, one-CRITICAL scan, not halt on it."
    )
