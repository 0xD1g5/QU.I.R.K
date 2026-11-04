"""Phase 235.1 plan 01 (SRCSCAN-01, D-05/D-06/D-07): a configured source or
container scan whose binary (semgrep / syft) is absent is recorded as
``skipped`` / ``missing-binary`` with one counted ``missing_binary`` ADVISORY
row, never as "ran" with zero findings.

Unit tests drive the REAL importable helpers in ``run_scan`` (no hand-mirrored
closure copy). The slow legs run ``run_scan.main()`` in-process against a
temp config/DB (cwd, output.directory, output.db_path and --db-path are all
under tmp) with ``run_scan.shutil.which`` patched so semgrep is absent
regardless of the machine running the test.
"""
from __future__ import annotations

import glob
import os
import shutil
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

import run_scan
from quirk.models import CryptoEndpoint, ScanPhaseRecord

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SEMGREP_DETAIL = "semgrep is not installed (QRK-INSTALL-008)"


def _which_without(*missing):
    """shutil.which stand-in: None for ``missing``, a fake path for everything else."""

    def _which(name, *a, **k):
        return None if name in missing else f"/fake/bin/{name}"

    return _which


# ---------------------------------------------------------------------------
# Gate helper unit tests
# ---------------------------------------------------------------------------


def test_semgrep_absent_returns_detail_and_emits_advisory(monkeypatch, capsys):
    monkeypatch.setattr(run_scan.shutil, "which", _which_without("semgrep"))
    eps: list = []
    detail = run_scan._missing_binary_detail("semgrep", eps)
    assert detail == _SEMGREP_DETAIL
    assert len(eps) == 1
    ep = eps[0]
    assert (ep.host, ep.port, ep.protocol) == ("source_scanner", 0, "ADVISORY")
    assert ep.scan_error == _SEMGREP_DETAIL
    assert ep.scan_error_category == "missing_binary"
    assert "INSTALL-008" in capsys.readouterr().err


def test_syft_absent_independent_of_semgrep(monkeypatch, capsys):
    # Patch BOTH explicitly: this machine has syft but not semgrep (Pitfall 8).
    monkeypatch.setattr(run_scan.shutil, "which", _which_without("syft"))
    eps: list = []
    assert run_scan._missing_binary_detail("semgrep", eps) is None
    assert eps == []
    detail = run_scan._missing_binary_detail("syft", eps)
    assert detail == "syft is not installed (QRK-INSTALL-007)"
    assert [e.host for e in eps] == ["container_scanner"]
    assert "INSTALL-007" in capsys.readouterr().err


def test_binary_present_returns_none_and_appends_nothing(monkeypatch):
    monkeypatch.setattr(run_scan.shutil, "which", _which_without())
    eps: list = []
    assert run_scan._missing_binary_detail("semgrep", eps) is None
    assert run_scan._missing_binary_detail("syft", eps) is None
    assert eps == []


def test_recorder_accepts_missing_binary_reason():
    rec = run_scan._PhaseRecorder()
    assert rec.skip("missing-binary", "x") is run_scan._PHASE_SKIPPED


def test_skip_note_renders_missing_binary():
    from quirk.reports.coverage import format_skip_note

    note = format_skip_note({"reason": "missing-binary", "detail": _SEMGREP_DETAIL})
    assert note == f"Not assessed — skipped: missing-binary ({_SEMGREP_DETAIL})"


# ---------------------------------------------------------------------------
# D-07: the counted advisory moves the score by a measured amount
# ---------------------------------------------------------------------------


