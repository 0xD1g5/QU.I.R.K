"""Inclusion guard: ``pip install quirk[all]`` MUST pull jira.

Phase 104 / TICKET-01 rationale
---------------------------------
``jira>=3.10.5`` is the Jira delivery backend. It is included in ``quirk[tickets]``
which is in turn bundled into ``quirk[all]``. jira has no cryptography downgrade
chain (slopcheck [OK], official pycontribs/jira, PyPI-verified 3.10.5).

This test resolves ``pip install -e <repo>[all]`` in dry-run mode, parses the
``--report`` JSON output, and asserts that ``jira`` IS present in the
resolved install set.

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
def test_install_all_includes_tickets(tmp_path: Path) -> None:
    """Phase 104 / TICKET-01 guard: ``quirk[all]`` must pull jira.

    If this test fails, someone removed ``quirk[tickets]`` from the ``[all]``
    meta-extra in ``pyproject.toml``. Restore it. Operators need Jira
    ticketing without extra install steps.
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
        "Phase 104 / TICKET-01: the [all] meta-extra must resolve cleanly. "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )

    combined_output = (result.stdout or "") + (result.stderr or "")
    assert "does not provide the extra 'all'" not in combined_output, (
        "pyproject.toml does not define the [all] meta-extra. "
        "Phase 104 / TICKET-01: [all] must include quirk-scanner[tickets]."
    )
    assert "does not provide the extra 'tickets'" not in combined_output, (
        "pyproject.toml does not define the [tickets] extra. "
        "Phase 104 / TICKET-01: add tickets = [\"jira>=3.10.5\"] to "
        "[project.optional-dependencies]."
    )

    assert report_path.exists(), (
        "pip --report did not write a JSON file; check pip version "
        "(>= 22.2 required for --report)."
    )

    report = json.loads(report_path.read_text())
    installed = {
        item["metadata"]["name"].lower().replace("-", "_")
        for item in report.get("install", [])
        if item.get("metadata", {}).get("name")
    }

    assert "jira" in installed, (
        "REGRESSION: jira is NOT present in the resolved set for quirk[all]. "
        "Phase 104 / TICKET-01: quirk[tickets] must be included in the [all] "
        "meta-extra in pyproject.toml. "
        f"Resolved packages: {sorted(installed)}"
    )
