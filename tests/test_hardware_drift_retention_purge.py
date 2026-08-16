"""Phase 157 Plan 01 (HWLC-16) — drift-event retention purge tests.

Confirms ``run_scan._purge_stale_drift_events`` enforces a calendar-cutoff
retention window over the WHOLE ``hardware_drift_events`` table — structurally
distinct from the Phase 154 ``_purge_stale_hardware_history`` purge, which is
scoped to the (host, port) pairs present in the current scan's ``hw_batch``.

This file is intentionally kept separate from
``tests/test_hardware_retention_purge.py`` (157-VALIDATION.md Wave 0 note) so
the two purge semantics stay visually distinguishable.

The single most important assertion in this file is
``test_purge_is_not_scoped_to_batch_host_port`` — the Pitfall 1 regression
test proving a stale event for a host NOT present in the current scan's
``hw_batch`` is still purged (table-wide, not scan-scoped).
"""
from __future__ import annotations

import inspect
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from quirk.db import init_db
from quirk.models import HardwareDriftEvent

from run_scan import _purge_stale_drift_events


def _make_cfg(retention_days):
    return SimpleNamespace(scan=SimpleNamespace(hardware_drift_event_retention_days=retention_days))


def _make_event(host, port, detected_at, event_type="tier_crossing"):
    return HardwareDriftEvent(
        host=host,
        port=port,
        event_type=event_type,
        old_value="tier2",
        new_value="tier1",
        detected_at=detected_at,
    )


def _session(tmp_path):
    db_path = str(tmp_path / "quirk.db")
    init_db(db_path)
    engine = create_engine(f"sqlite:///{db_path}")
    Session = sessionmaker(bind=engine)
    return Session()


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def test_purge_signature_has_no_hw_batch_parameter():
    """Structural proof of table-wide semantics (T-157-03) — a future
    refactor that reintroduces scan-scoping would fail this assertion."""
    params = inspect.signature(_purge_stale_drift_events).parameters
    assert "hw_batch" not in params


def test_purge_deletes_events_older_than_retention_window(tmp_path):
    session = _session(tmp_path)
    now = _now()
    old_row = _make_event("10.0.0.5", 22, now - timedelta(days=400))
    fresh_row = _make_event("10.0.0.5", 22, now - timedelta(days=10))
    session.add(old_row)
    session.add(fresh_row)
    session.commit()

    cfg = _make_cfg(365)

    deleted = _purge_stale_drift_events(session, cfg)
    session.commit()

    assert deleted == 1
    remaining = session.query(HardwareDriftEvent).filter_by(host="10.0.0.5", port=22).all()
    assert len(remaining) == 1
    assert remaining[0].id == fresh_row.id


def test_purge_is_not_scoped_to_batch_host_port(tmp_path):
    """Pitfall 1 regression test — the single most important assertion in
    this file. A stale drift event for a host NOT in the current scan's
    hw_batch must still be purged, because the purge is table-wide."""
    session = _session(tmp_path)
    now = _now()
    stale_untouched = _make_event("10.0.0.99", 22, now - timedelta(days=400))
    session.add(stale_untouched)
    session.commit()

    # hw_batch (unused by the purge — only present here to prove it has no
    # scoping effect) contains a completely different host.
    hw_batch = [SimpleNamespace(host="10.0.0.1", port=22)]  # noqa: F841
    cfg = _make_cfg(365)

    deleted = _purge_stale_drift_events(session, cfg)
    session.commit()

    assert deleted == 1
    assert session.query(HardwareDriftEvent).filter_by(host="10.0.0.99", port=22).count() == 0


def test_purge_runs_with_empty_batch(tmp_path):
    """Inverts test_hardware_retention_purge.py's empty-batch no-op
    expectation — the drift-event purge has no hw_batch dependency at all,
    so a stale row must still be deleted with zero fresh devices scanned."""
    session = _session(tmp_path)
    now = _now()
    stale_row = _make_event("10.0.0.5", 22, now - timedelta(days=400))
    session.add(stale_row)
    session.commit()

    cfg = _make_cfg(365)

    deleted = _purge_stale_drift_events(session, cfg)
    session.commit()

    assert deleted == 1
    assert session.query(HardwareDriftEvent).filter_by(host="10.0.0.5", port=22).count() == 0


@pytest.mark.parametrize("bad_retention", [0, -1, "abc", None])
def test_purge_skips_on_nonpositive_retention(tmp_path, bad_retention):
    session = _session(tmp_path)
    now = _now()
    stale_row = _make_event("10.0.0.5", 22, now - timedelta(days=400))
    session.add(stale_row)
    session.commit()

    cfg = _make_cfg(bad_retention)

    deleted = _purge_stale_drift_events(session, cfg)
    session.commit()

    assert deleted == 0
    assert session.query(HardwareDriftEvent).filter_by(host="10.0.0.5", port=22).count() == 1


def test_purge_and_insert_share_one_transaction(tmp_path):
    session = _session(tmp_path)
    now = _now()
    stale_row = _make_event("10.0.0.5", 22, now - timedelta(days=400))
    session.add(stale_row)
    session.commit()

    cfg = _make_cfg(365)

    _purge_stale_drift_events(session, cfg)
    fresh_event = _make_event("10.0.0.5", 22, now - timedelta(days=1))
    session.add(fresh_event)
    session.commit()
    fresh_event_id = fresh_event.id
    session.close()

    engine = session.bind
    Session = sessionmaker(bind=engine)
    reopened = Session()

    rows = reopened.query(HardwareDriftEvent).filter_by(host="10.0.0.5", port=22).all()
    assert len(rows) == 1
    assert rows[0].id == fresh_event_id


def test_boundary_row_exactly_at_cutoff_is_retained(tmp_path):
    """Strict `<` cutoff comparison — a row detected_at exactly
    retention_days ago is NOT deleted."""
    session = _session(tmp_path)
    retention_days = 365
    now = _now()
    # A small positive buffer accounts for the few microseconds/seconds of
    # wall-clock drift between this line and the cutoff computed inside
    # _purge_stale_drift_events (which calls its own now() slightly later).
    # Without the buffer this row could land a hair before the real cutoff
    # and get flakily deleted, which is not what this test is verifying.
    boundary_row = _make_event(
        "10.0.0.5", 22, now - timedelta(days=retention_days) + timedelta(seconds=10)
    )
    session.add(boundary_row)
    session.commit()

    cfg = _make_cfg(retention_days)

    deleted = _purge_stale_drift_events(session, cfg)
    session.commit()

    assert deleted == 0
    assert session.query(HardwareDriftEvent).filter_by(host="10.0.0.5", port=22).count() == 1
