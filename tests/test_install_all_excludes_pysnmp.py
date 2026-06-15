"""Regression test: ``pip install quirk[all]`` MUST NOT pull pysnmp or sysdescrparser.

Phase 133 / D-08 rationale
--------------------------
``pysnmp`` is a large optional dependency. SNMP scanning requires explicit
operator opt-in via ``quirk[hw]``. Including it in ``[all]`` would force a
heavyweight SNMP stack on every operator regardless of whether they do
hardware fingerprinting.

``sysdescrparser`` is co-bundled with pysnmp under ``[hw]``; it must also
be excluded from ``[all]``.

This test resolves ``pip install -e <repo>[all]`` in dry-run mode, parses the
``--report`` JSON output that pip emits, and asserts that neither ``pysnmp``
nor ``sysdescrparser`` appears in the resolved install set.

Mirrors: ``tests/test_install_all_excludes_impacket.py`` (Phase 45 / D-01)

Marked ``@pytest.mark.slow`` because the resolver round-trip is several
seconds; default ``pytest`` runs skip it. CI runs ``pytest -m slow`` separately.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.slow
def test_install_all_excludes_pysnmp(tmp_path: Path) -> None:
    """Phase 133 / D-08 guard: ``quirk[all]`` must not transitively pull pysnmp.

    pysnmp is a large optional SNMP dependency; SNMP hardware fingerprinting
    requires explicit opt-in via ``quirk[hw]``. Operators who need SNMP must
    install ``quirk[hw]`` explicitly.

    Regression: if this test fails, someone added ``quirk[hw]`` to the
    ``[all]`` meta-extra in ``pyproject.toml``. Revert that change.
    """
    report_path = tmp_path / "report.json"
    cmd = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--dry-run",
        "--ignore-installed",
        "--quiet",
        "--report",
        str(report_path),
        "-e",
        f"{REPO_ROOT}[all]",
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=180,
    )

    assert result.returncode == 0, (
        "pip install --dry-run -e <repo>[all] FAILED. "
        "Phase 133 / D-08: the [all] meta-extra must resolve cleanly. "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )

    # pip emits a WARNING (not an error) when an extra is unknown, then resolves
    # only the base package. Detect that case explicitly so the test cannot pass
    # vacuously before the [all] extra is defined in pyproject.toml.
    combined_output = (result.stdout or "") + (result.stderr or "")
    assert "does not provide the extra 'all'" not in combined_output, (
        "pyproject.toml does not define the [all] meta-extra yet. "
        "Phase 133 / D-08: the [all] extra must be defined in pyproject.toml."
    )

    assert report_path.exists(), (
        "pip --report did not write a JSON file; check pip version "
        "(>= 22.2 required for --report)."
    )

    report = json.loads(report_path.read_text())
    installed = {
        item["metadata"]["name"].lower()
        for item in report.get("install", [])
        if item.get("metadata", {}).get("name")
    }

    # Sanity check: the [all] extra must actually expand to its component extras.
    # If none of these expected packages are present, the resolver did not see
    # the [all] group at all (silent no-op) and the pysnmp assertion below would
    # be vacuous.
    expected_from_all = {
        "kubernetes",       # from [cloud]
        "psycopg2-binary",  # from [db]
        "redis",            # from [redis]/[broker]
        "fastapi",          # from [dashboard]
    }
    missing_expected = expected_from_all - installed
    assert not missing_expected, (
        "quirk[all] resolved but is missing expected component packages "
        f"{sorted(missing_expected)}. The [all] meta-extra in pyproject.toml "
        "must include cloud + db + motion + redis + dashboard. "
        f"Resolved packages: {sorted(installed)}"
    )

    assert "pysnmp" not in installed, (
        "REGRESSION (D-08): pysnmp is present in the resolved set for quirk[all]. "
        "Phase 133 / D-08: pysnmp must only be available via the [hw] extras group. "
        "Remove quirk[hw] from the [all] meta-extra in pyproject.toml. "
        "Operators who need SNMP fingerprinting must install quirk[hw] explicitly. "
        f"Resolved packages: {sorted(installed)}"
    )

    assert "sysdescrparser" not in installed, (
        "REGRESSION (D-08): sysdescrparser is present in the resolved set for quirk[all]. "
        "Phase 133 / D-08: sysdescrparser is co-bundled in [hw] and must not appear in [all]. "
        f"Resolved packages: {sorted(installed)}"
    )
