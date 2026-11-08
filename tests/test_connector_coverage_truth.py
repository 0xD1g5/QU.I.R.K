"""Phase 235.3 plan 01 (COVTRUTH-01/02): the connector outcome classifier.

Drives the REAL importable helpers in ``run_scan`` and a real
``_PhaseRecorder`` (no hand-mirrored closure copy), in the style of
tests/test_missing_binary_skip.py.
"""
from __future__ import annotations

import run_scan
from quirk.models import CryptoEndpoint
from quirk.scanner.target_outcome import (
    OUTCOME_ANSWERED, OUTCOME_AUTH_FAILED, OUTCOME_MISSING_CREDENTIALS,
    OUTCOME_REFUSED, OUTCOME_TO_SKIP_REASON, OUTCOME_UNREACHABLE,
    TargetOutcomes,
)

LABEL = "x_scanner"


def _run(outcomes, rows=None, eps=None):
    rec = run_scan._PhaseRecorder()
    eps = [] if eps is None else eps
    rows = [] if rows is None else rows
    result = run_scan._classify_connector_outcomes(LABEL, outcomes, rows, eps, rec)
    return result, rec, eps, rows


def _advisories(eps):
    return [e for e in eps if e.protocol == "ADVISORY"]


def test_classifier_all_refused_skips_with_policy_detail():
    o = TargetOutcomes(["http://a:1/x", "http://b:2/y"])
    for t in o.expected:
        o.record(t, OUTCOME_REFUSED, "loopback")
    result, rec, eps, _ = _run(o)
    assert result is run_scan._PHASE_SKIPPED
    assert rec._pending_reason == "internal-target-refused"
    d = rec._pending_detail
    assert "http://a:1/x" in d and "http://b:2/y" in d
    assert "security.allow_internal_targets" in d and "config.yaml" in d
    adv = _advisories(eps)
    assert len(adv) == 1 and adv[0].scan_error_category == "internal_target_refused"


def test_classifier_all_unreachable():
    o = TargetOutcomes(["a", "b"])
    o.record("a", OUTCOME_UNREACHABLE, "x")
    o.record("b", OUTCOME_UNREACHABLE, "y")
    result, rec, eps, _ = _run(o)
    assert result is run_scan._PHASE_SKIPPED
    assert rec._pending_reason == "failed"
    assert _advisories(eps)[0].scan_error_category == "targets_unreachable"


def test_classifier_mixed_missing_credentials_wins():
    o = TargetOutcomes(["a", "b"])
    o.record("a", OUTCOME_MISSING_CREDENTIALS, "no creds")
    o.record("b", OUTCOME_UNREACHABLE, "down")
    result, rec, _, _ = _run(o)
    assert result is run_scan._PHASE_SKIPPED
    assert rec._pending_reason == "missing-credentials"
    assert "a (missing_credentials" in rec._pending_detail
    assert "b (unreachable" in rec._pending_detail


def test_classifier_all_auth_failed():
    o = TargetOutcomes(["a"])
    o.record("a", OUTCOME_AUTH_FAILED, "bad key")
    result, rec, eps, _ = _run(o)
    assert result is run_scan._PHASE_SKIPPED
    assert rec._pending_reason == "auth-failed"
    assert _advisories(eps)[0].scan_error_category == "auth_failed"


def test_classifier_partial_answer_runs_with_one_error_row_no_advisory():
    o = TargetOutcomes(["a", "b"])
    o.answered("a")
    o.record("b", OUTCOME_REFUSED, "loopback")
    rows: list = []
    result, rec, eps, _ = _run(o, rows=rows)
    assert result is rows
    assert rec._pending_reason is None
    assert _advisories(eps) == []
    assert len(eps) == 1
    assert eps[0].protocol == "ERROR" and eps[0].host == "b"
    assert eps[0].scan_error_category == "target_unanswered"


def test_classifier_row_emitted_adds_no_extra_row():
    o = TargetOutcomes(["a", "b"])
    o.answered("a")
    o.record("b", OUTCOME_UNREACHABLE, "x", row_emitted=True)
    result, _, eps, rows = _run(o)
    assert result is rows and eps == []


def test_classifier_answered_with_nothing_stays_ran():
    o = TargetOutcomes(["a"])
    o.answered("a")
    rows: list = []
    result, rec, eps, _ = _run(o, rows=rows)
    assert result is rows and result == []
    assert eps == [] and rec._pending_reason is None


