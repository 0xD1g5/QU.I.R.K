"""Phase 98 EXEC-04 — Cross-surface content parity gate (D-03a).

Belt-and-suspenders corroboration on top of the structural D-03 guarantee:
one ExecContent instance passed to both CLI and HTML renderers must produce
identical narrative_lead text and identical top_risks count + labels.

This test is NOT the primary parity mechanism (D-03's single shared instance IS),
but provides an observable, auto-running regression gate for EXEC-04.

Test node IDs from 98-VALIDATION.md:
  - test_narrative_content_parity
  - test_top_risks_parity
"""
from __future__ import annotations

import os
from types import SimpleNamespace

from quirk.reports.content_model import build_exec_content, ExecContent


# ---------------------------------------------------------------------------
# Shared fixtures — canonical score_raw shape (Pitfall 1: "score" not "total")
# ---------------------------------------------------------------------------

# FAIR band: no CRITICAL-count restriction so the congruence guard won't fire
_SCORE_RAW = {
    "score": 42,
    "rating": "FAIR",
    "subscores": {
        "hygiene": 10,
        "modern_tls": 7,
        "identity_trust": 11,
        "agility_signals": 6,
        "data_at_rest": 5,
        "data_in_motion": 3,
    },
    "drivers": [
        "Weak TLS 1.0 configuration detected",
        "No PQC hybrid candidates identified",
    ],
}

# One MEDIUM-severity RSA finding — guarantees at least one top_risk entry
_FINDINGS = [
    {
        "title": "RSA-2048 certificate in use",
        "severity": "HIGH",
        "category": "certificate",
        "description": "RSA-2048 certificate; quantum-vulnerable harvest-now-decrypt-later risk.",
        "check_id": "CERT-RSA-2048",
        "host": "example.com",
        "port": 443,
    },
]

_ROADMAP_ITEMS_RAW = [
    {
        "phase": "NOW",
        "title": "Rotate RSA certificates to hybrid algorithm",
        "why": "RSA-2048 is quantum-vulnerable; migrate to hybrid or PQC certificate.",
        "owner_placeholder": "PKI Team",
        "timeframe": "NOW",
        "dependencies": [],
        "_priority": 1,
    },
]


def _make_minimal_cfg():
    """Minimal cfg-like namespace for renderer calls (mirrors test_html_report.py pattern)."""
    return SimpleNamespace(
        assessment=SimpleNamespace(
            name="Cross-Surface Parity Test Org",
            report_owner="Parity Tester",
            data_classification="CONFIDENTIAL",
            timezone="UTC",
        ),
        output=SimpleNamespace(directory="/tmp/quirk_test_cross_surface_parity"),
        intelligence=SimpleNamespace(
            profile="balanced",
            calibration_overrides=None,
        ),
    )


# ---------------------------------------------------------------------------
# EXEC-04 / D-03a: test_narrative_content_parity
# ---------------------------------------------------------------------------

def test_narrative_content_parity(tmp_path):
    """EXEC-04 / D-03a: single ExecContent yields identical narrative_lead in CLI and HTML.

    One ExecContent instance is built and passed to BOTH build_exec_markdown() and
    render_html_report(). The narrative_lead string must appear verbatim in both outputs.
    This is the cross-surface belt-and-suspenders corroboration of D-03 (structural
    single-source guarantee).

    Node ID: test_cross_surface_parity.py::test_narrative_content_parity
    """
    from quirk.reports.executive import build_exec_markdown
    from quirk.reports.html_renderer import render_html_report

    # Build ONE ExecContent instance (D-03 guarantee: same object → same content)
    exec_content: ExecContent = build_exec_content(
        score_raw=_SCORE_RAW,
        findings=_FINDINGS,
        roadmap_items=_ROADMAP_ITEMS_RAW,
    )
    assert exec_content.narrative_lead, (
        "exec_content.narrative_lead is empty — build_exec_content returned no narrative lead. "
        "EXEC-04: cannot assert parity on an empty string."
    )

    # CLI surface: pass exec_content to build_exec_markdown
    cfg = _make_minimal_cfg()
    cli_output: str = build_exec_markdown(
        cfg=cfg,
        endpoints=[],
        findings=_FINDINGS,
        exec_content=exec_content,
    )

    # HTML surface: render to tmp dir, read back
    html_path = os.path.join(str(tmp_path), "parity-test.html")
    render_html_report(
        path=html_path,
        cfg=cfg,
        endpoints=[],
        findings=_FINDINGS,
        score={
            "total": _SCORE_RAW["score"],
            "subscores": _SCORE_RAW["subscores"],
            "drivers": list(_SCORE_RAW["drivers"]),
        },
        conf={"confidence": 60, "confidence_factors": {}},
        roadmap_items=_ROADMAP_ITEMS_RAW,
        exec_content=exec_content,
    )
    html_output: str = open(html_path, encoding="utf-8").read()

    # EXEC-04 assertion: narrative_lead appears verbatim in CLI output
    assert exec_content.narrative_lead in cli_output, (
        f"EXEC-04 VIOLATION: exec_content.narrative_lead not found in CLI markdown output.\n"
        f"  Expected substring: {exec_content.narrative_lead!r}\n"
        f"  CLI output preview: {cli_output[:400]!r}"
    )

    # EXEC-04 assertion: narrative_lead appears verbatim in HTML output
    assert exec_content.narrative_lead in html_output, (
        f"EXEC-04 VIOLATION: exec_content.narrative_lead not found in HTML output.\n"
        f"  Expected substring: {exec_content.narrative_lead!r}\n"
        f"  HTML output preview (first 600 chars after <body): ..."
    )

    # Belt-and-suspenders: both surfaces contain the identical string — parity confirmed
    assert (exec_content.narrative_lead in cli_output) and (exec_content.narrative_lead in html_output), (
        "EXEC-04 VIOLATION: narrative_lead is present in one surface but absent in the other. "
        "D-03 shared content model must guarantee identical narrative_lead across CLI and HTML."
    )


