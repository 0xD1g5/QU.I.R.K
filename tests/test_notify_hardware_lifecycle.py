"""Tests for HWLC-14 hardware-lifecycle notification delivery.

Covers:
- HardwareLifecycleSummary + build_hardware_lifecycle_summary() (payload.py)
- to_hardware_lifecycle_payload() exhaustive outbound whitelist (ISEC-03)
- dispatch_hardware_lifecycle_notifications() trigger-filter, audit-row, and
  failure-isolation behavior (dispatcher.py)
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_event(
    *,
    id=1,
    host="10.0.0.5",
    port=443,
    event_type="tier_crossing",
    old_value="Tier 1",
    new_value="Tier 2",
    detected_at=None,
):
    """Duck-typed HardwareDriftEvent stand-in (avoids ORM/DB setup)."""
    ev = MagicMock()
    ev.id = id
    ev.host = host
    ev.port = port
    ev.event_type = event_type
    ev.old_value = old_value
    ev.new_value = new_value
    ev.detected_at = detected_at if detected_at is not None else datetime(
        2026, 8, 20, 12, 0, 0, tzinfo=timezone.utc
    )
    return ev


# ---------------------------------------------------------------------------
# Tests — build_hardware_lifecycle_summary
# ---------------------------------------------------------------------------


class TestBuildHardwareLifecycleSummary:
    def test_event_count_matches(self):
        from quirk.notify.payload import build_hardware_lifecycle_summary

        summary = build_hardware_lifecycle_summary([_make_event()])
        assert summary.event_count == 1

    def test_events_field_shape(self):
        from quirk.notify.payload import build_hardware_lifecycle_summary

        summary = build_hardware_lifecycle_summary([_make_event()])
        assert len(summary.events) == 1
        entry = summary.events[0]
        assert set(entry.keys()) == {
            "host",
            "port",
            "event_type",
            "old_value",
            "new_value",
            "detected_at",
        }
        assert entry["host"] == "10.0.0.5"
        assert entry["port"] == 443
        assert entry["event_type"] == "tier_crossing"
        assert isinstance(entry["detected_at"], str)

    def test_empty_events_no_raise(self):
        from quirk.notify.payload import build_hardware_lifecycle_summary

        summary = build_hardware_lifecycle_summary([])
        assert summary.event_count == 0
        assert summary.events == []

    def test_dashboard_url_none_when_base_unset(self):
        from quirk.notify.payload import build_hardware_lifecycle_summary

        summary = build_hardware_lifecycle_summary([], dashboard_base_url=None)
        assert summary.dashboard_url is None

    def test_dashboard_url_populated_when_base_set(self):
        from quirk.notify.payload import build_hardware_lifecycle_summary

        summary = build_hardware_lifecycle_summary(
            [], dashboard_base_url="https://quirk.example.com"
        )
        assert summary.dashboard_url is not None
        assert "quirk.example.com" in summary.dashboard_url


# ---------------------------------------------------------------------------
# Tests — to_hardware_lifecycle_payload whitelist
# ---------------------------------------------------------------------------


class TestToHardwareLifecyclePayloadWhitelist:
    def test_exact_key_set(self):
        from quirk.notify.payload import (
            build_hardware_lifecycle_summary,
            to_hardware_lifecycle_payload,
        )

        summary = build_hardware_lifecycle_summary([_make_event()])
        payload = to_hardware_lifecycle_payload(summary)
        assert set(payload.keys()) == {"event_type", "event_count", "events", "dashboard_url"}

    def test_event_type_literal(self):
        from quirk.notify.payload import (
            build_hardware_lifecycle_summary,
            to_hardware_lifecycle_payload,
        )

        summary = build_hardware_lifecycle_summary([_make_event()])
        payload = to_hardware_lifecycle_payload(summary)
        assert payload["event_type"] == "hardware_lifecycle"

    def test_no_id_field_leaked(self):
        from quirk.notify.payload import (
            build_hardware_lifecycle_summary,
            to_hardware_lifecycle_payload,
        )

        summary = build_hardware_lifecycle_summary([_make_event(id=999)])
        payload = to_hardware_lifecycle_payload(summary)
        for event_entry in payload["events"]:
            assert "id" not in event_entry

    def test_no_orm_object_in_payload(self):
        from quirk.notify.payload import (
            build_hardware_lifecycle_summary,
            to_hardware_lifecycle_payload,
        )

        summary = build_hardware_lifecycle_summary([_make_event()])
        payload = to_hardware_lifecycle_payload(summary)
        import json

        json.dumps(payload)  # must be plain-JSON-serializable, no ORM/MagicMock leakage


# ---------------------------------------------------------------------------
# Tests — dispatch_hardware_lifecycle_notifications
# ---------------------------------------------------------------------------


class TestDispatchHardwareLifecycleNotifications:
    def test_toggle_off_zero_calls(self):
        from quirk.notify import dispatcher
        from quirk.notify.config import NotifyCfg, EmailNotifyCfg, WebhookNotifyCfg

        notify_cfg = NotifyCfg(
            notify_on_hardware_lifecycle=False,
            email=EmailNotifyCfg(smtp_host="smtp.example.com"),
            webhook=WebhookNotifyCfg(url_env="WEBHOOK_URL"),
        )
        db = MagicMock()
        with patch.object(dispatcher, "load_notifications_config", return_value=notify_cfg), \
             patch.object(dispatcher, "_channel_send_email") as mock_email, \
             patch.object(dispatcher, "_channel_send_webhook") as mock_webhook, \
             patch.object(dispatcher, "_channel_send_slack") as mock_slack:
            dispatcher.dispatch_hardware_lifecycle_notifications([_make_event()], db)

        assert not mock_email.called
        assert not mock_webhook.called
        assert not mock_slack.called
        assert not db.add.called
        assert not db.commit.called

    def test_config_none_zero_calls(self):
        from quirk.notify import dispatcher

        db = MagicMock()
        with patch.object(dispatcher, "load_notifications_config", return_value=None), \
             patch.object(dispatcher, "_channel_send_email") as mock_email, \
             patch.object(dispatcher, "_channel_send_webhook") as mock_webhook:
            dispatcher.dispatch_hardware_lifecycle_notifications([_make_event()], db)

        assert not mock_email.called
        assert not mock_webhook.called
        assert not db.commit.called

    def test_toggle_on_empty_events_zero_rows(self):
        from quirk.notify import dispatcher
        from quirk.notify.config import NotifyCfg, EmailNotifyCfg, WebhookNotifyCfg

        notify_cfg = NotifyCfg(
            notify_on_hardware_lifecycle=True,
            email=EmailNotifyCfg(smtp_host="smtp.example.com"),
            webhook=WebhookNotifyCfg(url_env="WEBHOOK_URL"),
        )
        db = MagicMock()
        with patch.object(dispatcher, "load_notifications_config", return_value=notify_cfg), \
             patch.object(dispatcher, "_channel_send_email") as mock_email, \
             patch.object(dispatcher, "_channel_send_webhook") as mock_webhook:
            dispatcher.dispatch_hardware_lifecycle_notifications([], db)

        assert not mock_email.called
        assert not mock_webhook.called
        assert not db.commit.called

    def test_worsened_tier_crossing_triggers_both_channels(self):
        from quirk.notify import dispatcher
        from quirk.notify.config import NotifyCfg, EmailNotifyCfg, WebhookNotifyCfg

        notify_cfg = NotifyCfg(
            notify_on_hardware_lifecycle=True,
            email=EmailNotifyCfg(smtp_host="smtp.example.com"),
            webhook=WebhookNotifyCfg(url_env="WEBHOOK_URL"),
        )
        db = MagicMock()
        event = _make_event(event_type="tier_crossing", old_value="Tier 1", new_value="Tier 2")
        with patch.object(dispatcher, "load_notifications_config", return_value=notify_cfg), \
             patch("quirk.scanner.hardware_drift.tier_direction", return_value="worsened"), \
             patch.object(dispatcher, "_channel_send_email") as mock_email, \
             patch.object(dispatcher, "_channel_send_webhook") as mock_webhook, \
             patch.object(dispatcher, "_channel_send_slack") as mock_slack:
            dispatcher.dispatch_hardware_lifecycle_notifications([event], db)

        assert mock_email.call_count == 1
        assert mock_webhook.call_count == 1
        assert not mock_slack.called
        assert db.commit.call_count == 1

    def test_improved_tier_crossing_zero_calls(self):
        from quirk.notify import dispatcher
        from quirk.notify.config import NotifyCfg, EmailNotifyCfg, WebhookNotifyCfg

        notify_cfg = NotifyCfg(
            notify_on_hardware_lifecycle=True,
            email=EmailNotifyCfg(smtp_host="smtp.example.com"),
            webhook=WebhookNotifyCfg(url_env="WEBHOOK_URL"),
        )
        db = MagicMock()
        event = _make_event(event_type="tier_crossing", old_value="Tier 2", new_value="Tier 1")
        with patch.object(dispatcher, "load_notifications_config", return_value=notify_cfg), \
             patch("quirk.scanner.hardware_drift.tier_direction", return_value="improved"), \
             patch.object(dispatcher, "_channel_send_email") as mock_email, \
             patch.object(dispatcher, "_channel_send_webhook") as mock_webhook:
            dispatcher.dispatch_hardware_lifecycle_notifications([event], db)

        assert not mock_email.called
        assert not mock_webhook.called
        assert not db.commit.called

    def test_eol_state_change_triggers_both_channels(self):
        from quirk.notify import dispatcher
        from quirk.notify.config import NotifyCfg, EmailNotifyCfg, WebhookNotifyCfg

        notify_cfg = NotifyCfg(
            notify_on_hardware_lifecycle=True,
            email=EmailNotifyCfg(smtp_host="smtp.example.com"),
            webhook=WebhookNotifyCfg(url_env="WEBHOOK_URL"),
        )
        db = MagicMock()
        event = _make_event(event_type="eol_state_change", old_value="active", new_value="eol")
        with patch.object(dispatcher, "load_notifications_config", return_value=notify_cfg), \
             patch.object(dispatcher, "_channel_send_email") as mock_email, \
             patch.object(dispatcher, "_channel_send_webhook") as mock_webhook, \
             patch.object(dispatcher, "_channel_send_slack") as mock_slack:
            dispatcher.dispatch_hardware_lifecycle_notifications([event], db)

        assert mock_email.call_count == 1
        assert mock_webhook.call_count == 1
        assert not mock_slack.called

    def test_slack_never_called_even_when_configured(self):
        from quirk.notify import dispatcher
        from quirk.notify.config import (
            NotifyCfg,
            EmailNotifyCfg,
            WebhookNotifyCfg,
            SlackNotifyCfg,
        )

        notify_cfg = NotifyCfg(
            notify_on_hardware_lifecycle=True,
            email=EmailNotifyCfg(smtp_host="smtp.example.com"),
            webhook=WebhookNotifyCfg(url_env="WEBHOOK_URL"),
            slack=SlackNotifyCfg(slack_webhook_env="SLACK_URL"),
        )
        db = MagicMock()
        event = _make_event(event_type="eol_state_change")
        with patch.object(dispatcher, "load_notifications_config", return_value=notify_cfg), \
             patch.object(dispatcher, "_channel_send_email"), \
             patch.object(dispatcher, "_channel_send_webhook"), \
             patch.object(dispatcher, "_channel_send_slack") as mock_slack:
            dispatcher.dispatch_hardware_lifecycle_notifications([event], db)

        assert not mock_slack.called

    def test_audit_row_scan_id_composite(self):
        from quirk.notify import dispatcher
        from quirk.notify.config import NotifyCfg, EmailNotifyCfg, WebhookNotifyCfg

        notify_cfg = NotifyCfg(
            notify_on_hardware_lifecycle=True,
            email=EmailNotifyCfg(smtp_host="smtp.example.com"),
            webhook=WebhookNotifyCfg(url_env="WEBHOOK_URL"),
        )
        db = MagicMock()
        event = _make_event(
            id=42, host="10.0.0.9", port=8443, event_type="eol_state_change"
        )
        added_rows = []
        db.add.side_effect = lambda row: added_rows.append(row)
        with patch.object(dispatcher, "load_notifications_config", return_value=notify_cfg), \
             patch.object(dispatcher, "_channel_send_email"), \
             patch.object(dispatcher, "_channel_send_webhook"):
            dispatcher.dispatch_hardware_lifecycle_notifications([event], db)

        assert len(added_rows) == 2
        expected_scan_id = "10.0.0.9:8443:eol_state_change:42"
        for row in added_rows:
            assert row.scan_id == expected_scan_id

    def test_email_failure_marks_row_failed_webhook_still_runs(self):
        from quirk.notify import dispatcher
        from quirk.notify.config import NotifyCfg, EmailNotifyCfg, WebhookNotifyCfg
        from quirk.util.safe_exc import safe_str

        notify_cfg = NotifyCfg(
            notify_on_hardware_lifecycle=True,
            email=EmailNotifyCfg(smtp_host="smtp.example.com"),
            webhook=WebhookNotifyCfg(url_env="WEBHOOK_URL"),
        )
        db = MagicMock()
        event = _make_event(event_type="eol_state_change")
        added_rows = []
        db.add.side_effect = lambda row: added_rows.append(row)
        boom = Exception("smtp connection refused")
        with patch.object(dispatcher, "load_notifications_config", return_value=notify_cfg), \
             patch.object(dispatcher, "_channel_send_email", side_effect=boom), \
             patch.object(dispatcher, "_channel_send_webhook") as mock_webhook:
            dispatcher.dispatch_hardware_lifecycle_notifications([event], db)

        assert mock_webhook.call_count == 1
        email_rows = [r for r in added_rows if r.destination == "email"]
        assert len(email_rows) == 1
        assert email_rows[0].status == "failed"
        assert email_rows[0].error_summary == safe_str(boom)

    def test_commit_called_exactly_once(self):
        from quirk.notify import dispatcher
        from quirk.notify.config import NotifyCfg, EmailNotifyCfg, WebhookNotifyCfg

        notify_cfg = NotifyCfg(
            notify_on_hardware_lifecycle=True,
            email=EmailNotifyCfg(smtp_host="smtp.example.com"),
            webhook=WebhookNotifyCfg(url_env="WEBHOOK_URL"),
        )
        db = MagicMock()
        event = _make_event(event_type="eol_state_change")
        with patch.object(dispatcher, "load_notifications_config", return_value=notify_cfg), \
             patch.object(dispatcher, "_channel_send_email"), \
             patch.object(dispatcher, "_channel_send_webhook"):
            dispatcher.dispatch_hardware_lifecycle_notifications([event], db)

        assert db.commit.call_count == 1
