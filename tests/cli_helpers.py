"""Phase 166 GATE-03: shared fork-safe subprocess helper for CLI-runner tests.

Do not import this module outside ``tests/`` — the ``close_fds`` trade-off
below is accepted ONLY for short-lived test-harness subprocesses. See the
docstring on ``run_cli`` for the full rationale.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_RUN_SCAN = _REPO_ROOT / "run_scan.py"


def run_cli(args: list[str], *, timeout: int = 30) -> subprocess.CompletedProcess:
    """Run ``run_scan.py`` as a real subprocess, fork-safely, on macOS.

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
    call (not even explicitly as ``cwd=None`` -- the forward-locking AST gate
    in ``tests/test_cli_helper_usage.py`` forbids a literal ``cwd`` keyword on
    any ``subprocess.run`` call in the CLI-runner test files). Because there
    is no ``cwd``, every path passed in ``args`` MUST already be absolute --
    a relative path would resolve against pytest's own invocation directory,
    not against any test's ``tmp_path``.

    This helper always shells out to the real ``run_scan.py`` entry point as
    a subprocess -- it deliberately does NOT call ``run_scan.main()``
    in-process, to preserve real exit-code and argparse-boundary coverage.

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
    return subprocess.run(
        [sys.executable, str(_RUN_SCAN), *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        close_fds=False,
    )