# ---------------------------------------------------------------------------
# EXEC-04 / D-03a: test_top_risks_parity
# ---------------------------------------------------------------------------

def test_top_risks_parity(tmp_path):
    """EXEC-04 / D-03a: CLI and HTML carry identical top_risks count and labels.

    One ExecContent instance is built (guaranteeing same top_risks list). The CLI
    markdown Priority Business Risks bullet count and the HTML .risks-list item count
    must both equal exec_content.top_risks count. Risk labels must match across surfaces.

    Node ID: test_cross_surface_parity.py::test_top_risks_parity
    """
    from quirk.reports.executive import build_exec_markdown
    from quirk.reports.html_renderer import render_html_report

    exec_content: ExecContent = build_exec_content(
        score_raw=_SCORE_RAW,
        findings=_FINDINGS,
        roadmap_items=_ROADMAP_ITEMS_RAW,
    )

    # Prerequisite: fixture findings must produce at least one top_risk
    assert exec_content.top_risks, (
        "exec_content.top_risks is empty — _FINDINGS fixture does not produce any top-risks. "
        "EXEC-04 parity test requires at least one risk entry."
    )

    expected_risk_count = len(exec_content.top_risks)
    expected_labels = [r.risk_label for r in exec_content.top_risks]

    # CLI surface
    cfg = _make_minimal_cfg()
    cli_output: str = build_exec_markdown(
        cfg=cfg,
        endpoints=[],
        findings=_FINDINGS,
        exec_content=exec_content,
    )

    # HTML surface
    html_path = os.path.join(str(tmp_path), "parity-risks-test.html")
    render_html_report(
        path=html_path,
        cfg=cfg,
        endpoints=[],
        findings=_FINDINGS,
        score={
            "total": _SCORE_RAW["score"],
            "subscores": _SCORE_RAW["subscores"],
            "drivers": list(_SCORE_RAW["drivers"]),
        },
        conf={"confidence": 60, "confidence_factors": {}},
        roadmap_items=_ROADMAP_ITEMS_RAW,
        exec_content=exec_content,
    )
    html_output: str = open(html_path, encoding="utf-8").read()

    # --- CLI count gate ---
    # Priority Business Risks bullets appear after the "## Priority Business Risks" heading.
    # Each risk produces exactly one bullet: "- **{risk_label}** — {impact_sentence}"
    assert "## Priority Business Risks" in cli_output, (
        "EXEC-04 VIOLATION: '## Priority Business Risks' section not found in CLI markdown. "
        "build_exec_markdown must render top_risks when exec_content is provided."
    )
    # Count occurrences of risk_label in CLI (one per risk bullet)
    cli_risk_label_count = sum(
        1 for label in expected_labels if label in cli_output
    )
    assert cli_risk_label_count == expected_risk_count, (
        f"EXEC-04 VIOLATION: CLI markdown risk label count ({cli_risk_label_count}) != "
        f"exec_content.top_risks count ({expected_risk_count}). "
        "D-03: CLI must render all top_risks from the shared ExecContent."
    )

    # --- HTML count gate ---
    assert "risks-list" in html_output, (
        "EXEC-04 VIOLATION: '.risks-list' not found in HTML output. "
        "render_html_report must render top_risks when exec_content is provided."
    )
    # Count occurrences of risk_label in HTML (one per <li> item)
    html_risk_label_count = sum(
        1 for label in expected_labels if label in html_output
    )
    assert html_risk_label_count == expected_risk_count, (
        f"EXEC-04 VIOLATION: HTML risk label count ({html_risk_label_count}) != "
        f"exec_content.top_risks count ({expected_risk_count}). "
        "D-03: HTML must render all top_risks from the shared ExecContent."
    )

    # --- Cross-surface label identity ---
    for label in expected_labels:
        assert label in cli_output, (
            f"EXEC-04 VIOLATION: risk_label {label!r} present in exec_content.top_risks "
            f"but not found in CLI markdown output. "
            "D-03 shared model must guarantee identical labels across surfaces."
        )
        assert label in html_output, (
            f"EXEC-04 VIOLATION: risk_label {label!r} present in exec_content.top_risks "
            f"but not found in HTML output. "
            "D-03 shared model must guarantee identical labels across surfaces."
        )


# ---------------------------------------------------------------------------
# Phase 100 Plan 02 / FMT-03 / D-10: DOCX cross-surface parity
# ---------------------------------------------------------------------------

