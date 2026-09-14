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
# and one HIGH finding, mirroring the UAT-184.2-05 chaos-lab run.
#
# Phase 188 SCORE-06 (exclude-and-rescale) moved this fixture's real numeric
# score. This fixture only ever has TLS endpoints -- no DAR/motion protocol
# counts and no certificate_observations/KERBEROS/SAML/DNSSEC signals -- so
# identity_trust, data_at_rest, and data_in_motion are now correctly excluded
# as unassessed (domains_assessed == 3 of 6) instead of each silently
# contributing a full unearned 25/25 as they did pre-188. Derivation (not
# copied from a test run): hygiene=25, modern_tls=25, agility_signals=11
# (agility_high_impact_ratio = 2 HIGH+CRITICAL / max(findings,1)=2 -> ratio
# 1.0 -> -14 impact on a 25 cap); identity/dar/motion are None (unassessed).
# sum(25, 25, 11) = 61; 61 / (3 * 25) * 100 = 81.33... -> round() = 81.
# Pre-188 this same fixture scored 91 (sum of all six subscores including
# three fabricated full-25s, divided by the fixed 1.5) -- the drop to 81 is
# SCORE-06 working as intended, not a regression. The severity-floor
# assertions below (band capped to FAIR for an open CRITICAL) do not depend
# on the exact numeric value, only on it clearing GOOD (>= 70) before the cap
# is applied, which 81 still does.
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
    """Unconditional guard on the fixture's own preconditions.

    Asserts only that the fixture reproduces the documented defect
    conditions (a CRITICAL `TLS certificate expired` finding present, and a
    pinned real numeric score) without invoking `write_reports` at all, so
    the fixture cannot silently drift out from under the regression test
    below.

    999.115 — the pinned value moved 81 -> 34, and the SHAPE of the
    precondition moved with it. The old pin of 81 and the old
    `score >= 70` guard both encoded Phase 184.4 D-03: severity capped the
    BAND only, so the NUMBER had to stay above GOOD for the band cap to have
    something to cap. D-03 is superseded (operator-approved 2026-09-14, see
    `.planning/decisions/999.115-severity-caps-the-number-supersedes-184.4-D-03.md`)
    — `_consequence_ceiling()` now caps the number BEFORE the band is
    derived, so one open CRITICAL compresses this estate to 34, the top of
    POOR, and the band follows the number down instead of contradicting it.

    Two further changes fed the same value. `agility_high_impact_ratio` was
    removed by 999.115, so agility_signals returns to a clean 25 and the
    COMPUTED score is now 100 rather than 81 (sum(25, 25, 25) / (3*25) * 100).
    The defect condition the fixture exists to reproduce is unchanged and in
    fact sharper: an estate whose hygiene arithmetic says 100 while it carries
    an open CRITICAL. It is now asserted through `rating_cap_reason`, which
    discloses the pre-cap number, rather than through a raw `score >= 70`.
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
    # 999.115: was `== 81` under D-03 (band-only cap, agility_high_impact_ratio
    # still present). Now the consequence ceiling caps the NUMBER: 1 open
    # CRITICAL -> _top_of_band("POOR") == 34, compressed from a computed 100.
    assert score_raw["score"] == 34, (
        f"Fixture's real numeric score {score_raw['score']} no longer matches the "
        "derived post-999.115 value of 34. Derivation: hygiene=25, modern_tls=25, "
        "agility_signals=25 (agility_high_impact_ratio removed by 999.115); "
        "identity/dar/motion unassessed; sum(25,25,25) / (3*25) * 100 = 100 computed, "
        "then _consequence_ceiling(critical=1) = _top_of_band('POOR') = 34 applied by "
        "COMPRESSION (round(34 * 100 / 100)). A different value here means the "
        "fixture, the rescale formula, or the ceiling moved."
    )
    # The documented defect condition — hygiene arithmetic says the estate is
    # excellent while an open CRITICAL sits in it — is now asserted through the
    # disclosed pre-cap number, not through the post-cap one. Under D-03 the
    # post-cap number WAS the pre-cap number, so `score >= 70` could stand in
    # for this; after 999.115 those are two different values and the assertion
    # has to name the one it means.
    assert score_raw["rating_cap_reason"] == (
        "1 open CRITICAL finding — score limited to 34 (computed 100)"
    ), (
        "The fixture must still reproduce the documented defect conditions: a "
        "computed score in EXCELLENT territory carrying one open CRITICAL, with the "
        "cap disclosed. Got: "
        f"{score_raw.get('rating_cap_reason')!r} (score {score_raw['score']}). "
        "Adjust the clean endpoint count in _clean_endpoints() if the computed value "
        "has drifted below 85."
    )


# ---------------------------------------------------------------------------
# The D-13 RED-first regression.
#
# Plan 184.4-04 landed the severity floor (quirk/intelligence/scoring.py):
# compute_readiness_score() now caps the band to FAIR for any CRITICAL >= 1
# via quirk.severity_bands.cap_band_for_severity(), so this test is GREEN.
# The strict=True marker that used to fence this test has been
# deleted per D-13 / plan 184.4-04's own reason string.
# ---------------------------------------------------------------------------
def test_high_score_with_one_critical_still_produces_a_report(tmp_path):
    """D-13: a computed score >= 85 with one open CRITICAL must still produce a report.

    999.115 — the CONTRACT under test is unchanged and still the point of this
    test: `write_reports()` must not halt with `ReportCongruenceError` on this
    scan, and the executive markdown must actually land on disk. What moved is
    the MECHANISM that makes the headline congruent. Under Phase 184.4 D-02 the
    number stayed at 81 and `cap_band_for_severity()` overrode the band down to
    exactly FAIR. D-03 is superseded (operator-approved 2026-09-14), so
    `_consequence_ceiling()` now caps the NUMBER first and the band follows it
    to POOR — which is why the old `rating == "FAIR"` assertion below is now
    `== "POOR"`. Both satisfy the congruence guard; the new one satisfies it
    without the number and the label disagreeing, which is the whole reason
    D-03 was reversed.

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

    # CBOM and PDF are mocked for the same reason: this regression exists to prove
    # the SEVERITY FLOOR lets the report be produced at all, not to exercise CBOM
    # serialization or headless-Chromium rendering. Both are unrelated I/O on the
    # write_reports() path.
    #
    # The PDF mock is specifically load-bearing for suite-order independence.
    # OBSERVED (Phase 184.4 close-out): this test passed in isolation and in a
    # two-file run with test_html_report.py, but FAILED under a full `-m "not slow"`
    # suite run with:
    #     AttributeError: 'PlaywrightContextManager' object has no attribute '_playwright'
    # raised from inside `sync_playwright()` on the real `render_pdf_report()` call.
    # Some earlier test in the full suite leaves Playwright's import/driver state
    # broken for the rest of the session. Because the failure surfaces as an
    # AttributeError, it escapes `render_pdf_report()`'s ImportError-only graceful-
    # degradation guard.
    #
    # NOT YET IDENTIFIED: which test does the polluting. A two-file repro against the
    # most obvious suspect (test_html_report.py::test_pdf_graceful_degradation, which
    # poisons sys.modules["playwright"] and reloads writer) did NOT reproduce it, so
    # that hypothesis is explicitly unconfirmed — do not repeat it as fact.
    #
    # Either way this is a suite-hygiene / PDF-robustness issue, NOT a severity-floor
    # defect: the floor logic under test is unaffected. Do not remove this mock to
    # "make the test more end-to-end" without first identifying and fixing the
    # polluter, or this test will resume failing only in full-suite runs.
    with patch("quirk.reports.writer.build_cbom", return_value={}), \
         patch("quirk.reports.writer.render_pdf_report", return_value=False), \
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
        f"Real numeric score is {score_raw['score']} with one open CRITICAL "
        "finding, yet compute_readiness_score() still emits band "
        f"{score_raw['rating']!r} instead of capping below EXCELLENT."
    )
    # 999.115: was `== "FAIR"` per D-02, when the cap moved the band only and
    # FAIR was the least-destructive band the congruence guard accepts. The
    # consequence ceiling now moves the NUMBER to 34 and the band is derived
    # FROM it, so POOR is the honest label rather than an override.
    assert score_raw["rating"] == "POOR", (
        "Expected the consequence-ceiling-capped band to be exactly 'POOR' — the "
        "band derived from the capped number 34, not overridden onto an uncapped "
        f"81 as D-02 did. Got {score_raw['rating']!r} at score {score_raw['score']}."
    )
    # 999.115: was `"FAIR" in rating_cap_reason` (D-09's band-naming form). The
    # consequence cap's reason is more specific and more actionable — it names
    # the finding count that set the ceiling and discloses the pre-cap number,
    # so a capped 34 can never be read as a computed one.
    assert score_raw["rating_cap_reason"] == (
        "1 open CRITICAL finding — score limited to 34 (computed 100)"
    ), (
        "Expected a structured rating_cap_reason naming the CRITICAL count that set "
        f"the ceiling and disclosing the pre-cap number, got "
        f"{score_raw.get('rating_cap_reason')!r}."
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
