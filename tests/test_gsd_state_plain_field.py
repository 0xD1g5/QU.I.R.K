"""Phase 186.1 (TOOL-05): command-boundary fixtures for the GSD `state.*`
plain-field fallback scoping defect.

Sibling module to ``tests/test_gsd_state_patch.py`` (Phase 182/184, TOOL-01
through TOOL-04). Kept separate per 186.1-CONTEXT.md's "Claude's Discretion"
note on test file organisation, so that this plan's edits do not collide
with plan 186.1-02's concurrent edits to the sibling file.

Root cause under test here (do not re-derive -- see
``.planning/todos/pending/gsd-state-plain-field-fallback-unscoped.md`` and
``186.1-RESEARCH.md``): ``stateReplaceField()``'s and ``stateExtractField()``'s
**plain-field fallback** is already anchored to line start
(``^Field:...``, ``/im`` flags) -- TOOL-04 never touched this branch because
it was already anchored -- but it is **unscoped**: with the ``m`` flag, ``^``
matches the start of *any* line in the whole document body, so the first
line-initial ``Status:`` anywhere in the file wins, real field or not. This
project's real ``.planning/STATE.md`` has no bold ``**Status:**`` field and
no plain ``Status:`` field inside the leading run of ``## Current
Position``'s field-shaped lines, so the bold branch always misses, the
plain fallback always runs, and it has rewritten the same narrative
``Status:`` sentence (in a "prior phase retained for history" block) 8
times across ``state.planned-phase``, ``state.begin-phase``, and
``phase.complete``.

This module builds the RED-before-GREEN infrastructure this defect needs:
an invocation harness for BOTH entry points (the npx ``gsd-sdk`` install and
the ``.claude`` ``gsd-tools.cjs`` install), a STATE.md fixture that actually
reproduces the real file's no-blank-line field/narrative adjacency (a
short, cleanly-separated toy fixture would prove nothing -- see
186.1-RESEARCH.md Pitfall 2), and six negative-control nodes (3 verbs x 2
entry points) proving those fixtures are sensitive to the unpatched code.

D-06/D-07 (186.1-CONTEXT.md): the npx install is content-addressed
(``~/.npm/_npx/<hash>/...``) and rotates silently on every
``get-shit-done-cc`` version bump. This module resolves it dynamically via
``shutil.which("gsd-sdk")`` + ``os.path.realpath`` -- the content-addressed
hash observed on 2026-09-07 (see 186.1-RESEARCH.md's "Re-Resolved Install
Facts" section for the exact value) is deliberately NOT reproduced anywhere
in this file, including comments, so that a literal grep for it never
returns a false sense of currency; it is never used as a path component to
resolve anything at runtime.
"""
from __future__ import annotations

import json
import os
import re
import shutil
from pathlib import Path

import pytest

from tests.cli_helpers import run_fork_safe
from tests.test_gsd_state_patch import (
    GSD_HOME,
    GSD_TOOLS_CJS,
    GSD_TOOLCHAIN_AVAILABLE,
    GSD_SKIP_REASON,
    NODE_PATH,
)

# ---------------------------------------------------------------------------
# npx `gsd-sdk` install resolution -- dynamic, never hash-hardcoded (D-06).
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parent.parent
_REAL_STATE_MD = _REPO_ROOT / ".planning" / "STATE.md"

_GSD_SDK_WHICH = shutil.which("gsd-sdk")


def _resolve_npx_sdk_dist() -> Path | None:
    """Resolve the npx `get-shit-done-cc` install's `sdk/dist` directory
    dynamically from wherever `gsd-sdk` currently resolves on PATH:
    `shutil.which("gsd-sdk")` -> `os.path.realpath` -> walk parents until a
    directory named `dist` whose parent is `sdk` is found.

    Never derives this from a hardcoded content-addressed hash (D-06) --
    the npx cache directory name changes silently on every
    `get-shit-done-cc` version bump (CLAUDE.md §(h)(2)), and a hardcoded
    path would go stale without any error.
    """
    if _GSD_SDK_WHICH is None:
        return None
    real = Path(os.path.realpath(_GSD_SDK_WHICH))
    for candidate in [real, *real.parents]:
        if candidate.name == "dist" and candidate.parent.name == "sdk":
            return candidate
    return None


_NPX_SDK_DIST = _resolve_npx_sdk_dist()
_NPX_SDK_CLI = _NPX_SDK_DIST / "cli.js" if _NPX_SDK_DIST is not None else None
_NPX_QUERY_DIR = _NPX_SDK_DIST / "query" if _NPX_SDK_DIST is not None else None


def _resolve_npx_package_root() -> Path | None:
    """Walk up from the resolved `sdk/dist` directory to the
    `node_modules/get-shit-done-cc` package root, and return that package
    root (never the bare hash directory -- D-06 dynamic-resolution only).

    Needed because `cli.js` is loaded via Node's ESM resolver, which climbs
    `node_modules` directories starting from the importing file's own
    location to resolve bare specifiers like `@anthropic-ai/claude-agent-sdk`.
    A copy of `sdk/dist` alone (with no `node_modules` anywhere above it)
    fails at import time with `ERR_MODULE_NOT_FOUND` -- confirmed empirically
    while building this fixture. The whole package directory (not just
    `sdk/dist`) must be copied, sitting under a `node_modules` sibling that
    also carries (symlinked) copies of every other dependency package.
    """
    if _NPX_SDK_DIST is None:
        return None
    # sdk/dist -> sdk -> get-shit-done-cc -> node_modules -> <hash root>
    candidate = _NPX_SDK_DIST.parent.parent  # get-shit-done-cc
    if candidate.name == "get-shit-done-cc" and candidate.parent.name == "node_modules":
        return candidate
    return None


_NPX_PACKAGE_ROOT = _resolve_npx_package_root()
_NPX_NODE_MODULES = _NPX_PACKAGE_ROOT.parent if _NPX_PACKAGE_ROOT is not None else None

