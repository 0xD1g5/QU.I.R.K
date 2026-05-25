"""quirk.notify.dispatcher — Notification fan-out orchestrator (Phase 101 NOTIFY-01/02/07).

This module is the integration seam that:
  1. Discovers the two most recent scan sessions from the DB.
  2. Computes a TrendReport via compute_trend_report().
  3. Evaluates the conservative trigger (should_notify).
  4. Builds a DriftSummary ONCE and fans out to all enabled channels.
  5. Writes one IntegrationDelivery audit row per channel attempt.
  6. Isolates per-channel failures so one bad channel never blocks others
     or corrupts the scan record (NOTIFY-07).

CRITICAL CONSTRAINTS:
  - dispatch_notifications MUST NOT receive or use the scheduler DB path argument.
    The scheduler --config flag is a SQLite .db path — NOT a YAML config file.
    Config is loaded via load_notifications_config() which reads QUIRK_CONFIG_PATH.
  - error_summary is ALWAYS safe_str(exc) — never str(exc) or repr(exc) (ISEC-02).
  - The scheduler hook wraps the entire call in try/except so delivery failure
    NEVER aborts or corrupts the committed scan record (NOTIFY-07, T-101-10).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from quirk.intelligence.trends import TrendReport, compute_trend_report
from quirk.models import CryptoEndpoint, IntegrationDelivery, ScheduledRun, ScheduledScan
from quirk.notify.config import load_notifications_config, NotifyCfg
from quirk.notify.payload import build_drift_summary, to_integration_payload
from quirk.util.safe_exc import safe_str

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pluggable channel send functions (monkeypatched in tests)
# ---------------------------------------------------------------------------

def _channel_send_slack(cfg, summary) -> None:
    """Call send_slack — indirected for test monkeypatching."""
    from quirk.notify.channels.slack import send_slack
    send_slack(cfg, summary)


def _channel_send_email(cfg, summary) -> None:
    """Call send_email — indirected for test monkeypatching."""
    from quirk.notify.channels.email import send_email
    subject = f"QUIRK Alert: {summary.new_high} new HIGH finding(s) — score {summary.current_score}"
    body = (
        f"QUIRK Quantum-Readiness Alert\n"
        f"Score: {summary.current_score} (was {summary.previous_score}, "
        f"delta {summary.score_delta:+d})\n"
        f"New findings — HIGH: {summary.new_high}  MEDIUM: {summary.new_medium}  "
        f"LOW: {summary.new_low}\n"
    )
    if summary.dashboard_url:
        body += f"\nDashboard: {summary.dashboard_url}\n"
    send_email(cfg, subject=subject, body=body)


def _channel_send_webhook(cfg, payload) -> None:
    """Call send_webhook — indirected for test monkeypatching."""
    from quirk.notify.channels.webhook import send_webhook
    send_webhook(cfg, payload)


# ---------------------------------------------------------------------------
# Session discovery
# ---------------------------------------------------------------------------


def _find_two_sessions(db: Session) -> Tuple[Optional[datetime], Optional[datetime]]:
    """Return (current_ts, previous_ts) from the two most recent scan sessions.

    Mirrors _list_session_timestamps() in quirk/dashboard/api/routes/trends.py.
    Uses millisecond-precision strftime (%Y-%m-%d %H:%M:%f) — SQLite's %f gives
    3 decimal digits (ms), so two scans milliseconds apart appear as distinct
    sessions (CR-05).  NULL scanned_at rows excluded (D-13).
    """
    ts_usec = func.strftime(
        "%Y-%m-%d %H:%M:%f", CryptoEndpoint.scanned_at
    ).label("ts_usec")
    rows = (
        db.query(ts_usec)
        .filter(CryptoEndpoint.scanned_at.isnot(None))
        .group_by("ts_usec")
        .order_by(ts_usec.desc())
        .limit(2)
        .all()
    )
    sessions = [datetime.fromisoformat(r.ts_usec) for r in rows]
    current = sessions[0] if sessions else None
    previous = sessions[1] if len(sessions) > 1 else None
    return current, previous


# ---------------------------------------------------------------------------
# Trigger evaluation
# ---------------------------------------------------------------------------


def should_notify(report: TrendReport, threshold: int = 5) -> bool:
    """Evaluate the conservative notification trigger (NOTIFY-02).

    Fires when:
      - report.new_high > 0 (new HIGH or CRITICAL finding), OR
      - report.score_delta is not None AND score_delta < -threshold
        (score regression beyond the floor).

    Explicitly returns False when score_delta is None (Pitfall 4 — first scan
    with no previous session).  This prevents an alert storm on the very first
    scheduled scan.  A new HIGH finding on the first scan still triggers via
    the first condition.

    MEDIUM-only changes (new_high==0, score_delta within floor) return False.
    """
    if report.new_high > 0:
        return True
    if report.score_delta is not None and report.score_delta < -threshold:
        return True
    return False


# ---------------------------------------------------------------------------
# Per-channel delivery with failure isolation
# ---------------------------------------------------------------------------


def _deliver(channel_label: str, channel_fn, channel_cfg, call_arg, db: Session) -> None:
    """Invoke one channel sender and write an IntegrationDelivery audit row.

    Per-channel failure isolation (NOTIFY-07, T-101-13):
    - Any exception from channel_fn is caught.
    - error_summary is always safe_str(exc) — never raw exception text (ISEC-02, T-101-11).
    - A WARNING is logged via safe_str (no secret leak into logs).
    - The delivery row is written regardless of success/failure.
    - Other channels are unaffected.
    """
    row = IntegrationDelivery(
        scan_id="",  # will be set by caller before this call
        destination=channel_label,
        status="ok",
        attempted_at=datetime.now(timezone.utc).replace(tzinfo=None),
        error_summary=None,
    )
    try:
        channel_fn(channel_cfg, call_arg)
    except Exception as exc:
        row.status = "failed"
        row.error_summary = safe_str(exc)  # ISEC-02: safe_str always, never str(exc)
        logger.warning(
            "Delivery failed (%s): %s",
            channel_label,
            safe_str(exc),  # ISEC-02: safe_str in logs too
        )
    db.add(row)
    db.commit()


# ---------------------------------------------------------------------------
# Main fan-out entry point
# ---------------------------------------------------------------------------


def dispatch_notifications(
    run: ScheduledRun,
    schedule: ScheduledScan,
    db: Session,
) -> None:
    """Evaluate the trigger and fan out to all enabled notification channels.

    Called by the scheduler hook in _dispatch_schedule, immediately AFTER the
    final db.commit() and BEFORE return run.

    This function MUST NOT receive or use the scheduler DB path argument.  Notification config is
    loaded via load_notifications_config() which reads QUIRK_CONFIG_PATH env var.

    Args:
        run: The completed ScheduledRun (scan record already committed).
        schedule: The ScheduledScan that triggered this run.
        db: Active DB session — used to write IntegrationDelivery audit rows.

    Returns:
        None.  Delivery failures are logged; the function always returns normally.
    """
    # Load notification config via QUIRK_CONFIG_PATH — never from scheduler DB path
    notify_cfg: Optional[NotifyCfg] = load_notifications_config()
    if notify_cfg is None:
        return  # Notifications not configured — exit cleanly

    # Discover the two most recent scan sessions
    current_ts, previous_ts = _find_two_sessions(db)
    if current_ts is None:
        return  # No scan data yet — nothing to report

    # Compute the trend report for this scan pair
    report: TrendReport = compute_trend_report(current_ts, previous_ts, db)

    # Evaluate the conservative trigger (NOTIFY-02, T-101-12)
    threshold = abs(notify_cfg.trigger_score_floor)
    if not should_notify(report, threshold=threshold):
        return  # Trigger not met — no notification

    # Derive the canonical scan_id from the current session timestamp
    scan_id = current_ts.isoformat()

    # Bonus: populate run.scan_id when not already set (useful for audit queries)
    if run.scan_id is None:
        run.scan_id = scan_id
        db.commit()

    # Build the shared content model once — all channel formatters consume this
    dashboard_base_url: Optional[str] = None
    if notify_cfg.slack and notify_cfg.slack.dashboard_base_url:
        dashboard_base_url = notify_cfg.slack.dashboard_base_url

    summary = build_drift_summary(
        report,
        dashboard_base_url=dashboard_base_url,
        scan_id=scan_id,
    )
    payload = to_integration_payload(report)

    # Fan out to each enabled channel with per-channel failure isolation
    # Each _deliver call writes one IntegrationDelivery row (status ok/failed).
    if notify_cfg.slack is not None:
        row_slack = IntegrationDelivery(
            scan_id=scan_id,
            destination="slack",
            status="ok",
            attempted_at=datetime.now(timezone.utc).replace(tzinfo=None),
            error_summary=None,
        )
        try:
            _channel_send_slack(notify_cfg.slack, summary)
        except Exception as exc:
            row_slack.status = "failed"
            row_slack.error_summary = safe_str(exc)
            logger.warning(
                "Delivery failed (slack): %s",
                safe_str(exc),
            )
        db.add(row_slack)
        db.commit()

    if notify_cfg.email is not None:
        subject = (
            f"QUIRK Alert: {report.new_high} new HIGH finding(s) "
            f"— score {report.current_score}"
        )
        body_lines = [
            "QUIRK Quantum-Readiness Alert",
            f"Score: {report.current_score} (was {report.previous_score}, "
            f"delta {report.score_delta:+d})",
            f"New findings — HIGH: {report.new_high}  MEDIUM: {report.new_medium}"
            f"  LOW: {report.new_low}",
        ]
        if summary.dashboard_url:
            body_lines.append(f"\nDashboard: {summary.dashboard_url}")
        body = "\n".join(body_lines) + "\n"

        row_email = IntegrationDelivery(
            scan_id=scan_id,
            destination="email",
            status="ok",
            attempted_at=datetime.now(timezone.utc).replace(tzinfo=None),
            error_summary=None,
        )
        try:
            _channel_send_email(notify_cfg.email, body)
        except Exception as exc:
            row_email.status = "failed"
            row_email.error_summary = safe_str(exc)
            logger.warning(
                "Delivery failed (email): %s",
                safe_str(exc),
            )
        db.add(row_email)
        db.commit()

    if notify_cfg.webhook is not None:
        row_webhook = IntegrationDelivery(
            scan_id=scan_id,
            destination="webhook",
            status="ok",
            attempted_at=datetime.now(timezone.utc).replace(tzinfo=None),
            error_summary=None,
        )
        try:
            _channel_send_webhook(notify_cfg.webhook, payload)
        except Exception as exc:
            row_webhook.status = "failed"
            row_webhook.error_summary = safe_str(exc)
            logger.warning(
                "Delivery failed (webhook): %s",
                safe_str(exc),
            )
        db.add(row_webhook)
        db.commit()
