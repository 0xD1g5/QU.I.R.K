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


def test_no_continue_on_error_literal_in_file():
    """The CI file must not contain the literal string 'continue-on-error: true' anywhere."""
    ci_text = CI_FILE.read_text(encoding="utf-8").lower()
    # Only flag 'continue-on-error: true' — not just the key presence
    assert "continue-on-error: true" not in ci_text, (
        f"Literal 'continue-on-error: true' found in {CI_FILE.name} — "
        "this disables the SENSOR-06 hard gate. Remove it."
    )
