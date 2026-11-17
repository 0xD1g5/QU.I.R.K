"""Phase 238 D-20: the report and the dashboard share one undersized-RSA
predicate (quirk.util.weak_crypto.is_undersized_rsa).

Ledger 261116-rsa-undersized-key-predicate-differs-across-surfaces: the
dashboard used startswith("RSA") with a truthy size, the report used
== "RSA" with ``is not None``, so RSA size 0 and RSA-PSS 1024 rows got
different verdicts on the two surfaces.
"""
from __future__ import annotations

import copy
import datetime
import itertools

from quirk.dashboard.api.finding_derivation import (
    derive_dashboard_finding_items,
    derive_dashboard_scoring_findings,
)
from quirk.engine.findings_evaluator import derive_report_findings
from quirk.intelligence.evidence import build_evidence_summary
from quirk.intelligence.scoring import compute_readiness_score
from quirk.models import CryptoEndpoint

UNDERSIZED = "TLS certificate uses undersized RSA key"
QV_RSA = "TLS certificate uses quantum-vulnerable RSA key"

_PAST = datetime.datetime(2020, 1, 1)
_FUTURE = datetime.datetime(2035, 1, 1)
_NOW = datetime.datetime(2026, 11, 16, 12, 0, 0)
_ids = itertools.count(23850)


def _row(alg, size) -> CryptoEndpoint:
    return CryptoEndpoint(
        id=next(_ids), host="10.238.2.1", port=443, protocol="TLS",
        scanned_at=_NOW,
        cert_subject="CN=leaf", cert_issuer="CN=ca",
        cert_pubkey_alg=alg, cert_pubkey_size=size,
        cert_not_before=_PAST, cert_not_after=_FUTURE,
        tls_version="TLSv1.3", tls_supported_versions="TLSv1.3",
        chain_verified=True,
    )


def _report(eps):
    return [(f["title"], f["severity"]) for f in derive_report_findings(eps)]


def _dash(eps):
    return [(f.title, f.severity) for f in derive_dashboard_finding_items(eps)]


def _scores(eps):
    out = []
    for findings in (derive_report_findings(eps),
                     derive_dashboard_scoring_findings(eps)):
        ev = build_evidence_summary(endpoints=eps, findings=findings)
        out.append(compute_readiness_score(copy.deepcopy(ev))["score"])
    return out


def _of(pairs, title):
    return [sev for t, sev in pairs if t == title]


def test_rsa_size_0_no_undersized_high_either_surface():
    eps = [_row("RSA", 0)]
    report = _report(eps)
    assert _of(report, UNDERSIZED) == []
    assert _of(_dash(eps), UNDERSIZED) == []
    assert len(_of(report, QV_RSA)) == 1
    assert _scores(eps) == [77, 77]


def test_rsa_pss_1024_high_on_both_surfaces():
    eps = [_row("RSA-PSS", 1024)]
    assert _of(_report(eps), UNDERSIZED) == ["HIGH"]
    assert _of(_dash(eps), UNDERSIZED) == ["HIGH"]
    assert _scores(eps) == [63, 63]


def test_rsa_1024_unchanged():
    eps = [_row("RSA", 1024)]
    assert _of(_report(eps), UNDERSIZED) == ["HIGH"]
    assert _of(_dash(eps), UNDERSIZED) == ["HIGH"]