def test_docx_narrative_parity(tmp_path):
    """FMT-03 / D-10: DOCX carries the same exec_content.narrative_lead as HTML/CLI.

    The DOCX renderer must consume the shared ExecContent (D-10) — not build
    its own content. Narrative lead must appear verbatim in all three surfaces.
    """
    from quirk.reports.executive import build_exec_markdown
    from quirk.reports.html_renderer import render_html_report
    from quirk.reports.docx_renderer import render_docx_report

    exec_content: ExecContent = build_exec_content(
        score_raw=_SCORE_RAW,
        findings=_FINDINGS,
        roadmap_items=_ROADMAP_ITEMS_RAW,
    )
    assert exec_content.narrative_lead, (
        "exec_content.narrative_lead is empty — build_exec_content returned no narrative lead."
    )

    cfg = _make_minimal_cfg()

    # CLI surface
    cli_output: str = build_exec_markdown(
        cfg=cfg,
        endpoints=[],
        findings=_FINDINGS,
        exec_content=exec_content,
    )

    # HTML surface
    html_path = os.path.join(str(tmp_path), "parity-docx-test.html")
    render_html_report(
        path=html_path,
        cfg=cfg,
        endpoints=[],
        findings=_FINDINGS,
        score={
            "total": _SCORE_RAW["score"],
            "subscores": _SCORE_RAW["subscores"],
            "drivers": list(_SCORE_RAW["drivers"]),
        },
        conf={"confidence": 60, "confidence_factors": {}},
        roadmap_items=_ROADMAP_ITEMS_RAW,
        exec_content=exec_content,
    )
    html_output: str = open(html_path, encoding="utf-8").read()

    # DOCX surface
    docx_path = os.path.join(str(tmp_path), "parity-docx-test.docx")
    result = render_docx_report(
        path=docx_path,
        cfg=cfg,
        findings=_FINDINGS,
        exec_content=exec_content,
    )

    # Only assert DOCX parity if python-docx is available (graceful skip)
    if result is False:
        import pytest as _pytest
        _pytest.skip("python-docx not installed — skipping DOCX parity check")

    from docx import Document
    doc = Document(docx_path)
    docx_full_text = "\n".join(p.text for p in doc.paragraphs)

    # EXEC-04 assertion: narrative_lead appears verbatim in all three surfaces
    assert exec_content.narrative_lead in cli_output, (
        f"FMT-03 VIOLATION: narrative_lead not in CLI output.\n"
        f"  Expected: {exec_content.narrative_lead!r}"
    )
    assert exec_content.narrative_lead in html_output, (
        f"FMT-03 VIOLATION: narrative_lead not in HTML output.\n"
        f"  Expected: {exec_content.narrative_lead!r}"
    )
    assert exec_content.narrative_lead in docx_full_text, (
        f"FMT-03 VIOLATION: narrative_lead not in DOCX paragraph text.\n"
        f"  Expected: {exec_content.narrative_lead!r}\n"
        f"  DOCX text preview: {docx_full_text[:400]!r}"
    )


# ---------------------------------------------------------------------------
# Phase 210 Plan 05 / XSURF-04 (D-13/D-14/D-15): three-number cross-surface
# equality gate for ONE persisted scan_run_id.
#
# D-13: extends THIS file (no new top-level test file), reusing the
# TestClient + in-memory-SQLite harness shape from tests/test_api_scan_window.py
# (borrowed, not imported, per that plan's own harness contract) plus the
# "one seed, N surfaces, compare independently-extracted numbers" shape this
# file and tests/test_score_lift_cross_surface_numbers.py already use.
#
# D-14: asserts three numbers for ONE scan_run_id, each with its own
# assertion + named diagnostic — headline score, CRITICAL finding count,
# certificate count — comparing the report pipeline (evaluate_endpoints +
# evaluate_identity_endpoints -> build_evidence_summary -> compute_readiness_score,
# called directly over the persisted rows) against the dashboard pipeline
# (GET /api/scan/latest?scan_id=<scan_run_id> via TestClient).
#
# D-15: Task 2 (see 210-05-SUMMARY.md "Falsification" section) demonstrates
# this gate failing against two independently reintroduced double-counts.
# ---------------------------------------------------------------------------

import uuid as _uuid
from datetime import datetime as _datetime, timedelta as _timedelta, timezone as _timezone
from types import SimpleNamespace as _SimpleNamespace

from fastapi.testclient import TestClient as _TestClient
from sqlalchemy import create_engine as _create_engine
from sqlalchemy.orm import sessionmaker as _sessionmaker

from quirk.dashboard.api.app import create_app as _create_app
from quirk.dashboard.api.deps import get_db as _get_db
from quirk.models import Base as _Base, CryptoEndpoint as _CryptoEndpoint
from quirk.engine.findings_evaluator import (
    derive_report_findings as _derive_report_findings,
)
from quirk.intelligence.evidence import build_evidence_summary as _build_evidence_summary
from quirk.intelligence.scoring import compute_readiness_score as _compute_readiness_score

_XSURF04_CSRF = {"X-Quirk-Request": "1"}

# scan_run_id must be an ISO-parseable string: the `?scan_id=` branch of
# GET /api/scan/latest validates it via datetime.fromisoformat() before
# matching it LITERALLY against CryptoEndpoint.scan_run_id (scan.py:1701-1706)
# — a non-ISO id like "xsurf04-run-1" would 400 before ever reaching the
# equality filter. Real scan_run_id values are always ISO timestamps
# (quirk/models.py:104-105), so this fixture matches production shape.
_XSURF04_RUN_ID = "2026-09-27T09:15:00"

# Pinned expected values for the fixture in `_xsurf04_seed_scan_run` (Task 2 /
# D-15 widening). The plain A==B comparison below is STRUCTURALLY BLIND to a
# regression in a site that BOTH surfaces call identically in-process — Phase
# 210 D-06 unified SAML finding synthesis into one shared
# `evaluate_identity_endpoints`, called by both the report pipeline and (via
# `_derive_identity_findings`) the dashboard route, so a bug there moves BOTH
# sides together and A==B still holds. Live-verified during this plan's
# falsification (see 210-05-SUMMARY.md): disabling the `(host, port, serial)`
# dedupe made BOTH surfaces report CRITICAL=3 instead of 2 — equal, and wrong.
# Pinning the CORRECT value independently of either surface is what actually
# catches that class of regression.
_EXPECTED_XSURF04_CRITICAL_COUNT = 2   # 1 (deduped same-serial pair) + 1 (distinct-serial pair)
_EXPECTED_XSURF04_CERT_COUNT = 3       # two healthy TLS rows + the 228-07 near-expiry TLS row (was 2)
# quirk/intelligence/evidence.py's `_seen_saml_certs` dedupe (D-03) is a
# SEPARATE counter (`saml_weak_signing_count`) that feeds the headline score
# through a ratio too small, at this fixture's scale, to reliably move the
# post-consequence-ceiling COMPRESSED integer score (live-verified: baseline
# computed=95 vs sabotaged computed=94, both compress to the same displayed
# 32). Pin the pipeline's own internal counter directly, since neither of
# D-14's three surfaced numbers is guaranteed sensitive to this site.
_EXPECTED_XSURF04_SAML_WEAK_SIGNING_COUNT = 2


