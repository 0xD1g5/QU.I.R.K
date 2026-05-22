"""Version single-source-of-truth parity test (D-84-R1 / v4.10 D-02).

Direction: ``pyproject.toml [project.version]`` is the canonical source. Every
other version-bearing surface in the codebase must derive from it and match
exactly. No assertion in this file hardcodes a version string — the truth is
read dynamically via ``tomllib`` so version bumps need only touch
``pyproject.toml``.

Originally Phase 37 INFRA-01 (which pinned all surfaces to a 4.4.0 literal in
the opposite direction); flipped in Phase 84-01 to honor modern PEP 621 +
importlib.metadata packaging practice.
"""
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

_PYPROJECT = Path(__file__).resolve().parent.parent / "pyproject.toml"
_PROJECT = tomllib.loads(_PYPROJECT.read_text(encoding="utf-8"))["project"]
TRUTH = _PROJECT["version"]
DIST_NAME = _PROJECT["name"]


def test_pyproject_version_is_well_formed():
    # Guard against a malformed bump (e.g. empty, whitespace) — the SoT itself
    # must be sane before downstream comparisons are meaningful.
    assert isinstance(TRUTH, str) and TRUTH.strip() == TRUTH and TRUTH


def test_package_version_matches_pyproject():
    import quirk
    assert quirk.__version__ == TRUTH


def test_cbom_platform_version_matches_pyproject():
    from quirk.cbom.builder import PLATFORM_VERSION
    assert PLATFORM_VERSION == TRUTH


def test_reports_platform_version_matches_pyproject():
    from quirk.reports.writer import PLATFORM_VERSION
    assert PLATFORM_VERSION == TRUTH


def test_intelligence_config_default_matches_pyproject():
    from quirk.config import IntelligenceCfg
    assert IntelligenceCfg().intelligence_version == TRUTH


def test_distribution_name_is_canonical():
    # v4.10 D-01: the `quirk` PyPI name was claimed by an unrelated 0.1.x
    # project, so the canonical distribution name is `quirk-scanner`.
    assert DIST_NAME == "quirk-scanner"


@pytest.mark.slow
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
    assert TRUTH in output
