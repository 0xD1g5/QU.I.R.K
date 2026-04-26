"""Phase 31: Trend analysis intelligence module.

Stub created in Wave 0 (Plan 01) so test_intelligence_trends.py can be collected
by pytest while remaining in RED state. Wave 1 (Plan 02) implements the full logic.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session


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


def compute_trend_report(
    current_ts: datetime,
    previous_ts: Optional[datetime],
    db: Session,
) -> TrendReport:
    """Compare two scan sessions and return a trend report.

    Accuracy note: Trend accuracy depends on consistent target configuration
    between scans — IP-addressed targets may produce phantom new/resolved
    findings if IPs change. NULL collision with v4.2-era sessions
    (scanned_at IS NULL) is expected behavior per D-13.

    STUB: Not yet implemented. Wave 1 (Plan 02) provides the full implementation.
    """
    raise NotImplementedError(
        "compute_trend_report() is not yet implemented. "
        "Wave 1 (Plan 02) implements this function."
    )
