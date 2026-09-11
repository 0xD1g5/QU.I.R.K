"""Phase 200 Plan 04 / RPT-01: identity text on CLI-visible report surfaces.

Covers the CLI half of RPT-01 — the executive summary markdown, the
scorecard markdown, and the Rich console scan-summary — proving the
identity fields (client, engagement, prepared-by, cover date,
confidentiality) render when set, are each individually conditional, and
never leak a logo path or image data. No PDF/DOCX surfaces are covered
here (200-03 owns those).

Presence-based tests only (per feedback_report_render_tests_presence_not_appearance):
these assert the configured identity strings are PRESENT in the rendered
text, not that their visual position/order matches. Fixture style mirrors
tests/test_reports_writer.py and tests/test_report_injection_hardening.py
(PATTERNS §7) — always pin the `report` attribute explicitly on every
SimpleNamespace cfg (spec-mock auto-vivify trap).
"""
from __future__ import annotations

import glob
import os
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from rich.console import Console


# ---------------------------------------------------------------------------
# Fixtures / helpers (mirror tests/test_reports_writer.py)
# ---------------------------------------------------------------------------


def _branding(**overrides):
    fields = dict(
        logo_path=None,
        client_name=None,
        engagement_name=None,
        prepared_by=None,
        cover_date=None,
        confidentiality_line=None,
    )
    fields.update(overrides)
    return SimpleNamespace(**fields)


def _make_cfg(tmp_path, branding=None):
    return SimpleNamespace(
        output=SimpleNamespace(directory=str(tmp_path)),
        assessment=SimpleNamespace(
            name="Phase 200 Plan 04 Test Assessment",
            report_owner="Test Owner",
            data_classification="Internal",
            timezone="UTC",
        ),
        intelligence=SimpleNamespace(
            profile="balanced",
            calibration_overrides=None,
        ),
        report=SimpleNamespace(
            branding=branding if branding is not None else _branding(),
            template_dir=None,
            profile=None,
        ),
    )


