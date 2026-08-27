"""Phase 166 GATE-03: forward-locking gate against reintroducing
``subprocess.run(..., cwd=...)`` in the CLI-runner test files.

Root cause (fully diagnosed in
``.planning/phases/164-first-run-correctness/164-FINDING-fork-crash.md`` --
do not re-derive): CPython's ``subprocess.Popen._execute_child`` only
selects the safe ``posix_spawn`` path when BOTH
``(not close_fds or _HAVE_POSIX_SPAWN_CLOSEFROM)`` AND ``cwd is None``. On
this Python 3.14 build, ``_HAVE_POSIX_SPAWN_CLOSEFROM`` is ``False``, so
passing ``cwd`` to ``subprocess.run`` in any of these three files defeats
``posix_spawn`` selection and reintroduces the macOS
``fork()``-after-Network.framework SIGSEGV crash
(``nw_settings_child_has_forked``). That crash only manifests in a
full-suite, unfiltered ``python -m pytest`` run -- it is invisible in
per-file or standalone runs, so a naive "did the file still pass?" check
after a regression would not catch it. This gate exists specifically to
catch the regression BEFORE it ships, at collection time, regardless of
which subset of tests is run.

If this gate fails, route the offending call through
``tests/cli_helpers.py::run_cli`` instead of passing ``cwd`` directly.

Uses an AST walk, not a line-regex/substring grep, because several
``subprocess.run(...)`` calls span multiple lines with ``cwd=`` on its own
line, and the word "cwd" also legitimately appears in docstrings/comments
(including in this very file and in ``tests/cli_helpers.py``) that must NOT
trip the gate.
"""
from __future__ import annotations

import ast
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent

# Currently exactly the three CLI-runner test files that shell out to
# run_scan.py. Do not expand this list to cover unrelated subprocess.run
# call sites -- GATE-03's scope is these three files only (166-CONTEXT.md).
_COVERED_FILES = [
    "tests/test_target_cli.py",
    "tests/test_compliance_cli.py",
    "tests/test_db_migrate_cli.py",
]


def _find_cwd_kwarg_offenders(relative_path: str) -> list[str]:
    """Return 'file:lineno' strings for every subprocess.run(..., cwd=...)
    call site in *relative_path*, found via an AST walk (not a text grep)."""
    file_path = _REPO_ROOT / relative_path
    tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=relative_path)
    offenders: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        # Match subprocess.run(...): func is an Attribute named "run" whose
        # value is a Name "subprocess".
        if (
            isinstance(func, ast.Attribute)
            and func.attr == "run"
            and isinstance(func.value, ast.Name)
            and func.value.id == "subprocess"
        ):
            for kw in node.keywords:
                if kw.arg == "cwd":
                    offenders.append(f"{relative_path}:{node.lineno}")
    return offenders


def test_no_cwd_kwarg_on_subprocess_run_in_cli_runner_files() -> None:
    """Forward-locking gate: no subprocess.run(..., cwd=...) in the three
    CLI-runner test files (Phase 166 GATE-03).

    Passing `cwd` to subprocess.run in these files defeats CPython's
    posix_spawn selection on this Python build (posix_spawn requires BOTH
    close_fds=False AND cwd=None -- see
    .planning/phases/164-first-run-correctness/164-FINDING-fork-crash.md)
    and reintroduces the macOS fork()-after-Network.framework SIGSEGV
    crash. Route the offending call through tests/cli_helpers.py::run_cli
    instead, which supplies the absolute run_scan.py path and never passes
    cwd.
    """
    offenders: list[str] = []
    for relative_path in _COVERED_FILES:
        offenders.extend(_find_cwd_kwarg_offenders(relative_path))

    assert not offenders, (
        f"subprocess.run(..., cwd=...) found in {len(offenders)} site(s): "
        f"{offenders}. Passing cwd defeats posix_spawn selection on this "
        f"Python build and reintroduces the macOS fork()-after-"
        f"Network.framework SIGSEGV crash -- see "
        f"tests/cli_helpers.py::run_cli and "
        f".planning/phases/164-first-run-correctness/164-FINDING-fork-crash.md."
    )


def test_run_cli_helper_still_sets_close_fds_false() -> None:
    """Second half of the two-part fix (Phase 166 GATE-03): the shared
    run_cli() helper must still set close_fds=False.

    posix_spawn selection on this Python build requires close_fds=False
    (see .planning/phases/164-first-run-correctness/164-FINDING-fork-crash.md)
    -- omitting cwd alone is NOT sufficient. This assertion locks the other
    half of the fix, which the AST gate above does not cover.
    """
    helper_src = (_REPO_ROOT / "tests" / "cli_helpers.py").read_text(encoding="utf-8")
    assert "close_fds=False" in helper_src, (
        "tests/cli_helpers.py no longer sets close_fds=False on its "
        "subprocess.run call. Both close_fds=False AND omitting cwd are "
        "required to reach CPython's safe posix_spawn path on this Python "
        "build -- see "
        ".planning/phases/164-first-run-correctness/164-FINDING-fork-crash.md."
    )
