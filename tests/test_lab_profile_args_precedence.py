"""Phase 170-03 DEBT-02: real, non-Docker test of `lab.sh`'s documented
CLI-wins-over-.env `PROFILE_ARGS` precedence (Phase 52 DEBT-02).

Root cause / ground truth (verified 2026-08-28, do not re-derive): `lab.sh`
lines 4-16 snapshot the CLI-supplied `PROFILE_ARGS` environment variable
BEFORE sourcing `.env` (which could otherwise silently overwrite it), then
re-resolves `PROFILE_ARGS` from that snapshot if present, falling back to
whatever `.env` set. This test exercises the REAL script via a real `bash -x
lab.sh help` subprocess (the `help` branch calls only `usage()` and never
touches Docker) and inspects the xtrace output for the final resolved value
of `PROFILE_ARGS`, proving the precedence without reimplementing it.

Fork-safety: this spawns a real `bash` subprocess, so it is routed through
`tests/cli_helpers.py::run_fork_safe` (never a bare `subprocess.run`/`Popen`)
and this file is registered in `tests/test_cli_helper_usage.py`'s
`_COVERED_FILES` AST gate. See
`.planning/milestones/v5.16-phases/164-first-run-correctness/164-FINDING-fork-crash.md` for
why that matters.
"""
from __future__ import annotations

import os
import re
import shlex
import shutil
from pathlib import Path

from tests.cli_helpers import run_fork_safe

_REPO_ROOT = Path(__file__).resolve().parent.parent
_LAB_SH = _REPO_ROOT / "quantum-chaos-enterprise-lab" / "lab.sh"

# Matches a top-level xtrace line `+ PROFILE_ARGS=...` (single leading `+`,
# NOT `++` which is the nested trace produced while sourcing .env itself).
_TOP_LEVEL_TRACE_RE = re.compile(r"^\+\s*PROFILE_ARGS=(.*)$")


def _final_resolved_profile_args(stderr: str) -> str:
    """Return the value of the LAST top-level `+ PROFILE_ARGS=...` xtrace
    line in *stderr* (xtrace writes to stderr), shell-unquoted."""
    matches = [
        m.group(1) for line in stderr.splitlines() if (m := _TOP_LEVEL_TRACE_RE.match(line))
    ]
    assert matches, f"no top-level '+ PROFILE_ARGS=' xtrace line found in stderr:\n{stderr}"
    raw = matches[-1]
    # xtrace renders assigned string values already shell-quoted (e.g.
    # PROFILE_ARGS='--profile core' or PROFILE_ARGS=''); shlex.split handles
    # both the quoted and empty cases uniformly.
    parts = shlex.split(raw)
    return parts[0] if parts else ""


def _run_lab_sh_help(tmp_path: Path, *, env_file_contents: str | None, cli_profile_args: str | None):
    """Invoke the real lab.sh's `help` branch (no Docker) from *tmp_path* as
    its cwd, with an optional `.env` file and an optional CLI-supplied
    `PROFILE_ARGS` environment variable. Returns the CompletedProcess.

    `run_fork_safe` never accepts a `cwd` kwarg (forbidden by the AST gate),
    so the working-directory change happens inside the shell command text
    itself via `cd '<tmp_path>' && exec ...` (interfaces note option (b)).
    """
    if env_file_contents is not None:
        (tmp_path / ".env").write_text(env_file_contents, encoding="utf-8")

    bash = shutil.which("bash")
    assert bash is not None, "bash must be on PATH"

    shell_cmd = f"cd {shlex.quote(str(tmp_path))} && exec {shlex.quote(bash)} -x {shlex.quote(str(_LAB_SH))} help"

    env = dict(os.environ)
    if cli_profile_args is None:
        env.pop("PROFILE_ARGS", None)
    else:
        env["PROFILE_ARGS"] = cli_profile_args

    return run_fork_safe([bash, "-c", shell_cmd], env=env)


def test_cli_profile_args_wins_over_env_file():
    """A CLI-supplied PROFILE_ARGS env var beats a conflicting .env value."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        result = _run_lab_sh_help(
            tmp_path,
            env_file_contents='PROFILE_ARGS="--profile core"\n',
            cli_profile_args="--profile identity",
        )
        assert result.returncode == 0, (
            f"lab.sh help must exit clean (no Docker touched): "
            f"rc={result.returncode} stderr={result.stderr}"
        )
        assert _final_resolved_profile_args(result.stderr) == "--profile identity"


def test_env_file_honored_when_no_cli_override():
    """When no CLI PROFILE_ARGS is set, the .env value is used."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        result = _run_lab_sh_help(
            tmp_path,
            env_file_contents='PROFILE_ARGS="--profile core"\n',
            cli_profile_args=None,
        )
        assert result.returncode == 0
        assert _final_resolved_profile_args(result.stderr) == "--profile core"


def test_no_env_no_cli_resolves_empty():
    """With neither a .env value nor a CLI override, PROFILE_ARGS is empty."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        result = _run_lab_sh_help(
            tmp_path,
            env_file_contents=None,
            cli_profile_args=None,
        )
        assert result.returncode == 0
        assert _final_resolved_profile_args(result.stderr) == ""