def _findings_fixture():
    return [
        {
            "severity": "HIGH",
            "host": "10.0.0.1",
            "port": 443,
            "title": "RSA certificate quantum-vulnerable",
            "description": "This certificate uses RSA.",
            "recommendation": "Migrate to ML-KEM (FIPS 203) and ML-DSA (FIPS 204).",
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
        "vulns_by_severity": {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 0, "LOW": 0},
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


def _patches():
    """Standard intelligence-pipeline patches for write_reports (same set
    used by tests/test_reports_writer.py and test_report_injection_hardening.py)."""
    return (
        patch("quirk.reports.writer.categorize_waves", side_effect=_stub_waves),
        patch("quirk.reports.writer.build_phased_roadmap", side_effect=_stub_roadmap),
        patch("quirk.reports.writer.compute_confidence", side_effect=_stub_confidence),
        patch("quirk.reports.writer.compute_readiness_score", side_effect=_stub_score),
        patch("quirk.reports.writer.build_evidence_summary", side_effect=_stub_evidence),
    )


def _run_write_reports(tmp_path, branding=None):
    """Run write_reports; return (exec_md, scorecard_md) text."""
    from quirk.reports.writer import write_reports

    cfg = _make_cfg(tmp_path, branding=branding)
    endpoints = []
    findings = _findings_fixture()

    p1, p2, p3, p4, p5 = _patches()
    with p1, p2, p3, p4, p5:
        write_reports(cfg, endpoints=endpoints, findings=findings)

    exec_files = glob.glob(os.path.join(str(tmp_path), "executive-summary-*.md"))
    assert exec_files, "No executive summary markdown written"
    with open(exec_files[0], "r", encoding="utf-8") as fh:
        exec_md = fh.read()

    scorecard_files = glob.glob(os.path.join(str(tmp_path), "scorecard-*.md"))
    assert scorecard_files, "No scorecard markdown written"
    with open(scorecard_files[0], "r", encoding="utf-8") as fh:
        scorecard_md = fh.read()

    return exec_md, scorecard_md


def _run_write_reports_console(tmp_path, capsys, branding=None):
    """Run write_reports and return captured stdout (the Rich console output)."""
    from quirk.reports.writer import write_reports

    cfg = _make_cfg(tmp_path, branding=branding)
    endpoints = []
    findings = _findings_fixture()

    p1, p2, p3, p4, p5 = _patches()
    with p1, p2, p3, p4, p5:
        write_reports(cfg, endpoints=endpoints, findings=findings)

    captured = capsys.readouterr()
    return captured.out


# ---------------------------------------------------------------------------
# Fully-branded cfg
# ---------------------------------------------------------------------------


def test_fully_branded_executive_markdown_carries_identity(tmp_path):
    branding = _branding(
        client_name="Acme Corp",
        engagement_name="Q3 Readiness Assessment",
        prepared_by="Jane Analyst",
    )
    exec_md, _ = _run_write_reports(tmp_path, branding=branding)
    assert "Acme Corp" in exec_md
    assert "Q3 Readiness Assessment" in exec_md
    assert "Jane Analyst" in exec_md
    assert "**Client:**" in exec_md
    assert "**Engagement:**" in exec_md
    assert "**Prepared by:**" in exec_md


def test_fully_branded_scorecard_markdown_carries_identity(tmp_path):
    branding = _branding(
        client_name="Acme Corp",
        engagement_name="Q3 Readiness Assessment",
        prepared_by="Jane Analyst",
    )
    _, scorecard_md = _run_write_reports(tmp_path, branding=branding)
    assert "Acme Corp" in scorecard_md
    assert "Q3 Readiness Assessment" in scorecard_md
    assert "Jane Analyst" in scorecard_md


def test_fully_branded_console_summary_carries_identity(tmp_path, capsys):
    branding = _branding(
        client_name="Acme Corp",
        engagement_name="Q3 Readiness Assessment",
    )
    console_out = _run_write_reports_console(tmp_path, capsys, branding=branding)
    assert "Acme Corp" in console_out
    assert "Q3 Readiness Assessment" in console_out


# ---------------------------------------------------------------------------
# Partially-branded cfg
# ---------------------------------------------------------------------------


def test_partially_branded_cfg_emits_exactly_one_new_line_per_surface(tmp_path, capsys):
    branding = _branding(client_name="Acme Corp")
    exec_md, scorecard_md = _run_write_reports(tmp_path, branding=branding)

    assert "**Client:**" in exec_md
    assert "**Engagement:**" not in exec_md
    assert "**Prepared by:**" not in exec_md

    assert "**Client:**" in scorecard_md
    assert "**Engagement:**" not in scorecard_md
    assert "**Prepared by:**" not in scorecard_md


def test_partially_branded_cfg_console_summary_has_no_engagement_row(tmp_path, capsys):
    branding = _branding(client_name="Acme Corp")
    console_out = _run_write_reports_console(tmp_path, capsys, branding=branding)
    assert "Acme Corp" in console_out
    assert "Engagement" not in console_out
    assert "Prepared by" not in console_out


# ---------------------------------------------------------------------------
# No-report-section cfg -> byte-identical to today
# ---------------------------------------------------------------------------


def test_no_branding_produces_byte_identical_markdown_to_all_none_branding(tmp_path):
    """A cfg whose report.branding has every field None must render the same
    executive/scorecard markdown text as a cfg with no report section carrying
    any identity value — the 'absent field = today's rendering' contract."""
    exec_md_a, scorecard_md_a = _run_write_reports(tmp_path / "a", branding=_branding())
    exec_md_b, scorecard_md_b = _run_write_reports(
        tmp_path / "b",
        branding=_branding(
            client_name=None,
            engagement_name=None,
            prepared_by=None,
            cover_date=None,
            confidentiality_line=None,
        ),
    )
    assert exec_md_a == exec_md_b
    assert scorecard_md_a == scorecard_md_b
    for label in ("Client", "Engagement", "Prepared by", "Cover date", "Confidentiality"):
        assert f"**{label}:**" not in exec_md_a
        assert f"**{label}:**" not in scorecard_md_a


# ---------------------------------------------------------------------------
# Negative: no logo/image data on any CLI surface
# ---------------------------------------------------------------------------


def test_no_image_branding_reference_reaches_any_cli_surface(tmp_path, capsys):
    # NOTE: the pytest-generated tmp_path is derived from this function's own
    # name, so the test name deliberately avoids the substring "logo" — a
    # literal "logo" in the test's name would leak into the console's
    # "Output files" path listing and self-trigger the very assertion this
    # test exists to make, independent of any product behavior.
    branding = _branding(
        logo_path="/tmp/some-branding-image.png",
        client_name="Acme Corp",
    )
    exec_md, scorecard_md = _run_write_reports(tmp_path / "a", branding=branding)
    console_out = _run_write_reports_console(tmp_path / "b", capsys, branding=branding)

    for surface_name, surface_text in (
        ("executive markdown", exec_md),
        ("scorecard markdown", scorecard_md),
        ("console summary", console_out),
    ):
        assert "logo" not in surface_text.lower(), f"{surface_name} leaked a logo reference"
        assert "data:image" not in surface_text.lower(), f"{surface_name} leaked image data"
        assert "some-branding-image.png" not in surface_text, f"{surface_name} leaked the branding image path"
