"""Phase 48 Plan 02 — End-to-end report writer tests.

Asserts that the new `description` field flows from finding dicts through
`write_reports` into:
  - the on-disk `findings-*.json` (no projection / whitelist drop), and
  - the rendered HTML report's All Findings table (Description column).

Also asserts that the canonical NIST IR 8547 deprecation phrase emitted by
`_build_finding` is preserved verbatim through JSON serialization.
"""
from __future__ import annotations

import glob
import json
import os
from types import SimpleNamespace
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# Fixtures / helpers (mirrors tests/test_cbom_integration.py pattern)
# ---------------------------------------------------------------------------

def _make_cfg(tmp_path):
    return SimpleNamespace(
        output=SimpleNamespace(directory=str(tmp_path)),
        assessment=SimpleNamespace(
            name="Phase 48 Test Assessment",
            report_owner="Test Owner",
            data_classification="Internal",
            timezone="UTC",
        ),
        intelligence=SimpleNamespace(
            profile="balanced",
            calibration_overrides=None,
        ),
    )


def _findings_fixture():
    return [
        {
            "severity": "HIGH",
            "host": "10.0.0.1",
            "port": 443,
            "title": "RSA certificate quantum-vulnerable",
            "description": (
                "This certificate uses RSA, vulnerable to a sufficiently "
                "large quantum computer."
            ),
            "recommendation": (
                "Plan migration to ML-KEM (FIPS 203) and ML-DSA (FIPS 204). "
                "Per NIST IR 8547, RSA and ECC are deprecated after 2030 and "
                "disallowed after 2035."
            ),
        },
        {
            "severity": "LOW",
            "host": "10.0.0.2",
            "port": 443,
            "title": "Legacy TLS cipher suites accepted",
            "description": (
                "This service accepts TLS 1.0/1.1 cipher suites that are "
                "deprecated and exploitable."
            ),
            "recommendation": (
                "Disable TLS 1.0/1.1 and restrict to TLS 1.2+ AEAD cipher suites."
            ),
        },
    ]


def _stub_evidence(endpoints, findings):
    return {
        "total_endpoints": len(endpoints),
        "tls_endpoints": len(endpoints),
        "ssh_endpoints": 0,
        "http_endpoints": 0,
        "expired_certs": 0,
        "expiring_soon_certs": 0,
        "weak_ciphers": 0,
        "vulns_by_severity": {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0},
        "findings_count": len(findings or []),
        "scan_error_rate": 0.0,
    }


def _stub_score(evidence, **kwargs):
    return {
        "score": 55,
        "subscores": {"inventory": 50, "cipher": 50, "certificate": 50, "protocol": 50},
        "drivers": [{"reason": "Test driver", "impact": -5}],
    }


def _stub_confidence(evidence):
    return {"confidence_score": 70, "factor_breakdown": {}}


def _stub_roadmap(evidence, score):
    return {
        "items": [
            {"title": "Test Action", "why": "Because testing", "timeframe": "NOW"},
        ]
    }


def _stub_waves(findings):
    return {"Wave 1": [], "Wave 2": [], "Wave 3": []}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@patch("quirk.reports.writer.categorize_waves")
@patch("quirk.reports.writer.build_phased_roadmap")
@patch("quirk.reports.writer.compute_confidence")
@patch("quirk.reports.writer.compute_readiness_score")
@patch("quirk.reports.writer.build_evidence_summary")
def test_json_export_preserves_description(
    mock_evidence, mock_score, mock_conf, mock_roadmap, mock_waves, tmp_path
):
    """findings-{stamp}.json must carry `description` for every finding."""
    mock_evidence.side_effect = _stub_evidence
    mock_score.side_effect = _stub_score
    mock_conf.side_effect = _stub_confidence
    mock_roadmap.side_effect = _stub_roadmap
    mock_waves.side_effect = _stub_waves

    from quirk.reports.writer import write_reports

    write_reports(_make_cfg(tmp_path), endpoints=[], findings=_findings_fixture())

    json_files = glob.glob(os.path.join(str(tmp_path), "findings-*.json"))
    assert json_files, "No findings JSON written"
    with open(json_files[0], "r", encoding="utf-8") as fh:
        data = json.load(fh)
    assert all("description" in f for f in data), f"description missing in {data}"
    assert all(f["description"].strip() for f in data), \
        "Empty description in JSON export"