def test_classifier_unrecorded_target_fails_closed():
    o = TargetOutcomes(["a"])
    result, rec, _, _ = _run(o)
    assert result is run_scan._PHASE_SKIPPED
    assert rec._pending_reason == "failed"
    assert "no outcome recorded by scanner" in rec._pending_detail


def test_classifier_keeps_in_band_rows_when_skipped():
    o = TargetOutcomes(["a"])
    o.record("a", OUTCOME_UNREACHABLE, "x", row_emitted=True)
    inband = CryptoEndpoint(host="a", port=0, protocol="ERROR", scan_error="x",
                            scan_error_category="exception")
    eps = [inband]
    result, _, eps, _ = _run(o, eps=eps)
    assert result is run_scan._PHASE_SKIPPED
    assert inband in eps and len(eps) == 2


def test_classifier_forwards_returned_in_band_rows_when_skipped():
    """235.3-11 P-08: _wrapped_phase discards a skipped phase's return value,
    so the scanner's own error rows must be forwarded into error_endpoints."""
    o = TargetOutcomes(["a"])
    o.record("a", OUTCOME_UNREACHABLE, "x", row_emitted=True)
    inband = CryptoEndpoint(host="a", port=0, protocol="ERROR", scan_error="conn",
                            scan_error_category="exception")
    clean = CryptoEndpoint(host="a", port=1, protocol="TLS")
    result, _, eps, _ = _run(o, rows=[inband, clean])
    assert result is run_scan._PHASE_SKIPPED
    assert inband in eps and clean not in eps


def test_classifier_detail_caps_names_and_redacts():
    raws = [f"http://user:pw@h{i}:1/p?tok=secret{i}" for i in range(7)]
    o = TargetOutcomes(raws)
    for r in raws:
        o.record(r, OUTCOME_REFUSED, "loopback")
    _, rec, eps, _ = _run(o)
    d = rec._pending_detail
    assert "and 2 more" in d
    assert d.count("(refused") == 5
    assert "://user:" not in d and "?tok" not in d
    assert "://user:" not in eps[0].scan_error


def test_classifier_every_mapped_reason_accepted_by_real_recorder():
    for reason in OUTCOME_TO_SKIP_REASON.values():
        assert run_scan._PhaseRecorder().skip(reason, "d") is run_scan._PHASE_SKIPPED


def test_classifier_collision_guard_shared_64_char_prefix():
    a = "https://login.example.com/" + "t" * 60 + "/discovery/keys"
    b = "https://login.example.com/" + "t" * 60 + "/discovery/v2.0/keys"
    o = TargetOutcomes([a, b])
    o.answered(a)
    o.record(b, OUTCOME_UNREACHABLE, "down")
    rows: list = []
    result, _, eps, _ = _run(o, rows=rows)
    assert result is rows
    assert len(eps) == 1
    assert eps[0].host == o.labels[b]
    assert eps[0].scan_error_category == "target_unanswered"


def test_contract_error_in_production_records_failed_with_error_row():
    rec = run_scan._PhaseRecorder()
    stats = {"phase_records": rec, "timings_sec": {}}
    eps: list = []

    class _Log:
        def error(self, *_a, **_k):
            pass

    def fn():
        o = TargetOutcomes(["a"])
        o.record("b", OUTCOME_ANSWERED)
        return []

    out = run_scan._wrapped_phase(stats, "x_scanning", LABEL, fn, eps, _Log())
    assert out == []
    row = rec.rows()[-1]
    assert row["status"] == "skipped" and row["reason"] == "failed"
    assert len(eps) == 1 and eps[0].protocol == "ERROR"
    assert eps[0].scan_error_category == "exception"


# ---------------------------------------------------------------------------
# D-07 (235.1 D-07 rule): each skip reason lowers the score through the real pipeline
# ---------------------------------------------------------------------------

import pytest  # noqa: E402


