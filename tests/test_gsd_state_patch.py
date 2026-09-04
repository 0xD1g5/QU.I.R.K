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

import re
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

# Plain regex-literal convention: \*\*Field:\*\* (4 raw chars per marker).
_MARK4 = "\\*\\*"
# Template-literal-string convention: \\*\\*${expr}:\\*\\* (6 raw chars).
_MARK6 = "\\\\*\\\\*"

_FUNCTION_DECL_RE = re.compile(r"^\s*function\s+(\w+)\s*\(")
_VAR_NAME_RE = re.compile(r"\b(?:const|let|var)\s+(\w+)\s*=")


def _enclosing_function_name(lines: list[str], occurrence_idx: int) -> str:
    """Scan backward from `occurrence_idx` for the nearest `function NAME(`
    declaration. Text-based, not line-number-based -- it identifies WHICH
    function an occurrence lives in, so two textually-identical template
    patterns (e.g. `stateExtractField` and `stateReplaceField`, which both
    literally read `${escaped}` between the markers) still get distinct
    ledger keys without resorting to a line number."""
    for i in range(occurrence_idx, -1, -1):
        m = _FUNCTION_DECL_RE.match(lines[i])
        if m:
            return m.group(1)
    return "<module-scope>"


def _has_m_flag(line: str) -> bool:
    """True if the regex constructed on this line carries the `m` flag,
    under either the `new RegExp(pattern, 'im')` convention or the
    `/pattern/im` literal convention. Both forms place their flags
    immediately before the statement's trailing punctuation, so anchoring
    the check to end-of-line avoids being confused by parentheses inside
    the pattern body itself (e.g. a capture group)."""
    m = re.search(r"['\"]([a-z]+)['\"]\)\s*;?\s*$", line)
    if m:
        return "m" in m.group(1)
    m = re.search(r"/([a-z]+)\s*;\s*$", line)
    if m:
        return "m" in m.group(1)
    return False


def _scan_bold_field_occurrences() -> list[dict]:
    """Generate the occurrence set by reading the two installed,
    STATE.md-owning lib files line by line. Lines whose stripped form
    starts with `//` are skipped -- prose in a comment quoting a pattern
    (this very docstring block above, if it lived in the .cjs file, would
    be exactly that trap) must not count as an occurrence."""
    occurrences: list[dict] = []
    for relpath in _BOLD_FIELD_SCAN_RELPATHS:
        abs_path = GSD_HOME / relpath
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
}


@_GSD_SKIP
def test_bold_field_regex_class_is_fully_dispositioned() -> None:
    """Enumerate every `**Field:**`-shaped regex construction in the two
    STATE.md-owning libs (state.cjs, state-document.generated.cjs) BY
    SCANNING THE INSTALLED SOURCE AT RUN TIME, and assert each one carries
    an explicit, matching disposition in `_BOLD_FIELD_DISPOSITIONS`.

    Three independent failure modes are asserted against, each closing a
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
    """
    occurrences = _scan_bold_field_occurrences()

    generated_hits = [
        o
        for o in occurrences
        if o["relpath"] == "bin/lib/state-document.generated.cjs"
    ]
    if not generated_hits:
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

    stale = set(_BOLD_FIELD_DISPOSITIONS) - matched_keys
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
