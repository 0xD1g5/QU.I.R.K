"""Phase 184.2 Plan 01 — unknown connector key warning (D-14).

Confirmed live during discussion: loading a config containing
`enable_totally_bogus_key: true` succeeds silently and the key vanishes,
leaving a consultant with a silently narrower scan and no signal. This test
file locks in the fix: a non-fatal WARNING naming the dropped key, with the
key's value never echoed (T-184.2-03).

Covers five behaviors:
  - test_unknown_key_emits_one_named_warning: succeeds, raises nothing, emits
    exactly one WARNING naming the key.
  - test_two_unknown_keys_emit_two_warnings_sorted: two unknown keys produce
    two warning records in sorted order.
  - test_no_unknown_keys_emits_zero_warnings: an all-known connectors block
    emits zero warnings from this code path.
  - test_unknown_key_value_never_logged: an unknown key's secret-shaped value
    never appears in the warning message or caplog.text.
  - test_unknown_key_still_dropped: the unknown key is still absent from the
    resulting ConnectorsCfg — filter behaviour unchanged.
"""
from __future__ import annotations

import logging

import pytest
import yaml

from quirk.config import load_config


def _write_config(tmp_path, connectors_block):
    config_dict = {
        "assessment": {
            "name": "unknown-key-warning-test",
            "data_classification": "internal",
            "report_owner": "tester",
            "timezone": "UTC",
        },
        "scan": {
            "concurrency": 50,
            "ports_tls": [443],
        },
        "output": {
            "directory": str(tmp_path / "out"),
            "db_path": str(tmp_path / "out" / "quirk.db"),
        },
        "connectors": connectors_block,
    }
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(config_dict))
    return str(config_path)


class TestUnknownKeyEmitsOneNamedWarning:
    def test_unknown_key_emits_one_named_warning(self, tmp_path, caplog):
        config_path = _write_config(
            tmp_path, {"enable_totally_bogus_key": True},
        )
        with caplog.at_level(logging.WARNING, logger="quirk.config"):
            cfg = load_config(config_path)

        assert cfg is not None  # succeeds, raises nothing
        warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert len(warnings) == 1
        assert "enable_totally_bogus_key" in warnings[0].getMessage()


class TestTwoUnknownKeysEmitTwoWarningsSorted:
    def test_two_unknown_keys_emit_two_warnings_sorted(self, tmp_path, caplog):
        config_path = _write_config(
            tmp_path,
            {"enable_z_bogus": True, "enable_a_bogus": True},
        )
        with caplog.at_level(logging.WARNING, logger="quirk.config"):
            load_config(config_path)

        warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert len(warnings) == 2
        assert "enable_a_bogus" in warnings[0].getMessage()
        assert "enable_z_bogus" in warnings[1].getMessage()


class TestNoUnknownKeysEmitsZeroWarnings:
    def test_no_unknown_keys_emits_zero_warnings(self, tmp_path, caplog):
        config_path = _write_config(
            tmp_path, {"enable_jwt": True, "jwt_targets": ["https://example.com"]},
        )
        with caplog.at_level(logging.WARNING, logger="quirk.config"):
            load_config(config_path)

        warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert warnings == []


class TestUnknownKeyValueNeverLogged:
    def test_unknown_key_value_never_logged(self, tmp_path, caplog):
        config_path = _write_config(
            tmp_path, {"enable_windows_adcs": "s3cr3t-do-not-log"},
        )
        with caplog.at_level(logging.WARNING, logger="quirk.config"):
            load_config(config_path)

        warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert len(warnings) == 1
        assert "enable_windows_adcs" in warnings[0].getMessage()
        assert "s3cr3t-do-not-log" not in warnings[0].getMessage()
        assert "s3cr3t-do-not-log" not in caplog.text


class TestUnknownKeyStillDropped:
    def test_unknown_key_still_dropped(self, tmp_path, caplog):
        config_path = _write_config(
            tmp_path, {"enable_totally_bogus_key": True},
        )
        with caplog.at_level(logging.WARNING, logger="quirk.config"):
            cfg = load_config(config_path)

        assert not hasattr(cfg.connectors, "enable_totally_bogus_key")
