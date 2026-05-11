"""Phase 31: Trend analysis intelligence module.

compute_trend_report() is a pure function (D-12: no datetime.now() inside).
The caller supplies current_ts and previous_ts as parameters.

Session grouping uses func.strftime microsecond-precision grouping (%Y-%m-%d %H:%M:%f)
so two scans started within the same second appear as distinct sessions (CR-05).
_fetch_session_endpoints uses a 1-microsecond window to match exactly one session.

NULL scanned_at rows (D-13): v4.2-era endpoints may have scanned_at IS NULL.
These are excluded from session grouping AND from per-session endpoint fetches by
filtering scanned_at.isnot(None) in every query.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Iterable, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from quirk.models import CryptoEndpoint
from quirk.intelligence.evidence import build_evidence_summary
from quirk.intelligence.scoring import compute_readiness_score


# ---------------------------------------------------------------------------
# Severity bucketing
# ---------------------------------------------------------------------------

_SEVERITY_BUCKET = {
    "CRITICAL": "high",
    "HIGH": "high",
    "MEDIUM": "medium",
    "LOW": "low",
    # INFO intentionally absent — excluded from counts and samples (D-05)
}

_SEVERITY_RANK = {
    "CRITICAL": 0,
    "HIGH": 1,
    "MEDIUM": 2,
    "LOW": 3,
}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class SampleFindingItem:
    host: str
    port: int
    protocol: str
    severity: str


@dataclass
class TrendReport:
    current_session_ts: Optional[datetime]
    previous_session_ts: Optional[datetime]
    current_score: Optional[int]
    previous_score: Optional[int]
    score_delta: Optional[int]
    new_high: int
    new_medium: int
    new_low: int
    resolved_high: int
    resolved_medium: int
    resolved_low: int
    scan_errors_new_count: int
    scan_errors_resolved_count: int
    new_findings_sample: List[SampleFindingItem] = field(default_factory=list)
    resolved_findings_sample: List[SampleFindingItem] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _fetch_session_endpoints(db: Session, target_ts: datetime) -> List[CryptoEndpoint]:
    """Fetch all endpoints in the 1-microsecond window (one canonical scanned_at timestamp).

    Uses a 1-microsecond window so only endpoints whose scanned_at equals target_ts
    are returned. This prevents two scans within the same second from being merged
    (CR-05 fix). Excludes NULL scanned_at rows (D-13) via explicit filter.
    """
    endpoints = (
        db.query(CryptoEndpoint)
        .filter(
            CryptoEndpoint.scanned_at >= target_ts,
            CryptoEndpoint.scanned_at < target_ts + timedelta(microseconds=1),
            CryptoEndpoint.scanned_at.isnot(None),
        )
        .all()
    )
    return endpoints


def _bucket_for_severity(sev: str) -> Optional[str]:
    """Map a raw severity string to a display bucket, or None for INFO/unknown."""
    return _SEVERITY_BUCKET.get(sev)


def _count_by_bucket(keys: Iterable[tuple]) -> dict:
    """Count (host, port, protocol, severity) tuples by severity bucket.

    Returns a dict with keys "high", "medium", "low". INFO keys are silently
    ignored (D-05).
    """
    counts: dict = {"high": 0, "medium": 0, "low": 0}
    for _host, _port, _protocol, severity in keys:
        bucket = _bucket_for_severity(severity)
        if bucket is not None:
            counts[bucket] += 1
    return counts


def _sample_findings(
    endpoints: List[CryptoEndpoint],
    target_keys: set,
) -> List[SampleFindingItem]:
    """Return sample findings (max 5) whose match-key is in target_keys.

    Sort order: severity rank asc (CRITICAL=0 → first), then host asc, then port asc.
    Caps at 5 (D-08). INFO severity endpoints are excluded because their keys
    are not present in target_keys (they are never added to new_keys/resolved_keys).
    """
    matched = [
        ep for ep in endpoints
        if (ep.host, ep.port, ep.protocol, ep.severity) in target_keys
    ]
    matched.sort(
        key=lambda ep: (
            _SEVERITY_RANK.get(ep.severity, 99),
            ep.host or "",
            ep.port or 0,
        )
    )
    return [
        SampleFindingItem(
            host=ep.host,
            port=ep.port,
            protocol=ep.protocol,
            severity=ep.severity,
        )
        for ep in matched[:5]
    ]


def _score_for_session(endpoints: List[CryptoEndpoint]) -> int:
    """Compute the readiness score for a list of endpoints.

    Returns score as int (compute_readiness_score always returns int via
    total_score = int(...) — confirmed in scoring.py).
    """
    evidence = build_evidence_summary(endpoints)
    score_dict = compute_readiness_score(evidence)
    return score_dict["score"]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_trend_report(
    current_ts: datetime,
    previous_ts: Optional[datetime],
    db: Session,
) -> TrendReport:
    """Compare two scan sessions and return a trend report.

    D-12: Pure function — no datetime.now() inside. Caller supplies timestamps.
    D-06: When previous_ts is None, returns null-delta single-session response.
    D-13: NULL scanned_at rows are excluded from all session fetches.

    Match key for finding delta: (host, port, protocol, severity) — severity
    included intentionally so a HIGH→MEDIUM transition surfaces as 1 HIGH
    resolved + 1 MEDIUM new (D-03).

    Severity bucketing: CRITICAL/HIGH → "high", MEDIUM → "medium", LOW → "low",
    INFO → excluded from counts and samples (D-05).

    Scan error delta (D-04/D-05): rows with scan_error IS NOT NULL are excluded
    from finding delta keys; counted separately as scan_errors_new_count /
    scan_errors_resolved_count.

    Sample arrays (D-08): capped at 5, sorted by severity desc (CRITICAL first),
    then host asc, then port asc.

    Accuracy note: Trend accuracy depends on consistent target configuration
    between scans. IP-addressed targets may produce phantom new/resolved
    findings if IPs change. NULL collision with v4.2-era sessions
    (scanned_at IS NULL) is expected behavior per D-13.
    """
    current_eps = _fetch_session_endpoints(db, current_ts)
    current_score = _score_for_session(current_eps) if current_eps else None

    # D-06: single-session early return — no previous data to compare
    if previous_ts is None:
        return TrendReport(
            current_session_ts=current_ts,
            previous_session_ts=None,
            current_score=current_score,
            previous_score=None,
            score_delta=None,
            new_high=0,
            new_medium=0,
            new_low=0,
            resolved_high=0,
            resolved_medium=0,
            resolved_low=0,
            scan_errors_new_count=0,
            scan_errors_resolved_count=0,
        )

    previous_eps = _fetch_session_endpoints(db, previous_ts)
    previous_score = _score_for_session(previous_eps) if previous_eps else None
    score_delta = (
        current_score - previous_score
        if current_score is not None and previous_score is not None
        else None
    )

    # D-04: build match-key sets, excluding scan_error rows from finding delta.
    # Hosts that errored in the current session are excluded from BOTH sides:
    # a scan_error in current means we cannot determine if previous findings
    # for that host are resolved or still present — so exclude them to avoid
    # phantom "resolved" entries.
    current_error_hosts = {
        (ep.host, ep.port, ep.protocol)
        for ep in current_eps
        if ep.scan_error is not None
    }
    current_keys = {
        (ep.host, ep.port, ep.protocol, ep.severity)
        for ep in current_eps
        if ep.scan_error is None
    }
    previous_keys = {
        (ep.host, ep.port, ep.protocol, ep.severity)
        for ep in previous_eps
        if ep.scan_error is None
        and (ep.host, ep.port, ep.protocol) not in current_error_hosts
    }

    new_keys = current_keys - previous_keys
    resolved_keys = previous_keys - current_keys

    new_counts = _count_by_bucket(new_keys)
    resolved_counts = _count_by_bucket(resolved_keys)

    # D-05: scan error count delta computed independently of finding delta.
    # Phase 41 / D-15: exclude category='missing_extra' so that "user did not
    # install [motion] this run" does not register as a scan-error regression.
    # getattr(..., None) tolerates older DB rows that predate the column.
    cur_err = sum(
        1 for ep in current_eps
        if ep.scan_error is not None
        and getattr(ep, "scan_error_category", None) != "missing_extra"
    )
    prev_err = sum(
        1 for ep in previous_eps
        if ep.scan_error is not None
        and getattr(ep, "scan_error_category", None) != "missing_extra"
    )
    scan_errors_new_count = max(0, cur_err - prev_err)
    scan_errors_resolved_count = max(0, prev_err - cur_err)

    # D-08: top-5 sample arrays, sorted by severity then host then port
    new_samples = _sample_findings(current_eps, new_keys)
    resolved_samples = _sample_findings(previous_eps, resolved_keys)

    return TrendReport(
        current_session_ts=current_ts,
        previous_session_ts=previous_ts,
        current_score=current_score,
        previous_score=previous_score,
        score_delta=score_delta,
        new_high=new_counts["high"],
        new_medium=new_counts["medium"],
        new_low=new_counts["low"],
        resolved_high=resolved_counts["high"],
        resolved_medium=resolved_counts["medium"],
        resolved_low=resolved_counts["low"],
        scan_errors_new_count=scan_errors_new_count,
        scan_errors_resolved_count=scan_errors_resolved_count,
        new_findings_sample=new_samples,
        resolved_findings_sample=resolved_samples,
    )
