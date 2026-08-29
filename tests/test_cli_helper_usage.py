"""Phase 166 GATE-03: forward-locking gate against reintroducing a
crash-exposed ``subprocess.run``/``Popen``/``check_output``/``call`` spawn in
the CLI-runner and subprocess-spawning test files.

Root cause (fully diagnosed in
``.planning/milestones/v5.16-phases/164-first-run-correctness/164-FINDING-fork-crash.md`` --
do not re-derive): CPython's ``subprocess.Popen._execute_child`` only
selects the safe ``posix_spawn`` path when BOTH
``(not close_fds or _HAVE_POSIX_SPAWN_CLOSEFROM)`` AND ``cwd is None``. On
this Python 3.14 build, ``_HAVE_POSIX_SPAWN_CLOSEFROM`` is ``False``, so
EITHER passing ``cwd`` OR omitting an explicit ``close_fds`` set to
``False`` defeats ``posix_spawn`` selection and reintroduces the macOS
``fork()``-after-Network.framework SIGSEGV crash
(``nw_settings_child_has_forked``). That crash only manifests in a
full-suite, unfiltered ``python -m pytest`` run -- it is invisible in
per-file or standalone runs, so a naive "did the file still pass?" check
after a regression would not catch it. This gate exists specifically to
catch the regression BEFORE it ships, at collection time, regardless of
which subset of tests is run.

**close_fds=False is the load-bearing requirement, not cwd absence alone.**
166-05's full-suite evidence showed 4 of the 6 newly-migrated files crash
with NO ``cwd`` kwarg present at all -- the exposure is any default-
``close_fds`` spawn, not merely a ``cwd``-carrying one. A gate that only
forbade ``cwd`` would pass a newly-written crash-exposed call outright. So
this gate requires BOTH: an explicit ``close_fds=False`` keyword present,
AND no ``cwd`` keyword, on every direct spawn call in the covered files.

If this gate fails, route the offending call through
``tests/cli_helpers.py::run_cli`` (for ``run_scan.py`` invocations) or
``tests/cli_helpers.py::run_fork_safe`` (for any other executable) instead
of calling ``subprocess.run``/``Popen``/``check_output``/``call`` directly.

Uses an AST walk, not a line-regex/substring grep, because several spawn
calls span multiple lines with keywords on their own line, and the words
"cwd" and "close_fds" also legitimately appear in docstrings/comments
(including in this very file and in ``tests/cli_helpers.py``) that must NOT
trip the gate.
"""
from __future__ import annotations

import ast
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent

# The ten files that spawn real subprocesses and are covered by the
# fork-safety fix: the three CLI-runner files migrated in 166-03, the six
# broader crash-exposed files migrated in 166-05, plus tests/conftest.py
# (its _patch_sha1_signing shim was the actual crash source behind
# test_vault_connector.py's fatal signal -- discovered by 166-05's mandatory
# full-suite proof run, fixed alongside the nine, and added here so a future
# direct subprocess.run() reintroduced there is caught too).
# tests/cli_helpers.py itself is deliberately excluded -- it is the
# sanctioned chokepoint that implements the close_fds=False / no-cwd
# contract, not a caller of it.
_COVERED_FILES = [
    "tests/test_target_cli.py",
    "tests/test_compliance_cli.py",
    "tests/test_db_migrate_cli.py",
    "tests/test_lab_profile_args_precedence.py",
    "tests/test_lab_profile_certs.py",
    "tests/test_qramm_staleness.py",
    "tests/test_scheduler_dispatch_profile.py",
    "tests/test_sensor_windows_smoke.py",
    "tests/test_vault_connector.py",
    "tests/test_verify_phase_gates.py",
    "tests/conftest.py",
    # Phase 168-09: test_uat_disposition_integrity.py spawns `pytest`
    # subprocesses (collect-only + substitute-node execution) and hit the
    # exact same SIGSEGV in a full-suite run; migrated to run_fork_safe and
    # added here so a future direct subprocess.run() reintroduced there is
    # caught too.
    "tests/test_uat_disposition_integrity.py",
    # Phase 172-01: new CLI subprocess tests for the --fuzz argparse-time
    # non-TTY / budget-ceiling refusal checks (FUZZ-001/FUZZ-002).
    "tests/test_fuzz_cli_safety.py",
]

