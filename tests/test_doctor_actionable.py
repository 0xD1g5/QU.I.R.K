"""Phase 75-01 APCL-01 — RED-then-GREEN tests for D-01..D-03.

Covers:
  - D-01 (WR-01): _check_dashboard / _check_network typed status dict
                  {"ok": bool, "detail": str, "remediation": str}
  - D-02 (WR-02): _check_db honors QUIRK_DB_PATH env var; falls back to
                  _default_db_path() only when env is unset
  - D-03 (WR-03): _default_db_path single canonical resolution; raises
                  ValueError on multiple legacy DBs
"""
from __future__ import annotations

import os
import socket
from unittest.mock import patch
from urllib.error import URLError

import pytest

from quirk.cli.doctor_cmd import _check_dashboard, _check_db, _check_network
from quirk.dashboard.api.deps import _default_db_path


# ---------------------------------------------------------------------------
# D-01 (WR-01) — typed status dict shape on _check_dashboard / _check_network
# ---------------------------------------------------------------------------

EXPECTED_KEYS = {"ok", "detail", "remediation"}


def _assert_typed_status(result) -> None:
    assert isinstance(result, dict), f"expected dict, got {type(result).__name__}"
    assert set(result.keys()) == EXPECTED_KEYS, f"keys={set(result.keys())}"
    assert isinstance(result["ok"], bool)
    assert isinstance(result["detail"], str)
    assert isinstance(result["remediation"], str)


def test_check_dashboard_returns_typed_status_dict():
    """D-01: _check_dashboard returns {'ok', 'detail', 'remediation'} dict."""
    result = _check_dashboard()
    _assert_typed_status(result)


def test_check_network_returns_typed_status_dict():
    """D-01: _check_network returns {'ok', 'detail', 'remediation'} dict."""
    result = _check_network()
    _assert_typed_status(result)


def test_check_dashboard_unreachable_has_remediation():
    """D-01: When dashboard HTTP HEAD fails, ok is False and remediation non-empty."""
    with patch("quirk.cli.doctor_cmd.urlopen", side_effect=URLError("connection refused")):
        result = _check_dashboard()
    assert result["ok"] is False
    assert result["remediation"], "remediation must be non-empty on failure"
    assert isinstance(result["remediation"], str)


def test_check_network_dns_failure_has_remediation():
    """D-01: When DNS lookup fails, ok is False and remediation non-empty."""
    with patch("quirk.cli.doctor_cmd.socket.gethostbyname", side_effect=socket.gaierror("no resolver")):
        result = _check_network()
    assert result["ok"] is False
    assert result["remediation"], "remediation must mention next-step action"


# ---------------------------------------------------------------------------
# D-02 (WR-02) — _check_db honors QUIRK_DB_PATH env
# ---------------------------------------------------------------------------

def test_check_db_uses_quirk_db_path_env(tmp_path, monkeypatch):
    """D-02: When QUIRK_DB_PATH points at a readable file, _check_db reports ok=True."""
    db_file = tmp_path / "custom.db"
    db_file.write_bytes(b"")  # zero-byte file is fine for the existence/readable probe
    monkeypatch.setenv("QUIRK_DB_PATH", str(db_file))
    result = _check_db()
    assert isinstance(result, dict)
    assert set(result.keys()) == EXPECTED_KEYS
    assert result["ok"] is True


def test_check_db_quirk_db_path_nonexistent_fails(monkeypatch):
    """D-02: When QUIRK_DB_PATH is unreadable, ok=False and remediation mentions env var."""
    monkeypatch.setenv("QUIRK_DB_PATH", "/nonexistent/path/quirk.db")
    result = _check_db()
    assert isinstance(result, dict)
    assert result["ok"] is False
    assert "QUIRK_DB_PATH" in result["detail"] or "QUIRK_DB_PATH" in result["remediation"]


# ---------------------------------------------------------------------------
# D-03 (WR-03) — _default_db_path single canonical + fail-loud multi-DB
# ---------------------------------------------------------------------------

def test_default_db_path_no_dbs_returns_canonical(tmp_path, monkeypatch):
    """D-03: With no legacy DBs, returns canonical ./quirk-output/quirk.db."""
    monkeypatch.delenv("QUIRK_DB_PATH", raising=False)
    monkeypatch.chdir(tmp_path)
    result = _default_db_path()
    assert "quirk-output" in result and result.endswith("quirk.db")


def test_default_db_path_single_legacy_returns_it(tmp_path, monkeypatch):
    """D-03: With a single legacy DB present, deterministic return."""
    monkeypatch.delenv("QUIRK_DB_PATH", raising=False)
    monkeypatch.chdir(tmp_path)
    legacy = tmp_path / "quirk.db"
    legacy.write_bytes(b"")
    result = _default_db_path()
    assert result.endswith("quirk.db")


def test_default_db_path_multiple_legacy_raises_valueerror(tmp_path, monkeypatch):
    """D-03 (WR-03): Multiple DBs MUST raise ValueError; never silently pick."""
    monkeypatch.delenv("QUIRK_DB_PATH", raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "quirk.db").write_bytes(b"")
    (tmp_path / "output").mkdir()
    (tmp_path / "output" / "quirk.db").write_bytes(b"")
    (tmp_path / "quirk-output").mkdir()
    (tmp_path / "quirk-output" / "quirk.db").write_bytes(b"")
    with pytest.raises(ValueError, match=r"Multiple QU\.I\.R\.K\. DBs found.*set QUIRK_DB_PATH explicitly"):
        _default_db_path()
