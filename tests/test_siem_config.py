"""Tests for quirk/siem/config.py — SiemCfg loader (Phase 103 SIEM-01).

Covers:
- Unset QUIRK_CONFIG_PATH + no path -> None (disabled)
- Valid YAML with [siem] block -> populated SiemCfg with all fields
- Missing [siem] key in valid YAML -> None
- Binary/SQLite file path -> None (Pitfall 2 guard: DB path mistaken for YAML)
- Default field values when absent from YAML
- loopback/internal hosts are NOT blocked
"""
from __future__ import annotations

import os
import textwrap

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_siem_yaml(tmp_path, **overrides) -> str:
    """Write a minimal valid QUIRK YAML config with a [siem] block."""
    host = overrides.get("host", "siem.corp.example.com")
    port = overrides.get("port", 514)
    protocol = overrides.get("protocol", "udp")
    export_after_scan = overrides.get("export_after_scan", False)
    timeout_seconds = overrides.get("timeout_seconds", 5)
    content = textwrap.dedent(f"""\
        siem:
          host: {host}
          port: {port}
          protocol: {protocol}
          export_after_scan: {str(export_after_scan).lower()}
          timeout_seconds: {timeout_seconds}
    """)
    p = tmp_path / "config.yaml"
    p.write_text(content)
    return str(p)


def _write_no_siem_block(tmp_path) -> str:
    """Valid YAML but NO [siem] key."""
    content = textwrap.dedent("""\
        assessment:
          name: test
          data_classification: internal
          report_owner: test
          timezone: UTC
    """)
    p = tmp_path / "no_siem.yaml"
    p.write_text(content)
    return str(p)


def _write_binary_db_file(tmp_path, filename: str = "quirk.db") -> str:
    """Write a binary SQLite-header file to simulate the DB-path trap (Pitfall 2)."""
    p = tmp_path / filename
    # SQLite magic header
    p.write_bytes(b"SQLite format 3\x00" + b"\x00" * 100)
    return str(p)


# ---------------------------------------------------------------------------
# Tests — load_siem_config: no path
# ---------------------------------------------------------------------------

class TestLoadSiemConfigNoPath:
    """QUIRK_CONFIG_PATH unset + no explicit path -> None."""

    def test_no_env_no_path_returns_none(self, monkeypatch):
        monkeypatch.delenv("QUIRK_CONFIG_PATH", raising=False)
        from quirk.siem.config import load_siem_config

        result = load_siem_config()
        assert result is None

    def test_explicit_none_path_returns_none(self, monkeypatch):
        monkeypatch.delenv("QUIRK_CONFIG_PATH", raising=False)
        from quirk.siem.config import load_siem_config

        result = load_siem_config(path=None)
        assert result is None

    def test_nonexistent_path_returns_none(self, monkeypatch, tmp_path):
        monkeypatch.delenv("QUIRK_CONFIG_PATH", raising=False)
        from quirk.siem.config import load_siem_config

        result = load_siem_config(path=str(tmp_path / "missing.yaml"))
        assert result is None


# ---------------------------------------------------------------------------
# Tests — load_siem_config: valid YAML with [siem] block
# ---------------------------------------------------------------------------

