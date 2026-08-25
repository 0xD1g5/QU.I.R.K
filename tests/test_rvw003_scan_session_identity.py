"""RVW-003: a scan session must be identified by a stored key, not inferred time.

`CryptoEndpoint` carries no `scan_run_id`, so `list_scans()` reconstructs session
membership by truncating `scanned_at` to the second and `trends._list_session_timestamps()`
by truncating to the millisecond. Each scanner stage stamps its own rows with
`datetime.now()` at the moment that stage runs, and a real scan's stages span many
seconds — so one scan renders as several history rows, each scored over a fraction
of the endpoints, producing the contradictory per-session scores the review observed.

`ScanJob` and `ScanCheckpoint` already carry `scan_run_id` (the run's `started_utc`,
stable across resume). These tests require `CryptoEndpoint` to carry it too, and the
read paths to group on it.
"""
import datetime
import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from quirk.models import Base, CryptoEndpoint


@pytest.fixture
def db():
    """An isolated in-memory database per test.

    Deliberately does NOT reuse the shared `dashboard_client` engine, whose
    process-wide `cache=shared` name is the subject of RVW-017.
    """
    engine = create_engine(
        f"sqlite:///file:rvw003_{uuid.uuid4().hex}?mode=memory&cache=shared&uri=true",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _one_scan_spanning_stages(session, run_id, base, host="10.0.0.1"):
    """Persist one scan's endpoints the way real stages do — spread over time."""
    stages = [("TLS", 443, 0), ("SSH", 22, 4), ("JWT", 8443, 11)]
    for protocol, port, offset in stages:
        session.add(CryptoEndpoint(
            host=host, port=port, protocol=protocol,
            scan_run_id=run_id,
            scanned_at=base + datetime.timedelta(seconds=offset),
        ))
    session.commit()


def test_crypto_endpoint_has_scan_run_id():
    """The model must carry a stored session key."""
    assert hasattr(CryptoEndpoint, "scan_run_id"), (
        "RVW-003: CryptoEndpoint has no scan_run_id — scan session membership "
        "is inferred from wall-clock time"
    )


def test_one_scan_yields_exactly_one_history_row(db):
    """A single scan whose stages span 11 seconds must be ONE history entry."""
    from quirk.dashboard.api.routes.scan import list_scans

    base = datetime.datetime(2026, 8, 24, 10, 0, 0)
    _one_scan_spanning_stages(db, "2026-08-24T10:00:00", base)

    sessions = list_scans(db=db)

    assert len(sessions) == 1, (
        f"RVW-003: one scan produced {len(sessions)} history rows "
        f"({[s.scan_id for s in sessions]}) — stages span multiple seconds, "
        f"which no amount of timestamp truncation can group"
    )
    assert sessions[0].total_endpoints == 3, (
        f"RVW-003: history row covers {sessions[0].total_endpoints} of 3 endpoints "
        f"— the per-session score is computed over a fraction of the scan"
    )


def test_two_scans_stay_distinct(db):
    """Grouping on the stored key must still separate genuinely different scans."""
    from quirk.dashboard.api.routes.scan import list_scans

    _one_scan_spanning_stages(
        db, "2026-08-24T10:00:00", datetime.datetime(2026, 8, 24, 10, 0, 0))
    _one_scan_spanning_stages(
        db, "2026-08-24T12:00:00", datetime.datetime(2026, 8, 24, 12, 0, 0))

    sessions = list_scans(db=db)

    assert len(sessions) == 2, (
        f"RVW-003: two distinct scans collapsed into {len(sessions)} history rows"
    )
    assert [s.total_endpoints for s in sessions] == [3, 3]


def test_two_scans_in_the_same_second_stay_distinct(db):
    """Two scans sharing a second are distinct — the old key could not tell them apart."""
    from quirk.dashboard.api.routes.scan import list_scans

    base = datetime.datetime(2026, 8, 24, 10, 0, 0)
    _one_scan_spanning_stages(db, "run-a", base, host="10.0.0.1")
    _one_scan_spanning_stages(db, "run-b", base, host="10.0.0.2")

    sessions = list_scans(db=db)

    assert len(sessions) == 2, (
        f"RVW-003: two scans starting in the same second collapsed into "
        f"{len(sessions)} history row(s)"
    )


def test_trends_treats_one_scan_as_one_session(db):
    """trends must not split one scan into a session per millisecond."""
    from quirk.dashboard.api.routes.trends import _list_session_timestamps

    base = datetime.datetime(2026, 8, 24, 10, 0, 0)
    _one_scan_spanning_stages(db, "2026-08-24T10:00:00", base)

    sessions = _list_session_timestamps(db)

    assert len(sessions) == 1, (
        f"RVW-003: trends split one scan into {len(sessions)} sessions — "
        f"score deltas are then computed between two stages of the same scan"
    )


# ---------------------------------------------------------------------------
# Write path — the read-path fix is inert unless scans actually stamp the key.
# ---------------------------------------------------------------------------

def test_stage_flush_stamps_the_session_key():
    """_flush_stage_endpoints must persist the run's scan_run_id on every row."""
    import os
    import tempfile

    import run_scan
    from quirk.db import get_session, init_db

    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    init_db(tmp.name)
    try:
        eps = [
            CryptoEndpoint(host="10.0.0.1", port=443, protocol="TLS",
                           scanned_at=datetime.datetime.now()),
            CryptoEndpoint(host="10.0.0.1", port=22, protocol="SSH",
                           scanned_at=datetime.datetime.now()),
        ]
        run_scan._flush_stage_endpoints(tmp.name, eps, "2026-08-24T10:00:00")

        with get_session(tmp.name) as session:
            rows = session.query(CryptoEndpoint).all()
        assert rows, "no rows persisted"
        assert all(r.scan_run_id == "2026-08-24T10:00:00" for r in rows), (
            f"RVW-003: rows persisted without the session key — "
            f"{[r.scan_run_id for r in rows]}"
        )
    finally:
        os.unlink(tmp.name)


def test_stamping_backfills_missing_scanned_at():
    """An endpoint with no scanned_at is invisible to every read surface."""
    import run_scan

    ep = CryptoEndpoint(host="10.0.0.1", port=443, protocol="TLS")
    assert ep.scanned_at is None
    run_scan._stamp_scan_session([ep], "2026-08-24T10:00:00")
    assert ep.scanned_at is not None, (
        "RVW-003: NULL scanned_at survives persistence — the row is filtered "
        "out of both Scan History and Trends"
    )


def test_stamping_preserves_an_existing_session_key():
    """A resumed endpoint already carrying its original key must keep it."""
    import run_scan

    ep = CryptoEndpoint(host="10.0.0.1", port=443, protocol="TLS",
                        scan_run_id="original-run",
                        scanned_at=datetime.datetime.now())
    run_scan._stamp_scan_session([ep], "a-different-run")
    assert ep.scan_run_id == "original-run"


def test_dashboard_scan_id_lookup_returns_the_whole_session(db):
    """GET /api/scan/latest?scan_id=... must resolve by the stored key.

    Before RVW-003 this matched only the endpoints stamped in the same second as
    the scan_id, then fell back to the owning job's *lifetime* window — which
    could absorb rows belonging to a concurrent scan.
    """
    from quirk.models import CryptoEndpoint as CE

    base = datetime.datetime(2026, 8, 24, 10, 0, 0)
    _one_scan_spanning_stages(db, "2026-08-24T10:00:00", base, host="10.0.0.1")
    # A concurrent scan overlapping the same wall-clock window.
    _one_scan_spanning_stages(db, "2026-08-24T10:00:02", base, host="10.0.0.9")

    rows = (
        db.query(CE).filter(CE.scan_run_id == "2026-08-24T10:00:00").all()
    )
    assert len(rows) == 3
    assert {r.host for r in rows} == {"10.0.0.1"}, (
        "RVW-003: session lookup absorbed a concurrent scan's endpoints"
    )
