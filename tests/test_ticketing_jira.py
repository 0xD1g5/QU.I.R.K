"""Unit tests for quirk.ticketing.jira — JiraChannel (Phase 104 TICKET-01/TICKET-03).

Covers:
  - test_create_issue_per_finding: search returns [] → create_issue called once, key returned
  - test_dedup_creates_once_then_comments: first dispatch creates; second dispatch comments, no new issue
  - test_missing_extra_graceful_skip: absent jira package → ImportError with advisory message
  - test_credentials_not_in_logs: planted Bearer token in exc → absent from error_summary (safe_str ISEC-02)
  - test_jql_project_key_quoted: JQL passed to search_issues double-quotes project key (Pitfall 4)
"""
from __future__ import annotations

import os
import sys
from typing import Optional
from unittest.mock import MagicMock, call, patch

import pytest

from quirk.ticketing.config import JiraTicketingCfg


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _make_cfg(
    jira_url: str = "https://myco.atlassian.net",
    project_key: str = "SEC",
    auth_mode: str = "cloud",
    allow_internal: bool = False,
    jira_user_env: str = "QUIRK_JIRA_USER",
    jira_token_env: str = "QUIRK_JIRA_TOKEN",
) -> JiraTicketingCfg:
    """Build a JiraTicketingCfg with defaults suitable for unit tests."""
    return JiraTicketingCfg(
        jira_url=jira_url,
        jira_user_env=jira_user_env,
        jira_token_env=jira_token_env,
        project_key=project_key,
        issue_type="Bug",
        auth_mode=auth_mode,
        allow_internal=allow_internal,
    )


def _make_mock_jira_client() -> MagicMock:
    """Return a MagicMock JIRA client with sensible defaults."""
    client = MagicMock()
    client.search_issues.return_value = []  # no existing issue by default
    mock_issue = MagicMock()
    mock_issue.key = "SEC-1"
    client.create_issue.return_value = mock_issue
    return client


def _make_mock_jira_cls(client: MagicMock) -> MagicMock:
    """Return a MagicMock JIRA class whose __call__ returns *client*."""
    jira_cls = MagicMock()
    jira_cls.return_value = client
    return jira_cls


def _build_channel(cfg: JiraTicketingCfg, client: MagicMock) -> "JiraChannel":  # noqa: F821
    """Construct a JiraChannel with a mocked JIRA client via sys.modules patch."""
    from quirk.ticketing.jira import JiraChannel  # import after patch is set

    jira_cls = _make_mock_jira_cls(client)
    mock_jira_module = MagicMock()
    mock_jira_module.JIRA = jira_cls

    with patch.dict("sys.modules", {"jira": mock_jira_module}):
        channel = JiraChannel(cfg)
    return channel


