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
