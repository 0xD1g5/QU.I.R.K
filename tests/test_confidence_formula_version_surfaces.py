"""Phase 184.1-06 / SC-3 gap closure — per-surface emitted-artifact regression.

`tests/test_intelligence_confidence.py -k formula_version` passed the entire time
`confidence_formula_version` was computed by `compute_confidence()` but silently
dropped by all three shipped consumers (`quirk/reports/writer.py`,
`quirk/reports/executive.py`, `quirk/dashboard/api/routes/scan.py`) — a unit test on
the pure function cannot detect that the marker never reaches an operator or API
client (184.1-VERIFICATION.md SC-3 gap / 184.1-REVIEW.md CR-01). Every assertion in
this file therefore targets an EMITTED artifact — bytes written to disk, generated
markdown text, or an HTTP response body — never the return dict of
`compute_confidence()` directly.

Falsifiability contract: reverting any ONE of the three Task-1 consumer edits must
turn exactly the corresponding named test in this file RED:
  - reverting quirk/reports/writer.py's `conf` compat-dict addition ->
    test_intelligence_json_carries_formula_version RED
  - reverting quirk/reports/executive.py's markdown bullet ->
    test_exec_markdown_carries_formula_version RED
  - reverting quirk/dashboard/api/schemas.py's field or
    quirk/dashboard/api/routes/scan.py's pass-through ->
    test_api_scan_response_carries_formula_version RED

No Docker, no live DB, no network — this phase's tests must not degrade to an
honest skip (184.1-VALIDATION.md Known CI Degradation). All three tests build
their own fixtures directly (tmp_path, in-memory SQLite) with zero external
dependencies.
"""
from __future__ import annotations

import glob
import json
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from quirk.intelligence.confidence import CONFIDENCE_FORMULA_VERSION
from quirk.models import Base, CryptoEndpoint
from quirk.reports.executive import build_exec_markdown
from quirk.reports.writer import write_reports


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

def _make_cfg(outdir: str):
    """Mirrors tests/test_reports_writer.py's _make_cfg SimpleNamespace pattern."""
    return SimpleNamespace(
        output=SimpleNamespace(directory=outdir),
        assessment=SimpleNamespace(
            name="184.1-06 Test Assessment",
            report_owner="Test Owner",
            data_classification="Internal",
            timezone="UTC",
        ),
        intelligence=SimpleNamespace(
            profile="balanced",
            calibration_overrides=None,
        ),
    )


def _endpoints_fixture():
    """A minimal real CryptoEndpoint set (mirrors
    tests/test_evidence_coverage_regression.py's construction style) — enough
    for compute_confidence to run its normal (non-NO_DATA) path.
    """
    return [
        CryptoEndpoint(
            host="host1.example.com", port=443, protocol="TLS",
            tls_version="TLSv1.3", tls_supported_versions="TLSv1.2,TLSv1.3",
            cert_pubkey_alg="RSA", cert_pubkey_size=2048,
        ),
        CryptoEndpoint(host="host2.example.com", port=22, protocol="SSH"),
    ]


# ---------------------------------------------------------------------------
# (a) intelligence-{stamp}.json
# ---------------------------------------------------------------------------

def test_intelligence_json_carries_formula_version(tmp_path) -> None:
    cfg = _make_cfg(str(tmp_path))
    endpoints = _endpoints_fixture()
    findings: list = []

    write_reports(cfg, endpoints, findings)

    intel_files = glob.glob(str(tmp_path / "intelligence-*.json"))
    assert intel_files, "write_reports must emit an intelligence-{stamp}.json"
    with open(intel_files[0], "r", encoding="utf-8") as f:
        data = json.load(f)

    # Presence, not just value, is what D-15's absence-means-pre-184.1 rule turns on.
    assert "confidence_formula_version" in data["confidence"], (
        "SC-3 / D-12 / D-15: intelligence-{stamp}.json's confidence object must carry "
        "confidence_formula_version, or a client cannot distinguish a post-184.1 report "
        "from a pre-184.1 one per the documented rule."
    )
    assert data["confidence"]["confidence_formula_version"] == CONFIDENCE_FORMULA_VERSION


# ---------------------------------------------------------------------------
# (b) executive markdown
# ---------------------------------------------------------------------------

def test_exec_markdown_carries_formula_version() -> None:
    cfg = _make_cfg("/unused")
    endpoints = _endpoints_fixture()
    findings: list = []

    md = build_exec_markdown(cfg, endpoints, findings)

    # Assert PRESENCE of the literal field name, per project convention
    # (render-parity tests assert presence, not visual placement/ordering).
    assert "confidence_formula_version" in md, (
        "SC-3 / D-12 / D-15: the executive markdown's Confidence & Coverage section "
        "must name the confidence_formula_version field so a client can tell which "
        "formula produced the number."
    )


# ---------------------------------------------------------------------------
# (c) /api/scan/latest HTTP response
# ---------------------------------------------------------------------------

def _make_client_and_session():
    """Harness copied from tests/test_dashboard_scans_score_profile.py (not
    imported across test modules, per that file's established convention).
    """
    db_name = f"test_confidence_formula_version_{uuid.uuid4().hex}"
    engine = create_engine(
        f"sqlite:///file:{db_name}?mode=memory&cache=shared&uri=true",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def _override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    from quirk.dashboard.api.app import create_app
    from quirk.dashboard.api.deps import get_db

    app = create_app()
    app.dependency_overrides[get_db] = _override_get_db
    return TestClient(app), TestingSession


def test_api_scan_response_carries_formula_version(monkeypatch) -> None:
    # An unexplained 401 here would look like a code failure, not an auth gate.
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)

    client, TestingSession = _make_client_and_session()
    db = TestingSession()
    try:
        db.add(CryptoEndpoint(
            host="dashboard.example.com", port=443, protocol="TLS",
            tls_version="TLSv1.3", tls_supported_versions="TLSv1.2,TLSv1.3",
            cert_pubkey_alg="RSA", cert_pubkey_size=2048,
            scanned_at=datetime.now(timezone.utc).replace(tzinfo=None),
        ))
        db.commit()
    finally:
        db.close()

    resp = client.get("/api/scan/latest")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["confidence"]["confidence_formula_version"] == CONFIDENCE_FORMULA_VERSION, (
        "SC-3 / D-12: /api/scan/latest must pass confidence_raw's "
        "confidence_formula_version through to the ConfidenceData response."
    )