@patch("quirk.reports.writer.categorize_waves")
@patch("quirk.reports.writer.build_phased_roadmap")
@patch("quirk.reports.writer.compute_confidence")
@patch("quirk.reports.writer.compute_readiness_score")
@patch("quirk.reports.writer.build_evidence_summary")
def test_json_export_preserves_deprecation_phrase(
    mock_evidence, mock_score, mock_conf, mock_roadmap, mock_waves, tmp_path
):
    """findings JSON preserves the literal NIST IR 8547 + FIPS 203 strings."""
    mock_evidence.side_effect = _stub_evidence
    mock_score.side_effect = _stub_score
    mock_conf.side_effect = _stub_confidence
    mock_roadmap.side_effect = _stub_roadmap
    mock_waves.side_effect = _stub_waves

    from quirk.reports.writer import write_reports

    write_reports(_make_cfg(tmp_path), endpoints=[], findings=_findings_fixture())

    json_files = glob.glob(os.path.join(str(tmp_path), "findings-*.json"))
    with open(json_files[0], "r", encoding="utf-8") as fh:
        data = json.load(fh)
    qv = next(f for f in data if "RSA" in f["title"])
    assert "Per NIST IR 8547" in qv["recommendation"]
    assert "FIPS 203" in qv["recommendation"]


@patch("quirk.reports.writer.categorize_waves")
@patch("quirk.reports.writer.build_phased_roadmap")
@patch("quirk.reports.writer.compute_confidence")
@patch("quirk.reports.writer.compute_readiness_score")
@patch("quirk.reports.writer.build_evidence_summary")
def test_html_report_has_description_column(
    mock_evidence, mock_score, mock_conf, mock_roadmap, mock_waves, tmp_path
):
    """HTML report contains <th>Description</th> in BOTH Top Findings + All Findings."""
    mock_evidence.side_effect = _stub_evidence
    mock_score.side_effect = _stub_score
    mock_conf.side_effect = _stub_confidence
    mock_roadmap.side_effect = _stub_roadmap
    mock_waves.side_effect = _stub_waves

    from quirk.reports.writer import write_reports

    write_reports(_make_cfg(tmp_path), endpoints=[], findings=_findings_fixture())

    html_files = glob.glob(os.path.join(str(tmp_path), "report-*.html"))
    assert html_files, "No HTML report written"
    with open(html_files[0], "r", encoding="utf-8") as fh:
        html = fh.read()
    assert html.count("<th>Description</th>") >= 2, (
        "Description column missing in HTML All Findings (expected >= 2 occurrences "
        "— Top Findings + All Findings)"
    )


# ---------------------------------------------------------------------------
# Phase 73 INTEL-01 / WR-14 — PDF failure advisory propagates via writer
# ---------------------------------------------------------------------------

@patch("quirk.reports.writer.render_pdf_report")
@patch("quirk.reports.writer.categorize_waves")
@patch("quirk.reports.writer.build_phased_roadmap")
@patch("quirk.reports.writer.compute_confidence")
@patch("quirk.reports.writer.compute_readiness_score")
@patch("quirk.reports.writer.build_evidence_summary")
def test_pdf_failure_advisory_propagates_via_writer(
    mock_evidence, mock_score, mock_conf, mock_roadmap, mock_waves, mock_pdf,
    tmp_path, capsys,
):
    """Phase 73 WR-14: writer consumes False from render_pdf_report and assigns pdf_path=None.

    The user-visible stderr advisory is emitted by the callee (html_renderer.py
    per RESEARCH C-3). This test asserts the writer's `pdf_ok=False` branch is
    exercised when render fails and that the advisory CAN be observed via
    the callee path in the same writer flow.
    """
    mock_evidence.side_effect = _stub_evidence
    mock_score.side_effect = _stub_score
    mock_conf.side_effect = _stub_confidence
    mock_roadmap.side_effect = _stub_roadmap
    mock_waves.side_effect = _stub_waves

    # Force PDF render to fail AND emit the callee advisory directly so this
    # test exercises the contract that writer remains stable on pdf_ok=False.
    def _fail_and_advise(html_path, pdf_path):
        import sys as _sys
        print(
            f"PDF generation failed: RuntimeError: simulated; "
            f"scan complete, HTML report at {html_path}",
            file=_sys.stderr,
        )
        return False

    mock_pdf.side_effect = _fail_and_advise

    from quirk.reports.writer import write_reports

    # Should NOT raise even though PDF rendering "failed"
    write_reports(_make_cfg(tmp_path), endpoints=[], findings=_findings_fixture())

    err = capsys.readouterr().err
    assert "PDF generation failed:" in err, (
        "Expected PDF failure advisory in stderr — writer must not swallow callee output"
    )

    # HTML report still produced even with PDF failure
    html_files = glob.glob(os.path.join(str(tmp_path), "report-*.html"))
    assert html_files, "HTML report should still exist when PDF render fails"
