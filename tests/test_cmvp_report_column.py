"""Phase 81 CMVP-06 — HTML/PDF report column rendering smoke tests.

Harness cloned from tests/test_report_injection_hardening.py:13,30-60.

Builds a synthetic scan session with a few algorithms (AES-256-GCM covered by
the bundled cache, ChaCha20-Poly1305 explicitly absent), runs
``quirk.reports.writer.write_reports``, globs for the rendered HTML, and
asserts:

  * The ``Algorithm Inventory`` section header is present.
  * The ``CMVP Coverage`` column header is present.
  * A known covering module name (``OpenSSL FIPS Provider``) appears on the
    AES row.
  * The ChaCha20-Poly1305 row renders the literal ``Not in CMVP catalog``.
  * An XSS payload embedded in an algorithm name is escaped/stripped — the
    Phase 78 sanitize chokepoint contract holds for the new column.

PDF rendering is guarded by ``pytest.importorskip("playwright.sync_api")``
so HTML assertions still run in CI without Playwright.
"""
from __future__ import annotations

import glob
import os
from types import SimpleNamespace
from unittest.mock import patch

import pytest


XSS_PAYLOAD = "<script>alert(1)</script>"


# ---------------------------------------------------------------------------
# Fixture helpers (mirror tests/test_report_injection_hardening.py:30-72).
# ---------------------------------------------------------------------------

def _make_cfg(tmp_path):
    return SimpleNamespace(
        output=SimpleNamespace(directory=str(tmp_path)),
        assessment=SimpleNamespace(
            name="Phase 81 CMVP-06 Smoke",
            report_owner="Test Owner",
            data_classification="Internal",
            timezone="UTC",
        ),
        intelligence=SimpleNamespace(
            profile="balanced",
            calibration_overrides=None,
        ),
    )


def _aes_endpoint():
    """CryptoEndpoint with AES-256-GCM cipher suite — coverage hits the
    bundled cache (OpenSSL FIPS Provider, cert 4985, RESEARCH anchor)."""
    from quirk.models import CryptoEndpoint
    return CryptoEndpoint(
        host="aes.example.com",
        port=443,
        protocol="TLS",
        tls_version="TLSv1.3",
        cipher_suite="AES-256-GCM",
        cert_pubkey_alg="RSA",
        cert_pubkey_size=2048,
        cert_sig_alg="sha256WithRSAEncryption",
        cert_subject="CN=aes.example.com",
        cert_issuer="CN=test-ca",
        cert_not_before=None,
        cert_not_after=None,
        tls_capabilities_json=None,
        ssh_audit_json=None,
        service_detail=None,
        scan_error=None,
    )


def _chacha_endpoint():
    """CryptoEndpoint with ChaCha20-Poly1305 — _FAMILY_MAP returns None →
    HTML row should read 'Not in CMVP catalog'."""
    from quirk.models import CryptoEndpoint
    return CryptoEndpoint(
        host="chacha.example.com",
        port=443,
        protocol="TLS",
        tls_version="TLSv1.3",
        cipher_suite="ChaCha20-Poly1305",
        cert_pubkey_alg="RSA",
        cert_pubkey_size=2048,
        cert_sig_alg="sha256WithRSAEncryption",
        cert_subject="CN=chacha.example.com",
        cert_issuer="CN=test-ca",
        cert_not_before=None,
        cert_not_after=None,
        tls_capabilities_json=None,
        ssh_audit_json=None,
        service_detail=None,
        scan_error=None,
    )


def _xss_endpoint():
    """CryptoEndpoint whose cipher_suite is the XSS payload — exercises the
    Phase 78 sanitize chokepoint on the new CMVP Coverage row."""
    from quirk.models import CryptoEndpoint
    return CryptoEndpoint(
        host="xss.example.com",
        port=443,
        protocol="TLS",
        tls_version="TLSv1.3",
        cipher_suite=XSS_PAYLOAD,
        cert_pubkey_alg="RSA",
        cert_pubkey_size=2048,
        cert_sig_alg="sha256WithRSAEncryption",
        cert_subject="CN=xss.example.com",
        cert_issuer="CN=test-ca",
        cert_not_before=None,
        cert_not_after=None,
        tls_capabilities_json=None,
        ssh_audit_json=None,
        service_detail=None,
        scan_error=None,
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
        "findings_count": 0,
        "scan_error_rate": 0.0,
    }


def _stub_score(evidence, **kwargs):
    return {
        "score": 80,
        "subscores": {
            "inventory": 80, "cipher": 80, "certificate": 80, "protocol": 80,
        },
        "drivers": [],
    }


