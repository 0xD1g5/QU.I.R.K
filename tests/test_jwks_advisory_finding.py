"""SECH-05 (D-13/D-25): the JWKS verify-disabled advisory is a HIGH,
score-neutral finding on both pipelines and survives resume."""
from __future__ import annotations

import copy
from unittest.mock import MagicMock

from quirk.compliance import COMPLIANCE_MAP, UNMAPPED_TITLES
from quirk.dashboard.api.routes.scan import findings_for_endpoint
from quirk.engine.findings_evaluator import evaluate_endpoints
from quirk.intelligence.evidence import build_evidence_summary
from quirk.intelligence.scoring import compute_readiness_score
from quirk.models import CryptoEndpoint
from quirk.scanner.jwt_scanner import ADVISORY_JWKS_VERIFY_DISABLED

TITLE = "JWKS fetched with TLS certificate verification disabled"
URL = "https://idp.example.test/.well-known/jwks.json"


def _cfg():
    cfg = MagicMock()
    cfg.scan.ports_tls = []
    return cfg


def _row(**kw) -> CryptoEndpoint:
    base = dict(
        id=1, host=URL, port=443, protocol="ADVISORY", severity="HIGH",
        service_detail=ADVISORY_JWKS_VERIFY_DISABLED,
        scan_error_category="config",
    )
    base.update(kw)
    return CryptoEndpoint(**base)


def test_evaluator_emits_one_high_config_advisory():
    out = evaluate_endpoints(_cfg(), [_row()])
    assert len(out) == 1
    assert out[0]["severity"] == "HIGH"
    assert out[0]["title"] == TITLE
    assert out[0]["category"] == "config_advisory"


def test_dashboard_pipeline_emits_one_high_config_advisory():
    out = findings_for_endpoint(_row())
    assert len(out) == 1
    assert out[0].severity == "HIGH"
    assert out[0].title == TITLE
    assert out[0].category == "config_advisory"


def test_title_is_in_unmapped_titles_and_not_in_map():
    assert TITLE in UNMAPPED_TITLES
    assert TITLE not in COMPLIANCE_MAP


def test_missing_extra_advisory_still_coverage_gap():
    row = _row(service_detail="x", scan_error_category="missing_extra",
               severity="INFO")
    out = evaluate_endpoints(_cfg(), [row])
    assert len(out) == 1
    assert out[0]["category"] == "coverage_gap"
    assert out[0]["severity"] == "INFO"


def test_resume_predicate_keeps_jwt_and_jwks_advisory_only():
    from run_scan import _is_resumed_jwt_row

    assert _is_resumed_jwt_row(_row(protocol="JWT", service_detail=None))
    assert _is_resumed_jwt_row(_row())
    assert not _is_resumed_jwt_row(
        _row(service_detail="other", scan_error_category="missing_extra"))
    assert not _is_resumed_jwt_row(_row(protocol="TLS"))


def _plain_endpoints():
    return [CryptoEndpoint(id=9, host="h", port=443, protocol="TLS")]


def _score(findings):
    ev = build_evidence_summary(endpoints=_plain_endpoints(), findings=findings)
    return ev, compute_readiness_score(copy.deepcopy(ev))


def test_score_neutral_end_to_end_both_pipelines():
    base_ev, base_score = _score([])
    cli = evaluate_endpoints(_cfg(), [_row()])
    dash = [f.model_dump() for f in findings_for_endpoint(_row())]
    for findings in (cli, dash):
        ev, score = _score(findings)
        assert ev["finding_severity_counts"]["HIGH"] == (
            base_ev["finding_severity_counts"].get("HIGH", 0) + 1)
        assert ev["totals"]["findings"] == base_ev["totals"]["findings"] + 1
        assert ev["scored_finding_severity_counts"] == (
            base_ev["scored_finding_severity_counts"])
        assert score == base_score
