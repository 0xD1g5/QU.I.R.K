"""Tests for quirk/notify/dispatcher.py — Phase 101 NOTIFY-01/02/07, ISEC-02.

Covers:
  - should_notify: trigger fires on new HIGH, fires on score regression beyond floor,
    does NOT fire on first scan (score_delta=None), does NOT fire on MEDIUM-only.
  - dispatch_notifications: early-return when config is None, fan-out to enabled
    channels with per-channel failure isolation, safe_str in error_summary.
  - Scheduler isolation: _dispatch_schedule wraps dispatch_notifications in
    try/except; the scan record is returned unaffected even when dispatch raises.

Test DB setup mirrors test_scheduler_cmd.py (tmp_path + init_db pattern).
"""
from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from quirk.db import init_db, get_session
from quirk.models import ScheduledScan, ScheduledRun, IntegrationDelivery
from quirk.cli.scheduler_cmd import _utcnow_naive


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_db(tmp_path):
    """Create a test SQLite database and return its path."""
    db_path = str(tmp_path / "quirk_test.db")
    init_db(db_path)
    return db_path


def _make_trend_report(
    *,
    new_high=0,
    new_medium=0,
    new_low=0,
    score_delta=None,
    current_score=70,
    previous_score=None,
):
    """Build a TrendReport fixture for trigger evaluation tests."""
    from quirk.intelligence.trends import TrendReport

    previous_ts = datetime(2026, 1, 1) if previous_score is not None else None
    return TrendReport(
        current_session_ts=datetime(2026, 1, 2),
        previous_session_ts=previous_ts,
        current_score=current_score,
        previous_score=previous_score,
        score_delta=score_delta,
        new_high=new_high,
        new_medium=new_medium,
        new_low=new_low,
        resolved_high=0,
        resolved_medium=0,
        resolved_low=0,
        scan_errors_new_count=0,
        scan_errors_resolved_count=0,
    )


def _add_schedule(db_path, *, name="test-scan"):
    """Insert a ScheduledScan row and return it."""
    from quirk.cli.scheduler_cmd import _utcnow_naive

    row = ScheduledScan(
        name=name,
        cron_expr="* * * * *",
        target="127.0.0.1",
        profile=None,
        enabled=True,
        last_run_at=None,
        created_at=_utcnow_naive(),
    )
    with get_session(db_path) as db:
        db.add(row)
        db.flush()
        row_id = row.id
    with get_session(db_path) as db:
        return db.query(ScheduledScan).filter_by(id=row_id).one()


# ---------------------------------------------------------------------------
# should_notify tests (NOTIFY-02)
# ---------------------------------------------------------------------------


def test_trigger_high_fires():
    """NOTIFY-02: should_notify returns True when new_high > 0."""
    from quirk.notify.dispatcher import should_notify

    report = _make_trend_report(new_high=1, score_delta=-2, previous_score=80)
    assert should_notify(report) is True


def test_trigger_score_regression_fires():
    """NOTIFY-02: should_notify fires when score_delta < -threshold."""
    from quirk.notify.dispatcher import should_notify

    # score_delta=-10 with default threshold=5 → -10 < -5 → True
    report = _make_trend_report(new_high=0, score_delta=-10, previous_score=80)
    assert should_notify(report) is True


def test_no_trigger_medium_only():
    """NOTIFY-02: should_notify returns False on MEDIUM-only changes (no high, delta ok)."""
    from quirk.notify.dispatcher import should_notify

    # new_medium=3 but no high and delta within floor
    report = _make_trend_report(new_high=0, new_medium=3, score_delta=-3, previous_score=80)
    assert should_notify(report) is False


def test_no_notify_on_first_scan():
    """NOTIFY-02 / Pitfall 4: should_notify returns False when score_delta is None (first scan).

    score_delta=None means there is no previous session — the trigger must NOT fire
    to avoid an alert storm on the very first scheduled scan.
    """
    from quirk.notify.dispatcher import should_notify

    # Explicit first-scan case: new_high=0, score_delta=None
    report = _make_trend_report(new_high=0, new_medium=0, score_delta=None, previous_score=None)
    assert should_notify(report) is False


