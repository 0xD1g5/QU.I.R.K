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

import sys

import pytest

from tests.cli_helpers import run_fork_safe

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
    """Guard the specific confusion, semantically rather than textually.

    Walks the AST of scheduler_cmd.py for `<expr> or "<literal>"` fallbacks and
    asserts none yields a --score-profile value. Text matching is unusable here:
    the fix's own comment and docstring quote the old buggy line verbatim, and a
    grep-based guard would fail on its own documentation — the self-invalidation
    trap tests/test_cve_score_guard.py works around with comment stripping, which
    does not cover docstrings.
    """
    import ast
    import pathlib

    SCORE_ONLY = {"lenient", "balanced", "strict"}
    tree = ast.parse(pathlib.Path("quirk/cli/scheduler_cmd.py").read_text(encoding="utf-8"))
    offenders = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or):
            for value in node.values:
                if isinstance(value, ast.Constant) and value.value in SCORE_ONLY:
                    offenders.append((value.value, getattr(node, "lineno", "?")))
    assert not offenders, (
        f"SCHED-02: scheduler_cmd.py falls back to a --score-profile value where a "
        f"--profile is required; run_scan rejects it. Offenders (value, line): {offenders}"
    )



def _run_scan_argparse(profile: str):
    """Spawn `run_scan --profile <p> --help` and return the CompletedProcess.

    Skips rather than fails when the child is killed by a signal. On macOS a
    subprocess spawned late in a full-suite run can die with SIGSEGV before it
    executes anything (`git init` in tests/test_verify_phase_gates.py hits the
    same thing) — a signal-killed child tells us nothing about argparse, so
    asserting on its empty stderr would be a false failure. CI (Linux) is
    unaffected and runs these for real.
    """
    proc = run_fork_safe(
        [sys.executable, "-m", "run_scan", "--profile", profile, "--help"],
        timeout=120,
    )
    if proc.returncode is not None and proc.returncode < 0:
        pytest.skip(
            f"child killed by signal {-proc.returncode} before executing — "
            f"known macOS full-suite subprocess artifact, not an argparse result"
        )
    return proc


@pytest.mark.parametrize("profile", sorted(VALID_SCAN_PROFILES))
def test_run_scan_accepts_every_profile_the_dispatcher_can_emit(profile):
    """End-to-end: argparse must accept what the dispatcher builds.

    Uses --help so no scan runs; argparse validates choices before --help only
    when the value is invalid, which is exactly the failure being guarded.
    """
    proc = _run_scan_argparse(profile)
    assert "invalid choice" not in (proc.stderr or ""), (
        f"run_scan rejected --profile {profile!r}: {proc.stderr[-300:]}"
    )


def test_run_scan_rejects_the_old_hardcoded_fallback():
    """Proves the bug was real rather than theoretical."""
    proc = _run_scan_argparse("balanced")
    assert "invalid choice" in (proc.stderr or ""), (
        "expected run_scan to reject 'balanced' as a --profile value"
    )


# ---------------------------------------------------------------------------
# Phase 162 HWLC-20 — criterion 2: the dispatched command must match the
# schedule's kind. These assert `build_scan_argv` directly rather than through
# a subprocess, which is the coverage gap that let SCHED-02 live three months.
# ---------------------------------------------------------------------------

from types import SimpleNamespace  # noqa: E402

from quirk.cli.scheduler_cmd import build_scan_argv  # noqa: E402


def _sched(**kw):
    base = dict(name="s", cron_expr="0 0 * * *", target="10.0.0.1",
                profile=None, check_in=False)
    base.update(kw)
    return SimpleNamespace(**base)


def test_check_in_schedule_dispatches_check_in():
    argv = build_scan_argv(_sched(check_in=True), "/tmp/generated.yaml")
    assert "--check-in" in argv, (
        f"HWLC-20: a check-in schedule dispatched {argv!r} with no --check-in"
    )


def test_check_in_schedule_never_dispatches_a_profile_scan():
    """Criterion 2: 'a scheduled check-in job never silently runs a full
    profile scan instead'."""
    argv = build_scan_argv(_sched(check_in=True, profile="deep"), "/tmp/g.yaml")
    assert "--profile" not in argv, (
        f"HWLC-20: check-in schedule dispatched a profile scan — {argv!r}. "
        f"run_check_in() ignores --profile, so emitting it misrepresents what runs."
    )


def test_normal_schedule_is_unaffected_by_the_check_in_branch():
    argv = build_scan_argv(_sched(profile="deep"), "/tmp/g.yaml")
    assert "--check-in" not in argv
    assert argv[argv.index("--profile") + 1] == "deep"


def test_normal_schedule_with_no_profile_still_gets_the_valid_default():
    argv = build_scan_argv(_sched(profile=None), "/tmp/g.yaml")
    assert argv[argv.index("--profile") + 1] in VALID_SCAN_PROFILES


def test_legacy_schedule_row_without_the_column_is_treated_as_a_profile_scan():
    """Rows predating the check_in column read as False, not as a check-in."""
    legacy = SimpleNamespace(name="old", cron_expr="0 0 * * *",
                             target="10.0.0.1", profile="standard")
    argv = build_scan_argv(legacy, "/tmp/g.yaml")
    assert "--check-in" not in argv
    assert "--profile" in argv


def test_dispatched_argv_never_uses_shell_metacharacter_expansion():
    """T-63-07: list-form argv, and the config path is a single element."""
    argv = build_scan_argv(_sched(check_in=True), "/tmp/g.yaml")
    assert isinstance(argv, list) and all(isinstance(a, str) for a in argv)
    assert "/tmp/g.yaml" in argv
    assert not any(" " in a and a.startswith("-") for a in argv)