@pytest.mark.parametrize(
    "reason", ["internal-target-refused", "auth-failed", "missing-credentials", "failed"]
)
def test_coverage_skip_advisory_lowers_score_through_real_pipeline(reason, capsys):
    """Baseline is an ANSWERED-EMPTY connector (contributes nothing to evidence).

    Against a connector that ran and found weak keys a skip may score
    differently (RESEARCH Pitfall 7); that is outside the D-07 statement.
    Findings come from derive_report_findings and are passed as
    build_evidence_summary(findings=...) before compute_readiness_score.
    """
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
    run_scan._emit_coverage_skip_advisory("jwt_scanner", reason, "detail", adv)
    base_eps, skipped_eps = [tls], [tls] + adv

    def _measure(eps, with_findings):
        findings = derive_report_findings(eps, None) if with_findings else None
        ev = build_evidence_summary(eps, findings=findings)
        return ev, compute_readiness_score(ev)

    results = {}
    for with_findings in (True, False):
        ev0, s0 = _measure(base_eps, with_findings)
        ev1, s1 = _measure(skipped_eps, with_findings)
        assert ev0["scan_error"]["count"] == 0
        assert ev1["scan_error"]["count"] == 1
        assert s1["score"] < s0["score"]
        results[with_findings] = (s0, s1)

    s0, s1 = results[True]
    curve = _count_curve(1)
    w_h = SCORE_WEIGHTS["hygiene_scan_error_rate"]
    w_m = SCORE_WEIGHTS["modern_tls_scan_error_rate"]
    expected = (w_h + w_m) * curve
    assert s1["subscores"]["hygiene"] == round(25 - w_h * curve)
    assert s1["subscores"]["modern_tls"] == round(25 - w_m * curve)
    raw_drop = (25 - s1["subscores"]["hygiene"]) + (25 - s1["subscores"]["modern_tls"])
    assert abs(raw_drop - expected) <= 1.0  # integer rounding of two subscores
    d_with = results[True][0]["score"] - results[True][1]["score"]
    d_without = results[False][0]["score"] - results[False][1]["score"]
    assert d_with == d_without
    with capsys.disabled():
        print(
            f"\n[235.3-09] {reason}: evaluator-inclusive delta {d_with} "
            f"({s0['score']} -> {s1['score']}); endpoint-only delta {d_without}; "
            f"expected subscore delta {expected:.3f}"
        )


# ---------------------------------------------------------------------------
# SC3 / D-07: paired real scans -- JWT skipped vs JWT answered-empty
# ---------------------------------------------------------------------------

import glob  # noqa: E402
import os  # noqa: E402
import re  # noqa: E402

from tests import connector_coverage_harness as _h  # noqa: E402


def _paired_scan(root, tls_port, jwt_url, allow_internal):
    """One in-process scan; the TLS stub is the only TLS target in both scans."""
    root.mkdir()
    cfg_path = _h.build_config(root, {
        "targets": {"include_ips": ["127.0.0.1"]},
        "scan": {"ports_tls": [tls_port]},
        "connectors": {
            "enable_jwt": True, "jwt_targets": [jwt_url],
            "enable_container": False, "enable_source": False,
            "enable_saml": False, "enable_dnssec": False,
            "enable_email": False, "enable_broker": False,
        },
        "security": {"allow_internal_targets": allow_internal},
    })
    from quirk.config import load_config

    db = load_config(cfg_path).output.db_path
    before = _h.quirk_output_snapshot()
    _h.run_scan_in_process(cfg_path, db)
    assert _h.quirk_output_snapshot() == before, "scan wrote into repo quirk-output/"
    rows = {r["phase_name"]: r for r in _h.phase_rows(db)}
    return {
        "root": root, "db": db, "out": root / "out", "rows": rows,
        "scan_run_id": rows["jwt_scanning"]["scan_run_id"],
    }


@pytest.fixture(scope="module")
def answered_empty_pair(tmp_path_factory):
    """Baseline is ANSWERED-EMPTY (RESEARCH Pitfall 7): scan B's JWKS stub
    answers {"keys": []}; scan A's identical URL is refused by policy."""
    base = tmp_path_factory.mktemp("answered_empty_pair")
    mp = pytest.MonkeyPatch()
    try:
        _h.scrub_cloud_env(mp)
        with _h.tls_stub(base) as tls_port, _h.jwks_stub('{"keys": []}') as jwt_url:
            a = _paired_scan(base / "a_skipped", tls_port, jwt_url, False)
            b = _paired_scan(base / "b_answered", tls_port, jwt_url, True)
    finally:
        mp.undo()
    return {"a": a, "b": b, "tls_port": tls_port}


def _tls_set_and_evidence(db, scan_run_id):
    from quirk.db import get_session
    from quirk.intelligence.evidence import build_evidence_summary
    from quirk.intelligence.scoring import compute_readiness_score
    from quirk.models import CryptoEndpoint as Row

    with get_session(db) as s:
        eps = s.query(Row).filter_by(scan_run_id=scan_run_id).all()
        tls = sorted(
            (e.host, e.port, e.tls_version, e.cipher_suite)
            for e in eps if e.protocol == "TLS"
        )
        errs = [e for e in eps if e.scan_error]
        ev = build_evidence_summary(eps)
        score = compute_readiness_score(ev)
    return tls, len(errs), ev, score


