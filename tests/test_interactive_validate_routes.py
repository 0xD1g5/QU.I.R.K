"""Tests for Phase 75 APCL-04 (WR-10..WR-16) — interactive + validate + routes hardening.

Covers seven decisions:
- D-11 (WR-10): _prompt_int EOF-safe with in-range default; out-of-range default raises ValueError
- D-12 (WR-11): Exposure prompt 3-retry reprompt; ValueError on exhaustion
- D-13 (WR-12): ConnectorsCfg.enable_nmap declared field; setattr site removed from interactive.py
- D-14 (WR-13): validate.py expected_files includes intelligence-{stamp}.json
- D-15 (WR-14): qramm_cmd env override try/except on malformed input
- D-16 (WR-15): QUIRK_OUTPUT_DIR realpath + CWD-descent + .. reject
- D-17 (WR-16): parse_target_tokens RFC-1123 hostname validation + IP fallback
"""
from __future__ import annotations

import datetime
import logging
import os
import re
from pathlib import Path
from unittest.mock import patch

import pytest


# ----------------------------------------------------------------------
# D-11 (WR-10) — _prompt_int EOF safety
# ----------------------------------------------------------------------

def test_prompt_int_eof_returns_in_range_default():
    """EOFError on input must NOT infinite-loop; should return in-range default."""
    from quirk.interactive import _prompt_int
    with patch("builtins.input", side_effect=EOFError):
        result = _prompt_int("Enter int", default=2, minv=1, maxv=100)
    assert result == 2


def test_prompt_int_default_out_of_range_raises():
    """Default outside [minv, maxv] must raise ValueError at function entry."""
    from quirk.interactive import _prompt_int
    with pytest.raises(ValueError):
        _prompt_int("Enter int", default=0, minv=1, maxv=100)


def test_prompt_int_happy_path_returns_parsed_value():
    from quirk.interactive import _prompt_int
    with patch("builtins.input", return_value="5"):
        assert _prompt_int("Enter int", default=2, minv=1, maxv=100) == 5


# ----------------------------------------------------------------------
# D-12 (WR-11) — exposure prompt reprompt
# ----------------------------------------------------------------------

def test_exposure_prompt_third_try_succeeds(capsys):
    from quirk.interactive import _prompt_exposure
    with patch("builtins.input", side_effect=["bad", "alsobad", "1"]):
        result = _prompt_exposure(default=2)
    assert result == 1
    captured = capsys.readouterr()
    assert "Invalid choice 'bad'; expected 1, 2, or 3." in captured.out


def test_exposure_prompt_exhausted_raises():
    from quirk.interactive import _prompt_exposure
    with patch("builtins.input", side_effect=["bad", "alsobad", "stillbad"]):
        with pytest.raises(ValueError, match="Exposure selection exhausted retry budget"):
            _prompt_exposure(default=2)


def test_exposure_prompt_eof_returns_default():
    from quirk.interactive import _prompt_exposure
    with patch("builtins.input", side_effect=EOFError):
        assert _prompt_exposure(default=2) == 2


# ----------------------------------------------------------------------
# D-13 (WR-12) — ConnectorsCfg.enable_nmap declared field
# ----------------------------------------------------------------------

def test_connectors_cfg_has_enable_nmap_field():
    from quirk.config import ConnectorsCfg
    cfg = ConnectorsCfg()
    assert cfg.enable_nmap is False


def test_interactive_py_no_setattr_enable_nmap():
    """Static check: setattr-enable_nmap injection removed from interactive.py."""
    src = Path("quirk/interactive.py").read_text(encoding="utf-8")
    assert 'setattr(cfg.connectors, "enable_nmap"' not in src
    assert "setattr(cfg.connectors, 'enable_nmap'" not in src


# ----------------------------------------------------------------------
# D-14 (WR-13) — validate.py expected_files
# ----------------------------------------------------------------------

def test_validate_py_expects_intelligence_artifact():
    """validate.py expected_files list must reference intelligence-{stamp}.json."""
    src = Path("quirk/validate.py").read_text(encoding="utf-8")
    assert re.search(r'intelligence-\{stamp\}\.json', src) or \
        re.search(r'f"intelligence-\{stamp\}\.json"', src)


# ----------------------------------------------------------------------
# D-15 (WR-14) — qramm_cmd env override try/except
# ----------------------------------------------------------------------

def test_qramm_cmd_invalid_env_falls_back(monkeypatch, caplog):
    from quirk.cli import qramm_cmd
    monkeypatch.setenv("QUIRK_CI_STALENESS_OVERRIDE_DATE", "not-a-date")
    caplog.set_level(logging.WARNING, logger="quirk.cli.qramm_cmd")
    result = qramm_cmd._resolve_today()
    assert result == datetime.date.today()
    assert any("QRAMM cmd env override invalid" in r.message for r in caplog.records)


def test_qramm_cmd_valid_env_returns_parsed(monkeypatch):
    from quirk.cli import qramm_cmd
    monkeypatch.setenv("QUIRK_CI_STALENESS_OVERRIDE_DATE", "2026-05-15")
    assert qramm_cmd._resolve_today() == datetime.date(2026, 5, 15)


# ----------------------------------------------------------------------
# D-16 (WR-15) — QUIRK_OUTPUT_DIR path-traversal guard
# ----------------------------------------------------------------------

def test_output_dir_outside_cwd_raises(monkeypatch):
    from quirk.dashboard.api.routes.scan import _resolve_output_dir
    monkeypatch.setenv("QUIRK_OUTPUT_DIR", "/etc")
    with pytest.raises(ValueError, match="resolves outside CWD"):
        _resolve_output_dir()


def test_output_dir_dotdot_rejected(monkeypatch):
    from quirk.dashboard.api.routes.scan import _resolve_output_dir
    monkeypatch.setenv("QUIRK_OUTPUT_DIR", "./quirk-output/../../../etc")
    with pytest.raises(ValueError):
        _resolve_output_dir()


def test_output_dir_valid_returns_path(monkeypatch, tmp_path):
    from quirk.dashboard.api.routes.scan import _resolve_output_dir
    sub = tmp_path / "out"
    sub.mkdir()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("QUIRK_OUTPUT_DIR", "./out")
    result = _resolve_output_dir()
    assert Path(result).resolve() == sub.resolve()


# ----------------------------------------------------------------------
# D-17 (WR-16) — RFC-1123 hostname validation + IP fallback
# ----------------------------------------------------------------------

@pytest.mark.parametrize("token", [
    "good.example.com",
    "sub.domain.co.uk",
    "single-label",
    "a1.b2.c3",
    "1.2.3.4",
    "::1",
    "2001:db8::1",
])
def test_parse_target_tokens_accepts_valid(token):
    from quirk.util.targets import parse_target_tokens
    fqdns, cidrs = parse_target_tokens(token)
    assert token in fqdns


@pytest.mark.parametrize("token", [
    "-leading.com",
    "a..b.com",
    "host_with_underscore",
    "host with space",
    "bad!chars",
])
def test_parse_target_tokens_rejects_invalid(token):
    from quirk.util.targets import parse_target_tokens
    with pytest.raises(ValueError, match="not a valid hostname or IP address"):
        parse_target_tokens(token)
