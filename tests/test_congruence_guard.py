"""Phase 98 D-06 / TRANS-03 — _check_congruence unit tests.

Covers all band/severity cases for the congruence guard that prevents a
contradictory exec headline from being emitted (e.g., "GOOD" over 7 CRITICAL).

Test node IDs from 98-VALIDATION.md:
  - test_good_band_with_critical_raises
  - test_fair_band_with_critical_ok
"""
from __future__ import annotations

import pytest

from quirk.reports.content_model import (
    ReportCongruenceError,
    _check_congruence,
    assert_congruent,
    build_exec_content,
)

# ---------------------------------------------------------------------------
# Tests — exact VALIDATION.md node IDs
# ---------------------------------------------------------------------------


def test_good_band_with_critical_raises():
    """TRANS-03 / D-06: GOOD band with CRITICAL findings raises ReportCongruenceError.

    The congruence guard must make it structurally impossible to emit a "GOOD"
    headline while CRITICAL findings are open.
    Node ID: test_congruence_guard.py::test_good_band_with_critical_raises
    """
    with pytest.raises(ReportCongruenceError) as exc_info:
        _check_congruence("GOOD", {"CRITICAL": 3, "HIGH": 2})

    msg = str(exc_info.value)
    assert "GOOD" in msg, (
        "ReportCongruenceError message must include the band name 'GOOD'. "
        "TRANS-03 / UI-SPEC Copywriting Contract."
    )
    assert "3" in msg, (
        "ReportCongruenceError message must include the CRITICAL count '3'. "
        "TRANS-03 / UI-SPEC Copywriting Contract."
    )
    assert "CRITICAL" in msg, (
        "ReportCongruenceError message must include 'CRITICAL'. "
        "TRANS-03 / UI-SPEC Copywriting Contract."
    )


def test_excellent_band_with_critical_raises():
    """TRANS-03 / D-06: EXCELLENT band with any CRITICAL finding raises.

    EXCELLENT is a stricter band than GOOD; same restriction applies.
    """
    with pytest.raises(ReportCongruenceError) as exc_info:
        _check_congruence("EXCELLENT", {"CRITICAL": 1})

    msg = str(exc_info.value)
    assert "EXCELLENT" in msg, (
        "ReportCongruenceError message must include the band name 'EXCELLENT'. "
        "TRANS-03 / UI-SPEC Copywriting Contract."
    )
    assert "1" in msg, (
        "ReportCongruenceError message must include the CRITICAL count '1'. TRANS-03."
    )


def test_moderate_band_with_critical_raises():
    """TRANS-03 / D-06: MODERATE band with any CRITICAL finding raises.

    Per RESEARCH Pattern 2 / D-06 resolution: MODERATE is blocked by any CRITICAL.
    """
    with pytest.raises(ReportCongruenceError):
        _check_congruence("MODERATE", {"CRITICAL": 1})


def test_fair_band_with_critical_ok():
    """TRANS-03 / D-06: FAIR band with CRITICAL findings does NOT raise.

    FAIR band implies significant exposure — CRITICAL findings are consistent with it.
    Node ID: test_congruence_guard.py::test_fair_band_with_critical_ok
    """
    # Must not raise — no exception expected
    _check_congruence("FAIR", {"CRITICAL": 5, "HIGH": 10})


def test_poor_band_with_critical_ok():
    """TRANS-03 / D-06: POOR band with many CRITICAL findings does NOT raise.

    POOR band implies immediate remediation — CRITICAL findings are fully compatible.
    """
    _check_congruence("POOR", {"CRITICAL": 9, "HIGH": 5, "MEDIUM": 3})


def test_good_band_zero_critical_ok():
    """TRANS-03 / D-06: GOOD band with zero CRITICAL findings does NOT raise."""
    _check_congruence("GOOD", {"HIGH": 5, "MEDIUM": 3, "LOW": 10})


