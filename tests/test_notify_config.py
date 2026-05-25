"""Tests for quirk/notify/config.py — NOTIFY-06.

Covers:
- Unset QUIRK_CONFIG_PATH + no path → None (disabled)
- Valid YAML with [notifications] block → populated NotifyCfg
- Binary / SQLite file path → None (Pitfall 1 guard)
- Default trigger_score_floor when absent
- Env-var NAME fields (not literal secrets) in returned cfg
"""
from __future__ import annotations

import os
import textwrap

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_valid_yaml(tmp_path, extra: str = "") -> str:
    """Write a minimal valid QUIRK YAML config with a [notifications] block."""
    content = textwrap.dedent(f"""\
        notifications:
          trigger_score_floor: -10
          slack:
            slack_webhook_env: MY_SLACK_URL
            dashboard_base_url: https://dashboard.example.com
          email:
            smtp_host: smtp.example.com
            smtp_port: 587
            smtp_from: quirk@example.com
            recipients:
              - alice@example.com
              - bob@example.com
            smtp_password_env: SMTP_PASS
            use_ssl: false
          webhook:
            url_env: WEBHOOK_URL
            hmac_key_env: WEBHOOK_HMAC
            timeout_seconds: 15
        {extra}
    """)
    p = tmp_path / "config.yaml"
    p.write_text(content)
    return str(p)


def _write_notifications_only(tmp_path) -> str:
    """Minimal YAML with just trigger_score_floor, no sub-channels."""
    content = textwrap.dedent("""\
        notifications:
          trigger_score_floor: -3
    """)
    p = tmp_path / "minimal.yaml"
    p.write_text(content)
    return str(p)


def _write_no_notifications_block(tmp_path) -> str:
    """Valid YAML but NO [notifications] key."""
    content = textwrap.dedent("""\
        assessment:
          name: test
          data_classification: internal
          report_owner: test
          timezone: UTC
    """)
    p = tmp_path / "no_notify.yaml"
    p.write_text(content)
    return str(p)


def _write_binary_file(tmp_path) -> str:
    """Write a binary (SQLite-header-like) file."""
    p = tmp_path / "quirk.db"
    # SQLite magic header bytes
    p.write_bytes(b"SQLite format 3\x00" + b"\x00" * 100)
    return str(p)


# ---------------------------------------------------------------------------
# Tests — load_notifications_config
# ---------------------------------------------------------------------------

class TestLoadNotificationsConfigNoPath:
    """QUIRK_CONFIG_PATH unset + no explicit path → None."""

    def test_no_env_no_path_returns_none(self, monkeypatch):
        monkeypatch.delenv("QUIRK_CONFIG_PATH", raising=False)
        from quirk.notify.config import load_notifications_config

        result = load_notifications_config()
        assert result is None

    def test_explicit_none_path_returns_none(self, monkeypatch):
        monkeypatch.delenv("QUIRK_CONFIG_PATH", raising=False)
        from quirk.notify.config import load_notifications_config

        result = load_notifications_config(path=None)
        assert result is None

    def test_nonexistent_path_returns_none(self, monkeypatch, tmp_path):
        monkeypatch.delenv("QUIRK_CONFIG_PATH", raising=False)
        from quirk.notify.config import load_notifications_config

        result = load_notifications_config(path=str(tmp_path / "missing.yaml"))
        assert result is None


