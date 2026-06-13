"""Phase 125 — DIST-02 RED scaffold.

DIST-02 / CD-06: dispatcher.py:179-181 does an unprotected db.commit() for
run.scan_id. If that commit throws, the entire fan-out is aborted — subsequent
channels never dispatch.

Post-fix: a commit failure on run.scan_id must be caught and logged; fan-out
must continue so all configured channels still receive the notification.

RED: currently the db.commit() at :181 is NOT protected; the test below asserts
the channel is called even when the first commit fails. That assertion currently
fails because the commit raises and the function exits early.
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, call

import pytest

from quirk.models import MergeRun


def _make_run(scan_id=None):
    run = MagicMock(spec=MergeRun)
    run.scan_id = scan_id
    return run


def _make_trend_report(new_high=1):
    from quirk.intelligence.trends import TrendReport
    report = MagicMock(spec=TrendReport)
    report.previous_session_ts = datetime(2026, 6, 1, tzinfo=timezone.utc)
    report.current_session_ts = datetime(2026, 6, 13, tzinfo=timezone.utc)
    report.new_high = new_high
    report.new_medium = 0
    report.new_low = 0
    report.resolved_high = 0
    report.score_delta = -10.0
    return report


def test_scan_id_commit_failure_does_not_drop_slack_fanout():
    """A failing db.commit() for run.scan_id must NOT prevent Slack dispatch.

    Setup:
    - run.scan_id is None (triggers the commit path at :179-181)
    - db.commit() raises on the first call (the scan_id commit)
    - Slack channel is configured and enabled

    Post-fix: Slack _channel_send_slack is still called despite the commit failure.
    RED: currently the commit() exception propagates and exits dispatch_notifications,
         so _channel_send_slack is never reached.
    """
    from quirk.notify import dispatcher
    from quirk.notify.config import NotifyCfg, SlackNotifyCfg

    run = _make_run(scan_id=None)
    report = _make_trend_report(new_high=1)

    # db.commit raises on first call (scan_id commit), succeeds on second (audit rows)
    commit_calls = [0]
    def commit_side_effect():
        commit_calls[0] += 1
        if commit_calls[0] == 1:
            raise Exception("DB commit failed (simulated IAM/lock error)")
    db = MagicMock()
    db.commit.side_effect = commit_side_effect

    slack_cfg = SlackNotifyCfg(slack_webhook_env="QUIRK_SLACK_WEBHOOK_TEST", dashboard_base_url=None)
    notify_cfg = NotifyCfg(slack=slack_cfg, email=None, webhook=None, trigger_score_floor=5)

    with patch.object(dispatcher, "load_notifications_config", return_value=notify_cfg), \
         patch.object(dispatcher, "should_notify", return_value=True), \
         patch.object(dispatcher, "_channel_send_slack") as mock_slack, \
         patch.object(dispatcher, "build_drift_summary", return_value=MagicMock()), \
         patch.object(dispatcher, "to_integration_payload", return_value=MagicMock()):

        dispatcher.dispatch_notifications(run, report, db)

    # RED: currently mock_slack.called is False because commit() raises before we reach slack
    assert mock_slack.called, (
        "Slack channel must be called even when run.scan_id db.commit() fails. "
        "DIST-02 not yet fixed: unprotected commit at dispatcher.py:181 aborts fan-out."
    )
