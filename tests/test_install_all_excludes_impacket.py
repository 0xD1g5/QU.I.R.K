"""Regression test: ``pip install quirk[all]`` MUST NOT pull impacket.

Phase 45 / D-01 rationale
-------------------------
``impacket`` transitively depends on ``pyOpenSSL``, which in turn pins
``cryptography`` to a version range that downgrades the cryptography library
shipped in QUIRK's base dependencies. That downgrade silently breaks the TLS
scanner (cipher-suite enumeration loses TLS 1.3 / X25519 support).

To prevent accidental drift, the ``[all]`` meta-extra in ``pyproject.toml``
intentionally OMITS ``quirk[identity]`` (which contains impacket). Operators
who need Kerberos / impacket-backed scanners must install ``quirk[identity]``
in a separate virtual environment.

This test resolves ``pip install -e <repo>[all]`` in dry-run mode, parses the
``--report`` JSON output that pip emits, and asserts that no package named
``impacket`` (case-insensitive) appears in the resolved install set.

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
def test_install_all_excludes_impacket(tmp_path: Path) -> None:
    """Phase 45 / D-01 guard: ``quirk[all]`` must not transitively pull impacket.

    impacket -> pyOpenSSL -> downgrades cryptography -> breaks TLS scanner.
    Regression: if this test fails, someone added ``quirk[identity]`` to the
    ``[all]`` meta-extra in ``pyproject.toml``. Revert that change. Consultants
    who need Kerberos must install ``quirk[identity]`` in a separate venv.
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
        "Phase 45 / D-01: the [all] meta-extra must resolve cleanly. "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )

    # pip emits a WARNING (not an error) when an extra is unknown, then resolves
    # only the base package. Detect that case explicitly so the test cannot pass
    # vacuously before the [all] extra is defined in pyproject.toml.
    combined_output = (result.stdout or "") + (result.stderr or "")
    assert "does not provide the extra 'all'" not in combined_output, (
        "pyproject.toml does not define the [all] meta-extra yet. "
        "Phase 45 / D-01: add `all = [\"quirk[cloud]\", \"quirk[db]\", "
        "\"quirk[motion]\", \"quirk[redis]\", \"quirk[dashboard]\"]` to "
        "[project.optional-dependencies]."
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

    # Sanity check: the [all] extra must actually expand to its component
    # extras. If none of these expected packages are present, the resolver did
    # not see the [all] group at all (silent no-op) and the impacket assertion
    # below would be vacuous.
    expected_from_all = {
        "kubernetes",      # from [cloud]
        "psycopg2-binary", # from [db]
        "redis",           # from [redis]/[broker]
        "fastapi",         # from [dashboard]
    }
    missing_expected = expected_from_all - installed
    assert not missing_expected, (
        "quirk[all] resolved but is missing expected component packages "
        f"{sorted(missing_expected)}. The [all] meta-extra in pyproject.toml "
        "must include cloud + db + motion + redis + dashboard. "
        f"Resolved packages: {sorted(installed)}"
    )

    assert "impacket" not in installed, (
        "REGRESSION: impacket is present in the resolved set for quirk[all]. "
        "Phase 45 / D-01: impacket transitively pulls pyOpenSSL which "
        "downgrades the cryptography library and breaks the TLS scanner. "
        "Remove quirk[identity] from the [all] meta-extra in pyproject.toml. "
        f"Resolved packages: {sorted(installed)}"
    )
