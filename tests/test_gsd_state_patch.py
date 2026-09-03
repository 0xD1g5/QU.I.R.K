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

Bug B: ``syncStateFrontmatter`` (``state.cjs:898``) rebuilt frontmatter from a
fixed schema (``buildStateFrontmatter``, ``state.cjs:749``) instead of
merging it with the existing frontmatter it had already read and then
discarded. This silently deleted ``stopped_at``, the whole ``progress:``
block, and any unrecognized key on every ``begin-phase`` -- and, with no
``ROADMAP.md`` present, additionally reset ``milestone``/``milestone_name``
to invented defaults (``v1.0``/``milestone``). Patched locally 2026-09-03 in
``state.cjs`` (ordinary source, not generated) with a preserve-unknown-keys
merge: ``existingFm`` overlaid by ``derivedFm``'s non-null keys. See
``state.cjs``'s own ``LOCAL PATCH (2026-09-03)`` comment for the full
rationale, including the accepted T-182-10 trade-off.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from tests.cli_helpers import run_fork_safe

# Bug B (frontmatter reconstruction, state.cjs's syncStateFrontmatter) is
# patched and fixture-tested below (Wave 2 / 182-02), alongside Bug A's
# fixtures above (182-01). Both patches live in the same installed toolchain
# and both are exercised in this one file per 182-CONTEXT.md's discretion
# note ("whether the QUIRK-side detection test lives in a new file or
# extends an existing tooling test").

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


# ---------------------------------------------------------------------------
# Bug A: prose-survival fixture + sensitivity-proving negative control.
#
# The known-good repro (verbatim from
# .planning/reports/gsd-sdk-state-corruption-2026-09-03.md § Bug A):
#   before: - [Phase 170]: archived files gained a `**Status:**Ready to
#           execute` marker. Must not change.
#   after (unpatched): - [Phase 170]: archived files gained a
#           `**Status:**Executing Phase 901
# The trailing "` marker. Must not change." clause is destroyed because the
# unanchored bold-field regex matches **Status:** mid-sentence and consumes
# the rest of the line.
# ---------------------------------------------------------------------------

PROSE_LINE = (
    "- [Phase 170]: archived files gained a `**Status:**Ready to execute` "
    "marker. Must not change."
)

_LOCAL_PATCH_MARKER = "LOCAL PATCH (2026-09-03)"

# Fallback order for the pristine (pre-patch) source of
# state-document.generated.cjs, per 182-CONTEXT.md addendum item 5: plan
# 182-03 will populate gsd-pristine/ as the canonical location; until then
# (and as a permanent fallback) the .bak sitting alongside the patched file
# is the pristine copy taken at patch time.
_PRISTINE_CANDIDATES = [
    Path.home()
    / ".claude"
    / "gsd-pristine"
    / "get-shit-done"
    / "bin"
    / "lib"
    / "state-document.generated.cjs",
    GSD_HOME / "bin" / "lib" / "state-document.generated.cjs.bak",
]


def _resolve_pristine_state_document() -> Path | None:
    for candidate in _PRISTINE_CANDIDATES:
        if candidate.is_file():
            return candidate
    return None


def _fixture_state_md() -> str:
    return f"""---
gsd_state_version: 1.0
milestone: v9.9
status: verifying
---

## Accumulated Context

{PROSE_LINE}

## Current Position

Phase: 900 (demo) — EXECUTING
Status: Ready to execute
"""


@pytest.fixture(scope="session")
def unpatched_gsd_tree(tmp_path_factory):
    """A throwaway COPY of the whole GSD toolchain with
    `state-document.generated.cjs` swapped for its pristine (pre-Bug-A-patch)
    content -- reproducing the corruption in isolation, without ever writing
    inside the real `~/.claude/get-shit-done/`.

    Skips (does not fail) if no pristine source can be found, or if the
    would-be pristine source is itself accidentally already patched -- a
    negative control run against patched code would pass vacuously.
    """
    if not GSD_TOOLCHAIN_AVAILABLE:
        pytest.skip(GSD_SKIP_REASON)

    pristine_source = _resolve_pristine_state_document()
    if pristine_source is None:
        pytest.skip(
            "no pristine copy of state-document.generated.cjs found at any "
            f"of {[str(p) for p in _PRISTINE_CANDIDATES]} -- cannot run the "
            "negative control without a known-unpatched baseline"
        )

    pristine_bytes = pristine_source.read_bytes()
    if _LOCAL_PATCH_MARKER in pristine_bytes.decode("utf-8", errors="replace"):
        pytest.skip(
            f"{pristine_source} unexpectedly contains the "
            f"{_LOCAL_PATCH_MARKER!r} marker -- it is not a pristine "
            "pre-patch copy, so the negative control would run against "
            "already-patched code and pass vacuously"
        )

    dest_root = tmp_path_factory.mktemp("unpatched_gsd_tree")
    dest = dest_root / "get-shit-done"
    shutil.copytree(GSD_HOME, dest)

    target = dest / "bin" / "lib" / "state-document.generated.cjs"
    target.write_bytes(pristine_bytes)
    assert _LOCAL_PATCH_MARKER not in target.read_text(encoding="utf-8")

    return dest