def test_missing_binary_advisory_score_delta_is_measured_through_real_pipeline(capsys):
    """D-07 / 212 §8: measured through the real pipeline. Findings come from the
    real evaluator (derive_report_findings, the call run_scan.py makes) and are
    passed as build_evidence_summary(findings=...) before compute_readiness_score.
    The expected subscore delta is read from live scoring constants:
    SCORE_WEIGHTS['hygiene_scan_error_rate'] (6.0) and
    SCORE_WEIGHTS['modern_tls_scan_error_rate'] (5.0) times _count_curve(1)."""
    from quirk.engine.findings_evaluator import derive_report_findings
    from quirk.intelligence.evidence import build_evidence_summary
    from quirk.intelligence.scoring import (
        SCORE_WEIGHTS,
        _count_curve,
        compute_readiness_score,
    )

    tls = CryptoEndpoint(
        host="10.0.0.1", port=443, protocol="TLS",
        tls_version="TLSv1.3", tls_supported_versions="TLSv1.3",
    )
    adv: list = []
    run_scan._emit_missing_binary_advisory("source_scanner", "semgrep", "INSTALL-008", adv)
    base_eps, mb_eps = [tls], [tls] + adv

    def _measure(eps, with_findings):
        findings = derive_report_findings(eps, None) if with_findings else None
        ev = build_evidence_summary(eps, findings=findings)
        return ev, compute_readiness_score(ev)

    results = {}
    for with_findings in (True, False):
        ev0, s0 = _measure(base_eps, with_findings)
        ev1, s1 = _measure(mb_eps, with_findings)
        assert ev0["scan_error"]["count"] == 0
        assert ev1["scan_error"]["count"] == 1
        assert s1["score"] < s0["score"]
        results[with_findings] = (s0, s1)

    s0, s1 = results[True]
    curve = _count_curve(1)
    w_h = SCORE_WEIGHTS["hygiene_scan_error_rate"]
    w_m = SCORE_WEIGHTS["modern_tls_scan_error_rate"]
    expected = (w_h + w_m) * curve
    assert abs(expected - 11.0 * curve) < 0.01  # live weights are 6.0 + 5.0
    # Subscores are rounded ints: each must equal round(25 - weight * curve).
    assert s0["subscores"]["hygiene"] == 25
    assert s1["subscores"]["hygiene"] == round(25 - w_h * curve)
    assert s1["subscores"]["modern_tls"] == round(25 - w_m * curve)
    raw_drop = (25 - s1["subscores"]["hygiene"]) + (25 - s1["subscores"]["modern_tls"])
    assert abs(raw_drop - expected) <= 1.0  # integer rounding of two subscores
    # Endpoint-only and evaluator-inclusive deltas must agree (D-07: the
    # advisory is the only thing that moved; plan 02's INFO finding is neutral).
    assert results[True][0]["score"] - results[True][1]["score"] == \
        results[False][0]["score"] - results[False][1]["score"]
    with capsys.disabled():
        print(
            f"\n[235.1-01] evaluator-inclusive headline {s0['score']} -> {s1['score']} "
            f"(delta {s0['score'] - s1['score']}); endpoint-only "
            f"{results[False][0]['score']} -> {results[False][1]['score']}; "
            f"expected subscore delta {expected:.3f}"
        )


# ---------------------------------------------------------------------------
# Slow end-to-end: a real in-process scan with semgrep absent
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def missing_semgrep_scan(tmp_path_factory):
    """Run run_scan.main() once, in-process, with semgrep absent. Everything
    (cwd, output.directory, output.db_path, --db-path) lives under tmp."""
    root = tmp_path_factory.mktemp("missing_binary_scan")
    src = root / "src"
    src.mkdir()
    out = root / "out"
    db = root / "quirk.db"

    tmpl = os.path.join(_REPO, "quirk", "config_template.yaml")
    text = open(tmpl, encoding="utf-8").read()
    text = text.replace('directory: "./quirk-output"', f'directory: "{out}"')
    text = text.replace('db_path: "./quirk-output/quirk.db"', f'db_path: "{db}"')
    assert str(out) in text and str(db) in text
    text = text.replace("  # source_targets: []", f"  source_targets: ['{src}']")
    assert str(src) in text
    cfg_path = root / "config.yaml"
    cfg_path.write_text(text, encoding="utf-8")

    repo_out = os.path.join(_REPO, "quirk-output")
    before = sorted(os.listdir(repo_out)) if os.path.isdir(repo_out) else None

    mp = pytest.MonkeyPatch()
    try:
        mp.chdir(root)
        mp.setattr(run_scan.shutil, "which", _which_without("semgrep"))
        mp.setattr(sys, "argv", [
            "run_scan.py", "--config", str(cfg_path), "--db-path", str(db),
        ])
        run_scan.main()
    finally:
        mp.undo()

    after = sorted(os.listdir(repo_out)) if os.path.isdir(repo_out) else None
    assert before == after, "scan wrote into the repo's ./quirk-output/"

    from quirk.db import get_session

    with get_session(str(db)) as session:
        rec = session.query(ScanPhaseRecord).filter_by(phase_name="source_scanning").one()
        scan_run_id = rec.scan_run_id
    return {"root": root, "out": out, "db": str(db), "scan_run_id": scan_run_id}


