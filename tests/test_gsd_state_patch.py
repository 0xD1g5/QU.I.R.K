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

import os
import re
import shutil
import warnings
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
    and GSD_STATE_LIB.is_file()
)
GSD_SKIP_REASON = (
    "GSD toolchain unavailable in this environment (node on PATH: "
    f"{NODE_PATH is not None}, {GSD_HOME} present: {GSD_HOME.is_dir()}, "
    f"{GSD_TOOLS_CJS} present: {GSD_TOOLS_CJS.is_file()}, "
    f"{GSD_STATE_DOC} present: {GSD_STATE_DOC.is_file()}, "
    f"{GSD_STATE_LIB} present: {GSD_STATE_LIB.is_file()}) -- the Linux Full "
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


# ---------------------------------------------------------------------------
# TOOL-04 (182-06): full-command regression test at the boundary the safety
# claim is actually made about -- `state begin-phase` itself, not
# `stateReplaceField` in isolation. This is what 182-05's live demonstration
# against the real .planning/STATE.md found: `stateExtractField()` (the READ
# side, sibling of the already-patched `stateReplaceField`) carries the
# identical unanchored `**Field:**` defect, and the `## Session` scoping
# guard silently fails open on this project's own `## Session Continuity`
# header. Both feed `buildStateFrontmatter()` on every `begin-phase` call, so
# a test that only exercises `stateReplaceField` (as test_bug_a_* above does)
# cannot see this class of corruption -- it lives one call deeper, in the
# read path that turns body text back into frontmatter.
# ---------------------------------------------------------------------------

STOPPED_AT_PROSE_LINE = (
    "- [Phase 171]: an archived note recorded `**Stopped At:** "
    "stale-archived-value` verbatim."
)
FOCUS_PROSE_LINE = (
    "- [Phase 172]: a note quoted `**Current focus:** do-not-rewrite-this` "
    "while explaining the field."
)
# A fourth decoy, deliberately not Status/Stopped At/Current focus/Last
# Activity/Total Phases -- every one of those is EITHER normalized away
# (normalizeStateStatus() collapses any string containing "ready to
# execute" to the single keyword "executing", masking a Status-based
# discriminator entirely) OR itself rewritten by cmdStateBeginPhase's own
# stateReplaceField calls before frontmatter derivation runs (Last
# Activity, Current focus, Total Phases's sibling body fields are all
# written unconditionally or on first-time execution, entangling the
# write-side fix with the read-side one under test). Discovered
# empirically while proving this file's own negative control RED -- see
# 182-06-SUMMARY.md. `Paused At` is never written by `begin-phase` and is
# not normalized, so it isolates the bare `stateExtractField()` anchoring
# defect cleanly: absent legitimately (no real `**Paused At:**` field
# exists in this fixture), it must stay absent from frontmatter after a
# patched extraction, and must NOT pick up a decoy quoted elsewhere in
# body prose.
PAUSED_AT_PROSE_LINE = (
    "- [Phase 174]: a note incorrectly quoted `**Paused At:** "
    "waiting-for-review` while summarizing an unrelated phase."
)


def _full_command_state_md() -> str:
    return f"""---
gsd_state_version: 1.0
milestone: v9.9
milestone_name: Demo Milestone
status: verifying
stopped_at: "Completed 900-01-PLAN.md"
my_custom_key: must-survive
progress:
  total_phases: 7
  completed_phases: 6
  percent: 86
---

**Current focus:** Phase 900 — demo

## Accumulated Context

{PROSE_LINE}
{STOPPED_AT_PROSE_LINE}
{FOCUS_PROSE_LINE}
{PAUSED_AT_PROSE_LINE}

## Current Position

Phase: 900 (demo) — EXECUTING
Status: Ready to execute

## Session Continuity

**Stopped At:** Completed 900-01-PLAN.md
"""


@_GSD_SKIP
def test_begin_phase_does_not_read_body_prose_as_machine_fields(tmp_path) -> None:
    """Command-boundary regression test for TOOL-04. Runs the INSTALLED
    (patched) toolchain's full `state begin-phase` command -- not
    `stateReplaceField` in isolation -- against a fixture shaped like the
    real `.planning/STATE.md`, and asserts the resulting frontmatter is
    derived from the real machine fields, not from body prose that merely
    quotes a field name inside a code span."""
    root = tmp_path
    _seed_planning(root, _full_command_state_md())

    proc = _run_begin_phase(GSD_TOOLS_CJS, root, phase=901, name="demo", plans=3)
    assert proc.returncode == 0, proc.stdout + proc.stderr

    after_text = (root / ".planning" / "STATE.md").read_text(encoding="utf-8")
    after = _parse_frontmatter(after_text)

    # Assertion 1: status is not the **Status:**-quoting prose sentence.
    status = after.get("status") or ""
    assert "marker" not in status, (
        f"frontmatter status was read from body prose quoting **Status:** "
        f"instead of the real Status field (got: {status!r})"
    )
    assert "Must not change" not in status, (
        f"frontmatter status leaked the prose sentence's trailing clause "
        f"(got: {status!r})"
    )

    # Assertion 2: stopped_at is not the out-of-section prose decoy.
    stopped_at = after.get("stopped_at") or ""
    assert "stale-archived-value" not in stopped_at, (
        f"frontmatter stopped_at was read from an out-of-section "
        f"**Stopped At:** prose decoy instead of the real "
        f"## Session Continuity value (got: {stopped_at!r})"
    )

    # Assertion 3: stopped_at IS sourced from ## Session Continuity.
    assert "900-01-PLAN.md" in stopped_at, (
        f"frontmatter stopped_at was not derived from the "
        f"## Session Continuity section's real value (got: {stopped_at!r})"
    )

    # Assertion 4: all three prose decoys survive byte-identical -- the
    # write side did not regress while the read side was being fixed.
    assert PROSE_LINE in after_text, (
        "the **Status:**-quoting prose line did not survive begin-phase "
        "byte-identical"
    )
    assert STOPPED_AT_PROSE_LINE in after_text, (
        "the **Stopped At:**-quoting prose line did not survive begin-phase "
        "byte-identical"
    )
    assert FOCUS_PROSE_LINE in after_text, (
        "the **Current focus:**-quoting prose line did not survive "
        "begin-phase byte-identical"
    )
    assert PAUSED_AT_PROSE_LINE in after_text, (
        "the **Paused At:**-quoting prose line did not survive "
        "begin-phase byte-identical"
    )

    # Assertion 4c: no `**Paused At:**` field legitimately exists in this
    # fixture, so paused_at must stay absent -- not picked up from the
    # PAUSED_AT_PROSE_LINE decoy quoted elsewhere in the body.
    paused_at = after.get("paused_at")
    assert paused_at is None, (
        f"frontmatter paused_at was read from a body prose decoy quoting "
        f"**Paused At:** instead of staying absent (got: {paused_at!r})"
    )

    # Assertion 4b: the REAL **Current focus:** line genuinely moved --
    # proving assertion 4 is survival under a live rewrite, not survival
    # because nothing happened.
    focus_lines = [
        line for line in after_text.splitlines()
        if line.startswith("**Current focus:**")
    ]
    assert focus_lines, "no line starting with **Current focus:** found after begin-phase"
    assert "Phase 901" in focus_lines[0], (
        f"the real **Current focus:** line did not move to Phase 901 "
        f"(got: {focus_lines[0]!r})"
    )

    # Assertion 5: Bug B's preserve-unknown-keys merge still holds on this
    # richer fixture.
    assert after.get("my_custom_key") == "must-survive", (
        f"my_custom_key was dropped by begin-phase (got: "
        f"{after.get('my_custom_key')!r})"
    )
    progress = after.get("progress") or {}
    assert progress.get("total_phases") == 7
    assert progress.get("completed_phases") == 6
    assert "percent" in progress


def test_full_command_fixture_is_sensitive_to_the_unpatched_extractor(
    tmp_path, unpatched_gsd_tree
) -> None:
    """RED-proving negative control for the test above: the SAME fixture,
    run against a throwaway copy of the toolchain whose
    `state-document.generated.cjs` is pristine (pre-patch) content, DOES
    corrupt `paused_at` -- proving the positive test above is a sensitive
    assertion, not one that can only ever pass.

    The discriminator is `paused_at`, not `status`. Empirically (see
    182-06-SUMMARY.md), `status` cannot discriminate here:
    `normalizeStateStatus()` collapses ANY string containing the phrase
    "ready to execute" -- which both the real Status field and the reused
    `PROSE_LINE` decoy contain -- down to the single keyword "executing"
    regardless of which occurrence the (patched or unpatched) extractor
    picks up. A field like `Last Activity` is a worse choice too: it is
    unconditionally rewritten by `cmdStateBeginPhase` itself before
    frontmatter derivation ever runs, and reverting the WHOLE
    `state-document.generated.cjs` file (what `unpatched_gsd_tree` does)
    reverts `stateReplaceField` right along with `stateExtractField` --
    so an unanchored *write* lands on the decoy line instead of the real
    field, entangling the write-side regression with the read-side one
    this control means to isolate. `paused_at` is never written by
    `begin-phase` and is never normalized, so it isolates the bare
    `stateExtractField()` anchoring defect cleanly.

    `unpatched_gsd_tree` restores only `state-document.generated.cjs` (the
    `stateExtractField`/`stateReplaceField` file); `state.cjs` -- which
    carries the session-scoping guard and the Current-focus rewrite -- stays
    at whatever is currently installed. This control therefore isolates the
    `stateExtractField` extractor defect specifically; the session-guard
    defect is exercised by assertions 2 and 3 in the test above, against the
    installed tree.
    """
    root = tmp_path
    _seed_planning(root, _full_command_state_md())

    unpatched_tools_cjs = unpatched_gsd_tree / "bin" / "gsd-tools.cjs"
    proc = _run_begin_phase(
        unpatched_tools_cjs, root, phase=901, name="demo", plans=3
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr

    after_text = (root / ".planning" / "STATE.md").read_text(encoding="utf-8")
    after = _parse_frontmatter(after_text)

    paused_at = str(after.get("paused_at") or "")
    assert "waiting-for-review" in paused_at, (
        f"expected the unpatched extractor to read the "
        f"**Paused At:**-quoting prose decoy as the live value (got: "
        f"{paused_at!r}) -- if this assertion fails, the fixture no "
        f"longer reproduces the defect class 182-05 observed live"
    )


# ---------------------------------------------------------------------------
# Defect-class enumeration gate (182-07, TOOL-04 gap-closure).
#
# 182-01 root-caused "unanchored bold-field regex, where the sibling
# plain-text branch is already anchored" and patched ONE instance. 182-06
# found a SECOND instance (stateExtractField, the read-side twin) and a
# THIRD (focusPattern) -- both missed by the first pass's hand-derived
# enumeration. This gate exists so the fourth instance is never found by a
# corruption report either.
#
# BINDING DESIGN CONSTRAINT: the occurrence set below is GENERATED AT RUN
# TIME by scanning the installed source with Path.read_text() -- it is never
# seeded from a list written into this file. `_BOLD_FIELD_DISPOSITIONS`
# supplies a disposition ("anchored" or "accepted-read-only") for whatever
# the scan finds; it must never supply the occurrences themselves. A gate
# fed by a hand-written occurrence list is a hand-maintained allowlist
# wearing a test's clothes -- which is the exact shape of defect this phase
# has now hit three times. Keying is by (relative file path, the literal
# field-name text between the bold markers, the enclosing function name) --
# NEVER by line number (tests/test_skip_registry.py's `(file, LINENO)`
# keying is the documented cautionary example: it breaks on every line
# shift and is a phase-184-owned baseline failure this repo already lives
# with).
#
# TWO ESCAPING CONVENTIONS ARE IN PLAY, and a scan for only one is blind to
# half the toolchain: `state.cjs` writes plain regex literals, where the
# construct is `\*\*Field:\*\*` (four raw characters -- backslash, asterisk,
# backslash, asterisk). `state-document.generated.cjs` builds patterns as
# template-literal strings passed to `new RegExp()`, where every backslash
# is itself escaped, so the identical construct is
# `\\*\\*${escaped}:\\*\\*` (six raw characters). Verified by direct
# execution 2026-09-03: `grep -c '\\*\\*' state-document.generated.cjs`
# (single-backslash form) returns 0; `grep -c '\\\\*\\\\*'
# state-document.generated.cjs` (double-backslash form) returns 2. A scan
# matching only the single-backslash convention silently misses
# `stateExtractField` and `stateReplaceField` -- the two ORIGINAL sites of
# this entire defect class -- while still reporting a green, plausible
# result. `_MARK4`/`_MARK6` below match both.
# ---------------------------------------------------------------------------

_BOLD_FIELD_SCAN_RELPATHS = (
    "bin/lib/state.cjs",
    "bin/lib/state-document.generated.cjs",
)

# ---------------------------------------------------------------------------
# Install axis (186.1-02 / TOOL-05, D-06/D-07): a SECOND install of the same
# defect class exists -- the npx `gsd-sdk` package, resolved dynamically
# from wherever `gsd-sdk` currently sits on PATH, NEVER from a hardcoded
# content-addressed cache hash (CLAUDE.md GSD state.* Verb Integrity clause
# (h)(2): the npx cache directory name rotates silently on every
# `get-shit-done-cc` version bump). This mirrors -- rather than imports --
# `tests/test_gsd_state_plain_field.py`'s `_resolve_npx_sdk_dist()`; that
# sibling module already imports FROM this one (`GSD_HOME`,
# `GSD_TOOLCHAIN_AVAILABLE`, ...), so importing back here would be circular.
# ---------------------------------------------------------------------------


def _resolve_npx_sdk_dist() -> Path | None:
    """Resolve the npx `get-shit-done-cc` install's `sdk/dist` directory
    dynamically: `shutil.which("gsd-sdk")` -> `os.path.realpath` -> walk
    parents until a directory named `dist` whose parent is `sdk` is found.
    Returns `None` (never a guessed/hardcoded path) if any step fails."""
    which_path = shutil.which("gsd-sdk")
    if which_path is None:
        return None
    real = Path(os.path.realpath(which_path))
    for candidate in [real, *real.parents]:
        if candidate.name == "dist" and candidate.parent.name == "sdk":
            return candidate
    return None


_NPX_SDK_DIST = _resolve_npx_sdk_dist()

GSD_SDK_AVAILABLE = bool(
    NODE_PATH is not None
    and _NPX_SDK_DIST is not None
    and _NPX_SDK_DIST.is_dir()
    and (_NPX_SDK_DIST / "query" / "state.js").is_file()
    and (_NPX_SDK_DIST / "query" / "state-document.js").is_file()
)

if NODE_PATH is None:
    _npx_sdk_skip_check = "node not on PATH"
elif shutil.which("gsd-sdk") is None:
    _npx_sdk_skip_check = "`gsd-sdk` not on PATH (shutil.which returned None)"
elif _NPX_SDK_DIST is None or not _NPX_SDK_DIST.is_dir():
    _npx_sdk_skip_check = (
        "resolved `gsd-sdk`'s realpath but could not walk it to a sdk/dist "
        "directory"
    )
elif not (_NPX_SDK_DIST / "query" / "state.js").is_file():
    _npx_sdk_skip_check = f"resolved sdk/dist at {_NPX_SDK_DIST} but query/state.js is missing"
elif not (_NPX_SDK_DIST / "query" / "state-document.js").is_file():
    _npx_sdk_skip_check = (
        f"resolved sdk/dist at {_NPX_SDK_DIST} but query/state-document.js is missing"
    )
else:
    _npx_sdk_skip_check = "available"

GSD_SDK_SKIP_REASON = (
    f"npx `gsd-sdk` install unavailable in this environment ({_npx_sdk_skip_check}) "
    "-- the Linux Full Suite CI job does not provision an npx-installed "
    "get-shit-done-cc, so the npx leg of the field-scan gate is honestly "
    "skipped there rather than faked. IMPORTANT: a skip is not a pass -- "
    "the npx install was NOT scanned and is NOT proven clean when this "
    "reason fires. Run on an operator machine with `gsd-sdk` on PATH to "
    "actually exercise it."
)

# Two-axis scan registry (D-07): each entry names an install, its resolved
# root (may be `None`/unavailable), and the install-relative paths owning
# STATE.md field logic. `relpaths` are already textually distinct across
# installs (`bin/lib/...` vs `query/...`), so no extra key component is
# needed in the occurrence/ledger tuples below.
_FIELD_SCAN_INSTALLS: tuple[dict, ...] = (
    {
        "install_id": "cjs",
        "root": GSD_HOME,
        "available": GSD_TOOLCHAIN_AVAILABLE,
        "skip_reason": GSD_SKIP_REASON,
        "relpaths": ("bin/lib/state.cjs", "bin/lib/state-document.generated.cjs"),
    },
    {
        "install_id": "npx",
        "root": _NPX_SDK_DIST,
        "available": GSD_SDK_AVAILABLE,
        "skip_reason": GSD_SDK_SKIP_REASON,
        # `state-mutation.js` added by 186.1-02 (D-07): it hosts the npx
        # twin of `updateCurrentPositionFields`, a FOURTH, previously
        # undocumented site of this defect class first surfaced by
        # 186.1-01's negative controls (see 186.1-01-SUMMARY.md,
        # "Additional Sites Found"). It carries no bold `**Field:**`
        # markers (the bold scan finds nothing new here), but it does carry
        # bare `^Field:` constructs the bare-field scan below must see.
        "relpaths": ("query/state.js", "query/state-document.js", "query/state-mutation.js"),
    },
)

# Plain regex-literal convention: \*\*Field:\*\* (4 raw chars per marker).
_MARK4 = "\\*\\*"
# Template-literal-string convention: \\*\\*${expr}:\\*\\* (6 raw chars).
_MARK6 = "\\\\*\\\\*"

# `bin/lib/*.cjs` declares functions as `function NAME(...)`. The npx
# install's `query/*.js` files use ES module syntax instead -- either
# `export function NAME(...)` or `export const NAME = async (...) => {...}`
# (e.g. `stateGet` in `query/state.js`) -- so the enclosing-function finder
# must recognize both declaration shapes or every npx occurrence collapses
# to the useless `<module-scope>` bucket and silently loses its ledger key.
#
# BOTH regexes are anchored to COLUMN ZERO (no leading `\s*` before the
# keyword) deliberately -- verified necessary, not a stylistic choice: a
# permissive `^\s*const\s+(\w+)\s*=\s*\(` regex matches `state.cjs`'s own
# `const fmScalar = (key) => {...}` (line ~660), a helper arrow function
# declared INSIDE `cmdStateSnapshot`'s body. Backward-scanning from the
# "Last Date"/"Stopped At"/"Resume File" bold occurrences further down that
# same function, a column-permissive regex hits `fmScalar` FIRST and
# misattributes all three to it -- silently changing three pre-existing,
# already-dispositioned ledger keys the moment the arrow-const shape was
# added, rather than only adding new npx keys. Top-level declarations in
# both installs sit at column 0 (confirmed: `grep -n '^function \|^export '`
# against both files), so anchoring to column 0 recognizes the new npx
# shapes without perturbing any existing .cjs attribution.
_FUNCTION_DECL_RE = re.compile(r"^(?:export\s+)?function\s+(\w+)\s*\(")
_ARROW_CONST_DECL_RE = re.compile(r"^(?:export\s+)?const\s+(\w+)\s*=\s*(?:async\s*)?\(")
_VAR_NAME_RE = re.compile(r"\b(?:const|let|var)\s+(\w+)\s*=")


def _enclosing_function_name(lines: list[str], occurrence_idx: int) -> str:
    """Scan backward from `occurrence_idx` for the nearest function-shaped
    declaration -- `function NAME(`, `export function NAME(`, or
    `export const NAME = (...)`/`export const NAME = async (...)`. Text-based,
    not line-number-based -- it identifies WHICH function an occurrence
    lives in, so two textually-identical template patterns (e.g.
    `stateExtractField` and `stateReplaceField`, which both literally read
    `${escaped}` between the markers) still get distinct ledger keys
    without resorting to a line number."""
    for i in range(occurrence_idx, -1, -1):
        m = _FUNCTION_DECL_RE.match(lines[i])
        if m:
            return m.group(1)
        m = _ARROW_CONST_DECL_RE.match(lines[i])
        if m:
            return m.group(1)
    return "<module-scope>"


def _has_m_flag(line: str) -> bool:
    """True if the regex constructed on this line carries the `m` flag,
    under either the `new RegExp(pattern, 'im')` convention or the
    `/pattern/im` literal convention. Both forms place their flags
    immediately before the statement's trailing punctuation, so anchoring
    the check to end-of-line avoids being confused by parentheses inside
    the pattern body itself (e.g. a capture group).

    The npx install's `LOCAL PATCH` annotations are trailing INLINE `//`
    comments on the SAME line as the code (e.g. `..., 'im'); // LOCAL
    PATCH (2026-09-03, TOOL-05): anchored to line start -- ...`) -- a
    different convention from the `.cjs` install's own-line-above comments.
    A trailing `//` comment is stripped before the end-of-line checks below
    so this genuinely new npx line shape isn't misread as un-flagged;
    verified this strip does not corrupt any `.cjs` line, since none of
    that install's occurrence lines carry an inline trailing comment."""
    code_part = re.split(r"\s//", line, maxsplit=1)[0]
    m = re.search(r"['\"]([a-z]+)['\"]\)\s*;?\s*$", code_part)
    if m:
        return "m" in m.group(1)
    # `/pattern/im` literal convention. `)?` handles a call like
    # `sessionSection.match(/pattern/im)` whose statement continues on the
    # NEXT line (e.g. `|| sessionSection.match(...)`) and therefore has no
    # trailing `;` on THIS line at all -- verified against npx
    # `query/state.js`'s multi-line `||`-chained match() calls.
    m = re.search(r"/([a-z]+)\)?\s*;?\s*$", code_part)
    if m:
        return "m" in m.group(1)
    return False


def _scan_bold_field_occurrences() -> list[dict]:
    """Generate the occurrence set by reading BOTH installs' STATE.md-owning
    lib files line by line (D-07 install axis). Lines whose stripped form
    starts with `//` are skipped -- prose in a comment quoting a pattern
    (this very docstring block above, if it lived in the .cjs file, would
    be exactly that trap) must not count as an occurrence.

    An install whose root is unresolvable (`available` False in
    `_FIELD_SCAN_INSTALLS`) contributes zero occurrences and is silently
    excluded HERE -- callers that need to report the skip honestly (a skip
    is not a pass) do so via `_FIELD_SCAN_INSTALLS`'s own `available`/
    `skip_reason` fields, not by this function raising or skipping."""
    occurrences: list[dict] = []
    for entry in _FIELD_SCAN_INSTALLS:
        if not entry["available"]:
            continue
        root = entry["root"]
        for relpath in entry["relpaths"]:
            abs_path = root / relpath
            if not abs_path.is_file():
                continue
            text = abs_path.read_text(encoding="utf-8")
            lines = text.splitlines()
            for idx, line in enumerate(lines):
                if line.strip().startswith("//"):
                    continue
                for mark, convention in ((_MARK4, "4-char (regex-literal)"), (_MARK6, "6-char (template-literal)")):
                    pattern = re.compile(re.escape(mark) + r"([^\n:]*):" + re.escape(mark))
                    for m in pattern.finditer(line):
                        var_match = _VAR_NAME_RE.search(line)
                        occurrences.append(
                            {
                                "install": entry["install_id"],
                                "relpath": relpath,
                                "line_no": idx + 1,
                                "line": line,
                                "field_text": m.group(1),
                                "function": _enclosing_function_name(lines, idx),
                                "convention": convention,
                                "var_name": var_match.group(1) if var_match else "<unnamed>",
                            }
                        )
    return occurrences


# ---------------------------------------------------------------------------
# Construct-shape axis (186.1-02 / TOOL-05, D-07): bare, line-initial
# `Field:` regex constructions -- the plain-field FALLBACK branch that
# `stateExtractField()`/`stateReplaceField()` (and their CLI-display twins)
# fall through to when the bold `**Field:**` branch misses. This defect
# class (D-05, D-07) is a SEPARATE construct shape from the bold markers
# `_scan_bold_field_occurrences` looks for -- it has no `**`/`\\*\\*`
# anywhere in the pattern, so the bold scan's own marker regexes cannot see
# it at all. This is exactly how the plain-field fallback stayed invisible
# to the 182-series gate for four rounds: the gate was extended on the
# CONVENTION axis (regex-literal vs template-literal escaping, both still
# BOLD) but never on the SHAPE axis (bold vs bare).
#
# All six known sites share one concrete shape in this codebase: a
# template-literal regex source built as `new RegExp(\`^${expr}:...\`, 'im')`
# -- a literal caret immediately followed by a `${...}` interpolation
# immediately followed by a colon, with NO bold markers anywhere around it.
# `_BARE_FIELD_RE` matches that. Per 186.1-02-PLAN.md Task 2, a second,
# non-template "any plain-literal `^Something:` form" is also matched by
# `_BARE_LITERAL_FIELD_RE` for completeness/future-proofing, even though it
# currently matches zero sites in either install -- an honest zero is
# reported, not manufactured.
# ---------------------------------------------------------------------------

# `^${expr}:` -- e.g. `^${escaped}:`, `^${fieldEscaped}:`.
_BARE_FIELD_RE = re.compile(r"\^\$\{(\w+)\}:")
# `^Word:` as a literal (non-template) regex-source fragment -- deliberately
# NOT matching `^\s*\*\*...` (bold) or `^\$\{` (already handled above).
_BARE_LITERAL_FIELD_RE = re.compile(r"\^([A-Za-z][A-Za-z0-9 ]*):")

# Structural signals for the three-state scoping detector below. Read-only
# CLI-display sinks are distinguished from write-capable sites by what
# happens to the match result immediately afterward: `.cjs` funnels it
# through `output(...)` (stdout only, never a file write); the npx `query/`
# convention instead returns it wrapped in a `{ data: ... }` object (JSON
# stdout, likewise never written back to STATE.md).
_OUTPUT_SINK_RE = re.compile(r"\boutput\s*\(")
_DATA_RETURN_RE = re.compile(r"return\s*\{\s*data\s*:")
# `cmdStateSnapshot`/`stateSnapshot`'s Last Date/Stopped At/Resume File
# reads assign into a `session.<field> = match[1].trim()` object -- a
# third, mirrored-across-both-installs read-only sink shape distinct from
# `output(...)`/`return { data: ... }`, feeding a JSON "snapshot" response
# object that (like the other two shapes) is never written back to
# STATE.md. Verified identical in both `state.cjs` and `query/state.js`.
_SESSION_ASSIGN_RE = re.compile(r"\bsession\.\w+\s*=")


def _classify_field_scope(lines: list[str], occurrence_idx: int, var_name: str) -> str:
    """Return 'read-only', 'unscoped', or 'scoped' for the plain-field
    pattern named `var_name`, defined at `lines[occurrence_idx]`, based
    structurally on how the next few lines of source actually consume it --
    never on the enclosing function's name, which this deliberately avoids
    trusting per the run-time-scan design constraint above.

    - 'read-only': the match result is only ever handed to a display sink
      (`output(...)` or `return { data: ... }`) within the next few lines --
      it can never reach a STATE.md write.
    - 'unscoped': the pattern is applied (via `.match()`, `.test()`, or
      `.replace()`) directly against the whole-document `content` variable.
      This is the CURRENT, unpatched state of all four `state-document*`
      read/write sites -- a detector that reports 'scoped' here, before
      plan 03/04 lands, would make that plan's gate pass vacuously.
    - 'scoped': the pattern is applied against some OTHER, narrower
      variable (a derived region/substring) -- the post-patch shape.
    """
    window = lines[occurrence_idx : occurrence_idx + 8]
    window_text = "\n".join(window)

    if (
        _OUTPUT_SINK_RE.search(window_text)
        or _DATA_RETURN_RE.search(window_text)
        or _SESSION_ASSIGN_RE.search(window_text)
    ):
        return "read-only"

    # Two call shapes appear in this codebase for evaluating a pattern
    # variable against a text variable:
    #   <textVar>.match(<patternVar>)  /  <textVar>.replace(<patternVar>, ...)
    #   <patternVar>.test(<textVar>)
    target = None
    m = re.search(re.escape(var_name) + r"\.test\(\s*(\w+)", window_text)
    if m:
        target = m.group(1)
    else:
        m = re.search(r"(\w+)\.(?:match|replace)\(\s*" + re.escape(var_name), window_text)
        if m:
            target = m.group(1)

    if target is None:
        # Cannot prove scoping either way from this window -- conservative
        # default is 'unscoped' (today's known state for every real site),
        # never 'scoped', so an ambiguous detection can't mask a real
        # regression.
        return "unscoped"
    return "unscoped" if target == "content" else "scoped"


def _nearest_var_name(lines: list[str], idx: int) -> str | None:
    """Find the variable a pattern/match-result is assigned to, allowing
    for a `||`-chained multi-line statement -- e.g. `cmdStateSnapshot`'s
    `const lastDateMatch = sessionSection.match(/.../)\n  ||
    sessionSection.match(/^Last Date:.../);`, where the bare-field
    occurrence lives on the CONTINUATION line (no `const`/`let`/`var` on
    that line itself). Checks the occurrence's own line first, then up to
    two lines above it -- but ONLY accepts a candidate declaration whose
    OWN line contains `.match(`/`.test(`/`.replace(`/`RegExp(`, so an
    unrelated nearby variable (e.g. `updateCurrentPositionFields`'s
    `let posBody = posMatch[2];`, which sits just above its own inline,
    un-named `/^Status:/m.test(posBody)` calls) is never mistaken for the
    pattern's own name -- verified necessary: without this guard, `posBody`
    itself gets picked up as if it were the match-result variable, which is
    wrong in the opposite direction (it is the TEXT being matched, not the
    pattern/result)."""
    decl_shape_re = re.compile(r"\.(?:match|test|replace)\(|RegExp\(")
    for i in range(idx, max(idx - 3, -1), -1):
        if not decl_shape_re.search(lines[i]):
            continue
        m = _VAR_NAME_RE.search(lines[i])
        if m:
            return m.group(1)
    return None


def _scan_bare_field_occurrences() -> list[dict]:
    """Generate the bare/plain-field occurrence set the same way
    `_scan_bold_field_occurrences` does -- reading BOTH installs' source at
    run time, never from a checked-in list. A line already claimed by the
    BOLD scan's markers (`_MARK4`/`_MARK6` surrounding the same `Field:`
    text) is excluded here so the two occurrence sets stay disjoint; a bold
    construction textually contains a bare-looking `${expr}:` substring
    between its markers, and double-counting it under both scans would
    make the two ledgers fight over the same site."""
    bold_lines: set[tuple[str, int]] = {
        (o["relpath"], o["line_no"]) for o in _scan_bold_field_occurrences()
    }

    occurrences: list[dict] = []
    for entry in _FIELD_SCAN_INSTALLS:
        if not entry["available"]:
            continue
        root = entry["root"]
        for relpath in entry["relpaths"]:
            abs_path = root / relpath
            if not abs_path.is_file():
                continue
            text = abs_path.read_text(encoding="utf-8")
            lines = text.splitlines()
            for idx, line in enumerate(lines):
                if line.strip().startswith("//"):
                    continue
                if (relpath, idx + 1) in bold_lines:
                    continue
                seen_field_texts: set[str] = set()
                for regex, shape in (
                    (_BARE_FIELD_RE, "template (${expr}:)"),
                    (_BARE_LITERAL_FIELD_RE, "literal (Word:)"),
                ):
                    for m in regex.finditer(line):
                        field_text = f"${{{m.group(1)}}}" if regex is _BARE_FIELD_RE else m.group(1)
                        if field_text in seen_field_texts:
                            continue  # both regexes can match the same `${expr}:` span
                        seen_field_texts.add(field_text)
                        var_name = _nearest_var_name(lines, idx)
                        occurrences.append(
                            {
                                "install": entry["install_id"],
                                "relpath": relpath,
                                "line_no": idx + 1,
                                "line": line,
                                "field_text": field_text,
                                "function": _enclosing_function_name(lines, idx),
                                "shape": shape,
                                "var_name": var_name or "<unnamed>",
                                "scope_state": (
                                    _classify_field_scope(lines, idx, var_name)
                                    if var_name is not None
                                    else "unscoped"
                                ),
                            }
                        )
    return occurrences


# Ledger: (relpath, literal field-name text, enclosing function) ->
# (disposition, reason). "anchored" occurrences must carry `^` and the `/m`
# flag on the SAME line; "accepted-read-only" occurrences carry a written
# reason instead of a code change.
_BOLD_FIELD_DISPOSITIONS: dict[tuple[str, str, str], tuple[str, str]] = {
    ("bin/lib/state-document.generated.cjs", "${escaped}", "stateExtractField"): (
        "anchored",
        "TOOL-04 read-side twin of Bug A -- anchored 182-06. Lives in a "
        "*generated* file, so it is also registered in the "
        "gsd-local-patches/ durability layer.",
    ),
    ("bin/lib/state-document.generated.cjs", "${escaped}", "stateReplaceField"): (
        "anchored",
        "Bug A, the original write-side instance of this defect class -- "
        "anchored 182-01.",
    ),
    ("bin/lib/state.cjs", "Current focus", "cmdStateBeginPhase"): (
        "anchored",
        "182-06 Edit C: the in-command Current-focus rewrite inside "
        "cmdStateBeginPhase, a write path -- anchored and made newline-safe.",
    ),
    ("bin/lib/state.cjs", "Progress", "cmdStateUpdateProgress"): (
        "anchored",
        "T-182-25 / TOOL-04: the third write-path instance of this defect "
        "class, boldProgressPattern inside updateProgress's "
        "readModifyWriteStateMd callback -- anchored by 182-07 Task 2. "
        "Ledgered here as 'anchored' BEFORE that patch lands so this gate "
        "can be proven RED against the still-unpatched source; see "
        "182-07-SUMMARY.md for the verbatim RED/GREEN transcript.",
    ),
    ("bin/lib/state.cjs", "Last Date", "cmdStateSnapshot"): (
        "accepted-read-only",
        "T-182-29: feeds `state json`'s session object for console/report "
        "display only. Cannot write STATE.md. Scoped one level up by the "
        "## Session section guard (182-06 Edit B), but the field-level "
        "match itself is unanchored; the blast radius is a wrong displayed "
        "value, not a corrupted file.",
    ),
    ("bin/lib/state.cjs", "Stopped At", "cmdStateSnapshot"): (
        "accepted-read-only",
        "T-182-29: same session-display read path as Last Date immediately "
        "above -- see that entry's reason.",
    ),
    ("bin/lib/state.cjs", "Resume File", "cmdStateSnapshot"): (
        "accepted-read-only",
        "T-182-29: same session-display read path as Last Date above -- "
        "see that entry's reason.",
    ),
    ("bin/lib/state.cjs", "${fieldEscaped}", "cmdStateGet"): (
        "accepted-read-only",
        "NEW SITE found by this plan's run-time scan, absent from the "
        "plan's hand-derived orientation list -- itself a live instance of "
        "the exact failure mode ('a hand-derived enumeration read as "
        "complete while being partial') that motivates generating the "
        "occurrence set at run time instead of trusting a list. Backs the "
        "read-only `state get <field>` CLI command: the match result is "
        "only ever passed to output() for stdout display, never written "
        "back to STATE.md. Same accepted blast-radius class as T-182-29's "
        "other read-only sites: a wrong value shown for a manually-invoked "
        "diagnostic command, not a corruption vector. Recorded here rather "
        "than silently patched so the call to leave it alone can be "
        "overturned deliberately by a future session.",
    ),
    # --- npx `gsd-sdk` install (186.1-02, D-06/D-07 install-axis extension) ---
    # These three bold-field constructions in `sdk/dist/query/*.js` already
    # carry a `LOCAL PATCH (2026-09-03, TOOL-05): anchored to line start`
    # comment -- part of the 15-site npx patch set CLAUDE.md clause (h)
    # documents (`~/.claude/gsd-npx-sdk-patches/`). They were invisible to
    # this gate before 186.1-02 because the scan only ever read `GSD_HOME`.
    ("query/state-document.js", "${escaped}", "stateExtractField"): (
        "anchored",
        "npx twin of the .cjs stateExtractField bold branch -- already "
        "anchored per the 15-site npx patch set (CLAUDE.md clause (h)). "
        "Newly visible to this gate only as of 186.1-02's install-axis "
        "extension; not a new patch.",
    ),
    ("query/state-document.js", "${escaped}", "stateReplaceField"): (
        "anchored",
        "npx twin of the .cjs stateReplaceField bold branch (Bug A's "
        "original write-side instance) -- already anchored per the 15-site "
        "npx patch set (CLAUDE.md clause (h)). Newly visible to this gate "
        "only as of 186.1-02's install-axis extension; not a new patch.",
    ),
    ("query/state.js", "Last Date", "stateSnapshot"): (
        "anchored",
        "npx twin of `cmdStateSnapshot`'s Last Date read -- but UNLIKE the "
        ".cjs twin (ledgered 'accepted-read-only' below because its match "
        "is genuinely unanchored, `/\\*\\*Last Date:\\*\\*\\s*(.+)/i`, no "
        "`^`, no `/m`), this npx line IS anchored "
        "(`^\\s*\\*\\*Last Date:\\*\\*[ \\t]*(.+)$`, `/im`) per the 15-site "
        "npx patch set (CLAUDE.md clause (h)). Two installs implementing "
        "the same read genuinely differ here; each is ledgered to match "
        "its own actual code, not to match its sibling.",
    ),
    ("query/state.js", "Stopped At", "stateSnapshot"): (
        "anchored",
        "npx twin of `cmdStateSnapshot`'s Stopped At read -- see the Last "
        "Date entry immediately above for the anchored-vs-unanchored "
        "install divergence.",
    ),
    ("query/state.js", "Resume File", "stateSnapshot"): (
        "anchored",
        "npx twin of `cmdStateSnapshot`'s Resume File read -- see the Last "
        "Date entry above for the anchored-vs-unanchored install "
        "divergence.",
    ),
    ("query/state-mutation.js", "Progress", "stateUpdateProgress"): (
        "anchored",
        "npx twin of `cmdStateUpdateProgress`'s boldProgressPattern "
        "(182-07 Task 2's fix) -- already anchored per the 15-site npx "
        "patch set (CLAUDE.md clause (h)). Newly visible to this gate "
        "only as of 186.1-02's install-axis extension.",
    ),
    ("query/state-mutation.js", "Current focus", "stateBeginPhase"): (
        "anchored",
        "npx twin of `cmdStateBeginPhase`'s Current-focus rewrite (182-06 "
        "Edit C's fix) -- already anchored per the 15-site npx patch set "
        "(CLAUDE.md clause (h)). Newly visible to this gate only as of "
        "186.1-02's install-axis extension, which also added "
        "query/state-mutation.js to the npx relpaths list (D-07) because "
        "it hosts the npx twin of `updateCurrentPositionFields` -- the "
        "fourth defect-class site 186.1-01 found; see "
        "_PLAIN_FIELD_DISPOSITIONS below for that site's own dispositions.",
    ),
    ("query/state.js", "${fieldEscaped}", "stateGet"): (
        "anchored",
        "npx twin of `cmdStateGet`'s bold branch -- already anchored per "
        "the 15-site npx patch set (CLAUDE.md clause (h)). Unlike the "
        ".cjs twin (ledgered 'accepted-read-only' below because its match "
        "result only ever reaches stdout via output()), this branch's "
        "regex itself is anchored/newline-safe regardless of the "
        "read-only blast radius, and the npx patch set recorded it as "
        "'anchored' rather than 'accepted-read-only' -- both dispositions "
        "would be defensible for a read-only site; this ledger follows "
        "the npx patch set's own recorded choice rather than overriding "
        "it. Newly visible to this gate only as of 186.1-02's install-axis "
        "extension; not a new patch.",
    ),
}


@_GSD_SKIP
def test_bold_field_regex_class_is_fully_dispositioned() -> None:
    """Enumerate every `**Field:**`-shaped regex construction in the two
    STATE.md-owning libs (state.cjs, state-document.generated.cjs) BY
    SCANNING THE INSTALLED SOURCE AT RUN TIME, and assert each one carries
    an explicit, matching disposition in `_BOLD_FIELD_DISPOSITIONS`.

    Four independent failure modes are asserted against, each closing a
    gap this phase hit in practice:
      1. An occurrence with no ledger entry -- an unlisted defect-class
         member, the TOOL-04 shape itself.
      2. A ledger entry with no matching occurrence -- a stale allowlist
         row, which is how a gate quietly stops gating anything.
      3. Zero occurrences collected from state-document.generated.cjs
         specifically -- the convention-blindness failure mode: a scan
         written for only the plain regex-literal convention cannot see
         that file's template-literal-string patterns at all, and would
         otherwise surface as a confusing "stale ledger row" failure on
         (2) instead of naming its real, upstream cause.
      4. (186.1-02, D-07) Zero occurrences collected from the npx install
         when it is resolvable -- the install-axis counterpart of (3): a
         scan hardcoded to `GSD_HOME` is blind to `query/*.js` entirely,
         which is exactly how this defect class's fourth instance
         (186.1-01's `updateCurrentPositionFields` finding) stayed
         invisible to a gate that only ever looked at one install.
    """
    occurrences = _scan_bold_field_occurrences()

    # Availability is read from `_FIELD_SCAN_INSTALLS` itself (not the
    # standalone GSD_TOOLCHAIN_AVAILABLE/GSD_SDK_AVAILABLE module constants)
    # so that a test-time monkeypatch of the registry -- e.g. simulating a
    # rotated npx hash by flipping the npx entry's `available` to False --
    # actually changes this function's behaviour, which is exactly what the
    # D-07 skip-semantics inversion check (186.1-02 Task 1) exercises.
    installs_by_id = {e["install_id"]: e for e in _FIELD_SCAN_INSTALLS}

    generated_hits = [
        o
        for o in occurrences
        if o["relpath"] == "bin/lib/state-document.generated.cjs"
    ]
    if installs_by_id["cjs"]["available"] and not generated_hits:
        pytest.fail(
            "the run-time scan collected ZERO bold-field occurrences from "
            "state-document.generated.cjs. That file uses the "
            "template-literal-string escaping convention "
            "(`\\\\*\\\\*${expr}:\\\\*\\\\*`, six raw characters), not the "
            "plain regex-literal convention "
            "(`\\*\\*Field:\\*\\*`, four raw characters) that state.cjs "
            "uses. A scan matching only the four-character marker is BLIND "
            "to this file and would silently orphan its ledger rows "
            "(stateExtractField, stateReplaceField) rather than fail here "
            "with the real cause. Fix the scan's marker set (_MARK4/_MARK6), "
            "not the ledger."
        )

    npx_hits = [o for o in occurrences if o["install"] == "npx"]
    if installs_by_id["npx"]["available"] and not npx_hits:
        pytest.fail(
            "the run-time scan collected ZERO bold-field occurrences from "
            "the resolvable npx `gsd-sdk` install (query/state.js, "
            "query/state-document.js). This is the install-axis "
            "counterpart of the convention-blindness failure above: a scan "
            "hardcoded to GSD_HOME cannot see this install at all. Fix "
            "_FIELD_SCAN_INSTALLS' npx entry, not the ledger."
        )
    if not installs_by_id["npx"]["available"]:
        warnings.warn(
            RuntimeWarning(
                "npx `gsd-sdk` install SKIPPED for this gate run: "
                f"{installs_by_id['npx']['skip_reason']}"
            )
        )

    matched_keys: set[tuple[str, str, str]] = set()
    for occ in occurrences:
        key = (occ["relpath"], occ["field_text"], occ["function"])
        assert key in _BOLD_FIELD_DISPOSITIONS, (
            f"undispositioned bold-field construction found by the "
            f"run-time scan: file={occ['relpath']!r} "
            f"pattern=`**{occ['field_text']}:**` (variable "
            f"{occ['var_name']!r}, function {occ['function']!r}, line "
            f"{occ['line_no']}, {occ['convention']} convention). "
            f"Disposition it deliberately in _BOLD_FIELD_DISPOSITIONS as "
            f"'anchored' or 'accepted-read-only' with a written reason -- "
            f"do not add it reflexively just to satisfy this assertion."
        )
        matched_keys.add(key)
        disposition, reason = _BOLD_FIELD_DISPOSITIONS[key]
        assert reason.strip(), f"ledger entry {key} has an empty reason"

        if disposition == "anchored":
            assert "^" in occ["line"], (
                f"{key} (variable {occ['var_name']!r}, line "
                f"{occ['line_no']}) is ledgered 'anchored' but its line "
                f"has no `^` anchor: {occ['line']!r}"
            )
            assert _has_m_flag(occ["line"]), (
                f"{key} (variable {occ['var_name']!r}, line "
                f"{occ['line_no']}) is ledgered 'anchored' but its regex "
                f"does not carry the /m flag: {occ['line']!r}"
            )
        elif disposition != "accepted-read-only":
            pytest.fail(f"unknown disposition {disposition!r} for {key}")

    # A ledger row belonging to a currently-unavailable install is an
    # honest skip, not a stale row -- excluded here the same way the
    # per-install occurrence counts above are. `relpath` alone identifies
    # the owning install (the two installs' relpaths are textually
    # disjoint: `bin/lib/...` vs `query/...`).
    relpath_to_install = {
        relpath: entry["install_id"]
        for entry in _FIELD_SCAN_INSTALLS
        for relpath in entry["relpaths"]
    }
    unavailable_installs = {
        entry["install_id"] for entry in _FIELD_SCAN_INSTALLS if not entry["available"]
    }
    stale = {
        key
        for key in set(_BOLD_FIELD_DISPOSITIONS) - matched_keys
        if relpath_to_install.get(key[0]) not in unavailable_installs
    }
    assert not stale, (
        "ledger entries with no matching occurrence in the installed "
        "source -- a stale allowlist row is how a gate quietly stops "
        f"gating anything: {sorted(stale)}"
    )


# ---------------------------------------------------------------------------
# Bare/plain-field defect-class enumeration gate (186.1-02, TOOL-05).
#
# 186.1-CONTEXT.md's D-05/D-07 named SIX sites: `stateExtractField`'s and
# `stateReplaceField`'s plain-field FALLBACK branch, in both installs, plus
# the two read-only CLI-display twins (`cmdStateGet`, `stateGet`). Running
# the extended two-axis scan (`_scan_bare_field_occurrences`) against the
# CURRENTLY INSTALLED, unpatched source found TWENTY-THREE more --
# 186.1-01's negative controls had already flagged the reason why:
# `updateCurrentPositionFields` (`state.cjs`, `state-mutation.js`) and its
# siblings `cmdStateBeginPhase`/`cmdStateCompletePhase`/`stateBeginPhase`
# carry their OWN, separate, unscoped `^Field:.*$` full-region regexes,
# applied to a derived `posBody`/inline text variable rather than to
# `content` directly, but STILL not scoped to the correct (leading-run)
# granularity D-02 specifies. Per this phase's explicit honesty
# requirement, the real count (29 total, not 6) is reported and every one
# is dispositioned below -- none were filtered out to match the plan's
# original hypothesis, and the six originally-named sites are still
# present and still individually keyed among the 29.
#
# Ledger: (relpath, literal field-name text, enclosing function) ->
# (disposition, reason). Every row's disposition must match the scoping
# detector's OBSERVED state for that occurrence:
#   'accepted-read-only' <-> observed 'read-only'
#   'pending-scoping'    <-> observed 'unscoped'
#   'scoped'             <-> observed 'scoped'   (none exist yet -- 186.1-02
#                            lands before plans 03/04's fix, so this value
#                            is reserved for a future ledger update, not
#                            used here. A 'scoped' occurrence appearing
#                            with no matching 'scoped' ledger row is caught
#                            by the same undispositioned-occurrence check
#                            every other shape uses.)
# ---------------------------------------------------------------------------

_ADDITIONAL_SITE_REASON = (
    "Fourth defect-class site, found by 186.1-01's negative controls (see "
    "186.1-01-SUMMARY.md 'Additional Sites Found'), NOT the "
    "stateReplaceField/stateExtractField pair 186.1-CONTEXT.md/RESEARCH.md "
    "originally named. A SEPARATE, unscoped, full-region `^Field:.*$` "
    "regex applied to a derived `posBody` (or inlined directly against "
    "`content`) -- still not scoped to the leading-run granularity D-02 "
    "specifies, so it needs the SAME scoping treatment, just in a "
    "different function/file. Flagged for plans 03/04, NOT fixed here -- "
    "186.1-02 is guard-only. The scoping detector reports 'unscoped' here "
    "via its documented conservative default (no named pattern variable "
    "to test a scoping target against, since this code inlines the regex "
    "literal straight into `.test()`/`.replace()`); that default happens "
    "to be the semantically correct classification for this shape, not a "
    "coincidence papered over -- see `_classify_field_scope`'s docstring."
)

_NPX_186_1_03_SCOPED_REASON = (
    "Fourth defect-class site (see _ADDITIONAL_SITE_REASON above for the "
    "discovery trace) -- 186.1-03 scoped this npx instance to "
    "`fieldRegion`'s leading run (imported from ./state-document.js, the "
    "same run-time-derived, no-allowlist region the plain-fallback fix "
    "uses) instead of the whole outer `## Current Position` span, and "
    "named the pattern variables (`new RegExp('^Field:.*$', flags)`) so "
    "this scan's structural detector can see the scoping -- previously "
    "these were unnamed inline regex literals, which the detector's "
    "conservative default always reports as 'unscoped' regardless of "
    "actual behaviour. Flipped to 'scoped' in the same commit that landed "
    "the code change (the bidirectional property 186.1-02 Task 3 "
    "requires). The `.cjs` twin (bin/lib/state.cjs) is unaffected -- that "
    "install is plan 186.1-04's, not touched here."
)

_SNAPSHOT_READ_ONLY_REASON = (
    "Session-snapshot read: assigns into a `session.<field> = "
    "match[1].trim()` object consumed only by `state json`'s/`state "
    "snapshot`'s console/report display (same accepted blast-radius class "
    "as this file's T-182-29 bold-field entries for these same three "
    "fields) -- the match result can never reach a STATE.md write. Newly "
    "visible to this gate only as of 186.1-02's construct-shape extension "
    "(the plain FALLBACK branch of the same read, distinct from the bold "
    "branch already ledgered above)."
)

_PLAIN_FIELD_DISPOSITIONS: dict[tuple[str, str, str], tuple[str, str]] = {
    # --- The six originally-named sites (186.1-CONTEXT.md D-05/D-07) ---
    ("bin/lib/state-document.generated.cjs", "${escaped}", "stateExtractField"): (
        "pending-scoping",
        "TOOL-05 (D-05): read-side plain-fallback twin of stateReplaceField "
        "below. Anchored (TOOL-04, 182-06) but UNSCOPED -- the `/m` flag "
        "makes `^` match the start of ANY line in the whole document body, "
        "so the first line-initial `Status:` anywhere wins. Plan 186.1-04 "
        "scopes this to the correct leading-run region in the .cjs "
        "install. This row asserts the site is CURRENTLY unscoped -- "
        "flip to 'scoped' in the SAME commit that lands 186.1-04's patch, "
        "or this gate fails the moment the patch lands without a matching "
        "ledger update (the bidirectional property 186.1-02 Task 3 proves).",
    ),
    ("bin/lib/state-document.generated.cjs", "${escaped}", "stateReplaceField"): (
        "pending-scoping",
        "TOOL-05 (D-01/D-02): write-side plain-fallback branch. Anchored "
        "(TOOL-05, 2026-09-03) but UNSCOPED for the same reason as "
        "stateExtractField above. Plan 186.1-04 scopes this in the .cjs "
        "install; this row asserts the site is CURRENTLY unscoped and "
        "must flip to 'scoped' in the same commit that lands that patch.",
    ),
    ("bin/lib/state.cjs", "${fieldEscaped}", "cmdStateGet"): (
        "accepted-read-only",
        "Read-only `state get <field>` CLI display twin of the bold "
        "cmdStateGet entry above -- same accepted blast radius (a wrong "
        "value shown for a manually-invoked diagnostic command), same "
        "reasoning: the match result only ever reaches output() for "
        "stdout display, never written back to STATE.md.",
    ),
    ("query/state-document.js", "${escaped}", "stateExtractField"): (
        "scoped",
        "TOOL-05 (D-05): npx twin of the .cjs stateExtractField plain "
        "fallback above -- same unscoped-but-anchored shape. 186.1-03 "
        "scoped this to `fieldRegion`'s leading run (per-heading, "
        "run-time derived) and fails closed (null) when the field is "
        "absent from every region -- flipped in the same commit that "
        "landed the patch.",
    ),
    ("query/state-document.js", "${escaped}", "stateReplaceField"): (
        "scoped",
        "TOOL-05 (D-01/D-02): npx twin of the .cjs stateReplaceField plain "
        "fallback above -- the ORIGINAL live-corruption site (186.1-01's "
        "RED transcript: this exact branch rewrote STATE.md's narrative "
        "Status: decoy 8 times). 186.1-03 scoped this to `fieldRegion`'s "
        "leading run and splices the replacement back at that region's "
        "exact offset, failing closed (null) when the field is absent "
        "from every region -- flipped in the same commit that landed "
        "the patch.",
    ),
    ("query/state.js", "${fieldEscaped}", "stateGet"): (
        "accepted-read-only",
        "Read-only `state get <field>` npx query-handler twin of "
        "cmdStateGet above -- same accepted blast radius, same reasoning: "
        "the match result only ever reaches the query result's `data` "
        "field for JSON/stdout display, never written back to STATE.md.",
    ),
    # --- Session-snapshot read-only sites (6: 3 fields x 2 installs) ---
    ("bin/lib/state.cjs", "Last Date", "cmdStateSnapshot"): ("accepted-read-only", _SNAPSHOT_READ_ONLY_REASON),
    ("bin/lib/state.cjs", "Stopped At", "cmdStateSnapshot"): ("accepted-read-only", _SNAPSHOT_READ_ONLY_REASON),
    ("bin/lib/state.cjs", "Resume File", "cmdStateSnapshot"): ("accepted-read-only", _SNAPSHOT_READ_ONLY_REASON),
    ("query/state.js", "Last Date", "stateSnapshot"): ("accepted-read-only", _SNAPSHOT_READ_ONLY_REASON),
    ("query/state.js", "Stopped At", "stateSnapshot"): ("accepted-read-only", _SNAPSHOT_READ_ONLY_REASON),
    ("query/state.js", "Resume File", "stateSnapshot"): ("accepted-read-only", _SNAPSHOT_READ_ONLY_REASON),
    # --- Fourth defect-class site: updateCurrentPositionFields + siblings
    # (17: cjs cmdStateBeginPhase x4, cmdStateCompletePhase x3,
    # updateCurrentPositionFields x3; npx stateBeginPhase x4,
    # updateCurrentPositionFields x3) ---
    ("bin/lib/state.cjs", "Phase", "cmdStateBeginPhase"): ("pending-scoping", _ADDITIONAL_SITE_REASON),
    ("bin/lib/state.cjs", "Plan", "cmdStateBeginPhase"): ("pending-scoping", _ADDITIONAL_SITE_REASON),
    ("bin/lib/state.cjs", "Status", "cmdStateBeginPhase"): ("pending-scoping", _ADDITIONAL_SITE_REASON),
    ("bin/lib/state.cjs", "Last activity", "cmdStateBeginPhase"): ("pending-scoping", _ADDITIONAL_SITE_REASON),
    ("bin/lib/state.cjs", "Phase", "cmdStateCompletePhase"): ("pending-scoping", _ADDITIONAL_SITE_REASON),
    ("bin/lib/state.cjs", "Status", "cmdStateCompletePhase"): ("pending-scoping", _ADDITIONAL_SITE_REASON),
    ("bin/lib/state.cjs", "Last activity", "cmdStateCompletePhase"): ("pending-scoping", _ADDITIONAL_SITE_REASON),
    ("bin/lib/state.cjs", "Status", "updateCurrentPositionFields"): ("pending-scoping", _ADDITIONAL_SITE_REASON),
    ("bin/lib/state.cjs", "Plan", "updateCurrentPositionFields"): ("pending-scoping", _ADDITIONAL_SITE_REASON),
    ("bin/lib/state.cjs", "Last activity", "updateCurrentPositionFields"): ("pending-scoping", _ADDITIONAL_SITE_REASON),
    ("query/state-mutation.js", "Phase", "stateBeginPhase"): ("scoped", _NPX_186_1_03_SCOPED_REASON),
    ("query/state-mutation.js", "Plan", "stateBeginPhase"): ("scoped", _NPX_186_1_03_SCOPED_REASON),
    ("query/state-mutation.js", "Status", "stateBeginPhase"): ("scoped", _NPX_186_1_03_SCOPED_REASON),
    ("query/state-mutation.js", "Last activity", "stateBeginPhase"): ("scoped", _NPX_186_1_03_SCOPED_REASON),
    ("query/state-mutation.js", "Status", "updateCurrentPositionFields"): ("scoped", _NPX_186_1_03_SCOPED_REASON),
    ("query/state-mutation.js", "Plan", "updateCurrentPositionFields"): ("scoped", _NPX_186_1_03_SCOPED_REASON),
    ("query/state-mutation.js", "Last activity", "updateCurrentPositionFields"): (
        "scoped",
        _NPX_186_1_03_SCOPED_REASON,
    ),
}

_PLAIN_FIELD_SCOPE_STATE_BY_DISPOSITION = {
    "accepted-read-only": "read-only",
    "pending-scoping": "unscoped",
    "scoped": "scoped",
}


@_GSD_SKIP
def test_bare_field_regex_class_is_fully_dispositioned() -> None:
    """Enumerate every bare, line-initial `Field:`-shaped regex
    construction across BOTH installs BY SCANNING THE INSTALLED SOURCE AT
    RUN TIME (`_scan_bare_field_occurrences`), and assert each one carries
    an explicit, matching disposition in `_PLAIN_FIELD_DISPOSITIONS`.

    Failure modes mirror `test_bold_field_regex_class_is_fully_dispositioned`
    (undispositioned occurrence, stale ledger row) plus TWO new ones specific
    to this construct-shape/scoping axis:
      - A ledgered row whose declared disposition does NOT match the
        scoping detector's OBSERVED state for that occurrence -- this is
        the bidirectional property 186.1-02 Task 3 requires: it fails
        NOT ONLY when a site is wrongly left undispositioned, but ALSO the
        moment a 'pending-scoping' site's underlying code is patched to be
        genuinely scoped without its ledger row being flipped to 'scoped'
        in that same commit.
      - The bold and bare occurrence sets are NOT disjoint by
        (relpath, line_no) -- would mean the same construction is being
        double-ledgered under two different shape scanners.
    """
    bold_occurrences = _scan_bold_field_occurrences()
    bare_occurrences = _scan_bare_field_occurrences()

    bold_lines = {(o["relpath"], o["line_no"]) for o in bold_occurrences}
    bare_lines = {(o["relpath"], o["line_no"]) for o in bare_occurrences}
    overlap = bold_lines & bare_lines
    assert not overlap, (
        "the bold-field and bare-field scans both claimed the same "
        f"(relpath, line_no) pair(s): {sorted(overlap)} -- a construction "
        "is being double-ledgered under two different shape scanners."
    )

    matched_keys: set[tuple[str, str, str]] = set()
    for occ in bare_occurrences:
        key = (occ["relpath"], occ["field_text"], occ["function"])
        assert key in _PLAIN_FIELD_DISPOSITIONS, (
            f"undispositioned bare-field construction found by the "
            f"run-time scan: file={occ['relpath']!r} "
            f"pattern=`^{occ['field_text']}:` (variable "
            f"{occ['var_name']!r}, function {occ['function']!r}, line "
            f"{occ['line_no']}, {occ['shape']} shape, observed scope "
            f"state {occ['scope_state']!r}). Disposition it deliberately "
            f"in _PLAIN_FIELD_DISPOSITIONS as 'pending-scoping', "
            f"'accepted-read-only', or 'scoped' with a written reason -- "
            f"do not add it reflexively just to satisfy this assertion."
        )
        matched_keys.add(key)
        disposition, reason = _PLAIN_FIELD_DISPOSITIONS[key]
        assert reason.strip(), f"ledger entry {key} has an empty reason"
        assert disposition in _PLAIN_FIELD_SCOPE_STATE_BY_DISPOSITION, (
            f"unknown disposition {disposition!r} for {key}"
        )

        expected_state = _PLAIN_FIELD_SCOPE_STATE_BY_DISPOSITION[disposition]
        assert occ["scope_state"] == expected_state, (
            f"declared/observed scoping MISMATCH for {key}: ledger says "
            f"{disposition!r} (expects observed state {expected_state!r}) "
            f"but the scoping detector observed {occ['scope_state']!r} at "
            f"line {occ['line_no']} (variable {occ['var_name']!r}). "
            f"(relpath={key[0]!r}, function={key[2]!r}, "
            f"observed={occ['scope_state']!r}, declared={disposition!r})"
        )

    relpath_to_install = {
        relpath: entry["install_id"]
        for entry in _FIELD_SCAN_INSTALLS
        for relpath in entry["relpaths"]
    }
    unavailable_installs = {
        entry["install_id"] for entry in _FIELD_SCAN_INSTALLS if not entry["available"]
    }
    stale = {
        key
        for key in set(_PLAIN_FIELD_DISPOSITIONS) - matched_keys
        if relpath_to_install.get(key[0]) not in unavailable_installs
    }
    assert not stale, (
        "ledger entries with no matching occurrence in the installed "
        "source -- a stale allowlist row is how a gate quietly stops "
        f"gating anything: {sorted(stale)}"
    )


# ---------------------------------------------------------------------------
# Durability layer: gsd-local-patches/ + gsd-pristine/ (182-03).
#
# Bug A's fix lives in state-document.generated.cjs, a *generated* file --
# a future regeneration of the toolchain silently reverts it with no error,
# no warning, and no trace beyond the missing behaviour itself. The
# gsd-local-patches/ + gsd-pristine/ trees (seeded outside this repo, at
# ~/.claude/gsd-local-patches/ and ~/.claude/gsd-pristine/, per the Task 1
# checkpoint approved 2026-09-03) are what verify-reapply-patches.cjs
# resolves to detect that loss deterministically -- see that script's own
# header comment (bug #2969) for why this replaced trusting an LLM's
# free-text "verified: yes" reporting.
#
# Bug B's fix lives in ordinary source (state.cjs's syncStateFrontmatter) and
# is NOT regeneration-fragile -- it is registered in the same patch set for
# update-time re-apply (so a future `/gsd:update --reapply` can locate and
# reinstate it), but it does NOT need a redundant durability guard here. The
# behavioural fixtures in plan 182-02 (test_bug_b_frontmatter_survives_begin_phase,
# above) are what protect Bug B; this section is scoped to Bug A only.
#
# Retirement condition (per 182-CONTEXT.md "If upstream fixes it, REMOVE the
# local patch"): once gsd-build/get-shit-done lands the anchored-regex fix
# upstream and an operator `/gsd:update` picks it up, the local patch at
# ~/.claude/get-shit-done/bin/lib/state-document.generated.cjs is REMOVED
# (not left stacked on top of the upstream fix), gsd-local-patches/ and
# gsd-pristine/ are cleared of that entry, and the two tests below are
# replaced by a single assertion that the upstream-shipped regex is already
# anchored -- i.e. that the local patch is no longer necessary rather than
# merely redundant. Do not treat this durability layer as permanent
# furniture; it exists only until upstream catches up.
# ---------------------------------------------------------------------------

GSD_LOCAL_PATCHES_DIR = Path.home() / ".claude" / "gsd-local-patches"
GSD_PRISTINE_DIR = Path.home() / ".claude" / "gsd-pristine"
VERIFY_REAPPLY_SCRIPT = GSD_HOME / "bin" / "verify-reapply-patches.cjs"

_PATCH_RELPATH = "get-shit-done/bin/lib/state-document.generated.cjs"

GSD_PATCHES_AVAILABLE = (
    GSD_LOCAL_PATCHES_DIR.is_dir() and VERIFY_REAPPLY_SCRIPT.is_file()
)
GSD_PATCHES_SKIP_REASON = (
    "gsd-local-patches durability layer unavailable in this environment "
    f"({GSD_LOCAL_PATCHES_DIR} present: {GSD_LOCAL_PATCHES_DIR.is_dir()}, "
    f"{VERIFY_REAPPLY_SCRIPT} present: {VERIFY_REAPPLY_SCRIPT.is_file()}) -- "
    "CI provisions neither the seeded patches directory nor the operator's "
    "~/.claude/get-shit-done/ toolchain, so this leg is honestly skipped "
    "there rather than faked. Run on an operator machine with the 182-03 "
    "durability layer seeded to exercise it."
)

_GSD_PATCHES_SKIP = pytest.mark.skipif(
    not (GSD_TOOLCHAIN_AVAILABLE and GSD_PATCHES_AVAILABLE),
    reason=GSD_PATCHES_SKIP_REASON,
)


def _run_verify_reapply(
    *, patches_dir: Path, config_dir: Path, pristine_dir: Path
):
    """Invoke verify-reapply-patches.cjs through run_fork_safe -- argv[0] is
    the shutil.which('node') resolution, every path is absolute, and no cwd
    kwarg is ever passed (per this file's binding no-raw-subprocess /
    no-cwd-kwarg convention)."""
    assert NODE_PATH is not None
    argv = [
        NODE_PATH,
        str(VERIFY_REAPPLY_SCRIPT),
        "--patches-dir",
        str(patches_dir),
        "--config-dir",
        str(config_dir),
        "--pristine-dir",
        str(pristine_dir),
        "--json",
    ]
    return run_fork_safe(argv, timeout=30)


@_GSD_PATCHES_SKIP
def test_local_patches_are_durable() -> None:
    """Run verify-reapply-patches.cjs against the seeded gsd-local-patches/ +
    gsd-pristine/ trees (both patches registered by 182-03) and assert a
    clean gate. On failure, the assertion message includes the verifier's
    full JSON report -- naming WHICH line went missing in WHICH file, not
    just that something did -- and distinguishes exit 2 (structurally wrong
    directories) from exit 1 (a patch was genuinely lost), because those two
    failure classes point a reader to entirely different fixes."""
    proc = _run_verify_reapply(
        patches_dir=GSD_LOCAL_PATCHES_DIR,
        config_dir=GSD_HOME.parent,
        pristine_dir=GSD_PRISTINE_DIR,
    )

    if proc.returncode == 2:
        pytest.fail(
            "verify-reapply-patches.cjs exited 2 (usage/structural error) -- "
            "the gsd-local-patches/gsd-pristine layout is wrong, not merely "
            f"that a patch was lost. stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )

    assert proc.returncode == 0, (
        "verify-reapply-patches.cjs exited 1 -- at least one locally-patched "
        "line is missing from the installed toolchain file (a real content "
        f"loss, e.g. from a regeneration). Full JSON report:\n{proc.stdout}"
    )


def test_patch_loss_is_actually_detected(tmp_path) -> None:
    """Negative control: build a throwaway config-dir COPY of just the two
    installed files, overwrite the copy's state-document.generated.cjs with
    the PRISTINE (pre-Bug-A-patch) content -- simulating a regeneration that
    silently reverted the patch in place -- and assert the verifier now
    reports a non-zero exit when pointed at that copy as --config-dir. The
    real gsd-local-patches/ backup (unmodified, still holding the patched
    content) supplies the "what should be there" side of the comparison, so
    this exercises the exact same userAdded-lines diff the durability gate
    runs in production -- just against a deliberately-reverted installed
    file. This proves test_local_patches_are_durable's pass above is a real,
    sensitive assertion rather than a gate that can only ever pass. Writes
    only under tmp_path; the real ~/.claude/ trees are never touched."""
    if not (GSD_TOOLCHAIN_AVAILABLE and GSD_PATCHES_AVAILABLE):
        pytest.skip(GSD_PATCHES_SKIP_REASON)

    pristine_path = GSD_PRISTINE_DIR / _PATCH_RELPATH
    installed_path = GSD_HOME / "bin" / "lib" / "state-document.generated.cjs"
    other_installed_path = GSD_HOME / "bin" / "lib" / "state.cjs"
    if not pristine_path.is_file():
        pytest.skip(
            f"pristine baseline not found at {pristine_path} -- cannot run "
            "the negative control without a known-unpatched copy to "
            "simulate a regeneration reverting the patch"
        )
    pristine_content = pristine_path.read_bytes()
    assert _LOCAL_PATCH_MARKER not in pristine_content.decode(
        "utf-8", errors="replace"
    ), (
        f"{pristine_path} unexpectedly contains {_LOCAL_PATCH_MARKER!r} -- "
        "it is not a genuine pristine copy, so the negative control would "
        "run against already-patched content and pass vacuously"
    )

    # Mirror only the two relPath entries under a throwaway --config-dir,
    # then simulate the regeneration by overwriting ONE of them (the
    # generated file) with pristine content -- the other (state.cjs) is
    # copied through unmodified, since Bug B is durable and out of scope
    # for this negative control.
    fake_config_dir = tmp_path / "config-dir-copy"
    fake_target = fake_config_dir / _PATCH_RELPATH
    fake_other = fake_config_dir / "get-shit-done/bin/lib/state.cjs"
    fake_target.parent.mkdir(parents=True, exist_ok=True)
    fake_other.parent.mkdir(parents=True, exist_ok=True)
    fake_target.write_bytes(pristine_content)
    fake_other.write_bytes(other_installed_path.read_bytes())
    assert _LOCAL_PATCH_MARKER not in fake_target.read_text(encoding="utf-8")
    # Sanity: the REAL installed file is untouched by any of the above.
    assert _LOCAL_PATCH_MARKER in installed_path.read_text(encoding="utf-8")

    proc = _run_verify_reapply(
        patches_dir=GSD_LOCAL_PATCHES_DIR,
        config_dir=fake_config_dir,
        pristine_dir=GSD_PRISTINE_DIR,
    )

    assert proc.returncode != 0, (
        "expected a non-zero exit when the installed file is reverted to "
        "pristine content (simulating a regeneration silently undoing Bug "
        f"A's fix), but got exit 0. stdout:\n{proc.stdout}"
    )
    assert proc.returncode == 1, (
        "expected exit 1 (user-added lines missing) specifically, not exit "
        f"2 (structural error) -- got {proc.returncode}. stdout:\n{proc.stdout}"
    )