@pytest.mark.slow
def test_answered_empty_baseline_estate_identical_and_assessed(answered_empty_pair):
    a, b = answered_empty_pair["a"], answered_empty_pair["b"]
    tls_a, _, _, _ = _tls_set_and_evidence(a["db"], a["scan_run_id"])
    tls_b, _, ev_b, score_b = _tls_set_and_evidence(b["db"], b["scan_run_id"])
    assert tls_a == tls_b and tls_a, "baseline TLS estate must be identical and non-empty"
    assert score_b["score"] is not None
    assert a["rows"]["jwt_scanning"]["status"] == "skipped"
    assert a["rows"]["jwt_scanning"]["reason"] == "internal-target-refused"
    assert b["rows"]["jwt_scanning"]["status"] == "ran"


@pytest.mark.slow
def test_answered_empty_intel_score_skipped_lower(answered_empty_pair):
    a, b = answered_empty_pair["a"], answered_empty_pair["b"]
    _, err_a, _, score_a = _tls_set_and_evidence(a["db"], a["scan_run_id"])
    _, err_b, _, score_b = _tls_set_and_evidence(b["db"], b["scan_run_id"])
    assert err_a == err_b + 1
    assert score_a["score"] < score_b["score"], (score_a["score"], score_b["score"])


def _html_score(out):
    htmls = glob.glob(str(out / "report-*.html"))
    assert len(htmls) == 1
    html = open(htmls[0], encoding="utf-8").read()
    return html


@pytest.mark.slow
def test_answered_empty_html_report_score_and_coverage_row(answered_empty_pair):
    a, b = answered_empty_pair["a"], answered_empty_pair["b"]
    html_a, html_b = _html_score(a["out"]), _html_score(b["out"])
    assert "Scan Coverage" in html_a
    assert "JWT</td><td>skipped</td><td>internal-target-refused (" in html_a
    assert "JWT</td><td>ran</td>" in html_b
    assert "internal-target-refused (" not in html_b

    def _score(html):
        m = re.search(r'<div class="score-value">(\d+)</div>', html)
        assert m, "no score in HTML report"
        return int(m.group(1))

    assert _score(html_a) < _score(html_b)


def _api_client(monkeypatch, db, scan_run_id):
    import datetime

    from sqlalchemy.orm import sessionmaker
    from fastapi.testclient import TestClient

    from quirk.dashboard.api.app import create_app
    from quirk.dashboard.api.deps import get_db
    from quirk.db import get_engine
    from quirk.models import ScanJob

    Session = sessionmaker(bind=get_engine(db), autoflush=False, autocommit=False)
    with Session() as s:
        s.add(ScanJob(
            job_id="job-" + scan_run_id[:8], status="completed", target="127.0.0.1",
            profile="standard", calibration="balanced", scan_run_id=scan_run_id,
            completed_at=datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None),
        ))
        s.commit()

    def _override():
        s = Session()
        try:
            yield s
        finally:
            s.close()

    app = create_app()
    app.dependency_overrides[get_db] = _override
    monkeypatch.setattr("quirk.dashboard.api.routes.scan._default_db_path", lambda: db)
    return TestClient(app, headers={"X-Quirk-Request": "1"})


@pytest.mark.slow
def test_answered_empty_api_scan_latest_score_and_coverage(answered_empty_pair, monkeypatch):
    a, b = answered_empty_pair["a"], answered_empty_pair["b"]
    out = {}
    for key, m in (("a", a), ("b", b)):
        client = _api_client(monkeypatch, m["db"], m["scan_run_id"])
        latest = client.get("/api/scan/latest")
        assert latest.status_code == 200
        body = latest.json()
        cov = client.get(f"/api/scans/{m['scan_run_id']}/coverage").json()
        out[key] = (body, cov)

    body_a, cov_a = out["a"]
    body_b, cov_b = out["b"]
    assert body_a["score"]["score"] is not None
    assert body_a["score"]["score"] < body_b["score"]["score"]
    jwt_a = next(p for p in cov_a["phases"] if p["phase_name"] == "jwt_scanning")
    assert jwt_a["status"] == "skipped" and jwt_a["reason"] == "internal-target-refused"
    assert "security.allow_internal_targets" in jwt_a["detail"]
    latest_jwt = next(
        p for p in body_a["coverage"]["phases"] if p["phase_name"] == "jwt_scanning"
    )
    assert latest_jwt["reason"] == jwt_a["reason"] and latest_jwt["detail"] == jwt_a["detail"]
    jwt_b = next(p for p in body_b["coverage"]["phases"] if p["phase_name"] == "jwt_scanning")
    assert jwt_b["status"] == "ran"
