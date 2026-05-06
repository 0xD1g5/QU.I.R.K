"""Integration tests for write_reports() CBOM step.

Tests verify that calling write_reports() produces CBOM files alongside
the existing reports when the pipeline is integrated.
"""
from __future__ import annotations

import glob
import json
import os
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from quirk.models import CryptoEndpoint


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _tls_endpoint(**overrides):
    """Create a TLS CryptoEndpoint with sensible defaults."""
    defaults = dict(
        host="example.com", port=443, protocol=None,
        tls_version="TLSv1.2",
        cipher_suite="TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384",
        cert_pubkey_alg="RSA", cert_pubkey_size=2048,
        cert_sig_alg="sha256WithRSAEncryption",
        cert_subject="CN=example.com", cert_issuer="CN=Example CA",
        cert_not_before=None, cert_not_after=None,
        tls_capabilities_json=None, ssh_audit_json=None,
    )
    defaults.update(overrides)
    return CryptoEndpoint(**defaults)


def _make_cfg(tmp_path):
    return SimpleNamespace(
        output=SimpleNamespace(directory=str(tmp_path)),
        assessment=SimpleNamespace(
            name="Test Assessment",
            report_owner="Test Owner",
            data_classification="Internal",
            timezone="UTC",
        ),
        intelligence=SimpleNamespace(
            profile="balanced",
            calibration_overrides=None,
        ),
    )


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
    return {
        "confidence_score": 70,
        "factor_breakdown": {},
    }


def _stub_roadmap(evidence, score):
    return {
        "items": [
            {"title": "Test Action", "why": "Because testing", "timeframe": "NOW"},
        ]
    }


def _stub_waves(findings):
    return {"Wave 1": [], "Wave 2": [], "Wave 3": []}


# ---------------------------------------------------------------------------
# Test: write_reports() creates CBOM files
# ---------------------------------------------------------------------------

@patch("quirk.reports.writer.categorize_waves")
@patch("quirk.reports.writer.build_phased_roadmap")
@patch("quirk.reports.writer.compute_confidence")
@patch("quirk.reports.writer.compute_readiness_score")
@patch("quirk.reports.writer.build_evidence_summary")
def test_write_reports_creates_cbom_files(
    mock_evidence, mock_score, mock_conf, mock_roadmap, mock_waves, tmp_path
):
    mock_evidence.side_effect = _stub_evidence
    mock_score.side_effect = _stub_score
    mock_conf.side_effect = _stub_confidence
    mock_roadmap.side_effect = _stub_roadmap
    mock_waves.side_effect = _stub_waves

    from quirk.reports.writer import write_reports

    cfg = _make_cfg(tmp_path)
    endpoints = [_tls_endpoint()]
    findings = []

    write_reports(cfg, endpoints, findings)

    json_files = glob.glob(os.path.join(str(tmp_path), "cbom-*.cdx.json"))
    xml_files = glob.glob(os.path.join(str(tmp_path), "cbom-*.cdx.xml"))

    assert len(json_files) == 1, f"Expected 1 CBOM JSON file, found: {json_files}"
    assert len(xml_files) == 1, f"Expected 1 CBOM XML file, found: {xml_files}"


@patch("quirk.reports.writer.categorize_waves")
@patch("quirk.reports.writer.build_phased_roadmap")
@patch("quirk.reports.writer.compute_confidence")
@patch("quirk.reports.writer.compute_readiness_score")
@patch("quirk.reports.writer.build_evidence_summary")
def test_write_reports_cbom_paths_in_console(
    mock_evidence, mock_score, mock_conf, mock_roadmap, mock_waves, tmp_path, capsys
):
    mock_evidence.side_effect = _stub_evidence
    mock_score.side_effect = _stub_score
    mock_conf.side_effect = _stub_confidence
    mock_roadmap.side_effect = _stub_roadmap
    mock_waves.side_effect = _stub_waves

    from quirk.reports.writer import write_reports

    cfg = _make_cfg(tmp_path)
    endpoints = [_tls_endpoint()]
    findings = []

    write_reports(cfg, endpoints, findings)

    captured = capsys.readouterr()
    assert ".cdx.json" in captured.out, "Console output missing .cdx.json path"
    assert ".cdx.xml" in captured.out, "Console output missing .cdx.xml path"


@patch("quirk.reports.writer.categorize_waves")
@patch("quirk.reports.writer.build_phased_roadmap")
@patch("quirk.reports.writer.compute_confidence")
@patch("quirk.reports.writer.compute_readiness_score")
@patch("quirk.reports.writer.build_evidence_summary")
def test_write_reports_cbom_contains_endpoint_algorithms(
    mock_evidence, mock_score, mock_conf, mock_roadmap, mock_waves, tmp_path
):
    """CBOM JSON should contain algorithm components from the scanned endpoint."""
    mock_evidence.side_effect = _stub_evidence
    mock_score.side_effect = _stub_score
    mock_conf.side_effect = _stub_confidence
    mock_roadmap.side_effect = _stub_roadmap
    mock_waves.side_effect = _stub_waves

    from quirk.reports.writer import write_reports

    cfg = _make_cfg(tmp_path)
    # Use AES-256-GCM explicitly in cipher suite
    endpoints = [_tls_endpoint(cipher_suite="TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384")]
    findings = []

    write_reports(cfg, endpoints, findings)

    json_files = glob.glob(os.path.join(str(tmp_path), "cbom-*.cdx.json"))
    assert len(json_files) == 1

    with open(json_files[0], encoding="utf-8") as f:
        data = json.load(f)

    component_names = [c.get("name", "") for c in data.get("components", [])]
    assert any("AES-256-GCM" in name or "aes-256-gcm" in name.lower() for name in component_names), (
        f"AES-256-GCM not found in components: {component_names}"
    )