GSD_SDK_AVAILABLE = bool(
    NODE_PATH is not None
    and _GSD_SDK_WHICH is not None
    and _NPX_SDK_DIST is not None
    and _NPX_SDK_DIST.is_dir()
    and _NPX_SDK_CLI is not None
    and _NPX_SDK_CLI.is_file()
    and _NPX_QUERY_DIR is not None
    and (_NPX_QUERY_DIR / "state-document.js").is_file()
    and _NPX_PACKAGE_ROOT is not None
    and _NPX_PACKAGE_ROOT.is_dir()
    and _NPX_NODE_MODULES is not None
    and _NPX_NODE_MODULES.is_dir()
)

if NODE_PATH is None:
    _sdk_skip_check = "node not on PATH"
elif _GSD_SDK_WHICH is None:
    _sdk_skip_check = "`gsd-sdk` not on PATH (shutil.which returned None)"
elif _NPX_SDK_DIST is None or not _NPX_SDK_DIST.is_dir():
    _sdk_skip_check = (
        f"resolved `gsd-sdk` at {_GSD_SDK_WHICH!r} but could not walk to a "
        "sdk/dist directory from its realpath"
    )
elif _NPX_SDK_CLI is None or not _NPX_SDK_CLI.is_file():
    _sdk_skip_check = f"resolved sdk/dist at {_NPX_SDK_DIST} but cli.js is missing"
elif not (_NPX_QUERY_DIR / "state-document.js").is_file():
    _sdk_skip_check = (
        f"resolved sdk/dist at {_NPX_SDK_DIST} but query/state-document.js is missing"
    )
elif _NPX_PACKAGE_ROOT is None or not _NPX_PACKAGE_ROOT.is_dir():
    _sdk_skip_check = (
        f"resolved sdk/dist at {_NPX_SDK_DIST} but could not walk up to a "
        "node_modules/get-shit-done-cc package root (needed for ESM "
        "module resolution when the tree is copied for pristine fixtures)"
    )
elif _NPX_NODE_MODULES is None or not _NPX_NODE_MODULES.is_dir():
    _sdk_skip_check = (
        f"resolved package root at {_NPX_PACKAGE_ROOT} but its sibling "
        "node_modules directory is missing"
    )
else:
    _sdk_skip_check = "available"

GSD_SDK_SKIP_REASON = (
    f"npx `gsd-sdk` install unavailable in this environment ({_sdk_skip_check}) -- "
    "the Linux Full Suite CI job does not provision an npx-installed "
    "get-shit-done-cc, so this leg is honestly skipped there rather than "
    "faked. IMPORTANT: a skip is not a pass -- the plain-field fallback "
    "scan and RED/negative-control nodes gated on GSD_SDK_AVAILABLE were "
    "NOT run and this install was NOT scanned and is NOT proven clean. "
    "Run these tests on an operator machine with `gsd-sdk` on PATH to "
    "actually exercise them."
)

_SDK_SKIP = pytest.mark.skipif(not GSD_SDK_AVAILABLE, reason=GSD_SDK_SKIP_REASON)


def _run_gsd_sdk_query(sdk_cli: Path, root: Path, canonical: str, *extra_argv: str):
    """Invoke `gsd-sdk query <canonical> ... --project-dir <root> ...`
    against an explicit `cli.js` path (never the `gsd-sdk` PATH shim), so
    that `pristine_npx_tree`'s copied-and-swapped tree can be targeted just
    by pointing `sdk_cli` at the copy's `cli.js`.

    Uses `--project-dir`, NOT `--cwd` -- verified today (186.1-RESEARCH.md
    "Command-Boundary RED Proof") against `sdk/dist/cli.js`'s
    `parseCliArgsQueryPermissive`: the npx entry point's top-level argv
    parser only recognises `--project-dir` for this purpose; `--cwd` is
    gsd-tools.cjs's own flag and has no effect here.
    """
    assert NODE_PATH is not None
    argv = [
        NODE_PATH,
        str(sdk_cli),
        "query",
        canonical,
        *extra_argv,
        "--project-dir",
        str(root),
    ]
    return run_fork_safe(argv, timeout=60)


# ---------------------------------------------------------------------------
# Pristine-tree fixtures (negative-control machinery). Never write inside
# the real GSD_HOME or the real npx cache -- always copytree to a tmp dir
# first (T-186.1-01).
# ---------------------------------------------------------------------------

_LOCAL_PATCH_MARKER_186_1 = "LOCAL PATCH (2026-09-07, TOOL-05)"

_NPX_PRISTINE_DIR = Path.home() / ".claude" / "gsd-npx-sdk-patches" / "pristine" / "query"
_CJS_PRISTINE_DIR = Path.home() / ".claude" / "gsd-pristine" / "get-shit-done" / "bin" / "lib"

_NPX_PRISTINE_FILES = (
    "state-document.js",
    "state.js",
    "phase-lifecycle.js",
    "state-mutation.js",
)
_CJS_PRISTINE_FILES = (
    "state-document.generated.cjs",
    "state.cjs",
)


