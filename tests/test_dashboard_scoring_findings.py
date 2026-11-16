"""Phase 228 (XSURF-06/07, D-08/D-20/D-23): one dashboard scoring-findings helper.

Every dashboard score site (list_scans, lift_context_for_scan, get_latest_scan,
compare_scans) derives findings through `derive_dashboard_finding_items` /
`derive_dashboard_scoring_findings`, which adopt the report's email, broker and
code-signing evaluators and the identity findings.
"""
from __future__ import annotations

import ast
import datetime
from collections import Counter
from pathlib import Path

from quirk.dashboard.api.finding_title_bridge import canonical_cli_title
from quirk.dashboard.api.routes.scan import (
    _derive_findings,
    derive_dashboard_finding_items,
    derive_dashboard_scoring_findings,
)
from quirk.engine.findings_evaluator import (
    derive_report_findings,
    evaluate_protocol_service_endpoints,
)
from quirk.models import CryptoEndpoint

_NOW = datetime.datetime(2026, 10, 15, 12, 0, 0)
_PAST = datetime.datetime(2020, 1, 1)
_REPO = Path(__file__).resolve().parent.parent


def _ep(**kw):
    base = dict(id=1, host="10.0.0.1", port=443, protocol="TLS", scanned_at=_NOW)
    base.update(kw)
    return CryptoEndpoint(**base)


def _healthy_tls():
    return _ep(
        cert_subject="CN=ok.example", cert_issuer="CN=Real CA",
        cert_pubkey_alg="ECDSA", cert_pubkey_size=256,
        cert_not_before=_PAST, cert_not_after=datetime.datetime(2035, 1, 1),
        tls_version="TLSv1.3",
    )


def _smtps_weak():
    return _ep(id=2, host="10.0.1.1", port=465, protocol="SMTPS",
               tls_version="TLSv1.2", cipher_suite="TLS_RSA_WITH_AES_128_CBC_SHA")


def _codesign_expired():
    return _ep(id=3, host="10.0.2.1", port=0, protocol="CODE_SIGNING",
               cert_subject="CN=Signer", cert_issuer="CN=Real CA",
               cert_pubkey_alg="RSA", cert_pubkey_size=4096,
               cert_not_before=_PAST, cert_not_after=_PAST,
               codesign_scan_json='{"reasons": ["expired"]}')


def _kafka_plain():
    return _ep(id=4, host="10.0.3.1", port=9092, protocol="KAFKA-PLAIN")


def _saml_weak():
    return _ep(id=5, host="10.80.0.41", port=8080, protocol="SAML",
               cert_pubkey_alg="RSA", cert_pubkey_size=1024,
               service_detail="urn:mh-saml-idp|use=signing|serial=0a1b")


def test_email_weak_cipher_adopts_report_finding():
    items = derive_dashboard_finding_items([_smtps_weak()])
    hits = [i for i in items if i.title == "Weak cipher suite on email TLS endpoint"]
    assert len(hits) == 1 and hits[0].severity == "HIGH"
    report = [d for d in evaluate_protocol_service_endpoints([_smtps_weak()])
              if d["title"] == hits[0].title]
    assert hits[0].remediation == report[0]["recommendation"]


def test_code_signing_expired_uses_report_title_not_dashboard_critical():
    items = derive_dashboard_finding_items([_codesign_expired()])
    titles = {(i.title, i.severity) for i in items}
    report = evaluate_protocol_service_endpoints([_codesign_expired()])
    assert report, "report evaluator must flag the expired code-signing cert"
    assert (report[0]["title"], "HIGH") in titles
    assert not any(i.title == "Certificate expired" for i in items)


def test_broker_plaintext_included():
    items = derive_dashboard_finding_items([_kafka_plain()])
    assert any(i.severity == "HIGH" for i in items), items


def test_identity_finding_included_for_compare():
    items = derive_dashboard_finding_items([_saml_weak()])
    assert any(i.protocol == "SAML" or "SAML" in i.title for i in items), items


def test_healthy_tls_row_has_no_extra_items():
    eps = [_healthy_tls()]
    assert [i.model_dump() for i in derive_dashboard_finding_items(eps)] == [
        f.model_dump() for f in _derive_findings(eps)
    ]


