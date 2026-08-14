"""Phase 154 Plan 04 (HWLC-03) — hardware history retention purge tests.

Confirms ``run_scan._purge_stale_hardware_history`` enforces a time-based
(not row-count) retention window (D-10), is scoped strictly to the
(host, port) pairs present in the current scan batch (never table-wide),
is hard-guarded against a non-int/zero/negative retention value wiping all
history, and shares one transaction with the caller's insert loop.
"""
from __future__ import annotations

import datetime
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from quirk.db import init_db
from quirk.models import HardwareDevice

import run_scan


def _make_cfg(retention_days):
    return SimpleNamespace(scan=SimpleNamespace(hardware_history_retention_days=retention_days))


def _make_device(host, port, scanned_at, vendor="Cisco Systems"):
    return HardwareDevice(
        host=host,
        port=port,
        vendor=vendor,
        pqc_status="unsupported",
        confidence="high",
        fingerprint_method="ssh_banner",
        scanned_at=scanned_at,
        probe_status="success",
    )


def _session(tmp_path):
    db_path = str(tmp_path / "quirk.db")
    init_db(db_path)
    engine = create_engine(f"sqlite:///{db_path}")
    Session = sessionmaker(bind=engine)
    return Session()


def test_purge_deletes_rows_older_than_retention_window(tmp_path):
    session = _session(tmp_path)
    now = datetime.datetime.utcnow()
    old_row = _make_device("10.0.0.5", 22, now - datetime.timedelta(days=400))
    fresh_row = _make_device("10.0.0.5", 22, now)
    session.add(old_row)
    session.add(fresh_row)
    session.commit()

    hw_batch = [SimpleNamespace(host="10.0.0.5", port=22)]
    cfg = _make_cfg(180)

    deleted = run_scan._purge_stale_hardware_history(session, hw_batch, cfg)
    session.commit()

    assert deleted == 1
    remaining = session.query(HardwareDevice).filter_by(host="10.0.0.5", port=22).all()
    assert len(remaining) == 1
    assert remaining[0].id == fresh_row.id


def test_purge_is_scoped_to_batch_host_port(tmp_path):
    session = _session(tmp_path)
    now = datetime.datetime.utcnow()
    old_a = _make_device("10.0.0.5", 22, now - datetime.timedelta(days=400))
    old_b = _make_device("10.0.0.6", 22, now - datetime.timedelta(days=400))
    session.add(old_a)
    session.add(old_b)
    session.commit()

    # hw_batch only contains the first host:port pair
    hw_batch = [SimpleNamespace(host="10.0.0.5", port=22)]
    cfg = _make_cfg(180)

    deleted = run_scan._purge_stale_hardware_history(session, hw_batch, cfg)
    session.commit()

    assert deleted == 1
    assert session.query(HardwareDevice).filter_by(host="10.0.0.5", port=22).count() == 0
    assert session.query(HardwareDevice).filter_by(host="10.0.0.6", port=22).count() == 1


@pytest.mark.parametrize("bad_retention", [0, -1, "abc"])
def test_purge_skips_on_nonpositive_retention(tmp_path, bad_retention):
    session = _session(tmp_path)
    now = datetime.datetime.utcnow()
    old_row = _make_device("10.0.0.5", 22, now - datetime.timedelta(days=400))
    session.add(old_row)
    session.commit()

    hw_batch = [SimpleNamespace(host="10.0.0.5", port=22)]
    cfg = _make_cfg(bad_retention)

    deleted = run_scan._purge_stale_hardware_history(session, hw_batch, cfg)
    session.commit()

    assert deleted == 0
    assert session.query(HardwareDevice).filter_by(host="10.0.0.5", port=22).count() == 1


def test_purge_with_empty_batch_is_noop(tmp_path):
    session = _session(tmp_path)
    now = datetime.datetime.utcnow()
    old_row = _make_device("10.0.0.5", 22, now - datetime.timedelta(days=400))
    session.add(old_row)
    session.commit()

    deleted = run_scan._purge_stale_hardware_history(session, [], _make_cfg(180))
    session.commit()

    assert deleted == 0
    assert session.query(HardwareDevice).filter_by(host="10.0.0.5", port=22).count() == 1


def test_purge_and_insert_share_one_transaction(tmp_path):
    session = _session(tmp_path)
    now = datetime.datetime.utcnow()
    old_row = _make_device("10.0.0.5", 22, now - datetime.timedelta(days=400))
    session.add(old_row)
    session.commit()

    new_device = _make_device("10.0.0.5", 22, now, vendor="Juniper")
    hw_batch = [new_device]
    cfg = _make_cfg(180)

    run_scan._purge_stale_hardware_history(session, hw_batch, cfg)
    session.add(new_device)
    session.commit()

    rows = session.query(HardwareDevice).filter_by(host="10.0.0.5", port=22).all()
    assert len(rows) == 1
    assert rows[0].vendor == "Juniper"
