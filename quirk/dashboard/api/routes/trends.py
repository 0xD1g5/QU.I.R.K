"""GET /api/trends — trend report for the two most recent distinct scan sessions.

Returns HTTP 200 with score_delta=null and zeroed counts when fewer than two
distinct sessions exist (D-06). NULL scanned_at rows are excluded from session
grouping and endpoint fetches (D-13).

Session grouping uses func.strftime second-truncated grouping to match the
pattern in scan.py:457 — each session's endpoints share a common session_start
timestamp with microsecond precision, so we truncate to the second to produce
one logical session row per scan run.
"""
from __future__ import annotations

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from quirk.dashboard.api.deps import get_db
from quirk.dashboard.api.schemas import (
    SampleFinding,
    TrendReportResponse,
)
from quirk.intelligence.trends import compute_trend_report
from quirk.models import CryptoEndpoint

router = APIRouter()


def _list_session_timestamps(db: Session) -> List[datetime]:
    """Return up to 10 most recent distinct session timestamps (newest first).

    Uses the verbatim strftime grouping pattern from scan.py:457-472. Excludes
    NULL scanned_at rows (D-13) via explicit isnot(None) filter.
    """
    ts_sec = func.strftime(
        "%Y-%m-%d %H:%M:%S", CryptoEndpoint.scanned_at
    ).label("ts_sec")
    rows = (
        db.query(ts_sec)
        .filter(CryptoEndpoint.scanned_at.isnot(None))
        .group_by("ts_sec")
        .order_by(ts_sec.desc())
        .limit(10)
        .all()
    )
    return [datetime.fromisoformat(r.ts_sec) for r in rows]


@router.get("/trends", response_model=TrendReportResponse)
def get_trends(db: Session = Depends(get_db)) -> TrendReportResponse:
    """GET /api/trends — trend report for the two most recent distinct scan sessions.

    Returns HTTP 200 with score_delta=null and zeroed counts when fewer than two
    distinct sessions exist (D-06). NULL scanned_at rows excluded (D-13).
    """
    sessions = _list_session_timestamps(db)

    # 0-session case: empty DB — return default TrendReportResponse with all nulls/zeros
    if len(sessions) == 0:
        return TrendReportResponse()

    # 1-session case (D-06): single-session response, score_delta=None
    if len(sessions) == 1:
        report = compute_trend_report(
            current_ts=sessions[0],
            previous_ts=None,
            db=db,
        )
        return _to_response(report)

    # 2+ session case: compare two most recent distinct sessions
    report = compute_trend_report(
        current_ts=sessions[0],
        previous_ts=sessions[1],
        db=db,
    )
    return _to_response(report)


def _to_response(report) -> TrendReportResponse:
    """Convert TrendReport dataclass to TrendReportResponse Pydantic model."""
    return TrendReportResponse(
        current_session_ts=report.current_session_ts,
        previous_session_ts=report.previous_session_ts,
        current_score=report.current_score,
        previous_score=report.previous_score,
        score_delta=report.score_delta,
        new_high=report.new_high,
        new_medium=report.new_medium,
        new_low=report.new_low,
        resolved_high=report.resolved_high,
        resolved_medium=report.resolved_medium,
        resolved_low=report.resolved_low,
        scan_errors_new_count=report.scan_errors_new_count,
        scan_errors_resolved_count=report.scan_errors_resolved_count,
        new_findings_sample=[
            SampleFinding(
                host=s.host,
                port=s.port,
                protocol=s.protocol,
                severity=s.severity,
            )
            for s in report.new_findings_sample
        ],
        resolved_findings_sample=[
            SampleFinding(
                host=s.host,
                port=s.port,
                protocol=s.protocol,
                severity=s.severity,
            )
            for s in report.resolved_findings_sample
        ],
    )
