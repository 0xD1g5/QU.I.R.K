"""DETECT-05 (Phase 230, D-14..D-17, D-15a, D-16a): a bearer token whose JWT
header declares ``alg: none`` (any case) or carries no alg yields one CRITICAL
finding in a scan, on the CLI report and the dashboard alike.

Score treatment (D-15): an ORDINARY CRITICAL. It feeds ``_consequence_ceiling``
like any open CRITICAL (floors the band; ``rating_cap_reason`` names it) with no
score-exclusion special case. ``bearer_token_weak_alg_count`` keeps excluding
"none" and never counts a missing alg, so nothing is double-counted.

The proof walks the real scan path: CredentialContext.from_cli ->
run_scan._bearer_token_endpoints -> derive_report_findings ->
build_evidence_summary -> compute_readiness_score.
"""
from __future__ import annotations

import base64
import copy
import json
from types import SimpleNamespace

import pytest

from quirk.compliance import COMPLIANCE_MAP, UNMAPPED_TITLES
from quirk.auth.credentials import CredentialContext
from quirk.dashboard.api.routes.scan import derive_dashboard_finding_items
from quirk.engine.findings_evaluator import derive_report_findings
from quirk.intelligence.evidence import build_evidence_summary
from quirk.intelligence.scoring import compute_readiness_score

TITLE = "Bearer token is unsigned (alg:none)"
ENV = "QUIRK_T230_BEARER"


def _b64(obj) -> str:
    return base64.urlsafe_b64encode(json.dumps(obj).encode()).rstrip(b"=").decode()


def _token(header) -> str:
    return _b64(header) + "." + _b64({"sub": "t230"}) + ".c2ln"


def _cfg():
    return SimpleNamespace(
        targets=SimpleNamespace(fqdns=["api.example.test"]),
        scan=SimpleNamespace(tls_designated_ports=[], ports_tls=[]),
    )


def _endpoints(monkeypatch, raw):
    from run_scan import _bearer_token_endpoints

    monkeypatch.setenv(ENV, raw)
    ctx = CredentialContext.from_cli(bearer=ENV)
    return _bearer_token_endpoints(ctx, _cfg())


def _findings(eps):
    return derive_report_findings(eps, _cfg())


def _score(eps, findings):
    ev = build_evidence_summary(endpoints=eps, findings=findings)
    return ev, compute_readiness_score(copy.deepcopy(ev))


@pytest.mark.parametrize("alg", ["none", "None", "NONE"])
def test_alg_none_yields_critical_and_moves_ceiling(monkeypatch, alg):
    raw = _token({"alg": alg, "typ": "JWT"})
    eps = _endpoints(monkeypatch, raw)
    assert len(eps) == 1
    assert eps[0].protocol == "BEARER_TOKEN"
    assert eps[0].cert_pubkey_alg == alg
    findings = _findings(eps)
    hits = [f for f in findings if f["title"] == TITLE]
    assert len(hits) == 1 and hits[0]["severity"] == "CRITICAL"
    assert len([f for f in findings if f["severity"] == "CRITICAL"]) == 1
    _, base = _score(eps, [])
    _, score = _score(eps, findings)
    assert "1 open CRITICAL finding" in score["rating_cap_reason"]
    assert "CRITICAL" not in (base.get("rating_cap_reason") or "")
    # T-230-14: the token never reaches endpoint fields or finding text.
    blob = json.dumps([f for f in findings], default=str) + repr(eps[0].__dict__)
    assert raw not in blob


def test_missing_alg_yields_critical(monkeypatch):
    from quirk.util.jwt_alg import BEARER_ALG_ABSENT_MARKER

    raw = _token({"typ": "JWT"})
    eps = _endpoints(monkeypatch, raw)
    assert len(eps) == 1
    assert eps[0].cert_pubkey_alg is None
    assert BEARER_ALG_ABSENT_MARKER in eps[0].service_detail
    findings = _findings(eps)
    hits = [f for f in findings if f["title"] == TITLE]
    assert len(hits) == 1 and hits[0]["severity"] == "CRITICAL"
    assert raw not in json.dumps(findings, default=str)


def test_rs256_no_critical(monkeypatch):
    eps = _endpoints(monkeypatch, _token({"alg": "RS256", "typ": "JWT"}))
    assert len(eps) == 1
    findings = _findings(eps)
    assert not [f for f in findings if f["title"] == TITLE]
    assert not [f for f in findings if f["severity"] == "CRITICAL"]


def test_opaque_token_no_endpoint(monkeypatch):
    assert _endpoints(monkeypatch, "opaque-token-230") == []


@pytest.mark.parametrize("header", [{"alg": "none"}, {"typ": "JWT"}])
def test_dashboard_parity(monkeypatch, header):
    eps = _endpoints(monkeypatch, _token(header))
    items = derive_dashboard_finding_items(eps)
    assert TITLE in [i.title for i in items]
    assert [i.severity for i in items if i.title == TITLE] == ["CRITICAL"]


@pytest.mark.parametrize(
    "header,expected",
    [({"alg": "none"}, 0), ({"typ": "JWT"}, 0), ({"alg": "HS256"}, 1)],
)
def test_no_double_count(monkeypatch, header, expected):
    eps = _endpoints(monkeypatch, _token(header))
    ev, _ = _score(eps, _findings(eps))
    assert ev["bearer_token_weak_alg_count"] == expected


def test_title_is_in_unmapped_titles_and_not_in_map():
    assert TITLE in UNMAPPED_TITLES
    assert TITLE not in COMPLIANCE_MAP


def test_classifier_still_rates_none_level_zero():
    from quirk.cbom.classifier import classify_algorithm

    assert classify_algorithm("none")[1] == 0