# Attribute names on a `subprocess` module reference that spawn a real
# child process and therefore fall under the posix_spawn requirement.
_SPAWNING_ATTRS = {"run", "Popen", "check_output", "call"}


def _is_direct_subprocess_spawn_call(node: ast.AST) -> bool:
    """True if *node* is a `subprocess.<run|Popen|check_output|call>(...)`
    call -- an ast.Call whose func is an Attribute on a Name `subprocess`."""
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    return (
        isinstance(func, ast.Attribute)
        and func.attr in _SPAWNING_ATTRS
        and isinstance(func.value, ast.Name)
        and func.value.id == "subprocess"
    )


def _find_offenders(relative_path: str) -> list[str]:
    """Return 'file:lineno: reason' strings for every direct
    subprocess.run/Popen/check_output/call call site in *relative_path*
    that either carries a `cwd` keyword or lacks an explicit
    `close_fds=False` keyword, found via an AST walk (not a text grep)."""
    file_path = _REPO_ROOT / relative_path
    tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=relative_path)
    offenders: list[str] = []
    for node in ast.walk(tree):
        if not _is_direct_subprocess_spawn_call(node):
            continue

        has_cwd = False
        has_close_fds_false = False
        for kw in node.keywords:
            if kw.arg == "cwd":
                has_cwd = True
            if (
                kw.arg == "close_fds"
                and isinstance(kw.value, ast.Constant)
                and kw.value.value is False
            ):
                has_close_fds_false = True

        if has_cwd:
            offenders.append(f"{relative_path}:{node.lineno}: carries cwd=...")
        if not has_close_fds_false:
            offenders.append(
                f"{relative_path}:{node.lineno}: missing explicit close_fds=False"
            )
    return offenders


def test_no_direct_crash_exposed_subprocess_spawn_in_covered_files() -> None:
    """Forward-locking gate: no direct
    subprocess.run/Popen/check_output/call call in the nine covered files may
    carry a `cwd` keyword or omit an explicit `close_fds=False` keyword
    (Phase 166 GATE-03, strengthened in 166-05).

    Either condition alone defeats CPython's posix_spawn selection on this
    Python build (posix_spawn requires BOTH close_fds=False AND cwd=None --
    see .planning/milestones/v5.16-phases/164-first-run-correctness/164-FINDING-fork-crash.md)
    and reintroduces the macOS fork()-after-Network.framework SIGSEGV crash.
    Route the offending call through tests/cli_helpers.py::run_cli or
    ::run_fork_safe instead, which supply close_fds=False and never pass cwd.
    """
    offenders: list[str] = []
    for relative_path in _COVERED_FILES:
        offenders.extend(_find_offenders(relative_path))

    assert not offenders, (
        f"crash-exposed subprocess spawn(s) found in {len(offenders)} site(s): "
        f"{offenders}. A direct subprocess.run/Popen/check_output/call in these "
        f"files must carry close_fds=False and must NOT carry cwd -- otherwise "
        f"it defeats posix_spawn selection on this Python build and "
        f"reintroduces the macOS fork()-after-Network.framework SIGSEGV crash. "
        f"See tests/cli_helpers.py::run_cli / ::run_fork_safe and "
        f".planning/milestones/v5.16-phases/164-first-run-correctness/164-FINDING-fork-crash.md."
    )


def test_run_cli_helper_still_sets_close_fds_false() -> None:
    """Second half of the two-part fix (Phase 166 GATE-03): the shared
    fork-safe primitive must still set close_fds=False.

    posix_spawn selection on this Python build requires close_fds=False
    (see .planning/milestones/v5.16-phases/164-first-run-correctness/164-FINDING-fork-crash.md)
    -- omitting cwd alone is NOT sufficient. This assertion locks the other
    half of the fix, which the AST gate above does not cover (it inspects
    the covered *caller* files, not the chokepoint itself).
    """
    helper_src = (_REPO_ROOT / "tests" / "cli_helpers.py").read_text(encoding="utf-8")
    assert "close_fds=False" in helper_src, (
        "tests/cli_helpers.py no longer sets close_fds=False on its "
        "subprocess.run call. Both close_fds=False AND omitting cwd are "
        "required to reach CPython's safe posix_spawn path on this Python "
        "build -- see "
        ".planning/milestones/v5.16-phases/164-first-run-correctness/164-FINDING-fork-crash.md."
    )
