"""Tests for quirk.notify.channels.slack — Phase 101 NOTIFY-03, ISEC-01, ISEC-04.

TDD: RED → GREEN cycle.  Tests written first, then implementation.

Patching strategy: The production code does `from importlib.util import find_spec`
at module top.  Tests must patch `quirk.notify.channels.slack.find_spec` (the
name in the module's namespace), not `importlib.util.find_spec`.
"""
from __future__ import annotations

import importlib
import importlib.util
import logging
import sys
import types

import pytest

from quirk.notify.config import SlackNotifyCfg


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _make_cfg(slack_webhook_env: str = "QUIRK_SLACK_WEBHOOK") -> SlackNotifyCfg:
    return SlackNotifyCfg(
        slack_webhook_env=slack_webhook_env,
        dashboard_base_url="https://quirk.example.com",
    )


def _make_fake_slack_modules():
    """Return (fake_slack_sdk, fake_webhook_mod, FakeWebhookClient) for monkeypatching."""

    class _FakeResponse:
        def __init__(self, status_code: int = 200, body: str = "ok"):
            self.status_code = status_code
            self.body = body

    class _FakeWebhookClient:
        instances: list = []

        def __init__(self, url: str):
            self.url = url
            self.calls: list = []
            _FakeWebhookClient.instances.append(self)

        def send(self, **kwargs):
            self.calls.append(kwargs)
            return _FakeResponse(200, "ok")

    _FakeWebhookClient.instances = []

    fake_slack_sdk = types.ModuleType("slack_sdk")
    fake_webhook_mod = types.ModuleType("slack_sdk.webhook")
    fake_webhook_mod.WebhookClient = _FakeWebhookClient
    fake_slack_sdk.webhook = fake_webhook_mod
    return fake_slack_sdk, fake_webhook_mod, _FakeWebhookClient


def _inject_slack_modules(monkeypatch, fake_slack_sdk, fake_webhook_mod):
    monkeypatch.setitem(sys.modules, "slack_sdk", fake_slack_sdk)
    monkeypatch.setitem(sys.modules, "slack_sdk.webhook", fake_webhook_mod)


# ---------------------------------------------------------------------------
# ISEC-04: graceful skip when slack_sdk is not installed
# ---------------------------------------------------------------------------


def test_graceful_skip_missing_slack_sdk(monkeypatch, caplog):
    """ISEC-04: When find_spec('slack_sdk') is None, a WARNING is logged and
    the function returns without raising ImportError or AttributeError.

    Patch the name in the module's namespace (not importlib.util.find_spec).
    """
    import quirk.notify.channels.slack as slack_mod

    monkeypatch.setattr(slack_mod, "find_spec", lambda name: None)

    with caplog.at_level(logging.WARNING, logger="quirk.notify.channels.slack"):
        from quirk.notify.channels.slack import send_slack
        send_slack(cfg=_make_cfg(), summary=object())

    assert "pip install quirk[notify]" in caplog.text


# ---------------------------------------------------------------------------
# Missing env var: skip with WARNING
# ---------------------------------------------------------------------------


def test_skip_when_webhook_env_unset(monkeypatch, caplog):
    """When the slack_webhook_env env var is not set, log a WARNING and return."""
    import quirk.notify.channels.slack as slack_mod

    # Pretend slack_sdk is installed
    monkeypatch.setattr(slack_mod, "find_spec", lambda name: object())
    monkeypatch.delenv("QUIRK_SLACK_WEBHOOK", raising=False)

    with caplog.at_level(logging.WARNING, logger="quirk.notify.channels.slack"):
        from quirk.notify.channels.slack import send_slack
        send_slack(cfg=_make_cfg("QUIRK_SLACK_WEBHOOK"), summary=object())

    log_text = caplog.text
    assert "QUIRK_SLACK_WEBHOOK" in log_text or "not set" in log_text, \
        f"Expected warning about unset env var, got: {log_text}"


# ---------------------------------------------------------------------------
# ISEC-01: SSRF — loopback / metadata IP raises ValueError
# ---------------------------------------------------------------------------


