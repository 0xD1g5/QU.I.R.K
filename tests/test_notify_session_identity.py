"""FIND-12 (Phase 229 D-08..D-11): sessions are identified by scan run.

The notifier used to key sessions on millisecond strftime strings, which split
one scan into several "sessions" and then failed the exact-scanned_at lookup, so
both sides loaded zero endpoints and the drift trigger never fired.
"""
from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timedelta

import pytest
from sqlalchemy.orm import sessionmaker

from quirk.db import init_db
from quirk.intelligence.trends import _fetch_session_endpoints, compute_trend_report
from quirk.models import CryptoEndpoint
from quirk.notify.dispatcher import _find_two_sessions, should_notify


@pytest.fixture()
def db(tmp_path):
    engine = init_db(str(tmp_path / "notify_identity.db"))
    session = sessionmaker(bind=engine)()
    yield session
    session.close()
    engine.dispose()


def _ep(ts, run_id, host, severity="LOW"):
    return CryptoEndpoint(
        host=host, port=443, protocol="TLS", severity=severity,
        scanned_at=ts, scan_run_id=run_id,
    )


DAY0 = datetime(2026, 10, 1, 12, 0, 0, 123456)
DAY1 = datetime(2026, 10, 2, 12, 0, 0, 654321)
DAY2 = datetime(2026, 10, 3, 12, 0, 0, 111111)


def test_probe_two_runs_microsecond_timestamps_fires(db):
    db.add(_ep(DAY0, "run-a", "a.example"))
    db.add(_ep(DAY1, "run-b", "b.example", "HIGH"))
    db.add(_ep(DAY1 + timedelta(milliseconds=3), "run-b", "c.example"))
    db.commit()

    current, previous = _find_two_sessions(db)
    assert current == DAY1
    assert previous == DAY0

    cur_eps = _fetch_session_endpoints(db, current)
    prev_eps = _fetch_session_endpoints(db, previous)
    assert len(cur_eps) == 2
    assert len(prev_eps) == 1
    assert {e.scan_run_id for e in cur_eps} != {e.scan_run_id for e in prev_eps}

    report = compute_trend_report(current, previous, db)
    assert should_notify(report) is True


def test_three_runs_compare_two_newest_distinct(db):
    db.add(_ep(DAY0, "run-a", "a.example"))
    db.add(_ep(DAY1, "run-b", "b.example"))
    db.add(_ep(DAY2, "run-c", "c1.example"))
    db.add(_ep(DAY2 + timedelta(milliseconds=2), "run-c", "c2.example"))
    db.add(_ep(DAY2 + timedelta(milliseconds=9), "run-c", "c3.example"))
    db.commit()

    current, previous = _find_two_sessions(db)
    assert (current, previous) == (DAY2, DAY1)
    cur_runs = {e.scan_run_id for e in _fetch_session_endpoints(db, current)}
    prev_runs = {e.scan_run_id for e in _fetch_session_endpoints(db, previous)}
    assert cur_runs == {"run-c"}
    assert prev_runs == {"run-b"}


def test_legacy_null_run_rows_in_distinct_ms_stay_distinct(db):
    db.add(_ep(datetime(2026, 5, 10, 12, 0, 0, 100000), None, "x.example"))
    db.add(_ep(datetime(2026, 5, 10, 12, 0, 0, 200000), None, "y.example"))
    db.commit()
    current, previous = _find_two_sessions(db)
    assert current is not None and previous is not None
    assert current != previous


def test_import_hygiene_no_fastapi_or_pydantic():
    code = (
        "import sys, quirk.intelligence.trends, quirk.notify.dispatcher; "
        "bad = [m for m in ('fastapi', 'pydantic') if m in sys.modules]; "
        "assert not bad, bad; print('import cost OK')"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True, text=True, timeout=120, close_fds=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "import cost OK" in result.stdout
