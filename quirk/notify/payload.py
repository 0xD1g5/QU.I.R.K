"""quirk.notify.payload — Outbound payload whitelist + DriftSummary content model (Phase 101 ISEC-03).

STUB — implemented fully in Task 2 of Plan 101-02.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from quirk.intelligence.trends import TrendReport


@dataclass
class DriftSummary:
    """Placeholder — full implementation in Task 2."""
    current_score: Optional[int]
    previous_score: Optional[int]
    score_delta: Optional[int]
    score_band: str
    new_high: int
    new_medium: int
    new_low: int
    scan_id: str
    dashboard_url: Optional[str]


def build_drift_summary(
    report: TrendReport,
    dashboard_base_url: Optional[str] = None,
    scan_id: str = "",
) -> DriftSummary:
    """Placeholder — full implementation in Task 2."""
    raise NotImplementedError("Task 2 will implement this")


def to_integration_payload(report: TrendReport) -> dict:
    """Placeholder — full implementation in Task 2."""
    raise NotImplementedError("Task 2 will implement this")
