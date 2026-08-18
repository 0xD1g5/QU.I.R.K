"""Phase 155 Plan 02 (HWLC-04) — hardware_drift_events table creation tests.

Covers idempotent table creation via init_db() and the HardwareDriftEvent
ORM model's column shape / round-trip behavior. Mirrors the
tmp_path SQLite + create_engine + sessionmaker pattern already used in
tests/test_hardware_projection_sites.py.
"""
from __future__ import annotations

import datetime

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from quirk.db import _ensure_vendor_pqc_trend_events_table, init_db
from quirk.models import HardwareDriftEvent, VendorPqcTrendEvent


def test_init_db_creates_hardware_drift_events_table(tmp_path):
    """A fresh init_db() call creates the hardware_drift_events table."""
    db_path = str(tmp_path / "quirk.db")
    init_db(db_path)

    engine = create_engine(f"sqlite:///{db_path}")
    tables = inspect(engine).get_table_names()
    assert "hardware_drift_events" in tables


def test_init_db_is_idempotent_for_hardware_drift_events(tmp_path):
    """Calling init_db() twice does not raise and leaves exactly one table
    with unchanged columns (idempotency via checkfirst=True)."""
    db_path = str(tmp_path / "quirk.db")
    init_db(db_path)
    init_db(db_path)  # must not raise

    engine = create_engine(f"sqlite:///{db_path}")
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    assert tables.count("hardware_drift_events") == 1

    cols = {c["name"] for c in inspector.get_columns("hardware_drift_events")}
    assert cols == {
        "id", "host", "port", "event_type", "old_value", "new_value",
        "detected_at", "confirmed_at", "is_partial_scan",
    }


def test_hardware_drift_event_row_round_trips(tmp_path):
    """A HardwareDriftEvent row can be inserted and read back with all
    fields round-tripping, including confirmed_at=None."""
    db_path = str(tmp_path / "quirk.db")
    init_db(db_path)

    engine = create_engine(f"sqlite:///{db_path}")
    Session = sessionmaker(bind=engine)
    session = Session()
    detected_at = datetime.datetime(2026, 8, 14, 12, 0, 0)
    session.add(HardwareDriftEvent(
        host="10.0.0.5",
        port=22,
        event_type="tier_crossing",
        old_value="Tier 2",
        new_value="Tier 1",
        detected_at=detected_at,
        confirmed_at=None,
    ))
    session.commit()

    try:
        row = session.query(HardwareDriftEvent).filter_by(host="10.0.0.5").one()
        assert row.port == 22
        assert row.event_type == "tier_crossing"
        assert row.old_value == "Tier 2"
        assert row.new_value == "Tier 1"
        assert row.detected_at == detected_at
        assert row.confirmed_at is None
    finally:
        session.close()


def test_hardware_drift_event_docstring_names_all_event_types():
    """HardwareDriftEvent.__doc__ names all four event_type values."""
    doc = HardwareDriftEvent.__doc__
    for value in (
        "tier_crossing", "upstream_mitigated_change", "cve_delta", "eol_state_change",
    ):
        assert value in doc


# ---------------------------------------------------------------------------
# Phase 160 Plan 01 (HWLC-17) — vendor_pqc_trend_events table tests
# (pytest -k vendor selects this group)
# ---------------------------------------------------------------------------


def test_init_db_creates_vendor_pqc_trend_events_table(tmp_path):
    """A fresh init_db() call creates the vendor_pqc_trend_events table."""
    db_path = str(tmp_path / "quirk.db")
    init_db(db_path)

    engine = create_engine(f"sqlite:///{db_path}")
    tables = inspect(engine).get_table_names()
    assert "vendor_pqc_trend_events" in tables


def test_ensure_vendor_pqc_trend_events_table_is_idempotent(tmp_path):
    """Calling _ensure_vendor_pqc_trend_events_table(engine) twice does not
    raise (idempotent)."""
    db_path = str(tmp_path / "quirk.db")
    engine = create_engine(f"sqlite:///{db_path}")
    _ensure_vendor_pqc_trend_events_table(engine)
    _ensure_vendor_pqc_trend_events_table(engine)  # must not raise

    inspector = inspect(engine)
    assert inspector.get_table_names().count("vendor_pqc_trend_events") == 1


def test_vendor_pqc_trend_events_table_has_no_host_or_port_columns(tmp_path):
    """The vendor-scoped table's column set contains exactly the seven
    locked columns and neither host nor port."""
    db_path = str(tmp_path / "quirk.db")
    init_db(db_path)

    engine = create_engine(f"sqlite:///{db_path}")
    inspector = inspect(engine)
    cols = {c["name"] for c in inspector.get_columns("vendor_pqc_trend_events")}
    assert cols == {
        "id", "vendor", "event_type", "old_value", "new_value",
        "detected_at", "confirmed_at",
    }
    assert "host" not in cols
    assert "port" not in cols


def test_vendor_pqc_trend_event_row_round_trips(tmp_path):
    """A VendorPqcTrendEvent row can be inserted and read back with all
    fields round-tripping, including confirmed_at=None."""
    db_path = str(tmp_path / "quirk.db")
    init_db(db_path)

    engine = create_engine(f"sqlite:///{db_path}")
    Session = sessionmaker(bind=engine)
    session = Session()
    detected_at = datetime.datetime(2026, 8, 18, 12, 0, 0)
    session.add(VendorPqcTrendEvent(
        vendor="Cisco",
        event_type="pqc_status_change",
        old_value="unsupported",
        new_value="partial",
        detected_at=detected_at,
        confirmed_at=None,
    ))
    session.commit()

    try:
        row = session.query(VendorPqcTrendEvent).filter_by(vendor="Cisco").one()
        assert row.event_type == "pqc_status_change"
        assert row.old_value == "unsupported"
        assert row.new_value == "partial"
        assert row.detected_at == detected_at
        assert row.confirmed_at is None
    finally:
        session.close()
