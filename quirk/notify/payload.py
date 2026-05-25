"""quirk.notify.payload — Outbound payload whitelist + DriftSummary content model.

Phase 101 ISEC-03 / NOTIFY-01.

This module provides the two primitives that all notification channels and
downstream integration phases MUST consume:

1. DriftSummary — Shared content model, built once from a TrendReport and
   consumed by all channel formatters (mirrors v5.2 ExecContent / build_exec_content).
   Formatters receive this instance and format its fields — they do NOT re-derive
   content from raw TrendReport inputs.

2. to_integration_payload() — Canonical outbound field whitelist that exposes
   ONLY drift-level aggregate fields.  Downstream phases (103 SIEM, 104 Jira,
   105 ServiceNow) MUST call to_integration_payload() before building any
   outbound payload.  Topology fields (host, port, protocol) and
   new_findings_sample / resolved_findings_sample are EXCLUDED (ISEC-03).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from quirk.intelligence.trends import TrendReport


# ---------------------------------------------------------------------------
# DriftSummary — one structured object consumed by all channel formatters
# ---------------------------------------------------------------------------


@dataclass
class DriftSummary:
    """Shared content model consumed by all channel formatters (NOTIFY-01).

    Mirrors v5.2 ExecContent: built once by build_drift_summary(), channel
    formatters receive this instance and format its fields — they do not
    re-derive content from raw TrendReport inputs.

    score_band: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "GOOD"
    dashboard_url: None when dashboard_base_url is not configured.
    """

    current_score: Optional[int]
    previous_score: Optional[int]
    score_delta: Optional[int]
    score_band: str           # "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "GOOD"
    new_high: int
    new_medium: int
    new_low: int
    scan_id: str              # ISO timestamp from current_session_ts
    dashboard_url: Optional[str]


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _score_to_band(score: Optional[int]) -> str:
    """Map a readiness score (0–100) to a severity band string.

    Score bands mirror the readiness tiers used in the CLI/HTML/PDF reports.
    None (first scan, no previous data) is treated as CRITICAL (worst-case).
    """
    if score is None:
        return "CRITICAL"
    if score <= 30:
        return "CRITICAL"
    if score <= 50:
        return "HIGH"
    if score <= 65:
        return "MEDIUM"
    if score <= 79:
        return "LOW"
    return "GOOD"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_drift_summary(
    report: TrendReport,
    dashboard_base_url: Optional[str] = None,
    scan_id: str = "",
) -> DriftSummary:
    """Build the canonical DriftSummary from a TrendReport.

    Call once per dispatch cycle.  All channel formatters consume the returned
    DriftSummary — they do not call this function or touch TrendReport directly.

    Args:
        report: The computed TrendReport for the current scan session.
        dashboard_base_url: Optional base URL for the QUIRK dashboard.  When
            set, dashboard_url will be derived pointing to the trends view for
            this scan.  When unset, dashboard_url is None.
        scan_id: ISO timestamp string identifying the current scan session
            (typically report.current_session_ts.isoformat()).

    Returns:
        A DriftSummary instance ready for consumption by channel formatters.
    """
    score_band = _score_to_band(report.current_score)

    dashboard_url: Optional[str] = None
    if dashboard_base_url:
        # Strip trailing slash, append the trends route
        base = dashboard_base_url.rstrip("/")
        dashboard_url = f"{base}/trends"

    return DriftSummary(
        current_score=report.current_score,
        previous_score=report.previous_score,
        score_delta=report.score_delta,
        score_band=score_band,
        new_high=report.new_high,
        new_medium=report.new_medium,
        new_low=report.new_low,
        scan_id=scan_id,
        dashboard_url=dashboard_url,
    )


def to_integration_payload(report: TrendReport) -> dict:
    """Return a safe outbound dict containing ONLY whitelisted aggregate fields.

    ISEC-03 ENFORCEMENT: This is the single canonical outbound-field whitelist.
    Downstream phases (103 SIEM, 104 Jira, 105 ServiceNow) MUST call this
    function before building any outbound payload.  The returned dict contains
    NO topology fields (host, port, protocol) and NO new_findings_sample /
    resolved_findings_sample content.

    Whitelisted fields (drift-level aggregates only):
      current_score, previous_score, score_delta
      new_high, new_medium, new_low
      resolved_high, resolved_medium, resolved_low
      scan_errors_new_count
      current_session_ts (ISO string or None)
      previous_session_ts (ISO string or None)

    EXCLUDED (ISEC-03 topology exclusion):
      new_findings_sample[].host / .port / .protocol — infra topology detail
      resolved_findings_sample — same concern
      scan_errors_resolved_count — internal operational metric, not drift signal
    """
    return {
        "current_score": report.current_score,
        "previous_score": report.previous_score,
        "score_delta": report.score_delta,
        "new_high": report.new_high,
        "new_medium": report.new_medium,
        "new_low": report.new_low,
        "resolved_high": report.resolved_high,
        "resolved_medium": report.resolved_medium,
        "resolved_low": report.resolved_low,
        "scan_errors_new_count": report.scan_errors_new_count,
        "current_session_ts": (
            report.current_session_ts.isoformat()
            if report.current_session_ts is not None
            else None
        ),
        "previous_session_ts": (
            report.previous_session_ts.isoformat()
            if report.previous_session_ts is not None
            else None
        ),
        # EXCLUDED: new_findings_sample[].host/port/protocol — infra topology (ISEC-03)
        # EXCLUDED: resolved_findings_sample — same topology-disclosure concern
    }
