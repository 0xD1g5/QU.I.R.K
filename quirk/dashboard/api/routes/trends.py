"""GET /api/trends — trend report for the two most recent distinct scan sessions.

Returns HTTP 200 with score_delta=null and zeroed counts when fewer than two
distinct sessions exist (D-06). NULL scanned_at rows are excluded from session
grouping and endpoint fetches (D-13).

Sessions are grouped by scan_run_id via the shared
quirk.intelligence.trends.list_session_timestamps (legacy NULL-run rows fall
back to millisecond buckets, CR-05).
"""
from __future__ import annotations

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, Query
from quirk.dashboard.api.middleware.auth import require_auth
from sqlalchemy.orm import Session

from quirk.dashboard.api._timestamp_utils import stamp_utc_iso
from quirk.dashboard.api.deps import get_db
from quirk.dashboard.api.routes.scan import derive_dashboard_scoring_findings
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
    list_session_timestamps,
)

router = APIRouter(dependencies=[Depends(require_auth)])


def _list_session_timestamps(db: Session) -> List[datetime]:
    """Delegate to the shared lister; kept for existing importers (D-10)."""
    return list_session_timestamps(db, limit=10)


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
            findings_deriver=derive_dashboard_scoring_findings,
        )
        return _to_response(report)

    # 2+ session case: compare two most recent distinct sessions
    report = compute_trend_report(
        current_ts=sessions[0],
        previous_ts=sessions[1],
        db=db,
        findings_deriver=derive_dashboard_scoring_findings,
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
    sessions = list_session_timestamps(db, limit=n)
    if not sessions:
        return TrendTimelineResponse(sessions=[])
    points: List[TrendSessionPoint] = []
    for ts in sessions:
        eps = _fetch_session_endpoints(db, ts)
        if not eps:
            continue
        # Phase 228 D-08/D-12: derive dashboard findings; no try/except on purpose.
        evidence = build_evidence_summary(eps, derive_dashboard_scoring_findings(eps))
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
                session_ts=stamp_utc_iso(ts),
                # Phase 199 / TRIAGE-10: score_dict["score"] may be None (zero
                # domains assessed) or fractional (e.g. 71.4) — both pass
                # through unchanged. An unassessed session carries score=None
                # through TrendSessionPoint; the frontend renders the gap.
                score=score_dict["score"],
                subscores=sub,
                finding_counts=FindingCounts(
                    high=counts.get("high", 0),
                    medium=counts.get("medium", 0),
                    low=counts.get("low", 0),
                ),
            )
        )
    return TrendTimelineResponse(sessions=points)