def _xsurf04_make_client_and_session():
    """TestClient + in-memory-SQLite session factory, borrowed verbatim in
    shape from tests/test_api_scan_window.py:35-52 (D-13's named harness)."""
    db_name = f"test_xsurf04_{_uuid.uuid4().hex}"
    engine = _create_engine(
        f"sqlite:///file:{db_name}?mode=memory&cache=shared&uri=true",
        connect_args={"check_same_thread": False},
    )
    _Base.metadata.create_all(engine)
    TestingSession = _sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def _override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app = _create_app()
    app.dependency_overrides[_get_db] = _override_get_db
    return _TestClient(app, headers=_XSURF04_CSRF), TestingSession


def _xsurf04_seed_scan_run(TestingSession, scan_run_id: str) -> None:
    """Seeds ONE scan_run_id with a mixed endpoint set (D-14's fixture):

    - a SAML dual-`use` SAME-serial pair (serial=0a1b) — one certificate
      published under two KeyDescriptor `use` values, the exact XSURF-01
      reproduction shape (quirk/scanner/saml_scanner.py:168,277,308).
    - a SAML DISTINCT-serial row on a different host:port — must survive
      the dedupe uncollapsed (safety property: distinct certs are never
      suppressed).
    - two non-identity, healthy TLS endpoints — makes the certificate count
      non-1 and keeps the score off a trivial floor/ceiling.

    Every row sets scan_run_id explicitly (never NULL — the NULL fallback is
    plan 210-04's XSURF-03 concern, not this gate's) and sets scanned_at (a
    row without it is invisible to the history surfaces).
    """
    db = TestingSession()
    try:
        # ONE clock (Phase 230): scanned_at tracks the wall clock, like the
        # XSURF-0508/XSURF-07 fixtures. It used to be fixed at 2026-09-27
        # while the near-expiry row below is now+10d. evidence.py measures
        # expiry against scanned_at and the finding generators against the
        # wall clock, so the pinned score silently moved 31 -> 32 at
        # 2026-10-17 09:15 UTC (fixed scanned_at + 30d passed now+10d).
        # Only the run-id STRING is matched, so it stays a literal.
        now = _datetime.now()
        rows = [
            # --- SAML dual-`use` same-serial pair (XSURF-01 fixture) ---
            _CryptoEndpoint(
                scan_run_id=scan_run_id, scanned_at=now,
                host="10.80.0.41", port=8080, protocol="SAML",
                cert_pubkey_alg="RSA", cert_pubkey_size=1024,
                service_detail="urn:mh-saml-idp|use=signing|serial=0a1b",
            ),
            _CryptoEndpoint(
                scan_run_id=scan_run_id, scanned_at=now,
                host="10.80.0.41", port=8080, protocol="SAML",
                cert_pubkey_alg="RSA", cert_pubkey_size=1024,
                service_detail="urn:mh-saml-idp|use=encryption|serial=0a1b",
            ),
            # --- SAML distinct-serial row (over-dedupe guard) ---
            _CryptoEndpoint(
                scan_run_id=scan_run_id, scanned_at=now,
                host="10.80.0.42", port=8080, protocol="SAML",
                cert_pubkey_alg="RSA", cert_pubkey_size=1024,
                service_detail="urn:mh-saml-idp-2|use=signing|serial=deadbeef",
            ),
            # --- Two healthy, non-identity TLS endpoints (real certs) ---
            _CryptoEndpoint(
                scan_run_id=scan_run_id, scanned_at=now,
                host="10.80.0.50", port=443, protocol="TLS",
                cert_subject="CN=svc1.example.com", cert_issuer="CN=Example CA",
                cert_pubkey_alg="ECDSA", cert_pubkey_size=256,
                cert_not_after=_datetime(2030, 1, 1),
                tls_supported_versions="TLSv1.3",
            ),
            _CryptoEndpoint(
                scan_run_id=scan_run_id, scanned_at=now,
                host="10.80.0.51", port=443, protocol="TLS",
                cert_subject="CN=svc2.example.com", cert_issuer="CN=Example CA",
                cert_pubkey_alg="ECDSA", cert_pubkey_size=256,
                cert_not_after=_datetime(2030, 1, 1),
                tls_supported_versions="TLSv1.3",
            ),
            # --- D-16 coverage rows (228-07). COVERAGE, NOT DETECTION: this
            # fixture's SAML CRITICAL ceiling masks HIGH-count differences
            # (measured 30 vs 30 across the old and new compositions), so
            # `test_xsurf0508_no_critical_cross_surface_parity` is the
            # detector for XSURF-05/06/08 (D-28 supersedes D-16 here;
            # RESEARCH Pitfall 1).
            # Near-expiry: wall clock + 10 days. scanned_at is the wall clock
            # too (see `now` above), so evidence.py (scanned_at-relative) and
            # both finding generators (wall-clock-relative) agree this cert is
            # expiring within 30 days on every date the suite runs.
            _CryptoEndpoint(
                scan_run_id=scan_run_id, scanned_at=now,
                host="10.80.0.52", port=443, protocol="TLS",
                cert_subject="CN=soon.example.com", cert_issuer="CN=Example CA",
                cert_pubkey_alg="ECDSA", cert_pubkey_size=256,
                cert_not_after=_datetime.now(_timezone.utc) + _timedelta(days=10),
                tls_supported_versions="TLSv1.3",
            ),
            _CryptoEndpoint(
                scan_run_id=scan_run_id, scanned_at=now,
                host="10.80.0.53", port=995, protocol="SMIME",
                cert_pubkey_alg="RSA", cert_pubkey_size=1024,
            ),
            _CryptoEndpoint(
                scan_run_id=scan_run_id, scanned_at=now,
                host="10.80.0.54", port=25, protocol="SMTP-STARTTLS",
                tls_blocker_reason="CONNECTION_REFUSED", tls_version="",
                service_detail="SMTP-STARTTLS:25",
            ),
            _CryptoEndpoint(
                scan_run_id=scan_run_id, scanned_at=now,
                host="10.80.0.54", port=465, protocol="SMTPS",
                tls_blocker_reason="TIMEOUT", tls_version="",
                service_detail="SMTPS:465",
            ),
        ]
        for row in rows:
            db.add(row)
        db.commit()
    finally:
        db.close()


