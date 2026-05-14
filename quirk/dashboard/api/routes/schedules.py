"""Schedules CRUD router — Phase 63 Plan 03 / SCHED-03.

Four endpoint families:
  GET    /api/schedules                list all schedules with next_run_at + last_run_status (200)
  POST   /api/schedules                create a schedule (201/400/409)
  PATCH  /api/schedules/{schedule_id}  toggle enabled flag (200/404)
  DELETE /api/schedules/{schedule_id}  delete schedule + runs (204/404)

Per CONTEXT.md D-04: first writable dashboard route — auth + CSRF at router level.
Per CONTEXT.md D-06: next_run_at computed on-the-fly via croniter, never stored.
Per RESEARCH.md Pitfall 1: all datetimes tz-naive UTC (datetime.now(timezone.utc).replace(tzinfo=None)).
Per RESEARCH.md Pitfall 3 / T-63-16: IntegrityError → fixed 409 message, never stringified.
SQLite FK cascade: explicit ScheduledRun delete before ScheduledScan delete.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Optional

from croniter import croniter
from fastapi import APIRouter, Depends, HTTPException
from quirk.errors import format_error
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from quirk.dashboard.api.deps import get_db
from quirk.dashboard.api.middleware.auth import require_auth
from quirk.dashboard.api.middleware.csrf import require_csrf
from quirk.models import ScheduledRun, ScheduledScan

router = APIRouter(dependencies=[Depends(require_auth), Depends(require_csrf)])
logger = logging.getLogger(__name__)


# ---------- Pydantic models (inline per D-11) ----------

class ScheduleCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, pattern=r"^[A-Za-z0-9_\-\.]+$")
    cron_expr: str = Field(..., min_length=1, max_length=128)
    target: str = Field(..., min_length=1, max_length=512)
    profile: Optional[str] = Field(default=None, max_length=64)


class ScheduleTogglePayload(BaseModel):
    enabled: bool


class ScheduleResponse(BaseModel):
    id: int
    name: str
    cron_expr: str
    target: str
    profile: Optional[str]
    enabled: bool
    last_run_at: Optional[str]      # ISO-8601 string
    next_run_at: Optional[str]      # ISO-8601 string, computed via croniter
    last_run_status: Optional[str]  # most recent ScheduledRun.status, or None
    created_at: str


class ScheduleListResponse(BaseModel):
    schedules: List[ScheduleResponse]


# ---------- Helpers ----------

def _utcnow_naive() -> datetime:
    """Return current UTC datetime as tz-naive (Pitfall 1 — matches Plan 02 convention)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt else None


def _compute_next_run(s: ScheduledScan) -> Optional[datetime]:
    """Compute next run time on-the-fly (D-06 — never stored as persistent column)."""
    if not s.enabled:
        return None
    base = s.last_run_at or _utcnow_naive()
    try:
        return croniter(s.cron_expr, base).get_next(datetime)
    except Exception:
        return None  # invalid cron — should not happen post-validation


def _last_run_status(db: Session, schedule_id: int) -> Optional[str]:
    row = (
        db.query(ScheduledRun)
        .filter(ScheduledRun.schedule_id == schedule_id)
        .order_by(ScheduledRun.dispatched_at.desc())
        .first()
    )
    return row.status if row else None


def _get_or_404(db: Session, schedule_id: int) -> ScheduledScan:
    row = db.get(ScheduledScan, schedule_id)
    if row is None:
        raise HTTPException(status_code=404, detail=format_error("SCHED-004"))
    return row


def _to_response(db: Session, s: ScheduledScan) -> ScheduleResponse:
    return ScheduleResponse(
        id=s.id,
        name=s.name,
        cron_expr=s.cron_expr,
        target=s.target,
        profile=s.profile,
        enabled=bool(s.enabled),
        last_run_at=_iso(s.last_run_at),
        next_run_at=_iso(_compute_next_run(s)),
        last_run_status=_last_run_status(db, s.id),
        created_at=_iso(s.created_at) or "",
    )


# ---------- Endpoints ----------

@router.get("/schedules", response_model=ScheduleListResponse)
def list_schedules(db: Session = Depends(get_db)) -> ScheduleListResponse:
    """List all scheduled scans, ordered by id ascending."""
    rows = db.query(ScheduledScan).order_by(ScheduledScan.id.asc()).all()
    return ScheduleListResponse(schedules=[_to_response(db, s) for s in rows])


@router.post("/schedules", status_code=201, response_model=ScheduleResponse)
def create_schedule(
    payload: ScheduleCreateRequest,
    db: Session = Depends(get_db),
) -> ScheduleResponse:
    """Create a new scheduled scan. Returns 400 for invalid cron, 409 for duplicate name."""
    if not croniter.is_valid(payload.cron_expr):
        raise HTTPException(
            status_code=400,
            detail=format_error("SCHED-002"),
        )
    row = ScheduledScan(
        name=payload.name,
        cron_expr=payload.cron_expr,
        target=payload.target,
        profile=payload.profile,
        enabled=True,
        last_run_at=None,
        created_at=_utcnow_naive(),
    )
    db.add(row)
    try:
        db.flush()
        db.commit()
        db.refresh(row)
    except IntegrityError:
        db.rollback()
        # T-63-16 / LEAK-02: fixed message, never stringify the exception
        raise HTTPException(
            status_code=409,
            detail=format_error("SCHED-003"),
        )
    return _to_response(db, row)


@router.patch("/schedules/{schedule_id}", response_model=ScheduleResponse)
def update_schedule(
    schedule_id: int,
    payload: ScheduleTogglePayload,
    db: Session = Depends(get_db),
) -> ScheduleResponse:
    """Toggle the enabled flag on a schedule."""
    row = _get_or_404(db, schedule_id)
    row.enabled = payload.enabled
    db.commit()
    db.refresh(row)
    return _to_response(db, row)


@router.delete("/schedules/{schedule_id}", status_code=204)
def delete_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
) -> None:
    """Delete a schedule and all its run history. SQLite has no FK enforcement — explicit cascade."""
    row = _get_or_404(db, schedule_id)
    # Explicit cascade: delete runs first (SQLite FK enforcement is opt-in PRAGMA only)
    db.query(ScheduledRun).filter(
        ScheduledRun.schedule_id == schedule_id
    ).delete(synchronize_session=False)
    db.delete(row)
    db.commit()
    return None
