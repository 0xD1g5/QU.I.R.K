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

from quirk.db import init_db
from quirk.models import HardwareDriftEvent


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
        "detected_at", "confirmed_at",
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
