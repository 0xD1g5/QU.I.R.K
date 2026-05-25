"""Guard tests: safe_str redacts integration-secret shapes (Phase 101 / ISEC-02).

Three new patterns added to _SENSITIVE_PATTERNS:
  1. Slack bot/user tokens: xox[bpoa]-<10+ alphanumeric/dash chars>
  2. Slack incoming webhook URLs: hooks.slack.com/services/<path>
  3. SMTP connection strings with embedded credentials: smtp[s]://user:pass@host

A plain non-secret message must pass through unredacted (no over-redaction).
"""
from __future__ import annotations

from quirk.util.safe_exc import safe_str


def test_slack_token_is_redacted() -> None:
    """ISEC-02: Slack xoxb- token shape must be scrubbed."""
    exc = Exception("Slack API call failed, token xoxb-1234567890-abcdEFGH was rejected")
    result = safe_str(exc)
    assert "xoxb-1234567890-abcdEFGH" not in result, (
        f"Slack token leaked into safe_str output: {result!r}"
    )


def test_slack_webhook_url_is_redacted() -> None:
    """ISEC-02: Slack incoming webhook URL path must be scrubbed."""
    exc = Exception("posted to https://hooks.slack.com/services/T00/B00/XXXXXXXX failed")
    result = safe_str(exc)
    assert "services/T00/B00/XXXXXXXX" not in result, (
        f"Slack webhook URL leaked into safe_str output: {result!r}"
    )


def test_smtp_connection_string_is_redacted() -> None:
    """ISEC-02: SMTP connection string with embedded password must be scrubbed."""
    exc = Exception("SMTP connect failed: smtp://user:hunter2@smtp.example.com")
    result = safe_str(exc)
    assert "hunter2" not in result, (
        f"SMTP password leaked into safe_str output: {result!r}"
    )


def test_smtps_connection_string_is_redacted() -> None:
    """ISEC-02: smtps:// variant with embedded password must also be scrubbed."""
    exc = Exception("Connection error smtps://admin:s3cr3t@mail.corp.example.com")
    result = safe_str(exc)
    assert "s3cr3t" not in result, (
        f"SMTPS password leaked into safe_str output: {result!r}"
    )


def test_ordinary_message_not_redacted() -> None:
    """ISEC-02 no-over-redaction: a plain non-secret message passes through intact."""
    exc = Exception("ordinary connection refused to 10.0.0.1:587")
    result = safe_str(exc)
    assert "ordinary connection refused" in result, (
        f"Non-secret message was incorrectly redacted: {result!r}"
    )