def test_xsurf04_three_number_cross_surface_equality():
    """XSURF-04 / D-14: for ONE scan_run_id, the report pipeline and the
    dashboard's GET /api/scan/latest?scan_id= agree on headline score,
    CRITICAL finding count, and certificate count — each asserted
    separately with a diagnostic naming which number diverged.

    What would make this fail: a future regression that reintroduces a
    double-count at either of the two XSURF-01/03 dedupe sites (see the
    "Falsification" section of 210-05-SUMMARY.md for the two demonstrated
    reproductions), OR any change that makes the report pipeline and the
    dashboard pipeline diverge on the SAME persisted scan_run_id for any
    other reason.
    """
    client, TestingSession = _xsurf04_make_client_and_session()
    _xsurf04_seed_scan_run(TestingSession, _XSURF04_RUN_ID)

    # --- Surface A: report pipeline, computed directly over the persisted rows ---
    db = TestingSession()
    try:
        endpoints_a = (
            db.query(_CryptoEndpoint)
            .filter(_CryptoEndpoint.scan_run_id == _XSURF04_RUN_ID)
            .all()
        )
    finally:
        db.close()

    findings_a = _derive_report_findings(endpoints_a)
    evidence_a = _build_evidence_summary(endpoints_a, findings_a)
    score_raw_a = _compute_readiness_score(evidence_a, profile=None)

    headline_score_a = score_raw_a["score"]
    critical_count_a = evidence_a["finding_severity_counts"].get("CRITICAL", 0)
    # Mirrors quirk/dashboard/api/routes/scan.py::_is_real_cert_endpoint verbatim
    # (host TLS row with a cert_subject and no scan_error) — the same rule the
    # dashboard's `certificates` list applies, computed independently here
    # over the report pipeline's own endpoint set rather than imported, so a
    # divergence in that predicate itself would also be caught.
    cert_count_a = sum(
        1 for ep in endpoints_a
        if (ep.protocol or "").upper() == "TLS" and ep.cert_subject and not ep.scan_error
    )

    # Non-vacuity (the most important check in this test): two pipelines that
    # both report zero are trivially "equal" and prove nothing.
    assert critical_count_a >= 1, (
        f"XSURF-04 non-vacuity: report-pipeline CRITICAL count is {critical_count_a}, "
        "expected >= 1 from the seeded SAML weak-key fixture."
    )
    assert cert_count_a >= 1, (
        f"XSURF-04 non-vacuity: report-pipeline certificate count is {cert_count_a}, "
        "expected >= 1 from the seeded TLS rows."
    )

    # --- Surface B: dashboard pipeline, via the live route ---
    resp = client.get(f"/api/scan/latest?scan_id={_XSURF04_RUN_ID}")
    assert resp.status_code == 200, (
        f"XSURF-04: GET /api/scan/latest?scan_id={_XSURF04_RUN_ID} expected 200, "
        f"got {resp.status_code} ({resp.text[:300]})"
    )
    data = resp.json()

    headline_score_b = data["score"]["score"]
    critical_count_b = sum(1 for f in data["findings"] if f.get("severity") == "CRITICAL")
    cert_count_b = len(data["certificates"])

    assert critical_count_b >= 1, (
        f"XSURF-04 non-vacuity: dashboard-pipeline CRITICAL count is {critical_count_b}, "
        "expected >= 1 from the seeded SAML weak-key fixture."
    )
    assert cert_count_b >= 1, (
        f"XSURF-04 non-vacuity: dashboard-pipeline certificate count is {cert_count_b}, "
        "expected >= 1 from the seeded TLS rows."
    )

    # --- The three named equality assertions (D-14) ---
    assert headline_score_a == headline_score_b, (
        f"XSURF-04 VIOLATION: headline score diverged across surfaces. "
        f"report={headline_score_a} dashboard={headline_score_b}"
    )
    assert critical_count_a == critical_count_b, (
        f"XSURF-04 VIOLATION: CRITICAL finding count diverged across surfaces. "
        f"report={critical_count_a} dashboard={critical_count_b}"
    )
    assert cert_count_a == cert_count_b, (
        f"XSURF-04 VIOLATION: certificate count diverged across surfaces. "
        f"report={cert_count_a} dashboard={cert_count_b}"
    )

    # --- Pinned-oracle widening (D-15 Task 2 finding) ---
    # A==B alone is insensitive to a regression inside a function BOTH
    # surfaces call identically in-process (see the constants' docstring
    # above). Pin the correct value independently so a reintroduced
    # double-count trips even when it moves both surfaces together.
    assert score_raw_a["subscores"]["data_in_motion"] is None and data["score"]["subscores"]["data_in_motion"] is None, (
        "XSURF-08 VIOLATION: refused/timed-out mail rows must leave Data in Motion unassessed"
    )
    assert critical_count_a == _EXPECTED_XSURF04_CRITICAL_COUNT, (
        f"XSURF-04 VIOLATION: report-pipeline CRITICAL count is "
        f"{critical_count_a}, expected exactly {_EXPECTED_XSURF04_CRITICAL_COUNT} "
        "for this fixture (1 deduped same-serial SAML pair + 1 distinct-serial "
        "SAML row). A higher count means evaluate_identity_endpoints's "
        "(host, port, serial) dedupe (D-01) was not applied."
    )
    assert cert_count_a == _EXPECTED_XSURF04_CERT_COUNT, (
        f"XSURF-04 VIOLATION: certificate count is {cert_count_a}, expected "
        f"exactly {_EXPECTED_XSURF04_CERT_COUNT} for this fixture's two "
        "healthy TLS rows + the 228-07 near-expiry TLS row."
    )
    assert evidence_a["saml_weak_signing_count"] == _EXPECTED_XSURF04_SAML_WEAK_SIGNING_COUNT, (
        f"XSURF-04 VIOLATION: build_evidence_summary's saml_weak_signing_count "
        f"is {evidence_a['saml_weak_signing_count']}, expected exactly "
        f"{_EXPECTED_XSURF04_SAML_WEAK_SIGNING_COUNT}. A higher count means "
        "quirk/intelligence/evidence.py's _seen_saml_certs dedupe (D-03) was "
        "not applied — this is checked directly because neither of the three "
        "surfaced numbers above is guaranteed sensitive to this specific site "
        "(see 210-05-SUMMARY.md Falsification section)."
    )


