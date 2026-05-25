"""CLI tests for quirk.cli.ticket_cmd — Phase 104 TICKET-01, Phase 105 TICKET-02.

Covers:
  1. Missing [tickets] extra → advisory to stderr + exit 2 (no ImportError traceback)
  2. No findings file in output dir → exit 2
  3. --input flag reads specified file (mocked dispatch confirms file is read)
  4. Missing ticketing config → exit 2
  5. Happy path — all dispatched → exit 0
  6. --backend servicenow dispatches through ServiceNowChannel
  7. --backend servicenow with missing servicenow block → exit 2
  8. Default (no --backend) routes to JiraChannel (regression)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from quirk.cli.ticket_cmd import run_ticket


# ---------------------------------------------------------------------------
# Test 1: missing [tickets] extra
# ---------------------------------------------------------------------------


def test_missing_extra_advisory(capsys: pytest.CaptureFixture) -> None:
    """When [tickets] is not installed, exit 2 and emit pip-install advisory."""
    with patch("quirk.cli.ticket_cmd.is_extra_available", return_value=False):
        with pytest.raises(SystemExit) as exc_info:
            run_ticket(["create"])
        assert exc_info.value.code == 2

    captured = capsys.readouterr()
    assert "pip install quirk[tickets]" in captured.err


# ---------------------------------------------------------------------------
# Test 2: no findings file in output dir
# ---------------------------------------------------------------------------


def test_no_findings_file(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """Empty output dir (no findings-*.json) → exit 2."""
    with patch("quirk.cli.ticket_cmd.is_extra_available", return_value=True):
        with pytest.raises(SystemExit) as exc_info:
            run_ticket(["create", "--output-dir", str(tmp_path)])
        assert exc_info.value.code == 2

    captured = capsys.readouterr()
    assert "no findings file" in captured.err.lower()


# ---------------------------------------------------------------------------
# Test 3: --input flag reads specified file
# ---------------------------------------------------------------------------


def test_input_flag(tmp_path: Path) -> None:
    """--input <path> reads the specified file; dispatch is called for each finding."""
    findings = [
        {"host": "example.com", "port": 443, "title": "Weak TLS", "severity": "high"},
        {"host": "other.com", "port": 8443, "title": "Expired Cert", "severity": "medium"},
    ]
    findings_file = tmp_path / "findings-20260525-120000.json"
    findings_file.write_text(json.dumps(findings), encoding="utf-8")

    mock_cfg = MagicMock()
    mock_cfg.jira = MagicMock()

    mock_channel = MagicMock()
    mock_db_ctx = MagicMock()
    mock_db_ctx.__enter__ = MagicMock(return_value=MagicMock())
    mock_db_ctx.__exit__ = MagicMock(return_value=False)

    with patch("quirk.cli.ticket_cmd.is_extra_available", return_value=True), \
         patch("quirk.cli.ticket_cmd.load_ticketing_config", return_value=mock_cfg), \
         patch("quirk.db.get_session", return_value=mock_db_ctx), \
         patch("quirk.ticketing.jira.JiraChannel", return_value=mock_channel):
        # Should complete without raising SystemExit
        try:
            run_ticket(["create", "--input", str(findings_file)])
        except SystemExit as e:
            pytest.fail(f"run_ticket raised SystemExit({e.code}) on happy path with --input")


# ---------------------------------------------------------------------------
# Test 4: missing ticketing config
# ---------------------------------------------------------------------------


def test_missing_config(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """When load_ticketing_config() returns None, exit 2."""
    findings = [{"host": "h", "port": 443, "title": "T", "severity": "high"}]
    findings_file = tmp_path / "findings-20260525-120000.json"
    findings_file.write_text(json.dumps(findings), encoding="utf-8")

    with patch("quirk.cli.ticket_cmd.is_extra_available", return_value=True), \
         patch("quirk.cli.ticket_cmd.load_ticketing_config", return_value=None):
        with pytest.raises(SystemExit) as exc_info:
            run_ticket(["create", "--input", str(findings_file)])
        assert exc_info.value.code == 2

    captured = capsys.readouterr()
    assert "config" in captured.err.lower() or "QUIRK_CONFIG_PATH" in captured.err


# ---------------------------------------------------------------------------
# Test 5: happy path — all dispatched, exits 0
# ---------------------------------------------------------------------------


def test_exit_0_all_dispatched(tmp_path: Path) -> None:
    """Happy path: mocked JiraChannel.dispatch_finding; exits 0 (no SystemExit raised)."""
    findings = [
        {"host": "example.com", "port": 443, "title": "Weak TLS", "severity": "high"},
    ]
    findings_file = tmp_path / "findings-20260525-120000.json"
    findings_file.write_text(json.dumps(findings), encoding="utf-8")

    mock_cfg = MagicMock()
    mock_cfg.jira = MagicMock()

    mock_channel_instance = MagicMock()
    mock_channel_cls = MagicMock(return_value=mock_channel_instance)

    mock_db = MagicMock()
    mock_db_ctx = MagicMock()
    mock_db_ctx.__enter__ = MagicMock(return_value=mock_db)
    mock_db_ctx.__exit__ = MagicMock(return_value=False)

    with patch("quirk.cli.ticket_cmd.is_extra_available", return_value=True), \
         patch("quirk.cli.ticket_cmd.load_ticketing_config", return_value=mock_cfg), \
         patch("quirk.db.get_session", return_value=mock_db_ctx), \
         patch("quirk.ticketing.jira.JiraChannel", mock_channel_cls):
        # Happy path should NOT raise SystemExit
        try:
            run_ticket(["create", "--input", str(findings_file)])
        except SystemExit as e:
            pytest.fail(f"Happy path raised SystemExit({e.code})")

    # dispatch_finding should have been called once per finding
    assert mock_channel_instance.dispatch_finding.call_count == len(findings)


# ---------------------------------------------------------------------------
# Test 6: --backend servicenow dispatches through ServiceNowChannel
# ---------------------------------------------------------------------------


def test_backend_servicenow(tmp_path: Path) -> None:
    """--backend servicenow constructs ServiceNowChannel and calls dispatch_finding per finding."""
    findings = [
        {"host": "example.com", "port": 443, "title": "Weak TLS", "severity": "high"},
        {"host": "other.com", "port": 8443, "title": "Expired Cert", "severity": "medium"},
    ]
    findings_file = tmp_path / "findings-20260525-120000.json"
    findings_file.write_text(json.dumps(findings), encoding="utf-8")

    mock_cfg = MagicMock()
    mock_cfg.jira = MagicMock()
    mock_cfg.servicenow = MagicMock()  # servicenow block is present

    mock_channel_instance = MagicMock()
    mock_channel_cls = MagicMock(return_value=mock_channel_instance)

    mock_db = MagicMock()
    mock_db_ctx = MagicMock()
    mock_db_ctx.__enter__ = MagicMock(return_value=mock_db)
    mock_db_ctx.__exit__ = MagicMock(return_value=False)

    with patch("quirk.cli.ticket_cmd.is_extra_available", return_value=True), \
         patch("quirk.cli.ticket_cmd.load_ticketing_config", return_value=mock_cfg), \
         patch("quirk.db.get_session", return_value=mock_db_ctx), \
         patch("quirk.ticketing.servicenow.ServiceNowChannel", mock_channel_cls):
        try:
            run_ticket(["create", "--input", str(findings_file), "--backend", "servicenow"])
        except SystemExit as e:
            pytest.fail(f"--backend servicenow raised SystemExit({e.code}) on happy path")

    # ServiceNowChannel should have been constructed with cfg.servicenow
    mock_channel_cls.assert_called_once_with(mock_cfg.servicenow)
    # dispatch_finding should have been called once per finding
    assert mock_channel_instance.dispatch_finding.call_count == len(findings)


# ---------------------------------------------------------------------------
# Test 7: --backend servicenow with missing servicenow config block → exit 2
# ---------------------------------------------------------------------------


def test_backend_servicenow_missing_config(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """--backend servicenow but cfg.servicenow is None → exit 2 with clear error."""
    findings = [{"host": "h", "port": 443, "title": "T", "severity": "high"}]
    findings_file = tmp_path / "findings-20260525-120000.json"
    findings_file.write_text(json.dumps(findings), encoding="utf-8")

    mock_cfg = MagicMock()
    mock_cfg.servicenow = None  # servicenow block is absent

    with patch("quirk.cli.ticket_cmd.is_extra_available", return_value=True), \
         patch("quirk.cli.ticket_cmd.load_ticketing_config", return_value=mock_cfg):
        with pytest.raises(SystemExit) as exc_info:
            run_ticket(["create", "--input", str(findings_file), "--backend", "servicenow"])
        assert exc_info.value.code == 2

    captured = capsys.readouterr()
    assert "servicenow" in captured.err.lower()
    assert "QUIRK_CONFIG_PATH" in captured.err


# ---------------------------------------------------------------------------
# Test 8: Default (no --backend) still routes to JiraChannel (regression)
# ---------------------------------------------------------------------------


def test_default_backend_uses_jira(tmp_path: Path) -> None:
    """No --backend flag → JiraChannel is constructed (backward-compat regression)."""
    findings = [
        {"host": "example.com", "port": 443, "title": "Weak TLS", "severity": "high"},
    ]
    findings_file = tmp_path / "findings-20260525-120000.json"
    findings_file.write_text(json.dumps(findings), encoding="utf-8")

    mock_cfg = MagicMock()
    mock_cfg.jira = MagicMock()
    mock_cfg.servicenow = MagicMock()  # present but must NOT be used

    mock_channel_instance = MagicMock()
    mock_channel_cls = MagicMock(return_value=mock_channel_instance)

    mock_snow_cls = MagicMock()

    mock_db = MagicMock()
    mock_db_ctx = MagicMock()
    mock_db_ctx.__enter__ = MagicMock(return_value=mock_db)
    mock_db_ctx.__exit__ = MagicMock(return_value=False)

    with patch("quirk.cli.ticket_cmd.is_extra_available", return_value=True), \
         patch("quirk.cli.ticket_cmd.load_ticketing_config", return_value=mock_cfg), \
         patch("quirk.db.get_session", return_value=mock_db_ctx), \
         patch("quirk.ticketing.jira.JiraChannel", mock_channel_cls), \
         patch("quirk.ticketing.servicenow.ServiceNowChannel", mock_snow_cls):
        try:
            run_ticket(["create", "--input", str(findings_file)])
        except SystemExit as e:
            pytest.fail(f"Default backend raised SystemExit({e.code})")

    # JiraChannel must have been constructed with cfg.jira
    mock_channel_cls.assert_called_once_with(mock_cfg.jira)
    # ServiceNowChannel must NOT have been constructed
    mock_snow_cls.assert_not_called()


# ---------------------------------------------------------------------------
# Test 9: ServiceNowChannel init ValueError (SSRF) → correct error message (WR-02)
# ---------------------------------------------------------------------------


def test_servicenow_init_error_labelled_correctly(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """ValueError from ServiceNowChannel.__init__ (SSRF) must produce 'ticketing backend init
    failed', NOT 'audit-row persistence failed' (WR-02 regression).
    """
    findings = [{"host": "h", "port": 443, "title": "T", "severity": "high"}]
    findings_file = tmp_path / "findings-20260525-120000.json"
    findings_file.write_text(json.dumps(findings), encoding="utf-8")

    mock_cfg = MagicMock()
    mock_cfg.servicenow = MagicMock()  # servicenow block present

    def _raising_init(cfg):
        raise ValueError("SSRF blocked (loopback) for ServiceNow URL")

    with patch("quirk.cli.ticket_cmd.is_extra_available", return_value=True), \
         patch("quirk.cli.ticket_cmd.load_ticketing_config", return_value=mock_cfg), \
         patch("quirk.ticketing.servicenow.ServiceNowChannel", side_effect=_raising_init):
        with pytest.raises(SystemExit) as exc_info:
            run_ticket(["create", "--input", str(findings_file), "--backend", "servicenow"])
        assert exc_info.value.code == 2

    captured = capsys.readouterr()
    assert "ticketing backend init failed" in captured.err, (
        f"Expected 'ticketing backend init failed' in stderr, got: {captured.err!r}"
    )
    assert "audit-row persistence" not in captured.err, (
        f"'audit-row persistence' must not appear for an init error: {captured.err!r}"
    )
