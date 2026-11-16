"""COUNT-02 (Phase 237-01): Trends delta is keyed on derived findings, not on
CryptoEndpoint.severity (which only cloud connectors set).

Every endpoint is seeded with severity=NULL so the tests prove derivation.
Fixtures are wall-clock independent (no cert_not_after; title-churn cases use
a deriver stub).
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import sessionmaker

from quirk.db import init_db
from quirk.intelligence.trends import compute_trend_report
from quirk.models import CryptoEndpoint

PREV = datetime(2026, 1, 1, 10, 0, 0)
CUR = datetime(2026, 1, 2, 10, 0, 0)


def _db(tmp_path):
    engine = init_db(str(tmp_path / "t.db"))
    return sessionmaker(bind=engine)()


def _ep(ts, run, host="10.0.0.1", port=443, protocol="TLS", **kw):
    return CryptoEndpoint(
        host=host, port=port, protocol=protocol, scanned_at=ts,
        scan_run_id=run, severity=None, **kw,
    )


def _f(host, port, title, severity, protocol="TLS"):
    return {"host": host, "port": port, "title": title,
            "severity": severity, "protocol": protocol}


def _by_session(prev_findings, cur_findings):
    """Deriver stub keyed on the session's scan_run_id."""
    def derive(eps):
        run = eps[0].scan_run_id if eps else None
        return prev_findings if run == "prev" else cur_findings
    return derive


def test_new_tls_high_counted(tmp_path) -> None:
    from quirk.dashboard.api.finding_derivation import derive_dashboard_scoring_findings

    with _db(tmp_path) as db:
        db.add(_ep(PREV, "prev", protocol="TLS", tls_version="TLSv1.3"))
        db.add(_ep(CUR, "cur", protocol="TLS", tls_version="TLSv1.3"))
        db.add(_ep(CUR, "cur", host="10.0.0.9", port=80, protocol="HTTP"))
        db.commit()
        r = compute_trend_report(
            CUR, PREV, db, findings_deriver=derive_dashboard_scoring_findings
        )
    assert r.new_high >= 1, f"new_high={r.new_high}"
    assert r.new_total >= 1


def test_counts_are_per_finding_not_per_endpoint(tmp_path) -> None:
    with _db(tmp_path) as db:
        db.add(_ep(PREV, "prev"))
        db.add(_ep(CUR, "cur"))
        db.commit()
        d = _by_session([], [_f("10.0.0.1", 443, "A", "HIGH"), _f("10.0.0.1", 443, "B", "LOW")])
        r = compute_trend_report(CUR, PREV, db, findings_deriver=d)
    assert r.new_total == 2
    assert (r.new_high, r.new_low) == (1, 1)


def test_severity_change_is_one_transition(tmp_path) -> None:
    with _db(tmp_path) as db:
        db.add(_ep(PREV, "prev"))
        db.add(_ep(CUR, "cur"))
        db.commit()
        d = _by_session([_f("10.0.0.1", 443, "Weak", "MEDIUM")],
                        [_f("10.0.0.1", 443, "Weak", "HIGH")])
        r = compute_trend_report(CUR, PREV, db, findings_deriver=d)
    assert len(r.severity_transitions) == 1
    t = r.severity_transitions[0]
    assert (t.previous_severity, t.current_severity) == ("MEDIUM", "HIGH")
    assert t.title == "Weak"
    assert r.new_total == 0 and r.resolved_total == 0


def test_expiring_cert_day_count_not_churn(tmp_path) -> None:
    with _db(tmp_path) as db:
        db.add(_ep(PREV, "prev"))
        db.add(_ep(CUR, "cur"))
        db.commit()
        d = _by_session(
            [_f("10.0.0.1", 443, "Certificate expiring in 12 day(s)", "MEDIUM")],
            [_f("10.0.0.1", 443, "Certificate expiring in 3 day(s)", "MEDIUM")],
        )
        r = compute_trend_report(CUR, PREV, db, findings_deriver=d)
    assert r.new_total == 0 and r.resolved_total == 0


def test_errored_now_host_not_phantom_resolved(tmp_path) -> None:
    with _db(tmp_path) as db:
        db.add(_ep(PREV, "prev"))
        db.add(_ep(CUR, "cur", scan_error="boom", scan_error_category="exception"))
        db.commit()
        d = _by_session([_f("10.0.0.1", 443, "Weak", "HIGH")], [])
        r = compute_trend_report(CUR, PREV, db, findings_deriver=d)
    assert r.resolved_total == 0


def test_protocol_none_finding_serializes(tmp_path) -> None:
    from quirk.dashboard.api.schemas import SampleFinding, SeverityTransitionResponse

    with _db(tmp_path) as db:
        db.add(_ep(PREV, "prev"))
        db.add(_ep(CUR, "cur"))
        db.commit()
        d = _by_session(
            [_f("10.0.0.1", 443, "Old", "LOW", protocol=None),
             _f("10.0.0.1", 443, "Chg", "LOW", protocol=None)],
            [_f("10.0.0.1", 443, "New", "HIGH", protocol=None),
             _f("10.0.0.1", 443, "Chg", "HIGH", protocol=None)],
        )
        r = compute_trend_report(CUR, PREV, db, findings_deriver=d)
    assert r.new_findings_sample
    for s in r.new_findings_sample + r.resolved_findings_sample:
        m = SampleFinding(host=s.host, port=s.port, protocol=s.protocol,
                          severity=s.severity, title=s.title)
        assert m.protocol is None and m.title
    for t in r.severity_transitions:
        SeverityTransitionResponse(
            host=t.host, port=t.port, protocol=t.protocol, title=t.title,
            previous_severity=t.previous_severity, current_severity=t.current_severity,
        )
