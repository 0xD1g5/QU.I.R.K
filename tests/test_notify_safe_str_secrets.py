"""Guard tests: safe_str redacts integration-secret shapes (Phase 101 / ISEC-02).

Three new patterns added to _SENSITIVE_PATTERNS in Phase 101:
  1. Slack bot/user tokens: xox[bpoa]-<10+ alphanumeric/dash chars>
  2. Slack incoming webhook URLs: hooks.slack.com/services/<path>
  3. SMTP connection strings with embedded credentials: smtp[s]://user:pass@host

Phase 104 (CR-02):
  4. Jira auth tuple repr: basic_auth=('user', 'shortpat') / token_auth=<value>
     Covers short Jira Server PATs that are < 40 chars and bypass the base64 pattern.

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


def test_jira_basic_auth_short_pat_is_redacted() -> None:
    """ISEC-02 / CR-02: short Jira Server PAT in basic_auth= repr must be scrubbed.

    Jira Server PATs can be < 40 chars and bypass the base64 pattern.
    The basic_auth=('user', 'token') shape in exception messages must be caught.
    """
    short_token = "ABCDEFGHIJKLMNabcdefghij"  # 24 chars — typical Jira Server PAT
    exc = Exception(
        f"JIRAError: 401 Unauthorized, basic_auth=('user@co.com', '{short_token}')"
    )
    result = safe_str(exc)
    assert short_token not in result, (
        f"Short Jira PAT leaked into safe_str output: {result!r}"
    )


def test_jira_token_auth_is_redacted() -> None:
    """ISEC-02 / CR-02: token_auth= shape in Jira exception repr must be scrubbed."""
    short_token = "myshortpat123"  # 13 chars — well below 40-char floor
    exc = Exception(
        f"Connection error: token_auth='{short_token}' rejected by server"
    )
    result = safe_str(exc)
    assert short_token not in result, (
        f"Short token_auth value leaked into safe_str output: {result!r}"
    )


def test_basic_auth_variable_reference_not_over_redacted():
    """CR-02 iter-2: a variable-reference repr (no quotes) must NOT be over-redacted.

    basic_auth=(user, token) is a Python variable reference, not a credential
    literal — safe_str must preserve the error so the cause stays debuggable.
    """
    from quirk.util.safe_exc import safe_str

    exc = Exception("TypeError: basic_auth=(user, token) expected str, got tuple")
    out = safe_str(exc)
    assert "expected str" in out  # error cause preserved, not collapsed to class name


def test_basic_auth_credential_literal_redacted():
    """CR-02: a credential literal (quoted) IS redacted including short PATs."""
    from quirk.util.safe_exc import safe_str

    out = safe_str(Exception("JIRAError basic_auth=('alice@co.com', 'shortpat123')"))
    assert "shortpat123" not in out
    out2 = safe_str(Exception("auth failed token_auth='shortPAT99'"))
    assert "shortPAT99" not in out2
