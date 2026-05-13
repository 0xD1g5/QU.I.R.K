"""Phase 65 — update_job_stage helper tests."""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from quirk.cli.job_progress import update_job_stage, mark_job_completed, mark_job_failed
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
