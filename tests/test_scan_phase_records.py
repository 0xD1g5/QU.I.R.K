"""Phase 192 OBS-01: ScanPhaseRecord model + _ensure_scan_phase_records_table.

Wave 0 scaffold: nothing writes to this table yet (Plans 03/04/05 do that).
This file locks the schema and migration only.
"""
from __future__ import annotations

import datetime

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from quirk.db import init_db


# ---------------------------------------------------------------------------
# Task 1: ScanPhaseRecord model + reason constants
# ---------------------------------------------------------------------------


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)


def test_scan_phase_record_roundtrip(tmp_path) -> None:
    from quirk.models import ScanPhaseRecord

    db_path = tmp_path / "roundtrip.db"
    engine = init_db(str(db_path))
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        row = ScanPhaseRecord(
            scan_run_id="2026-09-08T00:00:00+00:00",
            phase_name="tls_scanning",
            status="ran",
            duration_sec=4.2,
            recorded_at=_now(),
        )
        session.add(row)
        session.commit()

        fetched = session.query(ScanPhaseRecord).filter_by(
            scan_run_id="2026-09-08T00:00:00+00:00", phase_name="tls_scanning",
        ).one()
        assert fetched.status == "ran"
        assert fetched.duration_sec == 4.2
    finally:
        session.close()


def test_scan_phase_record_duplicate_raises_integrity_error(tmp_path) -> None:
    from quirk.models import ScanPhaseRecord

    db_path = tmp_path / "dup.db"
    engine = init_db(str(db_path))
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        session.add(ScanPhaseRecord(
            scan_run_id="run-1", phase_name="ssh_scanning",
            status="ran", recorded_at=_now(),
        ))
        session.commit()

        session.add(ScanPhaseRecord(
            scan_run_id="run-1", phase_name="ssh_scanning",
            status="skipped", reason="failed", recorded_at=_now(),
        ))
        with pytest.raises(IntegrityError):
            session.commit()
    finally:
        session.rollback()
        session.close()


def test_scan_phase_record_same_phase_different_scan_run_both_persist(tmp_path) -> None:
    from quirk.models import ScanPhaseRecord

    db_path = tmp_path / "diffrun.db"
    engine = init_db(str(db_path))
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        session.add(ScanPhaseRecord(
            scan_run_id="run-1", phase_name="api_scanning",
            status="ran", recorded_at=_now(),
        ))
        session.add(ScanPhaseRecord(
            scan_run_id="run-2", phase_name="api_scanning",
            status="ran", recorded_at=_now(),
        ))
        session.commit()

        count = session.query(ScanPhaseRecord).filter_by(phase_name="api_scanning").count()
        assert count == 2
    finally:
        session.close()


def test_scan_phase_skip_reasons_exact_membership() -> None:
    from quirk.models import SCAN_PHASE_SKIP_REASONS

    assert len(SCAN_PHASE_SKIP_REASONS) == 5
    assert SCAN_PHASE_SKIP_REASONS == frozenset({
        "disabled-by-config",
        "missing-extra",
        "no-eligible-targets",
        "missing-credentials",
        "failed",
    })


# ---------------------------------------------------------------------------
# Task 2: _ensure_scan_phase_records_table migration + init_db() wiring
# ---------------------------------------------------------------------------


def test_init_db_creates_scan_phase_records_table_on_fresh_db(tmp_path) -> None:
    from sqlalchemy import inspect as sa_inspect

    db_path = tmp_path / "fresh.db"
    engine = init_db(str(db_path))
    names = set(sa_inspect(engine).get_table_names())
    assert "scan_phase_records" in names


def test_init_db_twice_does_not_raise_and_leaves_one_table(tmp_path) -> None:
    from sqlalchemy import inspect as sa_inspect

    db_path = tmp_path / "twice.db"
    engine1 = init_db(str(db_path))
    names1 = set(sa_inspect(engine1).get_table_names())
    assert "scan_phase_records" in names1

    engine2 = init_db(str(db_path))
    names2 = set(sa_inspect(engine2).get_table_names())
    assert names1 == names2


def test_init_db_adds_table_to_preexisting_db_without_touching_others(tmp_path) -> None:
    """A DB with other QUIRK tables but no scan_phase_records gets the table
    added without existing tables being dropped or altered."""
    from sqlalchemy import inspect as sa_inspect
    from quirk.models import Base, ScanPhaseRecord

    db_path = tmp_path / "preexisting.db"

    # Simulate a pre-Phase-192 DB: create all tables EXCEPT scan_phase_records.
    from sqlalchemy import create_engine
    engine = create_engine(f"sqlite:///{db_path}")
    tables_without_new = [
        t for name, t in Base.metadata.tables.items() if name != "scan_phase_records"
    ]
    Base.metadata.create_all(engine, tables=tables_without_new, checkfirst=True)

    names_before = set(sa_inspect(engine).get_table_names())
    assert "scan_phase_records" not in names_before
    assert "scan_checkpoints" in names_before  # a pre-existing table sentinel

    engine2 = init_db(str(db_path))
    names_after = set(sa_inspect(engine2).get_table_names())
    assert "scan_phase_records" in names_after
    assert names_before.issubset(names_after)