# ---------------------------------------------------------------------------
# Phase 228 Plan 07 -- no-CRITICAL seeded run (XSURF-05, XSURF-06, XSURF-08)
#
# Why a second scan: the XSURF-04 fixture's SAML CRITICAL ceiling caps both
# surfaces to the same displayed score and the same HIGH count, so it cannot
# detect a HIGH-count or non-TLS-cert divergence (RESEARCH Pitfall 1; D-28).
# This scan has no CRITICAL, so the headline moves with every HIGH finding.
# ---------------------------------------------------------------------------

_XSURF0508_RUN_ID = "2026-10-15T11:00:00"

# Each pin is MEASURED after the 228 fix and independently re-derived in
# 228-07-SUMMARY.md. `a == b` alone is blind: before the fix the report path
# scored 74 and the dashboard 61, but a regression that moves BOTH surfaces
# (e.g. one shared helper counting a refused mail port as plaintext) keeps
# a == b true. The literals are what catch that.
# Scoring 4.0 (Phase 234): 73 -> 76, absolute-count curve; both surfaces moved together.
_EXPECTED_XSURF0508_SCORE = 76
# HIGH count: SMIME RSA-1024 is NOT a TLS cert row (D-05) so it must add no
# HIGH; near-expiry is MEDIUM (D-01), not HIGH; refused/timeout mail rows add
# no finding (D-14).
_EXPECTED_XSURF0508_HIGH_COUNT = 0
# The no-PQC-key-exchange cap applies (computed 91 -> displayed 76 under
# scoring 4.0, Phase 234; was computed 87 -> displayed 73 on 3.0); a
# CRITICAL-ceiling reason here would mean a CRITICAL leaked in.
_EXPECTED_XSURF0508_CAP_REASON = (
    "no post-quantum key exchange observed \u2014 score limited to 76 (computed 91)"
)
# Lift for the `high-impact-findings` slug; None == slug absent.
_EXPECTED_XSURF0508_HIGH_IMPACT_LIFT = None


def _xsurf0508_seed_scan_run(TestingSession, scan_run_id: str) -> None:
    from quirk.scanner.email_scanner import EMAIL_PORTS

    db = TestingSession()
    try:
        now = _datetime.now()
        wall = _datetime.now(_timezone.utc)
        rows = []
        for i, host in enumerate(("10.81.0.10", "10.81.0.11")):
            rows.append(_CryptoEndpoint(
                scan_run_id=scan_run_id, scanned_at=now,
                host=host, port=443, protocol="TLS",
                tls_version="TLSv1.3", cipher_suite="TLS_AES_256_GCM_SHA384",
                cert_subject=f"CN=ok{i}.example.com", cert_issuer="CN=Example CA",
                cert_pubkey_alg="RSA", cert_pubkey_size=2048,
                cert_not_after=wall + _timedelta(days=365),
                tls_supported_versions="TLSv1.3",
            ))
        rows.append(_CryptoEndpoint(
            scan_run_id=scan_run_id, scanned_at=now,
            host="10.81.0.12", port=443, protocol="TLS",
            tls_version="TLSv1.3", cipher_suite="TLS_AES_256_GCM_SHA384",
            cert_subject="CN=soon.example.com", cert_issuer="CN=Example CA",
            cert_pubkey_alg="RSA", cert_pubkey_size=2048,
            cert_not_after=wall + _timedelta(days=10),
            tls_supported_versions="TLSv1.3",
        ))
        rows.append(_CryptoEndpoint(
            scan_run_id=scan_run_id, scanned_at=now,
            host="10.81.0.13", port=995, protocol="SMIME",
            cert_pubkey_alg="RSA", cert_pubkey_size=1024,
        ))
        for n, (port, label, _prefix, _enum) in enumerate(EMAIL_PORTS):
            rows.append(_CryptoEndpoint(
                scan_run_id=scan_run_id, scanned_at=now,
                host="10.81.0.14", port=port, protocol=label,
                tls_blocker_reason="CONNECTION_REFUSED" if n % 2 == 0 else "TIMEOUT",
                tls_version="", service_detail=f"{label}:{port}",
            ))
        for row in rows:
            db.add(row)
        db.commit()
    finally:
        db.close()


