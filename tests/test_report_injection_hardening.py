"""Phase 78 / HARDEN-03 regression: scanner-controlled HTML payloads
in certificate CN must be rendered as escaped plain text in HTML + PDF.

End-to-end regression that complements the Plan 78-05 AST CI gate:
the gate prevents future drift; this test proves the *current*
write_reports pipeline renders `<script>alert(1)</script>` placed in
adversary-controlled finding fields as escaped or stripped text in
both the HTML report and the PDF report.

Fixture style mirrors `tests/test_report_sanitization.py` and
`tests/test_reports_writer.py` (PATTERNS §7). PDF assertions are guarded
by `pytest.importorskip` for `playwright.sync_api` and `pypdf` so the
HTML tests run even when Playwright is unavailable.
"""
from __future__ import annotations

import glob
import os
from types import SimpleNamespace
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Fixtures / helpers (mirror tests/test_reports_writer.py + test_report_sanitization.py)
# ---------------------------------------------------------------------------

XSS_PAYLOAD = "<script>alert(1)</script>"


def _make_cfg(tmp_path):
    return SimpleNamespace(
        output=SimpleNamespace(directory=str(tmp_path)),
        assessment=SimpleNamespace(
            name="Phase 78 HARDEN-03 Regression",
            report_owner="Test Owner",
            data_classification="Internal",
            timezone="UTC",
        ),
        intelligence=SimpleNamespace(
            profile="balanced",
            calibration_overrides=None,
        ),
    )


def _xss_endpoint():
    """A synthetic endpoint whose cipher_suite (and adjacent fields)
    contain the XSS payload, mirroring an adversarial certificate CN.
    Uses CryptoEndpoint so the CBOM builder finds every expected attr.
    """
    from quirk.models import CryptoEndpoint

    return CryptoEndpoint(
        host="evil.example.com",
        port=443,
        protocol="TLS",
        tls_version="TLSv1.3",
        cipher_suite=XSS_PAYLOAD,
        cert_pubkey_alg="RSA",
        cert_pubkey_size=2048,
        cert_sig_alg="sha256WithRSAEncryption",
        cert_subject=f"CN={XSS_PAYLOAD}",
        cert_issuer="CN=evil-ca",
        cert_not_before=None,
        cert_not_after=None,
        tls_capabilities_json=None,
        ssh_audit_json=None,
        service_detail=None,
        scan_error=None,
    )


def _xss_findings():
    """Finding list with the XSS payload embedded in every scanner-controlled
    string field (host, title, description, recommendation)."""
    return [
        {
            "severity": "HIGH",
            "host": XSS_PAYLOAD,
            "port": 443,
            "title": "<img src=x onerror=alert(1)>",
            "description": f"{XSS_PAYLOAD} Vulnerable RSA cert.",
            "recommendation": "Migrate to PQC. See javascript:alert(1) for details",
        }
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
    used by tests/test_reports_writer.py)."""
    return (
        patch("quirk.reports.writer.categorize_waves", side_effect=_stub_waves),
        patch("quirk.reports.writer.build_phased_roadmap", side_effect=_stub_roadmap),
        patch("quirk.reports.writer.compute_confidence", side_effect=_stub_confidence),
        patch("quirk.reports.writer.compute_readiness_score", side_effect=_stub_score),
        patch("quirk.reports.writer.build_evidence_summary", side_effect=_stub_evidence),
    )


def _run_write_reports(tmp_path):
    """Run write_reports with adversarial fixture; return the rendered HTML
    contents as a single string."""
    from quirk.reports.writer import write_reports

    cfg = _make_cfg(tmp_path)
    endpoints = [_xss_endpoint()]
    findings = _xss_findings()
    write_reports(cfg, endpoints=endpoints, findings=findings)

    html_files = glob.glob(os.path.join(str(tmp_path), "report-*.html"))
    assert html_files, "No HTML report written"
    with open(html_files[0], "r", encoding="utf-8") as fh:
        return fh.read()


# ---------------------------------------------------------------------------
# HTML regression
# ---------------------------------------------------------------------------


def test_script_payload_in_cert_cn_is_escaped_in_html(tmp_path):
    """`<script>alert(1)</script>` in adversarial finding fields must never
    appear raw in `report-*.html`. Either escape (`&lt;script&gt;`) or
    strip-to-empty is acceptable per CONTEXT.md criterion #1."""
    p1, p2, p3, p4, p5 = _patches()
    with p1, p2, p3, p4, p5:
        html = _run_write_reports(tmp_path)

    # Raw payload MUST NOT appear unescaped anywhere in the HTML body.
    assert XSS_PAYLOAD not in html, (
        "Adversarial `<script>alert(1)</script>` payload rendered raw in HTML"
    )
    # Either escaped (autoescape path) OR stripped entirely (nh3 strip path)
    # is acceptable. We assert at least one of these two outcomes holds.
    escaped_present = "&lt;script&gt;" in html
    stripped_payload_absent = "<script" not in html  # no `<script` substring at all
    assert escaped_present or stripped_payload_absent, (
        "HTML neither escapes nor strips the adversarial payload"
    )


