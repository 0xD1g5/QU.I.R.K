"""Regression test: ``pip install quirk[all]`` MUST NOT pull schemathesis.

Phase 94 / PKG-01 rationale
----------------------------
``schemathesis`` is an active REST fuzzing tool that ships in the ``[api]``
extras group for Phase 96. The ``[api]`` extras group is intentionally OMITTED
from the ``[all]`` meta-extra for two reasons:

1. schemathesis activates fuzzing behavior that operators may not want to run
   against all targets by default; it must be explicitly opted in.
2. [api] is excluded from [all] now to prevent accidental schemathesis inclusion
   before Phase 96's usage documentation and controls are in place.

Additionally, ``openapi-spec-validator`` (the Phase 94 SPEC-01 dep) MUST NOT
appear in ``quirk[all]`` to maintain the [api] exclusion contract. If this
assertion fails, someone added ``quirk[api]`` to the ``[all]`` meta-extra —
revert that change.

This test resolves ``pip install -e <repo>[all]`` in dry-run mode, parses the
``--report`` JSON output that pip emits, and asserts that:
- ``schemathesis`` is absent from the resolved install set (PKG-01 primary guard)
- ``openapi-spec-validator`` is absent (proves [api] is NOT merged into [all])

Both assertions together prevent a vacuous pass if [api] was secretly folded in.

Mirrors ``tests/test_install_all_excludes_impacket.py`` exactly.
Marked ``@pytest.mark.slow`` because the resolver round-trip is several seconds;
default ``pytest`` runs skip it. CI runs ``pytest -m slow`` separately.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.slow
def test_install_all_excludes_schemathesis(tmp_path: Path) -> None:
    """Phase 94 / PKG-01 guard: ``quirk[all]`` must not transitively pull schemathesis.

    schemathesis ships in [api] extras only (deferred to Phase 96 per v5.1-D-05).
    quirk[api] is intentionally excluded from [all]. Regression: if this test fails,
    someone added quirk[api] to the [all] meta-extra in pyproject.toml. Revert
    that change. Phase 96 will add schemathesis with proper documentation and controls.
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
        "Phase 94 / PKG-01: the [all] meta-extra must resolve cleanly. "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )

    # pip emits a WARNING (not an error) when an extra is unknown, then resolves
    # only the base package. Detect that case explicitly so the test cannot pass
    # vacuously before the [all] extra is defined in pyproject.toml.
    combined_output = (result.stdout or "") + (result.stderr or "")
    assert "does not provide the extra 'all'" not in combined_output, (
        "pyproject.toml does not define the [all] meta-extra yet. "
        "Phase 94 / PKG-01: add the [all] meta-extra to [project.optional-dependencies]."
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
    # not see the [all] group at all (silent no-op) and the schemathesis assertion
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

    # Primary PKG-01 assertion: schemathesis must NOT be in [all]
    assert "schemathesis" not in installed, (
        "REGRESSION: schemathesis is present in the resolved set for quirk[all]. "
        "Phase 94 PKG-01: schemathesis is in [api] extras only — never in [all]. "
        "quirk[api] is intentionally excluded from [all] (Phase 96 will add schemathesis "
        "to [api] with proper controls). Remove quirk[api] from [all] in pyproject.toml. "
        f"Resolved packages: {sorted(installed)}"
    )

    # Sanity guard: openapi-spec-validator must NOT be in [all]
    # Proves that [api] was NOT silently merged into [all] (which would pull
    # openapi-spec-validator now and schemathesis when Phase 96 lands).
    assert "openapi-spec-validator" not in installed, (
        "REGRESSION: openapi-spec-validator is present in the resolved set for quirk[all]. "
        "Phase 94 PKG-01: openapi-spec-validator ships in [api] only. "
        "If this fails, quirk[api] was added to [all] — revert that change. "
        f"Resolved packages: {sorted(installed)}"
    )
