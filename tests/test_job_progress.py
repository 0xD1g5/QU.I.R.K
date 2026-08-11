"""Phase 65 — update_job_stage helper tests."""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from quirk.cli.job_progress import (
    update_job_stage,
    mark_job_completed,
    mark_job_failed,
    update_batch_progress,
)
from quirk.models import Base, ScanJob


def _tmp_db_with_row(tmp_path, job_id: str = "j-1"):
    db_file = str(tmp_path / "test.db")
    engine = create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    with Session() as db:
        db.add(ScanJob(
            job_id=job_id,
            status="running",
            target="example.com",
            profile="standard",
            calibration="balanced",
            enable_nmap=False,
        ))
        db.commit()
    return db_file, engine, Session


def test_update_job_stage_updates_running_job(tmp_path):
    db_file, _, Session = _tmp_db_with_row(tmp_path)
    update_job_stage(db_file, "j-1", "tls")
    with Session() as db:
        row = db.get(ScanJob, "j-1")
        assert row.current_stage == "tls"


def test_update_job_stage_noop_when_job_missing(tmp_path):
    db_file, _, Session = _tmp_db_with_row(tmp_path)
    # Should not raise; should silently do nothing
    update_job_stage(db_file, "does-not-exist", "tls")
    with Session() as db:
        assert db.get(ScanJob, "does-not-exist") is None


def test_update_job_stage_silent_on_db_error(tmp_path):
    # Bad path -> SQLAlchemy raises, helper must swallow
    update_job_stage(str(tmp_path / "nonexistent-dir" / "x.db"), "j-1", "tls")
    # Reaching this line means no exception escaped — test passes


def test_update_batch_progress_happy_path(tmp_path):
    db_file, _, Session = _tmp_db_with_row(tmp_path)
    update_batch_progress(db_file, "j-1", 3, 12, 2048)
    with Session() as db:
        row = db.get(ScanJob, "j-1")
        assert row.discovery_batch_index == 3
        assert row.discovery_batch_total == 12
        assert row.discovery_hosts_checked == 2048


def test_update_batch_progress_noop_when_job_missing(tmp_path):
    db_file, _, Session = _tmp_db_with_row(tmp_path)
    # Should not raise; should silently do nothing, no row created.
    update_batch_progress(db_file, "does-not-exist", 1, 2, 3)
    with Session() as db:
        assert db.get(ScanJob, "does-not-exist") is None


def test_update_batch_progress_silent_on_db_error(tmp_path):
    # Bad path -> SQLAlchemy raises, helper must swallow ("never crash the scan").
    result = update_batch_progress(
        str(tmp_path / "nonexistent-dir" / "x.db"), "j-1", 1, 2, 3
    )
    assert result is None  # reaching this line with no traceback proves the contract


def test_update_batch_progress_overwrites_on_repeated_calls(tmp_path):
    db_file, _, Session = _tmp_db_with_row(tmp_path)
    update_batch_progress(db_file, "j-1", 1, 12, 256)
    update_batch_progress(db_file, "j-1", 5, 12, 1280)
    with Session() as db:
        row = db.get(ScanJob, "j-1")
        assert row.discovery_batch_index == 5
        assert row.discovery_batch_total == 12
        assert row.discovery_hosts_checked == 1280


# --- v5.11 audit WR-02: per-batch engine disposal -------------------------------
# update_batch_progress() is an O(batches) hot path since Phase 144 removed the
# host-count ceiling, so each short-lived engine must release its SQLite handle
# deterministically instead of relying on CPython refcounting.


def _track_engines(monkeypatch):
    """Wrap sqlalchemy.create_engine, recording (engine, pool-at-creation) pairs.

    Engine.dispose() disposes the current pool and replaces it via pool.recreate(),
    so a pool identity change is real evidence dispose() ran — no mock assertions.
    """
    import sqlalchemy

    real_create_engine = sqlalchemy.create_engine
    created = []

    def tracking_create_engine(*args, **kwargs):
        engine = real_create_engine(*args, **kwargs)
        created.append((engine, engine.pool))
        return engine

    monkeypatch.setattr(sqlalchemy, "create_engine", tracking_create_engine)
    return created


def test_update_batch_progress_disposes_engine_after_each_call(tmp_path, monkeypatch):
    db_file, _, _ = _tmp_db_with_row(tmp_path)
    created = _track_engines(monkeypatch)

    for batch_index in range(1, 4):
        update_batch_progress(db_file, "j-1", batch_index, 3, batch_index * 1024)

    assert len(created) == 3, "each call should open its own short-lived engine"
    for engine, pool_at_creation in created:
        assert engine.pool is not pool_at_creation, (
            "engine.dispose() was never called — the connection pool it was "
            "created with is still installed, so the SQLite handle leaks"
        )


def test_update_batch_progress_disposes_engine_when_job_row_missing(tmp_path, monkeypatch):
    db_file, _, _ = _tmp_db_with_row(tmp_path)
    created = _track_engines(monkeypatch)

    update_batch_progress(db_file, "does-not-exist", 1, 2, 3)

    assert len(created) == 1
    engine, pool_at_creation = created[0]
    assert engine.pool is not pool_at_creation
