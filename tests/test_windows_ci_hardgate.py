"""Phase 108 SENSOR-06: Static guard — windows-latest CI job must stay a hard gate.

Loads .github/workflows/python-ci.yml and asserts:
  1. The windows-sensor-smoke job exists and runs on windows-latest.
  2. The job does NOT set continue-on-error: true at the job level.
  3. No step in the job sets continue-on-error: true.

This test runs locally on every pytest invocation, preventing a reviewer from
silently softening the hard gate by adding continue-on-error.
"""
from __future__ import annotations

import pathlib

import yaml

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
CI_FILE = REPO_ROOT / ".github" / "workflows" / "python-ci.yml"

JOB_NAME = "windows-sensor-smoke"


def _load_ci() -> dict:
    return yaml.safe_load(CI_FILE.read_text(encoding="utf-8"))


def test_ci_file_exists():
    """The CI workflow file must exist."""
    assert CI_FILE.exists(), (
        f"{CI_FILE} does not exist — windows-latest hard gate is missing (SENSOR-06)"
    )


def test_windows_sensor_smoke_job_present():
    """The windows-sensor-smoke job must be defined in the CI file."""
    ci = _load_ci()
    jobs = ci.get("jobs", {})
    assert JOB_NAME in jobs, (
        f"Job '{JOB_NAME}' not found in {CI_FILE.name}; "
        f"defined jobs: {list(jobs.keys())}  (SENSOR-06)"
    )


def test_windows_sensor_smoke_runs_on_windows_latest():
    """The windows-sensor-smoke job must run on windows-latest."""
    ci = _load_ci()
    job = ci["jobs"][JOB_NAME]
    runs_on = job.get("runs-on")
    assert runs_on == "windows-latest", (
        f"Job '{JOB_NAME}' runs-on is {runs_on!r}, expected 'windows-latest' (SENSOR-06)"
    )


def test_job_has_no_continue_on_error():
    """The windows-sensor-smoke job must NOT set continue-on-error: true at the job level."""
    ci = _load_ci()
    job = ci["jobs"][JOB_NAME]
    coe = job.get("continue-on-error")
    assert coe is not True, (
        f"Job '{JOB_NAME}' has continue-on-error: {coe!r} — this disables the hard gate. "
        "Remove continue-on-error from the job to restore SENSOR-06 enforcement."
    )


def test_no_step_has_continue_on_error():
    """No step in the windows-sensor-smoke job may set continue-on-error: true."""
    ci = _load_ci()
    job = ci["jobs"][JOB_NAME]
    steps = job.get("steps", [])
    violations = [
        (i, step.get("name", f"step[{i}]"))
        for i, step in enumerate(steps)
        if step.get("continue-on-error") is True
    ]
    assert not violations, (
        f"Steps with continue-on-error in job '{JOB_NAME}': {violations}  "
        "Removing continue-on-error from steps is required to keep the hard gate active."
    )


def test_smoke_test_file_is_run():
    """The CI job must invoke the smoke test file by name."""
    ci_text = CI_FILE.read_text(encoding="utf-8")
    assert "test_sensor_windows_smoke" in ci_text, (
        f"'test_sensor_windows_smoke' not found in {CI_FILE.name} — "
        "the CI job must execute the smoke test file (SENSOR-06)"
    )


def test_no_continue_on_error_literal_in_smoke_job():
    """The windows-sensor-smoke job's text block must not contain 'continue-on-error: true'.

    Scoped to the smoke job only (not the whole file): other jobs — e.g. the
    Phase 116 `windows-packaging-spike` job — are legitimately non-blocking and
    set `continue-on-error: true` by design. SENSOR-06 only requires that the
    *smoke* hard gate is never softened. This is a defense-in-depth text check
    complementing the YAML-parsed job/step assertions above.
    """
    ci_text = CI_FILE.read_text(encoding="utf-8")
    lines = ci_text.splitlines()
    # Find the smoke job's line span: from its 2-space-indented key to the next
    # 2-space-indented job key (or EOF).
    start = None
    for i, line in enumerate(lines):
        if line.strip().startswith(f"{JOB_NAME}:") and line.startswith("  ") and not line.startswith("   "):
            start = i
            break
    assert start is not None, f"Could not locate job '{JOB_NAME}' block in {CI_FILE.name}"
    end = len(lines)
    for j in range(start + 1, len(lines)):
        line = lines[j]
        # Terminate at the next sibling job key: a non-blank, non-comment line
        # indented exactly two spaces (the jobs.* level). Do not require a
        # trailing ':' — a sibling key with an inline mapping would otherwise
        # never terminate the block and fold the spike job into the smoke block.
        if line.startswith("  ") and not line.startswith("   ") and line.strip() and not line.lstrip().startswith("#"):
            end = j
            break
    smoke_block = "\n".join(lines[start:end]).lower()
    assert "continue-on-error: true" not in smoke_block, (
        f"Literal 'continue-on-error: true' found inside the '{JOB_NAME}' job block in "
        f"{CI_FILE.name} — this disables the SENSOR-06 hard gate. Remove it."
    )
