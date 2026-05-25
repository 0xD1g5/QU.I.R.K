"""Cross-channel SSRF parametrized tests — Phase 101 ISEC-01.

Parametrizes loopback / RFC1918 / metadata addresses across all three channel
entry points and asserts each raises ValueError before making any connection.
"""
from __future__ import annotations

import importlib
import logging
import sys
import types

import pytest

from quirk.notify.config import EmailNotifyCfg, SlackNotifyCfg, WebhookNotifyCfg


# ---------------------------------------------------------------------------
# SSRF address fixtures
# ---------------------------------------------------------------------------

_SSRF_ADDRESSES = [
    ("loopback_v4",   "127.0.0.1"),
    ("loopback_v6",   "::1"),
    ("rfc1918_a",     "10.0.0.1"),
    ("rfc1918_b",     "172.16.0.1"),
    ("rfc1918_c",     "192.168.1.1"),
    ("metadata_aws",  "169.254.169.254"),
    ("metadata_gcp",  "169.254.169.254"),  # same IP, different label
]


def _ids(params):
    return [p[0] for p in params]


# ---------------------------------------------------------------------------
# Slack channel
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("label,ip", _SSRF_ADDRESSES, ids=_ids(_SSRF_ADDRESSES))
def test_slack_ssrf_rejected(monkeypatch, label, ip):
    """Slack channel raises ValueError for SSRF addresses before connecting."""
    import quirk.notify.channels.slack as slack_mod

    monkeypatch.setattr(slack_mod, "find_spec", lambda name: object())
    monkeypatch.setenv("QUIRK_SLACK_WEBHOOK", f"https://{ip}/services/T000/B000/token")

    from quirk.notify.channels.slack import send_slack

    cfg = SlackNotifyCfg(slack_webhook_env="QUIRK_SLACK_WEBHOOK")
    with pytest.raises(ValueError, match="SSRF"):
        send_slack(cfg=cfg, summary=object())


# ---------------------------------------------------------------------------
# Email channel
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("label,ip", _SSRF_ADDRESSES, ids=_ids(_SSRF_ADDRESSES))
def test_email_ssrf_rejected(label, ip):
    """Email channel raises ValueError for SSRF SMTP host before connecting."""
    from quirk.notify.channels.email import send_email

    cfg = EmailNotifyCfg(
        smtp_host=ip,
        smtp_port=587,
        smtp_from="test@example.com",
        recipients=["user@example.com"],
    )
    with pytest.raises(ValueError, match="SSRF"):
        send_email(cfg=cfg, subject="Test", body="Body")


# ---------------------------------------------------------------------------
# Webhook channel
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("label,ip", _SSRF_ADDRESSES, ids=_ids(_SSRF_ADDRESSES))
def test_webhook_ssrf_rejected(monkeypatch, label, ip):
    """Webhook channel raises ValueError for SSRF addresses before connecting."""
    from quirk.notify.channels.webhook import send_webhook

    monkeypatch.setenv("QUIRK_WEBHOOK_URL", f"https://{ip}/notify")

    cfg = WebhookNotifyCfg(url_env="QUIRK_WEBHOOK_URL")
    with pytest.raises(ValueError, match="SSRF"):
        send_webhook(cfg=cfg, payload={"current_score": 70})