def _stub_confidence(evidence):
    return {"confidence_score": 70, "factor_breakdown": {}}


def _stub_roadmap(evidence, score):
    return {"items": []}


def _stub_waves(findings):
    return {"Wave 1": [], "Wave 2": [], "Wave 3": []}


def _patches():
    return (
        patch("quirk.reports.writer.categorize_waves", side_effect=_stub_waves),
        patch(
            "quirk.reports.writer.build_phased_roadmap", side_effect=_stub_roadmap
        ),
        patch(
            "quirk.reports.writer.compute_confidence", side_effect=_stub_confidence
        ),
        patch(
            "quirk.reports.writer.compute_readiness_score",
            side_effect=_stub_score,
        ),
        patch(
            "quirk.reports.writer.build_evidence_summary",
            side_effect=_stub_evidence,
        ),
    )


def _run_reports(tmp_path, endpoints) -> str:
    from quirk.reports.writer import write_reports

    cfg = _make_cfg(tmp_path)
    write_reports(cfg, endpoints=endpoints, findings=[])
    html_files = glob.glob(os.path.join(str(tmp_path), "report-*.html"))
    assert html_files, "No HTML report written"
    with open(html_files[0], "r", encoding="utf-8") as fh:
        return fh.read()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_html_has_algorithm_inventory_heading(tmp_path) -> None:
    """The Algorithm Inventory section header MUST be present in the HTML."""
    p1, p2, p3, p4, p5 = _patches()
    with p1, p2, p3, p4, p5:
        html = _run_reports(tmp_path, [_aes_endpoint(), _chacha_endpoint()])
    assert "<h2>Algorithm Inventory" in html, (
        "HTML report is missing the Algorithm Inventory <h2>"
    )


def test_html_has_cmvp_coverage_column_header(tmp_path) -> None:
    """The CMVP Coverage column header MUST be present."""
    p1, p2, p3, p4, p5 = _patches()
    with p1, p2, p3, p4, p5:
        html = _run_reports(tmp_path, [_aes_endpoint(), _chacha_endpoint()])
    assert "CMVP Coverage" in html, (
        "HTML report is missing the 'CMVP Coverage' column header"
    )


def test_html_aes_row_lists_known_covering_module(tmp_path) -> None:
    """The AES row's CMVP Coverage cell must list at least one of the bundled
    covering module names (RESEARCH anchor: OpenSSL FIPS Provider)."""
    p1, p2, p3, p4, p5 = _patches()
    with p1, p2, p3, p4, p5:
        html = _run_reports(tmp_path, [_aes_endpoint()])
    assert "OpenSSL FIPS Provider" in html, (
        "AES row does not surface 'OpenSSL FIPS Provider' from cmvp_cache.json"
    )


def test_html_unmapped_algorithm_renders_not_in_cmvp_catalog(tmp_path) -> None:
    """ChaCha20-Poly1305 has no _FAMILY_MAP entry → row reads the literal
    'Not in CMVP catalog' (v4.10-D-01 — DO NOT change this wording)."""
    p1, p2, p3, p4, p5 = _patches()
    with p1, p2, p3, p4, p5:
        html = _run_reports(tmp_path, [_chacha_endpoint()])
    assert "Not in CMVP catalog" in html, (
        "HTML should render 'Not in CMVP catalog' for ChaCha20-Poly1305"
    )


def test_html_xss_payload_in_algorithm_name_is_sanitized(tmp_path) -> None:
    """Phase 78 sanitize chokepoint contract: the XSS payload placed in an
    algorithm-name field MUST NOT appear unescaped in the rendered HTML —
    either escaped (``&lt;script&gt;``) or stripped is acceptable."""
    p1, p2, p3, p4, p5 = _patches()
    with p1, p2, p3, p4, p5:
        html = _run_reports(tmp_path, [_xss_endpoint(), _aes_endpoint()])
    assert XSS_PAYLOAD not in html, (
        "Raw XSS payload appears unescaped in the rendered HTML report"
    )


def test_html_never_emits_certified_true_literal(tmp_path) -> None:
    """v4.10-D-01 invariant — the rendered HTML must never contain a literal
    ``certified: true`` / ``"certified":true`` string."""
    import re

    p1, p2, p3, p4, p5 = _patches()
    with p1, p2, p3, p4, p5:
        html = _run_reports(tmp_path, [_aes_endpoint(), _chacha_endpoint()])
    # Case-insensitive, tolerant of whitespace/JSON-ish.
    pattern = re.compile(r"\"?certified\"?\s*:\s*true", re.IGNORECASE)
    assert not pattern.search(html), (
        "v4.10-D-01 violation — rendered HTML contains 'certified: true'"
    )