def test_ssrf_loopback_raises_value_error(monkeypatch):
    """ISEC-01: A loopback Slack webhook URL raises ValueError mentioning SSRF."""
    import quirk.notify.channels.slack as slack_mod

    monkeypatch.setattr(slack_mod, "find_spec", lambda name: object())
    monkeypatch.setenv("QUIRK_SLACK_WEBHOOK", "https://127.0.0.1/services/T123/B456/xxx")

    from quirk.notify.channels.slack import send_slack

    with pytest.raises(ValueError, match="SSRF"):
        send_slack(cfg=_make_cfg("QUIRK_SLACK_WEBHOOK"), summary=object())


def test_ssrf_metadata_ip_raises_value_error(monkeypatch):
    """ISEC-01: A cloud metadata IP Slack webhook URL raises ValueError."""
    import quirk.notify.channels.slack as slack_mod

    monkeypatch.setattr(slack_mod, "find_spec", lambda name: object())
    monkeypatch.setenv(
        "QUIRK_SLACK_WEBHOOK",
        "https://169.254.169.254/services/T123/B456/xxx",
    )

    from quirk.notify.channels.slack import send_slack

    with pytest.raises(ValueError, match="SSRF"):
        send_slack(cfg=_make_cfg("QUIRK_SLACK_WEBHOOK"), summary=object())


# ---------------------------------------------------------------------------
# Happy path: WebhookClient.send() is called once
# ---------------------------------------------------------------------------


def test_happy_path_sends_once(monkeypatch):
    """On the happy path, WebhookClient.send() is called exactly once."""
    import quirk.notify.channels.slack as slack_mod

    fake_slack_sdk, fake_webhook_mod, FakeClient = _make_fake_slack_modules()
    _inject_slack_modules(monkeypatch, fake_slack_sdk, fake_webhook_mod)
    monkeypatch.setattr(slack_mod, "find_spec", lambda name: object())
    monkeypatch.setenv(
        "QUIRK_SLACK_WEBHOOK",
        "https://hooks.slack.com/services/T123/B456/token",
    )

    from quirk.notify.payload import DriftSummary
    summary = DriftSummary(
        current_score=70,
        previous_score=80,
        score_delta=-10,
        score_band="MEDIUM",
        new_high=2,
        new_medium=1,
        new_low=0,
        scan_id="2026-05-25T00:00:00",
        dashboard_url="https://quirk.example.com/trends",
    )

    from quirk.notify.channels.slack import send_slack
    send_slack(cfg=_make_cfg("QUIRK_SLACK_WEBHOOK"), summary=summary)

    assert len(FakeClient.instances) == 1, "Expected exactly 1 WebhookClient instance"
    assert len(FakeClient.instances[0].calls) == 1, "Expected exactly 1 send() call"
    call_kwargs = FakeClient.instances[0].calls[0]
    assert "text" in call_kwargs, "send() must be called with a 'text' kwarg"


# ---------------------------------------------------------------------------
# Non-200 response raises RuntimeError
# ---------------------------------------------------------------------------


def test_non_200_response_raises_runtime_error(monkeypatch):
    """A non-200 Slack response raises RuntimeError."""
    import quirk.notify.channels.slack as slack_mod

    class _FailResponse:
        status_code = 400
        body = "bad_token"

    class _FailingClient:
        def __init__(self, url):
            pass

        def send(self, **kwargs):
            return _FailResponse()

    fake_slack_sdk = types.ModuleType("slack_sdk")
    fake_webhook_mod = types.ModuleType("slack_sdk.webhook")
    fake_webhook_mod.WebhookClient = _FailingClient
    _inject_slack_modules(monkeypatch, fake_slack_sdk, fake_webhook_mod)
    monkeypatch.setattr(slack_mod, "find_spec", lambda name: object())
    monkeypatch.setenv(
        "QUIRK_SLACK_WEBHOOK",
        "https://hooks.slack.com/services/T123/B456/token",
    )

    from quirk.notify.payload import DriftSummary
    summary = DriftSummary(
        current_score=70,
        previous_score=80,
        score_delta=-10,
        score_band="MEDIUM",
        new_high=2,
        new_medium=1,
        new_low=0,
        scan_id="2026-05-25T00:00:00",
        dashboard_url=None,
    )

    from quirk.notify.channels.slack import send_slack

    with pytest.raises(RuntimeError, match="400"):
        send_slack(cfg=_make_cfg("QUIRK_SLACK_WEBHOOK"), summary=summary)