@_GSD_SKIP
def test_bug_a_prose_line_survives_begin_phase(tmp_path) -> None:
    """Against the INSTALLED (patched) toolchain, a STATE.md prose line
    containing `**Status:**` inside a code span survives `begin-phase`
    byte-identical, AND the real `Status:` field under `## Current Position`
    has moved -- proving the command genuinely ran and the survival is not
    an accident of nothing happening."""
    root = tmp_path
    _seed_planning(root, _fixture_state_md())

    proc = _run_begin_phase(GSD_TOOLS_CJS, root, phase=901, name="demo", plans=3)
    assert proc.returncode == 0, proc.stdout + proc.stderr

    after = (root / ".planning" / "STATE.md").read_text(encoding="utf-8")

    assert PROSE_LINE in after
    current_position = after.split("## Current Position")[1]
    assert "Status: Ready to execute" not in current_position


def test_bug_a_fixture_is_sensitive_to_the_unpatched_regex(
    tmp_path, unpatched_gsd_tree
) -> None:
    """Negative control: the SAME fixture, run against a throwaway copy of
    the toolchain whose state-document.generated.cjs is the pristine
    (pre-Bug-A-patch) content, DOES corrupt the prose line -- proving the
    prior test's pass is a real, sensitive assertion and not vacuous."""
    root = tmp_path
    _seed_planning(root, _fixture_state_md())

    unpatched_tools_cjs = unpatched_gsd_tree / "bin" / "gsd-tools.cjs"
    proc = _run_begin_phase(
        unpatched_tools_cjs, root, phase=901, name="demo", plans=3
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr

    after = (root / ".planning" / "STATE.md").read_text(encoding="utf-8")

    assert PROSE_LINE not in after
    accumulated_context = after.split("## Accumulated Context")[1].split(
        "## Current Position"
    )[0]
    surviving_line = [
        line for line in accumulated_context.splitlines() if line.strip()
    ][0]
    assert surviving_line.startswith("- [Phase 170]:"), (
        "expected the corruption signature (line rewritten in place, not "
        f"removed entirely); got: {surviving_line!r}"
    )


# ---------------------------------------------------------------------------
# Bug B: preserve-unknown-keys round-trip fixture, parametrized over
# ROADMAP.md presence -- the two paths have documented different symptoms
# (see .planning/reports/gsd-sdk-state-corruption-2026-09-03.md § Bug B).
# ---------------------------------------------------------------------------

_BUG_B_SEED_FRONTMATTER = """---
gsd_state_version: 1.0
milestone: v9.9
milestone_name: Demo Milestone
status: verifying
stopped_at: mid-flight marker
my_custom_key: must-survive
last_updated: "2026-09-03T00:00:00.000Z"
progress:
  total_phases: 7
  completed_phases: 6
  percent: 86
---

## Current Position

Phase: 900 (demo) — EXECUTING
Status: Ready to execute
"""

# Minimal ROADMAP.md whose heading matches the seeded `milestone: v9.9` so
# `getMilestoneInfo` (bin/lib/core.cjs) re-derives milestone/milestone_name
# from disk rather than falling through to invented defaults.
_BUG_B_ROADMAP_MD = """# Roadmap

## Roadmap v9.9: Demo Milestone

🚧 In progress
"""


def _parse_frontmatter(state_md_text: str) -> dict:
    """Parse the YAML frontmatter block of a STATE.md-shaped document using
    the repo's already-vendored PyYAML (see quirk/config.py), rather than a
    hand-rolled parser or raw substring matching -- so a key that survives
    with a mangled value still fails an assertion on its parsed value."""
    assert state_md_text.startswith("---"), (
        f"expected a leading frontmatter block, got: {state_md_text[:80]!r}"
    )
    _, fm_block, _rest = state_md_text.split("---", 2)
    parsed = yaml.safe_load(fm_block)
    assert isinstance(parsed, dict), f"frontmatter did not parse to a dict: {parsed!r}"
    return parsed


@_GSD_SKIP
@pytest.mark.parametrize("roadmap_present", [True, False])
def test_bug_b_frontmatter_survives_begin_phase(tmp_path, roadmap_present) -> None:
    """A round-trip fixture proving Bug B's preserve-unknown-keys merge:
    `stopped_at`, the whole `progress:` block, and a NOVEL custom key (never
    part of any schema) all survive `state begin-phase` unchanged, on BOTH
    ROADMAP.md paths -- because the two paths have documented different
    symptoms (see gsd-sdk-state-corruption-2026-09-03.md). When no
    ROADMAP.md is present, `milestone`/`milestone_name` must NOT reset to
    the invented defaults `v1.0`/`milestone`. When one IS present, the
    re-derived milestone value must still win over the stale existing one
    -- proving the merge direction (derivedFm overlays existingFm) is
    correct, not merely that nothing was touched."""
    root = tmp_path
    roadmap_md = _BUG_B_ROADMAP_MD if roadmap_present else None
    _seed_planning(root, _BUG_B_SEED_FRONTMATTER, roadmap_md=roadmap_md)

    before = _parse_frontmatter(
        (root / ".planning" / "STATE.md").read_text(encoding="utf-8")
    )
    assert before["stopped_at"] == "mid-flight marker"
    assert before["progress"]["total_phases"] == 7

    proc = _run_begin_phase(GSD_TOOLS_CJS, root, phase=901, name="demo", plans=3)
    assert proc.returncode == 0, proc.stdout + proc.stderr

    after_text = (root / ".planning" / "STATE.md").read_text(encoding="utf-8")
    after = _parse_frontmatter(after_text)

    # Test 1: stopped_at survives.
    assert after.get("stopped_at") == "mid-flight marker", (
        f"stopped_at was dropped by begin-phase (got: {after.get('stopped_at')!r})"
    )

    # Test 2: the whole progress: block survives with every seeded sub-key.
    after_progress = after.get("progress")
    assert after_progress is not None, (
        f"progress block was dropped by begin-phase entirely (frontmatter: {after!r})"
    )
    assert after_progress.get("total_phases") == 7, (
        f"progress.total_phases was lost or mutated (got: {after_progress!r})"
    )
    assert after_progress.get("completed_phases") == 6, (
        f"progress.completed_phases was lost or mutated (got: {after_progress!r})"
    )
    assert after_progress.get("percent") == 86, (
        f"progress.percent was lost or mutated (got: {after_progress!r})"
    )

    # Test 3: a never-schema'd custom key survives -- proving generality,
    # not special-casing of the two named fields above.
    assert after.get("my_custom_key") == "must-survive", (
        f"my_custom_key (a novel, never-schema'd key) was dropped by "
        f"begin-phase (got: {after.get('my_custom_key')!r})"
    )

    if not roadmap_present:
        # Test 4: without a ROADMAP.md, the invented defaults must NOT appear.
        assert after.get("milestone") != "v1.0", (
            f"milestone was reset to the invented default 'v1.0' with no "
            f"ROADMAP.md present (got: {after.get('milestone')!r})"
        )
        assert after.get("milestone_name") != "milestone", (
            f"milestone_name was reset to the invented default 'milestone' "
            f"with no ROADMAP.md present (got: {after.get('milestone_name')!r})"
        )
    else:
        # Test 5: with a ROADMAP.md, re-derivation still wins over the stale
        # existing value -- proving the merge does not freeze old data.
        assert after.get("milestone") == "v9.9", (
            f"milestone should be re-derived from ROADMAP.md as 'v9.9' "
            f"(got: {after.get('milestone')!r})"
        )
        assert after.get("milestone_name") == "Demo Milestone", (
            f"milestone_name should be re-derived from ROADMAP.md as "
            f"'Demo Milestone' (got: {after.get('milestone_name')!r})"
        )