def test_scoring_findings_is_model_dump_of_items():
    eps = [_healthy_tls(), _smtps_weak(), _saml_weak()]
    assert derive_dashboard_scoring_findings(eps) == [
        i.model_dump() for i in derive_dashboard_finding_items(eps)
    ]


def test_high_critical_multiset_matches_report():
    eps = [
        _ep(id=10, host="10.0.0.9", cert_subject="CN=s", cert_issuer="CN=Real CA",
            cert_pubkey_alg="ECDSA", cert_pubkey_size=256, cert_not_before=_PAST,
            cert_not_after=datetime.datetime.now() + datetime.timedelta(days=10)),
        _smtps_weak(), _codesign_expired(), _saml_weak(),
    ]

    def ms(rows):
        return Counter(
            (r["title"], r["severity"]) for r in rows
            if r["severity"] in ("HIGH", "CRITICAL")
        )

    dash = Counter()
    for r in derive_dashboard_scoring_findings(eps):
        if r["severity"] in ("HIGH", "CRITICAL"):
            dash[(canonical_cli_title(r["title"]) or r["title"], r["severity"])] += 1
    assert dash == ms(derive_report_findings(eps))


def test_score_sites_use_the_single_helper():
    tree = ast.parse((_REPO / "quirk/dashboard/api/routes/scan.py").read_text())
    funcs = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    helpers = {"derive_dashboard_finding_items", "derive_dashboard_scoring_findings"}
    for name in ("list_scans", "lift_context_for_scan", "get_latest_scan", "compare_scans"):
        called = {
            getattr(c.func, "id", getattr(c.func, "attr", None))
            for c in ast.walk(funcs[name]) if isinstance(c, ast.Call)
        }
        assert called & helpers, f"{name} does not use the single helper"
        assert "_derive_findings" not in called, f"{name} calls _derive_findings directly"


# --- Phase 236 D-06: container crypto-library findings on the dashboard -----

def _sev_title(items):
    return sorted((f.severity, f.title) for f in items if f.protocol == "CONTAINER")


def test_container_findings_match_report_titles_and_severities():
    from tests.fixtures.divergence_rows import FAMILY_ROWS

    for fam, sev in (("container_openssl_111", "HIGH"),
                     ("container_openssl_102", "CRITICAL"),
                     ("container_pycrypto_old", "HIGH")):
        rows = FAMILY_ROWS[fam]()
        dash = [f for f in derive_dashboard_finding_items(rows)
                if f.title.startswith(("End-of-life", "Severely outdated"))]
        rep = [d for d in derive_report_findings(rows)
               if d["title"].startswith(("End-of-life", "Severely outdated"))]
        assert dash and sev in {f.severity for f in dash}, fam
        assert sorted((f.severity, f.title) for f in dash) == sorted(
            (d["severity"], d["title"]) for d in rep), fam


def test_container_scan_error_yields_no_finding_on_either_surface():
    from tests.fixtures.divergence_rows import FAMILY_ROWS

    rows = FAMILY_ROWS["container_scan_error"]()
    assert [f for f in derive_dashboard_finding_items(rows)
            if f.protocol == "CONTAINER"] == []
    assert [d for d in derive_report_findings(rows)
            if "container image" in d["title"].lower()] == []


def test_container_duplicate_packages_dedupe_identically():
    rows = [
        _ep(id=1, host="img", port=0, protocol="CONTAINER",
            cipher_suite="openssl", tls_version="1.1.1w"),
        _ep(id=2, host="img", port=0, protocol="CONTAINER",
            cipher_suite="libssl1.1", tls_version="1.1.1w"),
    ]
    def hi(titles):
        return Counter(
            (s, t) for s, t in titles if s in ("HIGH", "CRITICAL")
        )
    dash = hi((f.severity, f.title) for f in derive_dashboard_finding_items(rows))
    rep = hi((d["severity"], d["title"]) for d in derive_report_findings(rows))
    assert dash == rep and sum(dash.values()) >= 1


def test_container_findings_carry_container_protocol():
    from tests.fixtures.divergence_rows import FAMILY_ROWS

    items = derive_dashboard_finding_items(FAMILY_ROWS["container_openssl_102"]())
    eol = [f for f in items if f.title.startswith("End-of-life")]
    assert eol and all(f.protocol == "CONTAINER" for f in eol)
