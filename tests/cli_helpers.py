"""Phase 166 GATE-03: shared fork-safe subprocess helpers for CLI-runner tests.

Do not import this module outside ``tests/`` — the ``close_fds`` trade-off
below is accepted ONLY for short-lived test-harness subprocesses. See the
docstring on ``run_fork_safe`` for the full rationale.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_RUN_SCAN = _REPO_ROOT / "run_scan.py"


def run_fork_safe(
    argv: list[str],
    *,
    timeout: int = 30,
    env: dict[str, str] | None = None,
    check: bool = False,
    input: str | None = None,
) -> subprocess.CompletedProcess:
    """Run an arbitrary executable as a real subprocess, fork-safely, on macOS.

    Root cause (fully diagnosed in
    ``.planning/phases/164-first-run-correctness/164-FINDING-fork-crash.md`` —
    do not re-derive): CPython's ``subprocess.Popen._execute_child`` only
    selects the safe ``posix_spawn`` path when BOTH
    ``(not close_fds or _HAVE_POSIX_SPAWN_CLOSEFROM)`` AND ``cwd is None`` hold.
    On this Python 3.14 build, ``_HAVE_POSIX_SPAWN_CLOSEFROM`` is ``False``, so
    with the default ``close_fds=True``, ``posix_spawn`` is NEVER selected --
    with or without ``cwd``. Neither change alone is sufficient; BOTH
    setting ``close_fds`` to ``False`` AND omitting ``cwd`` (leaving it ``None``) are required
    to reach ``posix_spawn`` and avoid the macOS "fork() after Apple's
    Network.framework has initialised" SIGSEGV
    (``nw_settings_child_has_forked``). That crash is ordering-dependent: it
    only manifests once some earlier test in the same pytest process has
    initialised Network.framework, so it is invisible in standalone/per-file
    runs and only reproduces in a full unfiltered suite run.

    ``close_fds`` set to ``False`` leaks pytest's own inherited file descriptors into
    this short-lived child process. This is an ACCEPTED, TEST-SCOPED
    trade-off, not a production code path -- ``grep -rn "close_fds" quirk/
    run_scan.py`` must always return zero hits. DO NOT REVERT this parameter
    in a later cleanup pass without re-reading
    ``.planning/phases/164-first-run-correctness/164-FINDING-fork-crash.md``
    first: removing it makes the SIGSEGV reappear ONLY in full-suite macOS
    runs, invisible to standalone file runs, so the regression would ship
    silently.

    ``cwd`` is intentionally NEVER passed to the underlying ``subprocess.run``
    call (not even explicitly set to ``None`` -- the forward-locking AST gate
    in ``tests/test_cli_helper_usage.py`` requires an explicit ``close_fds``
    keyword set to ``False`` and forbids a literal ``cwd`` keyword on any
    covered ``subprocess.run``/``Popen``/``check_output``/``call`` call).
    Because there is no ``cwd`` kwarg, every path passed in ``argv`` MUST
    already be absolute -- a relative path would resolve against pytest's
    own invocation directory, not against any test's ``tmp_path``. Callers
    that genuinely need a working directory (e.g. git) must use the
    executable's own native flag instead of a ``cwd`` kwarg -- e.g.
    ``["git", "-C", str(abs_dir), "init", "-q"]``.

    This helper always shells out to a real executable as a subprocess -- it
    deliberately never calls anything in-process, to preserve real exit-code
    and argv-boundary coverage.

    Args:
        argv: the full argument vector, including the executable itself
            (e.g. ``["git", "-C", str(repo_dir), "init", "-q"]`` or
            ``[sys.executable, "-c", script]``). Any path-like argument must
            be absolute.
        timeout: seconds to wait before raising
            ``subprocess.TimeoutExpired``. Default 30.
        env: optional environment mapping to pass through to the child.
            When ``None`` (the default), the child inherits this process's
            environment as usual.
        check: when ``True``, raise ``subprocess.CalledProcessError`` on a
            non-zero exit code (mirrors ``subprocess.run``'s own ``check``).
        input: optional text passed to the child's stdin.

    Returns:
        The completed subprocess, with ``capture_output=True, text=True``.
    """
    return subprocess.run(
        list(argv),
        capture_output=True,
        text=True,
        timeout=timeout,
        close_fds=False,
        env=env,
        check=check,
        input=input,
    )


def run_cli(args: list[str], *, timeout: int = 30) -> subprocess.CompletedProcess:
    """Run ``run_scan.py`` as a real subprocess, fork-safely, on macOS.

    Thin wrapper over ``run_fork_safe`` that prepends
    ``[sys.executable, str(run_scan.py)]``. See ``run_fork_safe`` for the
    full fork-safety rationale (root-caused in
    ``.planning/phases/164-first-run-correctness/164-FINDING-fork-crash.md``).

    Args:
        args: CLI arguments to pass after ``run_scan.py`` (e.g.
            ``["compliance", "status", "--format", "json"]``). Any path-like
            argument must be absolute.
        timeout: seconds to wait before raising
            ``subprocess.TimeoutExpired``. Default 30; callers needing more
            headroom (e.g. db-migrate CLI tests) should pass a larger value
            explicitly.

    Returns:
        The completed subprocess, with ``capture_output=True, text=True``.
    """
    return run_fork_safe([sys.executable, str(_RUN_SCAN), *args], timeout=timeout)
