"""Phase 65 — best-effort scan_jobs progress updates from run_scan.py subprocess.

All functions are wrapped in a bare `except Exception: pass` — progress
updates must NEVER crash the scan. The scan itself is the source of truth;
progress is observational only.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional


def _utcnow_naive() -> datetime:
    """Return current UTC datetime as tz-naive (matches schedules.py convention; Pitfall 6 in RESEARCH.md)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _open_session(db_path: str):
    """Open a short-lived SQLAlchemy session against the given SQLite file."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    return Session()


def update_job_stage(db_path: str, job_id: str, stage: str) -> None:
    """Update scan_jobs.current_stage. Silent no-op on any failure."""
    try:
        from quirk.models import ScanJob
        with _open_session(db_path) as db:
            row = db.get(ScanJob, job_id)
            if row is not None:
                row.current_stage = stage
                db.commit()
    except Exception:
        pass


def mark_job_completed(db_path: str, job_id: str, scan_run_id: Optional[str]) -> None:
    """Flip scan_jobs row to status=completed with scan_run_id set."""
    try:
        from quirk.models import ScanJob
        with _open_session(db_path) as db:
            row = db.get(ScanJob, job_id)
            if row is not None:
                row.status = "completed"
                row.scan_run_id = scan_run_id
                row.completed_at = _utcnow_naive()
                db.commit()
    except Exception:
        pass


def mark_job_failed(db_path: str, job_id: str, error_message: str) -> None:
    """Flip scan_jobs row to status=failed with error_message set."""
    try:
        from quirk.models import ScanJob
        with _open_session(db_path) as db:
            row = db.get(ScanJob, job_id)
            if row is not None:
                row.status = "failed"
                row.error_message = error_message[:4096]  # cap to prevent oversize
                row.completed_at = _utcnow_naive()
                db.commit()
    except Exception:
        pass
