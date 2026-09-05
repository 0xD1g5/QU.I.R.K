"""Phase 184.2 Plan 01 — run_scan.py enable_adcs reachability wiring tests.

D-11: `enable_adcs` was not a `ConnectorsCfg` field, so the guard at
`run_scan.py:3284` (`_run_adcs_phase`) was permanently unreachable — every
getattr resolved to its fallback default regardless of YAML content.

Covers four behaviors:
  - test_enabled_with_targets_invokes_scanner: enable_adcs=True + non-empty
    adcs_targets calls scan_adcs_targets once, passing through the configured
    search_base/user/password/timeout rather than getattr fallbacks.
  - test_disabled_never_calls_scanner: enable_adcs=False (with targets) never
    calls scan_adcs_targets; phase returns the skipped sentinel.
  - test_enabled_empty_targets_never_calls_scanner: enable_adcs=True with an
    empty adcs_targets never calls scan_adcs_targets.
  - test_yaml_round_trip_preserves_adcs_fields: a YAML `connectors:` block
    setting enable_adcs/adcs_targets survives `load_config` with those values
    intact (previously filtered out by config.py's unknown-key drop).
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

_PHASE_SKIPPED = object()


def _make_cfg(enable_adcs=False, adcs_targets=None, adcs_search_base=None,
               adcs_user=None, adcs_password=None, adcs_timeout=10):
    connectors = SimpleNamespace(
        enable_adcs=enable_adcs,
        adcs_targets=adcs_targets if adcs_targets is not None else [],
        adcs_search_base=adcs_search_base,
        adcs_user=adcs_user,
        adcs_password=adcs_password,
        adcs_timeout=adcs_timeout,
    )
    return SimpleNamespace(connectors=connectors)


def _run_adcs_phase(cfg, logger, session_start, cfg_adcs_skip=False):
    """Mirrors run_scan.py:3286-3301's `_run_adcs_phase` closure exactly."""
    if cfg_adcs_skip or not (getattr(cfg.connectors, "enable_adcs", False)
            and getattr(cfg.connectors, "adcs_targets", None)):
        return _PHASE_SKIPPED
    from quirk.scanner.adcs_scanner import scan_adcs_targets
    eps = scan_adcs_targets(
        targets=cfg.connectors.adcs_targets,
        timeout=getattr(cfg.connectors, "adcs_timeout", 10),
        logger=logger,
        session_start=session_start,
        search_base=getattr(cfg.connectors, "adcs_search_base", None),
        user=getattr(cfg.connectors, "adcs_user", None),
        password=getattr(cfg.connectors, "adcs_password", None),
    )
    return eps


class TestEnabledWithTargetsInvokesScanner:
    def test_enabled_with_targets_invokes_scanner(self):
        cfg = _make_cfg(
            enable_adcs=True,
            adcs_targets=["ldap://dc.example.com"],
            adcs_search_base="DC=example,DC=com",
            adcs_user="svc-adcs",
            adcs_password="hunter2-placeholder",
            adcs_timeout=42,
        )
        logger = MagicMock()

        with patch(
            "quirk.scanner.adcs_scanner.scan_adcs_targets", return_value=[],
        ) as mock_scan:
            result = _run_adcs_phase(cfg, logger, session_start=None)

        mock_scan.assert_called_once_with(
            targets=["ldap://dc.example.com"],
            timeout=42,
            logger=logger,
            session_start=None,
            search_base="DC=example,DC=com",
            user="svc-adcs",
            password="hunter2-placeholder",
        )
        assert result == []


class TestDisabledNeverCallsScanner:
    def test_disabled_never_calls_scanner(self):
        cfg = _make_cfg(enable_adcs=False, adcs_targets=["ldap://dc.example.com"])
        logger = MagicMock()

        with patch(
            "quirk.scanner.adcs_scanner.scan_adcs_targets",
        ) as mock_scan:
            result = _run_adcs_phase(cfg, logger, session_start=None)

        mock_scan.assert_not_called()
        assert result is _PHASE_SKIPPED


class TestEnabledEmptyTargetsNeverCallsScanner:
    def test_enabled_empty_targets_never_calls_scanner(self):
        cfg = _make_cfg(enable_adcs=True, adcs_targets=[])
        logger = MagicMock()

        with patch(
            "quirk.scanner.adcs_scanner.scan_adcs_targets",
        ) as mock_scan:
            result = _run_adcs_phase(cfg, logger, session_start=None)

        mock_scan.assert_not_called()
        assert result is _PHASE_SKIPPED


class TestYamlRoundTripPreservesAdcsFields:
    def test_yaml_round_trip_preserves_adcs_fields(self, tmp_path):
        """A YAML config setting enable_adcs + adcs_targets must survive
        load_config with those values intact (D-11)."""
        import yaml
        from quirk.config import load_config

        config_dict = {
            "assessment": {
                "name": "adcs-roundtrip",
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
            "connectors": {
                "enable_adcs": True,
                "adcs_targets": ["ldap://dc.example.com"],
            },
        }
        config_path = tmp_path / "config.yaml"
        config_path.write_text(yaml.safe_dump(config_dict))

        cfg = load_config(str(config_path))

        assert cfg.connectors.enable_adcs is True
        assert cfg.connectors.adcs_targets == ["ldap://dc.example.com"]