def test_xsurf0508_no_critical_cross_surface_parity():
    """XSURF-05/06/08 (D-16, D-28): one no-CRITICAL scan, report path vs
    GET /api/scan/latest, every number pinned to a literal."""
    from quirk.dashboard.api.routes.scan import lift_context_for_scan
    from quirk.intelligence.roadmap import build_phased_roadmap
    from quirk.intelligence.score_lift import compute_item_lifts

    client, TestingSession = _xsurf04_make_client_and_session()
    _xsurf0508_seed_scan_run(TestingSession, _XSURF0508_RUN_ID)

    db = TestingSession()
    try:
        endpoints_a = (
            db.query(_CryptoEndpoint)
            .filter(_CryptoEndpoint.scan_run_id == _XSURF0508_RUN_ID).all()
        )
        findings_a = _derive_report_findings(endpoints_a)
        evidence_a = _build_evidence_summary(endpoints_a, findings_a)
        score_a = _compute_readiness_score(evidence_a, profile=None)
        roadmap_a = build_phased_roadmap(evidence_a, score_a)
        lifts_a = compute_item_lifts(evidence_a, roadmap_a.get("items", []), profile=None)
        lifts_b = lift_context_for_scan(db, _XSURF0508_RUN_ID)
    finally:
        db.close()

    resp = client.get(f"/api/scan/latest?scan_id={_XSURF0508_RUN_ID}")
    assert resp.status_code == 200, resp.text[:300]
    data = resp.json()
    score_b = data["score"]
    findings_b = data["findings"]

    high_a = evidence_a["finding_severity_counts"].get("HIGH", 0)
    high_b = sum(1 for f in findings_b if f.get("severity") == "HIGH")
    crit_a = evidence_a["finding_severity_counts"].get("CRITICAL", 0)
    crit_b = sum(1 for f in findings_b if f.get("severity") == "CRITICAL")

    assert score_a["score"] == score_b["score"] == _EXPECTED_XSURF0508_SCORE, (
        f"XSURF-05/06/08 VIOLATION: headline report={score_a['score']} "
        f"dashboard={score_b['score']} expected={_EXPECTED_XSURF0508_SCORE}"
    )
    assert crit_a == crit_b == 0, (
        f"XSURF-05 VIOLATION: fixture must be CRITICAL-free; report={crit_a} dashboard={crit_b}"
    )
    assert high_a == high_b == _EXPECTED_XSURF0508_HIGH_COUNT, (
        f"XSURF-05/06 VIOLATION: HIGH count report={high_a} dashboard={high_b} "
        f"expected={_EXPECTED_XSURF0508_HIGH_COUNT}"
    )
    assert score_a["rating_cap_reason"] == score_b["rating_cap_reason"] == _EXPECTED_XSURF0508_CAP_REASON, (
        f"XSURF-05 VIOLATION: rating_cap_reason report={score_a['rating_cap_reason']!r} "
        f"dashboard={score_b['rating_cap_reason']!r}"
    )
    assert score_a["subscores"]["data_in_motion"] is None, (
        "XSURF-08 VIOLATION: report Data in Motion must be unassessed (refused/timed-out mail ports)"
    )
    assert score_b["subscores"]["data_in_motion"] is None, (
        "XSURF-08 VIOLATION: dashboard Data in Motion must be unassessed (refused/timed-out mail ports)"
    )

    # (5) near-expiry is MEDIUM on both surfaces
    near_b = [f for f in findings_b if "Certificate expiring in" in (f.get("title") or "")]
    near_a = [f for f in findings_a if "TLS certificate expiring within 30 days" in str(f.get("title", ""))]
    assert near_a and near_b, "XSURF-05 non-vacuity: near-expiry finding missing on a surface"
    assert {f["severity"] for f in near_a} == {"MEDIUM"}, "XSURF-05 VIOLATION: report near-expiry not MEDIUM"
    assert {f["severity"] for f in near_b} == {"MEDIUM"}, "XSURF-05 VIOLATION: dashboard near-expiry not MEDIUM"

    # (6) no dashboard finding on the SMIME row
    smime_b = [f for f in findings_b if f.get("host") == "10.81.0.13"]
    assert smime_b == [], f"XSURF-06 VIOLATION: dashboard emitted TLS findings on an S/MIME row: {smime_b}"

    # (7) lift badges
    assert lifts_b == lifts_a, f"SC#2 VIOLATION: dashboard lifts {lifts_b} != report lifts {lifts_a}"
    assert lifts_b.get("high-impact-findings") == _EXPECTED_XSURF0508_HIGH_IMPACT_LIFT, (
        f"SC#2: high-impact-findings lift {lifts_b.get('high-impact-findings')!r}, "
        f"expected {_EXPECTED_XSURF0508_HIGH_IMPACT_LIFT!r}; all lifts {lifts_b}"
    )


# ---------------------------------------------------------------------------
# Phase 228 Plan 07 -- XSURF-07: every trend / timeline / merge / segment /
# compare score equals the dashboard headline for the same scan.
# ---------------------------------------------------------------------------

_XSURF07_RUN_ID = "2026-10-15T12:00:00"

# Headline for the XSURF-07 fixture (3 healthy + 1 expired-cert TLS row). The
# expired cert is CRITICAL, so the consequence ceiling caps it at <= 34. Before
# the fix trends/timeline/merge scored the same rows with NO findings and
# showed ~78+ -- the surfaces disagreed with the headline by 40+ points, but a
# bare a == b between two findings-less surfaces would never see it.
# Scoring 4.0 (Phase 234): 32 -> 33, still capped <= 34 by the CRITICAL ceiling.
_EXPECTED_XSURF07_HEADLINE = 33
# seg-a holds the expired row; seg-b is healthy so it is NOT capped.
# Scoring 4.0 (Phase 234): seg-a 31 -> 33, still capped <= 34.
_EXPECTED_XSURF07_SEG_A = 33
_EXPECTED_XSURF07_SEG_B = 100
# /compare side B (the XSURF-04 SAML-CRITICAL scan): identity findings must be
# included (D-23), which caps it at 30 (the XSURF-04 headline under scoring 4.0, Phase 234;
# 31 after the 228-07 coverage rows on 3.0, 32 before).
_EXPECTED_XSURF07_COMPARE_B = 30


