"""Phase 237 COUNT-06 (D-07/D-09): the one definition of scan completeness.

A ``scan_run_id`` is *complete* iff it has a ``scan_checkpoints`` row with
``stage == 'reports'`` and ``status == 'completed'``, or it has no checkpoint
rows at all (legacy, sensor, import and merge sessions, D-07/D-14). It is
*incomplete* when it has checkpoint rows but no completed reports row, and
*running* when, in addition, a ScanJob in status queued/running carries that
run id (D-15).

Residual (D-14): scans written before CLI and scheduled scans started writing
checkpoints have no checkpoint rows and so read as complete.

Every "latest scan" resolver must call this module rather than re-deriving the
rule (plans 237-04 and 237-06 wire it). The rule matches
``run_scan._handle_list_resumable``. Read-only; no FastAPI or pydantic import.
"""
from __future__ import annotations

from typing import Any, Optional, Set


def incomplete_scan_run_ids(db: Any) -> Set[str]:
    """Run ids with checkpoint rows but no completed 'reports' checkpoint."""
    from quirk.models import ScanCheckpoint

    all_ids = {r[0] for r in db.query(ScanCheckpoint.scan_run_id).distinct().all()}
    completed = {
        r[0]
        for r in db.query(ScanCheckpoint.scan_run_id)
        .filter(ScanCheckpoint.stage == "reports", ScanCheckpoint.status == "completed")
        .all()
    }
    return {rid for rid in all_ids if rid is not None and rid not in completed}


def running_scan_run_ids(db: Any) -> Set[str]:
    """Run ids of queued/running ScanJob rows whose scan_run_id is set."""
    from quirk.models import ScanJob

    rows = (
        db.query(ScanJob.scan_run_id)
        .filter(ScanJob.status.in_(("queued", "running")), ScanJob.scan_run_id.isnot(None))
        .all()
    )
    return {r[0] for r in rows}


def session_status(
    run_id: Optional[str], incomplete: Set[str], running: Set[str]
) -> str:
    """Return 'complete' | 'running' | 'incomplete' for one scan_run_id."""
    if not run_id or run_id not in incomplete:
        return "complete"
    if run_id in running:
        return "running"
    return "incomplete"
