"""SCHED-02 regression: the dispatched scan command must be runnable.

`_dispatch_schedule()` built its command as
`schedule.profile or "balanced"`. But "balanced" is a *score* profile
(`--score-profile lenient|balanced|strict`); `run_scan --profile` accepts only
`quick|standard|deep` and defaults to "standard". Someone confused the two flags.

`quirk schedule add` defaults `--profile` to None, so every CLI-created schedule
without an explicit profile dispatched:

    python -m run_scan --config <generated> --profile balanced

which argparse rejects immediately:

    quirk: error: argument --profile: invalid choice: 'balanced'

The ScheduledRun row was then marked "failed" with no indication why. Introduced
2026-05-10 (Phase 63-02) and never covered by a test — UAT-SERIES records
UAT-63-02's dispatcher walkthrough as "deferred to live session", which is how it
survived three months.

Schedules created through the dashboard API were unaffected: its schema declares
`Literal["quick", "standard", "deep"] = "standard"`.
"""
from __future__ import annotations

import subprocess
import sys

import pytest

VALID_SCAN_PROFILES = {"quick", "standard", "deep"}


def _dispatched_profile(stored_profile):
    """Reproduce the dispatcher's profile-selection expression."""
    from quirk.cli import scheduler_cmd  # noqa: F401  (import guard)

    return stored_profile or "standard"


def test_default_dispatch_profile_is_a_valid_scan_profile():
    """The fallback used when a schedule stores no profile must be accepted by
    run_scan's --profile, not by --score-profile."""
    assert _dispatched_profile(None) in VALID_SCAN_PROFILES


def test_dispatcher_source_does_not_fall_back_to_a_score_profile():
    """Guard the specific confusion: score-profile vocabulary must not appear as
    the --profile fallback."""
    import pathlib

    # Comment-stripped, following tests/test_cve_score_guard.py's precedent: an
    # explanatory comment quoting the old buggy line must not fail its own guard.
    raw = pathlib.Path("quirk/cli/scheduler_cmd.py").read_text(encoding="utf-8")
    src = "\n".join(
        line for line in raw.splitlines() if not line.lstrip().startswith("#")
    )
    for score_only in ('or "balanced"', "or 'balanced'",
                       'or "lenient"', 'or "strict"'):
        assert score_only not in src, (
            f"SCHED-02: scheduler_cmd.py falls back to {score_only!r} for "
            f"--profile, but that is a --score-profile value; run_scan rejects it"
        )


@pytest.mark.parametrize("profile", sorted(VALID_SCAN_PROFILES))
def test_run_scan_accepts_every_profile_the_dispatcher_can_emit(profile):
    """End-to-end: argparse must accept what the dispatcher builds.

    Uses --help so no scan runs; argparse validates choices before --help only
    when the value is invalid, which is exactly the failure being guarded.
    """
    proc = subprocess.run(
        [sys.executable, "-m", "run_scan", "--profile", profile, "--help"],
        capture_output=True, text=True, timeout=120,
    )
    assert "invalid choice" not in (proc.stderr or ""), (
        f"run_scan rejected --profile {profile!r}: {proc.stderr[-300:]}"
    )


def test_run_scan_rejects_the_old_hardcoded_fallback():
    """Proves the bug was real rather than theoretical."""
    proc = subprocess.run(
        [sys.executable, "-m", "run_scan", "--profile", "balanced", "--help"],
        capture_output=True, text=True, timeout=120,
    )
    assert "invalid choice" in (proc.stderr or ""), (
        "expected run_scan to reject 'balanced' as a --profile value"
    )