def test_congruence_error_message_matches_ui_spec():
    """TRANS-03: ReportCongruenceError message matches UI-SPEC Copywriting Contract.

    Expected format:
      "Report generation halted: executive headline '{band}' is inconsistent
       with {n} CRITICAL finding(s). Review findings before generating the report."
    """
    n = 7
    band = "GOOD"
    with pytest.raises(ReportCongruenceError) as exc_info:
        _check_congruence(band, {"CRITICAL": n})

    msg = str(exc_info.value)
    # Check all required phrases from the UI-SPEC Copywriting Contract
    assert "Report generation halted" in msg, (
        f"Message missing 'Report generation halted'. Got: {msg!r}. "
        "TRANS-03 / UI-SPEC Copywriting Contract."
    )
    assert f"'{band}'" in msg, (
        f"Message missing band name in quotes ('{band}'). Got: {msg!r}. "
        "TRANS-03 / UI-SPEC Copywriting Contract."
    )
    assert str(n) in msg, (
        f"Message missing count '{n}'. Got: {msg!r}. "
        "TRANS-03 / UI-SPEC Copywriting Contract."
    )
    assert "CRITICAL finding" in msg, (
        f"Message missing 'CRITICAL finding'. Got: {msg!r}. "
        "TRANS-03 / UI-SPEC Copywriting Contract."
    )
    assert "Review findings" in msg, (
        f"Message missing 'Review findings'. Got: {msg!r}. "
        "TRANS-03 / UI-SPEC Copywriting Contract."
    )


def test_congruence_guard_is_exception_subclass():
    """D-06: ReportCongruenceError is a subclass of ValueError (pattern from quirk/errors.py)."""
    assert issubclass(ReportCongruenceError, ValueError), (
        "ReportCongruenceError must subclass ValueError to match the custom exception pattern. "
        "D-06 / quirk/errors.py pattern."
    )


def test_build_exec_content_calls_guard_internally():
    """TRANS-03 / D-06: build_exec_content raises ReportCongruenceError when guard fires.

    The guard must be called before returning ExecContent — no I/O can occur first.
    """
    score_raw = {
        "score": 80,
        "rating": "GOOD",  # GOOD with CRITICAL -> guard fires
        "subscores": {
            "hygiene": 20, "modern_tls": 18, "identity_trust": 25,
            "agility_signals": 15, "data_at_rest": 22, "data_in_motion": 21,
        },
        "drivers": [],
    }
    findings = [
        {"title": "RSA cert", "severity": "CRITICAL", "category": "RSA"},
    ]

    with pytest.raises(ReportCongruenceError) as exc_info:
        build_exec_content(
            score_raw=score_raw,
            findings=findings,
            roadmap_items=[],
        )

    msg = str(exc_info.value)
    assert "GOOD" in msg, (
        "build_exec_content must propagate ReportCongruenceError from _check_congruence. "
        "TRANS-03 / D-06."
    )