def test_no_notify_first_scan_even_with_new_high():
    """Edge: if new_high > 0 on first scan (no previous), should still fire (high wins).

    The Pitfall 4 guard only applies when score_delta is None — a new HIGH finding
    is always worth notifying even if it's the first scan.
    """
    from quirk.notify.dispatcher import should_notify

    # new_high=1 with score_delta=None — new HIGH is the trigger, not score regression
    report = _make_trend_report(new_high=1, score_delta=None, previous_score=None)
    assert should_notify(report) is True


def test_threshold_boundary_not_fire():
    """should_notify returns False when score_delta == -threshold (not strictly below)."""
    from quirk.notify.dispatcher import should_notify

    # score_delta=-5 with threshold=5 → -5 is not < -5 → False
    report = _make_trend_report(new_high=0, score_delta=-5, previous_score=80)
    assert should_notify(report) is False


# ---------------------------------------------------------------------------
# dispatch_notifications — early-return and fan-out tests (NOTIFY-01/07)
# ---------------------------------------------------------------------------


def test_dispatch_returns_early_when_config_none(tmp_path, monkeypatch):
    """dispatch_notifications returns without calling any channel when config is None."""
    from quirk.notify import dispatcher

    monkeypatch.setattr(dispatcher, "load_notifications_config", lambda: None)

    db_path = _make_db(tmp_path)
    schedule = _add_schedule(db_path)

    with get_session(db_path) as db:
        run = ScheduledRun(
            schedule_id=schedule.id,
            dispatched_at=_utcnow_naive(),
            status="completed",
            scan_output_path=None,
            scan_id=None,
        )
        db.add(run)
        db.commit()

        # Should return cleanly with no deliveries written
        dispatcher.dispatch_notifications(run=run, schedule=schedule, db=db)
        count = db.query(IntegrationDelivery).count()

    assert count == 0


def test_dispatch_returns_early_when_no_session(tmp_path, monkeypatch):
    """dispatch_notifications returns early when _find_two_sessions returns (None, None)."""
    from quirk.notify import dispatcher
    from quirk.notify.config import NotifyCfg, SlackNotifyCfg

    cfg = NotifyCfg(
        trigger_score_floor=-5,
        slack=SlackNotifyCfg(slack_webhook_env="QUIRK_SLACK_WEBHOOK"),
    )
    monkeypatch.setattr(dispatcher, "load_notifications_config", lambda: cfg)
    monkeypatch.setattr(dispatcher, "_find_two_sessions", lambda db: (None, None))

    db_path = _make_db(tmp_path)
    schedule = _add_schedule(db_path)

    with get_session(db_path) as db:
        run = ScheduledRun(
            schedule_id=schedule.id,
            dispatched_at=_utcnow_naive(),
            status="completed",
            scan_output_path=None,
            scan_id=None,
        )
        db.add(run)
        db.commit()

        dispatcher.dispatch_notifications(run=run, schedule=schedule, db=db)
        count = db.query(IntegrationDelivery).count()

    assert count == 0


