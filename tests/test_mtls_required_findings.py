"""DETECT-06 (Phase 238, D-14/D-28): the INFO "mTLS required" finding.

Two stored shapes mean "this endpoint wants a client certificate":

* handshake variant: the handshake itself failed, so ``scan_error`` starts
  with ``MTLS_REQUIRED:`` and no certificate was observed;
* post-handshake variant (238-03): the handshake completed and the server then
  rejected the client, so ``tls_blocker_reason == "MTLS_REQUIRED"``, the
  version and certificate fields are set, and ``scan_error`` is empty.

Both pipelines call the one shared predicate
``findings_evaluator.mtls_required_variant``. The post-handshake row keeps
every certificate finding; the INFO is added beside them.
"""
from __future__ import annotations

import datetime
import itertools

from quirk.dashboard.api.finding_derivation import (
    derive_dashboard_finding_items,
    derive_dashboard_scoring_findings,
)
from quirk.engine.findings_evaluator import derive_report_findings
from quirk.intelligence.evidence import build_evidence_summary
from quirk.models import CryptoEndpoint
from tests.fixtures.divergence_rows import FAMILY_ROWS

MTLS = "mTLS required"
SHA1 = "TLS certificate uses a weak signature hash"

_PAST = datetime.datetime(2020, 1, 1)
_FUTURE = datetime.datetime(2035, 1, 1)
_NOW = datetime.datetime(2026, 11, 16, 12, 0, 0)
_ids = itertools.count(23870)


def _row(**kw) -> CryptoEndpoint:
    base = dict(
        id=next(_ids), host="10.238.7.1", port=443, protocol="TLS",
        scanned_at=_NOW,
        cert_subject="CN=leaf", cert_issuer="CN=ca",
        cert_pubkey_alg="ECDSA", cert_pubkey_size=256,
        cert_not_before=_PAST, cert_not_after=_FUTURE,
        tls_version="TLSv1.3", tls_supported_versions="TLSv1.3",
        chain_verified=True, cert_sig_alg="sha256",
    )
    base.update(kw)
    return CryptoEndpoint(**base)


def _post_handshake(**kw) -> CryptoEndpoint:
    kw.setdefault("tls_blocker_reason", "MTLS_REQUIRED")
    kw.setdefault("scan_error", None)
    return _row(**kw)


def _handshake(**kw) -> CryptoEndpoint:
    kw.setdefault("scan_error", "MTLS_REQUIRED: tlsv13 alert certificate required")
    kw.setdefault("tls_version", None)
    kw.setdefault("tls_supported_versions", None)
    return _row(**kw)


def _report(eps):
    return [(f["title"], f["severity"]) for f in derive_report_findings(eps)]


def _dash(eps):
    return [(f.title, f.severity) for f in derive_dashboard_finding_items(eps)]


def _of(pairs, title):
    return [sev for t, sev in pairs if t == title]


def test_mtls_variant_truth_table():
    from quirk.engine.findings_evaluator import mtls_required_variant

    assert mtls_required_variant(_handshake(scan_error="MTLS_REQUIRED: x")) == "handshake"
    assert mtls_required_variant(_post_handshake()) == "post_handshake"
    assert mtls_required_variant(_row(tls_blocker_reason="TIMEOUT")) is None
    assert mtls_required_variant(
        _row(protocol="HTTP", tls_blocker_reason="MTLS_REQUIRED")
    ) is None
    assert mtls_required_variant(_row()) is None


def test_post_handshake_mtls_row_keeps_cert_findings():
    from quirk.engine.findings_evaluator import mtls_required_variant

    eps = [_post_handshake(cert_sig_alg="sha1")]
    assert mtls_required_variant(eps[0]) == "post_handshake"
    for pairs in (_report(eps), _dash(eps)):
        assert _of(pairs, MTLS) == ["INFO"]
        assert _of(pairs, SHA1) == ["HIGH"]


def test_handshake_mtls_row_dashboard_info():
    from quirk.engine.findings_evaluator import mtls_required_variant

    eps = [_handshake()]
    assert mtls_required_variant(eps[0]) == "handshake"
    dash = _dash(eps)
    assert _of(dash, MTLS) == ["INFO"]
    assert [t for t, sev in dash if sev in ("HIGH", "CRITICAL")] == []
    report = [f for f in derive_report_findings(eps) if f["title"] == MTLS]
    assert len(report) == 1
    assert "before completing the TLS handshake" in report[0]["description"]


def test_http_mtls_pair_reports_one_mtls_info():
    from quirk.engine.findings_evaluator import mtls_required_variant

    eps = FAMILY_ROWS["http_on_tls_port_with_mtls_pair"]()
    assert [mtls_required_variant(e) for e in eps] == [None, "post_handshake"]
    assert _of(_report(eps), MTLS) == ["INFO"]


def test_mtls_presence_credit_unchanged():
    from quirk.engine.findings_evaluator import mtls_required_variant

    eps = [_post_handshake()]
    assert mtls_required_variant(eps[0]) == "post_handshake"
    for findings in (derive_report_findings(eps),
                     derive_dashboard_scoring_findings(eps)):
        summary = build_evidence_summary(endpoints=eps, findings=findings)
        assert summary["mtls_present_count"] == 1


# ---------------------------------------------------------------------------
# WR-07: one shared observed-mTLS predicate for the evaluator, the dashboard
# deriver and closure.
# ---------------------------------------------------------------------------


def test_shared_observed_mtls_predicate_shapes():
    from quirk.util.tls_rows import is_observed_mtls, mtls_required_variant

    assert is_observed_mtls(_post_handshake()) is True
    assert is_observed_mtls(_post_handshake(scan_error="")) is True
    assert is_observed_mtls(_post_handshake(tls_version=None)) is True
    assert is_observed_mtls(_handshake()) is False
    assert is_observed_mtls(_row(tls_blocker_reason="TIMEOUT")) is False
    assert is_observed_mtls(_row()) is False
    assert is_observed_mtls(_post_handshake(protocol="tls")) is False
    assert mtls_required_variant(_post_handshake(scan_error="")) == "post_handshake"
    assert mtls_required_variant(_handshake()) == "handshake"


def test_all_three_sites_use_the_shared_predicate():
    import inspect

    from quirk.dashboard.api import finding_derivation
    from quirk.engine import findings_evaluator
    from quirk.intelligence import closure
    from quirk.util import tls_rows

    assert findings_evaluator.mtls_required_variant is tls_rows.mtls_required_variant
    assert finding_derivation.mtls_required_variant is tls_rows.mtls_required_variant
    src = inspect.getsource(closure)
    assert src.count("is_observed_mtls(ep)") == 1
    assert '"MTLS_REQUIRED"' not in src


def test_empty_scan_error_and_missing_version_rows_get_findings_on_both_surfaces():
    for ep in (_post_handshake(scan_error="", cert_sig_alg="sha1"),
               _post_handshake(tls_version=None, cert_sig_alg="sha1")):
        assert _of(_report([ep]), MTLS) == ["INFO"]
        assert _of(_dash([ep]), MTLS) == ["INFO"]
        assert _of(_report([ep]), SHA1) == ["HIGH"]
        assert _of(_dash([ep]), SHA1) == ["HIGH"]