@pytest.fixture(scope="session")
def pristine_npx_tree(tmp_path_factory):
    """A throwaway COPY of the resolved npx `sdk/dist` tree with
    `query/state-document.js`, `query/state.js`, `query/phase-lifecycle.js`,
    and `query/state-mutation.js` swapped for their pristine (pre-any-patch)
    content. Skips (never fails) if the npx install or any pristine source
    is unavailable, or if a pristine source is itself already patched --
    which would make the negative control pass vacuously.
    """
    if not GSD_SDK_AVAILABLE:
        pytest.skip(GSD_SDK_SKIP_REASON)

    missing = [
        name for name in _NPX_PRISTINE_FILES
        if not (_NPX_PRISTINE_DIR / name).is_file()
    ]
    if missing:
        pytest.skip(
            f"pristine npx query sources missing for {missing} under "
            f"{_NPX_PRISTINE_DIR} -- a skip is not a pass, cannot run the "
            "negative control without a known-unpatched baseline"
        )

    for name in _NPX_PRISTINE_FILES:
        text = (_NPX_PRISTINE_DIR / name).read_text(encoding="utf-8", errors="replace")
        if _LOCAL_PATCH_MARKER_186_1 in text:
            pytest.skip(
                f"{_NPX_PRISTINE_DIR / name} unexpectedly contains the "
                f"{_LOCAL_PATCH_MARKER_186_1!r} marker -- it is not a "
                "pristine pre-patch copy, so the negative control would "
                "run against already-patched code and pass vacuously"
            )

    # Node's ESM resolver climbs `node_modules` directories starting from
    # the importing file's location to resolve bare specifiers (e.g.
    # `@anthropic-ai/claude-agent-sdk`, imported transitively by `cli.js`).
    # A copy of `sdk/dist` alone has no `node_modules` above it anywhere and
    # fails at import time with `ERR_MODULE_NOT_FOUND` -- confirmed
    # empirically while building this fixture. Build a symlink farm for
    # every OTHER dependency package (read-only, never written to) and a
    # REAL recursive copy of only `get-shit-done-cc` itself (the package
    # under repair), so the copy's `sdk/dist/query/*.js` can be safely
    # swapped without touching the real, shared npx cache.
    dest_root = tmp_path_factory.mktemp("pristine_npx_tree")
    node_modules_copy = dest_root / "node_modules"
    node_modules_copy.mkdir()
    for entry in _NPX_NODE_MODULES.iterdir():
        if entry.name == "get-shit-done-cc":
            continue
        (node_modules_copy / entry.name).symlink_to(
            entry, target_is_directory=entry.is_dir()
        )
    package_copy = node_modules_copy / "get-shit-done-cc"
    shutil.copytree(_NPX_PACKAGE_ROOT, package_copy)
    dest = package_copy / "sdk" / "dist"

    for name in _NPX_PRISTINE_FILES:
        target = dest / "query" / name
        pristine_bytes = (_NPX_PRISTINE_DIR / name).read_bytes()
        target.write_bytes(pristine_bytes)
        assert _LOCAL_PATCH_MARKER_186_1 not in target.read_text(encoding="utf-8")

    return dest


@pytest.fixture(scope="session")
def pristine_cjs_tree(tmp_path_factory):
    """A throwaway COPY of the whole `.cjs` GSD toolchain with
    `state-document.generated.cjs` and `state.cjs` swapped for their
    pristine (pre-any-patch) content. Mirrors `pristine_npx_tree` above and
    `unpatched_gsd_tree` in the sibling module. Skips, never fails, on
    missing pristine sources or an already-patched pristine baseline.
    """
    if not GSD_TOOLCHAIN_AVAILABLE:
        pytest.skip(GSD_SKIP_REASON)

    missing = [
        name for name in _CJS_PRISTINE_FILES
        if not (_CJS_PRISTINE_DIR / name).is_file()
    ]
    if missing:
        pytest.skip(
            f"pristine .cjs sources missing for {missing} under "
            f"{_CJS_PRISTINE_DIR} -- a skip is not a pass, cannot run the "
            "negative control without a known-unpatched baseline"
        )

    for name in _CJS_PRISTINE_FILES:
        text = (_CJS_PRISTINE_DIR / name).read_text(encoding="utf-8", errors="replace")
        if _LOCAL_PATCH_MARKER_186_1 in text:
            pytest.skip(
                f"{_CJS_PRISTINE_DIR / name} unexpectedly contains the "
                f"{_LOCAL_PATCH_MARKER_186_1!r} marker -- it is not a "
                "pristine pre-patch copy, so the negative control would "
                "run against already-patched code and pass vacuously"
            )

    dest_root = tmp_path_factory.mktemp("pristine_cjs_tree")
    dest = dest_root / "get-shit-done"
    shutil.copytree(GSD_HOME, dest)

    for name in _CJS_PRISTINE_FILES:
        target = dest / "bin" / "lib" / name
        pristine_bytes = (_CJS_PRISTINE_DIR / name).read_bytes()
        target.write_bytes(pristine_bytes)
        assert _LOCAL_PATCH_MARKER_186_1 not in target.read_text(encoding="utf-8")

    return dest


# ---------------------------------------------------------------------------
# Adjacency-representative STATE.md fixture (Task 2). Reproduces the real
# `.planning/STATE.md`'s no-blank-line adjacency between the leading run of
# field-shaped lines under a heading and the narrative prose that follows
# it -- a cleanly-separated toy fixture would not reproduce the defect's
# firing condition (186.1-RESEARCH.md Pitfall 2).
# ---------------------------------------------------------------------------

_STATUS_DECOY = (
    "Status: 184.3-10 complete (2026-09-05) -- `src/dashboard/src/components/"
    "__tests__/new-date-argument-guard.test.ts` was patched. Must not be "
    "rewritten by a later verb run."
)
_PHASE_DECOY = (
    "Phase: 184.3 (timestamp-correctness) -- COMPLETE and VERIFIED "
    "(2026-09-05) -- historical snapshot, must not change."
)
_PLAN_DECOY = (
    "Plan: 11 of 11 complete (01-11 all done) -- historical snapshot, must "
    "not change."
)
_SESSION_NARRATIVE_DECOY = (
    "Third-party functional review completed 2026-08-24 -- historical note, "
    "must not change."
)


def _adjacent_state_md() -> str:
    """A STATE.md fixture structurally mirroring the real file: a leading
    contiguous run of field-shaped lines under `## Current Position` with
    NO `Status:` field and NO `Last activity:` field (matching this repo's
    real file, which is exactly why the bold path misses and the plain
    fallback runs), immediately followed -- no blank line -- by narrative
    prose containing line-initial `Status:`/`Phase:`/`Plan:` decoy
    sentences. Same shape repeated for `## Session Continuity`.
    """
    return f"""---
gsd_state_version: 1.0
milestone: v9.9
status: verifying
---

## Current Position

Phase: 900 (demo) -- EXECUTING
Plan: 1 of 3
Milestone: v9.9 -- demo milestone, arbitrary prose long enough to resemble the real file's Milestone line
184-04 (complete, 2026-09-06) -- Verified the drift hypothesis live, and archived a prior phase's position inline below as a readability convention:
{_PHASE_DECOY}
{_PLAN_DECOY}
{_STATUS_DECOY}
another continuation line of the same archived narrative block

## Session Continuity

Last session: 2026-09-07T00:00:00.000Z
Stopped at: Completed 900-01-PLAN.md
Resume file: 900-02-PLAN.md
{_SESSION_NARRATIVE_DECOY}
"""


