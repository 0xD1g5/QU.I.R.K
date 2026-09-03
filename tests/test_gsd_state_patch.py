"""Phase 182 (TOOL-01): behavioural fixtures for the GSD `state.*` verb
patches applied downstream at ``~/.claude/get-shit-done/``.

Confirmed argv/cwd contract (Wave 0 blocker, resolved 2026-09-03 and proven
live by ``test_begin_phase_cwd_contract_is_honoured`` below):

    node <GSD_TOOLS_CJS> state begin-phase --cwd <root> \\
        --phase <phase> --name <name> --plans <plans>

``gsd-tools.cjs`` accepts a native global ``--cwd <path>`` (and ``--cwd=<path>``)
flag, spliced out of argv before dispatch (``bin/gsd-tools.cjs`` ~lines 264-283).
``process.cwd()`` is only the default when ``--cwd`` is absent. This is what
satisfies ``tests/cli_helpers.py::run_fork_safe``'s "never pass a `cwd`
kwarg" rule -- ``--cwd`` is the *executable's own* flag, not a subprocess
kwarg, so there is no tension with that helper's design.

``state begin-phase`` itself takes NAMED flags only: ``--phase``, ``--name``,
``--plans`` (``bin/lib/state-command-router.cjs:64-67``, via
``parseNamedArgs``). A **positional** argument in that position is silently
ignored (no error, no effect) -- the same failure family as the documented
``record-metric``/``add-decision`` positional-arg gotcha. Always pass named
flags.

Root cause background for the two bugs under test here (do not re-derive --
see ``.planning/reports/gsd-sdk-state-corruption-2026-09-03.md``):

Bug A: ``stateReplaceField``'s bold-field branch in
``state-document.generated.cjs`` used an unanchored regex
(``(\\*\\*Field:\\*\\*\\s*)(.*)``, no ``^``, no ``/m``), so ``**Status:**``
matched anywhere in the document -- including mid-sentence inside historical
prose quoting that exact token -- and ``(.*)`` swallowed the remainder of
that line. Patched locally 2026-09-03 to
``^(\\s*\\*\\*Field:\\*\\*[ \\t]*)(.*)$`` with the ``/m`` flag. Because the
fix lives in a ``.generated.cjs`` file, a future regeneration silently
reverts it -- this test file is the durable guard against that.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from tests.cli_helpers import run_fork_safe

# ---------------------------------------------------------------------------
# Toolchain guard -- copies the VITEST_TOOLCHAIN_AVAILABLE idiom from
# tests/test_uat_disposition_integrity.py exactly. The `Linux Full Suite` CI
# job (.github/workflows/python-ci.yml, `pytest -q -m ""`) never provisions
# `~/.claude/get-shit-done/`, so every test in this file must skip honestly
# there rather than fake a pass.
# ---------------------------------------------------------------------------

NODE_PATH = shutil.which("node")
GSD_HOME = Path.home() / ".claude" / "get-shit-done"
GSD_TOOLS_CJS = GSD_HOME / "bin" / "gsd-tools.cjs"
GSD_STATE_DOC = GSD_HOME / "bin" / "lib" / "state-document.generated.cjs"
GSD_STATE_LIB = GSD_HOME / "bin" / "lib" / "state.cjs"

GSD_TOOLCHAIN_AVAILABLE = (
    NODE_PATH is not None
    and GSD_HOME.is_dir()
    and GSD_TOOLS_CJS.is_file()
    and GSD_STATE_DOC.is_file()
)
GSD_SKIP_REASON = (
    "GSD toolchain unavailable in this environment (node on PATH: "
    f"{NODE_PATH is not None}, {GSD_HOME} present: {GSD_HOME.is_dir()}, "
    f"{GSD_TOOLS_CJS} present: {GSD_TOOLS_CJS.is_file()}, "
    f"{GSD_STATE_DOC} present: {GSD_STATE_DOC.is_file()}) -- the Linux Full "
    "Suite CI job does not provision `~/.claude/get-shit-done/`, so this leg "
    "is honestly skipped there rather than faked. Run these tests on an "
    "operator machine with GSD installed to exercise them."
)

_GSD_SKIP = pytest.mark.skipif(not GSD_TOOLCHAIN_AVAILABLE, reason=GSD_SKIP_REASON)

# The real project's live planning state -- must never be touched by any
# fixture in this file. Every test seeds its own tmp_path `.planning/` and
# points `--cwd` at that instead.
_REPO_ROOT = Path(__file__).resolve().parent.parent
_REAL_STATE_MD = _REPO_ROOT / ".planning" / "STATE.md"


def _seed_planning(root: Path, state_md: str, roadmap_md: str | None = None) -> None:
    """Write a throwaway `.planning/STATE.md` (and optionally `ROADMAP.md`)
    under `root`, which must be a tmp_path -- never the real repo root."""
    planning_dir = root / ".planning"
    planning_dir.mkdir(parents=True, exist_ok=True)
    (planning_dir / "STATE.md").write_text(state_md, encoding="utf-8")
    if roadmap_md is not None:
        (planning_dir / "ROADMAP.md").write_text(roadmap_md, encoding="utf-8")


def _run_begin_phase(tools_cjs: Path, root: Path, *, phase, name: str, plans):
    """Invoke `state begin-phase` against `root` via the confirmed
    `--cwd`/named-flags argv contract. Every path is absolute, argv[0] is a
    `shutil.which` resolution, and no `cwd` kwarg is ever passed to
    `run_fork_safe` -- `--cwd` is the executable's own flag."""
    assert NODE_PATH is not None
    argv = [
        NODE_PATH,
        str(tools_cjs),
        "state",
        "begin-phase",
        "--cwd",
        str(root),
        "--phase",
        str(phase),
        "--name",
        name,
        "--plans",
        str(plans),
    ]
    return run_fork_safe(argv, timeout=30)


MINIMAL_STATE_MD = """---
gsd_state_version: 1.0
milestone: v9.9
status: verifying
---

## Current Position

Phase: 900 (demo) — EXECUTING
Status: Ready to execute
"""


@_GSD_SKIP
def test_begin_phase_cwd_contract_is_honoured(tmp_path) -> None:
    """The `--cwd` global flag retargets `state begin-phase` at a throwaway
    directory -- proving the argv contract -- AND the real repo's
    `.planning/STATE.md` is provably untouched by the same run."""
    before_bytes = _REAL_STATE_MD.read_bytes()
    before_mtime = _REAL_STATE_MD.stat().st_mtime_ns

    root = tmp_path
    _seed_planning(root, MINIMAL_STATE_MD)
    before_tmp = (root / ".planning" / "STATE.md").read_text(encoding="utf-8")

    proc = _run_begin_phase(GSD_TOOLS_CJS, root, phase=901, name="demo", plans=3)

    after_tmp = (root / ".planning" / "STATE.md").read_text(encoding="utf-8")
    after_bytes = _REAL_STATE_MD.read_bytes()
    after_mtime = _REAL_STATE_MD.stat().st_mtime_ns

    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert after_tmp != before_tmp
    assert after_bytes == before_bytes, (
        "the real .planning/STATE.md changed during a --cwd-scoped test run "
        "-- the argv contract silently retargeted the live project file"
    )
    assert after_mtime == before_mtime