def test_dispatch_fan_out_creates_delivery_rows(tmp_path, monkeypatch):
    """When trigger fires, each enabled channel gets an IntegrationDelivery row."""
    from quirk.notify import dispatcher
    from quirk.notify.config import NotifyCfg, SlackNotifyCfg, WebhookNotifyCfg

    current_ts = datetime(2026, 1, 2, 12, 0, 0)
    previous_ts = datetime(2026, 1, 1, 12, 0, 0)

    cfg = NotifyCfg(
        trigger_score_floor=-5,
        slack=SlackNotifyCfg(slack_webhook_env="QUIRK_SLACK_WEBHOOK"),
        webhook=WebhookNotifyCfg(url_env="QUIRK_WEBHOOK_URL"),
    )
    monkeypatch.setattr(dispatcher, "load_notifications_config", lambda: cfg)
    monkeypatch.setattr(dispatcher, "_find_two_sessions", lambda db: (current_ts, previous_ts))

    # Fake trend report that triggers (new_high=2)
    fake_report = _make_trend_report(new_high=2, score_delta=-8, previous_score=80)
    monkeypatch.setattr(dispatcher, "compute_trend_report", lambda cur, prev, db: fake_report)

    # Stub channel senders — succeed silently
    monkeypatch.setattr(dispatcher, "_channel_send_slack", lambda cfg, summary: None)
    monkeypatch.setattr(dispatcher, "_channel_send_webhook", lambda cfg, payload: None)

    db_path = _make_db(tmp_path)
    schedule = _add_schedule(db_path)

    with get_session(db_path) as db:
        run = ScheduledRun(
            schedule_id=schedule.id,
            dispatched_at=_utcnow_naive(),
            status="completed",
            scan_output_path=None,
            scan_id=None,
        )
        db.add(run)
        db.commit()

        dispatcher.dispatch_notifications(run=run, schedule=schedule, db=db)
        rows = db.query(IntegrationDelivery).all()

    # Two channels → two rows, both status "ok"
    assert len(rows) == 2
    statuses = {r.status for r in rows}
    assert statuses == {"ok"}


def test_dispatch_email_channel_reaches_transport(tmp_path, monkeypatch):
    """NOTIFY-04 regression: the email fan-out passes a DriftSummary to the
    _channel_send_email wrapper, not a pre-built string.

    Guards against the bug where dispatch_notifications passed a `str` body to
    _channel_send_email(cfg, summary), which then crashed on summary.new_high.
    Here we let the REAL _channel_send_email wrapper run and stub only the
    lowest-level send_email transport — so a regression to passing a string
    re-raises AttributeError and fails this test.
    """
    import quirk.notify.channels.email as email_mod
    from quirk.notify import dispatcher
    from quirk.notify.config import NotifyCfg, EmailNotifyCfg

    current_ts = datetime(2026, 1, 2, 12, 0, 0)
    previous_ts = datetime(2026, 1, 1, 12, 0, 0)

    cfg = NotifyCfg(
        trigger_score_floor=-5,
        email=EmailNotifyCfg(
            smtp_host="smtp.example.com",
            smtp_from="quirk@example.com",
            recipients=["sec@example.com"],
        ),
    )
    monkeypatch.setattr(dispatcher, "load_notifications_config", lambda: cfg)
    monkeypatch.setattr(dispatcher, "_find_two_sessions", lambda db: (current_ts, previous_ts))

    fake_report = _make_trend_report(new_high=2, score_delta=-8, previous_score=80)
    monkeypatch.setattr(dispatcher, "compute_trend_report", lambda cur, prev, db: fake_report)

    # Stub only the transport — the real _channel_send_email wrapper runs and
    # reads summary.new_high / summary.current_score from the DriftSummary.
    captured = {}

    def _fake_send_email(cfg, subject, body):
        captured["subject"] = subject
        captured["body"] = body

    monkeypatch.setattr(email_mod, "send_email", _fake_send_email)

    db_path = _make_db(tmp_path)
    schedule = _add_schedule(db_path)

    with get_session(db_path) as db:
        run = ScheduledRun(
            schedule_id=schedule.id,
            dispatched_at=_utcnow_naive(),
            status="completed",
            scan_output_path=None,
            scan_id=None,
        )
        db.add(run)
        db.commit()

        dispatcher.dispatch_notifications(run=run, schedule=schedule, db=db)
        rows = db.query(IntegrationDelivery).filter_by(destination="email").all()

    # Transport was reached with a real subject/body derived from the summary.
    assert "subject" in captured, "send_email was never called — email fan-out broken"
    assert "2 new HIGH" in captured["subject"]
    # Exactly one email delivery row, status ok (no AttributeError crash).
    assert len(rows) == 1
    assert rows[0].status == "ok"