class TestLoadNotificationsConfigValidYAML:
    """Valid YAML referenced by QUIRK_CONFIG_PATH → populated NotifyCfg."""

    def test_env_var_path_loads_config(self, monkeypatch, tmp_path):
        path = _write_valid_yaml(tmp_path)
        monkeypatch.setenv("QUIRK_CONFIG_PATH", path)
        from quirk.notify.config import load_notifications_config

        cfg = load_notifications_config()
        assert cfg is not None

    def test_explicit_path_loads_config(self, monkeypatch, tmp_path):
        monkeypatch.delenv("QUIRK_CONFIG_PATH", raising=False)
        path = _write_valid_yaml(tmp_path)
        from quirk.notify.config import load_notifications_config

        cfg = load_notifications_config(path=path)
        assert cfg is not None

    def test_trigger_score_floor_populated(self, monkeypatch, tmp_path):
        path = _write_valid_yaml(tmp_path)
        monkeypatch.delenv("QUIRK_CONFIG_PATH", raising=False)
        from quirk.notify.config import load_notifications_config

        cfg = load_notifications_config(path=path)
        assert cfg.trigger_score_floor == -10

    def test_slack_env_var_name_not_literal(self, monkeypatch, tmp_path):
        """NOTIFY-06: slack config stores env-var NAME, not the secret itself."""
        path = _write_valid_yaml(tmp_path)
        monkeypatch.delenv("QUIRK_CONFIG_PATH", raising=False)
        from quirk.notify.config import load_notifications_config

        cfg = load_notifications_config(path=path)
        assert cfg.slack is not None
        assert cfg.slack.slack_webhook_env == "MY_SLACK_URL"

    def test_email_config_populated(self, monkeypatch, tmp_path):
        path = _write_valid_yaml(tmp_path)
        monkeypatch.delenv("QUIRK_CONFIG_PATH", raising=False)
        from quirk.notify.config import load_notifications_config

        cfg = load_notifications_config(path=path)
        assert cfg.email is not None
        assert cfg.email.smtp_host == "smtp.example.com"
        assert cfg.email.smtp_port == 587
        assert cfg.email.smtp_from == "quirk@example.com"
        assert "alice@example.com" in cfg.email.recipients
        # smtp_password_env stores the ENV VAR NAME, not a password literal
        assert cfg.email.smtp_password_env == "SMTP_PASS"

    def test_webhook_config_populated(self, monkeypatch, tmp_path):
        path = _write_valid_yaml(tmp_path)
        monkeypatch.delenv("QUIRK_CONFIG_PATH", raising=False)
        from quirk.notify.config import load_notifications_config

        cfg = load_notifications_config(path=path)
        assert cfg.webhook is not None
        assert cfg.webhook.url_env == "WEBHOOK_URL"
        assert cfg.webhook.hmac_key_env == "WEBHOOK_HMAC"
        assert cfg.webhook.timeout_seconds == 15

    def test_absent_channels_are_none(self, monkeypatch, tmp_path):
        """Channels absent from YAML are None, not error."""
        path = _write_notifications_only(tmp_path)
        monkeypatch.delenv("QUIRK_CONFIG_PATH", raising=False)
        from quirk.notify.config import load_notifications_config

        cfg = load_notifications_config(path=path)
        assert cfg is not None
        assert cfg.slack is None
        assert cfg.email is None
        assert cfg.webhook is None


class TestLoadNotificationsConfigDefaultFloor:
    """trigger_score_floor defaults to -5 when absent."""

    def test_default_floor(self, monkeypatch, tmp_path):
        monkeypatch.delenv("QUIRK_CONFIG_PATH", raising=False)
        # Write YAML with no trigger_score_floor key
        content = "notifications:\n  slack:\n    slack_webhook_env: FOO\n"
        path = tmp_path / "cfg.yaml"
        path.write_text(content)
        from quirk.notify.config import load_notifications_config

        cfg = load_notifications_config(path=str(path))
        assert cfg is not None
        assert cfg.trigger_score_floor == -5


class TestLoadNotificationsConfigNoBlock:
    """YAML with no [notifications] key returns None."""

    def test_no_notifications_block_returns_none(self, monkeypatch, tmp_path):
        monkeypatch.delenv("QUIRK_CONFIG_PATH", raising=False)
        path = _write_no_notifications_block(tmp_path)
        from quirk.notify.config import load_notifications_config

        result = load_notifications_config(path=path)
        assert result is None


class TestLoadNotificationsConfigBinaryFile:
    """Pitfall 1: binary / SQLite DB path must return None, not raise."""

    def test_binary_file_returns_none(self, monkeypatch, tmp_path):
        monkeypatch.delenv("QUIRK_CONFIG_PATH", raising=False)
        path = _write_binary_file(tmp_path)
        from quirk.notify.config import load_notifications_config

        # Must not raise — scheduler passes --config (DB path) in some flows
        result = load_notifications_config(path=path)
        assert result is None

    def test_binary_env_path_returns_none(self, monkeypatch, tmp_path):
        path = _write_binary_file(tmp_path)
        monkeypatch.setenv("QUIRK_CONFIG_PATH", path)
        from quirk.notify.config import load_notifications_config

        result = load_notifications_config()
        assert result is None


class TestNotifyCfgNoLiteralSecrets:
    """NOTIFY-06: The returned dataclass must only contain env-var NAMES."""

    def test_no_secret_literal_in_email_cfg(self, monkeypatch, tmp_path):
        """smtp_password_env must be a name ('SMTP_PASS'), not the secret value."""
        # Even if SMTP_PASS is set in the env, the config must NOT expand it
        monkeypatch.setenv("SMTP_PASS", "super-secret-password-literal")
        path = _write_valid_yaml(tmp_path)
        monkeypatch.delenv("QUIRK_CONFIG_PATH", raising=False)
        from quirk.notify.config import load_notifications_config

        cfg = load_notifications_config(path=path)
        assert cfg is not None
        assert cfg.email is not None
        # The field must be the env-var NAME, not the expanded value
        assert cfg.email.smtp_password_env == "SMTP_PASS"
        assert cfg.email.smtp_password_env != "super-secret-password-literal"
