"""DETECT-07 (Phase 238, D-17..D-19): a TLS leaf signed with a weak hash
(SHA-1, MD5, MD4, MD2) yields one finding on the report and the dashboard.

Severity (D-18): HIGH for a CA-issued leaf, LOW for a self-signed leaf (the
self-signed HIGH already carries the trust problem). Only the stored leaf is
evaluated (D-19). Rows with a scan_error never get the finding.

Score proof: one healthy TLS row scores 77; the same row with a SHA-1 leaf
gains one HIGH and the compressed ceiling lands it on 63, on both derivers.
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

TITLE = "TLS certificate uses a weak signature hash"
SELF_SIGNED = "TLS certificate is self-signed"

_PAST = datetime.datetime(2020, 1, 1)
_FUTURE = datetime.datetime(2035, 1, 1)
_NOW = datetime.datetime(2026, 11, 16, 12, 0, 0)
_ids = itertools.count(23800)


def _row(**kw) -> CryptoEndpoint:
    base = dict(
        id=next(_ids), host="10.238.1.1", port=443, protocol="TLS",
        scanned_at=_NOW,
        cert_subject="CN=leaf", cert_issuer="CN=ca",
        cert_pubkey_alg="ECDSA", cert_pubkey_size=256,
        cert_not_before=_PAST, cert_not_after=_FUTURE,
        tls_version="TLSv1.3", tls_supported_versions="TLSv1.3",
        chain_verified=True, cert_sig_alg="sha1",
    )
    base.update(kw)
    return CryptoEndpoint(**base)


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


def test_sha1_ca_issued_leaf_high_on_both_surfaces():
    eps = [_row()]
    assert _of(_report(eps), TITLE) == ["HIGH"]
    assert _of(_dash(eps), TITLE) == ["HIGH"]
    assert _scores(eps) == [63, 63]
    assert _scores([_row(cert_sig_alg="sha256")]) == [77, 77]


def test_sha1_self_signed_leaf_low():
    eps = [_row(cert_subject="CN=s", cert_issuer="CN=s")]
    for pairs in (_report(eps), _dash(eps)):
        assert _of(pairs, TITLE) == ["LOW"]
        assert _of(pairs, SELF_SIGNED) == ["HIGH"]


def test_md5_leaf_is_weak_too():
    eps = [_row(cert_sig_alg="md5")]
    assert _of(_report(eps), TITLE) == ["HIGH"]
    assert _of(_dash(eps), TITLE) == ["HIGH"]


def test_sha1_rule_skips_scan_error_rows():
    eps = [_row(scan_error="TLS_HANDSHAKE_FAILED: x")]
    assert _of(_report(eps), TITLE) == []
    assert _of(_dash(eps), TITLE) == []


def test_unknown_sig_alg_is_not_weak():
    eps = [_row(cert_sig_alg="unknown")]
    assert _of(_report(eps), TITLE) == []
    assert _of(_dash(eps), TITLE) == []