def test_dispatch_delivery_failure_isolated(tmp_path, monkeypatch):
    """NOTIFY-07: A channel raising an exception records 'failed' row; other channels still run.

    The function must return normally — delivery failure never propagates.
    """
    from quirk.notify import dispatcher
    from quirk.notify.config import NotifyCfg, SlackNotifyCfg, WebhookNotifyCfg

    current_ts = datetime(2026, 1, 2, 12, 0, 0)
    previous_ts = datetime(2026, 1, 1, 12, 0, 0)

    cfg = NotifyCfg(
        trigger_score_floor=-5,
        slack=SlackNotifyCfg(slack_webhook_env="QUIRK_SLACK_WEBHOOK"),
        webhook=WebhookNotifyCfg(url_env="QUIRK_WEBHOOK_URL"),
    )
    monkeypatch.setattr(dispatcher, "load_notifications_config", lambda: cfg)
    monkeypatch.setattr(dispatcher, "_find_two_sessions", lambda db: (current_ts, previous_ts))

    fake_report = _make_trend_report(new_high=1, score_delta=-8, previous_score=80)
    monkeypatch.setattr(dispatcher, "compute_trend_report", lambda cur, prev, db: fake_report)

    # Slack raises; webhook succeeds
    monkeypatch.setattr(dispatcher, "_channel_send_slack", lambda cfg, summary: (_ for _ in ()).throw(RuntimeError("Slack timeout")))
    monkeypatch.setattr(dispatcher, "_channel_send_webhook", lambda cfg, payload: None)

    db_path = _make_db(tmp_path)
    schedule = _add_schedule(db_path)

    with get_session(db_path) as db:
        run = ScheduledRun(
            schedule_id=schedule.id,
            dispatched_at=_utcnow_naive(),
            status="completed",
            scan_output_path=None,
            scan_id=None,
        )
        db.add(run)
        db.commit()

        # Must not raise
        dispatcher.dispatch_notifications(run=run, schedule=schedule, db=db)

        rows = db.query(IntegrationDelivery).all()

    assert len(rows) == 2
    statuses = {r.destination: r.status for r in rows}
    assert statuses.get("slack") == "failed"
    assert statuses.get("webhook") == "ok"


def test_dispatch_secret_not_in_delivery_row(tmp_path, monkeypatch):
    """ISEC-02: An exception carrying an xoxb- token must produce a scrubbed error_summary.

    Injects a Slack exception with a token in the message and asserts the stored
    IntegrationDelivery.error_summary does not contain the raw token text.
    """
    from quirk.notify import dispatcher
    from quirk.notify.config import NotifyCfg, SlackNotifyCfg

    current_ts = datetime(2026, 1, 2, 12, 0, 0)
    previous_ts = datetime(2026, 1, 1, 12, 0, 0)

    cfg = NotifyCfg(
        trigger_score_floor=-5,
        slack=SlackNotifyCfg(slack_webhook_env="QUIRK_SLACK_WEBHOOK"),
    )
    monkeypatch.setattr(dispatcher, "load_notifications_config", lambda: cfg)
    monkeypatch.setattr(dispatcher, "_find_two_sessions", lambda db: (current_ts, previous_ts))

    fake_report = _make_trend_report(new_high=1, score_delta=-8, previous_score=80)
    monkeypatch.setattr(dispatcher, "compute_trend_report", lambda cur, prev, db: fake_report)

    SECRET_TOKEN = "xoxb-12345678901-ABCDEFGHIJKLMNOP"

    def _raise_with_secret(cfg, summary):
        raise RuntimeError(f"Slack API error: token={SECRET_TOKEN}")

    monkeypatch.setattr(dispatcher, "_channel_send_slack", _raise_with_secret)

    db_path = _make_db(tmp_path)
    schedule = _add_schedule(db_path)

    with get_session(db_path) as db:
        run = ScheduledRun(
            schedule_id=schedule.id,
            dispatched_at=_utcnow_naive(),
            status="completed",
            scan_output_path=None,
            scan_id=None,
        )
        db.add(run)
        db.commit()

        dispatcher.dispatch_notifications(run=run, schedule=schedule, db=db)
        row = db.query(IntegrationDelivery).filter_by(destination="slack").one()
        error_summary = row.error_summary

    assert SECRET_TOKEN not in (error_summary or ""), (
        f"Secret token appeared in error_summary: {error_summary!r}"
    )
    assert row.status == "failed"