def _xsurf07_seed(TestingSession):
    db = TestingSession()
    try:
        # Phase 229 D-09: the timeline resolves sessions by scan_run_id, so a
        # microsecond stamp is visible to /api/trends/timeline (the old
        # whole-second workaround is no longer required).
        now = _datetime.now()
        wall = _datetime.now(_timezone.utc)

        def _ep(host, sensor, seg, not_after):
            return _CryptoEndpoint(
                scan_run_id=_XSURF07_RUN_ID, scanned_at=now,
                host=host, port=443, protocol="TLS", segment=seg, sensor_id=sensor,
                service_detail="pqc-hybrid-detected",
                tls_version="TLSv1.3", cipher_suite="TLS_AES_256_GCM_SHA384",
                tls_weak_ciphers_present=False, tls_legacy_suites_present=False,
                cert_pubkey_alg="ECDSA", cert_pubkey_size=256,
                cert_not_after=not_after, cert_subject=f"CN={host}",
                cert_issuer="CN=CA", tls_supported_versions="TLSv1.3",
            )

        good = wall + _timedelta(days=200)
        # One endpoint per sensor_id so _assemble_union keeps every row,
        # including the CRITICAL one (Pitfall 6; FIND-13 is Phase 229).
        db.add(_ep("bad.example.com", "s1", "seg-a", wall - _timedelta(days=5)))
        db.add(_ep("a1.example.com", "s2", "seg-a", good))
        db.add(_ep("b1.example.com", "s3", "seg-b", good))
        db.add(_ep("b2.example.com", "s4", "seg-b", good))
        db.commit()
        from quirk.models import MergeRun
        db.add(MergeRun(
            scan_id=_XSURF07_RUN_ID, merged_at=_datetime.now(),
            score=90, endpoint_count=4, sensor_count=4,
        ))
        db.commit()
    finally:
        db.close()


def test_xsurf07_trend_merge_segment_scores_match_headline():
    client, TestingSession = _xsurf04_make_client_and_session()
    _xsurf07_seed(TestingSession)

    head = client.get(f"/api/scan/latest?scan_id={_XSURF07_RUN_ID}").json()["score"]["score"]
    assert head == _EXPECTED_XSURF07_HEADLINE and head <= 34, (
        f"XSURF-07 VIOLATION: headline {head}, expected {_EXPECTED_XSURF07_HEADLINE} (<= 34)"
    )

    trends = client.get("/api/trends").json()
    assert trends["current_score"] == head, (
        f"XSURF-07 VIOLATION: /api/trends current_score {trends['current_score']} != headline {head}"
    )

    tl = client.get("/api/trends/timeline").json()["sessions"]
    assert len(tl) == 1
    # Closes the 228-06 gap: its timeline test only asserted <= 34.
    assert tl[0]["score"] == head, (
        f"XSURF-07 VIOLATION: timeline point {tl[0]['score']} != headline {head}"
    )

    scans = client.get("/api/scans").json()
    assert len(scans) == 1 and scans[0]["score"] == head, (
        f"XSURF-07 VIOLATION: /api/scans score {[s.get('score') for s in scans]} != headline {head}"
    )

    # /api/merge/latest overall is the LIVE recompute over the union, not MergeRun.score (90).
    merge = client.get("/api/merge/latest").json()["merge"]
    assert merge["score"] == head, (
        f"XSURF-07 VIOLATION: merge overall {merge['score']} != headline {head}"
    )
    segs = merge["per_segment_scores"]
    for seg, pinned in (("seg-a", _EXPECTED_XSURF07_SEG_A), ("seg-b", _EXPECTED_XSURF07_SEG_B)):
        seg_head = client.get(
            f"/api/scan/latest?scan_id={_XSURF07_RUN_ID}&segment={seg}"
        ).json()["score"]["score"]
        assert segs[seg] == seg_head == pinned, (
            f"XSURF-07 VIOLATION: segment {seg} merge={segs[seg]} "
            f"segment-filtered headline={seg_head} expected={pinned}"
        )
    assert segs["seg-a"] <= 34, "XSURF-07 VIOLATION: expired cert must cap its segment"


def test_xsurf07_compare_includes_identity_findings():
    """D-23: /compare derives identity findings, so each side equals its headline."""
    client, TestingSession = _xsurf04_make_client_and_session()
    _xsurf04_seed_scan_run(TestingSession, _XSURF04_RUN_ID)
    _xsurf0508_seed_scan_run(TestingSession, _XSURF0508_RUN_ID)

    head_b = client.get(f"/api/scan/latest?scan_id={_XSURF04_RUN_ID}").json()["score"]["score"]
    head_a = client.get(f"/api/scan/latest?scan_id={_XSURF0508_RUN_ID}").json()["score"]["score"]
    resp = client.get(f"/api/compare?a={_XSURF0508_RUN_ID}&b={_XSURF04_RUN_ID}")
    assert resp.status_code == 200, resp.text[:300]
    data = resp.json()
    assert data["scan_b"]["score"] == head_b == _EXPECTED_XSURF07_COMPARE_B and head_b <= 34, (
        f"XSURF-07 VIOLATION: /compare side B {data['scan_b']['score']} headline {head_b} "
        f"expected {_EXPECTED_XSURF07_COMPARE_B} (<= 34)"
    )
    assert data["scan_a"]["score"] == head_a == _EXPECTED_XSURF0508_SCORE, (
        f"XSURF-07 VIOLATION: /compare side A {data['scan_a']['score']} headline {head_a}"
    )
