"""Phase 228 plan 01: shared TLS-check predicate + report finding composer.

Pins ``derive_report_findings`` to the five-call composition that
``run_scan.py``'s ``risk_engine`` block used before Phase 228 D-25, so the
report stays byte-identical, and stops the five calls being re-inlined.
"""
from __future__ import annotations

import ast
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from quirk.engine import findings_evaluator as fe
from quirk.engine.findings_evaluator import (
    EMAIL_PROTOCOLS,
    derive_report_findings,
    evaluate_broker_endpoints,
    evaluate_codesign_endpoints,
    evaluate_email_endpoints,
    evaluate_endpoints,
    evaluate_identity_endpoints,
    evaluate_protocol_service_endpoints,
    runs_tls_certificate_checks,
)
from quirk.models import CryptoEndpoint

RUN_SCAN = Path(__file__).resolve().parent.parent / "run_scan.py"
WEAK = "TLS_RSA_WITH_AES_128_CBC_SHA"


def _cfg():
    return SimpleNamespace(scan=SimpleNamespace(tls_designated_ports=[]))


def _ep(protocol, host="h.example", port=443, **kw):
    return CryptoEndpoint(host=host, port=port, protocol=protocol, **kw)


def _titles(findings):
    return [(f.get("title"), f.get("severity"), f.get("host"), f.get("port")) for f in findings]


def _fixture():
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    return [
        _ep("TLS", host="tls.example", port=443, tls_version="TLSv1.2",
            cipher_suite=WEAK, cert_not_after=now + timedelta(days=5),
            cert_subject="CN=tls.example"),
        _ep("SMTPS", host="mail.example", port=465, tls_version="TLSv1.2", cipher_suite=WEAK),
        _ep("SMTP-STARTTLS", host="mail.example", port=25, tls_version="TLSv1.2",
            cipher_suite="TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384"),
        _ep("KAFKA-PLAIN", host="k.example", port=9092),
        _ep("KAFKA-TLS", host="k.example", port=9093, tls_version="TLSv1.2"),
        _ep("CODE_SIGNING", host="cs.example", port=0,
            cert_subject="CN=signer", cert_not_after=now - timedelta(days=3),
            codesign_scan_json=json.dumps({"reasons": ["expired"]})),
        _ep("SAML", host="idp.example", port=443, service_detail="SAML"),
        _ep("SMIME", host="sm.example", port=0, cert_subject="CN=sm"),
        _ep("VAULT", host="v.example", port=8200),
    ]


def _old_composition(cfg, eps):
    """The pre-Phase-228 run_scan.py five-call composition (the oracle)."""
    email = [e for e in eps if e.protocol in ("SMTP-STARTTLS", "SMTPS", "IMAP-STARTTLS",
                                              "IMAPS", "POP3-STARTTLS", "POP3S")]
    codesign = [e for e in eps if e.protocol == "CODE_SIGNING"]
    saml = [e for e in eps if e.protocol == "SAML"]
    findings = evaluate_endpoints(cfg, eps)
    for extra in (
        evaluate_email_endpoints(email),
        evaluate_broker_endpoints(eps),
        evaluate_codesign_endpoints(codesign),
        evaluate_identity_endpoints(saml),
    ):
        if extra:
            findings = (findings or []) + extra
    return findings


@pytest.mark.parametrize("proto,expected", [
    ("TLS", True), ("tls", False), ("SMTPS", False), ("SMIME", False), ("ADCS", False),
    ("VAULT", False), ("CODE_SIGNING", False), ("JWT", False), (None, False),
])
def test_runs_tls_certificate_checks(proto, expected):
    assert runs_tls_certificate_checks(_ep(proto)) is expected


def test_email_protocols_matches_scanner_table():
    from quirk.scanner import email_scanner
    assert EMAIL_PROTOCOLS == frozenset(row[1] for row in email_scanner.EMAIL_PORTS)


def test_partition_keeps_tls_rows_out_of_email_evaluator():
    plain_tls = _ep("TLS", tls_version="TLSv1.2", cipher_suite=WEAK)
    smtps = _ep("SMTPS", port=465, tls_version="TLSv1.2", cipher_suite=WEAK)
    title = "Weak cipher suite on email TLS endpoint"
    assert title not in [f["title"] for f in evaluate_protocol_service_endpoints([plain_tls])]
    assert title in [f["title"] for f in evaluate_protocol_service_endpoints([smtps])]


def test_partition_routes_broker_and_codesign():
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    eps = [
        _ep("KAFKA-PLAIN", port=9092),
        _ep("CODE_SIGNING", cert_subject="CN=x", cert_not_after=now - timedelta(days=1),
            codesign_scan_json=json.dumps({"reasons": ["expired"]})),
    ]
    titles = [f["title"] for f in evaluate_protocol_service_endpoints(eps)]
    assert any("expired" in t.lower() and "code-signing" in t.lower() for t in titles)
    assert any("plaintext" in t.lower() or "kafka" in t.lower() for t in titles)
    tls_expired = _ep("TLS", cert_subject="CN=x", cert_not_after=now - timedelta(days=1),
                      codesign_scan_json=json.dumps({"reasons": ["expired"]}))
    assert not any("Code-signing" in f["title"]
                   for f in evaluate_protocol_service_endpoints([tls_expired]))


def test_composer_equals_old_five_call_composition():
    cfg = _cfg()
    eps = _fixture()
    new = derive_report_findings(eps, cfg)
    old = _old_composition(cfg, eps)
    assert len(new) > 4  # non-vacuous
    assert _titles(new) == _titles(old)


def test_composer_cfg_optional():
    out = derive_report_findings(_fixture())
    assert isinstance(out, list)


def test_run_scan_risk_engine_uses_composer_not_inlined_calls():
    tree = ast.parse(RUN_SCAN.read_text(encoding="utf-8"))
    banned = {"evaluate_email_endpoints", "evaluate_broker_endpoints",
              "evaluate_codesign_endpoints", "evaluate_identity_endpoints"}
    found = False
    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        has_timer = any(
            isinstance(n, ast.Call) and any(
                isinstance(a, ast.Constant) and a.value == "risk_engine" for a in n.args)
            for n in ast.walk(fn)
        )
        if not has_timer:
            continue
        found = True
        called = {n.func.id for n in ast.walk(fn)
                  if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
        assert "derive_report_findings" in called
        assert not (called & banned), called & banned
    assert found, "no function with a risk_engine _phase_timer found"
