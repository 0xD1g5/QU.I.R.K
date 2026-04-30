"""Phase 41 D-06/D-07: TimeoutsCfg / RetryCfg loading + deprecation aliases.

Stubs created in Wave 0; turned green by Plan 02 which lands the
``[scan.timeouts]`` and ``[scan.retry]`` TOML sub-tables and the
deprecation-alias properties on ``ScanCfg``.
"""
from __future__ import annotations

import pytest


@pytest.mark.xfail(reason="Plan 02 lands TimeoutsCfg dataclass", strict=False)
def test_timeouts_cfg_loaded_from_subtable() -> None:
    """[scan.timeouts] sub-table populates TimeoutsCfg defaults."""
    raise NotImplementedError("Plan 02")


@pytest.mark.xfail(reason="Plan 02 lands RetryCfg dataclass", strict=False)
def test_retry_cfg_loaded_from_subtable() -> None:
    """[scan.retry] sub-table populates RetryCfg."""
    raise NotImplementedError("Plan 02")


@pytest.mark.xfail(reason="Plan 02 wires deprecation aliases", strict=False)
def test_deprecated_timeout_seconds_alias_warns() -> None:
    """D-07: cfg.scan.timeout_seconds emits DeprecationWarning and returns
    timeouts.default_seconds.
    """
    raise NotImplementedError("Plan 02")


@pytest.mark.xfail(reason="Plan 02 wires deprecation aliases", strict=False)
def test_deprecated_per_phase_timeout_aliases_warn() -> None:
    """D-07: tls_timeout_seconds, ssh_timeout_seconds, fingerprint_timeout_seconds
    all warn-on-read.
    """
    raise NotImplementedError("Plan 02")
