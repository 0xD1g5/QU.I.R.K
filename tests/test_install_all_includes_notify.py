"""Inclusion guard: ``pip install quirk[all]`` MUST pull slack-sdk.

Phase 101 / NOTIFY-03 rationale
---------------------------------
``slack-sdk`` is the Slack delivery backend for the notification fan-out
system. It is included in ``quirk[notify]`` which is in turn bundled into
``quirk[all]`` (mirroring the ``docx`` pattern). slack-sdk has no cryptography
downgrade chain (slopcheck [OK], >1M/week on PyPI, official Slack SDK).

This test resolves ``pip install -e <repo>[all]`` in dry-run mode, parses the
``--report`` JSON output, and asserts that ``slack-sdk`` IS present in the
resolved install set.

Marked ``@pytest.mark.slow`` because the resolver round-trip is several
seconds; default ``pytest`` runs skip it. CI runs ``pytest -m slow`` separately.

Conflict-check note (recorded per PLAN 101-01):
  pip dry-run of .[all,notify] EXIT 0, slack-sdk 3.42.0 resolved.
  slack-sdk aiohttp dep is under [optional] extra only — no required httpx/aiohttp conflict.
  Core httpx>=0.28.0 is unaffected. notify IS included in [all].
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.slow
def test_install_all_includes_notify(tmp_path: Path) -> None:
    """Phase 101 / NOTIFY-03 guard: ``quirk[all]`` must pull slack-sdk.

    If this test fails, someone removed ``quirk[notify]`` from the ``[all]``
    meta-extra in ``pyproject.toml``. Restore it. Operators need Slack
    notifications without extra install steps.
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
        "Phase 101 / NOTIFY-03: the [all] meta-extra must resolve cleanly. "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )

    combined_output = (result.stdout or "") + (result.stderr or "")
    assert "does not provide the extra 'all'" not in combined_output, (
        "pyproject.toml does not define the [all] meta-extra. "
        "Phase 101 / NOTIFY-03: [all] must include quirk-scanner[notify]."
    )
    assert "does not provide the extra 'notify'" not in combined_output, (
        "pyproject.toml does not define the [notify] extra. "
        "Phase 101 / NOTIFY-03: add notify = [\"slack-sdk>=3.33.0\"] to "
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

    # Sanity check: the [all] extra must actually expand to its component
    # extras. If none of these expected packages are present, the resolver did
    # not see the [all] group at all.
    expected_from_all = {
        "kubernetes",       # from [cloud]
        "psycopg2_binary",  # from [db]
        "redis",            # from [redis]/[broker]
        "fastapi",          # from [dashboard]
    }
    missing_expected = expected_from_all - installed
    assert not missing_expected, (
        "quirk[all] resolved but is missing expected component packages "
        f"{sorted(missing_expected)}. The [all] meta-extra in pyproject.toml "
        "must include cloud + db + redis + dashboard. "
        f"Resolved packages: {sorted(installed)}"
    )

    assert "slack_sdk" in installed, (
        "REGRESSION: slack-sdk is NOT present in the resolved set for quirk[all]. "
        "Phase 101 / NOTIFY-03: quirk[notify] must be included in the [all] "
        "meta-extra in pyproject.toml. "
        f"Resolved packages: {sorted(installed)}"
    )