def test_guard_blocks_report_generation(tmp_path):
    """TRANS-03 / D-06 integration: write_reports raises ReportCongruenceError before any file I/O.

    When the congruence guard fires (GOOD band + CRITICAL findings), write_reports must
    raise ReportCongruenceError and write no executive report file to disk.
    The findings JSON is the only file written before the guard fires (step 1 in writer.py).
    Node ID: test_congruence_guard.py::test_guard_blocks_report_generation
    """
    from types import SimpleNamespace
    from unittest.mock import patch, MagicMock

    from quirk.reports.writer import write_reports
    from quirk.reports.content_model import ReportCongruenceError

    # Minimal cfg that matches writer.py expectations
    cfg = SimpleNamespace(
        assessment=SimpleNamespace(
            name="Integration Test Org",
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

    # A finding that will produce GOOD band + CRITICAL → guard fires
    # We mock compute_readiness_score to return GOOD band deterministically
    mock_score_raw = {
        "score": 75,
        "rating": "GOOD",
        "subscores": {
            "hygiene": 20, "modern_tls": 18, "identity_trust": 25,
            "agility_signals": 15, "data_at_rest": 22, "data_in_motion": 21,
        },
        "drivers": [],
    }
    mock_roadmap_raw = {"items": []}
    mock_evidence = {}
    mock_conf_raw = {
        "confidence_score": 70,
        "confidence_rating": "HIGH",
        "factor_breakdown": {},
    }

    findings = [
        {
            "title": "Weak RSA Certificate",
            "severity": "CRITICAL",
            "category": "RSA",
            "description": "RSA-2048 certificate detected",
            "host": "example.com",
        }
    ]

    with patch("quirk.reports.writer.build_evidence_summary", return_value=mock_evidence), \
         patch("quirk.reports.writer.compute_readiness_score", return_value=mock_score_raw), \
         patch("quirk.reports.writer.compute_confidence", return_value=mock_conf_raw), \
         patch("quirk.reports.writer.build_phased_roadmap", return_value=mock_roadmap_raw), \
         patch("quirk.reports.writer.build_cbom", return_value={}), \
         patch("quirk.reports.writer.write_cbom_files", return_value=("/tmp/a.json", "/tmp/a.xml")):

        with pytest.raises(ReportCongruenceError) as exc_info:
            write_reports(cfg, endpoints=[], findings=findings)

    msg = str(exc_info.value)
    assert "GOOD" in msg, (
        "ReportCongruenceError from write_reports must include the band 'GOOD'. "
        "TRANS-03 / D-06 integration gate."
    )
    assert "CRITICAL" in msg, (
        "ReportCongruenceError from write_reports must reference CRITICAL findings. "
        "TRANS-03 / D-06 integration gate."
    )

    # Verify no executive markdown was written (guard fired before exec report I/O)
    import os
    report_dir = tmp_path / "reports"
    if report_dir.exists():
        exec_files = [f for f in os.listdir(report_dir) if f.startswith("executive-summary-")]
        assert exec_files == [], (
            f"write_reports wrote an executive-summary file despite guard firing: {exec_files}. "
            "D-06 requires ReportCongruenceError before any exec report is written."
        )


# ---------------------------------------------------------------------------
# WR-05 — public assert_congruent() guard + renderer backward-compat paths
# ---------------------------------------------------------------------------

import pytest as _pytest


@_pytest.mark.parametrize("band", ["EXCELLENT", "GOOD", "MODERATE"])
def test_assert_congruent_raises_for_healthy_band_with_critical(band):
    """assert_congruent must fail-closed when a healthy band coexists with CRITICAL."""
    with _pytest.raises(ReportCongruenceError):
        assert_congruent(band, [{"severity": "CRITICAL", "title": "x"}])


@_pytest.mark.parametrize("band", ["FAIR", "POOR"])
def test_assert_congruent_allows_low_band_with_critical(band):
    """FAIR / POOR carry no CRITICAL restriction — assert_congruent must not raise."""
    assert_congruent(band, [{"severity": "CRITICAL", "title": "x"}])


def test_assert_congruent_allows_healthy_band_without_critical():
    assert_congruent("EXCELLENT", [{"severity": "INFO", "title": "y"}])


def test_markdown_compat_path_is_fail_closed():
    """WR-05: build_exec_markdown with exec_content=None must still run the D-06 guard.

    The compat path computes its own score_raw; we force an EXCELLENT band over a
    CRITICAL finding via calibration so the guard must fire on the legacy path too.
    """
    from types import SimpleNamespace
    from datetime import datetime, timezone
    from quirk.reports.executive import build_exec_markdown

    cfg = SimpleNamespace(
        assessment=SimpleNamespace(name="t", report_owner="o", data_classification="c", timezone="UTC"),
        intelligence=SimpleNamespace(profile="balanced", calibration_overrides={}),
    )
    eps = [SimpleNamespace(host=f"10.0.0.{i}", port=443, protocol="TLS",
                           scanned_at=datetime.now(timezone.utc), scan_error=None) for i in range(1, 5)]
    crit = {"severity": "CRITICAL", "host": "10.0.0.9", "port": 443,
            "title": "Quantum-vulnerable key exchange", "category": "tls",
            "description": "d", "recommendation": "r", "compliance": []}
    with _pytest.raises(ReportCongruenceError):
        build_exec_markdown(cfg, eps, [crit], exec_content=None)