def _leading_field_run_lines(section_body: str) -> list[str]:
    """Mirror the leading-run algorithm from 186.1-RESEARCH.md Section 3:
    the contiguous run of blank lines and `Label: value`-shaped lines
    immediately following a heading, ending at the first line that breaks
    that shape."""
    field_shape = re.compile(r"^[A-Za-z][A-Za-z ]{0,40}:\s?")
    run: list[str] = []
    for line in section_body.split("\n"):
        if line.strip() == "":
            run.append(line)
            continue
        if field_shape.match(line):
            run.append(line)
            continue
        break
    return run


def _section_body(content: str, heading: str) -> str:
    outer = re.compile(
        rf"^##\s+{re.escape(heading)}\b[^\n]*\n([\s\S]*?)(?=\n##|\Z)",
        re.IGNORECASE | re.MULTILINE,
    )
    m = outer.search(content)
    assert m, f"heading {heading!r} not found in fixture"
    return m.group(1)


def test_fixture_reproduces_no_blank_line_adjacency() -> None:
    """Self-check (186.1-RESEARCH.md Pitfall 2 / D-09): asserts the fixture
    actually reproduces the real file's no-blank-line adjacency between the
    leading field run and narrative prose, for BOTH sections. If a future
    edit accidentally inserts a blank line here, this node fails loudly
    rather than silently converting every downstream RED/GREEN result into
    noise.

    IMPORTANT, found empirically while verifying the inversion this
    docstring promises (see 186.1-01-SUMMARY.md's "Inversion Test" section
    for the full account): `_leading_field_run_lines()` -- correctly,
    mirroring 186.1-RESEARCH.md's own leading-run algorithm verbatim --
    treats blank lines as part of the run, not as a terminator. A single
    blank-line insertion right before the narrative therefore does NOT
    change which line ends up immediately after the run (the run just
    absorbs the blank and extends by one), so the `next_line`-content
    assertions below are NOT, by themselves, sensitive to that specific
    edit. The explicit `len(...) ==` assertions immediately below EACH
    `next_line` check exist specifically to catch that edit anyway: they
    fail loudly the moment the run's line count changes for any reason,
    including a spuriously inserted blank line, even though the *content*
    check would not have caught it alone.
    """
    content = _adjacent_state_md()

    cp_body = _section_body(content, "Current Position")
    cp_lines = cp_body.split("\n")
    cp_run = _leading_field_run_lines(cp_body)
    # No Status: field anywhere in the leading run (matches the real file's
    # firing condition -- the bold path misses and the fallback runs).
    assert not any(line.strip().startswith("Status:") for line in cp_run), (
        "leading field run under ## Current Position unexpectedly contains "
        "a Status: line -- fixture no longer reproduces the firing condition"
    )
    assert len(cp_run) == 4, (
        f"expected exactly 4 lines (blank heading-separator + Phase/Plan/"
        f"Milestone) in ## Current Position's leading field run -- got "
        f"{len(cp_run)}: {cp_run!r}. A count that has moved means the "
        "fixture's structure changed (e.g. a blank line was inserted before "
        "the narrative block), even if the line immediately after the run "
        "still happens to read the same."
    )
    next_line = cp_lines[len(cp_run)] if len(cp_run) < len(cp_lines) else ""
    assert next_line.strip() != "", (
        "expected a non-blank narrative line immediately after the leading "
        "field run under ## Current Position (no-blank-line adjacency) -- "
        f"got a blank line at position {len(cp_run)}"
    )
    assert "184-04" in next_line, (
        f"expected the narrative block's first line immediately after the "
        f"field run; got: {next_line!r}"
    )

    sc_body = _section_body(content, "Session Continuity")
    sc_lines = sc_body.split("\n")
    sc_run = _leading_field_run_lines(sc_body)
    assert len(sc_run) == 4, (
        f"expected exactly 4 lines (blank heading-separator + Last "
        f"session/Stopped at/Resume file) in ## Session Continuity's "
        f"leading field run -- got {len(sc_run)}: {sc_run!r}. See the CP "
        "assertion above for why this exact-count check exists alongside "
        "the content check below."
    )
    sc_next_line = sc_lines[len(sc_run)] if len(sc_run) < len(sc_lines) else ""
    assert sc_next_line.strip() != "", (
        "expected a non-blank narrative line immediately after the leading "
        "field run under ## Session Continuity (no-blank-line adjacency)"
    )
    assert sc_next_line.strip() == _SESSION_NARRATIVE_DECOY, (
        f"expected the session narrative decoy immediately after the "
        f"leading field run; got: {sc_next_line!r}"
    )


