"""Regression lock for INFRA-01 — every version-bearing surface returns 4.4.0."""
import subprocess
import sys

import pytest


def test_package_version_is_4_4_0():
    import quirk
    assert quirk.__version__ == "4.4.0"


def test_cbom_platform_version_is_4_4_0():
    from quirk.cbom.builder import PLATFORM_VERSION
    assert PLATFORM_VERSION == "4.4.0"


def test_reports_platform_version_is_4_4_0():
    from quirk.reports.writer import PLATFORM_VERSION
    assert PLATFORM_VERSION == "4.4.0"


def test_cli_version_subprocess():
    try:
        result = subprocess.run(
            [sys.executable, "-m", "run_scan", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except Exception as exc:
        pytest.fail(f"CLI --version not invokable: {exc}")
    if result.returncode != 0:
        pytest.fail("CLI --version returned non-zero")
    output = (result.stdout or "") + (result.stderr or "")
    assert "4.4.0" in output


def test_intelligence_config_default_is_4_4_0():
    from quirk.config import IntelligenceCfg
    assert IntelligenceCfg().intelligence_version == "4.4.0"
