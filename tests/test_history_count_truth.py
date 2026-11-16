"""Phase 237-04 COUNT-01 / COUNT-03: History counts and Compare diffs come from
derived findings (one per finding), not endpoint severity columns."""
from __future__ import annotations

from datetime import datetime, timedelta

from tests.test_dashboard_scan_history import (
    _make_client_and_session,
    _seed_session,
)

RUN_A = "2026-11-10T10:00:00"
RUN_B = "2026-11-09T10:00:00"
T_A = datetime(2026, 11, 10, 10, 0, 0)
T_B = datetime(2026, 11, 9, 10, 0, 0)
FAR = datetime(2036, 1, 1)


def _http(host, run, port=80):
    return dict(host=host, port=port, protocol="HTTP", severity=None, scan_run_id=run)


def _selfsigned(host, run, port=443):
    return dict(
        host=host, port=port, protocol="TLS", severity=None, scan_run_id=run,
        tls_version="TLSv1.3", cert_subject="CN=x", cert_issuer="CN=x",
        cert_not_after=FAR,
    )


def _expiring(host, run, port=8443):
    return dict(
        host=host, port=port, protocol="TLS", severity=None, scan_run_id=run,
        tls_version="TLSv1.3", cert_subject="CN=a", cert_issuer="CN=b",
        cert_not_after=datetime.utcnow() + timedelta(days=5),
    )


def _bucket(findings):
    out = {"high": 0, "medium": 0, "low": 0}
    for f in findings:
        s = f["severity"]
        if s in ("CRITICAL", "HIGH"):
            out["high"] += 1
        elif s == "MEDIUM":
            out["medium"] += 1
        elif s == "LOW":
            out["low"] += 1
    return out


def test_history_counts_equal_findings_page():
    client, Session = _make_client_and_session()
    _seed_session(Session, T_A, [_http("h1", RUN_A), _expiring("h2", RUN_A)])
    row = next(s for s in client.get("/api/scans").json() if s["scan_id"] == RUN_A)
    latest = client.get("/api/scan/latest", params={"scan_id": RUN_A}).json()
    expected = _bucket(latest["findings"])
    assert expected["high"] >= 1 and expected["medium"] >= 1
    assert row["finding_counts"] == expected


def test_history_counts_per_finding():
    client, Session = _make_client_and_session()
    # self-signed + HTTP on separate rows; one TLS row with self-signed AND expiring
    ep = _selfsigned("h1", RUN_A)
    ep["cert_not_after"] = datetime.utcnow() + timedelta(days=5)
    _seed_session(Session, T_A, [ep])
    row = client.get("/api/scans").json()[0]
    assert row["finding_counts"]["high"] == 1
    assert row["finding_counts"]["medium"] == 1


def _compare(client, a, b):
    r = client.get("/api/compare", params={"a": a, "b": b})
    assert r.status_code == 200, r.text
    return r.json()


def test_compare_lists_added_and_removed_with_identity():
    client, Session = _make_client_and_session()
    _seed_session(Session, T_A, [_http("keep", RUN_A), _selfsigned("new", RUN_A)])
    _seed_session(Session, T_B, [_http("keep", RUN_B), _http("gone", RUN_B, port=8080)])
    body = _compare(client, RUN_A, RUN_B)
    added = body["added_findings"]
    removed = body["removed_findings"]
    assert [(f["host"], f["port"], f["title"]) for f in added] == [
        ("new", 443, "TLS certificate is self-signed")
    ]
    assert [(f["host"], f["port"], f["title"]) for f in removed] == [
        ("gone", 8080, "Unencrypted HTTP service")
    ]
    assert added[0]["severity"] == "HIGH"


def test_compare_identical_scans_empty():
    client, Session = _make_client_and_session()
    _seed_session(Session, T_A, [_http("h", RUN_A), _selfsigned("s", RUN_A)])
    _seed_session(Session, T_B, [_http("h", RUN_B), _selfsigned("s", RUN_B)])
    body = _compare(client, RUN_A, RUN_B)
    assert body["added_findings"] == []
    assert body["removed_findings"] == []


def test_compare_errored_host_not_phantom_removed():
    client, Session = _make_client_and_session()
    errored = dict(host="h", port=80, protocol="HTTP", severity=None,
                   scan_run_id=RUN_A, scan_error="timeout")
    _seed_session(Session, T_A, [errored, _http("other", RUN_A)])
    _seed_session(Session, T_B, [_http("h", RUN_B), _http("other", RUN_B)])
    body = _compare(client, RUN_A, RUN_B)
    assert body["removed_findings"] == []
