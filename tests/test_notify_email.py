"""Tests for quirk.notify.channels.email — Phase 101 NOTIFY-04, ISEC-01.

TDD: RED → GREEN cycle.  Tests written first, then implementation.
"""
from __future__ import annotations

import smtplib
from unittest.mock import MagicMock, patch, call

import pytest

from quirk.notify.config import EmailNotifyCfg


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _make_cfg(
    smtp_host: str = "smtp.example.com",
    smtp_port: int = 587,
    smtp_from: str = "quirk@example.com",
    recipients: list | None = None,
    smtp_user: str | None = "quirk_user",
    smtp_password_env: str | None = "QUIRK_SMTP_PASS",
    use_ssl: bool = False,
    timeout_seconds: int = 10,
) -> EmailNotifyCfg:
    return EmailNotifyCfg(
        smtp_host=smtp_host,
        smtp_port=smtp_port,
        smtp_from=smtp_from,
        recipients=recipients or ["recipient@example.com", "second@example.com"],
        smtp_user=smtp_user,
        smtp_password_env=smtp_password_env,
        use_ssl=use_ssl,
        timeout_seconds=timeout_seconds,
    )


# ---------------------------------------------------------------------------
# ISEC-01: SSRF — metadata IP raises ValueError
# ---------------------------------------------------------------------------


def test_ssrf_metadata_ip_raises_value_error():
    """ISEC-01: A metadata-IP SMTP host raises ValueError (SSRF blocked)."""
    from quirk.notify.channels.email import send_email

    cfg = _make_cfg(smtp_host="169.254.169.254", smtp_port=25)
    with pytest.raises(ValueError, match="SSRF"):
        send_email(cfg=cfg, subject="Test", body="body")


def test_ssrf_loopback_raises_value_error():
    """ISEC-01: A loopback SMTP host raises ValueError."""
    from quirk.notify.channels.email import send_email

    cfg = _make_cfg(smtp_host="127.0.0.1", smtp_port=25)
    with pytest.raises(ValueError, match="SSRF"):
        send_email(cfg=cfg, subject="Test", body="body")


def test_ssrf_rfc1918_raises_value_error():
    """ISEC-01: An RFC1918 SMTP host raises ValueError."""
    from quirk.notify.channels.email import send_email

    cfg = _make_cfg(smtp_host="192.168.1.100", smtp_port=25)
    with pytest.raises(ValueError, match="SSRF"):
        send_email(cfg=cfg, subject="Test", body="body")


# ---------------------------------------------------------------------------
# SMTP (STARTTLS path) — timeout passed, multi-recipient sendmail
# ---------------------------------------------------------------------------


def test_starttls_path_timeout_and_recipients(monkeypatch):
    """Verify timeout is passed to smtplib.SMTP and all recipients reach sendmail."""
    from quirk.notify.channels.email import send_email

    captured = {}

    class _FakeSMTP:
        def __init__(self, host, port, timeout=None):
            captured["host"] = host
            captured["port"] = port
            captured["timeout"] = timeout
            captured["starttls_called"] = False
            captured["login_called"] = False
            captured["sendmail_args"] = None

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def ehlo(self):
            pass

        def starttls(self, context=None):
            captured["starttls_called"] = True

        def login(self, user, password):
            captured["login_called"] = True
            captured["login_user"] = user

        def sendmail(self, from_addr, to_addrs, msg):
            captured["sendmail_args"] = (from_addr, to_addrs, msg)

    monkeypatch.setattr(smtplib, "SMTP", _FakeSMTP)
    monkeypatch.setenv("QUIRK_SMTP_PASS", "secret123")

    cfg = _make_cfg(
        smtp_host="smtp.example.com",
        smtp_port=587,
        recipients=["a@example.com", "b@example.com"],
        timeout_seconds=15,
        use_ssl=False,
    )
    send_email(cfg=cfg, subject="Alert", body="Hello world")

    assert captured["timeout"] == 15, f"Expected timeout=15, got {captured['timeout']}"
    assert captured["starttls_called"], "STARTTLS must be called for non-SSL path"
    assert captured["login_called"], "login() must be called when smtp_user is set"
    assert set(captured["sendmail_args"][1]) == {"a@example.com", "b@example.com"}, \
        f"Both recipients must be in sendmail call, got {captured['sendmail_args'][1]}"


# ---------------------------------------------------------------------------
# SMTP_SSL path — timeout passed
# ---------------------------------------------------------------------------


def test_ssl_path_timeout_passed(monkeypatch):
    """Verify timeout is passed to smtplib.SMTP_SSL."""
    from quirk.notify.channels.email import send_email

    captured = {}

    class _FakeSMTP_SSL:
        def __init__(self, host, port, context=None, timeout=None):
            captured["host"] = host
            captured["port"] = port
            captured["timeout"] = timeout
            captured["sendmail_args"] = None
            captured["login_called"] = False

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def login(self, user, password):
            captured["login_called"] = True

        def sendmail(self, from_addr, to_addrs, msg):
            captured["sendmail_args"] = (from_addr, to_addrs, msg)

    monkeypatch.setattr(smtplib, "SMTP_SSL", _FakeSMTP_SSL)
    monkeypatch.setenv("QUIRK_SMTP_PASS", "secret")

    cfg = _make_cfg(
        smtp_host="smtp.example.com",
        smtp_port=465,
        recipients=["user@example.com"],
        timeout_seconds=8,
        use_ssl=True,
    )
    send_email(cfg=cfg, subject="Alert SSL", body="SSL body")

    assert captured["timeout"] == 8, f"Expected timeout=8, got {captured['timeout']}"
    assert captured["login_called"], "login() must be called when smtp_user is set"
    assert "user@example.com" in captured["sendmail_args"][1], \
        f"Recipient missing from sendmail call: {captured['sendmail_args']}"


# ---------------------------------------------------------------------------
# Login skipped when smtp_user is None
# ---------------------------------------------------------------------------


def test_no_login_when_smtp_user_none(monkeypatch):
    """When smtp_user is None, login() must not be called."""
    from quirk.notify.channels.email import send_email

    login_calls = []

    class _FakeSMTP:
        def __init__(self, host, port, timeout=None):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def ehlo(self):
            pass

        def starttls(self, context=None):
            pass

        def login(self, *args):
            login_calls.append(args)

        def sendmail(self, *args):
            pass

    monkeypatch.setattr(smtplib, "SMTP", _FakeSMTP)

    cfg = _make_cfg(smtp_user=None, smtp_password_env=None, use_ssl=False)
    send_email(cfg=cfg, subject="No auth", body="No auth body")

    assert login_calls == [], "login() must not be called when smtp_user is None"


# ---------------------------------------------------------------------------
# Source-level assertion helpers (called from acceptance criteria verification)
# ---------------------------------------------------------------------------


def test_source_has_two_timeout_kwargs():
    """Acceptance: email.py contains at least 2 occurrences of 'timeout=' (SMTP + SMTP_SSL)."""
    import re
    import pathlib

    src = pathlib.Path(__file__).parent.parent / "quirk" / "notify" / "channels" / "email.py"
    text = src.read_text(encoding="utf-8")
    matches = re.findall(r"\btimeout=", text)
    assert len(matches) >= 2, \
        f"Expected at least 2 'timeout=' occurrences in email.py, found {len(matches)}"
