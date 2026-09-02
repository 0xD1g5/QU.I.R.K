"""GET /api/trends — trend report for the two most recent distinct scan sessions.

Returns HTTP 200 with score_delta=null and zeroed counts when fewer than two
distinct sessions exist (D-06). NULL scanned_at rows are excluded from session
grouping and endpoint fetches (D-13).

Session grouping uses func.strftime microsecond-precision grouping (%Y-%m-%d %H:%M:%f)
to produce one logical session row per scan run. This ensures two scans started
within the same second appear as distinct timeline points (CR-05 fix).
"""
from __future__ import annotations

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, Query
from quirk.dashboard.api.middleware.auth import require_auth
from sqlalchemy import func
from sqlalchemy.orm import Session

from quirk.dashboard.api.deps import get_db
from quirk.dashboard.api.schemas import (
    FindingCounts,
    SampleFinding,
    SeverityTransitionResponse,
    TrendReportResponse,
    TrendSessionPoint,
    TrendTimelineResponse,
)
from quirk.intelligence.evidence import build_evidence_summary
from quirk.intelligence.scoring import compute_readiness_score
from quirk.intelligence.trends import (
    _count_by_bucket,
    _fetch_session_endpoints,
    compute_trend_report,
)
from quirk.models import CryptoEndpoint

router = APIRouter(dependencies=[Depends(require_auth)])


def _list_session_timestamps(db: Session) -> List[datetime]:
    """Return up to 10 most recent distinct session timestamps (newest first).

    RVW-003: a session is one `scan_run_id`, represented by its *earliest*
    endpoint timestamp. Grouping on the millisecond-precision strftime key
    instead made one scan look like many sessions — a scan's stages each stamp
    their own rows as they run, so a 10-endpoint scan could yield 10 "sessions",
    and the trend delta was then computed between two stages of the same scan.

    Rows predating the column (scan_run_id IS NULL) keep the old key so existing
    databases still render trends: millisecond-precision strftime (%Y-%m-%d
    %H:%M:%f) — SQLite's %f returns 3 decimal digits (ms), not 6 (µs) — so two
    scans started in different milliseconds stay distinct (CR-05). NULL
    scanned_at rows are excluded (D-13) via explicit isnot(None) filter.
    """
    rows = (
        db.query(CryptoEndpoint.scanned_at, CryptoEndpoint.scan_run_id)
        .filter(CryptoEndpoint.scanned_at.isnot(None))
        .all()
    )
    earliest: dict[str, datetime] = {}
    for row_ts, row_run_id in rows:
        if row_ts is None:
            continue
        if isinstance(row_ts, str):
            try:
                row_ts = datetime.fromisoformat(row_ts)
            except ValueError:
                continue
        # Legacy key preserves millisecond precision by truncating microseconds
        # to a whole millisecond — the same bucket the strftime %f key produced.
        key = row_run_id or row_ts.replace(
            microsecond=(row_ts.microsecond // 1000) * 1000
        ).isoformat()
        prev = earliest.get(key)
        if prev is None or row_ts < prev:
            earliest[key] = row_ts
    return sorted(earliest.values(), reverse=True)[:10]


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
        severity_transitions=[
            SeverityTransitionResponse(
                host=t.host,
                port=t.port,
                protocol=t.protocol,
                previous_severity=t.previous_severity,
                current_severity=t.current_severity,
            )
            for t in report.severity_transitions
        ],
        new_total=report.new_total,
        resolved_total=report.resolved_total,
    )


def _list_session_timestamps_n(db: Session, n: int) -> List[datetime]:
    """Return up to n most recent distinct session timestamps (newest first).

    Variant of _list_session_timestamps() with a parameterized LIMIT.
    Do NOT modify _list_session_timestamps() — it is hardcoded to LIMIT 10
    and consumed by get_trends. (CONTEXT.md D-03)
    Uses microsecond-precision strftime format (%Y-%m-%d %H:%M:%f) — CR-05.
    """
    ts_usec = func.strftime(
        "%Y-%m-%d %H:%M:%f", CryptoEndpoint.scanned_at
    ).label("ts_usec")
    rows = (
        db.query(ts_usec)
        .filter(CryptoEndpoint.scanned_at.isnot(None))
        .group_by("ts_usec")
        .order_by(ts_usec.desc())
        .limit(n)
        .all()
    )
    return [datetime.fromisoformat(r.ts_usec) for r in rows]


@router.get("/trends/timeline", response_model=TrendTimelineResponse)
def get_trends_timeline(
    n: int = Query(default=30, ge=2, le=200),
    db: Session = Depends(get_db),
) -> TrendTimelineResponse:
    """Multi-scan timeline endpoint (TREND-01).

    Returns up to n most-recent sessions, newest-first. Each session
    carries the overall readiness score, all 6 subscores, and severity-
    bucketed finding counts. Auth is inherited from the router-level
    dependencies=[Depends(require_auth)] declaration — no per-route
    annotation needed (RESEARCH.md Pitfall 5).
    """
    sessions = _list_session_timestamps_n(db, n)
    if not sessions:
        return TrendTimelineResponse(sessions=[])
    points: List[TrendSessionPoint] = []
    for ts in sessions:
        eps = _fetch_session_endpoints(db, ts)
        if not eps:
            continue
        evidence = build_evidence_summary(eps)
        score_dict = compute_readiness_score(evidence)
        sub = score_dict["subscores"]
        keys = [
            (ep.host, ep.port, ep.protocol)
            for ep in eps
            if ep.scan_error is None
        ]
        sev_map = {
            (ep.host, ep.port, ep.protocol): ep.severity
            for ep in eps
            if ep.scan_error is None
        }
        counts = _count_by_bucket(keys, sev_map)
        points.append(
            TrendSessionPoint(
                session_ts=ts.isoformat(),
                score=int(score_dict["score"]),
                subscores=sub,
                finding_counts=FindingCounts(
                    high=counts.get("high", 0),
                    medium=counts.get("medium", 0),
                    low=counts.get("low", 0),
                ),
            )
        )
    return TrendTimelineResponse(sessions=points)