# ---------------------------------------------------------------------------
# Scheduler isolation test (NOTIFY-07) — dispatch_notifications raises,
# _dispatch_schedule still returns a completed ScheduledRun
# ---------------------------------------------------------------------------


def test_scheduler_dispatch_raises_scan_record_unaffected(tmp_path, monkeypatch):
    """NOTIFY-07: When dispatch_notifications raises, _dispatch_schedule still returns
    a ScheduledRun with status 'completed'.  The scan record is never corrupted.
    """
    import subprocess
    from quirk.cli import scheduler_cmd
    from quirk.cli.scheduler_cmd import _dispatch_schedule

    # Patch dispatch_notifications to raise
    monkeypatch.setattr(
        "quirk.notify.dispatcher.dispatch_notifications",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("notification boom")),
    )

    # Patch Popen to simulate a successful scan
    class FakePopen:
        returncode = 0

        def communicate(self):
            return b"", b""

    monkeypatch.setattr(subprocess, "Popen", lambda *args, **kwargs: FakePopen())

    db_path = _make_db(tmp_path)
    schedule = _add_schedule(db_path)

    with get_session(db_path) as db:
        schedule = db.query(ScheduledScan).filter_by(id=schedule.id).one()
        run = _dispatch_schedule(schedule=schedule, db=db, config_path=db_path)

    assert run is not None
    assert run.status == "completed", f"Expected 'completed', got {run.status!r}"


# ---------------------------------------------------------------------------
# CR-02 regression: email delivery must not crash when score_delta is None
# ---------------------------------------------------------------------------


def test_email_score_delta_none_does_not_crash(tmp_path, monkeypatch):
    """CR-02 regression: email channel with new_high>0 and score_delta=None produces
    status 'ok' delivery row (no TypeError from f'{None:+d}').

    This is the first-scan scenario: there is no previous session, so score_delta is
    None, but new_high > 0 fires the should_notify trigger.  Prior to the fix,
    _channel_send_email raised TypeError which was caught and silently became a
    'failed' delivery row — suppressing the most important alert.
    """
    import quirk.notify.channels.email as email_mod
    from quirk.notify import dispatcher
    from quirk.notify.config import NotifyCfg, EmailNotifyCfg

    current_ts = datetime(2026, 1, 2, 12, 0, 0)

    cfg = NotifyCfg(
        trigger_score_floor=-5,
        email=EmailNotifyCfg(
            smtp_host="smtp.example.com",
            smtp_from="quirk@example.com",
            recipients=["sec@example.com"],
        ),
    )
    monkeypatch.setattr(dispatcher, "load_notifications_config", lambda: cfg)
    monkeypatch.setattr(dispatcher, "_find_two_sessions", lambda db: (current_ts, None))

    # First-scan report: score_delta is None, new_high > 0
    fake_report = _make_trend_report(new_high=3, score_delta=None, previous_score=None)
    monkeypatch.setattr(dispatcher, "compute_trend_report", lambda cur, prev, db: fake_report)

    captured = {}

    def _fake_send_email(cfg, subject, body):
        captured["subject"] = subject
        captured["body"] = body

    monkeypatch.setattr(email_mod, "send_email", _fake_send_email)

    db_path = _make_db(tmp_path)
    schedule = _add_schedule(db_path)

    with get_session(db_path) as db:
        run = ScheduledRun(
            schedule_id=schedule.id,
            dispatched_at=_utcnow_naive(),
            status="completed",
            scan_output_path=None,
            scan_id=None,
        )
        db.add(run)
        db.commit()

        # Must not raise TypeError on score_delta=None
        dispatcher.dispatch_notifications(run=run, schedule=schedule, db=db)
        rows = db.query(IntegrationDelivery).filter_by(destination="email").all()

    assert len(rows) == 1, "Expected one email delivery row"
    assert rows[0].status == "ok", (
        f"Expected status 'ok', got {rows[0].status!r} — "
        f"error_summary: {rows[0].error_summary!r}"
    )
    assert "subject" in captured, "send_email transport was never reached"
    assert "N/A" in captured["body"], (
        "Email body must contain 'N/A' for score_delta when it is None"
    )