def _seed_phase_complete_inputs(root: Path, phase: int) -> None:
    """Seed the extra inputs `phase.complete` needs beyond `.planning/STATE.md`:
    a `.planning/ROADMAP.md` with a `### Phase <n>` section and an unchecked
    phase checkbox, and `.planning/phases/<n>-demo/` containing one
    `<n>-01-PLAN.md` and one matching `<n>-01-SUMMARY.md` so `findPhaseDir`
    (npx) / `findPhaseInternal` (.cjs) resolve and plan/summary counts are
    non-zero."""
    planning_dir = root / ".planning"
    planning_dir.mkdir(parents=True, exist_ok=True)

    roadmap_md = f"""# Roadmap

## Phase {phase}: Demo Phase

- [ ] Phase {phase} complete

| Phase | Plans | Status | Completed |
|-------|-------|--------|-----------|
| {phase} | 1 | In Progress | 0 |
"""
    (planning_dir / "ROADMAP.md").write_text(roadmap_md, encoding="utf-8")

    phase_dir = planning_dir / "phases" / f"{phase}-demo"
    phase_dir.mkdir(parents=True, exist_ok=True)
    (phase_dir / f"{phase}-01-PLAN.md").write_text(
        f"# Phase {phase} Plan 1\n\nDemo plan.\n", encoding="utf-8"
    )
    (phase_dir / f"{phase}-01-SUMMARY.md").write_text(
        f"# Phase {phase} Plan 1 Summary\n\nDemo summary.\n", encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# Six negative-control nodes: 3 verbs x 2 entry points (Task 3, D-09/D-10).
# Each runs against a PRISTINE (pre-any-patch) tree only -- never the real
# GSD_HOME/npx cache (T-186.1-01) and never the repo's own `.planning/`
# (T-186.1-02, asserted below).
# ---------------------------------------------------------------------------


def _assert_target_is_tmp(root: Path, tmp_path: Path) -> None:
    assert str(root).startswith(str(tmp_path)), (
        f"refusing to run a verb against {root} -- it is not under "
        f"pytest's tmp_path ({tmp_path}); this guard exists to guarantee "
        "no negative control ever touches the real .planning/STATE.md "
        "(T-186.1-02)"
    )


def _assert_corruption_signature(after_text: str) -> None:
    """Assert the specific corruption signature empirically observed while
    building this fixture (NOT the signature originally guessed at plan
    time -- see the SUMMARY's "Corrected Corruption Signature" section for
    the full account of why the guess was wrong and what replaced it).

    The captured `(prefix)` group in `stateReplaceField`'s plain-fallback
    regex is just the field-label syntax itself (`Status: `), not any of
    the decoy's own descriptive text -- so the ENTIRE decoy sentence is
    replaced by the verb's new value, not partially preserved. The
    corruption signature that actually reproduces, verified against the
    real unpatched source for `state.planned-phase`/`state.begin-phase`
    (both installs) and `phase.complete` (npx only -- see
    `test_negative_control_phase_complete_cjs`'s own docstring for why the
    `.cjs` install of that one verb behaves differently), is: the decoy's
    distinguishing lead-in and trailing text are BOTH gone, replaced by a
    short, unrelated field value. Do NOT assert merely that the file
    changed -- these verbs legitimately change other things too.
    """
    assert _STATUS_DECOY not in after_text, (
        "expected the pristine (unpatched) install to corrupt the "
        f"{_STATUS_DECOY!r} decoy line, but it survived byte-identical -- "
        "either the fixture no longer reproduces the defect, or the "
        "pristine tree is not actually unpatched"
    )
    assert "184.3-10 complete (2026-09-05)" not in after_text, (
        "expected the decoy's distinguishing lead-in text to be destroyed "
        "-- got it surviving, meaning the unpatched plain-field fallback "
        "did not reach this decoy the way this fixture assumes"
    )
    assert "Must not be rewritten by a later verb run." not in after_text, (
        "the decoy's trailing clause survived -- expected the unpatched "
        "plain-field fallback to destroy it entirely"
    )


@_SDK_SKIP
def test_negative_control_state_planned_phase_npx(tmp_path, pristine_npx_tree) -> None:
    root = tmp_path
    _assert_target_is_tmp(root, tmp_path)
    (root / ".planning").mkdir(parents=True, exist_ok=True)
    (root / ".planning" / "STATE.md").write_text(_adjacent_state_md(), encoding="utf-8")

    sdk_cli = pristine_npx_tree / "cli.js"
    proc = _run_gsd_sdk_query(
        sdk_cli, root, "state.planned-phase", "--phase", "901", "--plans", "3"
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr

    after_text = (root / ".planning" / "STATE.md").read_text(encoding="utf-8")
    _assert_corruption_signature(after_text)


def test_negative_control_state_planned_phase_cjs(tmp_path, pristine_cjs_tree) -> None:
    if not GSD_TOOLCHAIN_AVAILABLE:
        pytest.skip(GSD_SKIP_REASON)
    root = tmp_path
    _assert_target_is_tmp(root, tmp_path)
    (root / ".planning").mkdir(parents=True, exist_ok=True)
    (root / ".planning" / "STATE.md").write_text(_adjacent_state_md(), encoding="utf-8")

    tools_cjs = pristine_cjs_tree / "bin" / "gsd-tools.cjs"
    argv = [
        NODE_PATH,
        str(tools_cjs),
        "state",
        "planned-phase",
        "--cwd",
        str(root),
        "--phase",
        "901",
        "--plans",
        "3",
    ]
    proc = run_fork_safe(argv, timeout=30)
    assert proc.returncode == 0, proc.stdout + proc.stderr

    after_text = (root / ".planning" / "STATE.md").read_text(encoding="utf-8")
    _assert_corruption_signature(after_text)


@_SDK_SKIP
def test_negative_control_state_begin_phase_npx(tmp_path, pristine_npx_tree) -> None:
    root = tmp_path
    _assert_target_is_tmp(root, tmp_path)
    (root / ".planning").mkdir(parents=True, exist_ok=True)
    (root / ".planning" / "STATE.md").write_text(_adjacent_state_md(), encoding="utf-8")

    sdk_cli = pristine_npx_tree / "cli.js"
    proc = _run_gsd_sdk_query(
        sdk_cli, root, "state.begin-phase",
        "--phase", "901", "--name", "demo", "--plans", "3",
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr

    after_text = (root / ".planning" / "STATE.md").read_text(encoding="utf-8")
    _assert_corruption_signature(after_text)


def test_negative_control_state_begin_phase_cjs(tmp_path, pristine_cjs_tree) -> None:
    if not GSD_TOOLCHAIN_AVAILABLE:
        pytest.skip(GSD_SKIP_REASON)
    root = tmp_path
    _assert_target_is_tmp(root, tmp_path)
    (root / ".planning").mkdir(parents=True, exist_ok=True)
    (root / ".planning" / "STATE.md").write_text(_adjacent_state_md(), encoding="utf-8")

    tools_cjs = pristine_cjs_tree / "bin" / "gsd-tools.cjs"
    argv = [
        NODE_PATH,
        str(tools_cjs),
        "state",
        "begin-phase",
        "--cwd",
        str(root),
        "--phase",
        "901",
        "--name",
        "demo",
        "--plans",
        "3",
    ]
    proc = run_fork_safe(argv, timeout=30)
    assert proc.returncode == 0, proc.stdout + proc.stderr

    after_text = (root / ".planning" / "STATE.md").read_text(encoding="utf-8")
    _assert_corruption_signature(after_text)


@_SDK_SKIP
def test_negative_control_phase_complete_npx(tmp_path, pristine_npx_tree) -> None:
    root = tmp_path
    _assert_target_is_tmp(root, tmp_path)
    (root / ".planning").mkdir(parents=True, exist_ok=True)
    (root / ".planning" / "STATE.md").write_text(_adjacent_state_md(), encoding="utf-8")
    _seed_phase_complete_inputs(root, 901)

    sdk_cli = pristine_npx_tree / "cli.js"
    proc = _run_gsd_sdk_query(sdk_cli, root, "phase.complete", "901")
    assert proc.returncode == 0, proc.stdout + proc.stderr

    after_text = (root / ".planning" / "STATE.md").read_text(encoding="utf-8")
    _assert_corruption_signature(after_text)


def test_negative_control_phase_complete_cjs(tmp_path, pristine_cjs_tree) -> None:
    """DOCUMENTED DIVERGENCE (found empirically while building this fixture,
    not predicted by 186.1-RESEARCH.md): unlike the other five verb x
    entry-point combinations, `phase complete` via the `.cjs` install does
    NOT reproduce visible corruption of `_STATUS_DECOY` in this fixture.

    Root cause, traced and confirmed directly against `state.cjs` /
    `phase.cjs` source (both unpatched on this axis):

    1. `.cjs`'s `readModifyWriteStateMd(statePath, transformFn, cwd)`
       (`state.cjs:1073`) never strips frontmatter before calling
       `transformFn` -- unlike the npx install's `readModifyWriteStateMd`,
       whose frontmatter-stripping is D-03's confirmed load-bearing fact.
       `cmdPhaseComplete`'s inline `stateReplaceFieldWithFallback(
       stateContent, 'Status', null, ...)` call therefore runs against the
       FULL file text, frontmatter included.
    2. The plain-fallback regex is case-insensitive (`/im`) and untied to
       any field-name case convention, so it matches the frontmatter's own
       lowercase `status:` key -- which sits earlier in document order than
       the narrative decoy -- before ever reaching the decoy. Verified
       directly: calling `stateReplaceFieldWithFallback(content, 'Status',
       null, 'Milestone complete')` against this fixture's raw content
       rewrites line 4 (`status: verifying`) to `status: Milestone
       complete` and leaves the body decoy untouched, byte for byte.
    3. That corrupted frontmatter value never reaches disk: immediately
       afterward, `syncStateFrontmatter` re-derives the ENTIRE frontmatter
       block from the (unmodified) body via `buildStateFrontmatter`,
       discarding whatever `transformFn` wrote into the frontmatter
       region and replacing it with a freshly computed value. The net,
       on-disk, command-boundary-visible effect is that this specific
       corruption is silently absorbed and never surfaces.
    4. `cmdStateBeginPhase` (the other `.cjs` verb) additionally contains
       its own inline `## Current Position`-scoped, full-line `/^Status:.*
       $/m` rewrite block (mirroring the npx install's
       `updateCurrentPositionFields`) that `cmdPhaseComplete` does NOT
       have -- this is the actual mechanism that corrupts the decoy for
       `begin-phase`/`planned-phase`, not the `stateReplaceField` call
       itself (which, exactly like `phase.complete`, only ever reaches the
       frontmatter's `status:` key for a field named plain `Status`). This
       inline-block site is a fourth, previously-undocumented location of
       the same unscoped-plain-field defect class, distinct from
       `state-document.js`/`.generated.cjs`'s `stateReplaceField`/
       `stateExtractField` pair that CONTEXT.md/186.1-RESEARCH.md name --
       flagged here for the fix-implementing plans (03/04), not fixed in
       this Wave-0 test-infrastructure plan.

    This is reported here rather than forced into a false pass, per the
    plan's explicit honesty requirement: "If a negative control fails to
    fire against unpatched source, DO NOT adjust the fixture until it
    agrees." The assertions below encode the TRUE, verified behavior for
    this one combination -- the decoy legitimately, verifiably SURVIVES --
    so that a future regeneration of this file does not silently convert
    an honest "does not fire here" finding into a fake "fires everywhere"
    claim.
    """
    if not GSD_TOOLCHAIN_AVAILABLE:
        pytest.skip(GSD_SKIP_REASON)
    root = tmp_path
    _assert_target_is_tmp(root, tmp_path)
    (root / ".planning").mkdir(parents=True, exist_ok=True)
    (root / ".planning" / "STATE.md").write_text(_adjacent_state_md(), encoding="utf-8")
    _seed_phase_complete_inputs(root, 901)

    tools_cjs = pristine_cjs_tree / "bin" / "gsd-tools.cjs"
    argv = [
        NODE_PATH,
        str(tools_cjs),
        "phase",
        "complete",
        "901",
        "--cwd",
        str(root),
    ]
    proc = run_fork_safe(argv, timeout=30)
    assert proc.returncode == 0, proc.stdout + proc.stderr

    after_text = (root / ".planning" / "STATE.md").read_text(encoding="utf-8")
    assert _STATUS_DECOY in after_text, (
        "expected the documented divergence to hold (decoy survives "
        "phase.complete via .cjs, because frontmatter is not stripped and "
        "the corruption redirects into a frontmatter status: key that "
        "syncStateFrontmatter then silently rebuilds away) -- if this now "
        "fails, either the toolchain changed or a genuine new corruption "
        "path opened; investigate before touching this assertion"
    )


def test_negative_control_phase_complete_cjs_frontmatter_redirect_function_level(
    pristine_cjs_tree,
) -> None:
    """Function-level companion to the command-level test above (reusing
    the `test_bug_a_fixture_is_sensitive_to_the_unpatched_regex`-style
    precedent from the sibling module for exactly this situation: a
    command-boundary result that is masked by a downstream rebuild still
    deserves a positive demonstration that the underlying scoping defect
    is real). Calls `stateReplaceFieldWithFallback` directly against the
    pristine (unpatched) `.cjs` source with FULL (non-body-stripped)
    content, and asserts it corrupts the frontmatter `status:` key --
    which is the actual, verified defect this combination exhibits, one
    call site earlier than the command-boundary result can observe.
    """
    if not GSD_TOOLCHAIN_AVAILABLE:
        pytest.skip(GSD_SKIP_REASON)
    state_lib = pristine_cjs_tree / "bin" / "lib" / "state.cjs"
    script = (
        "const { stateReplaceFieldWithFallback } = require(process.argv[1]);"
        "const content = require('fs').readFileSync(process.argv[2], 'utf-8');"
        "const out = stateReplaceFieldWithFallback(content, 'Status', null, 'Milestone complete');"
        "process.stdout.write(out);"
    )
    fixture_path = None
    try:
        import tempfile
        fd, fixture_path = tempfile.mkstemp(suffix=".md")
        import os as _os
        with _os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(_adjacent_state_md())
        proc = run_fork_safe(
            [NODE_PATH, "-e", script, str(state_lib), fixture_path], timeout=30
        )
        assert proc.returncode == 0, proc.stdout + proc.stderr
        out = proc.stdout
    finally:
        if fixture_path is not None:
            Path(fixture_path).unlink(missing_ok=True)

    assert "status: verifying" not in out, (
        "expected the unpatched, unscoped plain-field fallback to corrupt "
        "the frontmatter status: key when given non-body-stripped content"
    )
    assert "status: Milestone complete" in out, (
        "expected the frontmatter status: key specifically to carry the "
        "verb's new value -- confirming the fallback crossed the "
        "frontmatter/body boundary rather than reaching the body decoy"
    )
    assert _STATUS_DECOY in out, (
        "expected the body decoy to survive untouched at this call site -- "
        "confirming the frontmatter redirect, not the decoy, is what "
        "absorbed this particular call"
    )


# ---------------------------------------------------------------------------
# Three positive command-boundary GREEN nodes (186.1-03 Task 3, D-09/D-10):
# run each of the three implicated verbs via `gsd-sdk` against the LIVE,
# now-patched npx install directly -- NOT a pristine copy, and NOT the
# repo's own `.planning/STATE.md` (T-186.1-02, asserted via
# `_assert_target_is_tmp`). Each node proves, at the command boundary
# (never merely at the function level -- CLAUDE.md clause (e)):
#   1. every decoy constant survives byte-identical
#   2. the verb genuinely wrote SOMETHING legitimate inside the leading
#      run (a bare no-op fixture would pass vacuously otherwise)
#   3. the fail-closed path is visible in the verb's own parsed JSON
#      return -- `Status` absent from `updated[]` rather than reported as
#      a successful write (the exact `{"updated": ["Status"]}` tell that
#      was misread for 7 occurrences)
#
# The plan-01 negative controls above remain untouched and still run
# against the PRISTINE tree, proving the fixture is sensitive to the
# unpatched code -- these new GREEN nodes are meaningless without that
# standing sensitivity proof alongside them.
# ---------------------------------------------------------------------------


def _adjacent_state_md_with_plan_count() -> str:
    """Variant of `_adjacent_state_md()` with a `Total Plans in Phase:`
    line added to ## Current Position's leading run (still field-shaped,
    so it does not disturb the run's structure or the decoy exclusion this
    module's self-check already proves). `state.planned-phase` is the only
    one of the three implicated verbs that never legitimately writes
    `Phase:`/`Plan:` themselves (those two are `state.begin-phase`'s and
    `phase.complete`'s territory) -- without a real field for it to update,
    every one of its writes would fail closed against the base fixture,
    proving D-04's visibility but NOT that the verb genuinely wrote
    anything (acceptance criterion 2 needs a real, non-vacuous change).
    """
    base = _adjacent_state_md()
    marker = "Plan: 1 of 3\n"
    assert base.count(marker) == 1, "fixture structure changed unexpectedly"
    return base.replace(marker, marker + "Total Plans in Phase: 3\n", 1)


@_SDK_SKIP
def test_positive_state_planned_phase_npx_live_patched(tmp_path) -> None:
    """186.1-03 GREEN: `state.planned-phase` via the LIVE, now-patched npx
    install (not a pristine copy)."""
    root = tmp_path
    _assert_target_is_tmp(root, tmp_path)
    (root / ".planning").mkdir(parents=True, exist_ok=True)
    (root / ".planning" / "STATE.md").write_text(
        _adjacent_state_md_with_plan_count(), encoding="utf-8"
    )

    assert _NPX_SDK_CLI is not None
    proc = _run_gsd_sdk_query(
        _NPX_SDK_CLI, root, "state.planned-phase", "--phase", "901", "--plans", "5"
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    result = json.loads(proc.stdout)

    after_text = (root / ".planning" / "STATE.md").read_text(encoding="utf-8")

    # 1. Every decoy survives byte-identical.
    assert _STATUS_DECOY in after_text
    assert _PHASE_DECOY in after_text
    assert _PLAN_DECOY in after_text
    assert _SESSION_NARRATIVE_DECOY in after_text

    # 2. The verb genuinely wrote something real inside the leading run --
    # `Total Plans in Phase` is present there (unlike Status/Last Activity/
    # Last Activity Description, none of which exist in this fixture) and
    # gets legitimately updated from 3 to 5.
    assert "Total Plans in Phase: 5" in after_text, (
        f"expected the leading-run Total Plans in Phase field to be "
        f"genuinely updated to 5 -- a no-op result would mean this GREEN "
        f"node proves nothing. Got updated={result.get('updated')!r}"
    )
    assert "Total Plans in Phase: 3" not in after_text

    # 3. D-04 visibility, checked against the PARSED JSON return, not
    # stdout substring presence: Status is absent from updated[] because
    # it does not exist anywhere in the leading run -- an honest no-op,
    # not a misdirected write.
    assert "Status" not in result["updated"], (
        f"expected 'Status' absent from updated[] (fail-closed, no Status "
        f"field in the leading run) -- got {result['updated']!r}"
    )
    assert "Total Plans in Phase" in result["updated"]


@_SDK_SKIP
def test_positive_state_begin_phase_npx_live_patched(tmp_path) -> None:
    """186.1-03 GREEN: `state.begin-phase` via the LIVE, now-patched npx
    install (not a pristine copy). This is the verb 186.1-01's RED
    transcript captured actually corrupting the real repo's STATE.md; this
    node is its direct GREEN inversion."""
    root = tmp_path
    _assert_target_is_tmp(root, tmp_path)
    (root / ".planning").mkdir(parents=True, exist_ok=True)
    (root / ".planning" / "STATE.md").write_text(_adjacent_state_md(), encoding="utf-8")

    assert _NPX_SDK_CLI is not None
    proc = _run_gsd_sdk_query(
        _NPX_SDK_CLI, root, "state.begin-phase",
        "--phase", "901", "--name", "demo", "--plans", "5",
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    result = json.loads(proc.stdout)

    after_text = (root / ".planning" / "STATE.md").read_text(encoding="utf-8")

    # 1. Every decoy survives byte-identical -- this is the exact
    # corruption 186.1-01's RED transcript captured against the real
    # repo's STATE.md; here it must NOT reproduce.
    assert _STATUS_DECOY in after_text
    assert _PHASE_DECOY in after_text
    assert _PLAN_DECOY in after_text
    assert _SESSION_NARRATIVE_DECOY in after_text

    # 2. The verb genuinely wrote something real inside the leading run:
    # Phase/Plan are both present there in the base fixture and both
    # legitimately change.
    assert "Phase: 901 (demo) — EXECUTING" in after_text, (
        f"expected the leading-run Phase field to be genuinely updated -- "
        f"a no-op result would mean this GREEN node proves nothing. Got "
        f"updated={result.get('updated')!r}"
    )
    assert "Phase: 900 (demo) -- EXECUTING" not in after_text
    assert "Plan: 1 of 5" in after_text
    assert "Plan: 1 of 3" not in after_text

    # 3. D-04 visibility, checked against the PARSED JSON return: `Status`
    # is absent from updated[] -- reported only as the coarser
    # 'Current Position' entry (Phase/Plan legitimately changed within
    # it), never as a standalone successful 'Status' write, because no
    # Status: field exists anywhere in the leading run.
    assert "Status" not in result["updated"], (
        f"expected 'Status' absent from updated[] (fail-closed, no Status "
        f"field in the leading run) -- got {result['updated']!r}. This is "
        f"the direct counter to the {{'updated': ['Status']}} tell that "
        f"was misread for 7 occurrences against the real repo's STATE.md."
    )
    assert "Current Position" in result["updated"]


@_SDK_SKIP
def test_positive_phase_complete_npx_live_patched(tmp_path) -> None:
    """186.1-03 GREEN: `phase.complete` via the LIVE, now-patched npx
    install (not a pristine copy).

    `phase.complete`'s JSON return has no per-field `updated`/`failed`
    array (unlike `state.planned-phase`/`state.begin-phase`) -- its
    `state_updated: true` is a document-level flag, not a field-level
    one. D-04's visibility requirement is therefore checked directly
    against the written body instead: the leading run must show NO
    Status: line was ever inserted or matched (this verb's inline splice
    never had insert-when-absent logic for Status to begin with -- only
    `stateReplaceFieldWithFallback` is called for it, which is
    unconditionally null-safe and never inserts), while Phase/Plan (which
    ARE present and legitimately targeted) genuinely change.
    """
    root = tmp_path
    _assert_target_is_tmp(root, tmp_path)
    (root / ".planning").mkdir(parents=True, exist_ok=True)
    (root / ".planning" / "STATE.md").write_text(_adjacent_state_md(), encoding="utf-8")
    _seed_phase_complete_inputs(root, 901)

    assert _NPX_SDK_CLI is not None
    proc = _run_gsd_sdk_query(_NPX_SDK_CLI, root, "phase.complete", "901")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    result = json.loads(proc.stdout)
    assert result["state_updated"] is True

    after_text = (root / ".planning" / "STATE.md").read_text(encoding="utf-8")

    # 1. Every decoy survives byte-identical -- this is one of the three
    # verbs 186.1-01's RED transcript captured corrupting the real repo's
    # STATE.md.
    assert _STATUS_DECOY in after_text
    assert _PHASE_DECOY in after_text
    assert _PLAN_DECOY in after_text
    assert _SESSION_NARRATIVE_DECOY in after_text

    # 2. The verb genuinely wrote something real inside the leading run:
    # Phase/Plan are both present there and both legitimately change
    # (phase.complete rewrites Phase to the completed phase number and
    # resets Plan to "Not started").
    cp_body = _section_body(after_text, "Current Position")
    cp_run = "\n".join(_leading_field_run_lines(cp_body))
    assert "Phase: 901" in cp_run, (
        f"expected the leading-run Phase field to be genuinely updated -- "
        f"a no-op result would mean this GREEN node proves nothing. "
        f"Leading run: {cp_run!r}"
    )
    assert "Plan: Not started" in cp_run

    # 3. D-04 visibility (this verb's JSON shape has no updated[]/failed[]
    # array, so checked against the body directly): no Status: line was
    # ever written into the leading run -- the fail-closed path never
    # inserted one, and the pre-existing absence is preserved rather than
    # silently redirecting into the decoy the way the unpatched fallback
    # did.
    assert not re.search(r"^Status:", cp_run, re.MULTILINE), (
        f"expected no Status: line in the leading run (fail-closed, no "
        f"insert-when-absent for this verb) -- got: {cp_run!r}"
    )