def test_javascript_url_in_finding_recommendation_stripped(tmp_path):
    """`javascript:alert(1)` URL in a finding recommendation must be stripped
    by sanitize_scanner_text (URL-scheme regex strip, Plan 78-01)."""
    p1, p2, p3, p4, p5 = _patches()
    with p1, p2, p3, p4, p5:
        html = _run_write_reports(tmp_path)

    assert "javascript:" not in html, (
        "javascript: URL leaked through into rendered HTML — "
        "sanitize_scanner_text URL-strip regression"
    )


def test_db_stored_raw_payload_preserved(tmp_path):
    """CONTEXT.md Cluster C invariant: raw scanner data stays in the DB so
    future report formats can re-apply policy. write_reports does NOT
    persist findings to a SQLAlchemy session — it writes JSON+MD+HTML+PDF
    artifacts to disk. The closest available proxy is the raw findings JSON
    (`findings-*.json`), which is `_json_dump`'d before any rendering. This
    test asserts the raw payload survives JSON write (i.e., sanitization is
    render-boundary only, not write-time).
    """
    import json

    p1, p2, p3, p4, p5 = _patches()
    with p1, p2, p3, p4, p5:
        from quirk.reports.writer import write_reports

        cfg = _make_cfg(tmp_path)
        endpoints = [_xss_endpoint()]
        findings = _xss_findings()
        write_reports(cfg, endpoints=endpoints, findings=findings)

    json_files = glob.glob(os.path.join(str(tmp_path), "findings-*.json"))
    assert json_files, "No findings JSON written"
    with open(json_files[0], "r", encoding="utf-8") as fh:
        data = json.load(fh)
    # Raw payload preserved in the JSON store (Cluster C: sanitize at render
    # boundary, never at write time).
    target = next((f for f in data if XSS_PAYLOAD in str(f.get("host", ""))), None)
    assert target is not None, (
        "Adversarial host payload was sanitized at write time — violates "
        "CONTEXT.md Cluster C raw-data-in-store invariant"
    )
    assert XSS_PAYLOAD in target["description"], (
        "Adversarial description payload was sanitized at write time"
    )


# ---------------------------------------------------------------------------
# PDF regression (skips cleanly when Playwright/pypdf unavailable)
# ---------------------------------------------------------------------------


def test_script_payload_in_cert_cn_is_escaped_in_pdf(tmp_path):
    """End-to-end PDF assertion: the adversarial payload must not appear
    raw in the extracted text of `report-*.pdf`. Skips cleanly if Playwright
    or pypdf is unavailable in the test environment."""
    pytest.importorskip("playwright.sync_api")
    pypdf = pytest.importorskip("pypdf")

    p1, p2, p3, p4, p5 = _patches()
    with p1, p2, p3, p4, p5:
        from quirk.reports.writer import write_reports

        cfg = _make_cfg(tmp_path)
        endpoints = [_xss_endpoint()]
        findings = _xss_findings()
        write_reports(cfg, endpoints=endpoints, findings=findings)

    pdf_files = glob.glob(os.path.join(str(tmp_path), "report-*.pdf"))
    if not pdf_files:
        pytest.skip(
            "report-*.pdf not produced (Playwright Chromium binary likely "
            "absent — graceful-degradation path). HTML assertions still ran."
        )

    reader = pypdf.PdfReader(pdf_files[0])
    extracted = ""
    for page in reader.pages:
        extracted += page.extract_text() or ""

    # The literal raw payload must not survive into the PDF text layer.
    assert XSS_PAYLOAD not in extracted, (
        "Adversarial `<script>alert(1)</script>` payload appeared raw in "
        "extracted PDF text"
    )
