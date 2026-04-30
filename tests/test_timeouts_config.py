"""Phase 41 D-06/D-07: TimeoutsCfg / RetryCfg loading + deprecation aliases.

Plan 02 lands the [scan.timeouts] / [scan.retry] sub-tables and the
deprecation-alias properties on ScanCfg. These tests verify both the
nested loader path and the legacy flat backward-compat path.
"""
from __future__ import annotations

import warnings

import pytest

from quirk.config import RetryCfg, ScanCfg, TimeoutsCfg, config_from_dict


def _base_raw(scan_block: dict) -> dict:
    return {
        "assessment": {
            "name": "test",
            "data_classification": "internal",
            "report_owner": "owner",
            "timezone": "UTC",
        },
        "scan": scan_block,
        "targets": {},
        "connectors": {},
        "output": {"directory": "/tmp", "db_path": "/tmp/q.db"},
    }


def test_timeouts_cfg_loaded_from_subtable() -> None:
    """[scan.timeouts] sub-table populates TimeoutsCfg fields; unspecified
    fields keep the documented defaults.
    """
    cfg = config_from_dict(
        _base_raw({"concurrency": 4, "ports_tls": [443], "timeouts": {"tls_seconds": 11, "ssh_seconds": 12}})
    )
    assert cfg.scan.timeouts.tls_seconds == 11
    assert cfg.scan.timeouts.ssh_seconds == 12
    assert cfg.scan.timeouts.default_seconds == 5  # default


def test_retry_cfg_loaded_from_subtable() -> None:
    """[scan.retry] sub-table populates RetryCfg; unspecified fields keep defaults."""
    cfg = config_from_dict(
        _base_raw({"concurrency": 4, "ports_tls": [443], "retry": {"retry_count": 3, "backoff_base_seconds": 2.0}})
    )
    assert cfg.scan.retry.retry_count == 3
    assert cfg.scan.retry.backoff_base_seconds == 2.0
    assert cfg.scan.retry.backoff_max_seconds == 5.0  # default


def test_deprecated_timeout_seconds_alias_warns() -> None:
    """D-07: cfg.scan.timeout_seconds emits DeprecationWarning and returns
    timeouts.default_seconds.
    """
    cfg = config_from_dict(
        _base_raw({"concurrency": 4, "ports_tls": [443], "timeouts": {"default_seconds": 9}})
    )
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        v = cfg.scan.timeout_seconds
        assert v == 9
        assert any(issubclass(x.category, DeprecationWarning) for x in w)


def test_deprecated_per_phase_timeout_aliases_warn() -> None:
    """D-07: tls_timeout_seconds, ssh_timeout_seconds, fingerprint_timeout_seconds
    all warn-on-read and redirect to the corresponding TimeoutsCfg field.
    """
    cfg = config_from_dict(
        _base_raw(
            {
                "concurrency": 4,
                "ports_tls": [443],
                "timeouts": {"tls_seconds": 6, "ssh_seconds": 7, "fingerprint_seconds": 3},
            }
        )
    )
    for attr, expected in [
        ("tls_timeout_seconds", 6),
        ("ssh_timeout_seconds", 7),
        ("fingerprint_timeout_seconds", 3),
    ]:
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            v = getattr(cfg.scan, attr)
            assert v == expected
            assert any(
                issubclass(x.category, DeprecationWarning) for x in w
            ), f"{attr} did not warn"


def test_legacy_flat_config_backward_compat() -> None:
    """Legacy flat [scan] config (no [scan.timeouts] sub-table) still loads:
    flat *_timeout_seconds keys are routed into TimeoutsCfg.
    """
    cfg = config_from_dict(
        _base_raw(
            {
                "concurrency": 4,
                "ports_tls": [443],
                "timeout_seconds": 7,
                "tls_timeout_seconds": 8,
            }
        )
    )
    assert cfg.scan.timeouts.default_seconds == 7
    assert cfg.scan.timeouts.tls_seconds == 8
    # Untouched fields keep their defaults
    assert cfg.scan.timeouts.ssh_seconds == 6
