"""Phase 237 plan 06 (COUNT-01 / COUNT-06 / D-22): timeline counts and complete-only resolvers.

Covers the Trends timeline's derived finding counts (D-13), the
``complete_only`` flag on ``list_session_timestamps`` (D-08/D-09), the notify
session pair, the exposure-map latest resolver (D-17) and the notify guard that
stops a failed or interrupted scheduled run re-sending the previous complete
pair's alert (D-22). Fixtures use fixed timestamps (no wall clock).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from quirk.models import Base, CryptoEndpoint, ScanCheckpoint
from quirk.scanner.jwt_scanner import ADVISORY_JWKS_VERIFY_DISABLED

T0 = datetime(2026, 3, 1, 10, 0, 0)


def _ts(n: int) -> datetime:
    return T0 + timedelta(hours=n)


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False},
        poolclass=__import__("sqlalchemy.pool", fromlist=["StaticPool"]).StaticPool,
    )
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    yield s
    s.close()


def _session(db, run_id, ts, high: int = 0, complete: bool | None = True):
    """One scan session. complete=True -> reports checkpoint; False -> only a
    discovery checkpoint; None -> no checkpoint rows (legacy/sensor/import)."""
    db.add(CryptoEndpoint(
        host="10.0.0.1", port=443, protocol="tls", scanned_at=ts, scan_run_id=run_id,
    ))
    for i in range(high):
        db.add(CryptoEndpoint(
            host=f"adv{i}.example", port=443, protocol="ADVISORY",
            service_detail=ADVISORY_JWKS_VERIFY_DISABLED,
            scanned_at=ts, scan_run_id=run_id,
        ))
    if complete is True:
        db.add(ScanCheckpoint(scan_run_id=run_id, stage="reports", status="completed", completed_at=ts))
    elif complete is False:
        db.add(ScanCheckpoint(scan_run_id=run_id, stage="discovery", status="completed", completed_at=ts))
    db.commit()


# ---------------------------------------------------------------------------
# HTTP harness (shared-cache in-memory DB, as tests/test_dashboard_trends.py)
# ---------------------------------------------------------------------------

@pytest.fixture
def client_and_db():
    from fastapi.testclient import TestClient

    from quirk.dashboard.api.app import create_app
    from quirk.dashboard.api.deps import get_db

    name = f"test_cs237_{uuid.uuid4().hex}"
    engine = create_engine(
        f"sqlite:///file:{name}?mode=memory&cache=shared&uri=true",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    maker = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def _override():
        s = maker()
        try:
            yield s
        finally:
            s.close()

    app = create_app()
    app.dependency_overrides[get_db] = _override
    seed = maker()
    yield TestClient(app), seed
    seed.close()


def test_timeline_counts_from_derived_findings(client_and_db):
    from quirk.dashboard.api.finding_derivation import derive_dashboard_scoring_findings
    from quirk.intelligence.trends import _count_findings_by_bucket, _fetch_session_endpoints

    client, db = client_and_db
    _session(db, "run-a", _ts(0), high=2)
    _session(db, "run-b", _ts(1), high=3)
    eps = _fetch_session_endpoints(db, _ts(1))
    expected = _count_findings_by_bucket(derive_dashboard_scoring_findings(eps))
    assert expected.get("high", 0) == 3
    points = client.get("/api/trends/timeline?n=30").json()["sessions"]
    assert len(points) == 2
    assert points[0]["finding_counts"]["high"] == expected["high"]
    assert points[1]["finding_counts"]["high"] == 2


def test_api_trends_current_session_is_last_complete(client_and_db):
    client, db = client_and_db
    _session(db, "run-a", _ts(0))
    _session(db, "run-b", _ts(1))
    _session(db, "run-c", _ts(2), complete=False)
    data = client.get("/api/trends").json()
    assert data["current_session_ts"].startswith("2026-03-01T11:00:00")
    assert data["previous_session_ts"].startswith("2026-03-01T10:00:00")


def test_timeline_excludes_incomplete(client_and_db):
    client, db = client_and_db
    _session(db, "run-a", _ts(0))
    _session(db, "run-b", _ts(1))
    _session(db, "run-c", _ts(2), complete=False)
    points = client.get("/api/trends/timeline?n=30").json()["sessions"]
    assert [p["session_ts"][:19] for p in points] == ["2026-03-01T11:00:00", "2026-03-01T10:00:00"]


# ---------------------------------------------------------------------------
# Lister
# ---------------------------------------------------------------------------

def test_list_session_timestamps_complete_only_drops_incomplete_before_limit(db):
    from quirk.intelligence.trends import list_session_timestamps

    _session(db, "run-a", _ts(0))
    _session(db, "run-b", _ts(1))
    _session(db, "run-c", _ts(2))
    _session(db, "run-d", _ts(3), complete=False)
    assert list_session_timestamps(db, limit=2, complete_only=True) == [_ts(2), _ts(1)]


def test_list_session_timestamps_default_unchanged(db):
    from quirk.intelligence.trends import list_session_timestamps

    _session(db, "run-a", _ts(0))
    _session(db, "run-d", _ts(3), complete=False)
    assert list_session_timestamps(db, limit=5) == [_ts(3), _ts(0)]


def test_legacy_null_run_rows_kept(db):
    from quirk.intelligence.trends import list_session_timestamps

    db.add(CryptoEndpoint(host="h", port=22, protocol="ssh", scanned_at=_ts(0), scan_run_id=None))
    db.commit()
    _session(db, "run-d", _ts(3), complete=False)
    assert list_session_timestamps(db, limit=5, complete_only=True) == [_ts(0)]


# ---------------------------------------------------------------------------
# notify / exposure
# ---------------------------------------------------------------------------

def test_notify_find_two_sessions_skips_incomplete(db):
    from quirk.notify.dispatcher import _find_two_sessions

    _session(db, "run-a", _ts(0))
    _session(db, "run-b", _ts(1))
    _session(db, "run-c", _ts(2), complete=False)
    assert _find_two_sessions(db) == (_ts(1), _ts(0))


def test_exposure_latest_skips_incomplete(db):
    from quirk.intelligence.exposure_map import latest_scan_run_id

    _session(db, "2026-03-01T10:00:00", _ts(0))
    _session(db, "2026-03-01T12:00:00", _ts(2), complete=False)
    assert latest_scan_run_id(db) == "2026-03-01T10:00:00"


def _shared_key_pair(db, run_id, ts, complete):
    """Two endpoints sharing one key (a key-reuse edge) in one session."""
    for host in ("10.0.0.11", "10.0.0.12"):
        db.add(CryptoEndpoint(
            host=host, port=443, protocol="TLS", scanned_at=ts, scan_run_id=run_id,
            cert_spki_fingerprint="a" * 64, cert_subject="CN=x",
            cert_pubkey_alg="RSA", cert_pubkey_size=2048,
        ))
    stage = "reports" if complete else "discovery"
    db.add(ScanCheckpoint(scan_run_id=run_id, stage=stage, status="completed", completed_at=ts))
    db.commit()


def test_exposure_map_all_incomplete_scopes_to_nothing(db):
    """WR-01 (237 review): keyed scans exist but none is complete (the first
    dashboard scan, still running). The default map must NOT fall back to
    unscoped and draw the running scan's partial rows (D-17); it returns an
    empty map that says why, so it never reads as verified zero exposure."""
    from quirk.intelligence.exposure_map import derive_exposure_map, latest_scan_run_id

    _shared_key_pair(db, "2026-03-01T10:00:00", _ts(0), complete=False)
    assert latest_scan_run_id(db) is None
    # Non-vacuity: pinned explicitly, the running scan's rows DO draw an edge.
    assert derive_exposure_map(db, scan_run_id="2026-03-01T10:00:00")["edges"]
    result = derive_exposure_map(db)
    assert result["nodes"] == [] and result["edges"] == []
    assert result.get("unavailable_reason")


def test_exposure_map_legacy_unkeyed_rows_stay_unscoped(db):
    """WR-01 control: an all-legacy DB (no scan_run_id anywhere) keeps the
    documented "do not scope" behaviour."""
    from quirk.intelligence.exposure_map import derive_exposure_map

    for host in ("10.0.0.11", "10.0.0.12"):
        db.add(CryptoEndpoint(
            host=host, port=443, protocol="TLS", scanned_at=_ts(0), scan_run_id=None,
            cert_spki_fingerprint="a" * 64, cert_subject="CN=x",
            cert_pubkey_alg="RSA", cert_pubkey_size=2048,
        ))
    db.commit()
    result = derive_exposure_map(db)
    assert result["edges"]
    assert result.get("unavailable_reason") is None


def _notify_setup(db, monkeypatch, newest_incomplete: bool):
    from quirk.cli.scheduler_cmd import _utcnow_naive
    from quirk.models import ScheduledScan
    from quirk.notify import dispatcher
    from quirk.notify.config import NotifyCfg, SlackNotifyCfg

    cfg = NotifyCfg(
        trigger_score_floor=-5,
        slack=SlackNotifyCfg(slack_webhook_env="QUIRK_SLACK_WEBHOOK"),
    )
    monkeypatch.setattr(dispatcher, "load_notifications_config", lambda: cfg)
    sent = []
    monkeypatch.setattr(dispatcher, "_channel_send_slack", lambda c, s: sent.append(s))
    _session(db, "run-a", _ts(0))
    _session(db, "run-b", _ts(1), high=2)  # new HIGH vs run-a -> should_notify
    if newest_incomplete:
        # more HIGH than run-b so an unguarded dispatcher would also alert
        _session(db, "run-c", _ts(2), high=5, complete=False)
    schedule = ScheduledScan(
        name="s", cron_expr="* * * * *", target="127.0.0.1", enabled=True,
        created_at=_utcnow_naive(),
    )
    db.add(schedule)
    db.commit()
    return dispatcher, schedule, sent


def _run(db, schedule, status):
    from quirk.cli.scheduler_cmd import _utcnow_naive
    from quirk.models import ScheduledRun

    run = ScheduledRun(
        schedule_id=schedule.id, dispatched_at=_utcnow_naive(),
        status=status, scan_output_path=None, scan_id=None,
    )
    db.add(run)
    db.commit()
    return run


def test_notify_skips_failed_scheduled_run(db, monkeypatch):
    dispatcher, schedule, sent = _notify_setup(db, monkeypatch, newest_incomplete=False)
    dispatcher.dispatch_notifications(run=_run(db, schedule, "failed"), schedule=schedule, db=db)
    assert sent == []
    dispatcher.dispatch_notifications(run=_run(db, schedule, "completed"), schedule=schedule, db=db)
    assert len(sent) == 1


def test_notify_skips_when_newest_session_incomplete(db, monkeypatch):
    dispatcher, schedule, sent = _notify_setup(db, monkeypatch, newest_incomplete=True)
    dispatcher.dispatch_notifications(run=_run(db, schedule, "completed"), schedule=schedule, db=db)
    assert sent == []