class TestLoadSiemConfigValidYAML:
    """Valid YAML referenced by QUIRK_CONFIG_PATH or explicit path -> populated SiemCfg."""

    def test_loads_siem_block(self, monkeypatch, tmp_path):
        """Primary test: [siem] block loads into SiemCfg with all fields."""
        path = _write_siem_yaml(
            tmp_path,
            host="syslog.corp.example.com",
            port=601,
            protocol="tcp",
            export_after_scan=True,
            timeout_seconds=10,
        )
        monkeypatch.delenv("QUIRK_CONFIG_PATH", raising=False)
        from quirk.siem.config import load_siem_config, SiemCfg

        cfg = load_siem_config(path=path)
        assert cfg is not None
        assert isinstance(cfg, SiemCfg)
        assert cfg.host == "syslog.corp.example.com"
        assert cfg.port == 601
        assert cfg.protocol == "tcp"
        assert cfg.export_after_scan is True
        assert cfg.timeout_seconds == 10

    def test_env_var_path_loads_config(self, monkeypatch, tmp_path):
        path = _write_siem_yaml(tmp_path)
        monkeypatch.setenv("QUIRK_CONFIG_PATH", path)
        from quirk.siem.config import load_siem_config

        cfg = load_siem_config()
        assert cfg is not None

    def test_explicit_path_loads_config(self, monkeypatch, tmp_path):
        monkeypatch.delenv("QUIRK_CONFIG_PATH", raising=False)
        path = _write_siem_yaml(tmp_path)
        from quirk.siem.config import load_siem_config

        cfg = load_siem_config(path=path)
        assert cfg is not None

    def test_host_field_populated(self, monkeypatch, tmp_path):
        path = _write_siem_yaml(tmp_path, host="10.0.0.100")
        monkeypatch.delenv("QUIRK_CONFIG_PATH", raising=False)
        from quirk.siem.config import load_siem_config

        cfg = load_siem_config(path=path)
        assert cfg.host == "10.0.0.100"

    def test_default_port_514(self, monkeypatch, tmp_path):
        """port defaults to 514 when absent from YAML."""
        content = "siem:\n  host: syslog.example.com\n"
        p = tmp_path / "minimal.yaml"
        p.write_text(content)
        monkeypatch.delenv("QUIRK_CONFIG_PATH", raising=False)
        from quirk.siem.config import load_siem_config

        cfg = load_siem_config(path=str(p))
        assert cfg is not None
        assert cfg.port == 514

    def test_default_protocol_udp(self, monkeypatch, tmp_path):
        """protocol defaults to 'udp' when absent from YAML."""
        content = "siem:\n  host: syslog.example.com\n"
        p = tmp_path / "minimal.yaml"
        p.write_text(content)
        monkeypatch.delenv("QUIRK_CONFIG_PATH", raising=False)
        from quirk.siem.config import load_siem_config

        cfg = load_siem_config(path=str(p))
        assert cfg is not None
        assert cfg.protocol == "udp"

    def test_default_export_after_scan_false(self, monkeypatch, tmp_path):
        """export_after_scan defaults to False when absent from YAML."""
        content = "siem:\n  host: syslog.example.com\n"
        p = tmp_path / "minimal.yaml"
        p.write_text(content)
        monkeypatch.delenv("QUIRK_CONFIG_PATH", raising=False)
        from quirk.siem.config import load_siem_config

        cfg = load_siem_config(path=str(p))
        assert cfg is not None
        assert cfg.export_after_scan is False

    def test_default_timeout_seconds_5(self, monkeypatch, tmp_path):
        """timeout_seconds defaults to 5 when absent from YAML."""
        content = "siem:\n  host: syslog.example.com\n"
        p = tmp_path / "minimal.yaml"
        p.write_text(content)
        monkeypatch.delenv("QUIRK_CONFIG_PATH", raising=False)
        from quirk.siem.config import load_siem_config

        cfg = load_siem_config(path=str(p))
        assert cfg is not None
        assert cfg.timeout_seconds == 5

    def test_protocol_lowercased(self, monkeypatch, tmp_path):
        """protocol value is lowercased even if YAML has uppercase."""
        content = "siem:\n  host: syslog.example.com\n  protocol: UDP\n"
        p = tmp_path / "upper.yaml"
        p.write_text(content)
        monkeypatch.delenv("QUIRK_CONFIG_PATH", raising=False)
        from quirk.siem.config import load_siem_config

        cfg = load_siem_config(path=str(p))
        assert cfg is not None
        assert cfg.protocol == "udp"


# ---------------------------------------------------------------------------
# Tests — load_siem_config: missing [siem] block
# ---------------------------------------------------------------------------

class TestLoadSiemConfigNoBlock:
    """YAML with no [siem] key returns None."""

    def test_missing_siem_block_returns_none(self, monkeypatch, tmp_path):
        monkeypatch.delenv("QUIRK_CONFIG_PATH", raising=False)
        path = _write_no_siem_block(tmp_path)
        from quirk.siem.config import load_siem_config

        result = load_siem_config(path=path)
        assert result is None


# ---------------------------------------------------------------------------
# Tests — load_siem_config: Pitfall 2 DB-path trap
# ---------------------------------------------------------------------------

class TestLoadSiemConfigBinaryFile:
    """Pitfall 2: binary/SQLite DB path must return None, never raise."""

    def test_db_path_returns_none(self, monkeypatch, tmp_path):
        """Scheduler --config SQLite DB passed to load_siem_config -> None."""
        db_file = tmp_path / "quirk.db"
        db_file.write_bytes(b"SQLite format 3\x00" + b"\x00" * 100)
        monkeypatch.delenv("QUIRK_CONFIG_PATH", raising=False)
        from quirk.siem.config import load_siem_config

        result = load_siem_config(path=str(db_file))
        assert result is None

    def test_binary_file_returns_none(self, monkeypatch, tmp_path):
        monkeypatch.delenv("QUIRK_CONFIG_PATH", raising=False)
        path = _write_binary_db_file(tmp_path)
        from quirk.siem.config import load_siem_config

        result = load_siem_config(path=path)
        assert result is None

    def test_binary_env_path_returns_none(self, monkeypatch, tmp_path):
        path = _write_binary_db_file(tmp_path)
        monkeypatch.setenv("QUIRK_CONFIG_PATH", path)
        from quirk.siem.config import load_siem_config

        result = load_siem_config()
        assert result is None

    def test_load_never_raises_on_malformed(self, monkeypatch, tmp_path):
        """Malformed file must return None, not raise any exception."""
        p = tmp_path / "malformed.yaml"
        p.write_bytes(b"\xff\xfe\x00\x01garbage\x00\xff")
        monkeypatch.delenv("QUIRK_CONFIG_PATH", raising=False)
        from quirk.siem.config import load_siem_config

        # Must not raise
        result = load_siem_config(path=str(p))
        assert result is None