def _phase_row(db, scan_run_id, phase):
    from quirk.db import get_session

    with get_session(db) as session:
        row = (
            session.query(ScanPhaseRecord)
            .filter_by(scan_run_id=scan_run_id, phase_name=phase)
            .one()
        )
        return row.status, row.reason, row.detail


@pytest.mark.slow
def test_e2e_source_phase_recorded_skipped_missing_binary(missing_semgrep_scan):
    from quirk.reports.coverage import load_scan_coverage

    m = missing_semgrep_scan
    assert _phase_row(m["db"], m["scan_run_id"], "source_scanning") == (
        "skipped", "missing-binary", _SEMGREP_DETAIL,
    )
    cov = load_scan_coverage(m["db"], m["scan_run_id"])
    src = next(p for p in cov["phases"] if p["phase_name"] == "source_scanning")
    assert src["status"] != "ran"
    assert src["reason"] == "missing-binary"


@pytest.mark.slow
def test_e2e_html_report_scan_coverage_shows_skipped_missing_binary(missing_semgrep_scan):
    htmls = glob.glob(str(missing_semgrep_scan["out"] / "report-*.html"))
    assert len(htmls) == 1
    html = open(htmls[0], encoding="utf-8").read()
    assert "Scan Coverage" in html
    expected_row = (
        "Source Code</td><td>skipped</td>"
        f"<td>missing-binary ({_SEMGREP_DETAIL})</td>"
    )
    assert expected_row in html
    assert "Source Code</td><td>ran</td>" not in html


@pytest.mark.slow
def test_e2e_api_coverage_and_scan_latest_partial_failures(missing_semgrep_scan, monkeypatch):
    from quirk.dashboard.api.app import create_app
    from quirk.dashboard.api.deps import get_db
    from quirk.db import get_engine

    m = missing_semgrep_scan
    TestingSession = sessionmaker(bind=get_engine(m["db"]), autoflush=False, autocommit=False)

    def _override():
        s = TestingSession()
        try:
            yield s
        finally:
            s.close()

    # /api/scan/latest resolves the checkpoint key through a completed ScanJob
    # (the dashboard-launched path; a bare CLI run writes no ScanJob row, so
    # partial_failures is empty for it by route design -- reported in the
    # 235.1-01 SUMMARY). Seed the row the dashboard would have written.
    import datetime

    from quirk.models import ScanJob

    with TestingSession() as s:
        s.add(ScanJob(
            job_id="job-mb-1", status="completed", target="127.0.0.1",
            profile="standard", calibration="balanced",
            scan_run_id=m["scan_run_id"],
            completed_at=datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None),
        ))
        s.commit()

    app = create_app()
    app.dependency_overrides[get_db] = _override
    monkeypatch.setattr("quirk.dashboard.api.routes.scan._default_db_path", lambda: m["db"])
    client = TestClient(app, headers={"X-Quirk-Request": "1"})

    cov = client.get(f"/api/scans/{m['scan_run_id']}/coverage")
    assert cov.status_code == 200
    src = next(p for p in cov.json()["phases"] if p["phase_name"] == "source_scanning")
    assert src["status"] == "skipped"
    assert src["reason"] == "missing-binary"
    assert src["detail"] == _SEMGREP_DETAIL

    latest = client.get("/api/scan/latest")
    assert latest.status_code == 200
    body = latest.json()
    pf = [e for e in body["partial_failures"] if e["error_category"] == "missing_binary"]
    assert len(pf) == 1, body["partial_failures"]
    assert pf[0]["scanner"] == "source_scanner"
    assert "QRK-INSTALL-008" in pf[0]["error_message"]
    assert not any(
        str(f.get("protocol", "")).upper() == "SOURCE" for f in body["findings"]
    )
