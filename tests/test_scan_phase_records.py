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