def _sample_finding() -> dict:
    return {
        "title": "Weak TLS cipher",
        "severity": "HIGH",
        "host": "example.com",
        "port": "443",
        "description": "TLS 1.0 accepted",
        "recommendation": "Disable TLS 1.0",
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_create_issue_per_finding(monkeypatch: pytest.MonkeyPatch) -> None:
    """First scan: search_issues returns [] → create_issue called once → key returned.

    Covers TICKET-01: a Jira issue is created per finding with QRAMM evidence.
    """
    monkeypatch.setenv("QUIRK_JIRA_USER", "user@example.com")
    monkeypatch.setenv("QUIRK_JIRA_TOKEN", "tok_abc")

    cfg = _make_cfg()
    client = _make_mock_jira_client()
    channel = _build_channel(cfg, client)

    finding = _sample_finding()
    fp = channel.compute_fingerprint(finding)
    evidence = channel.build_ticket_evidence(finding)

    result = channel.create_issue_from_finding(finding, fp, evidence)

    # Exactly one create_issue call with the fingerprint as a label
    assert result == "SEC-1"
    client.create_issue.assert_called_once()
    call_kwargs = client.create_issue.call_args
    fields = call_kwargs.kwargs.get("fields") or call_kwargs.args[0]
    assert fp in fields["labels"]
    assert fields["description"] == evidence
    assert fields["summary"][:255] == "Weak TLS cipher"


def test_dedup_creates_once_then_comments(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pytest.TempPathFactory
) -> None:
    """Two dispatch_finding calls with the same finding: create_issue called exactly
    once (first run), add_comment called on the second run — zero new issues (TICKET-03).
    """
    monkeypatch.setenv("QUIRK_JIRA_USER", "user@example.com")
    monkeypatch.setenv("QUIRK_JIRA_TOKEN", "tok_abc")

    cfg = _make_cfg()
    client = _make_mock_jira_client()

    # First run: no existing issue
    client.search_issues.return_value = []
    mock_issue = MagicMock()
    mock_issue.key = "SEC-42"
    client.create_issue.return_value = mock_issue

    channel = _build_channel(cfg, client)
    finding = _sample_finding()
    fp = channel.compute_fingerprint(finding)

    # Build a real tmp DB for audit row writes
    db_path = str(tmp_path / "test.db")
    from quirk.db import get_session, init_db

    init_db(db_path)
    with get_session(db_path) as db:
        channel.dispatch_finding(finding, db, "scan-001")

    # First dispatch: create called once, add_comment not called
    assert client.create_issue.call_count == 1
    assert client.add_comment.call_count == 0

    # Second run: existing issue returned by search
    existing = MagicMock()
    existing.key = "SEC-42"
    client.search_issues.return_value = [existing]

    with get_session(db_path) as db:
        channel.dispatch_finding(finding, db, "scan-002")

    # Second dispatch: create NOT called again; add_comment called once
    assert client.create_issue.call_count == 1, "create_issue must not be called on second run"
    assert client.add_comment.call_count == 1
    # add_comment first arg is the issue key
    add_comment_args = client.add_comment.call_args.args
    assert add_comment_args[0] == "SEC-42"
    # Body includes the fingerprint
    assert fp in add_comment_args[1]


def test_missing_extra_graceful_skip(monkeypatch: pytest.MonkeyPatch) -> None:
    """When jira package is not installed, JiraChannel(cfg) raises ImportError with advisory.

    Covers ISEC-04: missing [tickets] extra → advisory message, never a bare ModuleNotFoundError.
    """
    monkeypatch.setenv("QUIRK_JIRA_USER", "u")
    monkeypatch.setenv("QUIRK_JIRA_TOKEN", "t")

    cfg = _make_cfg()

    # Remove jira from sys.modules and replace with a broken import
    broken = sys.modules.copy()
    broken.pop("jira", None)

    def _broken_import(name, *args, **kwargs):
        if name == "jira":
            raise ImportError("No module named 'jira'")
        return original_import(name, *args, **kwargs)

    import builtins
    original_import = builtins.__import__

    # Re-import JiraChannel fresh with jira absent
    jira_module = sys.modules.pop("quirk.ticketing.jira", None)
    try:
        with patch.dict("sys.modules", {"jira": None}):  # None causes ImportError on "from jira import ..."
            # Force re-import of jira.py
            if "quirk.ticketing.jira" in sys.modules:
                del sys.modules["quirk.ticketing.jira"]
            from quirk.ticketing.jira import JiraChannel as _JiraChannel

            with pytest.raises(ImportError) as exc_info:
                _JiraChannel(cfg)
    finally:
        # Restore the module cache so other tests are unaffected
        if jira_module is not None:
            sys.modules["quirk.ticketing.jira"] = jira_module

    assert "pip install quirk[tickets]" in str(exc_info.value)


def test_credentials_not_in_logs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pytest.TempPathFactory
) -> None:
    """Exception whose message embeds a Bearer token must not appear in error_summary.

    Covers ISEC-02: safe_str() scrubs Authorization: Bearer patterns.
    Plants a recognizable fake token and asserts it is absent from the DB audit row.
    """
    monkeypatch.setenv("QUIRK_JIRA_USER", "user@example.com")
    monkeypatch.setenv("QUIRK_JIRA_TOKEN", "FAKE_JIRA_TOKEN_abc123xyz")

    cfg = _make_cfg()
    client = _make_mock_jira_client()

    # Make create_issue raise with a credential-bearing message
    fake_token = "FAKE_JIRA_TOKEN_abc123xyz"
    client.search_issues.return_value = []
    client.create_issue.side_effect = RuntimeError(
        f"HTTP 401 Unauthorized: Authorization: Bearer {fake_token}"
    )

    channel = _build_channel(cfg, client)
    finding = _sample_finding()

    db_path = str(tmp_path / "creds_test.db")
    from quirk.db import get_session, init_db
    from quirk.models import IntegrationDelivery

    init_db(db_path)
    with get_session(db_path) as db:
        channel.dispatch_finding(finding, db, "scan-creds")

        rows = db.query(IntegrationDelivery).filter(
            IntegrationDelivery.destination == "jira"
        ).all()

    assert rows, "audit row must be written even on failure"
    row = rows[0]
    assert row.status == "failed"
    assert row.error_summary is not None
    # The raw token must NOT appear in error_summary (safe_str enforcement)
    assert fake_token not in row.error_summary, (
        f"Credential token leaked into error_summary: {row.error_summary!r}"
    )


def test_jql_project_key_quoted(monkeypatch: pytest.MonkeyPatch) -> None:
    """JQL passed to search_issues double-quotes the project key (Pitfall 4 prevention).

    Covers TICKET-03 anti-pattern: unquoted project key breaks JQL for multi-word keys.
    """
    monkeypatch.setenv("QUIRK_JIRA_USER", "u")
    monkeypatch.setenv("QUIRK_JIRA_TOKEN", "t")

    cfg = _make_cfg(project_key="SEC")
    client = _make_mock_jira_client()
    client.search_issues.return_value = []

    channel = _build_channel(cfg, client)
    fp = "a" * 64  # 64-char hex-like fingerprint

    channel.find_by_fingerprint(fp)

    assert client.search_issues.called
    jql_arg = client.search_issues.call_args.args[0]

    # Project key must be double-quoted in the JQL string
    assert 'project = "SEC"' in jql_arg, (
        f"Expected double-quoted project key in JQL; got: {jql_arg!r}"
    )
    # Fingerprint label must also be double-quoted
    assert f'labels = "{fp}"' in jql_arg, (
        f"Expected double-quoted labels in JQL; got: {jql_arg!r}"
    )
